#!/usr/bin/env python3
"""Verify a committed REPORT block against the tree it claims (P-16).

An agent's final message is a REPORT block, and the identical block is
committed as the last entry of its task file's execution record. One shape
means a script can check it; two places means the record cannot quietly
disagree with what was said. This is that script, and it runs before the
verifier does -- a malformed report is a re-dispatch, not a judgement call.

WHICH BLOCKS IT JUDGES (roadmap 0.3.2, L-2.7). A task file holds many blocks:
each worker's step report, a step's later attempts, and the supervisor's own
task-level report at each close or stop. `check_report . T-n` judges the
task's latest task-level block and, for each step the file reports, that
step's latest block; `check_report . T-n.S-m` judges that step's latest block.
An earlier block for the same id is a superseded attempt and is not judged: a
failed attempt's commits are never promoted, so its citations would stand as a
finding for ever. It used to judge one block, the last one naming the task,
so `check_report . T-9` read clean over a step block that `check_report .
T-9.S-3` refused, on the same tree (F-37). Each finding names its block.

The finding classes it emits, and the rule each enforces, are in
docs/CHECKS.md -- one home (P-34). This docstring deliberately does not
list them: it used to, and ten classes were emitted, controlled, and
absent from the lists here. `unruled-finding` in check_plugin.py keeps
docs/CHECKS.md and the code equal in both directions.

Usage:  check_report.py <project-or-devteam> <T-n> [--json] [--blocking-only] [--at-commit]
Exit 0 clean, 1 findings, 2 could not run, 3 not evaluated -- the contract is
result.py's (roadmap 0.3.1, L-1.1).  Control: test_check_report.py.
"""
import collections
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claim   # noqa: E402 -- a task's current claim, computed in one place (L-2.5)
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)

REQUIRED = ("status", "model", "env", "requirements", "scope", "commits",
            "checks", "questions", "findings-for-protocol", "budget", "notes")
STATUSES = ("DONE", "BLOCKED", "NEEDS-DECISION", "RED", "READY-TO-AUDIT")
# Statuses that assert the work is finished, and so must be backed by a clean
# tree, a commit, and at least one check that was actually run.
CLOSING = ("DONE", "READY-TO-AUDIT", "ACCEPTED")
# ACCEPTED means the client closed the task OVER a failed or absent
# verification (P-2), so the title and the report are EXPECTED to disagree and
# the decision in the title is what reconciles them. Checking them for
# agreement inverts the state's whole purpose -- and lands on the common shape,
# not the rare one: the supervisor verifies each step and reports `DONE`, then
# an independent verifier checks the task (P-18), so a client accepting over a
# failure is almost always accepting over the VERIFIER's. The supervisor having
# escalated first, so its report reads `NEEDS-DECISION`, is the unusual case.


DASH = r"[—–-]"
# A title's separator is a dash SURROUNDED BY WHITESPACE. Neither greedy nor
# non-greedy matching on a bare dash works: non-greedy splits at the hyphen in
# "well-known", and greedy splits at the one inside "DONE (2026-09-03)". A
# hyphen inside a word or a date never has spaces around it; a separator always
# does.
SEP = r"(?:\s+[\u2014\u2013]\s+|\s+-\s+)"
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
# A status is one of STATUSES, read across its continuation lines (L-2.3), and
# may carry one qualifier: a report the supervisor reconstructed after its
# worker died says so, `DONE (reconstructed: <by whom, and why>)`. pricelog's
# `DONE -- RECONSTRUCTED` was refused, and `53326f6` moved the word into
# `notes:` so the parser would pass it. A check that refuses an honest label
# and accepts a less informative one is selecting against disclosure (F-86;
# roadmap 0.3.2, L-2.8).
STATUS = re.compile(r"^(" + "|".join(map(re.escape, STATUSES)) + r")"
                    r"(?:\s+\(reconstructed:\s*(\S.*?)\s*\))?$")
QUALIFIER = "`<status> (reconstructed: <by whom, and why>)`"
TITLE = re.compile(r"^#\s+(T-\d+)" + SEP + r"(.*?)" + SEP + r"(\S.*)$")
RECORD_HEADING = re.compile(r"^##\s+Execution record\s*$", re.I)
# `HEAD` alone means "the commit this block is in"; `HEAD~1`, `HEAD^` and a
# bare hash are ordinary resolvable refs and are checked as such.
HASH = re.compile(r"^\s*-\s+([0-9a-f]{7,40}|HEAD(?:[~^]\d*)+|HEAD)\b")


def git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, ""


# `git status --porcelain` emits `XY PATH`, and X is a SPACE for a
# worktree-only change. Stripping the output eats that space and shifts every
# path by one character. The original check only counted lines, so it never
# noticed; scoping it to a task's paths made it matter immediately.
STATUS_LINE = re.compile(r"^(..) (.*)$")


def status_paths(root):
    """(returncode, [path, ...]) for every uncommitted path, unshifted."""
    try:
        p = subprocess.run(["git", "-C", root, "status", "--porcelain"],
                           capture_output=True, text=True)
    except FileNotFoundError:
        return 127, []
    out = []
    for line in p.stdout.split("\n"):
        m = STATUS_LINE.match(line)
        if m:
            path = m.group(2).strip()
            out.append(path.split(" -> ")[-1])       # a rename names both
    return p.returncode, out


SCOPE_FIELD = re.compile(r"^-\s+\*\*Scope\.\*\*\s*(.*)$")
SCOPE_ITEM = re.compile(r"^\s+-\s+`?([^`\s]+)`?\s*$")
ANY_FIELD = re.compile(r"^-\s+\*\*[A-Za-z]")

# --- what the task file OFFERS (roadmap 0.3.1, L-1.3) ----------------------
# The grammar above says what parses; these say what was written in each
# shape, so a row the grammar misses is named instead of passed over.
TITLE_ISH = re.compile(r"^#\s*T-?\s*\d+\b(?![.'’])")
# A REPORT line naming a task -- `REPORT tester T-18.S-4-pre`, `REPORT auditor
# T-18 (re-run)` -- whatever follows. Prose that merely begins with the word
# ("REPORT block above …") names no task and is not offered.
HEADER_ISH = re.compile(r"^REPORT\s+\S+\s+(T-\d+)")
# The id such a line names, when it names one cleanly: `T-10.S-3` in a header
# whose annotation wraps onto the next line. `T-18.S-4-pre` names no step id,
# so no later block can be the same step's.
HEADER_ID = re.compile(r"^REPORT\s+\S+\s+(T-\d+)(?:\.(S-\d+))?(?=[\s(]|$)")
# A REPORT field as a writer would write one, annotation and all: F-88's
# `checks (all run by the supervisor…):` ended the parse, and every field
# after it read as missing. Only the grammar's own keys: prose after a block
# ends is full of `landing:` and `anchor:`, and pricelog's T-6, T-11 and T-13
# each have one -- measured as false gaps with any lowercase key allowed.
KEY_ISH = re.compile(r"^(" + "|".join(map(re.escape, REQUIRED)) + r")\s*(?:\([^)]*\)\s*)?:")
SCOPE_ITEMISH = re.compile(r"^\s+[-*+]\s+\S")
CONTAINMENT_ISH = re.compile(r"^\|\s*[*`_]*\s*containment\b", re.I)


def task_scope(devteam, task_id, unparsed=None):
    """The paths a task declares it writes, relative to the project root.

    `unparsed`, when given, collects the 1-based line of each list item under
    `Scope.` that does not parse as a path -- one such item used to be
    skipped here in silence, so `dirty-tree` and `unfinished-scope` never
    looked at what it named.
    """
    try:
        lines = open(os.path.join(devteam, "tasks", f"{task_id}.md"),
                     encoding="utf-8", errors="replace").read().split("\n")
    except OSError:
        return []
    out, collecting = [], False
    for n, line in enumerate(lines, 1):
        if SCOPE_FIELD.match(line):
            collecting = True
            continue
        if collecting:
            m = SCOPE_ITEM.match(line)
            if m:
                out.append(m.group(1).strip("`"))
                continue
            if SCOPE_ITEMISH.match(line):
                if unparsed is not None:
                    unparsed.append(n)
                continue
            if line.strip() and (ANY_FIELD.match(line) or line.startswith("#")):
                break
    return [p for p in out if p and "<" not in p]


# One block: the 0-based line of its header, what the header says, its fields
# (each a list: a key's inline value, then its indented continuation lines),
# each key's line, and the line the field parse stopped at, or None when it
# ran to the block's end (roadmap 0.3.1, L-1.3).
Block = collections.namedtuple("Block", "start role task step note fields at stop")


def parse_block(lines, i):
    """The block whose header is `lines[i]`."""
    m = HEADER.match(lines[i])
    fields, key, at, stop = {}, None, {}, None
    j = i + 1
    while j < len(lines):
        line = lines[j]
        if HEADER.match(line) or line.startswith("#"):
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


def judged(blocks, task_id, step_id=None):
    """(the blocks a run for `task_id`, or for its step `step_id`, judges, in
    file order; how many earlier blocks for the same ids they supersede)."""
    mine = [b for b in blocks if b.task == task_id and (b.step == step_id if step_id else True)]
    latest = {}
    for b in mine:
        latest[b.step] = b                    # a later block for the same id wins
    return sorted(latest.values(), key=lambda b: b.start), len(mine) - len(latest)


def landed(repo, path, n, commit):
    """Whether line `n` of `path` was already in it at `commit`: the commit
    that wrote the line, by blame, is `commit` or an ancestor of it. A line
    not yet committed was not. None when blame cannot say.

    A block is dated by its header line, which the record writes once and
    never edits; a field repaired after the fact leaves the header where it
    was. `--ignore-revs-file ""` clears any the project configured, which
    would move a line's authorship to an older commit."""
    rc, out = git(repo, "blame", "--porcelain", "--ignore-revs-file", "", "-L", f"{n},{n}",
                  "--", path)
    sha = out.split(" ", 1)[0] if rc == 0 else ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        return None
    if set(sha) == {"0"}:
        return False
    return git(repo, "merge-base", "--is-ancestor", sha, commit)[0] == 0


def previous_claim(repo, task_id, title_status, b):
    """A task-level block landed before the task's current claim is the
    PREVIOUS claim's report (roadmap 0.3.2, L-2.7; F-136): `(label, the
    claim's commit)` when block `b` was already in the task file at the commit
    the claim began, else None.

    A restart is a new claim under a new label (L-2.5), and until its
    supervisor reports, the file's latest task-level block is the last close
    or stop -- so its DONE was compared with the new RUNNING title, and 8 of
    0.3.1's 14 restart commits were refused for it. The claim is read from its
    one home, claim.py. A title that carries no label, or one no board commit
    carries, has no current claim here, and its block is compared as it
    always was: a reopen under the claim's own label compares its own close
    (the owner's reading of `b57c29e`, `7442808` and `f0db47c`)."""
    if not claim.label(title_status):
        return None
    rel = f"tasks/{task_id}.md"
    lab, anchor, _why = claim.current(repo, {task_id: (rel, title_status)})[task_id]
    if anchor and landed(repo, f"devteam/{rel}", b.start + 1, anchor):
        return lab, anchor
    return None


# THE CANONICAL FAILURE OF ASSISTED DEVELOPMENT, AND IT IS CHEAP TO CATCH.
# Work reported "done and tested" that is a function stub with a TODO comment
# and a hard-coded value chosen so the test passes. Several of those at once is
# how somebody discovers they are two weeks behind where they believed they
# were, and no amount of instructing an agent to be careful prevents it.
#
# This pipeline DELIBERATELY CREATES stubs -- a tests-first step writes the
# instrument red against one -- and nothing has ever checked they are gone by
# the time a task claims to have discharged its requirements.
#
# `raise NotImplementedError` is the statement; `raises(NotImplementedError)`
# is a test asserting behaviour and is legitimate, so the pattern matches the
# raise and not the assertion.
STUB = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b|(?<!_)\braise\s+NotImplementedError")


def stub_markers(repo, scope):
    """[(path, line no, marker)] for stub markers inside these paths."""
    out = []
    for rel in sorted(set(scope)):
        base = os.path.join(repo, rel)
        files = []
        if os.path.isdir(base):
            for root, _, names in os.walk(base):
                files += [os.path.join(root, n) for n in names if n.endswith(".py")]
        elif os.path.isfile(base):
            files = [base]
        for f in files:
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        m = STUB.search(line)
                        if m:
                            out.append((os.path.relpath(f, repo), n, m.group(0).strip()))
            except OSError:
                continue
    return out

def report_budget(line, field):
    """`budget: tokens=<n> minutes=<n>` -> (the number, whether it was marked
    approximate), or None.

    `tokens=~N` is read as N, marked approximate (roadmap 0.3.2, L-2.8). Four
    workers wrote `~N` because none can read its own counter, and each was
    out by 36, 24, 15.6 and 16.6 times; the regex wanted a digit after `=`,
    so none was compared (F-32). A worker stating a bare number it cannot
    know was checked, and one honestly hedging was not."""
    if not line:
        return None
    m = re.search(rf"\b{field}\s*=\s*(~?)\s*([0-9]+(?:\.[0-9]+)?)", str(line))
    return (float(m.group(2)), bool(m.group(1))) if m else None


CONTAINMENT = re.compile(r"^\|\s*Containment\s*\|\s*`?(structural|guard-only)`?(?![\w-])")


def charter_containment(devteam):
    """(`structural`, `guard-only` or None, the line of a row that did not parse).

    Read from the charter's own row (FORMATS.md, charter `Containment`), because
    only a DECLARATION may exclude the harness comparison (roadmap 0.3.1,
    L-1.2). A row that does not parse -- `guard only`, say, or the template's
    unfilled `<…>` cell, which `setup` fills -- declares nothing, and is named,
    because a reader of the charter sees a Containment row there (L-1.3).
    """
    unparsed = None
    try:
        with open(os.path.join(devteam, "CHARTER.md"), encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                m = CONTAINMENT.match(line)
                if m:
                    return m.group(1), None
                if CONTAINMENT_ISH.match(line) and unparsed is None:
                    unparsed = n
    except OSError:
        pass
    return None, unparsed


def harness_meter(repo, task_id):
    """What the harness metered for the step its `.sandbox` line names:
    (that step, the sandbox's base commit, the meter, None) -- or (the step,
    None, None, why there is nothing to compare against).

    NO LONGER SILENT (roadmap 0.3.1, L-1.2). This used to return None for every
    absence, on the reasoning that a `guard-only` project has no sandbox and a
    report from one is not defective for lacking a budget file. That reasoning
    stands, and the charter's `Containment: guard-only` now EXCLUDES the
    comparison by declaration, named in the line (see `check`). What it hid was
    the other case: a `structural` project whose sandboxes had been closed read
    `clean` because the comparator was gone (F-32's T-4 case, pricelog
    RECORD.md:356). With no declaration behind it, that absence is a part not
    evaluated, and the reason says which file was missing.

    ONE LINE, ONE STEP (roadmap 0.3.2, L-2.7). The harness rewrites the line at
    every dispatch, `T-n S-m <id> … root <path>`, so it holds the meter of the
    last step dispatched and of no other: F-103 compared S-2's block with
    S-4's meter. The step and the sandbox's base are returned, so the caller
    compares a block only with the meter that is its own.
    """
    lock = os.path.join(repo, "devteam", ".run", "locks", f"{task_id}.sandbox")
    try:
        with open(lock, encoding="utf-8") as fh:
            line = fh.read().strip()
    except OSError:
        return None, None, None, f"no devteam/.run/locks/{task_id}.sandbox names a sandbox to compare against"
    words = line.split()
    step = words[1] if len(words) > 1 and words[1] != "-" else None
    m = re.search(r"\broot\s+(\S.*)$", line)
    if not m:
        return step, None, None, f"devteam/.run/locks/{task_id}.sandbox names no `root`"
    meta = os.path.join(m.group(1).strip(), "meta")
    try:
        with open(os.path.join(meta, "budget.json")) as fh:
            doc = json.load(fh)
    except OSError:
        return step, None, None, (f"the sandbox's meta/budget.json is gone (its root no longer "
                                  f"exists, or it was closed)")
    except ValueError:
        return step, None, None, "the sandbox's meta/budget.json is not JSON"
    if not isinstance(doc, dict):
        return step, None, None, "the sandbox's meta/budget.json is not a JSON object"
    try:
        with open(os.path.join(meta, "base.sha"), encoding="utf-8") as fh:
            base = fh.read().strip() or None
    except OSError:
        base = None
    if base is None:
        return step, None, None, ("the sandbox's meta/base.sha names no commit, so which "
                                  "attempt its meter measured cannot be told")
    return step, base, doc, None


def steps_named(names):
    """`S-1, S-2 and S-4`."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def figure(x):
    """A figure as a person reads it. `{:g}` wrote every meter of a million
    tokens or more in scientific notation, `1.2692e+06`, and a worker's step
    is usually metered in millions; a whole number is written whole."""
    return f"{x:.0f}" if float(x).is_integer() else f"{x:g}"


def check(project, want_id):
    """`want_id` is `T-n` or `T-n.S-m`. A step is checked as a step: it does
    not own the task's title line, so its status is never compared to it.

    Returns (findings, parts not evaluated, exclusions, notes, counts), or None
    when the project is not a git repository. A finding is (class, anchor or
    None, message), and its anchor is the header line of the block it is
    about."""
    task_id, _, step_id = want_id.partition(".")
    step_id = step_id or None
    findings = []
    add = lambda kind, detail, at=None: findings.append((kind, at, detail))
    gaps, excluded = [], []  # (part, reason, advisory); (part, declaration)
    notes, counts = [], []   # (label, text); (n, label)
    outcome = lambda: (findings, gaps, excluded, notes, counts)

    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    repo = os.path.dirname(devteam)
    path = os.path.join(devteam, "tasks", f"{task_id}.md")
    if not os.path.isfile(path):
        add("no-file", os.path.relpath(path, repo))
        return outcome()

    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().split("\n")

    title_status = None
    for line in lines:
        m = TITLE.match(line)
        if m:
            title_status = m.group(3).strip()
            break

    if not any(RECORD_HEADING.match(l) for l in lines):
        add("no-report", "the task file has no `## Execution record` section")

    task_rel = f"tasks/{task_id}.md"
    blocks = [parse_block(lines, i) for i, l in enumerate(lines) if HEADER.match(l)]
    read, superseded = judged(blocks, task_id, step_id)
    # A REPORT line naming this task that HEADER cannot read is a block this
    # run judges nothing of -- F-34's shape, where attempt 2's header did not
    # parse and the check read attempt 1 in its place -- unless a block the
    # grammar does read comes after it for the same id. Then it is a
    # superseded attempt, like any earlier block for that id.
    unread = []
    for j, l in enumerate(lines):
        h = HEADER_ISH.match(l)
        if not h or h.group(1) != task_id or HEADER.match(l):
            continue
        loose = HEADER_ID.match(l)
        ident = (loose.group(1), loose.group(2)) if loose else None
        if step_id and ident and ident[1] != step_id:
            continue                          # another id, and this run reads one step
        if ident and any(b.start > j and (b.task, b.step) == ident for b in blocks):
            continue
        unread.append(j + 1)
    if unread:
        gaps.append(("the REPORT blocks", result.unparsed(
            [(task_rel, n) for n in unread], len(unread),
            f"REPORT lines naming {task_id} with no later block for their id",
            "`REPORT <role> T-n[.S-m] [(<annotation>)]` on one line",
            "a report may have been passed over (F-34)"), False))
    if not read and blocks:
        # Asking for a task and finding only another task's block, or a step
        # other than the one asked for, is a wrong report. The last block is
        # the one read, as it always was, and it is judged on its own terms.
        read = [blocks[-1]]
    counts += [(len(read), "blocks judged"), (superseded, "superseded")]
    if not read:
        add("no-report", "no REPORT block in the execution record")
        return outcome()

    # NO REPOSITORY IS "COULD NOT RUN" (roadmap 0.3.1, L-1.1). This branch
    # returned the bare findings list after 0.3.1's step 3.1 made every other
    # return a (findings, gaps, excluded) triple, so a project that is not a
    # git repository ended in a traceback -- none of the four results. It was
    # a `no-file` finding before that, which the rule for that class (the
    # task id against `tasks/`) never covered.
    rc, _ = git(repo, "rev-parse", "--git-dir")
    if rc != 0:
        return None

    # A commit may be named by hash OR by subject. A report is committed in
    # the same commit as the work (P-16), so that commit's own hash cannot be
    # written inside it -- the content would have to hash to a value contained
    # in the content. Both workers in the first real dispatch hit this and
    # refused to invent a placeholder, which was the right call.
    #
    # BOTH ARE READ IN HEAD'S HISTORY, NOT `--all` (roadmap 0.3.2, L-2.6). At
    # the gate HEAD is the commit being judged, and a commit the report cites
    # must be in the history that commit creates. `--all` let a subject resolve
    # on another branch, or under `refs/devteam/sandbox/`, where a promotion
    # stopped on a conflict leaves an unpromoted worker's commits (sandbox.py);
    # and a hash resolved if it named any commit object, a refused gate
    # candidate among them. Workers cite their commits by subject, because
    # promotion rewrites every hash, so the ancestry test reaches the commits a
    # supervisor or the manager cites by hash.
    rc, log = git(repo, "log", "--format=%s")
    subjects = set(log.split("\n")) if rc == 0 else set()

    containment, bad_row = charter_containment(devteam)
    if bad_row:
        gaps.append(("the charter's Containment row", f"CHARTER.md:{bad_row} does not parse "
                     "as `| Containment | structural or guard-only |`, so it declared no "
                     "exclusion", False))
    if containment == "guard-only":
        excluded.append(("budget-mismatch and model-mismatch",
                         "the charter's `Containment: guard-only`, which has no harness meter"))
    meter = None                  # read once, for the first step block that needs it
    unmetered = collections.defaultdict(list)   # why -> [the steps it applies to]

    for b in read:
        name = f"{b.task}.{b.step}" if b.step else b.task
        at = f"{task_rel}:{b.start + 1}"
        # EACH FINDING NAMES ITS BLOCK (L-2.7), so the same defect in two
        # blocks is two identities, and neither can stand in for the other at
        # the gate or under an acceptance.
        say = lambda text, name=name: f"{name}: {text}"
        # The field parse stops at the first line it cannot read (F-88). A field
        # of this block's grammar that it had not yet read, at or after that
        # point and before the block's end, was offered and never read.
        if b.stop is not None:
            rest = []
            for j in range(b.stop, len(lines)):
                if HEADER.match(lines[j]) or HEADER_ISH.match(lines[j]) or lines[j].startswith("#"):
                    break
                k = KEY_ISH.match(lines[j])
                if k and k.group(1) not in b.fields:
                    rest.append(j + 1)
            if rest:
                gaps.append((f"{name}'s REPORT block", f"{task_rel}:{b.stop + 1} does not parse as "
                             f"`<key>: <value>` or an indented continuation, and {len(rest)} field "
                             f"line(s) from there on were not read ({result.anchors([(task_rel, n) for n in rest])}) "
                             "(F-88)", False))
        # Asking for a task and finding only one of its steps is a mid-flight
        # state, not a wrong report: the task has simply not reported yet, and the
        # step block is still worth checking on its own terms. Only a DIFFERENT
        # task, or a step other than the one asked for, is wrong.
        if b.task != task_id or (step_id and b.step != step_id):
            add("wrong-task", f"the last block reports {name}, not {want_id}", at)
        # A block that describes a STEP is not the task's own report. Comparing its
        # status to the task's title produced a spurious `status-mismatch` on every
        # mid-flight step verification, because a finished step sits under a
        # RUNNING task by definition.
        is_step = bool(b.step)

        for key in REQUIRED:
            if key not in b.fields:
                add("missing-field", say(f"the block has no `{key}:`"), at)

        # READ WHOLE (roadmap 0.3.2, L-2.3): a status continued onto the next
        # line was read from its first, and named as not evaluated.
        said = " ".join(x.strip() for x in b.fields.get("status") or []).strip()
        m = STATUS.match(said)
        status = m.group(1) if m else ""
        if said and not m:
            shown = said if len(said) <= 80 else said[:79] + "…"
            add("bad-report-status", say(f"{shown!r} is not one of {', '.join(STATUSES)}, "
                                         f"or {QUALIFIER}"), at)
            # Everything below compares this status against the tree, which is
            # meaningless once it is not a status. One fault should produce one
            # finding: cascading consequences make a report harder to triage than
            # the defect that caused them.
        elif m and m.group(2):
            notes.append(("reconstructed", f"{name} — {m.group(2)}"))

        # THE TASK'S REPORT NOW: its own task-level block, and its current
        # claim's. That block alone is compared with the task's title and its
        # tree. A task-level block that was already in the file when the claim
        # its RUNNING title names began is the previous claim's close or stop:
        # compared with nothing of the current run -- not the title, not the
        # meter, and not the tree, where a restart's tests-first stub met the
        # previous close's DONE as `unfinished-scope` (the owner's answer of
        # 2026-09-24). Its own fields, status, evidence and citations are
        # still judged, as every judged block's are.
        current = not is_step
        if current and status and title_status and title_status.startswith("RUNNING"):
            prior = previous_claim(repo, task_id, title_status, b)
            if prior:
                current = False
                excluded.append((f"status-mismatch, dirty-tree and unfinished-scope for {name}'s "
                                 "block", f"the claim its title names, {prior[0]}, which began at "
                                 f"{prior[1][:7]} after the block landed: it is the previous "
                                 "claim's report (F-136)"))
        if status in CLOSING:
            # ACCEPTED reconciles a disagreement rather than asserting agreement,
            # so it is compatible with any report status -- including the `RED` or
            # `NEEDS-DECISION` that made the client's decision necessary.
            if (current and title_status
                    and not title_status.startswith(("DONE", "READY-TO-AUDIT", "ACCEPTED"))):
                add("status-mismatch", say(f"status {status} but the title says {title_status!r}"), at)
            checks = [c for c in b.fields.get("checks", []) if c.strip() and c.strip() != "none"]
            if not checks:
                add("no-evidence", say(f"status {status} with no `checks:` lines — "
                                       "a requirement is discharged by evidence, never by assertion"), at)
        elif status and current and title_status and title_status.startswith("DONE"):
            add("status-mismatch", say(f"status {status} but the title says {title_status!r}"), at)
        # The comparison above needs the title, and a title that does not parse
        # left it silently unmade (L-1.3).
        if status and current and title_status is None:
            offered = [n for n, l in enumerate(lines, 1) if TITLE_ISH.match(l)]
            gaps.append(("status-mismatch", (
                f"{task_rel}:{offered[0]} does not parse as `# T-n — <title> — <status>`"
                if offered else f"{task_rel} has no title line")
                + ", so the report's status was compared against no title", False))

        # Only a line that STARTS a list item is a commit; anything else is a
        # continuation of the one above it.
        for line in b.fields.get("commits", []):
            if not line.strip().startswith("- "):
                continue
            text = line.strip()[2:].strip()
            if not text or text == "none":
                continue
            h = HASH.match("- " + text)
            ref = h.group(1) if h else None
            if ref and ref != "HEAD":            # a hash, or HEAD~1 / HEAD^
                # The ancestry test's one home is result.py, which check_trace
                # reads for a ledger entry's fix too (roadmap 0.3.3, L-3.2).
                stands = result.in_history(repo, ref)
                if stands == result.ABSENT:
                    add("unknown-commit", say(f"{ref} is not a commit in this repository"), at)
                elif stands == result.ELSEWHERE:
                    add("unknown-commit", say(f"{ref} is a commit, and not one in HEAD's history"), at)
                continue
            # `HEAD <subject>` names the commit this block is committed in -- its
            # own hash cannot appear inside it, so the SUBJECT is what makes it
            # resolvable afterwards. Validate that, not the marker.
            subject = text[len(ref):].strip() if ref else text
            if subject and subject not in subjects:
                add("unknown-commit", say(f"no commit in HEAD's history has the subject "
                                          f"{subject[:60]!r}"), at)

        # These three are the TASK's, not the block's, and only its task-level
        # block reaches them, so their messages name the task. The two that
        # read the tree read it for the current claim's report only (above).
        if status in CLOSING and current:
            # Only paths the TASK controls. A supervisor owns its declared scope and
            # its own task file, and nothing else -- so measuring the whole tree
            # made a clean close unreachable from inside the task whenever the
            # manager happened to have an uncommitted file of its own. That is a
            # check nobody can satisfy, which is a check that gets ignored (P-35).
            unscoped = []
            scope = task_scope(devteam, task_id, unscoped) + [f"devteam/tasks/{task_id}.md"]
            if unscoped:
                gaps.append(("dirty-tree and unfinished-scope", f"{len(unscoped)} list item(s) "
                             "under Scope. do not parse as a path, so neither class looked at "
                             f"what they name ({result.anchors([(f'tasks/{task_id}.md', n) for n in unscoped])})",
                             False))
            rc, paths = status_paths(repo)
            if rc == 0 and paths:
                mine = [p for p in paths
                        if any(p == s.rstrip("/") or p.startswith(s.rstrip("/") + "/")
                               for s in scope)]
                if mine:
                    add("dirty-tree", f"uncommitted inside {task_id}'s scope on status "
                                      f"{status}: {', '.join(mine[:4])}", at)
            # A TASK DOES NOT CLOSE WITH A STUB IN ITS DECLARED SCOPE.
            for rel, n, marker in stub_markers(repo, task_scope(devteam, task_id))[:8]:
                add("unfinished-scope",
                    f"{rel}:{n} carries {marker!r} while {task_id} reports {status}. "
                    "A tests-first step leaves a stub on purpose; a closing task has "
                    "no business still holding one. Remove it, or the task is not "
                    "the thing the report says it is", at)
        if status in CLOSING and not is_step:
            # The task's OWN closing commit, not HEAD. Checking HEAD made every
            # finished task report `head-subject` the moment any later task
            # committed -- so an audit run afterwards saw a false positive against
            # every historical task. What the rule means is "this task committed
            # something that names it", and that stays true forever -- in HEAD's
            # history, where the citations above are read too (L-2.6). So a
            # previous claim's close is held to it as well.
            if not any(s.strip().lower().startswith(task_id.lower()) for s in subjects):
                add("head-subject", f"no commit in HEAD's history has a subject beginning with "
                                    f"{task_id}", at)

        # THE HARNESS METER, AGAINST THE BLOCK IT BELONGS TO (L-2.7). A
        # task-level block is a supervisor's, and the harness meters no
        # supervisor: F-109 marked a correct Sonnet supervisor's report for
        # re-dispatch against its last worker's Opus meter. So it is excluded,
        # by the header that declares it the task's, and named. A step's block
        # is compared with the meter the `.sandbox` line names for that step,
        # and with no other -- not S-4's meter for S-2's block (F-103), nor a
        # later attempt's for an earlier attempt's block, which was already in
        # the task file when the sandbox opened.
        if containment == "guard-only":
            continue
        if not is_step:
            excluded.append((f"{name}'s block against the harness meter",
                             "its header, which names no step: a task-level block is a "
                             "supervisor's report, and the harness meters no supervisor (F-109)"))
            continue
        if meter is None:
            meter = harness_meter(repo, task_id)
        on_line, base, harness, missing = meter
        if missing:
            unmetered[missing].append(b.step)
            continue
        if on_line != b.step:
            unmetered[f"devteam/.run/locks/{task_id}.sandbox names "
                       f"{on_line or 'no step'}"].append(b.step)
            continue
        if landed(repo, f"devteam/{task_rel}", b.start + 1, base) is not False:
            unmetered[f"the sandbox devteam/.run/locks/{task_id}.sandbox names opened at "
                      f"{base[:7]} with the block already in the task file, so its meter "
                      "is a later attempt's"].append(b.step)
            continue
        # P-17c. Both figures are self-reported today by the party least placed
        # to know them, and MEASURED 0.2.3 a live worker reported
        # `budget: tokens=3000 minutes=1` for a step the harness metered at
        # 309639 tokens -- a hundredfold understatement, written in good faith
        # by a process that cannot see the counter. So the harness's number is
        # the one that cannot be remembered wrongly, and a mismatch is a
        # FINDING rather than a correction: silently overwriting the worker's
        # figure would destroy the evidence that it cannot produce one.
        # `fields` values are LISTS -- a key's inline value plus any indented
        # continuation lines -- because `commits:` and `checks:` are lists in
        # the REPORT grammar. Reading one as a string is the F-2 class: right
        # about the field, wrong one level down.
        one = lambda k, b=b: " ".join(b.fields.get(k) or []).strip()
        want_model = one("model")
        got_model = (harness.get("model") or "").strip()
        if want_model and got_model and want_model != got_model:
            add("model-mismatch",
                say(f"the report says `model: {want_model}` and the harness "
                    f"dispatched {got_model}"), at)
        # Tokens get 10% and minutes 20%, because the worker is estimating a
        # number it genuinely cannot read, and a tolerance tight enough to fire
        # on honest rounding is one that gets ignored. A figure marked
        # approximate gets the same tolerance, and the finding says it was
        # marked (L-2.8): the mark is honest, and the harness's number is still
        # the one to trust.
        unreadable = []
        for field, tol in (("tokens", 0.10), ("minutes", 0.20)):
            got = report_budget(one("budget"), field)
            actual = harness.get(field)
            if got is None and actual:
                # The harness has a figure and the report gives none this can
                # read, and the comparison was not made: that used to read as
                # clean (L-1.3).
                written = re.search(rf"\b{field}\s*=\s*(\S+)", one("budget"))
                unreadable.append(f"{field} as `{written.group(1)}`, which is not a number"
                                  if written else f"no {field}= figure")
            if got is None or not actual:
                continue
            claimed, approximate = got
            if abs(claimed - actual) > tol * abs(actual):
                shown = (f"~{figure(claimed)}, marked approximate," if approximate
                         else figure(claimed))
                add("budget-mismatch",
                    say(f"the report says {field}={shown} and the harness "
                        f"metered {figure(actual)} ({tol:.0%} tolerance)"), at)
        if unreadable:
            gaps.append(("budget-mismatch", f"{name}'s `budget:` gives "
                         f"{' and '.join(unreadable)}, so it was not compared with "
                         "the harness's figure (F-32)", True))

    # One part per class, naming each step, rather than one per step: a task
    # with twelve steps and no meter left says so in two lines. Keeping a
    # step's meter past its sandbox's close is 0.3.7's (F-9).
    if unmetered:
        why = "; ".join(f"{reason} ({steps_named(steps)})" for reason, steps in unmetered.items())
        reason = f"no step block was compared with a meter of its own: {why}"
        gaps.append(("budget-mismatch", reason, True))
        gaps.append(("model-mismatch", reason, False))

    return outcome()


# ADVISORY findings say something true about the REPORT that is not a claim
# about the WORK, and that the party who wrote it could not have got right.
#
# There is exactly one, and it earned the category by breaking a live run.
# `budget-mismatch` fires because a worker cannot see the harness's counter:
# the first one ever metered reported `tokens=3000` against `309639`, in good
# faith, and 0.2.4's own end-to-end reproduced it at `15000` against `571986`.
# The number to trust is the harness's and it is already recorded; the worker's
# is a fact about self-reporting (P-17c).
#
# THE PAIR THAT MADE THIS NECESSARY, because it is the shape this project keeps
# paying for -- two rules each right alone that cannot both be satisfied:
#   `supervise` says budget-mismatch is recorded, never corrected
#   `verify`    treats a non-zero exit here as FAIL
#   `supervise` says a FAIL is re-dispatched once
# and a re-dispatch cannot help, because the new worker cannot see the counter
# either. Perfect work, blocked forever, by a finding nobody is allowed to fix.
# Found by a real supervisor on the first end-to-end run, which escalated it
# rather than picking one rule to break -- exactly right, and the escalation is
# what this flag answers.
#
# `model-mismatch` is deliberately NOT advisory: a report naming a model that
# did not run is a report about a different run, and P-40 says a result is not
# comparable across models. That one blocks.
ADVISORY = {"budget-mismatch"}

# The classes that read the WORKING STATE rather than a commit's tree or its
# history, which `--at-commit` excludes (result.AT_COMMIT; roadmap 0.3.1,
# L-1.5): `git status`, and the harness's meter, which lives under the ignored
# `devteam/.run/` and in a sandbox outside the repository, so no commit holds it.
WORKING_STATE = ("dirty-tree", "budget-mismatch", "model-mismatch")


def main(argv):
    as_json, argv = result.flag(list(argv), "--json")
    blocking_only, argv = result.flag(argv, "--blocking-only")
    at_commit, argv = result.flag(argv, "--at-commit")
    if len(argv) < 3:
        return result.could_not_run(
            "check_report", __doc__.strip().split("Usage:")[-1].strip(), as_json)
    project, task_id = os.path.realpath(argv[1]), argv[2]
    if not re.fullmatch(r"T-\d+(\.S-\d+)?", task_id):
        return result.could_not_run("check_report", f"{task_id!r} is not a task or step id", as_json)
    got = check(project, task_id)
    if got is None:
        return result.could_not_run("check_report", f"not a git repository: {project}", as_json)
    findings, gaps, excluded, notes, counts = got
    res = result.Result("check_report", task_id, width=18)
    res.blocking_only = blocking_only
    anchor = f"tasks/{task_id.partition('.')[0]}.md"
    for n, label in counts:
        res.count(n, label)
    for kind, where, detail in findings:
        res.finding(kind, where or anchor, detail, advisory=kind in ADVISORY)
    for part, reason, advisory in gaps:
        res.gap(part, reason, advisory)
    for part, declaration in excluded:
        res.exclude(part, declaration)
    for label, text in notes:
        res.note(label, text)
    if at_commit:
        res.exclude_classes(WORKING_STATE, result.AT_COMMIT)
    # WHAT A DECISION ACCEPTED (roadmap 0.3.1, L-1.6), for this task's own
    # report. An acceptance names the task's file, so a run for another task
    # neither applies it nor calls it stale; and a step's block is not the
    # task's report the acceptance was decided against, so a step run covers
    # none. A part is not acceptable here at all: check_report's parts name no
    # task, so no run could ever find one stale (result.py refuses it).
    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    covers = lambda a: "." not in task_id and a.file == anchor
    add = lambda kind, where, detail: res.finding(kind, where, detail)
    for where, detail in res.accept(result.acceptances(devteam), covers):
        add("stale-acceptance", where, detail)
    # ADVISORY findings are still PRINTED under --blocking-only. Suppressing
    # them would make the flag a way to not see something, which is how a
    # check loses the thing it was built for; it changes the verdict, never
    # the report.
    if blocking_only and res.findings and res.exit_code == result.CLEAN:
        res.trailer.append(f"{task_id}: no blocking findings — every one above is advisory, "
                           f"a fact about the report that the work does not depend on")
    return result.emit([res], as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
