#!/usr/bin/env python3
"""Negative control for conventions.py (P-35).

The failure that matters is not "no match". It is matching too widely — a
convention that reaches a project it was never meant for is a constraint
applied to somebody who never agreed to it, which is exactly the harm the
"stated, never inferred" rule exists to prevent.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
TOOL = os.path.join(HERE, "conventions.py")


def conv(id_, applies, kind="prohibition"):
    return f"""# {id_} — a stated rule

- **Applies to.** {applies}
- **Kind.** {kind}
- **Rule.** Something must or must not be true.
- **Because.** A reason that can be argued with.
- **Stated.** 2026-09-04 by someone
"""


def run(home, *args):
    env = {**os.environ, "DEVTEAM_CONVENTIONS": home}
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def main():
    passed = failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}   {detail}")

    root = tempfile.mkdtemp(prefix="devteam-conv-")
    home = os.path.join(root, "conventions")
    os.makedirs(home)
    proj = os.path.join(root, "work", "alpha-core")
    other = os.path.join(root, "work", "beta")
    os.makedirs(proj); os.makedirs(other)
    try:
        open(os.path.join(home, "CNV-1.md"), "w").write(
            conv("CNV-1", f"`{os.path.join(root, 'work', 'alpha-*')}`"))
        open(os.path.join(home, "CNV-2.md"), "w").write(
            conv("CNV-2", "tag `alpha`", kind="requirement"))
        open(os.path.join(home, "CNV-3.md"), "w").write(
            conv("CNV-3", f"`{os.path.join(root, 'work', 'beta')}`"))
        open(os.path.join(home, "notes.md"), "w").write("# not a convention\n\nprose.\n")

        rc, out = run(home, "list")
        check("lists every convention", all(f"CNV-{n}" in out for n in (1, 2, 3)))
        check("ignores a file that is not a convention", "not a convention" not in out)

        rc, out = run(home, "match", proj)
        check("a glob matches the project it names", "CNV-1" in out)
        check("MATCHES ONLY WHAT IT NAMES", "CNV-3" not in out,
              "a convention reached a project it was never meant for")
        check("a tag convention needs its tag", "CNV-2" not in out)
        check("match exits 0 when something matched", rc == 0)

        rc, out = run(home, "match", proj, "alpha")
        check("a tag matches when given", "CNV-2" in out)

        rc, out = run(home, "match", other)
        check("the other project gets only its own", "CNV-3" in out and "CNV-1" not in out)

        rc, out = run(home, "match", os.path.join(root, "work", "gamma"))
        check("an unrelated project matches nothing", rc == 1)

        rc, out = run(home, "match", proj)
        check("output says these are questions, not defaults",
              "QUESTIONS, not defaults" in out)
        check("output says a decline must be recorded", "declined convention" in out)

        rc, out = run(home, "new", "CNV-9")
        check("new prints a fillable template",
              rc == 0 and "**Applies to.**" in out and "**Because.**" in out)
        rc, out = run(home, "new", "nope")
        check("new refuses an id outside the reserved prefix", rc == 2)

        empty = os.path.join(root, "none")
        rc, out = run(empty, "match", proj)
        check("an absent store is not an error, just no match", rc == 1)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = passed + failed
    print(f"\nconventions control: {passed} passed, {failed} failed, {total} cases")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
