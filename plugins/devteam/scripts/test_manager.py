#!/usr/bin/env python3
"""Negative control for manager.py's frame (P-35; roadmap 0.3.4 §3.1).

The frame is what every verb shares: the three preconditions -- a session
id, the lock held, the named paths' state -- the commit through the gate
against the HEAD the verb read, and a refusal that changes nothing. It is
driven here through fixture verbs a wrapper registers, on the gate control's
own fixture project, with the committing session planted through the
environment. Every refusal is held to F-24's property, as the gate's are:
HEAD, the index and the working tree are exactly as they were.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import test_gate as fx  # noqa: E402 -- the fixture project, one home with the gate's control

SESSION = fx.SESSION

# The fixture verbs. Each is what a real verb does with the frame, reduced to
# the part under test. `race` lets another writer's commit land between its
# read and its commit.
WRAPPER = r'''
import os, subprocess, sys
sys.path.insert(0, {scripts!r})
import manager

def append(ctx, rel, line, carried=False):
    ctx.write(rel, (ctx.read(rel) or "") + line, carried=carried)

@manager.verb("note", "note <text>")
def note(ctx, args):
    append(ctx, "devteam/RECORD.md", f"- {{args[0]}}\n")
    doc = ctx.commit(f"devteam: {{args[0]}}")
    return f"noted, {{doc.get('committed', doc['candidate'])[:7]}}"

@manager.verb("twice", "twice")
def twice(ctx, args):
    append(ctx, "devteam/RECORD.md", "- the first.\n")
    first = ctx.commit("devteam: the first")
    append(ctx, "devteam/RECORD.md", "- the second.\n")
    second = ctx.commit("devteam: the second")
    return "two commits, " + " and ".join(d.get("committed", "")[:7] for d in (first, second))

@manager.verb("carry", "carry")
def carry(ctx, args):
    append(ctx, "devteam/tasks/T-2.md", "- the manager's line.\n", carried=True)
    append(ctx, "devteam/RECORD.md", "- carried.\n")
    ctx.commit("devteam: carried")
    return "carried"

@manager.verb("nocarry", "nocarry")
def nocarry(ctx, args):
    append(ctx, "devteam/tasks/T-2.md", "- the manager's line.\n")
    ctx.commit("devteam: not carried")
    return "not carried"

@manager.verb("create", "create <dir>")
def create(ctx, args):
    ctx.write(f"devteam/{{args[0]}}/x.md", "# x\n")
    ctx.commit("devteam: a new file")
    return "created"

@manager.verb("bad", "bad")
def bad(ctx, args):
    ctx.write("devteam/made/y.md", "# y\n")
    questions = ctx.read("devteam/QUESTIONS.md")
    ctx.write("devteam/QUESTIONS.md", questions.replace("REVERSIBLE", "MAYBE"))
    ctx.commit("devteam: a bad status")
    return "never"

@manager.verb("race", "race")
def race(ctx, args):
    append(ctx, "devteam/RECORD.md", "- raced.\n")
    subprocess.run(["git", "-C", ctx.top, "commit", "-q", "--allow-empty", "-m", "someone else"],
                   check=True)
    ctx.commit("devteam: raced")
    return "never"

@manager.verb("forget", "forget")
def forget(ctx, args):
    append(ctx, "devteam/RECORD.md", "- forgotten.\n")
    return "never"

@manager.verb("boom", "boom")
def boom(ctx, args):
    append(ctx, "devteam/RECORD.md", "- then it fails.\n")
    raise RuntimeError("the verb failed")

sys.exit(manager.main(sys.argv))
'''


def run(wrapper, root, *argv, env=None):
    p = subprocess.run([sys.executable, wrapper, *argv, "-C", root, "--json"],
                       capture_output=True, text=True, env=env or fx.planted({}))
    try:
        doc = json.loads(p.stdout)
    except ValueError:
        doc = None
    return p, doc


# --- what a case asserts ---------------------------------------------------------
# `check(root, proc, doc, before)` returns what is wrong, or "".

def unchanged(root, proc, doc, before):
    return "" if fx.state(root) == before else "HEAD, the index or the working tree moved"


def committed(*paths, n=1):
    def check(root, proc, doc, before):
        log = fx.git(root, "log", f"-{n}", "--format=%H").split()
        made = [c.get("committed") for c in doc.get("commits", [])]
        if len(made) != n or made != log[::-1]:
            return f"the commits made are not the verb's {n}, newest last"
        if fx.git(root, "rev-parse", f"HEAD~{n}").strip() != before[0].strip():
            return f"HEAD~{n} is not the HEAD the verb began at"
        reflog = fx.git(root, "reflog", "show", "--format=%gs", "main", "--").split("\n")[:n]
        if not all(s.startswith("commit (gate): ") for s in reflog):
            return f"not every commit is the gate's: {reflog}"
        for p in paths:
            if fx.git(root, "status", "--porcelain", "--", p).strip():
                return f"{p} is not committed"
        return ""
    return check


def refused_with(**want):
    def check(root, proc, doc, before):
        for kind, text in want.items():
            kind = kind.replace("_", "-")
            if not any(r["class"] == kind and text in r["where"] + " " + r["detail"] + " " + r["do"]
                       for r in doc["refused"]):
                return f"no {kind} refusal mentions {text!r}"
        return ""
    return check


def still_dirty(*paths):
    def check(root, proc, doc, before):
        for p in paths:
            if not fx.git(root, "status", "--porcelain", "--", p).strip():
                return f"{p} is no longer uncommitted"
            if p in fx.git(root, "show", "--name-only", "--format=", "HEAD"):
                return f"{p} was swept into the verb's commit"
        return ""
    return check


def gate_said(kind):
    def check(root, proc, doc, before):
        classes = [r["class"] for c in doc.get("commits", []) for r in c.get("refused", [])]
        return "" if kind in classes else f"the gate's document does not refuse {kind}: {classes}"
    return check


def absent(rel):
    return lambda root, proc, doc, before: (
        f"{rel} is still there" if os.path.exists(os.path.join(root, rel)) else "")


def both(*checks):
    return lambda *a: next((w for w in (c(*a) for c in checks) if w), "")


NOTE = ["note", "a note"]
DIRTY_RECORD = fx.edit({"devteam/RECORD.md": fx.RECORD + "- a hand edit.\n"})
# The manager's edit to a task file not yet claimed -- a claim carries one
# (L-4.11). Into a claimed task's file it would be `misattributed-write`.
AMENDED_T2 = fx.edit({"devteam/tasks/T-2.md": fx.task(2, "tidy the docs", "PLANNED", fx.T2_FIELDS,
                                                       "\n- the manager's edit.\n")})
NOTHING = lambda root: None

# (name, base, edit, argv, environment over the planted S-MGR, exit, refusal classes, check)
CASES = [
    # --- the frame, through the gate --------------------------------------------
    ("fp-a-verb-commits-through-the-gate", fx.WRITTEN, NOTHING, NOTE, {}, 0, set(),
     both(committed("devteam/RECORD.md"),
          lambda root, proc, doc, before: "" if doc["line"].startswith("manager note: noted")
          else f"the line is {doc['line']!r}")),
    ("fp-a-verb-making-two-commits-pins-each-to-the-head-before-it", fx.WRITTEN, NOTHING,
     ["twice"], {}, 0, set(), committed("devteam/RECORD.md", n=2)),
    ("fp-a-dry-run-changes-nothing", fx.WRITTEN, NOTHING, NOTE + ["--dry-run"], {}, 0, set(),
     both(unchanged, lambda root, proc, doc, before: "" if doc["result"] == "would commit"
          and doc["commits"][0]["result"] == "would commit" else "it did not say would commit")),

    # --- precondition 1: a session id ----------------------------------------------
    ("session-no-session-id-is-refused", fx.WRITTEN, NOTHING, NOTE, {SESSION: None}, 1,
     {"no-session"}, refused_with(no_session=SESSION)),
    ("session-a-blank-session-id-is-refused", fx.WRITTEN, NOTHING, NOTE, {SESSION: "  "}, 1,
     {"no-session"}, refused_with(no_session=SESSION)),

    # --- precondition 2: the lock held, at HEAD --------------------------------------
    ("lock-another-sessions-lock-is-refused", fx.WRITTEN, NOTHING, NOTE, {SESSION: "S-OTHER"}, 1,
     {"lock-not-held"}, refused_with(lock_not_held="this session is S-OTHER")),
    ("lock-a-vacant-lock-is-not-held", fx.VACANT, NOTHING, NOTE, {}, 1, {"lock-not-held"},
     refused_with(lock_not_held="names no session")),
    ("lock-a-session-whose-id-is-inside-the-writers-is-refused", fx.WRITTEN, NOTHING, NOTE,
     {SESSION: "MGR"}, 1, {"lock-not-held"}, refused_with(lock_not_held="this session is MGR")),
    ("lock-a-lock-taken-in-the-working-tree-only-is-not-held", fx.WRITTEN,
     fx.edit({"devteam/BOARD.md": fx.board(fx.IN_FLIGHT_T1, writer="S-NEW")}), NOTE,
     {SESSION: "S-NEW"}, 1, {"lock-not-held"}, refused_with(lock_not_held="this session is S-NEW")),
    ("lock-the-replaced-manager-is-told-it-was-replaced", fx.MOVED, fx.edit(fx.HANDOFF_READY),
     NOTE, {}, 1, {"lock-not-held"}, refused_with(lock_not_held="you have been replaced")),
    ("fp-lock-the-successor-holds-it", fx.MOVED, NOTHING, NOTE, {SESSION: "S-NEW"}, 0, set(),
     committed("devteam/RECORD.md")),

    # --- precondition 3: the named paths' state ---------------------------------------
    ("paths-an-uncommitted-edit-to-a-path-the-verb-writes-is-refused", fx.WRITTEN, DIRTY_RECORD,
     NOTE, {}, 1, {"uncommitted-path"}, refused_with(uncommitted_path="devteam/RECORD.md")),
    ("paths-an-untracked-file-where-the-verb-creates-one-is-refused", fx.WRITTEN,
     fx.edit({"devteam/dispatches/x.md": "# someone's\n"}), ["create", "dispatches"], {}, 1,
     {"uncommitted-path"}, refused_with(uncommitted_path="an untracked file")),
    ("fp-paths-an-uncommitted-edit-elsewhere-is-left-alone", fx.WRITTEN,
     fx.edit({"devteam/QUESTIONS.md": fx.QUESTIONS + "\nan unnamed edit\n"}), NOTE, {}, 0, set(),
     both(committed("devteam/RECORD.md"), still_dirty("devteam/QUESTIONS.md"))),
    ("fp-paths-a-carried-edit-is-committed-with-the-verb", fx.WRITTEN, AMENDED_T2, ["carry"], {},
     0, set(), committed("devteam/tasks/T-2.md", "devteam/RECORD.md")),
    ("paths-the-same-edit-not-carried-is-refused", fx.WRITTEN, AMENDED_T2, ["nocarry"], {}, 1,
     {"uncommitted-path"}, refused_with(uncommitted_path="devteam/tasks/T-2.md")),
    ("fp-paths-a-new-directory-is-created-and-committed", fx.WRITTEN, NOTHING,
     ["create", "dispatches"], {}, 0, set(), committed("devteam/dispatches/x.md")),

    # --- a refusal changes nothing ----------------------------------------------------
    ("gate-a-refusal-by-the-gate-puts-back-every-file-and-directory", fx.WRITTEN, NOTHING, ["bad"],
     {}, 1, {"gate-refused"}, both(gate_said("adds-finding"), absent("devteam/made"))),
    # The HEAD the verb read moved before its commit: the gate refuses it, and
    # the other writer's commit stands.
    ("gate-a-commit-landing-between-the-read-and-the-commit-is-refused", fx.WRITTEN, NOTHING,
     ["race"], {}, 1, {"gate-refused"},
     both(gate_said("head-moved"),
          lambda root, proc, doc, before: "" if fx.git(root, "log", "-1", "--format=%s").strip()
          == "someone else" and fx.git(root, "status", "--porcelain").strip() == ""
          else "the other writer's commit is not HEAD, or the verb's file was left")),
]

# The one refusal whose case moves HEAD: the other writer's commit, which stands.
MOVES_HEAD = {"gate-a-commit-landing-between-the-read-and-the-commit-is-refused"}

# Could not run: exit 2, nothing changed.
CNR = [
    ("cnr-a-verb-that-does-not-commit-what-it-wrote", ["forget"], "did not commit it"),
    ("cnr-a-verb-that-fails-puts-back-what-it-wrote", ["boom"], "RuntimeError: the verb failed"),
    ("cnr-no-verb", [], "no verb"),
    ("cnr-an-unknown-verb", ["claim-everything"], "no verb 'claim-everything'"),
]


def main():
    passed = failed = 0
    names = []
    tmp = tempfile.mkdtemp(prefix="devteam-managertest-")
    try:
        wrapper = os.path.join(tmp, "fixture_manager.py")
        with open(wrapper, "w", encoding="utf-8") as fh:
            fh.write(WRAPPER.format(scripts=HERE))
        bases = {}
        for history in (fx.WRITTEN, fx.VACANT, fx.MOVED):
            bases[repr(history)] = os.path.join(tmp, "bases", str(len(bases)))
            fx.make(bases[repr(history)], history)

        def case(name, root, argv, env, want_rc, want, check, before):
            proc, doc = run(wrapper, root, *argv, env=env)
            why = ""
            if proc.returncode != want_rc:
                why = f"exit {proc.returncode}, wanted {want_rc}: {proc.stderr.strip()[-300:]}"
            elif doc is None:
                why = "no JSON on stdout"
            elif want_rc == 1 and {r["class"] for r in doc["refused"]} != want:
                got = sorted({r["class"] for r in doc["refused"]})
                why = f"refused by {got}, wanted {sorted(want)}"
            elif want_rc in (1, 2) and name not in MOVES_HEAD and fx.state(root) != before:
                why = "a refusal moved HEAD, the index or the working tree (F-24)"
            elif fx.git(root, "worktree", "list", "--porcelain").count("worktree ") != 1:
                why = "a checkout was left behind"
            elif check:
                why = check(root, proc, doc, before)
            return why, doc

        for n, (name, history, apply, argv, env_extra, want_rc, want, check) in enumerate(CASES):
            names.append(name)
            root = os.path.join(tmp, "cases", f"{n:02d}")
            shutil.copytree(bases[repr(history)], root, symlinks=True)
            apply(root)
            before = fx.state(root)
            why, doc = case(name, root, argv, fx.planted(env_extra), want_rc, want, check, before)
            if why:
                failed += 1
                print(f"FAIL  {name}\n        {why}")
                for r in (doc or {}).get("refused", [])[:4]:
                    print(f"        | {r['class']} {r['where']}  {r['detail'][:150]}")
            else:
                passed += 1

        for name, argv, text in CNR:
            names.append(name)
            root = os.path.join(tmp, "cases", name)
            shutil.copytree(bases[repr(fx.WRITTEN)], root, symlinks=True)
            before = fx.state(root)
            proc, doc = run(wrapper, root, *argv)
            if proc.returncode == 2 and text in proc.stderr and fx.state(root) == before \
                    and (doc or {}).get("result") == "could not run":
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}\n        exit {proc.returncode}: {proc.stderr.strip()[-200:]}")

        # NOT A DEVTEAM PROJECT: exit 2 before any verb runs.
        name = "cnr-not-a-devteam-project"
        names.append(name)
        root = os.path.join(tmp, "cases", name)
        fx.make(root, [("init", {"README.md": "x\n"})])
        proc, doc = run(wrapper, root, *NOTE)
        if proc.returncode == 2 and "not a devteam project" in proc.stderr:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}\n        exit {proc.returncode}: {proc.stderr.strip()[-200:]}")

        # THE LINES AND --json ARE ONE DOCUMENT: a refusal, printed both ways.
        name = "fp-the-printed-lines-are-the-documents"
        names.append(name)
        root = os.path.join(tmp, "cases", name)
        shutil.copytree(bases[repr(fx.WRITTEN)], root, symlinks=True)
        env = fx.planted({SESSION: "S-OTHER"})
        proc, doc = run(wrapper, root, *NOTE, env=env)
        text = subprocess.run([sys.executable, wrapper, *NOTE, "-C", root], capture_output=True,
                              text=True, env=env)
        import manager
        if doc and text.returncode == proc.returncode == 1 \
                and text.stdout.rstrip("\n").split("\n") == manager.render(doc):
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}\n        the printed lines are not the document's")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fp = sum(1 for n in names if n.startswith("fp-"))
    print(f"\nmanager control: {passed} passed, {failed} failed, {len(names)} cases "
          f"({fp} of them false-positive controls, {100 * fp // max(1, len(names))}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
