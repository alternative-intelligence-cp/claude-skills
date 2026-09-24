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


CLAIMED_TITLE = re.compile(r"^# (T-\d+) — .*? — RUNNING \(since [^,()]+, ([^\s,()]+)\)$", re.M)
FLIGHT_HEAD = ("| Task | Title | Agent label | Agent id | Sandbox | Since | Model | Scope | Note |\n"
               "|---|---|---|---|---|---|---|---|---|\n")


def flight(*claims, note="running"):
    """A board whose in-flight table carries each (task, label): the claim, as
    the claim protocol writes it and as check_scope anchors a window at it
    (roadmap 0.3.2, L-2.5)."""
    rows = "".join(f"| {t} | a task | {label} | `a1b2c3` | — | 2026-09-03 12:00 | opus-5-5 | — | "
                   f"{note} |\n" for t, label in claims)
    return ("# The board\n\n## In flight\n\n" + FLIGHT_HEAD
            + (rows or "| — | — | — | — | — | — | — | — | nothing running |\n"))


BASE = {
    "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", ["src/loader/", "tests/loader/"]),
    "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/render/", "tests/render/"]),
}

# PRICELOG T-19'S RESTART (F-135). The supervisor stops; the manager commits
# into the task's file three times while it is stopped, as `run` §4.3 asks
# before a re-dispatch (95bcb33, 4f56a7a and 8ba93ad); the manager re-claims
# under a new label (7a87cf8); the new supervisor sets the title.
T1 = lambda status, notes="": task("T-1", status, ["src/loader/", "tests/loader/"]) + notes
HELD = "NEEDS-DECISION (2026-09-18, the residue exceeds what D-53 allowed)"
STOPPED = [
    ("T-1: title NEEDS-DECISION", [("devteam/tasks/T-1.md", T1(HELD))]),
    ("questions: Q-40 and Q-41 -- T-1's verifier FAILs",
     [("devteam/tasks/T-1.md", T1(HELD, "\n- Q-40 and Q-41 raised.\n"))]),
    ("plan: T-1's fourth step", [("devteam/tasks/T-1.md", T1(HELD, "\n- Q-40 and Q-41 raised.\n"
                                                                    "- S-4 planned.\n"))]),
    ("plan: T-1 Gate point 3 read on the disclosure branch",
     [("devteam/tasks/T-1.md", T1(HELD, "\n- Q-40 and Q-41 raised.\n- S-4 planned.\n"
                                        "- Gate point 3 read.\n"))]),
]
RECLAIMED = ("board: claim T-1 (T1-disclose-1934) -- its restart under run §9a",
             [("devteam/BOARD.md", flight(("T-1", "T1-disclose-1934"), ("T-2", "T2-b-1210")))])
RESTARTED = ("T-1: title RUNNING (since 2026-09-18, T1-disclose-1934)",
             [("devteam/tasks/T-1.md", T1("RUNNING (since 2026-09-18, T1-disclose-1934)",
                                          "\n- Q-40 and Q-41 raised.\n- S-4 planned.\n"
                                          "- Gate point 3 read.\n"))])
# Two tasks planned, and claimed in one commit whose subject no claim pattern
# reads for both: pricelog's `board: claim T-3 and T-2` (4dfc033) and `plan
# T-17 and claim T-15` (5207c90).
PLANNED = {"T-2": task("T-2", "PLANNED", ["src/render/"]),
           "T-3": task("T-3", "PLANNED", ["src/store/"])}
TITLED = lambda t, label, scope: (f"{t}: title RUNNING", [(f"devteam/tasks/{t}.md", task(
    t, f"RUNNING (since 2026-09-10, {label})", [scope]))])

CASES = [
    ("clean", BASE, None, [], set()),

    # --- unparseable-scope-entry: a grant the checker cannot read ---------
    # This grammar failed PERMISSIVELY: an entry with its reason inline was
    # skipped in silence, so a file declaring eleven paths was parsed as nine
    # and two granted paths sat outside the task's scope for its whole run.
    ("unparseable-scope-entry",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)",
                          ["src/loader/"]).replace(
         "  - `src/loader/`", "  - `src/loader/`\n  - `src/extra/` — for the sweep")},
     None, [], {"unparseable-scope-entry"}),
    # ...and prose AFTER the list is not a list item, so it must stay quiet --
    # every task file has explanatory text under its fields.
    ("fp-prose-after-the-scope-list-is-not-an-entry",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)",
                          ["src/loader/"]).replace(
         "- **Gate.**", "The loader is granted because it owns the dialect.\n\n- **Gate.**")},
     None, [], set()),

    # --- foreign-write: a write by somebody who is not in this run ---------
    # The guard no longer refuses a session outside the run, so this finding
    # is what replaces that refusal. Every case below is (…, dirty=[…]) --
    # written after the last commit and never staged.
    ("foreign-write",
     BASE, None, [], {"foreign-write"}, "T-1: the work", (),
     [("other/thing.py", "written by nobody in this run\n")]),
    ("foreign-write-untracked-file",
     BASE, None, [], {"foreign-write"}, "T-1: the work", (),
     [("src/other/new.py", "brand new\n")]),
    # THE COLLAPSE HAZARD, and it fired on the first run. Plain `--porcelain`
    # reports an untracked directory as its shortest prefix, so this new file
    # came back as `src/` -- outside every scope -- and the check accused the
    # run's own worker of being a stranger. `-uall` is what makes it a path.
    ("fp-untracked-file-inside-a-live-scope-is-not-collapsed",
     BASE, None, [], set(), "T-1: the work", (),
     [("src/loader/new/x.py", "a worker creating a subdirectory\n")]),
    # ...and the three ways it must stay quiet. A worker mid-step leaves its
    # own scope dirty constantly; the run writes devteam/ constantly; and with
    # nothing claimed there is no run to be foreign to.
    ("fp-dirty-inside-a-live-scope-is-a-worker-mid-step",
     BASE, None, [], set(), "T-1: the work", (),
     [("src/loader/a.py", "half a step\n")]),
    ("fp-dirty-inside-devteam-is-the-run-itself",
     BASE, None, [], set(), "T-1: the work", (),
     [("devteam/RECORD.md", "the manager writing its record\n")]),
    ("fp-dirty-with-no-live-claim-is-not-foreign-to-anything",
     {**BASE, "T-1": task("T-1", "DONE (2026-09-03)", ["src/loader/", "tests/loader/"]), "T-2": task("T-2", "DONE (2026-09-03)", ["src/render/"])}, None, [], set(), "T-1: the work", (),
     [("other/thing.py", "nothing is claimed\n")]),

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

    # F-17: the manager ran `git add -A` while a worker was mid-file, and the
    # worker's in-flight code landed in the manager's commit under the
    # manager's message. The step lost its commit and the write became
    # invisible to scope attribution.
    ("misattributed-write-steals-a-live-tasks-work",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: backfill sensitivity on the digests"),

    # F-19: the claim anchor was the NEWEST match for a literal phrase, so a
    # commit merely QUOTING that phrase became the anchor, collapsed the span
    # and switched the check off. An integrity check disabled by writing about
    # it — the act of documenting the bug was the act of hiding it.
    ("misattribution-survives-a-commit-quoting-the-anchor-phrase",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: an unrelated backfill",
     [("docs: explain that a title reads RUNNING (since <date>, <label>)", [])]),

    # F-20: the task-file carve-out routed devteam/tasks/T-n.md past the skip
    # and then tested it against a declared scope that never contains it, so
    # it could not fire — and a manager sweeping a supervisor's task file went
    # unreported.
    ("misattributed-write-on-the-tasks-own-file",
     BASE, None, [("devteam/tasks/T-1.md", BASE["T-1"] + "\nswept\n")],
     {"misattributed-write"}, "research: an unrelated backfill"),

    # A commit SUBJECTED as a re-claim is not one. The claim is the label on
    # the board, so a `board: re-claim T-1` commit carrying no new label
    # moves nothing, and a write before it is still in the window.
    ("misattribution-before-a-re-claim-subject-with-no-new-label-is-still-found",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: an unrelated backfill",
     [("board: re-claim T-1", [("devteam/BOARD.md", "| T-1 | CLAIMED again |\n")])]),
    ("misattribution-found-after-a-re-claim-subject-with-no-new-label",
     BASE, None, [("devteam/BOARD.md", "| T-1 | CLAIMED |\n")], {"misattributed-write"},
     "board: re-claim T-1",
     [("chore: unrelated", [("src/loader/b.py", "y=2\n")])]),

    # --- the current claim (roadmap 0.3.2, L-2.5) ------------------------------
    # F-135, pricelog T-19's restart: the manager's three commits into the
    # stopped task's file precede the claim under its new label, and none is
    # judged. The owner's answer of 2026-09-24: current claim only. Before
    # 0.3.2 the window opened at the first claim, and all three were reported.
    ("f135-a-restarts-stop-edits-are-not-judged",
     BASE, None, [], set(), None, STOPPED + [RECLAIMED, RESTARTED]),
    # ...and what the class is for, inside the current claim: a commit naming
    # no task, into the scope, after the re-claim and before its worker's.
    ("f135-a-write-after-the-re-claim-is-still-judged",
     BASE, None, [], {"misattributed-write"}, None,
     STOPPED + [RECLAIMED, ("research: a backfill", [("src/loader/a.py", "x=1\n")]), RESTARTED]),
    # F-48's shape, which this reverses by the owner's answer: a write into the
    # scope made while the task was stopped, then a claim under a new label.
    # It was reported at every later commit; it is now judged by nothing here,
    # and CHECKS.md says so. The gate names every path it commits and the hook
    # refuses every commit made around it, so the sweep that made this write
    # is refused where it is made.
    ("l25-a-write-while-stopped-falls-before-the-current-claim",
     BASE, None, [], set(), None,
     STOPPED[:1] + [("research: a backfill", [("src/loader/a.py", "x=1\n")]),
                    RECLAIMED, RESTARTED]),
    # THE ANCHORS PRICELOG WROTE. Its claims were subjected `board: claim T-3
    # and T-2` and `plan T-17 and claim T-15`, and each anchors at its commit:
    # a write into T-2's scope between the claim and the title is judged. The
    # old window missed both subjects and opened at the title instead.
    ("anchor-board-claim-t3-and-t2-anchors-at-its-commit",
     PLANNED, None, [], {"misattributed-write"}, None,
     [("board: claim T-3 and T-2", [("devteam/BOARD.md", flight(("T-3", "T3-store-1301"),
                                                                ("T-2", "T2-render-1301")))]),
      ("research: a backfill", [("src/render/x.py", "x=1\n")]),
      TITLED("T-2", "T2-render-1301", "src/render/"), TITLED("T-3", "T3-store-1301", "src/store/")]),
    ("anchor-plan-t3-and-claim-t2-anchors-at-its-commit",
     PLANNED, None, [], {"misattributed-write"}, None,
     [("plan T-3 and claim T-2", [("devteam/BOARD.md", flight(("T-2", "T2-render-0643")))]),
      ("research: a backfill", [("src/render/x.py", "x=1\n")]),
      TITLED("T-2", "T2-render-0643", "src/render/")]),
    ("fp-anchor-a-write-before-the-claim-is-not-judged",
     PLANNED, None, [], set(), None,
     [("research: a backfill", [("src/render/x.py", "x=1\n")]),
      ("board: claim T-3 and T-2", [("devteam/BOARD.md", flight(("T-3", "T3-store-1301"),
                                                                ("T-2", "T2-render-1301")))]),
      TITLED("T-2", "T2-render-1301", "src/render/"), TITLED("T-3", "T3-store-1301", "src/store/")]),
    # The claim commit is the window's edge, and a manager's claim that writes
    # the title too (pricelog 9749e60) is not judged by its own window.
    ("fp-the-claim-commit-itself-is-not-judged",
     PLANNED, None, [], set(), None,
     [("board: claim T-2", [("devteam/BOARD.md", flight(("T-2", "T2-render-1301"))),
                            ("devteam/tasks/T-2.md", task(
                                "T-2", "RUNNING (since 2026-09-10, T2-render-1301)", ["src/render/"]))])]),
    # The FIRST commit carrying the label, not the newest: the manager edits
    # the board for other tasks while a claim is held, and a write before that
    # edit is still inside the claim.
    ("misattribution-before-a-later-board-commit-is-still-found",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: an unrelated backfill",
     [("board: a note on T-2", [("devteam/BOARD.md", flight(("T-1", "T1-a-1200"), ("T-2", "T2-b-1210"),
                                                           note="a note"))])]),
    # A task's own commit and another task's are skipped, as before.
    ("fp-another-tasks-commit-into-a-live-scope-is-its-own-not-a-misattribution",
     BASE, None, [("src/loader/a.py", "x=1\n")], set(), "T-2: a stray write"),

    # NO ANCHOR: the window is a part not evaluated, as it was when no claim
    # commit could be found. A title with no label -- pricelog T-9's, written
    # by the manager -- names no claim.
    ("no-anchor-a-running-title-with-no-label",
     {**BASE, "T-1": T1("RUNNING (re-dispatched 2026-09-11, after verify FAIL)")},
     None, [], set(), "T-1: the work", (), (), {"misattributed-write for T-1"}),
    # A label the board never carried: pricelog T-5's title said T5-restart-0853
    # and its board T5-harness-restart-0730.
    ("no-anchor-a-label-no-board-commit-carries",
     {**BASE, "T-1": T1("PLANNED")}, None, [], set(), None,
     [("board: T-1 restarted", [("devteam/BOARD.md", flight(("T-1", "T1-harness-restart-0730"),
                                                            ("T-2", "T2-b-1210")))]),
      ("T-1: restarted", [("devteam/tasks/T-1.md", T1("RUNNING (since 2026-09-10 08:53, T1-restart-0853)"))])],
     (), {"misattributed-write for T-1"}),
    # The label on the task's own row, in the label column, and nowhere else.
    ("no-anchor-the-label-on-another-tasks-row",
     {**BASE, "T-1": T1("PLANNED")}, None, [], set(), None,
     [("board: claim", [("devteam/BOARD.md", flight(("T-2", "T1-a-1200")))]),
      ("T-1: title RUNNING", [("devteam/tasks/T-1.md", T1("RUNNING (since 2026-09-03, T1-a-1200)"))])],
     (), {"misattributed-write for T-1"}),
    ("no-anchor-the-label-outside-the-label-column",
     {**BASE, "T-1": T1("PLANNED")}, None, [], set(), None,
     [("board: claim", [("devteam/BOARD.md", flight(("T-1", "T1-other-0000"), ("T-2", "T2-b-1210"),
                                                     note="was T1-a-1200"))]),
      ("T-1: title RUNNING", [("devteam/tasks/T-1.md", T1("RUNNING (since 2026-09-03, T1-a-1200)"))])],
     (), {"misattributed-write for T-1"}),
    # A title is read as FORMATS writes it, `RUNNING (since <date>, <label>)`,
    # and nothing after it: pricelog T-14's `…, T14-onehost-1518, D-31 grant)`
    # names no claim, though the board carries the label.
    ("no-anchor-a-title-with-a-reason-after-its-label",
     BASE, None, [], set(), None,
     [("T-1: reopened under D-31", [("devteam/tasks/T-1.md", T1(
         "RUNNING (since 2026-09-03, T1-a-1200, D-31 grant)"))])],
     (), {"misattributed-write for T-1"}),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    ("fp-another-tasks-file-is-the-managers-not-a-misattribution",
     BASE, None, [("devteam/RECORD.md", "- entry\n")], set(),
     "record: a manager entry"),
    ("fp-the-tasks-own-commit-is-not-misattributed",
     BASE, None, [("src/loader/a.py", "x=1\n")], set(), "T-1: the work"),
    ("fp-a-step-commit-is-not-misattributed",
     BASE, None, [("src/loader/a.py", "x=1\n")], set(), "T-1.S-2: the step"),
    ("fp-a-manager-commit-touching-only-devteam-is-fine",
     BASE, None, [("devteam/RECORD.md", "- an entry\n")], set(),
     "record: a manager entry"),
    ("fp-a-foreign-commit-outside-every-live-scope-is-fine",
     BASE, None, [("docs/guide.md", "hi\n")], set(), "docs: unrelated"),
    # From the first real dispatch: the manager's own board and plan commits
    # mention the task in their message, and were being charged to it.
    # A board commit touches devteam/, not a worker's files — writing src/ in a
    # commit called "board: claim T-1" is the F-17 misattribution, not this.
    ("fp-manager-commits-mentioning-a-task-are-not-its-writes",
     BASE, "T-1", [("devteam/BOARD.md", "| T-1 | CLAIMED |\n")], set(),
     "board: claim T-1"),
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

    # --- zero rows, partial reads and wrapped fields (roadmap 0.3.1, L-1.3) --
    # The ninth element names the parts expected NOT EVALUATED. Each case
    # here used to report clean.
    #
    # ZERO ROWS: no title parses, so no task is in any comparison -- and both
    # are RUNNING, over intersecting scopes.
    ("zero-rows-no-title-parses",
     {"T-1": task("T-1", "RUNNING (since x, y)", ["src/"]).replace("# T-1 — a task — ", "# T-1 a task "),
      "T-2": task("T-2", "RUNNING (since x, y)", ["src/"]).replace("# T-2 — a task — ", "# T-2 a task ")},
     None, [], set(), "T-1: the work", (), (), {"tasks/T-1.md's title", "tasks/T-2.md's title"}),
    # A PARTIAL READ: one task dropped, and with it the overlap it has.
    ("partial-read-one-title-does-not-parse",
     {**BASE, "T-3": task("T-3", "RUNNING (since x, y)", ["src/loader/"]).replace(
         "# T-3 — a task — ", "# T-3: a task — ")},
     None, [], set(), "T-1: the work", (), (), {"tasks/T-3.md's title"}),
    # A live task with nothing in history to anchor its claim window: its
    # RUNNING title is in the working tree only.
    ("partial-read-a-live-task-with-no-claim-anchor",
     {**BASE, "T-1": task("T-1", "PLANNED", ["src/loader/"])},
     None, [], set(), "T-1: the work", (),
     [("devteam/tasks/T-1.md", task("T-1", "RUNNING (since x, y)", ["src/loader/"]))],
     {"misattributed-write for T-1"}),
    # A worker's step commit missing its colon is not attributed to the task.
    # Inside the live scope it is already `misattributed-write`, correctly;
    # the gap names why the task's own attribution never read it.
    ("partial-read-a-step-commit-without-its-colon",
     BASE, "T-1", [("src/loader/a.py", "x=1\n")], {"misattributed-write"}, "T-1.S-2 the work",
     (), (), {"undeclared-write for T-1"}),
    # A CONTINUED FIELD IS READ WHOLE (roadmap 0.3.2, L-2.3). A value written
    # beside `Scope.` is one entry, read across the lines that continue it, and
    # one entry is one path. 0.3.1 read the first line and named the rest as
    # not evaluated; read whole, this is two paths in one entry, so it declares
    # nothing -- and T-1 is RUNNING with no scope at all.
    ("continued-an-inline-scope-is-read-whole-and-is-not-one-path",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", []).replace(
         "- **Scope.**\n", "- **Scope.** `src/loader/`,\n  `tests/loader/`\n")},
     None, [], {"unparseable-scope-entry", "empty-scope"}),
    # One path with a note on the next line: its first line alone reads as a
    # path, and the value it is part of does not.
    ("continued-an-inline-scope-with-a-note-on-its-next-line-is-not-one-path",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", []).replace(
         "- **Scope.**\n", "- **Scope.** `src/loader/`\n  (and its tests)\n")},
     None, [], {"unparseable-scope-entry", "empty-scope"}),
    # ...and a sentence beside the field, on one line, is not a path either. It
    # used to be kept as an entry that matched nothing, and declared nothing
    # while every check said clean.
    ("unparseable-scope-entry-a-sentence-beside-the-field",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", ["tests/loader/"]).replace(
         "- **Scope.**\n", "- **Scope.** the loader and its tests\n")},
     None, [], {"unparseable-scope-entry"}),
    # ONE PATH BESIDE THE FIELD IS ONE ENTRY, and it is read: the overlap with
    # T-2 is found through it.
    ("overlapping-scope-through-a-path-written-beside-the-field",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", []).replace(
         "- **Scope.**\n", "- **Scope.** `src/render/`\n")},
     None, [], {"overlapping-scope"}),
    # ...and what must stay CLEAN.
    #
    # A GENUINELY EMPTY SOURCE: nothing planned yet, only the directory's
    # README -- which is not a task and offers no title.
    ("fp-no-task-files-yet-is-clean",
     {"README": "# Tasks\n\nOne file per task, named `T-1.md`.\n"}, None, [], set()),
    # A MULTI-LINE LIST FIELD THIS CHECK READS WHOLE.
    ("fp-a-long-scope-list-is-read-whole",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)",
                          ["src/loader/", "src/loader_util/", "tests/loader/", "docs/loader.md"])},
     None, [], set()),
    # The manager's own topic commit names the task and is not the task's
    # (pricelog has five: `T-10 DONE, verified PASS -- …`).
    ("fp-a-manager-topic-commit-is-not-a-stray",
     BASE, "T-1", [("devteam/RECORD.md", "the manager's entry\n")], set(),
     "T-1 DONE, verified PASS"),
    # A step's heading is not a title: a notes file in tasks/ quoting one
    # offers no task. (The title shape is consulted only where a file's own
    # title failed, so the heading has to be in a file with none.)
    ("fp-a-step-heading-in-a-notes-file-is-not-a-title",
     {**BASE, "notes": "# Notes\n\n# T-1.S-2 adversarial pass\n\nProse.\n"}, None, [], set()),
    # --- untracked files (roadmap 0.3.1, L-1.4) ----------------------------
    # A new task in no commit is read -- its overlap with T-1 is found -- and
    # named. With no claim in history, its window is a part not evaluated.
    ("untracked-file-a-new-task-is-read-and-named",
     BASE, None, [], {"untracked-file", "overlapping-scope"}, "T-1: the work", (),
     [("devteam/tasks/T-3.md", task("T-3", "RUNNING (since x, y)", ["src/loader/"]))],
     {"misattributed-write for T-3"}),
    ("fp-an-ignored-task-file-produces-nothing",
     BASE, None, [], set(), "T-1: the work", (),
     [("devteam/.gitignore", "tasks/T-9.md\n"),
      ("devteam/tasks/T-9.md", task("T-9", "RUNNING (since x, y)", ["src/loader/"]))]),
    # An inline value FOLLOWED BY LIST ITEMS is not a wrap: the items are read.
    ("fp-an-inline-scope-with-list-items-under-it",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", []).replace(
         "- **Scope.**\n", "- **Scope.** `src/loader/`\n  - `tests/loader/`\n")},
     None, [], set()),
]


def build_more(root, msg, files):
    """One more commit on the checked-out line: `files` written, then everything."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for rel, body in files:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True, env=env)
    subprocess.run(["git", "-C", root, "commit", "-q", "--allow-empty", "-m", msg],
                   capture_output=True, env=env)


def build(root, tasks, writes, subject="T-1: the work", later=(), dirty=()):
    dt = os.path.join(root, "devteam", "tasks")
    os.makedirs(dt, exist_ok=True)
    for ident, body in tasks.items():
        with open(os.path.join(dt, f"{ident}.md"), "w", encoding="utf-8") as fh:
            fh.write(body)
    # THE CLAIM IS IN THE FIXTURE'S FIRST COMMIT: an in-flight row for every
    # task whose title names a claim label, so each window opens there, as
    # the claim commit opens it. A case that builds its own board writes it in
    # a later commit.
    with open(os.path.join(root, "devteam", "BOARD.md"), "w", encoding="utf-8") as fh:
        fh.write(flight(*(m.groups() for body in tasks.values()
                          for m in CLAIMED_TITLE.finditer(body))))
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
    for msg, more in later:
        build_more(root, msg, more)
    # Written AFTER every commit and never staged. `foreign-write` is the one
    # finding about the working tree rather than history, so it is the one
    # thing this harness could not express -- every fixture committed
    # everything, which is why the check passed 27 cases without once firing.
    for rel, body in dirty:
        f = os.path.join(root, rel)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(body)
    return root


def main():
    passed = failed = 0
    for case in CASES:
        name, tasks, task_id, writes, expected = case[:5]
        subject = case[5] if len(case) > 5 else "T-1: the work"
        later = case[6] if len(case) > 6 else ()
        dirty = case[7] if len(case) > 7 else ()
        want_gaps = case[8] if len(case) > 8 else set()
        root = tempfile.mkdtemp(prefix="devteam-scope-")
        try:
            build(root, tasks, writes, subject, later, dirty)
            argv = [sys.executable, CHECK, root] + ([task_id] if task_id else [])
            proc = subprocess.run(argv, capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (?!not evaluated: |excluded: )(\S+)", proc.stdout, re.M)}
            got_gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            want_exit = 1 if expected else (3 if want_gaps else 0)
            if got == expected and got_gaps == want_gaps and proc.returncode == want_exit:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} "
                      f"not evaluated {sorted(want_gaps) or 'none'} exit {want_exit}")
                print(f"        got      {sorted(got) or 'clean'} "
                      f"not evaluated {sorted(got_gaps) or 'none'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- accepted findings (roadmap 0.3.1, L-1.6) --------------------------
    # `undeclared-write` is evaluated only for the task a run names, so only
    # that run may apply an acceptance of it or call one stale. The `fp-`
    # cases fail if every run judged every acceptance: a run naming no task,
    # or naming another, would call T-1's acceptance stale though neither
    # looked at T-1's commits.
    decisions = lambda *items: ("# Decisions\n\n### D-1 — what stands as it is\n\n"
                                "- **Decision.** it stands.\n- **Supersedes.** none\n"
                                "- **Reviewed.** unreviewed\n- **Accepts.**\n"
                                + "".join(f"  - {i}\n" for i in items))
    empty = {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", [])}
    a_empty = "`check_scope` `empty-scope` `tasks/T-2.md` — T-2 is RUNNING and declares no scope"
    stray = [("src/loader/a.py", "x=1\n"), ("src/render/b.py", "y=2\n")]
    a_stray = ("`check_scope` `undeclared-write` `tasks/T-1.md` — T-1 committed src/render/b.py, "
               "which its scope does not cover")
    accept_cases = [
        # (name, tasks, writes, run for, acceptances, exit, findings, accepted)
        ("accepted-finding-exits-0-and-is-named",
         empty, [], None, [a_empty], 0, set(), {("D-1", "empty-scope")}),
        ("a-fixed-finding-leaves-its-acceptance-stale",
         BASE, [], None, [a_empty], 1, {"stale-acceptance"}, set()),
        ("an-undeclared-write-is-accepted-in-its-tasks-run",
         BASE, stray, "T-1", [a_stray], 0, set(), {("D-1", "undeclared-write")}),
        ("an-undeclared-write-fixed-leaves-its-acceptance-stale-in-its-tasks-run",
         BASE, [], "T-1", [a_stray], 1, {"stale-acceptance"}, set()),
        ("fp-a-run-naming-no-task-does-not-judge-an-undeclared-write-acceptance",
         BASE, [], None, [a_stray], 0, set(), set()),
        ("fp-another-tasks-run-does-not-judge-it",
         BASE, stray, "T-2", [a_stray], 0, set(), set()),
    ]
    for name, tasks, writes, task_id, items, want_rc, expected, want_acc in accept_cases:
        root = tempfile.mkdtemp(prefix="devteam-scope-accept-")
        try:
            os.makedirs(os.path.join(root, "devteam"))
            with open(os.path.join(root, "devteam", "DECISIONS.md"), "w", encoding="utf-8") as fh:
                fh.write(decisions(*items))
            build(root, tasks, writes)
            argv = [sys.executable, CHECK, root] + ([task_id] if task_id else [])
            proc = subprocess.run(argv, capture_output=True, text=True)
            out = proc.stdout
            got = set(re.findall(r"^  (?!not evaluated: |excluded: |accepted by )(\S+)", out, re.M))
            got_acc = set(re.findall(r"^  accepted by (D-\d+): (\S+)", out, re.M))
            if proc.returncode == want_rc and got == expected and got_acc == want_acc:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected exit {want_rc} {sorted(expected) or 'clean'} "
                      f"accepted {sorted(want_acc) or 'none'}")
                for line in (out + proc.stderr).strip().split("\n")[:8]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
    CASES.extend([(c[0],) for c in accept_cases])

    # AN ARGUMENT NAMING NO TASK IS COULD-NOT-RUN (L-1.1), and it used to be
    # a traceback: check() returned a bare list where main() unpacks a tuple.
    root = tempfile.mkdtemp(prefix="devteam-scope-")
    try:
        build(root, BASE, [])
        proc = subprocess.run([sys.executable, CHECK, root, "T-9"], capture_output=True, text=True)
        if proc.returncode == 2 and "Traceback" not in proc.stderr and "T-9" in proc.stderr:
            passed += 1
        else:
            failed += 1
            print("FAIL  a-task-id-naming-no-task-is-could-not-run")
            for line in (proc.stdout + proc.stderr).strip().split("\n")[-4:]:
                print(f"        | {line}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    CASES.append(("a-task-id-naming-no-task-is-could-not-run",))

    # --- a checkout of one commit (roadmap 0.3.1, L-1.5) -------------------
    # `--at-commit` excludes the classes that read the working state, by the
    # caller's declaration, and names each. So a file written outside every live scope -- which a clean
    # checkout of a commit never holds -- is a finding without the flag, and
    # with it is excluded, named, and leaves the rest to decide the exit.
    root = tempfile.mkdtemp(prefix="devteam-scope-")
    try:
        build(root, BASE, [], dirty=[("other/thing.py", "x = 1\n")])
        live = subprocess.run([sys.executable, CHECK, root], capture_output=True, text=True)
        at = subprocess.run([sys.executable, CHECK, root, "--at-commit"], capture_output=True, text=True)
        ok = (live.returncode == 1 and re.search(r"^  foreign-write\s", live.stdout, re.M)
              and at.returncode == 0 and not re.search(r"^  foreign-write\s", at.stdout, re.M)
              and re.search(r"^  excluded: foreign-write — by --at-commit", at.stdout, re.M))
        if ok:
            passed += 1
        else:
            failed += 1
            print("FAIL  at-commit-excludes-the-working-state-and-names-it")
            for line in (live.stdout + at.stdout + at.stderr).strip().split("\n")[:8]:
                print(f"        | {line}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    CASES.append(("at-commit-excludes-the-working-state-and-names-it",))

    # --- HEAD's history, not `--all` (roadmap 0.3.2, L-2.6) ----------------
    # A commit on another branch, or under `refs/devteam/sandbox/` where a
    # promotion stopped on a conflict leaves an unpromoted worker's commits,
    # is not the task's write until it is in HEAD's history. And a claim made
    # only on another branch anchors nothing on this one.
    def aside(root, subject, files, ref=None):
        """Commit on a side line, point `ref` (or a branch) at it, and return."""
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, env=env)
        run("checkout", "-q", "--detach")
        for rel, body in files:
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
        run("add", "-A")
        run("commit", "-qm", subject)
        run("update-ref", ref or "refs/heads/side", "HEAD")
        run("checkout", "-q", "main")
    for name, ref, task_id, files, tasks, later, want_rc, want in (
            ("l26-a-branch-commit-under-the-tasks-prefix-is-not-its-write", None, "T-1",
             [("src/render/b.py", "y=2\n")], BASE, (), 0, None),
            ("l26-a-sandbox-ref-commit-under-the-tasks-prefix-is-not-its-write",
             "refs/devteam/sandbox/T-1-S-2-123456", "T-1", [("src/render/b.py", "y=2\n")], BASE, (),
             0, None),
            # The claim made on another branch only: this line's title names it
            # and no board in HEAD's history carries it.
            ("l26-a-claim-on-another-branch-anchors-nothing-here", None, None,
             [("devteam/BOARD.md", flight(("T-1", "T1-side-0900"), ("T-2", "T2-b-1210")))],
             {**BASE, "T-1": T1("PLANNED")},
             [("T-1: title RUNNING", [("devteam/tasks/T-1.md",
                                       T1("RUNNING (since 2026-09-03, T1-side-0900)"))])],
             3, "misattributed-write for T-1")):
        root = tempfile.mkdtemp(prefix="devteam-scope-")
        try:
            build(root, tasks, [])
            aside(root, "T-1: a stray write" if task_id else "board: claim T-1 (T1-side-0900)",
                  files, ref)
            for msg, more in later:
                build_more(root, msg, more)
            argv = [sys.executable, CHECK, root] + ([task_id] if task_id else [])
            proc = subprocess.run(argv, capture_output=True, text=True)
            ok = (proc.returncode == want_rc and "undeclared-write" not in proc.stdout
                  and (want is None or f"not evaluated: {want} — no commit in HEAD's history"
                       in proc.stdout))
            if ok:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}\n        exit {proc.returncode}, wanted {want_rc}")
                for line in (proc.stdout + proc.stderr).strip().split("\n")[:6]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
        CASES.append((name,))
    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\ncheck_scope control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
