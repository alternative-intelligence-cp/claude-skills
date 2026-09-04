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
  unreachable-acceptance a requirement whose `Requires-write.` set is not contained
                         in the `Scope.` of any single task that discharges it.
                         The task can make the BEHAVIOUR true and cannot make
                         the SENTENCE true, because the criterion needs a
                         write to something the task does not own

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
# The hyphen is required: `Requires-write.` parsed as no field at all under
# `[A-Za-z ]`, so `missing-field` fired on every requirement that HAD it --
# a check reporting the absence of the thing in front of it.
FIELD = re.compile(r"^-\s+\*\*([A-Za-z][A-Za-z -]*)\.\*\*\s*(.*)$")
IDS = re.compile(r"\b([GRT]-\d+)\b")

# A value the interview has not filled in yet. Reported as its own finding
# rather than silently treated as present -- a placeholder that passes a check
# is worse than one that fails it.
PLACEHOLDER = re.compile(r"^\s*(<[^>]*>|_none yet_|tbd|todo|\.\.\.)?\s*$", re.I)

REQ_FIELDS = ("Statement", "Satisfies", "Source", "Acceptance", "Requires-write",
              "Priority", "Status")
TASK_FIELDS = ("Discharges", "Depends on", "Scope", "Gate", "Verify")

STRUCK = re.compile(r"^struck\b", re.I)



# A path list is written ONE WAY everywhere: the field, then indented backticked
# items under it. `Scope.` on a task and `Requires-write.` on a requirement are the
# same shape deliberately -- this project has already paid for a record with two
# grammars for one thing, where an author used one, forgot the other, and shipped
# a red tree that cost somebody else's agents time.
LIST_FIELD = re.compile(r"^-\s+\*\*(Scope|Requires-write)\.\*\*\s*(.*)$")
LIST_ITEM = re.compile(r"^\s+-\s+`?([^`\s]+)`?\s*$")
NEXT_FIELD = re.compile(r"^-\s+\*\*[A-Za-z]|^#")


def path_lists(lines):
    """{field name: [entries]} for every `Scope.`/`Requires-write.` list in a block."""
    out, collecting = {}, None
    for line in lines:
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


def check(devteam):
    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))

    goals, reqs, tasks = {}, {}, {}

    for n, line in enumerate(read(devteam, "CHARTER.md"), 1):
        m = GOAL.match(line)
        if m:
            goals[m.group(1)] = f"CHARTER.md:{n}"

    req_lines = read(devteam, "REQUIREMENTS.md")
    must_write = {k: path_lists(v).get("Requires-write", [])
                 for k, v in blocks_of(req_lines, REQ).items()}
    for ident, n, _, fields in parse_blocks(req_lines, REQ, REQ_FIELDS):
        reqs[ident] = (f"REQUIREMENTS.md:{n}", fields)
        for f in REQ_FIELDS:
            if f not in fields:
                add("missing-field", f"REQUIREMENTS.md:{n}", f"{ident} has no **{f}.**")

    task_files = tracked(devteam, "tasks/*.md")
    if task_files is None:
        return None
    scopes = {}
    for rel in task_files:
        lines = read(devteam, rel)
        for k, v in blocks_of(lines, TASK).items():
            scopes[k] = path_lists(v).get("Scope", [])
        parsed_any = False
        for ident, n, extra, fields in parse_blocks(lines, TASK, TASK_FIELDS):
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
