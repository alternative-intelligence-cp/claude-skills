#!/usr/bin/env python3
"""Traceability for a project's `devteam/` directory (P-4).

Walks the chain the charter promises -- goal -> requirement -> task ->
acceptance evidence -- and reports every place it breaks. This is the check
the whole design leans on, because the prior art it is drawn from records that
every hole it ever found was found by a check that diffs two lists, and none
of them by a test.

Findings:

  orphan-scope           a charter goal no requirement satisfies -- promised
                         to the client and owned by nobody
  uncovered-requirement  a requirement no task discharges
  unmotivated-task       a task discharging no requirement. Either scope creep,
                         or a requirement nobody wrote down. Both matter
  unverified-requirement a requirement with no runnable acceptance criterion.
                         It will be declared done by opinion (P-3, P-5)
  missing-field          a required field absent. Never defaulted: a default is
                         a decision nobody made
  unknown-reference      a Satisfies/Discharges/Depends-on naming something
                         that does not exist
  dependency-cycle       tasks that can never start, because they wait on
                         each other

Exit 0 clean, 1 findings, 2 could not run. Grammar: templates/FORMATS.md.
Control: test_check_trace.py (P-35).
"""
import os
import re
import subprocess
import sys

DASH = r"[—–-]"
# A title's separator is a dash SURROUNDED BY WHITESPACE. Neither greedy nor
# non-greedy matching on a bare dash works: non-greedy splits at the hyphen in
# "well-known", and greedy splits at the one inside "DONE (2026-09-03)". A
# hyphen inside a word or a date never has spaces around it; a separator always
# does.
SEP = r"(?:\s+[\u2014\u2013]\s+|\s+-\s+)"
GOAL = re.compile(r"^-\s+\*\*(G-\d+)\*\*\s*" + DASH)
REQ = re.compile(r"^###\s+(R-\d+)\s*" + DASH + r"\s*(.*)$")
TASK = re.compile(r"^#\s+(T-\d+)" + SEP + r"(.*?)" + SEP + r"(\S.*)$")
FIELD = re.compile(r"^-\s+\*\*([A-Za-z][A-Za-z ]*)\.\*\*\s*(.*)$")
IDS = re.compile(r"\b([GRT]-\d+)\b")

# A value the interview has not filled in yet. Reported as its own finding
# rather than silently treated as present -- a placeholder that passes a check
# is worse than one that fails it.
PLACEHOLDER = re.compile(r"^\s*(<[^>]*>|_none yet_|tbd|todo|\.\.\.)?\s*$", re.I)

REQ_FIELDS = ("Statement", "Satisfies", "Source", "Acceptance", "Priority", "Status")
TASK_FIELDS = ("Discharges", "Depends on", "Scope", "Gate", "Verify")

STRUCK = re.compile(r"^struck\b", re.I)


def tracked(root, pattern):
    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z", "--", pattern],
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [p for p in out.split("\0") if p]


def read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read().split("\n")
    except OSError:
        return []


def parse_blocks(lines, header, fields_for):
    """Yield (identifier, line-number, extra, {field: value}) per heading."""
    cur = None
    for n, line in enumerate(lines, 1):
        m = header.match(line)
        if m:
            if cur:
                yield cur
            cur = (m.group(1), n, m.groups()[1:], {})
            continue
        if cur:
            f = FIELD.match(line)
            if f:
                cur[3][f.group(1).strip()] = f.group(2).strip()
    if cur:
        yield cur


def check(devteam):
    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))

    goals, reqs, tasks = {}, {}, {}

    for n, line in enumerate(read(devteam, "CHARTER.md"), 1):
        m = GOAL.match(line)
        if m:
            goals[m.group(1)] = f"CHARTER.md:{n}"

    for ident, n, _, fields in parse_blocks(read(devteam, "REQUIREMENTS.md"), REQ, REQ_FIELDS):
        reqs[ident] = (f"REQUIREMENTS.md:{n}", fields)
        for f in REQ_FIELDS:
            if f not in fields:
                add("missing-field", f"REQUIREMENTS.md:{n}", f"{ident} has no **{f}.**")

    task_files = tracked(devteam, "tasks/*.md")
    if task_files is None:
        return None
    for rel in task_files:
        lines = read(devteam, rel)
        for ident, n, extra, fields in parse_blocks(lines, TASK, TASK_FIELDS):
            tasks[ident] = (f"{rel}:{n}", fields, extra[1] if len(extra) > 1 else "")
            for f in TASK_FIELDS:
                if f not in fields:
                    add("missing-field", f"{rel}:{n}", f"{ident} has no **{f}.**")

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
        if not names:
            add("unmotivated-task", where,
                f"{ident} discharges no requirement — scope creep, or a requirement nobody wrote down")
        for r in names:
            discharged.add(r)
            if r not in reqs:
                add("unknown-reference", where, f"{ident} discharges {r}, which no requirement declares")

    for ident, (where, fields) in sorted(reqs.items()):
        if STRUCK.match(fields.get("Status", "")):
            continue
        if ident not in discharged:
            add("uncovered-requirement", where, f"{ident} is not discharged by any task")
        acc = fields.get("Acceptance", "")
        if "Acceptance" in fields and PLACEHOLDER.match(acc):
            add("unverified-requirement", where,
                f"{ident} has no runnable acceptance criterion — it will be declared done by opinion")

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

    return findings, len(goals), len(reqs), len(tasks)


def resolve(target):
    target = os.path.realpath(target)
    if os.path.basename(target) != "devteam" and os.path.isdir(os.path.join(target, "devteam")):
        target = os.path.join(target, "devteam")
    return target


def main(argv):
    # Before planning, no task exists, so EVERY requirement is uncovered by
    # construction. Reporting that at the onboarding gate makes a clean run
    # impossible and leaves a manager choosing between ignoring the check and
    # inventing tasks. `--pre-plan` suppresses exactly that one class and
    # nothing else: orphan-scope, unverified-requirement, missing-field,
    # unknown-reference and dependency-cycle all still apply, and those are
    # the ones onboarding actually needs clean.
    pre_plan = "--pre-plan" in argv[1:]
    args = [a for a in argv[1:] if a != "--pre-plan"]
    total = 0
    for t in (args or ["."]):
        devteam = resolve(t)
        if not os.path.isdir(devteam):
            print(f"check_trace: not a directory: {devteam}", file=sys.stderr)
            return 2
        got = check(devteam)
        if got is None:
            print(f"check_trace: not a git repository: {devteam}", file=sys.stderr)
            return 2
        findings, ng, nr, nt = got
        if pre_plan:
            findings = [f for f in findings if f[0] != "uncovered-requirement"]
        label = os.path.relpath(devteam, os.getcwd())
        if findings:
            print(f"{label}: {len(findings)} finding(s)  [{ng} goals, {nr} requirements, {nt} tasks]")
            for kind, where, detail in sorted(findings):
                print(f"  {kind:22} {where}  {detail}")
            total += len(findings)
        else:
            print(f"{label}: clean  [{ng} goals, {nr} requirements, {nt} tasks traced end to end]")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
