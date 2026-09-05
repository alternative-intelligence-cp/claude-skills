#!/usr/bin/env python3
"""Verify a committed REPORT block against the tree it claims (P-16).

An agent's final message is a REPORT block, and the identical block is
committed as the last entry of its task file's execution record. One shape
means a script can check it; two places means the record cannot quietly
disagree with what was said. This is that script, and it runs before the
verifier does -- a malformed report is a re-dispatch, not a judgement call.

Findings:

  no-file           the task file does not exist
  no-report         no REPORT block under `## Execution record`
  wrong-task        the last block names a different task
  missing-field     a required key of the block is absent
  bad-report-status a status outside the six
  status-mismatch   the block's status and the task title disagree
  unknown-commit    a hash under `commits:` the repository does not have
  head-subject      HEAD's subject does not name this task on a closing status
  dirty-tree        uncommitted paths, on a status that claims to be finished
  unfinished-scope  a TODO, FIXME, XXX or `raise NotImplementedError` inside the
                    task's declared scope on a closing status. The pipeline
                    creates stubs deliberately in tests-first steps; a task
                    reporting DONE while one survives is reporting something
                    other than what it did
  no-evidence       a closing status with no `checks:` lines. A requirement is
                    discharged by evidence, never by assertion (P-5)

Usage:  check_report.py <project-or-devteam> <T-n>
Exit 0 clean, 1 findings, 2 could not run.  Control: test_check_report.py.
"""
import os
import re
import subprocess
import sys

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


def task_scope(devteam, task_id):
    """The paths a task declares it writes, relative to the project root."""
    try:
        lines = open(os.path.join(devteam, "tasks", f"{task_id}.md"),
                     encoding="utf-8", errors="replace").read().split("\n")
    except OSError:
        return []
    out, collecting = [], False
    for line in lines:
        if SCOPE_FIELD.match(line):
            collecting = True
            continue
        if collecting:
            m = SCOPE_ITEM.match(line)
            if m:
                out.append(m.group(1).strip("`"))
                continue
            if line.strip() and (ANY_FIELD.match(line) or line.startswith("#")):
                break
    return [p for p in out if p and "<" not in p]


def parse_report(lines, task_id=None, step_id=None):
    """The last REPORT block FOR THIS TASK, as (role, task, step, fields).

    Not simply the last block in the file. A supervisor's record holds its
    workers' step blocks (`T-n.S-m`) as well as its own task block (`T-n`),
    and taking the last one meant validating a worker's step report in place
    of the supervisor's -- so a supervisor could not satisfy P-16 and P-17 at
    once. Prefer the last block whose id is exactly the task, and fall back to
    the last block of any kind so a step report can still be checked directly.
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
    fields, key = {}, None
    for line in lines[i + 1:]:
        if HEADER.match(line) or line.startswith("#"):
            break
        k = KEY.match(line)
        if k:
            key = k.group(1)
            fields[key] = [k.group(2)] if k.group(2) else []
        elif key is not None and line.startswith((" ", "\t")) and line.strip():
            fields[key].append(line.strip())
        elif not line.strip():
            continue
        else:
            break
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

def check(project, want_id):
    """`want_id` is `T-n` or `T-n.S-m`. A step is checked as a step: it does
    not own the task's title line, so its status is never compared to it."""
    task_id, _, step_id = want_id.partition(".")
    step_id = step_id or None
    findings = []
    add = lambda kind, detail: findings.append((kind, detail))

    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    repo = os.path.dirname(devteam)
    path = os.path.join(devteam, "tasks", f"{task_id}.md")
    if not os.path.isfile(path):
        return [("no-file", os.path.relpath(path, repo))]

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

    parsed = parse_report(lines, task_id, step_id)
    if parsed is None:
        add("no-report", "no REPORT block in the execution record")
        return findings

    _role, reported_task, reported_step, fields = parsed
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

    rc, _ = git(repo, "rev-parse", "--git-dir")
    if rc != 0:
        add("no-file", f"{repo} is not a git repository")
        return findings

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
        scope = task_scope(devteam, task_id) + [f"devteam/tasks/{task_id}.md"]
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

    return findings


def main(argv):
    if len(argv) < 3:
        print(__doc__.strip().split("Usage:")[-1].strip(), file=sys.stderr)
        return 2
    project, task_id = os.path.realpath(argv[1]), argv[2]
    if not re.fullmatch(r"T-\d+(\.S-\d+)?", task_id):
        print(f"check_report: {task_id!r} is not a task or step id", file=sys.stderr)
        return 2
    findings = check(project, task_id)
    if findings:
        print(f"{task_id}: {len(findings)} finding(s)")
        for kind, detail in sorted(findings):
            print(f"  {kind:18} {detail}")
        return 1
    print(f"{task_id}: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
