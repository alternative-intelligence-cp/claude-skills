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
  promote apply this sandbox's commits to the host repository, gated by the
          task's declared scope, under a lock, and never automatically
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
import fcntl
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

# What stays withheld from a worker INSIDE the sandbox (L-7). Everything
# filesystem-shaped is allowed, because an overlay makes it harmless; only the
# outward-facing entries are withheld, and they are withheld BY NAME so the
# list can be diffed against `templates/PERMISSIONS.md`'s "Deliberately not
# requested" table rather than being a second opinion about it (P-4).
#
# `sudo` is a no-op under --cap-drop ALL and `git push` has nothing to
# authenticate with (L-4, MEASURED 0.2.0), so these are belt and braces over a
# structural impossibility -- which is the right order, not a redundancy: the
# refusal names the rule, and a structural failure names nothing.
WORKER_OUTWARD = ("Bash(git push:*)", "Bash(gh:*)", "Bash(pip install:*)",
                  "Bash(uv add:*)", "Bash(sudo:*)")

SETUP_FAILED = "setup-failed"
# Extraction failed after the worker ran. A SEPARATE marker from SETUP_FAILED
# because the two mean opposite things to a supervisor: setup-failed says there
# was no worker, extract-failed says there was one and its exit code in
# exit.txt is still good -- we just could not capture what it produced.
EXTRACT_FAILED = "extract-failed"


# --- the inside permission set, generated (roadmap 0.2.3 §3.3) ------------

def role_tools(role):
    """The `tools:` line of `agents/<role>.md`, as a list.

    ONE HOME. DESIGN §2 records that a role's tool list is the only enforced
    restriction the 0.1 design had, so the headless allowlist is DERIVED from
    it rather than written beside it. F-6, F-24 and F-30 were each a grant and
    a rule disagreeing; a second list here would be the fourth.
    """
    path = os.path.join(PLUGIN, "agents", f"{role}.md")
    if not os.path.exists(path):
        raise SystemExit(
            f"sandbox: no agent definition at agents/{role}.md, so there is no "
            "tool list to derive an allowlist from. A role the plugin does not "
            "define cannot be dispatched.")
    front, seen = [], 0
    for line in open(path, encoding="utf-8"):
        if line.strip() == "---":
            seen += 1
            if seen == 2:
                break
            continue
        if seen == 1:
            front.append(line)
    for line in front:
        if line.startswith("tools:"):
            return [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
    raise SystemExit(f"sandbox: agents/{role}.md declares no `tools:` line")


def allowlist(role):
    """(allowed, disallowed) for `--allowedTools` / `--disallowedTools`.

    `Bash` is passed through bare -- inside an overlay `rm`, `python3 -c`,
    `chmod` and `truncate` can harm nothing that outlives the sandbox, and
    F-30, F-64, F-76 and F-100 are four findings where a command withheld for
    the guard's sake cost a verification chain (L-7). The withholding that
    remains is by name, in WORKER_OUTWARD.
    """
    return list(role_tools(role)), list(WORKER_OUTWARD)


def cmd_allowlist(args):
    allowed, disallowed = allowlist(args.role)
    print("allowed: " + " ".join(allowed))
    print("disallowed: " + " ".join(disallowed))
    return 0


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


def build_mount_plan(repo, merged, home_dir, cmd_file, uid, gid, sid, env_path,
                     parent_session=None):
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
    if parent_session:
        # L-3.1. The board's writer, stated by the harness, because the
        # headless worker's OWN session id is fresh and the guard's rules were
        # written for a subagent that inherits its parent's. Without it the
        # guard reads `unknown` inside -- which refuses devteam/ and keeps
        # policing scopes, the failing-CLOSED direction. See guard.py.
        env["DEVTEAM_PARENT_SESSION"] = parent_session
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
        cmd_file, os.getuid(), os.getgid(), sid, ":".join(ordered),
        getattr(args, "parent_session", None))

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
        "parent_session": getattr(args, "parent_session", None),
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
    base = q(doc["base"] or "")
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
BASE={base}
# Above this, a remainder file is NAMED rather than diffed. Ten mebibytes sits
# two orders of magnitude below where git's binary diff was measured to
# overflow, and already far past anything a person reads as a patch.
PATCH_MAX=10485760

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

# --- extraction (roadmap 0.2.2 §3.1) --------------------------------------
# Runs HERE -- inside the namespace, after the command and before the namespace
# goes -- because the merged view does not outlive it (spec §3.3). Whatever the
# worker produced is captured now or it is gone. Three things are captured and
# LABELLED (L-2.1): the committed work as a bundle, the uncommitted remainder as
# a patch, and the status listing. Never one combined `git diff <base>` -- spec
# S-5's form cannot tell committed from uncommitted, and the promotion gate and
# the report check both need to.
#
# The upper layer is NOT walked to compute any of this (spec §6.1): a deletion
# there is a character device and a removed directory is an xattr. The merged
# view is diffed instead.
#
# An extraction failure is `run` exit 126, signalled by the marker file
# meta/extract-failed and NOT by overwriting exit.txt. The supervisor still
# needs the worker's own exit code; an extraction failure that erased it would
# turn one fault into two. This mirrors how meta/setup-failed carries 125,
# for the same reason: a worker may legitimately exit 125 or 126 itself, so
# the codes are disambiguated by which file exists rather than by the number.
xrc=0
: > "$META/extract.log"

if [ ! -e "$MERGED/.git" ]; then
  : > "$META/status.txt"
  printf 'no-git skipped=not-a-repository\n' >> "$META/extract.log"
else
  # 1. status FIRST, pristine. The ORDER of this step and `add -N` below is
  #    load-bearing and was measured: `add -N` stages intent-to-add, which
  #    rewrites every untracked `??` in `git status` as ` A`. Taken after it,
  #    status.txt would report no untracked paths at all, and anything
  #    downstream that classifies a foreign write by `??` -- check_scope's
  #    `foreign-write` among them -- would silently stop finding them.
  #    `-uall` because `git status` collapses an untracked directory to its
  #    prefix, which 0.1 measured turning a worker's new package into one
  #    foreign write (DESIGN §20).
  git -C "$MERGED" status --porcelain -uall > "$META/status.txt" 2> "$META/status.err"
  rc2=$?
  printf 'status exit=%s\n' "$rc2" >> "$META/extract.log"
  [ "$rc2" -eq 0 ] || xrc=1

  if [ -z "$BASE" ]; then
    printf 'no-base skipped=open-recorded-no-base-sha\n' >> "$META/extract.log"
  else
    # 2. How many commits sit above the base. This count is what decides
    #    whether `bundle create` is called at all: MEASURED, it exits 128 with
    #    `fatal: Refusing to create empty bundle.` and writes no file when
    #    HEAD == base. A worker that committed nothing is the ordinary case,
    #    not an extraction failure, so it must never reach that command.
    NCOMMITS=0
    git -C "$MERGED" rev-list --count "$BASE"..HEAD > "$META/commits.count" 2>> "$META/extract.log"
    rc2=$?
    printf 'rev-list-count exit=%s\n' "$rc2" >> "$META/extract.log"
    if [ "$rc2" -eq 0 ]; then
      NCOMMITS=$(cat "$META/commits.count")
    else
      xrc=1
    fi

    if [ "$NCOMMITS" -gt 0 ] 2>/dev/null; then
      git -C "$MERGED" bundle create "$META/commits.bundle" "$BASE"..HEAD >> "$META/extract.log" 2>&1
      rc2=$?
      printf 'bundle exit=%s commits=%s\n' "$rc2" "$NCOMMITS" >> "$META/extract.log"
      [ "$rc2" -eq 0 ] || xrc=1
    else
      printf 'bundle skipped=no-commits (HEAD == base)\n' >> "$META/extract.log"
    fi

    # 3. The commits themselves, oldest first, one hash and subject per line.
    #    `git log`, not `rev-list`: rev-list --format emits a `commit <hash>`
    #    header line of its own and yields two lines per commit, which is not
    #    the shape §3.1 asks for.
    git -C "$MERGED" log --first-parent --reverse --format='%H %s' "$BASE"..HEAD \
        > "$META/commits.txt" 2>> "$META/extract.log"
    rc2=$?
    printf 'commits-txt exit=%s\n' "$rc2" >> "$META/extract.log"
    [ "$rc2" -eq 0 ] || xrc=1

    # The paths those commits touch, recorded HERE rather than derived at
    # promotion time. Deriving them on the host would mean fetching the bundle
    # into a ref BEFORE the gate had passed -- so `--dry-run` could no longer
    # claim to touch nothing, and the scope would be judged against objects
    # already admitted to the repository. As a file it is also trustworthy: a
    # worker cannot reach meta/, because only meta/cmd.sh is bound inside, and
    # read-only at that.
    git -C "$MERGED" log --first-parent --format= --name-only "$BASE"..HEAD \
        > "$META/commit-paths.raw" 2>> "$META/extract.log"
    rc2=$?
    sort -u "$META/commit-paths.raw" | sed '/^$/d' > "$META/commit-paths.txt"
    rm -f "$META/commit-paths.raw"
    printf 'commit-paths exit=%s paths=%s\n' "$rc2" \
        "$(wc -l < "$META/commit-paths.txt")" >> "$META/extract.log"
    [ "$rc2" -eq 0 ] || xrc=1

    # 4. L-2.3's evidence. A NON-ZERO exit here is DATA, not a failure: it says
    #    the base is no longer an ancestor of HEAD, which is a rewrite of shared
    #    history below the base and is what `promote-history-rewrite` refuses.
    #    So this step must never set xrc -- treating its answer as an error
    #    would convert the finding the gate exists to make into an extraction
    #    fault, and the supervisor would be told the wrong thing.
    git -C "$MERGED" merge-base --is-ancestor "$BASE" HEAD 2>> "$META/extract.log"
    printf '%s\n' "$?" > "$META/base-is-ancestor.txt"
    printf 'base-is-ancestor exit=0 value=%s (non-zero value is DATA, not a fault)\n' \
        "$(cat "$META/base-is-ancestor.txt")" >> "$META/extract.log"

    # 5. The remainder, LAST, because `add -N` is what alters `git status`.
    #    The `-N` cannot be dropped: MEASURED, without it `diff HEAD --binary`
    #    omits new files entirely, so the remainder patch would lose exactly
    #    the work L-2.1 exists to preserve. `--binary` so a binary fixture's
    #    patch survives.
    git -C "$MERGED" add -N . >> "$META/extract.log" 2>&1
    rc2=$?
    printf 'add-N exit=%s\n' "$rc2" >> "$META/extract.log"
    [ "$rc2" -eq 0 ] || xrc=1

    # A file too large for `diff --binary` is EXCLUDED from the patch and NAMED
    # instead. MEASURED on a 2 GiB untracked file:
    #   fatal: Out of memory, malloc failed (tried to allocate 18446744071562723405 bytes)
    # -- an overflow inside git's own binary-diff path, not a limit of this
    # machine, which had 5.5 TB free and 157 GiB of RAM at the time.
    #
    # Failing the extraction over it would be wrong twice over. A large build
    # artifact left uncommitted is ORDINARY -- spec §4 records a sibling
    # project whose compile peaked at 30.9 GiB -- and the remainder is never
    # promoted in any case (§3.2 refuses it), so the patch exists to be READ by
    # a supervisor deciding whether to re-dispatch. Nobody reads two gibibytes.
    # The path is still named in status.txt, which was taken first and does not
    # depend on this step, so what the worker left behind stays on the record
    # either way; only its content is dropped, and the drop is itself recorded.
    #
    # A gate that fails on ordinary work is a gate somebody switches off, which
    # is the same argument that keeps an unstaged host edit out of promotion's
    # pre-flight.
    : > "$META/uncommitted-oversize.txt"
    # This line deliberately uses neither `-z` nor `tr`, and the reason is a
    # property of this whole template rather than of this line. outer_script()
    # returns a Python f-string, so every backslash escape written below is
    # interpreted by PYTHON before the shell ever sees it. Written the obvious
    # way -- tr, backslash-zero, backslash-n -- Python turned the first into a
    # real NUL byte in the generated script, and a NUL cannot be passed in an
    # argv string, so `tr` received an empty set and translated nothing. The
    # nearby printf formats survive the same treatment only by luck: Python
    # turns their backslash-n into a real newline inside single quotes, which
    # the shell accepts as equivalent.
    #
    # This comment was itself the second casualty -- describing the trap using
    # the characters it is about split the comment across a real newline and
    # left the remainder as a command. Hence: no backslash escapes in this
    # template that must reach the shell intact, and none in prose about them.
    # `--name-only` is newline-separated already and needs none.
    # `core.quotePath=false` keeps a non-ASCII path unquoted so it still
    # matches the `:(exclude)` pathspec built from it. A path containing a
    # literal newline remains unhandled: the patch step then fails and is
    # recorded rather than being fatal, which is the safe direction.
    git -C "$MERGED" -c core.quotePath=false diff HEAD --name-only \
        > "$META/changed-names.txt" 2>> "$META/extract.log"
    set --
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      sz=$(wc -c < "$MERGED/$f" 2>/dev/null || echo 0)
      if [ "$sz" -gt "$PATCH_MAX" ] 2>/dev/null; then
        printf '%s %s\n' "$sz" "$f" >> "$META/uncommitted-oversize.txt"
        set -- "$@" ":(exclude)$f"
      fi
    done < "$META/changed-names.txt"
    NOVER=$(wc -l < "$META/uncommitted-oversize.txt")
    [ "$NOVER" -eq 0 ] || printf 'oversize excluded=%s over %s bytes\n' \
        "$NOVER" "$PATCH_MAX" >> "$META/extract.log"

    git -C "$MERGED" diff HEAD --binary -- . "$@" > "$META/uncommitted.patch" \
        2>> "$META/extract.log"
    rc2=$?
    printf 'uncommitted-patch exit=%s bytes=%s excluded=%s\n' "$rc2" \
        "$(wc -c < "$META/uncommitted.patch")" "$NOVER" >> "$META/extract.log"
    # A patch git could not produce is NOT an extraction failure. status.txt
    # already carries the list, and the alternative -- 126, which blocks the
    # sandbox entirely -- would throw away a worker's committed work because of
    # something it left lying beside it. Recorded, not fatal. `promote` reads
    # status.txt as well as the patch for exactly this reason, so a remainder
    # git cannot represent still refuses promotion (§3.2).
    if [ "$rc2" -ne 0 ]; then
      : > "$META/uncommitted.patch"
      printf 'uncommitted-patch UNREPRESENTABLE -- git could not diff the remainder; status.txt is the record of it\n' \
          >> "$META/extract.log"
    fi
  fi
fi

if [ "$xrc" -ne 0 ]; then
  : > "$META/extract-failed"
  echo "sandbox: extraction failed; see meta/extract.log" >&2
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

    # Every artifact a previous `run` on this sandbox may have left. A stale
    # commits.bundle read as this run's output is a promotion of work nobody
    # did in this step, which is the worst shape of wrong available here.
    for stale in ("exit.txt", SETUP_FAILED, EXTRACT_FAILED, "status.txt",
                  "status.err", "extract.log", "commits.bundle",
                  "uncommitted-oversize.txt", "changed-names.txt",
                  "commit-paths.txt", "commit-paths.raw", "promoted.json",
                  "commits.count", "commits.txt", "base-is-ancestor.txt",
                  "uncommitted.patch"):
        try:
            os.unlink(os.path.join(meta, stale))
        except OSError:
            pass

    outer = os.path.join(meta, "outer.sh")
    script = outer_script(path, doc["mount_plan"], doc, args.cmd, args.timeout)
    with open(outer, "w") as fh:
        fh.write(script)
    # The generated script is a Python f-string, so a backslash escape meant for
    # the shell is eaten by Python first -- `\0` becomes a real NUL byte and the
    # command it was an argument to silently receives an empty string. That
    # happened, and it cost a debugging round because the symptom was a step
    # that ran, exited 0 and did nothing. Neither reading the template nor
    # reading the generated file makes it visible; `file(1)` calling the script
    # "binary data" is what makes it visible. So it is checked here rather than
    # remembered: no NUL, and it must parse as a shell script.
    if "\0" in script:
        raise SystemExit(
            "sandbox: the generated outer.sh contains a NUL byte. A backslash "
            "escape in outer_script()'s template was interpreted by Python "
            "instead of reaching the shell. Write the escape doubled, or "
            "avoid it.")
    syn = subprocess.run(["/bin/sh", "-n", outer], capture_output=True, text=True)
    if syn.returncode != 0:
        raise SystemExit(
            "sandbox: the generated outer.sh is not valid shell:\n"
            + (syn.stderr.strip() or "(no message)")
            + "\n  The template is a Python f-string; a literal brace must be "
              "doubled and a backslash escape is consumed by Python first.")
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
    if os.path.exists(os.path.join(meta, EXTRACT_FAILED)):
        # 126, and exit.txt is deliberately left holding the worker's own code.
        # The worker may have succeeded; what failed is our capture of it, and
        # a supervisor that was told only "126" still needs to know whether the
        # step passed before deciding to re-dispatch it.
        say(f"run {doc['id']}: the extraction failed -- exit 126. The worker's "
            f"own exit code was {rc} and is preserved in meta/exit.txt; "
            "meta/extract.log says which step failed. Nothing may be promoted "
            "from this sandbox: what it produced was not captured.")
        return 126
    return rc


# --- dispatch: a headless worker inside (roadmap 0.2.3 §3.1) --------------

DISPATCH_FAILED = "dispatch-failed"


def sandbox_lock_file(repo, task):
    return os.path.join(repo, "devteam", ".run", "locks", f"{task}.sandbox")


def liveness_is_ignored(repo, task):
    """(ok, path) -- is the liveness file git-ignored in this repository?

    IT HAS TO BE, and until this check existed that was a written rule holding
    up a mechanism. `dispatch` writes the `.sandbox` file HOST-side, into
    `devteam/.run/locks/`, before the overlay is mounted -- so the merged view
    sees it as an untracked file inside the repository, it lands in the
    worker's uncommitted remainder, and `promote` refuses the whole promotion
    with `promote-uncommitted`. MEASURED 0.2.3: the first live promotion was
    refused for exactly this, and what saved the second was a `.gitignore` line
    that `setup.py` happens to write.

    So the mechanism depended on a line in a file nobody re-reads, and its
    failure mode was a refusal that names the wrong thing entirely -- a
    supervisor reading `promote-uncommitted` goes looking at the worker.
    A project scaffolded by hand, or one whose `.gitignore` was tidied, gets
    a paid worker round and then a misleading refusal.

    `git check-ignore` is asked rather than the file parsed, because the answer
    depends on precedence, negation and nested `.gitignore` files, and a
    second implementation of those rules here would be a second home for them.
    """
    path = os.path.join(repo, "devteam", ".run", "locks", f"{task}.sandbox")
    rc, _ = _git_rc(repo, "check-ignore", "-q", path)
    return rc == 0, path


def write_liveness(repo, task, text, say):
    """The fourth liveness signal (§3.5): written at dispatch, REWRITTEN at
    exit, never deleted.

    Never deleted for the reason the 0.1 heartbeats are never deleted: an
    absent file and a file nobody has written are the same thing to a reader,
    and recovery has to tell "no worker ran" from "a worker ran and we lost
    it". `ListAgents` cannot see a headless process at all (L-2's accepted
    cost), so this file is the only place a recovering session learns that one
    existed.
    """
    if not task:
        return None
    path = sandbox_lock_file(repo, task)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text + "\n")
    except OSError as e:
        say(f"dispatch: could not write {path}: {e}")
        return None
    return path


def seed_worker_home(path, role, say):
    """Credentials and a generated settings file in the worker's HOME.

    CREDENTIALS are a COPY (0.2.0 variant A, re-measured here inside
    sandbox.py's own composition): a copy, never a bind, so a token refresh
    inside cannot reach the host's file. It dies with the sandbox. The risk
    that remains, and it is REASONED rather than measured: if the provider
    rotates the refresh token when the copy refreshes, the host's copy may be
    invalidated. 0.2.9 is where that gets watched.

    SETTINGS are GENERATED, never the host's. §6 forbids passing the host's
    `~/.claude/settings.json` in, and it is right to: it carries the
    operator's hooks and permissions, which are not the worker's. This file
    carries exactly two things, and the first is the load-bearing one.

    THE GUARD IS REGISTERED HERE AND NOT BY THE PLUGIN, and that is measured
    rather than chosen. `--plugin-dir` DOES read the plugin's hooks.json --
    the CLI logs `Registered 2 hooks from 1 plugins` -- but in the same run it
    logs `hooks modules not loaded: rollout flag (tengu_plugin_hooks_modules)
    is off, from the default (a cold GrowthBook cache, no payload yet)`, and
    guard.py never ran. A fresh HOME has no feature-flag cache, so the flag
    reads its default; the sandbox's own design is what turns the plugin hook
    route off. A settings-file hook fires there and was measured firing.
    """
    home = os.path.join(path, "home")
    cdir = os.path.join(home, ".claude")
    os.makedirs(cdir, exist_ok=True)

    src = os.path.expanduser("~/.claude/.credentials.json")
    if os.path.exists(src):
        dst = os.path.join(cdir, ".credentials.json")
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o600)
        say(f"dispatch: credentials copied into the sandbox HOME "
            f"({os.path.getsize(dst)} bytes, mode 600); the copy dies with it")
    else:
        say("dispatch: no ~/.claude/.credentials.json on this host -- the "
            "worker will authenticate from the environment or not at all")

    settings = {
        "hooks": {"PreToolUse": [{
            "matcher": "Bash|Write|Edit|NotebookEdit",
            "hooks": [{"type": "command",
                       "command": f"python3 {os.path.join(PLUGIN, 'scripts', 'guard.py')}",
                       "timeout": 10}]}]},
        # The observed key from 0.2.0 §3.3 item 6. The worker's HOME is a
        # replacement that carries no host `sandbox` setting, so the CLI's own
        # Bash sandbox is off inside regardless; this states it rather than
        # relying on an absence, because an absence changes when a default does.
        "sandbox": {"enabled": False},
    }
    with open(os.path.join(cdir, "settings.json"), "w") as fh:
        json.dump(settings, fh, indent=1)
    say("dispatch: generated HOME/.claude/settings.json -- guard registered, "
        "the CLI's own sandbox disabled, no permission allowlist (the "
        "allowlist is --allowedTools)")


def cmd_dispatch(args):
    say = lambda m: print(m, file=sys.stderr)
    path = find_sandbox(args.id, getattr(args, "repo", None))
    doc = load_plan(path)
    meta = os.path.join(path, "meta")
    repo, task, step, sid = doc["repo"], doc["task"], doc["step"], doc["id"]

    if not doc.get("parent_session"):
        # REFUSED rather than warned. Without it the guard inside reads
        # `unknown` and refuses the worker its own task file -- so the worker
        # would run, cost money, and fail on its first REPORT append for a
        # reason nothing in its dispatch mentions. A structural refusal here
        # costs nothing; discovering it inside costs a paid round.
        raise SystemExit(
            f"sandbox: {sid} was opened without --parent-session, so the guard "
            "inside cannot tell this worker from a stranger and will refuse it "
            "its own task file (L-3.1). Re-open with `--parent-session <the "
            "board's writer id>`; a sandbox's environment is fixed at `open`.")
    if task:
        ok, lock_path = liveness_is_ignored(repo, task)
        if not ok:
            # REFUSED here, for the same reason the parent-session case is:
            # the alternative is a worker that runs, costs money, succeeds, and
            # then has its whole promotion refused as `promote-uncommitted` --
            # a message about the worker's remainder, for a file the HARNESS
            # put there. Cheap and truthful now, or expensive and misleading
            # later.
            rel = os.path.relpath(lock_path, repo)
            raise SystemExit(
                f"sandbox: {rel} is not git-ignored in {repo}, so the liveness "
                "file this dispatch is about to write would appear in the "
                "worker's overlay as an untracked path and `promote` would "
                "refuse the whole promotion with `promote-uncommitted` -- "
                "naming the worker for something the harness did. Add "
                "`devteam/.run/` to .gitignore (which `/devteam:setup` does; "
                "a hand-scaffolded project may not have it) and dispatch "
                "again.")

    if not os.path.exists(args.dispatch):
        raise SystemExit(f"sandbox: no dispatch file at {args.dispatch}")
    with open(args.dispatch, encoding="utf-8") as fh:
        body = fh.read()

    allowed, disallowed = allowlist(args.role)
    seed_worker_home(path, args.role, say)

    # One line, and no more. The `work` skill IS the procedure; a prompt that
    # restates it is a second home for it and they drift (P-34).
    prompt = (f"You are a devteam `{args.role}`. Invoke the `devteam:work` "
              f"skill and follow it.\n\n{body}")

    argv = ["claude", "-p", prompt,
            "--output-format", "json",
            "--plugin-dir", PLUGIN,
            "--model", args.model,
            # 0.2.0 measured a sandboxed worker connecting to the owner's
            # Google Drive in 11ms over the account's own authenticated
            # channel. The connectors travel with the TOKEN, so clearing the
            # environment and replacing HOME does not clear them, and no
            # overlay touches a document store outside the machine. This flag
            # is not optional and not a network control.
            "--strict-mcp-config",
            "--no-session-persistence",
            "--allowedTools"] + allowed + ["--disallowedTools"] + list(disallowed)
    if args.debug_hooks:
        # Into the worker's HOME, never the repository. MEASURED 0.2.3: with
        # the log inside the repo, `--debug-file` ALSO drops a sibling
        # `latest` symlink beside it, and both land in the worker's
        # uncommitted remainder -- so `promote-uncommitted` refuses a
        # promotion because of a diagnostic the harness itself asked for. A
        # debugging flag that changes the verdict is not a debugging flag.
        # The symlink's target is absolute, which additionally leaves it
        # DANGLING in the merged view during extraction (`cannot open
        # .../merged/latest`), because that path is only real inside.
        argv += ["--debug", "hooks", "--debug-file",
                 os.path.join(WORKER_HOME, "dispatch-debug.log")]

    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    lock = write_liveness(
        repo, task,
        f"{task} {step or '-'} {sid} pid - started {started} "
        f"step-timeout {args.timeout or '-'} root {path}", say)
    say(f"dispatch {sid}: {args.role} on {args.model}, "
        f"{len(allowed)} tools allowed, {len(disallowed)} withheld by name"
        + (f", liveness at {lock}" if lock else ""))

    for stale in (DISPATCH_FAILED, "result.json", "report.txt", "budget.json"):
        try:
            os.unlink(os.path.join(meta, stale))
        except OSError:
            pass

    # MEASURED 0.2.3: without this the CLI waits and prints `no stdin data
    # received in 3s, proceeding without it`. Three seconds is cheap; a
    # dispatch that BLOCKS on a stdin no supervisor will ever write is not,
    # and a backgrounded one would look like a worker that hung.
    argv = ["sh", "-c", 'exec "$@" < /dev/null', "sh"] + argv
    args.cmd = argv
    rc = cmd_run(args, path=path, doc=doc)

    # -- what came back ----------------------------------------------------
    raw = _slurp(os.path.join(meta, "stdout.txt"))
    result = None
    try:
        result = json.loads(raw)
    except Exception:
        pass
    if not isinstance(result, dict):
        with open(os.path.join(meta, DISPATCH_FAILED), "w") as fh:
            fh.write("the worker's stdout was not a JSON object\n")
        say(f"dispatch {sid}: the worker's stdout is not JSON -- "
            f"{len(raw)} byte(s) in meta/stdout.txt. Its own exit was {rc}.")
        write_liveness(repo, task,
                       f"{task} {step or '-'} {sid} exited {rc} at "
                       f"{time.strftime('%Y-%m-%dT%H:%M:%S')} root {path}", say)
        return rc if rc else 1

    with open(os.path.join(meta, "result.json"), "w") as fh:
        json.dump(result, fh, indent=1)
    with open(os.path.join(meta, "report.txt"), "w") as fh:
        fh.write(str(result.get("result") or ""))

    usage = result.get("usage") or {}
    tokens = sum(int(usage.get(k) or 0) for k in
                 ("input_tokens", "output_tokens",
                  "cache_creation_input_tokens", "cache_read_input_tokens"))
    model = ""
    for m in (result.get("modelUsage") or {}):
        model = m
        break
    budget = {"tokens": tokens,
              "minutes": round((result.get("duration_ms") or 0) / 60000.0, 2),
              "model": model or args.model,
              "cost_usd": result.get("total_cost_usd")}
    with open(os.path.join(meta, "budget.json"), "w") as fh:
        json.dump(budget, fh, indent=1)

    # `is_error`, NEVER `subtype`. 0.2.0 measured a run that came back with
    # is_error true, terminal_reason "api_error" and result "Not logged in ·
    # Please run /login" -- carrying `subtype: "success"` in the same object.
    # A dispatch that read subtype would hand a supervisor an unauthenticated
    # worker's empty output as a completed step.
    if result.get("is_error"):
        with open(os.path.join(meta, DISPATCH_FAILED), "w") as fh:
            fh.write(f"is_error true; subtype {result.get('subtype')!r}; "
                     f"terminal_reason {result.get('terminal_reason')!r}\n")
        say(f"dispatch {sid}: the worker reported is_error TRUE "
            f"(subtype {result.get('subtype')!r}, which is not the field to "
            f"read). {str(result.get('result'))[:160]}")
        rc = rc or 1
    else:
        say(f"dispatch {sid}: is_error false, {result.get('num_turns')} turns, "
            f"{budget['tokens']} tokens, {budget['minutes']} min, "
            f"${budget['cost_usd']}")

    # The ROOT is on the line because `check_report` has to find meta/budget.json
    # from here (§3.6) and a sandbox root is a machine-local environment
    # variable, not a project fact. Making the reader resolve
    # DEVTEAM_SANDBOX_ROOT the same way the writer did would be two homes for
    # one path, and the second home is always the one that is wrong.
    write_liveness(repo, task,
                   f"{task} {step or '-'} {sid} exited {rc} at "
                   f"{time.strftime('%Y-%m-%dT%H:%M:%S')} root {path}", say)
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
    if not args.id:
        # LISTING, not detail. `supervise`'s close checklist and `resume` §3
        # both ask "what is still open", and until this existed the only answer
        # was to glob a directory under DEVTEAM_SANDBOX_ROOT -- a machine-local
        # environment variable, which is a second home for a path and the exact
        # thing the `.sandbox` file's `root` field exists to avoid. A closing
        # supervisor that cannot enumerate its own sandboxes closes none of
        # them. MEASURED 0.2.4: the skills said `sandbox.py status` lists what
        # is open, and it refused with `the following arguments are required`.
        roots = sorted(glob.glob(os.path.join(sandbox_base(), "*", "*")))
        rows = []
        for path in roots:
            if not os.path.isdir(path):
                continue
            try:
                doc = load_plan(path)
            except (OSError, ValueError):
                continue
            if args.repo and os.path.realpath(doc["repo"]) != os.path.realpath(args.repo):
                continue
            pid, live = alive(path)
            # A non-empty upper layer is work nobody promoted, and it is the
            # one thing a recovering session can still lose. It is on the
            # listing line for that reason and not for tidiness.
            held = any(True for _ in os.walk(os.path.join(path, "upper")) for _ in _[2]) \
                if os.path.isdir(os.path.join(path, "upper")) else False
            rows.append((doc["id"], doc.get("task") or "-", doc.get("step") or "-",
                         "RUNNING" if live else ("idle" if not pid else "exited"),
                         "work in upper/" if held else "empty", path))
        if not rows:
            print(f"no open sandboxes under {sandbox_base()}")
            return 0
        w = max(len(r[0]) for r in rows)
        for sid, task, step, state, held, path in rows:
            print(f"{sid:<{w}}  {task} {step}  {state:<7}  {held:<14}  {path}")
        print(f"{len(rows)} open sandbox(es) under {sandbox_base()}")
        return 0
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

# --- promotion -------------------------------------------------------------
#
# The only path by which anything a worker did reaches the host, and it is
# never automatic (spec S-7). It is serialised on one lock per repository,
# gated by the task's DECLARED scope, and applied by cherry-pick rather than
# by a fast-forward -- at width above one the host HEAD has moved by the time
# a worker finishes, so its commits must be re-applied, not merged (L-5).

# A commit made inside a sandbox is cited by SUBJECT, never by hash (L-2.2),
# because cherry-pick rewrites every hash at promotion. This is the form a
# subject must take to belong to the task the sandbox was opened for.
SUBJECT = re.compile(r"\A(T-\d+)(?:\.(S-\d+))?:\s+\S")

PROMOTE_REF = "refs/devteam/sandbox/"


class Gate:
    """Every INDEPENDENT finding, and none of the findings it invalidates.

    Every other check in this plugin reports all of its findings, and a caller
    that must fix one thing, re-run, and be told the next thing pays a round
    trip per fault. But `one fault, one finding` is a real rule too -- it is
    why check_plugin registers a skill by its directory before parsing it -- and
    it is about CASCADES, not about stopping. So: report everything that was
    measured independently, and suppress what a fired finding has made
    meaningless. If the history was rewritten below the base, the scope diff is
    being taken over commits that are not the ones which would be applied, and
    reporting its verdict would bury the cause among its consequences.
    """

    def __init__(self):
        self.findings = []
        self.dead = set()

    def live(self, name):
        return name not in self.dead

    def fire(self, name, detail, invalidates=()):
        if name in self.dead:
            return False
        self.findings.append((name, detail))
        self.dead.update(invalidates)
        return True


def _slurp(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return default


def declared_scope(repo, task):
    """(state, entries) for a task's `Scope.`, through check_scope's parser.

    Never a second parser: the grammar has one home, and F-118 -- an annotated
    scope entry that parsed as nothing, and so was a grant nobody had -- is
    what a second one produces. Also never a string-prefix match; `covers`
    handles trailing slashes and `./` the way the guard does.
    """
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import check_scope

    devteam = os.path.join(repo, "devteam")
    rel = os.path.join("tasks", f"{task}.md")
    if not os.path.exists(os.path.join(devteam, rel)):
        return "no-task-file", []
    loaded = check_scope.load_tasks(devteam)
    if not loaded:
        return "no-task-file", []
    tasks, _unparsed = loaded
    if task not in tasks:
        # `load_tasks` returning nothing for this task has TWO causes and they
        # need opposite fixes, so asking git directly is the only honest way to
        # tell them apart. It enumerates tracked files only, so an uncommitted
        # task file declares no scope -- and an empty scope read as permission
        # is F-118's shape exactly. But a file git DOES track can also be
        # dropped, silently, by failing to parse: `# T-1 - say hello` has no
        # status segment, so the heading never matches and the task is not in
        # the map and not in `unparsed` either.
        #
        # MEASURED 0.2.3: a task file that `git ls-files` printed by name was
        # reported `untracked`, with a fix line telling the reader to `git add`
        # a file git already had. Advice that cannot work is worse than none --
        # somebody follows it, nothing changes, and they conclude the gate is
        # broken rather than that their heading is. The parser's silence is not
        # evidence about the index, so it is no longer read as any.
        rc = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch",
                             "--", os.path.join("devteam", rel)],
                            capture_output=True, text=True).returncode
        return ("unparsed" if rc == 0 else "untracked"), []
    entries = []
    for raw in tasks[task][2]:
        e = check_scope.normalise(raw)
        if e:
            entries.append(e)
    return ("ok" if entries else "no-scope"), entries


def covers_declared(entries, path, task):
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import check_scope
    # A task always owns its own file: that is where its execution record and
    # its REPORT block are appended, by the very commit being promoted (P-16).
    if path == os.path.join("devteam", "tasks", f"{task}.md"):
        return True
    return check_scope.covers(entries, path)


def cmd_promote(args):
    path = find_sandbox(args.id, getattr(args, "repo", None))
    meta = os.path.join(path, "meta")
    doc = load_plan(path)
    repo, task, base, sid = doc["repo"], doc["task"], doc["base"], doc["id"]
    gate = Gate()
    say = lambda m: print(m)

    if not task:
        raise SystemExit(
            f"sandbox: {sid} was opened with no --task, so there is no declared "
            "scope to gate a promotion against. A throwaway sandbox is not "
            "promotable; that is what `exec` is for.")

    # -- 1. was anything captured at all -----------------------------------
    if os.path.exists(os.path.join(meta, EXTRACT_FAILED)):
        gate.fire("promote-extraction-failed",
                  "the extraction did not complete; see meta/extract.log. "
                  "What the worker produced was not captured, so nothing here "
                  "can be trusted to be all of it",
                  invalidates=("promote-base-disagreement", "promote-no-task-file",
                               "promote-task-file-untracked", "promote-no-scope",
                               "promote-history-rewrite", "promote-no-commits",
                               "promote-foreign-subject", "promote-out-of-scope",
                               "promote-uncommitted"))

    # -- 2. the base has two homes; make the disagreement a finding ---------
    on_disk = _slurp(os.path.join(meta, "base.sha")).strip()
    if gate.live("promote-base-disagreement") and on_disk != (base or ""):
        gate.fire("promote-base-disagreement",
                  f"meta/base.sha is {on_disk or '(empty)'} and "
                  f"plan.json['base'] is {base or '(empty)'}. Two homes for one "
                  "fact have disagreed, and every check below is taken against "
                  "one of them",
                  invalidates=("promote-no-task-file", "promote-task-file-untracked",
                               "promote-no-scope", "promote-history-rewrite",
                               "promote-no-commits", "promote-foreign-subject",
                               "promote-out-of-scope", "promote-uncommitted"))

    # -- 3. the declared scope ---------------------------------------------
    entries = []
    if gate.live("promote-no-task-file"):
        state, entries = declared_scope(repo, task)
        if state == "no-task-file":
            gate.fire("promote-no-task-file",
                      f"devteam/tasks/{task}.md does not exist, so this sandbox "
                      "has no declared scope to be gated against",
                      invalidates=("promote-task-file-untracked", "promote-no-scope",
                                   "promote-out-of-scope"))
        elif state == "untracked":
            gate.fire("promote-task-file-untracked",
                      f"devteam/tasks/{task}.md exists but git does not track it, "
                      "so its `Scope.` is invisible to the parser and reads as "
                      f"empty. Fix: `git -C {repo} add devteam/tasks/{task}.md` "
                      "and commit it, then promote again",
                      invalidates=("promote-no-scope", "promote-out-of-scope"))
        elif state == "unparsed":
            gate.fire("promote-task-file-unparsed",
                      f"devteam/tasks/{task}.md exists and git tracks it, but "
                      "the task parser does not recognise it, so it declares no "
                      "scope. The heading must carry a status -- "
                      f"`# {task} - <goal> - PLANNED|RUNNING|DONE` -- and the "
                      "scope must be a `- **Scope.**` bullet with one "
                      "backticked path per line beneath it",
                      invalidates=("promote-no-scope", "promote-out-of-scope"))
        elif state == "no-scope":
            gate.fire("promote-no-scope",
                      f"devteam/tasks/{task}.md declares no parseable `Scope.` "
                      "entry. An empty scope is refused rather than read as "
                      "permission: a grant nobody wrote is F-118",
                      invalidates=("promote-out-of-scope",))

    # -- 4. history below the base -----------------------------------------
    anc = _slurp(os.path.join(meta, "base-is-ancestor.txt")).strip()
    if gate.live("promote-history-rewrite") and anc != "0":
        # Anything but 0, not just 1. `merge-base --is-ancestor` exits 128 on a
        # base the repository does not have, which is neither "is an ancestor"
        # nor "is not" -- and a gate written as `== 1` would read that as no
        # finding at all and promote over an undetermined history.
        why = ("the base is no longer an ancestor of the sandbox HEAD"
               if anc == "1" else
               f"the ancestry could not be determined (exit {anc or 'missing'})")
        gate.fire("promote-history-rewrite",
                  f"{why}. Commits at or below the base were rewritten inside "
                  "the sandbox. Above the base a rewrite is the worker's own "
                  "business; below it, it is the host's shared history wearing "
                  "new work as a disguise (L-2.3, P-12b)",
                  invalidates=("promote-foreign-subject", "promote-out-of-scope"))

    # -- 5. what there is to promote ---------------------------------------
    bundle = os.path.join(meta, "commits.bundle")
    commits = [l for l in _slurp(os.path.join(meta, "commits.txt")).split("\n") if l.strip()]
    remainder = _slurp(os.path.join(meta, "uncommitted.patch")).strip()
    status = [l for l in _slurp(os.path.join(meta, "status.txt")).split("\n") if l.strip()]
    oversize = [l for l in _slurp(os.path.join(meta, "uncommitted-oversize.txt")).split("\n")
                if l.strip()]

    if gate.live("promote-no-commits") and not os.path.exists(bundle) \
            and not remainder and not status:
        gate.fire("promote-no-commits",
                  "the sandbox produced no commits and left nothing uncommitted. "
                  "There is nothing to promote, which is a report about the "
                  "worker rather than about this command")

    # -- 6. whose commits are these ----------------------------------------
    if gate.live("promote-foreign-subject"):
        foreign = []
        for line in commits:
            sha, _, subject = line.partition(" ")
            m = SUBJECT.match(subject)
            if not m:
                foreign.append(f"{sha[:8]} {subject[:60]!r} is not of the form "
                               "`T-n: ...` or `T-n.S-m: ...`")
            elif m.group(1) != task:
                foreign.append(f"{sha[:8]} {subject[:60]!r} names {m.group(1)}, "
                               f"but this sandbox was opened for {task}")
        if foreign:
            gate.fire("promote-foreign-subject",
                      "a commit in this sandbox does not belong to its task: "
                      + "; ".join(foreign))

    # -- 7. the scope gate itself ------------------------------------------
    if gate.live("promote-out-of-scope"):
        touched = [l.strip() for l in
                   _slurp(os.path.join(meta, "commit-paths.txt")).split("\n") if l.strip()]
        outside = sorted(p for p in touched if not covers_declared(entries, p, task))
        if outside:
            gate.fire("promote-out-of-scope",
                      f"{len(outside)} path(s) outside the declared scope "
                      f"{entries or '[]'}: " + ", ".join(outside[:12])
                      + (" ..." if len(outside) > 12 else ""))

    # -- 8. a step that did not end committed -------------------------------
    if gate.live("promote-uncommitted") and (remainder or status):
        # Read from status.txt as well as the patch, deliberately. A remainder
        # too large for git to diff leaves the patch EMPTY while the work is
        # still sitting there, and a gate that read only the patch would then
        # promote the commits and call a partial result complete -- which is
        # the exact thing this finding exists to prevent.
        detail = (f"{len(status)} path(s) uncommitted when the sandbox ended: "
                  + ", ".join(s[3:] for s in status[:12])
                  + (" ..." if len(status) > 12 else ""))
        if oversize:
            detail += (f"; {len(oversize)} of them too large to appear in "
                       "uncommitted.patch and named in meta/uncommitted-oversize.txt")
        gate.fire("promote-uncommitted", detail +
                  ". A step is supposed to end committed (P-16), so this worker "
                  "either died or stopped early; promoting its commits while "
                  "discarding this would make a partial result look complete. "
                  "The supervisor decides: re-dispatch, or `close --keep` and "
                  "read the patch")

    # -- 9. the host, before anything is applied ----------------------------
    # A dirty INDEX, and only the index. MEASURED: cherry-pick exits 128 on a
    # staged change to an unrelated file, and exits 0 with an unstaged change or
    # an untracked file present. The manager and the supervisors share one
    # worktree host-side, so an unrelated unstaged edit is the NORMAL state --
    # gating on `status --porcelain` would refuse real promotions routinely, and
    # a gate that blocks legitimate work is a gate somebody switches off.
    # Staged work is different in kind: promoting over it is F-17's class, where
    # the manager's own `git add -A` swept up a worker's commit.
    unstaged, untracked = [], []
    rc_idx, _ = _git_rc(repo, "diff", "--cached", "--quiet")
    for line in git_out(repo, "status", "--porcelain").split("\n"):
        if not line.strip():
            continue
        (untracked if line.startswith("??") else unstaged).append(line[3:])
    if rc_idx != 0:
        gate.fire("promote-host-index-dirty",
                  "the host repository has staged changes. cherry-pick refuses "
                  "over a dirty index, and promoting over somebody's staged work "
                  "is how a commit gets stolen (F-17, F-66). Commit or reset the "
                  "index, then promote again")

    # -- report -------------------------------------------------------------
    for name, detail in gate.findings:
        say(f"{name}: {detail}")
    if gate.findings:
        say(f"promote {sid}: REFUSED -- {len(gate.findings)} finding(s). "
            "Nothing was applied and nothing was written. The way past a "
            "finding is a decision recorded in the task file and a re-run, "
            "never a flag.")
        return 1

    n = len(commits)
    if args.dry_run:
        say(f"promote {sid}: gate clean. Would cherry-pick {n} commit(s) onto "
            f"{git_out(repo, 'rev-parse', '--short', 'HEAD')}:")
        for line in commits:
            sha, _, subject = line.partition(" ")
            say(f"  {sha[:8]} {subject}")
        # Deliberately NOT a conflict prediction. `git merge-tree --write-tree`
        # would give one without touching the repository, and was measured to
        # work -- but it performs a MERGE, while the apply performs a sequence
        # of per-commit three-way applies, and the two can disagree. A dry run
        # that says "clean" and an apply that conflicts is worse than one that
        # says "not determinable", because the first is believed. Measured,
        # considered, declined.
        say("  conflicts are not determinable without applying; this dry run "
            "did not test for them")
        if unstaged or untracked:
            say(f"  host has {len(unstaged)} unstaged and {len(untracked)} "
                "untracked path(s) -- neither blocks a cherry-pick")
        return 0

    return _apply(repo, meta, sid, base, task, commits, unstaged, untracked, say)


def _git_rc(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def _apply(repo, meta, sid, base, task, commits, unstaged, untracked, say):
    ref = PROMOTE_REF + sid
    lockdir = os.path.join(repo, "devteam", ".run", "locks")
    os.makedirs(lockdir, exist_ok=True)
    lock = os.path.join(lockdir, "promote.lock")
    # One lock per repository, held for the apply only (L-2.4). Two supervisors
    # promoting at once cannot conflict on CONTENT -- P-12 makes their scopes
    # disjoint -- but they race on the ref update, and the loser's cherry-pick
    # lands on a HEAD that moved underneath it.
    with open(lock, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        lk.write(f"{os.getpid()} {sid} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
        lk.flush()
        before = git_out(repo, "rev-parse", "HEAD")
        rc, out = _git_rc(repo, "fetch", os.path.join(meta, "commits.bundle"),
                          f"HEAD:{ref}")
        if rc != 0:
            say(f"promote-fetch-failed: {out}")
            return 1
        rc, out = _git_rc(repo, "cherry-pick", "--allow-empty",
                          "--keep-redundant-commits", f"{base}..{ref}")
        if rc != 0:
            conflicted = git_out(repo, "diff", "--name-only", "--diff-filter=U")
            _git_rc(repo, "cherry-pick", "--abort")
            say("promote-conflict: cherry-pick stopped on "
                + (", ".join(conflicted.split("\n")) if conflicted else "no named path")
                + f". The host is back at {before[:8]} and {ref} is left in place "
                "for inspection; `git -C <repo> update-ref -d " + ref +
                "` removes it when you are done.\n  " + out.strip()[:400])
            return 1
        after = git_out(repo, "rev-parse", "HEAD")
        new = [l for l in git_out(repo, "log", "--reverse", "--format=%H %s",
                                  f"{before}..{after}").split("\n") if l.strip()]
        _git_rc(repo, "update-ref", "-d", ref)

    mapped = []
    for i, line in enumerate(commits):
        old, _, subject = line.partition(" ")
        newsha = new[i].split(" ", 1)[0] if i < len(new) else None
        mapped.append({"old": old, "new": newsha, "subject": subject})
        say(f"promoted {old[:8]} -> {(newsha or '?')[:8]} {subject}")
    with open(os.path.join(meta, "promoted.json"), "w") as fh:
        json.dump({"sandbox": sid, "task": task, "base": base,
                   "head_before": before, "head_after": after,
                   "promoted": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "commits": mapped,
                   # Recorded so a later conflict is diagnosable rather than
                   # mysterious: neither of these blocks a cherry-pick, but
                   # both change what the tree looked like when it happened.
                   "host_unstaged_at_promotion": unstaged,
                   "host_untracked_at_promotion": untracked}, fh, indent=2)
    say(f"promote {sid}: {len(mapped)} commit(s) applied; host {before[:8]} -> "
        f"{after[:8]}. The sandbox is NOT closed -- the supervisor decides that, "
        "and `close --keep` preserves the worker's transcript.")
    return 0



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
    p.add_argument("--parent-session", metavar="ID",
                   help="the board's writer id, so the guard inside knows this "
                        "worker is the run's own agent and not a stranger "
                        "(L-3.1). Required before `dispatch`.")

    p = sub.add_parser("run", help="run one command inside an open sandbox")
    p.add_argument("id")
    p.add_argument("--repo", help="disambiguate an id two projects share")
    p.add_argument("--timeout", type=int)

    p = sub.add_parser("exec", help="open + run + close, for a throwaway")
    p.add_argument("--repo", required=True)
    p.add_argument("--keep", action="store_true")
    p.add_argument("--timeout", type=int)
    p.add_argument("--id")

    p = sub.add_parser("dispatch", help="run a headless worker inside a sandbox")
    p.add_argument("id")
    p.add_argument("--repo")
    p.add_argument("--role", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--dispatch", required=True, metavar="FILE",
                   help="the step dispatch; its contents are the prompt")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--debug-hooks", action="store_true",
                   help="write the CLI's hook debug log into the overlay")

    p = sub.add_parser("allowlist", help="the --allowedTools value for a role")
    p.add_argument("--role", required=True)

    p = sub.add_parser("promote", help="apply a sandbox's commits to the host")
    p.add_argument("id")
    p.add_argument("--repo")
    p.add_argument("--dry-run", action="store_true",
                   help="report the gate's findings and the commits that would "
                        "be applied, and touch nothing")

    p = sub.add_parser("status", help="what a sandbox is for, and if it is busy; "
                                      "with no id, every open sandbox")
    p.add_argument("id", nargs="?")
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
    if cmd and args.verb in ("open", "status", "close", "promote",
                            "dispatch", "allowlist"):
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
    if args.verb == "dispatch":
        return cmd_dispatch(args)
    if args.verb == "allowlist":
        return cmd_allowlist(args)
    if args.verb == "promote":
        return cmd_promote(args)
    if args.verb == "status":
        return cmd_status(args)
    return cmd_close(args)


if __name__ == "__main__":
    sys.exit(main())
