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

Findings:

  overlapping-scope   two live tasks whose declared scopes intersect. Checked
                      BEFORE dispatch, never discovered afterwards
  undeclared-write    a task's commits touched a path outside its scope
  empty-scope         a task declares no scope and so cannot be claimed safely
  scope-escapes-tree  a scope entry that leaves the project root

Usage:  check_scope.py <project> [T-n]
        no task id: pairwise overlap among every live task
        with one:   that too, plus what its commits actually touched
Exit 0 clean, 1 findings, 2 could not run.  Control: test_check_scope.py.
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
TITLE = re.compile(r"^#\s+(T-\d+)" + SEP + r"(.*?)" + SEP + r"(\S.*)$")
SCOPE_FIELD = re.compile(r"^-\s+\*\*Scope\.\*\*\s*(.*)$")
SCOPE_ITEM = re.compile(r"^\s+-\s+`?([^`\s]+)`?\s*$")
ANY_FIELD = re.compile(r"^-\s+\*\*[A-Za-z]")
PLACEHOLDER = re.compile(r"[<>]")


def git(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def load_tasks(devteam):
    """{T-n: (relpath, status, [scope entries])} for every tracked task file."""
    rc, out = git(devteam, "ls-files", "-z", "--", "tasks/*.md")
    if rc != 0:
        return None
    tasks = {}
    for rel in (p for p in out.split("\0") if p):
        try:
            with open(os.path.join(devteam, rel), encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue
        ident = status = None
        scope, collecting = [], False
        for line in lines:
            m = TITLE.match(line)
            if m and ident is None:
                ident, status = m.group(1), m.group(3).strip()
                continue
            if SCOPE_FIELD.match(line):
                collecting = True
                inline = SCOPE_FIELD.match(line).group(1).strip()
                if inline and not PLACEHOLDER.search(inline):
                    scope.append(inline.strip("`"))
                continue
            if collecting:
                item = SCOPE_ITEM.match(line)
                if item:
                    scope.append(item.group(1))
                    continue
                if line.strip() and (ANY_FIELD.match(line) or line.startswith("#")):
                    collecting = False
        if ident:
            tasks[ident] = (rel, status or "", scope)
    return tasks


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
    tasks = load_tasks(devteam)
    if tasks is None:
        return None

    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))

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
                    add("misattributed-write", tasks[ident][0],
                        f"{sha[:7]} {subject[:44]!r} committed {path}, which is "
                        f"inside {ident}'s live scope. Stage explicit paths; "
                        f"never `git add -A` while a claim is live")
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
            return [("no-file", f"tasks/{base}.md", "no such task")]
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
    return findings


def main(argv):
    if len(argv) < 2:
        print("usage: check_scope.py <project> [T-n]", file=sys.stderr)
        return 2
    task_id = argv[2] if len(argv) > 2 else None
    if task_id and not re.fullmatch(r"T-\d+(\.S-\d+)?", task_id):
        print(f"check_scope: {task_id!r} is not a task or step id", file=sys.stderr)
        return 2
    findings = check(os.path.realpath(argv[1]), task_id)
    if findings is None:
        print("check_scope: not a devteam project, or not a git repository", file=sys.stderr)
        return 2
    if findings:
        print(f"{len(findings)} finding(s)")
        for kind, where, detail in sorted(findings):
            print(f"  {kind:20} {where}  {detail}")
        return 1
    print("scopes clean" + (f" for {task_id}" if task_id else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
