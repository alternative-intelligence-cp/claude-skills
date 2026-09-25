#!/usr/bin/env python3
"""A task's current claim, computed in one place (roadmap 0.3.2, L-2.5; P-34).

A CLAIM IS A COMMIT ON THE BOARD (P-11). The manager writes `CLAIMED <label>`
on the task's row and an in-flight row carrying the same label, and commits;
the supervisor writes the label into the task's title, `RUNNING (since <date>,
<label>)` (the claim protocol in templates/BOARD.md; FORMATS' task title). So
a RUNNING task's current claim is the label its title carries, and the claim
began at the first commit in HEAD's history whose board carries that label in
the in-flight table's `Agent label` column, on the task's row.

`check_scope` opens `misattributed-write`'s window there, and `check_report`
reads a restarted task's previous close as the previous claim's by it (L-2.7,
F-136); nothing else computes a claim.

THE IN-FLIGHT TABLE'S ONE READER IS HERE, `in_flight_rows`, because the table
is the claim's record: check_trace's `in_flight`, which the gate's allowance
keys on, reads it through this, and so does the claim at each commit. It was
check_trace's, and this read it from there. Then check_trace came to need the
claim -- an item raised under a task's current claim is not due until its row
leaves `CLAIMED` (roadmap 0.3.3, L-3.5) -- and the two modules would have
imported each other. So the reader moved here, and the reading it shares with
check_trace's Tasks table -- a section's lines, a row's cells, a cell's text
-- moved to result.py, at the bottom, which imports no check (roadmap 0.3.3
§3.4).

THE LABEL, NEVER A SUBJECT. pricelog's claims were subjected `board: claim T-3
and T-2`, `plan T-17 and claim T-15`, `board: claim T-9 (re-dispatch)`,
`board: re-claim T-18 as T18-refute-0928` and `board: T-5 restarted with Q-1
answered`, so any subject pattern misses some. A subject is also prose, and an
anchor found in prose can be moved by quoting it: the window once opened at
the newest commit mentioning a RUNNING title, and a commit describing that
defect switched the check off. The board's content is read instead.

THE CURRENT CLAIM, NOT THE FIRST: the owner's answer of 2026-09-24, over
listing a stop's commits and over keeping the first claim. A restart is a new
claim under a new label, so the manager's edits to a stopped task's file, made
before its re-dispatch as `run` §4.3 asks, fall before the claim and are
judged by nothing here -- F-135, three at pricelog T-19's restart and fourteen
gate refusals in 0.3.1's replay. The window used to open at the first claim
because a write made while a task was stopped was never live and in the window
at any one moment. That write was a sweep, `git add -A` taking a file the task
had left, and the gate now refuses a path naming the whole repository while
its hook refuses every commit made around it. A commit into a stopped task's
scope names its paths.

Its controls are test_check_scope.py, through the window it opens,
test_check_report.py, through the restarts it reads, and test_check_trace.py
and test_gate.py, through the in-flight table's allowance.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import result  # noqa: E402 -- a section, a row's cells and a cell's text, which the board is read by

BOARD = "devteam/BOARD.md"
GRAMMAR = "`RUNNING (since <date>, <label>)`"
# The title's claim, as FORMATS writes it and with nothing after it. The label
# is one token, backticked or not; a reason goes in the execution record.
TITLE_LABEL = re.compile(r"^RUNNING \(since [^,()]+, `?([^\s,()`]+)`?\)$")


def label(status):
    """The claim label a task title's status carries, or None."""
    m = TITLE_LABEL.match(status.strip())
    return m.group(1) if m else None


IN_FLIGHT_ROW = re.compile(r"^\|\s*(?:\[|\*\*|\*|`)*\s*(T-\d+)\b")


def in_flight_rows(lines):
    """([(T-n, its claim label or None, its line)], [lines of rows naming no
    task]) for the `## In flight` table of a board's lines -- the table's one
    reader, which check_trace's `in_flight` and the claim both read.

    The label is the cell under the header's `Agent label`, decoration
    peeled, as the Tasks table's state is the cell under `State`. It is None
    when the table has no such column, the cell is a placeholder, or the row
    has a cell more or fewer than its header, so that a label is never read
    from the wrong column (roadmap 0.3.2, L-2.5).
    """
    start, body = result.section_lines(lines, "in flight")
    out, unparsed, col, width = [], [], None, 0
    if start is None:
        return out, unparsed
    for k, line in enumerate(body):
        if not line.startswith("|") or result.TABLE_RULE.match(line):
            continue
        first = line.split("|")[1].strip().strip("*`_ ")
        if first.lower() == "task":
            head = [result.plain(c).lower() for c in result.cells(line)]
            col = head.index("agent label") if "agent label" in head else None
            width = len(head)
            continue
        m = IN_FLIGHT_ROW.match(line)
        if m:
            row = result.cells(line)
            label = result.plain(row[col]) if col is not None and len(row) == width else ""
            out.append((m.group(1), label if label not in ("", "—", "-") else None,
                        start + 1 + k))
        elif first.lower() not in ("—", "-", ""):
            unparsed.append(start + 1 + k)
    return out, unparsed


def boards(repo):
    """[(commit, the board's lines)] for every commit in HEAD's history that
    changes the board, oldest first. HEAD's history, never `--all`: at the
    gate, HEAD is the commit being judged (L-2.6)."""
    p = subprocess.run(["git", "-C", repo, "log", "--reverse", "--format=%H", "--", BOARD],
                       capture_output=True)
    shas = p.stdout.decode().split() if p.returncode == 0 else []
    if not shas:
        return []
    # One process for every revision: the `./` form is relative to `repo`,
    # which a bare `<commit>:<path>` is not.
    p = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], capture_output=True,
                       input="".join(f"{s}:./{BOARD}\n" for s in shas).encode())
    out, at = [], 0
    for sha in shas:
        end = p.stdout.find(b"\n", at)
        if end < 0:
            break
        head = p.stdout[at:end].split()
        at = end + 1
        if len(head) != 3:
            continue                      # `<name> missing`: the commit deleted it
        size = int(head[2])
        if head[1] == b"blob":
            out.append((sha, p.stdout[at:at + size].decode("utf-8", "replace").split("\n")))
        at += size + 1
    return out


def began(repo, wanted):
    """For `wanted`, {T-n: a claim label}: {T-n: the first commit in HEAD's
    history whose board carries that label in its in-flight table on T-n's
    row}, for each label some commit carries.

    `current` reads the label from a RUNNING title. check_trace reads it from
    the board's own row, `CLAIMED <label>`, which the claim still holds after
    its supervisor has closed or stopped and the title no longer carries the
    label: an item raised under the current claim is not due until the row
    leaves CLAIMED (roadmap 0.3.3, L-3.5)."""
    found = {}
    if wanted:
        for sha, lines in boards(repo):
            rows, _unparsed = in_flight_rows(lines)
            for tid, lab, _n in rows:
                if tid in wanted and lab == wanted[tid] and tid not in found:
                    found[tid] = sha
            if len(found) == len(wanted):
                break
    return found


def current(repo, running):
    """For `running`, {T-n: (its task file, its title's status)} of the tasks
    whose title reads RUNNING: {T-n: (label, the claim's commit, None)}, or
    {T-n: (label or None, None, why nothing anchors it)}."""
    labels = {t: label(status) for t, (_rel, status) in running.items()}
    found = began(repo, {t: lab for t, lab in labels.items() if lab})
    out = {}
    for t, (rel, status) in running.items():
        lab = labels[t]
        if lab is None:
            out[t] = (None, None, f"{rel}'s title reads {status!r}, which carries no claim "
                      f"label as {GRAMMAR} does, so nothing anchors {t}'s claim")
        elif t not in found:
            out[t] = (lab, None, f"no commit in HEAD's history has {lab!r} in its board's "
                      f"in-flight table on {t}'s row, so nothing anchors the claim {rel}'s "
                      "title names")
        else:
            out[t] = (lab, found[t], None)
    return out
