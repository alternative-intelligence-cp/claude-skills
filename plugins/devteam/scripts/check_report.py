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
CLOSING = ("DONE", "READY-TO-AUDIT")

DASH = r"[—–-]"
HEADER = re.compile(r"^REPORT\s+(\S+)\s+(T-\d+)(?:\.(S-\d+))?\s*$")
KEY = re.compile(r"^([a-z][a-z-]*):\s*(.*)$")
TITLE = re.compile(r"^#\s+(T-\d+)\s*" + DASH + r"\s*(.*?)\s*" + DASH + r"\s*(\S.*)$")
RECORD_HEADING = re.compile(r"^##\s+Execution record\s*$", re.I)
HASH = re.compile(r"^\s*-\s+([0-9a-f]{7,40}|HEAD)\b")


def git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, ""


def parse_report(lines):
    """The LAST REPORT block in the file, as (role, task, step, {key: value})."""
    starts = [i for i, l in enumerate(lines) if HEADER.match(l)]
    if not starts:
        return None
    i = starts[-1]
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


def check(project, task_id):
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

    parsed = parse_report(lines)
    if parsed is None:
        add("no-report", "no REPORT block in the execution record")
        return findings

    _role, reported_task, _step, fields = parsed
    if reported_task != task_id:
        add("wrong-task", f"the last block reports {reported_task}, not {task_id}")

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
        if title_status and not title_status.startswith(("DONE", "READY-TO-AUDIT")):
            add("status-mismatch", f"status {status} but the title says {title_status!r}")
        checks = [c for c in fields.get("checks", []) if c.strip() and c.strip() != "none"]
        if not checks:
            add("no-evidence", f"status {status} with no `checks:` lines — "
                               "a requirement is discharged by evidence, never by assertion")
    elif status and title_status and title_status.startswith("DONE"):
        add("status-mismatch", f"status {status} but the title says {title_status!r}")

    rc, _ = git(repo, "rev-parse", "--git-dir")
    if rc != 0:
        add("no-file", f"{repo} is not a git repository")
        return findings

    for line in fields.get("commits", []):
        m = HASH.match(line) or HASH.match("- " + line)
        if not m:
            continue
        ref = m.group(1)
        if ref == "HEAD":
            continue
        rc, _ = git(repo, "cat-file", "-e", f"{ref}^{{commit}}")
        if rc != 0:
            add("unknown-commit", f"{ref} is not a commit in this repository")

    if status in CLOSING:
        rc, out = git(repo, "status", "--porcelain")
        if rc == 0 and out:
            add("dirty-tree", f"{len(out.splitlines())} uncommitted path(s) on status {status}")
        rc, subject = git(repo, "log", "-1", "--format=%s")
        if rc == 0 and subject and task_id.lower() not in subject.lower():
            add("head-subject", f"HEAD is {subject!r}, which does not name {task_id}")

    return findings


def main(argv):
    if len(argv) < 3:
        print(__doc__.strip().split("Usage:")[-1].strip(), file=sys.stderr)
        return 2
    project, task_id = os.path.realpath(argv[1]), argv[2]
    if not re.fullmatch(r"T-\d+", task_id):
        print(f"check_report: {task_id!r} is not a task id", file=sys.stderr)
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
