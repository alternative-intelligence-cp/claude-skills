#!/usr/bin/env python3
"""Negative control for gate.py (P-35).

Each case is one of the run's own failures where there is one (roadmap 0.3.1
§3.5), planted on a small devteam project, and a twin that must go through.
Every refusal is also held to F-24's property: HEAD, the index and the working
tree are exactly as they were, and nothing is left to chain.
"""
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
GATE = os.path.join(HERE, "gate.py")
sys.path.insert(0, HERE)
import check_trace  # noqa: E402 -- the template rows the fixture's charter carries
import gate as gate_module  # noqa: E402 -- its renderer, so the line is asserted too

VALUES = {"Protected paths": "`protected/`", "Containment": "`guard-only`"}
CHARTER = ("# Charter — Fixture\n\n## Goals\n\n- **G-1** — the thing works\n\n"
           "## Constraints\n\n| Constraint | Value |\n|---|---|\n"
           + "".join(f"| {r} | {VALUES.get(r, 'fixture')} |\n" for r in check_trace.CHARTER_ROWS))


def requirement(n, statement, status, requires="src/"):
    return (f"### R-{n} — requirement {n}\n\n- **Statement.** {statement}\n"
            f"- **Satisfies.** G-1\n- **Source.** interview 2026-09-03\n"
            f"- **Acceptance.** `make test` → `ok`\n- **Requires-write.**\n  - `{requires}`\n"
            f"- **Priority.** must\n- **Status.** {status}\n\n")


def reqs(*blocks):
    return "# Requirements\n\n" + "".join(blocks)


def task(n, title, status, fields, record=""):
    return (f"# T-{n} — {title} — {status}\n\n" + "".join(f"- **{k}.** {v}\n" for k, v in fields)
            + "\n## Execution record\n" + record)


T1_FIELDS = [("Discharges", "R-1"), ("Depends on", "none"), ("Scope", "\n  - `src/`"),
             ("Gate", "it works."), ("Verify", "`make test`"), ("Estimate", "1 step")]
T2_FIELDS = [("Kind", "chore"), ("Because", "the docs drifted."), ("Discharges", "none"),
             ("Depends on", "none"), ("Scope", "\n  - `docs/`"), ("Gate", "the docs read true."),
             ("Verify", "`true`"), ("Estimate", "1 step")]
RUNNING = "RUNNING (since 2026-09-03, T1-work-1200)"
IN_FLIGHT_T1 = ("| T-1 | make it work | T1-work-1200 | `a1b2c3` | — | 2026-09-03 12:00 | "
                "opus-5-5 | `src/` | running |\n")


def board(in_flight="", rows=("| `T-1` | make it work | R-1 | none | `src/` | CLAIMED T1-work-1200 |",
                              "| `T-2` | tidy the docs | none | none | `docs/` | — |")):
    return ("# The board\n\n## In flight\n\n"
            "| Task | Title | Agent label | Agent id | Sandbox | Since | Model | Scope | Note |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            + (in_flight or "| — | — | — | — | — | — | — | — | nothing running |\n")
            + "\n## Tasks\n\n| Task | Title | Discharges | Depends on | Scope | State |\n"
            "|---|---|---|---|---|---|\n" + "".join(r + "\n" for r in rows))


def decision(n, title, more=""):
    return (f"### D-{n} — {title}\n\n- **Decision.** it is so.\n- **Supersedes.** none\n"
            f"- **Reviewed.** client\n{more}\n")


DECISIONS = "# Decisions\n\n" + decision(1, "the fixture's first decision")
RECORD = "# Record\n\n- setup, as D-1 records.\n"
QUESTIONS = ("# Questions\n\n### Q-1 — a settled question\n\n- **Class.** REVERSIBLE\n"
             "- **Status.** answered D-1\n")

# THE PROJECT AT ITS CLAIM: T-1 claimed and running, T-2 planned. Two commits,
# so the claim has a commit to anchor to, as check_scope reads it.
SETUP = {
    ".gitignore": "devteam/.run/\n",
    "src/app.py": "print('ok')\n",
    "docs/readme.md": "# docs\n",
    "devteam/CHARTER.md": CHARTER,
    "devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "open")),
    "devteam/tasks/T-1.md": task(1, "make it work", "PLANNED", T1_FIELDS),
    "devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", T2_FIELDS),
    "devteam/BOARD.md": board(rows=("| `T-1` | make it work | R-1 | none | `src/` | — |",
                                    "| `T-2` | tidy the docs | none | none | `docs/` | — |")),
    "devteam/DECISIONS.md": DECISIONS,
    "devteam/RECORD.md": RECORD,
    "devteam/QUESTIONS.md": QUESTIONS,
}
CLAIM = {
    "devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "in-progress (T-1)")),
    "devteam/tasks/T-1.md": task(1, "make it work", RUNNING, T1_FIELDS),
    "devteam/BOARD.md": board(IN_FLIGHT_T1),
}
CLAIMED = [("setup: the fixture", SETUP), ("board: claim T-1", CLAIM)]

# F-114: R-1's Statement already rewritten twice, so a third makes three.
CHURNED = CLAIMED + [
    ("devteam: R-1 restated", {"devteam/REQUIREMENTS.md": reqs(requirement(
        1, "the thing works when run twice.", "in-progress (T-1)"))}),
    ("devteam: R-1 restated again", {"devteam/REQUIREMENTS.md": reqs(requirement(
        1, "the thing works when run three times.", "in-progress (T-1)"))}),
]
THIRD = reqs(requirement(1, "the thing works when run four times.", "in-progress (T-1)"))

# F-12: a leak standing at HEAD, in another live task's file.
LEAKED = CLAIMED + [("T-1: note the command", {
    "devteam/tasks/T-1.md": task(1, "make it work", RUNNING, T1_FIELDS,
                                 "\n- ran `python3 /home/someone/project/x.py`\n")})]

# A finding standing at HEAD at a line, for the ratchet's identity.
LINKED = CLAIMED + [("devteam: a link", {
    "devteam/RECORD.md": RECORD + "- see [the notes](missing.md)\n"})]

# L-1.6: T-2 lacks its Estimate, and D-2 accepts that.
ACCEPTS = ("- **Accepts.**\n  - `check_trace` `missing-field` `tasks/T-2.md` — T-2 has no "
           "**Estimate.**\n")
NO_ESTIMATE = [f for f in T2_FIELDS if f[0] != "Estimate"]
ACCEPTED = CLAIMED + [("devteam: T-2's estimate is accepted as missing (D-2)", {
    "devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", NO_ESTIMATE),
    "devteam/DECISIONS.md": DECISIONS + decision(2, "T-2 has no estimate").replace(
        "- **Reviewed.** client\n", "- **Reviewed.** unreviewed\n" + ACCEPTS),
    "devteam/RECORD.md": RECORD + "- D-2 accepts T-2's missing estimate.\n"})]

# Before planning: requirements and no task.
UNPLANNED = [("setup: the fixture", {
    **{k: v for k, v in SETUP.items() if not k.startswith("devteam/tasks/")},
    "devteam/BOARD.md": board(rows=())})]

T3 = task(3, "a third thing", "PLANNED", [("Kind", "chore"), ("Because", "it came up."),
                                          ("Discharges", "none"), ("Depends on", "none"),
                                          ("Scope", "\n  - `docs/`"), ("Gate", "done."),
                                          ("Verify", "`true`"), ("Estimate", "1 step")])
BOARD_T3 = board(IN_FLIGHT_T1, rows=(
    "| `T-1` | make it work | R-1 | none | `src/` | CLAIMED T1-work-1200 |",
    "| `T-2` | tidy the docs | none | none | `docs/` | — |",
    "| `T-3` | a third thing | none | none | `docs/` | — |"))


def report(status, commits, subject="T-1"):
    return (f"\nREPORT supervisor {subject}\nstatus: {status}\nmodel: opus-5-5\nenv: fixture\n"
            f"requirements: R-1\nscope: src/\ncommits:\n{commits}\nchecks:\n"
            f"  - `make test` → ok\nquestions: none\nopen: none\nfindings-for-protocol: none\n"
            f"budget: tokens=1000 minutes=1\nnotes: none\n")


CLOSED_T1 = task(1, "make it work", "DONE (2026-09-04)", T1_FIELDS,
                 report("DONE", "  - HEAD T-1: close"))

# RECORD.md:486's shape: T-2 closed days ago, also discharging R-1, and its
# link goes one-sided the moment T-1 -- the task R-1 names -- reads DONE. The
# fact that legitimises it is which task the REQUIREMENT names as in
# progress, not which task the finding is anchored at.
T2_ALSO_R1 = [f if f[0] != "Discharges" else ("Discharges", "R-1")
              for f in T2_FIELDS if f[0] not in ("Kind", "Because")]
CLOSED_EARLIER = CLAIMED + [("T-2: close", {"devteam/tasks/T-2.md": task(
    2, "tidy the docs", "DONE (2026-09-03)", T2_ALSO_R1, report("DONE", "  - HEAD T-2: close", "T-2"))})]
# T-1 closed and advanced; then T-2 claimed over the same module, as T-8 was
# claimed over T-3's store.py.
IN_FLIGHT_T2 = IN_FLIGHT_T1.replace("T-1 | make it work | T1-work-1200", "T-2 | tidy the docs | T2-src-0900")
ADVANCED = CLAIMED + [
    ("T-1: close", {"devteam/tasks/T-1.md": CLOSED_T1}),
    ("advance T-1", {
        "devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "discharged (T-1)")),
        "devteam/BOARD.md": board(rows=("| `T-1` | make it work | R-1 | none | `src/` | DONE |",
                                        "| `T-2` | tidy the docs | none | none | `src/` | — |"))}),
    ("board: claim T-2", {
        "devteam/tasks/T-2.md": task(2, "tidy the docs", "RUNNING (since 2026-09-05, T2-src-0900)",
                                     [f if f[0] != "Scope" else ("Scope", "\n  - `src/`") for f in T2_FIELDS]),
        "devteam/BOARD.md": board(IN_FLIGHT_T2, rows=(
            "| `T-1` | make it work | R-1 | none | `src/` | DONE |",
            "| `T-2` | tidy the docs | none | none | `src/` | CLAIMED T2-src-0900 |"))}),
]
# AN ITEM DUE BY T-1'S CLOSE (roadmap 0.3.3, L-3.12): ledgered while T-1 runs,
# then T-1 closed by its supervisor, and then the manager's advance.
LEDGER_DUE = ("# The ledger\n\n### ITM-1 — an item due by T-1's close\n\n"
              "- **Raised.** manager 2026-09-04\n- **Disposition.** open (until T-1)\n")
LEDGERED = CLAIMED + [("devteam: ITM-1, due by T-1's close", {"devteam/LEDGER.md": LEDGER_DUE})]
LEDGERED_CLOSED = LEDGERED + [("T-1: close", {"devteam/tasks/T-1.md": CLOSED_T1})]
ADVANCE_T1 = {
    "devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "discharged (T-1)")),
    "devteam/BOARD.md": board(rows=("| `T-1` | make it work | R-1 | none | `src/` | DONE |",
                                    "| `T-2` | tidy the docs | none | none | `docs/` | — |"))}
ADVANCE_ARGS = ["-m", "advance T-1", "--", "devteam/REQUIREMENTS.md", "devteam/BOARD.md"]
# A SUPERVISOR'S STOP (roadmap 0.3.2, L-2.2): its title and report land with
# CLAIMED still on the board, which the manager moves afterwards.
STOPPED_T1 = task(1, "make it work", "NEEDS-DECISION (which way the docs go)", T1_FIELDS,
                  report("NEEDS-DECISION", "  - HEAD T-1: stop"))
# pricelog's board form: every row's first cell a link (F-70), which the gate
# now reads rather than naming the rows as a part not evaluated.
LINK_ROWS = ("| [T-1](tasks/T-1.md) | make it work | R-1 | none | `src/` | CLAIMED T1-work-1200 |",
             "| [T-2](tasks/T-2.md) | tidy the docs | none | none | `docs/` | — |")
CLAIMED_LINKED = [("setup: the fixture", SETUP),
                  ("board: claim T-1", {**CLAIM, "devteam/BOARD.md": board(IN_FLIGHT_T1, rows=LINK_ROWS)})]
T2_PLANNED = task(2, "tidy the docs", "PLANNED", T2_FIELDS)
# A RESTART (roadmap 0.3.2, L-2.5; pricelog T-19, F-135). The supervisor stops
# while its claim is held; the manager writes the task's file while it is
# stopped, as `run` §4.3 asks before a re-dispatch; the manager re-claims it
# under a new label; the new supervisor sets the title.
ANSWERED = "\n- The client answered; the restart takes the second step.\n"
AMENDED_T1 = task(1, "make it work", "NEEDS-DECISION (which way the docs go)", T1_FIELDS,
                  report("NEEDS-DECISION", "  - HEAD T-1: stop") + ANSWERED)
RESTARTED_T1 = task(1, "make it work", "RUNNING (since 2026-09-05, T1-again-1934)", T1_FIELDS,
                    report("NEEDS-DECISION", "  - HEAD T-1: stop") + ANSWERED)
RESTARTING = CLAIMED + [
    ("T-1: stop", {"devteam/tasks/T-1.md": STOPPED_T1}),
    ("answers: the client's answer, and T-1 restarts", {"devteam/tasks/T-1.md": AMENDED_T1}),
    ("board: claim T-1 (T1-again-1934)", {"devteam/BOARD.md": board(
        IN_FLIGHT_T1.replace("T1-work-1200", "T1-again-1934"),
        rows=("| `T-1` | make it work | R-1 | none | `src/` | CLAIMED T1-again-1934 |",
              "| `T-2` | tidy the docs | none | none | `docs/` | — |"))}),
]
# A RESTART AFTER A CLOSE (roadmap 0.3.2, L-2.7; F-136): the supervisor
# closes, the manager claims the task again under a new label -- after a
# verifier's FAIL, say -- and the new supervisor sets its title.
RECLAIMED = CLAIMED + [
    ("T-1: close", {"devteam/tasks/T-1.md": CLOSED_T1}),
    ("board: claim T-1 (T1-again-1934)", {"devteam/BOARD.md": board(
        IN_FLIGHT_T1.replace("T1-work-1200", "T1-again-1934"),
        rows=("| `T-1` | make it work | R-1 | none | `src/` | CLAIMED T1-again-1934 |",
              "| `T-2` | tidy the docs | none | none | `docs/` | — |"))}),
]
REOPENED_T1 = CLOSED_T1.replace("DONE (2026-09-04)", "RUNNING (since 2026-09-05, T1-again-1934)", 1)
# The restart's plan, and its first step's report: a tests-first stub.
REOPENED_STEPS = REOPENED_T1.replace("\n## Execution record\n", "\n## Steps\n\n- [ ] **S-1** — the "
                                     "stub first · class: `standard` · verify: `make test`\n\n"
                                     "## Execution record\n", 1)
TESTS_FIRST = ("\nREPORT tester T-1.S-1\nstatus: DONE\nmodel: opus-5-5\nenv: fixture\n"
               "requirements: R-1\nscope: src/\ncommits:\n  - HEAD T-1.S-1: the stub first\n"
               "checks:\n  - `make test` → 1 failed, as a tests-first step leaves it\n"
               "questions: none\nopen: none\nfindings-for-protocol: none\nbudget: tokens=1000 minutes=1\n"
               "notes: none\n")
STUB = "raise NotImplementedError\n"
STUBBED = CLAIMED + [("T-1.S-1: the stub first", {"src/app.py": STUB})]
FOREIGN = ("other/x.py is modified and lies outside every live scope (T-1). No agent of this "
           "run should have written it, and the guard no longer refuses a session that is not "
           "part of the run")


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr}")
    return p.stdout


def write(root, files):
    for rel, body in files.items():
        path = os.path.join(root, rel)
        if body is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)


def make(root, history):
    os.makedirs(root)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "config", "commit.gpgsign", "false")
    for subject, files in history:
        write(root, files)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", subject)


def state(root):
    """Everything F-24's property says a refusal leaves as it was."""
    return (git(root, "rev-parse", "HEAD", check=False), git(root, "symbolic-ref", "-q", "HEAD", check=False),
            git(root, "ls-files", "-s"), git(root, "status", "--porcelain", "-uall"),
            git(root, "diff"), git(root, "worktree", "list", "--porcelain"))


def gate(root, *args, env=None, script=GATE):
    p = subprocess.run([sys.executable, script, "commit", "-C", root, "--json", *args],
                       capture_output=True, text=True, env=env)
    try:
        doc = json.loads(p.stdout)
    except ValueError:
        doc = None
    return p, doc


def stub_scripts(tmp):
    """A copy of scripts/ and templates/ whose check_refs.py is a stand-in:
    it fails as GATE_STUB says, or runs the real one and then moves HEAD."""
    plugin = os.path.join(tmp, "plugin")
    shutil.copytree(HERE, os.path.join(plugin, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
    shutil.copytree(os.path.join(os.path.dirname(HERE), "templates"), os.path.join(plugin, "templates"))
    scripts = os.path.join(plugin, "scripts")
    os.rename(os.path.join(scripts, "check_refs.py"), os.path.join(scripts, "check_refs_real.py"))
    with open(os.path.join(scripts, "check_refs.py"), "w", encoding="utf-8") as fh:
        fh.write('''import os, subprocess, sys
WORKING_STATE = ("untracked-file",)
if __name__ == "__main__":
    mode = os.environ.get("GATE_STUB", "")
    at_commit = "--at-commit" in sys.argv
    if mode == "exit2" and at_commit:
        print("check_refs: planted failure", file=sys.stderr); sys.exit(2)
    if mode == "garbage" and at_commit:
        print("this is not json"); sys.exit(0)
    if mode == "exit-disagrees" and at_commit:
        print('{"schema": 1, "exit": 0, "results": [{"check": "check_refs"}]}'); sys.exit(1)
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_refs_real.py")
    code = subprocess.run([sys.executable, real, *sys.argv[1:]]).returncode
    live = os.environ.get("GATE_STUB_REPO", "")
    here = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    there = subprocess.run(["git", "-C", live, "rev-parse", "HEAD"], capture_output=True,
                           text=True).stdout if live else here
    if mode == "move-head" and at_commit and here != there:
        subprocess.run(["git", "-C", live, "commit", "-q", "--allow-empty", "-m", "someone else"])
    sys.exit(code)
''')
    return os.path.join(scripts, "gate.py")


# --- the cases -------------------------------------------------------------------
#
# (name, base, edit, gate arguments, expected exit, refusal classes, check)
# `check(root, proc, doc, before)` returns what is wrong, or "".

def committed(names_clean=(), still_dirty=()):
    """The commit made is the commit checked: HEAD is the candidate, its parent
    the old HEAD, its tree the candidate's; each named path committed and
    staged as committed; each unnamed change still in the working tree."""
    def check(root, proc, doc, before):
        head = git(root, "rev-parse", "HEAD").strip()
        if doc.get("committed") != head or doc.get("candidate") != head:
            return f"HEAD {head[:7]} is not the candidate {str(doc.get('candidate'))[:7]}"
        if git(root, "rev-parse", "HEAD^").strip() != before[0].strip():
            return "the commit's parent is not the old HEAD"
        if git(root, "rev-parse", "HEAD^{tree}").strip() != doc.get("tree"):
            return "the commit's tree is not the candidate's"
        for p in names_clean:
            if git(root, "status", "--porcelain", "--", p).strip():
                return f"{p} is not committed and staged as committed"
        for p in still_dirty:
            if not git(root, "status", "--porcelain", "--", p).strip():
                return f"{p}, not named, was swept into the commit"
            if p in git(root, "show", "--name-only", "--format=", "HEAD"):
                return f"{p}, not named, is in the commit"
        return ""
    return check


def refused_by(**want):
    """Every named refusal's `where`/`detail` contains what is asked."""
    def check(root, proc, doc, before):
        for kind, text in want.items():
            kind = kind.replace("_", "-")
            hits = [r for r in doc["refused"] if r["class"] == kind
                    and text in (r["where"] + " " + r["detail"])]
            if not hits:
                return f"no {kind} refusal mentions {text!r}"
        return ""
    return check


def both(*checks):
    return lambda *a: next((w for w in (c(*a) for c in checks) if w), "")


def says(pattern):
    """The gate's printed lines -- rendered from the same document as its
    `--json`, which is what makes the two unable to disagree -- or its
    stderr, match."""
    def check(root, proc, doc, before):
        lines = gate_module.render(doc) if doc and "line" in doc else []
        blob = "\n".join(lines) + "\n" + proc.stderr
        return "" if re.search(pattern, blob) else f"output does not match {pattern!r}"
    return check


def live_misses_it(root, proc, doc, before):
    """F-114's premise: the same check run on the working tree cannot see it."""
    p = subprocess.run([sys.executable, os.path.join(HERE, "check_trace.py"), root],
                       capture_output=True, text=True)
    return "the working-tree check_trace saw it too" if "re-litigated-requirement" in p.stdout else ""


def edit(files):
    return lambda root: write(root, files)


def hook(name, body):
    def apply(root):
        path = os.path.join(root, ".git", "hooks", name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\n" + body)
        os.chmod(path, 0o755)
    return apply


def combine(*edits):
    def apply(root):
        for e in edits:
            e(root)
    return apply


NOTE = edit({"devteam/RECORD.md": RECORD + "- a note.\n"})
MSG = ["-m", "devteam: a note"]
R = ["--", "devteam/RECORD.md"]

CASES = [
    # --- the commit made is the commit checked ----------------------------
    ("fp-a-clean-commit-lands-as-the-candidate", CLAIMED,
     combine(NOTE, edit({"devteam/QUESTIONS.md": QUESTIONS + "\nan unnamed edit\n"})),
     MSG + R, 0, set(), committed(["devteam/RECORD.md"], ["devteam/QUESTIONS.md"])),
    ("fp-a-dry-run-commits-nothing", CLAIMED, NOTE, ["--dry-run"] + MSG + R, 0, set(),
     lambda root, proc, doc, before: "" if (state(root) == before and doc["result"] == "would commit")
     else "a dry run moved something"),

    # --- F-114: history the commit creates, before it exists -----------------
    ("f114-a-third-revision-of-a-requirement-is-refused", CHURNED,
     edit({"devteam/REQUIREMENTS.md": THIRD}), MSG + ["--", "devteam/REQUIREMENTS.md"],
     1, {"adds-finding"}, both(refused_by(adds_finding="re-litigated-requirement"), live_misses_it)),
    ("fp-f114-a-second-revision-goes-through", CHURNED[:-1],
     edit({"devteam/REQUIREMENTS.md": THIRD}), MSG + ["--", "devteam/REQUIREMENTS.md"],
     0, set(), committed(["devteam/REQUIREMENTS.md"])),

    # --- F-12: a ratchet, not a project-wide green ---------------------------
    ("fp-f12-a-red-finding-in-another-tasks-file-lets-an-unrelated-commit-through", LEAKED,
     NOTE, MSG + R, 0, set(),
     both(committed(["devteam/RECORD.md"]),
          says(r"standing, at HEAD and not added here: 1 finding"),
          says(r"check_refs leak tasks/T-1\.md:\d+"))),
    ("f12-removing-a-declaration-another-file-cites-is-refused", CLAIMED,
     edit({"devteam/DECISIONS.md": "# Decisions\n"}), MSG + ["--", "devteam/DECISIONS.md"],
     1, {"adds-finding"},
     lambda root, proc, doc, before: "" if any(
         r["class"] == "adds-finding" and "D-1 is cited but never declared" in r["detail"]
         and not r["where"].startswith("DECISIONS.md") for r in doc["refused"])
     else "no cited-undefined for D-1 in a file the commit did not touch"),

    # --- CONSOLIDATION §8b: the tree committed is the tree checked ------------
    ("fp-8b-a-defect-in-an-unnamed-uncommitted-file-does-not-refuse", CLAIMED,
     combine(NOTE, edit({"devteam/QUESTIONS.md": QUESTIONS.replace("REVERSIBLE", "MAYBE")})),
     MSG + R, 0, set(), committed(["devteam/RECORD.md"], ["devteam/QUESTIONS.md"])),
    ("8b-the-same-defect-in-a-named-path-refuses", CLAIMED,
     combine(NOTE, edit({"devteam/QUESTIONS.md": QUESTIONS.replace("REVERSIBLE", "MAYBE")})),
     MSG + ["--", "devteam/RECORD.md", "devteam/QUESTIONS.md"], 1, {"adds-finding"},
     refused_by(adds_finding="bad-status")),

    # --- F-131 at the gate ----------------------------------------------------
    ("f131-a-board-citing-an-untracked-task-is-refused-naming-it", CLAIMED,
     edit({"devteam/tasks/T-3.md": T3, "devteam/BOARD.md": BOARD_T3}),
     MSG + ["--", "devteam/BOARD.md"], 1, {"untracked-unnamed", "adds-finding"},
     refused_by(untracked_unnamed="devteam/tasks/T-3.md")),
    ("fp-f131-with-the-task-file-named-too-it-goes-through", CLAIMED,
     edit({"devteam/tasks/T-3.md": T3, "devteam/BOARD.md": BOARD_T3}),
     MSG + ["--", "devteam/BOARD.md", "devteam/tasks/T-3.md"], 0, set(),
     both(committed(["devteam/BOARD.md", "devteam/tasks/T-3.md"]),
          says(r"check_report not run for T-1, T-2, T-3 — no REPORT block"))),
    ("untracked-an-untracked-devteam-file-refuses-an-unrelated-commit", CLAIMED,
     combine(NOTE, edit({"devteam/notes.md": "# scratch\n"})), MSG + R, 1,
     {"untracked-unnamed"}, refused_by(untracked_unnamed="devteam/notes.md")),
    ("fp-an-ignored-file-under-devteam-does-not-refuse", CLAIMED,
     combine(NOTE, edit({"devteam/.run/scratch.md": "# ignored\n"})), MSG + R, 0, set(),
     committed(["devteam/RECORD.md"])),
    ("fp-a-named-directory-names-what-is-under-it", CLAIMED,
     edit({"devteam/tasks/T-3.md": T3, "devteam/BOARD.md": BOARD_T3}),
     MSG + ["--", "devteam/BOARD.md", "devteam/tasks/"], 0, set(),
     committed(["devteam/tasks/T-3.md"])),

    # --- F-19's allowance, both ways (the run's own mutation, RECORD.md:487) ---
    ("fp-f19-a-closed-tasks-link-is-allowed-while-it-is-in-flight", CLAIMED,
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     0, set(), both(committed(["devteam/tasks/T-1.md"]),
                    says(r"allowed: check_trace one-sided-link tasks/T-1\.md:1 — F-19's window"))),
    ("fp-f19-a-long-closed-tasks-link-is-allowed-by-the-task-its-requirement-names", CLOSED_EARLIER,
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     0, set(), both(committed(["devteam/tasks/T-1.md"]),
                    says(r"allowed: check_trace one-sided-link tasks/T-2\.md:1 — F-19's window: T-2 "
                         r"reads DONE, R-1 reads 'in-progress \(T-1\)', and T-1 is in"))),
    ("f19-with-the-in-flight-row-removed-it-is-refused",
     CLAIMED + [("board: T-1's row", {"devteam/BOARD.md": board()})],
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     1, {"adds-finding"}, refused_by(adds_finding="one-sided-link")),
    # The owner's answer, 2026-09-24: F-19's window only. A requirement naming
    # a task that does not list it is a plan disagreeing with itself.
    ("f19-a-requirement-naming-a-task-that-does-not-list-it-is-refused", CLAIMED,
     edit({"devteam/REQUIREMENTS.md": reqs(
         requirement(1, "the thing works when run.", "in-progress (T-1)"),
         requirement(2, "the docs say so.", "in-progress (T-1)", requires="docs/")),
         "devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", [
             f if f[0] != "Discharges" else ("Discharges", "R-2")
             for f in T2_FIELDS if f[0] not in ("Kind", "Because")])}),
     MSG + ["--", "devteam/REQUIREMENTS.md", "devteam/tasks/T-2.md"], 1, {"adds-finding"},
     lambda root, proc, doc, before: "" if [r["detail"][:60] for r in doc["refused"]] == [
         "check_trace one-sided-link: R-2 is in-progress (T-1), but T-"]
     else f"wanted the requirement-side link alone, got {[r['detail'][:70] for r in doc['refused']]}"),
    # T-2 is set RUNNING with no claim on the board, so its title names a label
    # no board carries, and check_scope names its window as not evaluated too
    # (roadmap 0.3.2, L-2.5).
    ("f19-a-running-tasks-link-is-refused-though-its-requirement-names-a-task-in-flight", CLAIMED,
     edit({"devteam/tasks/T-2.md": task(2, "tidy the docs", RUNNING.replace("T1-work", "T2-docs"),
                                         [f if f[0] != "Discharges" else ("Discharges", "R-1")
                                          for f in T2_FIELDS if f[0] not in ("Kind", "Because")])}),
     MSG + ["--", "devteam/tasks/T-2.md"], 1, {"adds-finding", "adds-not-evaluated"},
     both(refused_by(adds_finding="T-2 is RUNNING and discharges R-1"),
          refused_by(adds_not_evaluated="misattributed-write for T-2"))),

    # --- an item due by a task's close (roadmap 0.3.3, L-3.12) ---------------
    # The owner's answer of 2026-09-25: it falls due when the task's row leaves
    # CLAIMED. The supervisor's close lands with the row still CLAIMED, since it
    # may not write the ledger (P-13); the manager's advance moves the row, and
    # is refused until the item is decided. The gate itself is unchanged: the
    # window is check_trace's rule, as L-2.2's is.
    ("fp-l312-a-supervisors-close-lands-over-an-item-due-by-its-task", LEDGERED,
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     0, set(), committed(["devteam/tasks/T-1.md"])),
    ("l312-the-advance-over-the-item-still-open-is-refused", LEDGERED_CLOSED,
     edit(ADVANCE_T1), ADVANCE_ARGS, 1, {"adds-finding"},
     refused_by(adds_finding="ITM-1 is `open (until T-1)`, and T-1 has closed")),
    ("fp-l312-the-advance-that-decides-the-item-lands", LEDGERED_CLOSED,
     edit({**ADVANCE_T1, "devteam/LEDGER.md": LEDGER_DUE.replace("open (until T-1)",
                                                                 "declined (D-1)")}),
     ADVANCE_ARGS + ["devteam/LEDGER.md"], 0, set(), committed(["devteam/LEDGER.md"])),

    # --- the board's rows, read at the gate (roadmap 0.3.2, L-2.1, L-2.2) ---
    # Once board-drift reads the rows, a supervisor's own close or stop meets
    # CLAIMED on the board, which only the manager moves. While the claim is
    # held both land; with the in-flight row removed both are refused, now by
    # board-drift as well.
    ("fp-l22-a-supervisors-stop-lands-while-its-claim-is-held", CLAIMED,
     edit({"devteam/tasks/T-1.md": STOPPED_T1}), ["-m", "T-1: stop", "--", "devteam/tasks/T-1.md"],
     0, set(), committed(["devteam/tasks/T-1.md"])),
    ("l22-a-supervisors-stop-is-refused-with-the-in-flight-row-removed",
     CLAIMED + [("board: T-1's row", {"devteam/BOARD.md": board()})],
     edit({"devteam/tasks/T-1.md": STOPPED_T1}), ["-m", "T-1: stop", "--", "devteam/tasks/T-1.md"],
     1, {"adds-finding"}, refused_by(adds_finding="board-drift")),
    # F-19's close on pricelog's board form, both ways.
    ("fp-f19-a-close-on-a-board-of-link-rows-lands-while-in-flight", CLAIMED_LINKED,
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     0, set(), committed(["devteam/tasks/T-1.md"])),
    ("f19-a-close-on-a-board-of-link-rows-is-refused-with-the-row-removed",
     CLAIMED_LINKED + [("board: T-1's row", {"devteam/BOARD.md": board(rows=LINK_ROWS)})],
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     1, {"adds-finding"}, both(refused_by(adds_finding="board-drift"),
                               refused_by(adds_finding="one-sided-link"))),
    # The plan commit on a board written as the template writes it. Before 0.3.2
    # this was refused for *BOARD.md's task rows*, and the plan skill told the
    # manager to accept the part by a decision (roadmap 0.3.1, §3.7).
    ("fp-a-plan-commit-on-a-template-shaped-board-lands-with-no-acceptance", UNPLANNED,
     edit({"devteam/tasks/T-1.md": task(1, "make it work", "PLANNED", T1_FIELDS),
           "devteam/tasks/T-2.md": T2_PLANNED,
           "devteam/BOARD.md": board(rows=("| `T-1` | make it work | R-1 | none | `src/` | — |",
                                           "| `T-2` | tidy the docs | none | none | `docs/` | — |"))}),
     ["-m", "devteam: the plan", "--", "devteam/tasks", "devteam/BOARD.md"],
     0, set(), committed(["devteam/tasks/T-1.md", "devteam/tasks/T-2.md", "devteam/BOARD.md"])),

    # --- a restart, judged by its current claim (roadmap 0.3.2, L-2.5) -------
    # F-135: the manager's edit to the stopped task's file precedes the claim
    # under the new label, so the new supervisor's title lands. Before 0.3.2
    # the window opened at the first claim, and this commit was refused for
    # the manager's edit: fourteen such refusals in 0.3.1's corpus replay.
    ("fp-f135-a-restarts-title-lands-over-the-stops-edits", RESTARTING,
     edit({"devteam/tasks/T-1.md": RESTARTED_T1}),
     ["-m", "T-1: title RUNNING (since 2026-09-05, T1-again-1934)", "--", "devteam/tasks/T-1.md"],
     0, set(), committed(["devteam/tasks/T-1.md"])),
    # ...and the same edit made after the re-claim is inside the current claim.
    ("f135-an-edit-after-the-re-claim-is-still-refused",
     RESTARTING + [("answers: a note after the claim", {"devteam/tasks/T-1.md": AMENDED_T1
                                                       + "- A note after the claim.\n"})],
     edit({"devteam/tasks/T-1.md": RESTARTED_T1 + "- A note after the claim.\n"}),
     ["-m", "T-1: title RUNNING (since 2026-09-05, T1-again-1934)", "--", "devteam/tasks/T-1.md"],
     1, {"adds-finding"}, refused_by(adds_finding="misattributed-write")),
    # F-136's status half (roadmap 0.3.2, L-2.7): a task closed, then claimed
    # again under a new label. Until the new supervisor reports, the task's
    # latest task-level block is the previous claim's DONE, and it met the new
    # RUNNING title as `status-mismatch`: `90b8b42` and `79e9b7f` in 0.3.1's
    # replay, refused for nothing else.
    ("fp-f136-a-restarts-title-lands-over-the-previous-close", RECLAIMED,
     edit({"devteam/tasks/T-1.md": REOPENED_T1}),
     ["-m", "T-1: title RUNNING (since 2026-09-05, T1-again-1934)", "--", "devteam/tasks/T-1.md"],
     0, set(), committed(["devteam/tasks/T-1.md"])),
    # Nor with the tree (the owner's answer of 2026-09-24): the restart's
    # tests-first step lands its stub and its report together. Before, the
    # stub met the previous close's DONE as `unfinished-scope`.
    ("fp-f136-a-restarts-tests-first-step-lands-with-its-report",
     RECLAIMED + [("T-1: title RUNNING (since 2026-09-05, T1-again-1934)",
                   {"devteam/tasks/T-1.md": REOPENED_STEPS})],
     edit({"src/app.py": STUB, "devteam/tasks/T-1.md": REOPENED_STEPS + TESTS_FIRST}),
     ["-m", "T-1.S-1: the stub first", "--", "src/app.py", "devteam/tasks/T-1.md"],
     0, set(), committed(["src/app.py", "devteam/tasks/T-1.md"])),
    # ...and a reopen that keeps its label -- the board still carrying it, as
    # a close leaves it -- is the close's own claim, so the close meets the
    # title: `b57c29e`'s shape, which the owner read as real.
    ("f136-a-reopen-under-its-own-label-meets-its-close", RECLAIMED[:-1],
     edit({"devteam/tasks/T-1.md": REOPENED_T1.replace("T1-again-1934", "T1-work-1200")}),
     ["-m", "T-1: title RUNNING (since 2026-09-05, T1-work-1200)", "--", "devteam/tasks/T-1.md"],
     1, {"adds-finding"}, refused_by(adds_finding="status-mismatch")),

    # --- F-24 and F-117: a red result, with nothing left to chain ------------
    ("f24-a-red-result-exits-1-with-head-the-index-and-the-tree-untouched", CLAIMED,
     edit({"devteam/QUESTIONS.md": QUESTIONS.replace("REVERSIBLE", "MAYBE")}),
     MSG + ["--", "devteam/QUESTIONS.md"], 1, {"adds-finding"}, lambda *a: ""),
    ("f117-a-report-citing-an-unknown-commit-is-refused", CLAIMED,
     edit({"devteam/tasks/T-1.md": task(1, "make it work", RUNNING, T1_FIELDS,
                                        report("BLOCKED", "  - 1234567 nothing"))}),
     ["-m", "T-1: land the report", "--", "devteam/tasks/T-1.md"], 1, {"adds-finding"},
     refused_by(adds_finding="unknown-commit")),
    # `HEAD <subject>` names the commit the report lands in, so it resolves only
    # in the history the commit creates -- which is where the gate reads it.
    ("fp-a-report-naming-its-own-commit-by-subject-lands", CLAIMED,
     edit({"devteam/tasks/T-1.md": task(1, "make it work", RUNNING, T1_FIELDS,
                                        report("BLOCKED", "  - HEAD T-1: land the report"))}),
     ["-m", "T-1: land the report", "--", "devteam/tasks/T-1.md"], 0, set(),
     committed(["devteam/tasks/T-1.md"])),
    # F-123: a commit under a task's subject prefix is that task's write, and
    # only the history this commit creates holds it.
    ("f123-a-commit-under-a-tasks-prefix-outside-its-scope-is-refused", CLAIMED,
     edit({"devteam/BOARD.md": board(IN_FLIGHT_T1) + "\nA note.\n"}),
     ["-m", "T-1: a board note", "--", "devteam/BOARD.md"], 1, {"adds-finding"},
     refused_by(adds_finding="T-1 committed devteam/BOARD.md")),
    # 1f88891 in pricelog: a tests-first stub in a file a closed task shares is
    # the writer's, judged at the writer's close -- and a report closing over a
    # stub in its own scope is still refused.
    ("fp-a-stub-in-a-closed-tasks-scope-is-judged-at-its-writers-close", ADVANCED,
     edit({"src/app.py": STUB}), ["-m", "T-2.S-1: the stub first", "--", "src/app.py"], 0, set(),
     both(committed(["src/app.py"]),
          says(r"allowed: check_report unfinished-scope tasks/T-1\.md:\d+ — unfinished-scope is "
               r"judged when T-1"))),
    ("a-report-closing-over-a-stub-in-its-own-scope-is-refused", STUBBED,
     edit({"devteam/tasks/T-1.md": CLOSED_T1}), ["-m", "T-1: close", "--", "devteam/tasks/T-1.md"],
     1, {"adds-finding"}, refused_by(adds_finding="unfinished-scope")),
    ("report-a-task-closed-without-a-report-is-refused", CLAIMED,
     edit({"devteam/tasks/T-2.md": task(2, "tidy the docs", "DONE (2026-09-04)", T2_FIELDS)}),
     MSG + ["--", "devteam/tasks/T-2.md"], 1, {"adds-finding"}, refused_by(adds_finding="no-report")),

    # --- the ratchet's identity ----------------------------------------------
    ("fp-a-line-shift-does-not-add-a-finding", LINKED,
     edit({"devteam/RECORD.md": "# Record\n\nTwo lines above.\n\n" + RECORD[len("# Record\n\n"):]
           + "- see [the notes](missing.md)\n"}), MSG + R, 0, set(),
     both(committed(["devteam/RECORD.md"]), says(r"check_refs broken-link RECORD\.md:6"))),
    ("a-second-instance-of-a-standing-finding-is-refused", LINKED,
     edit({"devteam/RECORD.md": RECORD + "- see [the notes](missing.md)\n"
           "- and again [the notes](missing.md)\n"}), MSG + R, 1, {"adds-finding"},
     refused_by(adds_finding="(2 here, 1 at HEAD)")),
    ("a-part-not-evaluated-added-is-refused", CLAIMED,
     edit({"devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", [
         (k, v if k != "Discharges" else "none, though it\n  touches what R-1 reads")
         for k, v in T2_FIELDS])}),
     MSG + ["--", "devteam/tasks/T-2.md"], 1, {"adds-not-evaluated"},
     refused_by(adds_not_evaluated="T-2's Discharges.")),

    # --- accepted findings (L-1.6), as 3.4 left them for this step -------------
    ("fp-a-finding-accepted-in-the-same-commit-goes-through", CLAIMED,
     edit({"devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", NO_ESTIMATE),
           "devteam/DECISIONS.md": ACCEPTED[-1][1]["devteam/DECISIONS.md"],
           "devteam/RECORD.md": ACCEPTED[-1][1]["devteam/RECORD.md"]}),
     MSG + ["--", "devteam/tasks/T-2.md", "devteam/DECISIONS.md", "devteam/RECORD.md"], 0, set(),
     committed(["devteam/DECISIONS.md"])),
    ("accept-fixing-an-accepted-finding-alone-is-refused-as-stale", ACCEPTED,
     edit({"devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", T2_FIELDS)}),
     MSG + ["--", "devteam/tasks/T-2.md"], 1, {"adds-finding"},
     both(refused_by(adds_finding="stale-acceptance"), says(r"supersede D-2"))),
    ("fp-accept-the-fix-and-the-supersession-in-one-commit-go-through", ACCEPTED,
     edit({"devteam/tasks/T-2.md": task(2, "tidy the docs", "PLANNED", T2_FIELDS),
           "devteam/DECISIONS.md": ACCEPTED[-1][1]["devteam/DECISIONS.md"]
           + decision(3, "T-2 has its estimate").replace("- **Supersedes.** none", "- **Supersedes.** D-2"),
           "devteam/RECORD.md": ACCEPTED[-1][1]["devteam/RECORD.md"] + "- D-3 supersedes it.\n"}),
     MSG + ["--", "devteam/tasks/T-2.md", "devteam/DECISIONS.md", "devteam/RECORD.md"], 0, set(),
     committed(["devteam/tasks/T-2.md"])),

    # --- onboarding ----------------------------------------------------------------
    ("fp-pre-plan-before-planning-commits-an-uncovered-requirement", UNPLANNED,
     edit({"devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "open"),
                                           requirement(2, "and the other.", "open"))}),
     ["--pre-plan"] + MSG + ["--", "devteam/REQUIREMENTS.md"], 0, set(),
     committed(["devteam/REQUIREMENTS.md"])),
    ("without-pre-plan-the-same-commit-is-refused", UNPLANNED,
     edit({"devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "open"),
                                           requirement(2, "and the other.", "open"))}),
     MSG + ["--", "devteam/REQUIREMENTS.md"], 1, {"adds-finding"},
     refused_by(adds_finding="uncovered-requirement")),
    # iterate's charter gate (pricelog 34f778d): the next cycle's requirements
    # are signed before their tasks are planned. The owner's answer,
    # 2026-09-24: --pre-plan holds back a requirement the commit adds, and no
    # requirement HEAD has -- so one that loses its task is still refused.
    ("fp-pre-plan-lets-iterate-commit-a-new-requirement-before-its-plan", CLAIMED,
     edit({"devteam/REQUIREMENTS.md": reqs(requirement(1, "the thing works when run.", "in-progress (T-1)"),
                                           requirement(2, "and the next cycle's.", "open"))}),
     ["--pre-plan"] + MSG + ["--", "devteam/REQUIREMENTS.md"], 0, set(),
     both(committed(["devteam/REQUIREMENTS.md"]),
          says(r"allowed: check_trace uncovered-requirement REQUIREMENTS\.md:\d+ — --pre-plan: R-2 is new"))),
    ("pre-plan-still-refuses-a-requirement-that-loses-its-task", CLAIMED,
     edit({"devteam/tasks/T-1.md": task(1, "make it work", RUNNING, [
         ("Kind", "chore"), ("Because", "it is tidying now.")]
         + [f if f[0] != "Discharges" else ("Discharges", "none") for f in T1_FIELDS])}),
     ["--pre-plan"] + MSG + ["--", "devteam/tasks/T-1.md"], 1, {"adds-finding"},
     refused_by(adds_finding="R-1 is not discharged by any task")),

    # --- the working state is printed, and judged only for untracked files -----
    ("fp-a-foreign-write-is-printed-and-does-not-refuse", CLAIMED,
     combine(NOTE, edit({"other/x.py": "x = 1\n"})), MSG + R, 0, set(),
     both(committed(["devteam/RECORD.md"], ["other/x.py"]), says(r"foreign-write"))),

    # An acceptance of a working-state finding is not judged at a commit, where
    # the state is not: `--at-commit` excludes the class, so it is not stale.
    ("fp-accepting-a-working-state-finding-is-not-stale-at-a-commit", CLAIMED,
     edit({"other/x.py": "x = 1\n",
           "devteam/DECISIONS.md": DECISIONS + decision(2, "the stray file stands").replace(
               "- **Reviewed.** client\n", "- **Reviewed.** unreviewed\n- **Accepts.**\n"
               f"  - `check_scope` `foreign-write` `BOARD.md` — {FOREIGN}\n"),
           "devteam/RECORD.md": RECORD + "- D-2 accepts the stray file.\n"}),
     MSG + ["--", "devteam/DECISIONS.md", "devteam/RECORD.md"], 0, set(),
     committed(["devteam/DECISIONS.md"], ["other/x.py"])),

    # --- the project's commit hooks run, as `git commit` runs them -------------
    ("hook-a-failing-pre-commit-hook-refuses", CLAIMED,
     combine(NOTE, hook("pre-commit", "echo 'the project says no' >&2\nexit 1\n")), MSG + R, 1,
     {"hook-refused"}, refused_by(hook_refused="the project says no")),
    ("fp-hook-a-commit-msg-hook-edits-the-message-and-post-commit-runs", CLAIMED,
     combine(NOTE, hook("commit-msg", 'printf "\\nSigned-off-by: a hook\\n" >> "$1"\n'),
             hook("post-commit", "touch .git/post-commit-ran\n")), MSG + R, 0, set(),
     lambda root, proc, doc, before: committed(["devteam/RECORD.md"])(root, proc, doc, before) or (
         "" if "Signed-off-by: a hook" in git(root, "log", "-1", "--format=%B")
         and os.path.exists(os.path.join(root, ".git", "post-commit-ran"))
         else "the hook's trailer or the post-commit hook is missing")),

    # --- could not run: nothing committed, and exit 2 --------------------------
    ("cnr-no-separator", CLAIMED, NOTE, MSG + ["devteam/RECORD.md"], 2, set(), says("no `--`")),
    ("cnr-no-path", CLAIMED, NOTE, MSG + ["--"], 2, set(), says("no path")),
    ("cnr-the-m-trap", CLAIMED, NOTE, ["--", "devteam/RECORD.md", "-m", "x"], 2, set(),
     says("follows `--`")),
    ("cnr-the-whole-repository", CLAIMED, NOTE, MSG + ["--", "."], 2, set(), says("whole repository")),
    ("cnr-a-path-outside-the-repository", CLAIMED, NOTE, MSG + ["--", "../elsewhere"], 2, set(),
     says("outside the repository")),
    ("cnr-nothing-to-commit", CLAIMED, lambda root: None, MSG + R, 2, set(), says("nothing to commit")),
]


def extra_cases(tmp, bases):
    """Cases that need a stand-in check, a held lock or a repository of their own."""
    out = []
    stub_gate = stub_scripts(tmp)
    for mode, text in (("exit2", "could not run (exit 2)"), ("garbage", "cannot read"),
                       ("exit-disagrees", "cannot read")):
        out.append((f"closed-a-check-{mode}-means-nothing-is-committed", "CLAIMED", NOTE, MSG + R, 2,
                    set(), says(re.escape(text)), {"GATE_STUB": mode}, stub_gate))
    out.append(("head-moved-between-the-evaluation-and-the-commit-is-refused", "CLAIMED", NOTE,
                MSG + R, 1, {"head-moved"},
                lambda root, proc, doc, before: "" if git(root, "log", "-1", "--format=%s").strip()
                == "someone else" else "HEAD is not the other writer's commit",
                {"GATE_STUB": "move-head"}, stub_gate))
    return out


def main():
    passed = failed = 0
    # Not the gate's own prefix: its sweep must never meet a directory it did
    # not make.
    tmp = tempfile.mkdtemp(prefix="devteam-gatetest-")
    names = []
    try:
        bases, histories = {}, {}
        for _name, history, *_rest in CASES:
            key = repr(history)
            if key not in histories:
                histories[key] = f"base{len(histories)}"
                bases[histories[key]] = os.path.join(tmp, "bases", histories[key])
                make(bases[histories[key]], history)
        bases["CLAIMED"] = bases[histories[repr(CLAIMED)]]
        todo = [(name, histories[repr(history)], apply, args, want_rc, want, check, None, GATE)
                for name, history, apply, args, want_rc, want, check in CASES]
        todo += extra_cases(tmp, bases)
        for n, (name, label, apply, args, want_rc, want, check, env_extra, script) in enumerate(todo):
            names.append(name)
            root = os.path.join(tmp, "cases", f"{n:02d}")
            shutil.copytree(bases[label], root, symlinks=True)
            apply(root)
            before = state(root)
            env = dict(os.environ, **(env_extra or {}), GATE_STUB_REPO=root)
            proc, doc = gate(root, *args, env=env, script=script)
            why = ""
            if proc.returncode != want_rc:
                why = f"exit {proc.returncode}, wanted {want_rc}"
            elif doc is None:
                why = "no JSON on stdout"
            elif want_rc == 1 and {r["class"] for r in doc["refused"]} != want:
                why = f"refused by {sorted({r['class'] for r in doc['refused']})}, wanted {sorted(want)}"
            elif want_rc in (1, 2) and "head-moved" not in want and state(root) != before:
                why = "a refusal moved HEAD, the index, the working tree or a checkout (F-24)"
            elif git(root, "worktree", "list", "--porcelain").count("worktree ") != 1:
                why = "the gate left a checkout behind"
            else:
                why = check(root, proc, doc, before)
            if why:
                failed += 1
                print(f"FAIL  {name}\n        {why}")
                for line in (proc.stderr.strip().split("\n") + [
                        f"{r['class']} {r['where']}  {r['detail'][:160]}" for r in (doc or {}).get("refused", [])])[:12]:
                    print(f"        | {line}")
            else:
                passed += 1

        # THE LOCK: one gate at a time, and a run that cannot take it commits
        # nothing (exit 2).
        names.append("closed-a-held-lock-means-nothing-is-committed")
        root = os.path.join(tmp, "cases", "lock")
        shutil.copytree(bases["CLAIMED"], root, symlinks=True)
        NOTE(root)
        before = state(root)
        with open(os.path.join(root, ".git", "devteam-gate.lock"), "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            proc, doc = gate(root, "--wait", "0", *MSG, *R)
        if proc.returncode == 2 and state(root) == before and "another gate run" in proc.stderr:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  closed-a-held-lock-means-nothing-is-committed\n        exit {proc.returncode}")

        # A CHECKOUT A KILLED RUN LEFT BEHIND is removed, so it does not stay
        # registered in the repository for good.
        names.append("fp-a-stale-checkout-from-a-killed-run-is-swept")
        root = os.path.join(tmp, "cases", "sweep")
        shutil.copytree(bases["CLAIMED"], root, symlinks=True)
        stale = os.path.join(tempfile.mkdtemp(prefix="devteam-gate-"), "checkout")
        git(root, "worktree", "add", "--detach", "--quiet", stale, "HEAD")
        NOTE(root)
        proc, doc = gate(root, *MSG, *R)
        listed = git(root, "worktree", "list", "--porcelain")
        if proc.returncode == 0 and "devteam-gate-" not in listed and not os.path.exists(stale):
            passed += 1
        else:
            failed += 1
            print(f"FAIL  fp-a-stale-checkout-from-a-killed-run-is-swept\n        exit "
                  f"{proc.returncode}; {listed.strip()}")

        # A REPOSITORY THAT LIVES UNDER A NAME LIKE THE GATE'S is never swept.
        # The first sweep matched a path fragment, and would have removed this
        # repository's main worktree and then deleted the directory above it.
        names.append("fp-a-repository-under-a-gate-named-directory-is-never-swept")
        root = os.path.join(tmp, "devteam-gate-lookalike", "repo")
        shutil.copytree(bases["CLAIMED"], root, symlinks=True)
        NOTE(root)
        proc, doc = gate(root, *MSG, *R)
        if proc.returncode == 0 and os.path.isdir(os.path.join(root, ".git")):
            passed += 1
        else:
            failed += 1
            print(f"FAIL  fp-a-repository-under-a-gate-named-directory-is-never-swept\n"
                  f"        exit {proc.returncode}; repository present: {os.path.isdir(root)}")

        # A REFUSED CANDIDATE IS AN OBJECT, NOT A COMMIT OF THE PROJECT (roadmap
        # 0.3.2, L-2.6). A report citing it by hash is refused: the hash must be
        # in HEAD's history, not merely resolve. Before 0.3.2 it resolved.
        name = "l26-a-report-citing-a-refused-candidate-by-hash-is-refused"
        names.append(name)
        root = os.path.join(tmp, "cases", "refused-candidate")
        shutil.copytree(bases["CLAIMED"], root, symlinks=True)
        write(root, {"devteam/QUESTIONS.md": QUESTIONS.replace("REVERSIBLE", "MAYBE")})
        first, doc = gate(root, *MSG, "--", "devteam/QUESTIONS.md")
        refused = (doc or {}).get("candidate", "")
        write(root, {"devteam/QUESTIONS.md": QUESTIONS,
                     "devteam/tasks/T-1.md": task(1, "make it work", RUNNING, T1_FIELDS, report(
                         "BLOCKED", f"  - {refused[:12]} T-1: the attempt the gate refused"))})
        proc, doc = gate(root, "-m", "T-1: land the report", "--", "devteam/tasks/T-1.md")
        hit = [r for r in (doc or {}).get("refused", []) if r["class"] == "adds-finding"
               and "unknown-commit" in r["detail"] and "not one in HEAD's history" in r["detail"]]
        if first.returncode == 1 and refused and proc.returncode == 1 and hit:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}\n        first exit {first.returncode}, candidate {refused[:7]!r}, "
                  f"second exit {proc.returncode}")
            for r in (doc or {}).get("refused", [])[:4]:
                print(f"        | {r['class']} {r['detail'][:150]}")

        # NO PROJECT AT HEAD, OR NO HEAD: exit 2, pointing at `setup`.
        for name, prepare in (
                ("cnr-head-holds-no-devteam", lambda r: (make(r, [("init", {"README.md": "x\n"})]),
                                                          write(r, {"devteam/RECORD.md": RECORD}))),
                ("cnr-head-has-no-commit", lambda r: (os.makedirs(r), git(r, "init", "-q"),
                                                       write(r, {"devteam/RECORD.md": RECORD}))),
                ("cnr-not-a-devteam-project", lambda r: make(r, [("init", {"README.md": "x\n"})]))):
            names.append(name)
            root = os.path.join(tmp, "cases", name)
            prepare(root)
            proc, doc = gate(root, *MSG, "--", "devteam/RECORD.md" if "not-a" not in name else "README.md")
            want = "setup" if "head" in name else "not a devteam project"
            if proc.returncode == 2 and want in proc.stderr:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}\n        exit {proc.returncode}: {proc.stderr.strip()[:200]}")

        # EACH CHECK EXCLUDES ITS OWN WORKING-STATE CLASSES AT A COMMIT, and
        # every name it lists is a class it emits: a stale name would exclude
        # nothing, and a missing one would be evaluated where it sees nothing.
        import check_plugin  # noqa: E402
        for check in ("check_trace", "check_refs", "check_scope", "check_report"):
            name = f"at-commit-{check}-excludes-exactly-its-working-state"
            names.append(name)
            mod = __import__(check)
            emitted = check_plugin.emitted_classes(os.path.join(HERE, f"{check}.py"))
            args = [bases["CLAIMED"], "--json", "--at-commit"] + (["T-1"] if check in
                                                                   ("check_report",) else [])
            p = subprocess.run([sys.executable, os.path.join(HERE, f"{check}.py"), *args],
                               capture_output=True, text=True)
            try:
                excluded = {e["part"] for e in json.loads(p.stdout)["results"][0]["excluded"]
                            if "--at-commit" in e["by"]}
            except (ValueError, KeyError, IndexError):
                excluded = None
            if excluded == set(mod.WORKING_STATE) and set(mod.WORKING_STATE) <= set(emitted):
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}\n        excluded {excluded}, WORKING_STATE "
                      f"{mod.WORKING_STATE}, emitted {sorted(emitted)[:6]}…")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fp = sum(1 for n in names if n.startswith("fp-"))
    print(f"\ngate control: {passed} passed, {failed} failed, {len(names)} cases "
          f"({fp} of them false-positive controls, {100 * fp // max(1, len(names))}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
