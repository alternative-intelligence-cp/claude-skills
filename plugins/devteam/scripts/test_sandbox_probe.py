#!/usr/bin/env python3
"""Negative control for sandbox_probe.py (P-35).

Every other control in this directory builds a fixture tree and runs the real
check against it. This one cannot: the faults it has to plant are a missing
`bwrap`, a kernel with user namespaces switched off, and an overlay mount that
lies about copying on write -- none of which can be arranged on a machine that
works. So it plants them at the script's four seams (`run`, `read`, `which`,
`exists`) and demands the matching line.

**State the limit, so nobody reads more into a green line than is there.**
This control proves the verdict logic: that each fault produces its finding,
that a blocker outranks an undetermined row, and that the rows which merely
differ between distributions produce nothing. It does **not** prove that the
composition works, because every command is faked. That the composition works
was measured by hand on 2026-09-05 and again on 2026-09-07, and is recorded in
`meta/roadmap/0.2/0.2.0.md` §3.2 and §3.3 with the output. The last case here
is the join between the two: it runs the real probe against the real machine
and requires only that it survives and returns one of its three documented
exit codes -- which is all a control can honestly ask of a machine it did not
choose.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import sandbox_probe  # noqa: E402

HOST_MAP = "         0          0 4294967295"

HEALTHY = {
    "bins": {"bwrap": "/usr/bin/bwrap", "unshare": "/usr/bin/unshare",
             "claude": "/home/u/.local/bin/claude", "fuse-overlayfs": None},
    "bwrap_version": "bubblewrap 0.9.0",
    "bwrap_help": "usage: bwrap [OPTION...]\n  --ro-bind SRC DEST\n  --bind SRC DEST\n",
    "sysctl": (0, "1"),
    "apparmor": "0",
    "unshare_ok": True,
    "uid_map": HOST_MAP,
    "overlay_mounts": True,
    "lower_after": "v1",
    "upper_has_added": True,
}


def install(machine):
    """Point the script's four seams at a described machine, not at this one."""

    def run(argv, timeout=30):
        cmd = " ".join(argv)
        if argv[:2] == ["uname", "-r"]:
            return 0, "6.14.0-test", cmd
        if argv[:2] == ["bwrap", "--version"]:
            return 0, machine["bwrap_version"], cmd
        if argv[:2] == ["bwrap", "--help"]:
            return 0, machine["bwrap_help"], cmd
        if argv[:2] == ["claude", "--version"]:
            return 0, "2.1.263 (Claude Code)", cmd
        if argv[0] == "sysctl":
            rc, out = machine["sysctl"]
            return rc, out, cmd
        if argv[:2] == ["unshare", "--user"] and argv[-1] == "true":
            return (0, "", cmd) if machine["unshare_ok"] else (1, "operation not permitted", cmd)
        if argv[0] == "unshare":                      # the overlay probe
            return ((0, "", cmd) if machine["overlay_mounts"]
                    else (32, "mount: permission denied", cmd))
        if argv[0] == "df":
            return 0, "Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 10G 90G 10% /tmp", cmd
        raise AssertionError(f"the control was not asked about: {cmd}")

    def read(path):
        if path.endswith("apparmor_restrict_unprivileged_userns"):
            return machine["apparmor"]
        if path == "/proc/self/uid_map":
            return machine["uid_map"]
        if path.endswith(os.path.join("lower", "tracked")):
            return machine["lower_after"]
        raise AssertionError(f"the control was not asked to read: {path}")

    sandbox_probe.run = run
    sandbox_probe.read = read
    sandbox_probe.which = lambda n: machine["bins"].get(n)
    sandbox_probe.exists = lambda p: machine["upper_has_added"]


def machine(**overrides):
    m = {k: (dict(v) if isinstance(v, dict) else v) for k, v in HEALTHY.items()}
    m.update(overrides)
    return m


def no_bin(name):
    bins = dict(HEALTHY["bins"])
    bins[name] = None
    return machine(bins=bins)


CASES = [
    # name, machine, expected findings, expected exit
    ("clean", machine(), set(), 0),

    ("no-bwrap", no_bin("bwrap"), {"no-bwrap"}, 1),
    ("no-unshare", no_bin("unshare"), {"no-unshare"}, 1),
    ("no-cli", no_bin("claude"), {"no-cli"}, 1),
    ("userns-denied-by-sysctl", machine(sysctl=(0, "0")), {"userns-denied"}, 1),
    ("userns-denied-by-apparmor", machine(apparmor="1"), {"userns-denied"}, 1),
    ("userns-failed", machine(unshare_ok=False), {"userns-failed"}, 1),
    ("overlay-failed-mount", machine(overlay_mounts=False), {"overlay-failed"}, 1),
    # The one that matters most: a mount that wrote straight through to the
    # lower layer would satisfy "did it exit 0?" and destroy the repository it
    # was supposed to protect. The probe checks the lower layer is byte-identical,
    # and this case is what proves that check is wired up.
    ("overlay-wrote-through-to-the-lower-layer",
     machine(lower_after="v2"), {"overlay-failed"}, 1),
    ("overlay-upper-layer-empty",
     machine(upper_has_added=False), {"overlay-failed"}, 1),

    # Undetermined, not broken: exit 2, and a human reads it.
    ("already-nested",
     machine(uid_map="         0       1000          1"), {"already-nested"}, 2),
    # A kernel that will not show its own uid_map is not evidence of safety.
    ("uid-map-unreadable", machine(uid_map=None), {"already-nested"}, 2),
    ("native-overlay",
     machine(bwrap_help=HEALTHY["bwrap_help"] + "  --overlay SRC RWSRC WORKDIR DEST\n"),
     {"native-overlay"}, 2),

    # A blocker outranks an undetermined row: a nested machine with no bwrap
    # is unavailable, not merely unclear. Exit 1, and both lines are printed.
    ("blocker-outranks-undetermined",
     machine(uid_map="         0       1000          1",
             bins={**HEALTHY["bins"], "bwrap": None}),
     {"already-nested", "no-bwrap"}, 1),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    # Each of these differs from the developer's machine and none of them is
    # a fault. A probe that reports them sends its reader hunting a knob that
    # was never turned, which is how a detector loses its audience.
    ("fp-fuse-overlayfs-installed",
     machine(bins={**HEALTHY["bins"], "fuse-overlayfs": "/usr/bin/fuse-overlayfs"}), set(), 0),
    # The sysctl is Debian/Ubuntu-specific. On Fedora or Arch it is absent and
    # user namespaces are on regardless.
    ("fp-sysctl-not-present-on-this-kernel",
     machine(sysctl=(1, "sysctl: cannot stat ...: No such file or directory")), set(), 0),
    ("fp-apparmor-file-not-present", machine(apparmor=None), set(), 0),
    # `uid_map` is whitespace-formatted by the kernel and the column widths are
    # not part of the contract, so the comparison is on fields.
    ("fp-uid-map-spaced-differently", machine(uid_map="0\t0\t4294967295"), set(), 0),
    ("fp-uid-map-single-spaced", machine(uid_map="0 0 4294967295"), set(), 0),
    # A newer bwrap that merely mentions overlays in prose is not one that has
    # the flag; the row asks about the flag.
    ("fp-help-text-mentions-overlay-in-prose",
     machine(bwrap_help="usage: bwrap\n  --bind SRC DEST   (see also: overlay support)\n"),
     set(), 0),
]


def run_case(m):
    """Return (findings, exit code) from one described machine."""
    install(m)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = sandbox_probe.main()
    text = buf.getvalue()
    got = {line.split()[0] for line in text.splitlines()
           if line.split() and line.split()[0] in KINDS}
    return got, code, text


KINDS = {"no-bwrap", "no-unshare", "no-cli", "userns-denied", "userns-failed",
         "overlay-failed", "already-nested", "native-overlay"}


def main():
    saved = (sandbox_probe.run, sandbox_probe.read, sandbox_probe.which, sandbox_probe.exists)
    passed = failed = 0
    for name, m, expected, want_exit in CASES:
        got, code, text = run_case(m)
        if got == expected and code == want_exit:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}")
            print(f"        expected {sorted(expected) or 'clean'} exit {want_exit}")
            print(f"        got      {sorted(got) or 'clean'} exit {code}")
            for line in text.strip().split("\n")[-6:]:
                print(f"        | {line}")
    sandbox_probe.run, sandbox_probe.read, sandbox_probe.which, sandbox_probe.exists = saved

    # The join: the real script against the real machine. It may legitimately
    # report any of its three verdicts here -- what it may not do is crash, or
    # invent a fourth.
    proc = subprocess.run([sys.executable, os.path.join(HERE, "sandbox_probe.py")],
                          capture_output=True, text=True)
    if proc.returncode in (0, 1, 2) and "devteam sandbox probe" in proc.stdout:
        passed += 1
    else:
        failed += 1
        print("FAIL  live-machine-smoke")
        print(f"        exit {proc.returncode}")
        print(f"        | {(proc.stdout + proc.stderr).strip()[:400]}")

    # --- `--pin`, the machine-readable form the ENV pin records (0.2.4 §3.2)
    # A pin is only worth having if it records the things that MOVE, so each
    # case asks for a named row rather than for "some output": a pin that
    # silently dropped the CLI version would still look like a pin, and the
    # finding it lets expire is one nobody knows to go back for.
    pin_cases = [
        ("pin-carries-the-cli-version-that-moves", machine(),
         lambda t: "claude CLI\t2.1.263 (Claude Code)" in t),
        ("pin-carries-bwrap-and-the-userns-sysctls", machine(),
         lambda t: ("bwrap\tbubblewrap 0.9.0" in t
                    and "kernel.unprivileged_userns_clone\t1" in t
                    and "apparmor userns restriction\t0" in t)),
        ("pin-records-the-containment-a-project-would-get", machine(),
         lambda t: "containment\tstructural" in t),
        # The arm that makes the row mean something: on a machine that cannot
        # do it, the SAME pin says guard-only. Without this the row could be a
        # constant and every case above would still pass.
        ("pin-says-guard-only-where-the-probe-blocks", no_bin("bwrap"),
         lambda t: "containment\tguard-only" in t),
        # A tool being ABSENT is still a row: `bwrap absent` is a measurement
        # and belongs in the pin. Written after a first version of this case
        # asserted the opposite and failed, which is the control doing its job
        # on its own author.
        ("pin-records-an-absent-tool-as-a-row-not-a-gap", no_bin("bwrap"),
         lambda t: "bwrap\tabsent" in t),
    ]
    saved = (sandbox_probe.run, sandbox_probe.read, sandbox_probe.which, sandbox_probe.exists)
    for name, m, want in pin_cases:
        install(m)
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = sandbox_probe.main(["--pin"])
        text = buf.getvalue()
        if code == 0 and want(text):
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}: exit {code}")
            for line in text.strip().split("\n"):
                print(f"        | {line}")

    # The refusal that keeps a pin from silently shrinking. It cannot be
    # reached by any machine -- every row in `rows()` is unconditional -- so it
    # is reached by naming a row that does not exist, which is exactly the
    # state a future edit would create.
    real_rows = sandbox_probe.PIN_ROWS
    install(machine())
    try:
        sandbox_probe.PIN_ROWS = real_rows + ("a row nobody yields",)
        import io
        import contextlib
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            code = sandbox_probe.main(["--pin"])
        if code == 2 and "a row nobody yields" in err.getvalue():
            passed += 1
        else:
            failed += 1
            print(f"FAIL  pin-refuses-rather-than-emitting-a-short-pin: exit {code}")
            print(f"        | {err.getvalue().strip()[:200]}")
    finally:
        sandbox_probe.PIN_ROWS = real_rows
    pin_cases = pin_cases + [("pin-refuses-rather-than-emitting-a-short-pin",)]
    sandbox_probe.run, sandbox_probe.read, sandbox_probe.which, sandbox_probe.exists = saved

    total = len(CASES) + 1 + len(pin_cases)
    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\nsandbox_probe control: {passed} passed, {failed} failed, "
          f"{total} cases ({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
