#!/usr/bin/env python3
"""How often the verification layer said PASS and FAIL, counted from the record.

A CHECKPOINT COUNTED ITS VERDICTS WITH GREP, AND GREP COUNTS TEXT. The
`checkpoint` skill's verification tally was two `grep -coE "verify [A-Za-z0-9-]+
PASS"` commands over RECORD.md, which count the lines the words appear on. On
pricelog, C-5 reported eleven PASS and three FAIL where the record's verdict
entries held nine PASS: the grep also matched a hypothetical inside a finding --
"Had the record said only `verify T-2 PASS`" (RECORD.md:422) -- and a step
verifier's line (RECORD.md:684). C-4 and C-5 attributed the three FAILs "(T-9
twice, T-7 once)" while calling them three different tasks, and a hygiene
auditor re-ran the same commands and reported a match, which showed the count
could be reproduced and nothing about whether it counted verdicts (roadmap
0.2.9's Findings, *The checkpoints' verification tally counts grep matches*;
roadmap 0.3.2, L-2.12).

SO THIS READS ENTRIES, NOT TEXT. A verdict is a list item whose entry is
`verify <label> PASS|FAIL`, the form the RECORD template's vocabulary defines:

    - `verify T4-fetch-2343 FAIL` — the manager's fresh verifier, ...

  * The item is top-level and outside a fence, and its backticks hold the entry
    and nothing else: whatever else the author has to say goes after them. Bold
    or italic around the item is decoration, as it is in a board cell (L-2.1).
    Both are the owner's answers, 2026-09-24: pricelog wrote six verdicts in
    bold, and one, RECORD.md:684, with words inside its backticks.
  * The label names the verdict's task. A claim's `T<n>-<slug>-<HHMM>`, which is
    how the claim protocol in the BOARD template writes a label, and a task's
    `T-n` are the task's verdicts. A step's `T-n.S-m` is that step's.

A list item whose entry is `verify` and does not read that way -- nested under
another item, with words inside its backticks, a label that names no task -- is
verify-shaped, and is named by its line as not evaluated rather than skipped
(roadmap 0.3.1, L-1.3). A verdict mentioned anywhere else -- a `finding:` entry
quoting one, a `report` entry summarising one -- is not an entry and is not
read, which is the whole of the difference from the grep. RECORD.md is
append-only, so an entry read as not evaluated stays that way: the remedy is a
correct entry appended after it, and the count then carries both.

It prints four counts -- task and step, PASS and FAIL -- and one line per task
naming the lines it read, so a checkpoint quotes a count and its members from
one output. A record with no verdict yet is clean, with its zeros shown.

    python3 tally.py <project> [--at <commit>] [--json]

`--at` reads RECORD.md as that commit holds it, which is how a checkpoint's
count is measured again afterwards. Exit 0 clean, 2 could not run, 3 not
evaluated -- the contract is result.py's (roadmap 0.3.1, L-1.1). It reports no
finding, so it never exits 1.

Its control is test_tally.py.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)

USAGE = "usage: tally.py <project> [--at <commit>] [--json]"
ITEM = re.compile(r"^(\s*)[-*+]\s+(.*)$")
FENCE = re.compile(r"^\s*(?:```|~~~)")
# Emphasis around an entry is decoration, as a board cell's is (L-2.1):
# pricelog wrote `- **`verify T-15 FAIL`** — …` six times.
DECOR = r"(?:[*_]{1,3}\s*)?"
# An item whose entry IS `verify`, however the rest is written. `verified` and
# `verify-note` are other words.
VERIFY_ISH = re.compile(r"^" + DECOR + r"`?\s*verify(?![\w-])")
VERDICT = re.compile(r"^" + DECOR + r"`verify[ \t]+([^\s`]+)[ \t]+(PASS|FAIL)`")
STEP = re.compile(r"^T-(\d+)\.S-(\d+)$")
TASK = re.compile(r"^T-(\d+)$")
CLAIM = re.compile(r"^T(\d+)-\S+$")
GRAMMAR = ("a top-level `verify <label> PASS|FAIL` with nothing else inside its backticks, "
           "the label `T<n>-<slug>-<HHMM>`, `T-n` or `T-n.S-m`")


def read(text):
    """(verdicts, offered, unread) in RECORD.md's text. Each verdict is
    `(line, task number, step number or None, "PASS" or "FAIL")`; `offered`
    counts the verify-shaped items; `unread` is the line of each one the
    grammar did not read."""
    verdicts, offered, unread, fenced = [], 0, [], False
    for n, line in enumerate(text.split("\n"), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        m = None if fenced else ITEM.match(line)
        if not m or not VERIFY_ISH.match(m.group(2)):
            continue
        offered += 1
        v = None if m.group(1) else VERDICT.match(m.group(2))
        label = v.group(1) if v else ""
        step, task = STEP.match(label), TASK.match(label) or CLAIM.match(label)
        if step:
            verdicts.append((n, int(step.group(1)), int(step.group(2)), v.group(2)))
        elif task:
            verdicts.append((n, int(task.group(1)), None, v.group(2)))
        else:
            unread.append(n)
    return verdicts, offered, unread


def per_task(verdicts):
    """{task number: the line that says what its verdicts were}."""
    out = {}
    for task in sorted({v[1] for v in verdicts}):
        parts = []
        for layer, mine in (("task", [v for v in verdicts if v[1] == task and v[2] is None]),
                            ("step", [v for v in verdicts if v[1] == task and v[2] is not None])):
            # A task's own verdicts are always said, zeros too: a task closed
            # with no task-level PASS is what C-8 asserted and C-9 found.
            if layer == "step" and not mine:
                continue
            passed = sum(1 for v in mine if v[3] == "PASS")
            where = f" ({result.anchors([('RECORD.md', v[0]) for v in mine])})" if mine else ""
            parts.append(f"{layer} {passed} PASS, {len(mine) - passed} FAIL{where}")
        out[task] = "; ".join(parts)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json, argv = result.flag(argv, "--json")
    at = None
    if "--at" in argv:
        i = argv.index("--at")
        if i + 1 >= len(argv):
            return result.could_not_run("tally", USAGE, as_json)
        at, argv = argv[i + 1], argv[:i] + argv[i + 2:]
    if len(argv) != 1:
        return result.could_not_run("tally", USAGE, as_json)
    project = os.path.realpath(argv[0])
    devteam = project if os.path.basename(project) == "devteam" else os.path.join(project, "devteam")
    target = "RECORD.md" + (f" at {at}" if at else "")
    res = result.Result("tally", target)
    raw = None

    if at:
        git = lambda *a: subprocess.run(["git", "-C", project, *a], capture_output=True)
        top = git("rev-parse", "--show-toplevel")
        if top.returncode:
            return result.could_not_run("tally", "not a git repository, so --at reads nothing", as_json)
        commit = git("rev-parse", "--verify", "--quiet", f"{at}^{{commit}}")
        if commit.returncode:
            return result.could_not_run("tally", f"{at!r} names no commit", as_json)
        rel = os.path.relpath(os.path.join(devteam, "RECORD.md"),
                              os.path.realpath(top.stdout.decode().strip()))
        shown = git("show", f"{commit.stdout.decode().strip()}:{rel}")
        if shown.returncode:
            res.gap("RECORD.md", f"{at} holds no {rel}, so no verdict was counted")
        else:
            raw = shown.stdout
    elif not os.path.isdir(devteam):
        return result.could_not_run("tally", "not a devteam project", as_json)
    else:
        try:
            with open(os.path.join(devteam, "RECORD.md"), "rb") as fh:
                raw = fh.read()
        except FileNotFoundError:
            res.gap("RECORD.md", "devteam/ has no RECORD.md, so no verdict was counted")
        except OSError as exc:
            res.gap("RECORD.md", f"RECORD.md cannot be read ({exc.strerror}), so no verdict "
                                 "was counted")

    verdicts = []
    if raw is not None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            res.gap("RECORD.md", f"RECORD.md is not UTF-8 (byte {exc.object[exc.start]:#04x} "
                                 f"at offset {exc.start}), so no verdict was counted")
        else:
            verdicts, offered, unread = read(text)
            if unread:
                res.gap("RECORD.md's verdict entries", result.unparsed(
                    [("RECORD.md", n) for n in unread], offered, "verify-shaped entries",
                    GRAMMAR, "no verdict was counted from them"))

    for layer in ("task", "step"):
        for word in ("PASS", "FAIL"):
            res.count(sum(1 for v in verdicts
                          if (v[2] is None) == (layer == "task") and v[3] == word),
                      f"{layer} {word}")
    for task, line in per_task(verdicts).items():
        res.note(f"T-{task}", line)
    return result.emit([res], as_json)


if __name__ == "__main__":
    sys.exit(main())
