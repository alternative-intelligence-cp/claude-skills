#!/usr/bin/env python3
"""The disposition ledger, read in one place (roadmap 0.3.3, L-3.1, L-3.2; P-34).

EVERY ITEM RAISED HAS ONE HOME, AND IT IS HERE. pricelog's run raised items
that reached no owner, to the end: an auditor's open item needing a client
decision was read past by a supervisor and by the manager (F-139), a gate
audit's finding sat four days with no owner (F-99), and a question's status
lived in two files that disagreed (F-63, F-64). So `devteam/LEDGER.md` gives
every item an entry -- an id, where its text is, and its disposition -- and
the item's text stays where it was raised, verbatim (P-17). The manager writes
the ledger and nobody else (P-13). The shape is the one pricelog's manager
improvised for T-18's audit: "This file declares them and carries each one's
disposition; the evidence stays where it was landed"
(audits/pricelog-T-18-S-4-2026-09-17.md). The rule is P-52.

An entry, as templates/FORMATS.md §"The ledger" writes it:

    ### ITM-2 — the truncation branch's delivered bytes are unpinned

    - **Raised.** T-18.S-4 COR-6
    - **Needs.**
      - `tests/test_failures.py`
    - **Disposition.** open (until C-9)

THE VOCABULARY IS CLOSED, AND AN OPEN ITEM NAMES THE DATE IT IS DUE BY: the
owner's answer of 2026-09-24 (L-3.2), five values. `open (until T-n)` or
`open (until C-n)`; `routed T-n`; `raised Q-n`; `declined (D-n)`; and
`fixed (<commit>)`, several commits comma-separated. The audit skill's four had
no date and no word for a fix, so T-18's manager wrote its three deferrals as
"carried to the checkpoint D-38 requires before T-18's next dispatch, to be
given an owner there", and both checks read that as decided, because they
judged only whether the first word was `open`. A value that says it is open,
and does not say by when, is undecided with nobody due to decide it.

A commit may be written in backticks, as pricelog's manager wrote every hash:
`fixed (`a4f3774`)` reads as `fixed (a4f3774)`. Nothing else is decoration;
the value is matched whole, as a requirement's `Status.` is.

What this module holds, and who reads it:
  * the entry heading, `### ITM-n — <one line>`, which check_refs declares
    `ITM-n` from, in LEDGER.md and nowhere else;
  * each entry's fields, read whole across their continuation lines (L-2.3);
  * the vocabulary, which check_refs judges each disposition against
    (`bad-status`, and `undispositioned-finding` for one that is missing or
    open with no date);
  * the first-word `open` test, which check_refs applies to a ledger value
    outside the vocabulary, to tell one that says it is open from one that
    is merely wrong. It was a regex copied into both checks for an audit
    file's own `Disposition.` lines (0.3.2 §3.2's joint); those lines are no
    longer read (roadmap 0.3.3 §3.4), and this reader stayed;
  * an audit's answer, which is where an audit's findings come from: the
    heading each finding is, read into the answer's scope and its findings
    wherever the answer lands, in a task file or in `audits/` (FORMATS §"An
    audit's answer"; roadmap 0.3.3, L-3.4). The `AUDIT <scope> (<dimension>)`
    and `END AUDIT <scope>` lines that open and close it are report.py's,
    because a REPORT block ends at either, and this module reads them from
    there (roadmap 0.3.3 §3.4).

    python3 ledger.py <project> [--pending] [--json]

prints each entry's disposition and the counts by value. An entry it cannot
read -- a heading in the entry's position that does not parse, a field named
and not parsed or named twice, a disposition missing or outside the
vocabulary -- is named by its line as not evaluated, because its disposition
was not counted (roadmap 0.3.1, L-1.3). No LEDGER.md at all is not evaluated
too: nothing was read. Exit 0 clean, 2 could not run, 3 not evaluated -- the
contract is result.py's (roadmap 0.3.1, L-1.1). It reports no finding, so it
never exits 1: check_refs and check_trace judge the ledger, and this prints it.

With `--pending` it prints instead, for every item raised that no entry
covers, the `Raised.` line its entry needs, after the file and line where its
text is (roadmap 0.3.3, L-3.5): the manager copies it rather than types it.

THE JOIN IS HERE TOO: every item a project raises -- each item under a judged
REPORT block's `questions:` and `open:`, and each finding of an audit's
answer -- read where it was raised, and matched against the entries'
`Raised.` lines, one entry to one item. check_trace reads the same join for
`unledgered-item`, `unknown-source` and `open-finding-at-close`.

Its control is test_ledger.py.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report  # noqa: E402 -- the REPORT block, and an answer's two lines (roadmap 0.3.3 §3.4)
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)

USAGE = "usage: ledger.py <project> [--pending] [--json]"
PATH = "LEDGER.md"
DASH = r"[—–-]"
FENCE = re.compile(r"^\s*(?:```|~~~)")

# The declaration, in the shape R-, D- and Q- are declared in (FORMATS
# §"Identifier declarations"). check_refs declares ITM-n from it, in LEDGER.md
# alone: `### ITM-3 —` in a task file declares nothing.
HEADING = re.compile(r"^###\s+(ITM)-(\d+)\s*" + DASH + r"\s*(.*?)\s*$")
# A heading in the entry's position, however it is written: `## ITM-3 — …`,
# `### ITM-3: …`, `### ITM 3 — …`. One that does not parse as HEADING is named.
HEADING_ISH = re.compile(r"^#{1,6}\s*\**\s*ITM(?![A-Za-z])", re.I)
ANY_HEADING = re.compile(r"^#{1,6}\s")

FIELDS = ("Raised", "Needs", "Disposition")
FIELD = {name: re.compile(r"^-\s+\*\*" + name + r"\.\*\*\s*(.*?)\s*$") for name in FIELDS}
# A list item that NAMES the field, however it is decorated -- the loose shape
# check_refs' `named_field` reads, so a field written slightly wrong is named
# rather than read as absent in silence.
FIELD_ISH = {name: re.compile(r"^\s*-\s+\**\s*" + name + r"\s*\**\s*[.:]", re.I)
             for name in FIELDS}
# `Needs.` is a path list, the field and then one path per indented item
# (FORMATS §"Identifier declarations"), so its value stops at its first item.
LIST_ITEMISH = re.compile(r"^\s+[-*+]\s+\S")

# --- the vocabulary (FORMATS §"Status vocabularies"; L-3.2) ----------------
COMMIT = r"`?[0-9a-f]{7,40}`?"
VOCABULARY = (
    ("open", re.compile(r"^open \(until ([TC]-\d+)\)$")),
    ("routed", re.compile(r"^routed (T-\d+)$")),
    ("raised", re.compile(r"^raised (Q-\d+)$")),
    ("declined", re.compile(r"^declined \((D-\d+)\)$")),
    ("fixed", re.compile(r"^fixed \((" + COMMIT + r"(?:\s*,\s*" + COMMIT + r")*)\)$")),
)
KINDS = tuple(kind for kind, _ in VOCABULARY)
GRAMMAR = ("`open (until T-n)`, `open (until C-n)`, `routed T-n`, `raised Q-n`, "
           "`declined (D-n)` or `fixed (<commit>)`, several commits comma-separated")

# OPEN IS THE FIRST WORD, NOT THE WHOLE VALUE (roadmap 0.3.2, L-2.3). An audit
# file's `Disposition.` is read whole, and an exact match would have read
# `open` with a note on the next line as decided. A value that says it is open
# is open, whatever follows it. `opened` and `open-ended` are other words.
OPEN = re.compile(r"^\**open\b(?!-)", re.I)


def is_open(value):
    """Does this disposition say it is open? The first-word test."""
    return bool(OPEN.match(value.strip()))


# --- an audit's answer (FORMATS §"An audit's answer"; roadmap 0.3.3, L-3.4) --
#
# AN AUDIT'S FINDINGS ARE ITEMS WHEREVER ITS TEXT LANDS. The answer opens and
# closes on two lines the grammar reads, `AUDIT <scope> (<dimension>)` and
# `END AUDIT <scope>`, which are report.py's (a REPORT block ends at either),
# and each finding between them is a heading carrying its dimension's label.
# The four gate audits numbered their findings `## Finding 1 (…)`, `### 1.`
# and `## F-1 — HIGH`, and one of them waited four days for an owner (F-99).

# A finding is a heading with its dimension's label, `##` or `###`, which is
# how the audits carrying `Disposition.` declared their findings before the
# ledger (check_refs' audit heading). The number is the audit's own, from 1.
FINDING = re.compile(r"^#{2,3}\s+(" + "|".join(report.LABELS.values()) + r")-(\d+)\s*" + DASH
                     + r"\s*(.*?)\s*$")
# A heading that looks like a finding, in the shapes the corpus used for one:
# the gate audits' `## Finding 1 (…) —`, `### 1.` and `## F-1 — HIGH —`, and
# any label written loosely. Any other heading in an answer, `## Verdict` or
# `## Checked and found clean`, is its text.
FINDING_ISH = re.compile(r"^#{2,3}\s*[*_]*\s*(?:finding\s*#?\s*\d+\b|\d+[.)]\s"
                         r"|(?:" + "|".join(report.LABELS.values()) + r")[\s-]*\d+\b|[A-Z]{1,5}-\d+\b)",
                         re.I)


class Finding:
    """One finding of an answer: its label and number as written, its title,
    its heading's line, and its `Needs.` -- (line, the value read whole) -- or
    None when it has none."""

    def __init__(self, label, number, title, line):
        self.label, self.number, self.title, self.line = label, number, title, line
        self.needs = None

    @property
    def ident(self):
        return f"{self.label}-{self.number}"


class Answer:
    """An audit's answer: the scope and dimension its AUDIT line names, the
    lines that open and close it, and its findings. A file in `audits/` that
    opens no answer is read as one with no scope, AUDIT line or dimension."""

    def __init__(self, scope, dimension, line, end=None):
        self.scope, self.dimension, self.line, self.end = scope, dimension, line, end
        self.findings = []

    @property
    def label(self):
        return report.LABELS.get(self.dimension)

    @property
    def task(self):
        """The task the answer is tied to: T-n for an audit of T-n or of one
        of its steps, None for a milestone's or for no scope at all."""
        m = re.match(r"T-\d+", self.scope or "")
        return m.group(0) if m else None


def _findings(lines, inside, start, stop, answer, labels, unread):
    """Read the findings between two lines into `answer`, naming each heading
    that looks like a finding and is not one of `labels`' or does not parse."""
    seen, current = {}, None
    for i in range(start, stop):
        if inside[i]:
            continue
        line = lines[i]
        m = FINDING.match(line)
        if m and m.group(1) in labels:
            ident = f"{m.group(1)}-{m.group(2)}"
            if ident in seen:
                unread.append((i + 1, f"a second {ident} in one answer, after line {seen[ident]}, "
                                      "so it is not counted"))
                current = None
                continue
            seen[ident] = i + 1
            current = Finding(m.group(1), m.group(2), m.group(3), i + 1)
            answer.findings.append(current)
            continue
        if m:
            unread.append((i + 1, f"{m.group(1)}-{m.group(2)} is not this answer's label: "
                                  f"a {answer.dimension} audit's findings are "
                                  f"`## {answer.label}-n — <one line>`, so it is not counted"))
            current = None
            continue
        if FINDING_ISH.match(line):
            shown = f"{answer.label}-n" if answer.label else "<LABEL>-n"
            unread.append((i + 1, f"a heading that looks like a finding and does not parse as "
                                  f"`## {shown} — <one line>`, so it is not counted"))
            current = None
            continue
        if ANY_HEADING.match(line):
            current = None
            continue
        f = FIELD["Needs"].match(line)
        if f and current is not None and current.needs is None:
            current.needs = (i + 1, result.joined(lines, i, f.group(1)))


def answers(lines, filed=False):
    """([Answer], [(line, what)]) for one file's lines: every audit's answer
    in it, and every line the answer's grammar offered and did not read,
    whose findings are therefore not counted.

    An answer runs from its AUDIT line to the next END AUDIT line, and a
    fenced block holds none: a fence hides an answer's own citations from
    check_refs, and one nested inside another ends it early (L-3.4). An
    answer that is never closed is not read, because what follows it in a
    task file is the task's own text. `filed` says the lines are a file in
    `audits/`, which is the auditor's whole message: one that offers no
    AUDIT or END AUDIT line at all, and does offer a finding or a heading
    that looks like one, is read as one answer with no scope, its findings
    counted and tied to no task, and the missing line is named.
    Outside an answer, a task file's own headings -- `## S-4 — …`, `### S-2`
    -- are never an audit's.
    """
    inside, fenced = [], False
    for line in lines:
        if FENCE.match(line):
            inside.append(True)
            fenced = not fenced
        else:
            inside.append(fenced)
    out, unread, events = [], [], []
    for i, line in enumerate(lines):
        if not report.is_answer_line(line):
            continue
        if inside[i]:
            unread.append((i + 1, "an `AUDIT` or `END AUDIT` line inside a fenced block, where "
                                  "no answer is read: an answer is landed unfenced, so the "
                                  "findings under it are not counted"))
            continue
        m = report.AUDIT.match(line) or report.END.match(line)
        closing = bool(report.END_ISH.match(line))
        events.append((i, closing, m.group(1) if m else None, None if closing or not m else m.group(2)))
    # Each opening is closed by the next closing line. A malformed line
    # still opens or closes, so that one fault is reported once.
    current = None
    for i, closing, scope, dimension in events:
        if not closing:
            if current is not None and current[1] is not None:
                unread.append((current[0] + 1, f"the answer opened here has no `END AUDIT "
                                               f"{current[1]}` before line {i + 1}, so its "
                                               "findings are not counted"))
            if scope is None:
                unread.append((i + 1, f"an `AUDIT` line that does not parse as {report.OPENING}, so "
                                      "no answer opens here and the findings under it are "
                                      "not counted"))
            current = (i, scope, dimension)
            continue
        if current is None:
            unread.append((i + 1, "an `END AUDIT` line with no answer open"))
            continue
        if scope is None:
            unread.append((i + 1, "an `END AUDIT` line that does not parse as `END AUDIT "
                                  "<scope>` alone on its line"))
        elif current[1] is not None and scope != current[1]:
            unread.append((i + 1, f"`END AUDIT {scope}` closes the answer `AUDIT {current[1]}` "
                                  f"opened at line {current[0] + 1}"))
        if current[1] is not None:
            answer = Answer(current[1], current[2], current[0] + 1, i + 1)
            _findings(lines, inside, current[0] + 1, i, answer, {answer.label}, unread)
            out.append(answer)
        current = None
    if current is not None and current[1] is not None:
        unread.append((current[0] + 1, f"the answer opened here has no `END AUDIT {current[1]}` "
                                       "after it, so its findings are not counted"))
    if filed and not events and not unread:
        # A file that offers no finding either -- notes, say -- offers nothing
        # the grammar reads, and is genuinely empty (roadmap 0.3.1, L-1.3).
        answer = Answer(None, None, None)
        _findings(lines, inside, 0, len(lines), answer, set(report.LABELS.values()), unread)
        if answer.findings or unread:
            out.append(answer)
            unread.append((1, f"no line opens an answer as {report.OPENING}, so the file's "
                              "findings are tied to no task"))
    unread.sort()
    return out, unread


# Where an answer may land: a task file, and a report in `audits/` other than
# the directory's README, which `setup` scaffolds -- the task files and audit
# reports among check_refs' artifacts.
SOURCES = re.compile(r"^tasks/T-\d+\.md$|^audits/(?!README\.md$)[^/]+\.md$")


def answers_in(devteam):
    """([(file, Answer)], [(file, line, what)]) for every answer in a project's
    task files and `audits/`, read as git would show them (roadmap 0.3.1,
    L-1.4), or None outside a repository. A file is `audits/`'s by where it
    is, and its answer's scope is its AUDIT line's, whatever the file is
    called: T-18's step audit was named `pricelog-T-18-S-4-2026-09-17.md`,
    and a name was all that could have tied it to its task (0.3.1 §3.2)."""
    listing = result.listed(devteam, "tasks/*.md", "audits/*.md")
    if listing is None:
        return None
    found, unread = [], []
    for rel in listing[0]:
        if not SOURCES.match(rel):
            continue
        try:
            with open(os.path.join(devteam, rel), encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError as exc:
            unread.append((rel, 1, f"cannot be read ({exc.strerror}), so no answer in it was read"))
            continue
        got, missed = answers(lines, filed=rel.startswith("audits/"))
        found += [(rel, a) for a in got]
        unread += [(rel, n, what) for n, what in missed]
    return found, unread


# --- the join: every item raised, and the entry that names it ---------------
# (FORMATS §"The ledger"; roadmap 0.3.3, L-3.5)
#
# AN ITEM IS FOUND WHERE IT WAS RAISED, AND ITS ENTRY NAMES WHERE. pricelog's
# T-19 stopped with seven open items under its auditor's answer, and its
# manager filed questions for five: two items -- a charter decision on a
# user's interrupt among them -- reached no owner, and nothing counted them
# (F-139). So every item is counted from where its text is: each item under a
# judged REPORT block's `questions:` and `open:`, read with the parse
# check_report judges the block with (report.py; P-34), and each finding of an
# audit's answer, in a task file or in `audits/`. An entry covers the item its
# `Raised.` names, one entry to one item, and an item no entry covers is
# pending: `ledger.py --pending` prints the `Raised.` line to write for it, and
# check_trace reports it once it is due (`unledgered-item`).
#
# A report's item is named by its block's id, its key and its opening words,
# matched with whitespace and dashes normalised, against every block for that
# id, so an entry made at an earlier stop still resolves after a later attempt
# supersedes the block it named. Only the judged block's items need an entry.

KEYS = ("questions", "open")
TASK_FILE = re.compile(r"^tasks/(T-\d+)\.md$")
DASHES = re.compile(r"[—–-]+")
# `none` is an answer (DESIGN.md §6), and so is `- none`: neither is an item.
NONE = re.compile(r"^none\b", re.I)
NO_ITEM = re.compile(r"^none\.?$", re.I)
_LABEL = "(" + "|".join(report.LABELS.values()) + r")-(\d+)"
# `Raised.`'s four forms (FORMATS §"The ledger"). A path may be backticked, as
# pricelog's manager backticked every path it wrote.
RAISED = (
    ("report", re.compile(r'^(T-\d+(?:\.S-\d+)?)\s+(' + "|".join(KEYS) + r')\s+"(.+)"$')),
    ("filed", re.compile(r"^`?(audits/[^`\s]+\.md)`?\s+" + _LABEL + r"$")),
    ("answer", re.compile(r"^" + report.SCOPE + r"\s+" + _LABEL + r"$")),
    ("own", re.compile(r"^(client|manager)\s+(\d{4}-\d{2}-\d{2})$")),
)
FORMS = ('`<T-n or T-n.S-m> <questions or open> "<the item\'s opening words>"`, '
         "`<scope> <LABEL>-n` for an audit landed in a task file, "
         "`audits/<file>.md <LABEL>-n` for one filed, or `client <date>` or `manager <date>`")
# The fewest opening words `--pending` prints, before it adds more to tell an
# item from another in its block's key.
LEAST_WORDS = 5


def words(text):
    """Text as `Raised.` matches it: whitespace and dashes normalised (L-3.5)."""
    return " ".join(DASHES.sub("-", text).split())


class Item:
    """One item raised.

    `kind` is `report`, `answer` (a finding of an audit landed in a task file)
    or `filed` (one in `audits/`). `file` and `line` are where its text is;
    `task` is the task whose file holds it, whose board row the window reads,
    or None for a filed audit, which is due from the commit that adds it; and
    `dated` is the line that dates it against a claim -- its block's header,
    or its answer's AUDIT line. `group` is what an entry must name to cover
    it, `text` a report item's words, `raised` the `Raised.` value that names
    it, and `audited` the task an audit's finding is of, for P-31."""

    def __init__(self, kind, file, line, task, dated, group, raised, text=None, audited=None):
        self.kind, self.file, self.line, self.task, self.dated = kind, file, line, task, dated
        self.group, self.raised, self.text, self.audited = group, raised, text, audited


def key_items(vals, where):
    """[(0-based line, text)] of the items in one key's values: each `- ` line
    with the lines that continue it; or, when there is none, the value read
    whole, unless it is `none`."""
    starts = [k for k, v in enumerate(vals) if v.startswith("- ")]
    if not starts:
        whole = " ".join(vals).strip()
        return [] if not whole or NONE.match(whole) else [(where[0], whole)]
    out = []
    for i, k in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(vals)
        text = " ".join([vals[k][2:].strip()] + vals[k + 1:end]).strip()
        if text and not NO_ITEM.match(text):
            out.append((where[k], text))
    return out


def opening(text, others):
    """The opening words `--pending` prints for an item: LEAST_WORDS of them,
    or more until no other item in its block's key begins with them."""
    ws = words(text).split(" ")
    rest = [words(o) for o in others]
    for n in range(min(LEAST_WORDS, len(ws)), len(ws) + 1):
        pre = " ".join(ws[:n])
        if not any(o.startswith(pre) for o in rest):
            return pre
    return " ".join(ws)


class Found:
    """What a project's task files and `audits/` raise: `items`, each needing
    an entry; `every`, each item of every block by (id, key), superseded
    attempts' too, which an entry may name; `answers`, every audit answer read;
    `unread`, each answer line the grammar could not read, as (file, line,
    what); and `files`, the files read."""

    def __init__(self):
        self.items, self.every, self.answers, self.unread, self.files = [], {}, [], [], set()


def found_in(devteam):
    """Every item a project raises, as a Found, or None outside a repository."""
    got = answers_in(devteam)
    listing = result.listed(devteam, "tasks/*.md", "audits/*.md")
    if got is None or listing is None:
        return None
    out = Found()
    out.answers, out.unread = got
    out.files = {rel for rel in listing[0] if SOURCES.match(rel)}
    for rel in sorted(out.files):
        m = TASK_FILE.match(rel)
        if not m:
            continue
        try:
            with open(os.path.join(devteam, rel), encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue                      # answers_in has named it
        tid = m.group(1)
        # The task's own blocks, as check_report reads them for the task: a
        # block naming another task is that task's report, landed here, and
        # check_report names it `wrong-task`.
        mine = [b for b in report.blocks(lines) if b.task == tid]
        for b in mine:
            ident = f"{b.task}.{b.step}" if b.step else b.task
            for key in KEYS:
                out.every.setdefault((ident, key), []).extend(
                    words(t) for _, t in key_items(b.fields.get(key) or [], b.where.get(key) or []))
        for b in report.judged(mine, tid)[0]:
            ident = f"{b.task}.{b.step}" if b.step else b.task
            for key in KEYS:
                got_items = key_items(b.fields.get(key) or [], b.where.get(key) or [])
                texts = [t for _, t in got_items]
                for k, (n, text) in enumerate(got_items):
                    out.items.append(Item(
                        "report", rel, n + 1, tid, b.start + 1, ("report", ident, key),
                        f'{ident} {key} "{opening(text, texts[:k] + texts[k + 1:])}"',
                        text=words(text)))
    for rel, a in out.answers:
        m = TASK_FILE.match(rel)
        for f in a.findings:
            if m:
                out.items.append(Item("answer", rel, f.line, m.group(1), a.line,
                                      ("answer", a.scope, f.ident), f"{a.scope} {f.ident}",
                                      audited=a.task))
            else:
                out.items.append(Item("filed", rel, f.line, None, None,
                                      ("filed", rel, f.ident), f"{rel} {f.ident}",
                                      audited=a.task))
    return out


def answer_gaps(unread):
    """[(part, reason)]: one part per file whose audit answers the grammar
    could not all read, naming each line and why -- check_trace's parts, and
    `--pending`'s, in one wording."""
    by = {}
    for rel, n, what in unread:
        by.setdefault(rel, []).append((n, what))
    return [(f"{rel}'s audit findings",
             f"{len(rows)} line(s) of an audit's answer the grammar does not read — "
             + "; ".join(f"{rel}:{n}, {what}" for n, what in sorted(rows))
             + " (FORMATS §\"An audit's answer\")")
            for rel, rows in sorted(by.items())]


def raised(value):
    """(form, the groups of its pattern) for a `Raised.` value, or None."""
    v = " ".join(value.split())
    for form, pat in RAISED:
        m = pat.match(v)
        if m:
            return form, m.groups()
    return None


def join(listed, found):
    """Which entry covers which item, and what each entry's `Raised.` names.

    Returns ({item index: the Entry covering it}, [(Entry, what, detail)]),
    where `what` is `covers`, `resolves` (it names an item that exists, and
    covers none: a superseded attempt's, say, or the manager's own), `unknown`
    (it names nothing that exists, and `detail` says what is missing),
    `unread` (its `Raised.` does not parse, and `detail` is its line), or
    `none` (it has no `Raised.`).

    One entry covers one item, and one item needs one entry. Within the items
    an entry could name -- a report item beginning with its words, an audit's
    finding of its scope and label -- entries are paired with items as a
    maximum matching, so that entries naming words two items begin with, or
    two audits of one scope that each hold `COR-1`, are covered by as many
    entries as there are items, and none is left over by the order they were
    read in.
    """
    groups = {}
    for i, it in enumerate(found.items):
        groups.setdefault(it.group, []).append(i)
    verdicts, want = [], {}
    for e in listed:
        got = e.fields.get("Raised")
        if got is None:
            verdicts.append((e, "none", None))
            continue
        r = raised(got[1])
        if r is None:
            verdicts.append((e, "unread", got[0]))
            continue
        form, g = r
        if form == "own":
            verdicts.append((e, "resolves", None))
            continue
        if form == "report":
            ident, key, said = g
            said = words(said)
            group = ("report", ident, key)
            cands = [i for i in groups.get(group, []) if found.items[i].text.startswith(said)]
            exists = bool(cands) or any(t.startswith(said) for t in found.every.get((ident, key), []))
            missing = (f"no REPORT block for {ident} has a `{key}:` item beginning "
                       f"\"{said}\"")
        elif form == "filed":
            path, label, num = g
            group = ("filed", path, f"{label}-{num}")
            cands = list(groups.get(group, []))
            exists = bool(cands)
            missing = (f"{path} is not in devteam/" if path not in found.files
                       else f"{path} holds no finding {label}-{num}")
        else:
            scope, label, num = g
            group = ("answer", scope, f"{label}-{num}")
            cands = list(groups.get(group, []))
            exists = bool(cands)
            missing = f"no audit answer of {scope} in a task file holds {label}-{num}"
        want[e.ident, e.line] = cands
        verdicts.append((e, "match" if exists else "unknown", None if exists else missing))
    # Pair entries with items (Kuhn's augmenting paths): each entry tries the
    # items it could name, taking one already taken only if its holder can
    # move to another.
    owner = {}

    def place(key, seen):
        for i in want[key]:
            if i in seen:
                continue
            seen.add(i)
            if i not in owner or place(owner[i], seen):
                owner[i] = key
                return True
        return False

    for e, what, _ in verdicts:
        if what == "match":
            place((e.ident, e.line), set())
    by_key = {(e.ident, e.line): e for e, _, _ in verdicts}
    covered = {i: by_key[key] for i, key in owner.items()}
    holding = set(owner.values())
    out = []
    for e, what, detail in verdicts:
        if what == "match":
            what = "covers" if (e.ident, e.line) in holding else "resolves"
        out.append((e, what, detail))
    return covered, out


def disposition(value):
    """(kind, what it names) for a value in the vocabulary, or None.

    What it names is the `T-n` or `C-n` an open item is due by, the task, the
    question or the decision, or for `fixed` the list of commits, bare.
    Whitespace is layout: a value reads the same with its spaces doubled or
    its list wrapped.
    """
    v = " ".join(value.split())
    for kind, pat in VOCABULARY:
        m = pat.match(v)
        if m:
            if kind == "fixed":
                return kind, [c.strip().strip("`") for c in m.group(1).split(",")]
            return kind, m.group(1)
    return None


class Entry:
    """One `### ITM-n` entry: its heading line, and each field read whole."""

    def __init__(self, number, line, title):
        # The number as written, as check_refs keys a declaration.
        self.number, self.line, self.title = number, line, title
        self.fields = {}      # name -> (line, the value, read whole)
        self.block = []       # (line, text) for every line of the entry

    @property
    def ident(self):
        return f"ITM-{self.number}"

    def value(self, name):
        got = self.fields.get(name)
        return got[1] if got else None

    def parsed(self):
        """The disposition, as `disposition` reads it, or None."""
        got = self.fields.get("Disposition")
        return disposition(got[1]) if got else None


def entries(lines):
    """([Entry], [(line, field, what)]) for LEDGER.md's lines.

    The second list is every line the file offered in an entry's grammar that
    the grammar did not read, with the field it names, or None for a heading:
    a heading in the entry's position that does not parse, and a field named
    and not parsed, or named a second time in one entry, whose first reading
    stands. A fenced block holds no entry.
    """
    out, unread, current, fenced = [], [], None, False
    for i, line in enumerate(lines):
        n = i + 1
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEADING.match(line)
        if m:
            current = Entry(m.group(2), n, m.group(3))
            out.append(current)
            current.block.append((n, line))
            continue
        if HEADING_ISH.match(line) or ANY_HEADING.match(line):
            if HEADING_ISH.match(line):
                unread.append((n, None, "an entry heading that does not parse as "
                                        "`### ITM-n — <one line>`"))
            current = None
            continue
        if current is None:
            continue
        current.block.append((n, line))
        for name in FIELDS:
            f = FIELD[name].match(line)
            if f:
                if name in current.fields:
                    unread.append((n, name, f"a second `{name}.` in {current.ident}, "
                                            f"after line {current.fields[name][0]}"))
                else:
                    current.fields[name] = (n, result.joined(
                        lines, i, f.group(1), until=LIST_ITEMISH if name == "Needs" else None))
                break
            if FIELD_ISH[name].match(line):
                unread.append((n, name, f"`{name}.` named and not written "
                                        f"`- **{name}.** <value>`"))
                break
    return out, unread


def count(listed):
    """{kind: n} over the entries whose disposition is in the vocabulary."""
    got = {kind: 0 for kind in KINDS}
    for e in listed:
        p = e.parsed()
        if p:
            got[p[0]] += 1
    return got


def pending(devteam, as_json):
    """`--pending`: the `Raised.` line to write for every item no entry
    covers, whether it is due yet or not -- the manager runs it before the
    commit that moves a row, when the current claim's items are about to fall
    due -- each after the file and line where its text is (roadmap 0.3.3,
    L-3.5). An item's entry is written by hand until 0.3.4's `land`. A line
    this could not read, in an answer or in a `Raised.`, is named as not
    evaluated, because an item it hides is missing from the list."""
    found = found_in(devteam)
    if found is None:
        return result.could_not_run("ledger", "not a git repository", as_json)
    res = result.Result("ledger", "pending")
    listed = []
    try:
        with open(os.path.join(devteam, PATH), "rb") as fh:
            listed = entries(fh.read().decode("utf-8").split("\n"))[0]
    except FileNotFoundError:
        pass                      # no ledger: every item is pending, and that is the answer
    except (OSError, UnicodeDecodeError) as exc:
        res.gap(PATH, f"LEDGER.md cannot be read ({exc}), so no entry was matched")
    covered, verdicts = join(listed, found)
    for part, reason in answer_gaps(found.unread):
        res.gap(part, reason)
    for e, what, detail in verdicts:
        if what == "unread":
            res.gap(f"{e.ident}'s Raised.", f"{PATH}:{detail} does not parse as one of "
                    f"`Raised.`'s forms — {FORMS} — so {e.ident} covers no item")
    waiting = sorted((it.file, it.line, it.raised) for i, it in enumerate(found.items)
                     if i not in covered)
    res.count(len(found.items), "items")
    res.count(len(waiting), "pending")
    for rel, n, text in waiting:
        res.note(f"{rel}:{n}", f"- **Raised.** {text}")
    return result.emit([res], as_json)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json, argv = result.flag(argv, "--json")
    only_pending, argv = result.flag(argv, "--pending")
    if len(argv) != 1:
        return result.could_not_run("ledger", USAGE, as_json)
    project = os.path.realpath(argv[0])
    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    if not os.path.isdir(devteam):
        return result.could_not_run("ledger", "not a devteam project", as_json)
    if only_pending:
        return pending(devteam, as_json)
    res = result.Result("ledger", PATH)
    listed = []
    try:
        with open(os.path.join(devteam, PATH), "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        raw = None
        res.gap(PATH, "devteam/ has no LEDGER.md, so no entry was read")
    except OSError as exc:
        raw = None
        res.gap(PATH, f"LEDGER.md cannot be read ({exc.strerror}), so no entry was read")
    if raw is not None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            res.gap(PATH, f"LEDGER.md is not UTF-8 (byte {exc.object[exc.start]:#04x} "
                          f"at offset {exc.start}), so no entry was read")
        else:
            listed, offered = entries(text.split("\n"))
            unread = [(n, what) for n, _field, what in offered]
            # An entry whose disposition is missing, or outside the
            # vocabulary, was read and could not be counted.
            for e in listed:
                got = e.fields.get("Disposition")
                if got is None:
                    unread.append((e.line, f"{e.ident} has no `Disposition.`"))
                elif e.parsed() is None:
                    unread.append((got[0], f"{e.ident}'s disposition {got[1]!r} is not in "
                                           "the vocabulary"))
            if unread:
                unread.sort()
                res.gap("LEDGER.md's entries",
                        f"{len(unread)} line(s) the ledger's grammar does not read, so "
                        "those entries' dispositions were not counted: "
                        + "; ".join(f"line {n}, {what}" for n, what in unread)
                        + f" (the vocabulary is {GRAMMAR})")
    res.count(len(listed), "entries")
    for kind, n in count(listed).items():
        res.count(n, kind)
    for e in listed:
        got = e.fields.get("Disposition")
        res.note(e.ident, f"{got[1] if got else 'no disposition'} ({PATH}:{e.line})")
    return result.emit([res], as_json)


if __name__ == "__main__":
    sys.exit(main())
