#!/usr/bin/env python3
"""Negative control for ledger.py, the disposition ledger's one reader (P-35).

The ledger exists because pricelog's items reached no owner (roadmap 0.3.3,
L-3.1), and the vocabulary is closed because the one it replaces could not say
when an open item was due: T-18's three deferrals read "carried to the
checkpoint ... to be given an owner there", and both checks passed them as
decided (L-3.2). So the cases here are that wording and its neighbours, each
stated as what the ledger reads, what it counts, and what it names as not
read. The `fp-` and `clean-` cases are the honest forms that must read clean:
a command that named every wrapped disposition would be one nobody ran.

It runs ledger.py as a command, as the manager does, and reads the module's
first-word test directly, because check_refs and check_trace import it.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
LEDGER = (os.environ.get("DEVTEAM_SUBJECT_LEDGER")
          or os.path.join(HERE, "ledger.py"))
TEMPLATE = os.path.join(HERE, "..", "templates", "LEDGER.md")
EXAMPLE = re.compile(r"^<!-- example:begin -->\n.*?^<!-- example:end -->\n", re.S | re.M)

HEAD = "# The ledger\n\nProse about the ledger.\n\n---\n\n"


def entry(n, disposition, raised="manager 2026-09-18", extra=""):
    body = f"### ITM-{n} — item {n}\n\n- **Raised.** {raised}\n"
    if disposition is not None:
        body += f"- **Disposition.** {disposition}\n"
    return body + extra + "\n"


# One entry per value, T-18's ten in the vocabulary as the plan measured them:
# COR-1 raised Q-28, COR-5 fixed by one commit, COR-6 open until C-9, COR-8
# fixed by two, and the other two values beside them.
EVERY_VALUE = HEAD + "".join((
    entry(1, "raised Q-28", "T-18.S-4 COR-1"),
    entry(2, "fixed (a4f3774)", "T-18.S-4 COR-5"),
    entry(3, "open (until C-9)", "T-18.S-4 COR-6"),
    entry(4, "open (until T-18)", "T-18.S-4 COR-10"),
    entry(5, "routed T-18", "T-18.S-4 COR-7",
          "- **Needs.**\n  - `pricelog/cli.py`\n"),
    entry(6, "declined (D-45)", "T-18.S-4 COR-9"),
    entry(7, "fixed (a4f3774, 55c0eb7)", "T-18.S-4 COR-8"),
))


def line_of(text, needle):
    return next(n for n, l in enumerate(text.split("\n"), 1) if needle in l)


def project(ledger=None, raw=None, devteam=True):
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-ledger-"))
    if devteam:
        os.makedirs(os.path.join(root, "devteam"))
    if ledger is not None or raw is not None:
        with open(os.path.join(root, "devteam", "LEDGER.md"), "wb") as fh:
            fh.write(raw if raw is not None else ledger.encode("utf-8"))
    return root


def run(root, *args):
    return subprocess.run([sys.executable, LEDGER, root, *args], capture_output=True, text=True)


def read(out):
    """(counts, notes, the lines named as not read, the parts) from the printed lines."""
    m = re.search(r"\[(\d+) entries, (\d+) open, (\d+) routed, (\d+) raised, "
                  r"(\d+) declined, (\d+) fixed\]", out)
    counts = tuple(int(x) for x in m.groups()) if m else None
    notes = dict(re.findall(r"^  (ITM-\d+): (.*)$", out, re.M))
    parts = set(re.findall(r"^  not evaluated: (.+?) — ", out, re.M))
    lines = {int(n) for n in re.findall(r"\bline (\d+)[,:]", out)}
    return counts, notes, lines, parts


def load():
    spec = importlib.util.spec_from_file_location("ledger_under_test", LEDGER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
            for line in str(got).rstrip("\n").split("\n")[:14]:
                print(f"        | {line}")

    def case(name, ledger, exit_, counts, notes=None, lines=(), parts=None, said=""):
        """Run ledger.py over `ledger` and compare everything it printed."""
        root = project(ledger)
        try:
            out = run(root)
            got_counts, got_notes, got_lines, got_parts = read(out.stdout)
            want_parts = parts if parts is not None else (
                {"LEDGER.md's entries"} if lines else set())
            ok = (out.returncode == exit_ and got_counts == counts
                  and got_lines == set(lines) and got_parts == want_parts
                  and (notes is None or got_notes == notes) and said in out.stdout)
            check(name, ok, out.stdout + out.stderr)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- an entry per value, each read and counted ---------------------------
    at = lambda needle: line_of(EVERY_VALUE, needle)
    case("clean-an-entry-per-value-is-counted", EVERY_VALUE, 0, (7, 2, 1, 1, 1, 2),
         notes={
             "ITM-1": f"raised Q-28 (LEDGER.md:{at('ITM-1 ')})",
             "ITM-2": f"fixed (a4f3774) (LEDGER.md:{at('ITM-2 ')})",
             "ITM-3": f"open (until C-9) (LEDGER.md:{at('ITM-3 ')})",
             "ITM-4": f"open (until T-18) (LEDGER.md:{at('ITM-4 ')})",
             "ITM-5": f"routed T-18 (LEDGER.md:{at('ITM-5 ')})",
             "ITM-6": f"declined (D-45) (LEDGER.md:{at('ITM-6 ')})",
             "ITM-7": f"fixed (a4f3774, 55c0eb7) (LEDGER.md:{at('ITM-7 ')})"})
    # THE TEMPLATE AS SETUP INSTALLS IT: its example stripped, no entry.
    installed = EXAMPLE.sub("", open(TEMPLATE, encoding="utf-8").read())
    case("clean-an-empty-ledger-shows-its-zeros", installed, 0, (0, 0, 0, 0, 0, 0), notes={})
    # A field is read whole (roadmap 0.3.2, L-2.3): a list of commits wrapped
    # onto its next line is one value.
    case("fp-a-disposition-continuing-onto-a-second-line-is-read-whole",
         HEAD + "### ITM-1 — x\n\n- **Raised.** manager 2026-09-18\n"
                "- **Disposition.** fixed (a4f3774,\n  55c0eb7)\n", 0, (1, 0, 0, 0, 0, 1))
    # pricelog's manager backticked every hash it wrote.
    case("fp-a-backticked-commit-is-read-bare",
         HEAD + entry(1, "fixed (`a4f3774`, `55c0eb7`)"), 0, (1, 0, 0, 0, 0, 1))
    case("fp-whitespace-inside-a-value-is-layout",
         HEAD + entry(1, "open  (until   C-9)"), 0, (1, 1, 0, 0, 0, 0))
    # Anything else the manager writes in an entry is not a field.
    case("fp-a-note-on-its-own-bullet-is-not-a-field",
         HEAD + entry(1, "routed T-2", extra="- **Why.** the task owns `src/`.\n"
                                            "Prose after the fields.\n"), 0, (1, 0, 1, 0, 0, 0))
    # The preamble teaches the grammar; a field named there opens no entry.
    case("fp-a-field-named-in-the-preamble-is-not-an-entry",
         "# The ledger\n\nEach entry carries a `- **Disposition.**` line.\n"
         "- **Disposition.** open\n\n---\n\n" + entry(1, "raised Q-1"), 0, (1, 0, 0, 1, 0, 0))
    case("fp-an-entry-inside-a-fence-is-quoted",
         HEAD + "```\n" + entry(1, "open") + "```\n", 0, (0, 0, 0, 0, 0, 0), notes={})
    # A heading that is not an entry's ends the entry above it: a field under
    # it is prose, not that entry's second disposition.
    case("fp-another-heading-ends-an-entry",
         HEAD + entry(1, "raised Q-1") + "## Notes\n\n- **Disposition.** open\n",
         0, (1, 0, 0, 1, 0, 0))

    # --- F-99 and F-139's state, and T-18's wording: named, never counted ----
    for name, value in (
            ("a-bare-open-names-no-date", "open"),
            ("f139-open-carried-to-the-checkpoint-names-no-date",
             "open — carried to the checkpoint, to be given an owner there"),
            ("t18-carried-to-the-checkpoint-is-outside-the-vocabulary",
             "carried to the checkpoint D-38 requires before T-18's next dispatch, "
             "to be given an owner there"),
            ("t18-cor1-put-to-the-client-is-outside-the-vocabulary",
             "put to the client as Q-28"),
            ("an-open-with-a-note-after-its-date-is-outside-the-vocabulary",
             "open (until C-9) — at the checkpoint"),
            ("an-uppercase-hash-is-not-a-commit", "fixed (A4F3774)"),
            ("a-short-hash-is-not-a-commit", "fixed (a4f37)"),
            ("fixed-with-no-commit-names-nothing", "fixed ()"),
            ("routed-to-two-tasks-is-outside-the-vocabulary", "routed T-1, T-2"),
            ("decoration-around-a-value-is-not-read", "**raised Q-1**")):
        text = HEAD + entry(1, value)
        case(name, text, 3, (1, 0, 0, 0, 0, 0), lines=[line_of(text, "Disposition.")],
             said="is not in the vocabulary")
    text = HEAD + entry(1, None)
    case("an-entry-with-no-disposition-is-named", text, 3, (1, 0, 0, 0, 0, 0),
         lines=[line_of(text, "ITM-1")], said="ITM-1 has no `Disposition.`")

    # --- lines the grammar offered and did not read --------------------------
    for name, heading in (("an-entry-heading-at-the-wrong-level", "## ITM-2 — x"),
                          ("an-entry-heading-with-a-colon", "### ITM-2: x"),
                          ("an-entry-heading-with-no-dash", "### ITM2 — x"),
                          ("an-entry-heading-with-no-space", "###ITM-2 — x")):
        text = HEAD + entry(1, "raised Q-1") + heading + "\n\n- **Disposition.** open\n"
        case(name, text, 3, (1, 0, 0, 1, 0, 0), lines=[line_of(text, heading)])
    text = HEAD + entry(1, None, extra="- **Disposition**: routed T-2\n")
    case("a-disposition-named-with-a-colon-is-named", text, 3, (1, 0, 0, 0, 0, 0),
         lines=[line_of(text, "Disposition**:"), line_of(text, "ITM-1")])
    text = HEAD + entry(1, "open (until C-9)", extra="- **Disposition.** fixed (55c0eb7)\n")
    case("a-second-disposition-is-named-and-the-first-stands", text, 3, (1, 1, 0, 0, 0, 0),
         lines=[line_of(text, "fixed (55c0eb7)")], said="a second `Disposition.` in ITM-1")
    text = HEAD + entry(1, "raised Q-1", raised=None).replace("- **Raised.** None\n",
                                                            "- Raised: manager 2026-09-18\n")
    case("a-raised-field-named-and-not-written-is-named", text, 3, (1, 0, 0, 1, 0, 0),
         lines=[line_of(text, "Raised:")])
    # One unread entry among read ones: the read ones are still counted.
    text = HEAD + entry(1, "raised Q-1") + entry(2, "open") + entry(3, "declined (D-1)")
    case("an-unread-entry-among-read-ones-is-named-alone", text, 3, (3, 0, 0, 1, 1, 0),
         lines=[line_of(text, "- **Disposition.** open")])

    # --- the file itself, and the invocation ---------------------------------
    case("no-ledger-is-not-evaluated", None, 3, (0, 0, 0, 0, 0, 0), parts={"LEDGER.md"})
    root = project(raw=b"# The ledger\n\n### ITM-1 \xff\n")
    try:
        out = run(root)
        check("a-ledger-not-utf8-is-not-evaluated",
              out.returncode == 3 and "LEDGER.md — LEDGER.md is not UTF-8" in out.stdout,
              out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    root = project(devteam=False)
    try:
        out = run(root)
        check("no-devteam-is-exit-2", out.returncode == 2 and "not a devteam project" in out.stderr,
              out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    out = subprocess.run([sys.executable, LEDGER], capture_output=True, text=True)
    check("no-argument-is-exit-2", out.returncode == 2 and "usage:" in out.stderr, out.stderr)
    root = project(EVERY_VALUE)
    try:
        out = run(root, "--json")
        try:
            doc = json.loads(out.stdout)
            r = doc["results"][0]
            ok = (out.returncode == 0 and doc["exit"] == 0 and r["check"] == "ledger"
                  and r["counts"] == {"entries": 7, "open": 2, "routed": 1, "raised": 1,
                                      "declined": 1, "fixed": 2}
                  and r["notes"][0] == {"label": "ITM-1",
                                        "text": f"raised Q-28 (LEDGER.md:{at('ITM-1 ')})"})
        except (ValueError, KeyError, IndexError):
            ok = False
        check("json-carries-the-counts-and-each-entrys-line", ok, out.stdout + out.stderr)
        out = run(os.path.join(root, "devteam"))
        check("fp-the-devteam-directory-itself-is-the-project",
              out.returncode == 0 and read(out.stdout)[0] == (7, 2, 1, 1, 1, 2),
              out.stdout + out.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # --- the module: the vocabulary, and the first-word test both checks use --
    mod = load()
    # Each named for what it asserts, and with no space in the name, so that
    # a mutation runner reading `FAIL <name>` reads the whole of it.
    for name, value, want in (
            ("fp-vocabulary-open-until-a-task", "open (until T-3)", ("open", "T-3")),
            ("fp-vocabulary-open-until-a-checkpoint", "open (until C-9)", ("open", "C-9")),
            ("fp-vocabulary-routed", "routed T-18", ("routed", "T-18")),
            ("fp-vocabulary-raised", "raised Q-28", ("raised", "Q-28")),
            ("fp-vocabulary-declined", "declined (D-45)", ("declined", "D-45")),
            ("fp-vocabulary-fixed-by-one-commit", "fixed (a4f3774)", ("fixed", ["a4f3774"])),
            ("fp-vocabulary-fixed-by-two-one-backticked", "fixed (`a4f3774`,  55c0eb7)",
             ("fixed", ["a4f3774", "55c0eb7"])),
            ("fp-vocabulary-fixed-by-a-whole-hash", "fixed (" + "a" * 40 + ")", ("fixed", ["a" * 40])),
            ("vocabulary-open-until-a-question", "open (until Q-3)", None),
            ("vocabulary-open-until-two", "open (until T-3, C-9)", None),
            ("vocabulary-routed-to-a-question", "routed Q-3", None),
            ("vocabulary-raised-two-questions", "raised Q-28, Q-29", None),
            ("vocabulary-declined-without-parentheses", "declined D-45", None),
            ("vocabulary-fixed-without-parentheses", "fixed a4f3774", None),
            ("vocabulary-fixed-by-a-hash-too-long", "fixed (" + "a" * 41 + ")", None),
            ("vocabulary-open-capitalised", "Open (until C-9)", None)):
        got = mod.disposition(value)
        check(name, got == want, f"{value!r}: {got!r}, not {want!r}")
    # `Needs.` is a path list: its items are entries of their own, never the
    # field's value read whole (FORMATS §"Identifier declarations").
    listed, unread = mod.entries((HEAD + entry(1, "routed T-2", extra=(
        "- **Needs.**\n  - `src/a.py`\n  - `tests/`\n"))).split("\n"))
    got = (listed[0].fields.get("Needs"), [t for _, t in listed[0].block if t.startswith("  - ")],
           unread, listed[0].parsed())
    check("fp-a-needs-list-is-its-items-not-its-value",
          got[0] is not None and got[0][1] == "" and got[1] == ["  - `src/a.py`", "  - `tests/`"]
          and not got[2] and got[3] == ("routed", "T-2"), repr(got))
    # `open` is a word, not a prefix; bold around it is decoration; a note
    # after it leaves it open (roadmap 0.3.2, L-2.3).
    for name, value, want in (("first-word-open", "open", True),
                              ("first-word-bold-open", "**open**", True),
                              ("first-word-open-capitalised-with-a-note", "Open — carried on", True),
                              ("first-word-open-with-its-date", "open (until C-9)", True),
                              ("first-word-open-indented", "  open", True),
                              ("fp-first-word-opened", "opened as Q-1", False),
                              ("fp-first-word-open-ended", "open-ended", False),
                              ("fp-first-word-open-later-in-the-value",
                               "routed T-1, the open question settled", False),
                              ("fp-first-word-carried", "carried to the checkpoint", False)):
        check(name, mod.is_open(value) is want, f"is_open({value!r}) is {mod.is_open(value)!r}")

    total = passed + failed
    print(f"\nledger control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
