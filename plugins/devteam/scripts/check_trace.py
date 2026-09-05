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
  gate-omits-decision    a decision a requirement's Statement or Acceptance
                         rests on, named in no discharging task's `Gate.`. A
                         gate narrower than its requirement can only fail in
                         the direction of shipping LESS, because the verifier
                         reads the gate and P-18 puts it last. Existential
                         over the discharging tasks, so partial discharge
                         cannot defeat it -- and inert on a project whose
                         requirements cite no decisions, which is a real limit
  re-litigated-requirement  a requirement whose Statement or Acceptance has
                         changed three or more times since it was written or
                         last shape-reviewed. Not a defect: a signal that it
                         may be enumerating cases where it should state a rule
  board-drift            the board's `State` for a task and that task's own
                         title disagree. The board is "live state, and the
                         lock", and it was the one artifact in `devteam/` that
                         no check read back
  one-sided-link         a requirement and a task that name each other only in
                         one direction. `Status.` names the task; `Discharges.`
                         names the requirements; nothing compared them, so a
                         scheduling decision could reach one artifact and not
                         the other
  template-drift         a charter missing a constraint row the CURRENT
                         template declares. Every other check here diffs the
                         project against itself; this one diffs it against the
                         plugin, so a project older than its plugin stops
                         silently lacking what the plugin has since learned.
                         Covers the charter's constraints and, through the
                         derived field lists, requirements and tasks. NOT the
                         board, decisions, questions, permissions or
                         checkpoints -- those templates are unmarked and their
                         drift is still invisible
  unrecorded-amendment   a requirement whose `Requires-write.` changed since it
                         was first committed, with no `Requires-write amended.`
                         naming the decision. The one list the checker's own
                         author could tune to make the check pass
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


PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = re.compile(r"<!--\s*example:begin\s*-->(.*?)<!--\s*example:end\s*-->", re.S)
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
    for block in EXAMPLE.findall(body):
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
REQ_FIELDS = tuple(template_names("REQUIREMENTS.md", "field") or
                   ("Statement", "Satisfies", "Source", "Acceptance",
                    "Requires-write", "Priority", "Status"))
TASK_FIELDS = tuple(n for n in (template_names("tasks/TASK.md", "field") or
                                ("Discharges", "Depends on", "Scope", "Gate", "Verify"))
                    if n != "Kind")
CHARTER_ROWS = template_names("CHARTER.md", "row") or []

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
    seen, prev, churn = {}, {}, {}
    for sha in (s for s in log.split("\n") if s.strip()):
        try:
            blob = subprocess.run(["git", "-C", devteam, "show", f"{sha}:./REQUIREMENTS.md"],
                                  capture_output=True, text=True, check=True).stdout
        except (subprocess.CalledProcessError, OSError):
            continue
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
    return seen, churn


BOARD_ROW = re.compile(r"^\|\s*(T-\d+)\s*\|.*\|\s*([^|]+?)\s*\|\s*$")
# What a board State and a task title may say about one task at one moment.
# Not an equality -- the two vocabularies are different by design, the board
# saying what a reader needs and the title saying what the task holds.
BOARD_PHASES = {
    "—": ("PLANNED",), "-": ("PLANNED",),
    "CLAIMED": ("RUNNING",),
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

    goals, reqs, tasks = {}, {}, {}

    charter = read(devteam, "CHARTER.md")
    for n, line in enumerate(charter, 1):
        m = GOAL.match(line)
        if m:
            goals[m.group(1)] = f"CHARTER.md:{n}"

    # THE CHARTER AGAINST THE TEMPLATE IT CAME FROM.
    have = {m.group(1).strip() for m in (TPL_ROW.match(l) for l in charter) if m}
    for row in CHARTER_ROWS:
        if row not in have:
            add("template-drift", "CHARTER.md",
                f"the charter has no `{row}` row, which the current template "
                "declares. A charter signed before the template gained a row "
                "never acquires it, and nothing else would ever say so")

    req_lines = read(devteam, "REQUIREMENTS.md")
    req_blocks = blocks_of(req_lines, REQ)
    must_write = {k: path_lists(v).get("Requires-write", [])
                  for k, v in req_blocks.items()}
    original, churn = first_declared(devteam) or (None, {})
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
