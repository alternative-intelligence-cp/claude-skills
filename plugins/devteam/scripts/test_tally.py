#!/usr/bin/env python3
"""Negative control for tally.py, the checkpoint's verification tally (P-35).

The tally it replaces was two greps, and a grep cannot fail in the way that
matters: it counts every line the words appear on, so a record that QUOTES a
verdict and a record that RECORDS one read the same. The cases here are the
shapes pricelog's record actually wrote -- a hypothetical inside a finding, a
report entry summarising a verdict, a step verifier's line, six verdicts in
bold -- and each states what is a verdict, what is not, and what is named as
not read (roadmap 0.3.2, L-2.12). The `fp-` cases are the honest forms that
must read clean: a tally that named every bold verdict would be one nobody
quoted.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
TALLY = (os.environ.get("DEVTEAM_SUBJECT_TALLY")
         or os.path.join(HERE, "tally.py"))
TEMPLATE = os.path.join(HERE, "..", "templates", "RECORD.md")

HEAD = ("# The record\n\n"
        "`dispatch <label>` · `report <label> <status> <tokens> <minutes>` ·\n"
        "`verify <label> PASS|FAIL` · `advance T-n` · `release T-n` ·\n\n---\n\n")

# pricelog's RECORD.md as it stood at C-5 (2b8f0de), cut to its entries'
# shapes and in their order: twelve task verdicts, nine PASS and three FAIL on
# T-4, T-9 and T-7; a bold paragraph quoting the grep; a finding quoting a
# hypothetical verdict (RECORD.md:422); and the step verifier's line with words
# inside its backticks (RECORD.md:684). C-5's own grep read 11 PASS here.
C5 = HEAD + """## 2026-09-10

- `dispatch T1-append-atomicity-0551` — supervisor on Sonnet 5.
- `verify T1-append-atomicity-0551 PASS` — the manager's own verifier.
- `verify T5-harness-restart-0730 PASS` — built its own adversarial cases.
- `verify T3-store-1301 PASS` — attacked rather than re-ran.
- **THE VERIFICATION LAYER REJECTED TWO STEPS ON THIS TASK.** `grep -coE "verify [A-Za-z0-9-]+ FAIL" RECORD.md` still returns **0**.
- `verify T2-clock-1301 PASS` — read the entire package.

## 2026-09-11

- `verify T4-fetch-2343 FAIL` — the first task-level FAIL in this project's life.
- `verify T4-fetch-2343 PASS` — the manager's second verifier.
- `finding: a check that forces a link cannot be satisfied by writing.` **Had the record said only `verify T-2 PASS`, there would have been no way to tell.**
- `verify T8-reader-0833 PASS` — answering R-11 and R-2 separately.
- `verify T6-cli-1226 PASS` — all three hold.
- `verify T9-heal-1856 FAIL` — R-4 does not hold.
- `verify T-9.S-11 PASS, ticked at `6a68166`` — the step verifier confirmed by reading the code.
- `verify T9-stderr-1309 PASS` — R-12 and R-1 hold.

## 2026-09-13

- `verify T7-lint-1606 FAIL` — R-10's evidence fails on one of three limbs.
- `verify T-10 PASS` — fresh verifier under P-18.
"""


def line_of(text, needle):
    return next(n for n, l in enumerate(text.split("\n"), 1) if needle in l)


def project(record=None, raw=None, devteam=True):
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-tally-"))
    if devteam:
        os.makedirs(os.path.join(root, "devteam"))
    if record is not None or raw is not None:
        with open(os.path.join(root, "devteam", "RECORD.md"), "wb") as fh:
            fh.write(raw if raw is not None else record.encode("utf-8"))
    return root


def git(root, *args):
    subprocess.run(["git", "-C", root, "-c", "user.name=control",
                    "-c", "user.email=control@example.invalid", *args],
                   capture_output=True, text=True, check=True)


def tally(root, *args):
    return subprocess.run([sys.executable, TALLY, root, *args], capture_output=True, text=True)


def read(out):
    """(counts, notes, gap lines, gap parts) from tally's printed lines."""
    m = re.search(r"\[(\d+) task PASS, (\d+) task FAIL, (\d+) step PASS, (\d+) step FAIL\]", out)
    counts = tuple(int(x) for x in m.groups()) if m else None
    notes = dict(re.findall(r"^  (T-\d+): (.*)$", out, re.M))
    parts = set(re.findall(r"^  not evaluated: (.+?) — ", out, re.M))
    lines = set()
    for anchor in re.findall(r"^  not evaluated: .*\(RECORD\.md:([\d, -]+)\)$", out, re.M):
        for piece in anchor.split(", "):
            a, _, b = piece.partition("-")
            lines.update(range(int(a), int(b or a) + 1))
    return counts, notes, lines, parts


def main():
    passed = failed = fp = 0

    def check(name, ok, got):
        nonlocal passed, failed, fp
        fp += name.startswith(("fp-", "clean-"))
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}")
            for line in str(got).rstrip("\n").split("\n")[:12]:
                print(f"        | {line}")

    def case(name, record, exit_, counts, notes=None, lines=(), parts=None, said="", pre=True):
        """Run tally over `record` and compare everything it printed. `pre` is
        what the fixture itself must hold for the case to mean anything."""
        root = project(record)
        try:
            out = tally(root)
            got_counts, got_notes, got_lines, got_parts = read(out.stdout)
            want_parts = parts if parts is not None else (
                {"RECORD.md's verdict entries"} if lines else set())
            ok = (pre is True and out.returncode == exit_ and got_counts == counts
                  and got_lines == set(lines) and got_parts == want_parts
                  and (notes is None or got_notes == notes) and said in out.stdout)
            check(name, ok, (f"fixture: {pre}\n" if pre is not True else "") + out.stdout + out.stderr)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- A12: the record at C-5 -------------------------------------------
    # The fixture first shown to carry the defect: C-5's own grep reads eleven
    # PASS here, as it did on the real record (P-35b). Then tally reads nine
    # and three, names the step verifier's line, and splits the FAILs one
    # each over T-4, T-7 and T-9 -- where C-4 and C-5 wrote "(T-9 twice, T-7
    # once)".
    greps = [sum(1 for l in C5.split("\n") if re.search(p, l))
             for p in (r"verify [A-Za-z0-9.-]+ PASS", r"verify [A-Za-z0-9.-]+ FAIL")]
    at = lambda needle: line_of(C5, needle)
    case("a12-the-c5-record-is-nine-pass-three-fail-and-names-684",
         C5, 3, (9, 3, 0, 0),
         notes={
             "T-1": f"task 1 PASS, 0 FAIL (RECORD.md:{at('T1-append-atomicity-0551 PASS')})",
             "T-2": f"task 1 PASS, 0 FAIL (RECORD.md:{at('T2-clock-1301')})",
             "T-3": f"task 1 PASS, 0 FAIL (RECORD.md:{at('T3-store-1301')})",
             "T-4": (f"task 1 PASS, 1 FAIL (RECORD.md:{at('T4-fetch-2343 FAIL')}-"
                     f"{at('T4-fetch-2343 PASS')})"),
             "T-5": f"task 1 PASS, 0 FAIL (RECORD.md:{at('T5-harness-restart-0730')})",
             "T-6": f"task 1 PASS, 0 FAIL (RECORD.md:{at('T6-cli-1226')})",
             "T-7": f"task 0 PASS, 1 FAIL (RECORD.md:{at('T7-lint-1606')})",
             "T-8": f"task 1 PASS, 0 FAIL (RECORD.md:{at('T8-reader-0833')})",
             "T-9": f"task 1 PASS, 1 FAIL (RECORD.md:{at('T9-heal-1856')}, {at('T9-stderr-1309')})",
             "T-10": f"task 1 PASS, 0 FAIL (RECORD.md:{at('verify T-10 PASS')})"},
         lines=[at("T-9.S-11")], said="1 of 13 verify-shaped entries do not parse",
         pre=greps == [11, 3] or f"C-5's grep reads {greps} here, not [11, 3]")

    # --- what is a verdict ---------------------------------------------------
    one = HEAD + "## 2026-09-10\n\n- `verify T-1 PASS` — the manager's verifier.\n"
    case("clean-one-verdict-is-counted", one, 0, (1, 0, 0, 0),
         notes={"T-1": f"task 1 PASS, 0 FAIL (RECORD.md:{line_of(one, 'verify T-1')})"})
    case("fp-a-claim-label-names-its-task",
         HEAD + "- `verify T9-heal-1856 FAIL` — R-4 does not hold.\n", 0, (0, 1, 0, 0),
         notes={"T-9": "task 0 PASS, 1 FAIL (RECORD.md:8)"})
    case("fp-a-task-id-label-is-the-tasks-own-verdict",
         HEAD + "- `verify T-10 PASS` — fresh verifier.\n", 0, (1, 0, 0, 0),
         notes={"T-10": "task 1 PASS, 0 FAIL (RECORD.md:8)"})
    # A step's verdict is its task's, in its own column, and the task's own
    # zeros are still said: a task with no task-level verdict is what C-8
    # asserted away and C-9 found.
    case("fp-a-step-verdict-is-its-tasks-step",
         HEAD + "- `verify T-9.S-11 PASS` — ticked at `6a68166`.\n", 0, (0, 0, 1, 0),
         notes={"T-9": "task 0 PASS, 0 FAIL; step 1 PASS, 0 FAIL (RECORD.md:8)"})
    # Decoration, by the owner's answer: pricelog wrote six verdicts in bold,
    # with the author's words after the entry, inside the bold or outside it.
    bold = HEAD + ("- **`verify T-15 FAIL`** — the fourth FAIL in this project.\n"
                   "- **`verify T-15 PASS` — re-verification after the FAIL.**\n"
                   "- **`verify T-11 PASS`; R-13 discharged (T-11); T-11 closed.**\n")
    case("fp-a-bold-verdict-is-read", bold, 0, (2, 1, 0, 0),
         notes={"T-11": "task 1 PASS, 0 FAIL (RECORD.md:10)",
                "T-15": "task 1 PASS, 1 FAIL (RECORD.md:8-9)"})
    case("fp-an-italic-verdict-is-read",
         HEAD + "- *`verify T-2 PASS`* — read the whole package.\n", 0, (1, 0, 0, 0))
    case("fp-a-star-or-plus-bullet-is-an-item",
         HEAD + "* `verify T-1 PASS` — one.\n+ `verify T-2 FAIL` — two.\n", 0, (1, 1, 0, 0))

    # --- what is not a verdict, and is not read at all -----------------------
    case("fp-a-finding-quoting-a-verdict-is-not-one",
         HEAD + ("- `finding: the shape is worth keeping.` **Had the record said only "
                 "`verify T-2 PASS`, there would have been no way to tell.**\n"), 0, (0, 0, 0, 0))
    case("fp-a-report-entry-summarising-a-verdict-is-not-one",
         HEAD + ("- `verify T-13 PASS` — fresh verifier under P-18.\n"
                 "- `report supervisor T-13 DONE; verify T-13 PASS; T-13 closed.` Three steps.\n"),
         0, (1, 0, 0, 0))
    case("fp-a-verdict-inside-a-fence-is-quoted",
         HEAD + "```\n- `verify T-1 PASS` — pasted output\n```\n", 0, (0, 0, 0, 0))
    case("fp-other-words-beginning-verify-are-not-the-entry",
         HEAD + ("- `verified T-1 by hand` — a note.\n- verifying the fixture first.\n"
                 "- `verify-note: T-1 PASS` — a made-up entry.\n"), 0, (0, 0, 0, 0))
    case("fp-a-line-continuing-an-item-is-not-an-entry",
         HEAD + "- `finding: the manager should`\nverify T-1 PASS before it moves.\n",
         0, (0, 0, 0, 0))
    case("clean-a-record-with-no-verdict-shows-its-zeros",
         open(TEMPLATE, encoding="utf-8").read(), 0, (0, 0, 0, 0), notes={})

    # --- verify-shaped, and not read: named, never skipped -------------------
    words = HEAD + "- `verify T-9.S-11 PASS, ticked at `6a68166`` — the step verifier.\n"
    case("words-inside-the-backticks-are-not-evaluated", words, 3, (0, 0, 0, 0), lines=[8])
    case("a-label-naming-no-task-is-not-evaluated",
         HEAD + "- `verify heal-1856 PASS` — no task in the label.\n", 3, (0, 0, 0, 0), lines=[8])
    case("a-nested-verdict-is-not-evaluated",
         HEAD + "- `report T1-x-0900 DONE 1000 5`\n  - `verify T-1 PASS` — under a report.\n",
         3, (0, 0, 0, 0), lines=[9])
    case("a-verdict-without-backticks-is-not-evaluated",
         HEAD + "- verify T-1 PASS — no backticks.\n", 3, (0, 0, 0, 0), lines=[8])
    case("a-lowercase-verdict-word-is-not-evaluated",
         HEAD + "- `verify T-1 pass` — lowercase.\n", 3, (0, 0, 0, 0), lines=[8])
    # One unread among read ones: the read ones are still counted, and the line
    # names the one.
    case("an-unread-entry-among-read-ones-is-named-alone",
         HEAD + "- `verify T-1 PASS` — read.\n- `verify T-1 FAIL, then re-run` — not.\n",
         3, (1, 0, 0, 0), lines=[9])

    # --- the record itself, and the invocation -------------------------------
    case("no-record-is-not-evaluated", None, 3, (0, 0, 0, 0), parts={"RECORD.md"})
    root = project(raw=b"# The record\n\n- `verify T-1 PASS` \xff\n")
    try:
        out = tally(root)
        check("a-record-not-utf8-is-not-evaluated",
              out.returncode == 3 and "RECORD.md — RECORD.md is not UTF-8" in out.stdout,
              out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    root = project(devteam=False)
    try:
        out = tally(root)
        check("no-devteam-is-exit-2", out.returncode == 2 and "not a devteam project" in out.stderr,
              out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    out = subprocess.run([sys.executable, TALLY], capture_output=True, text=True)
    check("no-argument-is-exit-2", out.returncode == 2 and "usage:" in out.stderr, out.stderr)
    out = subprocess.run([sys.executable, TALLY, ".", "--at"], capture_output=True, text=True)
    check("at-without-a-commit-is-exit-2", out.returncode == 2 and "usage:" in out.stderr, out.stderr)

    # --- --at: the record as a commit holds it --------------------------------
    root = project(devteam=True)
    try:
        git(root, "init", "-q")
        open(os.path.join(root, "README.md"), "w").write("no record yet\n")
        git(root, "add", "README.md")
        git(root, "commit", "-qm", "before the record")
        before = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        rec = os.path.join(root, "devteam", "RECORD.md")
        open(rec, "w").write(HEAD + "- `verify T-1 PASS` — first.\n")
        git(root, "add", "devteam/RECORD.md")
        git(root, "commit", "-qm", "the first verdict")
        first = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
        open(rec, "a").write("- `verify T-2 FAIL` — second, on disk only.\n")
        out = tally(root, "--at", first)
        check("at-a-commit-reads-its-record-and-not-the-working-file",
              out.returncode == 0 and read(out.stdout)[0] == (1, 0, 0, 0)
              and out.stdout.startswith(f"RECORD.md at {first}: clean"), out.stdout + out.stderr)
        out = tally(root)
        check("fp-without-at-the-working-file-is-read",
              out.returncode == 0 and read(out.stdout)[0] == (1, 1, 0, 0), out.stdout + out.stderr)
        out = tally(root, "--at", before)
        check("at-a-commit-with-no-record-is-not-evaluated",
              out.returncode == 3 and read(out.stdout)[3] == {"RECORD.md"}
              and read(out.stdout)[0] == (0, 0, 0, 0), out.stdout + out.stderr)
        out = tally(root, "--at", "no-such-commit")
        check("at-naming-no-commit-is-exit-2",
              out.returncode == 2 and "names no commit" in out.stderr, out.stdout + out.stderr)
        out = tally(root, "--json", "--at", first)
        try:
            doc = json.loads(out.stdout)
            r = doc["results"][0]
            ok = (out.returncode == 0 and doc["exit"] == 0 and r["check"] == "tally"
                  and r["counts"] == {"task PASS": 1, "task FAIL": 0, "step PASS": 0, "step FAIL": 0}
                  and r["notes"] == [{"label": "T-1", "text": "task 1 PASS, 0 FAIL (RECORD.md:8)"}])
        except (ValueError, KeyError, IndexError):
            ok = False
        check("json-carries-the-counts-and-each-tasks-line", ok, out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    root = project(HEAD)
    try:
        out = tally(root, "--at", "HEAD")
        check("at-outside-a-repository-is-exit-2",
              out.returncode == 2 and "not a git repository" in out.stderr, out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = passed + failed
    print(f"\ntally control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
