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
  - HEAD cycle T-1: the config loader
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
        "  - HEAD cycle T-1: the config loader",
        "  - deadbee cycle T-1: the config loader")),
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
         "  - HEAD cycle T-1: the config loader",
         "  - HEAD cycle T-1: the config loader\n  - HEAD~1 cycle T-1: the probe")
        .replace("  - make test -> 12 passed, 0 failed [exit 0]",
                 "  - make test -> 12 passed, 0 failed [exit 0]\n  - make lint -> clean [exit 0]")),
     set()),
    ("fp-multiline-notes-are-continuations",
     task_file(report=REPORT.replace("notes: none",
                                     "notes: the predecessor died here;\n  its work was stashed")),
     set()),
    ("fp-earlier-report-superseded-by-a-later-one",
     task_file(report=REPORT.replace("status: DONE", "status: RED") + "\n" + REPORT), set()),
    ("fp-step-scoped-report-id",
     task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-2")),
     set()),
]


def build(root, body):
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
    run("commit", "-qm", "cycle T-1: the config loader")
    run("commit", "-q", "--allow-empty", "-m", "cycle T-1: the config loader")
    return root


def main():
    passed = failed = 0
    for name, body, expected in CASES:
        root = tempfile.mkdtemp(prefix="devteam-report-")
        try:
            build(root, body)
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"],
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
