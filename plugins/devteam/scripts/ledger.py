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
  * the first-word `open` test, which check_refs and check_trace apply to an
    audit file's own `Disposition.` lines. It was a regex copied into both
    checks (0.3.2 §3.2's joint), and it retires with those lines at step 3.4;
  * an audit's answer, which is where an audit's findings come from: the
    `AUDIT <scope> (<dimension>)` and `END AUDIT <scope>` lines that open and
    close it, and the heading each finding is, read into the answer's scope
    and its findings wherever the answer lands, in a task file or in
    `audits/` (FORMATS §"An audit's answer"; roadmap 0.3.3, L-3.4).
    check_report reads the opening and closing lines' shape from here, and
    ends a REPORT block at either.

    python3 ledger.py <project> [--json]

prints each entry's disposition and the counts by value. An entry it cannot
read -- a heading in the entry's position that does not parse, a field named
and not parsed or named twice, a disposition missing or outside the
vocabulary -- is named by its line as not evaluated, because its disposition
was not counted (roadmap 0.3.1, L-1.3). No LEDGER.md at all is not evaluated
too: nothing was read. Exit 0 clean, 2 could not run, 3 not evaluated -- the
contract is result.py's (roadmap 0.3.1, L-1.1). It reports no finding, so it
never exits 1: check_refs judges the ledger, and this prints it.

Its control is test_ledger.py.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)

USAGE = "usage: ledger.py <project> [--json]"
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
# AN AUDIT'S FINDINGS ARE ITEMS WHEREVER ITS TEXT LANDS, SO THE TEXT OPENS AND
# CLOSES ON TWO LINES THE GRAMMAR READS. pricelog's auditors answered in
# whatever shape their message took, and nothing could count what they found.
# T-10.S-3's supervisor landed its answer under a header of its own making,
# `REPORT auditor T-10.S-3 (…`, which is not a report. T-19.S-3's answer opened
# `AUDIT T-19.S-3 (correctness): **one break found.** …` inside a fence, and
# two of the items under it reached no owner (F-139). The four gate audits
# numbered their findings `## Finding 1 (…)`, `### 1.` and `## F-1 — HIGH`,
# and one of them waited four days for an owner (F-99). So an answer opens
# `AUDIT <scope> (<dimension>)` and closes `END AUDIT <scope>`, each alone on
# its line, and each finding in it is a heading carrying its dimension's
# label. The scope is read from the AUDIT line, never from a file's name:
# T-18's step audit had only its name, `pricelog-T-18-S-4-2026-09-17.md`, and
# nothing tied it to its task (0.3.1 §3.2).

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
# A finding is a heading with its dimension's label, `##` or `###`, which is
# how the audits carrying `Disposition.` declared their findings before the
# ledger (check_refs' audit heading). The number is the audit's own, from 1.
FINDING = re.compile(r"^#{2,3}\s+(" + "|".join(LABELS.values()) + r")-(\d+)\s*" + DASH
                     + r"\s*(.*?)\s*$")
# A heading that looks like a finding, in the shapes the corpus used for one:
# the gate audits' `## Finding 1 (…) —`, `### 1.` and `## F-1 — HIGH —`, and
# any label written loosely. Any other heading in an answer, `## Verdict` or
# `## Checked and found clean`, is its text.
FINDING_ISH = re.compile(r"^#{2,3}\s*[*_]*\s*(?:finding\s*#?\s*\d+\b|\d+[.)]\s"
                         r"|(?:" + "|".join(LABELS.values()) + r")[\s-]*\d+\b|[A-Z]{1,5}-\d+\b)",
                         re.I)


def is_answer_line(line):
    """Does this line open or close an audit's answer, however it is written?
    check_report ends a REPORT block at one."""
    return bool(AUDIT_ISH.match(line) or END_ISH.match(line))


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
        return LABELS.get(self.dimension)

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
    AUDIT or END AUDIT line at all is read as one answer with no scope, its
    findings counted and tied to no task, and the missing line is named.
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
        if not is_answer_line(line):
            continue
        if inside[i]:
            unread.append((i + 1, "an `AUDIT` or `END AUDIT` line inside a fenced block, where "
                                  "no answer is read: an answer is landed unfenced, so the "
                                  "findings under it are not counted"))
            continue
        m = AUDIT.match(line) or END.match(line)
        closing = bool(END_ISH.match(line))
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
                unread.append((i + 1, f"an `AUDIT` line that does not parse as {OPENING}, so "
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
        answer = Answer(None, None, None)
        _findings(lines, inside, 0, len(lines), answer, set(LABELS.values()), unread)
        out.append(answer)
        unread.append((1, f"no line opens an answer as {OPENING}, so the file's findings "
                          "are tied to no task"))
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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json, argv = result.flag(argv, "--json")
    if len(argv) != 1:
        return result.could_not_run("ledger", USAGE, as_json)
    project = os.path.realpath(argv[0])
    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    if not os.path.isdir(devteam):
        return result.could_not_run("ledger", "not a devteam project", as_json)
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
