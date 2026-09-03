#!/usr/bin/env python3
"""Run every negative control in this directory (P-35).

A check that has never failed has not been shown to work, so this is what
proves the checks still do. Run it after touching any check, and in CI.
Exit 0 all green, 1 any control failed.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))


def main():
    controls = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if not controls:
        print("no controls found — that is itself a finding", file=sys.stderr)
        return 1
    failed = []
    for path in controls:
        proc = subprocess.run([sys.executable, path], capture_output=True, text=True)
        tail = [l for l in proc.stdout.strip().split("\n") if l.strip()]
        print(tail[-1] if tail else f"{os.path.basename(path)}: no output")
        if proc.returncode != 0:
            failed.append(os.path.basename(path))
            for line in proc.stdout.strip().split("\n"):
                if line.startswith(("FAIL", "        ")):
                    print(f"  {line}")
            if proc.stderr.strip():
                print(f"  stderr: {proc.stderr.strip()[:500]}")
    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print(f"all {len(controls)} controls green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
