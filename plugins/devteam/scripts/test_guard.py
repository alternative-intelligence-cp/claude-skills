#!/usr/bin/env python3
"""Negative control for guard.py (P-35).

Half of these cases are false-positive controls, deliberately. The first
version of the guard this one is descended from refused a write whose HEREDOC
BODY mentioned a protected path, and a guard that blocks legitimate work gets
switched off by whoever it obstructs — which is strictly worse than no guard.
So: reads of protected trees, copies OUT of them, documents that merely
mention them, and every write that is genuinely in scope must all pass.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
GUARD = os.path.join(HERE, "guard.py")
WRITER_SESSION = "session-A"

CHARTER = """# Charter — Fixture

## Goals

- **G-1** — it works

## Constraints

| Constraint | Value |
|---|---|
| Protected paths | `vendor/`, `generated/` |
| Licence | Apache-2.0 |
"""

BOARD = f"""# The board

**Writer.** `{WRITER_SESSION}` since 2026-09-03
"""

T1 = """# T-1 — the loader — RUNNING (since 2026-09-03, T1-a-1200)

- **Discharges.** R-1
- **Depends on.** none
- **Scope.**
  - `src/loader/`
  - `tests/loader/`
- **Gate.** it works.
- **Verify.** `true`
"""

T2 = """# T-2 — the renderer — PLANNED

- **Discharges.** R-2
- **Depends on.** none
- **Scope.**
  - `src/render/`
- **Gate.** it works.
- **Verify.** `true`
"""

TREE = ["src/loader", "src/render", "tests/loader", "vendor/lib", "generated", "docs"]


def bash(cmd):
    return ("Bash", {"command": cmd})


def write(path):
    return ("Write", {"file_path": path})


def edit(path):
    return ("Edit", {"file_path": path})


# (name, tool, session, expect_deny)
CASES = [
    # --- must be REFUSED ---------------------------------------------------
    ("deny-write-into-protected", write("vendor/lib/x.c"), WRITER_SESSION, True),
    ("deny-edit-into-protected", edit("generated/tables.py"), WRITER_SESSION, True),
    ("deny-redirect-into-protected", bash("echo hi > vendor/lib/x.c"), WRITER_SESSION, True),
    ("deny-rm-in-protected", bash("rm vendor/lib/x.c"), WRITER_SESSION, True),
    ("deny-sed-i-on-protected", bash("sed -i s/a/b/ generated/tables.py"), WRITER_SESSION, True),
    ("deny-git-commit-in-protected", bash("git -C vendor commit -m x"), WRITER_SESSION, True),
    ("deny-mv-into-protected", bash("mv src/loader/a.py vendor/lib/a.py"), WRITER_SESSION, True),
    ("deny-write-outside-any-live-scope", write("src/render/b.py"), WRITER_SESSION, True),
    ("deny-write-to-unclaimed-docs", write("docs/guide.md"), WRITER_SESSION, True),
    ("deny-devteam-write-from-wrong-session", write("devteam/RECORD.md"), "session-B", True),
    ("deny-cd-then-write-into-protected", bash("cd vendor/lib && touch x.c"), WRITER_SESSION, True),
    ("deny-touch-out-of-scope", bash("touch src/render/new.py"), WRITER_SESSION, True),

    # --- the project-root blind spot, found by a manager during a live run --
    # judge() searched from the target's PARENT, so a target that IS the
    # project root found no project and went unjudged. Every `git -C <root> …`
    # resolves to exactly that, so the whole git rule was dead where git runs.
    ("deny-git-reset-hard-at-the-project-root", bash("git reset --hard"), WRITER_SESSION, True),
    ("deny-git-clean-at-the-project-root", bash("git clean -fd"), WRITER_SESSION, True),
    ("deny-git-checkout-dot-at-the-project-root", bash("git checkout ."), WRITER_SESSION, True),
    ("deny-git-push-is-outward-facing", bash("git push origin main"), WRITER_SESSION, True),
    ("deny-git-fetch-moves-refs-under-a-claim", bash("git fetch origin"), WRITER_SESSION, True),

    # --- FALSE-POSITIVE CONTROLS: must be ALLOWED --------------------------
    # Splitting git by what it can DESTROY is the point: judged as one set,
    # the rule either refuses every worker's commit or permits reset --hard.
    # F-8, found by a manager when `rmdir src 2>/dev/null` was refused for a
    # directory plainly in scope. A file-descriptor number belongs to the
    # redirect, not the command; none of the 27 existing false-positive cases
    # carried one, so the control could not see it.
    ("fp-in-scope-write-with-stderr-redirected",
     bash("touch src/loader/a.py 2>/dev/null"), WRITER_SESSION, False),
    ("fp-in-scope-write-with-2-to-1",
     bash("touch src/loader/a.py 2>&1"), WRITER_SESSION, False),
    ("fp-in-scope-write-with-both-streams-redirected",
     bash("touch src/loader/a.py 1>/dev/null 2>&1"), WRITER_SESSION, False),
    ("fp-in-scope-rmdir-with-redirect",
     bash("rmdir src/loader 2>/dev/null"), WRITER_SESSION, False),
    ("fp-numeric-flag-value-is-not-a-path",
     bash("truncate -s 0 src/loader/a.py"), WRITER_SESSION, False),
    ("deny-out-of-scope-write-survives-a-redirect",
     bash("touch src/render/b.py 2>/dev/null"), WRITER_SESSION, True),
    ("deny-out-of-scope-rm-survives-a-redirect",
     bash("rm -rf docs 2>&1"), WRITER_SESSION, True),
    ("fp-git-commit-at-the-project-root", bash("git commit -m x"), WRITER_SESSION, False),
    ("fp-git-add-at-the-project-root", bash("git add -A"), WRITER_SESSION, False),
    ("fp-git-tag-touches-refs-only", bash("git tag v1"), WRITER_SESSION, False),
    ("fp-git-status-is-still-a-read", bash("git status"), WRITER_SESSION, False),
    ("fp-write-inside-scope", write("src/loader/a.py"), WRITER_SESSION, False),
    ("fp-write-inside-second-scope-entry", write("tests/loader/t.py"), WRITER_SESSION, False),
    ("fp-board-is-always-writable", write("devteam/BOARD.md"), "session-B", False),
    ("fp-devteam-write-from-the-named-session", write("devteam/RECORD.md"), WRITER_SESSION, False),
    ("fp-reading-protected-is-fine", bash("cat vendor/lib/x.c"), WRITER_SESSION, False),
    ("fp-grepping-protected-is-fine", bash("grep -r thing vendor/"), WRITER_SESSION, False),
    ("fp-listing-protected-is-fine", bash("ls -la generated/"), WRITER_SESSION, False),
    ("fp-copy-OUT-of-protected-is-a-read",
     bash("cp vendor/lib/x.c src/loader/x.c"), WRITER_SESSION, False),
    ("fp-heredoc-body-mentioning-protected-is-data",
     bash("cat > src/loader/notes.md <<'EOF'\nDo not edit vendor/lib or generated/.\nEOF"),
     WRITER_SESSION, False),
    ("fp-unexpanded-variable-is-not-judged",
     bash('touch "$SOMEWHERE/x.c"'), WRITER_SESSION, False),
    ("fp-cd-into-protected-then-read",
     bash("cd vendor/lib && cat x.c"), WRITER_SESSION, False),
    ("fp-cd-into-scope-then-write",
     bash("cd src/loader && touch a.py"), WRITER_SESSION, False),
    ("fp-write-outside-the-project-entirely",
     write("/tmp/devteam-guard-scratch/x"), WRITER_SESSION, False),
    ("fp-non-write-tool-is-ignored",
     ("Read", {"file_path": "vendor/lib/x.c"}), WRITER_SESSION, False),
    ("fp-git-status-is-not-a-write", bash("git -C vendor status"), WRITER_SESSION, False),
    ("fp-pipeline-of-reads", bash("cat vendor/lib/x.c | grep thing | wc -l"),
     WRITER_SESSION, False),
]

# Cases needing a different fixture: (name, tool, session, deny, mutate)
SPECIAL = [
    # --- regressions from the live-hook test -----------------------------
    # The guard derived the project from the SESSION, so a write into a
    # project the session was not inside went unjudged. That is every
    # subagent, which inherits the parent's project directory -- the guard
    # was inert for an entire rehearsal before a deliberate violation went
    # through unrefused.
    ("deny-out-of-scope-write-from-a-session-elsewhere",
     write("src/render/b.py"), WRITER_SESSION, True, None, "/tmp"),
    ("deny-protected-write-from-a-session-elsewhere",
     write("vendor/lib/x.c"), WRITER_SESSION, True, None, "/tmp"),
    ("fp-in-scope-write-from-a-session-elsewhere",
     write("src/loader/a.py"), WRITER_SESSION, False, None, "/tmp"),
    # `session in writer` was a substring test: a short id matched inside an
    # ordinary word in the writer line and was handed the lock.
    ("deny-session-id-that-is-only-a-substring-of-the-writer-line",
     write("devteam/RECORD.md"), "sion", True, None, None),
    ("fp-exact-session-id-still-holds-the-lock",
     write("devteam/RECORD.md"), WRITER_SESSION, False, None, None),

    ("fp-no-live-task-means-no-scope-enforcement",
     write("docs/guide.md"), WRITER_SESSION, False,
     lambda dt: open(os.path.join(dt, "tasks", "T-1.md"), "w").write(
         T1.replace("RUNNING (since 2026-09-03, T1-a-1200)", "DONE (2026-09-03)"))),
    # A writer line still holding its template placeholder is VACANT. Reading
    # it as another session locked every new project out of its own devteam/
    # on the first write after setup.
    ("fp-unfilled-writer-placeholder-is-vacant",
     write("devteam/RECORD.md"), "session-B", False,
     lambda dt: open(os.path.join(dt, "BOARD.md"), "w").write(
         "# The board\n\n**Writer.** `<session id>` since <date>\n")),
    ("fp-writer-none-lets-anyone-write-devteam",
     write("devteam/RECORD.md"), "session-B", False,
     lambda dt: open(os.path.join(dt, "BOARD.md"), "w").write("# The board\n\n**Writer.** none\n")),
    # F-12: protected paths were read only from the project containing the
    # TARGET, so a write outside every devteam project returned early and was
    # never judged -- which is every sibling repository, the case the guard's
    # own docstring advertises by name.
    ("deny-protected-path-outside-the-project",
     write("/etc/devteam-probe/x.conf"), WRITER_SESSION, True,
     lambda dt: open(os.path.join(dt, "CHARTER.md"), "w").write(
         CHARTER.replace("| Protected paths | `vendor/`, `generated/` |",
                         "| Protected paths | `vendor/`, `/etc/devteam-probe` |"))),
    ("fp-undeclared-path-outside-the-project-is-not-guarded",
     write("/etc/something-else/x.conf"), WRITER_SESSION, False,
     lambda dt: open(os.path.join(dt, "CHARTER.md"), "w").write(
         CHARTER.replace("| Protected paths | `vendor/`, `generated/` |",
                         "| Protected paths | `vendor/`, `/etc/devteam-probe` |"))),
    ("fp-no-protected-paths-declared",
     write("src/loader/a.py"), WRITER_SESSION, False,
     lambda dt: open(os.path.join(dt, "CHARTER.md"), "w").write(
         CHARTER.replace("| Protected paths | `vendor/`, `generated/` |",
                         "| Protected paths | none |"))),
]


def build(mutate=None):
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-guard-"))
    dt = os.path.join(root, "devteam")
    os.makedirs(os.path.join(dt, "tasks"))
    for d in TREE:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    open(os.path.join(root, "vendor", "lib", "x.c"), "w").write("int x;\n")
    open(os.path.join(root, "generated", "tables.py"), "w").write("T = {}\n")
    open(os.path.join(root, "src", "loader", "a.py"), "w").write("a = 1\n")
    open(os.path.join(dt, "CHARTER.md"), "w").write(CHARTER)
    open(os.path.join(dt, "BOARD.md"), "w").write(BOARD)
    open(os.path.join(dt, "RECORD.md"), "w").write("# The record\n")
    open(os.path.join(dt, "tasks", "T-1.md"), "w").write(T1)
    open(os.path.join(dt, "tasks", "T-2.md"), "w").write(T2)
    if mutate:
        mutate(dt)
    return root


def run(root, tool, session, project_dir=None):
    name, ti = tool
    if name in ("Write", "Edit") and not os.path.isabs(ti.get("file_path", "")):
        ti = {**ti, "file_path": os.path.join(root, ti["file_path"])}
    payload = {"tool_name": name, "cwd": root, "session_id": session, "tool_input": ti}
    proc = subprocess.run(
        [sys.executable, GUARD], input=json.dumps(payload), capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": project_dir or root})
    out = proc.stdout.strip()
    if not out:
        return False, ""
    try:
        d = json.loads(out)
        hso = d.get("hookSpecificOutput", {})
        return hso.get("permissionDecision") == "deny", hso.get("permissionDecisionReason", "")
    except json.JSONDecodeError:
        return False, out


def main():
    passed = failed = 0
    all_cases = [(n, t, s, d, None, None) for n, t, s, d in CASES] + [
        (c + (None,) * (6 - len(c))) for c in SPECIAL]
    for name, tool, session, expect_deny, mutate, project_dir in all_cases:
        root = build(mutate)
        try:
            denied, reason = run(root, tool, session, project_dir)
            if denied == expect_deny:
                passed += 1
            else:
                failed += 1
                verb = "REFUSED" if denied else "ALLOWED"
                want = "refuse" if expect_deny else "allow"
                print(f"FAIL  {name}: {verb}, expected to {want}")
                if reason:
                    print(f"        | {reason[:200]}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # DEVTEAM_GUARD=off must disable it entirely.
    root = build()
    try:
        proc = subprocess.run(
            [sys.executable, GUARD],
            input=json.dumps({"tool_name": "Write", "cwd": root, "session_id": "x",
                              "tool_input": {"file_path": os.path.join(root, "vendor/lib/x.c")}}),
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": root, "DEVTEAM_GUARD": "off"})
        if proc.stdout.strip():
            failed += 1
            print("FAIL  off-switch: guard still fired with DEVTEAM_GUARD=off")
        else:
            passed += 1
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = len(all_cases) + 1
    fp = sum(1 for c in all_cases if c[0].startswith("fp-")) + 1
    print(f"\nguard control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
