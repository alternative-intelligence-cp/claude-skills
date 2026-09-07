#!/usr/bin/env python3
"""A per-worker copy-on-write view of a repository, and the walls around it.

A devteam worker used to be contained by a hook that read its commands and
judged them. That works until the write is spelled in a way the reader does
not parse -- an interpreter heredoc (F-80, F-121) -- or has no path to judge
at all, which is what a history rewrite is (F-71, F-73, F-81). This script
replaces the judgement with a shape: the worker runs inside a mount namespace
where the only writable thing that outlives it is an overlay upper layer of
its own, and the host's tree, index and HEAD are not reachable to be harmed.

The composition, verified in roadmap 0.2.0 §3.3 and built here:

    unshare --user --map-root-user --mount     <- stage one: namespace root,
     |                                            which is what it takes to
     |                                            mount an overlay unprivileged
     +- mount -t overlay (lower=<repo> ro, upper=<id>/upper, work=<id>/work)
         |
         +- bwrap --unshare-user --uid <you> ...  <- stage two: drop back to
         |   |                                       being yourself, because
         |   |                                       the CLI refuses to run
         |   |                                       as root
         |   +- /bin/sh /devteam-cmd.sh            <- the command, from a FILE
         |
         +- extraction, INSIDE the namespace, because the merged view dies
            with it (spec §3.3)

Three things in that picture were learned the hard way and are not style:

  * `bwrap` applies mounts in the order given, so the mount plan is an ORDERED
    LIST and its order is part of its contract. A bind under a replacement
    HOME that is declared before the HOME is shadowed by it.
  * the command is written to a file and the file is executed. Interpolating a
    command through `sh -c "... 'bash -lc \\'...\\''"` is what produced 0.2.0's
    one false reading, and a false reading of an instrument is worse than a
    broken one.
  * the outer stage is namespace-root and the inner stage must not be. Both
    halves are required and they are reconciled by bwrap's nested namespace.

Subcommands:

  open    make a sandbox: the directories, the recorded base SHA, the mount
          plan as data. Refuses on a machine `sandbox_probe.py` will not pass.
  run     mount, compose, execute one command inside, extract, tear down
  exec    open + run + close, for a throwaway experiment with no task
  status  what a sandbox is for, and whether anything is alive on it
  close   remove it, or keep it for a post-mortem

`run` exits with the command's own exit code, so a caller can tell what the
worker did. Two codes are reserved and mean the worker never ran:

  125     the sandbox itself failed to set up. A caller MUST be able to
          distinguish "the worker failed" from "there was no worker", or a
          broken machine reads as a failing task.
  124     the command hit `--timeout` and was killed. The namespace is still
          torn down in order and the extraction still runs.

`run` writes its own narration to STDERR and passes the command's stdout
through unchanged on STDOUT, because a supervisor reads the worker's final
message from there and a harness that mixes its own voice into it hands the
supervisor a report nobody wrote.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.realpath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, ".."))

ID_OK = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")

# HOME inside is a path that exists nowhere on this machine, so nothing a
# worker does under `~` can collide with a host path even by accident. This
# only works because the mount plan builds a root out of named binds inside
# bwrap's own tmpfs; under a `--ro-bind / /` root bwrap cannot create a mount
# point it was not given, which is what 0.2.0 measured.
WORKER_HOME = "/home/devteam-worker"

# `/bin/sh` adds these to the environment of a script it runs. They are
# declared rather than filtered so the control can diff what is actually
# inside against `env` + this, and treat a third thing as a finding (P-4).
SHELL_ADDED = ("PWD", "SHLVL", "_")

SETUP_FAILED = "setup-failed"


# --- where a sandbox lives ------------------------------------------------

def sandbox_base():
    """The directory all sandboxes live under, never inside the repository.

    An upper layer inside its own lower layer is undefined behaviour for
    overlayfs, and a sandbox directory inside the tree would be a foreign
    write to every check the project runs (L-1.3).
    """
    base = os.environ.get("DEVTEAM_SANDBOX_ROOT")
    if not base:
        base = os.environ.get("TMPDIR") or "/tmp"
    return os.path.join(base, "devteam-sandbox")


def project_hash(repo):
    """First 12 hex of sha256 of the repository's real path, so two projects
    never share a root and the same project always finds its own."""
    return hashlib.sha256(os.path.realpath(repo).encode()).hexdigest()[:12]


def sandbox_dir(repo, sid):
    return os.path.join(sandbox_base(), project_hash(repo), sid)


def find_sandbox(sid, repo=None):
    """Locate a sandbox by id. Returns its directory, or raises."""
    if repo:
        path = sandbox_dir(repo, sid)
        if os.path.isdir(path):
            return path
        raise SystemExit(f"sandbox: no sandbox {sid!r} for {repo}")
    hits = sorted(glob.glob(os.path.join(sandbox_base(), "*", sid)))
    hits = [h for h in hits if os.path.isdir(h)]
    if not hits:
        raise SystemExit(f"sandbox: no sandbox {sid!r} under {sandbox_base()}")
    if len(hits) > 1:
        listing = "\n  ".join(hits)
        raise SystemExit(
            f"sandbox: {sid!r} is ambiguous -- {len(hits)} projects have one.\n"
            f"  {listing}\nPass --repo to say which.")
    return hits[0]


def load_plan(path):
    with open(os.path.join(path, "meta", "plan.json")) as fh:
        return json.load(fh)


# --- liveness -------------------------------------------------------------
# `os.kill(pid, 0)` alone answers "is SOME process alive with this number",
# which after a wrap-around is a different question from the one being asked.
# The start time pins the identity.

def proc_starttime(pid):
    try:
        with open(f"/proc/{pid}/stat") as fh:
            data = fh.read()
    except OSError:
        return None
    try:
        return data[data.rindex(")") + 2:].split()[19]
    except (ValueError, IndexError):
        return None


def alive(path):
    """(pid, True) if a `run` is still on this sandbox, else (pid or None, False)."""
    pidfile = os.path.join(path, "meta", "pid")
    try:
        with open(pidfile) as fh:
            pid_s, start = (fh.read().split() + [""])[:2]
        pid = int(pid_s)
    except (OSError, ValueError):
        return None, False
    now = proc_starttime(pid)
    if now is None:
        return pid, False
    if start and now != start:
        return pid, False           # the number was recycled; not our process
    try:
        os.kill(pid, 0)
    except OSError:
        return pid, False
    return pid, True


# --- the mount plan, as data ----------------------------------------------

def _entry(op, args, why):
    return {"op": op, "args": list(args), "why": why}


def _covered(src, planned):
    """True if `src` already sits inside something the plan binds."""
    for e in planned:
        if e["op"] in ("--bind", "--ro-bind", "--ro-bind-try") and e["args"]:
            other = e["args"][0]
            if src == other or src.startswith(other.rstrip("/") + "/"):
                return True
    return False


def read_pin(repo):
    """The charter's environment pin (P-33), if the project has one.

    Returns a list of absolute tool paths. The pin is the project's own
    statement of what a worker runs, so the sandbox binds exactly that rather
    than a second opinion about it (L-1.4).
    """
    pins = sorted(glob.glob(os.path.join(repo, "devteam", ".run", "env", "*", "pin.txt")))
    if not pins:
        return [], None
    paths = []
    for line in open(pins[-1], encoding="utf-8", errors="replace"):
        m = re.search(r"\bat\s+(/\S+)", line)
        if m and os.path.exists(m.group(1)):
            paths.append(m.group(1))
    return paths, pins[-1]


def toolchain_binds(repo):
    """Read-only binds for the interpreter and tools, resolved NOW.

    `~/.local/bin/claude` is a symlink into a versioned directory that an
    auto-update moves -- twice in the two days around 0.2.0 -- so a bind of
    the link alone gives the worker a dangling pointer. Every tool
    contributes both the path it is named by and the path it resolves to.
    """
    binds, path_dirs = [], []
    pinned, pin_file = read_pin(repo)
    named = list(pinned)
    for tool in ("python3", "git", "claude"):
        found = shutil.which(tool)
        if found and found not in named:
            named.append(found)
    for tool in named:
        real = os.path.realpath(tool)
        bindir = os.path.dirname(tool)
        prefix = os.path.dirname(bindir)
        # A venv is a prefix, not a binary: its `bin/python3` resolves to the
        # SYSTEM interpreter while every module it can import lives under the
        # prefix. Binding only the resolved binary, or leaving the venv's own
        # `bin` off PATH, gives the worker a python that starts and cannot
        # import anything the project pinned -- which reads as a broken
        # project rather than a broken sandbox. MEASURED: this machine's
        # `python3` is such a venv.
        if os.path.exists(os.path.join(prefix, "pyvenv.cfg")):
            binds.append((prefix, f"the pinned toolchain prefix for {os.path.basename(tool)}"))
        else:
            binds.append((bindir, f"the directory {os.path.basename(tool)} is named from"))
        binds.append((real, f"what {os.path.basename(tool)} actually resolves to today"))
        # PATH carries the directory the tool is NAMED from, never the one it
        # resolves to: `claude` resolves to a versioned FILE whose directory
        # holds nothing else, and putting that on PATH is how a plausible
        # entry becomes a useless one.
        if bindir not in path_dirs:
            path_dirs.append(bindir)
    return binds, path_dirs, pin_file


def build_mount_plan(repo, merged, home_dir, cmd_file, uid, gid, sid, env_path):
    """The ordered list bwrap is composed from. ORDER IS PART OF THE CONTRACT.

    bwrap applies mounts in sequence. `--tmpfs /tmp` before the repository
    bind is what lets a repository under /tmp be re-created inside the
    replacement; reversed, the tmpfs would bury it. Every entry carries the
    reason it is there, because a mount table nobody can read is one that
    grows a convenience bind and loses the property it was built for.
    """
    plan = [
        _entry("--unshare-user", [], "a user namespace of our own"),
        _entry("--uid", [str(uid)],
               "the worker must NOT be root: `--dangerously-skip-permissions "
               "cannot be used with root/sudo privileges` (0.2.0). The invoking "
               "user's real id, never a hardcoded one"),
        _entry("--gid", [str(gid)], "as above"),
        _entry("--unshare-pid", [], "its processes are not the host's"),
        _entry("--unshare-ipc", [], "no shared memory with the host"),
        _entry("--unshare-uts", [], "its hostname is not the host's"),
        # NOT --unshare-net: L-4. The model API must be reachable. Outward git
        # is made impossible by the environment instead -- no SSH_AUTH_SOCK,
        # no ~/.ssh, no ~/.gitconfig, no gh config, nothing to authenticate.
        _entry("--cap-drop", ["ALL"], "what the harness's own sandbox does; "
               "bwrap sets PR_SET_NO_NEW_PRIVS on its own besides"),
        _entry("--die-with-parent", [], "spec §6.3: no orphaned build holding "
               "the overlay busy after the worker is gone"),
        _entry("--new-session", [], "spec §6.2: without it a sandboxed process "
               "can inject keystrokes into the parent terminal via TIOCSTI, "
               "which is an escape from an otherwise sound sandbox"),
        _entry("--ro-bind", ["/usr", "/usr"], "the system, read-only"),
    ]
    for d in ("/bin", "/sbin", "/lib", "/lib64"):
        plan.append(_entry("--ro-bind-try", [d, d],
                           "spec §6.4: -try, because a merged-/usr system has "
                           "these as symlinks and --ro-bind aborts on them"))
    plan.append(_entry("--ro-bind-try", ["/etc", "/etc"],
                       "certificates, passwd, and the resolver's configuration"))

    # /etc/resolv.conf is a symlink out of /etc on any systemd-resolved
    # machine, so binding /etc alone leaves it dangling and DNS fails inside
    # -- which means the model API is unreachable and a worker cannot run.
    # MEASURED 2026-09-07: `getent hosts` failed without this entry and
    # succeeded with it. Resolved rather than hardcoded, so it holds on a
    # machine that points resolv.conf somewhere else.
    resolv = os.path.realpath("/etc/resolv.conf")
    if os.path.exists(resolv) and not resolv.startswith("/etc/"):
        rdir = os.path.dirname(resolv)
        plan.append(_entry("--ro-bind-try", [rdir, rdir],
                           "where /etc/resolv.conf actually points; without it "
                           "DNS fails inside and the model API is unreachable"))

    plan += [
        _entry("--proc", ["/proc"], "its own, so /proc/self is its own"),
        _entry("--dev", ["/dev"], "a minimal device set; /dev/null and /dev/zero"),
        _entry("--tmpfs", ["/tmp"], "scratch inside is ephemeral. BEFORE the "
               "repository bind, so a repository under /tmp survives it"),
        # A real directory rather than a tmpfs, deliberately: the worker's own
        # transcript lands under HOME and `close --keep` exists so a
        # post-mortem can read it. A tmpfs HOME cannot be kept.
        _entry("--bind", [home_dir, WORKER_HOME],
               "HOME at a path that exists nowhere on the host, backed by a "
               "real directory so `close --keep` can keep the transcript"),
        _entry("--bind", [merged, repo],
               "L-3: the merged view at the SAME absolute path as the host "
               "repository, so every path-shaped rule in the pipeline is still "
               "true inside"),
        _entry("--ro-bind", [PLUGIN, PLUGIN],
               "the plugin, read-only, at its host path so --plugin-dir works"),
    ]

    tools, _path_dirs, pin_file = toolchain_binds(repo)
    for src, why in tools:
        if not os.path.exists(src) or _covered(src, plan):
            continue
        plan.append(_entry("--ro-bind", [src, src], why))

    plan += [
        _entry("--ro-bind", [cmd_file, "/devteam-cmd.sh"],
               "the command, as a FILE. Never interpolated into a quoted "
               "string -- three levels of quoting produced 0.2.0's one false "
               "reading"),
        # LAST, and it is not a tidy-up. bwrap synthesises a directory for
        # every mount point it is given, so binding a toolchain under the
        # host's home materialises `/home/<you>`, `/home/<you>/Workspace` and
        # the rest as WRITABLE directories in bwrap's own root tmpfs. Without
        # this line `echo x > /home/<you>/f` and `mkdir -p
        # /home/<you>/Workspace/REPOS/<a sibling repo>` both SUCCEED inside --
        # into a tmpfs that evaporates. The host is still safe; the worker is
        # not, because it is told a write worked that will never exist
        # anywhere. MEASURED 2026-09-07, both ways. `--remount-ro` touches
        # only the mount named, so /tmp, HOME and the repository stay writable.
        _entry("--remount-ro", ["/"],
               "bwrap's own root, so the directories it synthesised as mount "
               "points cannot be written to and a phantom write fails loudly"),
        _entry("--chdir", [repo], "start where the work is"),
        _entry("--clearenv", [], "spec §4: never the host environment"),
    ]
    env = {
        "PATH": env_path,
        "HOME": WORKER_HOME,
        "LANG": "C.UTF-8",
        "TMPDIR": "/tmp",
        "DEVTEAM_SANDBOX": sid,
    }
    for k, v in env.items():
        plan.append(_entry("--setenv", [k, v], "the environment allowlist is "
                           "data (§3.3); this map is the whole of it"))
    return plan, env, pin_file


def plan_argv(plan):
    argv = []
    for e in plan:
        argv.append(e["op"])
        argv.extend(e["args"])
    return argv


def required_sources(plan):
    """Bind sources that must exist. `-try` entries are excluded by design."""
    return [e["args"][0] for e in plan
            if e["op"] in ("--bind", "--ro-bind") and e["args"]]


# --- open -----------------------------------------------------------------

def probe(quiet=True):
    """Ask sandbox_probe.py, rather than re-deciding what it decides."""
    sys.path.insert(0, HERE)
    import io
    import contextlib
    import sandbox_probe
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = sandbox_probe.main()
    if rc != 0 or not quiet:
        sys.stderr.write(buf.getvalue())
    return rc


def git_out(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def cmd_open(args, narrate=print):
    repo = os.path.realpath(args.repo)
    if not os.path.isdir(repo):
        raise SystemExit(f"sandbox: --repo {args.repo} is not a directory")
    # overlayfs carries lowerdir/upperdir/workdir in one comma-separated,
    # colon-separated option string. A path containing either character is not
    # expressible there, and quietly mounting the wrong thing is the worst
    # available outcome, so it is refused with the reason.
    for p in (repo, sandbox_base()):
        if "," in p or ":" in p:
            raise SystemExit(
                f"sandbox: {p!r} contains ',' or ':', which an overlayfs mount "
                "option string cannot carry. Move the repository, or set "
                "DEVTEAM_SANDBOX_ROOT to a path without them.")

    rc = probe()
    if rc != 0:
        raise SystemExit(
            f"sandbox: refusing to open -- sandbox_probe.py exits {rc} on this "
            "machine. The rows are above; a project here degrades to guard-only.")
    narrate("sandbox: probe clean -- the two-stage composition runs here")

    sid = args.id or "-".join(
        [p for p in (args.task, args.step) if p] + [time.strftime("%H%M%S")])
    if not ID_OK.match(sid):
        raise SystemExit(f"sandbox: id {sid!r} is not [A-Za-z0-9][A-Za-z0-9._-]*")
    path = sandbox_dir(repo, sid)
    if os.path.exists(path):
        raise SystemExit(f"sandbox: {path} already exists -- close it or pick another id")
    for d in ("upper", "work", "merged", "home", "meta"):
        os.makedirs(os.path.join(path, d), exist_ok=True)
    narrate(f"created {path}/{{upper,work,merged,home,meta}}")

    # The base SHA is read from the HOST before anything enters. HEAD lives in
    # the overlay once the worker is inside and the worker may move it, so a
    # later `git diff HEAD` would compare the work against itself (spec §3.4).
    base = git_out(repo, "rev-parse", "HEAD")
    with open(os.path.join(path, "meta", "base.sha"), "w") as fh:
        fh.write((base or "") + "\n")
    narrate(f"base {base or '-'} recorded from `git -C {repo} rev-parse HEAD`"
            + ("" if base else " -- not a git repository, extraction will be empty"))

    cmd_file = os.path.join(path, "meta", "cmd.sh")
    with open(cmd_file, "w") as fh:
        fh.write("#!/bin/sh\n# filled by `sandbox.py run`\n")
    _tools, bindirs, _pin = toolchain_binds(repo)
    seen, ordered = set(), []
    for d in bindirs + ["/usr/local/bin", "/usr/bin", "/bin"]:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    plan, env, pin_file = build_mount_plan(
        repo, os.path.join(path, "merged"), os.path.join(path, "home"),
        cmd_file, os.getuid(), os.getgid(), sid, ":".join(ordered))

    # Recorded, not applied: the overlay does not exist until `run` mounts it,
    # so the identity is seeded inside the namespace where the repository is
    # actually writable. Without it a worker's first commit fails with
    # `Author identity unknown` for a reason unrelated to its task (0.2.0).
    identity = {"name": git_out(repo, "config", "user.name") or "devteam worker",
                "email": git_out(repo, "config", "user.email")
                or "worker@devteam.invalid"}

    doc = {
        "version": 1,
        "id": sid,
        "repo": repo,
        "task": args.task,
        "step": args.step,
        "base": base,
        "root": path,
        "opened": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "home": WORKER_HOME,
        "git_identity": identity,
        "pin": pin_file,
        "mount_plan": plan,
        "env": env,
        "env_shell_added": list(SHELL_ADDED),
        "required_sources": required_sources(plan),
        "cmd": None,
    }
    with open(os.path.join(path, "meta", "plan.json"), "w") as fh:
        json.dump(doc, fh, indent=2)
    ro = sum(1 for e in plan if e["op"].startswith("--ro-bind"))
    narrate(f"mount plan: {len(plan)} ordered entries, {ro} read-only binds, "
            f"{len(env)} environment variables"
            + (f", toolchain from {pin_file}" if pin_file else
               ", toolchain resolved from PATH (no environment pin found)"))
    narrate(f"opened {sid} base {base or '-'} at {path}")
    return sid, path


# --- run ------------------------------------------------------------------

def outer_script(path, plan, doc, cmd_argv, timeout):
    q = shlex.quote
    merged = q(os.path.join(path, "merged"))
    meta = q(os.path.join(path, "meta"))
    over = ",".join([f"lowerdir={doc['repo']}",
                     f"upperdir={os.path.join(path, 'upper')}",
                     f"workdir={os.path.join(path, 'work')}"])
    ident = doc["git_identity"]
    bw = " \\\n  ".join(q(a) for a in ["bwrap"] + plan_argv(plan)
                        + ["--", "/bin/sh", "/devteam-cmd.sh"])
    limit = (f"timeout --kill-after=5 {int(timeout)} " if timeout else "")
    return f"""#!/bin/sh
# Generated by sandbox.py -- stage one. Do not edit; it is rewritten per run.
# This whole file exists inside a user and mount namespace where we are root,
# which is the only way an unprivileged process may mount an overlay.
set -u
MERGED={merged}
META={meta}

mount -t overlay overlay -o {q(over)} "$MERGED" || {{
  echo "sandbox: could not mount the overlay on $MERGED" >&2
  : > "$META/{SETUP_FAILED}"
  exit 125
}}

# Seed the author identity in the OVERLAY's copy of the config. --clearenv and
# a replacement HOME take ~/.gitconfig with them, and a worker's first commit
# would fail with `Author identity unknown` for a reason nothing to do with
# its task. Writing it here copies the real config up whole, remotes included.
if [ -e "$MERGED/.git" ]; then
  git -C "$MERGED" config user.name {q(ident['name'])} || true
  git -C "$MERGED" config user.email {q(ident['email'])} || true
fi

{limit}{bw}
rc=$?
printf '%s\\n' "$rc" > "$META/exit.txt"

# Extraction runs HERE -- inside the namespace, after the command and before
# the namespace goes -- because the merged view does not outlive it (spec
# §3.3). 0.2.2 replaces this stub with the base-SHA diff and the promotion
# bundle; until then it records what the worker left behind.
if [ -e "$MERGED/.git" ]; then
  git -C "$MERGED" status --porcelain -uall > "$META/status.txt" 2> "$META/status.err"
else
  : > "$META/status.txt"
fi
exit $rc
"""


def _tee(stream, sink, path):
    with open(path, "w") as fh:
        for line in iter(stream.readline, ""):
            fh.write(line)
            fh.flush()
            sink.write(line)
            sink.flush()


def cmd_run(args, path=None, doc=None):
    say = lambda m: print(m, file=sys.stderr)
    path = path or find_sandbox(args.id, getattr(args, "repo", None))
    doc = doc or load_plan(path)
    meta = os.path.join(path, "meta")
    pid_alive, is_alive = alive(path)
    if is_alive:
        raise SystemExit(f"sandbox: {doc['id']} already has pid {pid_alive} on it")
    if not args.cmd:
        raise SystemExit("sandbox: run needs a command after `--`")

    missing = [s for s in doc["required_sources"] if not os.path.exists(s)]
    if missing:
        raise SystemExit(
            "sandbox: a required bind source has gone since `open`: "
            + ", ".join(missing)
            + "\n  A toolchain auto-update between open and run is the usual "
              "cause. Close this sandbox and open a new one; the paths are "
              "resolved at open time and never cached longer.")

    cmd_file = os.path.join(meta, "cmd.sh")
    with open(cmd_file, "w") as fh:
        fh.write("#!/bin/sh\n# Generated by sandbox.py run. The command is a FILE\n"
                 "# because interpolating it through nested quotes is what made\n"
                 "# 0.2.0's instrument lie.\n"
                 f"exec {shlex.join(args.cmd)}\n")
    say(f"run {doc['id']}: command written to meta/cmd.sh "
        f"({len(args.cmd)} argv element{'s' if len(args.cmd) != 1 else ''})")

    for stale in ("exit.txt", SETUP_FAILED, "status.txt", "status.err"):
        try:
            os.unlink(os.path.join(meta, stale))
        except OSError:
            pass

    outer = os.path.join(meta, "outer.sh")
    with open(outer, "w") as fh:
        fh.write(outer_script(path, doc["mount_plan"], doc, args.cmd, args.timeout))
    say(f"run {doc['id']}: composing -- unshare --user --map-root-user --mount "
        f"-> mount -t overlay -> bwrap ({len(doc['mount_plan'])} mount entries)"
        + (f", timeout {args.timeout}s" if args.timeout else ""))

    doc["cmd"] = list(args.cmd)
    doc["started"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(os.path.join(meta, "plan.json"), "w") as fh:
        json.dump(doc, fh, indent=2)

    started = time.time()
    proc = subprocess.Popen(
        ["unshare", "--user", "--map-root-user", "--mount", "/bin/sh", outer],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    with open(os.path.join(meta, "pid"), "w") as fh:
        fh.write(f"{proc.pid} {proc_starttime(proc.pid) or ''}\n")
    threads = [
        threading.Thread(target=_tee, args=(proc.stdout, sys.stdout,
                                            os.path.join(meta, "stdout.txt"))),
        threading.Thread(target=_tee, args=(proc.stderr, sys.stderr,
                                            os.path.join(meta, "stderr.txt"))),
    ]
    for t in threads:
        t.start()
    try:
        # `timeout(1)` inside the script is the real limit, so the namespace is
        # torn down in order and the extraction still runs. This one is only a
        # backstop for a `timeout` that itself wedged.
        proc.wait(timeout=(args.timeout + 60) if args.timeout else None)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), 9)
        proc.wait()
        say(f"run {doc['id']}: the backstop fired -- `timeout` did not")
    finally:
        for t in threads:
            t.join()
        try:
            os.unlink(os.path.join(meta, "pid"))
        except OSError:
            pass
    ended = time.time()
    with open(os.path.join(meta, "timing.txt"), "w") as fh:
        fh.write(f"start {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(started))}\n"
                 f"end   {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ended))}\n"
                 f"seconds {ended - started:.1f}\n")

    if os.path.exists(os.path.join(meta, SETUP_FAILED)):
        say(f"run {doc['id']}: the sandbox did not set up -- exit 125. "
            "No command ran; this is not a failing command.")
        return 125
    try:
        with open(os.path.join(meta, "exit.txt")) as fh:
            rc = int(fh.read().strip())
    except (OSError, ValueError):
        say(f"run {doc['id']}: no exit code was recorded -- exit 125. "
            "The namespace died before the command's status could be written.")
        return 125
    try:
        entries = len([l for l in open(os.path.join(meta, "status.txt")) if l.strip()])
    except OSError:
        entries = 0
    note = " (the timeout fired)" if rc == 124 and args.timeout else ""
    say(f"run {doc['id']}: exit {rc}{note} after {ended - started:.1f}s; "
        f"status.txt lists {entries} path{'s' if entries != 1 else ''}")
    return rc


# --- exec, status, close --------------------------------------------------

def cmd_exec(args):
    sid, path = cmd_open(args, narrate=lambda m: print(m, file=sys.stderr))
    doc = load_plan(path)
    try:
        return cmd_run(args, path=path, doc=doc)
    finally:
        if args.keep:
            print(f"kept {path}", file=sys.stderr)
        else:
            remove(path)
            print(f"closed {sid}", file=sys.stderr)


def cmd_status(args):
    path = find_sandbox(args.id, args.repo)
    doc = load_plan(path)
    pid, live = alive(path)
    print(f"sandbox {doc['id']} at {path}")
    print(f"  repo   {doc['repo']}")
    print(f"  task   {doc['task'] or '-'}   step {doc['step'] or '-'}")
    print(f"  base   {doc['base'] or '-'}")
    print(f"  opened {doc['opened']}")
    print(f"  state  " + (f"RUNNING (pid {pid})" if live else
                          f"idle{f' (pid {pid} is gone)' if pid else ''}"))
    if doc.get("cmd"):
        print(f"  cmd    {shlex.join(doc['cmd'])}")
    last = ""
    try:
        lines = [l.rstrip() for l in open(os.path.join(path, "meta", "stderr.txt"))
                 if l.strip()]
        last = lines[-1] if lines else ""
    except OSError:
        pass
    print(f"  stderr {last or '(none)'}")
    return 0


def remove(path):
    """Delete a sandbox tree.

    The upper layer holds whiteouts -- character devices made by the namespace
    root -- and a `work/` directory it made too. Ordinary removal has been
    enough on every machine measured; where it is not, the same namespace that
    made them can unmake them, and saying so is cheaper than a mystery.
    """
    shutil.rmtree(path, ignore_errors=True)
    if os.path.exists(path):
        subprocess.run(["unshare", "--user", "--map-root-user", "--mount",
                        "rm", "-rf", path], capture_output=True)
    if os.path.exists(path):
        return False
    # And the <project-hash> directory above it, if this was the last sandbox
    # in it. Each project gets its own, and a temporary repository gets a new
    # hash every time -- so the control alone left nine empty directories under
    # /tmp in one afternoon. `rmdir` and not `rmtree`: it must refuse if a
    # sibling sandbox is still there.
    for parent in (os.path.dirname(path), sandbox_base()):
        try:
            os.rmdir(parent)
        except OSError:
            break
    return True


def cmd_close(args):
    path = find_sandbox(args.id, args.repo)
    pid, live = alive(path)
    if live:
        raise SystemExit(
            f"sandbox: {args.id} still has pid {pid} on it -- refusing to "
            "remove a sandbox somebody is inside. Wait, or kill it first.")
    if args.keep:
        print(f"kept {path} -- its transcript is under home/.claude/projects/")
        return 0
    if not remove(path):
        raise SystemExit(f"sandbox: could not remove {path}")
    print(f"closed {args.id} -- removed {path}")
    return 0


# --- cli ------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="sandbox.py", description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("open", help="make a sandbox for one task or step")
    p.add_argument("--repo", required=True)
    p.add_argument("--task")
    p.add_argument("--step")
    p.add_argument("--id")

    p = sub.add_parser("run", help="run one command inside an open sandbox")
    p.add_argument("id")
    p.add_argument("--repo", help="disambiguate an id two projects share")
    p.add_argument("--timeout", type=int)

    p = sub.add_parser("exec", help="open + run + close, for a throwaway")
    p.add_argument("--repo", required=True)
    p.add_argument("--keep", action="store_true")
    p.add_argument("--timeout", type=int)
    p.add_argument("--id")

    p = sub.add_parser("status", help="what a sandbox is for, and if it is busy")
    p.add_argument("id")
    p.add_argument("--repo")

    p = sub.add_parser("close", help="remove a sandbox, or keep it")
    p.add_argument("id")
    p.add_argument("--repo")
    p.add_argument("--keep", action="store_true")

    # The command is split off before argparse runs, on the first standalone
    # `--`. argparse.REMAINDER collects from the first token it does not
    # recognise instead, which turned `run <id> --timeout 2 -- sleep 10` into
    # an attempt to execute a program called `--timeout`. A flag quietly
    # becoming the thing to run is the parse to make impossible, not to warn
    # about.
    raw = list(sys.argv[1:] if argv is None else argv)
    cmd = []
    if "--" in raw:
        i = raw.index("--")
        raw, cmd = raw[:i], raw[i + 1:]
    args = ap.parse_args(raw)
    args.cmd = cmd
    if cmd and args.verb in ("open", "status", "close"):
        raise SystemExit(f"sandbox: `{args.verb}` takes no command")
    if args.verb in ("open",):
        args.task = args.task or None
        args.step = args.step or None
        cmd_open(args)
        return 0
    if args.verb == "run":
        return cmd_run(args)
    if args.verb == "exec":
        args.task = args.step = None
        return cmd_exec(args)
    if args.verb == "status":
        return cmd_status(args)
    return cmd_close(args)


if __name__ == "__main__":
    sys.exit(main())
