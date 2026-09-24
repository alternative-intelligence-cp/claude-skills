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
# THE SUBJECT IS OVERRIDABLE SO THAT MUTATION TESTING NEED NOT WRITE THE
# SHIPPED TREE. scripts/mutate.py used to apply each mutation to the real
# file and restore it in a `finally`, which is safe in time and not in the
# tree: a concurrent `git add -A` read check_plugin.py mid-mutation and
# shipped the defect, with this control green in the working tree the whole
# while. Two trees, one report. The window is now removed rather than
# declared -- mutate.py writes a mutated COPY and names it here.
CHECK = (os.environ.get("DEVTEAM_SUBJECT_CHECK_TRACE")
        or os.path.join(HERE, "check_trace.py"))

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


# --- open-finding-at-close (0.2.6) ---------------------------------------
# P-31 puts the audit BEFORE the close, so a task that closed over a finding
# it commissioned closed over its own evidence. The measured gap: two audits
# produced fifteen findings and ELEVEN were never dispositioned.

AUDIT_OPEN = """# T-1 correctness audit

## COR-1 — the parser accepts a trailing comma

- **Disposition.** open

Prose.
"""

# Closing T-1 without closing R-1 fires `one-sided-link`, which would make
# every case below report a class it is not about.
REQS_R1_DONE = REQS.replace("- **Status.** open", "- **Status.** discharged (T-1)", 1)

AUDIT_ROUTED = """# T-1 correctness audit

## COR-1 — the parser accepts a trailing comma

- **Disposition.** routed T-2

Prose.
"""


# --- the amendment re-affirmation (P-48, 0.2.6) --------------------------
# A project learns forward only: a done-means condition signed before a
# decision is never revisited by it. Enumeration, not judgement.

_DMS = ["DM-1", "DM-2"]
CHARTER_DM = CHARTER.replace(
    "## Constraints",
    "## Done means\n\n"
    + "\n".join(f"- **{d}** — an observable condition" for d in _DMS)
    + "\n\n## Constraints", 1)

# Built from the SAME two lists the check reads, so the fixture cannot fall out
# of step with the template's row set the way a hand-written block would.
_REAFFIRM = "\n".join(
    [f"  - {d} — holds" for d in _DMS]
    + [f"  - {r} — holds" for r in _template_rows()])

def headed(charter, n):
    """The charter with the template's header line, reading `Version. n`. A
    charter with amendment entries and no header is a part not evaluated
    (roadmap 0.3.2, L-2.9), so every amended fixture carries one."""
    return charter.replace("# Charter — Fixture\n",
                           f"# Charter — Fixture\n\n**Version.** {n} · **Status.** SIGNED\n", 1)


CHARTER_AMENDED = headed(CHARTER_DM, 2) + f"""
## Amendments

### Version 2 — 2026-09-07 — the test command changed

**Carried by D-1.**

- **Re-affirmed.**
{_REAFFIRM}
"""


def entry(n, body):
    """One amendment entry, numbered `n`, whose list is `body`."""
    return f"### Version {n} — 2026-09-0{n} — entry {n}\n\n**Carried by D-{n}.**\n\n{body}\n\n"


def reaffirm(*omit, verdicts=None):
    """A `Re-affirmed.` block naming every condition but `omit`."""
    verdicts = verdicts or {}
    return "- **Re-affirmed.**\n" + "\n".join(
        f"  - {c} — {verdicts.get(c, 'holds')}" for c in _DMS + _template_rows()
        if c not in omit)


# pricelog's Version 11 omitted four rows that Version 2 had re-affirmed, and
# the check read Version 2's list as Version 11's (F-68, RECORD.md:922).
_F68 = ("Budget ceiling", "Licence", "Repository", "Public?")
CHARTER_F68 = (headed(CHARTER_DM, 4) + "\n## Amendments\n\n"
               + entry(4, reaffirm(*_F68)) + entry(3, reaffirm()) + entry(2, reaffirm()))
# F-36's opener, verbatim (RECORD.md:563), over an older entry whose own list
# omits DM-2: that omission is what the check used to report as the latest's.
_EVERY_OTHER = "**Every other row, checked rather than assumed:**"
CHARTER_F36 = (headed(CHARTER_DM, 3) + "\n## Amendments\n\n"
               + entry(3, "- " + _EVERY_OTHER + "\n" + reaffirm().split("\n", 1)[1])
               + entry(2, reaffirm("DM-2")))
# The template's own unfilled Protected paths cell, read from the template so
# this case follows it (roadmap 0.3.2, L-2.11).
_TEMPLATE_PROTECTED = next(
    l for l in open(os.path.join(os.path.dirname(HERE), "templates", "CHARTER.md"),
                    encoding="utf-8").read().split("\n")
    if l.startswith("| Protected paths |"))

# The estimate against its steps (roadmap 0.3.2, L-2.10): T-1 PLANNED, with a
# model and a `## Steps` section.
def stepped(model, *lines, state="PLANNED"):
    """T-1 estimated at `model=<model>x…` with `lines` under its `## Steps`."""
    body = T1.replace("- **Estimate.** tokens=1000 minutes=10",
                      f"- **Estimate.** tokens=1000 minutes=10 model={model}x440000x1.78+150000")
    return (body.replace("— PLANNED", f"— {state}") + "\n## Steps\n\n"
            + "\n".join(lines) + "\n")


def steps(n, box="[ ]"):
    return [f"- {box} **S-{k}** — step {k} · class: `standard` · verify: `true`"
            for k in range(1, n + 1)]

FIXTURE = {"CHARTER.md": CHARTER, "REQUIREMENTS.md": REQS,
           "tasks/T-1.md": T1, "tasks/T-2.md": T2}

BOARD = """# The board

| Task | Title | Discharges | Depends on | Scope | State |
|---|---|---|---|---|---|
| T-1 | make it work | R-1 | — | `src/` | {s1} |
| T-2 | write the README | R-2 | T-1 | `README.md` | {s2} |
"""


def flight(*tids, note="—"):
    """An `## In flight` table holding a row for each task named (roadmap 0.3.2,
    L-2.2). A claim is held while its task has a row here. The row's last cell
    is a Note, which the old row grammar read as a state, because it took the
    last cell of every table on the board."""
    rows = "\n".join(f"| {t} | x | {t.replace('-', '')}-a-1200 | `a1` | — | "
                     f"2026-09-24 12:00 | claude-opus-5-5 | `src/` | {note} |" for t in tids)
    return ("\n## In flight\n\n| Task | Title | Agent label | Agent id | Sandbox | Since "
            "| Model | Scope | Note |\n|---|---|---|---|---|---|---|---|---|\n"
            + (rows or "| — | — | — | — | — | — | — | — | nothing running |") + "\n")


T1_RUNNING = T1.replace("— PLANNED", "— RUNNING (since 2026-09-24, T1-a-1200)")
T1_STOPPED = T1.replace("— PLANNED", "— NEEDS-DECISION (Q-1: which way)")
REQS_R1_RUNNING = REQS.replace("- **Status.** open", "- **Status.** in-progress (T-1)", 1)
_UNREAD_FLIGHT = ("| — | — | — | — | — | — | — | — | nothing running |",
                  "| the first task | x | T1-a-1200 | `a1` | — | — | — | — | — |")

# --- identifier fields and the requirement states (roadmap 0.3.2) ---------
T1_DONE = T1.replace("— PLANNED", "— DONE (2026-09-24)")
T2_DONE = T2.replace("— PLANNED", "— DONE (2026-09-24)")


def statuses(r1, r2="open"):
    """REQS with R-1's and R-2's `Status.` set."""
    return (REQS.replace("- **Status.** open", f"- **Status.** {r1}", 1)
            .replace("- **Status.** open", f"- **Status.** {r2}", 1))


# pricelog's T-17 and T-18: a fix under a requirement another task discharged,
# which takes no discharge of its own (RECORD.md:495).
T3_RENEWS = """# T-3 — fix what T-1 shipped — DONE (2026-09-24)

- **Discharges.** none
- **Re-establishes.** R-1
- **Why R-1 stays with T-1.** this task fixes code under R-1 and takes no discharge.
- **Depends on.** T-1
- **Scope.**
  - `src/`
- **Gate.** the test command exits zero again.
- **Verify.** `make test`
- **Estimate.** tokens=100 minutes=5
"""

CASES = [
    # --- unparseable-protected-path ---------------------------------------
    # The row that fooled 0.2.8, verbatim. It reads correctly to a human, and
    # the guard resolved two non-paths out of it and protected nothing.
    ("unparseable-protected-path",
     {"CHARTER.md": CHARTER.replace(
         "| Protected paths | fixture |",
         "| Protected paths | `devteam/` — the pipeline's own record. Readable "
         "by every role, written only by the manager and the supervisors |")},
     {"unparseable-protected-path"}),
    # THE CASE `_s9` DEMANDED BEFORE THIS SHIPPED, and it is the one that keeps
    # the check honest. The first wording of CONSOLIDATION N-4 said "an entry
    # that does not resolve to a path in the tree", which would have reported
    # THREE findings on the fixture project's correct row: sibling repositories
    # are the row's advertised use, named in guard.py's docstring, in the check
    # that "defends a path outside every devteam project", and in setup.py's own
    # scaffolded cell text. In-tree-ness is the wrong discriminator; being
    # path-shaped is the right one.
    ("fp-protected-paths-are-absolute-sibling-repos",
     {"CHARTER.md": CHARTER.replace(
         "| Protected paths | fixture |",
         "| Protected paths | `~/Workspace/REPOS/nitpick`, "
         "`~/Workspace/REPOS/nitpick-libs`, "
         "`~/Workspace/REPOS/claude-skills/plugins` |")},
     set()),
    ("fp-protected-paths-none-is-a-value",
     {"CHARTER.md": CHARTER.replace("| Protected paths | fixture |",
                                    "| Protected paths | none |")},
     set()),
    # --- amendment-omits-condition / amendment-names-unknown (P-48) -------
    ("amendment-omits-condition",
     {"CHARTER.md": CHARTER_AMENDED.replace("  - DM-1 — holds\n", "")},
     {"amendment-omits-condition"}),
    ("amendment-omits-condition-bad-verdict",
     {"CHARTER.md": CHARTER_AMENDED.replace("DM-1 — holds", "DM-1 — probably fine")},
     {"amendment-omits-condition"}),
    ("amendment-names-unknown",
     {"CHARTER.md": CHARTER_AMENDED.replace(
         "  - DM-1 — holds\n", "  - DM-1 — holds\n  - DM-99 — holds\n")},
     {"amendment-names-unknown"}),
    # THE LATEST ENTRY IS THE HIGHEST VERSION, NOT THE LAST IN THE FILE.
    # Charters are written newest-first, so the first draft of this check read
    # Version 2 of a charter at Version 17 and reported against the oldest
    # entry in the document.
    # The newer entry is COMPLETE and the older one is DEFICIENT, which is the
    # only arrangement that tells the two selection rules apart: by position
    # the deficient Version 2 is chosen and the check fires; by version the
    # complete Version 3 is chosen and it is clean.
    ("amendment-latest-is-by-version-not-position",
     {"CHARTER.md": headed(CHARTER_DM, 3) + "\n## Amendments\n\n"
      "### Version 3 — 2026-09-08 — later, and complete\n\n"
      "**Carried by D-1.**\n\n- **Re-affirmed.**\n" + _REAFFIRM + "\n\n"
      "### Version 2 — 2026-09-07 — earlier, and deficient\n\n"
      "**Carried by D-1.**\n\n- **Re-affirmed.**\n  - DM-1 — holds\n"},
     set()),

    # --- FALSE-POSITIVE TWINS ---------------------------------------------
    ("fp-complete-reaffirmation-is-clean",
     {"CHARTER.md": CHARTER_AMENDED},
     set()),
    # A CHARTER WITH NO AMENDMENTS HAS NOTHING TO RE-AFFIRM. Reporting here
    # would fire on every project on its first day.
    ("fp-no-amendments-yet",
     {}, set()),
    # THE GATE IS ON THE SECTION, NOT ON FINDING NO HEADINGS. Without this the
    # mutation that drops the `## Amendments` gate survives the whole suite,
    # because the fixture charter happens to contain no `###` line at all.
    ("fp-charter-subheadings-outside-an-amendments-section",
     {"CHARTER.md": CHARTER_DM + "\n### A note about scope\n\nProse.\n"},
     set()),

    # --- THE LATEST ENTRY, AND ONLY IT (roadmap 0.3.2, L-2.9) --------------
    # F-68: three entries, newest first, and the latest omits four rows the
    # older two re-affirm. Read to the end of the file, the older lists
    # supplied all four and nothing fired.
    ("l29-f68-the-latest-omission-is-named-and-no-older-list-is-read",
     {"CHARTER.md": CHARTER_F68},
     {"amendment-omits-condition"}, [], None, set(),
     ("re-affirms 14 of 18 — omits Budget ceiling, Licence, Repository, Public?",)),
    # F-36: the latest entry opens its list with another opener. The entry is
    # named, and the older entry's omission of DM-2 -- which the check used to
    # report as the latest's -- is not read.
    ("l29-f36-a-list-under-another-opener-names-the-entry",
     {"CHARTER.md": CHARTER_F36},
     set(), [], None, {"Version 3's Re-affirmed. list"},
     ("lists 18 of the charter's conditions under '- " + _EVERY_OTHER + "'",)),
    ("l29-f36-the-opener-as-a-paragraph-over-top-level-items",
     {"CHARTER.md": CHARTER_F36.replace(
         "- " + _EVERY_OTHER + "\n  - DM-1", _EVERY_OTHER + "\n\n- DM-1").replace(
         "\n  - ", "\n- ", 17)},
     set(), [], None, {"Version 3's Re-affirmed. list"},
     ("under '" + _EVERY_OTHER + "'",)),
    # An entry with no list at all re-affirms nothing, which is P-48's finding,
    # not a part: there is nothing under another opener to have misread. Its
    # one bullet is prose, with a dash in it, and names no condition.
    ("l29-an-entry-with-no-list-re-affirms-nothing",
     {"CHARTER.md": headed(CHARTER_DM, 3) + "\n## Amendments\n\n"
      + entry(3, "**Why.** a reason, and no list.\n\n"
                 "- **The log path follows a symlink**, at the file — and at the directory.")
      + entry(2, reaffirm())},
     {"amendment-omits-condition"}, [], None, set(), ("re-affirms 0 of 18",)),
    # The section ends at the next section: a `###` there is not an entry.
    ("fp-l29-a-section-after-the-amendments-holds-no-entry",
     {"CHARTER.md": CHARTER_AMENDED + "\n## Appendix\n\n### Notes\n\nProse.\n"},
     set()),
    # pricelog's Version 13 carries two prose bullets before its block. They
    # name no condition, so the block is read as usual.
    ("fp-l29-prose-bullets-before-the-block",
     {"CHARTER.md": CHARTER_AMENDED.replace(
         "**Carried by D-1.**\n",
         "**Carried by D-1.**\n\n- **A future-dated record blocks every coin.** Reproduced.\n"
         "- **The log path follows a symlink**, at the file — and at the directory.\n")},
     set()),
    # N-4: a condition the entry adds. The vocabulary had no word for it.
    ("fp-l29-n4-added-this-entry-is-read",
     {"CHARTER.md": CHARTER_AMENDED.replace("  - DM-2 — holds", "  - DM-2 — added (this entry)")},
     set()),
    ("l29-n4-an-added-item-naming-no-condition",
     {"CHARTER.md": CHARTER_AMENDED.replace(
         "  - DM-2 — holds\n", "  - DM-2 — holds\n  - DM-99 — added (this entry)\n")},
     {"amendment-names-unknown"}, [], None, set(), ("re-affirms 'DM-99'",)),
    # A verdict that wraps is read whole, and the items after it are read
    # (0.3.2 §3.2's joint: the parse stopped at the continuation line).
    ("fp-l29-a-verdict-that-wraps-is-read-whole",
     {"CHARTER.md": CHARTER_AMENDED.replace(
         "  - DM-1 — holds", "  - DM-1 — struck (D-3, the project no longer\n    produces a CLI)")},
     set()),
    ("l29-a-wrapped-verdict-outside-the-vocabulary-is-quoted-whole",
     {"CHARTER.md": CHARTER_AMENDED.replace("  - DM-1 — holds", "  - DM-1 — probably\n    fine")},
     {"amendment-omits-condition"}, [], None, set(), ("re-affirmed as 'probably fine'",)),
    # Version 18: the header was not moved with its entry (RECORD.md:1350).
    ("l29-stale-version-header",
     {"CHARTER.md": CHARTER_AMENDED.replace("**Version.** 2", "**Version.** 1")},
     {"stale-version-header"}, [], None, set(),
     ("reads `Version. 1`, and its newest amendment entry is Version 2",)),
    ("l29-stale-version-header-ahead-of-its-entries",
     {"CHARTER.md": CHARTER_AMENDED.replace("**Version.** 2", "**Version.** 3")},
     {"stale-version-header"}),
    ("l29-stale-version-header-with-no-entry",
     {"CHARTER.md": headed(CHARTER, 2)},
     {"stale-version-header"}, [], None, set(), ("has no amendment entry, so its version is 1",)),
    ("fp-l29-version-1-with-no-entry",
     {"CHARTER.md": headed(CHARTER, 1)},
     set()),
    ("fp-l29-version-1-under-an-empty-amendments-section",
     {"CHARTER.md": headed(CHARTER, 1) + "\n## Amendments\n\n_None yet._\n"},
     set()),
    ("l29-a-header-that-does-not-parse",
     {"CHARTER.md": CHARTER_AMENDED.replace("**Version.** 2", "**Version.** two")},
     set(), [], None, {"the charter's Version. header"},
     ("does not read `**Version.** <n>`",)),
    ("l29-entries-and-no-header",
     {"CHARTER.md": CHARTER_AMENDED.replace("\n**Version.** 2 · **Status.** SIGNED\n", "")},
     set(), [], None, {"the charter's Version. header"}),
    ("l29-an-unnumbered-entry-leaves-the-newest-unknown",
     {"CHARTER.md": CHARTER_AMENDED.replace(
         "## Amendments\n\n", "## Amendments\n\n### A later entry\n\n" + reaffirm() + "\n\n")},
     set(), [], None, {"the charter's Version. header"}),

    # --- estimate-step-mismatch (roadmap 0.3.2, L-2.10) --------------------
    # pricelog's T-12 and T-16: four steps under `model=3x…` (RECORD.md:946).
    ("l210-four-steps-under-a-three-step-model",
     {"tasks/T-1.md": stepped(3, *steps(4))},
     {"estimate-step-mismatch"}, [], None, set(),
     ("prices 3 step(s) (`model=3x…`) and its `## Steps` lists 4",)),
    ("fp-l210-equal-counts",
     {"tasks/T-1.md": stepped(4, *steps(4))},
     set()),
    # A struck step was estimated, so it counts; a step's second attempt is
    # one step.
    ("l210-a-struck-step-counts",
     {"tasks/T-1.md": stepped(3, *steps(3), steps(4, "[~]")[3] + " — struck (D-2)")},
     {"estimate-step-mismatch"}),
    ("fp-l210-a-struck-step-was-estimated",
     {"tasks/T-1.md": stepped(4, *steps(3), steps(4, "[~]")[3] + " — struck (D-2)")},
     set()),
    ("fp-l210-a-second-attempt-is-one-step",
     {"tasks/T-1.md": stepped(2, *steps(2), "- [x] **S-2 (attempt 2)** — step 2 again")},
     set()),
    # THE OWNER'S ANSWER: compared while PLANNED only. A step a supervisor
    # adds once the task runs is what the model's rounds rate prices.
    ("fp-l210-a-step-added-after-the-claim-is-not-compared",
     {"tasks/T-1.md": stepped(3, *steps(4), state="RUNNING (since 2026-09-24, T1-a-1200)"),
      "REQUIREMENTS.md": REQS_R1_RUNNING},
     set()),
    ("fp-l210-a-closed-task-is-not-compared",
     {"tasks/T-1.md": stepped(3, *steps(5), state="DONE (2026-09-24)"),
      "REQUIREMENTS.md": REQS_R1_DONE},
     set()),
    # No `## Steps` is compared with nothing: the supervisor writes the steps.
    ("fp-l210-no-steps-section",
     {"tasks/T-1.md": stepped(3).split("\n## Steps")[0] + "\n"},
     set()),
    ("l210-steps-and-an-estimate-with-no-model",
     {"tasks/T-1.md": stepped(3, *steps(3)).replace(" model=3x440000x1.78+150000", "")},
     set(), [], None, {"T-1's Estimate."}),
    ("l210-an-item-under-steps-that-is-not-a-step-line",
     {"tasks/T-1.md": stepped(2, *steps(2), "1. S-3 — a numbered step")},
     set(), [], None, {"T-1's steps"}),

    # --- a fresh project reads clean (roadmap 0.3.2, L-2.11) ---------------
    # The template's unfilled cell is ONE placeholder holding commas. Split
    # before it was tested, it read as four sentences.
    ("fp-l211-the-template-s-unfilled-protected-paths-cell",
     {"CHARTER.md": CHARTER.replace("| Protected paths | fixture |", _TEMPLATE_PROTECTED)},
     set()),
    ("fp-l211-a-cell-filled-in-part",
     {"CHARTER.md": CHARTER.replace("| Protected paths | fixture |",
                                    "| Protected paths | `dist/`, <more, when known> |")},
     set()),
    # Tested WHOLE: a placeholder beside a filled entry does not excuse it.
    ("l211-a-prose-entry-beside-a-placeholder-still-fires",
     {"CHARTER.md": CHARTER.replace("| Protected paths | fixture |",
                                    "| Protected paths | `dist/` — the build output, <more> |")},
     {"unparseable-protected-path"}),
    # --- open-finding-at-close (0.2.6) ------------------------------------
    ("open-finding-at-close",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/T-1-correctness-2026-09-04.md": AUDIT_OPEN,
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     {"open-finding-at-close"}),
    ("open-finding-at-close-no-disposition-line",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/T-1-correctness-2026-09-04.md":
          AUDIT_OPEN.replace("- **Disposition.** open\n", ""),
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     {"open-finding-at-close"}),

    # A DISPOSITION IS READ WHOLE, and `open` is its first word (roadmap 0.3.2,
    # L-2.3), as check_refs reads the same field: a note after `open` on the
    # next line leaves the finding open.
    ("open-finding-at-close-an-open-disposition-with-a-note-on-its-next-line",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/T-1-correctness-2026-09-04.md":
          AUDIT_OPEN.replace("- **Disposition.** open", "- **Disposition.** open\n  until T-2 lands"),
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     {"open-finding-at-close"}),

    # --- FALSE-POSITIVE TWINS ---------------------------------------------
    # A finding that WAS routed is the ordinary case and must stay silent.
    ("fp-routed-finding-at-close-is-clean",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/T-1-correctness-2026-09-04.md": AUDIT_ROUTED,
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     set()),
    # AN OPEN FINDING ON AN OPEN TASK IS NOT A DEFECT. It is the normal state
    # between the audit and the close, and reporting it would make the check
    # fire on every project mid-audit -- the false positive that gets a check
    # disabled (P-35).
    ("fp-open-finding-while-the-task-is-still-open",
     {"audits/T-1-correctness-2026-09-04.md": AUDIT_OPEN},
     set()),
    # The task id is read from the FILENAME, which the audit skill fixes as
    # `T-n-<dimension>-<date>.md`. A file that does not match is tied to no
    # task, so nothing is inferred from its name and no finding is raised.
    #
    # THIS CASE USED TO SAY "IGNORED" AND EXPECT CLEAN, and that was the
    # defect roadmap 0.3.1 exists to end: the file holds an open finding about
    # a closed task, and the check said clean without having asked whether it
    # was open. It is now a part not evaluated, named (L-1.3). pricelog's step
    # audit is this shape exactly.
    ("audit-filename-outside-the-grammar-is-not-evaluated",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/notes-about-T-1.md": AUDIT_OPEN,
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     set(), [], None, {"audits/notes-about-T-1.md"}),
    # ...and a file in audits/ naming a closed task and holding NO finding
    # heading offers nothing, so it stays quiet.
    ("fp-audit-notes-with-no-finding-heading-offer-nothing",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/notes-about-T-1.md": "# Notes about T-1\n\nProse only.\n",
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     set()),
    # --- zero rows, partial reads and wrapped fields (roadmap 0.3.1, L-1.3) --
    # Each of these used to report CLEAN, and each is a row the source offered
    # that the grammar did not read. The case expects the part named, and a
    # finding only where the missed row really does cause one.
    #
    # ZERO ROWS. These two were F-70's link rows until 0.3.2 read that form
    # (L-2.1); a link row is now read, so the rows the grammar still cannot
    # read are a row short of a cell and a row naming two tasks.
    ("zero-rows-a-tasks-table-whose-rows-are-all-short-a-cell",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace(" | — |\n", " |\n")},
     set(), [], None, {"BOARD.md's task rows"}),
    # A PARTIAL READ: one row among parsed ones.
    ("partial-read-one-row-naming-two-tasks",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace("| T-2 |", "| T-2 and T-3 |")},
     set(), [], None, {"BOARD.md's task rows"}),
    # A pipe inside a cell misaligns the row, so its State cell is not where
    # the header says: the row is named, never read with the wrong cell.
    ("partial-read-a-row-with-a-cell-too-many",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace("| R-1 |", "| R-1 | R-3 |")},
     set(), [], None, {"BOARD.md's task rows"}),
    # The State column is found by its header, not by being the last cell.
    ("fp-the-state-column-is-found-by-its-header",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace("| State |", "| State | Note |")
      .replace("|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|")
      .replace("| `src/` | — |", "| `src/` | — | DONE |")
      .replace("| `README.md` | — |", "| `README.md` | — | DONE |")},
     set()),
    ("a-board-with-no-tasks-table-is-not-evaluated",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace("| State |", "| Status |")},
     set(), [], None, {"BOARD.md's Tasks table"}),
    ("partial-read-a-requirement-heading-with-a-colon",
     {"REQUIREMENTS.md": REQS + "\n### R-3: it is fast\n\n- **Statement.** fast.\n"},
     set(), [], None, {"REQUIREMENTS.md's requirement headings"}),
    ("partial-read-a-goal-written-with-a-colon",
     {"CHARTER.md": CHARTER.replace("- **G-2** — the thing is documented",
                                    "- **G-2** — the thing is documented\n- **G-3**: it is fast")},
     set(), [], None, {"the charter's goals"}),
    # WRAPPED FIELDS ARE READ WHOLE NOW (roadmap 0.3.2, L-2.3), so the cases
    # that asserted 0.3.1's first-line reading are the identifier-field cases
    # below; a field that continues is simply read.
    # A field NAMED and not parsed as that field. The finding is the old
    # behaviour and stays; the gap names the line that caused it.
    ("field-named-with-a-colon-is-a-row-not-parsed",
     {"REQUIREMENTS.md": REQS.replace("- **Priority.** should", "- **Priority**: should")},
     {"missing-field"}, [], None, {"R-2's Priority."}),
    ("path-list-item-with-its-reason-inline",
     {"tasks/T-1.md": T1.replace("  - `src/`", "  - `src/`\n  - `docs/` — for the notes")},
     set(), [], None, {"T-1's Scope."}),
    ("protected-paths-row-the-guard-cannot-read",
     {"CHARTER.md": CHARTER.replace("| Protected paths | fixture |",
                                    "| **Protected paths** | `dist/` |")},
     {"template-drift"}, [], None, {"unparseable-protected-path"}),
    # The part names its entry (roadmap 0.3.2, L-2.9), and an item that does
    # not parse no longer stops the parse: the sixteen rows after DM-2 are read.
    ("re-affirmed-item-without-a-separator",
     {"CHARTER.md": CHARTER_AMENDED.replace("  - DM-2 — holds", "  - DM-2 holds")},
     {"amendment-omits-condition"}, [], None, {"Version 2's Re-affirmed. list"},
     ("re-affirms 17 of 18 — omits DM-2",)),
    ("audit-heading-outside-the-namespace",
     {"tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-07)"),
      "REQUIREMENTS.md": REQS_R1_DONE,
      "audits/T-1-safety-2026-09-04.md": AUDIT_OPEN.replace("COR-1", "SAF-1"),
      "BOARD.md": BOARD.format(s1="DONE", s2="—")},
     set(), [], None, {"audits/T-1-safety-2026-09-04.md's findings"}),
    # MISSING SOURCES. A project always has these files, so a missing one is
    # not an empty source: nothing was there to read.
    ("missing-board-is-not-an-empty-board",
     {"BOARD.md": None}, set(), [], None, {"BOARD.md"}),
    ("missing-requirements-is-not-zero-requirements",
     {"REQUIREMENTS.md": None}, {"unknown-reference", "orphan-scope"}, [], None,
     {"REQUIREMENTS.md"}),
    # HISTORY, READ WHOLE (roadmap 0.3.2, L-2.3). 0.3.1's churn compared first
    # lines, so a rewrite past one was uncounted and the part said so. Each
    # revision's fields are read whole now: three rewrites that change only the
    # continuation line count as three...
    ("continued-rewrites-past-the-first-line-are-counted",
     {"REQUIREMENTS.md": REQS.replace("- **Statement.** the thing works when run.",
                                      "- **Statement.** the thing works\n  under load, v4.", 1)},
     {"re-litigated-requirement"}, [],
     [REQS.replace("- **Statement.** the thing works when run.",
                   "- **Statement.** the thing works\n  under load, v%d." % v, 1) for v in (1, 2, 3)]),
    # ...and the same words wrapped differently are not a rewrite at all.
    ("fp-continued-a-rewrapped-statement-is-not-a-rewrite",
     {}, set(), [],
     [REQS.replace("- **Statement.** the thing works when run.",
                   "- **Statement.** the thing works\n  when run.", 1),
      REQS.replace("- **Statement.** the thing works when run.",
                   "- **Statement.** the thing\n  works when run.", 1),
      REQS.replace("- **Statement.** the thing works when run.",
                   "- **Statement.** the thing works when\n  run.", 1)]),
    # ...and what must stay CLEAN.
    #
    # A GENUINELY EMPTY SOURCE: nothing planned yet, which is every project
    # between setup and planning. Offered nothing, so it read everything.
    ("fp-genuinely-empty-sources-are-clean",
     {"CHARTER.md": CHARTER.replace("- **G-1** — the thing works\n", "").replace(
         "- **G-2** — the thing is documented\n", ""),
      "REQUIREMENTS.md": "# Requirements\n\nNone yet.\n",
      "tasks/T-1.md": None, "tasks/T-2.md": None,
      "BOARD.md": BOARD.split("| T-1 |")[0]},
     set()),
    # A MULTI-LINE LIST FIELD THE CHECK DOES READ is not a wrapped field.
    ("fp-a-multi-line-path-list-is-read-whole",
     {"tasks/T-1.md": T1.replace("  - `src/`", "  - `src/`\n  - `lib/`\n  - `tests/`"),
      "REQUIREMENTS.md": REQS.replace("  - `src/`", "  - `src/`\n  - `lib/`", 1)},
     set()),
    # A field that wraps is read whole, and one no class reads never was a
    # partial read of anything this check evaluates.
    ("fp-a-wrapped-field-nothing-reads",
     {"tasks/T-1.md": T1.replace("- **Estimate.** tokens=1000 minutes=10",
                                 "- **Estimate.** tokens=1000 minutes=10,\n  from T-0's figure")},
     set()),
    # A field-shaped line in an execution record, when the task's real field
    # parsed, is a mention (pricelog's T-16.md:190, a verifier quoting
    # `- **Scope:** check_scope … prints clean`).
    ("fp-a-field-mentioned-in-the-record-after-the-real-one",
     {"tasks/T-1.md": T1 + "\n## Execution record\n\n- **Scope:** `check_scope` printed clean.\n"},
     set()),
    # A step heading and a possessive MENTION a task or requirement; they are
    # not titles written wrong.
    ("fp-step-headings-and-possessives-are-not-titles",
     {"tasks/T-1.md": T1 + "\n## Execution record\n\n# T-1.S-2 adversarial pass\n\nProse.\n",
      "REQUIREMENTS.md": REQS + "\n## R-1's history\n\nProse.\n"},
     set()),

    # --- board-drift: the one artifact no check read back ------------------
    # A board saying a task was CLAIMED with a live in-flight row, two hours
    # after that task closed, passed all four checks. `check_scope` reads the
    # board for scopes and a claim is legal whatever a title says;
    # `check_trace` read titles and never opened the Tasks table.
    # The dispatch window: a claim is committed before the supervisor exists,
    # and the title is the supervisor's to write. Whether this is healthy or a
    # dead claim depends on agent liveness, which is not in any file -- so it
    # belongs to §3's recovery table and not to a static check.
    ("fp-claimed-over-a-not-yet-started-supervisor",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—")}, set()),
    ("board-drift-claimed-over-a-finished-task",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—"),
      "tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-03)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** discharged (T-1)", 1)},
     {"board-drift"}),
    ("board-drift-done-over-a-running-task",
     {"BOARD.md": BOARD.format(s1="DONE", s2="—"),
      "tasks/T-1.md": T1.replace("— PLANNED", "— RUNNING (since 2026-09-03, T1-a-1200)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** in-progress (T-1)", 1)},
     {"board-drift"}),
    ("board-drift-row-with-no-task-file",
     {"BOARD.md": BOARD.format(s1="—", s2="—") + "| T-9 | a ghost | R-1 | — | `x/` | — |\n"},
     {"board-drift"}),
    # ...and the states that legitimately agree, since the two vocabularies
    # differ by design and this is a relation rather than an equality.
    ("fp-board-and-title-agree-at-rest",
     {"BOARD.md": BOARD.format(s1="—", s2="—")}, set()),
    ("fp-board-claimed-over-a-running-task",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—"),
      "tasks/T-1.md": T1.replace("— PLANNED", "— RUNNING (since 2026-09-03, T1-a-1200)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** in-progress (T-1)", 1)},
     set()),
    ("fp-board-accepted-over-an-accepted-task",
     {"BOARD.md": BOARD.format(s1="ACCEPTED (2026-09-05, D-41)", s2="—"),
      "tasks/T-1.md": T1.replace("— PLANNED", "— ACCEPTED (2026-09-05, D-41)"),
      "REQUIREMENTS.md": REQS.replace("- **Status.** open",
                                      "- **Status.** discharged (T-1)", 1)},
     set()),

    # --- the board read as its grammar writes it (roadmap 0.3.2, L-2.1) -----
    # F-70'S OWN ROWS: every real row is a link, and the old grammar wanted a
    # bare id, so board-drift compared nothing for a project's whole life.
    ("f70-a-link-row-that-disagrees-with-its-title-fires",
     {"BOARD.md": BOARD.format(s1="DONE", s2="—").replace(
         "| T-1 |", "| [T-1](tasks/T-1.md) |").replace("| T-2 |", "| [T-2](tasks/T-2.md) |")},
     {"board-drift"}),
    ("fp-f70-link-rows-that-agree-are-read-and-clean",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace(
         "| T-1 |", "| [T-1](tasks/T-1.md) |").replace("| T-2 |", "| [T-2](tasks/T-2.md) |")},
     set()),
    # The template writes backticks, and pricelog writes its states in bold.
    ("backticked-row-with-a-bold-state-that-disagrees-fires",
     {"BOARD.md": BOARD.format(s1="**DONE**", s2="—").replace("| T-1 |", "| `T-1` |")},
     {"board-drift"}),
    ("fp-backticked-and-bold-rows-and-states-are-read",
     {"BOARD.md": BOARD.format(s1="**—**", s2="`—`").replace(
         "| T-1 |", "| `T-1` |").replace("| T-2 |", "| **T-2** |")},
     set()),
    # F-107'S OWN: T-12 read DONE on the board and NEEDS-DECISION in its title
    # for three days, and every check passed (pricelog RECORD.md:1181).
    ("f107-done-on-the-board-over-a-needs-decision-title",
     {"BOARD.md": BOARD.format(s1="DONE", s2="—"), "tasks/T-1.md": T1_STOPPED},
     {"board-drift"}),
    # THE IN-FLIGHT ROW IS NOT A TASKS ROW. Its last cell is a Note, and the old
    # grammar read that as the task's state (0.3.1 §3.2's T-19).
    ("fp-an-in-flight-rows-note-is-not-a-state",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—")
      + flight("T-1", note="DONE — waiting on the verifier"),
      "tasks/T-1.md": T1_RUNNING, "REQUIREMENTS.md": REQS_R1_RUNNING},
     set()),
    # L-2.2, BOTH WAYS: CLAIMED over a title its supervisor wrote at a close or a
    # stop is legal while the claim is held, and drifts once its row is gone --
    # the run's own mutation (pricelog RECORD.md:487).
    ("fp-l22-claimed-over-a-done-title-while-in-flight",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—") + flight("T-1"),
      "tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-24)"),
      "REQUIREMENTS.md": REQS_R1_DONE},
     set()),
    ("l22-claimed-over-a-done-title-with-the-row-removed",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—") + flight(),
      "tasks/T-1.md": T1.replace("— PLANNED", "— DONE (2026-09-24)"),
      "REQUIREMENTS.md": REQS_R1_DONE},
     {"board-drift"}),
    ("fp-l22-claimed-over-a-needs-decision-stop-while-in-flight",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—") + flight("T-1"),
      "tasks/T-1.md": T1_STOPPED},
     set()),
    ("l22-claimed-over-a-needs-decision-stop-with-the-row-removed",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—") + flight(),
      "tasks/T-1.md": T1_STOPPED},
     {"board-drift"}),
    # ...and the allowance is what a supervisor writes, not anything at all:
    # ACCEPTED is the client's.
    ("l22-an-accepted-title-drifts-under-claimed-even-in-flight",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—") + flight("T-1"),
      "tasks/T-1.md": T1.replace("— PLANNED", "— ACCEPTED (2026-09-24, D-1)"),
      "REQUIREMENTS.md": REQS_R1_DONE},
     {"board-drift"}),
    # The in-flight table is read when a row is CLAIMED, and a row of it this
    # cannot read is then a part not evaluated: the allowance fails closed on
    # it. With nothing CLAIMED, the table is not read at all.
    ("an-unreadable-in-flight-row-under-a-claim-is-not-evaluated",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200", s2="—") + flight().replace(*_UNREAD_FLIGHT),
      "tasks/T-1.md": T1_RUNNING, "REQUIREMENTS.md": REQS_R1_RUNNING},
     set(), [], None, {"BOARD.md's in-flight rows"}),
    ("fp-an-unreadable-in-flight-row-with-nothing-claimed-is-not-read",
     {"BOARD.md": BOARD.format(s1="—", s2="—") + flight().replace(*_UNREAD_FLIGHT)},
     set()),
    # --- bad-board-state: a state outside the vocabulary (L-2.1) ------------
    # pricelog's T-16 and T-19 at the stop. A state the check did not know
    # compared nothing and said nothing (`if allowed and …`).
    ("bad-board-state-a-state-the-vocabulary-lacks",
     {"BOARD.md": BOARD.format(s1="**STOPPED (D-67)** — never restarted", s2="—")},
     {"bad-board-state"}),
    # A known state with a sentence after it, as pricelog wrote a dozen times.
    ("bad-board-state-a-reason-written-after-the-state",
     {"BOARD.md": BOARD.format(s1="CLAIMED T1-a-1200 — stopped; restarts under §9a", s2="—"),
      "tasks/T-1.md": T1_RUNNING, "REQUIREMENTS.md": REQS_R1_RUNNING},
     {"bad-board-state"}),
    ("fp-blocked-on-several-named-blockers",
     {"BOARD.md": BOARD.format(s1="BLOCKED on Q-1, Q-2", s2="—")},
     set()),

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

    # --- identifier fields: identifiers only, read whole (roadmap 0.3.2, L-2.3)
    # A seventh element names text the output must carry, where the case is
    # about WHAT a part or a finding says rather than that it exists.
    #
    # F-132, T-19'S OWN FIRST LINE (pricelog RECORD.md:1675). Cut at commas,
    # `R-2 — **completed here` was a requirement that does not exist; read by
    # regex, the prose would name R-2 by accident. Neither now: the piece is
    # named, T-1 does not list R-2, and R-2's status naming T-1 is the finding
    # the record measured in every state from the claim.
    ("f132-a-discharges-line-of-prose-names-the-piece-and-reads-nothing-from-it",
     {"tasks/T-1.md": T1_RUNNING.replace(
         "- **Discharges.** R-1",
         "- **Discharges.** R-1, R-2 — **completed here, advanced by T-2, and both are\n"
         "  named in their status**"),
      "REQUIREMENTS.md": statuses("in-progress (T-1)", "in-progress (T-2, T-1)")},
     {"one-sided-link"}, [], None, {"T-1's Discharges."},
     ["'R-2 — **completed here'",
      "R-2 is in-progress (T-2, T-1), but T-1 does not list R-2 in its `Discharges.`"]),
    # ...and the record's repair: the prose on a bullet of its own.
    ("fp-f132-the-prose-on-its-own-bullet-leaves-both-links-two-sided",
     {"tasks/T-1.md": T1_RUNNING.replace(
         "- **Discharges.** R-1",
         "- **Discharges.** R-1, R-2\n"
         "- **Why R-2 is here as well as T-2.** Completed here, advanced by T-2, and both\n"
         "  are named in their status."),
      "REQUIREMENTS.md": statuses("in-progress (T-1)", "in-progress (T-2, T-1)")},
     set()),
    # F-95, D-31'S REPAIR (RECORD.md:1137): a sentence naming the task itself in
    # its own `Depends on.` was an edge to itself, a `dependency-cycle T-2 → T-2`.
    # It is no edge now, and the piece is named.
    ("f95-a-sentence-naming-the-task-itself-adds-no-edge-and-is-named",
     {"tasks/T-2.md": T2.replace("- **Depends on.** T-1",
                                 "- **Depends on.** T-1, and T-2's brief is written against it")},
     set(), [], None, {"T-2's Depends on."}, ["and T-2's brief is written against it"]),
    # A PROSE MENTION OF ANOTHER TASK: the record read this case from the parser
    # and never ran it. The edge it would add is silent unless it closes a
    # cycle, so here it would: T-2 already depends on T-1.
    ("f95-a-prose-mention-of-another-task-adds-no-edge",
     {"tasks/T-1.md": T1.replace("- **Depends on.** none",
                                 "- **Depends on.** none — T-2 reads what this writes")},
     set(), [], None, {"T-1's Depends on."}),
    # ...and of a task nobody declared: no `unknown-reference`, because no
    # dependency was read.
    ("f95-a-prose-mention-of-an-undeclared-task-reads-no-dependency",
     {"tasks/T-1.md": T1.replace("- **Depends on.** none",
                                 "- **Depends on.** none — T-9 was folded into this")},
     set(), [], None, {"T-1's Depends on."}),
    # A REAL CYCLE between two bare lists still fires, one of them continued.
    ("dependency-cycle-a-bare-list-continued-onto-its-next-line",
     {"tasks/T-1.md": T1.replace("- **Depends on.** none", "- **Depends on.**\n  T-2")},
     {"dependency-cycle"}),
    # CONTINUATION: a list of bare identifiers over two lines is read whole.
    # T-2 is gone, so R-2 is covered only if the second line was read.
    ("fp-continued-a-discharges-of-bare-identifiers-is-read-whole",
     {"tasks/T-1.md": T1.replace("- **Discharges.** R-1", "- **Discharges.** R-1,\n  R-2")
                        .replace("  - `src/`", "  - `src/`\n  - `README.md`"),
      "tasks/T-2.md": None},
     set()),
    # A requirement's `Status.` continued: `in-progress` alone names no task.
    ("fp-continued-a-requirement-status-is-read-whole",
     {"tasks/T-1.md": T1_RUNNING, "REQUIREMENTS.md": statuses("in-progress\n  (T-1)")},
     set()),
    # A PIECE OF ANOTHER KIND is not the field's: a task in `Discharges.` used
    # to be dropped in silence.
    ("a-task-named-in-discharges-is-a-piece-not-a-requirement",
     {"tasks/T-2.md": T2.replace("- **Discharges.** R-2", "- **Discharges.** R-2, T-1")},
     set(), [], None, {"T-2's Discharges."}),
    # `none` is the whole field or it is a piece like any other.
    ("a-none-beside-an-identifier-is-a-piece",
     {"tasks/T-2.md": T2.replace("- **Depends on.** T-1", "- **Depends on.** none, T-1")},
     set(), [], None, {"T-2's Depends on."}),
    # `Satisfies.` is read the same way: prose naming G-1 does not satisfy it,
    # so G-2 is uncovered once its own id is inside a sentence.
    ("a-satisfies-holding-prose-names-the-piece",
     {"REQUIREMENTS.md": REQS.replace("- **Satisfies.** G-2", "- **Satisfies.** G-2 — and G-1 in part")},
     {"orphan-scope"}, [], None, {"R-2's Satisfies."}),
    ("a-probes-informs-holding-prose-names-the-piece",
     {"tasks/T-3.md": """# T-3 — can the store be atomic? — PLANNED

- **Kind.** probe
- **Informs.** R-1 — whether an append can be atomic
- **Discharges.** none
- **Depends on.** none
- **Scope.**
  - `probe/`
- **Gate.** the question is answered either way.
- **Verify.** `test -s probe/FINDING.md`
- **Estimate.** tokens=100 minutes=5
"""},
     {"unjustified-task"}, [], None, {"T-3's Informs."}),
    # A PATH LIST WRITTEN BESIDE ITS FIELD is read whole too: its second line
    # used to be dropped in silence, and R-2's `README.md` read as unreachable.
    ("fp-continued-an-inline-scope-is-read-whole",
     {"tasks/T-1.md": T1.replace("- **Discharges.** R-1", "- **Discharges.** R-1, R-2")
                        .replace("- **Scope.**\n  - `src/`", "- **Scope.** `src/`,\n  `README.md`"),
      "tasks/T-2.md": None},
     set()),
    # ...and a piece of it that is not a path is named, as a list item is.
    ("an-inline-scope-piece-that-is-not-a-path-is-named",
     {"tasks/T-1.md": T1.replace("- **Scope.**\n  - `src/`", "- **Scope.** src/ and its tests")},
     {"unreachable-acceptance"}, [], None, {"T-1's Scope."}),
    # ...and what stays CLEAN: an identifier field left empty is read as empty,
    # which is not a piece it failed to read.
    ("fp-an-empty-depends-on-is-empty-not-a-gap",
     {"tasks/T-2.md": T2.replace("- **Depends on.** T-1", "- **Depends on.**")},
     set()),

    # --- the requirement states a closed task could not say (L-2.4) --------
    # The owner's answer of 2026-09-24. pricelog left three requirements
    # `open` over closed tasks rather than write something untrue, and the
    # check refused all three (0.3.1 §3.5). Each is here in the new vocabulary,
    # and each still refused as plain `open`.
    #
    # 63674de: R-4 discharged but for three residuals a decision records.
    ("fp-l24-63674de-partly-discharged-over-the-closed-task",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("partly-discharged (T-1; D-1)")},
     set()),
    ("l24-63674de-written-as-open-is-still-refused",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("open")},
     {"one-sided-link"}),
    # ef8ee45: R-10 built and evidenced, and the judgement is the client's.
    ("fp-l24-ef8ee45-awaiting-judgement-over-the-closed-task",
     {"tasks/T-1.md": T1_DONE.replace("- **Discharges.** R-1", "- **Discharges.** R-1, R-2")
                             .replace("  - `src/`", "  - `src/`\n  - `README.md`"),
      "tasks/T-2.md": None,
      "REQUIREMENTS.md": statuses("discharged (T-1)", "awaiting-judgement (T-1; Q-1)")},
     set()),
    ("l24-ef8ee45-written-as-open-is-still-refused",
     {"tasks/T-1.md": T1_DONE.replace("- **Discharges.** R-1", "- **Discharges.** R-1, R-2")
                             .replace("  - `src/`", "  - `src/`\n  - `README.md`"),
      "tasks/T-2.md": None,
      "REQUIREMENTS.md": statuses("discharged (T-1)", "open")},
     {"one-sided-link"}),
    # 3bcf1f2: a second task's fix closed one violation and made another.
    ("fp-l24-3bcf1f2-partly-discharged-naming-both-closed-tasks",
     {"tasks/T-1.md": T1_DONE,
      "tasks/T-2.md": T2_DONE.replace("- **Discharges.** R-2", "- **Discharges.** R-1, R-2")
                             .replace("  - `README.md`", "  - `README.md`\n  - `src/`"),
      "REQUIREMENTS.md": statuses("partly-discharged (T-1, T-2; D-2)", "discharged (T-2)")},
     set()),
    ("l24-3bcf1f2-written-as-open-is-still-refused",
     {"tasks/T-1.md": T1_DONE,
      "tasks/T-2.md": T2_DONE.replace("- **Discharges.** R-2", "- **Discharges.** R-1, R-2")
                             .replace("  - `README.md`", "  - `README.md`\n  - `src/`"),
      "REQUIREMENTS.md": statuses("open", "discharged (T-2)")},
     {"one-sided-link"}),
    # A new status naming a task that does not list the requirement is the
    # requirement-side message, unchanged. T-2 is PLANNED, so nothing else can
    # fire.
    ("l24-a-new-status-naming-a-task-that-does-not-list-it-is-refused",
     {"tasks/T-1.md": T1_DONE,
      "REQUIREMENTS.md": statuses("discharged (T-1)", "partly-discharged (T-1; D-1)")},
     {"one-sided-link"}, [], None, set(),
     ["R-2 is partly-discharged (T-1; D-1), but T-1 does not list R-2 in its `Discharges.`"]),
    # ...and from the task's side, the status must name the closed task: a
    # partial discharge by somebody else says nothing about T-1. T-2 lists R-1,
    # so the requirement's side is two-sided and only T-1's link can fire.
    ("l24-a-closed-tasks-new-status-must-name-it",
     {"tasks/T-1.md": T1_DONE,
      "tasks/T-2.md": T2.replace("- **Discharges.** R-2", "- **Discharges.** R-1, R-2")
                        .replace("  - `README.md`", "  - `README.md`\n  - `src/`"),
      "REQUIREMENTS.md": statuses("partly-discharged (T-2; D-1)")},
     {"one-sided-link"}, [], None, set(),
     ["T-1 is DONE and discharges R-1, but R-1's status is 'partly-discharged (T-2; D-1)'"]),
    # Both are a CLOSED task's words: a running one still wants `in-progress`.
    ("l24-a-running-task-under-a-closed-tasks-status-is-still-refused",
     {"tasks/T-1.md": T1_RUNNING, "REQUIREMENTS.md": statuses("partly-discharged (T-1; D-1)")},
     {"one-sided-link"}),
    # RE-ESTABLISHES: T-17's shape. The requirement keeps its `discharged
    # (T-1)`, and the field is T-3's motivation.
    ("fp-l24-re-establishes-motivates-a-task-that-takes-no-discharge",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("discharged (T-1)"),
      "tasks/T-3.md": T3_RENEWS},
     set()),
    ("unmotivated-task-without-its-re-establishes",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("discharged (T-1)"),
      "tasks/T-3.md": T3_RENEWS.replace("- **Re-establishes.** R-1\n", "")},
     {"unmotivated-task"}, [], None, set(), ["name it in **Re-establishes.**"]),
    ("unknown-reference-re-establishes-a-requirement-nobody-declared",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("discharged (T-1)"),
      "tasks/T-3.md": T3_RENEWS.replace("- **Re-establishes.** R-1", "- **Re-establishes.** R-9")},
     {"unknown-reference"}),
    # T-17's own form, the reason inside the field: named, and the task is
    # then unmotivated by what was read.
    ("re-establishes-holding-prose-names-the-piece",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("discharged (T-1)"),
      "tasks/T-3.md": T3_RENEWS.replace("- **Re-establishes.** R-1",
                                        "- **Re-establishes.** R-1 — a fourth time")},
     {"unmotivated-task"}, [], None, {"T-3's Re-establishes."}),
    # A re-establishing task is not a discharging one: a status naming it is a
    # link its `Discharges.` does not return.
    ("one-sided-link-a-status-naming-a-task-that-only-re-establishes-it",
     {"tasks/T-1.md": T1_DONE, "REQUIREMENTS.md": statuses("discharged (T-1, T-3)"),
      "tasks/T-3.md": T3_RENEWS},
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
    # --- untracked files (roadmap 0.3.1, L-1.4) ----------------------------
    # THIS USED TO BE `fp-untracked-task-is-not-scanned`, asserting F-131's
    # defect: a task file in no commit was invisible, so what it discharged
    # read as uncovered and the file was never mentioned. It is now read --
    # R-3, discharged only by the untracked T-3, is covered -- and named.
    ("untracked-file-f131-a-new-task-is-read-and-named",
     {"REQUIREMENTS.md": REQS + """
### R-3 — it is fast

- **Statement.** it runs in a second.
- **Satisfies.** G-1
- **Source.** interview 2026-09-03
- **Acceptance.** `make bench` → `ok`
- **Requires-write.**
  - `bench/`
- **Priority.** should
- **Status.** open
""",
      "tasks/T-3.md": ("untracked", T1.replace("T-1 — make it work", "T-3 — make it fast")
                       .replace("- **Discharges.** R-1", "- **Discharges.** R-3")
                       .replace("  - `src/`", "  - `bench/`"))},
     {"untracked-file"}),
    # IGNORED FILES STAY INVISIBLE, whatever pattern they match.
    ("fp-an-ignored-task-file-produces-nothing",
     {"../.gitignore": ("untracked", "devteam/tasks/T-9.md\n"),
      "tasks/T-9.md": ("untracked", "# T-9 — scratch — PLANNED\n")},
     set()),
]


# --- accepted findings (roadmap 0.3.1, L-1.6) ------------------------------
# An accepted finding is a DECISION, and the check says so on its line. These
# are the plan's planted cases (§3.4) in fixture form: accepted exits 0 and is
# named; a finding nobody accepted still exits 1; an edit that moves the
# anchor does not un-accept it; a fixed finding leaves its acceptance STALE,
# which is a finding; and an acceptance outside the grammar accepts nothing.
# Each fails if the check reads an acceptance as a quiet exemption.

FINDING_LINE = r"^  (?!not evaluated: |excluded: |accepted by )(\S+)"

T1_NO_VERIFY = T1.replace("- **Verify.** `make test`\n", "")
_ACCEPT_VERIFY = "`check_trace` `missing-field` `tasks/T-1.md` — T-1 has no **Verify.**"


def decisions(*items, reviewed="unreviewed", more=""):
    """DECISIONS.md with one decision, D-1, accepting `items`."""
    field = "- **Accepts.**\n" + "".join(f"  - {i}\n" for i in items) if items else ""
    return f"""# Decisions

### D-1 — what T-1 leaves as it is

- **Decision.** it stays.
- **Because.** a fixture.
- **Alternatives declined.**
  - change it — a fixture.
- **Date.** 2026-09-24
- **Supersedes.** none
- **Reviewed.** {reviewed}
{field}{more}"""


ACCEPT_CASES = [
    # (name, overrides, extra args, exit, findings, accepted (D, class or
    #  part), parts not evaluated)
    ("accepted-finding-exits-0-and-the-line-names-the-decision",
     {"tasks/T-1.md": T1_NO_VERIFY, "DECISIONS.md": decisions(_ACCEPT_VERIFY)},
     [], 0, set(), {("D-1", "missing-field")}, set()),
    ("a-finding-nobody-accepted-still-exits-1",
     {"tasks/T-1.md": T1_NO_VERIFY, "DECISIONS.md": decisions(_ACCEPT_VERIFY),
      "tasks/T-2.md": T2.replace("- **Gate.** the README exists and is non-empty.\n", "")},
     [], 1, {"missing-field"}, {("D-1", "missing-field")}, set()),
    ("an-edit-that-moves-the-anchor-does-not-un-accept-it",
     {"tasks/T-1.md": "<!-- a note above the title -->\n\n" + T1_NO_VERIFY,
      "DECISIONS.md": decisions(_ACCEPT_VERIFY), "BOARD.md": BOARD.format(s1="—", s2="—")},
     [], 0, set(), {("D-1", "missing-field")}, set()),
    ("a-fixed-finding-leaves-its-acceptance-stale",
     {"DECISIONS.md": decisions(_ACCEPT_VERIFY)},
     [], 1, {"stale-acceptance"}, set(), set()),
    ("an-acceptance-outside-the-grammar-accepts-nothing",
     {"tasks/T-1.md": T1_NO_VERIFY,
      "DECISIONS.md": decisions(_ACCEPT_VERIFY.replace("`check_trace` ", "check_trace "))},
     [], 1, {"missing-field"}, set(), set()),
    ("a-decision-that-does-not-say-who-reviewed-it-accepts-nothing",
     {"tasks/T-1.md": T1_NO_VERIFY, "DECISIONS.md": decisions(_ACCEPT_VERIFY, reviewed="")},
     [], 1, {"missing-field"}, set(), set()),
    ("a-superseded-acceptance-accepts-nothing-and-is-not-stale",
     {"tasks/T-1.md": T1_NO_VERIFY, "DECISIONS.md": decisions(
         _ACCEPT_VERIFY, more="\n### D-2 — T-1 gets its Verify. after all\n\n"
                              "- **Decision.** add it.\n- **Supersedes.** D-1\n")},
     [], 1, {"missing-field"}, set(), set()),
    # A PART ACCEPTED: a board row naming two tasks, which the grammar reads as
    # neither. (It was F-70's link row until 0.3.2 read that form.)
    ("an-accepted-part-exits-0-and-is-named",
     {"BOARD.md": BOARD.format(s1="—", s2="—").replace("| T-2 |", "| T-2 and T-3 |"),
      "DECISIONS.md": decisions("`check_trace` not evaluated: BOARD.md's task rows")},
     [], 0, set(), {("D-1", "BOARD.md's task rows")}, set()),
    ("a-part-now-evaluated-leaves-its-acceptance-stale",
     {"DECISIONS.md": decisions("`check_trace` not evaluated: BOARD.md's task rows")},
     [], 1, {"stale-acceptance"}, set(), set()),
    # EXCLUDED IS NOT EVALUATED (L-1.2), so --pre-plan cannot judge an
    # acceptance of the class it holds back -- and without the flag, the
    # same acceptance is applied.
    ("fp-pre-plan-does-not-judge-an-acceptance-of-the-class-it-excludes",
     {"tasks/T-2.md": None, "DECISIONS.md": decisions(
         "`check_trace` `uncovered-requirement` `REQUIREMENTS.md` — R-2 is not discharged by any task")},
     ["--pre-plan"], 0, set(), set(), set()),
    ("fp-without-pre-plan-the-same-acceptance-is-applied",
     {"tasks/T-2.md": None, "DECISIONS.md": decisions(
         "`check_trace` `uncovered-requirement` `REQUIREMENTS.md` — R-2 is not discharged by any task")},
     [], 0, set(), {("D-1", "uncovered-requirement")}, set()),
    ("fp-an-acceptance-of-another-check-changes-nothing-here",
     {"DECISIONS.md": decisions("`check_refs` `broken-link` `tasks/T-1.md` — missing.md")},
     [], 0, set(), set(), set()),
    ("fp-a-decisions-file-with-no-acceptance-changes-nothing",
     {"DECISIONS.md": decisions()},
     [], 0, set(), set(), set()),
]


_TITLE = re.compile(r"^#\s+(T-\d+)\s+[—–-]\s+(.*?)\s+[—–-]\s+(\S+)")
_STATE = {"PLANNED": "—", "RUNNING": "CLAIMED T-a-1200", "DONE": "DONE",
          "ACCEPTED": "ACCEPTED (2026-09-05, D-41)", "BLOCKED": "BLOCKED on Q-1",
          "NEEDS-DECISION": "BLOCKED on Q-1"}


def board_for(files):
    """A BOARD.md that agrees with every tracked task title in the fixture.

    A project always has a board, and a missing one is now a part not
    evaluated (roadmap 0.3.1, L-1.3), so a case that says nothing about the
    board gets one that board-drift reads and finds nothing wrong with. A case
    testing the board supplies its own, and `"BOARD.md": None` removes it.
    """
    rows = []
    for name, body in sorted(files.items()):
        m = _TITLE.match(body) if name.startswith("tasks/") else None
        if m:
            rows.append(f"| {m.group(1)} | {m.group(2)} | — | — | — | "
                        f"{_STATE.get(m.group(3), '—')} |")
    return ("# The board\n\n| Task | Title | Discharges | Depends on | Scope | State |\n"
            "|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")


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
    if "BOARD.md" not in overrides:
        files["BOARD.md"] = board_for(files)

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
        # The parts the case expects NOT EVALUATED (roadmap 0.3.1, L-1.3),
        # compared as a set like the findings: a part named that the case did
        # not plant fails it as surely as a missing one.
        want_gaps = case[5] if len(case) > 5 else set()
        # Text the output must carry, where the case is about what a part or
        # a finding SAYS (roadmap 0.3.2, L-2.3's "the part names the piece").
        must = case[6] if len(case) > 6 else ()
        root = tempfile.mkdtemp(prefix="devteam-trace-")
        try:
            dt = build(root, overrides, prior)
            proc = subprocess.run([sys.executable, CHECK, *extra, dt],
                                  capture_output=True, text=True)
            got = set(re.findall(FINDING_LINE, proc.stdout, re.M))
            got_gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            want_exit = 1 if expected else (3 if want_gaps else 0)
            # HELD BACK IS NOT CLEAN (roadmap 0.3.1, L-1.2): `--pre-plan`
            # excludes one class by the caller's declaration, so the line must
            # NAME it and how many it held back, or an onboarding gate that
            # hid sixteen uncovered requirements would read like one that had
            # none.
            named = ("--pre-plan" not in extra or re.search(
                r"^  excluded: uncovered-requirement — by --pre-plan \(\d+ held back\)$",
                proc.stdout, re.M) is not None)
            unsaid = [s for s in must if s not in proc.stdout]
            if (got == expected and got_gaps == want_gaps
                    and proc.returncode == want_exit and named and not unsaid):
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} "
                      f"not evaluated {sorted(want_gaps) or 'none'} exit {want_exit}")
                print(f"        got      {sorted(got) or 'clean'} "
                      f"not evaluated {sorted(got_gaps) or 'none'} exit {proc.returncode}")
                for s in unsaid:
                    print(f"        missing  {s!r}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # THE PROJECT GATE (0.2.7, docs/PAIRS.md row 21). These two run outside the
    # CASES loop because that loop always builds a devteam/ directory and hands
    # it over, so it structurally cannot express "there is no project here" --
    # which is precisely why the gap survived a full cycle.
    #
    # The pair matters more than either half. The first alone would pass if the
    # check refused EVERYTHING; the second alone would pass if it refused
    # nothing, which is the shipped behaviour being corrected. Only together do
    # they discriminate.
    # THE TARGET MUST BE A GIT REPOSITORY OR THIS CASE IS VACUOUS, and the
    # first draft of it was. `check()` returns None for a non-repository and
    # main() already exits 2 for that -- so a bare mkdtemp exits 2 whether the
    # project gate exists or not, and the case passed against the mutation that
    # deletes the gate. An earlier branch returning before the code under test
    # runs is 0.2.5's vacuous-control shape, and this is its sixth instance.
    def _bare_repo(root):
        subprocess.run(["git", "init", "-q", root], check=True)
        return root

    gate = [
        ("not-a-devteam-project-is-exit-2-not-sixteen-findings",
         _bare_repo, 2),
        ("fp-a-real-project-still-reports-its-real-findings",
         lambda root: build(root, {"CHARTER.md": CHARTER.replace("G-2", "G-9")}), 1),
    ]
    for name, make, want_exit in gate:
        root = tempfile.mkdtemp(prefix="devteam-trace-gate-")
        try:
            target = make(root)
            proc = subprocess.run([sys.executable, CHECK, target],
                                  capture_output=True, text=True)
            if proc.returncode == want_exit:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected exit {want_exit}, got {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n")[:4]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # WHAT THE CASES LOOP CANNOT BUILD: the check's own inputs gone, and a
    # history cut short. Both used to report clean (roadmap 0.3.1, L-1.3).
    #
    # The first is the silent zero 0.3.1's mutation run found: this check read
    # its template rows as `template_names(...) or []`, so a check run from a
    # copy of scripts/ with no templates/ beside it compared the charter
    # against nothing and said clean. The copy is of the WHOLE scripts/
    # directory, so the one thing missing is the templates.
    def _no_templates(root):
        plugin = os.path.join(root, "plugin")
        shutil.copytree(os.path.dirname(CHECK), os.path.join(plugin, "scripts"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(CHECK, os.path.join(plugin, "scripts", "check_trace.py"))
        return (os.path.join(plugin, "scripts", "check_trace.py"),
                build(os.path.join(root, "p"), {}))

    def _shallow(root):
        build(os.path.join(root, "p"), {}, [REQS])
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        "file://" + os.path.join(root, "p"), os.path.join(root, "s")],
                       check=True, capture_output=True)
        return CHECK, os.path.join(root, "s", "devteam")

    inputs = [
        ("templates-unreadable-is-not-evaluated-not-clean", _no_templates,
         {"template-drift", "missing-field in requirements", "missing-field in tasks"}),
        ("a-shallow-clone-reads-a-history-that-starts-partway", _shallow,
         {"REQUIREMENTS.md's history"}),
    ]
    for name, make, want_gaps in inputs:
        root = tempfile.mkdtemp(prefix="devteam-trace-inputs-")
        try:
            check, target = make(root)
            proc = subprocess.run([sys.executable, check, target],
                                  capture_output=True, text=True)
            got_gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            got = set(re.findall(FINDING_LINE, proc.stdout, re.M))
            if got_gaps == want_gaps and not got and proc.returncode == 3:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected not evaluated {sorted(want_gaps)} exit 3")
                print(f"        got      {sorted(got) or 'clean'} "
                      f"not evaluated {sorted(got_gaps) or 'none'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n")[:6]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    for name, overrides, extra, want_exit, expected, want_acc, want_gaps in ACCEPT_CASES:
        root = tempfile.mkdtemp(prefix="devteam-trace-accept-")
        try:
            dt = build(root, overrides)
            proc = subprocess.run([sys.executable, CHECK, *extra, dt],
                                  capture_output=True, text=True)
            out = proc.stdout
            got = set(re.findall(FINDING_LINE, out, re.M))
            got_acc = (set(re.findall(r"^  accepted by (D-\d+): not evaluated: (.+?) — ", out, re.M))
                       | set(re.findall(r"^  accepted by (D-\d+): (?!not evaluated: )(\S+)", out, re.M)))
            got_gaps = set(re.findall(r"^  not evaluated: (.+?) — ", out, re.M))
            # The head line says how many were accepted, and by which decision,
            # so a zero reached by accepting never reads as a zero reached by
            # fixing -- and an accepted part never claims the whole was read.
            head = out.split("\n", 1)[0]
            said = (not want_acc or f", {len(want_acc)} accepted by D-1" in head) and not (
                any(" " in p or "'" in p for _, p in want_acc) and "traced end to end" in head)
            if (proc.returncode == want_exit and got == expected and got_acc == want_acc
                    and got_gaps == want_gaps and said):
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected exit {want_exit} {sorted(expected) or 'clean'} "
                      f"accepted {sorted(want_acc) or 'none'}")
                print(f"        got      exit {proc.returncode} {sorted(got) or 'clean'} "
                      f"accepted {sorted(got_acc) or 'none'}")
                for line in (out + proc.stderr).strip().split("\n")[:8]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- a checkout of one commit (roadmap 0.3.1, L-1.5) -------------------
    # `--at-commit` excludes the classes that read the working state, by the
    # caller's declaration, and names each. So an untracked file -- which a clean
    # checkout of a commit never holds -- is a finding without the flag, and
    # with it is excluded, named, and leaves the rest to decide the exit.
    root = tempfile.mkdtemp(prefix="devteam-trace-")
    try:
        build(root, {"audits/scratch.md": ("untracked", "notes, not an audit\n")})
        live = subprocess.run([sys.executable, CHECK, root], capture_output=True, text=True)
        at = subprocess.run([sys.executable, CHECK, root, "--at-commit"], capture_output=True, text=True)
        ok = (live.returncode == 1 and re.search(r"^  untracked-file\s", live.stdout, re.M)
              and at.returncode == 0 and not re.search(r"^  untracked-file\s", at.stdout, re.M)
              and re.search(r"^  excluded: untracked-file — by --at-commit", at.stdout, re.M))
        if ok:
            passed += 1
        else:
            failed += 1
            print("FAIL  at-commit-excludes-the-working-state-and-names-it")
            for line in (live.stdout + at.stdout + at.stderr).strip().split("\n")[:8]:
                print(f"        | {line}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # COUNTED FROM WHAT RAN, not from len(CASES). The gate cases above are not
    # in that list, and a hand-maintained total that disagrees with the number
    # of cases executed is the exact defect docs/CHECKS.md exists to stop.
    total = passed + failed
    fp = sum(1 for c in CASES + ACCEPT_CASES if c[0].startswith("fp-") or c[0] == "clean") + 1
    print(f"\ncheck_trace control: {passed} passed, {failed} failed, "
          f"{total} cases ({fp} of them false-positive controls, "
          f"{100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
