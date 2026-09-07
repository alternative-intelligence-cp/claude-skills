#!/usr/bin/env python3
"""Which control cases does each mutation flip? (P-35, P-35b)

THE HOUSE RULES ALREADY REQUIRE a false-positive twin beside every finding
class and a mutation test of every new mechanism. Neither requires THE TWIN
ITSELF TO BE SHOWN TO FAIL -- and a twin built from the mechanism's intended
shape usually cannot be made to fail, because the intended shape is what the
correct and the broken version both produce. So the discipline mutation-tests
the check and takes the twin on trust, and the twin is the half that silently
controls nothing.

Five instances were measured across three subcycles of cycle 0.2 before anyone
wrote this down, and every one of them PASSED:

  0.2.4  a control asserting a branch that could never fire -- an absent tool
         was reported as a row, not as a gap
  0.2.5  rotation cases that built the mid-rotation precondition the live run
         destroys
  0.2.5  a twin made vacuous because lock_state returned `mine` before the
         parser under test ever ran
  0.2.6  the amendment ordering twin -- BOTH entries complete, so position and
         version selected indistinguishable things
  0.2.6  the section-gate twin -- the fixture charter contains no `###` line,
         so "gated on the section" and "scan the whole file" produced
         identical output

None was visible by asking whether the suite was green. Four of the five were
found only by mutating the mechanism and asking WHAT ELSE WOULD MAKE THIS PASS.

So this script asks that question mechanically. It applies each declared
mutation to a COPY of the source, runs the control against it, and records
which cases changed verdict. What it prints is the thing no instrument in this
repository recorded before: PER CASE, THE MUTATIONS THAT MOVE IT.

AND IT REFUSES TO GUESS WHICH UNMOVED CASES ARE DECORATION. A case no mutation
moved is decoration only if the mutation set for its mechanism is COMPLETE;
otherwise it is merely unasked, and the two are not distinguishable from the
output. An earlier draft inferred the difference from case and mutation names
and got it wrong on its first run -- it called the `unknown-rule` case
decoration because the string "unknown" appears in four mutation names, when in
truth no declared mutation deletes that emit at all. An instrument answering
"which cases did MY mutations move" while appearing to answer "which cases
control anything" is P-35b, inside the script written to catch that shape.

So completeness is DECLARED, in COMPLETE_FOR below, and diffed against what was
measured -- two lists (P-4), never a reading. A case matching a declared prefix
and moved by nothing is a defect and exits 1. Every other unmoved case is
printed as UNASKED, which is a statement about this file rather than about the
case.

    $ python3 scripts/mutate.py                 every declared mutation
    $ python3 scripts/mutate.py --check unknown-rule    one set
    $ python3 scripts/mutate.py --list          what is declared, without running

WHY THE MUTATIONS ARE WRITTEN HERE AND NOT DERIVED. A generated mutation --
flip a comparison, drop a branch -- would mostly produce sources that fail
every case at once, which says nothing about any individual case. Each mutation
below is a WRONG-BUT-PLAUSIBLE version of the mechanism: the draft that was
actually written first, or the simplification a later reader would reach for.
That is the population a twin has to discriminate against.

IT NEVER WRITES THE SHIPPED TREE, and the first draft of it did.

The obvious design is to apply each mutation to the real file and restore it in
a `finally`, because the controls resolve their subject to a fixed path and a
scratch copy would test the copy. TWO SESSIONS REACHED THAT DESIGN
INDEPENDENTLY -- 0.2.6's and this one -- which is DESIGN §20's second-half
detector firing, and both were wrong in the same way.

A `finally` guarantees restoration IN TIME. It guarantees nothing about the
tree A CONCURRENT READER OBSERVES. A peer session ran `git add -A` inside the
window, and check_plugin.py shipped at 6f2f389 with mutation 4 applied --
while this control ran green in the working tree, because by then the `finally`
had already restored it. Two trees, one report, and nothing in either session's
procedure distinguished them. Repaired at c4d3f26; the row is in docs/PAIRS.md.

The hazard is not really the peer. The window exists whether or not anybody
else is present -- a hook, a scheduled task, a crash-recovery path or an
interrupted run has the same exposure, and an interrupted run leaves the
mutation applied permanently, which looks exactly like a suite that passes
(0.2.3's lesson).

So the window is REMOVED rather than declared. Each control resolves its
subject through `DEVTEAM_SUBJECT_<NAME>` before falling back to its shipped
path; this script writes the mutated source to a temporary file and names it
there. The shipped tree is never wrong, so there is no window to protect, no
marker to remember to write, and nothing for an interrupted run to leave
behind. Preventing the mistake structurally beats asking the next session to
remember not to commit during it.

IT ASKS THE QUESTION IN BOTH DIRECTIONS, because they are different defects.
A case no mutation moves is a control that guards nothing. A MUTATION NO CASE
CATCHES is a mechanism nothing guards -- the suite is green against a source
that is broken, which is the plain reading of P-35 and is how four mutations
survived their first drafts across 0.2.5 and 0.2.6. Both are reported; both
exit 1.

Exit 0 when every declared mutation is caught by some case and every case
claimed in COMPLETE_FOR is moved by some mutation; 1 if either direction has a
gap; 2 if a mutation could not be applied or the suite was not green first.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))


# (control script, mutation name, target file, old text, new text)
#
# Every entry names the DRAFT THAT WAS ACTUALLY WRITTEN FIRST where one
# existed, because a mutation nobody would ever write discriminates nothing.
MUTATIONS = [
    # --- unknown-rule's three exemptions (0.2.7) -------------------------
    # The check read every P-n in a raw body as a citation, so a document
    # reporting a rule number could not be committed. These three mutations
    # are each "the exemption was never added", which is the shipped state
    # this subcycle found.
    ("test_check_plugin.py", "unknown-rule: the fence skip is removed",
     "check_plugin.py",
     '        if line.lstrip().startswith("```"):\n'
     '            in_fence = not in_fence\n'
     '            continue\n',
     '        if False:\n'
     '            in_fence = not in_fence\n'
     '            continue\n'),
    ("test_check_plugin.py", "unknown-rule: quoted check output is read as a citation",
     "check_plugin.py",
     '        out.update(int(x) for x in RULE.findall(CHECK_OUTPUT.sub("`quoted`", line)))',
     '        out.update(int(x) for x in RULE.findall(line))'),
    ("test_check_plugin.py", "unknown-rule: the teaching form is read as a citation",
     "check_plugin.py",
     "        if in_fence or TEACHING.search(line):",
     "        if in_fence:"),
    # THE EXEMPTION EATING THE CHECK. A fence skip written per FILE rather
    # than per LINE is the simplification a later reader reaches for -- it is
    # shorter, and it passes all three twins above. Only a case with a quoted
    # number AND a real citation in one file can tell them apart.
    ("test_check_plugin.py", "unknown-rule: a file containing any fence is skipped whole",
     "check_plugin.py",
     "    out, in_fence = set(), False\n"
     "    for line in body.split(\"\\n\"):",
     "    out, in_fence = set(), False\n"
     "    if \"```\" in body:\n"
     "        return out\n"
     "    for line in body.split(\"\\n\"):"),
]


# Case-name prefixes whose mutation set above is claimed COMPLETE -- every
# plausible wrong version of that mechanism is declared. A case matching one of
# these that no mutation moves is a control that controls nothing.
#
# Keep this list SHORT and true. Adding a prefix here is a claim, and the claim
# is checked: it is what turns "no mutation moved this" from an observation into
# a verdict. The four below are 0.2.7's; the mechanism is `cited_rules` in
# check_plugin.py and the four mutations are its three missing exemptions plus
# the file-scoped simplification a later reader would reach for.
COMPLETE_FOR = (
    "fp-a-rule-number-inside-a-fenced-block",
    "fp-a-rule-number-in-quoted-check-output",
    "fp-the-teaching-form-of-a-rule-number",
    "unknown-rule-still-fires-in-prose",
)


def subject_var(target):
    """The env var a control reads to be pointed at a mutated copy."""
    return "DEVTEAM_SUBJECT_" + os.path.splitext(target)[0].upper()


def cases_failing(control, env=None):
    """The set of case names the control reports as FAIL."""
    proc = subprocess.run([sys.executable, os.path.join(HERE, control)],
                          capture_output=True, text=True,
                          env={**os.environ, **(env or {})})
    return {m for m in re.findall(r"^FAIL\s+(\S+)", proc.stdout, re.M)}


def all_cases(control):
    """Every case name the control declares, from its CASES list."""
    src = open(os.path.join(HERE, control), encoding="utf-8").read()
    body = src.split("CASES = [", 1)[1]
    return [m for m in re.findall(r'^\s{4}\("([^"]+)"', body, re.M)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", help="only mutations whose name starts with this")
    ap.add_argument("--list", action="store_true", help="print the mutations and stop")
    args = ap.parse_args()

    muts = [m for m in MUTATIONS
            if not args.check or m[1].startswith(args.check)]
    if args.list:
        for control, name, target, _old, _new in muts:
            print(f"{control:24} {target:20} {name}")
        return 0
    if not muts:
        print("mutate.py: no mutations match", file=sys.stderr)
        return 2

    controls = sorted({m[0] for m in muts})

    # THE BASELINE MUST BE GREEN, or every difference below is noise. A suite
    # that was already red would attribute its own failures to the mutation.
    baseline = {}
    for control in controls:
        red = cases_failing(control)
        if red:
            print(f"mutate.py: {control} is not green before any mutation: "
                  f"{sorted(red)}", file=sys.stderr)
            return 2
        baseline[control] = all_cases(control)

    flipped = {c: {name: [] for name in baseline[c]} for c in controls}
    uncaught = []
    for control, name, target, old, new in muts:
        src = open(os.path.join(HERE, target), encoding="utf-8").read()
        # ASSERTED APPLIED BEFORE THE RUN. A mutation that silently failed to
        # apply produces a green suite and reads as a control that works
        # (0.2.3's lesson) -- and it is the one failure the copy does not fix,
        # because a copy nobody mutated runs exactly like the shipped file.
        if src.count(old) != 1:
            print(f"mutate.py: {name!r} matches {src.count(old)} sites in "
                  f"{target}, expected exactly 1", file=sys.stderr)
            return 2
        # The mutated source is a COPY in a temp directory, named to the
        # control through the environment. The shipped tree is never written,
        # so an interrupted run leaves nothing behind and a concurrent commit
        # has nothing to catch.
        with tempfile.TemporaryDirectory(prefix="devteam-mutate-") as tmp:
            copy = os.path.join(tmp, target)
            with open(copy, "w", encoding="utf-8") as fh:
                fh.write(src.replace(old, new, 1))
            caught = cases_failing(control, {subject_var(target): copy})
            for case in caught:
                flipped[control].setdefault(case, []).append(name)
            if not caught:
                uncaught.append((control, name))

    rc = 0
    if uncaught:
        # A MUTATION NO CASE CATCHES is the other half of the question, and the
        # more urgent half: the suite is green against a source that is broken.
        print(f"\n{len(uncaught)} MUTATION(S) NO CASE CAUGHT — the suite is "
              f"green against a broken source. Each needs a case:")
        for control, name in uncaught:
            print(f"      {control}: {name}")
        rc = 1
    for control in controls:
        print(f"\n{control}")
        unmoved = []
        for case, names in flipped[control].items():
            if names:
                print(f"  {case}")
                for n in names:
                    print(f"      moved by: {n}")
            else:
                unmoved.append(case)
        # DECORATION IS A VERDICT AND IS ONLY REACHED THROUGH COMPLETE_FOR.
        # Everything else unmoved is UNASKED -- a statement about this file,
        # not about the case. Most unasked cases WERE mutation-tested by the
        # subcycle that wrote them, with an ad-hoc harness that no longer
        # exists; calling them decoration would be this script asserting
        # something it did not measure.
        claimed = [c for c in unmoved if c.startswith(COMPLETE_FOR)]
        if claimed:
            print(f"\n  {len(claimed)} case(s) DECORATION — the mutation set for "
                  f"their mechanism is declared complete in COMPLETE_FOR and "
                  f"none of it moves them:")
            for case in sorted(claimed):
                print(f"      {case}")
            rc = 1
        rest = [c for c in unmoved if not c.startswith(COMPLETE_FOR)]
        if rest:
            print(f"\n  {len(rest)} case(s) UNASKED — no mutation declared here "
                  f"targets them, and their mechanism is not in COMPLETE_FOR. "
                  f"Not a verdict. Declaring a mutation, and then the prefix, "
                  f"is how one becomes an answer.")
            for case in sorted(rest):
                print(f"      {case}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
