#!/usr/bin/env python3
"""Negative control for root_guard.py (P-35).

A hook is proved by a refused write, never by its control (setup/SKILL.md §3):
this shows the SCRIPT decides correctly, and says nothing about whether the
hook is registered and running. 0.2.10 §4 pastes the live refusal separately,
and the two pieces of evidence are not interchangeable.

Built in a throwaway tree, never against this repository. root_guard.judge_root
takes the repository as a parameter for exactly this reason -- a guard testable
only against the tree it guards needs a control that mutates that tree, which
is the window PAIRS row 12 removed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
REAL = (os.environ.get("DEVTEAM_SUBJECT_ROOT_GUARD")
        or os.path.join(HERE, "root_guard.py"))

README = """# fixture

## What is in this repository

| Entry | What |
|---|---|
| `README.md` | this file |
| `plugins/` | the plugins |
| `.gitignore` | what never reaches the remote |

## After

Text below the table, which the parser must stop before.
"""


def build():
    """A throwaway repository with the guard installed at its real depth.

    root_guard derives the repository from its own __file__ three levels up,
    so the copy has to sit at plugins/devteam/scripts/ for REPO to come out
    right. Faking that with an environment variable would test a path the
    hook never takes.
    """
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-rootguard-"))
    scripts = os.path.join(root, "plugins", "devteam", "scripts")
    os.makedirs(scripts)
    os.makedirs(os.path.join(root, ".internal", "scratch"))
    shutil.copy2(REAL, os.path.join(scripts, "root_guard.py"))
    # main() imports guard.py for its resolver and its command tokeniser. One
    # resolver, and this control uses the real one rather than a stub, because
    # a stub would agree with whatever this file expected.
    shutil.copy2(os.path.join(HERE, "guard.py"), os.path.join(scripts, "guard.py"))
    open(os.path.join(root, "README.md"), "w", encoding="utf-8").write(README)
    open(os.path.join(root, ".gitignore"), "w", encoding="utf-8").write("/*.py\n")
    return root, os.path.join(scripts, "root_guard.py")


# (name, tool_name, tool_input built from the root, refusal expected)
CASES = [
    ("a-stray-written-at-the-root-is-refused",
     "Write", lambda r: {"file_path": os.path.join(r, "stray.md")}, True),
    ("a-stray-redirected-at-the-root-is-refused",
     "Bash", lambda r: {"command": f"echo hi > {os.path.join(r, 'notes.txt')}"}, True),
    # THE FALSE POSITIVE THAT WOULD MATTER MOST. Editing the README is the
    # commonest write at any repository root, and a guard that refused it would
    # be switched off within the hour -- taking the stray refusal with it.
    ("fp-a-write-to-a-listed-entry-is-allowed",
     "Write", lambda r: {"file_path": os.path.join(r, "README.md")}, False),
    ("fp-a-write-below-the-root-is-not-this-guards-business",
     "Write", lambda r: {"file_path": os.path.join(r, "plugins", "devteam", "x.py")}, False),
    # Where a stray is SUPPOSED to go. If this were refused the refusal message
    # would be sending people somewhere the guard forbids, which is worse than
    # having no message at all.
    ("fp-a-write-into-internal-scratch-is-allowed",
     "Bash", lambda r: {"command": f"echo x > {os.path.join(r, '.internal/scratch/probe.py')}"}, False),
    ("fp-a-read-at-the-root-is-allowed",
     "Bash", lambda r: {"command": f"cat {os.path.join(r, 'anything.md')}"}, False),
    # THE TRAILING SLASH. A directory is written `plugins/` for a reader and
    # neither git nor a path carries one, so root_allowlist strips it. Without
    # this case the strip is exercised only through check_plugin's control --
    # the same function, proved on one of its two callers, which is how a
    # shared helper acquires a caller-specific bug nobody looks for.
    ("fp-a-write-to-a-listed-directory-entry-is-allowed",
     "Write", lambda r: {"file_path": os.path.join(r, "plugins")}, False),
    # THIS GUARD JUDGES WRITES ONLY. guard.py's targets() also yields `index`,
    # `tree` and `outward` targets -- `git add`, `git checkout -- path`,
    # `git push` -- and those are guard.py's business, not the root table's.
    # Judging them here would refuse `git checkout -- stray.md`, which creates
    # no stray at all, and the filter that prevents it was unproven until this
    # case existed.
    ("fp-a-git-tree-operation-at-the-root-is-not-a-write",
     "Bash", lambda r: {"command": f"git checkout -- {os.path.join(r, 'stray.md')}"}, False),
    # The resolver's stated limit, inherited from guard.py and restated rather
    # than quietly relied on: a target it cannot resolve is NOT JUDGED. Silent
    # inheritance is how a limit stops being read.
    ("fp-an-unexpanded-variable-is-not-judged",
     "Bash", lambda r: {"command": 'echo x > "$REPO/thing.md"'}, False),
]


def main():
    passed = failed = 0
    for name, tool, make_input, expect in CASES:
        root, script = build()
        try:
            payload = {"tool_name": tool, "cwd": root, "session_id": "control",
                       "tool_input": make_input(root)}
            proc = subprocess.run([sys.executable, script], input=json.dumps(payload),
                                  capture_output=True, text=True)
            refused = '"permissionDecision": "deny"' in proc.stdout
            if refused == expect and proc.returncode == 0:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {'REFUSED' if expect else 'allowed'}, exit 0")
                print(f"        got      {'REFUSED' if refused else 'allowed'}, "
                      f"exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n")[:4]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    fp = sum(1 for c in CASES if c[0].startswith("fp-"))
    print(f"\nroot_guard control: {passed} passed, {failed} failed, {len(CASES)} cases "
          f"({fp} of them false-positive controls, {100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
