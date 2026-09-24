#!/usr/bin/env python3
"""PreToolUse hook: in a devteam project, an agent's commit is made by the gate
(roadmap 0.3.1, L-1.7; P-49).

`gate.py commit` checks a commit before it exists and then makes exactly that
commit. That only matters if an agent cannot commit some other way, and the run
this pipeline was measured on committed over red findings because nothing tied
a check's answer to the commit. So, from an agent session outside a sandbox,
this refuses two things in a devteam project at the moment they are typed:

1. EVERY GIT COMMAND THAT WRITES A COMMIT -- `commit` in any form, `merge`,
   `cherry-pick`, `revert`, `am`, `rebase`, `pull`, `commit-tree`,
   `filter-branch`, `filter-repo` and `fast-import` -- except its forms that
   write none: `--no-commit`, `--squash`, `--abort`, `--quit`, `--dry-run`,
   and help.
2. EVERY COMMAND THAT POINTS A BRANCH AT A COMMIT NO BRANCH HOLDS -- `reset`,
   `update-ref`, `branch`, `checkout -b/-B`, `switch -c/-C`, `worktree add`,
   `stash branch`, and a fetch or push into a local branch. The gate refuses a
   commit after building it, so the refused commit exists, and so does
   anything `commit-tree` made. Moving a branch to one lands a commit nobody
   checked. A commit is HELD when a local branch reaches it, or when the moved
   branch's own reflog records it. So P-12b's recovery -- `git reset --soft`
   to a commit from `git reflog` -- is never refused.

Both were settled by the owner on 2026-09-24 ("Close it structurally"), over
refusing `git commit` alone. HEAD counts through the branch it names. A
detached HEAD is not a branch: moving it is not refused, and it holds nothing,
so a branch created at it is tested like any other.

"A devteam project" is the gate's own test (`gate.locate`): the top level of
the work tree git resolves -- from the command's directory, `-C`, `--git-dir`,
`--work-tree` and `GIT_DIR`, as git itself resolves them -- holds `devteam/`.
It is not guard.py's walk upward for any `devteam/` directory, which finds one
inside this plugin's own repository, at `plugins/devteam/`.

WHAT IS READ, AND HOW FAR. The command text is read as a shell reads it, as far
as the text shows: `;`, `&&`, `||`, pipes and subshells; `cd`, `pushd` and
`popd`; variables assigned or exported earlier in the same command; `$(...)`,
backticks and `<(...)`; heredocs and here-strings fed to a shell; `sh -c` and
`bash -c`; `eval`; the wrappers in WRAPPERS; and git's own aliases, including
`!` shell aliases. What the text cannot settle is refused only where it
matters. A commit whose directory or target cannot be read is refused if the
session is working in a devteam project, and asked to name it literally.

KNOWN LIMITS, NAMED IN EVERY REFUSAL: an interpreter or a script file that
runs git (`python3 -c`, `bash ./x.sh`, `make`); a write under `.git` itself.
Named here, not in the refusal: a wrapper not in WRAPPERS (`find -exec`,
`parallel`); another tool than Bash that runs a command; `git replace`, which
changes what a commit appears to contain without moving a branch; a refspec a
repository's config supplies rather than the command. A commit made through
any of these is unchecked, and the next gate run counts what it added as
standing rather than refusing it.

EXEMPT: a worker inside a sandbox, because promotion gates its commits (P-44).
DEVTEAM_SANDBOX is read from THIS HOOK'S environment, which the sandbox's
mount plan sets; a `DEVTEAM_SANDBOX=1` prefix in the command text sets it for
the command only, and exempts nothing. The client's own terminal runs no hook.

The refusal families have names in the code, emitted through `add(...)`, so
docs/CHECKS.md lists them and `check_plugin` diffs the two. guard.py's
families have none (CHECKS.md, CONSOLIDATION N-2), and a control can then only
match message text.

Set DEVTEAM_COMMIT_GUARD=off to disable. Reads PreToolUse JSON on stdin; prints
a deny decision, or nothing; exits 0. Control: test_commit_guard.py.
"""
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
GATE = os.path.join(HERE, "gate.py")
FORMATS = os.path.join(os.path.dirname(HERE), "templates", "FORMATS.md")
MAX_DEPTH = 8

# --- the commands --------------------------------------------------------------

# Each command that writes a commit, and its options that make it write none.
# `merge --no-commit` still fast-forwards, so it counts only with `--no-ff`, and
# `cherry-pick -n` / `revert -n` are read out of short-option clusters below.
WRITERS = {
    "commit": {"--dry-run", "--porcelain", "--short", "--long"},
    "merge": {"--abort", "--quit", "--squash"},
    "cherry-pick": {"--abort", "--quit", "--no-commit"},
    "revert": {"--abort", "--quit", "--no-commit"},
    "am": {"--abort", "--quit", "--show-current-patch"},
    "rebase": {"--abort", "--quit", "--show-current-patch", "--edit-todo"},
    "pull": set(),
    "commit-tree": set(),
    "filter-branch": set(),
    "filter-repo": set(),
    "fast-import": set(),
}
# What each writer's refusal says to do instead.
INSTEAD = {
    "revert": "`git revert --no-commit <commit>` stages the same change without a commit. "
              "Then run `git revert --quit`, because the gate makes ordinary commits only and "
              "will not run while a revert is in progress, and commit the paths it changed "
              "through the gate.",
    "cherry-pick": "`git cherry-pick --no-commit <commit>` stages the same change without a "
                   "commit. Then run `git cherry-pick --quit`, because the gate makes ordinary "
                   "commits only and will not run while a cherry-pick is in progress, and "
                   "commit the paths it changed through the gate.",
    "merge": "`git merge --squash <branch>` stages the merged content without a commit; commit "
             "its paths through the gate.",
    "am": "`git apply <patch>` applies it without a commit; commit its paths through the gate.",
    "commit-tree": "`commit-tree` is how the gate itself makes a commit. Typed by hand it is the "
                   "same commit with the checks left out.",
}
REWRITES = ("rebase", "pull", "filter-branch", "filter-repo", "fast-import")

# Git's own subcommands. An alias cannot shadow one (git ignores it), so only
# a word outside this set is looked up as an alias -- which costs a git call.
BUILTINS = set("""
add am annotate apply archive bisect blame branch bugreport bundle cat-file check-attr
check-ignore check-mailmap check-ref-format checkout checkout-index cherry cherry-pick citool
clean clone column commit commit-graph commit-tree config count-objects credential
credential-cache credential-store describe diagnose diff diff-files diff-index diff-tree
difftool fast-export fast-import fetch fetch-pack filter-branch fmt-merge-msg for-each-ref
for-each-repo format-patch fsck gc get-tar-commit-id grep gui hash-object help hook
http-backend index-pack init init-db instaweb interpret-trailers log ls-files ls-remote
ls-tree mailinfo mailsplit maintenance merge merge-base merge-file merge-index
merge-one-file merge-tree mergetool mktag mktree multi-pack-index mv name-rev notes
pack-objects pack-redundant pack-refs patch-id prune prune-packed pull push range-diff
read-tree rebase receive-pack reflog remote repack replace request-pull rerere reset restore
rev-list rev-parse revert rm send-email send-pack shortlog show show-branch show-index
show-ref sparse-checkout stage stash status stripspace submodule switch symbolic-ref tag
unpack-file unpack-objects update-index update-ref update-server-info upload-archive
upload-pack var verify-commit verify-pack verify-tag version whatchanged worktree
write-tree
""".split())

# git's own options that take the next word as their value.
GIT_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix",
              "--config-env", "--attr-source"}
# git's own options after which no subcommand runs.
GIT_TERMINAL = {"-h", "--help", "-v", "--version", "--html-path", "--man-path",
                "--info-path", "--list-cmds", "--exec-path"}

SHELLS = {"sh", "bash", "dash", "zsh", "ksh", "mksh", "ash", "yash", "posh"}
SHELL_VALUED = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
# A command that runs the rest of its words as a command: (its options that
# take a value, how many positional words come before the command).
WRAPPERS = {
    "command": ((), 0), "builtin": ((), 0), "exec": (("-a",), 0), "nohup": ((), 0),
    "time": (("-f", "--format", "-o", "--output"), 0), "setsid": ((), 0),
    "nice": (("-n", "--adjustment"), 0), "chronic": ((), 0), "unbuffer": ((), 0),
    "timeout": (("-s", "--signal", "-k", "--kill-after"), 1),
    "stdbuf": (("-i", "--input", "-o", "--output", "-e", "--error"), 0),
    "watch": (("-n", "--interval"), 0),
    "xargs": (("-a", "--arg-file", "-d", "--delimiter", "-E", "-I", "-L", "-n", "--max-args",
               "-P", "--max-procs", "-s", "--max-chars", "--process-slot-var"), 0),
    "flock": (("-w", "--wait", "--timeout", "-E", "--conflict-exit-code"), 1),
    "sudo": (("-u", "--user", "-g", "--group", "-C", "--close-from", "-h", "--host", "-p",
              "--prompt", "-r", "--role", "-t", "--type", "-T", "--command-timeout", "-U",
              "--other-user", "-D", "--chdir"), 0),
    "doas": (("-u", "-C"), 0),
    "env": (("-u", "--unset", "-C", "--chdir", "-S", "--split-string"), 0),
}
# Words that begin a compound command and are followed by one. `time` is a
# wrapper above; `!` negates the command after it.
KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{"}
# Words that begin something that is not a command to run.
NOT_COMMANDS = {"for", "case", "select", "function", "}", "fi", "done", "esac", "in"}

SEPARATORS = {"&&", "||", ";", ";;", ";&", ";;&", "|", "|&", "&"}
REDIRECT = re.compile(r"^(?:[<>]|>>|&>|&>>|>&|<&|>\||<>|<<<)$")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*=")
VAR = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z_0-9]*)\}|([A-Za-z_][A-Za-z_0-9]*))")
SUBST = "__devteam_subst_{}__"
HEREDOC = "__devteam_heredoc_{}__"
MARK = re.compile(r"__devteam_(subst|heredoc)_(\d+)__")
DELIM = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([^\s;&|<>()'\"]+))")
# A command naming git with a word that could write a commit: what the hook
# refuses on its own failure, where the session is in a devteam project.
COMMITISH = re.compile(r"\bgit\b|\bgit-[a-z]")


class Unknown(str):
    """A word whose value the command text does not show: a substitution, a
    variable nobody assigned in the text, or a directory after `cd -`."""


class Invocation:
    """One git command the text runs: its words, where it runs, its environment."""

    def __init__(self, words, cwd, env):
        self.words, self.cwd, self.env = words, cwd, env


# --- reading the text as a shell reads it -----------------------------------------

def close_paren(text, i):
    """The index of the `)` that closes the `(` at `i`, or len(text)."""
    depth, j, n, quote = 0, i, len(text), None
    while j < n:
        c = text[j]
        if quote:
            if c == "\\" and quote == '"':
                j += 2
                continue
            if c == quote:
                quote = None
        elif c == "\\":
            j += 2
            continue
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n


def close_backtick(text, i):
    """The index of the backtick that closes the one at `i`, or len(text)."""
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == "`":
            return j
        j += 1
    return len(text)


def read_body(text, i, word, strip):
    """(heredoc body, index after its terminator line), reading from `i`."""
    lines, n = [], len(text)
    while i < n:
        j = text.find("\n", i)
        line = text[i:] if j < 0 else text[i:j]
        i = n if j < 0 else j + 1
        if (line.lstrip("\t") if strip else line) == word:
            return "\n".join(lines), i
        lines.append(line)
    return "\n".join(lines), n


def scan(text, body=False):
    """(command text, heredocs, substitutions).

    Comments and line continuations are removed, every unquoted newline becomes
    `;`, and each heredoc body and each command substitution is taken out and
    replaced by a marker word, so the tokenizer never sees their contents. A
    heredoc is `[body, quoted]`. With `body`, `text` is an unquoted heredoc's
    body, in which only substitutions are syntax.
    """
    out, heredocs, substs, pending = [], [], [], []
    i, n, quote, word_start = 0, len(text), None, True
    while i < n:
        c = text[i]
        if quote == "'":
            out.append(c)
            quote = None if c == "'" else quote
            i += 1
            continue
        if c == "\\":
            if text.startswith("\\\n", i):
                i += 2
                continue
            out.append(text[i:i + 2])
            i += 2
            word_start = False
            continue
        if text.startswith("$(", i) and not text.startswith("$((", i):
            j = close_paren(text, i + 1)
            substs.append(text[i + 2:j])
            out.append(SUBST.format(len(substs) - 1))
            i, word_start = j + 1, False
            continue
        if c == "`":
            j = close_backtick(text, i)
            substs.append(text[i + 1:j].replace("\\`", "`"))
            out.append(SUBST.format(len(substs) - 1))
            i, word_start = j + 1, False
            continue
        if body or quote == '"':
            if c == '"' and quote == '"':
                quote = None
            out.append(c)
            i += 1
            continue
        if c in "'\"":
            quote, word_start = c, False
            out.append(c)
            i += 1
            continue
        if c == "#" and word_start:
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "<>" and text.startswith("(", i + 1):
            j = close_paren(text, i + 1)
            substs.append(text[i + 2:j])
            out.append(SUBST.format(len(substs) - 1))
            i, word_start = j + 1, False
            continue
        if text.startswith("<<<", i):
            # A here-string. Taken whole: its last two characters are not a heredoc.
            out.append("<<<")
            i, word_start = i + 3, True
            continue
        if text.startswith("<<", i):
            m = DELIM.match(text, i)
            if m:
                word = next(g for g in (m.group(2), m.group(3), m.group(5)) if g is not None)
                quoted = m.group(2) is not None or m.group(3) is not None or bool(m.group(4))
                heredocs.append(["", quoted])
                pending.append((word, m.group(1) == "-", len(heredocs) - 1))
                out.append(" " + HEREDOC.format(len(heredocs) - 1) + " ")
                i, word_start = m.end(), False
                continue
        if c == "\n":
            out.append(" ; ")
            i += 1
            for word, strip, k in pending:
                heredocs[k][0], i = read_body(text, i, word, strip)
            pending, word_start = [], True
            continue
        out.append(c)
        word_start = c in " \t;&|()<>"
        i += 1
    return "".join(out), heredocs, substs


OPERATORS = sorted([";;&", "&>>", "<<<", "&&", "||", ";;", ";&", "|&", ">>", "&>", ">&",
                    "<&", ">|", "<>", ";", "&", "|", "(", ")", "<", ">"], key=len, reverse=True)
LITERAL = "\x01"                             # a `$` the shell does not expand


def words_of(text):
    """The words and operators of scanned text. Quotes are removed from each word,
    and a `$` inside single quotes or escaped is written LITERAL, so that `expand`
    expands exactly the `$` the shell would -- which is what tells
    `bash -c "git -C $R commit"` from `bash -c 'git -C $R commit'`."""
    out, cur, i, n, in_word = [], [], 0, len(text), False
    while i < n:
        c = text[i]
        if c in " \t\n":
            if in_word:
                out.append("".join(cur))
                cur, in_word = [], False
            i += 1
            continue
        op = next((o for o in OPERATORS if text.startswith(o, i)), None)
        if op:
            if in_word:
                out.append("".join(cur))
                cur, in_word = [], False
            out.append(op)
            i += len(op)
            continue
        if c == "~" and not in_word and (i + 1 == n or text[i + 1] in "/ \t;&|()<>"):
            cur.append(os.path.expanduser("~"))
            in_word = True
            i += 1
            continue
        in_word = True
        if c == "\\":
            if i + 1 < n:
                cur.append(LITERAL if text[i + 1] == "$" else text[i + 1])
            i += 2
            continue
        if c == "'":
            j = text.find("'", i + 1)
            j = n if j < 0 else j
            cur.append(text[i + 1:j].replace("$", LITERAL))
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n and text[j + 1] in '$`"\\':
                    cur.append(LITERAL if text[j + 1] == "$" else text[j + 1])
                    j += 2
                    continue
                cur.append(text[j])
                j += 1
            i = j + 1
            continue
        cur.append(c)
        i += 1
    if in_word:
        out.append("".join(cur))
    return out


class State:
    """Where the shell is, and what it has assigned, as the text goes along."""

    def __init__(self, cwd, env=None, shell_vars=None):
        self.cwd = cwd
        self.env = dict(env or {})            # exported, changed from the hook's own
        self.vars = dict(shell_vars or {})    # every assignment, for expansion
        self.dirs = []

    def copy(self):
        st = State(self.cwd, self.env, self.vars)
        st.dirs = list(self.dirs)
        return st


def expand(word, st):
    """The word as the shell would pass it, or Unknown when its value is not in the text."""
    if MARK.search(word):
        return Unknown(word.replace(LITERAL, "$"))
    if "$" not in word:
        return word.replace(LITERAL, "$")
    if "$" in VAR.sub("", word):              # ${x:-y}, $1, $@, $?, $((...)): not expanded here
        return Unknown(word.replace(LITERAL, "$"))
    unknown = []

    def value(m):
        name = m.group(1) or m.group(2)
        v = st.vars.get(name, st.env.get(name, os.environ.get(name, "")))
        if isinstance(v, Unknown):
            unknown.append(name)
        return v
    out = VAR.sub(value, word).replace(LITERAL, "$")
    return Unknown(word.replace(LITERAL, "$")) if unknown or MARK.search(out) else out


def join(cwd, path):
    if isinstance(cwd, Unknown) or isinstance(path, Unknown):
        return Unknown(path)
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))


def invocations(text, st, depth=0):
    """Yield every git Invocation this shell text runs, as far as the text shows,
    updating `st` for what the text does to the shell it runs in."""
    if depth > MAX_DEPTH:
        raise RecursionError(f"nested more than {MAX_DEPTH} deep")
    cleaned, heredocs, substs = scan(text)
    stack, seg = [], []
    for tok in words_of(cleaned) + [";"]:
        if tok in SEPARATORS or tok in ("(", ")"):
            if seg:
                yield from simple(seg, st, heredocs, substs, depth)
            seg = []
            if tok == "(":
                stack.append(st.copy())
            elif tok == ")" and stack:
                # A subshell's `cd` and assignments end with it.
                saved = stack.pop()
                st.cwd, st.env, st.vars, st.dirs = saved.cwd, saved.env, saved.vars, saved.dirs
            continue
        seg.append(tok)


def inner(word, st, heredocs, substs, depth):
    """Yield the invocations of the substitutions and heredoc bodies inside a word."""
    for kind, k in MARK.findall(word):
        k = int(k)
        if kind == "subst" and k < len(substs):
            yield from invocations(substs[k], st.copy(), depth + 1)
        elif kind == "heredoc" and k < len(heredocs) and not heredocs[k][1]:
            # An unquoted heredoc expands its body, substitutions and all.
            _, _, body_substs = scan(heredocs[k][0], body=True)
            for s in body_substs:
                yield from invocations(s, st.copy(), depth + 1)


def simple(seg, st, heredocs, substs, depth):
    """Yield the invocations of one simple command, and apply what it does to `st`."""
    words, stdin, i = [], [], 0
    while i < len(seg):
        t = seg[i]
        if REDIRECT.match(t):
            target = seg[i + 1] if i + 1 < len(seg) else ""
            if t == "<<<":
                stdin.append(target)
            # A file-descriptor number belongs to the redirection: `2>&1`.
            if words and words[-1].isdigit() and t != "<<<":
                words.pop()
            yield from inner(target, st, heredocs, substs, depth)
            i += 2
            continue
        m = MARK.fullmatch(t)
        if m and m.group(1) == "heredoc":
            k = int(m.group(2))
            if k < len(heredocs):
                stdin.append(heredocs[k][0])
            yield from inner(t, st, heredocs, substs, depth)
            i += 1
            continue
        words.append(t)
        i += 1
    for w in words:
        yield from inner(w, st, heredocs, substs, depth)
    local = {}
    while words and ASSIGN.match(words[0]):
        name, value = words[0].split("=", 1)
        local[name] = expand(value, st)
        words = words[1:]
    if not words:
        # A bare assignment: the shell keeps it, and an exported name's value changes.
        st.vars.update(local)
        st.env.update({k: v for k, v in local.items() if k in st.env or k in os.environ})
        return
    yield from command([expand(w, st) for w in words], local, stdin, st, depth)


def command(words, local, stdin, st, depth):
    """Yield the invocations of a command, after its assignments and redirections."""
    while words and words[0] in KEYWORDS:
        words = words[1:]
    if not words or words[0] in NOT_COMMANDS:
        return
    head, args = os.path.basename(words[0]), words[1:]
    env = {**st.env, **local}
    if head in ("cd", "pushd", "popd"):
        if head == "popd":
            st.cwd = st.dirs.pop() if st.dirs else Unknown("popd")
            return
        rest = [a for a in args if a not in ("-L", "-P", "-e", "-@", "--")]
        if head == "pushd":
            st.dirs.append(st.cwd)
        target = rest[0] if rest else os.path.expanduser("~")
        st.cwd = Unknown(target) if target == "-" else join(st.cwd, target)
        return
    if head in ("export", "declare", "typeset", "readonly", "local"):
        for a in args:
            if a.startswith("-"):
                continue
            name, eq, value = a.partition("=")
            if eq:
                st.vars[name] = Unknown(value) if isinstance(a, Unknown) else value
            if head == "export" or "-x" in args:
                st.env[name] = st.vars.get(name, os.environ.get(name, ""))
        return
    if head == "unset":
        for a in args:
            st.vars.pop(a, None)
            st.env.pop(a, None)
        return
    if head == "git" or head.startswith("git-"):
        yield Invocation(words, st.cwd, env)
        return
    if head == "eval":
        # eval runs in THIS shell, so its `cd` and assignments persist.
        yield from invocations(" ".join(args), st, depth + 1)
        return
    if head in SHELLS:
        i, script, flags = 0, None, ""
        while i < len(args) and args[i][:1] in "-+" and args[i] not in ("-", "--"):
            if args[i] in SHELL_VALUED:
                i += 2
                continue
            if not args[i].startswith("--"):
                flags += args[i][1:]
            i += 1
        if "c" in flags and i < len(args):
            script = args[i]
        elif i >= len(args) or args[i] in ("-", "--"):
            script = "\n".join(stdin) or None   # the script is the shell's input
        if script is not None:
            child = State(st.cwd, env, {**env})
            yield from invocations(script, child, depth + 1)
        return
    if head in ("command", "builtin") and args and args[0] not in ("-v", "-V"):
        # These run their command in THIS shell: `command cd x` moves it.
        yield from command([a for a in args if a != "-p"], local, stdin, st, depth + 1)
        return
    if head in WRAPPERS:
        rest, extra, chdir, shell = unwrap(head, args)
        inner_st = st.copy()
        inner_st.env = {**env, **extra}
        if chdir is not None:
            inner_st.cwd = join(st.cwd, chdir)
        if shell is not None:
            yield from invocations(shell, inner_st, depth + 1)
        elif rest:
            yield from command(rest, {}, stdin, inner_st, depth + 1)


def unwrap(head, args):
    """(the command a wrapper runs, environment it adds, directory it enters, or a
    shell string it runs). `command -v` runs nothing."""
    valued, npos = WRAPPERS[head]
    extra, chdir, i = {}, None, 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a.startswith("-") and a != "-":
            name, eq, attached = a.partition("=")
            if head == "command" and a in ("-v", "-V"):
                return [], {}, None, None
            value = attached if eq else (args[i + 1] if name in valued and i + 1 < len(args)
                                         else None)
            if name in ("-C", "--chdir", "-D") and head in ("env", "sudo") and value is not None:
                chdir = value
            if name in ("-S", "--split-string") and head == "env" and value is not None:
                return (shlex.split(value) + args[i + 2 - bool(eq):]), extra, chdir, None
            i += 1 if (eq or name not in valued) else 2
            continue
        if head in ("env", "sudo") and ASSIGN.match(a):
            name, value = a.split("=", 1)
            extra[name] = value
            i += 1
            continue
        break
    rest = args[i:]
    if head == "flock" and len(rest) > 2 and rest[1] in ("-c", "--command"):
        return [], extra, chdir, rest[2]
    if head == "watch" and rest:
        return [], extra, chdir, " ".join(rest)
    return rest[npos:], extra, chdir, None


# --- git ---------------------------------------------------------------------------

def run_git(cwd, args, env=None):
    """A read-only git call. Never a pager, a prompt, or a lock on the index."""
    full = dict(os.environ)
    full.update(env or {})
    full.update(GIT_PAGER="cat", GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                          env=full, timeout=5)


def existing(path):
    """The nearest directory at or above `path` that exists: a `mkdir x && cd x`
    earlier in the same command has not run yet when the hook reads it."""
    while path and not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path or "/"


def toplevel(cwd, globs=(), env=None):
    """The top level of the work tree git resolves here: a path, None when git
    finds no work tree, or Unknown when the text does not say where it runs."""
    if isinstance(cwd, Unknown):
        return cwd
    bad = next((g for g in globs if isinstance(g, Unknown)), None)
    if bad is not None:
        return Unknown(bad)
    p = run_git(existing(cwd), [*globs, "rev-parse", "--show-toplevel"], env)
    out = p.stdout.strip()
    return os.path.realpath(out) if p.returncode == 0 and out else None


def is_project(top):
    """The gate's test for a devteam project (`gate.locate`)."""
    return bool(top) and not isinstance(top, Unknown) and os.path.isdir(os.path.join(top, "devteam"))


def parse_git(words):
    """(options to replay, the directories -C names, subcommand, its arguments)."""
    head = os.path.basename(words[0])
    if head != "git":
        return [], [], head[len("git-"):], list(words[1:])
    args, globs, dirs, i = list(words[1:]), [], [], 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        name = a.split("=", 1)[0]
        if name in GIT_TERMINAL and "=" not in a:
            return globs, dirs, None, []
        if a == "-C":
            dirs.append(args[i + 1] if i + 1 < len(args) else "")
            i += 2
            continue
        if name in GIT_VALUED and "=" not in a:
            globs += [a, args[i + 1] if i + 1 < len(args) else ""]
            i += 2
            continue
        globs.append(a)
        i += 1
    return globs, dirs, (args[i] if i < len(args) else None), args[i + 1:]


def before_dashes(args):
    return args[:args.index("--")] if "--" in args else args


def asks_for_help(args):
    return any(a in ("-h", "--help") for a in before_dashes(args))


def writes(sub, args):
    """Does this subcommand, with these arguments, write a commit?"""
    if sub not in WRITERS:
        return False
    opts = before_dashes(args)
    names = {a.split("=", 1)[0] for a in opts if a.startswith("--")}
    if names & WRITERS[sub]:
        return False
    if sub == "merge" and {"--no-commit", "--no-ff"} <= names:
        return False
    if sub in ("cherry-pick", "revert"):
        skip = False
        for a in opts:
            if skip:
                skip = False
                continue
            if a in ("-m", "-X", "--mainline", "--strategy", "--strategy-option"):
                skip = True
                continue
            if a.startswith("-") and not a.startswith("--"):
                for letter in a[1:]:
                    if letter == "n":
                        return False
                    if letter in "mXS":
                        break
    return True


def positionals(args, valued=()):
    """(positional words before `--`, words after `--` or None, option names, option values)."""
    pos, names, values, i = [], set(), {}, 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return pos, args[i + 1:], names, values
        if a.startswith("-") and a != "-":
            name, eq, attached = a.partition("=")
            names.add(name)
            if eq:
                values[name] = attached
            elif name in valued:
                values[name] = args[i + 1] if i + 1 < len(args) else ""
                i += 2
                continue
            i += 1
            continue
        pos.append(a)
        i += 1
    return pos, None, names, values


BRANCH_LISTING = {"-l", "--list", "-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose",
                  "--show-current", "-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C",
                  "--copy", "-u", "--set-upstream-to", "--unset-upstream", "--edit-description",
                  "--contains", "--no-contains", "--merged", "--no-merged", "--points-at",
                  "--format", "--sort"}
FOREIGN = "the fetched commit"


def moves(sub, args, repo):
    """[(branch, target)]: each branch this command points at a commit. `branch` is a
    full ref, "HEAD" for the branch HEAD names, or "stdin"; `target` is the word naming
    the commit, Unknown, or FOREIGN."""
    if sub == "reset":
        pos, after, names, values = positionals(args, {"--pathspec-from-file"})
        if names & {"-p", "--patch", "--pathspec-from-file"} or after or len(pos) != 1:
            return []                       # the index only, or no commit named
        # `git reset <path>` names no commit, and is passed where the commit is looked up.
        return [("HEAD", pos[0])]
    if sub == "update-ref":
        pos, after, names, values = positionals(args, {"-m"})
        if "--stdin" in names:
            return [("stdin", None)]
        if names & {"-d", "--delete"} or len(pos) < 2:
            return []
        ref, new = pos[0], pos[1]
        if isinstance(ref, Unknown):
            return [(ref, new)]
        if ref == "HEAD":
            return [] if "--no-deref" in names else [("HEAD", new)]
        return [(ref, new)] if ref.startswith("refs/heads/") else []
    if sub == "branch":
        pos, after, names, values = positionals(args, {"-u", "--set-upstream-to", "--format",
                                                       "--sort", "--contains", "--no-contains",
                                                       "--merged", "--no-merged", "--points-at"})
        if names & BRANCH_LISTING or not pos:
            return []
        return [(f"refs/heads/{pos[0]}", pos[1] if len(pos) > 1 else "HEAD")]
    if sub in ("checkout", "switch"):
        create = ("-b", "-B") if sub == "checkout" else ("-c", "-C", "--create", "--force-create")
        pos, after, names, values = positionals(args, set(create) | {"--orphan",
                                                                    "--pathspec-from-file"})
        if "--orphan" in names or "--detach" in names or (sub == "switch" and "-d" in names):
            return []
        for opt in create:
            if opt in values:
                return [(f"refs/heads/{values[opt]}", pos[0] if pos else "HEAD")]
        if after is None and len(pos) == 1 and not names & {"-p", "--patch"}:
            if names & {"-t", "--track"} and "/" in pos[0]:
                return [(f"refs/heads/{pos[0].split('/', 1)[1]}", pos[0])]
            guessed = None if "--no-guess" in names else repo.guess(pos[0])
            if guessed:
                return [(f"refs/heads/{pos[0]}", guessed)]
        return []
    if sub == "worktree":
        if not args or args[0] != "add":
            return []
        pos, after, names, values = positionals(args[1:], {"-b", "-B", "--reason"})
        if names & {"--detach", "--orphan"} or not pos:
            return []
        start = pos[1] if len(pos) > 1 else None
        for opt in ("-b", "-B"):
            if opt in values:
                return [(f"refs/heads/{values[opt]}", start or "HEAD")]
        if start is None:
            name = os.path.basename(pos[0].rstrip("/"))
            return [] if repo.has_branch(name) else [(f"refs/heads/{name}", "HEAD")]
        guessed = None if repo.has_branch(start) else repo.guess(start)
        return [(f"refs/heads/{start}", guessed)] if guessed else []
    if sub == "stash":
        if not args or args[0] != "branch":
            return []
        pos, *_ = positionals(args[1:])
        if not pos:
            return []
        stash = pos[1] if len(pos) > 1 else "stash@{0}"
        return [(f"refs/heads/{pos[0]}", Unknown(stash) if isinstance(stash, Unknown)
                 else f"{stash}^1")]
    if sub in ("fetch", "push"):
        pos, *_ = positionals(args, {"-o", "--server-option", "--upload-pack", "--receive-pack",
                                     "--exec", "--depth", "--deepen", "--shallow-since",
                                     "--shallow-exclude", "--negotiation-tip", "--refmap", "-j",
                                     "--jobs", "--push-option", "--repo"})
        if len(pos) < 2 or (sub == "push" and pos[0] != "."):
            return []
        out = []
        for spec in pos[1:]:
            src, colon, dst = spec.lstrip("+").partition(":")
            if not colon or not dst or (dst.startswith("refs/") and not dst.startswith("refs/heads/")):
                continue
            ref = dst if dst.startswith("refs/heads/") else f"refs/heads/{dst}"
            out.append((ref, src if pos[0] == "." else FOREIGN))
        return out
    return []


class Repo:
    """The read-only questions the hook asks of one repository."""

    def __init__(self, top, globs, env):
        self.top, self.globs, self.env = top, globs, env

    def git(self, *args):
        return run_git(self.top, [*self.globs, *args], self.env)

    def commit(self, word):
        """The commit a word names, or None."""
        p = self.git("rev-parse", "--verify", "--quiet", "--end-of-options", f"{word}^{{commit}}")
        return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None

    def has_branch(self, name):
        return self.git("show-ref", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0

    def guess(self, name):
        """The remote-tracking branch `checkout <name>` would create a branch from, or None."""
        if isinstance(name, Unknown) or self.has_branch(name) or self.commit(name):
            return None
        refs = self.git("for-each-ref", "--format=%(refname)", f"refs/remotes/*/{name}").stdout.split()
        return refs[0] if len(refs) == 1 else None

    def branch(self):
        """The branch HEAD names, or None when HEAD is detached."""
        return self.git("symbolic-ref", "--quiet", "HEAD").stdout.strip() or None

    def held(self, sha, branch):
        """Does a local branch reach this commit, or has `branch` itself held it?"""
        if self.git("for-each-ref", "--count=1", "--contains", sha, "--format=%(refname)",
                    "refs/heads/").stdout.strip():
            return True
        log = self.git("reflog", "show", "--format=%H", branch, "--")
        return log.returncode == 0 and sha in log.stdout.split()

    def has_devteam_at_head(self):
        return self.git("cat-file", "-e", "HEAD:devteam").returncode == 0


# --- the judgement ------------------------------------------------------------------

def shown(word):
    """A word as a reader would recognise it: a substitution shown as `$(…)`."""
    return MARK.sub("$(…)", str(word)).replace(LITERAL, "$")


def said(words, limit=100):
    text = shown(" ".join(str(w) for w in words))
    return text if len(text) <= limit else text[:limit - 1] + "…"


def judge_invocation(inv, refusals, evidence, depth):
    """Append a refusal for each thing this git invocation does that the gate should."""
    add = lambda kind, where, detail: refusals.append((kind, where, detail))
    globs, dirs, sub, args = parse_git(inv.words)
    what = said(inv.words)
    cwd = inv.cwd
    for d in dirs:
        cwd = cwd if d == "" else join(cwd, d)
    if sub is None or sub == "help" or asks_for_help(args):
        return
    if depth > MAX_DEPTH:
        raise RecursionError(f"aliases nested more than {MAX_DEPTH} deep")
    if sub not in BUILTINS and sub not in WRITERS:
        # An alias, perhaps. `-c alias.x=...` on the command line counts, because
        # the lookup replays the command's own options.
        where = os.path.expanduser("~") if isinstance(cwd, Unknown) else existing(cwd)
        p = run_git(where, [*globs, "config", "--get", f"alias.{sub}"], inv.env)
        expansion = p.stdout.strip() if p.returncode == 0 else ""
        if expansion.startswith("!"):
            text = expansion[1:] + "".join(" " + shlex.quote(str(a)) for a in args)
            for alias_inv in invocations(text, State(cwd, inv.env, inv.env), depth + 1):
                judge_invocation(alias_inv, refusals, evidence, depth + 1)
            return
        if expansion:
            words = ["git", *globs, *shlex.split(expansion), *args]
            judge_invocation(Invocation(words, cwd, inv.env), refusals, evidence, depth + 1)
            return
    writer = writes(sub, args)
    if not writer and sub not in ("reset", "update-ref", "branch", "checkout", "switch",
                                  "worktree", "stash", "fetch", "push"):
        return
    top = toplevel(cwd, globs, inv.env)
    if isinstance(top, Unknown):
        home = evidence()
        if home:
            add("unresolved-repository", str(cwd),
                f"`{what}` would write a commit or move a branch, and the command text does "
                f"not say which repository it runs in (`{shown(top)}` is not in the text), while "
                f"{home}, where this session is working, is a devteam project. Write the "
                "directory literally — `git -C /absolute/path …` — or commit through the "
                "gate.")
        return
    if not is_project(top):
        return
    repo = Repo(top, globs, inv.env)
    if writer:
        why = INSTEAD.get(sub, "")
        if sub in REWRITES:
            why = (f"`git {sub}` writes commits nobody checked. If the history genuinely needs "
                   "it, that is the client's to do, from their own terminal.")
        if not repo.has_devteam_at_head():
            why = ("HEAD holds no devteam/ yet. The scaffold's first commit is the client's, "
                   "made from their own terminal (the `setup` skill), and the gate has nothing "
                   "to compare a commit with until it exists.")
        add("writes-commit", top,
            f"`{what}` writes a commit into {top}, a devteam project, without the gate."
            + (f" {why}" if why else ""))
        return
    for branch, target in moves(sub, args, repo):
        if branch == "stdin":
            add("unresolved-target", top,
                f"`{what}` reads the refs it moves from its input, which the hook cannot see. "
                "Name the ref and the commit on the command line.")
            continue
        if branch == "HEAD":
            branch = repo.branch()
            if branch is None:
                continue                    # a detached HEAD is not a branch
        if isinstance(branch, Unknown) or isinstance(target, Unknown):
            add("unresolved-target", top,
                f"`{what}` points a branch at a commit, and the command text does not name "
                f"{'the branch' if isinstance(branch, Unknown) else 'the commit'} "
                f"(`{shown(branch if isinstance(branch, Unknown) else target)}`), so the hook cannot "
                "tell a recovery from a commit nobody checked. Name it literally.")
            continue
        short = branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else branch
        if target == FOREIGN:
            add("lands-unheld-commit", top,
                f"`{what}` points {short} at a commit fetched from outside this repository, "
                "which its checks have never read. That lands commits nobody checked.")
            continue
        sha = repo.commit(target)
        if sha is None or repo.held(sha, branch):
            continue
        add("lands-unheld-commit", top,
            f"`{what}` points {short} at {sha[:12]}, which no branch holds and {short}'s "
            "reflog does not record. That lands a commit nobody checked, such as a candidate "
            "the gate refused or one `commit-tree` made. Recovering a commit this branch held "
            "is not refused: `git reset --soft` to a commit from `git reflog` (P-12b).")


GATE_FORM = ("A commit to a devteam project is made by the gate. It runs the project's checks "
             "on the commit itself before the commit exists, then makes exactly that commit "
             "(P-49):\n\n"
             "    python3 {gate} commit -F <message file> -- <each path, named>\n\n"
             "It exits 0 committed. It exits 1 refused, naming what the commit adds: fix the "
             "commit, or accept the finding by a decision's `Accepts.` field (the `check` "
             "skill's *Accepting a finding* says how, and {formats}, §\"Accepted findings\", "
             "is the grammar); on `head-moved`, run it again. It exits 2 when it could not "
             "run, and the fault is in the invocation or in the gate. Nothing is committed "
             "on 1 or 2.")
LIMITS = ("Committing another way is not a gap to use. A command this hook cannot read — an "
          "interpreter or a script file that runs git, or a write under .git — still lands a "
          "commit nobody checked, and the next gate run counts what it added as standing "
          "instead of refusing it. A refusal from the gate is a finding to fix or a decision "
          "to take.\n\n"
          "Not refused: a worker inside a sandbox, whose commits promotion gates (P-44), and "
          "the client's own terminal, which runs no hook.\n\n"
          "IF THIS COMMAND HAD OTHER PARTS, NONE OF THEM RAN. A refusal blocks the whole "
          "call. Re-run whatever was chained before the commit.")


def judge(command_text, cwd):
    """[(family, where, detail)] for one Bash command run from `cwd`."""
    if "git" not in command_text:
        return []
    found = {}

    def evidence():
        """The devteam project this session is working in, if any: the call's own
        directory, then the session's project."""
        if "home" not in found:
            found["home"] = None
            for d in (cwd, os.environ.get("CLAUDE_PROJECT_DIR")):
                top = toplevel(d) if d else None
                if is_project(top):
                    found["home"] = top
                    break
        return found["home"]

    refusals = []
    st = State(cwd)
    for inv in invocations(command_text, st):
        judge_invocation(inv, refusals, evidence, 0)
    return refusals


def failed(command_text, cwd, exc):
    """The hook's own failure: refused where a commit could land in a devteam project."""
    refusals = []
    add = lambda kind, where, detail: refusals.append((kind, where, detail))
    if not COMMITISH.search(command_text):
        return refusals
    for d in (cwd, os.environ.get("CLAUDE_PROJECT_DIR")):
        try:
            top = toplevel(d) if d else None
        except Exception:
            top = None
        if is_project(top):
            add("guard-failed", top,
                f"The commit guard could not read this command ({type(exc).__name__}: "
                f"{str(exc)[:120]}), and {top} is a devteam project. If the command writes a "
                "commit, commit through the gate. If it does not, the failure is a defect in "
                "scripts/commit_guard.py: report it with the command.")
            break
    return refusals


def render(refusals):
    leads = []
    for kind, _where, detail in refusals:
        line = f"Refused [{kind}]: {detail}"
        if line not in leads:
            leads.append(line)
    return "\n\n".join(leads + [GATE_FORM.format(gate=GATE, formats=FORMATS), LIMITS])


def main():
    if (os.environ.get("DEVTEAM_COMMIT_GUARD") or "").lower() in ("off", "0", "false"):
        return 0
    if os.environ.get("DEVTEAM_SANDBOX"):
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    command_text = (data.get("tool_input") or {}).get("command") or ""
    cwd = os.path.realpath(data.get("cwd") or os.getcwd())
    try:
        refusals = judge(command_text, cwd)
    except Exception as exc:                  # fails closed where it matters
        refusals = failed(command_text, cwd, exc)
    if refusals:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": render(refusals),
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
