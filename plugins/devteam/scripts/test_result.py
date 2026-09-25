#!/usr/bin/env python3
"""Negative control for result.py, the four-result contract (P-35).

Every check ends in result.py's contract (roadmap 0.3.1, L-1.1 and L-1.2), so a
defect here is a defect in all five at once -- and the defect it exists to stop
is the quietest one: a check reporting CLEAN when it did not look. Each case
states the exit code, the words on the line and the JSON the gate reads, and
the `fp-` cases are the ones that must stay clean: a contract that reported
every exclusion as a gap would make onboarding's gate unpassable, and a gate
nobody can pass gets switched off.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import result  # noqa: E402


def build(findings=(), gaps=(), excluded=(), blocking_only=False, counts=((3, "tasks"),),
          notes=()):
    r = result.Result("check_x", "devteam", width=16)
    for kind, where, detail, advisory in findings:
        r.finding(kind, where, detail, advisory)
    for part, reason, advisory in gaps:
        r.gap(part, reason, advisory)
    for part, declaration in excluded:
        r.exclude(part, declaration)
    for label, text in notes:
        r.note(label, text)
    for n, label in counts:
        r.count(n, label)
    r.blocking_only = blocking_only
    return r


def agree(r):
    """The line and the JSON must say the same thing: one object, two renderings."""
    d = r.as_dict()
    text = "\n".join(r.lines())
    noted = tuple(f"  {n['label']}: " for n in d["notes"])
    line_classes = sorted(l.split()[0] for l in r.lines()[1:]
                          if l.startswith("  ") and not l.startswith(
                              ("  not evaluated: ", "  excluded: ", "  accepted by ") + noted))
    accepted = sorted((m.group(1), m.group(2)) for m in (
        re.match(r"^  accepted by (D-\d+): (?!not evaluated: )(\S+)", l) for l in r.lines()) if m)
    return (d["exit"] == r.exit_code
            and d["result"] == result.WORD[r.exit_code]
            and sorted(f["class"] for f in d["findings"]) == line_classes
            and sorted((f["by"], f["class"]) for f in d["accepted"]) == accepted
            and all(f"not evaluated: {g['part']} — " in text for g in d["not_evaluated"])
            and all(f"accepted by {g['by']}: not evaluated: {g['part']} — " in text
                    for g in d["accepted_not_evaluated"])
            and all(f"excluded: {e['part']} — by " in text for e in d["excluded"])
            and all(f"  {n['label']}: {n['text']}" in r.lines() for n in d["notes"]))


F = ("missing-field", "tasks/T-1.md:1", "T-1 has no **Discharges.**", False)
ADV = ("budget-mismatch", "tasks/T-1.md", "tokens=1 against 309639", True)
GAP = ("board-drift", "0 of 19 board rows parsed", False)
ADV_GAP = ("budget-mismatch", "the sandbox's meta/budget.json is gone", True)

CASES = [
    # (name, result, exit, words the head line must contain)
    ("one-gap-and-no-finding-is-not-evaluated",
     build(gaps=[GAP]), 3, ["not evaluated (1 part(s))", "[3 tasks]"]),
    ("a-finding-beside-a-gap-exits-1-and-names-both",
     build(findings=[F], gaps=[GAP]), 1, ["1 finding(s), 1 part(s) not evaluated"]),
    ("a-finding-alone-exits-1",
     build(findings=[F]), 1, ["1 finding(s)"]),
    ("blocking-only-still-stops-on-a-blocking-gap",
     build(findings=[ADV], gaps=[GAP], blocking_only=True), 3, ["1 finding(s), 1 part(s) not evaluated"]),
    ("without-blocking-only-an-advisory-finding-exits-1",
     build(findings=[ADV]), 1, ["1 finding(s)"]),
    ("without-blocking-only-an-advisory-gap-exits-3",
     build(gaps=[ADV_GAP]), 3, ["not evaluated (1 part(s))"]),
    # fp: the exits that must stay 0.
    ("fp-nothing-found-and-nothing-skipped-is-clean",
     build(), 0, ["devteam: clean  [3 tasks]"]),
    ("fp-an-exclusion-names-itself-and-stays-clean",
     build(excluded=[("uncovered-requirement", "--pre-plan (2 held back)")]), 0, ["devteam: clean"]),
    # A note is a fact about what was read (roadmap 0.3.2, L-2.8): on the line
    # and in the JSON alike, and never a finding or a gap.
    ("fp-a-note-is-said-on-the-line-and-stays-clean",
     build(notes=[("reconstructed", "T-1.S-2 — by the supervisor; the worker died")]), 0,
     ["devteam: clean"]),
    ("fp-blocking-only-passes-an-advisory-finding-alone",
     build(findings=[ADV], blocking_only=True), 0, ["1 finding(s)"]),
    ("fp-blocking-only-passes-an-advisory-gap-alone",
     build(gaps=[ADV_GAP], blocking_only=True), 0, ["not evaluated (1 part(s))"]),
]


# --- what a decision accepts (roadmap 0.3.1, L-1.6) -------------------------

def decisions(*items, reviewed="unreviewed", supersedes="none", field="- **Accepts.**",
              before=(), after=()):
    """DECISIONS.md's lines: one decision, D-3, accepting `items`."""
    head = ["# Decisions", "", *before, "### D-3 — T-1's missing field stays", "",
            "- **Decision.** it stays.", f"- **Supersedes.** {supersedes}"]
    if reviewed is not None:
        head.append(f"- **Reviewed.** {reviewed}")
    return head + [field, *(f"  - {i}" for i in items), "- **Date.** 2026-09-24", "", *after]


A_F = "`check_trace` `missing-field` `tasks/T-1.md` — T-1 has no **Discharges.**"
A_P = "`check_trace` not evaluated: BOARD.md's task rows"


def trace(findings=(), gaps=(), excluded=(), note=""):
    r = result.Result("check_trace", "devteam", width=16)
    for kind, where, detail in findings:
        r.finding(kind, where, detail)
    for part, reason in gaps:
        r.gap(part, reason)
    for part, declaration in excluded:
        r.exclude(part, declaration)
    r.count(3, "tasks")
    r.clean_note = note
    return r


def main():
    passed = failed = fp = 0

    def check(name, ok, detail=""):
        nonlocal passed, failed, fp
        fp += name.startswith("fp-")
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}")
            if detail:
                for line in str(detail).split("\n"):
                    print(f"        | {line}")

    for name, r, want, words in CASES:
        head = r.lines()[0]
        check(name, r.exit_code == want and all(w in head for w in words) and agree(r),
              f"exit {r.exit_code}, wanted {want}\n" + "\n".join(r.lines()))

    # Every part not evaluated, and every exclusion, is NAMED -- a gap the line
    # does not name is the silence this module exists to end.
    r = build(findings=[F], gaps=[GAP, ADV_GAP], excluded=[("x", "a flag")])
    text = "\n".join(r.lines())
    check("every-gap-and-exclusion-is-named-on-its-own-line",
          "not evaluated: board-drift — 0 of 19 board rows parsed" in text
          and "not evaluated: budget-mismatch — the sandbox's meta/budget.json is gone  (advisory)" in text
          and "excluded: x — by a flag" in text, text)
    # ...and every note, in both renderings, since only the JSON reaches a
    # program and only the line reaches a person.
    r = build(notes=[("reconstructed", "T-1.S-2 — by the supervisor")])
    check("a-note-is-on-the-line-and-in-the-json",
          "  reconstructed: T-1.S-2 — by the supervisor" in r.lines()
          and r.as_dict()["notes"] == [{"label": "reconstructed",
                                        "text": "T-1.S-2 — by the supervisor"}],
          "\n".join(r.lines()) + "\n" + json.dumps(r.as_dict().get("notes")))

    # The anchor is split for the gate's identity: file and line apart.
    r = build(findings=[F, ADV, ("leak", "", "an absolute path", False)])
    got = [(f["file"], f["line"]) for f in r.findings]
    check("anchors-split-into-file-and-line",
          got == [("tasks/T-1.md", 1), ("tasks/T-1.md", None), ("", None)], got)

    # Several targets report the worst, by 2 > 1 > 3 > 0.
    for codes, want in (([0, 3], 3), ([3, 1], 1), ([1, 2], 2), ([3, 0, 1], 1), ([], 0), ([0, 0], 0)):
        check(f"precedence-{codes}-is-{want}", result.worst(codes) == want,
              f"worst({codes}) = {result.worst(codes)}")

    # emit() prints the JSON the gate reads, with the worst exit.
    out = io.StringIO()
    code = result.emit([build(gaps=[GAP]), build(findings=[F])], True, stream=out)
    try:
        doc = json.loads(out.getvalue())
        ok = (code == 1 and doc["exit"] == 1 and doc["schema"] == result.SCHEMA
              and [x["exit"] for x in doc["results"]] == [3, 1])
    except (ValueError, KeyError, TypeError):
        ok = False
    check("emit-json-carries-every-result-and-the-worst-exit", ok, out.getvalue())

    out = io.StringIO()
    code = result.emit([build()], False, stream=out)
    check("fp-emit-lines-for-a-clean-run", code == 0 and out.getvalue() == "devteam: clean  [3 tasks]\n",
          out.getvalue())

    # --- L-1.3's shared helpers: what continues a field, and how a row is named
    # Each check applies these, so a defect here is a wrapped field or an
    # unparsed row that every check misses at once.
    doc = ["- **Discharges.** R-1, and R-2 once",          # 0
           "  T-2's README exists",                         # 1  indented
           "lazily continued",                              # 2  lazy, no blank
           "",                                              # 3
           "  a second paragraph of the item",              # 4  indented after blank
           "",                                              # 5
           "Prose after the list."]                         # 6  unindented after blank
    got = result.continuation(doc, 0)
    check("continuation-takes-indented-lazy-and-indented-after-a-blank",
          got == [1, 2, 4], got)
    for name, following in (("a-new-list-item", "- **Next.** x"), ("a-heading", "## Steps"),
                            ("a-table-row", "| a | b |"), ("a-numbered-item", "1. first")):
        got = result.continuation(["- **Gate.** it works.", following], 0)
        check(f"fp-continuation-stops-at-{name}", got == [], got)
    got = result.continuation(["- **Status.** open", "", "Prose."], 0)
    check("fp-continuation-stops-at-unindented-prose-after-a-blank", got == [], got)

    # --- roadmap 0.3.2, L-2.3: a field read whole -------------------------
    # The first line's value, then every continuation line, each stripped and
    # joined by one space -- so a value reads the same wrapped or not.
    got = result.joined(doc, 0, "R-1, and R-2 once")
    check("joined-reads-the-value-across-every-continuation-line",
          got == "R-1, and R-2 once T-2's README exists lazily continued "
                 "a second paragraph of the item", got)
    got = result.joined(["- **Status.** in-progress (T-1,", "    T-2)"], 0, "in-progress (T-1,")
    check("joined-a-rewrapped-value-reads-as-the-one-line-value",
          got == "in-progress (T-1, T-2)", got)
    # A value that starts on the line after its field is still its value.
    got = result.joined(["- **Depends on.**", "  T-2"], 0, "")
    check("joined-a-value-that-starts-on-the-next-line", got == "T-2", got)
    # `until` ends the value at the first line that is an entry of its own: a
    # path list's first item, under a value written beside the field.
    got = result.joined(["- **Scope.** `src/`,", "  `lib/`", "  - `tests/`", "  more"], 0,
                        "`src/`,", until=re.compile(r"^\s+[-*+]\s+\S"))
    check("joined-stops-at-the-until-line", got == "`src/`, `lib/`", got)
    got = result.joined(["- **Status.** open", "- **Next.** x"], 0, "open")
    check("fp-joined-a-one-line-value-is-that-line", got == "open", got)

    got = result.anchors([("BOARD.md", n) for n in (64, 65, 66, 70)] + [("a.md", 3)])
    check("anchors-compress-only-a-run-every-line-of-which-is-a-row",
          got == "BOARD.md:64-66, 70; a.md:3", got)
    got = result.unparsed([("BOARD.md", 64), ("BOARD.md", 65)], 20, "rows", "`| T-n |`",
                          "board-drift compared nothing for them")
    check("unparsed-names-the-count-the-grammar-and-every-row",
          got == "2 of 20 rows do not parse as `| T-n |`, so board-drift compared "
                 "nothing for them (BOARD.md:64-65)", got)

    # --- L-1.6: the grammar of an acceptance ------------------------------
    # Every shape a rushed hand writes slightly wrong must accept NOTHING and
    # be named at its line: an acceptance the parser half-reads is a finding
    # suppressed by accident, which is the failure the grammar exists to stop.
    got = result.parse_acceptances(decisions(A_F, A_P))
    check("accept-reads-a-finding-and-a-part",
          [(a.decision, a.check, a.cls, a.file, a.message, a.part) for a in got.items]
          == [("D-3", "check_trace", "missing-field", "tasks/T-1.md",
               "T-1 has no **Discharges.**", None),
              ("D-3", "check_trace", None, None, None, "BOARD.md's task rows")]
          and not got.unread and got.quoted == {9, 10}, (got.items, got.unread, got.quoted))
    for name, lines, at in (
            ("the-field-written-with-a-colon", decisions(A_F, field="- **Accepts:**"), 8),
            ("the-field-carrying-an-item-inline", decisions(field="- **Accepts.** " + A_F), 8),
            ("the-field-as-a-paragraph", decisions(A_F, field="**Accepts.**"), 8),
            ("a-field-in-no-decision", ["# Decisions", "", "- **Accepts.**", f"  - {A_F}"], 3),
            ("a-decision-with-no-reviewed-line", decisions(A_F, reviewed=None), 7),
            ("a-reviewed-line-outside-the-vocabulary", decisions(A_F, reviewed="the team"), 8),
            ("a-field-with-no-item", decisions(), 8),
            ("an-item-without-its-backticks",
             decisions("check_trace missing-field tasks/T-1.md — T-1 has no **Discharges.**"), 9),
            ("an-item-without-its-dash",
             decisions("`check_trace` `missing-field` `tasks/T-1.md` T-1 has no **Discharges.**"), 9),
            ("an-item-wrapped-past-its-line", decisions(A_F.replace(" **Discharges.**", ""))[:9]
             + ["    **Discharges.**"] + decisions()[9:], 9),
            ("an-item-naming-no-project-check", decisions(A_F.replace("check_trace", "check_plugin")), 9),
            ("a-part-of-check_report", decisions("`check_report` not evaluated: the REPORT block"), 9)):
        got = result.parse_acceptances(lines)
        check(f"accept-refuses-{name}",
              not got.items and [w for w, _ in got.unread][:1] == [f"DECISIONS.md:{at}"]
              and all(d.endswith("so it accepts nothing") for _, d in got.unread),
              (lines, got.items, got.unread))
    # A line under the field that is no item is named at ITS line; the item
    # after it names exactly what it accepts, so reading it over-accepts
    # nothing.
    got = result.parse_acceptances(decisions(A_F)[:8] + ["  both are permanent"] + decisions(A_F)[8:])
    check("accept-names-a-line-under-the-field-that-is-no-item",
          len(got.items) == 1 and [w for w, _ in got.unread] == ["DECISIONS.md:9"], got.unread)
    # What must be READ, and what must be withdrawn without a word.
    for name, lines, want in (
            ("fp-accept-reads-a-client-reviewed-decision", decisions(A_F, reviewed="client"), 1),
            ("fp-accept-reads-a-proceeded-unreviewed-decision",
             decisions(A_F, reviewed="proceeded-unreviewed (Q-4)"), 1),
            ("fp-accept-reads-an-item-with-its-message-line-number",
             decisions("`check_refs` `duplicate-id` `tasks/T-4.md` — S-3 already declared at "
                       "tasks/T-4.md:12"), 1),
            ("fp-accept-withdraws-a-superseded-decision-silently",
             decisions(A_F, after=["### D-4 — it is fixed", "", "- **Supersedes.** D-3"]), 0),
            ("fp-accept-withdraws-a-superseded-malformed-field-silently",
             decisions("not an acceptance", after=["### D-4 — x", "", "- **Supersedes.** D-3"]), 0),
            ("fp-accept-ignores-a-fenced-example",
             ["# Decisions", "", "```", "- **Accepts.**", f"  - {A_F}", "```"], 0),
            ("fp-accept-ignores-a-document-with-no-field", decisions()[:7], 0)):
        got = result.parse_acceptances(lines)
        check(name, len(got.items) == want and not got.unread, (got.items, got.unread))

    # --- L-1.6: a finding's identity, which the gate matches by too --------
    same = lambda a, b: result.stable(a) == result.stable(b)
    check("identity-drops-a-line-number-inside-the-message",
          same("S-3 already declared at tasks/T-4.md:12", "S-3 already declared at tasks/T-4.md:40")
          and same("BOARD.md:64-82 rows", "BOARD.md:70-88 rows"))
    check("identity-drops-an-also-list", same("S-4 is cited (also 14, 22)", "S-4 is cited"))
    check("fp-identity-keeps-numbers-that-are-not-lines",
          result.stable("19 of 20 rows; T-10 and R-4 at 12:18:16") == "19 of 20 rows; T-10 and R-4 at 12:18:16",
          result.stable("19 of 20 rows; T-10 and R-4 at 12:18:16"))
    check("fp-identity-keeps-a-different-message-different",
          not same("T-1 has no **Discharges.**", "T-2 has no **Discharges.**"))

    # --- L-1.6: what the Result does with them -----------------------------
    FT = ("missing-field", "tasks/T-1.md:9", "T-1 has no **Discharges.**")
    GT = ("BOARD.md's task rows", "19 of 20 table rows do not parse (BOARD.md:64-82)")
    got = result.parse_acceptances(decisions(A_F, A_P))
    r = trace(findings=[FT], gaps=[GT], note="traced end to end")
    stale = r.accept(got)
    head = r.lines()[0]
    check("accepted-finding-and-part-exit-0-and-the-line-names-the-decision",
          r.exit_code == 0 and not stale and head.startswith("devteam: clean, 2 accepted by D-3")
          and "  accepted by D-3: missing-field tasks/T-1.md:9  T-1 has no **Discharges.**" in r.lines()
          and [f["by"] for f in r.as_dict()["accepted"]] == ["D-3"] and agree(r), "\n".join(r.lines()))
    check("an-accepted-part-never-lets-the-line-claim-the-whole-was-read",
          "traced end to end" not in head, head)
    r = trace(findings=[FT, ("missing-field", "tasks/T-2.md:1", "T-2 has no **Verify.**")])
    r.accept(got)
    check("a-finding-no-acceptance-names-still-exits-1",
          r.exit_code == 1 and r.lines()[0].startswith("devteam: 1 finding(s), 1 accepted by D-3")
          and agree(r), "\n".join(r.lines()))
    r = trace(findings=[("missing-field", "tasks/T-1.md:1", "T-1 has no **Verify.**")])
    stale = r.accept(got)
    check("an-acceptance-matching-nothing-is-returned-stale-with-its-line",
          [w for w, _ in stale] == ["DECISIONS.md:9", "DECISIONS.md:10"] and r.exit_code == 1
          and "fixed since" in stale[0][1] and "evaluated since" in stale[1][1], stale)
    r = trace(findings=[FT], gaps=[GT])
    stale = r.accept(got, covers=lambda a: False)
    check("fp-an-acceptance-this-run-does-not-cover-is-neither-applied-nor-stale",
          not stale and not r.accepted and not r.accepted_gaps and r.exit_code == 1, stale)
    r = trace(excluded=[("missing-field", "--a-flag")])
    stale = r.accept(result.parse_acceptances(decisions(A_F)))
    check("fp-an-excluded-class-is-not-judged", not stale and r.exit_code == 0, stale)
    r = trace(findings=[FT])
    stale = r.accept(result.parse_acceptances(decisions(A_F.replace("check_trace", "check_refs"))))
    check("fp-an-acceptance-of-another-check-is-not-applied-here",
          not stale and r.exit_code == 1 and not r.accepted, stale)
    r = trace(findings=[FT])
    stale = r.accept(result.parse_acceptances(decisions(A_F, A_F)))
    check("fp-two-lines-naming-one-finding-are-both-matched",
          not stale and r.exit_code == 0 and len(r.accepted) == 1, stale)
    bad = result.Accepted()
    bad.unreadable = "DECISIONS.md is not UTF-8"
    r = trace(findings=[FT])
    r.accept(bad)
    check("an-unreadable-decisions-file-is-a-part-not-evaluated",
          r.exit_code == 1 and r.gaps == [("DECISIONS.md's acceptances", "DECISIONS.md is not UTF-8", False)],
          r.gaps)

    # A CHECKOUT OF ONE COMMIT (roadmap 0.3.1, L-1.5). `exclude_classes` takes
    # a working-state class out of the findings and the parts, names it, and
    # leaves the exit to the rest; and an acceptance of it is then not judged,
    # because nothing that could have found it was evaluated. The gate's own
    # fixture cannot show the removal: a clean checkout never has anything of
    # these classes to remove.
    ws = ("untracked-file", "tasks/T-9.md", "is not tracked")
    r = trace(findings=[FT, ws], gaps=[("untracked-file", "a working-state part"), GT])
    r.exclude_classes(("untracked-file",), result.AT_COMMIT)
    check("exclude-classes-removes-the-class-and-names-it",
          [f["class"] for f in r.findings] == ["missing-field"] and [g[0] for g in r.gaps] == [GT[0]]
          and r.excluded == [("untracked-file", result.AT_COMMIT)]
          and "  excluded: untracked-file — by --at-commit" in "\n".join(r.lines())
          and r.exit_code == 1 and agree(r), "\n".join(r.lines()))
    r = trace(findings=[ws])
    r.exclude_classes(("untracked-file",), result.AT_COMMIT)
    check("fp-excluding-the-only-finding-leaves-clean",
          r.exit_code == 0 and agree(r), "\n".join(r.lines()))
    r = trace()
    r.exclude_classes(("untracked-file",), result.AT_COMMIT)
    stale = r.accept(result.parse_acceptances(decisions(
        "`check_trace` `untracked-file` `tasks/T-9.md` — is not tracked")))
    check("fp-an-acceptance-of-an-excluded-working-state-class-is-not-stale",
          not stale and r.exit_code == 0, stale)

    # As git would show it (L-1.4): untracked is read, ignored is not.
    root = tempfile.mkdtemp(prefix="devteam-result-")
    try:
        dt = os.path.join(root, "devteam")
        os.makedirs(dt)
        subprocess.run(["git", "init", "-q", root], check=True)
        with open(os.path.join(dt, "DECISIONS.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(decisions(A_F)))
        got = result.acceptances(dt)
        check("acceptances-reads-an-untracked-decisions-file", len(got.items) == 1, got.items)
        with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("devteam/DECISIONS.md\n")
        got = result.acceptances(dt)
        check("fp-acceptances-ignores-an-ignored-decisions-file", not got.items, got.items)
        os.remove(os.path.join(root, ".gitignore"))
        with open(os.path.join(dt, "DECISIONS.md"), "wb") as fh:
            fh.write(b"# Decisions\n\xff\n")
        got = result.acceptances(dt)
        check("acceptances-names-a-decisions-file-it-cannot-decode",
              got.unreadable and "not UTF-8" in got.unreadable, got.unreadable)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = passed + failed
    print(f"\nresult control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
