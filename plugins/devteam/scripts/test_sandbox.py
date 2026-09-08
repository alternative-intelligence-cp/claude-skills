#!/usr/bin/env python3
"""Negative control for sandbox.py (P-35).

A sandbox that has never refused has not been shown to contain anything, and a
sandbox that refuses a legitimate build is one somebody switches off -- which
is strictly worse than no sandbox, because the pipeline still says it has one.
So more than half of the cases here are false-positive controls: writing,
committing, amending, deleting, building, resolving a hostname and filling two
gigabytes must all still work inside.

Two disciplines this file follows and the reason for each:

  * **The two known-answer cases run first** (L-0.2). One write that must be
    contained, one that must not. An instrument that cannot tell those apart
    has nothing to say about the interesting cases behind them, and finding
    that out at case 1 is cheaper than reading twenty-nine wrong verdicts.

  * **Every case asserts the host is byte-identical afterwards**, blocked and
    allowed alike, by hashing the whole throwaway repository and its sibling
    including `.git`. A case that passes its own assertion while changing the
    host has answered the wrong question.

On the error a blocked write should produce. Spec S-4 asks for `No such file
or directory` rather than `Permission denied`, because a permission error
means DAC was built instead of structure. Two things came out of running it:

  * `dash` words ENOENT as `Directory nonexistent`, `bash` as `No such file or
    directory`, and Python as `FileNotFoundError`. An assertion on the prose
    is an assertion about which shell the worker used. So the cases here
    assert the ERRNO where they can get at it, and elsewhere assert only that
    the command failed and that the reason was NOT `Permission denied` --
    which is the distinction S-4 actually cares about.
  * `Read-only file system` (EROFS) is the second structural answer and is not
    a DAC failure. It is what bwrap's own root returns for the directories it
    synthesised as mount points -- see sandbox.py's `--remount-ro /` entry.

Exit 0 all green, 1 any case failed, 2 could not run here (and it says why --
a control that cannot run must never pass).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
SANDBOX = os.path.join(HERE, "sandbox.py")
PLUGIN = os.path.normpath(os.path.join(HERE, ".."))
HOME = os.path.expanduser("~")

# Set on the host for one case, to prove they do not survive `--clearenv`.
# A control that asserts the absence of something never present proves
# nothing, so they are put there on purpose before the assertion is made.
LEAKY_ENV = {
    "SSH_AUTH_SOCK": "/tmp/devteam-control-fake-agent",
    "GH_TOKEN": "gho_devteam_control_not_a_real_token",
    "GITHUB_TOKEN": "ghs_devteam_control_not_a_real_token",
    "ANTHROPIC_API_KEY": "sk-ant-devteam-control-not-a-real-key",
    "GIT_AUTHOR_NAME": "Host Identity That Must Not Travel",
}

PY_ERRNO = ("import sys\n"
            "try:\n"
            "    open(sys.argv[1], 'w').write('x')\n"
            "    print('errno=0-WROTE')\n"
            "except OSError as e:\n"
            "    print('errno=%d' % e.errno)\n")


def tree_hash(root):
    """Every file under root, content and all, `.git` included."""
    h = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            p = os.path.join(base, name)
            h.update(os.path.relpath(p, root).encode())
            try:
                if os.path.islink(p):
                    h.update(b"L" + os.readlink(p).encode())
                else:
                    with open(p, "rb") as fh:
                        h.update(fh.read())
            except OSError as exc:
                h.update(b"E%d" % (exc.errno or 0))
    return h.hexdigest()


def build_fixture(root):
    """A throwaway repository, and a sibling one beside it that nothing in
    this suite is allowed to touch."""
    repo = os.path.join(root, "repo")
    sibling = os.path.join(root, "sibling")
    for path, name in ((repo, "Fixture"), (sibling, "Sibling")):
        os.makedirs(os.path.join(path, "build"), exist_ok=True)
        for cmd in (["init", "-q", "."], ["config", "user.name", name],
                    ["config", "user.email", f"{name.lower()}@devteam.invalid"]):
            subprocess.run(["git", "-C", path, *cmd], check=True,
                           capture_output=True)
        with open(os.path.join(path, "tracked.txt"), "w") as fh:
            fh.write("v1\n")
        with open(os.path.join(path, "build", "artifact"), "w") as fh:
            fh.write("old\n")
        with open(os.path.join(path, "test_smoke.py"), "w") as fh:
            fh.write("def test_ok():\n    assert True\n")
        subprocess.run(["git", "-C", path, "add", "-A"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", path, "commit", "-qm", "base"], check=True,
                       capture_output=True)
    return repo, sibling


# --- assertions a case can ask for ---------------------------------------

def upper(ctx, *parts):
    return os.path.join(ctx["path"], "upper", *parts)


def landed_in_upper(name):
    def check(ctx):
        if not os.path.exists(upper(ctx, name)):
            return f"{name} is not in the upper layer"
    return check


def is_whiteout(name):
    def check(ctx):
        p = upper(ctx, name)
        try:
            st = os.stat(p, follow_symlinks=False)
        except OSError:
            return f"{name} has no entry in the upper layer at all"
        import stat as st_
        if not st_.S_ISCHR(st.st_mode) or st.st_rdev != 0:
            return f"{name} in the upper layer is not a 0/0 whiteout device"
    return check


def host_absent(path):
    def check(ctx):
        if os.path.exists(path.format(**ctx["fmt"])):
            return f"{path.format(**ctx['fmt'])} EXISTS on the host"
    return check


def size_at_least(name, want):
    def check(ctx):
        try:
            got = os.path.getsize(upper(ctx, name))
        except OSError as exc:
            return str(exc)
        if got < want:
            return f"{name} is {got} bytes in the upper layer, wanted {want}"
    return check


def env_matches_the_plan(ctx):
    """`env` inside, diffed against the declared allowlist (§3.3).

    The comparison is two lists (P-4): what the plan says will be there, plus
    the variables `/bin/sh` declares it adds. Anything else inside is a leak
    and anything missing is a sandbox that will not run a worker.
    """
    with open(os.path.join(ctx["path"], "meta", "plan.json")) as fh:
        plan = json.load(fh)
    inside = {}
    for line in ctx["stdout"].splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            inside[k] = v
    allowed = set(plan["env"]) | set(plan["env_shell_added"])
    extra = sorted(set(inside) - allowed)
    if extra:
        return f"variables inside that the plan never declared: {extra}"
    for k, v in plan["env"].items():
        if inside.get(k) != v:
            return f"{k} is {inside.get(k)!r} inside, the plan says {v!r}"
    for k in LEAKY_ENV:
        if k in inside:
            return f"{k} survived --clearenv"
    return None


def uid_map_is_not_the_host(ctx):
    if ctx["stdout"].split() == ["0", "0", "4294967295"]:
        return "uid_map inside is the host identity map -- nothing was unshared"


def resolv_conf_is_usable(ctx):
    """0.2.1 §3.2: `/etc/resolv.conf` is a symlink into `/run` on any
    systemd-resolved machine, and `--ro-bind-try /etc /etc` leaves it dangling
    -- a sandbox with no DNS, whose failure surfaces one subcycle later as an
    authentication error and is read as a credentials problem. The mount plan
    binds what the symlink points at; this case is what says so. It reads the
    file rather than the network, so it answers only about the mount."""
    if "nameserver" not in ctx["stdout"]:
        return ("/etc/resolv.conf inside carries no `nameserver` line -- the "
                "symlink target is not bound, and a worker cannot reach the "
                "model API (0.2.1 §3.2)")


def exit_file_says(want):
    def check(ctx):
        try:
            with open(os.path.join(ctx["path"], "meta", "exit.txt")) as fh:
                got = fh.read().strip()
        except OSError as exc:
            return str(exc)
        if got != str(want):
            return f"meta/exit.txt says {got!r}, wanted {want!r}"
    return check


def no_leftover(pattern):
    def check(ctx):
        p = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return f"processes matching {pattern!r} outlived the sandbox: {p.stdout.split()}"
    return check


# --- the cases ------------------------------------------------------------
# name, argv inside, expectation. `want` is "ok", "fail", or an exit code.
# `out` is a substring stdout must contain. `check` is one callable or a list.
# Names beginning `fp-` are false-positive controls: they must be ALLOWED.

def cases(fmt):
    f = lambda s: s.format(**fmt)
    escape = f("{home}/devteam-sandbox-control-escape.txt")
    deep = f("{home}/devteam-control-no-such-dir/f")
    return [
        # -- the two known answers, first, before anything interesting ------
        dict(name="known-contained-write", want="fail",
             cmd=["sh", "-c", f"echo x > {escape}"],
             check=host_absent(escape)),
        dict(name="fp-known-allowed-write", want="ok",
             cmd=["sh", "-c", f("echo v2 > {repo}/tracked.txt")],
             check=landed_in_upper("tracked.txt")),

        # -- contained ------------------------------------------------------
        dict(name="absolute-host-path-deep", want="fail",
             cmd=["sh", "-c", f"echo x > {deep}"], check=host_absent(deep)),
        dict(name="interpreter-write-outside", want="fail_is_ok",
             cmd=["python3", "-c", PY_ERRNO, f("{sibling}/planted.txt")],
             out="errno=2", check=host_absent(f("{sibling}/planted.txt"))),
        dict(name="interpreter-heredoc-outside", want="fail",
             cmd=["sh", "-c",
                  f("python3 - <<'PY'\nopen('{sibling}/heredoc.txt','w').write('x')\nPY")],
             err="FileNotFoundError",
             check=host_absent(f("{sibling}/heredoc.txt"))),
        dict(name="traversal-to-a-sibling", want="fail",
             cmd=["sh", "-c", f("cd {repo} && echo x > ../sibling/f")],
             check=host_absent(f("{sibling}/f"))),
        # The symlink target is a file this user OWNS AND CAN WRITE, and that
        # is the whole design of the case. Pointing it at /etc/passwd -- the
        # obvious choice, and the one this control shipped with for an hour --
        # is refused with `Permission denied` by ordinary Unix permissions,
        # word for word, WITH THE SANDBOX AND WITHOUT IT. MEASURED both ways.
        # A case that returns the same verdict when the mechanism it tests is
        # absent is not a strict case; it is a case that cannot fail (P-35b).
        dict(name="symlink-planted-to-a-writable-host-file", want="fail",
             cmd=["sh", "-c", f("ln -sf {sibling}/tracked.txt {repo}/link "
                                "&& echo pwned >> {repo}/link")],
             check=landed_in_upper("link")),
        dict(name="fp-symlink-followed-inside-the-overlay", want="ok",
             out="followed",
             cmd=["sh", "-c", f("cd {repo} && ln -sf tracked.txt inner "
                                "&& echo v2 > inner && cat tracked.txt "
                                "&& echo followed")],
             check=landed_in_upper("tracked.txt")),
        dict(name="commit-into-a-sibling-repository", want="fail",
             cmd=["git", "-C", fmt["sibling"], "commit", "--allow-empty",
                  "-m", "intruder"]),
        dict(name="git-push", want="fail", cmd=["git", "-C", fmt["repo"], "push"]),
        dict(name="write-under-the-plugin-root", want="fail",
             cmd=["sh", "-c", f("echo x > {plugin}/CONTROL-PROBE.txt")],
             check=host_absent(f("{plugin}/CONTROL-PROBE.txt"))),
        dict(name="sudo", want="fail", cmd=["sudo", "-n", "true"]),
        dict(name="mount-inside", want="fail",
             cmd=["sh", "-c", "mount -t tmpfs none /mnt"]),
        dict(name="kill-the-namespace-init", want="ok", out="still-here",
             cmd=["sh", "-c", "kill -9 1 2>/dev/null; echo still-here"]),
        dict(name="timeout-kills-a-long-command", want=124, timeout=2,
             cmd=["sleep", "600"],
             check=[exit_file_says(124), no_leftover("sleep 600")]),

        # -- false-positive controls ---------------------------------------
        dict(name="fp-create-modify-delete-inside", want="ok",
             cmd=["sh", "-c", f("cd {repo} && echo n > new.txt && echo m >> "
                                "tracked.txt && rm test_smoke.py && ls")],
             check=landed_in_upper("new.txt")),
        dict(name="fp-git-add-and-commit", want="ok", out="worker commit",
             cmd=["sh", "-c", f("cd {repo} && echo v2 > tracked.txt && git add -A "
                                "&& git commit -qm 'worker commit' "
                                "&& git log -1 --format=%s")]),
        dict(name="fp-git-commit-amend", want="ok", out="amended by the worker",
             cmd=["sh", "-c", f("cd {repo} && echo v2 > tracked.txt && git add -A "
                                "&& git commit -qm first "
                                "&& git commit -q --amend -m 'amended by the worker' "
                                "&& git log -1 --format=%s")]),
        dict(name="fp-rm-rf-a-directory", want="ok",
             cmd=["rm", "-rf", f("{repo}/build")],
             check=[is_whiteout("build"),
                    lambda ctx: None if os.path.exists(
                        f("{repo}/build/artifact")) else "the host build/ is gone"]),
        dict(name="fp-interpreter-write-inside", want="ok", out="errno=0-WROTE",
             cmd=["python3", "-c", PY_ERRNO, f("{repo}/from-python.txt")],
             check=landed_in_upper("from-python.txt")),
        dict(name="fp-read-usr-etc-plugin-repo", want="ok", out="all-four-read",
             cmd=["sh", "-c",
                  f("head -c1 /usr/bin/env >/dev/null && head -c1 /etc/hostname "
                    ">/dev/null && head -c1 {plugin}/PROTOCOL.md >/dev/null && "
                    "head -c1 {repo}/tracked.txt >/dev/null && echo all-four-read")]),
        dict(name="fp-two-gibibytes-under-the-repo", want="ok",
             cmd=["dd", "if=/dev/zero", f("of={repo}/big.bin"), "bs=1M",
                  "count=2048", "status=none"],
             check=size_at_least("big.bin", 2 * 1024 ** 3)),
        dict(name="fp-uid-map-is-ours", want="ok", cmd=["cat", "/proc/self/uid_map"],
             check=uid_map_is_not_the_host),
        dict(name="fp-exit-code-passes-through", want=3,
             cmd=["sh", "-c", "exit 3"], check=exit_file_says(3)),
        dict(name="fp-timeout-not-reached", want="ok", out="done", timeout=5,
             cmd=["sh", "-c", "sleep 1; echo done"]),
        dict(name="fp-the-environment-is-the-allowlist", want="ok", cmd=["env"],
             env=LEAKY_ENV, check=env_matches_the_plan),
        dict(name="fp-resolv-conf-is-bound", want="ok",
             cmd=["cat", "/etc/resolv.conf"], check=resolv_conf_is_usable),
        dict(name="fp-home-and-tmp-are-writable", want="ok", out="both",
             cmd=["sh", "-c", "touch $HOME/w && touch /tmp/w && echo both"]),
    ]


def dns_case(fmt):
    """A live lookup states something about the network as much as about the
    sandbox, so it runs only when the host can resolve the same name.

    It is still worth having: L-4 shares the network namespace on purpose, and
    the case that would catch a sandbox breaking DNS while the host is fine is
    this one. What it must not do is go red when the resolver blips -- that
    happened once, and `getent`'s exit 2 for `not found` was reported as
    `command written to meta/cmd.sh (3 argv elements)`, which sent the reader
    to the command composition. A control that reds for a reason outside its
    subject teaches its operator to re-run until green, and that is the habit
    that hides a real regression."""
    probe = subprocess.run(["getent", "hosts", "api.anthropic.com"],
                           capture_output=True)
    if probe.returncode != 0:
        print("sandbox control: SKIP fp-dns-resolves -- the HOST cannot "
              "resolve api.anthropic.com either (getent exit "
              f"{probe.returncode}), so this case has nothing to say about "
              "the sandbox. The case count below is one lower for that "
              "reason and no other.")
        return []
    return [dict(name="fp-dns-resolves", want="ok", out="resolved",
                 cmd=["sh", "-c", "getent hosts api.anthropic.com >/dev/null "
                                  "&& echo resolved"])]


def pytest_case(fmt):
    """Only if the host has pytest: a real build must run inside."""
    p = subprocess.run([sys.executable, "-m", "pytest", "--version"],
                       capture_output=True)
    if p.returncode != 0:
        return []
    return [dict(name="fp-pytest-runs-inside", want="ok", out="1 passed",
                 cmd=["sh", "-c", "cd {repo} && python3 -m pytest -q".format(**fmt)])]


# --- the runner -----------------------------------------------------------

def run_case(case, fmt, n):
    sid = "ctl%02d-%s" % (n, re.sub(r"[^A-Za-z0-9]+", "-", case["name"])[:28])
    opened = subprocess.run(
        [sys.executable, SANDBOX, "open", "--repo", fmt["repo"], "--id", sid],
        capture_output=True, text=True)
    if opened.returncode != 0:
        return None, f"could not open a sandbox: {opened.stdout}{opened.stderr}"
    path = opened.stdout.strip().split(" at ")[-1]
    argv = [sys.executable, SANDBOX, "run", sid]
    if case.get("timeout"):
        argv += ["--timeout", str(case["timeout"])]
    argv += ["--"] + case["cmd"]
    proc = subprocess.run(argv, capture_output=True, text=True,
                          env={**os.environ, **case.get("env", {})})
    ctx = {"path": path, "stdout": proc.stdout, "stderr": proc.stderr,
           "rc": proc.returncode, "fmt": fmt}
    return ctx, None


def tail(stream, n=200):
    """The END of a stream, not its beginning.

    `sandbox.py run` writes two progress lines to stderr before anything can
    go wrong, so the head of stderr is always harness chatter and the reason,
    when there is one, is last. Reporting the head made a failing case say
    `command written to meta/cmd.sh (3 argv elements)` where the cause was a
    DNS miss -- an instrument answering a question adjacent to the one asked,
    in the suite that exists to catch exactly that."""
    text = stream.strip()
    return text if len(text) <= n else "..." + text[-n:]


def verdict(case, ctx):
    """The reason this case failed, or None."""
    want, rc = case["want"], ctx["rc"]
    if want == "ok" and rc != 0:
        return f"expected to be ALLOWED, exited {rc}: {tail(ctx['stderr'])}"
    if want in ("fail", "fail_is_ok"):
        if want == "fail" and rc == 0:
            return "expected to be BLOCKED and the command SUCCEEDED"
        # S-4: structure, not DAC. ENOENT and EROFS are the sandbox not being
        # there; EACCES would mean we had built permissions instead.
        if "Permission denied" in ctx["stderr"]:
            return ("refused with `Permission denied` -- that is DAC, not "
                    "structure (spec S-4)")
    if isinstance(want, int) and rc != want:
        return f"exited {rc}, expected {want}: {tail(ctx['stderr'])}"
    if case.get("out") and case["out"] not in ctx["stdout"]:
        return f"stdout does not contain {case['out']!r}: {ctx['stdout'].strip()[:200]!r}"
    if case.get("err") and case["err"] not in ctx["stderr"]:
        return f"stderr does not contain {case['err']!r}: {tail(ctx['stderr'])!r}"
    checks = case.get("check") or []
    for check in (checks if isinstance(checks, list) else [checks]):
        why = check(ctx)
        if why:
            return why
    return None


# --- the promotion section (roadmap 0.2.2 §3.3) ----------------------------
#
# A SEPARATE fixture and a separate loop, and the reason is structural rather
# than tidiness: every case above asserts that the host repository is BYTE
# IDENTICAL afterwards, which is the property that makes them meaningful. A
# promotion case exists to change the host, so it cannot share that harness
# without weakening it. Each case gets a repository of its own, built fresh, so
# no case can be satisfied by state a previous one left; and each keeps a
# sibling repository beside it that must be untouched at the end, because a
# promotion that lands correctly and also perturbs something else would
# otherwise pass.

PROMO_TASKS = {
    "T-1": ("first", ["src/"]),
    "T-2": ("second", ["neighbour/"]),
    "T-3": ("no scope at all", []),
}


def build_promo_fixture(root, n):
    repo = os.path.join(root, "promo%02d" % n)
    sibling = os.path.join(root, "promo%02d-sibling" % n)
    for path in (repo, sibling):
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        os.makedirs(os.path.join(path, "neighbour"), exist_ok=True)
        os.makedirs(os.path.join(path, "devteam", "tasks"), exist_ok=True)
        for cmd in (["init", "-q", "."], ["config", "user.name", "Fixture"],
                    ["config", "user.email", "fixture@devteam.invalid"]):
            subprocess.run(["git", "-C", path, *cmd], check=True, capture_output=True)
        for task, (title, scope) in PROMO_TASKS.items():
            body = "# %s — %s — RUNNING\n\n" % (task, title)
            if scope:
                body += "- **Scope.**\n" + "".join("  - %s\n" % s for s in scope)
            else:
                body += "- **Goal.** a task that declares no scope.\n"
            body += "\n## Execution record\n"
            with open(os.path.join(path, "devteam", "tasks", "%s.md" % task), "w") as fh:
                fh.write(body)
        with open(os.path.join(path, "src", "a.py"), "w") as fh:
            fh.write("v1\n")
        with open(os.path.join(path, "neighbour", "other.txt"), "w") as fh:
            fh.write("theirs\n")
        # What `/devteam:setup` writes, and what this fixture did NOT have
        # until 0.2.4. Without it `dispatch`'s own liveness file lands in the
        # worker's uncommitted remainder and `promote` refuses the promotion
        # for it -- MEASURED 0.2.3, on the first live promotion this pipeline
        # ever attempted. `dispatch` now refuses up front instead, which is
        # what `dispatch-refuses-a-repo-that-does-not-ignore-the-run-directory`
        # below controls; a fixture without the line cannot reach any of the
        # other dispatch cases.
        with open(os.path.join(path, ".gitignore"), "w") as fh:
            fh.write("devteam/.run/\n")
        subprocess.run(["git", "-C", path, "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", path, "commit", "-qm", "base"], check=True,
                       capture_output=True)
    return repo, sibling


def sbx(*args):
    return subprocess.run([sys.executable, SANDBOX, *args], capture_output=True, text=True)


def tamper_base(meta):
    with open(os.path.join(meta, "base.sha"), "w") as fh:
        fh.write("0" * 40 + "\n")


def plant_extract_failed(meta):
    open(os.path.join(meta, "extract-failed"), "w").close()


def undetermined_ancestry(meta):
    """`merge-base --is-ancestor` exits 128 on a base the repository does not
    have -- neither 0 nor 1. A gate written as `== 1` reads that as no finding
    and promotes over a history it could not determine, which is why the
    condition is `!= 0` and why this case exists beside the real amend."""
    with open(os.path.join(meta, "base-is-ancestor.txt"), "w") as fh:
        fh.write("128\n")


def unrepresentable_remainder(meta):
    """The remainder patch empty while status.txt still names the work -- what
    a file too large for `git diff --binary` leaves behind. A gate reading only
    the patch would call this a clean, complete step."""
    open(os.path.join(meta, "uncommitted.patch"), "w").close()


def stage_on_host(repo):
    with open(os.path.join(repo, "src", "staged.py"), "w") as fh:
        fh.write("staged\n")
    subprocess.run(["git", "-C", repo, "add", "src/staged.py"], capture_output=True)


def dirty_unstaged(repo):
    with open(os.path.join(repo, "neighbour", "other.txt"), "a") as fh:
        fh.write("host edit\n")


def leave_untracked(repo):
    with open(os.path.join(repo, "loose-on-host.txt"), "w") as fh:
        fh.write("untracked\n")


def untrack_task_file(repo):
    subprocess.run(["git", "-C", repo, "rm", "--cached", "-q",
                    "devteam/tasks/T-1.md"], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "untrack T-1"],
                   capture_output=True)


def remove_task_file(repo):
    subprocess.run(["git", "-C", repo, "rm", "-q", "devteam/tasks/T-1.md"],
                   capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "remove T-1"],
                   capture_output=True)


COMMIT = "git add %s && git commit -qm '%s'"


def promotion_cases():
    """(name, task, what the worker does inside, host/meta tamper, expectation).

    `want` is a finding name the gate must report, or "promoted".
    """
    return [
        # -- the gate's findings, each planted --------------------------------
        dict(name="promote-no-commits", task="T-1", inside="true",
             want="promote-no-commits"),
        dict(name="promote-history-rewrite", task="T-1",
             inside="git commit --amend -qm 'T-1: rewritten base'",
             want="promote-history-rewrite"),
        dict(name="promote-foreign-subject", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-2: not my task"),
             want="promote-foreign-subject"),
        dict(name="promote-foreign-subject-unshaped", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "wip"),
             want="promote-foreign-subject"),
        dict(name="promote-out-of-scope", task="T-1",
             inside="echo mine > neighbour/other.txt && "
                    + COMMIT % ("neighbour/other.txt", "T-1: a file the neighbour owns"),
             want="promote-out-of-scope"),
        dict(name="promote-uncommitted", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work")
                    + " && echo after > src/later.py",
             want="promote-uncommitted"),
        dict(name="promote-no-task-file", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             host=remove_task_file, want="promote-no-task-file"),
        dict(name="promote-task-file-untracked", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             host=untrack_task_file, want="promote-task-file-untracked"),
        dict(name="promote-history-rewrite-undetermined", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             meta=undetermined_ancestry, want="promote-history-rewrite"),
        dict(name="promote-uncommitted-that-no-patch-can-represent", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work")
                    + " && echo after > src/later.py",
             meta=unrepresentable_remainder, want="promote-uncommitted"),
        dict(name="promote-no-scope", task="T-3",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-3: work"),
             want="promote-no-scope"),
        dict(name="promote-host-index-dirty", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             host=stage_on_host, want="promote-host-index-dirty"),
        dict(name="promote-base-disagreement", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             meta=tamper_base, want="promote-base-disagreement"),
        dict(name="promote-extraction-failed", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             meta=plant_extract_failed, want="promote-extraction-failed"),

        # -- and the twins that must NOT fire ---------------------------------
        dict(name="fp-promotes-work-inside-the-declared-scope", task="T-1",
             inside="echo v2 > src/a.py && echo new > src/b.py && "
                    + COMMIT % ("src/a.py src/b.py", "T-1.S-1: two files in scope"),
             want="promoted", landed=["src/b.py"]),
        dict(name="fp-a-task-owns-its-own-task-file", task="T-1",
             inside="echo v2 > src/a.py && echo note >> devteam/tasks/T-1.md && "
                    + COMMIT % ("src/a.py devteam/tasks/T-1.md", "T-1: work and record"),
             want="promoted"),
        dict(name="fp-the-supervisor-close-subject-form", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: the close"),
             want="promoted"),
        dict(name="fp-host-unstaged-edit-does-not-block", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             host=dirty_unstaged, want="promoted"),
        dict(name="fp-host-untracked-file-does-not-block", task="T-1",
             inside="echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: work"),
             host=leave_untracked, want="promoted"),
        dict(name="fp-an-empty-commit-is-still-promotable", task="T-1",
             inside="git commit -q --allow-empty -m 'T-1: nothing to see'",
             want="promoted"),
    ]


def run_promotion_case(case, root, n):
    """Always closes what it opened. An early return that skipped the close left
    a sandbox behind, and the next run found two projects holding that id and
    refused to resolve it -- so a single failure made every later run fail for
    an unrelated reason. try/finally, not a close on the happy path."""
    sid = "pro%02d" % n
    try:
        return _promotion_case(case, root, n, sid)
    finally:
        subprocess.run([sys.executable, SANDBOX, "close", sid],
                       capture_output=True)


def _promotion_case(case, root, n, sid):
    repo, sibling = build_promo_fixture(root, n)
    sib_before = tree_hash(sibling)
    opened = sbx("open", "--repo", repo, "--task", case["task"], "--id", sid)
    if opened.returncode != 0:
        return "could not open: %s%s" % (opened.stdout, opened.stderr)
    path = opened.stdout.strip().split(" at ")[-1]
    meta = os.path.join(path, "meta")
    ran = sbx("run", sid, "--repo", repo, "--", "sh", "-c", "cd %s && %s" % (repo, case["inside"]))
    if ran.returncode not in (0, 1):
        return "the worker exited %d: %s" % (ran.returncode, ran.stderr.strip()[:200])
    if case.get("meta"):
        case["meta"](meta)
    if case.get("host"):
        case["host"](repo)

    head_before = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                                 capture_output=True, text=True).stdout.strip()
    dry = sbx("promote", sid, "--repo", repo, "--dry-run")
    got = sbx("promote", sid, "--repo", repo)
    out = got.stdout + got.stderr
    want = case["want"]

    if want == "promoted":
        if got.returncode != 0:
            return "expected a promotion, got exit %d: %s" % (got.returncode,
                                                              out.strip()[:300])
        if "promote" not in dry.stdout or dry.returncode != 0:
            return "the dry run disagreed with the apply: %s" % dry.stdout.strip()[:200]
        after = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
        if after == head_before:
            return "promote reported success and the host HEAD did not move"
        if not os.path.exists(os.path.join(meta, "promoted.json")):
            return "no promoted.json was written"
        for rel in case.get("landed", []):
            if not os.path.exists(os.path.join(repo, rel)):
                return "%s was promoted but is not on the host" % rel
        refs = subprocess.run(["git", "-C", repo, "for-each-ref", "refs/devteam/"],
                              capture_output=True, text=True).stdout.strip()
        if refs:
            return "the sandbox ref was left behind: %s" % refs
    else:
        if got.returncode == 0:
            return "expected %s and the promotion SUCCEEDED" % want
        if want not in out:
            return "expected %s, got: %s" % (want, out.strip()[:300])
        # A refusal must be total. The gate reports before it takes the lock,
        # so nothing may have moved -- this is the assertion that would catch a
        # gate which reports a finding and applies anyway.
        after = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
        if after != head_before:
            return "%s was reported and the host HEAD moved anyway" % want
        if want not in (dry.stdout + dry.stderr):
            return "the dry run did not report %s: %s" % (want, dry.stdout.strip()[:200])
    if tree_hash(sibling) != sib_before:
        return "the sibling repository changed during this case"
    return None


def promotion_extras(root, n):
    """The two cases that need more than one sandbox, reported as named cases."""
    out = []

    # width two: disjoint scopes, same base, both land, and the SECOND pair's
    # hashes are rewritten because the host HEAD moved underneath it. That
    # rewrite is the whole reason promotion is a cherry-pick rather than a
    # fetch and fast-forward (L-5), and a single-sandbox case cannot show it:
    # with the base still equal to HEAD, cherry-pick reproduces the same hashes
    # and the case passes without exercising the mechanism.
    repo, sibling = build_promo_fixture(root, n)
    sib_before = tree_hash(sibling)
    err = None
    ids = []
    for task, body in (("T-1", "echo v2 > src/a.py && " + COMMIT % ("src/a.py", "T-1: edit a")),
                       ("T-2", "echo mine > neighbour/other.txt && "
                               + COMMIT % ("neighbour/other.txt", "T-2: edit other"))):
        sid = "w%s%02d" % (task[-1], n)
        ids.append(sid)
        sbx("open", "--repo", repo, "--task", task, "--id", sid)
        sbx("run", sid, "--repo", repo, "--", "sh", "-c", "cd %s && %s" % (repo, body))
    sha = {}
    for sid in ids:
        p = sbx("promote", sid, "--repo", repo)
        if p.returncode != 0:
            err = "width-two: %s refused: %s" % (sid, (p.stdout + p.stderr).strip()[:200])
            break
        for line in p.stdout.split("\n"):
            if line.startswith("promoted "):
                bits = line.split()
                sha.setdefault(sid, []).append((bits[1], bits[3]))
    if not err:
        log = subprocess.run(["git", "-C", repo, "log", "--first-parent",
                              "--format=%s"], capture_output=True, text=True).stdout
        subjects = [l for l in log.split("\n") if l.strip()]
        if len(subjects) != 3:
            err = "width-two: expected 3 commits on --first-parent, got %d" % len(subjects)
        elif not any(o != nw for o, nw in sha.get(ids[1], [])):
            err = ("width-two: the second sandbox's hashes were NOT rewritten, so "
                   "this case did not exercise cherry-pick at all")
        elif tree_hash(sibling) != sib_before:
            err = "width-two: the sibling repository changed"
    out.append(("fp-width-two-both-land-and-the-second-is-rewritten", err))
    for sid in ids:
        sbx("close", sid, "--repo", repo)

    # a genuine conflict, which is a RUNTIME outcome and not a gate finding:
    # the gate is pre-flight and a conflict is only discoverable by applying.
    # P-12 forbids the overlapping scopes that produce one, so this case is the
    # proof that the apply catches it anyway.
    repo, sibling = build_promo_fixture(root, n + 1)
    sib_before = tree_hash(sibling)
    err = None
    for sid, text in (("cfa%02d" % n, "left"), ("cfb%02d" % n, "right")):
        sbx("open", "--repo", repo, "--task", "T-1", "--id", sid)
        sbx("run", sid, "--repo", repo, "--", "sh", "-c",
            "cd %s && echo %s > src/a.py && %s"
            % (repo, text, COMMIT % ("src/a.py", "T-1: %s" % text)))
    first = sbx("promote", "cfa%02d" % n, "--repo", repo)
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    second = sbx("promote", "cfb%02d" % n, "--repo", repo)
    out2 = second.stdout + second.stderr
    if first.returncode != 0:
        err = "conflict: the first promotion was refused: %s" % (first.stdout.strip()[:200])
    elif second.returncode == 0:
        err = "conflict: the second promotion SUCCEEDED where it should have conflicted"
    elif "promote-conflict" not in out2:
        err = "conflict: expected promote-conflict, got %s" % out2.strip()[:250]
    else:
        now = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        if now != head:
            err = "conflict: the host HEAD moved despite the conflict"
        elif not subprocess.run(["git", "-C", repo, "for-each-ref", "refs/devteam/"],
                                capture_output=True, text=True).stdout.strip():
            err = ("conflict: the ref was not left behind for inspection, so the "
                   "work is unreachable")
        elif os.path.exists(os.path.join(repo, ".git", "CHERRY_PICK_HEAD")):
            err = "conflict: the cherry-pick was not aborted; the repo is mid-pick"
        elif tree_hash(sibling) != sib_before:
            err = "conflict: the sibling repository changed"
    out.append(("promote-conflict-is-caught-by-the-apply", err))
    for sid in ("cfa%02d" % n, "cfb%02d" % n):
        sbx("close", sid, "--repo", repo)
    return out


# --- 0.2.3: the allowlist, the dispatch, and the liveness file -------------

# The GOLDEN. It is written out here rather than derived, because a golden
# computed the same way as the thing it checks agrees with any bug they share
# (P-4: a check is a diff of two lists that were arrived at differently).
ALLOWLIST_GOLDEN = {
    "implementer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "tester":      ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "documenter":  ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
}
OUTWARD_GOLDEN = ["Bash(git push:*)", "Bash(gh:*)", "Bash(pip install:*)",
                  "Bash(uv add:*)", "Bash(sudo:*)"]

FAKE_CLAUDE = """#!/bin/sh
# A worker whose output this control controls. `dispatch` resolves `claude`
# through PATH at open time and binds what it resolves to, so putting this
# first on PATH exercises the REAL dispatch path with a known result --
# without a model, a token, or a penny.
cat <<'JSON'
%s
JSON
exit %s
"""


def with_fake_claude(root, n, payload, exit_code=0):
    d = os.path.join(root, "fakebin%02d" % n)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "claude")
    with open(path, "w") as fh:
        fh.write(FAKE_CLAUDE % (payload, exit_code))
    os.chmod(path, 0o755)
    return d


def dispatch_extras(root, n):
    """0.2.3's cases: the generated allowlist, the dispatch's reading of a
    result, and the liveness file."""
    out = []
    sys.path.insert(0, HERE)
    import importlib
    sandbox = importlib.import_module("sandbox")

    # -- the allowlist is the agent file, and nothing else ------------------
    for role, golden in ALLOWLIST_GOLDEN.items():
        allowed, disallowed = sandbox.allowlist(role)
        err = None
        if allowed != golden:
            err = "allowlist %s: got %r, golden %r" % (role, allowed, golden)
        elif disallowed != OUTWARD_GOLDEN:
            err = "allowlist %s: disallowed %r, golden %r" % (role, disallowed, OUTWARD_GOLDEN)
        out.append(("allowlist-%s-is-its-agent-file" % role, err))

    # The two-declared-lists test. A golden alone cannot tell a list DERIVED
    # from the agent file from one hardcoded to the same value, and a hardcoded
    # one is a second home that stops tracking the agent file the day somebody
    # edits it. So: change the agent file, demand the output change.
    tmp_plugin = os.path.join(root, "plugin%02d" % n)
    os.makedirs(os.path.join(tmp_plugin, "agents"), exist_ok=True)
    with open(os.path.join(tmp_plugin, "agents", "implementer.md"), "w") as fh:
        fh.write("---\nname: implementer\ntools: Read, Bash\n---\nbody\n")
    real, sandbox.PLUGIN = sandbox.PLUGIN, tmp_plugin
    try:
        got, _ = sandbox.allowlist("implementer")
        out.append(("allowlist-follows-the-agent-file",
                    None if got == ["Read", "Bash"] else
                    "editing the agent file did not change the allowlist: %r" % (got,)))
        try:
            sandbox.allowlist("nosuchrole")
            err = "an undefined role produced an allowlist instead of refusing"
        except SystemExit:
            err = None
        out.append(("allowlist-undefined-role-refuses", err))
    finally:
        sandbox.PLUGIN = real

    # A false-positive twin for L-7: everything filesystem-shaped stays
    # allowed. Four findings (F-30, F-64, F-76, F-100) were a command withheld
    # for the guard's sake costing a verification chain, and this is the case
    # that fails if somebody "tightens" the inside grant back up.
    _a, d = sandbox.allowlist("implementer")
    leaked = [x for x in d if any(k in x for k in ("rm", "chmod", "python3",
                                                  "truncate", "mv", "git commit"))]
    out.append(("fp-allowlist-withholds-nothing-filesystem-shaped",
                None if not leaked else "withheld inside the sandbox: %r" % leaked))

    # -- dispatch --------------------------------------------------------
    repo, _sib = build_promo_fixture(root, 800 + n)
    dfile = os.path.join(root, "d%02d.txt" % n)
    with open(dfile, "w") as fh:
        fh.write("GOAL: do nothing\n")

    # Opened without --parent-session: REFUSED before a penny is spent. The
    # worker would otherwise run, cost money, and fail on its REPORT append
    # for a reason its dispatch never mentions.
    sbx("open", "--repo", repo, "--task", "T-1", "--step", "S-1", "--id", "nop%02d" % n)
    r = sbx("dispatch", "nop%02d" % n, "--repo", repo, "--role", "implementer",
            "--model", "m", "--dispatch", dfile)
    out.append(("dispatch-refuses-a-sandbox-with-no-parent-session",
                None if r.returncode != 0 and "parent-session" in (r.stdout + r.stderr)
                else "expected a refusal naming --parent-session, got: %s"
                     % (r.stdout + r.stderr)[:200]))
    sbx("close", "nop%02d" % n, "--repo", repo)

    # The `.gitignore` entry `dispatch` DEPENDS ON, made mechanical (0.2.4).
    # Until this refusal existed it was a written rule holding up a mechanism:
    # the harness writes its own liveness file into `devteam/.run/locks/`
    # host-side, the merged view sees it as untracked, and `promote` then
    # refuses the whole promotion as `promote-uncommitted` -- blaming the
    # worker for a file the harness put there. MEASURED 0.2.3.
    #
    # The FALSE-POSITIVE TWIN is the load-bearing half and it is not written
    # here: it is every other dispatch case in this function, all of which run
    # against a fixture that DOES carry the line. A refusal that fired
    # unconditionally would take them all down with it -- which is exactly what
    # happened when this check was first added to a fixture that lacked it.
    gi = os.path.join(repo, ".gitignore")
    keep_gi = _slurp_file(gi)
    try:
        with open(gi, "w") as fh:
            fh.write("# the line a hand-scaffolded project never got\n")
        subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", repo, "commit", "-qm", "drop the ignore"],
                       capture_output=True)
        sbx("open", "--repo", repo, "--task", "T-1", "--step", "S-1",
            "--id", "gid%02d" % n, "--parent-session", "writer-1")
        r = sbx("dispatch", "gid%02d" % n, "--repo", repo, "--role", "implementer",
                "--model", "m", "--dispatch", dfile)
        blob = r.stdout + r.stderr
        out.append(("dispatch-refuses-a-repo-that-does-not-ignore-the-run-directory",
                    None if r.returncode != 0 and "not git-ignored" in blob
                    else "expected a refusal naming the ignore rule, got: %s"
                         % blob[:200]))
        # And it must name the CONSEQUENCE, not just the condition. A refusal
        # that says "not ignored" and stops sends a reader to a .gitignore with
        # no idea why it matters; the whole point is that the failure it
        # prevents surfaces later, elsewhere, under another name.
        out.append(("dispatch-ignore-refusal-names-the-promotion-it-prevents",
                    None if "promote-uncommitted" in blob
                    else "the refusal never mentions promote-uncommitted: %s"
                         % blob[:200]))
        sbx("close", "gid%02d" % n, "--repo", repo)
    finally:
        with open(gi, "w") as fh:
            fh.write(keep_gi)
        subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", repo, "commit", "-qm", "restore the ignore"],
                       capture_output=True)

    # THE 0.2.0 FINDING, PLANTED. A failed run reported `subtype: "success"`
    # in the same object as `is_error: true`. A dispatch that read subtype
    # would hand a supervisor an unauthenticated worker's empty output as a
    # completed step. This case fails if the branch is ever moved to subtype.
    cases = [
        ("dispatch-reads-is_error-not-subtype",
         '{"is_error":true,"subtype":"success","result":"Not logged in",'
         '"usage":{"input_tokens":1},"duration_ms":60000}', 0, True),
        ("fp-dispatch-accepts-a-run-that-really-succeeded",
         '{"is_error":false,"subtype":"success","result":"REPORT",'
         '"usage":{"input_tokens":10,"output_tokens":5},"duration_ms":120000,'
         '"total_cost_usd":0.5}', 0, False),
        ("dispatch-stdout-that-is-not-json-is-a-failure",
         'this is not json', 0, True),
    ]
    for name, payload, code, want_fail in cases:
        bindir = with_fake_claude(root, n, payload, code)
        sid = "dsp%02d%s" % (n, name[:3])
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"])
        subprocess.run([sys.executable, SANDBOX, "open", "--repo", repo,
                        "--task", "T-1", "--step", "S-1", "--id", sid,
                        "--parent-session", "writer-1"],
                       capture_output=True, text=True, env=env)
        r = subprocess.run([sys.executable, SANDBOX, "dispatch", sid, "--repo", repo,
                            "--role", "implementer", "--model", "m",
                            "--dispatch", dfile, "--timeout", "60"],
                           capture_output=True, text=True, env=env)
        meta = os.path.join(sandbox.sandbox_dir(repo, sid), "meta")
        failed = (r.returncode != 0
                  or os.path.exists(os.path.join(meta, sandbox.DISPATCH_FAILED)))
        err = None
        if failed != want_fail:
            err = ("reported %s, expected %s -- %s"
                   % ("failure" if failed else "success",
                      "failure" if want_fail else "success",
                      (r.stdout + r.stderr).strip()[:200]))
        elif not want_fail:
            # The harness's own numbers, not the worker's. P-17c: a live worker
            # reported tokens=3000 for a step metered at 309639.
            try:
                b = json.load(open(os.path.join(meta, "budget.json")))
            except Exception as e:
                b, err = {}, "budget.json unreadable: %s" % e
            if not err and b.get("tokens") != 15:
                err = "budget.json tokens=%r, expected the harness's 15" % (b.get("tokens"),)
            if not err and b.get("minutes") != 2.0:
                err = "budget.json minutes=%r, expected 2.0" % (b.get("minutes"),)
            line = _slurp_file(os.path.join(repo, "devteam", ".run", "locks", "T-1.sandbox"))
            if not err and "exited" not in line:
                err = "the liveness file was not rewritten at exit: %r" % line[:120]
            if not err and " root " not in line:
                err = "the liveness file carries no root, so check_report cannot find the budget"
        out.append((name, err))
        sbx("close", sid, "--repo", repo)

    # -- `status` with no id LISTS, because two skills said it did ---------
    # `supervise`'s close checklist and `resume` §3 both send a reader to
    # `sandbox.py status` for "what is still open". It required an id and
    # refused. MEASURED 0.2.4, on the first real end-to-end: the supervisor
    # could not enumerate its own sandboxes and closed none of them, leaving
    # two overlays holding unpromoted work.
    #
    # The alternative was to tell readers to glob DEVTEAM_SANDBOX_ROOT, which
    # is a machine-local environment variable -- a second home for a path, and
    # exactly what the `.sandbox` line's `root` field exists to avoid.
    sbx("open", "--repo", repo, "--task", "T-1", "--step", "S-9",
        "--id", "lst%02d" % n, "--parent-session", "writer-1")
    r = sbx("status", "--repo", repo)
    out.append(("status-with-no-id-lists-open-sandboxes",
                None if r.returncode == 0 and ("lst%02d" % n) in r.stdout
                else "expected a listing naming lst%02d, got exit %s: %s"
                     % (n, r.returncode, (r.stdout + r.stderr)[:200])))
    # It must say whether an overlay HOLDS anything. An empty sandbox and one
    # with unpromoted work are the same line otherwise, and the second is the
    # only thing recovery can still lose.
    subprocess.run([sys.executable, SANDBOX, "exec", "--repo", repo, "--",
                    "sh", "-c", "echo x > held.txt"], capture_output=True)
    r2 = sbx("status", "--repo", repo)
    out.append(("status-listing-says-whether-an-overlay-holds-work",
                None if "empty" in r2.stdout or "work in upper/" in r2.stdout
                else "the listing does not distinguish a held overlay: %s"
                     % r2.stdout[:200]))
    # fp: an id still gives the DETAIL view, not the listing. Without this the
    # listing could have replaced the single-sandbox form entirely.
    r3 = sbx("status", "lst%02d" % n, "--repo", repo)
    out.append(("fp-status-with-an-id-still-gives-the-detail-view",
                None if r3.returncode == 0 and "opened" in r3.stdout
                else "an id did not produce the detail view: %s"
                     % (r3.stdout + r3.stderr)[:200]))
    sbx("close", "lst%02d" % n, "--repo", repo)

    # -- declared_scope must not call a TRACKED file untracked --------------
    tf = os.path.join(repo, "devteam", "tasks", "T-1.md")
    keep = open(tf).read()
    with open(tf, "w") as fh:
        fh.write("# T-1 - no status segment, so the parser drops it\n\nScope. src/\n")
    subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "unparseable"], capture_output=True)
    state, _ = sandbox.declared_scope(repo, "T-1")
    out.append(("declared-scope-tracked-but-unparsed-is-not-untracked",
                None if state == "unparsed" else
                "a tracked-but-unparseable task file reported %r, which sends the "
                "reader to `git add` a file git already has" % state))
    with open(tf, "w") as fh:
        fh.write(keep)
    subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "restore"], capture_output=True)
    state, entries = sandbox.declared_scope(repo, "T-1")
    out.append(("fp-declared-scope-reads-a-good-task-file",
                None if state == "ok" and entries else
                "a well-formed tracked task file reported %r/%r" % (state, entries)))
    os.remove(tf)
    subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "gone"], capture_output=True)
    state, _ = sandbox.declared_scope(repo, "T-1")
    out.append(("declared-scope-a-missing-file-is-still-no-task-file",
                None if state == "no-task-file" else "got %r" % state))

    # -- §3.7: a verifier's mutation goes through `exec` --------------------
    # F-100 was a verifier that could not mutate anything because the guard
    # refused in-tree writes by a role holding no claim. Inside `exec` the
    # whole tree is mutable and nothing survives, which is what makes a
    # mutation test possible at all.
    ex = os.path.join(root, "exec%02d" % n)
    os.makedirs(ex, exist_ok=True)
    subprocess.run(["git", "-C", ex, "init", "-q", "."], capture_output=True)
    with open(os.path.join(ex, "m.py"), "w") as fh:
        fh.write("def f():\n    return 1\n")
    with open(os.path.join(ex, "t.py"), "w") as fh:
        fh.write("import m\nassert m.f() == 1\nprint('green')\n")
    r = sbx("exec", "--repo", ex, "--id", "mut%02d" % n, "--timeout", "120", "--",
            "sh", "-c", "cd " + ex + " && sed -i s/return.1/return 2/ m.py && python3 t.py")
    after = open(os.path.join(ex, "m.py")).read()
    err = None
    if r.returncode == 0:
        err = "the mutated test PASSED, so the control cannot fail"
    elif "return 1" not in after:
        err = "the mutation escaped the sandbox and changed the host file"
    out.append(("exec-mutates-and-the-check-fails-and-nothing-survives", err))
    return out


def _slurp_file(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""


def selftest():
    """`tail()` is reporting machinery inside the suite that gates a release,
    and it was wrong for the whole life of the file. P-35 applies to it too:
    plant a stream whose reason is last and demand the reason back."""
    chatter = "run x: command written to meta/cmd.sh (3 argv elements)\n"
    stream = chatter * 12 + "sandbox: THE ACTUAL REASON\n"
    got = tail(stream)
    assert "THE ACTUAL REASON" in got, f"tail() lost the reason: {got!r}"
    assert got.startswith("..."), f"tail() did not mark the truncation: {got!r}"
    assert tail("short") == "short", "tail() mangled a stream under the limit"

    # `main_model` picks the model that did the WORK, not the first dict key.
    # The numbers are the ones actually measured in 0.2.8's walk, so this case
    # fails if anyone reverts to `next(iter(modelUsage))`.
    import sandbox
    result = {"modelUsage": {
        "claude-haiku-4-5-20251001": {"inputTokens": 1604, "outputTokens": 15,
                                      "cacheReadInputTokens": 0,
                                      "cacheCreationInputTokens": 32000},
        "claude-sonnet-5": {"inputTokens": 2100, "outputTokens": 8000,
                            "cacheReadInputTokens": 1050000,
                            "cacheCreationInputTokens": 6226}}}
    got = sandbox.main_model(result, "fallback")
    assert got == "claude-sonnet-5", f"main_model picked {got!r}"
    assert sandbox.main_model({}, "fallback") == "fallback", \
        "main_model must fall back to the dispatched model when usage is absent"


def main():
    selftest()
    sys.path.insert(0, HERE)
    import io
    import contextlib
    import sandbox_probe
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = sandbox_probe.main()
    if rc != 0:
        tail = [l for l in buf.getvalue().strip().split("\n") if l.strip()]
        print(f"sandbox control: SKIPPED -- sandbox_probe.py exits {rc} here "
              f"({tail[-1] if tail else 'no detail'})")
        return 2

    root = tempfile.mkdtemp(prefix="devteam-sandbox-control-")
    # The suite's sandboxes go UNDER its own temp root, so cleaning the root
    # cleans them. Without this they land in `sandbox_base()` -- /tmp -- which
    # the `finally` below does not touch, and every case that fails leaves one
    # behind: a mutation run here left seven. A leaked sandbox with a colliding
    # id makes the NEXT run fail with `is ambiguous -- 2 projects have one`,
    # for a reason that has nothing to do with what is being tested. Closing
    # each sandbox in a `finally` is what a case can do; putting them somewhere
    # that is deleted wholesale is what the suite can do, and only the second
    # survives a case that dies in a way nobody anticipated.
    os.environ["DEVTEAM_SANDBOX_ROOT"] = root
    try:
        repo, sibling = build_fixture(root)
        fmt = {"repo": repo, "sibling": sibling, "home": HOME, "plugin": PLUGIN}
        before = {"repo": tree_hash(repo), "sibling": tree_hash(sibling)}
        all_cases = cases(fmt) + pytest_case(fmt) + dns_case(fmt)
        passed = failed = 0
        for n, case in enumerate(all_cases):
            ctx, err = run_case(case, fmt, n)
            why = err or verdict(case, ctx)
            if not why:
                # Blocked or allowed, the host must be untouched. Checked after
                # EVERY case, because the interesting failure is a case that
                # passes its own assertion and changes the tree anyway.
                for name, path in (("repo", repo), ("sibling", sibling)):
                    if tree_hash(path) != before[name]:
                        why = f"the host {name} changed on disk during this case"
                        break
            if why:
                failed += 1
                print(f"FAIL  {case['name']}: {why}")
            else:
                passed += 1
            if ctx:
                subprocess.run([sys.executable, SANDBOX, "close",
                                os.path.basename(ctx["path"])], capture_output=True)
        # -- the promotion section (§3.3), its own fixtures and its own
        # loop, because these cases exist to CHANGE the host and the loop above
        # asserts the host did not change.
        promo = promotion_cases()
        for n, case in enumerate(promo):
            why = run_promotion_case(case, root, n)
            if why:
                failed += 1
                print(f"FAIL  {case['name']}: {why}")
            else:
                passed += 1
        extra = promotion_extras(root, 900) + dispatch_extras(root, 901)
        for name, why in extra:
            if why:
                failed += 1
                print(f"FAIL  {name}: {why}")
            else:
                passed += 1

        names = ([c["name"] for c in all_cases] + [c["name"] for c in promo]
                 + [n for n, _ in extra])
        total = len(names)
        fp = sum(1 for n in names if n.startswith("fp-"))
        state = "green" if not failed else f"{failed} FAILED"
        print(f"\nsandbox: {total} cases, {fp} false-positive controls "
              f"({100 * fp // total}%), {state}")
        return 1 if failed else 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
