#!/usr/bin/env python3
"""Negative control for check_refs.py (P-35).

Plants exactly one fault per finding class and requires exactly that class
back. Then plants a set of things that LOOK like faults and must not be
reported at all -- because a check that cries wolf on legitimate work gets
switched off by whoever it obstructs, which is strictly worse than no check.
Those false-positive controls are deliberately more than a third of the cases.

Run it: python3 test_check_refs.py     Exit 0 all pass, 1 any fail.
"""
import json
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
CHECK = (os.environ.get("DEVTEAM_SUBJECT_CHECK_REFS")
        or os.path.join(HERE, "check_refs.py"))

FIXTURE = {
    "CHARTER.md": """# Charter — Fixture

## Goals

- **G-1** — the thing works

## Constraints

| Constraint | Value |
|---|---|
| Licence | Apache-2.0 |
""",
    "REQUIREMENTS.md": """# Requirements

### R-1 — it works

- **Statement.** the thing works when run.
- **Satisfies.** G-1
- **Source.** interview 2026-09-03
- **Acceptance.** `make test` → `ok`
- **Priority.** must
- **Status.** open
""",
    "DECISIONS.md": """# Decisions

### D-1 — make over cmake

- **Decision.** the build is a Makefile.
- **Because.** the project has one artifact.
- **Alternatives declined.**
  - cmake — heavier than one artifact justifies
- **Date.** 2026-09-03
- **Supersedes.** none
- **Reviewed.** client
""",
    "QUESTIONS.md": """# Open questions

### Q-1 — which formatter?

- **Class.** REVERSIBLE
- **Recommendation.** black, because it is not configurable and so cannot drift.
- **Evidence.** none needed.
- **Raised.** 2026-09-03 by T-1
- **Status.** open
""",
    "RECORD.md": """# The record

Append-only. Findings are declared here as `- **F-n** — <one line>`.

## 2026-09-04

- first entry
""",
    "tasks/T-1.md": """# T-1 — make it work — PLANNED

- **Discharges.** R-1
- **Depends on.** none
- **Scope.**
  - `src/`
- **Gate.** the test command exits zero.
- **Verify.** `make test`
- **Estimate.** tokens=1000 minutes=10

Per D-1 the build is a Makefile.

## Steps

- [ ] **S-1** — write it · class: `standard` · verify: `make test`

## Execution record
""",
}


def append(name, text):
    return ("append", name, text)


def create(name, text):
    return ("create", name, text)


def replace(name, old, new):
    return ("replace", name, old, new)



# --- the audit namespace (0.2.6) -----------------------------------------
# Three-letter prefixes were chosen BECAUSE the scanner could not mistake them
# for citations, which is the same fact as the scanner being unable to check
# them. 0.2.6 reserved five and watches them; everything else three-letter is
# still ignored, and these cases pin BOTH halves.

AUDIT_OPEN = """# T-1 security audit

## SEC-1 — the input is not bounded

- **Disposition.** open

Prose about the finding.
"""

AUDIT_NONE = """# T-1 security audit

## SEC-1 — the input is not bounded

Prose about the finding, and no disposition line anywhere.
"""

AUDIT_ROUTED = """# T-1 security audit

## SEC-1 — the input is not bounded

- **Disposition.** routed T-1

Prose about the finding.
"""

# (case name, [mutations], expected finding kinds)
CASES = [
    # --- one fault per class, and exactly that class back -----------------
    ("clean", [], set()),
    ("broken-link", [append("CHARTER.md", "\nSee [the plan](nowhere.md).\n")],
     {"broken-link"}),
    ("duplicate-id", [append("REQUIREMENTS.md", "\n### R-1 — declared twice\n\n- **Status.** open\n")],
     {"duplicate-id"}),
    ("cited-undefined", [append("CHARTER.md", "\nThis is required by R-99.\n")],
     {"cited-undefined"}),
    ("defined-uncited", [append("DECISIONS.md",
        "\n### D-2 — nothing cites this\n\n- **Decision.** a rule nobody attributed.\n- **Date.** 2026-09-03\n")],
     {"defined-uncited"}),
    ("bad-status-requirement", [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** nearly")],
     {"bad-status"}),
    ("bad-status-task", [replace("tasks/T-1.md", "— PLANNED", "— NEARLY DONE")],
     {"bad-status"}),
    ("leak-home-path", [append("CHARTER.md", "\nBuilt from /home/someone/project/src.\n")],
     {"leak"}),
    ("leak-token", [append("CHARTER.md", "\nToken ghp_abcdefghijklmnopqrstuvwxyz0123456789 here.\n")],
     {"leak"}),

    # --- P-47: a bare CR is content the reading does not show -------------
    # 0.2.6 shipped P-47 saying "outside tab and newline" against code that
    # permitted CR anywhere, so a tracked file with a bare mid-line CR passed
    # clean while the rule forbade it. The rule and the code disagreed, in the
    # subcycle whose purpose was making them agree.
    ("control-character-bare-cr-midline",
     [append("CHARTER.md", "\nA line with a stray\rcarriage return.\n")],
     {"control-character"}),
    # A CRLF FILE IS NOT A DEFECT. Splitting on \n leaves the CR last on every
    # line, so a rule that forbade CR outright would report every line of every
    # file written on a platform that uses CRLF -- the false positive that gets
    # a check disabled (P-35).
    ("fp-crlf-line-endings-are-not-control-characters",
     [("tracked", "notes.md", "# Notes\r\n\r\nOrdinary CRLF text.\r\n")],
     set()),

    # --- the audit namespace (0.2.6) -------------------------------------
    ("undispositioned-finding-no-line",
     [("tracked", "audits/T-1-security-2026-09-04.md", AUDIT_NONE)],
     {"undispositioned-finding"}),
    ("undispositioned-finding-still-open",
     [("tracked", "audits/T-1-security-2026-09-04.md", AUDIT_OPEN)],
     {"undispositioned-finding"}),
    ("cited-undefined-audit-finding",
     [("tracked", "audits/T-1-security-2026-09-04.md", AUDIT_ROUTED),
      append("CHARTER.md", "\nThis rests on COR-99.\n")],
     {"cited-undefined"}),
    ("duplicate-id-audit-finding",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_ROUTED + "\n## SEC-1 — declared twice\n\n- **Disposition.** routed T-1\n")],
     {"duplicate-id"}),

    # --- FALSE-POSITIVE CONTROLS for the namespace ------------------------
    ("fp-audit-finding-routed-is-clean",
     [("tracked", "audits/T-1-security-2026-09-04.md", AUDIT_ROUTED)],
     set()),
    # `defined-uncited` MUST NOT fire on an audit finding. A finding nobody
    # cites is the ordinary state of one that has been filed; the thing that
    # matters is whether it was DISPOSITIONED. Audit prefixes are therefore
    # kept out of MUST_BE_CITED, and this case is what says so.
    ("fp-dispositioned-and-uncited-is-not-defined-uncited",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_ROUTED.replace("routed T-1", "declined (D-1)"))],
     set()),
    # A CITATION IS NOT AN ESCAPE FROM A DISPOSITION, and this is the case that
    # pins it. 0.2.6 planned the rule as "cited OR dispositioned" and measured
    # it over a real project: ZERO findings, against five that carried no
    # Disposition line at all -- because every one was mentioned in RECORD.md.
    # Mention is not disposition (CONSOLIDATION 7). If the citation half is
    # ever restored as an escape, this case fails.
    ("undispositioned-even-though-cited",
     [("tracked", "audits/T-1-security-2026-09-04.md", AUDIT_OPEN),
      append("RECORD.md", "\nThe audit raised SEC-1 and we discussed it.\n")],
     {"undispositioned-finding"}),
    # EVERY OTHER THREE-LETTER PREFIX IS STILL IGNORED, deliberately and by
    # name. The scanner reads [A-Z]{1,3} and then discards anything whose
    # prefix is not reserved -- which is why `UTF-8` is not a citation. Widening
    # the regex without this half is what turns a green tree into dozens of
    # findings at once (F-63, F-64).
    ("fp-unreserved-three-letter-prefixes-are-ignored",
     [append("CHARTER.md",
             "\nEncoded as UTF-8 per RFC-2119, hashed with SHA-256, see ABC-1.\n")],
     set()),

    # --- FALSE-POSITIVE CONTROLS: legitimate work, must stay clean --------
    # A check that reports these is a check somebody will disable (P-35).
    ("fp-fenced-code-is-not-a-citation",
     [append("CHARTER.md", "\n```\ngrep R-99 file.txt\n```\n")], set()),
    ("fp-protocol-rule-is-external",
     [append("CHARTER.md", "\nThe manager owns this file (P-13), per P-1 and P-42.\n")], set()),
    ("fp-answered-question-status",
     [replace("QUESTIONS.md", "- **Status.** open", "- **Status.** answered D-1")], set()),
    ("fp-running-task-title",
     [replace("tasks/T-1.md", "— PLANNED", "— RUNNING (since 2026-09-03, T1-mk-1200)")], set()),
    # The title vocabulary and the REPORT vocabulary overlap in meaning and not
    # in spelling. `BLOCKED (<why>)` means "waiting on a named task" by design,
    # so a task stopped on a question for the client had no title state at all
    # -- while the report status the supervisor had just written has exactly
    # the right word. One reached for `NEEDS-DECISION` and was told it was a
    # bad status for using the correct term for its situation.
    # --- steps are numbered PER TASK -------------------------------------
    # Flattening the namespace made an `S-n` resolve against ANY task that
    # declared that number, so a task whose steps were written in an
    # unrecognised form declared none of its own and passed on other tasks'
    # declarations. Only the first number nobody had ever used reported.
    ("cited-undefined-step-declared-only-in-another-task",
     [create("tasks/T-2.md", """# T-2 — a second task — PLANNED

- **Discharges.** R-1
- **Depends on.** T-1
- **Scope.**
  - `docs/`
- **Gate.** it is written.
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5

## Steps

This task cites `S-1` in prose and declares no step in any form, so the
identifier resolves nowhere in this file — it used to resolve against T-1's.
""")],
     {"cited-undefined"}),
    # The table form DOES declare. Three tasks in one project wrote their
    # steps this way rather than as a checklist, because a rich step carries a
    # class, a role and a verify command and those are columns.
    ("fp-table-form-step-declares-its-own-number",
     [create("tasks/T-2.md", """# T-2 — a second task — PLANNED

- **Discharges.** R-1
- **Depends on.** T-1
- **Scope.**
  - `docs/`
- **Gate.** it is written.
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5

## Steps

| Step | What | Verify |
|---|---|---|
| S-1 | write the thing, discharging R-1 | `true` |

S-1 is the only step.
""")],
     set()),
    ("fp-step-cited-inside-the-task-that-declares-it",
     [append("tasks/T-1.md", "\n`S-1` is the step above.\n")], set()),
    # The record legitimately discusses steps in prose. A bare `S-2` there
    # names no task and cannot be resolved -- firing on it would be firing on
    # prose, and a check that does that gets turned off.
    ("fp-bare-step-in-prose-outside-a-task-file",
     [append("RECORD.md", "\n- S-2 was the tricky one\n")], set()),
    # ...but the QUALIFIED form names its task, so it resolves, and must.
    ("fp-qualified-step-that-exists",
     [append("RECORD.md", "\n- T-1.S-1 landed clean\n")], set()),
    ("cited-undefined-qualified-step-that-does-not-exist",
     [append("RECORD.md", "\n- T-1.S-9 landed clean\n")], {"cited-undefined"}),
    # THE QUALIFIED FORM MUST NOT CITE ITSELF TWICE. `CITATION` finds both
    # `T-2` and `S-7` inside `T-2.S-7`, and the bare half was charged to the
    # CITING file -- so the one form offered for a cross-task step reference
    # fired against the task using it. Every control above uses the form
    # either outside a task file or on a task declaring the same number, which
    # are exactly the two cases where the defect cannot show.
    ("fp-qualified-step-cited-from-a-task-that-declares-no-such-number",
     [create("tasks/T-2.md", """# T-2 — a second task — PLANNED

- **Discharges.** R-1
- **Depends on.** T-1
- **Scope.**
  - `docs/`
- **Gate.** it is written.
- **Verify.** `true`
- **Estimate.** tokens=100 minutes=5

## Steps

- [ ] **S-7** — the step this task does declare · verify: `true`
"""),
      append("tasks/T-1.md", "\nThe refactor is T-2.S-7's, declined by it.\n")],
     set()),

    # REPORTING A FINDING MUST NOT CREATE ONE. A supervisor quoted a check's
    # output verbatim in its report -- the right thing to do -- and the scanner
    # read the quoted identifier as a citation against the quoting file. It
    # would recur in every task file that ever quotes output naming an
    # unresolvable identifier.
    ("fp-quoted-check-output-is-not-a-citation",
     [append("tasks/T-1.md",
             "\n`check_refs` reports `cited-undefined  tasks/T-9.md:67  S-8`.\n")],
     set()),
    # ...and the blanking must not swallow real citations on the same line.
    ("fp-a-real-citation-beside-quoted-output-still-counts",
     [append("tasks/T-1.md",
             "\nPer D-1, `cited-undefined  tasks/T-9.md:67  S-8` is pre-existing.\n")],
     set()),
    # P-2 lets the client close a task that failed verification. Nothing in the
    # vocabulary could say so, so the board said `DONE` -- glossed as "closed,
    # verified, and released" -- about a task that was not verified.
    ("fp-accepted-task-title",
     [replace("tasks/T-1.md", "— PLANNED", "— ACCEPTED (2026-09-05, D-41)")], set()),
    ("bad-status-accepted-without-its-decision",
     [replace("tasks/T-1.md", "— PLANNED", "— ACCEPTED")], {"bad-status"}),
    ("fp-needs-decision-task-title",
     [replace("tasks/T-1.md", "— PLANNED", "— NEEDS-DECISION (R-7 narrows G-3; charter-adjacent)")], set()),
    # ...and it still needs its parenthetical, like BLOCKED and DONE. A bare
    # state that cannot say WHY is the "waiting" the board legend forbids.
    ("bad-status-needs-decision-without-a-reason",
     [replace("tasks/T-1.md", "— PLANNED", "— NEEDS-DECISION")], {"bad-status"}),
    ("fp-done-task-title",
     [replace("tasks/T-1.md", "— PLANNED", "— DONE (2026-09-03)")], set()),
    ("fp-valid-relative-link",
     [append("CHARTER.md", "\nSee [the requirements](REQUIREMENTS.md).\n")], set()),
    ("fp-link-with-anchor",
     [append("CHARTER.md", "\nSee [goals](REQUIREMENTS.md#r-1).\n")], set()),
    ("fp-hyphen-instead-of-em-dash",
     [append("DECISIONS.md", "\n### D-3 - hyphen declares too\n\n- **Decision.** yes.\n"),
      append("tasks/T-1.md", "\nAlso per D-3.\n")], set()),
    ("fp-teaching-placeholder-is-not-a-status",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** <open | discharged (T-n)>")], set()),
    ("fp-version-numbers-are-not-citations",
     [append("CHARTER.md", "\nApache-2.0, UTF-8, SHA-256, ISO-8601, Python 3.12.\n")], set()),
    # F-50: a requirement advanced by one task and completed by another could
    # not be expressed, so the record had to say something untrue.
    ("fp-in-progress-across-two-tasks",
     [("tracked", "tasks/T-2.md", "# T-2 — the second — PLANNED\n\n- **Discharges.** R-1\n"),
      ("tracked", "tasks/T-5.md", "# T-5 — the fifth — PLANNED\n\n- **Discharges.** R-1\n"),
      replace("REQUIREMENTS.md", "- **Status.** open",
              "- **Status.** in-progress (T-2, T-5)")],
     set()),
    ("fp-discharged-by-two-tasks",
     [("tracked", "tasks/T-2.md", "# T-2 — the second — PLANNED\n\n- **Discharges.** R-1\n"),
      ("tracked", "tasks/T-5.md", "# T-5 — the fifth — PLANNED\n\n- **Discharges.** R-1\n"),
      replace("REQUIREMENTS.md", "- **Status.** open",
              "- **Status.** discharged (T-2, T-5)")],
     set()),
    ("bad-status-still-caught-with-a-task-list",
     [("tracked", "tasks/T-2.md", "# T-2 — the second — PLANNED\n\n- **Discharges.** R-1\n"),
      ("tracked", "tasks/T-5.md", "# T-5 — the fifth — PLANNED\n\n- **Discharges.** R-1\n"),
      replace("REQUIREMENTS.md", "- **Status.** open",
              "- **Status.** nearly (T-2, T-5)")],
     {"bad-status"}),
    # L-2.4 (roadmap 0.3.2, the owner's answer of 2026-09-24): the two states a
    # closed task could not say, which pricelog wrote as `open` rather than say
    # something untrue. Each names its tasks, then the one decision recording
    # what remains or the one question the judgement waits on.
    ("fp-l24-partly-discharged-names-its-decision",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** partly-discharged (T-1; D-1)")],
     set()),
    ("fp-l24-awaiting-judgement-names-its-question",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** awaiting-judgement (T-1; Q-1)")],
     set()),
    ("fp-l24-several-tasks-before-the-decision",
     [("tracked", "tasks/T-2.md", "# T-2 — the second — PLANNED\n\n- **Discharges.** R-1\n"),
      replace("REQUIREMENTS.md", "- **Status.** open",
              "- **Status.** partly-discharged (T-1, T-2; D-1)")],
     set()),
    # ...and the parenthetical holds identifiers only: what remains is written
    # in the decision or the question, never beside the status.
    ("bad-status-l24-partly-discharged-without-its-decision",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** partly-discharged (T-1)")],
     {"bad-status"}),
    ("bad-status-l24-awaiting-judgement-naming-a-decision-not-a-question",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** awaiting-judgement (T-1; D-1)")],
     {"bad-status"}),
    ("bad-status-l24-what-remains-written-beside-the-status",
     [replace("REQUIREMENTS.md", "- **Status.** open",
              "- **Status.** partly-discharged (T-1; D-1) — three residuals")],
     {"bad-status"}),
    # F-55: findings are the largest numbered set a project accumulates and had
    # no integrity check at all — a signed charter cited a finding that was
    # never declared anywhere, and the tree reported clean.
    ("cited-undefined-finding",
     [append("CHARTER.md", "\nThe reasoning for this is F-9 in the record.\n")],
     {"cited-undefined"}),
    ("fp-declared-finding-may-be-cited",
     [append("RECORD.md", "\n- **F-9** — a client is not an operator\n"),
      append("CHARTER.md", "\nThe reasoning for this is F-9 in the record.\n")],
     set()),
    ("fp-a-finding-need-not-be-cited-by-anything",
     [append("RECORD.md", "\n- **F-9** — a client is not an operator\n")], set()),
    ("fp-in-progress-status",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** in-progress (T-1)")], set()),
    ("fp-struck-question-keeps-its-decision",
     [replace("QUESTIONS.md", "- **Status.** open", "- **Status.** proceeded-unreviewed D-1")], set()),
    ("fp-template-is-not-project-state",
     [("tracked", "templates/tasks/TASK.md",
       "# T-<n> — blank form — PLANNED\n\n- **Discharges.** R-4\n\nPer D-9.\n"),
      ("tracked", "NOTES.md", "Scratch thinking about R-99 and D-7.\n")], set()),
    ("links-and-leaks-are-checked-outside-artifacts-too",
     [("tracked", "NOTES.md", "See [gone](nope.md) at /home/someone/x/\n")],
     {"broken-link", "leak"}),
    # A title's status is its LAST segment. A hyphenated word or a date in the
    # middle used to split it and yield the tail of the wrong segment.
    ("fp-hyphenated-title-text-does-not-split-the-status",
     [replace("tasks/T-1.md", "# T-1 — make it work — PLANNED",
              "# T-1 — the well-known parser — DONE (2026-09-03)")], set()),
    ("fp-checkpoint-title-with-a-date",
     [("tracked", "checkpoints/C-1-2026-09-03.md", "# C-1 — 2026-09-03 — DRIFTED\n")], set()),
    ("bad-checkpoint-verdict",
     [("tracked", "checkpoints/C-1-2026-09-03.md", "# C-1 — 2026-09-03 — MOSTLY FINE\n")],
     {"bad-status"}),
    # Found by a security audit: check_refs reported clean on a tree with four
    # absolute session paths baked into a committed task record.
    ("leak-path-encoded-home",
     [append("CHARTER.md", "\nSee /tmp/claude-1000/-home-randy-Workspace-REPOS-x/notes.md\n")],
     {"leak"}),
    ("leak-session-uuid-under-tmp",
     [append("CHARTER.md",
             "\nBuilt at /tmp/x/eb56900f-edd4-4078-968d-b099be23b975/scratchpad/a.txt\n")],
     {"leak"}),
    ("fp-ordinary-tmp-path-is-not-a-leak",
     [append("CHARTER.md", "\nScratch output goes to /tmp/wordfreq-build/out.txt\n")], set()),
    ("fp-hyphenated-words-are-not-encoded-home-paths",
     [append("CHARTER.md", "\nA well-home-grown approach; see at-home-testing notes.\n")], set()),
    # F-13: a document that CONTAINS a control byte rather than naming it is
    # committed as binary, so git produces no diff for it and the audit
    # discipline of diffing a document against what it describes has nothing
    # to work with. Decoding succeeds, so nothing else noticed.
    ("control-character-nul",
     [("tracked", "research/limits.md", "The NUL byte \x00 terminates a C string.\n")],
     {"control-character"}),
    ("control-character-escape",
     [("tracked", "research/term.md", "ESC \x1b[2J clears the screen.\n")],
     {"control-character"}),
    # Renamed in 0.2.6's repair: the CR here is a LINE ENDING, which is what
    # makes it ordinary. A CR is not ordinary anywhere — a bare mid-line one is
    # reported, and `control-character-bare-cr-midline` is the case for it.
    ("fp-tabs-are-ordinary-and-a-trailing-cr-is-a-line-ending",
     [("tracked", "research/table.md", "a\tb\tc\r\nd\te\tf\n")], set()),
    ("fp-naming-a-byte-is-not-embedding-it",
     [("tracked", "research/limits.md",
       "The NUL byte U+0000 (written `\\x00`) terminates a C string.\n")], set()),
    ("fp-directory-readme-is-not-an-artifact",
     [("tracked", "tasks/README.md",
       "One file per task, named `T-1.md`. See `C-1-<date>.md` for checkpoints.\n"),
      ("tracked", "research/README.md", "Digests live here; see D-9 for the policy.\n")],
     set()),
    # --- untracked files (roadmap 0.3.1, L-1.4) ----------------------------
    # THIS CASE USED TO BE `fp-untracked-file-is-not-scanned`, and asserted
    # F-131's defect: a file under devteam/ that is in no commit was invisible
    # to the check. It is now read -- its link and its leak are found -- and
    # named. Its `R-99` is still no citation, because SCRATCH.md is not one of
    # the artifacts the identifier grammar governs.
    ("untracked-file-is-read-and-named",
     [("untracked", "SCRATCH.md", "Broken [link](nope.md) and R-99 and /home/x/y/\n")],
     {"untracked-file", "broken-link", "leak"}),
    # F-131's own (pricelog RECORD.md:1641-1642): a new task file untracked
    # while another file cites it. Its declaration is read, so there is no
    # `cited-undefined`, and the file is named.
    ("untracked-file-f131-a-new-task-another-file-cites",
     [("untracked", "tasks/T-2.md", "# T-2 — a new task — PLANNED\n\n- **Discharges.** R-1\n"),
      append("RECORD.md", "- T-2 is planned next.\n")],
     {"untracked-file"}),
    # ...and one nothing cites, which used to be "not checked at all".
    ("untracked-file-a-new-task-nothing-cites",
     [("untracked", "tasks/T-3.md", "# T-3 — another — PLANNED\n\n- **Discharges.** R-1\n")],
     {"untracked-file"}),
    # IGNORED FILES STAY INVISIBLE: devteam/.run/ is ignored in every project.
    ("fp-an-ignored-file-under-run-produces-nothing",
     [("ignore", "devteam/.run/"),
      ("untracked", ".run/notes.md", "Broken [link](nope.md) and /home/x/y/\n")],
     set()),

    # --- zero rows, partial reads and wrapped fields (roadmap 0.3.1, L-1.3) --
    # A fourth element names the parts expected NOT EVALUATED. Each case here
    # used to report clean.
    #
    # ZERO ROWS: an audit whose every finding is outside the namespace --
    # pricelog's four gate audits, which `undispositioned-finding` never saw
    # (register A6, F-99).
    ("zero-rows-an-audit-in-no-finding-namespace",
     [("tracked", "audits/T-1-safety-2026-09-04.md",
       "# T-1 safety audit\n\n## Finding 1 (HIGH) — the log can be truncated\n\nProse.\n\n"
       "## Finding 2 (LOW) — a message is vague\n\nProse.\n")],
     set(), {"audits/T-1-safety-2026-09-04.md's findings"}),
    # A PARTIAL READ: one finding outside the namespace among one inside it.
    ("partial-read-one-audit-finding-outside-the-namespace",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_ROUTED + "\n## SAF-2 — a second finding, another prefix\n\nProse.\n")],
     set(), {"audits/T-1-security-2026-09-04.md's findings"}),
    # A declaration written wrong declares nothing, so its own line reads as a
    # citation of what it failed to declare -- the finding, and the old
    # behaviour. The gap names the line that caused it.
    ("partial-read-a-decision-declared-with-a-colon",
     [append("DECISIONS.md", "\n### D-2: a decision nobody can cite\n\n- **Decision.** x.\n")],
     {"cited-undefined"}, {"declarations"}),
    ("partial-read-a-status-named-with-a-colon",
     [replace("QUESTIONS.md", "- **Status.** open", "- **Status**: open")],
     set(), {"QUESTIONS.md's question-status"}),
    # A CONTINUED FIELD IS READ WHOLE (roadmap 0.3.2, L-2.3). 0.3.1 judged the
    # vocabulary on a field's first line and named the rest as not evaluated.
    # The continuation is judged with it now, so a note written onto the next
    # line is part of the value -- and outside the vocabulary.
    ("continued-a-requirement-status-is-judged-whole",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** open\n  (until D-1 is reviewed)")],
     {"bad-status"}),
    # ...and a status wrapped inside its parenthetical is one value, in the
    # vocabulary.
    ("fp-continued-a-status-wrapped-inside-its-parenthetical-is-read-whole",
     [replace("REQUIREMENTS.md", "- **Status.** open", "- **Status.** partly-discharged (T-1;\n  D-1)")],
     set()),
    ("fp-continued-a-question-status-is-read-whole",
     [replace("QUESTIONS.md", "- **Status.** open", "- **Status.** answered\n  D-1")],
     set()),
    # A DISPOSITION IS READ WHOLE, and `open` is its first word, so a note
    # after `open` on the next line leaves the finding open. Read whole with an
    # exact match, the note would have made it read as dispositioned.
    ("continued-an-open-disposition-with-a-note-is-still-open",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_OPEN.replace("- **Disposition.** open", "- **Disposition.** open\n  until the review"))],
     {"undispositioned-finding"}),
    ("fp-continued-a-routed-disposition-is-read-whole",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_ROUTED.replace("routed T-1", "routed T-1\n  after the review"))],
     set()),
    # `open` is a word, not a prefix: `opened` is not it.
    ("fp-a-disposition-beginning-with-opened-is-not-open",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_ROUTED.replace("routed T-1", "opened as Q-1"))],
     set()),
    # A disposition NAMED and not parsed is still not evaluated.
    ("partial-read-a-disposition-named-with-a-colon",
     [("tracked", "audits/T-1-security-2026-09-04.md",
       AUDIT_ROUTED.replace("- **Disposition.** routed T-1", "- **Disposition**: routed T-1"))],
     {"undispositioned-finding"}, {"audits/T-1-security-2026-09-04.md's dispositions"}),
    # ...and what must stay CLEAN.
    #
    # A GENUINELY EMPTY SOURCE: an audit with no finding, only its method.
    ("fp-an-audit-with-no-findings-offers-none",
     [("tracked", "audits/T-1-hygiene-2026-09-04.md",
       "# T-1 hygiene audit\n\n## Checked and found clean\n\nEverything.\n\n"
       "## Method\n\nRead every file.\n")],
     set()),
    # A MULTI-LINE FIELD THIS CHECK READS WHOLE: every line is scanned for
    # citations, so a field outside the vocabularies may wrap freely.
    ("fp-a-wrapped-field-outside-the-vocabularies",
     [replace("QUESTIONS.md", "- **Evidence.** none needed.",
              "- **Evidence.** none needed,\n  beyond D-1's reasoning.")],
     set()),
    # A title is a heading, and a heading has no continuation: a line written
    # directly under it is a paragraph, not the title wrapping.
    ("fp-a-line-directly-under-a-title-is-not-a-wrap",
     [replace("tasks/T-1.md", "— PLANNED\n\n", "— PLANNED\nA line directly under the title.\n\n")],
     set()),
    # Numbered headings are an audit's finding shape ONLY in audits/. A
    # research digest numbering its sections offers no finding.
    ("fp-numbered-headings-outside-audits-are-not-findings",
     [("tracked", "research/2026-09-04-limits.md",
       "# Limits\n\n## 1. Sources\n\nProse.\n\n## 2. Method\n\nProse.\n")],
     set()),
    # pricelog writes each finding twice: the `- **F-n** —` register line
    # declares it, and a bold narrative entry `- **F-n — …**` discusses it.
    # The second is not a declaration written wrong.
    ("fp-a-narrative-finding-entry-beside-its-declaration",
     [append("RECORD.md", "- **F-1** — the store truncates\n"
                          "- **F-1 — the store truncates, and here is how.**\n")],
     set()),
    # A declaration's shape is offered only where its kind is DECLARED: a
    # decision number written in declaration form in the record is a citation
    # of an undeclared decision, and that is the finding -- not a gap as well.
    ("fp-a-declaration-shape-outside-its-home-is-a-citation-only",
     [append("RECORD.md", "- **D-9** proposed, not yet taken\n")],
     {"cited-undefined"}),
]


# --- accepted findings (roadmap 0.3.1, L-1.6) ------------------------------
# This check owns DECISIONS.md's grammar, so it is the one that reports an
# acceptance it cannot read -- and an acceptance is quoted check output, so it
# cites nothing. The two `cites-nothing` cases are the discriminating ones:
# without that rule, accepting a finding that names an undeclared T-99 cites
# T-99 again from DECISIONS.md, which sorts first, so the finding moves there
# and the acceptance naming its old anchor goes stale.

FINDING_LINE = r"^  (?!not evaluated: |excluded: |accepted by )(\S+)"
LINK = append("tasks/T-1.md", "See [the notes](notes.md).\n")
A_LINK = "`check_refs` `broken-link` `tasks/T-1.md` — notes.md"
A_T99 = ("`check_refs` `cited-undefined` `tasks/T-1.md` — T-99 is cited but never declared. "
         "Declare it in tasks/T-99.md as `# T-99 — <title>`")


def accepts(*items):
    """An `Accepts.` field for D-1, the fixture's last decision."""
    return append("DECISIONS.md", "- **Accepts.**\n" + "".join(f"  - {i}\n" for i in items))


ACCEPT_CASES = [
    # (name, mutations, exit, findings, accepted as (D, class or part))
    ("accepted-finding-exits-0-and-the-line-names-the-decision",
     [LINK, accepts(A_LINK)], 0, set(), {("D-1", "broken-link")}),
    ("a-fixed-finding-leaves-its-acceptance-stale",
     [accepts(A_LINK)], 1, {"stale-acceptance"}, set()),
    ("unparseable-acceptance-an-item-without-its-backticks",
     [LINK, accepts(A_LINK.replace("`", ""))], 1, {"broken-link", "unparseable-acceptance"}, set()),
    ("unparseable-acceptance-a-decision-that-does-not-say-who-reviewed-it",
     [LINK, replace("DECISIONS.md", "- **Reviewed.** client", "- **Reviewed.** the team"),
      accepts(A_LINK)], 1, {"broken-link", "unparseable-acceptance"}, set()),
    ("unparseable-acceptance-a-field-in-no-decision",
     [LINK, replace("DECISIONS.md", "# Decisions\n", f"# Decisions\n\n- **Accepts.**\n  - {A_LINK}\n")],
     1, {"broken-link", "unparseable-acceptance"}, set()),
    ("unparseable-acceptance-a-field-written-with-a-colon",
     [LINK, append("DECISIONS.md", f"- **Accepts:**\n  - {A_LINK}\n")],
     1, {"broken-link", "unparseable-acceptance"}, set()),
    # A part of check_report names no task, so no run could judge it: without
    # the refusal, the line would be read and then never applied and never
    # stale -- an acceptance nobody could see doing nothing.
    ("unparseable-acceptance-a-part-of-check_report",
     [accepts("`check_report` not evaluated: model-mismatch")], 1, {"unparseable-acceptance"}, set()),
    ("an-acceptance-cites-nothing-so-accepting-an-undeclared-id-holds",
     [append("tasks/T-1.md", "Waiting on T-99.\n"), accepts(A_T99)],
     0, set(), {("D-1", "cited-undefined")}),
    ("fp-a-malformed-acceptance-cites-nothing-either",
     [accepts(A_T99.replace("`check_refs` ", "check_refs "))], 1, {"unparseable-acceptance"}, set()),
    ("an-accepted-part-exits-0-and-is-named",
     [("tracked", "audits/T-1-safety-2026-09-04.md",
       "# T-1 safety audit\n\n## Finding 1 (HIGH) — the log can be truncated\n\nProse.\n"),
      accepts("`check_refs` not evaluated: audits/T-1-safety-2026-09-04.md's findings")],
     0, set(), {("D-1", "audits/T-1-safety-2026-09-04.md's findings")}),
    ("fp-an-acceptance-of-another-check-is-neither-applied-nor-stale-here",
     [accepts("`check_trace` `missing-field` `tasks/T-1.md` — T-1 has no **Verify.**")],
     0, set(), set()),
]


def build(root, mutations):
    dt = os.path.join(root, "devteam")
    for name, body in FIXTURE.items():
        p = os.path.join(dt, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)

    untracked, extra_tracked = [], []
    for mut in mutations:
        if mut[0] == "tracked":
            _, name, text = mut
            extra_tracked.append(name)
            p = os.path.join(dt, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
            continue
        if mut[0] == "untracked":
            _, name, text = mut
            untracked.append(name)
            os.makedirs(os.path.dirname(os.path.join(dt, name)), exist_ok=True)
            with open(os.path.join(dt, name), "w", encoding="utf-8") as fh:
                fh.write(text)
            continue
        if mut[0] == "ignore":                 # a pattern for the root .gitignore
            with open(os.path.join(root, ".gitignore"), "a", encoding="utf-8") as fh:
                fh.write(mut[1] + "\n")
            continue
        name = mut[1]
        p = os.path.join(dt, name)
        if mut[0] == "create":
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(mut[2])
            # Staged, or `check_refs` never sees it: the scan is over TRACKED
            # files, so an untracked fixture is silently absent and the case
            # passes by measuring nothing.
            extra_tracked.append(name)
            continue
        with open(p, encoding="utf-8") as fh:
            body = fh.read()
        if mut[0] == "append":
            body += mut[2]
        else:
            _, _, old, new = mut
            assert old in body, f"fixture mutation target missing: {old!r} in {name}"
            body = body.replace(old, new, 1)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)

    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, env=env)
    run("init", "-q", "-b", "main")
    for name in list(FIXTURE) + extra_tracked:
        run("add", os.path.join("devteam", name))
    run("commit", "-qm", "fixture")
    return dt


def main():
    passed = failed = 0
    for case in CASES:
        name, mutations, expected = case[:3]
        want_gaps = case[3] if len(case) > 3 else set()
        root = tempfile.mkdtemp(prefix="devteam-refs-")
        try:
            dt = build(root, mutations)
            proc = subprocess.run([sys.executable, CHECK, dt],
                                  capture_output=True, text=True)
            got = set(re.findall(FINDING_LINE, proc.stdout, re.M))
            got_gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            expected_exit = 1 if expected else (3 if want_gaps else 0)
            ok = got == expected and got_gaps == want_gaps and proc.returncode == expected_exit
            if ok:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} "
                      f"not evaluated {sorted(want_gaps) or 'none'} exit {expected_exit}")
                print(f"        got      {sorted(got) or 'clean'} "
                      f"not evaluated {sorted(got_gaps) or 'none'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- A FILE THE CHECK CANNOT READ IS NOT EVALUATED (roadmap 0.3.1) -------
    # 0.2.6 moved `unreadable` and `not-utf8` from findings to exit 2 -- and no
    # case here ever planted either, so that move was never shown to happen.
    # L-1.1 moves them again, to exit 3: a project file the check cannot decode
    # is the project's state, whose remedy is in the project, not in the
    # invocation. One unreadable file makes every cross-file class
    # untrustworthy, so the whole run is not evaluated and names the file.
    gap_cases = [
        ("a-tracked-file-that-is-not-utf8-is-not-evaluated",
         b"# Notes\n\nA byte that is not UTF-8: \xff\n", "not UTF-8"),
    ]
    for name, raw, reason in gap_cases:
        for as_json in (False, True):
            root = tempfile.mkdtemp(prefix="devteam-refs-gap-")
            try:
                dt = build(root, [])
                with open(os.path.join(dt, "NOTES.md"), "wb") as fh:
                    fh.write(raw)
                git = lambda *a: subprocess.run(
                    ["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                    capture_output=True)
                git("add", "devteam/NOTES.md")
                git("commit", "-qm", "an undecodable note")
                cmd = [sys.executable, CHECK, dt] + (["--json"] if as_json else [])
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if as_json:
                    try:
                        doc = json.loads(proc.stdout)
                        gaps = doc["results"][0]["not_evaluated"]
                        ok = (proc.returncode == 3 and doc["exit"] == 3
                              and not doc["results"][0]["findings"]
                              and len(gaps) == 1 and "NOTES.md" in gaps[0]["reason"]
                              and reason in gaps[0]["reason"])
                    except (ValueError, KeyError, IndexError, TypeError):
                        ok = False  # a different shape is a failure, not a crash
                else:
                    ok = (proc.returncode == 3
                          and re.search(rf"^  not evaluated: every class — NOTES\.md: {reason}",
                                        proc.stdout, re.M) is not None
                          and not re.findall(r"^  (?!not evaluated: |excluded: )(\S+)",
                                             proc.stdout, re.M))
                label = f"{name}{' --json' if as_json else ''}"
                if ok:
                    passed += 1
                else:
                    failed += 1
                    print(f"FAIL  {label}")
                    for line in (proc.stdout + proc.stderr).strip().split("\n"):
                        print(f"        | {line}")
            finally:
                shutil.rmtree(root, ignore_errors=True)

    for name, mutations, want_exit, expected, want_acc in ACCEPT_CASES:
        for as_json in (False, True) if name.startswith("accepted-finding") else (False,):
            root = tempfile.mkdtemp(prefix="devteam-refs-accept-")
            try:
                dt = build(root, mutations)
                proc = subprocess.run([sys.executable, CHECK, dt] + (["--json"] if as_json else []),
                                      capture_output=True, text=True)
                out = proc.stdout
                if as_json:
                    # The gate reads this, never the line: an accepted finding
                    # is out of `findings` and in `accepted`, with its decision.
                    try:
                        r = json.loads(out)["results"][0]
                        ok = (proc.returncode == want_exit and r["result"] == "clean"
                              and not r["findings"]
                              and {(f["by"], f["class"]) for f in r["accepted"]} == want_acc)
                    except (ValueError, KeyError, IndexError, TypeError):
                        ok = False
                else:
                    got = set(re.findall(FINDING_LINE, out, re.M))
                    got_acc = (set(re.findall(r"^  accepted by (D-\d+): not evaluated: (.+?) — ",
                                              out, re.M))
                               | set(re.findall(r"^  accepted by (D-\d+): (?!not evaluated: )(\S+)",
                                                out, re.M)))
                    head = out.split("\n", 1)[0]
                    ok = (proc.returncode == want_exit and got == expected and got_acc == want_acc
                          and (not want_acc or f", {len(want_acc)} accepted by D-1" in head))
                label = f"{name}{' --json' if as_json else ''}"
                if ok:
                    passed += 1
                else:
                    failed += 1
                    print(f"FAIL  {label}")
                    print(f"        expected exit {want_exit} {sorted(expected) or 'clean'} "
                          f"accepted {sorted(want_acc) or 'none'}")
                    for line in (out + proc.stderr).strip().split("\n")[:10]:
                        print(f"        | {line}")
            finally:
                shutil.rmtree(root, ignore_errors=True)

    # --- a checkout of one commit (roadmap 0.3.1, L-1.5) -------------------
    # `--at-commit` excludes the classes that read the working state, by the
    # caller's declaration, and names each. So an untracked file -- which a clean
    # checkout of a commit never holds -- is a finding without the flag, and
    # with it is excluded, named, and leaves the rest to decide the exit.
    root = tempfile.mkdtemp(prefix="devteam-refs-")
    try:
        build(root, [("untracked", "SCRATCH.md", "plain notes\n")])
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

    # COUNTED FROM WHAT RAN: a total computed from the case lists missed every
    # loop that was not one of them.
    total = passed + failed
    fp = sum(1 for c in CASES + ACCEPT_CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\ncheck_refs control: {passed} passed, {failed} failed, "
          f"{total} cases ({fp} of them false-positive controls, "
          f"{100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
