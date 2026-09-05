#!/usr/bin/env python3
"""PreToolUse guard for a devteam project: three rules, one script.

1. PROTECTED PATHS ARE READ-ONLY. The charter declares them -- vendored
   dependencies, generated trees, sibling repositories, production config.
   Reading, grepping and listing them is always fine.
2. WHILE THE LOOP IS RUNNING, A WRITE MUST LAND INSIDE THE DECLARED SCOPE OF
   A LIVE TASK (P-10, P-12). This is what makes width greater than one safe
   inside one repository. Enforced only when at least one task is RUNNING,
   because outside the loop the project is the author's to edit.
3. `devteam/` IS WRITTEN ONLY BY THE SESSION THE BOARD NAMES (P-13), with
   BOARD.md itself exempt -- it IS the lock. Taking it is always possible and
   always in the history, and the session refused afterwards is the one that
   lost it. Without the exemption nobody could ever hand the lock over.

Covers Bash, Write, Edit and NotebookEdit in one place, because a guard that
covers the file tools and not the shell (or the reverse) has a hole exactly
where somebody will walk.

THE RULE THAT MATTERS: a write is judged by its TARGET, never by whether the
command text mentions a protected path. A guard that refuses `cat > NOTES.md`
because the document being written happens to describe a protected tree is a
guard that gets switched off -- which is strictly worse than no guard (P-35).
More than a third of its control's cases are false-positive controls for
exactly this reason.

Self-scoping is on the SESSION'S PROJECT DIRECTORY (`CLAUDE_PROJECT_DIR`), not
the hook's per-call `cwd`, because `cwd` follows the shell's `cd` -- and a `cd`
into a protected tree, which is a read and allowed, would otherwise disarm the
guard for the next call. The per-call `cwd` is still what relative targets
resolve against, because it is what the shell will use.

KNOWN LIMITS, STATED: an interpreter heredoc that writes (`python3 - <<PY`)
cannot be classified from the command text, and a target containing an
unexpanded variable (`"$REPO"`) cannot be resolved and is not judged. The
airtight mechanism for the first is the sandbox's own write-deny list; this is
a second layer, not the only one.

Set DEVTEAM_GUARD=off to disable. Reads PreToolUse JSON on stdin; prints a
deny decision, or nothing.  Control: test_guard.py.
"""
import json
import os
import re
import shlex
import sys

# Commands whose non-flag arguments are ALL written to.
WRITE_CMDS = {
    "rm": "a removal", "rmdir": "a removal", "unlink": "a removal",
    "shred": "a removal", "tee": "tee", "truncate": "a truncate",
    "mkdir": "a create", "touch": "a create", "chmod": "a permission change",
    "chown": "an ownership change", "chgrp": "an ownership change",
    "patch": "patch",
}
# Only the LAST argument is written; the rest are SOURCES, and reading a source
# out of a protected tree is exactly what this guard must allow.
DEST_LAST_CMDS = {"cp": "a copy", "install": "an install",
                  "rsync": "an rsync", "ln": "a link"}
BOTH_ENDS_CMDS = {"mv": "a move"}
# Git subcommands are split by WHAT THEY CAN DESTROY, not by whether they
# write. Treating them as one set made the rule unusable: judged against task
# scope it refuses `git commit`, which every worker must do; not judged at all
# it lets `git reset --hard` through. Three sets, three answers.
#
# The index and refs only. These cannot overwrite a working-tree file that was
# not already written -- and that write was judged when it happened.
GIT_INDEX = {"add", "commit", "tag", "notes", "init", "gc", "prune"}
# These overwrite or delete arbitrary working-tree paths, including paths no
# live task has claimed. Judged as a write to the repository itself.
GIT_TREE = {
    "checkout", "switch", "restore", "reset", "revert", "merge", "rebase",
    "cherry-pick", "stash", "clean", "rm", "mv", "apply", "am", "worktree",
    "config",
}
# Outward-facing or ref-fetching. `push` is IRREVERSIBLE by P-26 and the
# permission set deliberately never grants it; the rest move refs under the
# working tree from somewhere nobody in this session controls.
GIT_OUTWARD = {"push", "pull", "fetch", "remote"}
GIT_WRITE = GIT_INDEX | GIT_TREE | GIT_OUTWARD
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\s*\2\s*$", re.S | re.M)
SEPARATORS = {"&&", "||", ";", ";;", "|", "|&", "&"}
REDIRECTS = {">", ">>", "&>", "&>>"}

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
WRITER = re.compile(r"^\*\*Writer\.\*\*\s*(.*)$")
PROTECTED_ROW = re.compile(r"^\|\s*Protected paths\s*\|(.*)\|", re.I)
PLACEHOLDER = re.compile(r"[<>]")


def strip_heredocs(cmd):
    """A heredoc body is DATA, not command."""
    prev = None
    while prev != cmd:
        prev, cmd = cmd, HEREDOC.sub("<<STRIPPED", cmd)
    return cmd


def inside(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def resolve(target, cwd):
    """Absolute real path of a target, or None if it cannot be judged."""
    if not target or target.startswith("-") or "$" in target or "*" in target:
        return None
    # A bare number is a file descriptor or a flag's value (`truncate -s 0 f`),
    # never a path worth guarding. Judging it produced refusals against
    # <project>/0 and <project>/2. A file actually named `2` goes unjudged,
    # which is the cheaper mistake by a wide margin.
    if target.isdigit():
        return None
    t = os.path.expanduser(target)
    return os.path.realpath(t if os.path.isabs(t) else os.path.join(cwd, t))


def tokens(cmd):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        return cmd.split()


def targets(cmd, cwd):
    """(absolute target, description) for every write, following `cd` anywhere."""
    for m in re.finditer(r"\bof=([^\s;|&()]+)", cmd):
        yield resolve(m.group(1), cwd), "dd", "write"
    toks = tokens(cmd)
    eff, stack, seg = cwd, [], []

    def flush(seg, eff):
        if not seg:
            return eff
        base = os.path.basename(seg[0])
        args = [a for a in seg[1:] if not a.startswith("-")]
        if base in ("cd", "pushd"):
            dest = os.path.expanduser(args[0]) if args else os.path.expanduser("~")
            if "$" not in dest:
                return os.path.realpath(dest if os.path.isabs(dest) else os.path.join(eff, dest))
        return eff

    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t == "(":
            stack.append(eff); seg = []; i += 1; continue
        if t == ")":
            eff = flush(seg, eff); seg = []
            eff = stack.pop() if stack else eff
            i += 1; continue
        if t in SEPARATORS:
            eff = flush(seg, eff); seg = []; i += 1; continue
        if t in REDIRECTS:
            if i + 1 < n and not toks[i + 1].startswith("&"):
                yield resolve(toks[i + 1], eff), "a redirection", "write"
                i += 2; continue
            i += 1; continue
        if t.startswith(">") or t.startswith("<"):
            i += 1; continue
        seg.append(t)
        i += 1
        if i == n or toks[i] in SEPARATORS or toks[i] in ("(", ")") or toks[i] in REDIRECTS:
            # A file-descriptor number belongs to the REDIRECT, not to the
            # command. `touch src/x 2>/dev/null` tokenises as [touch, src/x, 2]
            # followed by `>`, so the `2` was read as a positional argument,
            # resolved to <project>/2, matched no scope, and refused a write
            # that was plainly in scope. `2>&1` is ubiquitous, so this fired
            # constantly on correct work -- the false-positive failure this
            # guard's own docstring calls strictly worse than no guard.
            if (i < n and seg and seg[-1].isdigit()
                    and (toks[i] in REDIRECTS or toks[i].startswith(">"))):
                seg.pop()
            base = os.path.basename(seg[0])
            args = [a for a in seg[1:] if not a.startswith("-")]
            if base in WRITE_CMDS:
                for a in args:
                    yield resolve(a, eff), WRITE_CMDS[base], "write"
            elif base in BOTH_ENDS_CMDS:
                for a in args:
                    yield resolve(a, eff), BOTH_ENDS_CMDS[base], "write"
            elif base in DEST_LAST_CMDS and args:
                yield resolve(args[-1], eff), DEST_LAST_CMDS[base], "write"
            elif base in ("sed", "perl") and any(a.startswith("-") and "i" in a for a in seg[1:4]):
                for a in args:
                    r = resolve(a, eff)
                    if r and os.path.exists(r):
                        yield r, f"{base} -i", "write"
            elif base == "git":
                rest = seg[1:]
                gdir = None
                if len(rest) >= 2 and rest[0] == "-C":
                    gdir, rest = rest[1], rest[2:]
                sub = next((r for r in rest if not r.startswith("-")), None)
                flags = [r for r in rest if r.startswith("-")]
                # HISTORY, WHICH NO SCOPE COVERS (P-12b). Judged first, because
                # `commit` and `add` are otherwise index operations and pass:
                # `git commit --amend` and `git add -A` are the two forms that
                # have actually corrupted work here, and both went unjudged
                # while `stash` and `rebase` -- which nobody reached for --
                # were refused. The rule lived in a protocol file read at
                # dispatch and was violated hours later at a commit prompt,
                # which is where this guard already stands.
                bare = [r for r in rest[1:] if not r.startswith("-")] if sub else []
                if ((sub == "commit" and "--amend" in flags)
                        or (sub == "add" and (set(flags) & {"-A", "--all"} or "." in bare))
                        or (sub == "reset" and "--hard" in flags)
                        or sub in ("rebase", "stash", "cherry-pick", "am", "filter-branch")):
                    yield (resolve(gdir if gdir is not None else ".", eff),
                           f"git {sub}" + (" --amend" if "--amend" in flags else ""),
                           "history")
                elif sub in GIT_OUTWARD:
                    yield resolve(gdir if gdir is not None else ".", eff), f"git {sub}", "outward"
                elif sub in GIT_INDEX:
                    yield resolve(gdir if gdir is not None else ".", eff), f"git {sub}", "index"
                elif sub in GIT_TREE:
                    # An EXPLICIT `-- <paths>` names what this touches, and is
                    # far more precise than the repository root. `git reset --
                    # src/a.py` unstages one file and was judged as though it
                    # were `git reset --hard` over the whole tree, because the
                    # pathspec was never read. Only the `--` form is trusted:
                    # without it, `git checkout <branch>` and `git clean -fd`
                    # touch everything, so the root stays the target.
                    paths = rest[rest.index("--") + 1:] if "--" in rest else []
                    if paths:
                        for a in paths:
                            r = resolve(a, eff)
                            if r:
                                yield r, f"git {sub} -- {a}", "tree"
                    else:
                        yield resolve(gdir if gdir is not None else ".", eff), f"git {sub}", "tree"


def find_project(start):
    """Nearest ancestor containing a devteam/ directory, or None."""
    cur = os.path.realpath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "devteam")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().split("\n")
    except OSError:
        return []


def load_state(project):
    """(protected paths, live scopes, writer line) for this project."""
    devteam = os.path.join(project, "devteam")

    protected = []
    for line in read(os.path.join(devteam, "CHARTER.md")):
        m = PROTECTED_ROW.match(line)
        if m:
            for raw in re.split(r"[,;]", m.group(1)):
                raw = raw.strip().strip("`").strip()
                if not raw or PLACEHOLDER.search(raw) or raw.lower() in ("none", "n/a"):
                    continue
                p = os.path.expanduser(raw)
                protected.append(os.path.realpath(
                    p if os.path.isabs(p) else os.path.join(project, p)))

    live = {}
    tasks_dir = os.path.join(devteam, "tasks")
    for name in sorted(os.listdir(tasks_dir)) if os.path.isdir(tasks_dir) else []:
        if not name.endswith(".md"):
            continue
        ident = status = None
        scope, collecting = [], False
        for line in read(os.path.join(tasks_dir, name)):
            m = TITLE.match(line)
            if m and ident is None:
                ident, status = m.group(1), m.group(3).strip()
                continue
            if SCOPE_FIELD.match(line):
                collecting = True
                continue
            if collecting:
                item = SCOPE_ITEM.match(line)
                if item:
                    scope.append(item.group(1))
                    continue
                if line.strip() and (ANY_FIELD.match(line) or line.startswith("#")):
                    collecting = False
        if ident and status and status.startswith("RUNNING"):
            paths = []
            for raw in scope:
                raw = raw.strip().strip("`")
                if not raw or PLACEHOLDER.search(raw) or raw.startswith("~") or os.path.isabs(raw):
                    continue
                if ".." in raw.split("/"):
                    continue
                paths.append(os.path.realpath(os.path.join(project, raw)))
            live[ident] = paths

    writer = None
    for line in read(os.path.join(devteam, "BOARD.md")):
        m = WRITER.match(line)
        if m:
            writer = m.group(1)
            break
    return protected, live, writer


def lock_state(writer, session):
    """Whose run this is: `vacant`, `mine`, `theirs`, or `unknown`.

    `unknown` means the payload carried no session id, and it is deliberately
    NOT merged into `theirs`. Every caller treats unknown the same as mine --
    it keeps policing -- because a guard that goes quiet when it cannot
    identify the writer is the failure this project has already had once: the
    scope rule was inert for an entire rehearsal and nothing said so.
    """
    if writer is None or re.search(r"\bnone\b", writer) or PLACEHOLDER.search(writer):
        return "vacant"
    if not session:
        return "unknown"
    return "mine" if session in re.findall(r"[0-9A-Za-z_-]+", writer) else "theirs"


def history_refusal(what, live):
    """Why a history rewrite is refused, for both the stranger and the run."""
    return (f"Refused: `{what}` while {', '.join(sorted(live))} "
            f"{'is' if len(live) == 1 else 'are'} claimed. Declared scopes "
            "divide the working tree; they do not divide the branch, the "
            "index or HEAD, which every task in flight shares \u2014 and the "
            "manager is committing to the same tree as every worker, so "
            "HEAD is not yours even at width 1 (P-12b).\n\n"
            "A worker ran `git commit --amend` on what it believed was its "
            "own commit, landed on a concurrent task's, merged its report "
            "into that task's subject and rewrote its hash. Another agent's "
            "`git add -A` swept a worker's in-flight files into the "
            "manager's commit. Neither violated any scope.\n\n"
            "If this repository is not the one you meant, that is the more "
            "likely explanation: a shell left in another project's directory "
            "is how this is usually reached. Use `git -C <repo>` rather than "
            "relying on the working directory.\n\n"
            "To correct a commit, ADD ANOTHER ONE \u2014 a step may take two, "
            "and post-commit evidence is why. To stage, name the paths: "
            "`git commit -F \"$msgfile\" -- <paths>`. If a rewrite has "
            "already happened, recover with `git reset --soft` to the "
            "original from `git reflog`, never `--hard`: soft leaves the "
            "index and working tree untouched, and the tree holds other "
            "tasks' uncommitted work.")


def judge(target, what, session, session_project, cache, category="write"):
    """None, or a refusal reason for a target this session may not write.

    The project is discovered by walking up from the TARGET, not from the
    session's own directory. The guard's own rule is that a write is judged by
    its target; deriving the project from the session broke that rule one
    level up, and made the guard silently inert for every write into a project
    the session did not happen to be inside -- which is every subagent, since
    they inherit the parent's project directory. It was disabled for an entire
    rehearsal before a deliberate violation went through unrefused.
    """
    if target is None:
        return None

    # PROTECTED PATHS ARE CHECKED FIRST, AND FROM THE SESSION'S OWN PROJECT.
    # They were previously read only from the project containing the TARGET, so
    # a write outside every devteam project returned early and was never judged
    # -- which is every sibling repository, the case this guard's own docstring
    # advertises by name. The declaring project is the one whose charter names
    # the path, so that is the charter to consult, wherever the target lands.
    home = find_project(session_project)
    if home is not None:
        if home not in cache:
            try:
                cache[home] = load_state(home)
            except OSError:
                cache[home] = ([], {}, None)
        for prot in cache[home][0]:
            if inside(target, prot):
                return (f"Refused: {what} targeting {prot}, which this project's "
                        "charter declares a protected path. It is read-only from "
                        "here -- reading, grepping and listing it are fine. If it "
                        "genuinely needs a change, that is a question for the "
                        "client, not an edit (P-39): a permission the pipeline "
                        "does not have is a stop, never a workaround.")

    # From the TARGET, not its parent. `dirname` started the search one level
    # too high, so a target that IS a project root found no project and went
    # unjudged -- which is precisely what every `git -C <root> …` resolves to.
    # `git reset --hard`, `git clean -fd` and `git push` were all allowed at a
    # project root while `touch <root>/x` on the same project was refused.
    project = find_project(target)
    if project is None:
        return None                           # not inside any devteam project
    if project not in cache:
        try:
            cache[project] = load_state(project)
        except OSError:
            return None
    protected, live, writer = cache[project]
    devteam = os.path.join(project, "devteam")
    board = os.path.join(devteam, "BOARD.md")

    for p in protected:
        if inside(target, p):
            return (f"Refused: {what} targeting {p}, which the charter declares a "
                    "protected path. It is read-only from this project — reading, "
                    "grepping and listing it are fine. If it genuinely needs a "
                    "change, that is a question for the client, not an edit "
                    "(P-39): a permission the pipeline does not have is a stop, "
                    "never a workaround.")

    if inside(target, devteam):
        if target == board:
            return None                       # the board IS the lock
        # A writer line still holding its template placeholder is VACANT, not
        # held by someone else. Reading `<session id>` as another session
        # locked every new project out of its own devteam/ on the first write
        # after setup, and taught managers that forcing a lock takeover is a
        # routine move. The same script already treats `<…>` as unfilled in
        # scope entries and protected paths.
        state = lock_state(writer, session)
        # An EXACT token match. `session in writer` is a substring test, and a
        # short id matched inside an ordinary word -- "me" inside "names" --
        # handing the lock to a session that never held it.
        if state in ("vacant", "mine"):
            return None
        return (f"Refused: {what} into devteam/, and BOARD.md names another session "
                f"as its writer (this session is {session or 'unknown'}). One "
                "writer here (P-13). If that session is gone, take the lock: set "
                "the `**Writer.**` line to this session's id — BOARD.md itself is "
                "always writable — and record the takeover in RECORD.md.")

    # THE PIPELINE POLICES ITS OWN AGENTS, IT DOES NOT CLAIM THE REPOSITORY.
    # Everything below divides work among the agents of ONE run: declared
    # scopes (P-12) and the outward-facing refusal (P-26) are both statements
    # about what this run's own workers may do. They are not authority over
    # anyone else's session. Creating a `devteam/` directory used to silently
    # make this guard the arbiter of every write anywhere in the tree, by any
    # session -- so a repository that already had an owner got intermittent
    # refusals in that owner's session, for reasons originating in a run they
    # were not part of. A real user read that in the docs and declined to
    # trial the pipeline at all, which is the correct reading: two lock
    # regimes over one tree is not a thing to discover at width 3.
    #
    # `devteam/` itself stays tree-scoped above, and so do protected paths:
    # that directory IS the run, and its lock (P-13) is exactly the rule that
    # has to hold against a session that is not part of it.
    # HISTORY IS THE RUN, LIKE `devteam/` IS, SO IT IS DEFENDED AGAINST A
    # STRANGER TOO -- and this check therefore sits ABOVE the stranger exit
    # below rather than with the scope rules.
    #
    # The distinction that keeps this from being the over-reach that turned a
    # real team away: we do not police a stranger's WRITES to the product tree,
    # because those are theirs. We refuse operations on THIS RUN'S shared index
    # and history while a claim is live, for exactly the reason `devteam/` is
    # refused -- P-12b says no scope covers history, so nothing else can.
    #
    # Found by nearly doing it: a session with a shell left in another
    # project's directory ran `git add -A && git commit` against a live run's
    # repository. It short-circuited on an unrelated error, which is luck
    # rather than a control. Expecting anyone -- person or agent -- to
    # remember `git -C` every time is not a mechanism.
    if category == "history" and live:
        return history_refusal(what, live)

    if lock_state(writer, session) == "theirs":
        return None

    if category == "outward":
        return (f"Refused: `{what}` from inside a devteam project. Publishing is "
                "outward-facing and IRREVERSIBLE (P-26) — it is the client's to "
                "do, at the moment it matters, not a standing grant. Fetching "
                "moves refs under a working tree a task is claiming. If this is "
                "genuinely needed, it is a question for the client.")

    if inside(session_project, project) and not live:
        return None                           # the author's own project, loop idle
    if not live:
        return None                           # no claim is in flight; nothing to police

    if category == "history":
        return history_refusal(what, live)

    if category == "index":
        # Staging and committing touch the index and refs. They cannot write a
        # working-tree file that was not already written, and that write was
        # judged when it happened. Refusing these would make every step's
        # commit impossible, which is why one undifferentiated GIT_WRITE set
        # could not be enforced at all.
        return None

    for paths in live.values():
        for p in paths:
            if inside(target, p):
                return None

    running = ", ".join(sorted(live))
    return (f"Refused: {what} to a path no live task has claimed, while {running} "
            f"is running. A task declares the paths it writes and a worker stays "
            "inside them (P-10, P-12) — that is what keeps two agents out of one "
            "file. If this task genuinely needs this path, that is an escalation "
            "to widen its scope, not a write outside it.\n\n"
            "If you hold no claim at all — verifying, auditing, or building a "
            "mutation to test a check — then no scope can ever cover you, and "
            "this refusal is not about the path. Work outside the repository: "
            "`T=$(mktemp -d); git -C \"$REPO\" archive HEAD | tar -x -C \"$T\"` "
            "gives you the committed tree to mutate, the guard does not police "
            "it, and cleaning it up afterwards is fine. A verifier that treats "
            "this refusal as 'mutation is unavailable' downgrades an "
            "independent re-measurement to an independent reading.\n\n"
            "Do not reach for an interpreter to do the same write. A heredoc "
            "like `python3 - <<PY` cannot be classified from the command text, "
            "so it is not refused — that is a known limit of this guard, not "
            "permission. It is the first thing anyone finds after this message "
            "and it does not feel like evasion, which is exactly why it is "
            "named here. The write still lands outside your scope, and "
            "`check_scope` reports it as `undeclared-write` against your task "
            "the moment you commit, or as `foreign-write` before that. You "
            "would be trading a refusal you can escalate for a finding with "
            "your name on it.")


def main():
    if (os.environ.get("DEVTEAM_GUARD") or "").lower() in ("off", "0", "false"):
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Bash", "Write", "Edit", "NotebookEdit"):
        return 0

    cwd = os.path.realpath(data.get("cwd") or os.getcwd())
    session_project = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    cache = {}
    session = str(data.get("session_id") or "")
    ti = data.get("tool_input") or {}

    reason = None
    if data["tool_name"] == "Bash":
        # A newline separates commands as surely as `;`. Without this the line
        # after a heredoc is swallowed into the interpreter's segment.
        cmd = strip_heredocs(ti.get("command") or "").replace("\n", " ; ")
        for target, what, category in targets(cmd, cwd):
            reason = judge(target, what, session, session_project, cache, category)
            if reason:
                break
    else:
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        reason = judge(resolve(path, cwd), "a direct write", session,
                       session_project, cache)

    if reason is None:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
