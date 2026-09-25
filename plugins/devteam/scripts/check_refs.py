#!/usr/bin/env python3
"""Reference integrity for a project's `devteam/` directory.

Diffs two lists, repeatedly, because that is what finds holes: identifiers
cited against identifiers declared, links against files, status values against
their closed vocabularies. Reading any one document never reveals the gap.

The finding classes it emits, and the rule each enforces, are in
docs/CHECKS.md -- one home (P-34). This docstring deliberately does not
list them: it used to, and ten classes were emitted, controlled, and
absent from the lists here. `unruled-finding` in check_plugin.py keeps
docs/CHECKS.md and the code equal in both directions.

Reads what git would show under devteam/: tracked files, and untracked ones
no ignore rule covers, each of which is reported as `untracked-file` (roadmap
0.3.1, L-1.4). Ignored files, devteam/.run/ among them, stay invisible.
Exit 0 clean, 1 findings, 2 could not run, 3 not evaluated -- the contract
is result.py's (roadmap 0.3.1, L-1.1).

The grammar it implements is templates/FORMATS.md, which is its one home
(P-34). Its negative control is test_check_refs.py; a check that has never
failed has not been shown to work (P-35).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)
import ledger  # noqa: E402 -- the ledger's grammar (roadmap 0.3.3, L-3.1)

# --- the grammar (templates/FORMATS.md) ----------------------------------

DASH = r"[—–-]"
# A title's separator is a dash SURROUNDED BY WHITESPACE. Neither greedy nor
# non-greedy matching on a bare dash works: non-greedy splits at the hyphen in
# "well-known", and greedy splits at the one inside "DONE (2026-09-03)". A
# hyphen inside a word or a date never has spaces around it; a separator always
# does.
SEP = r"(?:\s+[\u2014\u2013]\s+|\s+-\s+)"

DECLARATIONS = (
    re.compile(r"^###\s+(R|D|Q)-(\d+)\s*" + DASH),          # REQUIREMENTS/DECISIONS/QUESTIONS
    re.compile(r"^-\s+\*\*(G|DM|F)-(\d+)\*\*\s*" + DASH),    # goals, done-means, findings
    re.compile(r"^#\s+(T|C)-(\d+)\s*" + DASH),               # a task or checkpoint title
    re.compile(r"^-\s+\[[ x~]\]\s+\*\*(S)-(\d+)\*\*"),       # a step inside a task
    # An audit finding, declared by a heading in devteam/audits/*.md. The
    # HEADING form is canonical because it is what the audits carrying
    # `Disposition.` already use and it matches the idiom R/D/Q and T/C use.
    # The audit SKILL prescribed `- **COR-6.** <one line>`, a form no audit
    # has ever written; that is corrected rather than the tree.
    re.compile(r"^#{2,3}\s+(COR|SEC|HYG|REV|CNV)-(\d+)\s*" + DASH),
)

# The audit namespace. Three-letter prefixes were chosen BECAUSE the scanner
# could not mistake them for citations -- which is the same fact as the scanner
# being unable to check them, so the namespace had no citation integrity in
# either direction. 0.2.6 reserves these five and watches them. Nothing
# three-letter beyond this set is resolved; everything else is still ignored.
AUDIT = {"COR", "SEC", "HYG", "REV", "CNV"}
# `ITM-n` is an item's one id, declared by its heading in LEDGER.md and nowhere
# else (roadmap 0.3.3, L-3.3), from ledger.HEADING. Like an audit finding it is
# not in MUST_BE_CITED: an item nobody cites is the ordinary state of one being
# decided, and its disposition is what is judged.
KNOWN = {"G", "DM", "R", "T", "S", "D", "Q", "C", "F", "ITM"} | AUDIT
TASK_FILE = re.compile(r"(^|/)tasks/[^/]+\.md$")
# `T-4.S-2` -- the only form that names which task's step it means.
QUALIFIED_STEP = re.compile(r"\bT-(\d+)(?:'s)?[.\s]\s*(?=S-)S-(\d+)\b")
# A STEP TABLE DECLARES ITS STEPS, because a rich step carries a class, a role
# and a verify command, and those are columns rather than a run-on line.
#
# The count first given for this was wrong and the correction is worth keeping.
# It was claimed that THREE tasks had independently written tables; measured,
# ONE had. The other two wrote a checklist declaration AND a `### S-n` section
# holding the prose -- which is not a third layout but the rich body hung off
# the declaration this grammar already has. Three findings had been read as
# three departures without anyone counting what each file actually contained.
#
# `### S-n` is therefore NOT a declaration, and adding it here is the obvious
# next move and the wrong one: it produces `duplicate-id` on every task using
# the normal pattern -- eleven of them in one project -- because those tasks
# correctly declare in the checklist and elaborate under the heading.
#
# So: nobody writes the checklist AND the table, and a task that does gets
# `duplicate-id`, correctly. That reasoning holds for the table and does not
# transfer to the heading, which is why the heading stays a body.
TABLE_STEP = re.compile(r"^\|\s*\*{0,2}(S)-(\d+)\*{0,2}\s*\|")
# The tail of a qualified reference, immediately before the bare half.
# `CITATION` finds BOTH `T-9` and `S-4` inside `T-9.S-4`, and the `S-4` was
# charged to the CITING file -- so the one form offered for a cross-task step
# reference fired `cited-undefined` against the task using it, unless that task
# happened to declare the same number. Every control used the form on a task
# that did, which is the single case where the defect is invisible.
QUAL_TAIL = re.compile(r"\bT-\d+(?:'s)?[.\s]\s*$")
# QUOTED CHECK OUTPUT IS NOT A CITATION, and this one reproduces itself.
# A supervisor reporting a finding wrote `cited-undefined  tasks/T-8.md:67
# S-4` inline, and the scanner read the quoted `S-4` as a citation against the
# quoting file -- so REPORTING A FINDING CREATED A FINDING, in every task file
# that ever quotes check output naming an unresolvable identifier. The
# supervisor did exactly the right thing; the check punished it for doing so.
# Fenced blocks were already skipped; an inline span was not. The shape is
# distinctive enough to match on: a lowercase hyphenated kind, then a
# `path:line`, which is what every check here prints and what prose does not.
CHECK_OUTPUT = re.compile(r"`[a-z][a-z-]{3,}\s+\S+:\d+[^`]*`")
# Prefixes that live outside devteam/ and are never declared here. `P-n` is a
# protocol rule; citing one is correct and must not be reported as undefined.
EXTERNAL = {"P"}
# Only decisions are required to be cited. A task or question that nothing
# else references is ordinary; an uncited DECISION is the valuable finding.
MUST_BE_CITED = {"D"}

CITATION = re.compile(r"\b([A-Z]{1,3})-(\d+)\b")
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# The identifier grammar governs the ARTIFACTS and nothing else. Paths are
# anchored at the devteam root, so `templates/tasks/TASK.md` -- a blank form
# full of example identifiers -- is not mistaken for `tasks/T-1.md`. Every
# other markdown file under devteam/ still gets its links and leaks checked;
# it just is not project state, and reporting its illustrations as dangling
# citations is the false positive that gets a check disabled (P-35).
ARTIFACTS = re.compile(
    r"^(CHARTER|REQUIREMENTS|DECISIONS|QUESTIONS|BOARD|RECORD|PERMISSIONS|LEDGER)\.md$"
    r"|^tasks/T-\d+\.md$"
    r"|^checkpoints/C-\d+[^/]*\.md$"
    r"|^research/(?!README\.md$)[^/]+\.md$"
    # Audit reports were outside the identifier grammar entirely, which is why
    # a COR-n could be declared and nothing ever resolved it.
    r"|^audits/(?!README\.md$)[^/]+\.md$"
)

# Each entry is scoped to the file it governs. `Status.` means different
# things in REQUIREMENTS.md and QUESTIONS.md, and a vocabulary applied to the
# wrong file is a false positive -- the failure mode that gets a check disabled
# (P-35).
VOCAB = (
    # `partly-discharged` and `awaiting-judgement` are the states a closed task
    # could not say (roadmap 0.3.2, L-2.4, the owner's answer of 2026-09-24):
    # pricelog left three requirements `open` over closed tasks rather than
    # write something untrue -- named residuals, and a judgement only the
    # client could make. Each names its tasks, and then the one decision or
    # question that holds what remains, because a parenthetical holds
    # identifiers only.
    ("requirement-status",
     re.compile(r"(^|/)REQUIREMENTS\.md$"),
     re.compile(r"^-\s+\*\*Status\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(open"
                r"|in-progress \(T-\d+(?:,\s*T-\d+)*\)"
                r"|discharged \(T-\d+(?:,\s*T-\d+)*\)"
                r"|partly-discharged \(T-\d+(?:,\s*T-\d+)*; D-\d+\)"
                r"|awaiting-judgement \(T-\d+(?:,\s*T-\d+)*; Q-\d+\)"
                r"|struck \(D-\d+\))$")),
    ("question-class",
     re.compile(r"(^|/)QUESTIONS\.md$"),
     re.compile(r"^-\s+\*\*Class\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(REVERSIBLE|IRREVERSIBLE|CHARTER)$")),
    ("question-status",
     re.compile(r"(^|/)QUESTIONS\.md$"),
     re.compile(r"^-\s+\*\*Status\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(open|answered D-\d+|proceeded-unreviewed D-\d+|withdrawn)$")),
    # ACCEPTED is here because the vocabulary could not express the outcome of
    # its own escalation path. `DONE` is glossed on the board as "closed,
    # verified, and released", and P-2 lets the client close a task that FAILED
    # verification -- so a task accepted over a verifier's FAIL is closed and
    # released and not verified, and no state said that. A manager wrote `DONE`
    # and reported the gap rather than inventing a status the check would
    # refuse, which is correct and left the one table a reader scans saying
    # something untrue. A VOCABULARY THAT CANNOT EXPRESS THE OUTCOME OF ITS OWN
    # ESCALATION PATH WILL BE LIED TO BY WHOEVER HOLDS THE PEN. It takes the
    # decision in its parenthetical -- `ACCEPTED (2026-09-05, D-41)` -- because
    # a task closed against its own evidence is only legible with the reason
    # attached.
    #
    # NEEDS-DECISION is here because the two vocabularies OVERLAP IN MEANING
    # AND NOT IN SPELLING. `BLOCKED (<why>)` means "waiting on a named task",
    # deliberately -- the board legend forbids a bare "waiting". So a task
    # stopped on a question for the client had no title state at all, while
    # the REPORT vocabulary it had just used has exactly the right word. A
    # supervisor reached for `NEEDS-DECISION` and got `bad-status` for using
    # the correct term for its actual situation. That is the same gap as the
    # board once having no state for a task stopped on a question: the fix is
    # to add the state, not to police the word.
    ("task-title",
     re.compile(r"(^|/)tasks/[^/]+\.md$"),
     re.compile(r"^#\s+T-\d+" + SEP + r".*?" + SEP + r"(.+?)\s*$"),
     re.compile(r"^(PLANNED|RUNNING \(.+\)|READY-TO-AUDIT|NEEDS-DECISION \(.+\)"
                r"|BLOCKED \(.+\)|ACCEPTED \(.+\)|DONE \(.+\))$")),
    ("checkpoint-verdict",
     re.compile(r"(^|/)checkpoints/[^/]+\.md$"),
     re.compile(r"^#\s+C-\d+" + SEP + r".*?" + SEP + r"(.+?)\s*$"),
     re.compile(r"^(ON-COURSE|DRIFTED|BLOCKED)$")),
)

LEAKS = (
    (re.compile(r"(?<![\w.~])/(?:home|Users)/[A-Za-z0-9._-]+/"), "an absolute home path"),
    # A session-scoped temp path encodes a machine layout and a session id and
    # resolves for nobody else. Four were baked into a permanent task record
    # before this existed, and `check_refs` reported the tree clean -- a check
    # passing on the exact condition it exists to detect.
    #
    # Two shapes, because the first attempt at one pattern missed both. A home
    # path survives path-encoding as `-home-<user>-...`, which no `/home/` rule
    # can see; and a UUID under a temp root is a session id wherever it sits in
    # the path, not only in the segment after the root.
    (re.compile(r"(?<![\w-])-home-[A-Za-z0-9._]+-[A-Za-z0-9._-]{4,}"),
     "a path-encoded home directory"),
    (re.compile(r"(?<![\w.~])/(?:tmp|var/folders|private/var)/\S*?"
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}"),
     "a session-scoped temporary path"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), "a GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "an API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key)\s*[=:]\s*['\"][^'\"]{6,}"), "a credential"),
)

# A line that is teaching the grammar rather than using it. Without this the
# format documentation and the templates report themselves, and a check that
# cries wolf on its own examples is one nobody runs.
TEACHING = re.compile(r"<[A-Za-z][^>]*>|`[A-Z]{1,3}-<n>`|\bPREFIX\b")



# Where each kind is declared, and in what shape. A `cited-undefined` that only
# says an identifier is undeclared makes the reader go and find the grammar; a
# record has two grammars for a finding -- the narrative `finding: F-n ...`
# entry and the `- **F-n** --` register line -- and a manager who wrote four of
# the first and none of the second shipped a red tree that cost two of another
# task's agents time establishing the findings were not theirs. Naming the line
# to add turns a diagnosis into a paste, which is a fix; remembering to write
# both is vigilance, which is not.
HOMES = {
    "G":  ("CHARTER.md",      "- **{id}** — <one line>"),
    "DM": ("CHARTER.md",      "- **{id}** — <one line>"),
    "F":  ("RECORD.md",       "- **{id}** — <one line>"),
    "R":  ("REQUIREMENTS.md", "### {id} — <one line>"),
    "D":  ("DECISIONS.md",    "### {id} — <one line>"),
    "Q":  ("QUESTIONS.md",    "### {id} — <one line>"),
    "T":  ("tasks/{id}.md",   "# {id} — <title>"),
    "C":  ("checkpoints/",    "# {id} — <title>"),
    "S":  ("its task file",   "- [ ] **{id}** <one line>"),
    "ITM": ("LEDGER.md",      "### {id} — <one line>"),
}


def how_to_declare(ident):
    """The line that would declare this identifier, or "" for an unknown kind."""
    home = HOMES.get(ident.split("-")[0])
    if home is None:
        return ""
    where, shape = home
    return f". Declare it in {where.format(id=ident)} as `{shape.format(id=ident)}`"

def listed_markdown(root: str):
    """(.md files under root as git would show them, as absolute paths; the
    untracked ones, relative) -- or None outside a repository (L-1.4)."""
    got = result.listed(root, "*.md")
    if got is None:
        return None
    every, untracked = got
    return [os.path.join(root, p) for p in every], untracked


class CouldNotRun(Exception):
    """A file this check cannot read or decode.

    SUPERSEDED IN 0.3.1 (L-1.1): such a file now ends the run as NOT EVALUATED,
    exit 3, naming the file -- not exit 2. The reasoning below still holds for
    why it is not a finding; what changed is that exit 2 means the TOOL cannot
    answer, whose remedy is the invocation, while a file it cannot decode is
    the PROJECT's state, whose remedy is in the project. The name is kept
    because it is what the exception has always meant to this file's readers.

    WITHDRAWN AS FINDINGS IN 0.2.6 (`unreadable`, `not-utf8`). Both reported
    "the check could not read a file" as an exit-1 finding, and the script
    already distinguishes that case with exit 2 -- FORMATS.md's three-way
    contract is 0 clean, 1 findings, 2 could not run. A file the checker cannot
    decode is not a defect in the PROJECT; it is the checker unable to answer,
    and reporting it as a finding made a clean project and an unreadable one
    give the same exit code to the verifier, which reads nothing else (P-19).

    The information is not lost -- it moves to the path that means what it says.
    """


# The classes that read the WORKING STATE rather than a commit's tree, which
# `--at-commit` excludes (result.AT_COMMIT; roadmap 0.3.1, L-1.5).
WORKING_STATE = ("untracked-file",)

DISPOSITION = re.compile(r"^\s*-\s+\*\*Disposition\.\*\*\s*(.+?)\s*$")
# Whether an audit file's disposition is open is ledger.is_open: the value's
# first word, read whole (roadmap 0.3.2, L-2.3). It was a regex copied here
# and into check_trace, and it has one home now (roadmap 0.3.3, L-3.2).

# --- what each file OFFERS (roadmap 0.3.1, L-1.3) --------------------------
# The grammar above says what parses. These say what was WRITTEN in each
# shape, however it is punctuated, so a row the grammar misses is counted and
# named instead of never seen.
#
# A declaration is offered only IN THE FILE WHERE ITS KIND IS DECLARED, and
# only in a declaration's position -- a heading, or the bold lead of a list
# item. A record discussing `## C-3 notes` is not a checkpoint declared wrong;
# a `### D-5: title` in DECISIONS.md is a decision declared wrong.
DECLARED_IN = {
    "G": re.compile(r"^CHARTER\.md$"), "DM": re.compile(r"^CHARTER\.md$"),
    "F": re.compile(r"^RECORD\.md$"), "R": re.compile(r"^REQUIREMENTS\.md$"),
    "D": re.compile(r"^DECISIONS\.md$"), "Q": re.compile(r"^QUESTIONS\.md$"),
    "T": re.compile(r"^tasks/"), "S": re.compile(r"^tasks/"),
    "C": re.compile(r"^checkpoints/"), "ITM": re.compile(r"^LEDGER\.md$"),
    **{p: re.compile(r"^audits/") for p in AUDIT},
}
DECLARATION_ISH = (
    re.compile(r"^#{1,6}\s*([A-Z]{1,3})-?\s*(\d+)\b(?![.'’])"),
    re.compile(r"^-\s+\*\*\s*([A-Z]{1,3})-(\d+)\b"),
    re.compile(r"^-\s+\[[ x~]\]\s+\**\s*(S)-?(\d+)\b"),
)
# An audit's findings, in any of the forms pricelog's four gate audits used:
# `## Finding 1 (…) —`, `### 1. …`, `## F-1 — HIGH —`. None is in the
# namespace `undispositioned-finding` reads, so none was ever seen (register
# A6, F-99), and the check said clean.
AUDIT_FINDING_ISH = re.compile(r"^#{2,3}\s+(?:finding\s+\d+\b|\d+\.\s|[A-Z]{1,5}-\d+\b)", re.I)


def named_field(name):
    """A list item that NAMES this field, however it is decorated."""
    return re.compile(r"^\s*-\s+\**\s*" + re.escape(name) + r"\s*\**\s*[.:]", re.I)


# Each vocabulary's loose shape, in the order of VOCAB.
VOCAB_ISH = {
    "requirement-status": named_field("Status"),
    "question-class": named_field("Class"),
    "question-status": named_field("Status"),
    "task-title": re.compile(r"^#\s*T-?\s*\d+\b(?![.'’])"),
    "checkpoint-verdict": re.compile(r"^#\s*C-?\s*\d+\b(?![.'’])"),
}
DISPOSITION_ISH = named_field("Disposition")


def scan(files, base, untracked=frozenset(), quoted=frozenset()):
    declared, cited, findings = {}, {}, []
    step_cited = {}
    # ident -> (file:line, disposition-text-or-None) for audit findings only.
    audit_findings = {}
    # What the files offered, for the parts not evaluated (L-1.3).
    offered = {"declarations": [], "audit": {}, "vocab": {}, "dispositions": {}, "ledger": []}

    for path in files:
        rel = os.path.relpath(path, base)
        # Read, and named: a file in no commit is invisible to every reader
        # of the tree but this one (F-131).
        if rel.replace(os.sep, "/") in untracked:
            findings.append(("untracked-file", rel, 1, result.UNTRACKED))
        try:
            raw = open(path, "rb").read()
        except OSError as exc:
            raise CouldNotRun(f"{rel}: cannot read: {exc}")

        # A document that CONTAINS a control byte rather than naming it is
        # treated as binary by git, which then produces no diff for it -- and
        # the whole audit discipline is diffing a document against the thing it
        # describes. Decoding succeeds, so nothing else notices; only git's own
        # stat line does, and nobody reads that. A digest about encodings or
        # protocols is more likely to do this than an ordinary document,
        # because the natural way to write about a byte is to write the byte.
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CouldNotRun(
                f"{rel}: not UTF-8 — byte {exc.object[exc.start]:#04x} "
                f"at offset {exc.start}")
        for n_, line in enumerate(text.split("\n"), 1):
            # `\r` is tolerated ONLY as a line ending (a CRLF file splits on
            # \n and leaves the CR last). A BARE CR mid-line is the exact
            # hazard P-47 names -- content present in the file and absent from
            # the reading of it, because a CR moves the cursor to column zero
            # and what follows overwrites what came before ON A TERMINAL while
            # a diff shows both. 0.2.6 shipped P-47 saying "outside tab and
            # newline" against code that permitted CR anywhere; the rule and
            # the code disagreed, in the subcycle whose purpose was making them
            # agree. Found by the next session reading the rule at handoff.
            body = line[:-1] if line.endswith("\r") else line
            bad = {c for c in body if ord(c) < 0x20 and c != "\t"}
            if bad:
                names = ", ".join(f"U+{ord(c):04X}" for c in sorted(bad))
                findings.append(("control-character", rel, n_,
                                 f"{names} embedded in the text — name the byte, "
                                 "do not write it; git treats the file as binary "
                                 "and stops diffing it"))
        lines = text.split("\n")

        is_artifact = bool(ARTIFACTS.match(rel.replace(os.sep, "/")))
        in_fence = False
        current_audit = None
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue

            for pat, why in LEAKS:
                m = pat.search(line)
                if m:
                    findings.append(("leak", rel, n, f"{why}: {m.group(0)[:40]}"))

            if in_fence:
                continue

            for target in LINK.findall(line):
                target = target.split("#", 1)[0].strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), target))):
                    findings.append(("broken-link", rel, n, target))

            if is_artifact and current_audit:
                md = DISPOSITION.match(line)
                # Read whole, across its continuation lines (roadmap 0.3.2,
                # L-2.3), as check_trace reads the same field.
                if md and audit_findings.get(current_audit, (None, None))[1] is None:
                    audit_findings[current_audit] = (
                        audit_findings[current_audit][0],
                        result.joined(lines, n - 1, md.group(1)))
                # A disposition this check reads, written so it cannot be read:
                # the field named, and not parsed as one.
                if DISPOSITION_ISH.match(line) and not md:
                    offered["dispositions"].setdefault(rel, []).append(n)

            if not is_artifact:
                continue

            # --- what this line OFFERS (L-1.3) -------------------------------
            relp = rel.replace(os.sep, "/")
            for pat in DECLARATION_ISH:
                mo = pat.match(line)
                if mo:
                    if mo.group(1) in DECLARED_IN and DECLARED_IN[mo.group(1)].search(relp):
                        offered["declarations"].append((mo.group(1), mo.group(2), rel, n))
                    break
            if relp.startswith("audits/") and AUDIT_FINDING_ISH.match(line):
                offered["audit"].setdefault(rel, []).append(
                    (n, bool(DECLARATIONS[4].match(line))))
            for name, scope, field, _valid in VOCAB:
                if scope.search(rel) and VOCAB_ISH[name].match(line):
                    state = "unparsed" if not field.match(line) else None
                    offered["vocab"].setdefault((rel, name), []).append((n, state))

            # Status vocabularies are checked BEFORE declarations are handled,
            # because a task's title line is both -- it declares T-n AND
            # carries the status. Checking after the declaration branch's
            # `continue` meant task and checkpoint statuses were never checked
            # at all, which the control caught.
            #
            # A `Status.` or `Class.` field is judged WHOLE, across its
            # continuation lines (roadmap 0.3.2, L-2.3). A title is a heading,
            # and a heading does not continue.
            for name, scope, field, valid in VOCAB:
                if not scope.search(rel):
                    continue
                m = field.match(line)
                if not m:
                    continue
                value = (result.joined(lines, n - 1, m.group(1))
                         if name.endswith(("status", "class")) else m.group(1))
                if not TEACHING.search(value) and not valid.match(value):
                    findings.append(("bad-status", rel, n,
                                     f"{name}: {value!r} is not in the vocabulary"))

            # Recorded WITHOUT `continue`, unlike every other declaration,
            # because a step row's remaining cells carry real citations -- the
            # requirements it discharges, the decision its verify proves. The
            # step's own `S-n` then resolves against the declaration this line
            # just made, which is harmless: only decisions must be cited.
            tab = TABLE_STEP.match(line)
            if tab:
                key = f"{rel}:{tab.group(1)}-{tab.group(2)}"
                if key in declared:
                    findings.append(("duplicate-id", rel, n,
                                     f"S-{tab.group(2)} already declared at {declared[key]}"))
                else:
                    declared[key] = f"{rel}:{n}"

            # A declaration line declares; it does not also cite itself.
            decl = None
            for pat in DECLARATIONS:
                m = pat.match(line)
                if m:
                    decl = f"{m.group(1)}-{m.group(2)}"
                    break
            # An item's id is declared in the ledger and nowhere else, so
            # `### ITM-3 —` in a task file declares nothing and reads as the
            # citation it is (roadmap 0.3.3, L-3.3).
            if decl is None and relp == ledger.PATH:
                m = ledger.HEADING.match(line)
                if m:
                    decl = f"{m.group(1)}-{m.group(2)}"

            if decl:
                # An audit finding opens a block: the `Disposition.` line that
                # follows belongs to it, until the next finding heading.
                if decl.split("-")[0] in AUDIT:
                    current_audit = decl
                    audit_findings.setdefault(decl, (f"{rel}:{n}", None))
                # Steps are numbered per task, so they are keyed by their file.
                key = f"{rel}:{decl}" if decl.startswith("S-") else decl
                if key in declared:
                    findings.append(("duplicate-id", rel, n,
                                     f"{decl} already declared at {declared[key]}"))
                else:
                    declared[key] = f"{rel}:{n}"
                # A STEP LINE IS NOT ONLY A DECLARATION. The checklist form
                # carries the step's class, role and verify command on the same
                # line -- 900 characters of it in one real task -- so `continue`
                # here made every identifier after `**S-1**` invisible. The two
                # step layouts disagreed about this, and the greedier one
                # scanned less: the table branch below deliberately does not
                # `continue`, for exactly this reason, and the checklist branch
                # fell into the shared path that does. A `D-n` cited only
                # inside a step's verify command would have vanished, and the
                # check would then have reported that decision as uncited.
                if not decl.startswith("S-"):
                    continue

            # A STEP IS NUMBERED PER TASK, so a citation of one resolves
            # against a single file rather than the whole project. Flattening
            # the namespace made every `S-n` resolve against any task that
            # happened to declare that number: a task whose steps were written
            # in a form the grammar does not recognise declared NONE of its
            # own, and its S-1..S-5 passed anyway on other tasks' declarations.
            # Only S-6 -- the first number no task had ever used -- reported.
            # The check was measuring whether a number had ever been used
            # anywhere, which is not what it is for.
            owner = rel if TASK_FILE.search(rel) else None
            # AN ACCEPTANCE IS QUOTED CHECK OUTPUT TOO (roadmap 0.3.1, L-1.6),
            # and it reproduces itself the same way: accepting a finding that
            # names an undeclared T-99 would cite T-99 from DECISIONS.md, which
            # sorts first, so the finding's anchor moved there and the
            # acceptance naming the old anchor went stale. Its lines cite
            # nothing. What watches them instead: every one is an acceptance
            # that must match a finding, or `stale-acceptance`; or one the
            # grammar cannot read, `unparseable-acceptance` below; or one its
            # decision's supersession withdrew.
            if relp == "DECISIONS.md" and n in quoted:
                continue
            # Blanked before any identifier is read out of the line, so a
            # quoted finding cannot cite anything.
            line = CHECK_OUTPUT.sub("`quoted check output`", line)

            for m in QUALIFIED_STEP.finditer(line):
                step_cited.setdefault(
                    (f"tasks/T-{m.group(1)}.md", f"S-{m.group(2)}"), []
                ).append(f"{rel}:{n}")
            for m in CITATION.finditer(line):
                pre, num = m.group(1), m.group(2)
                if pre in EXTERNAL or pre not in KNOWN:
                    continue
                if pre == "S":
                    # The bare half of `T-n.S-m`, already recorded against the
                    # task it names. Charging it to this file as well made the
                    # qualified form self-defeating. The `T-n` half is a real
                    # citation of that task and is deliberately left alone.
                    if QUAL_TAIL.search(line[:m.start()]):
                        continue
                    # Bare `S-n` outside a task file names no task and cannot
                    # be resolved -- `T-4.S-2` is the form that can. Skipping
                    # it beats guessing: the record legitimately discusses
                    # steps in prose, and a check that fires on prose is one
                    # somebody turns off.
                    if owner:
                        step_cited.setdefault((owner, f"S-{num}"), []).append(f"{rel}:{n}")
                    continue
                cited.setdefault(f"{pre}-{num}", []).append(f"{rel}:{n}")

        # THE LEDGER'S DISPOSITIONS, read through the ledger's own reader
        # (roadmap 0.3.3, L-3.2; P-34). An entry is decided, or it names the
        # date it is due by: an entry with no `Disposition.`, or one that reads
        # `open` and names no `until`, is undispositioned. pricelog's T-18
        # wrote three deferrals as "carried to the checkpoint ... to be given
        # an owner there", which the first-word test read as decided; in the
        # ledger that wording is outside the vocabulary, and is `bad-status`,
        # as every other closed field's value outside its set is.
        if is_artifact and rel.replace(os.sep, "/") == ledger.PATH:
            listed, unread = ledger.entries(lines)
            offered["ledger"] += [(n, what) for n, field, what in unread
                                  if field == "Disposition"]
            for e in listed:
                got = e.fields.get("Disposition")
                if got is None:
                    findings.append(("undispositioned-finding", rel, e.line,
                                     f"{e.ident} carries no **Disposition.** line — an item "
                                     f"is decided, or names the date it is due by: "
                                     f"{ledger.GRAMMAR}"))
                elif e.parsed() is None and not TEACHING.search(got[1]):
                    if ledger.is_open(got[1]):
                        findings.append(("undispositioned-finding", rel, e.line,
                                         f"{e.ident} reads {got[1]!r}: open, with no date the "
                                         f"vocabulary reads — an open item is `open (until "
                                         f"T-n)` or `open (until C-n)`, the task or the "
                                         f"checkpoint by which it is decided"))
                    else:
                        findings.append(("bad-status", rel, got[0],
                                         f"ledger-disposition: {got[1]!r} is not in the "
                                         f"vocabulary — {ledger.GRAMMAR}"))


    for (owner, ident), sites in sorted(step_cited.items()):
        if f"{owner}:{ident}" not in declared:
            # EVERY site, not the first. `setdefault` reported one line per
            # (file, identifier), so three occurrences in one file surfaced one
            # at a time -- fix, re-run, discover another, three times -- and
            # each output looked like progress while saying nothing about how
            # much remained. A count of problems is not a count of edits, and
            # "one finding left" carries no information; only "clean" does.
            first = sites[0]
            f, n = first.rsplit(":", 1)
            more = (f" (also {', '.join(s.rsplit(':', 1)[1] for s in sites[1:])})"
                    if len(sites) > 1 else "")
            findings.append(("cited-undefined", f, int(n),
                             f"{ident} is cited but {owner} declares no such step "
                             f"— steps are numbered per task, so a declaration in "
                             f"another task file does not resolve this one{more}"))

    bare = {k for k in declared if not k.startswith("tasks/")}
    for ident, where in sorted(cited.items()):
        if ident not in bare:
            findings.append(("cited-undefined", where[0].split(":")[0],
                             int(where[0].split(":")[-1]),
                             f"{ident} is cited but never declared{how_to_declare(ident)}"))
    for key, where in sorted(declared.items()):
        ident = key.split(":", 1)[1] if ":" in key else key
        if ident.split("-")[0] in MUST_BE_CITED and ident not in cited:
            f, n = where.rsplit(":", 1)
            findings.append(("defined-uncited", f, int(n),
                             f"{ident} is declared but nothing cites it"))

    # `defined-uncited` IS WRONG FOR AN AUDIT FINDING, which is why audit
    # prefixes are not in MUST_BE_CITED. A finding nobody cites is the normal
    # state of one still under `Disposition. open` -- it has been filed and not
    # yet routed, which is a stage, not a defect.
    #
    # The real gap is the other one, and it was measured: two audits produced
    # fifteen findings, three became client questions, one entered a task
    # brief, and ELEVEN were never dispositioned. A "declared here, cited
    # nowhere" rule reports ZERO on that project, because all eleven were
    # mentioned -- the manager had logged them in the record. MENTION IS NOT
    # DISPOSITION, and the difference is invisible in a citation graph.
    #
    # THE RULE IS DISPOSITION ALONE, AND THE CITATION HALF IS DELIBERATELY NOT
    # AN ESCAPE. 0.2.6 planned it as "cited OR dispositioned" and measured both
    # over the fixture corpus:
    #
    #     cited OR non-open Disposition  ->  0 findings
    #     non-open Disposition alone     ->  5 findings, every one real
    #
    # The corpus has sixteen findings with no `Disposition.` line at all, and
    # the planned rule reported NONE of them -- because they are cited, in
    # RECORD.md, QUESTIONS.md and CHARTER.md. That is the same defect
    # CONSOLIDATION item 7 measured and warned about in the same paragraph:
    # all eleven undispositioned findings on that project WERE mentioned, and
    # a citation-based rule scored zero. Letting a citation excuse a missing
    # disposition rebuilds the hole the field exists to close.
    for ident, (where, disp) in sorted(audit_findings.items()):
        if disp is not None and not ledger.is_open(disp):
            continue
        f, n = where.rsplit(":", 1)
        why = ("carries no **Disposition.** line at all" if disp is None
               else "is still **Disposition.** open")
        findings.append(("undispositioned-finding", f, int(n),
                         f"{ident} {why} and nothing cites it — filed is not "
                         f"routed; disposition is `routed T-n`, `raised Q-n` "
                         f"or `declined (D-n)`"))
    return findings, gaps_from(offered, declared), (len(files), len(declared), len(cited))


def gaps_from(offered, declared):
    """[(part, reason)]: what the files offered that the grammar did not read.

    A line in a declaration's position that does not parse is a LOSS only if
    what it names is declared nowhere. pricelog's record writes each finding
    twice -- the `- **F-70** —` register line, and a bold narrative entry
    `- **F-70 — …**` -- and the second is not a declaration written wrong,
    because the first declared it.
    """
    gaps = []
    decl = offered["declarations"]
    missed = [(rel, n) for kind, num, rel, n in decl
              if (f"{rel}:S-{num}" if kind == "S" else f"{kind}-{num}") not in declared]
    if missed:
        gaps.append(("declarations", result.unparsed(
            missed, len(decl), "lines in a declaration's position",
            "a declaration (templates/FORMATS.md)",
            "what they name is declared nowhere, and cited-undefined and "
            "defined-uncited ran without it")))
    for rel, rows in sorted(offered["audit"].items()):
        missed = [(rel, n) for n, ok in rows if not ok]
        if missed:
            gaps.append((f"{rel}'s findings", result.unparsed(
                missed, len(rows), "finding headings",
                "`## <COR|SEC|HYG|REV|CNV>-n — <title>`",
                "undispositioned-finding cannot see them")))
    for (rel, name), rows in sorted(offered["vocab"].items()):
        bad = [(rel, n) for n, state in rows if state == "unparsed"]
        if bad:
            gaps.append((f"{rel}'s {name}", result.unparsed(
                bad, len(rows), "fields", f"the {name} field's grammar")
                + ", so bad-status did not judge them"))
    for rel, rows in sorted(offered["dispositions"].items()):
        gaps.append((f"{rel}'s dispositions", f"{len(rows)} `Disposition.` field(s) do not "
                     "parse as `- **Disposition.** <value>`, so undispositioned-finding "
                     f"read a finding's disposition as absent "
                     f"({result.anchors([(rel, n) for n in rows])})"))
    # The ledger's own reader says why each line was not read: a field named
    # and not written as one reads as absent, and a second one in an entry
    # leaves the first standing.
    rows = offered["ledger"]
    if rows:
        gaps.append((f"{ledger.PATH}'s dispositions", f"{len(rows)} `Disposition.` line(s) "
                     "the ledger's grammar does not read — "
                     + "; ".join(f"line {n}: {what}" for n, what in rows)
                     + " — so undispositioned-finding judged each of those entries by the "
                     "line it did read, or as having none "
                     f"({result.anchors([(ledger.PATH, n) for n, _ in rows])})"))
    return gaps


def check(target: str, as_json=False, at_commit=False):
    """A Result for one target, or an int exit code when it could not run."""
    target = os.path.realpath(target)
    if os.path.basename(target) != "devteam" and os.path.isdir(os.path.join(target, "devteam")):
        target = os.path.join(target, "devteam")
    if not os.path.isdir(target):
        return result.could_not_run("check_refs", f"not a directory: {target}", as_json)
    got = listed_markdown(target)
    if got is None:
        return result.could_not_run("check_refs", f"not a git repository: {target}", as_json)
    files, untracked = got
    res = result.Result("check_refs", os.path.relpath(target, os.getcwd()), width=16)
    accepted = result.acceptances(target)
    try:
        findings, gaps, (nfiles, ndeclared, ncited) = scan(files, target, untracked,
                                                           accepted.quoted)
    except CouldNotRun as exc:
        # One unreadable file makes every cross-file class untrustworthy -- a
        # declaration inside it would read as `cited-undefined` everywhere else
        # -- so the whole run is not evaluated, naming the file, rather than a
        # partial run whose findings are the gap's artifacts.
        res.gap("every class", str(exc))
        if at_commit:
            res.exclude_classes(WORKING_STATE, result.AT_COMMIT)
        res.count(len(files), "files")
        return res
    for kind, path, line, detail in findings:
        res.finding(kind, f"{path}:{line}", detail)
    for part, reason in gaps:
        res.gap(part, reason)
    if at_commit:
        res.exclude_classes(WORKING_STATE, result.AT_COMMIT)
    # WHAT A DECISION ACCEPTED (roadmap 0.3.1, L-1.6). This check owns
    # DECISIONS.md's grammar, so it alone reports an acceptance it cannot
    # read -- once, rather than once per check -- and that acceptance
    # accepts nothing, in this check or any other.
    add = lambda kind, where, detail: res.finding(kind, where, detail)
    for where, detail in res.accept(accepted):
        add("stale-acceptance", where, detail)
    for where, detail in accepted.unread:
        add("unparseable-acceptance", where, detail)
    res.count(nfiles, "files")
    res.count(ndeclared, "declared")
    res.count(ncited, "cited")
    return res


def main(argv):
    as_json, targets = result.flag(argv[1:], "--json")
    at_commit, targets = result.flag(targets, "--at-commit")
    results = []
    for t in (targets or ["."]):
        got = check(t, as_json, at_commit)
        if isinstance(got, int):
            return got
        results.append(got)
    return result.emit(results, as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
