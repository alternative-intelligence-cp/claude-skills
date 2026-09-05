#!/usr/bin/env python3
"""Negative control for check_refs.py (P-35).

Plants exactly one fault per finding class and requires exactly that class
back. Then plants a set of things that LOOK like faults and must not be
reported at all -- because a check that cries wolf on legitimate work gets
switched off by whoever it obstructs, which is strictly worse than no check.
Those false-positive controls are deliberately more than a third of the cases.

Run it: python3 test_check_refs.py     Exit 0 all pass, 1 any fail.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
CHECK = os.path.join(HERE, "check_refs.py")

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
    ("fp-tabs-and-carriage-returns-are-ordinary-text",
     [("tracked", "research/table.md", "a\tb\tc\r\nd\te\tf\n")], set()),
    ("fp-naming-a-byte-is-not-embedding-it",
     [("tracked", "research/limits.md",
       "The NUL byte U+0000 (written `\\x00`) terminates a C string.\n")], set()),
    ("fp-directory-readme-is-not-an-artifact",
     [("tracked", "tasks/README.md",
       "One file per task, named `T-1.md`. See `C-1-<date>.md` for checkpoints.\n"),
      ("tracked", "research/README.md", "Digests live here; see D-9 for the policy.\n")],
     set()),
    ("fp-untracked-file-is-not-scanned",
     [("untracked", "SCRATCH.md", "Broken [link](nope.md) and R-99 and /home/x/y/\n")], set()),
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
            with open(os.path.join(dt, name), "w", encoding="utf-8") as fh:
                fh.write(text)
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
    for name, mutations, expected in CASES:
        root = tempfile.mkdtemp(prefix="devteam-refs-")
        try:
            dt = build(root, mutations)
            proc = subprocess.run([sys.executable, CHECK, dt],
                                  capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (\S+)", proc.stdout, re.M)}
            expected_exit = 1 if expected else 0
            ok = got == expected and proc.returncode == expected_exit
            if ok:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} exit {expected_exit}")
                print(f"        got      {sorted(got) or 'clean'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\ncheck_refs control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
