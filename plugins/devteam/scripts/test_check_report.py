#!/usr/bin/env python3
"""Negative control for check_report.py (P-35)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
CHECK = os.path.join(HERE, "check_report.py")

REPORT = """REPORT implementer T-1
status: DONE
model: claude-opus-5
env: pin-2026-09-03
requirements: R-1
scope: src/
commits:
  - HEAD T-1: the config loader
checks:
  - make test -> 12 passed, 0 failed [exit 0]
questions: none
findings-for-protocol: none
budget: tokens=4210 minutes=9
notes: none
"""

TASK = """# T-1 — make it work — DONE (2026-09-03)

- **Discharges.** R-1
- **Depends on.** none
- **Scope.**
  - `src/`
- **Gate.** the test command exits zero.
- **Verify.** `make test`

## Execution record

Wrote the loader, then the tests.

```
{report}```
"""


def task_file(report=REPORT, title=None, record=True):
    body = TASK.format(report=report)
    if title is not None:
        body = re.sub(r"^# T-1 .*$", f"# T-1 — make it work — {title}", body, count=1, flags=re.M)
    if not record:
        body = body.replace("## Execution record", "## Notes")
    return body


CASES = [
    ("clean", task_file(), set()),

    # --- one fault per class ----------------------------------------------
    ("no-report", task_file(report=""), {"no-report"}),
    ("no-report-missing-heading", task_file(record=False), {"no-report"}),
    ("wrong-task", task_file(report=REPORT.replace("REPORT implementer T-1",
                                                   "REPORT implementer T-2")),
     {"wrong-task"}),
    ("missing-field", task_file(report=REPORT.replace("budget: tokens=4210 minutes=9\n", "")),
     {"missing-field"}),
    ("bad-report-status", task_file(report=REPORT.replace("status: DONE", "status: FINISHED")),
     {"bad-report-status"}),
    ("status-mismatch", task_file(title="PLANNED"), {"status-mismatch"}),
    ("unknown-commit", task_file(report=REPORT.replace(
        "  - HEAD T-1: the config loader",
        "  - deadbee T-1: the config loader")),
     {"unknown-commit"}),
    ("no-evidence", task_file(report=REPORT.replace(
        "checks:\n  - make test -> 12 passed, 0 failed [exit 0]\n", "checks: none\n")),
     {"no-evidence"}),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    ("fp-ready-to-audit-is-a-closing-status",
     task_file(report=REPORT.replace("status: DONE", "status: READY-TO-AUDIT"),
               title="READY-TO-AUDIT"), set()),
    ("fp-blocked-report-on-a-planned-task",
     task_file(report=REPORT.replace("status: DONE", "status: BLOCKED")
                             .replace("checks:\n  - make test -> 12 passed, 0 failed [exit 0]\n",
                                      "checks: none\n"),
               title="BLOCKED (waiting on a decision)"), set()),
    ("fp-needs-decision-needs-no-evidence",
     task_file(report=REPORT.replace("status: DONE", "status: NEEDS-DECISION")
                             .replace("checks:\n  - make test -> 12 passed, 0 failed [exit 0]\n",
                                      "checks: none\n"),
               title="BLOCKED (Q-3)"), set()),
    ("fp-several-checks-and-commits",
     task_file(report=REPORT.replace(
         "  - HEAD T-1: the config loader",
         "  - HEAD T-1: the config loader\n  - HEAD~1 T-1: the probe")
        .replace("  - make test -> 12 passed, 0 failed [exit 0]",
                 "  - make test -> 12 passed, 0 failed [exit 0]\n  - make lint -> clean [exit 0]")),
     set()),
    ("fp-multiline-notes-are-continuations",
     task_file(report=REPORT.replace("notes: none",
                                     "notes: the predecessor died here;\n  its work was stashed")),
     set()),
    ("fp-earlier-report-superseded-by-a-later-one",
     task_file(report=REPORT.replace("status: DONE", "status: RED") + "\n" + REPORT), set()),
    # --- regressions from the first real dispatch -------------------------
    ("fp-HEAD-names-this-commit-by-its-subject",
     task_file(report=REPORT.replace(
         "  - HEAD T-1: the config loader",
         "  - HEAD T-1: the config loader")), set()),
    ("commit-subject-that-does-not-exist",
     task_file(report=REPORT.replace(
         "  - HEAD T-1: the config loader",
         "  - HEAD T-1: a subject nobody ever committed")),
     {"unknown-commit"}),
    ("fp-commits-continuation-lines-are-not-commits",
     task_file(report=REPORT.replace(
         "  - HEAD T-1: the config loader",
         "  - HEAD T-1: the config loader\n    (rewritten after review)")),
     set()),
    ("fp-supervisor-block-is-checked-not-its-workers",
     task_file(report=REPORT + "\n--- WORKER REPORTS (verbatim, P-17) ---\n\n"
               + REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-1")
                       .replace("status: DONE", "status: RED")
                       .replace("checks:\n  - make test -> 12 passed, 0 failed [exit 0]\n",
                                "checks: none\n")),
     set()),
    # From the second real dispatch: a mid-flight task whose record holds only
    # a finished STEP block was reporting a spurious status-mismatch, because a
    # DONE step necessarily sits under a RUNNING task.
    # From the recovery dispatch: a supervisor cannot close cleanly while the
    # MANAGER has an uncommitted file, even though nothing of the task's is
    # dirty. dirty-tree now measures only the task's own scope.
    # head-subject requires the task's own commit-subject PREFIX, the same rule
    # check_scope attributes by. A subject that merely mentions the task is not
    # that task's commit.
    ("head-subject-when-no-commit-begins-with-the-task",
     task_file(report=REPORT.replace("  - HEAD T-1: the config loader",
                                     "  - HEAD chore: touch up T-1 a bit")),
     {"head-subject"}, "T-1", [], "chore: touch up T-1 a bit"),
    ("fp-dirty-file-outside-the-tasks-scope",
     task_file(), set(), "T-1", [("devteam/RECORD.md", "manager's own edit\n")]),
    ("dirty-file-inside-the-tasks-scope",
     task_file(), {"dirty-tree"}, "T-1", [("src/leftover.py", "x = 1\n")]),
    ("fp-finished-step-under-a-running-task",
     task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-1"),
               title="RUNNING (since 2026-09-03, T1-a-1200)"), set()),
    ("fp-step-checked-by-its-own-dotted-id",
     task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-1"),
               title="RUNNING (since 2026-09-03, T1-a-1200)"), set(), "T-1.S-1"),
    ("wrong-step-when-a-dotted-id-is-asked-for",
     task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-1"),
               title="RUNNING (since 2026-09-03, T1-a-1200)"), {"wrong-task"}, "T-1.S-9"),
    ("fp-step-scoped-report-id",
     task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-2")),
     set()),
]


def build(root, body, leftovers=(), subject="T-1: the config loader"):
    dt = os.path.join(root, "devteam", "tasks")
    os.makedirs(dt, exist_ok=True)
    with open(os.path.join(dt, "T-1.md"), "w", encoding="utf-8") as fh:
        fh.write(body)
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    with open(os.path.join(root, "src", "main.py"), "w") as fh:
        fh.write("x = 1\n")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, env=env)
    run("init", "-q", "-b", "main")
    run("add", "-A")
    run("commit", "-qm", subject)
    run("commit", "-q", "--allow-empty", "-m", subject)
    for rel, text in leftovers:                # uncommitted after the commit
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        run("add", "-N", rel)
    return root


def main():
    passed = failed = 0
    for case in CASES:
        name, body, expected = case[:3]
        want = case[3] if len(case) > 3 else "T-1"
        leftovers = case[4] if len(case) > 4 else []
        subject = case[5] if len(case) > 5 else "T-1: the config loader"
        root = tempfile.mkdtemp(prefix="devteam-report-")
        try:
            build(root, body, leftovers, subject)
            proc = subprocess.run([sys.executable, CHECK, root, want],
                                  capture_output=True, text=True)
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
    print(f"\ncheck_report control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
