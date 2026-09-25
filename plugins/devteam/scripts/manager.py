#!/usr/bin/env python3
"""The manager's acts, one verb each, each checking its own preconditions
(roadmap 0.3.4, L-4.1; cycle 0.3's L-5).

    manager.py <verb> [<argument> ...] [--dry-run] [--json] [-C <dir>]

THE MANAGER'S FAILURES WERE BOOKKEEPING, and every bookkeeping fix that held
replaced a remembered step with a command (cycle 0.3's §2). So each act the
`run` and `resume` skills ask the manager to repeat is a verb here, and the
skills say only when to call it and what a refusal asks. A verb refuses rather
than proceeding: it exits 1, names the precondition that failed as a class
with a row in docs/CHECKS.md, and says what to do. A verb that cannot run
exits 2, as the result contract says (result.py). Exit 0 is done, and with
`--dry-run`, would be done.

EVERY VERB MEETS THREE PRECONDITIONS, checked here and nowhere else:

1. A SESSION ID. The verb's session is the one `CLAUDE_CODE_SESSION_ID` names.
   The harness sets it in a session's Bash, and in the Bash of an agent that
   session dispatches (MEASURED 2026-09-25, CLI 2.1.282: a subagent printed
   its dispatcher's id). Without one the verb cannot tell whose it is:
   `no-session`.
2. THE LOCK HELD: that id on BOARD.md's `**Writer.**` line at HEAD, read by
   guard.py's four readings (P-11, P-13). Only `mine` holds it. Vacant does
   not: a verb writes `devteam/` for the session that took the lock. HEAD's
   board, not the working tree's, because a verb builds on HEAD and the lock
   moves at the commit that takes it (L-4.9). Why a command checks this at
   all: guard.py judges command text, and it sees no write target in
   `python3 <script>`, so a command that checked nothing would be the way
   around P-13. `lock-not-held`.
3. THE NAMED PATHS' STATE. A path a verb writes has no uncommitted change,
   and no untracked file sits where it creates one, unless the verb carries
   that change as its act says -- a claim carries the manager's edit to the
   task file (L-4.11). So a verb never overwrites an edit it did not make,
   nor commits one under its own subject, and a refusal can put back exactly
   what was there. `uncommitted-path`.

A REFUSAL CHANGES NOTHING. A verb writes whole files, each generated from
what it restates and never typed (F-26), and commits them through the gate's
own function, gate.commit (P-49; L-4.8). The commit is pinned to the HEAD the
verb read the project at, so one built from a project that has since changed
is refused as `head-moved`. If the gate refuses, the dry run ends, or anything
fails, every file the verb wrote and did not commit is put back byte for
byte, and a directory it made is removed: HEAD, the index and the working tree
are as they were (F-24's property). What the gate refused, and what stands,
come back as data and are reported whole: `gate-refused`.

`--json` prints the result as one document, as the gate's does, and the lines
are rendered from that document, so the two cannot disagree. Control:
test_manager.py.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import result  # noqa: E402 -- the exit contract
import gate    # noqa: E402 -- the commit, the project's test, and the lock at a commit
import guard   # noqa: E402 -- the Writer line's four readings, one home (P-34)

USAGE = "usage: manager.py <verb> [<argument> ...] [--dry-run] [--json] [-C <dir>]"
CouldNotRun = gate.CouldNotRun


class Refused(Exception):
    """Exit 1. `args[0]` is the refusals, each {class, where, detail, do}."""


# The verbs, each `fn(ctx, args)` returning the line that says what it did.
# Each is registered by `verb`, and 0.3.4's steps 3.2 to 3.6 add them.
VERBS = {}


def verb(name, usage):
    def register(fn):
        VERBS[name] = (fn, usage)
        return fn
    return register


def usage():
    listed = "; ".join(u for _fn, u in VERBS.values()) or "none is defined yet"
    return f"{USAGE}. The verbs: {listed}"


# --- the three preconditions ----------------------------------------------------

def refusal(kind, where, detail, do):
    return {"class": kind, "where": where, "detail": detail, "do": do}


def session_and_lock(top, head):
    """This session's id, if it holds the lock at HEAD; else Refused.
    Preconditions 1 and 2."""
    refusals = []
    add = lambda kind, where, detail, do: refusals.append(refusal(kind, where, detail, do))
    session = os.environ.get(gate.SESSION, "").strip()
    if not session:
        add("no-session", gate.SESSION,
            f"this process has no {gate.SESSION}, so whether it holds the writer lock cannot "
            "be read",
            "run the verb from the session that holds the lock: the harness sets "
            f"{gate.SESSION} in a session's Bash")
        raise Refused(refusals)
    holder = gate.writer(top, head)
    reading = guard.lock_state(holder, session)
    if reading == "mine":
        return session
    if reading == "vacant":
        add("lock-not-held", gate.BOARD,
            f"BOARD.md's `**Writer.**` line at HEAD {head[:7]} names no session, so nobody "
            "holds the lock",
            "take the lock first (`run` §1.1): a verb writes `devteam/` only for the session "
            "that holds it")
    elif guard.handoff_names(top, session):
        add("lock-not-held", gate.BOARD,
            f"BOARD.md at HEAD {head[:7]} names your successor as its writer "
            f"({gate.named_id(holder)}), and `devteam/.run/session/handoff-ready` names "
            f"this session ({session}) as the outgoing manager",
            "you have been replaced: do not take the lock back, and write nothing (`run` §2, "
            "`resume` §0)")
    else:
        add("lock-not-held", gate.BOARD,
            f"BOARD.md at HEAD {head[:7]} names another session as its writer "
            f"({gate.named_id(holder)}); this session is {session}",
            "only the writer writes `devteam/` (P-13). If that session is gone, taking the "
            "lock is the client's word (`run` §1.1)")
    raise Refused(refusals)


def unchanged(top, rel):
    """Precondition 3 for one path: None, or Refused naming what is there."""
    said = gate.git(top, "--literal-pathspecs", "status", "--porcelain", "-uall", "--",
                    rel).stdout.rstrip("\n")
    if not said:
        return
    code = said.split("\n")[0][:2]
    what = ("an untracked file where this verb would create one" if code == "??"
            else f"an uncommitted change (`{code.strip()}`)")
    refusals = []
    add = lambda kind, where, detail, do: refusals.append(refusal(kind, where, detail, do))
    add("uncommitted-path", rel,
        f"{rel} holds {what}, which this verb did not make",
        "commit it through the gate, or put it back, and run the verb again: a verb never "
        "overwrites an edit it did not make, nor commits one under its own subject")
    raise Refused(refusals)


# --- what a verb reads and writes --------------------------------------------------

class Context:
    """The project a verb acts on, as it stood at `head`, and what it wrote."""

    def __init__(self, top, ref, head, session, dry_run):
        self.top, self.ref, self.head = top, ref, head
        self.session, self.dry_run = session, dry_run
        self.saved = {}       # path -> its bytes before the verb wrote it, or None: absent
        self.made = []        # directories the verb created, deepest last
        self.commits = []     # the gate's document for each commit made

    def path(self, rel):
        return os.path.join(self.top, rel)

    def read(self, rel):
        """The file as the checkout holds it, or None."""
        try:
            with open(self.path(rel), encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return None

    def write(self, rel, text, carried=False):
        """Write a whole file this verb commits. Its first write checks the
        named paths' state, unless the verb carries what is there."""
        if rel not in self.saved:
            if not carried:
                unchanged(self.top, rel)
            try:
                with open(self.path(rel), "rb") as fh:
                    self.saved[rel] = fh.read()
            except FileNotFoundError:
                self.saved[rel] = None
        parent, missing = os.path.dirname(self.path(rel)), []
        while not os.path.isdir(parent):
            missing.append(parent)
            parent = os.path.dirname(parent)
        for d in reversed(missing):
            os.mkdir(d)
            self.made.append(d)
        with open(self.path(rel), "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self, message):
        """Commit what the verb has written since its last commit, through the
        gate, against the HEAD the verb read. Returns the gate's document, or
        raises Refused, and `run` puts the files back."""
        paths = sorted(self.saved)
        if not paths:
            raise CouldNotRun("the verb committed nothing it wrote")
        doc = gate.commit(paths, message, cwd=self.top, dry_run=self.dry_run, expect=self.head)
        self.commits.append(doc)
        if doc["exit"] != result.CLEAN:
            refusals = []
            add = lambda kind, where, detail, do: refusals.append(refusal(kind, where, detail, do))
            add("gate-refused", f"HEAD {doc.get('head', self.head)[:7]}",
                "the gate refused this verb's commit: "
                + ", ".join(r["class"] for r in doc["refused"]),
                "read what the gate refused, below: fix it, or accept a finding by a decision "
                "(the `check` skill), and run the verb again")
            raise Refused(refusals)
        if not self.dry_run:
            self.head, self.saved, self.made = doc["committed"], {}, []
        return doc

    def restore(self):
        """Put back every file written and not committed, byte for byte, and
        remove each directory the verb made that is empty again."""
        for rel, data in self.saved.items():
            if data is None:
                if os.path.lexists(self.path(rel)):
                    os.remove(self.path(rel))
            else:
                with open(self.path(rel), "wb") as fh:
                    fh.write(data)
        for d in reversed(self.made):
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        self.saved, self.made = {}, []


# --- the command ----------------------------------------------------------------

def parse(argv):
    """(verb, its arguments, options), or CouldNotRun."""
    opts = {"json": False, "dry_run": False, "dir": None}
    args, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            opts["json"] = True
        elif a == "--dry-run":
            opts["dry_run"] = True
        elif a == "-C":
            if i + 1 >= len(argv):
                raise CouldNotRun(f"-C needs a directory. {USAGE}")
            opts["dir"] = argv[i + 1]
            i += 1
        else:
            args.append(a)
        i += 1
    if not args:
        raise CouldNotRun(f"no verb. {usage()}")
    if args[0] not in VERBS:
        raise CouldNotRun(f"no verb {args[0]!r}. {usage()}")
    return args[0], args[1:], opts


def run(name, args, cwd=None, dry_run=False):
    """The verb's document. Raises CouldNotRun, having put back what it wrote."""
    top, _common = gate.locate(cwd)
    ref, head = gate.head(top)
    doc = {"schema": result.SCHEMA, "manager": name, "args": args, "head": head,
           "refused": [], "commits": []}
    ctx = None
    try:
        session = session_and_lock(top, head)
        ctx = Context(top, ref, head, session, dry_run)
        said = VERBS[name][0](ctx, args)
        if ctx.saved and not dry_run:
            raise CouldNotRun(f"the verb wrote {', '.join(sorted(ctx.saved))} and did not "
                              "commit it")
    except Refused as exc:
        if ctx:
            ctx.restore()
        made = [c["committed"][:7] for c in (ctx.commits if ctx else []) if c.get("committed")]
        doc.update(refused=exc.args[0], commits=ctx.commits if ctx else [],
                   exit=result.FINDINGS, result="refused",
                   line=(f"manager {name}: refused — {', '.join(r['class'] for r in exc.args[0])}; "
                         + (f"{len(made)} commit(s) made before it ({', '.join(made)})"
                            if made else "nothing was changed")
                         + f"  [HEAD {head[:7]}]"))
        return doc
    except BaseException:
        if ctx:
            ctx.restore()
        raise
    if dry_run:
        ctx.restore()
    doc.update(commits=ctx.commits, exit=result.CLEAN,
               result="would commit" if dry_run else "committed",
               line=f"manager {name}: {said}" + ("  [--dry-run: nothing was changed]" if dry_run
                                                  else ""))
    return doc


def render(doc):
    out = [doc["line"]]
    for r in doc["refused"]:
        out.append(f"  {r['class']:17} {r['where']}  {r['detail']}")
        out.append(f"  {'':17} do: {r['do']}")
    for g in doc["commits"]:
        out += ["  " + line for line in gate.render(g)]
    return out


def main(argv):
    as_json = "--json" in argv[1:]
    try:
        name, args, opts = parse(argv[1:])
        doc = run(name, args, cwd=opts["dir"], dry_run=opts["dry_run"])
    except Exception as exc:
        # A verb that fails, rather than refusing, could not run: exit 1 is a
        # refusal, which says a precondition failed, and this is not one. What
        # it wrote was put back by `run`.
        if not isinstance(exc, CouldNotRun):
            import traceback
            traceback.print_exc()
            exc = f"{type(exc).__name__}: {exc}"
        print(f"manager: could not run — {exc}", file=sys.stderr)
        if as_json:
            json.dump({"schema": result.SCHEMA, "manager": argv[1] if len(argv) > 1 else None,
                       "exit": result.COULD_NOT_RUN, "result": "could not run",
                       "error": str(exc)}, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        return result.COULD_NOT_RUN
    if as_json:
        json.dump(doc, sys.stdout, indent=1, sort_keys=True, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for line in render(doc):
            print(line)
    return doc["exit"]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
