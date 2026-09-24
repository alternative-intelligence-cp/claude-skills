#!/usr/bin/env python3
"""Scope integrity: the check that makes parallel work safe in one repository.

A task declares the paths it writes. Two tasks in flight must have disjoint
declared scopes (P-12), and a worker must stay inside its own (P-10). The prior
art this pipeline is drawn from avoided the problem by giving each stream a
whole repository; that is not available to a project with one repository, so
the scopes are declared and checked instead.

A task is LIVE when its own title line says RUNNING. That is the same source
of truth stale-claim recovery reads (P-14), so the two can never disagree --
which they could if this parsed the board's table separately.

The finding classes it emits, and the rule each enforces, are in
docs/CHECKS.md -- one home (P-34). This docstring deliberately does not
list them: it used to, and ten classes were emitted, controlled, and
absent from the lists here. `unruled-finding` in check_plugin.py keeps
docs/CHECKS.md and the code equal in both directions.

Usage:  check_scope.py <project> [T-n]
        no task id: pairwise overlap among every live task
        with one:   that too, plus what its commits actually touched
Exit 0 clean, 1 findings, 2 could not run, 3 not evaluated -- the contract is
result.py's (roadmap 0.3.1, L-1.1).  Control: test_check_scope.py.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)

DASH = r"[—–-]"
# A title's separator is a dash SURROUNDED BY WHITESPACE. Neither greedy nor
# non-greedy matching on a bare dash works: non-greedy splits at the hyphen in
# "well-known", and greedy splits at the one inside "DONE (2026-09-03)". A
# hyphen inside a word or a date never has spaces around it; a separator always
# does.
SEP = r"(?:\s+[\u2014\u2013]\s+|\s+-\s+)"
TITLE = re.compile(r"^#\s+(T-\d+)" + SEP + r"(.*?)" + SEP + r"(\S.*)$")
SCOPE_FIELD = re.compile(r"^-\s+\*\*Scope\.\*\*\s*(.*)$")
SCOPE_ITEM = re.compile(r"^\s+-\s+`?([^`\s]+)`?\s*$")
# A LIST ITEM UNDER `Scope.` THAT IS NOT A BARE PATH. It used to be skipped in
# silence, so a grant written as `` - `path` — because reasons `` declared
# nothing: the file said eleven entries and the checker parsed nine, and two
# paths a manager believed it had granted were mechanically outside the task's
# scope for its entire run. The supervisor read the resulting findings as
# checker false positives, which is the wrong direction -- the check was right,
# because a grant nobody can parse is a sentence a human believes and a machine
# never saw. This grammar failed PERMISSIVELY, which is why it went unnoticed
# where a strike-through and a forward citation failed loudly and did not.
SCOPE_ITEMISH = re.compile(r"^\s+-\s+\S")
ANY_FIELD = re.compile(r"^-\s+\*\*[A-Za-z]")
PLACEHOLDER = re.compile(r"[<>]")


def git(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return p.returncode, p.stdout


# What a task file OFFERS (roadmap 0.3.1, L-1.3). A title-shaped line that
# TITLE rejects -- a step's heading in an execution record is prose, not one.
TITLE_ISH = re.compile(r"^#\s*T-?\s*\d+\b(?![.'’])")


def load_tasks(devteam, gaps=None):
    """({T-n: (relpath, status, [scope entries])}, unparsed items, untracked
    files) for every task file git would show -- tracked, or untracked and not
    ignored (roadmap 0.3.1, L-1.4). It read the index alone, so a new task was
    in no comparison until it was staged (F-131).

    `gaps`, when given, collects (part, reason) for what a file offered and
    this did not read: a task whose title does not parse -- it was dropped
    from every comparison in silence, and a RUNNING one with it, so an
    overlap with it could not be seen -- and an inline `Scope.` value that
    continues past its line.
    """
    listing = result.listed(devteam, "tasks/*.md")
    if listing is None:
        return None
    every, untracked = listing
    tasks, unparsed = {}, []
    for rel in every:
        try:
            with open(os.path.join(devteam, rel), encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue
        ident = status = None
        scope, collecting = [], False
        for n, line in enumerate(lines, 1):
            m = TITLE.match(line)
            if m and ident is None:
                ident, status = m.group(1), m.group(3).strip()
                continue
            if SCOPE_FIELD.match(line):
                collecting = True
                inline = SCOPE_FIELD.match(line).group(1).strip()
                if inline and not PLACEHOLDER.search(inline):
                    scope.append(inline.strip("`"))
                    # An inline value is one entry; a line continuing it that
                    # is not a list item was never read.
                    more = [j for j in result.continuation(lines, n - 1)
                            if not SCOPE_ITEMISH.match(lines[j])]
                    if more and gaps is not None:
                        gaps.append((f"{rel}'s Scope.", result.wrapped(
                            f"{rel}:{n}", "check_scope")))
                continue
            if collecting:
                item = SCOPE_ITEM.match(line)
                if item:
                    scope.append(item.group(1))
                    continue
                if SCOPE_ITEMISH.match(line):
                    unparsed.append((rel, n, line.strip()))
                    continue
                if line.strip() and (ANY_FIELD.match(line) or line.startswith("#")):
                    collecting = False
        if ident:
            tasks[ident] = (rel, status or "", scope)
        elif gaps is not None:
            offered = [n for n, line in enumerate(lines, 1) if TITLE_ISH.match(line)]
            if offered or os.path.basename(rel).startswith("T-"):
                gaps.append((f"{rel}'s title", (
                    f"{rel}:{offered[0]} does not parse as `# T-n — <title> — <status>`"
                    if offered else f"{rel} has no title line")
                    + ", so its scope and state were in no comparison"))
    return tasks, unparsed, untracked


def normalise(entry):
    """A scope entry as a clean relative prefix.

    None -> not a scope (blank, or an unfilled placeholder).
    False -> it escapes the project root, which is a finding.

    The escape test runs BEFORE any stripping, because `lstrip("./")` strips a
    character SET rather than a prefix: it turned `../sibling/` into
    `sibling/` and silently disarmed this check. The control caught it.
    """
    e = entry.strip().strip("`").strip()
    if not e or PLACEHOLDER.search(e):
        return None
    if os.path.isabs(e) or e.startswith("~"):
        return False
    if e.startswith("./"):
        e = e[2:]
    if ".." in e.split("/"):
        return False
    if not e or e == ".":
        return None
    return e.rstrip("/") + ("/" if e.endswith("/") else "")


def covers(scope, path):
    for entry in scope:
        e = entry.rstrip("/")
        if path == e or path.startswith(e + "/"):
            return True
    return False


def intersects(a, b):
    for x in a:
        for y in b:
            x, y = x.rstrip("/"), y.rstrip("/")
            if x == y or x.startswith(y + "/") or y.startswith(x + "/"):
                return (x, y)
    return None


def check(project, task_id=None):
    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    repo = os.path.dirname(devteam)
    if not os.path.isdir(devteam):
        return None
    gaps = []  # (part, reason): parts not evaluated (roadmap 0.3.1, L-1.3)
    loaded = load_tasks(devteam, gaps)
    if loaded is None:
        return None
    tasks, unparsed, untracked = loaded

    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))

    for rel in sorted(untracked):
        add("untracked-file", rel, result.UNTRACKED)

    for rel, n, text in unparsed:
        add("unparseable-scope-entry", f"{rel}:{n}",
            f"{text!r} is a list item under `Scope.` that does not parse as a "
            "path, so it declares nothing. A grant the checker cannot read is "
            "not a grant: the file says one thing and every scope check sees "
            "another. Put the reason on its own line or after the list")

    clean = {}
    for ident, (rel, status, scope) in sorted(tasks.items()):
        entries, escaped = [], False
        for raw in scope:
            n = normalise(raw)
            if n is False:
                escaped = True
                add("scope-escapes-tree", rel, f"{ident} declares {raw!r}, which leaves the project root")
            elif n:
                entries.append(n)
        clean[ident] = entries
        # A scope emptied by rejecting its entries is already reported as the
        # rejection. Reporting it again as `empty-scope` turns one fault into
        # two findings and buries the cause under its consequence.
        if not entries and not escaped and not status.startswith(("PLANNED", "DONE")):
            add("empty-scope", rel, f"{ident} is {status.split()[0]} and declares no scope")

    live = [t for t, (_, s, _) in tasks.items() if s.startswith("RUNNING")]

    # A WRITE BY SOMEBODY WHO IS NOT IN THIS RUN.
    #
    # The guard used to refuse every write into this tree by any session while
    # a claim was live. That over-reached -- it made a repository with an owner
    # unusable, and a real team declined the pipeline over it -- so the guard
    # now polices only this run's own agents. The protection was traded for
    # composability, and this is what replaces it: not a refusal, which was
    # never ours to make, but a finding the manager can see.
    #
    # A peer asked the question that produced this, and it is the right one to
    # ask of any mitigation offered for a removed control: does verification
    # look where the NEW gap is, or where the old one was? It did not. The
    # answer given -- "the manager finds it at verification" -- was false when
    # it was written: `undeclared-write` inspects a TASK'S OWN commits, and
    # `dirty-tree` is scoped to the task's own paths, so a stranger's writes
    # were examined by nothing at all.
    #
    # Coverage now, stated exactly, because a half-covered check that sounds
    # whole is the thing this project keeps finding:
    #   - a stranger's COMMIT touching a live scope -- already caught, as
    #     `misattributed-write`, since its subject names no task;
    #   - a stranger's UNCOMMITTED write, anywhere outside every live scope --
    #     caught here;
    #   - a stranger's COMMIT outside every live scope -- NOT CAUGHT. It
    #     touches nothing any task claims and names no task, so nothing in the
    #     run has a reason to look at it. Naming this rather than implying it
    #     is covered is the whole point of the paragraph.
    #
    # `devteam/` is excluded because it has its own rule: it is the run itself,
    # the guard still refuses a stranger's write into it, and the board is
    # deliberately always writable.
    if live:
        union = [e for ident in live for e in clean.get(ident, [])]
        # `-uall`, NOT the default. Plain `--porcelain` collapses an
        # untracked directory to its shortest prefix, so a worker creating
        # `src/loader/new/x.py` in a tree where nothing under `src/` is tracked
        # yet gets reported as `src/` -- which no scope covers, so the check
        # accuses the run's own worker of being a stranger. Caught by a
        # false-positive control on the first run, which is the only reason
        # this is a comment rather than a defect.
        rc, out = git(repo, "status", "--porcelain", "-uall")
        if rc == 0:
            for line in out.split("\n"):
                # The status code is two columns wide and a leading space is
                # part of it, so the path starts at column 3 and must not be
                # lstripped off the code.
                if len(line) < 4:
                    continue
                path = line[3:].strip().split(" -> ")[-1].strip('"')
                if not path or path == "devteam" or path.startswith("devteam/"):
                    continue
                if covers(union, path):
                    continue
                add("foreign-write", "BOARD.md",
                    f"{path} is modified and lies outside every live scope "
                    f"({', '.join(live)}). No agent of this run should have "
                    "written it, and the guard no longer refuses a session "
                    "that is not part of the run")

    # A commit touching a LIVE task's scope whose subject does not name that
    # task took the work away from it. The manager is the one party guaranteed
    # to be writing concurrently with every worker, and `git add -A` is what
    # anyone types by reflex -- so a worker's in-flight file lands in the
    # manager's commit under the manager's message. The step loses its commit,
    # scope attribution inverts (a write belonging to no task is invisible to
    # the undeclared-write check), and the record says one thing while
    # containing another. Only commits since the claim are considered, so the
    # scaffold and earlier tasks are not charged to it.
    for ident in live:
        # THE CLAIM IS A COMMIT ON THE BOARD (P-11), so read it from there.
        #
        # This previously took the NEWEST `git log -S "RUNNING (since"` match on
        # the task file. Any commit quoting that phrase became the anchor and
        # collapsed the span to nothing — so a commit DESCRIBING this bug
        # switched the check off, and the live finding disappeared. An
        # integrity check disabled by writing about it is the worst failure
        # available to one, because the act of documenting it is the act of
        # hiding it.
        #
        # `board: claim T-n` is the subject the run skill mandates and the
        # board's history is the designed record of who claimed what and when.
        # Prose cannot forge it: a commit merely mentioning the phrase does not
        # carry that subject.
        # The OLDEST claim, and any claim-shaped verb.
        #
        # Two defects, both found in one run. Taking the NEWEST claim left a
        # permanent blind spot: a write made while a task was BLOCKED was not
        # live, so nothing flagged it — and a later re-claim moved the anchor
        # past it, so nothing ever could. The write was never live-and-in-window
        # at any single moment, which is worse than F-19's erased findings.
        # These are findings that never existed.
        #
        # And `board: re-claim T-1` did not match a pattern expecting `claim`,
        # so a real anchor was missed entirely. Commits belonging to other
        # tasks are skipped by subject anyway, so widening the window to the
        # first claim costs nothing and closes the hole.
        # The window opens when the task FIRST EXISTED, not when a board commit
        # happened to be made. Anchoring on the first board claim still left the
        # blind spot whenever the only claim commit came late: a write before it
        # sat outside the window and nothing could ever flag it.
        #
        # Take the oldest of every candidate — board claim commits in any
        # claim-shaped spelling, and the first appearance of a RUNNING title in
        # the task file — because a commit that wrote into this task's scope
        # without naming it is misattributed regardless of which claim period
        # it landed in. Commits belonging to other tasks are skipped by subject,
        # so a wide window costs nothing.
        candidates = []
        rc, out = git(repo, "log", "--reverse", "--format=%H%x00%s", "--", "devteam/BOARD.md")
        for line in out.strip().split("\n"):
            if "\0" not in line:
                continue
            sha, subject = line.split("\0", 1)
            if re.match(rf"^board:\s*(?:re-?)?claims?\s+{re.escape(ident)}\b",
                        subject.strip(), re.I):
                candidates.append(sha)
                break
        rc, out = git(repo, "log", "--reverse", "-S", "RUNNING (since",
                      "--format=%H", "--", f"devteam/tasks/{ident}.md")
        if rc == 0 and out.split():
            candidates.append(out.split()[0])
        claim = None
        if candidates:
            # Oldest wins: `git log` lists newest first, so the last of the
            # candidates to appear in that listing is the earliest commit.
            rc, order = git(repo, "log", "--format=%H")
            seq = order.split()
            claim = max(candidates, key=lambda s: seq.index(s) if s in seq else -1)
        if not claim:
            # A LIVE TASK WITH NO WINDOW. Nothing anchors where its claim
            # began, so no commit was asked whether it wrote into this scope
            # under another name -- which used to read as clean (L-1.3).
            gaps.append((f"misattributed-write for {ident}", f"{ident} is RUNNING and "
                         f"no `board: claim {ident}` commit or RUNNING title in "
                         "history anchors its window"))
            continue
        # Strictly AFTER the claim. The claim commit itself creates or marks the
        # task file, so including it charged the task with its own creation.
        rc, out = git(repo, "log", f"{claim}..HEAD", "--format=%H%x00%s")
        for line in out.strip().split("\n"):
            if "\0" not in line:
                continue
            sha, subject = line.split("\0", 1)
            # Only commits belonging to NO task. A commit named `T-n:` that
            # wrote outside its own scope is already `undeclared-write`, and
            # reporting the same event twice under two names buries the cause.
            if any(re.match(rf"^{re.escape(other)}(\.S-\d+)?\s*:", subject)
                   for other in tasks):
                continue
            rc2, files = git(repo, "show", "--name-only", "--format=", sha)
            for path in (f for f in files.split("\n") if f.strip()):
                if path.startswith("devteam/") and path != f"devteam/tasks/{ident}.md":
                    continue                      # the manager's own artifacts
                # A task's own file is implicitly its own to write, and it is
                # never in the DECLARED scope — so routing it past the skip and
                # then testing it against that scope meant the carve-out could
                # not fire at all, and a manager sweeping a supervisor's task
                # file went unreported.
                own_file = path == f"devteam/tasks/{ident}.md"
                if own_file or covers(clean[ident], path):
                    # THE TASK FILE HAS A STRUCTURAL CAUSE THE GENERIC REMEDY
                    # DOES NOT FIT. A worker appending its REPORT must commit
                    # the task file, and `git commit -- <path>` takes file
                    # CONTENT rather than hunks -- so anything the manager left
                    # uncommitted there rides along under the worker's subject.
                    # Interactive staging is outside the grant, so no move
                    # available to the worker avoids it, and telling it to
                    # "stage explicit paths" describes what it already did.
                    remedy = ("The manager must commit its edits to this file "
                              "BEFORE dispatching: a worker appending its "
                              "REPORT commits the whole file, `git commit -- "
                              "<path>` takes content and not hunks, and no "
                              "move available to the worker avoids that"
                              ) if own_file else (
                              "Stage explicit paths; never `git add -A` while "
                              "a claim is live")
                    add("misattributed-write", tasks[ident][0],
                        f"{sha[:7]} {subject[:44]!r} committed {path}, which is "
                        f"inside {ident}'s live scope. {remedy}")
                    break
    for i, a in enumerate(sorted(live)):
        for b in sorted(live)[i + 1:]:
            hit = intersects(clean[a], clean[b])
            if hit:
                add("overlapping-scope", tasks[a][0],
                    f"{a} and {b} are both RUNNING and their scopes intersect at "
                    f"{hit[0]!r} / {hit[1]!r}")

    if task_id:
        # `T-n` or `T-n.S-m`. A step inherits its task's declared scope, so a
        # verifier judging one step has the same check available as one
        # judging the whole task.
        base, _, step = task_id.partition(".")
        if base not in tasks:
            # AN ARGUMENT THAT NAMES NO TASK IS COULD-NOT-RUN (L-1.1). This
            # returned a bare list where the caller unpacks a triple, so it
            # ended in a traceback; and `no-file` was never a class this check
            # has a rule for.
            return ("no task", f"{task_id!r} names no tracked tasks/{base}.md "
                    "whose title parses")
        # Attribute by SUBJECT PREFIX, not by grepping the whole message.
        # `--grep T-1` also matched the manager's own `board: claim T-1` and
        # `plan: T-1 and T-2` commits and charged their paths to the task, so
        # a supervisor could never close a task cleanly through no fault of
        # its own -- found the first time this ran against a real dispatch.
        # The work skill mandates the subject form `T-n:` / `T-n.S-m:`, so the
        # prefix is exactly the set of commits the task actually made.
        rc, out = git(repo, "log", "--format=%H%x00%s", "--all")
        prefix = re.compile(rf"^{re.escape(task_id)}\s*:" if step
                            else rf"^{re.escape(base)}(\.S-\d+)?\s*:")
        shas = [line.split("\0", 1)[0] for line in out.strip().split("\n")
                if "\0" in line and prefix.match(line.split("\0", 1)[1])]
        # A STEP-SHAPED subject missing its colon -- `T-3.S-2 fix` -- is a
        # worker's commit this attribution did not read, so what it wrote was
        # checked against nothing (L-1.3). A bare `T-3 <words>` is NOT offered:
        # it is the manager's topic commit, which the prefix exists to leave
        # out, and pricelog's five such subjects are all the manager's
        # (`T-10 DONE, verified PASS -- …`), measured as false gaps.
        loose = re.compile(rf"^{re.escape(base)}\.S-\d+\b")
        stray = [line.split("\0", 1)[0][:7] for line in out.strip().split("\n")
                 if "\0" in line and loose.match(line.split("\0", 1)[1])
                 and not prefix.match(line.split("\0", 1)[1])
                 and (not step or re.match(rf"^{re.escape(task_id)}(?!\d)",
                                           line.split("\0", 1)[1]))]
        if stray:
            gaps.append((f"undeclared-write for {task_id}", f"{len(stray)} commit(s) "
                         f"are subjected `{base}.S-m` without the colon, so what they "
                         f"wrote was not attributed to {task_id} ({', '.join(stray)})"))
        allowed = clean[base] + [f"devteam/tasks/{base}.md"]
        seen = set()
        for sha in shas:
            rc, files = git(repo, "show", "--name-only", "--format=", sha)
            for path in (p for p in files.split("\n") if p.strip()):
                if path in seen or covers(allowed, path):
                    continue
                seen.add(path)
                add("undeclared-write", tasks[base][0],
                    f"{task_id} committed {path}, which its scope does not cover")
    return findings, gaps, len(tasks), len(live)


def main(argv):
    as_json, argv = result.flag(list(argv), "--json")
    if len(argv) < 2:
        return result.could_not_run("check_scope", "usage: check_scope.py <project> [T-n] [--json]", as_json)
    task_id = argv[2] if len(argv) > 2 else None
    if task_id and not re.fullmatch(r"T-\d+(\.S-\d+)?", task_id):
        return result.could_not_run("check_scope", f"{task_id!r} is not a task or step id", as_json)
    got = check(os.path.realpath(argv[1]), task_id)
    if got is None:
        return result.could_not_run("check_scope", "not a devteam project, or not a git repository", as_json)
    if got[0] == "no task":
        return result.could_not_run("check_scope", got[1], as_json)
    findings, gaps, ntasks, nlive = got
    res = result.Result("check_scope", "scopes" + (f" for {task_id}" if task_id else ""), width=20)
    for kind, where, detail in findings:
        res.finding(kind, where, detail)
    for part, reason in gaps:
        res.gap(part, reason)
    # The live count is the denominator RECORD.md:86 asked for: "a check that is
    # silent because nothing is running looks identical to a check that is
    # silent because nothing is wrong". With it on the line, they do not.
    res.count(ntasks, "tasks")
    res.count(nlive, "live")
    return result.emit([res], as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
