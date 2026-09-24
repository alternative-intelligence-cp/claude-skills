#!/usr/bin/env python3
"""Verify a committed REPORT block against the tree it claims (P-16).

An agent's final message is a REPORT block, and the identical block is
committed as the last entry of its task file's execution record. One shape
means a script can check it; two places means the record cannot quietly
disagree with what was said. This is that script, and it runs before the
verifier does -- a malformed report is a re-dispatch, not a judgement call.

The finding classes it emits, and the rule each enforces, are in
docs/CHECKS.md -- one home (P-34). This docstring deliberately does not
list them: it used to, and ten classes were emitted, controlled, and
absent from the lists here. `unruled-finding` in check_plugin.py keeps
docs/CHECKS.md and the code equal in both directions.

Usage:  check_report.py <project-or-devteam> <T-n> [--json] [--blocking-only] [--at-commit]
Exit 0 clean, 1 findings, 2 could not run, 3 not evaluated -- the contract is
result.py's (roadmap 0.3.1, L-1.1).  Control: test_check_report.py.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
HEADER = re.compile(r"^REPORT\s+(\S+)\s+(T-\d+)(?:\.(S-\d+))?\s*$")
KEY = re.compile(r"^([a-z][a-z-]*):\s*(.*)$")
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


def parse_report(lines, task_id=None, step_id=None, where=None):
    """The last REPORT block FOR THIS TASK, as (role, task, step, fields).

    Not simply the last block in the file. A supervisor's record holds its
    workers' step blocks (`T-n.S-m`) as well as its own task block (`T-n`),
    and taking the last one meant validating a worker's step report in place
    of the supervisor's -- so a supervisor could not satisfy P-16 and P-17 at
    once. Prefer the last block whose id is exactly the task, and fall back to
    the last block of any kind so a step report can still be checked directly.

    `where`, when given, is filled with what the parse did NOT read (roadmap
    0.3.1, L-1.3): `start` and `stop`, the 0-based lines of the header and of
    the line the field parse stopped at, and `lines`, each key's line.
    """
    starts = [i for i, l in enumerate(lines) if HEADER.match(l)]
    if not starts:
        return None
    i = starts[-1]
    if task_id:
        own = [j for j in starts
               if (m := HEADER.match(lines[j])) and m.group(2) == task_id
               and (m.group(3) == step_id if step_id else not m.group(3))]
        if own:
            i = own[-1]
    m = HEADER.match(lines[i])
    fields, key, at, stop = {}, None, {}, None
    for j, line in enumerate(lines[i + 1:], i + 1):
        if HEADER.match(line) or line.startswith("#"):
            break
        k = KEY.match(line)
        if k:
            key = k.group(1)
            fields[key] = [k.group(2)] if k.group(2) else []
            at[key] = j
        elif key is not None and line.startswith((" ", "\t")) and line.strip():
            fields[key].append(line.strip())
        elif not line.strip():
            continue
        else:
            stop = j
            break
    if where is not None:
        where.update(start=i, stop=stop, lines=at)
    return m.group(1), m.group(2), m.group(3), fields



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
    """`budget: tokens=<n> minutes=<n>` -> one number, or None."""
    if not line:
        return None
    m = re.search(rf"\b{field}\s*=\s*([0-9]+(?:\.[0-9]+)?)", str(line))
    return float(m.group(1)) if m else None


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


def harness_budget(repo, task_id):
    """(what the harness metered for this task's last step, None) -- or
    (None, why there is nothing to compare against).

    NO LONGER SILENT (roadmap 0.3.1, L-1.2). This used to return None for every
    absence, on the reasoning that a `guard-only` project has no sandbox and a
    report from one is not defective for lacking a budget file. That reasoning
    stands, and the charter's `Containment: guard-only` now EXCLUDES the
    comparison by declaration, named in the line (see `check`). What it hid was
    the other case: a `structural` project whose sandboxes had been closed read
    `clean` because the comparator was gone (F-32's T-4 case, pricelog
    RECORD.md:356). With no declaration behind it, that absence is a part not
    evaluated, and the reason says which file was missing.
    """
    lock = os.path.join(repo, "devteam", ".run", "locks", f"{task_id}.sandbox")
    try:
        with open(lock, encoding="utf-8") as fh:
            line = fh.read().strip()
    except OSError:
        return None, f"no devteam/.run/locks/{task_id}.sandbox names a sandbox to compare against"
    m = re.search(r"\broot\s+(\S.*)$", line)
    if not m:
        return None, f"devteam/.run/locks/{task_id}.sandbox names no `root`"
    budget = os.path.join(m.group(1).strip(), "meta", "budget.json")
    try:
        with open(budget) as fh:
            doc = json.load(fh)
    except OSError:
        return None, (f"the sandbox's meta/budget.json is gone (its root no longer "
                      f"exists, or it was closed)")
    except ValueError:
        return None, "the sandbox's meta/budget.json is not JSON"
    if not isinstance(doc, dict):
        return None, "the sandbox's meta/budget.json is not a JSON object"
    return doc, None


def check(project, want_id):
    """`want_id` is `T-n` or `T-n.S-m`. A step is checked as a step: it does
    not own the task's title line, so its status is never compared to it."""
    task_id, _, step_id = want_id.partition(".")
    step_id = step_id or None
    findings = []
    add = lambda kind, detail: findings.append((kind, detail))
    gaps, excluded = [], []  # (part, reason, advisory); (part, declaration)
    outcome = lambda: (findings, gaps, excluded)

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
    where = {}
    parsed = parse_report(lines, task_id, step_id, where)
    # A REPORT header naming this task that HEADER cannot read, after the
    # block that was read -- or anywhere, when none was: F-34's shape, where
    # the check read an earlier block and a later report went unseen.
    after = where.get("start", -1)
    headers = [j + 1 for j, l in enumerate(lines)
               if (h := HEADER_ISH.match(l)) and h.group(1) == task_id
               and not HEADER.match(l) and j > after]
    if headers:
        gaps.append(("the REPORT blocks", result.unparsed(
            [(task_rel, n) for n in headers], len(headers), f"REPORT lines naming {task_id} "
            "after the block read", "`REPORT <role> T-n[.S-m]`",
            "a later report may have been passed over (F-34)"), False))
    if parsed is None:
        add("no-report", "no REPORT block in the execution record")
        return outcome()

    _role, reported_task, reported_step, fields = parsed
    # The field parse stops at the first line it cannot read (F-88). A field
    # of this block's grammar that it had not yet read, at or after that
    # point and before the block's end, was offered and never read.
    if where.get("stop") is not None:
        rest = []
        for j in range(where["stop"], len(lines)):
            if HEADER.match(lines[j]) or HEADER_ISH.match(lines[j]) or lines[j].startswith("#"):
                break
            k = KEY_ISH.match(lines[j])
            if k and k.group(1) not in fields:
                rest.append(j + 1)
        if rest:
            gaps.append(("the REPORT block", f"{task_rel}:{where['stop'] + 1} does not parse as "
                         f"`<key>: <value>` or an indented continuation, and {len(rest)} field "
                         f"line(s) from there on were not read ({result.anchors([(task_rel, n) for n in rest])}) "
                         "(F-88)", False))
    if len(fields.get("status") or []) > 1:
        gaps.append(("the report's status", result.wrapped(
            f"{task_rel}:{where['lines']['status'] + 1} `status:`", "check_report"), False))
    found = f"{reported_task}.{reported_step}" if reported_step else reported_task
    # Asking for a task and finding only one of its steps is a mid-flight
    # state, not a wrong report: the task has simply not reported yet, and the
    # step block is still worth checking on its own terms. Only a DIFFERENT
    # task, or a step other than the one asked for, is wrong.
    if reported_task != task_id or (step_id and reported_step != step_id):
        add("wrong-task", f"the last block reports {found}, not {want_id}")
    # A block that describes a STEP is not the task's own report. Comparing its
    # status to the task's title produced a spurious `status-mismatch` on every
    # mid-flight step verification, because a finished step sits under a
    # RUNNING task by definition.
    is_step = bool(reported_step)

    for key in REQUIRED:
        if key not in fields:
            add("missing-field", f"the block has no `{key}:`")

    status = (fields.get("status") or [""])[0].strip()
    if status and status not in STATUSES:
        add("bad-report-status", f"{status!r} is not one of {', '.join(STATUSES)}")
        # Everything below compares this status against the tree, which is
        # meaningless once it is not a status. One fault should produce one
        # finding: cascading consequences make a report harder to triage than
        # the defect that caused them.
        status = ""

    if status in CLOSING:
        # ACCEPTED reconciles a disagreement rather than asserting agreement,
        # so it is compatible with any report status -- including the `RED` or
        # `NEEDS-DECISION` that made the client's decision necessary.
        if (not is_step and title_status
                and not title_status.startswith(("DONE", "READY-TO-AUDIT", "ACCEPTED"))):
            add("status-mismatch", f"status {status} but the title says {title_status!r}")
        checks = [c for c in fields.get("checks", []) if c.strip() and c.strip() != "none"]
        if not checks:
            add("no-evidence", f"status {status} with no `checks:` lines — "
                               "a requirement is discharged by evidence, never by assertion")
    elif status and not is_step and title_status and title_status.startswith("DONE"):
        add("status-mismatch", f"status {status} but the title says {title_status!r}")
    # The comparison above needs the title, and a title that does not parse
    # left it silently unmade (L-1.3).
    if status and not is_step and title_status is None:
        offered = [n for n, l in enumerate(lines, 1) if TITLE_ISH.match(l)]
        gaps.append(("status-mismatch", (
            f"{task_rel}:{offered[0]} does not parse as `# T-n — <title> — <status>`"
            if offered else f"{task_rel} has no title line")
            + ", so the report's status was compared against no title", False))

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
    rc, log = git(repo, "log", "--format=%s", "--all")
    subjects = set(log.split("\n")) if rc == 0 else set()
    # Only a line that STARTS a list item is a commit; anything else is a
    # continuation of the one above it.
    for line in fields.get("commits", []):
        if not line.strip().startswith("- "):
            continue
        text = line.strip()[2:].strip()
        if not text or text == "none":
            continue
        m = HASH.match("- " + text)
        ref = m.group(1) if m else None
        if ref and ref != "HEAD":            # a hash, or HEAD~1 / HEAD^
            rc, _ = git(repo, "cat-file", "-e", f"{ref}^{{commit}}")
            if rc != 0:
                add("unknown-commit", f"{ref} is not a commit in this repository")
            continue
        # `HEAD <subject>` names the commit this block is committed in -- its
        # own hash cannot appear inside it, so the SUBJECT is what makes it
        # resolvable afterwards. Validate that, not the marker.
        subject = text[len(ref):].strip() if ref else text
        if subject and subject not in subjects:
            add("unknown-commit", f"no commit has the subject {subject[:60]!r}")

    if status in CLOSING and not is_step:
        # Only paths the TASK controls. A supervisor owns its declared scope and
        # its own task file, and nothing else -- so measuring the whole tree
        # made a clean close unreachable from inside the task whenever the
        # manager happened to have an uncommitted file of its own. That is a
        # check nobody can satisfy, which is a check that gets ignored (P-35).
        unread = []
        scope = task_scope(devteam, task_id, unread) + [f"devteam/tasks/{task_id}.md"]
        if unread:
            gaps.append(("dirty-tree and unfinished-scope", f"{len(unread)} list item(s) "
                         "under Scope. do not parse as a path, so neither class looked at "
                         f"what they name ({result.anchors([(f'tasks/{task_id}.md', n) for n in unread])})",
                         False))
        rc, paths = status_paths(repo)
        if rc == 0 and paths:
            mine = [p for p in paths
                    if any(p == s.rstrip("/") or p.startswith(s.rstrip("/") + "/")
                           for s in scope)]
            if mine:
                add("dirty-tree", f"uncommitted inside {task_id}'s scope on status "
                                  f"{status}: {', '.join(mine[:4])}")
        # A TASK DOES NOT CLOSE WITH A STUB IN ITS DECLARED SCOPE.
        for rel, n, marker in stub_markers(repo, task_scope(devteam, task_id))[:8]:
            add("unfinished-scope",
                f"{rel}:{n} carries {marker!r} while {task_id} reports {status}. "
                "A tests-first step leaves a stub on purpose; a closing task has "
                "no business still holding one. Remove it, or the task is not "
                "the thing the report says it is")

        # The task's OWN closing commit, not HEAD. Checking HEAD made every
        # finished task report `head-subject` the moment any later task
        # committed -- so an audit run afterwards saw a false positive against
        # every historical task. What the rule means is "this task committed
        # something that names it", and that stays true forever.
        rc, log = git(repo, "log", "--format=%s", "--all")
        if rc == 0 and not any(l.strip().lower().startswith(task_id.lower())
                               for l in log.split("\n")):
            add("head-subject", f"no commit's subject begins with {task_id}")

    containment, bad_row = charter_containment(devteam)
    if bad_row:
        gaps.append(("the charter's Containment row", f"CHARTER.md:{bad_row} does not parse "
                     "as `| Containment | structural or guard-only |`, so it declared no "
                     "exclusion", False))
    harness, missing = (None, None) if containment == "guard-only" else harness_budget(repo, task_id)
    if containment == "guard-only":
        excluded.append(("budget-mismatch and model-mismatch",
                         "the charter's `Containment: guard-only`, which has no harness meter"))
    elif harness is None:
        gaps.append(("budget-mismatch", missing, True))
        gaps.append(("model-mismatch", missing, False))
    if harness:
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
        one = lambda k: " ".join(fields.get(k) or []).strip()
        want_model = one("model")
        got_model = (harness.get("model") or "").strip()
        if want_model and got_model and want_model != got_model:
            add("model-mismatch",
                f"the report says `model: {want_model}` and the harness "
                f"dispatched {got_model}")
        # Tokens get 10% and minutes 20%, because the worker is estimating a
        # number it genuinely cannot read, and a tolerance tight enough to fire
        # on honest rounding is one that gets ignored.
        unreadable = []
        for field, tol, scale in (("tokens", 0.10, 1), ("minutes", 0.20, 1)):
            claimed = report_budget(one("budget"), field)
            actual = harness.get(field)
            if claimed is None and actual:
                # The harness has a figure and the report gives none this can
                # read: F-32's hedged `tokens=~N`, or no figure at all. The
                # comparison was not made, and that used to read as clean
                # (L-1.3). Reading `~N` as approximate is 0.3.2's.
                said = re.search(rf"\b{field}\s*=\s*(\S+)", one("budget"))
                unreadable.append(f"{field} as `{said.group(1)}`, which is not a number"
                                  if said else f"no {field}= figure")
            if claimed is None or not actual:
                continue
            if abs(claimed - actual) > tol * abs(actual):
                add("budget-mismatch",
                    f"the report says {field}={claimed:g} and the harness "
                    f"metered {actual:g} ({tol:.0%} tolerance)")
        if unreadable:
            gaps.append(("budget-mismatch", f"the report's `budget:` gives "
                         f"{' and '.join(unreadable)}, so it was not compared with "
                         "the harness's figure (F-32)", True))

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
    findings, gaps, excluded = got
    res = result.Result("check_report", task_id, width=18)
    res.blocking_only = blocking_only
    anchor = f"tasks/{task_id.partition('.')[0]}.md"
    for kind, detail in findings:
        res.finding(kind, anchor, detail, advisory=kind in ADVISORY)
    for part, reason, advisory in gaps:
        res.gap(part, reason, advisory)
    for part, declaration in excluded:
        res.exclude(part, declaration)
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
