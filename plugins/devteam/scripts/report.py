#!/usr/bin/env python3
"""A REPORT block, and the two lines of an audit's answer that end one, read in
one place (roadmap 0.3.3 §3.4; P-34).

An agent's final message is a REPORT block, committed verbatim as an entry of
its task file's execution record (P-16; DESIGN.md §6). Two readers read those
blocks: check_report, which judges each against the tree it claims, and the
ledger's join (ledger.py), which counts the items under each judged block's
`questions:` and `open:` (roadmap 0.3.3, L-3.5). They read them with ONE
parse, so that the blocks the ledger counts items from are the blocks the
check judges -- the same header, the same fields, the same latest block per
id -- and an auditor's REPORT line is left out of both the same way.

WHY THIS IS A MODULE OF ITS OWN. The parse was check_report's, and the ledger
could not import it from there: check_report imports claim.py, for a task's
current claim, and check_trace imports both the ledger and claim.py, so the
ledger importing check_report would have closed a cycle through check_trace.
Here it imports no check. The two lines that open and close an audit's answer
are here too, because a block ends at either (L-3.4): had they stayed in the
ledger, which reads the answer's findings, this module and the ledger would
have imported each other.

Nothing here judges anything: `open:` being required, a status being in its
vocabulary, a commit being in HEAD's history are check_report's; a finding's
heading, and an answer read into its findings, are the ledger's.

Its controls are test_check_report.py, through every block it judges, and
test_ledger.py, through the items it counts and the answers it reads.
"""
import collections
import re

# A header may carry an annotation after its id, in parentheses and on its own
# line: `REPORT implementer T-6.S-4 (ATTEMPT 2, correcting attempt 1's FAILED
# verification)`. The run wrote exactly that, the grammar refused it, and the
# check read attempt 1's block in its place with no word said (F-34; roadmap
# 0.3.2, L-2.7). The parenthetical is the idiom a title's status already uses.
HEADER = re.compile(r"^REPORT\s+(\S+)\s+(T-\d+)(?:\.(S-\d+))?(?:\s+\((.+)\))?\s*$")
# A key may carry an annotation before its colon: F-88's `checks (all run by
# the supervisor…):` ended the field parse, and every field after it read as
# missing (L-2.7). The annotation may continue onto indented lines, as any
# value may, and F-88's did: its parenthesis opened on the key's line and
# closed two indented lines below, `…post-promotion run):`.
KEY = re.compile(r"^([a-z][a-z-]*)(?:\s*\(.*?\))?:\s*(.*)$")
OPEN_KEY = re.compile(r"^([a-z][a-z-]*)\s*\((?!.*\):)")
CLOSE_KEY = re.compile(r"\):\s*(.*)$")
# AN AUDITOR'S ANSWER IS NOT A REPORT (roadmap 0.3.3, L-3.4). An auditor has
# no tool that writes, so its supervisor lands its answer, and pricelog's
# T-10.S-3 supervisor landed one under a header of its own making,
# `REPORT auditor T-10.S-3 (adversarial pass, verbatim, P-17 — …`, its
# parenthesis closing two lines below it. An answer opens
# `AUDIT <scope> (<dimension>)` and closes `END AUDIT
# <scope>`, and a REPORT line whose role is `auditor`, parsed or not, is named
# as not a report, with that form in the reason. It is never judged as a
# block, and never counts as a later block for its id.
AUDITOR = re.compile(r"^REPORT\s+(?i:auditor)\s+T-\d+")


# --- an audit's answer: the two lines that open and close it ----------------
#
# AN AUDIT'S FINDINGS ARE ITEMS WHEREVER ITS TEXT LANDS, SO THE TEXT OPENS AND
# CLOSES ON TWO LINES THE GRAMMAR READS (FORMATS §"An audit's answer"; roadmap
# 0.3.3, L-3.4). pricelog's auditors answered in whatever shape their message
# took, and nothing could count what they found. T-10.S-3's supervisor landed
# its answer under a header of its own making, `REPORT auditor T-10.S-3 (…`,
# which is not a report. T-19.S-3's answer opened `AUDIT T-19.S-3
# (correctness): **one break found.** …` inside a fence, and two of the items
# under it reached no owner (F-139). So an answer opens
# `AUDIT <scope> (<dimension>)` and closes `END AUDIT <scope>`, each alone on
# its line. The scope is read from the AUDIT line, never from a file's name:
# T-18's step audit had only its name, `pricelog-T-18-S-4-2026-09-17.md`, and
# nothing tied it to its task (0.3.1 §3.2). The findings between the two lines
# are the ledger's to read (ledger.answers).

LABELS = {"safety": "SAF", "correctness": "COR", "security": "SEC", "hygiene": "HYG"}
DIMENSIONS = ", ".join(list(LABELS)[:-1]) + " or " + list(LABELS)[-1]
# A step's scope, a task's, or a lowercase word for a milestone's. A word never
# begins as a task id does: `t-18` or `t18` is a task mistyped, and read as a
# milestone it would tie the audit to no task.
SCOPE = r"(T-\d+(?:\.S-\d+)?|(?!t-?\d)[a-z][a-z0-9-]*)"
AUDIT = re.compile(r"^AUDIT\s+" + SCOPE + r"\s+\((" + "|".join(LABELS) + r")\)\s*$")
END = re.compile(r"^END\s+AUDIT\s+" + SCOPE + r"\s*$")
# The same two lines however they are written, so one written slightly wrong
# is named rather than passed over: T-19's, with text after the dimension; a
# scope or a dimension left out or misplaced; an emphasised `**AUDIT`; the
# audit skill's own form copied with its `<scope>` unfilled. Not the dispatch
# field `AUDIT: none`, nor prose such as `**AUDIT triaged** (…)`, which
# pricelog's task files hold at T-15:542 and T-18:2037.
AUDIT_ISH = re.compile(r"^[*_]{0,2}AUDIT[*_]{0,2}(?:\s+<|(?::\s*|\s+)"
                       r"(?:T-?\d|\(|(?:" + "|".join(LABELS) + r")\b|[A-Za-z][A-Za-z0-9-]*\s*\())")
END_ISH = re.compile(r"^[*_]{0,2}END[*_]{0,2}\s+AUDIT\b")
OPENING = (f"`AUDIT <scope> (<dimension>)` alone on its line (the scope `T-n.S-m`, `T-n` "
           f"or a lowercase word; the dimension {DIMENSIONS})")


def is_answer_line(line):
    """Does this line open or close an audit's answer, however it is written?
    A REPORT block ends at one."""
    return bool(AUDIT_ISH.match(line) or END_ISH.match(line))


# --- a REPORT block ----------------------------------------------------------

# One block: the 0-based line of its header, what the header says, its fields
# (each a list: a key's inline value, then its indented continuation lines),
# each key's line, and the line the field parse stopped at, or None when it
# ran to the block's end (roadmap 0.3.1, L-1.3).
Block = collections.namedtuple("Block", "start role task step note fields at stop")


def ends_block(line):
    """Does this line end the block above it? The next header, a heading, or
    an audit's answer opening or closing (roadmap 0.3.3, L-3.4): an answer
    landed right after a block is text between blocks, as a supervisor's
    prose is, and none of its lines is that block's field."""
    return bool(HEADER.match(line) or line.startswith("#") or is_answer_line(line))


def parse_block(lines, i):
    """The block whose header is `lines[i]`."""
    m = HEADER.match(lines[i])
    fields, key, at, stop = {}, None, {}, None
    j = i + 1
    while j < len(lines):
        line = lines[j]
        if ends_block(line):
            break
        k = KEY.match(line)
        closed = None
        if not k and OPEN_KEY.match(line):
            # The annotation's indented lines, up to the one that closes it.
            # One that never closes leaves the line unread, as before.
            n = j + 1
            while n < len(lines) and lines[n].startswith((" ", "\t")) and lines[n].strip():
                if CLOSE_KEY.search(lines[n]):
                    closed = n
                    break
                n += 1
        if k or closed is not None:
            key = (k or OPEN_KEY.match(line)).group(1)
            value = k.group(2) if k else CLOSE_KEY.search(lines[closed]).group(1)
            fields[key] = [value] if value else []
            at[key] = j
            j = closed if closed is not None else j
        elif key is not None and line.startswith((" ", "\t")) and line.strip():
            fields[key].append(line.strip())
        elif line.strip():
            stop = j
            break
        j += 1
    return Block(i, m.group(1), m.group(2), m.group(3), m.group(4), fields, at, stop)


def blocks(lines):
    """Every block in a file's lines, in file order. An auditor's REPORT line
    opens none: it is not a report."""
    return [parse_block(lines, i) for i, line in enumerate(lines)
            if HEADER.match(line) and not AUDITOR.match(line)]


def judged(blocks, task_id, step_id=None):
    """(the blocks a run for `task_id`, or for its step `step_id`, judges, in
    file order; how many earlier blocks for the same ids they supersede)."""
    mine = [b for b in blocks if b.task == task_id and (b.step == step_id if step_id else True)]
    latest = {}
    for b in mine:
        latest[b.step] = b                    # a later block for the same id wins
    return sorted(latest.values(), key=lambda b: b.start), len(mine) - len(latest)
