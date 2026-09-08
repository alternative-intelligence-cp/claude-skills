#!/usr/bin/env python3
"""Negative control for setup.py (P-35).

`setup.py` writes into a repository that is not ours -- the scaffold, and two
groups of `.gitignore` lines -- and until now it had no control at all. That
gap was found by roadmap 0.2.4's own end-to-end, which scaffolded a throwaway
project and watched a promotion get refused for build artifacts the worker's
own test command had created.

**What each group of ignore lines is owed to, because they are not the same
obligation.** `devteam/.run/` is OURS: the loop cannot run without it ignored,
and `sandbox.py dispatch` refuses outright when it is missing, because the
harness's own liveness file would otherwise land in the worker's uncommitted
remainder and `promote` would blame the worker for it. The stack lines are the
PROJECT'S build artifacts and are a proposal -- printed back for the client,
and theirs to delete.

**The false-positive controls are the load-bearing half here**, more than
usual, because this script appends to a file somebody else owns. A scaffold
that invents ignore rules for a stack it did not detect, or that re-appends on
every run, or that silently restores a line the client deliberately removed, is
worse than one that does nothing: it teaches a client that the tool edits their
files unpredictably, and that is how a tool stops being allowed near a
repository at all.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
SETUP = os.path.join(HERE, "setup.py")


def project(root, name, marker=None, gitignore=None):
    p = os.path.join(root, name)
    os.makedirs(p, exist_ok=True)
    subprocess.run(["git", "-C", p, "init", "-q", "."], capture_output=True)
    if marker:
        open(os.path.join(p, marker), "w").close()
    if gitignore is not None:
        with open(os.path.join(p, ".gitignore"), "w") as fh:
            fh.write(gitignore)
    return p


def scaffold(p):
    r = subprocess.run([sys.executable, SETUP, p], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def ignore_lines(p):
    path = os.path.join(p, ".gitignore")
    if not os.path.isfile(path):
        return []
    return [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]


def main():
    root = tempfile.mkdtemp(prefix="devteam-setup-control-")
    passed = failed = 0

    def case(name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}")
            if detail:
                print(f"        | {detail}")

    try:
        # -- the runtime line, which the loop cannot run without ------------
        p = project(root, "bare")
        scaffold(p)
        got = ignore_lines(p)
        case("runtime-directory-is-ignored", "devteam/.run/" in got, str(got))

        # It is not enough for the line to be THERE; git has to agree, which is
        # what `dispatch` actually asks. A line that does not match the path is
        # a line that reads correct and refuses every dispatch.
        rc = subprocess.run(
            ["git", "-C", p, "check-ignore", "-q",
             os.path.join(p, "devteam", ".run", "locks", "T-1.sandbox")],
            capture_output=True)
        case("git-agrees-the-liveness-path-is-ignored", rc.returncode == 0,
             "git check-ignore says the path dispatch writes is NOT ignored")

        # -- the stack lines, for a stack that was detected -----------------
        p = project(root, "py", marker="pyproject.toml")
        scaffold(p)
        got = ignore_lines(p)
        case("python-build-artifacts-are-ignored",
             "__pycache__/" in got and ".pytest_cache/" in got, str(got))
        # And git agrees for the artifact a test run actually leaves. This is
        # the F-37 case: the suite writes it, the tree is never clean, every
        # verifier's first check fails and `promote` refuses the remainder.
        os.makedirs(os.path.join(p, "src", "__pycache__"), exist_ok=True)
        open(os.path.join(p, "src", "__pycache__", "m.cpython-312.pyc"), "w").close()
        st = subprocess.run(["git", "-C", p, "status", "--porcelain"],
                            capture_output=True, text=True).stdout
        case("a-test-run-leaves-the-tree-clean", "__pycache__" not in st,
             f"git status after a simulated test run:\n{st.strip()[:200]}")

        p = project(root, "node", marker="package.json")
        scaffold(p)
        case("node-build-artifacts-are-ignored",
             "node_modules/" in ignore_lines(p), str(ignore_lines(p)))

        # -- the charter ships the SCHEMA, not only the guidance ------------
        # Found by 0.2.8's end-to-end walk on a project the pipeline had not
        # written. `setup.py` strips `<!-- example:begin -->` blocks, which is
        # correct -- an installed template declares nothing of this repository
        # (P-35b). The charter's ENTIRE constraints table was inside one. So a
        # scaffolded charter carried three paragraphs on how to write a
        # constraint row and no table to write one into, while
        # `skills/setup/SKILL.md` said "write the charter's `Containment` row",
        # `skills/onboard/SKILL.md` said "everything the charter's constraints
        # table names", and `templates/FORMATS.md` said the row is written by
        # setup. Three documents pointing at a table the scaffold deleted, and
        # every check green, because no check compared them.
        p = project(root, "charter")
        scaffold(p)
        charter = open(os.path.join(p, "devteam", "CHARTER.md"),
                       encoding="utf-8").read()
        case("charter-ships-the-constraints-schema",
             "| Constraint | Value |" in charter,
             "a scaffolded charter has no constraints table to fill in")
        case("charter-ships-the-containment-row",
             "| Containment |" in charter,
             "the row setup's own skill is told to write is absent from the "
             "file it is told to write it into")
        # The three below are why this is not a revert: the stripping still
        # has to work, or the fix trades one defect for the one P-35b names.
        case("charter-ships-no-example-markers",
             "example:begin" not in charter and "example:end" not in charter,
             "an example marker survived into a client's charter")
        # A `schema:` block ships its CONTENT and not its markers. Without this
        # case the split between the two markers is only half proved: the rows
        # would arrive with `<!-- schema:begin -->` sitting above them in a
        # document a client signs.
        case("charter-ships-no-schema-markers",
             "schema:begin" not in charter and "schema:end" not in charter,
             "a schema marker survived into a client's charter")
        case("charter-strips-the-goal-examples",
             "**G-1**" not in charter,
             "this repository's example goals shipped into a client's charter")

        # -- FALSE-POSITIVE CONTROLS ---------------------------------------
        # A stack that was NOT detected gets no stack lines. Without this the
        # script could ignore everything for everyone and every case above
        # would still pass.
        p = project(root, "bare2")
        scaffold(p)
        got = ignore_lines(p)
        case("fp-no-stack-detected-adds-no-stack-lines", got == ["devteam/.run/"],
             f"invented ignore rules for a stack it did not detect: {got}")

        # A python project does not get node's lines, or rust's.
        p = project(root, "py2", marker="pyproject.toml")
        scaffold(p)
        got = ignore_lines(p)
        case("fp-one-stack-does-not-get-anothers-lines",
             "node_modules/" not in got and "target/" not in got, str(got))

        # Re-running setup appends nothing. Setup refuses to overwrite an
        # existing devteam/, so this is the realistic repeat: the directory is
        # gone, the .gitignore is not.
        p = project(root, "twice", marker="pyproject.toml")
        scaffold(p)
        first = open(os.path.join(p, ".gitignore")).read()
        shutil.rmtree(os.path.join(p, "devteam"))
        scaffold(p)
        case("fp-re-running-setup-appends-nothing",
             open(os.path.join(p, ".gitignore")).read() == first,
             "the second run appended to a .gitignore that already had its lines")

        # A line the CLIENT deliberately removed stays removed. Silently
        # restoring it is the behaviour that makes a tool unwelcome in
        # somebody's repository, and it is invisible until they notice.
        p = project(root, "client-removed", marker="pyproject.toml",
                    gitignore="devteam/.run/\n__pycache__/\n")
        scaffold(p)
        got = ignore_lines(p)
        case("fp-a-line-the-client-already-has-is-not-duplicated",
             got.count("__pycache__/") == 1 and got.count("devteam/.run/") == 1,
             f"duplicated an existing line: {got}")

        # An existing .gitignore's own content survives untouched.
        p = project(root, "preserves", marker="pyproject.toml",
                    gitignore="# theirs\n*.log\nsecrets.env\n")
        scaffold(p)
        got = ignore_lines(p)
        case("fp-the-clients-existing-rules-survive",
             "*.log" in got and "secrets.env" in got, str(got))

        # And setup still refuses to clobber an existing devteam/ -- the
        # property that everything above is layered on top of.
        p = project(root, "existing")
        os.makedirs(os.path.join(p, "devteam"), exist_ok=True)
        rc, out = scaffold(p)
        case("refuses-to-overwrite-an-existing-devteam-directory", rc != 0,
             f"exit {rc}: {out.strip()[:160]}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = passed + failed
    fp = 6
    print(f"\nsetup control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
