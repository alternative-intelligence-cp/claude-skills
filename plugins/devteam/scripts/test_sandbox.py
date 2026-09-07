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
        dict(name="fp-dns-resolves", want="ok", out="resolved",
             cmd=["sh", "-c", "getent hosts api.anthropic.com >/dev/null "
                              "&& echo resolved"]),
        dict(name="fp-home-and-tmp-are-writable", want="ok", out="both",
             cmd=["sh", "-c", "touch $HOME/w && touch /tmp/w && echo both"]),
    ]


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


def verdict(case, ctx):
    """The reason this case failed, or None."""
    want, rc = case["want"], ctx["rc"]
    if want == "ok" and rc != 0:
        return f"expected to be ALLOWED, exited {rc}: {ctx['stderr'].strip()[:200]}"
    if want in ("fail", "fail_is_ok"):
        if want == "fail" and rc == 0:
            return "expected to be BLOCKED and the command SUCCEEDED"
        # S-4: structure, not DAC. ENOENT and EROFS are the sandbox not being
        # there; EACCES would mean we had built permissions instead.
        if "Permission denied" in ctx["stderr"]:
            return ("refused with `Permission denied` -- that is DAC, not "
                    "structure (spec S-4)")
    if isinstance(want, int) and rc != want:
        return f"exited {rc}, expected {want}: {ctx['stderr'].strip()[:200]}"
    if case.get("out") and case["out"] not in ctx["stdout"]:
        return f"stdout does not contain {case['out']!r}: {ctx['stdout'].strip()[:200]!r}"
    if case.get("err") and case["err"] not in ctx["stderr"]:
        return f"stderr does not contain {case['err']!r}: {ctx['stderr'].strip()[:200]!r}"
    checks = case.get("check") or []
    for check in (checks if isinstance(checks, list) else [checks]):
        why = check(ctx)
        if why:
            return why
    return None


def main():
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
    try:
        repo, sibling = build_fixture(root)
        fmt = {"repo": repo, "sibling": sibling, "home": HOME, "plugin": PLUGIN}
        before = {"repo": tree_hash(repo), "sibling": tree_hash(sibling)}
        all_cases = cases(fmt) + pytest_case(fmt)
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
        total = len(all_cases)
        fp = sum(1 for c in all_cases if c["name"].startswith("fp-"))
        state = "green" if not failed else f"{failed} FAILED"
        print(f"\nsandbox: {total} cases, {fp} false-positive controls "
              f"({100 * fp // total}%), {state}")
        return 1 if failed else 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
