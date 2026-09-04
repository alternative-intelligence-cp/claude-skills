#!/usr/bin/env python3
"""Negative control for check_scope.py (P-35)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
CHECK = os.path.join(HERE, "check_scope.py")


def task(ident, status, scope, title="a task"):
    body = f"# {ident} — {title} — {status}\n\n- **Discharges.** R-1\n- **Depends on.** none\n- **Scope.**\n"
    for s in scope:
        body += f"  - `{s}`\n"
    body += "- **Gate.** it works.\n- **Verify.** `true`\n\n## Execution record\n"
    return body


BASE = {
    "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", ["src/loader/", "tests/loader/"]),
    "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/render/", "tests/render/"]),
}

CASES = [
    ("clean", BASE, None, [], set()),

    # --- one fault per class ----------------------------------------------
    ("overlapping-scope",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/", "docs/"])},
     None, [], {"overlapping-scope"}),
    ("overlapping-scope-identical",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/loader/"])},
     None, [], {"overlapping-scope"}),
    ("empty-scope",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", [])},
     None, [], {"empty-scope"}),
    ("scope-escapes-tree",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["../sibling/src/"])},
     None, [], {"scope-escapes-tree"}),
    ("scope-escapes-tree-absolute",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["/etc/"])},
     None, [], {"scope-escapes-tree"}),
    ("undeclared-write",
     BASE, "T-1", [("src/loader/a.py", "x=1\n"), ("src/render/b.py", "y=2\n")],
     {"undeclared-write"}),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    # From the first real dispatch: the manager's own board and plan commits
    # mention the task in their message, and were being charged to it.
    ("fp-manager-commits-mentioning-a-task-are-not-its-writes",
     BASE, "T-1", [("src/loader/a.py", "x=1\n")], set(), "board: claim T-1"),
    ("fp-planned-tasks-may-overlap-a-running-one",
     {**BASE, "T-3": task("T-3", "PLANNED", ["src/loader/"])}, None, [], set()),
    ("fp-done-tasks-may-overlap",
     {**BASE, "T-3": task("T-3", "DONE (2026-09-03)", ["src/loader/"])}, None, [], set()),
    ("fp-planned-task-may-declare-no-scope-yet",
     {**BASE, "T-3": task("T-3", "PLANNED", [])}, None, [], set()),
    ("fp-sibling-prefixes-do-not-intersect",
     {"T-1": task("T-1", "RUNNING (since x, y)", ["src/loader/"]),
      "T-2": task("T-2", "RUNNING (since x, y)", ["src/loader_v2/"])}, None, [], set()),
    ("fp-writes-inside-scope",
     BASE, "T-1", [("src/loader/a.py", "x=1\n"), ("tests/loader/t.py", "z=3\n")], set()),
    ("fp-the-task-file-itself-is-always-writable",
     BASE, "T-1", [("src/loader/a.py", "x=1\n"),
                   ("devteam/tasks/T-1.md", BASE["T-1"] + "\nmore record\n")], set()),
    ("fp-single-file-scope-entry",
     {"T-1": task("T-1", "RUNNING (since x, y)", ["README.md"]),
      "T-2": task("T-2", "RUNNING (since x, y)", ["src/"])},
     "T-1", [("README.md", "hello\n")], set()),
    ("fp-placeholder-scope-in-a-planned-template",
     {**BASE, "T-3": task("T-3", "PLANNED", ["<area>/"])}, None, [], set()),
    ("fp-blocked-task-with-scope-is-not-live",
     {**BASE, "T-3": task("T-3", "BLOCKED (Q-2)", ["src/loader/"])}, None, [], set()),
]


def build(root, tasks, writes, subject="T-1: the work"):
    dt = os.path.join(root, "devteam", "tasks")
    os.makedirs(dt, exist_ok=True)
    for ident, body in tasks.items():
        with open(os.path.join(dt, f"{ident}.md"), "w", encoding="utf-8") as fh:
            fh.write(body)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, env=env)
    run("init", "-q", "-b", "main")
    run("add", "-A")
    run("commit", "-qm", "fixture")
    if writes:
        for rel, body in writes:
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
        run("add", "-A")
        run("commit", "-qm", subject)
    return root


def main():
    passed = failed = 0
    for case in CASES:
        name, tasks, task_id, writes, expected = case[:5]
        subject = case[5] if len(case) > 5 else "T-1: the work"
        root = tempfile.mkdtemp(prefix="devteam-scope-")
        try:
            build(root, tasks, writes, subject)
            argv = [sys.executable, CHECK, root] + ([task_id] if task_id else [])
            proc = subprocess.run(argv, capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (\S+)", proc.stdout, re.M)}
            want_exit = 1 if expected else 0
            if got == expected and proc.returncode == want_exit:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} exit {want_exit}")
                print(f"        got      {sorted(got) or 'clean'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\ncheck_scope control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
