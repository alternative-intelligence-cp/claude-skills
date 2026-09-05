#!/usr/bin/env python3
"""Negative control for check_scope.py (P-35)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
CHECK = os.path.join(HERE, "check_scope.py")


def task(ident, status, scope, title="a task"):
    body = f"# {ident} — {title} — {status}\n\n- **Discharges.** R-1\n- **Depends on.** none\n- **Scope.**\n"
    for s in scope:
        body += f"  - `{s}`\n"
    body += "- **Gate.** it works.\n- **Verify.** `true`\n\n## Execution record\n"
    return body


BASE = {
    "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)", ["src/loader/", "tests/loader/"]),
    "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/render/", "tests/render/"]),
}

CASES = [
    ("clean", BASE, None, [], set()),

    # --- unparseable-scope-entry: a grant the checker cannot read ---------
    # This grammar failed PERMISSIVELY: an entry with its reason inline was
    # skipped in silence, so a file declaring eleven paths was parsed as nine
    # and two granted paths sat outside the task's scope for its whole run.
    ("unparseable-scope-entry",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)",
                          ["src/loader/"]).replace(
         "  - `src/loader/`", "  - `src/loader/`\n  - `src/extra/` — for the sweep")},
     None, [], {"unparseable-scope-entry"}),
    # ...and prose AFTER the list is not a list item, so it must stay quiet --
    # every task file has explanatory text under its fields.
    ("fp-prose-after-the-scope-list-is-not-an-entry",
     {**BASE, "T-1": task("T-1", "RUNNING (since 2026-09-03, T1-a-1200)",
                          ["src/loader/"]).replace(
         "- **Gate.**", "The loader is granted because it owns the dialect.\n\n- **Gate.**")},
     None, [], set()),

    # --- foreign-write: a write by somebody who is not in this run ---------
    # The guard no longer refuses a session outside the run, so this finding
    # is what replaces that refusal. Every case below is (…, dirty=[…]) --
    # written after the last commit and never staged.
    ("foreign-write",
     BASE, None, [], {"foreign-write"}, "T-1: the work", (),
     [("other/thing.py", "written by nobody in this run\n")]),
    ("foreign-write-untracked-file",
     BASE, None, [], {"foreign-write"}, "T-1: the work", (),
     [("src/other/new.py", "brand new\n")]),
    # THE COLLAPSE HAZARD, and it fired on the first run. Plain `--porcelain`
    # reports an untracked directory as its shortest prefix, so this new file
    # came back as `src/` -- outside every scope -- and the check accused the
    # run's own worker of being a stranger. `-uall` is what makes it a path.
    ("fp-untracked-file-inside-a-live-scope-is-not-collapsed",
     BASE, None, [], set(), "T-1: the work", (),
     [("src/loader/new/x.py", "a worker creating a subdirectory\n")]),
    # ...and the three ways it must stay quiet. A worker mid-step leaves its
    # own scope dirty constantly; the run writes devteam/ constantly; and with
    # nothing claimed there is no run to be foreign to.
    ("fp-dirty-inside-a-live-scope-is-a-worker-mid-step",
     BASE, None, [], set(), "T-1: the work", (),
     [("src/loader/a.py", "half a step\n")]),
    ("fp-dirty-inside-devteam-is-the-run-itself",
     BASE, None, [], set(), "T-1: the work", (),
     [("devteam/RECORD.md", "the manager writing its record\n")]),
    ("fp-dirty-with-no-live-claim-is-not-foreign-to-anything",
     {**BASE, "T-1": task("T-1", "DONE (2026-09-03)", ["src/loader/", "tests/loader/"]), "T-2": task("T-2", "DONE (2026-09-03)", ["src/render/"])}, None, [], set(), "T-1: the work", (),
     [("other/thing.py", "nothing is claimed\n")]),

    # --- one fault per class ----------------------------------------------
    ("overlapping-scope",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/", "docs/"])},
     None, [], {"overlapping-scope"}),
    ("overlapping-scope-identical",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["src/loader/"])},
     None, [], {"overlapping-scope"}),
    ("empty-scope",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", [])},
     None, [], {"empty-scope"}),
    ("scope-escapes-tree",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["../sibling/src/"])},
     None, [], {"scope-escapes-tree"}),
    ("scope-escapes-tree-absolute",
     {**BASE, "T-2": task("T-2", "RUNNING (since 2026-09-03, T2-b-1210)", ["/etc/"])},
     None, [], {"scope-escapes-tree"}),
    ("undeclared-write",
     BASE, "T-1", [("src/loader/a.py", "x=1\n"), ("src/render/b.py", "y=2\n")],
     {"undeclared-write"}),

    # F-17: the manager ran `git add -A` while a worker was mid-file, and the
    # worker's in-flight code landed in the manager's commit under the
    # manager's message. The step lost its commit and the write became
    # invisible to scope attribution.
    ("misattributed-write-steals-a-live-tasks-work",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: backfill sensitivity on the digests"),

    # F-19: the claim anchor was the NEWEST match for a literal phrase, so a
    # commit merely QUOTING that phrase became the anchor, collapsed the span
    # and switched the check off. An integrity check disabled by writing about
    # it — the act of documenting the bug was the act of hiding it.
    ("misattribution-survives-a-commit-quoting-the-anchor-phrase",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: an unrelated backfill",
     [("docs: explain that a title reads RUNNING (since <date>, <label>)", [])]),

    # F-20: the task-file carve-out routed devteam/tasks/T-n.md past the skip
    # and then tested it against a declared scope that never contains it, so
    # it could not fire — and a manager sweeping a supervisor's task file went
    # unreported.
    ("misattributed-write-on-the-tasks-own-file",
     BASE, None, [("devteam/tasks/T-1.md", BASE["T-1"] + "\nswept\n")],
     {"misattributed-write"}, "research: an unrelated backfill"),

    # F-48: a write made while a task was BLOCKED was not live, so nothing
    # flagged it — and a later re-claim moved the anchor past it, so nothing
    # ever could. Never live-and-in-window at any single moment: a finding
    # that could not exist rather than one that was erased.
    ("misattribution-between-a-block-and-a-reclaim-is-still-found",
     BASE, None, [("src/loader/a.py", "x=1\n")], {"misattributed-write"},
     "research: an unrelated backfill",
     [("board: re-claim T-1", [("devteam/BOARD.md", "| T-1 | CLAIMED again |\n")])]),
    ("misattribution-found-when-the-anchor-says-re-claim",
     BASE, None, [("devteam/BOARD.md", "| T-1 | CLAIMED |\n")], {"misattributed-write"},
     "board: re-claim T-1",
     [("chore: unrelated", [("src/loader/b.py", "y=2\n")])]),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    ("fp-another-tasks-file-is-the-managers-not-a-misattribution",
     BASE, None, [("devteam/RECORD.md", "- entry\n")], set(),
     "record: a manager entry"),
    ("fp-the-tasks-own-commit-is-not-misattributed",
     BASE, None, [("src/loader/a.py", "x=1\n")], set(), "T-1: the work"),
    ("fp-a-step-commit-is-not-misattributed",
     BASE, None, [("src/loader/a.py", "x=1\n")], set(), "T-1.S-2: the step"),
    ("fp-a-manager-commit-touching-only-devteam-is-fine",
     BASE, None, [("devteam/RECORD.md", "- an entry\n")], set(),
     "record: a manager entry"),
    ("fp-a-foreign-commit-outside-every-live-scope-is-fine",
     BASE, None, [("docs/guide.md", "hi\n")], set(), "docs: unrelated"),
    # From the first real dispatch: the manager's own board and plan commits
    # mention the task in their message, and were being charged to it.
    # A board commit touches devteam/, not a worker's files — writing src/ in a
    # commit called "board: claim T-1" is the F-17 misattribution, not this.
    ("fp-manager-commits-mentioning-a-task-are-not-its-writes",
     BASE, "T-1", [("devteam/BOARD.md", "| T-1 | CLAIMED |\n")], set(),
     "board: claim T-1"),
    ("fp-planned-tasks-may-overlap-a-running-one",
     {**BASE, "T-3": task("T-3", "PLANNED", ["src/loader/"])}, None, [], set()),
    ("fp-done-tasks-may-overlap",
     {**BASE, "T-3": task("T-3", "DONE (2026-09-03)", ["src/loader/"])}, None, [], set()),
    ("fp-planned-task-may-declare-no-scope-yet",
     {**BASE, "T-3": task("T-3", "PLANNED", [])}, None, [], set()),
    ("fp-sibling-prefixes-do-not-intersect",
     {"T-1": task("T-1", "RUNNING (since x, y)", ["src/loader/"]),
      "T-2": task("T-2", "RUNNING (since x, y)", ["src/loader_v2/"])}, None, [], set()),
    ("fp-writes-inside-scope",
     BASE, "T-1", [("src/loader/a.py", "x=1\n"), ("tests/loader/t.py", "z=3\n")], set()),
    ("fp-the-task-file-itself-is-always-writable",
     BASE, "T-1", [("src/loader/a.py", "x=1\n"),
                   ("devteam/tasks/T-1.md", BASE["T-1"] + "\nmore record\n")], set()),
    ("fp-single-file-scope-entry",
     {"T-1": task("T-1", "RUNNING (since x, y)", ["README.md"]),
      "T-2": task("T-2", "RUNNING (since x, y)", ["src/"])},
     "T-1", [("README.md", "hello\n")], set()),
    ("fp-placeholder-scope-in-a-planned-template",
     {**BASE, "T-3": task("T-3", "PLANNED", ["<area>/"])}, None, [], set()),
    ("fp-blocked-task-with-scope-is-not-live",
     {**BASE, "T-3": task("T-3", "BLOCKED (Q-2)", ["src/loader/"])}, None, [], set()),
]


def build(root, tasks, writes, subject="T-1: the work", later=(), dirty=()):
    dt = os.path.join(root, "devteam", "tasks")
    os.makedirs(dt, exist_ok=True)
    for ident, body in tasks.items():
        with open(os.path.join(dt, f"{ident}.md"), "w", encoding="utf-8") as fh:
            fh.write(body)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, env=env)
    run("init", "-q", "-b", "main")
    run("add", "-A")
    run("commit", "-qm", "fixture")
    if writes:
        for rel, body in writes:
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
        run("add", "-A")
        run("commit", "-qm", subject)
    for msg, more in later:
        for rel, body in more:
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
        run("add", "-A")
        run("commit", "-q", "--allow-empty", "-m", msg)
    # Written AFTER every commit and never staged. `foreign-write` is the one
    # finding about the working tree rather than history, so it is the one
    # thing this harness could not express -- every fixture committed
    # everything, which is why the check passed 27 cases without once firing.
    for rel, body in dirty:
        f = os.path.join(root, rel)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(body)
    return root


def main():
    passed = failed = 0
    for case in CASES:
        name, tasks, task_id, writes, expected = case[:5]
        subject = case[5] if len(case) > 5 else "T-1: the work"
        later = case[6] if len(case) > 6 else ()
        dirty = case[7] if len(case) > 7 else ()
        root = tempfile.mkdtemp(prefix="devteam-scope-")
        try:
            build(root, tasks, writes, subject, later, dirty)
            argv = [sys.executable, CHECK, root] + ([task_id] if task_id else [])
            proc = subprocess.run(argv, capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (\S+)", proc.stdout, re.M)}
            want_exit = 1 if expected else 0
            if got == expected and proc.returncode == want_exit:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} exit {want_exit}")
                print(f"        got      {sorted(got) or 'clean'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n"):
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\ncheck_scope control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
