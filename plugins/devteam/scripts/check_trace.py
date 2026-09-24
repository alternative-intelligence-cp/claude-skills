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
IDS = re.compile(r"\b([GRT]-\d+)\b")

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
TASK_EXTRA = ("Kind", "Informs", "Because")

STRUCK = re.compile(r"^struck\b", re.I)

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
# `  - <name> — <verdict>` under that block. The name may itself contain a
# hyphen (`DM-1`, `Lint / format command`), so the separator is a dash with
# whitespace on both sides -- the same rule every other title in this grammar
# uses, and for the same reason.
REAFFIRM_ITEM = re.compile(r"^\s+-\s+(.+?)" + SEP + r"(.+?)\s*$")
REAFFIRM_VERDICT = re.compile(r"^(holds|amended \(this entry\)|struck \(D-\d+[^)]*\))\.?\s*$", re.I)



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


def path_lists(lines, unparsed=None):
    """{field name: [entries]} for every `Scope.`/`Requires-write.` list in a block.

    `unparsed`, when given, collects (index into `lines`, field name) for each
    list item under a path list that does not parse as a path.
    """
    out, collecting = {}, None
    for i, line in enumerate(lines):
        m = LIST_FIELD.match(line)
        if m:
            collecting = m.group(1)
            out.setdefault(collecting, [])
            inline = m.group(2).strip()
            if inline and not PLACEHOLDER.search(inline):
                out[collecting] += [x.strip().strip("`") for x in inline.split(",") if x.strip()]
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
    """A block's fields, each held as its FIRST physical line -- and what that
    leaves unread (roadmap 0.3.1, L-1.3).

    `parse_blocks` keeps a field's first line only. That is a partial read
    exactly when the field continues past it and something reads the value:
    F-132 was a `Discharges.` field whose first line ended mid-sentence, cut at
    commas into pieces none of which was the requirement it named. So a value
    read out of this mapping is RECORDED, and a field both read and wrapped is
    named as not evaluated. Presence -- `in` -- is not a read, because a field's
    existence is on its first line.

    Recording reads rather than listing the fields each class uses keeps the
    two from drifting: a class added later that reads a wrapped field is
    covered without anybody remembering to add it here.
    """

    def __init__(self):
        super().__init__()
        self.line, self.wraps, self.misparsed, self.read = {}, set(), {}, set()

    def get(self, key, default=None):
        self.read.add(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.read.add(key)
        return super().__getitem__(key)


def _named_field(name):
    """A line that NAMES this field, however it is decorated: the loose shape."""
    return re.compile(r"^-\s+\**\s*" + re.escape(name) + r"\s*\**\s*[.:]", re.I)


def parse_blocks(lines, header, fields_for):
    """Yield (identifier, line-number, extra, Fields) per heading.

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
                cur[3][name] = f.group(2).strip()
                cur[3].line[name] = n
                if result.continuation(lines, n - 1):
                    cur[3].wraps.add(name)
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
             f"{len(rows)} list item(s) under the field do not parse as a bare "
             f"`path`, so no class compares against what they name "
             f"({result.anchors(rows)})")
            for field, rows in sorted(out.items())]


def field_gaps(ident, where, fields):
    """[(part, reason)] for a block's fields that were read and not whole."""
    rel = where.rsplit(":", 1)[0]
    out = [(f"{ident}'s {name}.", result.wrapped(f"{rel}:{fields.line[name]}", "check_trace"))
           for name in sorted(fields.wraps & fields.read)]
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
    # its rewrites before the cut are not in it; a revision `git show` cannot
    # produce is skipped; and churn compares each revision's FIRST line of a
    # field, so a rewrite past it is not counted.
    gaps, unread, wrapped_in = [], [], {}
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
            for name in fields.wraps & fields.read:
                wrapped_in.setdefault(ident, {}).setdefault(name, 0)
                wrapped_in[ident][name] += 1
    if unread:
        gaps.append(("REQUIREMENTS.md's history",
                     f"{len(unread)} revision(s) could not be read ({', '.join(unread)}), "
                     "so unrecorded-amendment and re-litigated-requirement skipped them"))
    for ident in sorted(wrapped_in, key=lambda r: int(r.split("-")[1])):
        names = ", ".join(f"{name}. in {k}" for name, k in sorted(wrapped_in[ident].items()))
        gaps.append((f"re-litigated-requirement for {ident}",
                     f"{ident}'s {names} committed revision(s) of REQUIREMENTS.md "
                     "continue past the first line, and the count compares first lines only"))
    return seen, churn, gaps


BOARD_ROW = re.compile(r"^\|\s*(T-\d+)\s*\|.*\|\s*([^|]+?)\s*\|\s*$")
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


def board_states(devteam):
    """{T-n: the board's State cell} from the Tasks table."""
    out = {}
    for line in read(devteam, "BOARD.md"):
        m = BOARD_ROW.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("`")
    return out

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

    if amend_start is not None:
        tail = charter[amend_start:]
        entries = [i for i, l in enumerate(tail) if AMENDMENT_ENTRY.match(l)]
        if entries:
            versions = {}
            for i in entries:
                mv = AMENDMENT_VERSION.match(
                    AMENDMENT_ENTRY.match(tail[i]).group(1))
                if mv:
                    versions[i] = int(mv.group(1))
            pick = (max(versions, key=versions.get) if len(versions) == len(entries)
                    else entries[0])
            last = tail[pick:]
            title = AMENDMENT_ENTRY.match(last[0]).group(1)
            where = f"CHARTER.md:{amend_start + pick + 1}"
            named, collecting = {}, False
            # What each `Re-affirmed.` list OFFERS, for L-1.3: every indented
            # item from that line to the next line that is not indented. The
            # parse stops at the first line it cannot read, so an item after it
            # is offered and never read, as well as one that does not parse.
            # This measures the same window the parse reads -- every list after
            # the entry's heading, which is F-36's slice and 0.3.2's to bound.
            in_list, extent, consumed = False, [], set()
            for k, line in enumerate(last[1:], 1):
                if REAFFIRM_OPEN.match(line):
                    in_list = True
                elif in_list and line.strip():
                    if not line[:1].isspace():
                        in_list = False
                    elif LIST_ITEMISH.match(line):
                        extent.append(k)
                if REAFFIRM_OPEN.match(line):
                    collecting = True
                    continue
                if collecting:
                    mi = REAFFIRM_ITEM.match(line)
                    if mi:
                        named[mi.group(1).strip()] = mi.group(2).strip()
                        consumed.add(k)
                        continue
                    if line.strip():
                        collecting = False
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
            unread = [first_line + k for k in extent if k not in consumed]
            if unread:
                gaps.append(("the latest amendment's Re-affirmed. list", result.unparsed(
                    [("CHARTER.md", n) for n in unread], len(extent), "items",
                    "`  - <name> — <verdict>`",
                    "what they re-affirm was not read, and any condition they name "
                    "reads as omitted")))
            wanted = dm_ids + constraint_rows
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
                        f"{name} is re-affirmed as {verdict!r} — wanted "
                        f"`holds`, `amended (this entry)` or `struck (D-n, why)`")

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
        for g in IDS.findall(fields.get("Satisfies", "")):
            if g.startswith("G-"):
                satisfied.add(g)
                if g not in goals:
                    add("unknown-reference", where, f"{ident} satisfies {g}, which no charter goal declares")
    for g, where in sorted(goals.items()):
        if g not in satisfied:
            add("orphan-scope", where, f"{g} is promised in the charter and no requirement covers it")

    # --- requirement -> task ------------------------------------------------
    discharged = set()
    for ident, (where, fields, _) in tasks.items():
        names = [r for r in IDS.findall(fields.get("Discharges", "")) if r.startswith("R-")]
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
            if not names:
                add("unmotivated-task", where,
                    f"{ident} discharges no requirement — scope creep, or a "
                    "requirement nobody wrote down. If it is a probe, a spike "
                    "or a chore, say so with **Kind.** and give it an "
                    "**Informs.** or a **Because.**")
        elif kind in ("probe", "spike"):
            informs = [r for r in IDS.findall(fields.get("Informs", "")) if r[0] in "RG"]
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
    # a real board is written as a link, `| [T-1](tasks/T-1.md) | … |`, and the
    # row grammar wants a bare id, so no row parsed and the check said clean.
    # Reading the link form is 0.3.2's; naming each row it did not read is
    # this (L-1.3).
    board = read(devteam, "BOARD.md")
    offered = [n for n, line in enumerate(board, 1) if BOARD_ROW_ISH.match(line)]
    missed = [n for n in offered if not BOARD_ROW.match(board[n - 1])]
    if missed:
        gaps.append(("BOARD.md's task rows", result.unparsed(
            [("BOARD.md", n) for n in missed], len(offered), "table rows naming a task",
            "`| T-n | … | <state> |`", "board-drift compared nothing for them")))
    for tid, state in sorted(board_states(devteam).items()):
        if tid not in tasks:
            add("board-drift", "BOARD.md",
                f"the board lists {tid}, which has no task file")
            continue
        title_phase = (tasks[tid][2].split() or [""])[0]
        key = state.split()[0] if state.split() else state
        allowed = BOARD_PHASES.get(key)
        if allowed and title_phase and title_phase not in allowed:
            add("board-drift", "BOARD.md",
                f"the board says {tid} is {state!r} and its title says "
                f"{tasks[tid][2].strip()!r} — a board state of {key} wants a "
                f"title of {' or '.join(allowed)}")

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
    for tid, (twhere, tfields, tstatus) in sorted(tasks.items()):
        phase = tstatus.split()[0] if tstatus.split() else ""
        if phase not in ("RUNNING", "DONE", "ACCEPTED"):
            continue
        for r in [x.strip() for x in tfields.get("Discharges", "").split(",") if x.strip()]:
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
                ok = ((rstatus.startswith("discharged") and tid in named)
                      or (rstatus.startswith("in-progress") and unfinished))
                want = (f"`discharged ({tid})`, or `in-progress` naming another "
                        "task that has not finished")
            if not ok:
                add("one-sided-link", twhere,
                    f"{tid} is {phase} and discharges {r}, but {r}'s status is "
                    f"{rstatus!r} — wanted {want}")

    for ident, (where, fields) in sorted(reqs.items()):
        if STRUCK.match(fields.get("Status", "")):
            continue
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
        owners = [tid for tid, (_, tf, _) in tasks.items()
                  if ident in [x.strip() for x in tf.get("Discharges", "").split(",")]]
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
            if ident not in [x.strip() for x in tasks[tid][1].get("Discharges", "").split(",")]:
                add("one-sided-link", where,
                    f"{ident} is {fields.get('Status', '').strip()}, but {tid} "
                    f"does not list {ident} in its `Discharges.`")

        want = must_write.get(ident, [])
        owners = [tid for tid, (_, tf, _) in tasks.items()
                  if ident in [x.strip() for x in tf.get("Discharges", "").split(",")]]
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
        deps = [d for d in IDS.findall(fields.get("Depends on", "")) if d.startswith("T-")]
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
                d = AUDIT_DISPOSITION.match(line)
                if d and current and not OPEN_DISP.match(d.group(1)):
                    disposed = True
            if current and not disposed:
                add("open-finding-at-close", f"{rel_a}:{n_at}",
                    f"{current} is still open and {tid} is {phase} — P-31 puts "
                    f"the audit before the close, so this task closed over a "
                    f"finding it commissioned")

    # Last, because every class above has now read whatever it reads: a field
    # is not evaluated when it was read AND continues past its first line, and
    # the reads are only known once they have happened.
    number = lambda kv: int(kv[0].split("-")[1])
    for ident, (where, fields) in sorted(reqs.items(), key=number):
        gaps += field_gaps(ident, where, fields)
    for ident, (where, fields, _) in sorted(tasks.items(), key=number):
        gaps += field_gaps(ident, where, fields)

    return findings, gaps, len(goals), len(reqs), len(tasks)


AUDIT_FILE = re.compile(r"^T-(\d+)-[a-z]+-\d{4}-\d{2}-\d{2}\.md$")
AUDIT_HEADING = re.compile(r"^#{2,3}\s+(COR|SEC|HYG|REV|CNV)-(\d+)\s*[\u2014\u2013-]")
AUDIT_DISPOSITION = re.compile(r"^\s*-\s+\*\*Disposition\.\*\*\s*(.+?)\s*$")
OPEN_DISP = re.compile(r"^\**open\**\.?\s*$", re.I)


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
        res.count(ng, "goals")
        res.count(nr, "requirements")
        res.count(nt, "tasks")
        res.clean_note = "traced end to end"
        results.append(res)
    return result.emit(results, as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
