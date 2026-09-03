#!/usr/bin/env python3
"""Negative control for reinject.py (P-35).

The failure that matters is not silence — it is speaking to a session that is
not the manager. A hook that injects "you are the project manager" into an
unrelated session is worse than one that never fires, so most of these cases
check that it stays quiet.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
HOOK = os.path.join(HERE, "reinject.py")
MANAGER = "session-manager-1"


def build(marker=MANAGER, nested=False, no_devteam=False):
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-reinject-"))
    if not no_devteam:
        d = os.path.join(root, "devteam", ".run", "session")
        os.makedirs(d)
        if marker is not None:
            open(os.path.join(d, "manager"), "w").write(marker + "\n")
    sub = os.path.join(root, "src", "deep")
    os.makedirs(sub, exist_ok=True)
    return root, (sub if nested else root)


def run(cwd, session, project_dir=None):
    env = {**os.environ}
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    proc = subprocess.run([sys.executable, HOOK],
                          input=json.dumps({"session_id": session, "cwd": cwd}),
                          capture_output=True, text=True, env=env)
    return proc.stdout.strip()


CASES = [
    ("fires-for-the-manager", dict(), MANAGER, True),
    ("fires-from-a-nested-directory", dict(nested=True), MANAGER, True),
    ("silent-for-another-session", dict(), "session-other", False),
    ("silent-when-no-marker", dict(marker=None), MANAGER, False),
    ("silent-outside-a-devteam-project", dict(no_devteam=True), MANAGER, False),
    ("silent-for-empty-session-id", dict(), "", False),
]


def main():
    passed = failed = 0
    for name, kw, session, expect in CASES:
        root, cwd = build(**kw)
        try:
            out = run(cwd, session, project_dir=cwd)
            got = bool(out)
            if got == expect:
                if expect:
                    for needed in ("re-read devteam/BOARD.md", "STALE", "skills/run/SKILL.md", root):
                        if needed not in out:
                            failed += 1
                            print(f"FAIL  {name}: block missing {needed!r}")
                            break
                    else:
                        passed += 1
                else:
                    passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}: {'spoke' if got else 'silent'}, expected "
                      f"{'to speak' if expect else 'silence'}")
                if out:
                    print(f"        | {out.splitlines()[0]}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    silent = sum(1 for c in CASES if not c[3])
    print(f"\nreinject control: {passed} passed, {failed} failed, {len(CASES)} cases "
          f"({silent} of them checking it stays quiet, {100 * silent // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
