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


# --- an audit's answer, as pricelog landed two and as the grammar has them --
# (roadmap 0.3.3, L-3.4). Each is cut to its shape: the lines the grammar
# reads, the headings that are the answer's text, and a fence of evidence.

# T-10.S-3's, as its supervisor landed it (tasks/T-10.md:423): under a REPORT
# line of its own making, with `## Finding n` headings. check_report names the
# REPORT line; no line of it opens an answer.
T10_LANDED = """REPORT auditor T-10.S-3 (adversarial pass, verbatim, P-17 — the auditor has no write
access and could not land this itself; reproduced here by the supervisor exactly as
received)

# T-10.S-3 Adversarial Audit — R-4 at HEAD (5864572)

## Environment and tree

```
python3 --version        -> Python 3.12.3
```

## Verdict

**No new behavioural violation of R-4 survived adversarial testing.**

## Finding 1 — R-4's text still claims a "sole exclusion" that isn't sole

```
# argv=[] (refusal path), fd 2 closed outright before exec:
-> returncode=1 stdout=b''
```

## Finding 2 (minor, cosmetic) — `cli.py`'s "F-44" citations point at the wrong finding

## Everything else tried — survived (R-4 held)

## Coverage statement
"""
# The same answer in the grammar's form.
T10_ANSWER = (T10_LANDED
              .replace("REPORT auditor T-10.S-3 (adversarial pass, verbatim, P-17 — the auditor has "
                       "no write\naccess and could not land this itself; reproduced here by the "
                       "supervisor exactly as\nreceived)", "AUDIT T-10.S-3 (correctness)")
              .replace("## Finding 1 — R-4's text", "## COR-1 — R-4's text")
              .replace("## Finding 2 (minor, cosmetic) — `cli.py`'s", "## COR-2 — `cli.py`'s")
              .replace("## Everything else", "- **Needs.**\n  - `pricelog/cli.py`\n\n"
                                            "## Everything else")
              + "\nEND AUDIT T-10.S-3\n")

# T-19.S-3's, as its supervisor landed it (tasks/T-19.md:1704-1869): inside a
# fence, text after its dimension, and its seven open items as bullets.
T19_ITEMS = (
    ("(L)/(M), the break.", "`pricelog/store.py` and `tests/test_store.py`"),
    ("The three false sentences about (L)/(M).", "`pricelog/store.py` and `tests/test_store.py`."),
    ("The message in items 2 and 3.", "`pricelog/cli.py` (outside T-19's scope)."),
    ("(N) as a DM-15 disclosure.", None),
    ("Item 8, DM-4 versus draft (a).", "a CHARTER decision on a user's interrupt."),
    ("Draft fixes.", None),
    ("Cosmetic.", None),
)
T19_LANDED = ("### S-3 — adversarial pass\n\n<Landed verbatim (P-17), with no `## COR-n` headings "
              "per F-104.>\n\n```\nAUDIT T-19.S-3 (correctness): **one break found.** A directory "
              "above the log replaced while a run waits for the lock breaks Gate point 3.\n\n"
              "**Open items for the manager (none decided here; each disposition open)**\n"
              + "".join(f"- **{title}**\n" + (f"  - Needs: {needs}\n" if needs else "")
                        for title, needs in T19_ITEMS)
              + "\n**Checked and found clean**\n- **No shortening.** No code path shortens the log.\n"
                "```\n\n## Supervisor's closing report — NEEDS-DECISION\n")
# The same text with the scope alone on its line, its items written as
# findings, and its closing line after it.
T19_ANSWER = ("### S-3 — adversarial pass\n\nAUDIT T-19.S-3 (correctness)\n\n**one break found.** "
              "A directory above the log replaced while a run waits for the lock breaks Gate "
              "point 3.\n\n"
              + "".join(f"## COR-{n} — {title}\n\n" + (f"- **Needs.** {needs}\n\n" if needs else "")
                        for n, (title, needs) in enumerate(T19_ITEMS, 1))
              + "**Checked and found clean**\n- **No shortening.** No code path shortens the log.\n\n"
                "END AUDIT T-19.S-3\n\n## Supervisor's closing report — NEEDS-DECISION\n")


def answer(scope="T-7", dimension="security", body="", end=None):
    """An answer in the grammar's form around `body`."""
    return (f"AUDIT {scope} ({dimension})\n\nThe verdict.\n\n{body}\n"
            f"END AUDIT {scope if end is None else end}\n")


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

    # --- an audit's answer (roadmap 0.3.3, L-3.4) ---------------------------
    # What the reader returns, cut to what each case compares: each answer's
    # scope, dimension, task and finding ids, and the lines it named.
    def reads(text, filed=False):
        got, unread = mod.answers(text.split("\n"), filed)
        return ([(a.scope, a.dimension, a.task, [f.ident for f in a.findings]) for a in got],
                sorted({n for n, _ in unread}))

    def answer_case(name, text, answers_, lines=(), filed=False, said=""):
        got = reads(text, filed)
        whats = " ".join(w for _, w in mod.answers(text.split("\n"), filed)[1])
        check(name, got == (answers_, sorted(lines)) and said in whats,
              f"{got!r}, not {(answers_, sorted(lines))!r}; said {whats!r}")

    # T-10: as landed, no line opens an answer, and check_report names its
    # REPORT line. Landed in the grammar's form, it is read with its two
    # findings; its level-one title, its section headings and the comment
    # lines in its fences are its text.
    answer_case("t10-as-pricelog-landed-it-opens-no-answer", T10_LANDED, [])
    answer_case("t10-landed-in-the-audit-form-is-read-with-its-two-findings", T10_ANSWER,
                [("T-10.S-3", "correctness", "T-10", ["COR-1", "COR-2"])])
    # T-19: its fenced opening line, with text after its dimension, is named
    # by its line, and nothing under it is counted (F-139).
    answer_case("t19-fenced-with-text-after-its-scope-is-named-by-its-line", T19_LANDED, [],
                [line_of(T19_LANDED, "AUDIT T-19.S-3")], said="inside a fenced block")
    answer_case("t19-with-its-scope-alone-and-an-end-line-is-read-with-seven-findings", T19_ANSWER,
                [("T-19.S-3", "correctness", "T-19", [f"COR-{n}" for n in range(1, 8)])])
    # ...its opening line unfenced, text still after it: named once. The
    # closing line after it is not named again, one fault being one report.
    text = T19_ANSWER.replace("AUDIT T-19.S-3 (correctness)\n\n**one break found.**",
                              "AUDIT T-19.S-3 (correctness): **one break found.**")
    answer_case("t19-text-after-its-dimension-is-named-once-and-nothing-counted", text, [],
                [line_of(text, "AUDIT T-19.S-3")], said="does not parse as `AUDIT <scope>")
    # A well-formed answer inside a fence is not read either.
    text = "```\n" + answer(body="## SEC-1 — x\n") + "```\n"
    answer_case("a-well-formed-answer-inside-a-fence-is-named-not-read", text, [],
                [line_of(text, "AUDIT T-7"), line_of(text, "END AUDIT")], said="inside a fenced block")

    # The opening line: its scope, its dimension, and nothing after them.
    for name, scope, dimension, task, label in (
            ("fp-a-steps-audit-is-its-tasks", "T-7.S-2", "safety", "T-7", "SAF"),
            ("fp-a-tasks-audit-is-its-own", "T-7", "security", "T-7", "SEC"),
            ("fp-a-milestones-audit-is-tied-to-no-task", "release", "hygiene", None, "HYG"),
            ("fp-a-milestone-word-may-hold-digits-and-hyphens", "release-2", "correctness", None,
             "COR")):
        text = answer(scope, dimension, f"## {label}-1 — x\n")
        answer_case(name, text, [(scope, dimension, task, [f"{label}-1"])])
    for name, line in (("an-audit-line-naming-no-dimension-is-named", "AUDIT T-7.S-2"),
                       ("an-audit-line-with-a-dimension-outside-the-four-is-named",
                        "AUDIT T-7 (performance)"),
                       ("an-audit-line-with-its-dimension-first-is-named",
                        "AUDIT (security) T-7"),
                       ("an-audit-line-with-a-colon-is-named", "AUDIT: T-7 (security)"),
                       ("an-emphasised-audit-line-is-named", "**AUDIT T-7 (security)**"),
                       ("a-task-mistyped-lowercase-is-named-not-read-as-a-milestone",
                        "AUDIT t-7 (security)"),
                       ("a-task-with-no-hyphen-is-named", "AUDIT T7 (security)"),
                       ("a-step-that-is-no-step-id-is-named", "AUDIT T-18.S-4-pre (security)"),
                       ("a-milestone-word-capitalised-is-named", "AUDIT Release (security)")):
        text = line + "\n\n## SEC-1 — x\n\nEND AUDIT T-7\n"
        answer_case(name, text, [], [1], said="does not parse as `AUDIT <scope>")
    # The audit skill's own form, copied with its placeholders unfilled, is
    # named at its opening line -- not only at its closing line, as an END
    # with no answer open -- and each of its two lines is wrong on its own.
    answer_case("the-audit-skills-form-copied-unfilled-is-named-at-both-its-lines",
                "AUDIT <scope> (<dimension>)\n\n## COR-1 — x\n\nEND AUDIT <scope>\n", [], [1, 5],
                said="does not parse as `AUDIT <scope>")
    # Prose that begins with the word opens nothing, as pricelog's task files
    # and record hold it: a dispatch's field, a triage paragraph, an indented
    # note under a report's key.
    answer_case("fp-prose-that-begins-with-the-word-is-not-an-audit-line",
                "AUDIT: none\nAUDIT: $REPO/devteam/audits/x-hygiene-2026-09-13.md\n"
                "**AUDIT triaged** (`devteam/audits/pricelog-correctness-2026-09-13.md`, six)\n"
                "  AUDIT triaged (pricelog-correctness-2026-09-13): Findings 1 and 4 fixed\n"
                "AUDIT triage, final: the security audit's F-2\n## COR-1 — x\n", [])

    # The closing line.
    text = answer(body="## SEC-1 — x\n").replace("END AUDIT T-7\n", "")
    answer_case("an-answer-with-no-closing-line-is-named-and-not-counted", text, [], [1],
                said="has no `END AUDIT T-7`")
    text = answer(body="## SEC-1 — x\n").replace("END AUDIT T-7\n", "") + answer("T-8")
    answer_case("an-answer-closed-by-none-before-the-next-opens-is-named", text,
                [("T-8", "security", "T-8", [])], [1], said="before line")
    text = "Some prose.\n\nEND AUDIT T-7\n"
    answer_case("a-closing-line-with-no-answer-open-is-named", text, [], [3],
                said="with no answer open")
    text = answer(body="## SEC-1 — x\n", end="T-8")
    answer_case("a-closing-line-naming-another-scope-is-named-and-the-answer-read", text,
                [("T-7", "security", "T-7", ["SEC-1"])], [line_of(text, "END AUDIT")],
                said="closes the answer `AUDIT T-7`")
    text = answer(body="## SEC-1 — x\n").replace("END AUDIT T-7", "END AUDIT")
    answer_case("a-closing-line-naming-no-scope-is-named-and-the-answer-read", text,
                [("T-7", "security", "T-7", ["SEC-1"])], [line_of(text, "END AUDIT")],
                said="does not parse as `END AUDIT <scope>`")

    # The findings: a heading with the dimension's label, `##` or `###`.
    text = answer(body="## SEC-1 — a\n\n### SEC-2 — b\n\n## SEC-10 — c\n")
    answer_case("fp-a-finding-is-a-level-two-or-three-heading", text,
                [("T-7", "security", "T-7", ["SEC-1", "SEC-2", "SEC-10"])])
    text = answer(body="## SEC-1 — a\n\n## COR-2 — b\n")
    answer_case("a-finding-with-another-dimensions-label-is-named-and-not-counted", text,
                [("T-7", "security", "T-7", ["SEC-1"])], [line_of(text, "COR-2")],
                said="is not this answer's label")
    text = answer(body="## SEC-1 — a\n\n## SEC-1 — b\n")
    answer_case("a-second-finding-of-one-number-is-named-and-the-first-stands", text,
                [("T-7", "security", "T-7", ["SEC-1"])], [line_of(text, "SEC-1 — b")],
                said="a second SEC-1 in one answer")
    # The gate audits' shapes (F-99), and a label written loosely.
    for name, heading in (("the-gate-audits-finding-n-is-named",
                           "## Finding 1 (defect, load-bearing) — a crash state"),
                          ("the-gate-audits-numbered-heading-is-named", "### 1. D-6's justification"),
                          ("the-gate-audits-f-n-is-named", "## F-1 — HIGH — the log path"),
                          ("a-label-with-a-colon-is-named", "## SEC-2: x"),
                          ("a-label-with-no-hyphen-is-named", "## SEC 2 — x"),
                          ("a-label-lowercase-is-named", "## sec-2 — x"),
                          ("a-label-emphasised-is-named", "## **SEC-2** — x"),
                          ("a-label-with-no-title-is-named", "## SEC-2")):
        text = answer(body=f"## SEC-1 — a\n\n{heading}\n")
        answer_case(name, text, [("T-7", "security", "T-7", ["SEC-1"])], [line_of(text, heading)],
                    said="looks like a finding")
    # The answer's own text: sections, a level-one title, evidence in a fence.
    text = answer(body="# T-7 Security Audit — at HEAD\n\n## Verdict\n\n## SEC-1 — a\n\n"
                       "## Observation, not a finding — b\n\n```\n## Finding 9 — quoted\n"
                       "# 1. a comment\n```\n\n## Checked and found clean\n\n"
                       "## Everything else tried — survived (R-4 held)\n")
    answer_case("fp-an-answers-own-headings-and-its-fenced-evidence-are-its-text", text,
                [("T-7", "security", "T-7", ["SEC-1"])])
    # Outside an answer, a task file's own headings are not an audit's.
    answer_case("fp-a-task-files-own-headings-are-not-an-audits",
                "## Steps\n\n## S-4 — the adversarial pass\n\n### S-2\n\n## Finding 1 — the "
                "supervisor's\n\n### 1. a list\n\n## COR-1 — a label in prose\n", [])

    # `Needs.`: read whole, never required to count a finding.
    got, _ = mod.answers(answer(body="## SEC-1 — a\n\n- **Needs.**\n  - `src/a.py`\n  - `tests/`\n\n"
                                     "## SEC-2 — b\n\n## Notes\n\n- **Needs.** `src/b.py`\n")
                         .split("\n"))
    needs = [f.needs[1] if f.needs else None for f in got[0].findings] if got else None
    check("fp-a-findings-needs-is-read-and-one-with-none-still-counts",
          needs == ["- `src/a.py` - `tests/`", None], repr(needs))

    # A filed audit that opens no answer (L-3.4): its findings are counted,
    # tied to no task, and the missing line is named. pricelog's T-18
    # declarations file is the shape: ten `### COR-n` headings, no AUDIT line.
    text = "# Declarations — T-18's S-4\n\n### COR-1 — a\n\n- **Disposition.** raised Q-28\n\n### COR-2 — b\n"
    answer_case("a-filed-audit-with-no-audit-line-counts-its-findings-and-is-named", text,
                [(None, None, None, ["COR-1", "COR-2"])], [1], filed=True, said="tied to no task")
    text = ("# Audit — pricelog — correctness — 2026-09-13\n\n## Finding 1 (defect) — a\n\n"
            "## Finding 2 (gap) — b\n\n## Checked and found clean\n")
    answer_case("a-filed-audit-in-the-gate-audits-shape-names-each-heading", text,
                [(None, None, None, [])], [1, line_of(text, "Finding 1"), line_of(text, "Finding 2")],
                filed=True)
    # ...and the same text in a task file is not an audit's.
    answer_case("fp-a-task-file-that-opens-no-answer-is-not-a-filed-audit", text, [])
    text = answer(body="## SEC-1 — a\n")
    answer_case("fp-a-filed-audit-that-opens-its-answer-is-read-as-any-answer", text,
                [("T-7", "security", "T-7", ["SEC-1"])], filed=True)

    # The files: where an answer is, and what ties it to a task. The scope
    # is its AUDIT line's, whatever the file is called; the directory's
    # README, which setup scaffolds, is not an audit.
    root = project(ledger="")
    try:
        devteam = os.path.join(root, "devteam")
        os.makedirs(os.path.join(devteam, "audits"))
        os.makedirs(os.path.join(devteam, "tasks"))
        files = {
            "audits/T-7-security-2026-09-30.md": answer("T-9", "security", "## SEC-1 — a\n"),
            "audits/pricelog-correctness-2026-09-13.md": "# Audit\n\n## COR-1 — a\n",
            "audits/README.md": "# Audits\n\nOne file per audit, named "
                                "`<scope>-<dimension>-<date>.md`.\n\n## COR-9 — an example\n",
            "tasks/T-3.md": "# T-3 — x — RUNNING\n\n## Execution record\n\n"
                            + answer("T-3.S-1", "hygiene", "## HYG-1 — a\n"),
            "tasks/README.md": answer("T-4", "hygiene", "## HYG-1 — a\n"),
        }
        for rel, body in files.items():
            with open(os.path.join(devteam, rel), "w", encoding="utf-8") as fh:
                fh.write(body)
        subprocess.run(["git", "-C", root, "init", "-q"], check=True)
        found, unread = mod.answers_in(devteam)
        got = sorted((rel, a.scope, a.task, [f.ident for f in a.findings]) for rel, a in found)
        check("a-filed-audit-is-tied-to-its-audit-lines-scope-whatever-it-is-called",
              ("audits/T-7-security-2026-09-30.md", "T-9", "T-9", ["SEC-1"]) in got, repr(got))
        check("a-file-in-audits-with-no-audit-line-is-named-by-its-file",
              ("audits/pricelog-correctness-2026-09-13.md", None, None, ["COR-1"]) in got
              and [(r, n) for r, n, _ in unread] == [("audits/pricelog-correctness-2026-09-13.md", 1)],
              f"{got!r}; {unread!r}")
        check("fp-a-task-files-answer-is-found-by-its-lines",
              ("tasks/T-3.md", "T-3.S-1", "T-3", ["HYG-1"]) in got, repr(got))
        check("fp-the-readmes-are-not-audits-or-tasks",
              not any(rel.endswith("README.md") for rel, *_ in got)
              and not any(r.endswith("README.md") for r, *_ in unread), f"{got!r}; {unread!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = passed + failed
    print(f"\nledger control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
