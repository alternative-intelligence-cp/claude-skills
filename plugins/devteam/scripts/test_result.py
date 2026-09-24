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
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import result  # noqa: E402


def build(findings=(), gaps=(), excluded=(), blocking_only=False, counts=((3, "tasks"),)):
    r = result.Result("check_x", "devteam", width=16)
    for kind, where, detail, advisory in findings:
        r.finding(kind, where, detail, advisory)
    for part, reason, advisory in gaps:
        r.gap(part, reason, advisory)
    for part, declaration in excluded:
        r.exclude(part, declaration)
    for n, label in counts:
        r.count(n, label)
    r.blocking_only = blocking_only
    return r


def agree(r):
    """The line and the JSON must say the same thing: one object, two renderings."""
    d = r.as_dict()
    text = "\n".join(r.lines())
    line_classes = sorted(l.split()[0] for l in r.lines()[1:]
                          if l.startswith("  ") and not l.startswith(("  not evaluated: ", "  excluded: ")))
    return (d["exit"] == r.exit_code
            and d["result"] == result.WORD[r.exit_code]
            and sorted(f["class"] for f in d["findings"]) == line_classes
            and all(f"not evaluated: {g['part']} — " in text for g in d["not_evaluated"])
            and all(f"excluded: {e['part']} — by " in text for e in d["excluded"]))


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
    ("fp-blocking-only-passes-an-advisory-finding-alone",
     build(findings=[ADV], blocking_only=True), 0, ["1 finding(s)"]),
    ("fp-blocking-only-passes-an-advisory-gap-alone",
     build(gaps=[ADV_GAP], blocking_only=True), 0, ["not evaluated (1 part(s))"]),
]


def main():
    passed = failed = 0

    def check(name, ok, detail=""):
        nonlocal passed, failed
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

    fp = sum(1 for c in CASES if c[0].startswith("fp-")) + 1
    total = passed + failed
    print(f"\nresult control: {passed} passed, {failed} failed, {total} cases "
          f"({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
