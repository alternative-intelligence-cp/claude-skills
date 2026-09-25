#!/usr/bin/env python3
"""Negative control for check_report.py (P-35)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
CHECK = os.path.join(HERE, "check_report.py")
# A finding's line, as the check prints it: every indented line that is not a
# part, an exclusion, an acceptance or a note (roadmap 0.3.2, L-2.8).
FINDING = re.compile(r"^  (?!not evaluated: |excluded: |accepted by |reconstructed: )(\S+)", re.M)
PART = re.compile(r"^  not evaluated: (.+?) — ", re.M)

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
open: none
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
    # --- ACCEPTED reconciles rather than asserts agreement -----------------
    # The client closed the task OVER a failed verification (P-2), so the title
    # and report are EXPECTED to disagree. Checking them for agreement inverts
    # the state's purpose -- and the first of these is the COMMON shape: the
    # supervisor verifies each step and reports DONE, then an independent
    # verifier fails the task, and the client accepts over the verifier.
    ("fp-accepted-title-over-a-done-report",
     task_file(title="ACCEPTED (2026-09-05, D-41)"), set()),
    ("fp-accepted-title-over-an-escalated-report",
     task_file(report=REPORT.replace("status: DONE", "status: NEEDS-DECISION"),
               title="ACCEPTED (2026-09-05, D-41)"), set()),
    # ...and a DONE title still must agree, which is what caught the real one.
    ("status-mismatch-done-title-over-an-escalated-report",
     task_file(report=REPORT.replace("status: DONE", "status: NEEDS-DECISION")),
     {"status-mismatch"}),

    # --- unfinished-scope: the canonical assisted-development failure ------
    # A function stub with a TODO and a hard-coded value chosen so the test
    # passes, reported as done and tested. This pipeline CREATES stubs on
    # purpose in tests-first steps and never checked they were gone by close.
    ("unfinished-scope", task_file(), {"unfinished-scope"}, "T-1", [], "T-1: the config loader",
     "def load():\n    return 42  # TODO: read the real config\n"),
    ("unfinished-scope-not-implemented", task_file(), {"unfinished-scope"}, "T-1", [],
     "T-1: the config loader",
     "def load():\n    raise NotImplementedError\n"),
    # A TEST asserting the stub raises is legitimate and must not fire -- it is
    # exactly what a tests-first step writes, and the distinction is the
    # statement versus the assertion.
    ("fp-raises-notimplementederror-is-an-assertion", task_file(), set(), "T-1", [],
     "T-1: the config loader",
     "def test_stub():\n    with pytest.raises(NotImplementedError):\n        load()\n"),

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


def build(root, body, leftovers=(), subject="T-1: the config loader", src="x = 1\n",
          containment="guard-only"):
    """A committed project holding T-1. Its charter DECLARES its containment,
    because only a declaration may exclude the harness comparison (roadmap
    0.3.1, L-1.2): `guard-only` by default, so every case not about the harness
    meter sees it excluded by name; `structural` for the cases that are; None
    for a project that declares nothing, which gets no exclusion at all."""
    dt = os.path.join(root, "devteam", "tasks")
    os.makedirs(dt, exist_ok=True)
    with open(os.path.join(dt, "T-1.md"), "w", encoding="utf-8") as fh:
        fh.write(body)
    if containment is not None:
        with open(os.path.join(root, "devteam", "CHARTER.md"), "w", encoding="utf-8") as fh:
            fh.write("# Charter\n\n| Row | Value |\n|---|---|\n"
                     f"| Containment | `{containment}` — probe exit, 2026-09-24 |\n")
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    with open(os.path.join(root, "src", "main.py"), "w") as fh:
        fh.write(src)
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


ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
# A worker's block for S-1. The harness meters a step's dispatch, and only a
# step's block is compared with a meter (roadmap 0.3.2, L-2.7).
STEP = REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-1")


def metered(root, report, budget, line="S-1", containment="structural", already=False, base=True):
    """A project whose step blocks landed after the sandbox that metered them
    opened, as a promotion lands them: the task file is committed with an
    empty record, that commit is the sandbox's base -- `sandbox.py open`
    records the host's HEAD -- and the blocks land in the next commit.

    `line` is the step the `.sandbox` line names; None writes no line, and
    `no-root` a line naming no root. `budget` None writes no meta/budget.json.
    `already` makes the base the commit that landed the blocks, so they were
    in the file when the sandbox opened: a later attempt's sandbox. `base`
    False writes no meta/base.sha."""
    build(root, task_file(report=""), containment=containment)
    git = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, text=True,
                                    env=ENV).stdout.strip()
    opened = git("rev-parse", "HEAD")
    with open(os.path.join(root, "devteam", "tasks", "T-1.md"), "w", encoding="utf-8") as fh:
        fh.write(task_file(report=report))
    git("commit", "-qam", "T-1.S-1: land the step's report")
    if already:
        opened = git("rev-parse", "HEAD")
    sroot = os.path.join(root, "sbox")
    os.makedirs(os.path.join(sroot, "meta"), exist_ok=True)
    if budget is not None:
        with open(os.path.join(sroot, "meta", "budget.json"), "w") as fh:
            json.dump(budget, fh)
    if base:
        with open(os.path.join(sroot, "meta", "base.sha"), "w") as fh:
            fh.write(opened + "\n")
    if line is not None:
        locks = os.path.join(root, "devteam", ".run", "locks")
        os.makedirs(locks, exist_ok=True)
        with open(os.path.join(locks, "T-1.sandbox"), "w") as fh:
            fh.write(f"T-1 {'S-1' if line == 'no-root' else line} live2 exited 0 at "
                     f"2026-09-07T04:57:06{'' if line == 'no-root' else f' root {sroot}'}\n")
    return root


def main():
    passed = failed = 0
    for case in CASES:
        name, body, expected = case[:3]
        want = case[3] if len(case) > 3 else "T-1"
        leftovers = case[4] if len(case) > 4 else []
        subject = case[5] if len(case) > 5 else "T-1: the config loader"
        src = case[6] if len(case) > 6 else "x = 1\n"
        root = tempfile.mkdtemp(prefix="devteam-report-")
        try:
            build(root, body, leftovers, subject, src)
            proc = subprocess.run([sys.executable, CHECK, root, want],
                                  capture_output=True, text=True)
            got = set(FINDING.findall(proc.stdout))
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

    # --- 0.2.3 §3.6: the harness meters, the worker estimates --------------
    # P-17c. MEASURED 0.2.3: a live Haiku implementer reported
    # `budget: tokens=3000 minutes=1` for a step the harness metered at 309639
    # tokens and 0.59 minutes -- a hundredfold understatement written in good
    # faith by a process that cannot see the counter. These need a sandbox on
    # disk, so they sit here rather than in CASES.
    #
    # The `fp-` cases are the load-bearing half. A `guard-only` project has no
    # sandbox, and its reports are not defective for it; a check that announced
    # a problem on every such project would be noise in the common case, and
    # noise is how a check stops being read. SUPERSEDED IN PART by roadmap
    # 0.3.1, L-1.2: that silence also covered a `structural` project whose
    # comparator was GONE -- F-32's T-4 case, `clean` because the sandboxes had
    # been closed (pricelog RECORD.md:356). Now the charter's declaration
    # EXCLUDES the comparison by name (exit 0), and an absence with no
    # declaration behind it is NOT EVALUATED (exit 3), naming what was missing.
    #
    # AGAINST THE STEP IT METERED (roadmap 0.3.2, L-2.7). The harness meters a
    # worker's dispatch, and its `.sandbox` line names that dispatch's step. So
    # a step's block is compared with the meter the line names for that step,
    # and a task-level block -- a supervisor's, which the harness never
    # meters -- is excluded by name. The blocks below are S-1's unless a case
    # says otherwise, each landed after the sandbox that metered it opened.
    def step(report=STEP, **edits):
        for key, val in edits.items():
            report = re.sub(rf"^{key}: .*$", f"{key}: {val}", report, count=1, flags=re.M)
        return report

    meter = {"tokens": 4210, "minutes": 9.0, "model": "claude-opus-5"}
    both = {"budget-mismatch", "model-mismatch"}
    budget_cases = [
        # (name, the blocks landed, the step the `.sandbox` line names -- None
        #  for no line, "no-root" for a line naming no root -- budget.json or
        #  None, expected findings, expected parts not evaluated, the charter's
        #  containment, text the output must hold, metered()'s options)
        ("budget-mismatch-on-tokens", step(budget="tokens=3000 minutes=9"), "S-1",
         dict(meter, tokens=309639), {"budget-mismatch"}, set(), "structural",
         ["T-1.S-1: the report says tokens=3000 and the harness metered 309639"], {}),
        ("budget-mismatch-on-minutes", step(), "S-1", dict(meter, minutes=0.59),
         {"budget-mismatch"}, set(), "structural", [], {}),
        ("model-mismatch-when-the-worker-names-another-model", step(), "S-1",
         dict(meter, model="claude-haiku-4-5-20251001"), {"model-mismatch"}, set(), "structural",
         ["T-1.S-1: the report says `model: claude-opus-5`"], {}),
        ("fp-budget-inside-the-tolerances-is-clean", step(), "S-1",
         {"tokens": 4400, "minutes": 10.5, "model": "claude-opus-5"}, set(), set(), "structural", [], {}),
        # The declaration: a guard-only project has no meter, says so, exits 0.
        ("fp-guard-only-excludes-the-harness-by-declaration", step(budget="tokens=1 minutes=1"),
         None, None, set(), set(), "guard-only",
         ["excluded: budget-mismatch and model-mismatch"], {}),
        # THE DID-NOT-LOOK CASES (L-6). Each one read `clean` before 0.3.1.
        ("no-sandbox-file-on-a-structural-project-is-not-evaluated",
         step(budget="tokens=1 minutes=1"), None, None, set(), both, "structural", [], {}),
        ("a-sandbox-line-with-no-root-is-not-evaluated", step(budget="tokens=1 minutes=1"),
         "no-root", None, set(), both, "structural", [], {}),
        # F-32's T-4 case: the sandbox was closed, so its meter is gone.
        ("a-closed-sandbox-with-no-budget-json-is-not-evaluated",
         step(budget="tokens=1 minutes=1"), "S-1", None, set(), both, "structural", [], {}),
        # A project that declares nothing gets no exclusion: silence would need
        # a declaration behind it, and there is none.
        ("an-undeclared-containment-excludes-nothing", step(budget="tokens=1 minutes=1"),
         None, None, set(), both, None, [], {}),
        # ...and a row whose author BELIEVES it declared something is named
        # as well (L-1.3): `guard only` is not `guard-only`.
        ("a-containment-row-that-does-not-parse-is-named", step(budget="tokens=1 minutes=1"),
         None, None, set(), both | {"the charter's Containment row"}, "guard only", [], {}),
        # A figure that is no number at all is not compared, and says so.
        ("a-budget-figure-that-is-no-number-is-not-evaluated",
         step(budget="tokens=unknown minutes=9"), "S-1", meter, set(), {"budget-mismatch"},
         "structural", ["tokens as `unknown`, which is not a number"], {}),
        # A figure split over two lines is still read whole: the budget field
        # is joined before it is parsed.
        ("fp-a-budget-split-over-two-lines-is-read-whole", step(budget="tokens=4210\n  minutes=9"),
         "S-1", meter, set(), set(), "structural", [], {}),
        # F-32 (L-2.8): the honest hedge is read, and compared. RECORD.md:475's
        # four workers, T-8's S-1, S-2, S-3 and S-5, as T-8.md:1055 recorded
        # each figure against the harness's: out by 36, 24, 15.6 and 16.6
        # times, and none flagged.
        *[(f"f32-{said}-against-{got}-fires-marked-approximate",
           step(budget=f"tokens=~{said} minutes=~9"), "S-1", dict(meter, tokens=got),
           {"budget-mismatch"}, set(), "structural",
           [f"tokens=~{said}, marked approximate, and the harness metered {got} "
            "(10% tolerance)  (advisory)"], {})
          for said, got in ((35000, 1269199), (150000, 3600914), (240000, 3749248),
                            (260000, 4306918))],
        ("fp-f32-an-approximate-figure-within-tolerance-is-clean",
         step(budget="tokens=~4000 minutes=~9"), "S-1", meter, set(), set(), "structural", [], {}),
        # F-109: a correct Sonnet supervisor's report, marked for re-dispatch
        # against its last worker's Opus meter. A task-level block is excluded,
        # and the line names it.
        ("fp-f109-a-task-level-block-is-excluded-from-the-meter-by-name",
         REPORT.replace("model: claude-opus-5", "model: claude-sonnet-5"), "S-3", meter,
         set(), set(), "structural",
         ["excluded: T-1's block against the harness meter — by its header, which names no step"],
         {}),
        # F-103: S-2's block against S-4's meter. S-4's is compared, and S-2 is
        # named as compared with nothing.
        ("f103-only-the-step-the-line-names-is-compared",
         step(STEP.replace("T-1.S-1", "T-1.S-2"), budget="tokens=1 minutes=1") + "\n"
         + step(STEP.replace("T-1.S-1", "T-1.S-4"), budget="tokens=1 minutes=9"), "S-4", meter,
         {"budget-mismatch"}, both, "structural",
         ["T-1.S-4: the report says tokens=1 and the harness metered 4210",
          "devteam/.run/locks/T-1.sandbox names S-4 (S-2)"], {}),
        # F-136: a restarted task's latest task-level block is the previous
        # supervisor's, and the meter is the current step's worker's.
        ("fp-f136-the-previous-supervisors-block-is-never-compared-with-the-current-meter",
         REPORT.replace("REPORT implementer T-1", "REPORT supervisor T-1")
               .replace("model: claude-opus-5", "model: claude-sonnet-5")
               .replace("budget: tokens=4210 minutes=9", "budget: tokens=1 minutes=1") + "\n"
         + STEP.replace("T-1.S-1", "T-1.S-5"), "S-5", meter, set(), set(), "structural",
         ["excluded: T-1's block against the harness meter"], {}),
        # A LATER ATTEMPT'S METER (L-2.7). The line names S-1, and S-1's latest
        # block was already in the file when that sandbox opened: it is an
        # earlier attempt's, and the meter is not its own.
        ("a-block-already-there-when-the-sandbox-opened-is-not-compared",
         step(budget="tokens=1 minutes=1"), "S-1", meter, set(), both, "structural",
         ["with the block already in the task file, so its meter is a later attempt's (S-1)"],
         {"already": True}),
        ("a-sandbox-naming-no-base-is-not-compared", step(budget="tokens=1 minutes=1"), "S-1",
         meter, set(), both, "structural", ["meta/base.sha names no commit"], {"base": False}),
    ]
    for name, report, line, budget, expected, want_gaps, containment, must, opts in budget_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-budget-")
        try:
            metered(root, report, budget, line, containment, **opts)
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"],
                                  capture_output=True, text=True)
            got = set(FINDING.findall(proc.stdout))
            gaps = set(PART.findall(proc.stdout))
            want_rc = 1 if expected else (3 if want_gaps else 0)
            unsaid = [m for m in must if m not in proc.stdout]
            if got == expected and gaps == want_gaps and proc.returncode == want_rc and not unsaid:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'}, not evaluated "
                      f"{sorted(want_gaps) or 'nothing'}, exit {want_rc}")
                print(f"        got      {sorted(got) or 'clean'}, not evaluated "
                      f"{sorted(gaps) or 'nothing'}, exit {proc.returncode}")
                for m in unsaid:
                    print(f"        never says {m!r}")
                for text in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {text}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- `--blocking-only`, and the deadlock it exists to break (0.2.4) ----
    #
    # A worker cannot see the harness's counter, so `budget-mismatch` is a
    # finding nobody is ALLOWED to fix (`supervise`: record it, never edit the
    # worker's figure) and nobody CAN fix (a re-dispatch produces the same
    # estimate). With it blocking, correct work is rejected forever. Found by a
    # real supervisor on the first end-to-end run.
    #
    # Every case here names the exit code AND what stayed on stdout, because
    # the whole risk in a flag like this is that it becomes a way to not see
    # something. It must change the verdict and never the report.
    blocking_cases = [
        # (name, edits, budget, want_exit, must_print, must_not_print)
        ("blocking-only-passes-a-budget-mismatch-alone",
         {"budget": "tokens=15000 minutes=5"},
         {"tokens": 571986, "minutes": 1.16, "model": "claude-opus-5"},
         0, "budget-mismatch", None),
        # The advisory finding is STILL PRINTED. A flag that hid it would be a
        # way to make a finding go away, which is the opposite of the point.
        ("blocking-only-still-reports-the-advisory-finding",
         {"budget": "tokens=15000 minutes=5"},
         {"tokens": 571986, "minutes": 1.16, "model": "claude-opus-5"},
         0, "advisory", None),
        # THE ARM THAT MAKES THE FLAG MEAN ANYTHING. `model-mismatch` is not
        # advisory: a report naming a model that did not run is a report about
        # a different run (P-40). Without this case the flag could pass
        # everything and every case above would still be green.
        ("blocking-only-still-fails-a-model-mismatch",
         {"model": "claude-sonnet-5", "budget": "tokens=15000 minutes=5"},
         {"tokens": 571986, "minutes": 1.16, "model": "claude-haiku-4-5-20251001"},
         1, "model-mismatch", None),
        # And a blocking finding beside an advisory one still fails, rather
        # than the advisory one dragging the verdict down with it.
        ("blocking-only-fails-when-a-real-finding-sits-beside-an-advisory-one",
         {"status": "NONSENSE", "budget": "tokens=15000 minutes=5"},
         {"tokens": 571986, "minutes": 1.16, "model": "claude-opus-5"},
         1, "budget-mismatch", None),
        # fp: without the flag, the SAME report still fails. The flag is the
        # verifier's, not a change to what the check thinks.
        ("fp-without-the-flag-a-budget-mismatch-still-fails",
         {"budget": "tokens=15000 minutes=5"},
         {"tokens": 571986, "minutes": 1.16, "model": "claude-opus-5"},
         None, "budget-mismatch", None),
    ]
    for name, edits, budget, want_exit, must_print, must_not in blocking_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-blocking-")
        try:
            metered(root, step(**edits), budget)
            cmd = [sys.executable, CHECK, root, "T-1"]
            if want_exit is not None:
                cmd.append("--blocking-only")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            expect_rc = 1 if want_exit is None else want_exit
            err = None
            if proc.returncode != expect_rc:
                err = f"exit {proc.returncode}, expected {expect_rc}"
            elif must_print and must_print not in proc.stdout:
                err = f"stdout never mentions {must_print!r}"
            elif must_not and must_not in proc.stdout:
                err = f"stdout still mentions {must_not!r}"
            if err:
                failed += 1
                print(f"FAIL  {name}: {err}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
            else:
                passed += 1
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- zero rows, partial reads and wrapped fields (roadmap 0.3.1, L-1.3) --
    # Each case here read `clean`, or a misleading finding with nothing naming
    # its cause, before 0.3.1. The report is inside the task file's fence, as
    # every real one is.
    def _task(report=REPORT, edit=lambda body: body, title=None):
        return edit(task_file(report=report, title=title))

    no_budget = lambda block: block.replace("budget: tokens=4210 minutes=9\n", "")
    s4 = STEP.replace("T-1.S-1", "T-1.S-4")
    parse_cases = [
        # (name, task file body, expected findings, expected parts not evaluated,
        #  text the output must hold)
        # ZERO ROWS: the only REPORT line does not parse, so no block is read.
        # An annotation left open is not one (roadmap 0.3.2, L-2.7).
        ("zero-rows-the-only-header-leaves-its-annotation-open",
         _task(REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1 (re-dispatch")),
         {"no-report"}, {"the REPORT blocks"}, []),
        # A PARTIAL READ, F-34's shape: a later report the header grammar
        # cannot read, so the check reads the earlier one and says clean.
        ("partial-read-a-later-header-the-grammar-cannot-read",
         _task(REPORT + "\nREPORT implementer T-1 attempt 2\nstatus: RED\n"),
         set(), {"the REPORT blocks"}, []),
        # A key the grammar cannot read ends the field parse, and every field
        # after it is named at its line, not merely reported missing.
        ("partial-read-a-key-the-grammar-cannot-read-ends-the-parse",
         _task(REPORT.replace("checks:", "Checks:")),
         {"missing-field", "no-evidence"}, {"T-1's REPORT block"}, []),
        ("partial-read-a-scope-item-with-its-reason-inline",
         _task(edit=lambda b: b.replace("  - `src/`\n", "  - `src/`\n  - `docs/` — for the notes\n")),
         set(), {"dirty-tree and unfinished-scope"}, []),
        ("partial-read-a-title-without-separators",
         _task(edit=lambda b: b.replace("# T-1 — make it work — DONE (2026-09-03)",
                                        "# T-1 make it work DONE")),
         set(), {"status-mismatch"}, []),
        # READ WHOLE (roadmap 0.3.2, L-2.3): `status:` was read from its first
        # line, and one that continued was named as not evaluated. It is read
        # with its continuation, and refused as a whole when it is no status.
        ("a-status-continued-outside-the-grammar-is-refused-whole",
         _task(REPORT.replace("status: DONE", "status: DONE\n  (after the re-run)")),
         {"bad-report-status"}, set(), ["'DONE (after the re-run)' is not one of"]),
        # ...and what must stay CLEAN.
        # A status given wholly on its own continuation line is read whole.
        ("fp-a-status-on-its-own-line-is-read-whole",
         _task(REPORT.replace("status: DONE", "status:\n  DONE")), set(), set(), []),
        # Prose after a finished block, full of lowercase words and colons,
        # offers no REPORT field -- pricelog's T-6, T-11 and T-13 each have one.
        ("fp-prose-after-a-finished-block-is-not-its-fields",
         _task(REPORT + "\nSUPERVISOR NOTE — reproduced before\nlanding: the refusal line\n"
                        "anchor: the canonical one\n"), set(), set(), []),
        # A header the grammar cannot read is a superseded attempt when a block
        # it does read comes after it for the same id, as any earlier block is.
        ("fp-a-malformed-header-superseded-by-a-later-block-for-its-id",
         _task("REPORT tester T-1.S-4 attempt 1\nstatus: DONE\n\n" + s4), set(), set(), []),
        # ...and not when it names no step id, as pricelog's `REPORT tester
        # T-18.S-4-pre` does (F-111): no later block can be the same step's,
        # not even S-4's.
        ("a-header-naming-no-step-id-is-named-though-a-block-follows",
         _task("REPORT tester T-1.S-4-pre\nstatus: DONE\n\n" + s4),
         set(), {"the REPORT blocks"}, []),
        # ...nor when its annotation wraps past its line: `c6d1f82`'s auditor
        # header, whose parenthesis closed two lines below it.
        ("a-header-whose-annotation-wraps-past-its-line-is-named",
         _task("REPORT auditor T-1.S-3 (adversarial pass, verbatim — the auditor has no write\n"
               "access; reproduced here by the supervisor)\n\n" + REPORT),
         set(), {"the REPORT blocks"}, []),

        # --- WHICH BLOCKS ARE JUDGED (roadmap 0.3.2, L-2.7) ----------------
        # F-34: attempt 2's annotated header is S-4's latest block. Attempt 1's
        # -- no `budget:`, and citing a commit that was never promoted -- is
        # superseded, and judged for nothing.
        ("fp-f34-an-annotated-header-is-its-steps-latest-block",
         _task(no_budget(s4).replace("HEAD T-1: the config loader",
                                     "T-1.S-4: attempt 1, never promoted") + "\n"
               + s4.replace("REPORT implementer T-1.S-4", "REPORT implementer T-1.S-4 (ATTEMPT 2, "
                            "correcting attempt 1's FAILED verification)")),
         set(), set(), ["[1 blocks judged, 1 superseded]"]),
        # F-37: a malformed step block, then a well-formed task-level block.
        # `check_report . T-9` read clean where `. T-9.S-3` did not, on one
        # tree; the task's run reports the step's finding, naming the step, at
        # its block's header.
        ("f37-the-tasks-run-reports-a-step-blocks-finding",
         _task(no_budget(STEP.replace("T-1.S-1", "T-1.S-3")) + "\n" + REPORT),
         {"missing-field"}, set(),
         ["tasks/T-1.md:15  T-1.S-3: the block has no `budget:`", "[2 blocks judged, 0 superseded]"]),
        # F-88: an annotated key is read as its key, and nothing after it is
        # missing.
        ("fp-f88-an-annotated-key-is-read-as-its-key",
         _task(REPORT.replace("checks:", "checks (all run by the supervisor, verbatim):")),
         set(), set(), []),
        # ...and F-88's own, as `7aa90ac` landed it: the parenthesis opened on
        # the key's line and closed on the second indented line under it.
        ("fp-f88-a-key-annotation-continued-onto-indented-lines-is-read",
         _task(REPORT.replace("checks:", "checks (all run by the supervisor -- first inside the "
                              "sandbox before\n  promotion, then re-run host-side; figures below\n"
                              "  are the host-side, post-promotion run):")),
         set(), set(), []),
        # An annotation that never closes is no key, and the line is named as
        # the one the parse stopped at.
        ("a-key-annotation-that-never-closes-ends-the-parse",
         _task(REPORT.replace("checks:", "checks (all run by the supervisor\n  and never closed")),
         {"missing-field", "no-evidence"}, {"T-1's REPORT block"}, []),
        # F-86 (L-2.8): the qualifier is read, and the line says so.
        ("fp-f86-a-reconstructed-status-is-read-and-named",
         _task(REPORT.replace("status: DONE", "status: DONE (reconstructed: by the supervisor from "
                              "the worker's commits; the worker died)")),
         set(), set(),
         ["  reconstructed: T-1 — by the supervisor from the worker's commits; the worker died"]),
        ("fp-f86-a-reconstructed-status-over-two-lines-is-read-whole",
         _task(REPORT.replace("status: DONE", "status: DONE (reconstructed: by the supervisor from\n"
                              "  the worker's commits; the worker died)")),
         set(), set(),
         ["  reconstructed: T-1 — by the supervisor from the worker's commits; the worker died"]),
        # ...and the run's own form is still refused, showing the grammar's.
        ("f86-the-runs-own-form-is-refused-showing-the-grammars",
         _task(REPORT.replace("status: DONE", "status: DONE -- RECONSTRUCTED")),
         {"bad-report-status"}, set(),
         ["T-1: 'DONE -- RECONSTRUCTED' is not one of DONE, BLOCKED, NEEDS-DECISION, RED, "
          "READY-TO-AUDIT, or `<status> (reconstructed: <by whom, and why>)`"]),
        # One defect in a step's block and in the task's block is two findings,
        # each naming its block: two identities, so neither stands in for the
        # other at the gate or under an acceptance.
        ("one-defect-in-two-blocks-is-two-findings-each-naming-its-block",
         _task(no_budget(STEP) + "\n" + no_budget(REPORT)), {"missing-field"}, set(),
         ["T-1.S-1: the block has no `budget:`", "T-1: the block has no `budget:`"]),
        # A task that has not reported has its steps judged, and nothing meets
        # its title.
        ("a-running-tasks-steps-are-judged-and-none-meets-the-title",
         _task(no_budget(STEP), title="RUNNING (since 2026-09-03, T1-a-1200)"),
         {"missing-field"}, set(), ["T-1.S-1: the block has no `budget:`"]),
        # A superseded attempt citing a commit never promoted is not judged.
        ("fp-a-superseded-attempt-citing-a-commit-never-promoted-is-not-judged",
         _task(STEP.replace("HEAD T-1: the config loader", "T-1.S-1: attempt 1, never promoted")
               + "\n" + STEP), set(), set(), ["[1 blocks judged, 1 superseded]"]),

        # --- WHERE ITEMS COME FROM (roadmap 0.3.3, L-3.4) ------------------
        # T-10.S-3's landing (tasks/T-10.md:423): an auditor's answer under a
        # REPORT line over three lines. It is named as not a report, and the
        # reason shows the form an answer lands in.
        ("t10-an-auditors-report-line-is-named-with-the-audit-form",
         _task("REPORT auditor T-1.S-3 (adversarial pass, verbatim, P-17 — the auditor has no "
               "write\naccess and could not land this itself; reproduced here by the supervisor "
               "exactly as\nreceived)\n\n## Finding 1 — a claim that is not sole\n\n" + REPORT),
         set(), {"the REPORT blocks"},
         ["tasks/T-1.md:15 is an auditor's REPORT line, and an audit's answer is not a report",
          "`AUDIT T-1.S-3 (<dimension>)`", "`END AUDIT T-1.S-3`",
          "safety, correctness, security or hygiene"]),
        # One that parses as a header is no block: it is named, not judged.
        ("an-auditors-report-line-that-parses-is-named-not-judged",
         _task("REPORT auditor T-1.S-3\n\nNo new violation survived.\n\n" + REPORT),
         set(), {"the REPORT blocks"},
         ["`AUDIT T-1.S-3 (<dimension>)`", "[1 blocks judged, 0 superseded]"]),
        # ...and a later block for its id does not supersede it, because it
        # was never a report.
        ("an-auditors-report-line-is-named-though-a-later-block-names-its-id",
         _task("REPORT auditor T-1.S-4 (adversarial pass, over\ntwo lines)\n\n" + s4 + "\n" + REPORT),
         set(), {"the REPORT blocks"}, ["`AUDIT T-1.S-4 (<dimension>)`"]),
        # A worker's header whose annotation wraps is still F-34's shape.
        ("a-workers-header-whose-annotation-wraps-past-its-line-is-named",
         _task("REPORT implementer T-1.S-3 (attempt 2, correcting\nattempt 1)\n\n" + REPORT),
         set(), {"the REPORT blocks"}, ["do not parse as `REPORT <role> T-n[.S-m]"]),
        # `open:` is required, as `questions:` is; `none` is an answer.
        ("open-a-block-with-no-open-key-is-missing-field",
         _task(REPORT.replace("open: none\n", "")), {"missing-field"}, set(),
         ["T-1: the block has no `open:`"]),
        ("fp-open-none-is-an-answer", _task(REPORT), set(), set(), []),
        ("fp-open-with-two-items-is-clean",
         _task(REPORT.replace("open: none\n", "open:\n  - a defect found and not fixed: the "
                              "retry's second line\n  - work the step could not reach: the "
                              "ext4 half\n")), set(), set(), []),
        # An answer landed after a block is text between blocks: its lines are
        # never that block's fields. Here the block's parse stopped early, and
        # only the block's own two unread lines are named.
        ("an-answer-after-a-block-is-never-read-as-its-fields",
         _task(REPORT.replace("budget: tokens=4210 minutes=9\n",
                              "Budget, below.\nbudget: tokens=4210 minutes=9\n")
               + "\nAUDIT T-1.S-2 (correctness)\n\nnotes: the auditor's own word\n"
                 "questions: none of its own\n\nEND AUDIT T-1.S-2\n"),
         {"missing-field"}, {"T-1's REPORT block"},
         ["2 field line(s) from there on were not read"]),
        # ...and a block followed directly by an answer reads clean.
        ("fp-a-block-followed-directly-by-an-answer-reads-clean",
         _task(REPORT + "AUDIT T-1.S-2 (correctness)\nstatus: every clause held\nscope: "
                        "T-1.S-2's claim\nnotes: none\n\n## COR-1 — a stale sentence\n\n"
                        "END AUDIT T-1.S-2\n"), set(), set(), []),
        # A block landed after an answer's closing line is read as before.
        ("fp-a-block-after-an-answers-closing-line-is-read-as-before",
         _task("AUDIT T-1.S-2 (correctness)\n\n## COR-1 — a stale sentence\n\nEND AUDIT "
               "T-1.S-2\n\n" + REPORT), set(), set(), ["[1 blocks judged, 0 superseded]"]),
    ]
    for name, body, expected, want_gaps, must in parse_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-parse-")
        try:
            build(root, body)
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"],
                                  capture_output=True, text=True)
            got = set(FINDING.findall(proc.stdout))
            gaps = set(PART.findall(proc.stdout))
            want_rc = 1 if expected else (3 if want_gaps else 0)
            unsaid = [m for m in must if m not in proc.stdout]
            if got == expected and gaps == want_gaps and proc.returncode == want_rc and not unsaid:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'}, not evaluated "
                      f"{sorted(want_gaps) or 'nothing'}, exit {want_rc}")
                print(f"        got      {sorted(got) or 'clean'}, not evaluated "
                      f"{sorted(gaps) or 'nothing'}, exit {proc.returncode}")
                for m in unsaid:
                    print(f"        never says {m!r}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- accepted findings (roadmap 0.3.1, L-1.6) --------------------------
    # This check reads ONE task, so an acceptance names the task's file and
    # only that task's own run may apply it or call it stale. The `fp-` cases
    # are the ones that fail if it judges every acceptance in every run: a run
    # for T-1 would call T-2's acceptance stale, and a step's run would call
    # its task's acceptance stale, though neither evaluated what it names.
    mismatch = task_file(report=REPORT.replace("status: DONE", "status: NEEDS-DECISION"))
    # The message names its block (roadmap 0.3.2, L-2.7), so an acceptance of
    # the message as it read before names nothing.
    a_mismatch = ("`check_report` `status-mismatch` `tasks/T-1.md` — T-1: status NEEDS-DECISION "
                  "but the title says 'DONE (2026-09-03)'")
    step = task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1.S-1"),
                     title="RUNNING (since 2026-09-03, T1-a-1200)")
    decisions = lambda *items: ("# Decisions\n\n### D-1 — T-1's report stands as it is\n\n"
                                "- **Decision.** it stands.\n- **Supersedes.** none\n"
                                "- **Reviewed.** client\n- **Accepts.**\n"
                                + "".join(f"  - {i}\n" for i in items))
    accept_cases = [
        # (name, task file, acceptances, run, containment, exit, findings, accepted, parts)
        ("accepted-finding-in-the-tasks-own-run-exits-0",
         mismatch, [a_mismatch], "T-1", "guard-only", 0, set(), {("D-1", "status-mismatch")}, set()),
        ("a-fixed-finding-leaves-its-acceptance-stale-in-the-tasks-own-run",
         task_file(), [a_mismatch], "T-1", "guard-only", 1, {"stale-acceptance"}, set(), set()),
        ("fp-a-run-for-one-task-does-not-judge-anothers-acceptance",
         task_file(), [a_mismatch.replace("tasks/T-1.md", "tasks/T-2.md")], "T-1", "guard-only",
         0, set(), set(), set()),
        ("fp-a-steps-run-neither-applies-nor-judges-its-tasks-acceptance",
         step, [a_mismatch], "T-1.S-1", "guard-only", 0, set(), set(), set()),
        # A part cannot be accepted here (result.py refuses it, and check_refs
        # reports the line): the harness gap stands, named, and exits 3.
        ("a-part-of-check_report-is-not-acceptable",
         task_file(report=STEP), ["`check_report` not evaluated: model-mismatch"], "T-1",
         "structural", 3, set(), set(), {"budget-mismatch", "model-mismatch"}),
        ("an-acceptance-of-a-message-that-named-no-block-is-stale",
         mismatch, [a_mismatch.replace("— T-1: status", "— status")], "T-1", "guard-only", 1,
         {"stale-acceptance", "status-mismatch"}, set(), set()),
    ]
    for (name, body, items, run_id, containment, want_rc, expected, want_acc,
         want_gaps) in accept_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-accept-")
        try:
            os.makedirs(os.path.join(root, "devteam"))
            with open(os.path.join(root, "devteam", "DECISIONS.md"), "w", encoding="utf-8") as fh:
                fh.write(decisions(*items))
            build(root, body, containment=containment)
            proc = subprocess.run([sys.executable, CHECK, root, run_id], capture_output=True, text=True)
            out = proc.stdout
            got = set(FINDING.findall(out))
            got_acc = set(re.findall(r"^  accepted by (D-\d+): (\S+)", out, re.M))
            gaps = set(PART.findall(out))
            if (proc.returncode == want_rc and got == expected and got_acc == want_acc
                    and gaps == want_gaps):
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected exit {want_rc} {sorted(expected) or 'clean'} "
                      f"accepted {sorted(want_acc) or 'none'} not evaluated {sorted(want_gaps) or 'none'}")
                for line in (out + proc.stderr).strip().split("\n")[:8]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- the previous claim's report (roadmap 0.3.2, L-2.7; F-136) ---------
    # A restart is a new claim under a new label (L-2.5), and until its
    # supervisor reports, the task's latest task-level block is the previous
    # claim's close. Its DONE was compared with the new RUNNING title: 8 of
    # 0.3.1's 14 restart commits were refused for it, `90b8b42` and `79e9b7f`
    # for nothing else. The history below is the claim protocol's: a claim on
    # the board, the supervisor's title, its close, the board cleared, and a
    # claim again.
    flight_head = ("| Task | Title | Agent label | Agent id | Sandbox | Since | Model | Scope | "
                   "Note |\n|---|---|---|---|---|---|---|---|---|\n")
    board = lambda *claims: ("# The board\n\n## In flight\n\n" + flight_head + "".join(
        f"| {t} | a task | {lab} | `a1b2c3` | — | 2026-09-03 12:00 | opus-5-5 | — | running |\n"
        for t, lab in claims) or "")
    close = task_file(report=REPORT.replace("REPORT implementer T-1", "REPORT supervisor T-1"))
    title = lambda status: re.sub(r"^# T-1 .*$", f"# T-1 — make it work — {status}", close,
                                  count=1, flags=re.M)
    stub = {"src/main.py": "def load():\n    raise NotImplementedError\n"}
    restarts = [
        # (name, the title and board after the close, what lands after them,
        #  the restart's own work -- committed, then left uncommitted --
        #  expected findings, text the output must hold)
        ("fp-f136-a-restart-under-a-new-label-compares-its-previous-close-with-nothing",
         "RUNNING (since 2026-09-04, T1-b-1500)", "T1-b-1500", None, {}, {}, set(),
         ["excluded: status-mismatch, dirty-tree and unfinished-scope for T-1's block — by the "
          "claim its title names, T1-b-1500, which began at"]),
        # b57c29e's shape, with its title written as the grammar says: a reopen
        # that keeps its label keeps its claim, so the close is its own.
        ("f136-a-reopen-under-its-own-label-compares-its-own-close",
         "RUNNING (since 2026-09-04, T1-a-1200)", "T1-a-1200", None, {}, {}, {"status-mismatch"},
         ["T-1: status DONE but the title says 'RUNNING (since 2026-09-04, T1-a-1200)'"]),
        # 42425a8's shape: a title that names no label has no current claim,
        # and its block is compared as it always was.
        ("f136-a-title-naming-no-label-compares-its-previous-close",
         "RUNNING (re-dispatched 2026-09-04, after verify FAIL)", "T1-b-1500", None, {}, {},
         {"status-mismatch"}, []),
        # ...and so has a label no board commit carries: `cbbad26`'s shape,
        # T-5's title naming `T5-restart-0853` over a board that carried
        # `T5-harness-restart-0730`.
        ("f136-a-label-no-board-carries-compares-its-previous-close",
         "RUNNING (since 2026-09-04, T1-z-0853)", "T1-b-1500", None, {}, {},
         {"status-mismatch"}, []),
        # Only the previous claim's block is exempt: the restart's own close,
        # landed with the title left RUNNING, is compared.
        ("f136-the-restarts-own-close-is-compared",
         "RUNNING (since 2026-09-04, T1-b-1500)", "T1-b-1500",
         REPORT.replace("REPORT implementer T-1", "REPORT supervisor T-1 (the restart's close)"),
         {}, {}, {"status-mismatch"}, []),
        # NOR THE TREE (the owner's answer of 2026-09-24). A restart's
        # tests-first step writes a stub into the scope, and a worker's file
        # sits uncommitted in it; neither is the previous close's.
        ("fp-f136-a-restarts-stub-and-uncommitted-work-meet-not-the-previous-close",
         "RUNNING (since 2026-09-04, T1-b-1500)", "T1-b-1500", None, stub,
         {"src/next.py": "x = 2\n"}, set(), []),
        # ...and under a claim that kept its label, the close is the current
        # claim's, so both are compared with it, as at any close.
        ("f136-a-reopens-stub-and-uncommitted-work-meet-its-own-close",
         "RUNNING (since 2026-09-04, T1-a-1200)", "T1-a-1200", None, stub,
         {"src/next.py": "x = 2\n"}, {"status-mismatch", "unfinished-scope", "dirty-tree"}, []),
    ]
    for name, status, label, later, work, dirty, expected, must in restarts:
        root = tempfile.mkdtemp(prefix="devteam-report-restart-")
        git = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, text=True,
                                        env=ENV)

        def land(subject, files):
            for rel, text in files.items():
                path = os.path.join(root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            git("add", "-A")
            git("commit", "-qm", subject)
        try:
            build(root, task_file(report="", title="PLANNED"), subject="plan T-1")
            land("board: claim T-1", {"devteam/BOARD.md": board(("T-1", "T1-a-1200"))})
            land("T-1: claimed", {"devteam/tasks/T-1.md": task_file(
                report="", title="RUNNING (since 2026-09-03, T1-a-1200)")})
            land("T-1: the config loader", {"devteam/tasks/T-1.md": close})
            land("board: T-1 closed", {"devteam/BOARD.md": board()})
            land(f"board: claim T-1 as {label}", {"devteam/BOARD.md": board(("T-1", label))})
            land("T-1: restarted", {"devteam/tasks/T-1.md": title(status)})
            if later:
                land("T-1: the restart's close", {"devteam/tasks/T-1.md": title(status).rstrip("\n")
                                                  .removesuffix("```").rstrip("\n")
                                                  + "\n\n" + later + "```\n"})
            if work:
                land("T-1.S-2: the stub first", work)
            for rel, text in dirty.items():
                with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
                    fh.write(text)
                git("add", "-N", rel)
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"], capture_output=True, text=True)
            got = set(FINDING.findall(proc.stdout))
            unsaid = [m for m in must if m not in proc.stdout]
            if got == expected and proc.returncode == (1 if expected else 0) and not unsaid:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}\n        expected {sorted(expected) or 'clean'}, "
                      f"got {sorted(got) or 'clean'} exit {proc.returncode}")
                for m in unsaid:
                    print(f"        never says {m!r}")
                for text in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {text}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
        parse_cases.append((name,))

    # NO REPOSITORY IS COULD-NOT-RUN (L-1.1), and it used to be a traceback:
    # step 3.1 made every return of check() a triple except this one.
    root = tempfile.mkdtemp(prefix="devteam-report-nogit-")
    try:
        build(root, task_file())
        shutil.rmtree(os.path.join(root, ".git"))
        proc = subprocess.run([sys.executable, CHECK, root, "T-1"], capture_output=True, text=True)
        if proc.returncode == 2 and "Traceback" not in proc.stderr and not proc.stdout.strip():
            passed += 1
        else:
            failed += 1
            print("FAIL  no-repository-is-could-not-run-not-a-traceback")
            for line in (proc.stdout + proc.stderr).strip().split("\n")[-4:]:
                print(f"        | {line}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    parse_cases.append(("no-repository-is-could-not-run-not-a-traceback",))

    # --- a checkout of one commit (roadmap 0.3.1, L-1.5) -------------------
    # `--at-commit` excludes the classes that read the working state, by the
    # caller's declaration, and names each. So an uncommitted file inside the task's scope -- which a clean
    # checkout of a commit never holds -- is a finding without the flag, and
    # with it is excluded, named, and leaves the rest to decide the exit.
    root = tempfile.mkdtemp(prefix="devteam-report-")
    try:
        build(root, task_file(), leftovers=[("src/leftover.py", "x = 1\n")])
        live = subprocess.run([sys.executable, CHECK, root, "T-1"], capture_output=True, text=True)
        at = subprocess.run([sys.executable, CHECK, root, "T-1", "--at-commit"], capture_output=True, text=True)
        ok = (live.returncode == 1 and re.search(r"^  dirty-tree\s", live.stdout, re.M)
              and at.returncode == 0 and not re.search(r"^  dirty-tree\s", at.stdout, re.M)
              and re.search(r"^  excluded: dirty-tree — by --at-commit", at.stdout, re.M))
        if ok:
            passed += 1
        else:
            failed += 1
            print("FAIL  at-commit-excludes-the-working-state-and-names-it")
            for line in (live.stdout + at.stdout + at.stderr).strip().split("\n")[:8]:
                print(f"        | {line}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    parse_cases.append(("at-commit-excludes-the-working-state-and-names-it",))

    # --- HEAD's history, not `--all` (roadmap 0.3.2, L-2.6) ----------------
    # A commit a report cites must be in the history of HEAD, which at the gate
    # is the commit being judged. `--all` let a subject resolve on another
    # branch, or under `refs/devteam/sandbox/`, where a promotion stopped on a
    # conflict leaves an unpromoted worker's commits; and a hash resolved when
    # it named any commit object, a refused gate candidate among them.
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def side(root, subject, ref):
        """A commit off HEAD's history: on a branch, under a ref, or (no ref)
        an object only, as a refused gate candidate is. Its full hash."""
        run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, text=True,
                                        env=env)
        sha = run("commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", subject).stdout.strip()
        if ref:
            run("update-ref", ref, sha)
        return sha

    history_cases = [
        # (name, the side commit's subject, its ref, the commits: line given
        #  that hash, main's subject, expected)
        ("l26-a-subject-only-on-another-branch-is-an-unknown-commit",
         "T-1: the side work", "refs/heads/side", lambda sha: "  - T-1: the side work",
         "T-1: the config loader", {"unknown-commit"}),
        ("l26-a-subject-only-under-a-sandbox-ref-is-an-unknown-commit",
         "T-1.S-1: an unpromoted step", "refs/devteam/sandbox/T-1-S-1-120000",
         lambda sha: "  - T-1.S-1: an unpromoted step", "T-1: the config loader", {"unknown-commit"}),
        ("l26-a-hash-not-in-heads-history-is-an-unknown-commit",
         "T-1: a refused gate candidate", None, lambda sha: f"  - {sha[:12]} T-1: a refused gate candidate",
         "T-1: the config loader", {"unknown-commit"}),
        ("l26-a-branch-commit-under-the-prefix-does-not-satisfy-head-subject",
         "T-1: the side work", "refs/heads/side", lambda sha: "  - HEAD chore: land the report",
         "chore: touch up", {"head-subject"}),
        ("fp-l26-a-hash-in-heads-history-is-known",
         "T-1: the side work", "refs/heads/side", None, "T-1: the config loader", set()),
    ]
    for name, subject, ref, cite, main_subject, expected in history_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-history-")
        try:
            build(root, task_file(), subject=main_subject)
            sha = side(root, subject, ref)
            root_sha = subprocess.run(["git", "-C", root, "rev-list", "--max-parents=0", "HEAD"],
                                      capture_output=True, text=True).stdout.strip()
            line = cite(sha) if cite else f"  - {root_sha} T-1: the config loader"
            with open(os.path.join(root, "devteam", "tasks", "T-1.md"), "w", encoding="utf-8") as fh:
                fh.write(task_file(report=REPORT.replace("  - HEAD T-1: the config loader", line)))
            landed = "chore: land the report" if "head-subject" in name else "T-1: land the report"
            subprocess.run(["git", "-C", root, "commit", "-qam", landed], capture_output=True, env=env)
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"], capture_output=True, text=True)
            got = set(FINDING.findall(proc.stdout))
            said = ("HEAD's history" in proc.stdout) if expected else True
            if got == expected and proc.returncode == (1 if expected else 0) and said:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}\n        expected {sorted(expected) or 'clean'}, "
                      f"got {sorted(got) or 'clean'} exit {proc.returncode}")
                for text in (proc.stdout + proc.stderr).strip().split("\n")[:6]:
                    print(f"        | {text}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
        parse_cases.append((name,))
    CASES.extend([(c[0],) for c in parse_cases])
    CASES.extend([(c[0],) for c in blocking_cases])
    CASES.extend([(c[0],) for c in accept_cases])
    fp = (sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
          + sum(1 for c in budget_cases if c[0].startswith("fp-")))
    print(f"\ncheck_report control: {passed} passed, {failed} failed, "
          f"{len(CASES) + len(budget_cases)} cases ({fp} of them "
          f"false-positive controls, "
          f"{100 * fp // (len(CASES) + len(budget_cases))}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
