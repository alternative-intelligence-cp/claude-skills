#!/usr/bin/env python3
"""Traceability for a project's `devteam/` directory (P-4).

Walks the chain the charter promises -- goal -> requirement -> task ->
acceptance evidence -- and reports every place it breaks. This is the check
the whole design leans on, because the prior art it is drawn from records that
every hole it ever found was found by a check that diffs two lists, and none
of them by a test.

The finding classes it emits, and the rule each enforces, are in
docs/CHECKS.md -- one home (P-34). This docstring deliberately does not
list them: it used to, and ten classes were emitted, controlled, and
absent from the lists here. `unruled-finding` in check_plugin.py keeps
docs/CHECKS.md and the code equal in both directions.

Exit 0 clean, 1 findings, 2 could not run, 3 not evaluated -- the contract
is result.py's (roadmap 0.3.1, L-1.1). Grammar: templates/FORMATS.md.
Control: test_check_trace.py (P-35).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)
import ledger  # noqa: E402 -- the ledger's grammar, and the first-word `open` test


PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = re.compile(r"<!--\s*example:begin\s*-->(.*?)<!--\s*example:end\s*-->", re.S)
# A template declares a name in one of two blocks, and the difference is what
# SETUP does with them, not what this check does: an `example:` block is
# stripped from an installed artifact, a `schema:` block ships with its marker
# lines removed. Both declare. Reading only `example:` is what made the
# charter's constraints table unable to be both shipped and checked.
SCHEMA = re.compile(r"<!--\s*schema:begin\s*-->(.*?)<!--\s*schema:end\s*-->", re.S)
TPL_FIELD = re.compile(r"^-\s+\*\*([A-Za-z][A-Za-z -]*)\.\*\*", re.M)
TPL_ROW = re.compile(r"^\|\s*([A-Za-z][^|]*?)\s*\|", re.M)


def template_names(rel, kind):
    """Names the CURRENT template declares, in order, or None if unreadable.

    Every other check in this project diffs the project against ITSELF --
    citations against declarations, tasks against requirements, reports against
    the tree. Nothing diffed it against the PLUGIN, so an artifact was
    instantiated once and diverged forever: a template row added afterwards
    reached nothing already created. A real project was signed six hours before
    two constraint rows entered the template and silently lacked both for the
    rest of its life. One of them was the checkpoint cadence, so no checkpoint
    ever fired; the other was the priority order, so twenty-six decisions cited
    an order that did not exist. Any project older than its plugin is missing
    whatever the plugin has learned since, and until now nothing said so.
    """
    path = os.path.join(PLUGIN_ROOT, "templates", rel)
    try:
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
    except OSError:
        return None
    out, seen = [], set()
    for block in EXAMPLE.findall(body) + SCHEMA.findall(body):
        pat = TPL_FIELD if kind == "field" else TPL_ROW
        for name in pat.findall(block):
            name = name.strip()
            # A table's header cell and its `---` separator are not rows.
            if kind == "row" and (name in ("Constraint", "Value") or set(name) <= set("- ")):
                continue
            if name not in seen:
                seen.add(name)
                out.append(name)
    return out or None

DASH = r"[—–-]"
# A title's separator is a dash SURROUNDED BY WHITESPACE. Neither greedy nor
# non-greedy matching on a bare dash works: non-greedy splits at the hyphen in
# "well-known", and greedy splits at the one inside "DONE (2026-09-03)". A
# hyphen inside a word or a date never has spaces around it; a separator always
# does.
SEP = r"(?:\s+[\u2014\u2013]\s+|\s+-\s+)"
GOAL = re.compile(r"^-\s+\*\*(G-\d+)\*\*\s*" + DASH)
TASK_REF = re.compile(r"\bT-\d+\b")
DECISION_REF = re.compile(r"\bD-\d+\b")
REQ = re.compile(r"^###\s+(R-\d+)\s*" + DASH + r"\s*(.*)$")
TASK = re.compile(r"^#\s+(T-\d+)" + SEP + r"(.*?)" + SEP + r"(\S.*)$")
# The hyphen is required: `Requires-write.` parsed as no field at all under
# `[A-Za-z ]`, so `missing-field` fired on every requirement that HAD it --
# a check reporting the absence of the thing in front of it.
FIELD = re.compile(r"^-\s+\*\*([A-Za-z][A-Za-z -]*)\.\*\*\s*(.*)$")

# A FIELD READ AS IDENTIFIERS HOLDS IDENTIFIERS ONLY (roadmap 0.3.2, L-2.3):
# `none`, or bare identifiers separated by commas, continuing onto indented
# lines if it must. Each field holds one kind, or two for `Informs.`.
#
# Two readings of one field disagreed, and each was wrong somewhere. A regex
# over the field read every identifier a sentence mentioned, so T-17's own
# name in the prose of its `Depends on.` became an edge to itself, and an
# unrelated task named there would have held T-17 back with no finding at all
# (F-95, pricelog RECORD.md:1137). Cutting at commas and comparing each piece
# whole read `R-2 — **completed here` as a requirement that does not exist, so
# T-19 never listed R-2 and every state from its claim reported a one-sided
# link (F-132, RECORD.md:1675). So a piece is read whole or not at all: a piece
# that is not `none` or a bare identifier of the field's kind is never read as
# one, and the field is named as not evaluated, naming the piece. The reason
# goes on a bullet of its own, as T-8's file carries it. `Satisfies.` is read
# the same way because it is read as identifiers too, and reading it whole by
# regex would carry F-95 onto its continuation lines.
#
# `Re-establishes.` is L-2.4's: the requirements whose acceptance a task
# re-establishes without taking the discharge. It is what T-17 and T-18 wrote
# as prose inside `Discharges.`, which no reading could get right.
ID_FIELDS = {"Satisfies": ("G",), "Discharges": ("R",), "Re-establishes": ("R",),
             "Informs": ("R", "G"), "Depends on": ("T",)}
ID_WORDS = {("G",): "goal", ("R",): "requirement", ("R", "G"): "requirement or goal",
            ("T",): "task"}
BARE_ID = re.compile(r"^([A-Z]{1,2})-\d+$")


def id_list(value, kinds):
    """([the bare identifiers], [the pieces that are not one]) of an
    identifier field's whole value -- the one reading every class uses (P-34).

    An empty value names nothing and is not a gap: a field left blank is read
    as blank, and whatever needs it says so. `none` is the whole value or it
    is a piece like any other.
    """
    value = value.strip()
    if not value or value == "none":
        return [], []
    ids, bad = [], []
    for piece in (p.strip() for p in value.split(",")):
        if not piece:
            continue
        m = BARE_ID.match(piece)
        if m and m.group(1) in kinds:
            if piece not in ids:
                ids.append(piece)
        else:
            bad.append(piece)
    return ids, bad

# THE LOOSE SHAPES (roadmap 0.3.1, L-1.3): what a source OFFERS, whatever the
# grammar above accepts of it. Each is deliberately wider than its grammar --
# a heading naming a requirement or a task however it is punctuated, any list
# item or table row inside a section -- so that a row written slightly wrong
# is counted as offered and named, rather than never seen. Separator rows of
# a table are not rows.
#
# A heading that DECLARES something written wrong is offered; one that merely
# MENTIONS it is not. So a step's heading in an execution record -- `# T-10.S-3
# Adversarial Audit`, measured in pricelog -- and a possessive -- `## R-4's
# history` -- are prose about an identifier, not a title that failed.
REQ_ISH = re.compile(r"^#{1,6}\s*R-?\s*\d+\b(?![.'’])")
TASK_ISH = re.compile(r"^#\s*T-?\s*\d+\b(?![.'’])")
SECTION_ROW = re.compile(r"^(?:[-*+]\s|\d+[.)]\s|\|(?!\s*:?-{3,}))")
PROTECTED_ISH = re.compile(r"^\|\s*[*`_]*\s*protected[\s_-]*paths\b", re.I)
BOARD_ROW_ISH = re.compile(r"^\|\s*(?:\[|\*\*|\*|`)*\s*T-\d+\b")
AUDIT_HEADING_ISH = re.compile(r"^#{2,3}\s+(?:finding\s+\d+\b|\d+\.\s|[A-Z]{1,5}-\d+\b)", re.I)

# A value the interview has not filled in yet. Reported as its own finding
# rather than silently treated as present -- a placeholder that passes a check
# is worse than one that fails it.
PLACEHOLDER = re.compile(r"^\s*(<[^>]*>|_none yet_|tbd|todo|\.\.\.)?\s*$", re.I)

# DERIVED FROM THE TEMPLATES, not restated here. A hardcoded list is a second
# home for the template's contract, and the two drift silently -- which is the
# defect this whole mechanism exists to catch, so restating it here would have
# been the check committing its own finding. The literals remain only as a
# fallback for a plugin whose templates cannot be read, because a check that
# silently stops checking is worse than one that is slightly out of date.
#
# A FALLBACK IS STILL A PART NOT EVALUATED (roadmap 0.3.1, L-1.3). The charter
# rows had no literals behind them, so an unreadable template made
# `template-drift` compare the charter against nothing and report clean -- found
# by 0.3.1's own mutation run, from a copy of scripts/ without templates/ beside
# it. Each template that cannot be read is now named in the line, and the
# field lists say they fell back.
_REQ_TEMPLATE = template_names("REQUIREMENTS.md", "field")
_TASK_TEMPLATE = template_names("tasks/TASK.md", "field")
_CHARTER_TEMPLATE = template_names("CHARTER.md", "row")
REQ_FIELDS = tuple(_REQ_TEMPLATE or
                   ("Statement", "Satisfies", "Source", "Acceptance",
                    "Requires-write", "Priority", "Status"))
TASK_FIELDS = tuple(n for n in (_TASK_TEMPLATE or
                                ("Discharges", "Depends on", "Scope", "Gate", "Verify"))
                    if n != "Kind")
CHARTER_ROWS = _CHARTER_TEMPLATE or []
TEMPLATE_GAPS = [
    (part, f"templates/{rel} cannot be read beside check_trace, so {what}")
    for got, part, rel, what in (
        (_CHARTER_TEMPLATE, "template-drift", "CHARTER.md",
         "the charter was compared against no template row"),
        (_REQ_TEMPLATE, "missing-field in requirements", "REQUIREMENTS.md",
         "requirements were checked against the field list built into this script"),
        (_TASK_TEMPLATE, "missing-field in tasks", "tasks/TASK.md",
         "tasks were checked against the field list built into this script"))
    if got is None]
# Fields a check below reads by NAME but that no template lists, so that a
# line naming one in a form the grammar does not accept is still offered.
REQ_EXTRA = ("Shape reviewed", "Requires-write amended")
TASK_EXTRA = ("Kind", "Informs", "Because", "Re-establishes")

STRUCK = re.compile(r"^struck\b", re.I)
# The requirement statuses a closed task may leave, each naming it (FORMATS
# §"Status vocabularies"; roadmap 0.3.2, L-2.4). `check_refs` judges the whole
# grammar -- the `; D-n` and `; Q-n` a partial and an awaited discharge carry.
CLOSED_STATUSES = ("discharged", "partly-discharged", "awaiting-judgement")

# The classes that read the WORKING STATE rather than a commit's tree or its
# history, which `--at-commit` excludes (result.AT_COMMIT; roadmap 0.3.1, L-1.5).
# A class added here later that reads anything a clean checkout of one commit
# does not hold belongs in this list, or the gate evaluates it where it can see
# nothing.
WORKING_STATE = ("untracked-file",)

# --- the amendment re-affirmation (P-48) ---------------------------------
DM_DECL = re.compile(r"^-\s+\*\*(DM-\d+)\*\*\s*" + DASH)
SECTION = re.compile(r"^##\s+(.+?)\s*$")
AMENDMENT_ENTRY = re.compile(r"^###\s+(.+?)\s*$")
# WHICH ENTRY IS "THE LATEST" IS A DECLARED FIELD, NOT A POSITION. Charters
# write amendments NEWEST FIRST, so taking the last `###` in the section picks
# the OLDEST -- which is what the first draft of this check did, reporting
# against Version 2 of a charter at Version 17. The version number is parsed
# and the maximum wins; document order is only the fallback, and then it is
# the FIRST entry.
AMENDMENT_VERSION = re.compile(r"^Version\s+(\d+)\b", re.I)
REAFFIRM_OPEN = re.compile(r"^-\s+\*\*Re-affirmed\.\*\*\s*$")
# `  - <name> — <verdict>` under that block, read WHOLE -- the item's line and
# every line continuing it, joined (roadmap 0.3.2, L-2.3) -- so this matches
# the joined text, whose indentation is gone. The name may itself contain a
# hyphen (`DM-1`, `Lint / format command`), so the separator is a dash with
# whitespace on both sides -- the same rule every other title in this grammar
# uses, and for the same reason.
REAFFIRM_ITEM = re.compile(r"^-\s+(.+?)" + SEP + r"(.+?)\s*$")
# `added (this entry)` is L-2.9's: the vocabulary had no word for a condition
# the entry adds, so four authors invented one (N-4, pricelog RECORD.md:938,
# :970-971).
REAFFIRM_VERDICT = re.compile(r"^(holds|amended \(this entry\)|added \(this entry\)"
                              r"|struck \(D-\d+[^)]*\))\.?\s*$", re.I)
# What an entry OFFERS as a re-affirmation when it has no `Re-affirmed.` block:
# a list item, at any depth, whose text before its first separator is one of
# the charter's conditions. F-36's entry opened its list with `**Every other
# row, checked rather than assumed:**` (pricelog RECORD.md:563); a prose bullet
# about the change, as Version 13 carries two, names no condition this way.
REAFFIRM_ISH = re.compile(r"^\s*[-*+]\s+(.+?)" + SEP)
# The charter's header, `**Version.** <n> · **Status.** …`: the pointer to its
# newest entry (L-2.9's `stale-version-header`). What it OFFERS is any line
# above the first section that starts by naming a version.
HEADER_VERSION = re.compile(r"^\*\*Version\.\*\*\s*(\d+)\b")
HEADER_ISH = re.compile(r"^[*_\s]*Version\b", re.I)



# A path list is written ONE WAY everywhere: the field, then indented backticked
# items under it. `Scope.` on a task and `Requires-write.` on a requirement are the
# same shape deliberately -- this project has already paid for a record with two
# grammars for one thing, where an author used one, forgot the other, and shipped
# a red tree that cost somebody else's agents time.
LIST_FIELD = re.compile(r"^-\s+\*\*(Scope|Requires-write)\.\*\*\s*(.*)$")
LIST_ITEM = re.compile(r"^\s+-\s+`?([^`\s]+)`?\s*$")
# What a path list OFFERS (L-1.3): any indented list item under the field. An
# item with its reason written inline -- `` - `src/` — because … `` -- is not a
# path, and used to be skipped here in silence; check_scope has reported the
# same shape as `unparseable-scope-entry` since 0.2.
LIST_ITEMISH = re.compile(r"^\s+[-*+]\s+\S")
NEXT_FIELD = re.compile(r"^-\s+\*\*[A-Za-z]|^#")
# One entry of a path list written beside its field rather than under it: a
# path, backticked or not, and nothing else.
BARE_PATH = re.compile(r"^`?[^`\s]+`?$")


def path_lists(lines, unparsed=None):
    """{field name: [entries]} for every `Scope.`/`Requires-write.` list in a block.

    `unparsed`, when given, collects (index into `lines`, field name) for each
    entry of a path list that does not parse as a path.
    """
    out, collecting = {}, None
    for i, line in enumerate(lines):
        m = LIST_FIELD.match(line)
        if m:
            collecting = m.group(1)
            out.setdefault(collecting, [])
            # A value written beside the field is read whole (roadmap 0.3.2,
            # L-2.3): a line continuing it that was not a list item used to be
            # dropped in silence. Each comma-separated piece is a path, or it
            # is named as a list item that is not one is, never kept as an
            # entry that matches nothing.
            inline = result.joined(lines, i, m.group(2), until=LIST_ITEMISH)
            if inline and not PLACEHOLDER.search(inline):
                for piece in (p.strip() for p in inline.split(",")):
                    if BARE_PATH.match(piece):
                        out[collecting].append(piece.strip("`"))
                    elif piece and unparsed is not None:
                        unparsed.append((i, collecting))
            continue
        if collecting:
            item = LIST_ITEM.match(line)
            if item:
                # An UNFILLED item is not a path. `<paths>` under a template's
                # `Requires-write.` was collected as a literal filename, so every
                # freshly scaffolded requirement reported `unreachable-
                # acceptance` against a file called `<paths>` -- a new project
                # meeting a wall of findings about its own blank form. The
                # inline branch above already dropped these; the item branch
                # did not, which is the same field with two behaviours.
                if not PLACEHOLDER.search(item.group(1)):
                    out[collecting].append(item.group(1))
                continue
            if LIST_ITEMISH.match(line):
                if unparsed is not None:
                    unparsed.append((i, collecting))
                continue
            if line.strip() and NEXT_FIELD.match(line):
                collecting = None
    return out


def contains(scope, path):
    """Does a declared scope entry cover this path? Prefix match on segments."""
    path = path.strip().strip("`").rstrip("/")
    for entry in scope:
        e = entry.strip().strip("`").rstrip("/")
        if not e:
            continue
        if path == e or path.startswith(e + "/"):
            return True
    return False

def read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read().split("\n")
    except OSError:
        return []


class Fields(dict):
    """A block's fields, each held WHOLE -- its first line and every line that
    continues it (roadmap 0.3.2, L-2.3) -- and what a class could not read.

    0.3.1 kept a field's first line only, and named a field that continued past
    it as not evaluated wherever some class read it (L-1.3). F-132 was that
    shape: a `Discharges.` field whose first line ended mid-sentence. Every
    field is now read whole, so a wrapped field is simply read.

    What can still go unread is a piece of an identifier field that is not an
    identifier. `ids` is the one reading of those fields, and it records each
    such piece for the field it read, so a field no class reads is never
    named -- the same rule 0.3.1 kept for a wrapped field nothing read.
    """

    def __init__(self):
        super().__init__()
        self.line, self.misparsed, self.pieces, self._ids = {}, {}, {}, {}

    def ids(self, name):
        """The bare identifiers the field `name` holds (`id_list`), with each
        piece that is not one recorded for `field_gaps`."""
        if name not in self._ids:
            got, bad = id_list(self.get(name, ""), ID_FIELDS[name])
            self._ids[name] = got
            if bad:
                self.pieces[name] = bad
        return self._ids[name]


def _named_field(name):
    """A line that NAMES this field, however it is decorated: the loose shape."""
    return re.compile(r"^-\s+\**\s*" + re.escape(name) + r"\s*\**\s*[.:]", re.I)


def parse_blocks(lines, header, fields_for):
    """Yield (identifier, line-number, extra, Fields) per heading, each field
    read whole across its continuation lines (`result.joined`).

    `fields_for` are the names the caller reads. A line naming one of them that
    FIELD does not accept as that name is recorded in `Fields.misparsed`: a
    field line offered and not parsed (L-1.3).
    """
    loose = [(name, _named_field(name)) for name in fields_for]
    cur = None
    for n, line in enumerate(lines, 1):
        m = header.match(line)
        if m:
            if cur:
                yield cur
            cur = (m.group(1), n, m.groups()[1:], Fields())
            continue
        if cur:
            f = FIELD.match(line)
            name = f.group(1).strip() if f else None
            if f:
                cur[3][name] = result.joined(lines, n - 1, f.group(2))
                cur[3].line[name] = n
            for want, pat in loose:
                if want != name and pat.match(line):
                    cur[3].misparsed.setdefault(want, n)
    if cur:
        yield cur


def block_starts(lines, header):
    """{identifier: the 1-based line of its heading}, as `blocks_of` keys them."""
    return {m.group(1): n for n, m in ((n, header.match(l)) for n, l in enumerate(lines, 1)) if m}


def heading_gaps(lines, rel, loose, strict, what, grammar):
    """[(part, reason)] when `lines` offer headings `strict` does not accept."""
    offered = [n for n, line in enumerate(lines, 1) if loose.match(line)]
    missed = [n for n in offered if not strict.match(lines[n - 1])]
    if not missed:
        return []
    return [(f"{rel}'s {what}", result.unparsed(
        [(rel, n) for n in missed], len(offered), what, grammar,
        "each is invisible to every class that reads one"))]


def list_gaps(ident, bad, rel, start):
    """[(part, reason)] for path-list items `path_lists` offered and could not read.

    `bad` holds (index into the block's lines, field); the block's lines begin
    on the line after its heading at `start`.
    """
    out = {}
    for i, field in bad:
        out.setdefault(field, []).append((rel, start + 1 + i))
    return [(f"{ident}'s {field}.",
             (f"1 entry of the field, listed under it or written beside it, does"
              if len(rows) == 1 else
              f"{len(rows)} entries of the field, listed under it or written beside it, do")
             + f" not parse as a bare `path`, so no class compares against what they "
             f"name ({result.anchors(rows)})")
            for field, rows in sorted(out.items())]


def pieces_reason(where, name, bad):
    """Why an identifier field is not evaluated: the pieces it holds that are
    not identifiers, each named (roadmap 0.3.2, L-2.3)."""
    shown = [repr(p[:48] + "…" if len(p) > 48 else p) for p in bad[:3]]
    more = f" and {len(bad) - 3} more" if len(bad) > 3 else ""
    word = ID_WORDS[ID_FIELDS[name]]
    return (f"{where} holds {len(bad)} piece(s) that are not `none` or a bare {word} "
            f"identifier — {', '.join(shown)}{more} — so no class reads them, and no "
            "identifier inside one is read. Give the field identifiers only, and "
            "the reason a bullet of its own")


def field_gaps(ident, where, fields):
    """[(part, reason)] for a block's fields that a class read and could not
    read whole: an identifier field holding a piece that is not one."""
    rel = where.rsplit(":", 1)[0]
    out = [(f"{ident}'s {name}.", pieces_reason(f"{rel}:{fields.line[name]}", name, bad))
           for name, bad in sorted(fields.pieces.items())]
    # A misparsed line is a LOSS only when the field never parsed in this
    # block. The block runs to the end of the file, so an execution record
    # quoting `- **Scope:** check_scope … prints clean` (pricelog's T-16) is a
    # mention; the task's real `Scope.` field was read.
    out += [(f"{ident}'s {name}.",
             f"{rel}:{n} names the field and does not parse as `- **{name}.** <value>`, "
             "and the field is read nowhere else in the block")
            for name, n in sorted(fields.misparsed.items()) if name not in fields]
    return out


def section_lines(lines, title):
    """(first line number, lines) of the `## <title>` section, or (None, [])."""
    start = None
    for n, line in enumerate(lines, 1):
        m = SECTION.match(line)
        if m and start is None and m.group(1).strip().lower() == title:
            start = n
        elif m and start is not None:
            return start, lines[start:n - 1]
    return (start, lines[start:]) if start is not None else (None, [])


# --- estimate-step-mismatch (roadmap 0.3.2, L-2.10) --------------------------
# The estimate states its model, `model=<steps>x440000x1.78+150000` (P-41), and
# `<steps>` is the step-units AS PLANNED -- the plan skill's model, whose rounds
# rate `r` prices every step a supervisor adds once the task is running. So the
# count is compared with the task's steps only while its title reads PLANNED:
# the owner's answer of 2026-09-24, over comparing in every state, which would
# have refused 13 of pricelog's 19 tasks for steps their supervisors added.
# pricelog's T-12 and T-16 each listed four steps under `model=3x…`, and only
# arithmetic caught it (RECORD.md:946); T-8 was committed that way and never
# caught at all.
ESTIMATE_MODEL = re.compile(r"\bmodel=(\d+)x")
# A step line, FORMATS §"Status vocabularies": `- [ ] **S-n** — …`, ticked
# `[x]` or struck `[~]`. A struck step was estimated, so it counts.
STEP_LINE = re.compile(r"^[-*+]\s+(?:\[[ xX~]\]\s+)?(?:~~)?\**\s*S-(\d+)\b")
# What `## Steps` OFFERS (L-1.3): every top-level list item in it.
STEP_ISH = re.compile(r"^(?:[-*+]|\d+[.)])\s+\S")


def planned_steps(lines):
    """([the step numbers under `## Steps`], [1-based lines offered there that
    are not a step line]). A step named twice -- a re-attempt's own line --
    is one step."""
    start, body = section_lines(lines, "steps")
    got, missed = [], []
    for k, line in enumerate(body):
        if not STEP_ISH.match(line):
            continue
        m = STEP_LINE.match(line)
        if not m:
            missed.append(start + 1 + k)
        elif m.group(1) not in got:
            got.append(m.group(1))
    return got, missed


def blocks_of(lines, header):
    """{identifier: [its lines]} -- `parse_blocks` keeps fields, not ranges."""
    out, cur = {}, None
    for line in lines:
        m = header.match(line)
        if m:
            cur = m.group(1)
            out[cur] = []
            continue
        if cur is not None:
            out[cur].append(line)
    return out



def first_declared(devteam):
    """({R-n: first `Requires-write.`}, {R-n: semantic amendments since review}).

    Walks the file's history oldest-first and records the value each
    requirement had when it first appeared. This is what makes "supersede,
    never edit" a control rather than a request: the planner draws the scopes
    AND could edit the requirement, so either list can be tuned until the
    check agrees with itself -- a judge trying his own case, and green having
    measured nothing.
    """
    try:
        log = subprocess.run(["git", "-C", devteam, "log", "--format=%H",
                              "--reverse", "--", "REQUIREMENTS.md"],
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    # WHAT THE HISTORY DID NOT SHOW (L-1.3). A shallow clone hands this walk
    # a history that starts partway, so a requirement's first declaration and
    # its rewrites before the cut are not in it; and a revision `git show`
    # cannot produce is skipped. Churn compares each revision's fields WHOLE
    # (roadmap 0.3.2, L-2.3), so a rewrite past a field's first line counts,
    # and rewrapping the same words does not.
    gaps, unread = [], []
    shallow = subprocess.run(["git", "-C", devteam, "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True)
    if shallow.stdout.strip() == "true":
        gaps.append(("REQUIREMENTS.md's history",
                     "the repository is a shallow clone, so unrecorded-amendment and "
                     "re-litigated-requirement read a history that starts partway"))
    seen, prev, churn = {}, {}, {}
    for sha in (s for s in log.split("\n") if s.strip()):
        try:
            got = subprocess.run(["git", "-C", devteam, "show", f"{sha}:./REQUIREMENTS.md"],
                                 capture_output=True, text=True)
        except OSError:
            got = None
        if got is None or got.returncode != 0:
            # A revision in which the file does not exist -- the commit that
            # deleted it -- has nothing to read, and is no gap.
            err = got.stderr if got is not None else ""
            if "does not exist" not in err and "exists on disk, but not in" not in err:
                unread.append(sha[:7])
            continue
        blob = got.stdout
        lines = blob.split("\n")
        for ident, block in blocks_of(lines, REQ).items():
            seen.setdefault(ident, path_lists(block).get("Requires-write", []))
        # SEMANTIC churn, in the same pass. Counting every edit to a
        # requirement is useless: measured over a real project it flagged
        # twelve of thirteen, because a status moving `open` -> `in-progress`
        # -> `discharged` and a field added later are edits too. Counting only
        # `Statement.` and `Acceptance.` -- what the requirement MEANS --
        # separated re-litigation from bookkeeping on the same corpus, and a
        # `Shape reviewed.` line resets it, or a requirement could never clear
        # this by being rewritten, since rewriting it is another change.
        for ident, n, _, fields in parse_blocks(lines, REQ, REQ_FIELDS):
            now = (fields.get("Statement", ""), fields.get("Acceptance", ""),
                   fields.get("Shape reviewed", ""))
            was = prev.get(ident)
            if was is not None:
                if was[2] != now[2]:
                    churn[ident] = 0
                elif was[:2] != now[:2]:
                    churn[ident] = churn.get(ident, 0) + 1
            else:
                churn.setdefault(ident, 0)
            prev[ident] = now
    if unread:
        gaps.append(("REQUIREMENTS.md's history",
                     f"{len(unread)} revision(s) could not be read ({', '.join(unread)}), "
                     "so unrecorded-amendment and re-litigated-requirement skipped them"))
    return seen, churn, gaps


# THE BOARD, READ AS ITS GRAMMAR WRITES IT (roadmap 0.3.2, L-2.1). The Tasks
# table is the one whose header row names `Task` first and has a `State`
# column, and a row's state is the cell under that header. The regex this
# replaces ran over EVERY line of the board and took a row's LAST cell as its
# state, so pricelog's in-flight row for T-19 was compared with its `Note`; and
# it wanted a bare `T-n` where every real row is a link, so for that project's
# whole life board-drift compared nothing and said clean (F-70). The table is
# found by its header rather than by its `## Tasks` heading, so a board written
# without the heading reads the same.
TABLE_ROW = re.compile(r"^\|")
LINK_TEXT = re.compile(r"^\[([^\]]*)\]\([^)]*\)$")
TASK_ID = re.compile(r"^T-\d+$")

# FORMATS' board task states (§"Status vocabularies"), matched WHOLE. A reason
# goes in the in-flight table's Note, never after the state: pricelog wrote
# `CLAIMED <label> — stopped; restarts under §9a …` and a dozen like it, a
# sentence where a token belongs (N-4's second cause). BLOCKED may name several
# blockers, comma-separated, for the reason a requirement's status may name
# several tasks: pricelog blocked tasks on two at once, and one id would have
# said something untrue.
BOARD_STATE = re.compile(r"^(?:—|-|CLAIMED \S+|BLOCKED on [TQ]-\d+(?:, [TQ]-\d+)*|DONE"
                         r"|ACCEPTED \(\d{4}-\d{2}-\d{2}, D-\d+\))$")


def cells(line):
    """A table row's cells, stripped, without the empty cells outside its pipes."""
    parts = line.strip().split("|")
    return [c.strip() for c in parts[1:-1 if line.strip().endswith("|") else None]]


def plain(cell):
    """A cell's text with its decoration peeled, in any order: a link becomes
    its text, and bold, italics and backticks come off both ends."""
    c = cell.strip()
    while True:
        before = c
        c = c.strip("*`_ ").strip()
        m = LINK_TEXT.match(c)
        if m:
            c = m.group(1).strip()
        if c == before:
            return c


def board_rows(lines):
    """([(T-n, its state, its line)], [lines offered and not read], found).

    `found` is False when no table on the board has a `Task` first column and
    a `State` column. A row of that table is OFFERED when its first cell looks
    like a task in any decoration (`BOARD_ROW_ISH`), and READ when that cell
    names exactly one task and the row has one cell per column of the header.
    A row in any other table -- the in-flight table above all -- is not
    offered: `in_flight` reads that one.
    """
    out, missed, found, n = [], [], False, 0
    while n < len(lines):
        if not TABLE_ROW.match(lines[n]):
            n += 1
            continue
        start = n
        while n < len(lines) and TABLE_ROW.match(lines[n]):
            n += 1
        table = lines[start:n]
        head = [plain(c).lower() for c in cells(table[0])]
        if (len(table) < 2 or not TABLE_RULE.match(table[1])
                or not head or head[0] != "task" or "state" not in head):
            continue
        found, col = True, head.index("state")
        for line_no, line in enumerate(table[2:], start + 3):
            if not BOARD_ROW_ISH.match(line):
                continue
            row = cells(line)
            tid = plain(row[0]) if row else ""
            if len(row) != len(head) or not TASK_ID.match(tid) or not plain(row[col]):
                missed.append(line_no)
                continue
            # Bold and backticks anywhere in the state are decoration:
            # pricelog writes `**DONE**` and `**STOPPED (D-67)** — …`.
            out.append((tid, " ".join(re.sub(r"\*\*|`", "", row[col]).split()), line_no))
    return out, missed, found


# What a board State and a task title may say about one task at one moment.
# Not an equality -- the two vocabularies are different by design, the board
# saying what a reader needs and the title saying what the task holds.
BOARD_PHASES = {
    "—": ("PLANNED",), "-": ("PLANNED",),
    # PLANNED is legal under CLAIMED and it is not an exemption for
    # convenience -- this pair is the one thing this check structurally cannot
    # decide, and something else already owns it.
    #
    # A claim is a commit and the commit authorises the dispatch, so the board
    # says CLAIMED first. The title is the SUPERVISOR's to write -- established
    # at cost when a re-claim commit that also set a title made itself
    # retroactively a foreign write -- so there is an unbounded gap between two
    # agents, and a supervisor that spends ten minutes reading the charter
    # holds it open for ten minutes. It also does not close against COMMITTED
    # state until the supervisor commits, so a clone, a `git archive` or CI
    # sees it on a perfectly healthy task.
    #
    # Whether that pair is a healthy dispatch or a claim whose supervisor never
    # started depends on ONE FACT NOT IN ANY FILE: is an agent alive on it.
    # `ListAgents` answers that and this check has no access to it, which is
    # exactly why §3's recovery table carries the `PLANNED | any` row. Firing
    # here would put a false stop immediately before the procedure that decides
    # it -- and `run` §1 ran this check two steps BEFORE recovery, so a fresh
    # session resuming a project with a dead supervisor stopped on a finding it
    # was about to repair.
    "CLAIMED": ("RUNNING", "PLANNED"),
    "BLOCKED": ("PLANNED", "BLOCKED", "NEEDS-DECISION"),
    "DONE": ("DONE",),
    "ACCEPTED": ("ACCEPTED",),
}

# WHILE A CLAIM IS HELD (roadmap 0.3.2, L-2.2). The manager moves the board only
# after the verifier returns (P-13, P-18), and the title is the supervisor's
# line, so every supervisor's close and every stop lands with CLAIMED still on
# the board. 0.3.1 met this at its gate for DONE, which is F-19's window; a
# supervisor that stops NEEDS-DECISION meets it too, and could not repair it,
# because the board is not its to edit. So while the task has a row in the
# in-flight table -- the claim protocol releases that row only on a PASS --
# CLAIMED allows every state a supervisor writes. Without the row, only the two
# above. Planted both ways, as the run's own mutation (pricelog RECORD.md:487).
CLAIM_HELD = ("DONE", "READY-TO-AUDIT", "NEEDS-DECISION", "BLOCKED")


IN_FLIGHT_ROW = re.compile(r"^\|\s*(?:\[|\*\*|\*|`)*\s*(T-\d+)\b")
TABLE_RULE = re.compile(r"^\|\s*:?-{3,}")


def in_flight(devteam):
    """({T-n: its line in BOARD.md}, [lines of rows naming no task]) for the
    board's `## In flight` table.

    THE GATE'S ONE ALLOWANCE KEYS ON THIS TABLE (roadmap 0.3.1, L-1.5). The
    claim protocol releases a claim only on a verifier's PASS, so a task still
    in this table has not been verified, and that is the whole of F-19's
    window (pricelog RECORD.md:369). A row whose first cell names no task --
    other than the template's `—` placeholder and the header -- is returned
    as unparsed, so the allowance cannot read a task into it and fails closed.
    """
    rows, unparsed = in_flight_rows(read(devteam, "BOARD.md"))
    out = {}
    for tid, _label, n in rows:
        out.setdefault(tid, n)
    return out, unparsed


def in_flight_rows(lines):
    """([(T-n, its claim label or None, its line)], [lines of rows naming no
    task]) for the `## In flight` table of a board's lines -- the table's one
    reader, which `in_flight` and the claim's home (claim.py) both read.

    The label is the cell under the header's `Agent label`, decoration
    peeled, as the Tasks table's state is the cell under `State`. It is None
    when the table has no such column, the cell is a placeholder, or the row
    has a cell more or fewer than its header, so that a label is never read
    from the wrong column (roadmap 0.3.2, L-2.5).
    """
    start, body = section_lines(lines, "in flight")
    out, unparsed, col, width = [], [], None, 0
    if start is None:
        return out, unparsed
    for k, line in enumerate(body):
        if not line.startswith("|") or TABLE_RULE.match(line):
            continue
        first = line.split("|")[1].strip().strip("*`_ ")
        if first.lower() == "task":
            head = [plain(c).lower() for c in cells(line)]
            col = head.index("agent label") if "agent label" in head else None
            width = len(head)
            continue
        m = IN_FLIGHT_ROW.match(line)
        if m:
            row = cells(line)
            label = plain(row[col]) if col is not None and len(row) == width else ""
            out.append((m.group(1), label if label not in ("", "—", "-") else None,
                        start + 1 + k))
        elif first.lower() not in ("—", "-", ""):
            unparsed.append(start + 1 + k)
    return out, unparsed


def requirement_statuses(devteam):
    """{R-n: its `Status.` value}, read from REQUIREMENTS.md as `check` reads
    it -- for the gate's one allowance, which asks which task a requirement
    names as in progress (roadmap 0.3.1, L-1.5)."""
    return {ident: fields.get("Status", "").strip()
            for ident, _n, _x, fields in parse_blocks(read(devteam, "REQUIREMENTS.md"),
                                                     REQ, REQ_FIELDS)}

def check(devteam):
    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))
    # Parts not evaluated, as (part, reason) -- never findings, so none of them
    # needs a CHECKS.md row, and they reach the Result through `res.gap`.
    gaps = list(TEMPLATE_GAPS)
    for rel, what in (("CHARTER.md", "no goal, protected path or amendment was read"),
                      ("REQUIREMENTS.md", "no requirement was read"),
                      ("BOARD.md", "board-drift compared nothing")):
        if not os.path.isfile(os.path.join(devteam, rel)):
            gaps.append((rel, f"missing, so {what}"))

    goals, reqs, tasks = {}, {}, {}

    # WHAT THIS CHECK READS, AS GIT WOULD SHOW IT (roadmap 0.3.1, L-1.4):
    # tracked files and untracked ones no ignore rule covers. Task files were
    # read from the index alone, so a new one was invisible until staged
    # (F-131). Each untracked file read is now a finding of its own.
    listing = result.listed(devteam, "CHARTER.md", "REQUIREMENTS.md", "BOARD.md",
                            "tasks/*.md", "audits/*.md")
    if listing is None:
        return None
    every, untracked = listing
    for rel in sorted(untracked):
        add("untracked-file", rel, result.UNTRACKED)

    charter = read(devteam, "CHARTER.md")
    for n, line in enumerate(charter, 1):
        m = GOAL.match(line)
        if m:
            goals[m.group(1)] = f"CHARTER.md:{n}"
    # What the Goals section OFFERS: every top-level list item and table row
    # in it. GOAL is read over the whole charter and that is unchanged; this
    # only names a row written in the section that GOAL does not accept.
    start, body = section_lines(charter, "goals")
    offered = [start + 1 + k for k, line in enumerate(body) if SECTION_ROW.match(line)]
    missed = [n for n in offered if not GOAL.match(charter[n - 1])]
    if missed:
        gaps.append(("the charter's goals", result.unparsed(
            [("CHARTER.md", n) for n in missed], len(offered), "rows in its Goals section",
            "`- **G-n** — <one line>`", "orphan-scope and every goal reference ran without them")))
    elif charter and start is None and not goals:
        gaps.append(("the charter's goals", "CHARTER.md has no `## Goals` section and "
                     "declares no goal, so no goal was read"))

    # THE CHARTER AGAINST THE TEMPLATE IT CAME FROM.
    have = {m.group(1).strip() for m in (TPL_ROW.match(l) for l in charter) if m}
    for row in CHARTER_ROWS:
        if row not in have:
            add("template-drift", "CHARTER.md",
                f"the charter has no `{row}` row, which the current template "
                "declares. A charter signed before the template gained a row "
                "never acquires it, and nothing else would ever say so")

    # --- unparseable-protected-path ---------------------------------------
    # The charter's `Protected paths` cell is the ONLY thing telling the guard
    # which trees are off-limits, and the guard reads it by splitting on commas
    # and semicolons and stripping backticks. A cell written as PROSE therefore
    # yields sentence fragments, each of which becomes a path that matches
    # nothing -- so the row reads correctly to every human who checks it and
    # protects nothing at all, with no check anywhere saying so.
    #
    # MEASURED, 0.2.8's end-to-end walk, in a charter written by the session
    # that had just read the guard's source:
    #
    #   | Protected paths | `devteam/` - the pipeline's own record. Readable by
    #     every role, written only by the manager and the supervisors |
    #
    # split into two entries, neither a path, and a `Write` to
    # `<project>/devteam/CHARTER.md` from a non-writer session was ALLOWED.
    # Rewritten as a bare `` `devteam/` `` the same write is refused, so the
    # mechanism was never broken: the cell FORMAT is load-bearing and nothing
    # said so. This is the second instance of the shape `setup/SKILL.md`
    # already warns about for unexpanded variables -- a thing written the
    # natural way that passes silently and looks exactly like a guard that is
    # not installed. The first cost four false negatives and a retracted claim.
    #
    # THE RULE IS DECLARED RATHER THAN PROPOSED (F-113): templates/CHARTER.md's
    # own `Protected paths` cell states the grammar -- one path per entry,
    # comma-separated, nothing else. This enforces that and nothing wider.
    #
    # The two sides: what the GUARD parses out of the row, against that
    # grammar. The guard's regexes are IMPORTED rather than restated, because a
    # second copy of the split rule would drift from the thing being protected
    # and this check would then agree with itself instead of with the guard
    # (P-34).
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import guard as _guard
    except Exception:
        _guard = None
    # A partial tree without guard.py is not this check's to report as a
    # FINDING (P-35b) -- but it is a part not evaluated, and saying nothing
    # made it read as a charter whose row was fine (L-1.3).
    if _guard is None:
        gaps.append(("unparseable-protected-path", "guard.py cannot be imported beside "
                     "check_trace, so the Protected paths row was not read the way the "
                     "guard reads it"))
    else:
        offered = [n for n, line in enumerate(charter, 1) if PROTECTED_ISH.match(line)]
        missed = [n for n in offered if not _guard.PROTECTED_ROW.match(charter[n - 1])]
        if missed:
            gaps.append(("unparseable-protected-path", result.unparsed(
                [("CHARTER.md", n) for n in missed], len(offered),
                "Protected paths rows", "the guard's `| Protected paths | … |`",
                "neither the guard nor this check reads them")))
    if _guard is not None:
        for line in charter:
            m = _guard.PROTECTED_ROW.match(line)
            if not m:
                continue
            # AN UNFILLED CELL IS ONE PLACEHOLDER, tested whole before it is
            # split (roadmap 0.3.2, L-2.11). The template's cell is a single
            # `<…>` whose prose holds commas, and split first it read as four
            # sentences: every fresh project failed this check on its first
            # commit, and the only control that scaffolded one never ran it
            # (0.3.1 §3.2). The guard is unchanged: it drops each piece holding
            # `<` or `>` and reads the rest as paths that match nothing, which
            # protects nothing, as an unfilled cell should.
            if PLACEHOLDER.match(m.group(1)):
                break
            for raw in re.split(r"[,;]", m.group(1)):
                raw = raw.strip().strip("`").strip()
                if (not raw or _guard.PLACEHOLDER.search(raw)
                        or raw.lower() in ("none", "n/a")):
                    continue
                if re.search(r"\s", raw):
                    add("unparseable-protected-path", "CHARTER.md",
                        f"{raw[:60]!r} is a sentence, not a path. The guard "
                        f"splits this cell on commas and strips backticks, so "
                        f"this entry resolves to a path that matches nothing "
                        f"and the row protects less than it reads. One path "
                        f"per entry, comma-separated")
            break

    # --- amendment-omits-condition / amendment-names-unknown (P-48) --------
    # A PROJECT LEARNS FORWARD ONLY. C-3 §2: the final review found DM-7
    # undischargeable because a decision had changed the project's nature and
    # three later amendments never re-read it. Each amendment was correct about
    # what it changed; the charter drifted anyway.
    #
    # Two declared lists, never a reading: the charter's CURRENT done-means and
    # constraint labels against the LATEST amendment entry's enumeration.
    # Whether `holds` is TRUE is a question for a person -- this only makes the
    # claim exist, so the person has something to disagree with.
    section, dm_ids, constraint_rows = None, [], []
    amend_start = None
    # Rows each list offered that its grammar did not accept (L-1.3). They are
    # reported only if the amendment check below runs, because only then is
    # anything read out of them.
    dm_offered, dm_missed, row_offered, row_missed = 0, [], 0, []
    for n, line in enumerate(charter, 1):
        ms = SECTION.match(line)
        if ms:
            section = ms.group(1).strip().lower()
            if section.startswith("amendment"):
                amend_start = n
            continue
        if section == "done means":
            md = DM_DECL.match(line)
            if md:
                dm_ids.append(md.group(1))
            if SECTION_ROW.match(line):
                dm_offered += 1
                if not md:
                    dm_missed.append(n)
        elif section == "constraints":
            mr = TPL_ROW.match(line)
            if mr:
                label = mr.group(1).strip()
                if label and label.lower() != "constraint" and not set(label) <= set("-: "):
                    constraint_rows.append(label)
            if line.startswith("|") and SECTION_ROW.match(line):
                row_offered += 1
                if not mr:
                    row_missed.append(n)

    # The charter's header: the first line above the first section that offers
    # a version, read for stale-version-header below.
    header_at, header_n = None, None
    for n, line in enumerate(charter, 1):
        if SECTION.match(line):
            break
        if HEADER_ISH.match(line):
            mh = HEADER_VERSION.match(line)
            header_at, header_n = n, (int(mh.group(1)) if mh else None)
            break
    # The newest version the entries hold, and its line. A charter with no
    # entry is Version 1, its signed original; None is an entry unnumbered.
    newest, newest_at = 1, None

    if amend_start is not None:
        # THE LATEST ENTRY, AND ONLY IT (roadmap 0.3.2, L-2.9). The slice ran
        # to the end of the file, so an entry whose list the parse could not
        # open was scored on the NEXT entry's list -- an older one, because
        # entries are written newest first -- and reported as the latest's: a
        # true statement about Version 4 presented as a finding about Version
        # 5 (F-36, pricelog RECORD.md:563). And with two or more entries the
        # older lists supplied whatever the latest omitted, so the check could
        # not fire at all (F-68, RECORD.md:922). An entry runs to the next
        # entry heading, and the section to the next section.
        end = next((k for k in range(amend_start, len(charter))
                    if SECTION.match(charter[k])), len(charter))
        tail = charter[amend_start:end]
        entries = [i for i, l in enumerate(tail) if AMENDMENT_ENTRY.match(l)]
        if entries:
            versions = {}
            for i in entries:
                mv = AMENDMENT_VERSION.match(
                    AMENDMENT_ENTRY.match(tail[i]).group(1))
                if mv:
                    versions[i] = int(mv.group(1))
            numbered = len(versions) == len(entries)
            pick = max(versions, key=versions.get) if numbered else entries[0]
            later = [i for i in entries if i > pick]
            last = tail[pick:later[0] if later else len(tail)]
            title = AMENDMENT_ENTRY.match(last[0]).group(1)
            where = f"CHARTER.md:{amend_start + pick + 1}"
            label = f"Version {versions[pick]}" if pick in versions else "the latest amendment"
            newest, newest_at = ((versions[pick], amend_start + pick + 1) if numbered
                                 else (None, None))
            wanted = dm_ids + constraint_rows
            named = {}
            # What each `Re-affirmed.` list OFFERS, for L-1.3: every indented
            # item from that line to the next line that is not indented. Each
            # item is read whole, across the lines that continue it, so a
            # verdict that wraps is read entire, and an item that does not
            # parse no longer stops the parse: the items after it are read.
            opens = [k for k, line in enumerate(last) if REAFFIRM_OPEN.match(line)]
            extent, consumed = [], set()
            for o in opens:
                for k in range(o + 1, len(last)):
                    line = last[k]
                    if line.strip() and not line[:1].isspace():
                        break
                    if not LIST_ITEMISH.match(line):
                        continue
                    extent.append(k)
                    mi = REAFFIRM_ITEM.match(result.joined(last, k, line, until=LIST_ITEMISH))
                    if mi:
                        named[mi.group(1).strip()] = mi.group(2).strip()
                        consumed.add(k)
            # AN ENTRY WHOSE LIST OPENS WITH ANYTHING BUT `- **Re-affirmed.**`
            # IS NOT READ (L-2.9). Its conditions sit under another opener, so
            # scoring it would report every one of them omitted -- F-36's wrong
            # subject in a new form -- and the entry is named instead.
            listed = [] if opens else [
                k for k, line in enumerate(last[1:], 1)
                if REAFFIRM_ISH.match(line)
                and REAFFIRM_ISH.match(line).group(1).strip(" *`") in wanted]
            if listed:
                opener = next((last[k].strip() for k in range(listed[0] - 1, 0, -1)
                               if last[k].strip()), "")
                gaps.append((f"{label}'s Re-affirmed. list",
                             f"{where} lists {len(listed)} of the charter's conditions "
                             + (f"under {opener[:60]!r}" if opener else "under its heading")
                             + ", not under `- **Re-affirmed.**`, so none of them was read "
                             "and amendment-omits-condition did not run on the entry. "
                             "Open the list with `- **Re-affirmed.**`"))
            else:
                first_line = amend_start + pick + 1
                for missed, offered, what, grammar in (
                        (dm_missed, dm_offered, "the charter's done-means",
                         "`- **DM-n** — <one line>`"),
                        (row_missed, row_offered, "the charter's constraint rows",
                         "`| <Constraint> | <value> |`")):
                    if missed:
                        gaps.append((what, result.unparsed(
                            [("CHARTER.md", n) for n in missed], offered, "rows", grammar,
                            "amendment-omits-condition cannot ask the amendment for them")))
                # The part names its entry, so an acceptance of one entry's
                # unread items never covers the next entry's.
                unread = [first_line + k for k in extent if k not in consumed]
                if unread:
                    gaps.append((f"{label}'s Re-affirmed. list", result.unparsed(
                        [("CHARTER.md", n) for n in unread], len(extent), "items",
                        "`  - <name> — <verdict>`",
                        "what they re-affirm was not read, and any condition they name "
                        "reads as omitted")))
                missing = [w for w in wanted if w not in named]
                if missing:
                    add("amendment-omits-condition", where,
                        f"the latest amendment ({title[:40]}) re-affirms "
                        f"{len(named)} of {len(wanted)} — omits "
                        f"{', '.join(missing[:6])}"
                        + (f" and {len(missing) - 6} more" if len(missing) > 6 else "")
                        + ". Backfill with ONE entry, dated today, citing P-48 and "
                        "enumerating the charter's current state.")
                for name, verdict in sorted(named.items()):
                    if name not in wanted:
                        add("amendment-names-unknown", where,
                            f"the latest amendment re-affirms {name!r}, which the "
                            f"charter no longer has")
                    elif not REAFFIRM_VERDICT.match(verdict):
                        add("amendment-omits-condition", where,
                            f"{name} is re-affirmed as {verdict!r} — wanted `holds`, "
                            "`amended (this entry)`, `added (this entry)` or "
                            "`struck (D-n, why)`")

    # --- stale-version-header (roadmap 0.3.2, L-2.9) -----------------------
    # The header's `Version.` is the charter's pointer to its newest entry.
    # pricelog's charter moved it in the same commit as its own entry at every
    # version from 3 to 17, and Version 18 did not: "bookkeeping no check
    # reads" (RECORD.md:1350), found by a person reading `git log -L`. Read
    # now. A charter with no entry is Version 1; one with no header line and
    # no entry has nothing to compare.
    if header_at is not None and header_n is None:
        gaps.append(("the charter's Version. header", f"CHARTER.md:{header_at} does not "
                     "read `**Version.** <n>`, so stale-version-header compared nothing"))
    elif newest is None:
        gaps.append(("the charter's Version. header", "an amendment heading carries no "
                     "`Version <n>`, so the newest entry is unknown and "
                     "stale-version-header compared nothing"))
    elif header_n is None:
        if newest_at is not None:
            gaps.append(("the charter's Version. header", "CHARTER.md has amendment entries "
                         "and no `**Version.** <n>` line above its first section, so "
                         "stale-version-header compared nothing"))
    elif header_n != newest:
        add("stale-version-header", f"CHARTER.md:{header_at}",
            f"the charter's header reads `Version. {header_n}`, "
            + (f"and its newest amendment entry is Version {newest} (CHARTER.md:{newest_at})"
               if newest_at is not None else
               "and it has no amendment entry, so its version is 1")
            + ". The header moves in the commit that adds the entry")

    req_lines = read(devteam, "REQUIREMENTS.md")
    req_blocks = blocks_of(req_lines, REQ)
    starts = block_starts(req_lines, REQ)
    must_write = {}
    for k, v in req_blocks.items():
        bad = []
        must_write[k] = path_lists(v, bad).get("Requires-write", [])
        gaps += list_gaps(k, bad, "REQUIREMENTS.md", starts[k])
    original, churn, history_gaps = first_declared(devteam) or (None, {}, [])
    gaps += history_gaps
    gaps += heading_gaps(req_lines, "REQUIREMENTS.md", REQ_ISH, REQ,
                         "requirement headings", "`### R-n — <title>`")
    for ident, n, _, fields in parse_blocks(req_lines, REQ, REQ_FIELDS + REQ_EXTRA):
        reqs[ident] = (f"REQUIREMENTS.md:{n}", fields)
        for f in REQ_FIELDS:
            if f not in fields:
                add("missing-field", f"REQUIREMENTS.md:{n}", f"{ident} has no **{f}.**")

    task_files = [p for p in every if p.startswith("tasks/")]
    scopes = {}
    for rel in task_files:
        lines = read(devteam, rel)
        starts = block_starts(lines, TASK)
        for k, v in blocks_of(lines, TASK).items():
            bad = []
            scopes[k] = path_lists(v, bad).get("Scope", [])
            gaps += list_gaps(k, bad, rel, starts[k])
        parsed_any = False
        for ident, n, extra, fields in parse_blocks(lines, TASK, TASK_FIELDS + TASK_EXTRA):
            parsed_any = True
            tasks[ident] = (f"{rel}:{n}", fields, extra[1] if len(extra) > 1 else "")
            for f in TASK_FIELDS:
                if f not in fields:
                    add("missing-field", f"{rel}:{n}", f"{ident} has no **{f}.**")
            # THE ESTIMATE AGAINST THE STEPS IT PRICES, while the task is
            # PLANNED (L-2.10). No `## Steps` is compared with nothing and is
            # clean, because the plan skill lets a supervisor write the steps.
            status = extra[1] if len(extra) > 1 else ""
            if status.split()[:1] == ["PLANNED"] and "Estimate" in fields:
                steps, unread = planned_steps(lines)
                at = f"{rel}:{fields.line['Estimate']}"
                model = ESTIMATE_MODEL.search(fields["Estimate"])
                if unread:
                    gaps.append((f"{ident}'s steps", result.unparsed(
                        [(rel, u) for u in unread], len(steps) + len(unread),
                        "items under `## Steps`", "`- [ ] **S-n** — <goal>`",
                        "estimate-step-mismatch did not count them")))
                if steps and not model:
                    gaps.append((f"{ident}'s Estimate.", f"{at} states no "
                                 "`model=<steps>x…`, so estimate-step-mismatch compared "
                                 f"its {len(steps)} step(s) with nothing"))
                elif steps and int(model.group(1)) != len(steps):
                    add("estimate-step-mismatch", at,
                        f"{ident}'s estimate prices {model.group(1)} step(s) "
                        f"(`model={model.group(1)}x…`) and its `## Steps` lists "
                        f"{len(steps)}. An estimate counts the steps as planned (P-41), "
                        "so correct the model or the steps")
        # A task file whose title will not parse yields no block at all, so the
        # task is INVISIBLE: the requirements it discharges read as uncovered
        # and the file itself is never mentioned. Same class as a research
        # digest skipped for a title typo -- a failure whose only symptom is a
        # number nobody cross-checks.
        if not parsed_any and os.path.basename(rel).startswith("T-"):
            add("unparseable-task", f"{rel}:1",
                "no `# T-n — <title> — <status>` title line, so this file is "
                "invisible to every check and its requirements read as uncovered")
        else:
            # Any OTHER title-shaped line this file offers and TASK rejects --
            # a second task in one file, or a task in a file not named for it.
            # The whole-file case is the finding above, and one fault gets one
            # report.
            gaps += heading_gaps(lines, rel, TASK_ISH, TASK, "task titles",
                                 "`# T-n — <title> — <status>`")

    # --- goal -> requirement ------------------------------------------------
    satisfied = set()
    for ident, (where, fields) in reqs.items():
        for g in fields.ids("Satisfies"):
            satisfied.add(g)
            if g not in goals:
                add("unknown-reference", where, f"{ident} satisfies {g}, which no charter goal declares")
    for g, where in sorted(goals.items()):
        if g not in satisfied:
            add("orphan-scope", where, f"{g} is promised in the charter and no requirement covers it")

    # --- requirement -> task ------------------------------------------------
    discharged = set()
    for ident, (where, fields, _) in tasks.items():
        names = fields.ids("Discharges")
        # RE-ESTABLISHING IS A MOTIVATION, NOT A DISCHARGE (roadmap 0.3.2,
        # L-2.4). T-17 and T-18 each fixed code under a requirement another task
        # had discharged, and the model allowed one discharging task per
        # requirement (pricelog RECORD.md:495), so they wrote it as prose inside
        # `Discharges.`. The requirement keeps its `discharged (T-n)`; this field
        # is why the task exists, and nothing else reads it as a link.
        renewed = fields.ids("Re-establishes")
        for r in renewed:
            if r not in reqs:
                add("unknown-reference", where, f"{ident} re-establishes {r}, which no requirement declares")
        # A probe discharges nothing BY DEFINITION -- it asks whether something
        # is possible, and its answer changes the design. The plan skill demands
        # one as task one; `unmotivated-task` made it unexpressible, so a plan
        # had to choose between an untrue Discharges field and a permanent
        # finding. A task now declares its KIND, and only an implementation
        # task owes a requirement.
        kind = (fields.get("Kind", "implementation") or "implementation").strip().lower()
        if kind not in ("implementation", "probe", "spike", "chore"):
            add("bad-kind", where,
                f"{ident} has Kind {kind!r}; expected implementation, probe, spike or chore")
            kind = "implementation"
        if kind == "implementation":
            if not names and not renewed:
                add("unmotivated-task", where,
                    f"{ident} discharges no requirement — scope creep, or a "
                    "requirement nobody wrote down. If it fixes a requirement "
                    "another task discharged, name it in **Re-establishes.**; if "
                    "it is a probe, a spike or a chore, say so with **Kind.** and "
                    "give it an **Informs.** or a **Because.**")
        elif kind in ("probe", "spike"):
            informs = fields.ids("Informs")
            if not informs:
                add("unjustified-task", where,
                    f"{ident} is a {kind} and names no **Informs.** — a probe that "
                    "de-risks nothing identifiable is work nobody can judge")
            for r in informs:
                if r.startswith("R-") and r not in reqs:
                    add("unknown-reference", where, f"{ident} informs {r}, which no requirement declares")
                if r.startswith("G-") and r not in goals:
                    add("unknown-reference", where, f"{ident} informs {r}, which no charter goal declares")
        elif kind == "chore":
            if PLACEHOLDER.match(fields.get("Because", "")):
                add("unjustified-task", where,
                    f"{ident} is a chore and gives no **Because.** — a task with "
                    "neither a requirement nor a reason is one nobody agreed to")
        for r in names:
            discharged.add(r)
            if r not in reqs:
                add("unknown-reference", where, f"{ident} discharges {r}, which no requirement declares")

    # ...and the same disagreement seen from the task. A PLANNED task has not
    # started, so a requirement it will discharge is correctly still `open`;
    # once the task is RUNNING or DONE the requirement's status has to say so,
    # or the board and the requirements disagree about what is being worked.
    # NOTHING READ THE BOARD BACK. `check_scope` reads it for declared scopes
    # and a claim is legal whatever a title says; `check_trace` read task
    # titles and never opened the Tasks table; `check_report` reads one task
    # file. So the file the run skill calls "live state, and the lock", whose
    # startup procedure says "it, not your memory, is the state", was the one
    # artifact here with no checker reading it back -- and a board saying a
    # task was CLAIMED with a live in-flight row, two hours after that task
    # closed, passed all four checks.
    #
    # Cheap precisely BECAUSE the board is redundant with the task files, which
    # is the same property that lets them disagree.
    #
    # AND IT COMPARED NOTHING FOR A PROJECT'S WHOLE LIFE (F-70): every row of
    # a real board is written as a link, and the row grammar wanted a bare id,
    # so no row parsed and the check said clean. 0.3.1 named each row it did
    # not read (L-1.3); 0.3.2 reads them (L-2.1), and names only a row that
    # is still not in the grammar.
    board = read(devteam, "BOARD.md")
    rows, missed, found = board_rows(board)
    if missed:
        gaps.append(("BOARD.md's task rows", result.unparsed(
            [("BOARD.md", n) for n in missed], len(rows) + len(missed),
            "rows of the Tasks table naming a task",
            "`| T-n | … | <state> |` with one cell per column, the task bare, "
            "linked, bold or in backticks", "board-drift compared nothing for them")))
    if board and not found:
        gaps.append(("BOARD.md's Tasks table", "no table on BOARD.md has `Task` as its "
                     "first column and a `State` column, so board-drift compared nothing"))
    # The in-flight table decides L-2.2's allowance, so it is read only when
    # some row is CLAIMED -- and then a row of it this cannot read is a part
    # not evaluated, because the allowance fails closed on it.
    flying, unread = in_flight(devteam) if any(
        s.split()[:1] == ["CLAIMED"] for _, s, _ in rows) else ({}, [])
    if unread:
        gaps.append(("BOARD.md's in-flight rows", result.unparsed(
            [("BOARD.md", n) for n in unread], len(flying) + len(unread),
            "in-flight rows", "`| T-n | … |`",
            "a CLAIMED task's in-flight row may not have been seen")))
    for tid, state, n in sorted(rows):
        if tid not in tasks:
            add("board-drift", "BOARD.md",
                f"the board lists {tid}, which has no task file")
            continue
        if not BOARD_STATE.match(state):
            add("bad-board-state", f"BOARD.md:{n}",
                f"{tid}'s state is {state!r}, which is not a board state: FORMATS "
                "allows `—`, `CLAIMED <label>`, `BLOCKED on T-n` or `Q-n` (several, "
                "comma-separated), `DONE` and `ACCEPTED (<date>, D-n)`. A reason goes "
                "in the in-flight table's Note, not after the state")
        title_phase = (tasks[tid][2].split() or [""])[0]
        key = state.split()[0] if state.split() else state
        allowed = BOARD_PHASES.get(key)
        held = key == "CLAIMED" and tid in flying
        if held:
            allowed = allowed + CLAIM_HELD
        if allowed and title_phase and title_phase not in allowed:
            add("board-drift", "BOARD.md",
                f"the board says {tid} is {state!r} and its title says "
                f"{tasks[tid][2].strip()!r} — a board state of {key} wants a "
                f"title of {' or '.join(allowed)}"
                + (f", or, while {tid} has a row in the in-flight table, "
                   f"{' or '.join(CLAIM_HELD)}" if key == "CLAIMED" and not held else ""))

    # COMPARE PHASE, NOT IDENTITY. Naming the task was the whole test, so
    # `in-progress (T-6)` passed while T-6 was DONE -- a requirement claiming to
    # be under construction by a task that had finished. The asymmetry ran the
    # wrong way: coverage was strongest at the CLAIM, where a missed update is
    # loud and fires in minutes, and vanished at the CLOSE, where it is
    # permanent -- the task is gone, nothing revisits it, and the requirement
    # sits citing a finished task until somebody reads it by hand at the final
    # review, which is a gate where the checks are supposed to have read
    # already.
    #
    # The legal states are a RELATION rather than an equality, which is
    # presumably why identity was reached for first. A requirement advanced by
    # one task and completed by another is normal and the format says so, so a
    # closed task may leave its requirement `in-progress` -- but only naming
    # some OTHER task that has not itself finished.
    #
    # AND A CLOSED TASK MAY LEAVE ITS REQUIREMENT HONESTLY UNFINISHED (roadmap
    # 0.3.2, L-2.4, the owner's answer of 2026-09-24). pricelog's managers left
    # three requirements `open` over closed tasks rather than write something
    # untrue -- named residuals a decision recorded, and a judgement only the
    # client could make (RECORD.md:712-713, :820) -- and this check refused all
    # three, because the vocabulary had no word for either. It has two now,
    # each naming the task, so a status that names none is still refused.
    for tid, (twhere, tfields, tstatus) in sorted(tasks.items()):
        phase = tstatus.split()[0] if tstatus.split() else ""
        if phase not in ("RUNNING", "DONE", "ACCEPTED"):
            continue
        for r in tfields.ids("Discharges"):
            if r not in reqs or STRUCK.match(reqs[r][1].get("Status", "")):
                continue
            rstatus = reqs[r][1].get("Status", "").strip()
            named = TASK_REF.findall(rstatus)
            if phase == "RUNNING":
                ok = tid in named and rstatus.startswith("in-progress")
                want = f"`in-progress` naming {tid}"
            else:
                unfinished = [o for o in named if o != tid
                              and not tasks.get(o, ("", {}, ""))[2].startswith(
                                  ("DONE", "ACCEPTED"))]
                ok = ((rstatus.startswith(CLOSED_STATUSES) and tid in named)
                      or (rstatus.startswith("in-progress") and unfinished))
                want = (f"`discharged ({tid})`, `partly-discharged ({tid}; D-n)` or "
                        f"`awaiting-judgement ({tid}; Q-n)`, or `in-progress` naming "
                        "another task that has not finished")
            # CLOSED_LINK below reads this message back for the gate's one
            # allowance, so the two are kept side by side.
            if not ok:
                add("one-sided-link", twhere,
                    f"{tid} is {phase} and discharges {r}, but {r}'s status is "
                    f"{rstatus!r} — wanted {want}")

    for ident, (where, fields) in sorted(reqs.items()):
        if STRUCK.match(fields.get("Status", "")):
            continue
        # UNCOVERED below reads this message back for the gate's --pre-plan,
        # so the two are kept side by side.
        if ident not in discharged:
            add("uncovered-requirement", where, f"{ident} is not discharged by any task")
        acc = fields.get("Acceptance", "")
        if "Acceptance" in fields and PLACEHOLDER.match(acc):
            add("unverified-requirement", where,
                f"{ident} has no runnable acceptance criterion — it will be declared done by opinion")

        # THE CRITERION'S LEVEL AGAINST THE TASK'S SCOPE.
        #
        # Three times in one project an acceptance criterion written in process
        # language -- "exits non-zero", "fails under the default and succeeds
        # under --encoding" -- was discharged by a task scoped to one module.
        # Each time the task worked correctly and the requirement was still not
        # discharged: it could make the BEHAVIOUR true and not the SENTENCE
        # true, because the sentence describes a process only the wiring task
        # can run. All three surfaced late, from a verifier invoking the
        # command end to end after the module task had closed.
        #
        # It is checkable only because the level is DECLARED rather than
        # inferred. No script can reliably tell a process-level sentence from a
        # module-level one, and a heuristic that guessed would misfire on
        # ordinary plans -- which is how a check gets switched off by whoever
        # it obstructs. Set containment over two declared lists needs no
        # English at all.
        #
        # It fails in the safe direction: an understated `Requires-write.` makes
        # this MISS a real mismatch and never invent one. So the residual
        # failure is a criterion whose author did not understand what it
        # must write -- and that at least leaves a declaration somebody can
        # read and dispute, rather than a silence.
        # A DECLARATION THAT CAN BE EDITED IS NOT EVIDENCE. `Requires-write.`
        # is half of the pair `unreachable-acceptance` compares, and the
        # planner who draws the other half can reach both -- so seven red
        # findings and two editable lists is a situation with an obvious exit.
        # The manager who hit exactly that reported the reason it did not take
        # it was that the failure had been NAMED in advance, which is a thin
        # thing to rely on twice. Superseding stays allowed and is the point:
        # it leaves a record naming a decision, and an edit does not.
        if original is not None and ident in original:
            before, now = set(original[ident]), set(must_write.get(ident, []))
            amended = any(FIELD.match(l) and FIELD.match(l).group(1).strip()
                          == "Requires-write amended"
                          for l in req_blocks.get(ident, []))
            if before != now and not amended:
                add("unrecorded-amendment", where,
                    f"{ident} declared {sorted(before) or 'nothing'} when it was "
                    f"first committed and now declares {sorted(now) or 'nothing'}, "
                    "with no `**Requires-write amended.**` naming the decision "
                    "(P-23). Superseding is allowed; editing the list a check "
                    "reads is not")

        # A REQUIREMENT RE-LITIGATED IS PROBABLY SHAPED WRONG.
        #
        # The rule this enforces is stated in the onboarding skill: a
        # requirement is a rule over a domain, and the enumerated cases belong
        # in the acceptance criterion. A requirement written as "X, except in
        # these cases" costs a client stop per new case, and nothing noticed.
        #
        # Measured on a real project: seven of twelve build-time client stops
        # were ONE requirement, re-litigated as each new exception surfaced --
        # a closed pipe, an interrupt, a signal-killed run, a usage error, a
        # vendored caller. It stopped the moment the requirement was rewritten
        # to state its preconditions instead of listing its exceptions. That
        # requirement's semantic amendment count was 3; the next highest was 2
        # and five requirements were at 0, so the threshold isolates it.
        #
        # NOT A DEFECT, and the message says so. A requirement legitimately
        # gains detail. Three rewrites of what it MEANS is a question about its
        # shape, and the answer may be that the cases really are irreducible --
        # which is what `Shape reviewed.` records.
        if churn.get(ident, 0) >= 3:
            add("re-litigated-requirement", where,
                f"{ident}'s Statement or Acceptance has changed "
                f"{churn[ident]} times since it was written or last reviewed. "
                "That is usually a requirement enumerating cases where it "
                "should state a rule over them — each new case costs a client "
                "stop. Restate it as a rule, or add "
                "`- **Shape reviewed.** <date> (D-n)` recording that the cases "
                "are genuinely irreducible")

        # BOTH ENDS OF THE LINK, NOT JUST ITS EXISTENCE.
        #
        # A requirement's `Status.` names the tasks working it; a task's
        # `Discharges.` names the requirements it closes. Every check here
        # verified that each end pointed at something real and none compared
        # the two. A decision that scheduled two requirements across two tasks
        # reached the decision log and neither artifact: three of thirteen
        # requirements named a task that did not list them, and it survived
        # four closed tasks and every clean run. One of them was the only
        # requirement of a signed goal, so dispatching as briefed would have
        # left that goal half built with this whole pipeline reporting clean.
        # A GATE NARROWER THAN ITS REQUIREMENT SHIPS LESS, SILENTLY.
        #
        # The verifier reads the GATE, and P-18 puts the verifier last, so the
        # asymmetry is one-directional: a gate that asks for less than its
        # requirement passes everything and delivers less, and nothing in the
        # chain has a reason to notice. A real task's gate listed four things
        # its requirement wanted and neither of the two caveats the same
        # requirement had gone to a charter amendment to establish. A worker
        # satisfying that gate exactly would have shipped a document omitting
        # the remedy a signed requirement points its reader at, reinstating an
        # alternative the project had explicitly declined, and passed.
        #
        # EXISTENTIAL over the discharging tasks, which is what makes it
        # survive partial discharge: a requirement legitimately worked across
        # three tasks only needs ONE of them to carry the obligation. The
        # per-task form was measured first and produces 14 findings to 1 real
        # on the same corpus, because a gate states what must be true and is
        # not obliged to cite anything.
        #
        # The limit, stated because it is invisible: this is only as good as
        # the requirement's decision citations. A project whose requirements
        # cite no decisions gets no coverage here and no warning that it does
        # not.
        owners = [tid for tid, (_, tf, _) in tasks.items() if ident in tf.ids("Discharges")]
        if owners:
            for d in sorted(set(DECISION_REF.findall(
                    fields.get("Statement", "") + " " + fields.get("Acceptance", "")))):
                if not any(d in tasks[o][1].get("Gate", "") for o in owners):
                    add("gate-omits-decision", where,
                        f"{ident} rests on {d} and no gate among "
                        f"{', '.join(sorted(owners))} names it. Either a gate "
                        f"should require what {d} decided, or {ident} should not "
                        "be citing it")

        for tid in TASK_REF.findall(fields.get("Status", "")):
            if tid not in tasks:
                continue
            if ident not in tasks[tid][1].ids("Discharges"):
                add("one-sided-link", where,
                    f"{ident} is {fields.get('Status', '').strip()}, but {tid} "
                    f"does not list {ident} in its `Discharges.`")

        want = must_write.get(ident, [])
        if want and owners and not any(
                all(contains(scopes.get(tid, []), path) for path in want)
                for tid in owners):
            missing = {path for tid in owners for path in want
                       if not contains(scopes.get(tid, []), path)}
            add("unreachable-acceptance", where,
                f"{ident} needs a write to {', '.join(sorted(missing))}, which no task "
                f"discharging it ({', '.join(sorted(owners))}) has in scope — "
                "the criterion cannot be run to green by any single one of them")

    # --- the task graph -----------------------------------------------------
    graph = {}
    for ident, (where, fields, _) in tasks.items():
        # An edge is a bare task identifier and nothing else (roadmap 0.3.2,
        # L-2.3): a task a sentence in this field mentions is not a dependency.
        deps = fields.ids("Depends on")
        graph[ident] = deps
        for d in deps:
            if d not in tasks:
                add("unknown-reference", where, f"{ident} depends on {d}, which no task declares")

    WHITE, GREY, BLACK = 0, 1, 2
    colour = {t: WHITE for t in graph}

    def walk(node, trail):
        colour[node] = GREY
        for dep in graph.get(node, []):
            if dep not in colour:
                continue
            if colour[dep] == GREY:
                cycle = trail[trail.index(dep):] + [dep] if dep in trail else [dep, node, dep]
                add("dependency-cycle", tasks[node][0], " → ".join(cycle))
            elif colour[dep] == WHITE:
                walk(dep, trail + [dep])
        colour[node] = BLACK

    for t in sorted(graph):
        if colour[t] == WHITE:
            walk(t, [t])

    # --- open-finding-at-close (CONSOLIDATION 7, 0.2.6) ---------------------
    # An audit finding still `Disposition. open` when the task it audited has
    # closed. THE MEASURED GAP: two audits produced fifteen findings, three
    # became client questions, one entered a task brief, and eleven were never
    # dispositioned -- filed in a report nothing pointed at again. P-31 puts the
    # audit BEFORE the close, so a task that closed over an open finding closed
    # over evidence it had itself commissioned.
    #
    # Two declared lists: the audit file's `Disposition.` values against the
    # task's own title status. The task id comes from the FILENAME, which the
    # audit skill already fixes as `T-n-<dimension>-<date>.md`, so nothing is
    # read out of prose.
    audits_dir = os.path.join(devteam, "audits")
    closed = lambda t: (t in tasks and (tasks[t][2].split() or [""])[0].strip().upper()
                        in ("DONE", "ACCEPTED"))
    if os.path.isdir(audits_dir):
        for name in sorted(os.path.basename(p) for p in every if p.startswith("audits/")):
            m = AUDIT_FILE.match(name)
            if not m:
                # A file NAMING a closed task in another form, and holding
                # findings, cannot be tied to that task, so whether they are
                # open is never asked (L-1.3). Nothing is inferred from the
                # name; the file is named as not evaluated. pricelog's step
                # audit, `pricelog-T-18-S-4-2026-09-17.md`, is one.
                named = re.search(r"\bT-(\d+)\b", name)
                if name.endswith(".md") and named and closed(f"T-{named.group(1)}"):
                    with open(os.path.join(audits_dir, name), encoding="utf-8",
                              errors="replace") as fh:
                        headings = sum(1 for line in fh if AUDIT_HEADING_ISH.match(line))
                    if headings:
                        gaps.append((f"audits/{name}", f"names T-{named.group(1)} and holds "
                                     f"{headings} finding heading(s), but is not named "
                                     "`T-n-<dimension>-<date>.md`, so open-finding-at-close "
                                     "cannot tie them to the task"))
                continue
            tid = f"T-{m.group(1)}"
            if not closed(tid):
                continue
            phase = (tasks[tid][2].split() or [""])[0].strip().upper()
            rel_a = os.path.join("audits", name)
            with open(os.path.join(audits_dir, name), encoding="utf-8", errors="replace") as fh:
                audit = fh.read().split("\n")
            offered = [n for n, line in enumerate(audit, 1) if AUDIT_HEADING_ISH.match(line)]
            missed = [n for n in offered if not AUDIT_HEADING.match(audit[n - 1])]
            if missed:
                gaps.append((f"{rel_a}'s findings", result.unparsed(
                    [(rel_a, n) for n in missed], len(offered), "finding headings",
                    "`## <COR|SEC|HYG|REV|CNV>-n — <title>`",
                    "open-finding-at-close cannot see whether they are open")))
            current, n_at, disposed = None, 0, False
            for n, line in enumerate(audit, 1):
                h = AUDIT_HEADING.match(line)
                if h:
                    if current and not disposed:
                        add("open-finding-at-close", f"{rel_a}:{n_at}",
                            f"{current} is still open and {tid} is {phase} — "
                            f"P-31 puts the audit before the close, so this "
                            f"task closed over a finding it commissioned")
                    current, n_at, disposed = f"{h.group(1)}-{h.group(2)}", n, False
                    continue
                # Read whole, as check_refs reads the same field (roadmap
                # 0.3.2, L-2.3): a line break inside it changes nothing.
                d = AUDIT_DISPOSITION.match(line)
                if d and current and not ledger.is_open(result.joined(audit, n - 1, d.group(1))):
                    disposed = True
            if current and not disposed:
                add("open-finding-at-close", f"{rel_a}:{n_at}",
                    f"{current} is still open and {tid} is {phase} — P-31 puts "
                    f"the audit before the close, so this task closed over a "
                    f"finding it commissioned")

    # Last, because every class above has now read whatever it reads: an
    # identifier field is not evaluated when a class read it AND it holds a
    # piece that is not an identifier (roadmap 0.3.2, L-2.3), and the reads
    # are only known once they have happened.
    number = lambda kv: int(kv[0].split("-")[1])
    for ident, (where, fields) in sorted(reqs.items(), key=number):
        gaps += field_gaps(ident, where, fields)
    for ident, (where, fields, _) in sorted(tasks.items(), key=number):
        gaps += field_gaps(ident, where, fields)

    return findings, gaps, len(goals), len(reqs), len(tasks)


# F-19'S WINDOW, AS THIS CHECK REPORTS IT (roadmap 0.3.1, L-1.5): a task whose
# title its supervisor has set to DONE, while the requirement it discharges
# still reads `in-progress`, because the manager may not move a requirement
# before the independent verifier returns (P-18). That is the task-side message
# above, for a DONE task, and only that. The requirement-side message -- a
# requirement naming a task that does not list it -- is a plan that disagrees
# with itself, never a window, and the run's gate refused one correctly
# (pricelog RECORD.md:430). The gate reads the task and the requirement back
# from this pattern and fails closed on anything it does not match.
CLOSED_LINK = re.compile(r"^(T-\d+) is DONE and discharges (R-\d+), but \2's status is ")

# THE GATE'S --pre-plan (roadmap 0.3.1, L-1.5, as the owner settled it on
# 2026-09-24): a requirement committed before its task is planned -- at
# onboarding, and at every later cycle's charter gate -- is uncovered by
# construction, so the gate holds back this finding for a requirement the
# commit adds, and for no other. The gate reads the requirement back from this.
UNCOVERED = re.compile(r"^(R-\d+) is not discharged by any task$")

AUDIT_FILE = re.compile(r"^T-(\d+)-[a-z]+-\d{4}-\d{2}-\d{2}\.md$")
AUDIT_HEADING = re.compile(r"^#{2,3}\s+(COR|SEC|HYG|REV|CNV)-(\d+)\s*[\u2014\u2013-]")
AUDIT_DISPOSITION = re.compile(r"^\s*-\s+\*\*Disposition\.\*\*\s*(.+?)\s*$")
# Whether it is open is ledger.is_open, the value's first word read whole, as
# check_refs reads the same field (roadmap 0.3.2, L-2.3). It was a copy of
# check_refs' regex, and has one home now (roadmap 0.3.3, L-3.2).


def resolve(target):
    target = os.path.realpath(target)
    if os.path.basename(target) != "devteam" and os.path.isdir(os.path.join(target, "devteam")):
        target = os.path.join(target, "devteam")
    return target


def is_project(devteam):
    """Is this actually a devteam project, or just a directory?

    check_scope refuses a target that is not a devteam project. THIS CHECK HAD
    NO SUCH GATE, and answered anyway. Run against the repository that builds
    the plugin -- which has no devteam/ directory -- it read a CHARTER.md that
    does not exist as a charter with every row missing and reported SIXTEEN
    template-drift findings:

        $ python3 scripts/check_trace.py .
        .: 16 finding(s)  [0 goals, 0 requirements, 0 tasks]
          template-drift  CHARTER.md  the charter has no `Budget ceiling` row …

    Every one false, and each reads exactly like a true one. The tell -- `[0
    goals, 0 requirements, 0 tasks]` -- is on a different line from the
    findings, so a reader grepping the finding lines, which is what a verifier
    does, sees sixteen charter defects on a project with no charter. That is
    P-35b at the level of the check suite: an instrument returning an answer
    for a question it was never wired to ask.

    The right answer is the one FORMATS.md §"What each check reads" already
    defines and this script already implements for two other conditions -- exit
    2, COULD NOT RUN. 0.2.6 used exactly this reasoning to withdraw two
    check_refs classes: a clean project and an unreadable one must not give the
    verifier the same exit code, because the exit code is the only thing it
    reads (P-19).

    The discriminator is `resolve()`'s own: it appends `devteam` when it finds
    one, so a resolved path whose basename is not `devteam` means there was
    none to find. No new notion of "is a project" is introduced -- a second one
    would be a second home (P-34).
    """
    return os.path.basename(devteam) == "devteam"


def main(argv):
    # Before planning, no task exists, so EVERY requirement is uncovered by
    # construction. Reporting that at the onboarding gate makes a clean run
    # impossible and leaves a manager choosing between ignoring the check and
    # inventing tasks. `--pre-plan` holds back exactly that one class and
    # nothing else: orphan-scope, unverified-requirement, missing-field,
    # unknown-reference and dependency-cycle all still apply, and those are
    # the ones onboarding actually needs clean.
    #
    # Held back is not the same as clean (roadmap 0.3.1, L-1.2). The class is
    # EXCLUDED by the caller's declaration, so the line names it and how many
    # findings it held back, and the exit code is the rest's.
    as_json, args = result.flag(argv[1:], "--json")
    pre_plan, args = result.flag(args, "--pre-plan")
    at_commit, args = result.flag(args, "--at-commit")
    results = []
    for t in (args or ["."]):
        devteam = resolve(t)
        if not os.path.isdir(devteam):
            return result.could_not_run("check_trace", f"not a directory: {devteam}", as_json)
        if not is_project(devteam):
            return result.could_not_run(
                "check_trace", f"not a devteam project: {devteam} holds no "
                f"devteam/ directory", as_json)
        got = check(devteam)
        if got is None:
            return result.could_not_run("check_trace", f"not a git repository: {devteam}", as_json)
        findings, gaps, ng, nr, nt = got
        res = result.Result("check_trace", os.path.relpath(devteam, os.getcwd()), width=22)
        if pre_plan:
            held = [f for f in findings if f[0] == "uncovered-requirement"]
            findings = [f for f in findings if f[0] != "uncovered-requirement"]
            res.exclude("uncovered-requirement", f"--pre-plan ({len(held)} held back)")
        for kind, where, detail in findings:
            res.finding(kind, where, detail)
        for part, reason in gaps:
            res.gap(part, reason)
        if at_commit:
            res.exclude_classes(WORKING_STATE, result.AT_COMMIT)
        # WHAT A DECISION ACCEPTED (roadmap 0.3.1, L-1.6) is reported as
        # accepted, and an acceptance nothing matches is a finding here, so
        # the count returns to zero when the finding is fixed.
        add = lambda kind, where, detail: res.finding(kind, where, detail)
        for where, detail in res.accept(result.acceptances(devteam)):
            add("stale-acceptance", where, detail)
        res.count(ng, "goals")
        res.count(nr, "requirements")
        res.count(nt, "tasks")
        res.clean_note = "traced end to end"
        results.append(res)
    return result.emit(results, as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
