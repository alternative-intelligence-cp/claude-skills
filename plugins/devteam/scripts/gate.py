#!/usr/bin/env python3
"""The commit gate: a commit to a devteam project is checked before it is made
(roadmap 0.3.1, L-1.5; P-49).

    gate.py commit (-m <message> ... | -F <file>) [--pre-plan] [--dry-run]
                   [--json] [--wait <seconds>] [-C <dir>] -- <path> ...

It does what `git commit -F <msg> -- <paths>` does -- the named paths'
working-tree content on HEAD's tree, HEAD as the parent, the rest of the index
left as it is, the project's commit hooks run -- with the project's checks run
in between, on the commit itself:

1. THE CANDIDATE is built without moving any ref: a temporary index holding
   HEAD's tree and the named paths' working-tree content, the commit hooks run
   against it as `git commit` runs them, and a commit object whose parent is
   HEAD.
2. EVERY TREE- AND HISTORY-DERIVED CLASS is evaluated in a clean checkout of
   HEAD, and then of the candidate: the four project checks with
   `--at-commit`, `check_scope` again for each task, and `check_report` for
   each task that has reported or says it is closed. A class that counts
   committed history therefore reads the history this commit creates, before
   the commit exists (F-114).
3. IT COMMITS ONLY IF THE CANDIDATE ADDS NOTHING: no finding and no part not
   evaluated that HEAD lacks, compared by the identity an acceptance matches
   by (result.identity), net of what decisions accept (L-1.6) and of the one
   allowance below. A finding already at HEAD does not refuse an unrelated
   commit (F-12). A commit that adds one anywhere, even in a file it did not
   touch, is refused. Every run prints what stands.
4. THE COMMIT MADE IS THE COMMIT CHECKED. The branch is moved to the candidate
   itself, by a compare-and-swap against HEAD's old value, so the gate refuses
   if HEAD moved in between, and it cannot land a commit it did not evaluate.
5. ONLY THE WRITER COMMITS A MANAGER ARTIFACT (P-13; roadmap 0.3.4, L-4.8).
   A manager artifact is every path under `devteam/` but two: BOARD.md, which
   is the lock and always writable (P-11), and a task file, which its
   supervisor writes. A commit that changes one is refused unless BOARD.md's
   `**Writer.**` line, as the commit leaves it, is vacant or names the
   committing session -- the one `CLAUDE_CODE_SESSION_ID` names -- read by
   guard.py's four readings as they read it for an edit. The lock guarded
   edits and nothing read it for a commit, so a replaced manager could still
   commit an edit it made before the lock moved. The board as the commit
   leaves it, not HEAD's: a commit that takes the lock and writes under it is
   one writer's, as the guard lets that writer edit once the board names it.

The WORKING STATE -- untracked files, uncommitted changes, the harness's
meters -- is in no commit. It is read from the live checkout and printed. Of
it, only an untracked file under `devteam/` that the commit does not name
refuses the commit, as the run's own gate did (pricelog RECORD.md:432; F-131).
It is read before the commit exists, so every close used to print the task
file being committed as `dirty-tree` (roadmap 0.3.2 §3.5's joint). A named path
whose working-tree content is the candidate's is left out of it now: after
this commit it is not uncommitted (L-4.8).

WHAT HEAD HOLDS THAT THE GATE DID NOT MAKE is named at every run, and never
refused, because the client's terminal commits without the gate by design
(roadmap 0.3.1 §3.6; 0.3.4, L-4.8). The gate trusts HEAD: what a commit made
around it added is counted as standing at the next run. So each commit on
HEAD's first-parent line above the newest one the gate made is named, with the
reflog's own word for how it came -- `commit`, `merge`, `reset`, or
`cherry-pick`, which is how a promotion comes (P-44). The gate's own commits
are the reflog entries it writes, `commit (gate): <subject>`. Where the reflog
does not say how a commit was made -- a clone's first entry, a branch's
creation, or no reflog at all -- it says it cannot tell.

THE ONE ALLOWANCE is F-19's window: a task whose title reads DONE, discharging
a requirement that still reads `in-progress (T-n)` with T-n in the board's
in-flight table, because the manager may not move the requirement before the
independent verifier returns (P-18). It fails closed on anything it cannot
read, and 0.3.4's `close` removes it. Two narrowings of WHERE a class is
judged sit beside it, each planted both ways in the control and kept by the
owner on 2026-09-24: check_report runs for a task that has reported or says it
is closed (`reporting`), and its `unfinished-scope` counts only in a commit
that changes that task's own file (`at_its_close`). And `--pre-plan` holds
back `uncovered-requirement` for a requirement the commit adds, and for no
other (`held_back`).

The gate fails closed on its own failures (RECORD.md:430, 1139): if a check
cannot run, or prints output the gate cannot read, nothing is committed.

Exit 0 committed (with `--dry-run`: would commit) · 1 refused · 2 could not
run. Its refusal classes, and the rule each enforces, are in docs/CHECKS.md.
Control: test_gate.py.
"""
import collections
import concurrent.futures
import contextlib
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import result        # noqa: E402 -- the check contract and a finding's identity
import check_trace   # noqa: E402 -- the board and requirement grammars, one home each
import check_refs    # noqa: E402
import check_report  # noqa: E402 -- which tasks have a report to verify
import check_scope   # noqa: E402 -- which tasks a per-task run can name
import guard         # noqa: E402 -- the Writer line and its four readings, one home (P-34)

PROJECT_WIDE = ("check_trace", "check_refs", "check_scope")
WORKING_STATE = {"check_trace": check_trace.WORKING_STATE,
                 "check_refs": check_refs.WORKING_STATE,
                 "check_scope": check_scope.WORKING_STATE,
                 "check_report": check_report.WORKING_STATE}
PREFIX = "devteam-gate-"
CHECKOUT = "checkout"
HOOKS_BEFORE = ("pre-commit", "prepare-commit-msg", "commit-msg")
# What a caller's environment may carry that would point git at another
# repository or index than the one the gate is working in.
GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
           "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_PREFIX",
           "GIT_NAMESPACE")
USAGE = ("usage: gate.py commit (-m <message> ... | -F <file>) [--pre-plan] [--dry-run] "
         "[--json] [--wait <seconds>] [-C <dir>] -- <path> ...")
IN_PROGRESS = re.compile(r"^in-progress \((T-\d+(?:,\s*T-\d+)*)\)$")
TASK_FILE = re.compile(r"^tasks/(T-\d+)\.md$")
BOARD = "devteam/BOARD.md"
# The committing session (roadmap 0.3.4, L-4.8). The harness sets it in a
# session's Bash and in the Bash of an agent that session dispatches: MEASURED
# 2026-09-25, CLI 2.1.282, a subagent printed its dispatcher's id. A worker in
# a sandbox is its own `claude -p` session with its own id.
SESSION = "CLAUDE_CODE_SESSION_ID"
# The word the gate's own reflog entries begin with, which `land` writes.
GATE_ENTRY = "commit (gate)"
# The reflog's words that say how a branch came to hold a commit, not how the
# commit was made: a clone's first entry, a branch's creation, and a checkout,
# which is how a detached HEAD moves.
COPIED = ("clone", "branch", "checkout")
AROUND = 20
AT = {"head": "at HEAD", "candidate": "at the candidate", "live": "in the live checkout"}


class CouldNotRun(Exception):
    """Exit 2: the gate cannot answer. Nothing was committed."""


class Refused(Exception):
    """Raised by a step that refuses before the comparison: `(kind, where, detail)`."""


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in GIT_ENV}
    env.update(extra)
    return env


def git(root, *args, env=None, stdin=None, check=True):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                           env=env or clean_env(), input=stdin)
    except OSError as exc:
        raise CouldNotRun(f"git cannot be run: {exc}")
    if check and p.returncode != 0:
        said = (p.stderr.strip() or p.stdout.strip()).split("\n")[-1]
        raise CouldNotRun(f"`git {' '.join(a for a in args if not a.startswith('-c'))[:60]}` "
                          f"failed: {said}")
    return p


# --- the invocation -----------------------------------------------------------

def parse(argv):
    """The options, or CouldNotRun naming what is wrong with them."""
    if not argv or argv[0] != "commit":
        raise CouldNotRun(USAGE)
    opts = {"messages": [], "file": None, "pre_plan": False, "dry_run": False,
            "dir": None, "wait": 120.0, "paths": None}
    args, i = argv[1:], 0
    value = lambda: args[i + 1] if i + 1 < len(args) else None
    while i < len(args):
        a = args[i]
        if a == "--":
            opts["paths"] = args[i + 1:]
            break
        if a in ("-m", "--message", "-F", "--file", "-C", "--wait"):
            v = value()
            if v is None:
                raise CouldNotRun(f"{a} needs a value. {USAGE}")
            if a in ("-m", "--message"):
                opts["messages"].append(v)
            elif a in ("-F", "--file"):
                opts["file"] = v
            elif a == "-C":
                opts["dir"] = v
            else:
                try:
                    opts["wait"] = float(v)
                except ValueError:
                    raise CouldNotRun(f"--wait takes seconds, not {v!r}")
            i += 2
            continue
        if a in ("--pre-plan", "--dry-run", "--json"):
            opts[{"--pre-plan": "pre_plan", "--dry-run": "dry_run", "--json": "json"}[a]] = True
            i += 1
            continue
        if not a.startswith("-"):
            raise CouldNotRun(f"no `--` before {a!r}: name the paths to commit after `--`, "
                              "as `git commit -F <msg> -- <paths>` does")
        raise CouldNotRun(f"{a!r} is not an option, and paths follow `--`. {USAGE}")
    if opts["paths"] is None:
        raise CouldNotRun("no `--`: name the paths to commit after `--`, as "
                          "`git commit -F <msg> -- <paths>` does")
    if not opts["paths"]:
        raise CouldNotRun("no path after `--`: the gate commits named paths only")
    # THE `-m` TRAP (the `work` skill): after `--`, everything is a path.
    for p in opts["paths"]:
        if p in ("-m", "--message", "-F", "--file", "--pre-plan", "--dry-run", "--json", "-C"):
            raise CouldNotRun(f"{p!r} follows `--`, so it would be read as a path. Put "
                              "every option before `--`")
    if bool(opts["messages"]) == bool(opts["file"]):
        raise CouldNotRun("give the message with -m or with -F, and not both")
    return opts


def message_text(opts):
    if opts["file"] == "-":
        return sys.stdin.read()
    if opts["file"]:
        try:
            with open(opts["file"], encoding="utf-8") as fh:
                return fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise CouldNotRun(f"the message file cannot be read: {exc}")
    return "\n\n".join(opts["messages"]) + "\n"


def named_paths(top, cwd, paths):
    """Each named path, relative to the repository root. A path is resolved
    through the directories above it, never through itself, so a tracked
    symbolic link is committed as the link."""
    out = []
    for p in paths:
        full = os.path.normpath(os.path.join(os.path.realpath(cwd), p))
        full = os.path.join(os.path.realpath(os.path.dirname(full)), os.path.basename(full))
        rel = os.path.relpath(full, top).replace(os.sep, "/")
        if rel == ".":
            # `git add -A` by another name, which `run` §4.5 forbids because
            # it sweeps a worker's in-flight file into the manager's commit.
            raise CouldNotRun(f"{p!r} names the whole repository: name the files this "
                              "commit is for")
        if rel == ".." or rel.startswith("../"):
            raise CouldNotRun(f"{p!r} is outside the repository {top}")
        out.append(rel)
    return sorted(set(out))


def covered(path, named):
    """Is this repository path one of the named paths, or under a named directory?"""
    return any(path == n or path.startswith(n.rstrip("/") + "/") for n in named)


# --- the repository -------------------------------------------------------------

def locate(where):
    start = os.path.abspath(where or os.getcwd())
    p = git(start, "rev-parse", "--show-toplevel", check=False)
    if p.returncode != 0 or not p.stdout.strip():
        raise CouldNotRun(f"not a git repository: {start}")
    top = os.path.realpath(p.stdout.strip())
    if not os.path.isdir(os.path.join(top, "devteam")):
        raise CouldNotRun(f"not a devteam project: {top} holds no devteam/")
    common = git(top, "rev-parse", "--git-common-dir").stdout.strip()
    gitdir = git(top, "rev-parse", "--git-dir").stdout.strip()
    common, gitdir = (d if os.path.isabs(d) else os.path.join(top, d) for d in (common, gitdir))
    for name, what in (("MERGE_HEAD", "a merge"), ("CHERRY_PICK_HEAD", "a cherry-pick"),
                       ("REVERT_HEAD", "a revert"), ("rebase-merge", "a rebase"),
                       ("rebase-apply", "a rebase or `git am`")):
        if os.path.exists(os.path.join(gitdir, name)):
            raise CouldNotRun(f"{what} is in progress; the gate makes ordinary commits only")
    return top, common


@contextlib.contextmanager
def held(common, wait):
    """One gate at a time in a repository, because each run's sweep removes
    every gate checkout it finds, which is safe only while no other gate is
    running. The history classes read the history of the checkout's own HEAD
    (roadmap 0.3.2, L-2.6), so no other gate's candidate is in what they read;
    before 0.3.2 three of them read `git log --all`, which is every worktree's
    HEAD, and the lock was also what kept a second gate's candidate out of it."""
    path = os.path.join(common, "devteam-gate.lock")
    try:
        fh = open(path, "a+")
    except OSError as exc:
        raise CouldNotRun(f"the gate's lock cannot be opened: {exc}")
    deadline = time.monotonic() + wait
    try:
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise CouldNotRun(f"another gate run holds {path}, and it did not finish "
                                      f"within {wait:g}s. Nothing was committed")
                time.sleep(0.2)
        yield
    finally:
        fh.close()


def sweep(top):
    """Remove checkouts an earlier gate run left behind -- a killed run cannot
    clean up after itself, and its worktree would otherwise stay registered in
    the repository for good. Safe only while the lock is held, which is the
    only time it is called: no other gate can be using one.

    ONLY THE GATE'S OWN SHAPE IS TOUCHED: a detached worktree named `checkout`
    directly inside a `devteam-gate-*` temporary directory, and never the
    main worktree, which is listed first. Matching a path fragment alone would
    remove -- and then delete the directory above -- any repository that
    happened to live under such a name.
    """
    git(top, "worktree", "prune", check=False)
    entries = git(top, "worktree", "list", "--porcelain", check=False).stdout.split("\n\n")
    for entry in entries[1:]:
        lines = entry.strip().split("\n")
        if not lines[0].startswith("worktree ") or "detached" not in lines:
            continue
        path = lines[0][len("worktree "):]
        owner = os.path.dirname(path)
        if (os.path.basename(path) != CHECKOUT or not os.path.basename(owner).startswith(PREFIX)
                or os.path.realpath(path) == top):
            continue
        git(top, "worktree", "remove", "--force", path, check=False)
        shutil.rmtree(owner, ignore_errors=True)
    git(top, "worktree", "prune", check=False)


def head(top):
    """(the ref HEAD names, or None when detached; HEAD's commit)."""
    p = git(top, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", check=False)
    if p.returncode != 0:
        raise CouldNotRun("HEAD has no commit yet. The gate compares a commit against the "
                          "project at HEAD; the scaffold's first commit is the client's "
                          "(the `setup` skill)")
    ref = git(top, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip() or None
    return ref, p.stdout.strip()


# --- the candidate -------------------------------------------------------------

def hook_exists(top, name):
    d = git(top, "rev-parse", "--git-path", "hooks").stdout.strip()
    path = os.path.join(d if os.path.isabs(d) else os.path.join(top, d), name)
    return os.path.isfile(path) and os.access(path, os.X_OK)


def run_hook(top, name, args, env):
    """None if the hook passed or does not exist, else what it said."""
    if not hook_exists(top, name):
        return None
    p = subprocess.run(["git", "-C", top, "hook", "run", name, "--", *args],
                       capture_output=True, text=True, env=env)
    if "is not a git command" in p.stderr:
        raise CouldNotRun(f"this repository has a {name} hook, and this git cannot run one "
                          "outside `git commit` (`git hook run` needs git 2.36)")
    if p.returncode != 0:
        return (p.stderr.strip() or p.stdout.strip() or f"exit {p.returncode}")[-400:]
    return None


def build(top, old, paths, message, tmp, hooks=True):
    """(the candidate commit, its tree, its message), as `git commit -- <paths>`
    would make it. Moves no ref, and touches neither the index nor the
    working tree. With `hooks` false -- `--dry-run` -- no commit hook runs,
    as `git commit --dry-run` runs none, since a hook may write."""
    index = os.path.join(tmp, "index")
    env = clean_env(GIT_INDEX_FILE=index, GIT_EDITOR=":")
    git(top, "read-tree", old, env=env)
    listed = "\0".join(paths) + "\0"
    p = git(top, "--literal-pathspecs", "add", "-A", "--pathspec-from-file=-",
            "--pathspec-file-nul", env=env, stdin=listed, check=False)
    if p.returncode != 0:
        raise CouldNotRun(f"the named paths cannot be staged: "
                          f"{(p.stderr.strip() or p.stdout.strip())[:400]}")
    msgfile = os.path.join(tmp, "COMMIT_EDITMSG")
    with open(msgfile, "w", encoding="utf-8") as fh:
        fh.write(message)
    for name, args in (("pre-commit", []), ("prepare-commit-msg", [msgfile, "message"]),
                       ("commit-msg", [msgfile])) if hooks else ():
        said = run_hook(top, name, args, env)
        if said is not None:
            raise Refused(("hook-refused", name, said))
    with open(msgfile, encoding="utf-8") as fh:
        cleaned = git(top, "stripspace", stdin=fh.read()).stdout
    if not cleaned.strip():
        raise CouldNotRun("the commit message is empty")
    with open(msgfile, "w", encoding="utf-8") as fh:
        fh.write(cleaned)
    tree = git(top, "write-tree", env=env).stdout.strip()
    if tree == git(top, "rev-parse", f"{old}^{{tree}}").stdout.strip():
        raise CouldNotRun("nothing to commit: the named paths change nothing in HEAD's tree")
    sign = ["-S"] if git(top, "config", "--bool", "commit.gpgsign",
                         check=False).stdout.strip() == "true" else []
    commit = git(top, "commit-tree", tree, "-p", old, *sign, "-F", msgfile).stdout.strip()
    return commit, tree, cleaned


# --- evaluation ------------------------------------------------------------------

def reporting(devteam):
    """(tasks check_report runs for, tasks it does not) at this tree.

    check_report verifies a REPORT block, so it runs for a task that has one --
    a line naming a report for it, a step's included -- and for a task whose
    title says it is closed, which must have one. A task that has neither has
    no report to verify: a freshly planned or claimed task reads `no-report`,
    which is true and is not a defect, and would refuse every planning commit.
    Those tasks are named as not run, because the title and the record are a
    declaration a reader can check (L-1.2).
    """
    listing = result.listed(devteam, "tasks/*.md")
    run, skip = [], []
    for rel in (listing[0] if listing else []):
        m = TASK_FILE.match(rel)
        if not m:
            continue
        tid = m.group(1)
        try:
            with open(os.path.join(devteam, rel), encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError:
            run.append(tid)          # check_report says what is wrong with it
            continue
        title = next((t.group(3).strip() for t in map(check_report.TITLE.match, lines) if t), "")
        said = any((h := check_report.HEADER_ISH.match(line)) and h.group(1) == tid
                   for line in lines)
        (run if said or title.startswith(check_report.CLOSING) else skip).append(tid)
    order = lambda t: int(t.split("-")[1])
    return sorted(run, key=order), sorted(skip, key=order)


def plan(tree, at):
    """Every check run the gate makes at one tree, as (check, task, argv).

    `--pre-plan` is not passed on: check_trace would exclude every
    uncovered-requirement, and the gate holds back only a requirement the
    commit adds (`held_back`)."""
    devteam = os.path.join(tree, "devteam")
    flags = ["--json"] + (["--at-commit"] if at != "live" else [])
    jobs = [(c, "", [tree, *flags]) for c in PROJECT_WIDE]
    if at != "live":
        # A per-task class reads a task's commits, which only a commit's
        # history holds; the live checkout adds nothing to it.
        loaded = check_scope.load_tasks(devteam)
        ids = sorted(loaded[0], key=lambda t: int(t.split("-")[1])) if loaded else []
        jobs += [("check_scope", t, [tree, t, *flags]) for t in ids]
    run, skip = reporting(devteam)
    jobs += [("check_report", t, [tree, t, *flags]) for t in run]
    return jobs, skip


def run_one(job, tree, at):
    check, task, argv = job
    where = f"{check}{' ' + task if task else ''} {AT[at]}"
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, f"{check}.py"), *argv],
                           cwd=tree, capture_output=True, text=True, env=clean_env())
    except OSError as exc:
        raise CouldNotRun(f"{where} cannot be started: {exc}")
    said = (p.stderr.strip() or p.stdout.strip()).split("\n")[-1][:300]
    if p.returncode == result.COULD_NOT_RUN:
        raise CouldNotRun(f"{where} could not run (exit 2): {said}")
    try:
        doc = json.loads(p.stdout)
        ok = (doc.get("schema") == result.SCHEMA and doc.get("exit") == p.returncode
              and p.returncode in (result.CLEAN, result.FINDINGS, result.NOT_EVALUATED)
              and len(doc["results"]) == 1 and doc["results"][0]["check"] == check)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        ok = False
    if not ok:
        raise CouldNotRun(f"{where} exited {p.returncode} with output the gate cannot read"
                          + (f": {said}" if said else ""))
    return {"check": check, "task": task, "at": at, "exit": p.returncode,
            "result": doc["results"][0]}


def evaluate(tree, at):
    jobs, skip = plan(tree, at)
    width = min(8, os.cpu_count() or 2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
        runs = list(pool.map(lambda j: run_one(j, tree, at), jobs))
    return runs, skip


class Tally:
    """What one tree's runs found, keyed so HEAD and the candidate compare.

    A finding is keyed by its identity (result.identity), without a line, so
    an edit above it moves nothing. The checks remove what a decision accepts,
    so what is left is what stands unaccepted. Several runs of one check
    report the project's findings once each, and a per-task run only adds its
    own; so each identity counts at its most in any one run of its check.
    A part not evaluated is keyed by its name, which carries no line, and for
    check_report by its task too, whose parts do not name one.
    """

    def __init__(self, runs):
        self.count, self.found, self.gaps = collections.Counter(), {}, {}
        self.tasks = 0
        per_check = collections.defaultdict(collections.Counter)
        for r in runs:
            res, check = r["result"], r["check"]
            if check == "check_trace" and not r["task"]:
                self.tasks = res["counts"].get("tasks", 0)
            seen = collections.Counter()
            for f in res["findings"]:
                key = result.identity(check, f)
                seen[key] += 1
                self.found.setdefault(key, []).append(dict(f, check=check, task=r["task"]))
            per_check[check] |= seen
            for g in res["not_evaluated"]:
                key = (check, r["task"] if check == "check_report" else "", " ".join(g["part"].split()))
                self.gaps.setdefault(key, dict(g, check=check, task=r["task"]))
        for c in per_check.values():
            self.count += c


def working_state(runs):
    """What the live checkout says that no commit holds: each check's
    WORKING_STATE classes, and its parts of the same name."""
    out = []
    for r in runs:
        ws = WORKING_STATE[r["check"]]
        res = r["result"]
        out += [dict(f, check=r["check"], task=r["task"]) for f in res["findings"]
                if f["class"] in ws]
        out += [dict(g, check=r["check"], task=r["task"], **{"class": "not evaluated"})
                for g in res["not_evaluated"] if g["part"] in ws]
    seen, unique = set(), []
    for w in out:
        key = (w["check"], w.get("file"), w.get("detail"), w.get("part"), w["task"])
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique


def allowance(f, statuses, flying):
    """Why F-19's window lets this added finding through, or None.

    Only a `one-sided-link` reported for a task whose title reads DONE
    (check_trace.CLOSED_LINK), whose requirement still reads `in-progress
    (T-n, …)` naming a task in the board's in-flight table -- the task the
    requirement names, not the one the finding is anchored at, which is how
    the run's gate came to key it after failing closed twice (pricelog
    RECORD.md:486-487). Anything it cannot read is refused.
    """
    if f["check"] != "check_trace" or f["class"] != "one-sided-link":
        return None
    m = check_trace.CLOSED_LINK.match(f["detail"])
    if not m:
        return None
    task, req = m.groups()
    status = statuses.get(req, "")
    named = IN_PROGRESS.match(status)
    hit = [t for t in (re.findall(r"T-\d+", named.group(1)) if named else []) if t in flying]
    if not hit:
        return None
    return (f"F-19's window: {task} reads DONE, {req} reads {status!r}, and {hit[0]} is in "
            f"the board's in-flight table (BOARD.md:{flying[hit[0]]}), so its verifier has "
            "not returned")


def at_its_close(f, touched):
    """Why this added finding is judged at its task's close and not here, or None.

    `unfinished-scope` enforces that a task does not CLOSE with a stub in its
    declared scope, and check_report reads the scope's files as they are now.
    So once a task has closed, a later task writing a tests-first stub into a
    file the two share makes the closed task's report read unfinished: pricelog
    `1f88891`, T-8's stub in `store.py`, which T-3 had closed over days before
    (0.3.1 §3.5's corpus replay). That stub is the writing task's, attributed
    to it by check_scope and judged at its own close. So the class is judged
    for a task only in a commit that changes the task's own file -- its report
    or its title -- which is the moment the rule is about.
    """
    if f["check"] != "check_report" or f["class"] != "unfinished-scope" or f["task"] in touched:
        return None
    return (f"unfinished-scope is judged when {f['task']}'s report or title changes, and this "
            f"commit changes neither: a stub written into a closed task's scope belongs to the "
            f"task writing it, and is judged at that task's close")


def held_back(f, pre_plan, before):
    """Why --pre-plan holds this added finding back, or None.

    A requirement committed before its task is planned is uncovered by
    construction: at onboarding every one is, and at a later cycle's charter
    gate every new one is, because the client signs the amended charter before
    the plan (the `iterate` skill). So --pre-plan holds back
    `uncovered-requirement` for a requirement HEAD does not have. One HEAD
    has, and that has now lost its task, is refused as any added finding is.
    Once committed, the uncovered requirement stands at HEAD, and every gate
    run prints it until a task discharges it. Settled by the owner,
    2026-09-24, over accepting each by a decision and over committing the
    requirements with their plan.
    """
    if not pre_plan or f["check"] != "check_trace" or f["class"] != "uncovered-requirement":
        return None
    m = check_trace.UNCOVERED.match(f["detail"])
    if not m or m.group(1) in before:
        return None
    return (f"--pre-plan: {m.group(1)} is new in this commit, and its task is not planned yet; "
            "it stands, printed at every gate run, until a task discharges it")


def judge(base, cand, live, named, pre_plan, statuses, flying, unread, changed=(), before=()):
    """(refusals, allowed, standing findings, standing parts, fixed)."""
    touched = {m.group(1) for m in (re.match(r"^devteam/tasks/(T-\d+)\.md$", p) for p in changed) if m}
    refusals = []
    add = lambda kind, where, detail, **more: refusals.append(
        dict(more, **{"class": kind, "where": where, "detail": detail}))
    allowed, standing, fixed = [], [], []
    for key in sorted(set(base.count) | set(cand.count)):
        was, now = base.count[key], cand.count[key]
        if now > was:
            for f in cand.found[key][:now - was]:
                why = (allowance(f, statuses, flying) or at_its_close(f, touched)
                       or held_back(f, pre_plan, before))
                if why:
                    allowed.append(dict(f, allowed=why))
                    continue
                at = f"{f['file']}:{f['line']}" if f.get("line") is not None else f["file"]
                more = (f" ({now} here, {was} at HEAD)" if was else "")
                hint = ""
                if f["class"] == "one-sided-link" and unread:
                    hint = (f". The board's in-flight table has {len(unread)} row(s) naming no "
                            f"task ({result.anchors([('BOARD.md', n) for n in unread])}), "
                            "which the allowance cannot read")
                add("adds-finding", at,
                    f"{f['check']} {f['class']}: {f['detail']}{more}{hint}", finding=f)
        if min(was, now):
            standing += cand.found[key][:min(was, now)]
        if was > now:
            fixed += base.found[key][:was - now]
    for key in sorted(set(cand.gaps) - set(base.gaps)):
        g = cand.gaps[key]
        who = f"{g['check']}{' ' + g['task'] if g['task'] else ''}"
        add("adds-not-evaluated", g["part"], f"{who}: {g['reason']}", part=g)
    parts = [cand.gaps[k] for k in sorted(set(cand.gaps) & set(base.gaps))]
    untracked = sorted({f"devteam/{w['file']}" for w in live
                        if w.get("class") == "untracked-file" and w.get("file")})
    for path in untracked:
        if not covered(path, named):
            add("untracked-unnamed", path,
                "is under devteam/ and in no commit, and this commit does not name it: every "
                "check reads it, and a clone, a review and the gate at HEAD do not (F-131). "
                "Name it in this commit, commit it first, or move it out of devteam/")
    return refusals, allowed, standing, parts, fixed


# --- the writer lock (roadmap 0.3.4, L-4.8) --------------------------------------

def manager_artifacts(paths):
    """The paths under devteam/ that only the writer commits: every one but
    BOARD.md, the lock itself (P-11), and a task file, its supervisor's (P-13)."""
    return [p for p in paths if p.startswith("devteam/") and p != BOARD
            and not TASK_FILE.match(p[len("devteam/"):])]


def named_id(holder):
    """The id a `**Writer.**` line names, for a message: its backticked value,
    or the line itself."""
    m = re.search(r"`([^`]*)`", holder or "")
    return m.group(1) if m else (holder or "").strip()


def writer(top, commit):
    """BOARD.md's `**Writer.**` line at a commit, as guard.py reads it -- the
    rest of the line after the field -- or None: no board, or no such line."""
    p = git(top, "show", f"{commit}:{BOARD}", check=False)
    if p.returncode != 0:
        return None
    return next((m.group(1) for m in map(guard.WRITER.match, p.stdout.split("\n")) if m), None)


def unheld(top, commit, wrote):
    """The refusals for a commit that changes a manager artifact from a session
    that does not hold the lock, or [] (P-13).

    The lock is BOARD.md's `**Writer.**` line in the candidate, which is
    HEAD's unless the commit changes the board, read by guard.py's four
    readings: `vacant` and `mine` commit, `unknown` and `theirs` are refused.
    `unknown` is a process with no session id. It is refused, never read as
    anyone's, as the guard refuses it an edit: a gate that went quiet when it
    could not tell who was committing is the failure the guard's comment on
    `lock_state` records (DESIGN §20)."""
    ours = manager_artifacts(wrote)
    if not ours:
        return []
    session = os.environ.get(SESSION, "").strip()
    holder = writer(top, commit)
    reading = guard.lock_state(holder, session)
    if reading in ("vacant", "mine"):
        return []
    named = ", ".join(ours[:4]) + (f" and {len(ours) - 4} more" if len(ours) > 4 else "")
    refusals = []
    add = lambda kind, where, detail: refusals.append(
        {"class": kind, "where": where, "detail": detail})
    if reading == "unknown":
        add("no-session", ours[0],
            f"the commit changes {named}, which only the session BOARD.md names as its "
            f"writer commits, and this process has no {SESSION} to tell it by (P-13). "
            "Commit from the session that holds the lock")
        return refusals
    how = (". You have been REPLACED: `devteam/.run/session/handoff-ready` names this "
           "session as the outgoing manager, and the lock has moved to your successor. Do "
           "not take it back; write nothing (`run` §2, `resume` §0)"
           if guard.handoff_names(top, session) else
           ". If that session is gone, taking the lock is the client's word and the "
           "board's first commit (`run` §1.1); BOARD.md and a task file are never refused")
    add("lock-not-held", ours[0],
        f"the commit changes {named}, which only the writer commits (P-13), and BOARD.md "
        f"names another session as its writer ({named_id(holder)}); this session is "
        f"{session}{how}")
    return refusals


# --- what HEAD holds that the gate did not make (roadmap 0.3.4, L-4.8) --------------

def around(top, ref, old):
    """The commits on HEAD's first-parent line above the newest one the gate
    made, each with the reflog's own word for how it came. Printed, never
    refused.

    A branch's reflog has one entry per move, newest first, each naming the
    commit the branch moved to; the entry below it names where it moved from.
    So an entry brought the commits on its first-parent line that the line it
    moved from lacks -- one for a commit or a cherry-pick, several for a
    fast-forward, none for a reset backwards. A commit is named with the word
    of the oldest entry above the gate's that brought it, which is how it
    first came: a merge reset away and back came by merge. `AROUND` bounds the
    walk, and a commit the reflog does not reach, or reaches only by a copy
    (`COPIED`), ends it: from there down the gate cannot tell.
    """
    out = {"since": None, "commits": [], "cannot_tell": None, "more": False, "walked": 0}
    p = git(top, "reflog", "show", "--format=%H%x00%gs", ref or "HEAD", "--", check=False)
    entries = ([tuple(e.split("\0", 1)) for e in p.stdout.split("\n") if "\0" in e]
               if p.returncode == 0 else [])
    ours = {new for new, said in entries if said.startswith(GATE_ENTRY + ": ")}
    walked = []
    line = git(top, "rev-list", "--first-parent", f"--max-count={AROUND + 1}", old).stdout
    for c in line.split():
        if c in ours:
            out["since"] = c
            break
        walked.append(c)
    out["walked"], out["more"] = min(len(walked), AROUND), len(walked) > AROUND
    if not walked:
        return out
    if not entries:
        out["cannot_tell"] = {"from": walked[0], "why": "the branch has no reflog, so how "
                              "its commits came is recorded nowhere"}
        return out
    top_entry = next((i for i, (new, said) in enumerate(entries)
                      if new == out["since"] and said.startswith(GATE_ENTRY + ": ")),
                     min(len(entries), 200))
    how, todo = {}, set(walked)
    for i in range(top_entry - 1, -1, -1):
        if not todo:
            break
        new, said = entries[i]
        below = [f"^{entries[i + 1][0]}"] if i + 1 < len(entries) else []
        brought = git(top, "rev-list", "--first-parent", f"--max-count={AROUND + 1}", new,
                      *below, check=False).stdout.split()
        for c in brought:
            if c in todo:
                how[c] = said.split(":", 1)[0].strip()
                todo.discard(c)
    shown = git(top, "show", "-s", "--format=%H%x00%s", *walked[:AROUND]).stdout
    subjects = dict(s.split("\0", 1) for s in shown.split("\n") if "\0" in s)
    for c in walked[:AROUND]:
        word = how.get(c)
        if not word or word.split()[0] in COPIED:
            out["cannot_tell"] = {"from": c, "why": (
                f"the reflog says `{word}`, which records how the branch came to hold it, not "
                "how it was made" if word else "the reflog does not reach it")}
            return out
        out["commits"].append({"commit": c, "how": word, "subject": subjects.get(c, "")})
    return out


def committing(top, index, named):
    """Is this path one the commit commits as the working tree holds it? The
    candidate's temporary index says: `git diff-files` names each named path
    whose working-tree content differs from it (roadmap 0.3.4, L-4.8)."""
    differs = set(git(top, "--literal-pathspecs", "diff-files", "--name-only", "-z", "--",
                      *named, env=clean_env(GIT_INDEX_FILE=index)).stdout.split("\0")) - {""}
    return lambda path: covered(path, named) and path not in differs


def uncommitted(ws, same):
    """The working state less each `dirty-tree` path that `same` says the commit
    commits as it stands: after this commit it is not uncommitted."""
    out = []
    for w in ws:
        m = (check_report.DIRTY.match(w.get("detail") or "")
             if (w["check"], w["class"]) == ("check_report", "dirty-tree") else None)
        if m:
            left = [p for p in m.group(2).split(", ") if not same(p)]
            if not left:
                continue
            w = dict(w, detail=m.group(1) + ", ".join(left))
        out.append(w)
    return out


# --- the commit ------------------------------------------------------------------

def land(top, ref, old, commit, subject, changed):
    """Move the branch to the candidate, if HEAD is still `old`, and bring the
    index level with the commit for every path it changed. Returns a
    refusal, or None once committed."""
    now_ref = git(top, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip() or None
    if now_ref != ref:
        return ("head-moved", "HEAD", f"HEAD named {ref or 'a detached commit'} when the gate "
                f"began and names {now_ref or 'a detached commit'} now. Nothing was committed; "
                "run the gate again")
    target = [ref] if ref else ["--no-deref", "HEAD"]
    p = git(top, "update-ref", "-m", f"{GATE_ENTRY}: {subject}", *target, commit, old,
            check=False)
    if p.returncode != 0:
        now = git(top, "rev-parse", "--verify", "--quiet", "HEAD", check=False).stdout.strip()
        return ("head-moved", ref or "HEAD", f"{ref or 'HEAD'} moved from {old[:7]} to "
                f"{now[:7] or 'nothing'} while the gate evaluated, so the candidate's parent is "
                "no longer HEAD. Nothing was committed; run the gate again")
    # As `git commit -- <paths>` leaves it: every path the commit changed is
    # staged as committed, and every other path in the index is untouched.
    p = git(top, "--literal-pathspecs", "reset", "-q", commit, "--pathspec-from-file=-",
            "--pathspec-file-nul", stdin="\0".join(changed) + "\0", check=False)
    run_hook(top, "post-commit", [], clean_env())     # its exit is advisory, as in git
    if p.returncode != 0:
        return ("index", (p.stderr.strip() or p.stdout.strip())[:300])
    return None


# --- output ----------------------------------------------------------------------

def at_of(f):
    return f"{f['file']}:{f['line']}" if f.get("line") is not None else (f.get("file") or "")


def render(doc):
    out = [doc["line"]]
    for r in doc["refused"]:
        out.append(f"  {r['class']:20} {r['where']}  {r['detail']}")
    for f in doc["allowed"]:
        out.append(f"  allowed: {f['check']} {f['class']} {at_of(f)} — {f['allowed']}")
    ar = doc.get("around") or {}
    if ar.get("commits") or ar.get("cannot_tell"):
        where = (f"above {ar['since'][:7]}, its newest commit on HEAD's first-parent line"
                 if ar.get("since") else
                 f"none of the {'newest ' if ar.get('more') else ''}{ar.get('walked', 0)} "
                 "commit(s) on HEAD's first-parent line is the gate's")
        out.append(f"  made without the gate, {where} (named, never refused; what they added "
                   "stands):")
        for c in ar["commits"]:
            out.append(f"    {c['commit'][:7]} {c['how']}: {c['subject']}")
        if ar.get("more") and not ar.get("cannot_tell"):
            out.append(f"    and more below these {AROUND}")
        if ar.get("cannot_tell"):
            out.append(f"    from {ar['cannot_tell']['from'][:7]} down, cannot tell: "
                       f"{ar['cannot_tell']['why']}")
    st = doc["standing"]
    if st["findings"] or st["not_evaluated"]:
        out.append(f"  standing, at HEAD and not added here: {len(st['findings'])} finding(s), "
                   f"{len(st['not_evaluated'])} part(s) not evaluated")
        for f in st["findings"]:
            out.append(f"    {f['check']} {f['class']} {at_of(f)}  {f['detail']}")
        for g in st["not_evaluated"]:
            who = f"{g['check']}{' ' + g['task'] if g['task'] else ''}"
            out.append(f"    {who} not evaluated: {g['part']}")
    for f in doc["fixed"]:
        out.append(f"  fixed here: {f['check']} {f['class']} {at_of(f)}  {f['detail']}")
    if doc["working_state"]:
        out.append("  working state, read from the live checkout before this commit (printed; "
                   "only an untracked file under devteam/ that the commit does not name refuses):")
        parts = collections.OrderedDict()
        for w in doc["working_state"]:
            if w["class"] == "not evaluated":
                parts.setdefault((w["check"], w["part"]), []).append(w)
                continue
            who = f"{w['check']}{' ' + w['task'] if w['task'] else ''}"
            out.append(f"    {who} {w['class']} {at_of(w)}  {w['detail']}")
        # One line per part, not per task: a project whose sandboxes are
        # closed has no meter for any of them, and that is one fact.
        for (check, part), ws in parts.items():
            tasks = [w["task"] for w in ws if w["task"]]
            out.append(f"    {check} not evaluated: {part}"
                       + (f", for {len(tasks)} task(s) ({', '.join(tasks)})" if tasks else "")
                       + f" — {ws[0]['reason']}")
    for w in doc.get("warnings", []):
        out.append(f"  warning: {w}")
    if doc["not_run"]:
        out.append(f"  check_report not run for {', '.join(doc['not_run'])} — no REPORT block, "
                   "and the title does not say closed")
    return out


def commit(paths, message, cwd=None, pre_plan=False, dry_run=False, wait=120.0, expect=None):
    """The gate's one act, as data: build the candidate, judge it, and land it.

    `paths` are named as `git commit -- <paths>` names them, relative to
    `cwd`, the working directory when None. Returns the document `--json`
    prints, whose `exit` is 0 committed (with `dry_run`, would commit) or 1
    refused. Raises CouldNotRun when the gate cannot answer, and nothing was
    committed then. `main` is this function behind the command line. A
    command that commits for the manager calls it directly, so it gets what
    the gate refused and what stands as data, and reports it whole (roadmap
    0.3.4, L-4.1). `expect` is the HEAD the caller read the project at: if
    HEAD is another commit, it is refused as `head-moved`, so a commit built
    from what the caller read never lands on a project that has changed.
    """
    doc = {"schema": result.SCHEMA, "gate": "commit", "refused": [], "allowed": [],
           "standing": {"findings": [], "not_evaluated": []}, "fixed": [],
           "working_state": [], "not_run": [],
           "around": {"since": None, "commits": [], "cannot_tell": None, "more": False}}
    tmp = None
    try:
        top, common = locate(cwd)
        paths = named_paths(top, cwd or os.getcwd(), paths)
        with held(common, wait):
            sweep(top)
            ref, old = head(top)
            if git(top, "cat-file", "-e", f"{old}:devteam", check=False).returncode != 0:
                raise CouldNotRun("HEAD holds no devteam/, so there is no project at HEAD to "
                                  "compare with; the scaffold's first commit is the client's "
                                  "(the `setup` skill)")
            if expect and old != expect:
                refusals = []
                add = lambda kind, where, detail: refusals.append(
                    {"class": kind, "where": where, "detail": detail})
                add("head-moved", "HEAD", f"HEAD is {old[:7]}, and the commit was prepared "
                    f"against {expect[:7]}: another commit landed in between. Nothing was "
                    "committed; prepare it again")
                doc.update(refused=refusals, exit=result.FINDINGS, head=old,
                           result="would refuse" if dry_run else "refused",
                           line=f"gate: refused — HEAD moved; nothing was committed  "
                                f"[HEAD {old[:7]} unchanged]")
                return doc
            doc["around"] = around(top, ref, old)
            tmp = tempfile.mkdtemp(prefix=PREFIX)
            try:
                commit, tree, cleaned = build(top, old, paths, message, tmp,
                                              hooks=not dry_run)
            except Refused as exc:
                kind, where, detail = exc.args[0]
                refusals = []
                add = lambda kind, where, detail: refusals.append(
                    {"class": kind, "where": where, "detail": detail})
                add("hook-refused", where, f"the {where} hook refused the commit: {detail}")
                doc.update(refused=refusals, exit=result.FINDINGS, head=old,
                           result="would refuse" if dry_run else "refused",
                           line=f"gate: refused — the {where} hook refused it; nothing was "
                                f"committed  [HEAD {old[:7]} unchanged]")
                return doc
            subject = cleaned.split("\n", 1)[0]
            wrote = sorted(p for p in git(
                top, "diff-tree", "-r", "--name-only", "--no-renames", "-z", old, commit
            ).stdout.split("\0") if p)
            changed = sorted(set(paths) | set(wrote))
            doc.update(head=old, ref=ref, candidate=commit, tree=tree, subject=subject,
                       paths=paths)
            refusals = unheld(top, commit, wrote)
            if refusals:
                doc.update(refused=refusals, exit=result.FINDINGS,
                           result="would refuse" if dry_run else "refused",
                           line=(f"gate: {'would refuse' if dry_run else 'refused'} — the commit "
                                 "changes a manager artifact, and only the writer commits one; "
                                 f"nothing was committed  [HEAD {old[:7]} and the index "
                                 "unchanged]"))
                return doc
            # ONE CHECKOUT, AT HEAD AND THEN AT THE CANDIDATE. Every history
            # class reads the history of the checkout's own HEAD (roadmap 0.3.2,
            # L-2.6), so HEAD is judged in HEAD's history and the candidate in
            # the history it creates, before it exists (F-114).
            live, _ = evaluate(top, "live")
            wt = os.path.join(tmp, CHECKOUT)
            git(top, "-c", "core.hooksPath=/dev/null", "worktree", "add", "--detach", "--quiet",
                wt, old)
            try:
                base_runs, _ = evaluate(wt, "head")
                before = set(check_trace.requirement_statuses(os.path.join(wt, "devteam")))
                git(wt, "-c", "core.hooksPath=/dev/null", "checkout", "--detach", "--quiet", commit)
                cand_runs, not_run = evaluate(wt, "candidate")
                statuses = check_trace.requirement_statuses(os.path.join(wt, "devteam"))
                flying, unread = check_trace.in_flight(os.path.join(wt, "devteam"))
            finally:
                git(top, "worktree", "remove", "--force", wt, check=False)
            base, cand = Tally(base_runs), Tally(cand_runs)
            ws = uncommitted(working_state(live),
                             committing(top, os.path.join(tmp, "index"), paths))
            refusals, allowed, standing, parts, fixed = judge(
                base, cand, ws, paths, pre_plan, statuses, flying, unread, changed, before)
            doc.update(refused=refusals, allowed=allowed, fixed=fixed, working_state=ws,
                       not_run=not_run, standing={"findings": standing, "not_evaluated": parts},
                       runs=[{"check": r["check"], "task": r["task"], "at": r["at"],
                              "exit": r["exit"]} for r in live + base_runs + cand_runs])
            checked = (f"checked at HEAD and at the candidate: {len(PROJECT_WIDE)} checks, "
                       f"check_scope for {sum(1 for r in cand_runs if r['check'] == 'check_scope' and r['task'])} "
                       f"task(s), check_report for "
                       f"{sum(1 for r in cand_runs if r['check'] == 'check_report')} task(s)")
            if refusals:
                n = collections.Counter(r["class"] for r in refusals)
                said = [text.format(n[kind]) for kind, text in (
                    ("adds-finding", "adds {} finding(s)"),
                    ("adds-not-evaluated", "adds {} part(s) not evaluated"),
                    ("untracked-unnamed", "leaves {} untracked file(s) under devteam/ unnamed"))
                    if n[kind]]
                doc.update(exit=result.FINDINGS,
                           result="would refuse" if dry_run else "refused",
                           line=(f"gate: {'would refuse' if dry_run else 'refused'} — the "
                                 f"commit {' and '.join(said)}; nothing was committed  [HEAD "
                                 f"{old[:7]} and the index unchanged; {checked}]"))
                return doc
            if dry_run:
                doc.update(exit=result.CLEAN, result="would commit",
                           line=f"gate: would commit {commit[:7]} — {subject}  [HEAD "
                                f"{old[:7]}; {checked}]")
                return doc
            refusal = land(top, ref, old, commit, subject, changed)
            if refusal and refusal[0] == "index":
                doc["warnings"] = [f"the commit is made, and the index could not be brought "
                                   f"level with it ({refusal[1]}); run `git reset -q -- "
                                   f"{' '.join(changed)}`"]
                refusal = None
            if refusal:
                kind, where, detail = refusal
                late = []
                add = lambda kind, where, detail: late.append(
                    {"class": kind, "where": where, "detail": detail})
                add("head-moved", where, detail)
                doc.update(refused=late, exit=result.FINDINGS, result="refused",
                           line=f"gate: refused — HEAD moved; nothing was committed  [{checked}]")
                return doc
            made = git(top, "rev-parse", "HEAD").stdout.strip()
            if (made != commit or git(top, "rev-parse", f"{made}^{{tree}}").stdout.strip() != tree
                    or git(top, "rev-parse", f"{made}^").stdout.strip() != old):
                raise CouldNotRun(f"the ref moved to {commit[:7]}, but HEAD now reads "
                                  f"{made[:7]}: something moved it after the gate committed. "
                                  f"The commit checked is {commit[:7]}")
            doc.update(exit=result.CLEAN, result="committed", committed=made,
                       line=f"gate: committed {made[:7]}"
                            f"{' on ' + ref.rsplit('/', 1)[-1] if ref else ''} — {subject}  "
                            f"[parent {old[:7]}; {checked}]")
            return doc
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    as_json = "--json" in argv[1:argv.index("--")] if "--" in argv else "--json" in argv
    try:
        opts = parse(argv[1:])
        message = message_text(opts)
        doc = commit(opts["paths"], message, cwd=opts["dir"], pre_plan=opts["pre_plan"],
                     dry_run=opts["dry_run"], wait=opts["wait"])
    except CouldNotRun as exc:
        print(f"gate: could not run — {exc}", file=sys.stderr)
        if as_json:
            json.dump({"schema": result.SCHEMA, "gate": "commit", "exit": result.COULD_NOT_RUN,
                       "result": "could not run", "error": str(exc)}, sys.stdout,
                      ensure_ascii=False)
            sys.stdout.write("\n")
        return result.COULD_NOT_RUN
    return finish(doc, as_json)


def finish(doc, as_json):
    if as_json:
        json.dump(doc, sys.stdout, indent=1, sort_keys=True, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for line in render(doc):
            print(line)
    return doc["exit"]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
