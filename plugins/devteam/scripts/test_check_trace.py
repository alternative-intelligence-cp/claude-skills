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

def _template_rows():
    """The constraint rows the current template declares."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import check_trace
    return check_trace.CHARTER_ROWS


# The constraints table is generated from the CURRENT template rather than
# typed out, so this fixture cannot itself go stale the way the artifact it is
# testing does. A hand-written table here would need editing every time the
# template gained a row -- and the case that catches a missing row would be the
# first to break, quietly, in exactly the direction that hides the defect.
_ROWS = "\n".join(f"| {r} | fixture |" for r in _template_rows())

CHARTER = f"""# Charter — Fixture

## Goals

- **G-1** — the thing works
- **G-2** — the thing is documented

## Constraints

| Constraint | Value |
|---|---|
{_ROWS}
"""

REQS = """# Requirements

### R-1 — it works

- **Statement.** the thing works when run.
- **Satisfies.** G-1
- **Source.** interview 2026-09-03
- **Acceptance.** `make test` → `ok`
- **Requires-write.**
  - `src/`
- **Priority.** must
- **Status.** open

### R-2 — it is documented

- **Statement.** a README explains how to run it.
- **Satisfies.** G-2
- **Source.** interview 2026-09-03
- **Acceptance.** `test -s README.md`
- **Requires-write.**
  - `README.md`
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
- **Requires-write.**
  - `src/`
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
- **Estimate.** tokens=100 minutes=5
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
    # F-10: at the onboarding gate no task exists, so every requirement is
    # uncovered by construction and a plain run can never exit 0.
    ("fp-pre-plan-suppresses-uncovered-requirement",
     {"tasks/T-1.md": None, "tasks/T-2.md": None}, set(), ["--pre-plan"]),
    ("uncovered-requirement-without-the-flag",
     {"tasks/T-1.md": None, "tasks/T-2.md": None}, {"uncovered-requirement"}),
    ("pre-plan-still-reports-an-orphan-goal",
     {"CHARTER.md": CHARTER + "- **G-3** — the thing is fast\n"},
     {"orphan-scope"}, ["--pre-plan"]),
    # F-14: the plan skill demands the riskiest unknown as "task one, and it is
    # small", and a probe discharges nothing by definition — so the check made
    # the thing the skill demands unexpressible.
    # Same class as the research index's silent skip: a task file whose title
    # will not parse is invisible, and its requirements read as uncovered with
    # nothing naming the file.
    # T-2 is dropped so the case isolates ONE fault. Left in, its dependency on
    # the now-invisible T-1 correctly reports unknown-reference too — accurate,
    # but a consequence rather than a second fault.
    ("unparseable-task",
     {"tasks/T-1.md": "# T-1 the word counter (no separators)\n\n- **Discharges.** R-1\n",
      "tasks/T-2.md": None},
     {"unparseable-task", "uncovered-requirement"}),
    ("fp-a-probe-discharges-nothing-and-is-fine",
     {"tasks/T-3.md": """# T-3 — is R-1 even achievable? — PLANNED

- **Kind.** probe
- **Informs.** R-1
- **Discharges.** none
- **Depends on.** none
- **Scope.**
  - `probe/`
- **Gate.** the question is answered either way.
- **Verify.** `test -s probe/FINDING.md`
- **Estimate.** tokens=100 minutes=5
"""}, set()),
    ("unjustified-probe-informs-nothing",
     {"tasks/T-3.md": """# T-3 — a probe about nothing — PLANNED

- **Kind.** probe
- **Discharges.** none
- **Depends on.** none
- **Scope.**
  - `probe/`
- **Gate.** g
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5
"""}, {"unjustified-task"}),
    ("unjustified-chore-gives-no-reason",
     {"tasks/T-3.md": """# T-3 — a chore — PLANNED

- **Kind.** chore
- **Because.** <why>
- **Discharges.** none
- **Depends on.** none
- **Scope.**
  - `tools/`
- **Gate.** g
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5
"""}, {"unjustified-task"}),
    ("bad-kind",
     {"tasks/T-3.md": """# T-3 — a task — PLANNED

- **Kind.** whatever
- **Discharges.** R-1
- **Depends on.** none
- **Scope.**
  - `x/`
- **Gate.** g
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5
"""}, {"bad-kind"}),
    ("fp-struck-requirement-needs-no-task",
     {"REQUIREMENTS.md": REQS + """
### R-3 — withdrawn idea

- **Statement.** it syncs to the cloud.
- **Satisfies.** G-1
- **Source.** interview
- **Acceptance.** n/a
- **Requires-write.**
  - `src/`
- **Priority.** may
- **Status.** struck (D-2)
"""},
     set()),
    # A task discharging several requirements must own every path they
    # exercise. The scope widens with the Discharges line -- it was not
    # widened here at first, and `unreachable-acceptance` caught the fixture
    # on its first run: T-1 claimed R-2 while owning only `src/`.
    ("fp-one-task-discharges-several",
     {"tasks/T-1.md": T1.replace("- **Discharges.** R-1", "- **Discharges.** R-1, R-2")
                        .replace("  - `src/`", "  - `src/`\n  - `README.md`"),
      "tasks/T-2.md": None},
     set()),

    # --- gate-omits-decision: a gate narrower than its requirement --------
    # The verifier reads the GATE and P-18 puts it last, so the asymmetry only
    # fails toward shipping less. Existential over the discharging tasks: the
    # per-task form was measured first at 14 findings to 1 real, because a
    # gate states what must be true and is not obliged to cite anything.
    ("gate-omits-decision",
     {"REQUIREMENTS.md": REQS.replace("- **Statement.** the thing works when run.",
                                      "- **Statement.** the thing works when run, per D-1.", 1)},
     {"gate-omits-decision"}),
    ("fp-gate-that-names-the-decision",
     {"REQUIREMENTS.md": REQS.replace("- **Statement.** the thing works when run.",
                                      "- **Statement.** the thing works when run, per D-1.", 1),
      "tasks/T-1.md": T1.replace("- **Gate.** the test command exits zero.",
                                 "- **Gate.** the test command exits zero, including D-1's Makefile.")},
     set()),
    # PARTIAL DISCHARGE MUST NOT DEFEAT IT. Two tasks share the requirement and
    # only the second carries the obligation; that is the pattern a real
    # project uses most, and the per-task form fired on all of it.
    ("fp-one-of-several-discharging-tasks-carries-the-obligation",
     {"REQUIREMENTS.md": REQS.replace("- **Statement.** the thing works when run.",
                                      "- **Statement.** the thing works when run, per D-1.", 1),
      "tasks/T-2.md": T2.replace("- **Discharges.** R-2", "- **Discharges.** R-1, R-2")
                        .replace("  - `README.md`", "  - `README.md`\n  - `src/`")
                        .replace("- **Gate.** the README exists and is non-empty.",
                                 "- **Gate.** the README exists, and D-1's Makefile is used.")},
     set()),
    # A requirement citing no decision gets no coverage and no warning. Stated
    # as a control so the limit is visible rather than discovered.
    ("fp-requirement-citing-no-decision-is-simply-not-covered",
     {}, set()),

    # --- re-litigated-requirement: a shape signal, not a defect -----------
    # Counting EVERY edit was measured first and flagged twelve of thirteen
    # requirements on a real project, because a status moving open ->
    # in-progress -> discharged is an edit too. Counting only Statement and
    # Acceptance isolated the one requirement that had actually cost seven
    # client stops.
    ("re-litigated-requirement",
     {"REQUIREMENTS.md": REQS.replace("the thing works when run.", "the thing works, v4.", 1)},
     {"re-litigated-requirement"}, [],
     [REQS,
      REQS.replace("the thing works when run.", "the thing works, v2.", 1),
      REQS.replace("the thing works when run.", "the thing works, v3.", 1)]),
    ("fp-two-semantic-amendments-is-under-the-threshold",
     {"REQUIREMENTS.md": REQS.replace("the thing works when run.", "the thing works, v3.", 1)},
     set(), [],
     [REQS, REQS.replace("the thing works when run.", "the thing works, v2.", 1)]),
    # THE CASE THAT KILLED THE NAIVE METRIC. Status churn is bookkeeping and
    # every requirement has it; it must not count.
    ("fp-status-churn-is-bookkeeping-not-re-litigation",
     {"REQUIREMENTS.md": REQS.replace("- **Status.** open", "- **Status.** discharged (T-1)", 1)},
     set(), [],
     [REQS,
      REQS.replace("- **Status.** open", "- **Status.** in-progress (T-1)", 1),
      REQS.replace("- **Status.** open", "- **Status.** in-progress (T-1, T-2)", 1)]),
    # ...and a shape review resets it, or a requirement could never clear this
    # by being rewritten, since rewriting it is another semantic change.
    ("fp-shape-reviewed-resets-the-count",
     {"REQUIREMENTS.md": REQS.replace("- **Priority.** must",
                                      "- **Shape reviewed.** 2026-09-04 (D-9)\n- **Priority.** must", 1)
                             .replace("the thing works when run.", "the thing works, v4.", 1)},
     set(), [],
     [REQS,
      REQS.replace("the thing works when run.", "the thing works, v2.", 1),
      REQS.replace("the thing works when run.", "the thing works, v3.", 1)]),

    # --- one-sided-link: both ends of the link, not just its existence -----
    # A scheduling decision reached the decision log and neither artifact:
    # three of thirteen requirements named a task that did not list them, and
    # it survived four closed tasks and every clean run.
    ("one-sided-link-from-the-requirement",
     {"REQUIREMENTS.md": REQS.replace("- **Status.** open", "- **Status.** in-progress (T-2)", 1)},
     {"one-sided-link"}),
    ("one-sided-link-from-the-task",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— RUNNING (since 2026-09-03, T1-a-1200)")},
     {"one-sided-link"}),
    # A PLANNED task has not started, so a requirement it will discharge is
    # correctly still `open`. Reporting that would fire on every plan the
    # moment it was drawn.
    ("fp-planned-task-leaves-its-requirement-open",
     {}, set()),
    ("fp-both-ends-agree",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— RUNNING (since 2026-09-03, T1-a-1200)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open", "- **Status.** in-progress (T-1)", 1)},
     set()),
    # A struck requirement is out of the graph entirely; linking it to a task
    # that still names it would report a decision the project already made.
    ("fp-struck-requirement-is-not-linked",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— RUNNING (since 2026-09-03, T1-a-1200)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open", "- **Status.** struck (D-2)", 1)},
     set()),

    # --- phase, not identity: the close is where the miss is permanent -----
    # `in-progress (T-6)` named T-6, so an identity test passed on a
    # requirement claiming to be under construction by a task that had
    # finished. Coverage was strongest at the claim, where a miss is loud, and
    # absent at the close, where it is permanent.
    ("one-sided-link-in-progress-under-a-finished-task",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** in-progress (T-1)", 1)},
     {"one-sided-link"}),
    ("fp-discharged-by-the-task-that-finished",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** discharged (T-1)", 1)},
     set()),
    # A requirement advanced by one task and completed by another is normal, so
    # a finished task may leave it `in-progress` -- naming a task that has NOT
    # finished. That distinction is the whole of why this is a relation.
    ("fp-finished-task-hands-on-to-an-unfinished-one",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "tasks/T-2.md": T2.replace("- **Discharges.** R-2", "- **Discharges.** R-1, R-2")
                        .replace("  - `README.md`", "  - `README.md`\n  - `src/`"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** in-progress (T-1, T-2)", 1)},
     set()),
    ("one-sided-link-handed-on-to-a-task-that-also-finished",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "tasks/T-2.md": T2.replace("— PLANNED", "— DONE (2026-09-03)")
                        .replace("- **Discharges.** R-2", "- **Discharges.** R-1, R-2")
                        .replace("  - `README.md`", "  - `README.md`\n  - `src/`"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** in-progress (T-1, T-2)", 1)
                             .replace("- **Status.** open",
                                      "- **Status.** discharged (T-2)", 1)},
     {"one-sided-link"}),

    # --- template-drift: the project against the PLUGIN --------------------
    # Every other check here diffs the project against itself, so an artifact
    # was instantiated once and diverged forever. A real charter was signed six
    # hours before two constraint rows entered the template and silently
    # lacked both for the rest of its life -- one of them the checkpoint
    # cadence, so no checkpoint ever fired.
    ("template-drift",
     {"CHARTER.md": CHARTER.replace("| Checkpoint cadence | fixture |\n", "")},
     {"template-drift"}),
    ("template-drift-several-rows",
     {"CHARTER.md": CHARTER.replace("| Checkpoint cadence | fixture |\n", "")
                           .replace("| Priority order | fixture |\n", "")},
     {"template-drift"}),
    # A row present but empty is the interview's problem, not the template's.
    # Reporting it here would put two different faults under one finding.
    ("fp-a-row-present-but-unfilled-is-not-drift",
     {"CHARTER.md": CHARTER.replace("| Priority order | fixture |",
                                    "| Priority order |  |")},
     set()),

    # --- unrecorded-amendment: the list a checker's author could tune -------
    # `Requires-write.` is half of what `unreachable-acceptance` compares, and
    # the planner who draws the other half can reach both. Superseding stays
    # allowed and is the point: it leaves a record naming a decision.
    # This is the gaming move exactly: narrowing the list until it fits the
    # scope. `unreachable-acceptance` goes GREEN on it -- `src/narrowed/` is
    # inside T-1's `src/` -- and only the history catches it. Which is the
    # argument for the check existing: the finding it is protecting cannot
    # protect itself.
    ("unrecorded-amendment",
     {"REQUIREMENTS.md": REQS.replace("- **Requires-write.**\n  - `src/`",
                                      "- **Requires-write.**\n  - `src/narrowed/`", 1)},
     {"unrecorded-amendment"}, [], REQS),
    ("fp-amendment-that-names-its-decision",
     {"REQUIREMENTS.md": REQS.replace("- **Requires-write.**\n  - `src/`",
                                      "- **Requires-write amended.** 2026-09-04 (D-3)\n"
                                      "- **Requires-write.**\n  - `src/deeper/`", 1)},
     set(), [], REQS),
    ("fp-unchanged-list-with-real-history",
     {}, set(), [], REQS),
    # A requirement that did not exist in the earlier commit has nothing to
    # have been amended FROM. Reporting one would make every requirement added
    # after planning look tampered with.
    ("fp-requirement-added-later-was-never-amended",
     {}, set(), [], REQS.split("### R-2")[0]),

    # --- unreachable-acceptance: the criterion's level vs the task's scope --
    # Three measured instances, all late-caught by a verifier running the
    # command end to end after the module task had closed.
    ("unreachable-acceptance",
     {"REQUIREMENTS.md": REQS.replace("- **Requires-write.**\n  - `src/`",
                                      "- **Requires-write.**\n  - `src/`\n  - `bin/cli.py`", 1)},
     {"unreachable-acceptance"}),
    # ...and the ways it must stay quiet.
    ("fp-requires-write-exactly-equal-to-the-scope",
     {"REQUIREMENTS.md": REQS.replace("- **Requires-write.**\n  - `README.md`",
                                      "- **Requires-write.**\n  - `README.md`", 1)},
     set()),
    ("fp-requires-write-a-file-inside-a-declared-directory",
     {"REQUIREMENTS.md": REQS.replace("- **Requires-write.**\n  - `src/`",
                                      "- **Requires-write.**\n  - `src/deep/nested/a.py`", 1)},
     set()),
    # An UNDERSTATED set must MISS, never invent. This is the property that
    # makes the check safe to add at all: it cannot misfire on an ordinary plan.
    ("fp-empty-requires-write-checks-nothing-rather-than-guessing",
     {"REQUIREMENTS.md": REQS.replace("- **Requires-write.**\n  - `src/`",
                                      "- **Requires-write.**\n  - `<paths>`", 1)},
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
- **Estimate.** tokens=100 minutes=5
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
- **Estimate.** tokens=100 minutes=5
""",
      "tasks/T-4.md": """# T-4 — b — PLANNED

- **Discharges.** R-2
- **Depends on.** T-2, T-3
- **Scope.**
  - `b/`
- **Gate.** b
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5
"""},
     set()),
    # The requirement statuses move WITH the task statuses. Leaving them `open`
    # while their tasks were DONE and RUNNING was incoherent, and passed only
    # because nothing compared the two ends -- which is the defect this
    # fixture now has to avoid rather than demonstrate.
    ("fp-running-and-done-tasks-still-trace",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "tasks/T-2.md": T2.replace("— PLANNED", "— RUNNING (since 2026-09-03, T2-rm-1400)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open", "- **Status.** discharged (T-1)", 1)
                             .replace("- **Status.** open", "- **Status.** in-progress (T-2)", 1)},
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


def build(root, overrides, prior=None):
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

    # `prior` is an EARLIER committed REQUIREMENTS.md, so the fixture's final
    # state is a modification with real history behind it. Without this the
    # harness could only build single-commit trees, in which first-declared
    # always equals current and `unrecorded-amendment` can never fire -- the
    # same blind spot the scope harness had, where every fixture committed
    # everything and the working-tree check could not be expressed at all.
    if prior is not None:
        # A LIST of earlier versions, not one: `unrecorded-amendment` needs a
        # single earlier commit, but semantic churn needs a sequence, and a
        # harness that can only build two versions cannot express a count.
        for i, version in enumerate([prior] if isinstance(prior, str) else prior):
            with open(os.path.join(dt, "REQUIREMENTS.md"), "w", encoding="utf-8") as fh:
                fh.write(version)
            for name in files:
                run("add", os.path.join("devteam", name))
            run("commit", "-qm", f"fixture (v{i})")
        with open(os.path.join(dt, "REQUIREMENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(files["REQUIREMENTS.md"])

    for name in files:
        run("add", os.path.join("devteam", name))
    run("commit", "-qm", "fixture")
    return dt


def main():
    passed = failed = 0
    for case in CASES:
        name, overrides, expected = case[:3]
        extra = case[3] if len(case) > 3 else []
        prior = case[4] if len(case) > 4 else None
        root = tempfile.mkdtemp(prefix="devteam-trace-")
        try:
            dt = build(root, overrides, prior)
            proc = subprocess.run([sys.executable, CHECK, *extra, dt],
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
    print(f"\ncheck_trace control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
