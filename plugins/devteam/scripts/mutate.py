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
mutation to the shipped source, runs the control, records which cases changed
verdict, and restores. What it prints is the thing no instrument in this
repository recorded before: PER CASE, THE MUTATIONS THAT MOVE IT -- and,
underneath, THE CASES NO MUTATION MOVES, which are the decorations.

    $ python3 scripts/mutate.py                 every declared mutation
    $ python3 scripts/mutate.py --check unknown-rule    one set
    $ python3 scripts/mutate.py --list          what is declared, without running

WHY THE MUTATIONS ARE WRITTEN HERE AND NOT DERIVED. A generated mutation --
flip a comparison, drop a branch -- would mostly produce sources that fail
every case at once, which says nothing about any individual case. Each mutation
below is a WRONG-BUT-PLAUSIBLE version of the mechanism: the draft that was
actually written first, or the simplification a later reader would reach for.
That is the population a twin has to discriminate against.

IT MUTATES THE SHIPPED FILES IN PLACE and restores in a `finally`. That is a
departure from "mutate in a scratch copy" and it is deliberate: the controls
import and copy the real module path, so a scratch copy would test the copy.
Two workers made this same departure independently before it was written down
(0.2.6's session, and this one), which is DESIGN §20's second-half detector
firing -- so the departure is recorded here rather than left to be re-derived
a third time. The guard against the obvious hazard is that every mutation
asserts its OLD text is present before writing, and a mutation left applied
looks exactly like a suite that passes (0.2.3's lesson).

Exit 0 if every case is moved by at least one mutation, 1 if any case is
moved by none, 2 if a mutation could not be applied.
"""
import argparse
import os
import re
import subprocess
import sys

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


def cases_failing(control):
    """The set of case names the control reports as FAIL."""
    proc = subprocess.run([sys.executable, os.path.join(HERE, control)],
                          capture_output=True, text=True)
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
    for control, name, target, old, new in muts:
        path = os.path.join(HERE, target)
        src = open(path, encoding="utf-8").read()
        # ASSERTED APPLIED BEFORE THE RUN. A mutation that silently failed to
        # apply produces a green suite and reads as a control that works.
        if src.count(old) != 1:
            print(f"mutate.py: {name!r} matches {src.count(old)} sites in "
                  f"{target}, expected exactly 1", file=sys.stderr)
            return 2
        try:
            open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
            for case in cases_failing(control):
                flipped[control].setdefault(case, []).append(name)
        finally:
            open(path, "w", encoding="utf-8").write(src)

    rc = 0
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
        # A CASE THIS FILE DECLARES NO MUTATION FOR IS NOT SHOWN TO BE
        # DECORATION -- IT IS UNASKED, and the difference is the whole
        # honesty of the instrument. An earlier draft of this script printed
        # every unmoved case under the heading "decoration". Run over the
        # 32-case check_plugin control with only the four 0.2.7 mutations
        # declared, it called 28 cases decoration -- every one of which HAD
        # been mutation-tested, by the ad-hoc harnesses of the subcycles that
        # wrote them, which no longer exist. The instrument would have
        # answered "which cases did MY mutations move" while appearing to
        # answer "which cases control anything" (P-35b), inside the script
        # built to catch that shape. So the two are separated by name, and
        # only the first is a verdict.
        targeted = {c for c in unmoved
                    if any(c.split("-")[0] in m[1] or m[1].split(":")[0] in c
                           for m in muts if m[0] == control)}
        if targeted:
            print(f"\n  {len(targeted)} case(s) NO MUTATION MOVED, though this "
                  f"file declares mutations for their mechanism — decoration:")
            for case in sorted(targeted):
                print(f"      {case}")
            rc = 1
        rest = [c for c in unmoved if c not in targeted]
        if rest:
            print(f"\n  {len(rest)} case(s) NOT ASKED — no mutation declared "
                  f"here targets them. NOT a verdict: most were mutation-tested "
                  f"by the subcycle that wrote them, with a harness that no "
                  f"longer exists. Declaring a mutation for one is how it "
                  f"becomes an answer.")
            for case in sorted(rest):
                print(f"      {case}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
