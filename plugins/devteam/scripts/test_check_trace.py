#!/usr/bin/env python3
"""Negative control for check_trace.py (P-35).

One planted fault per finding class, and a majority of cases that look like
faults and must come back clean.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
CHECK = os.path.join(HERE, "check_trace.py")

CHARTER = """# Charter — Fixture

## Goals

- **G-1** — the thing works
- **G-2** — the thing is documented
"""

REQS = """# Requirements

### R-1 — it works

- **Statement.** the thing works when run.
- **Satisfies.** G-1
- **Source.** interview 2026-09-03
- **Acceptance.** `make test` → `ok`
- **Priority.** must
- **Status.** open

### R-2 — it is documented

- **Statement.** a README explains how to run it.
- **Satisfies.** G-2
- **Source.** interview 2026-09-03
- **Acceptance.** `test -s README.md`
- **Priority.** should
- **Status.** open
"""

T1 = """# T-1 — make it work — PLANNED

- **Discharges.** R-1
- **Depends on.** none
- **Scope.**
  - `src/`
- **Gate.** the test command exits zero.
- **Verify.** `make test`
- **Estimate.** tokens=1000 minutes=10
"""

T2 = """# T-2 — write the README — PLANNED

- **Discharges.** R-2
- **Depends on.** T-1
- **Scope.**
  - `README.md`
- **Gate.** the README exists and is non-empty.
- **Verify.** `test -s README.md`
- **Estimate.** tokens=500 minutes=5
"""

FIXTURE = {"CHARTER.md": CHARTER, "REQUIREMENTS.md": REQS,
           "tasks/T-1.md": T1, "tasks/T-2.md": T2}

CASES = [
    ("clean", {}, set()),

    # --- one fault per class ----------------------------------------------
    ("orphan-scope",
     {"CHARTER.md": CHARTER + "- **G-3** — the thing is fast\n"},
     {"orphan-scope"}),
    ("uncovered-requirement",
     {"REQUIREMENTS.md": REQS + """
### R-3 — it is fast

- **Statement.** p99 under 200ms.
- **Satisfies.** G-1
- **Source.** interview
- **Acceptance.** `bench.py`
- **Priority.** should
- **Status.** open
"""},
     {"uncovered-requirement"}),
    ("unmotivated-task",
     {"tasks/T-3.md": """# T-3 — refactor everything — PLANNED

- **Discharges.** none
- **Depends on.** none
- **Scope.**
  - `src/`
- **Gate.** it still builds.
- **Verify.** `make`
"""},
     {"unmotivated-task"}),
    ("unverified-requirement",
     {"REQUIREMENTS.md": REQS.replace("- **Acceptance.** `test -s README.md`",
                                      "- **Acceptance.** <the command>")},
     {"unverified-requirement"}),
    ("missing-field",
     {"REQUIREMENTS.md": REQS.replace("- **Priority.** should\n", "")},
     {"missing-field"}),
    ("unknown-reference-goal",
     {"REQUIREMENTS.md": REQS.replace("- **Satisfies.** G-2", "- **Satisfies.** G-9")},
     {"unknown-reference", "orphan-scope"}),
    ("unknown-reference-task-dep",
     {"tasks/T-2.md": T2.replace("- **Depends on.** T-1", "- **Depends on.** T-9")},
     {"unknown-reference"}),
    ("dependency-cycle",
     {"tasks/T-1.md": T1.replace("- **Depends on.** none", "- **Depends on.** T-2")},
     {"dependency-cycle"}),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    ("fp-struck-requirement-needs-no-task",
     {"REQUIREMENTS.md": REQS + """
### R-3 — withdrawn idea

- **Statement.** it syncs to the cloud.
- **Satisfies.** G-1
- **Source.** interview
- **Acceptance.** n/a
- **Priority.** may
- **Status.** struck (D-2)
"""},
     set()),
    ("fp-one-task-discharges-several",
     {"tasks/T-1.md": T1.replace("- **Discharges.** R-1", "- **Discharges.** R-1, R-2"),
      "tasks/T-2.md": None},
     set()),
    ("fp-one-requirement-satisfies-several-goals",
     {"REQUIREMENTS.md": REQS.replace("- **Satisfies.** G-1\n", "- **Satisfies.** G-1, G-2\n")},
     set()),
    ("fp-long-dependency-chain-is-not-a-cycle",
     {"tasks/T-3.md": """# T-3 — ship it — PLANNED

- **Discharges.** R-2
- **Depends on.** T-2
- **Scope.**
  - `dist/`
- **Gate.** the artifact exists.
- **Verify.** `test -e dist/out`
"""},
     set()),
    ("fp-diamond-dependency-is-not-a-cycle",
     {"tasks/T-3.md": """# T-3 — a — PLANNED

- **Discharges.** R-1
- **Depends on.** T-1
- **Scope.**
  - `a/`
- **Gate.** a
- **Verify.** `true`
""",
      "tasks/T-4.md": """# T-4 — b — PLANNED

- **Discharges.** R-2
- **Depends on.** T-2, T-3
- **Scope.**
  - `b/`
- **Gate.** b
- **Verify.** `true`
"""},
     set()),
    ("fp-running-and-done-tasks-still-trace",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "tasks/T-2.md": T2.replace("— PLANNED", "— RUNNING (since 2026-09-03, T2-rm-1400)")},
     set()),
    ("fp-acceptance-that-is-an-observation-not-a-command",
     {"REQUIREMENTS.md": REQS.replace("- **Acceptance.** `test -s README.md`",
                                      "- **Acceptance.** a new user follows the README and succeeds unaided")},
     set()),
    ("fp-untracked-task-is-not-scanned",
     {"tasks/DRAFT.md": ("untracked", """# T-9 — a draft nobody committed — PLANNED

- **Discharges.** none
""")},
     set()),
]


def build(root, overrides):
    dt = os.path.join(root, "devteam")
    files = dict(FIXTURE)
    untracked = {}
    for name, body in overrides.items():
        if body is None:
            files.pop(name, None)
        elif isinstance(body, tuple):
            untracked[name] = body[1]
        else:
            files[name] = body

    for name, body in {**files, **untracked}.items():
        p = os.path.join(dt, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)

    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, env=env)
    run("init", "-q", "-b", "main")
    for name in files:
        run("add", os.path.join("devteam", name))
    run("commit", "-qm", "fixture")
    return dt


def main():
    passed = failed = 0
    for name, overrides, expected in CASES:
        root = tempfile.mkdtemp(prefix="devteam-trace-")
        try:
            dt = build(root, overrides)
            proc = subprocess.run([sys.executable, CHECK, dt], capture_output=True, text=True)
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
    print(f"\ncheck_trace control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
