#!/usr/bin/env python3
"""Negative control for findings_index.py (P-35).

The failure that matters is not "no findings". It is a subcycle that reads as
having learned nothing because the parser did not recognise its format — a
false negative on the one lookup the index exists for. So every case here is
about what the index must NOT do: drop a format, count a subsection, count a
heading inside a code fence, list a README, carry a finding's content, or stay
quiet about a section it could not read.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
TOOL = os.path.join(HERE, "findings_index.py")

H3_FILE = """# 0.9.1 — a subcycle — DONE

## Findings

### The first finding, as a heading

Body text that must never reach the index: ZEBRA-SENTENCE.

#### A subsection inside the first finding

### The second finding

```
### a heading inside a fence, which is not a finding
```

## Something after the findings

### A heading in a later section, which is not a finding
"""

BULLET_FILE = """# 0.9.0 — the old format — DONE

## Findings

- **The bullet finding.** Detail on the same line.
  - **A nested bullet, which is detail and not a finding.**
- **The second bullet finding.**
"""

THIRD_FORMAT = """# 0.9.2 — a format nobody taught the parser — DONE

## Findings

1. A numbered finding the parser does not know.
2. Another one.
"""

NO_SECTION = """# 0.9.3 — planned, nothing found yet — PLANNED

## 1. Where you are
"""


def build(root, files):
    for rel, body in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)


def run(*args):
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    passed = failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}" + (f"  ({detail})" if detail else ""))

    tmp = tempfile.mkdtemp(prefix="devteam-findings-")
    try:
        build(tmp, {
            "0.9/0.9.1.md": H3_FILE,
            "done/0.9.0.md": BULLET_FILE,
            "0.9/0.9.3.md": NO_SECTION,
            "README.md": "## Findings\n\n### A README heading, which is not a subcycle\n",
        })
        rc, out, err = run(tmp)
        check("both formats index cleanly, exit 0", rc == 0, err.strip())
        check("the ### format yields its two findings",
              "The first finding, as a heading" in out and "The second finding" in out)
        check("a #### subsection is not a finding",
              "A subsection inside the first finding" not in out)
        check("a heading inside a code fence is not a finding",
              "a heading inside a fence" not in out)
        check("a heading after the Findings section is not a finding",
              "A heading in a later section" not in out)
        check("the bullet format yields its two top-level findings",
              "The bullet finding" in out and "The second bullet finding" in out)
        check("a nested bullet is not a finding", "A nested bullet" not in out)
        check("a README is not a subcycle", "A README heading" not in out)
        check("the index carries pointers, never a finding's body",
              "ZEBRA-SENTENCE" not in out)
        check("pointers name the file and line", "`0.9/0.9.1.md:5`" in out, out[:400])
        check("the total counts four findings in two files",
              "**4 findings across 2 subcycle files.**" in out)
        check("a file with no Findings section is listed, not silently dropped",
              "`0.9/0.9.3.md`" in out and "no `## Findings` section" in out)

        # A section with content in a format the parser does not know must be
        # LOUD: listed as unparsed, and a non-zero exit.
        build(tmp, {"0.9/0.9.2.md": THIRD_FORMAT})
        rc, out, err = run(tmp)
        check("an unrecognised format exits 1", rc == 1, f"exit {rc}")
        check("an unrecognised format is listed as UNPARSED",
              "UNPARSED" in out and "0.9/0.9.2.md" in out)
        check("the unparsed count reaches stderr", "unparsed section" in err)

        out_file = os.path.join(tmp, "INDEX.md")
        os.remove(os.path.join(tmp, "0.9/0.9.2.md"))
        rc, out, err = run(tmp, "--out", out_file)
        check("--out writes the file and says where", rc == 0 and os.path.isfile(out_file)
              and out_file in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    rc, out, err = run(os.path.join(tempfile.gettempdir(), "devteam-no-such-dir-xyz"))
    check("a missing directory exits 2", rc == 2, f"exit {rc}")

    total = passed + failed
    print(f"\nfindings_index control: {passed} passed, {failed} failed, {total} cases")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
