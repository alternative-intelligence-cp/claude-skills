#!/usr/bin/env python3
"""Can this machine run a devteam worker sandbox?

The worker sandbox is a two-stage composition: `unshare` opens a user and
mount namespace, an overlay is mounted inside it with the repository as the
read-only lower layer, and `bwrap` binds the merged view and drops privilege.
Each stage has a precondition, and a precondition that is merely assumed is
the kind that fails on somebody else's machine six weeks later. So each one is
a row here, with the command that produced it printed beside it -- the same
rule the reports run under: every number from a command, with the command.

  no-bwrap             bubblewrap is not installed -- stage three is missing
  no-unshare           util-linux's `unshare` is not installed -- stage one
  no-cli               the headless `claude` CLI is not on PATH; a sandboxed
                       worker is a `claude -p` process, so this is a blocker
  userns-denied        unprivileged user namespaces are switched off, by
                       sysctl or by AppArmor. Nothing here works without them
  userns-failed        they are permitted and still would not start
  overlay-failed       overlayfs would not mount inside a user namespace, so
                       the copy-on-write layer -- the whole point -- is absent

Two rows are not blockers and are not clean either. Both mean the design
assumption behind the composition no longer holds here, and a human has to
look before anything runs:

  already-nested       this process is already inside a user namespace (the
                       harness's own Bash sandbox, or a container). Nesting is
                       a different design, not a degraded one
  native-overlay       this `bwrap` can mount the overlay itself. The two-stage
                       composition exists only because 0.9.0 cannot; with a
                       `bwrap` that can, it collapses to one stage and the
                       sandbox harness should be rewritten to use it

Exit 0 the composition runs here, 1 a blocker, 2 undetermined -- see above.

`setup` runs this to decide whether a project gets a sandboxed worker or
degrades to `guard-only`. Its four external seams -- `run`, `read`, `which`
and `exists` -- exist so its control can plant each failure without needing a
machine that has it.
"""
import os
import shutil
import subprocess
import sys
import tempfile

# --- the seam ------------------------------------------------------------
# Everything this script learns about the machine comes through one of these
# three. A control replaces them to plant a fault; nothing else in here
# touches the outside world.


def run(argv, timeout=30):
    """Run a command. Returns (returncode, combined output, the command)."""
    printable = " ".join(argv)
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip(), printable
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s", printable
    except OSError as exc:
        return 127, str(exc), printable


def read(path):
    """Read a file, or None. Used for /proc and /sys, which are not commands."""
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def which(name):
    return shutil.which(name)


def exists(path):
    return os.path.exists(path)


# --- the rows ------------------------------------------------------------

HOST_UID_MAP_FIELDS = ("0", "0", "4294967295")


def overlay_probe(root):
    """Mount an overlay inside a user namespace and write through it.

    Returns (ok, detail, command). This is the one row that cannot be
    answered by asking -- kernel config, AppArmor profile and filesystem type
    all have a say, and the only honest test is to do it. The lower layer is
    left byte-identical on success, which is checked rather than assumed:
    a mount that silently wrote through would pass a weaker test.
    """
    lower = os.path.join(root, "lower")
    for d in ("lower", "upper", "work", "merged"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    with open(os.path.join(lower, "tracked"), "w") as fh:
        fh.write("v1")
    script = (
        f"mount -t overlay overlay -o lowerdir={lower},"
        f"upperdir={root}/upper,workdir={root}/work {root}/merged && "
        f"printf v2 > {root}/merged/tracked && printf new > {root}/merged/added"
    )
    argv = ["unshare", "--user", "--map-root-user", "--mount", "sh", "-c", script]
    rc, out, cmd = run(argv)
    if rc != 0:
        return False, out.splitlines()[-1] if out else f"exit {rc}", cmd
    if read(os.path.join(lower, "tracked")) != "v1":
        return False, "the lower layer was modified -- this is not copy-on-write", cmd
    if not exists(os.path.join(root, "upper", "added")):
        return False, "the write did not land in the upper layer", cmd
    return True, "writes land in the upper layer; the lower layer is untouched", cmd


def rows():
    """Yield (name, value, command, verdict) -- verdict is a finding or None."""
    rc, out, cmd = run(["uname", "-r"])
    yield "kernel", out or "unknown", cmd, None

    path = which("bwrap")
    if not path:
        yield "bwrap", "absent", "command -v bwrap", "no-bwrap"
    else:
        _, ver, cmd = run(["bwrap", "--version"])
        yield "bwrap", f"{ver} ({path})", cmd, None
        rc, help_out, cmd = run(["bwrap", "--help"])
        native = "--overlay" in help_out
        yield ("bwrap --overlay", "supported" if native else "not supported", cmd,
               "native-overlay" if native else None)

    fo = which("fuse-overlayfs")
    yield "fuse-overlayfs", fo or "absent (not needed; the kernel's is used)", \
        "command -v fuse-overlayfs", None

    path = which("unshare")
    yield "unshare", path or "absent", "command -v unshare", None if path else "no-unshare"

    path = which("claude")
    if path:
        _, ver, cmd = run(["claude", "--version"])
        yield "claude CLI", f"{ver} ({path})", cmd, None
    else:
        yield "claude CLI", "absent", "command -v claude", "no-cli"

    # Two independent switches can forbid user namespaces, and a machine with
    # one of them set looks identical to a working one until something tries.
    rc, out, cmd = run(["sysctl", "-n", "kernel.unprivileged_userns_clone"])
    # The sysctl is Debian/Ubuntu-specific; its absence is not a fault, and
    # reporting one would send a Fedora user hunting a knob they do not have.
    if rc == 0 and out.strip() == "0":
        yield "kernel.unprivileged_userns_clone", "0 -- user namespaces are off", cmd, "userns-denied"
    elif rc == 0:
        yield "kernel.unprivileged_userns_clone", out.strip(), cmd, None
    else:
        yield "kernel.unprivileged_userns_clone", "not present on this kernel", cmd, None

    aa_path = "/proc/sys/kernel/apparmor_restrict_unprivileged_userns"
    aa = read(aa_path)
    if aa is None:
        yield "apparmor userns restriction", "not present", f"cat {aa_path}", None
    else:
        yield ("apparmor userns restriction",
               f"{aa}{' -- AppArmor forbids unprivileged userns' if aa == '1' else ''}",
               f"cat {aa_path}", "userns-denied" if aa == "1" else None)

    rc, out, cmd = run(["unshare", "--user", "--map-root-user", "true"])
    yield ("user namespace", "usable" if rc == 0 else f"failed: {out or rc}",
           cmd, None if rc == 0 else "userns-failed")

    # `uid_map` is how a process learns it is already contained. On the host
    # it is the identity map; anything else means somebody else's namespace is
    # already in the way and our mounts would compose with theirs, not replace
    # them. `enableWeakerNestedSandbox` is the harness's own name for the case.
    uid_map = read("/proc/self/uid_map")
    if uid_map is None:
        # Not knowing is the same verdict as being nested, and for the same
        # reason: somebody has to look before a worker runs. It is not the
        # same sentence, though -- a reader sent to check a map that could not
        # be read will spend the trip looking for the wrong thing.
        detail, nested = "could not be read", True
    else:
        nested = tuple(uid_map.split()) != HOST_UID_MAP_FIELDS
        detail = f"{uid_map!r}" + (" -- not the host identity map" if nested else " (host)")
    yield ("already inside a namespace", detail,
           "cat /proc/self/uid_map", "already-nested" if nested else None)

    root = os.environ.get("DEVTEAM_SANDBOX_ROOT") or tempfile.gettempdir()
    rc, out, cmd = run(["df", "-h", root])
    tail = out.splitlines()[-1].split() if out.splitlines() else []
    yield ("space under the sandbox root",
           f"{tail[3]} free on {root}" if len(tail) > 3 else out, cmd, None)

    # Last, because it is the only row that costs anything, and because a
    # machine that failed an earlier row cannot pass this one.
    tmp = tempfile.mkdtemp(prefix="devteam-probe-")
    try:
        ok, detail, cmd = overlay_probe(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    yield "overlay in a user namespace", detail, cmd, None if ok else "overlay-failed"


UNDETERMINED = {"already-nested", "native-overlay"}


# The rows a PIN needs, as opposed to the rows a human reading a diagnosis
# needs. Named rather than filtered by a predicate so that adding a row to the
# probe does not silently change what a pin records -- a pin whose contents
# drift is worse than one that is missing something, because two runs then
# compare unequal things and nothing says so.
#
# These three are here because they are OUTSIDE this repository and move on
# their own: the CLI every dispatch resolves through PATH (MEASURED: it moved
# 2.1.261 -> 2.1.263 inside two days of this cycle's planning), the bwrap that
# composes the namespace, and the kernel settings that decide whether a user
# namespace can be created. The plugin's own commit pins `sandbox.py`.
PIN_ROWS = ("claude CLI", "bwrap", "kernel",
            "kernel.unprivileged_userns_clone", "apparmor userns restriction")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--pin" in argv:
        # One `name<TAB>value` line per row, plus the verdict, so a diff of two
        # pins is readable and a missing row is visible as a missing line
        # rather than as a shifted column.
        collected = list(rows())
        for name, value, _, _ in collected:
            if name in PIN_ROWS:
                print(f"{name}\t{value}")
        blocked = [v for _, _, _, v in collected if v]
        print(f"containment\t{'guard-only' if blocked else 'structural'}")
        # A SHORT PIN IS WORSE THAN NO PIN, so this refuses rather than emits
        # one. Every row above is unconditional today -- each branch of `rows()`
        # yields its name either way, `absent` included, because an absent tool
        # is a measurement. If a later edit makes one conditional, two runs
        # would silently compare pins of different shapes and nothing would say
        # so. This is that edit's alarm, and it is here rather than in the
        # control because a control cannot fire on the machine that runs it.
        missing = sorted(set(PIN_ROWS) - {n for n, _, _, _ in collected})
        if missing:
            print(f"sandbox_probe: --pin is incomplete, no row for: "
                  f"{', '.join(missing)}. A pin missing a row it has always "
                  f"carried makes two runs incomparable without saying so; fix "
                  f"`rows()` or PIN_ROWS rather than recording this.",
                  file=sys.stderr)
            return 2
        return 0
    collected = list(rows())
    width = max(len(name) for name, _, _, _ in collected)
    print("devteam sandbox probe\n")
    findings = []
    for name, value, cmd, verdict in collected:
        mark = "!" if verdict else " "
        print(f" {mark} {name:<{width}}  {value}")
        print(f"   {'':<{width}}  \033[2m{cmd}\033[0m" if sys.stdout.isatty()
              else f"   {'':<{width}}  {cmd}")
        if verdict:
            findings.append((verdict, name, value))
    print()
    if not findings:
        print("sandbox: available -- the two-stage composition runs on this machine")
        return 0
    for verdict, name, value in findings:
        print(f"  {verdict:<16} {name}: {value}")
    print()
    if all(v in UNDETERMINED for v, _, _ in findings):
        print("sandbox: undetermined -- the composition's assumptions do not hold here; "
              "read the finding above before running a worker")
        return 2
    print("sandbox: unavailable -- setup degrades to guard-only")
    return 1


if __name__ == "__main__":
    sys.exit(main())
