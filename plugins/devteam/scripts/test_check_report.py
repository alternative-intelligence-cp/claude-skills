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
            got = {m for m in re.findall(r"^  (?!not evaluated: |excluded: )(\S+)", proc.stdout, re.M)}
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
    budget_cases = [
        # (name, report edits, sandbox {} or None, budget.json or None, expected,
        #  expected parts not evaluated, the charter's containment)
        ("budget-mismatch-on-tokens",
         {"budget": "tokens=3000 minutes=9"},
         True, {"tokens": 309639, "minutes": 9.0, "model": "claude-opus-5"},
         {"budget-mismatch"}, set(), "structural"),
        ("budget-mismatch-on-minutes",
         {"budget": "tokens=4210 minutes=9"},
         True, {"tokens": 4210, "minutes": 0.59, "model": "claude-opus-5"},
         {"budget-mismatch"}, set(), "structural"),
        ("model-mismatch-when-the-worker-names-another-model",
         {}, True,
         {"tokens": 4210, "minutes": 9.0, "model": "claude-haiku-4-5-20251001"},
         {"model-mismatch"}, set(), "structural"),
        ("fp-budget-inside-the-tolerances-is-clean",
         {}, True, {"tokens": 4400, "minutes": 10.5, "model": "claude-opus-5"},
         set(), set(), "structural"),
        # The declaration: a guard-only project has no meter, says so, exits 0.
        ("fp-guard-only-excludes-the-harness-by-declaration",
         {"budget": "tokens=1 minutes=1"}, False, None, set(), set(), "guard-only"),
        # THE DID-NOT-LOOK CASES (L-6). Each one read `clean` before 0.3.1.
        ("no-sandbox-file-on-a-structural-project-is-not-evaluated",
         {"budget": "tokens=1 minutes=1"}, False, None, set(),
         {"budget-mismatch", "model-mismatch"}, "structural"),
        ("a-sandbox-line-with-no-root-is-not-evaluated",
         {"budget": "tokens=1 minutes=1"}, "no-root", None, set(),
         {"budget-mismatch", "model-mismatch"}, "structural"),
        # F-32's T-4 case: the sandbox was closed, so its meter is gone.
        ("a-closed-sandbox-with-no-budget-json-is-not-evaluated",
         {"budget": "tokens=1 minutes=1"}, True, None, set(),
         {"budget-mismatch", "model-mismatch"}, "structural"),
        # A project that declares nothing gets no exclusion: silence would need
        # a declaration behind it, and there is none.
        ("an-undeclared-containment-excludes-nothing",
         {"budget": "tokens=1 minutes=1"}, False, None, set(),
         {"budget-mismatch", "model-mismatch"}, None),
        # ...and a row whose author BELIEVES it declared something is named
        # as well (L-1.3): `guard only` is not `guard-only`.
        ("a-containment-row-that-does-not-parse-is-named",
         {"budget": "tokens=1 minutes=1"}, False, None, set(),
         {"budget-mismatch", "model-mismatch", "the charter's Containment row"}, "guard only"),
        # F-32's hedged figure: the harness has a number, the report gives
        # `~N`, and the comparison was skipped as though it had passed.
        ("a-hedged-budget-figure-is-not-evaluated",
         {"budget": "tokens=~4000 minutes=9"}, True,
         {"tokens": 4210, "minutes": 9.0, "model": "claude-opus-5"},
         set(), {"budget-mismatch"}, "structural"),
        # A figure split over two lines is still read whole: the budget field
        # is joined before it is parsed.
        ("fp-a-budget-split-over-two-lines-is-read-whole",
         {"budget": "tokens=4210\n  minutes=9"}, True,
         {"tokens": 4210, "minutes": 9.0, "model": "claude-opus-5"},
         set(), set(), "structural"),
    ]
    for name, edits, sb, budget, expected, want_gaps, containment in budget_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-budget-")
        try:
            report = REPORT
            for key, val in edits.items():
                report = re.sub(rf"^{key}: .*$", f"{key}: {val}", report,
                                count=1, flags=re.M)
            build(root, task_file(report=report), containment=containment)
            sroot = os.path.join(root, "sbox")
            os.makedirs(os.path.join(sroot, "meta"), exist_ok=True)
            if budget is not None:
                with open(os.path.join(sroot, "meta", "budget.json"), "w") as fh:
                    json.dump(budget, fh)
            if sb:
                locks = os.path.join(root, "devteam", ".run", "locks")
                os.makedirs(locks, exist_ok=True)
                line = ("T-1 S-1 live2 exited 0 at 2026-09-07T04:57:06"
                        + ("" if sb == "no-root" else f" root {sroot}"))
                with open(os.path.join(locks, "T-1.sandbox"), "w") as fh:
                    fh.write(line + "\n")
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"],
                                  capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (?!not evaluated: |excluded: )(\S+)", proc.stdout, re.M)}
            gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            want_rc = 1 if expected else (3 if want_gaps else 0)
            excluded_ok = (containment != "guard-only"
                           or "excluded: budget-mismatch and model-mismatch" in proc.stdout)
            if got == expected and gaps == want_gaps and proc.returncode == want_rc and excluded_ok:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'}, not evaluated "
                      f"{sorted(want_gaps) or 'nothing'}, exit {want_rc}")
                print(f"        got      {sorted(got) or 'clean'}, not evaluated "
                      f"{sorted(gaps) or 'nothing'}, exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
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
            report = REPORT
            for key, val in edits.items():
                report = re.sub(rf"^{key}: .*$", f"{key}: {val}", report,
                                count=1, flags=re.M)
            build(root, task_file(report=report), containment="structural")
            sroot = os.path.join(root, "sbox")
            os.makedirs(os.path.join(sroot, "meta"), exist_ok=True)
            with open(os.path.join(sroot, "meta", "budget.json"), "w") as fh:
                json.dump(budget, fh)
            locks = os.path.join(root, "devteam", ".run", "locks")
            os.makedirs(locks, exist_ok=True)
            with open(os.path.join(locks, "T-1.sandbox"), "w") as fh:
                fh.write(f"T-1 S-1 live2 exited 0 at 2026-09-07T04:57:06 root {sroot}\n")
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
    def _task(report=REPORT, edit=lambda body: body):
        return edit(task_file(report=report))

    parse_cases = [
        # (name, task file body, expected findings, expected parts not evaluated)
        # ZERO ROWS: the only REPORT line does not parse, so no block is read.
        ("zero-rows-the-only-header-carries-an-annotation",
         _task(REPORT.replace("REPORT implementer T-1", "REPORT implementer T-1 (re-dispatch)")),
         {"no-report"}, {"the REPORT blocks"}),
        # A PARTIAL READ, F-34's shape: a later report the header grammar
        # cannot read, so the check reads the earlier one and says clean.
        ("partial-read-a-later-header-the-grammar-cannot-read",
         _task(REPORT + "\nREPORT implementer T-1 (second attempt)\nstatus: RED\n"),
         set(), {"the REPORT blocks"}),
        # F-88's shape: an annotated key ends the field parse, and every field
        # after it reads as missing with nothing naming the line.
        ("partial-read-an-annotated-key-ends-the-parse",
         _task(REPORT.replace("checks:", "checks (all run by the supervisor):")),
         {"missing-field", "no-evidence"}, {"the REPORT block"}),
        ("partial-read-a-scope-item-with-its-reason-inline",
         _task(edit=lambda b: b.replace("  - `src/`\n", "  - `src/`\n  - `docs/` — for the notes\n")),
         set(), {"dirty-tree and unfinished-scope"}),
        ("partial-read-a-title-without-separators",
         _task(edit=lambda b: b.replace("# T-1 — make it work — DONE (2026-09-03)",
                                        "# T-1 make it work DONE")),
         set(), {"status-mismatch"}),
        # A WRAPPED FIELD: `status:` read from its first line only.
        ("wrapped-field-a-status-that-continues",
         _task(REPORT.replace("status: DONE", "status: DONE\n  (after the re-run)")),
         set(), {"the report's status"}),
        # ...and what must stay CLEAN.
        # A status given wholly on its own continuation line is read whole.
        ("fp-a-status-on-its-own-line-is-read-whole",
         _task(REPORT.replace("status: DONE", "status:\n  DONE")), set(), set()),
        # Prose after a finished block, full of lowercase words and colons,
        # offers no REPORT field -- pricelog's T-6, T-11 and T-13 each have one.
        ("fp-prose-after-a-finished-block-is-not-its-fields",
         _task(REPORT + "\nSUPERVISOR NOTE — reproduced before\nlanding: the refusal line\n"
                        "anchor: the canonical one\n"), set(), set()),
        # A malformed header BEFORE the block read cannot hide a later report
        # -- pricelog's `REPORT tester T-18.S-4-pre` is this.
        ("fp-a-malformed-header-before-the-block-read",
         _task("REPORT tester T-1.S-4-pre\nstatus: DONE\n\n" + REPORT), set(), set()),
    ]
    for name, body, expected, want_gaps in parse_cases:
        root = tempfile.mkdtemp(prefix="devteam-report-parse-")
        try:
            build(root, body)
            proc = subprocess.run([sys.executable, CHECK, root, "T-1"],
                                  capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (?!not evaluated: |excluded: )(\S+)", proc.stdout, re.M)}
            gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            want_rc = 1 if expected else (3 if want_gaps else 0)
            if got == expected and gaps == want_gaps and proc.returncode == want_rc:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'}, not evaluated "
                      f"{sorted(want_gaps) or 'nothing'}, exit {want_rc}")
                print(f"        got      {sorted(got) or 'clean'}, not evaluated "
                      f"{sorted(gaps) or 'nothing'}, exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

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

    CASES.extend([(c[0],) for c in parse_cases])
    CASES.extend([(c[0],) for c in blocking_cases])
    fp = (sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
          + sum(1 for c in budget_cases if c[0].startswith("fp-")))
    print(f"\ncheck_report control: {passed} passed, {failed} failed, "
          f"{len(CASES) + len(budget_cases)} cases ({fp} of them "
          f"false-positive controls, "
          f"{100 * fp // (len(CASES) + len(budget_cases))}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
