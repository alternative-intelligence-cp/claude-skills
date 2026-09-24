#!/usr/bin/env python3
"""The result every devteam check ends in -- one object, one line, one exit.

A check never reports clean when it did not look (cycle 0.3's L-6; roadmap
0.3.1, L-1.1 and L-1.2). So a check ends in one of FOUR results, not three:

    clean           0   everything the check owns was evaluated against
                        everything it exists to read, and nothing was found
    findings        1   at least one finding
    could not run   2   the check could not start -- its arguments, no
                        repository, no devteam/
    not evaluated   3   no finding, and at least one part not evaluated,
                        each named with its reason

Findings and parts not evaluated together exit 1, and the line names both:
a finding is definite, and naming the parts not looked at stops anyone
reading a partial finding set as the whole.

EXIT 2 AND EXIT 3 ARE DIFFERENT REMEDIES. Exit 2 is the tool unable to answer,
and the remedy is in the invocation. Exit 3 is the tool answering about the
project and naming what it could not read, and the remedy is in the project.
One code for two remedies sends one of them to the wrong place -- which is why
0.2.6's move of `unreadable` and `not-utf8` to exit 2 is superseded here: a
project file the check cannot decode is the project's state.

A part EXCLUDED by a declaration -- a flag the caller passed (`--pre-plan`), or
a project declaration the check reads itself (the charter's
`Containment: guard-only`) -- is named in the line and does not change the exit
code. What makes the difference is who said so: an exclusion has a declaration
behind it that a reader can check, and a gap has none.

THE LINE AND `--json` ARE RENDERED FROM ONE OBJECT, so the two cannot disagree,
and this file is the contract's one home (P-34). The checks keep their own emit
sites -- bare `add(...)` and `findings.append((...))` -- because check_plugin's
`unruled-finding` reads each check's classes from exactly those sites
(docs/CHECKS.md). A finding reaches a Result only at the end, through
`Result.finding`, which that parser deliberately does not match.

Its control is test_result.py.
"""
import json
import re
import sys

CLEAN, FINDINGS, COULD_NOT_RUN, NOT_EVALUATED = 0, 1, 2, 3
SCHEMA = 1
WORD = {CLEAN: "clean", FINDINGS: "findings", COULD_NOT_RUN: "could not run",
        NOT_EVALUATED: "not evaluated"}

# Which exit a run over several targets reports: 2 > 1 > 3 > 0. A target that
# could not be checked at all outranks everything; a definite finding outranks
# a gap; a gap outranks clean.
_RANK = {CLEAN: 0, NOT_EVALUATED: 1, FINDINGS: 2, COULD_NOT_RUN: 3}
_ANCHOR = re.compile(r"^(?P<file>.+?):(?P<line>\d+)$")


def worst(codes):
    """The exit code for several results, by the precedence 2 > 1 > 3 > 0."""
    return max(codes, key=_RANK.__getitem__, default=CLEAN)


def flag(argv, name):
    """(present, argv without it). Flags may appear anywhere in argv."""
    return name in argv, [a for a in argv if a != name]


class Result:
    """What one check found in one target, and what it did not look at."""

    def __init__(self, check, target, width=20):
        self.check, self.target, self.width = check, target, width
        self.findings = []      # dicts: class, file, line, detail, advisory
        self.gaps = []          # (part, reason, advisory)
        self.excluded = []      # (part, declaration)
        self.counts = []        # (n, label): the denominators, in order
        self.clean_note = ""    # said after the denominators, only when clean
        self.blocking_only = False
        self.trailer = []       # check-specific lines printed after the rest

    def finding(self, kind, where, detail, advisory=False):
        """A finding. `where` is `file:line`, a bare file, or empty."""
        m = _ANCHOR.match(where or "")
        path, line = (m.group("file"), int(m.group("line"))) if m else (where or "", None)
        self.findings.append({"class": kind, "file": path, "line": line,
                              "detail": detail, "advisory": bool(advisory)})

    def gap(self, part, reason, advisory=False):
        """A part this check did not evaluate, and why. Never silent."""
        self.gaps.append((part, reason, bool(advisory)))

    def exclude(self, part, declaration):
        """A part left out because a declaration says so, named with it."""
        self.excluded.append((part, declaration))

    def count(self, n, label):
        self.counts.append((n, label))

    def _live(self, items, advisory):
        # --blocking-only changes the VERDICT, never the report: advisory
        # findings and gaps are still printed, and only stop counting here.
        return [x for x in items if not (self.blocking_only and advisory(x))]

    @property
    def exit_code(self):
        if self._live(self.findings, lambda f: f["advisory"]):
            return FINDINGS
        if self._live(self.gaps, lambda g: g[2]):
            return NOT_EVALUATED
        return CLEAN

    def status(self):
        n, k = len(self.findings), len(self.gaps)
        if n:
            return f"{n} finding(s)" + (f", {k} part(s) not evaluated" if k else "")
        if k:
            return f"not evaluated ({k} part(s))"
        return "clean"

    def lines(self):
        head = f"{self.target}: {self.status()}" if self.target else self.status()
        denominators = ", ".join(f"{n} {label}" for n, label in self.counts)
        if denominators and self.clean_note and not (self.findings or self.gaps):
            denominators += f" {self.clean_note}"
        if denominators:
            head += f"  [{denominators}]"
        out = [head]
        for f in sorted(self.findings, key=lambda f: (f["class"], f["file"], f["line"] or 0)):
            where = f"{f['file']}:{f['line']}" if f["line"] is not None else f["file"]
            mark = "  (advisory)" if f["advisory"] else ""
            out.append(f"  {f['class']:{self.width}} {where}  {f['detail']}{mark}".rstrip())
        for part, reason, advisory in self.gaps:
            mark = "  (advisory)" if advisory else ""
            out.append(f"  not evaluated: {part} — {reason}{mark}")
        for part, declaration in self.excluded:
            out.append(f"  excluded: {part} — by {declaration}")
        return out + self.trailer

    def as_dict(self):
        return {
            "check": self.check,
            "target": self.target,
            "result": WORD[self.exit_code],
            "exit": self.exit_code,
            "counts": {label: n for n, label in self.counts},
            "findings": self.findings,
            "not_evaluated": [{"part": p, "reason": r, "advisory": a}
                              for p, r, a in self.gaps],
            "excluded": [{"part": p, "by": d} for p, d in self.excluded],
        }


def emit(results, as_json, stream=None):
    """Print every result, as lines or as one JSON document; return the exit."""
    stream = stream or sys.stdout
    code = worst(r.exit_code for r in results)
    if as_json:
        json.dump({"schema": SCHEMA, "exit": code,
                   "results": [r.as_dict() for r in results]},
                  stream, indent=1, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    else:
        for r in results:
            for line in r.lines():
                print(line, file=stream)
    return code


def could_not_run(check, message, as_json):
    """Exit 2: the tool cannot answer. Always said on stderr; in JSON too if asked."""
    print(f"{check}: {message}", file=sys.stderr)
    if as_json:
        json.dump({"schema": SCHEMA, "exit": COULD_NOT_RUN, "check": check,
                   "error": message}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    return COULD_NOT_RUN
