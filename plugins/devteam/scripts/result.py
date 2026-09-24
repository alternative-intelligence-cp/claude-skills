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

What makes a part not evaluated when a check parses rows -- zero rows, a
partial read, a wrapped field (L-1.3) -- is also here, at the bottom, for the
same reason. So is what a decision accepts (L-1.6): its grammar is read here,
and a finding's identity -- what the gate also matches by -- is defined here.

Its control is test_result.py.
"""
import collections
import json
import os
import re
import subprocess
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
        self.accepted = []      # finding dicts, each with `by`: the D-n that accepts it
        self.accepted_gaps = [] # (part, reason, advisory, by)
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

    def accept(self, got, covers=lambda a: True):
        """Apply what DECISIONS.md accepts of this check (L-1.6), and return
        each acceptance this run covers that matched nothing, as `(where,
        detail)` for the check to emit as `stale-acceptance` at its own emit
        site -- which is where check_plugin's `unruled-finding` reads classes.

        `covers(a)` says whether this run evaluated what `a` names, so that
        only a run able to have found it can call it stale. A targeted run --
        one task's report, one task's writes -- covers only what names its
        target, or every acceptance of a task-scoped class would read as
        stale in every other task's run. A class this run EXCLUDED by a
        declaration was not evaluated either, so it is never covered.

        An acceptance matches every finding with its identity, so two lines
        naming one finding both match and neither is stale.
        """
        if got.unreadable:
            self.gap("DECISIONS.md's acceptances", got.unreadable)
            return []
        held = " ".join(part for part, _ in self.excluded)
        found, gaps = list(self.findings), list(self.gaps)
        took_f, took_g, stale = {}, {}, []
        for a in got.items:
            if a.check != self.check or not covers(a):
                continue
            if a.cls and re.search(rf"(?<![\w-]){re.escape(a.cls)}(?![\w-])", held):
                continue
            if a.part is not None:
                hit = [i for i, g in enumerate(gaps) if " ".join(g[0].split()) == a.part]
                for i in hit:
                    took_g.setdefault(i, a.decision)
            else:
                hit = [i for i, f in enumerate(found) if identity(self.check, f) == a.key]
                for i in hit:
                    took_f.setdefault(i, a.decision)
            if not hit:
                stale.append((f"DECISIONS.md:{a.line}", _stale(a, self.check)))
        self.findings = [f for i, f in enumerate(found) if i not in took_f]
        self.accepted += [dict(f, by=took_f[i]) for i, f in enumerate(found) if i in took_f]
        self.gaps = [g for i, g in enumerate(gaps) if i not in took_g]
        self.accepted_gaps += [(*g, took_g[i]) for i, g in enumerate(gaps) if i in took_g]
        return stale

    def deciders(self):
        """The decisions that accepted anything here, in number order."""
        by = {f["by"] for f in self.accepted} | {g[3] for g in self.accepted_gaps}
        return sorted(by, key=lambda d: int(d.split("-")[1]))

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
            out = f"{n} finding(s)" + (f", {k} part(s) not evaluated" if k else "")
        elif k:
            out = f"not evaluated ({k} part(s))"
        else:
            out = "clean"
        # What a decision accepted is said ON THE LINE, with the decisions,
        # so a zero reached by accepting is never read as a zero reached by
        # fixing (CONSOLIDATION 8a).
        accepted = len(self.accepted) + len(self.accepted_gaps)
        if accepted:
            out += f", {accepted} accepted by {', '.join(self.deciders())}"
        return out

    def lines(self):
        head = f"{self.target}: {self.status()}" if self.target else self.status()
        denominators = ", ".join(f"{n} {label}" for n, label in self.counts)
        # A part a decision accepted was still not looked at, so a note that
        # claims the whole was read -- `traced end to end` -- would be false.
        if (denominators and self.clean_note
                and not (self.findings or self.gaps or self.accepted_gaps)):
            denominators += f" {self.clean_note}"
        if denominators:
            head += f"  [{denominators}]"
        out = [head]
        at = lambda f: f"{f['file']}:{f['line']}" if f["line"] is not None else f["file"]
        order = lambda f: (f["class"], f["file"], f["line"] or 0)
        for f in sorted(self.findings, key=order):
            mark = "  (advisory)" if f["advisory"] else ""
            out.append(f"  {f['class']:{self.width}} {at(f)}  {f['detail']}{mark}".rstrip())
        for part, reason, advisory in self.gaps:
            mark = "  (advisory)" if advisory else ""
            out.append(f"  not evaluated: {part} — {reason}{mark}")
        for part, declaration in self.excluded:
            out.append(f"  excluded: {part} — by {declaration}")
        for f in sorted(self.accepted, key=order):
            out.append(f"  accepted by {f['by']}: {f['class']} {at(f)}  {f['detail']}".rstrip())
        for part, reason, _advisory, by in self.accepted_gaps:
            out.append(f"  accepted by {by}: not evaluated: {part} — {reason}")
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
            "accepted": self.accepted,
            "accepted_not_evaluated": [{"part": p, "reason": r, "advisory": a, "by": b}
                                       for p, r, a, b in self.accepted_gaps],
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


# --- zero rows, partial reads and wrapped fields (roadmap 0.3.1, L-1.3) -----
#
# Every parse site counts two things: the rows its source OFFERS, by a loose
# shape -- a table line, a list item, a field line -- and the rows its grammar
# ACCEPTS. A row offered and not accepted makes the site not evaluated, and is
# named by file and line; zero rows parsed from a source that offered some is
# the same thing at its limit. A source that offers nothing is genuinely empty,
# and clean, with its zero in the denominators. A field whose value continues
# past its first physical line, where the check reads only that line, is not
# evaluated either, and the field is named.
#
# The loose shapes are each check's, because each reads a different grammar.
# What is shared is below: what counts as a continuation, and how an unparsed
# row is named, so the three cases read the same in every check (P-34).
# Reading continuation lines is 0.3.2's work; this only makes each gap visible.

_BLOCK_START = re.compile(r"^(?:[-*+]\s|\d+[.)]\s|#|\||>|```|~~~)")


def continuation(lines, i):
    """0-based indices of the lines that continue the list item at `lines[i]`.

    CommonMark's rule, cut to what these documents use. An indented line
    belongs to the item, after a blank line too, because that is how a nested
    list or a second paragraph is written. An unindented line belongs to it
    only as a lazy continuation: immediately after, and only when it does not
    open a block of its own.
    """
    out, j, blank = [], i + 1, False
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            blank = True
        elif line[:1] in (" ", "\t"):
            out.append(j)
            blank = False
        elif not blank and not _BLOCK_START.match(line):
            out.append(j)
        else:
            break
        j += 1
    return out


def anchors(rows):
    """`(file, line)` pairs as one compact string that still names every row.

    `BOARD.md:64-82` only when every line in the run is one of the rows, so a
    range never names a line that is not.
    """
    by_file = {}
    for f, n in rows:
        by_file.setdefault(f, set()).add(n)
    parts = []
    for f in sorted(by_file):
        ns, runs = sorted(by_file[f]), []
        for n in ns:
            if runs and n == runs[-1][1] + 1:
                runs[-1][1] = n
            else:
                runs.append([n, n])
        parts.append(f"{f}:" + ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in runs))
    return "; ".join(parts)


def unparsed(rows, offered, what, grammar, consequence=""):
    """The reason a parse site is not evaluated, naming each row it missed."""
    return (f"{len(rows)} of {offered} {what} do not parse as {grammar}"
            + (f", so {consequence}" if consequence else "")
            + f" ({anchors(rows)})")


def wrapped(where, check):
    """The reason a field is not evaluated: it continues past the line read."""
    return f"{where} continues past its first line, and {check} reads only the first"


# --- untracked files (roadmap 0.3.1, L-1.4) ---------------------------------
#
# A check that enumerates `devteam/` reads what git would show: tracked files
# AND untracked ones that no ignore rule covers. It used to read the index
# alone, so a new task file was invisible to all three plan checks until it
# was staged, and the checks said clean over it (F-131). Each untracked file is
# now read, and reported as `untracked-file`, which turns the miss into a
# finding rather than a step someone must remember -- the register's reason
# for choosing this remedy. Ignored files, `devteam/.run/` among them, stay
# invisible.

def listed(root, *patterns):
    """(every file, the untracked ones among them) that git lists under `root`
    for these pathspecs, relative to `root` -- or None outside a repository."""
    run = lambda *a: subprocess.run(["git", "-C", root, "ls-files", "-z", *a, "--", *patterns],
                                    capture_output=True, text=True, check=True).stdout
    try:
        every = run("--cached", "--others", "--exclude-standard")
        untracked = run("--others", "--exclude-standard")
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    split = lambda out: [p for p in out.split("\0") if p]
    return sorted(set(split(every))), set(split(untracked))


UNTRACKED = ("is not tracked by git, so it is in no commit: every check reads it, "
             "and a clone, a review or the gate at HEAD does not. Commit it, or "
             "move it out of devteam/ if it is scratch")


# --- accepted findings (roadmap 0.3.1, L-1.6) --------------------------------
#
# AN ACCEPTED FINDING IS A DECISION, classed like any other. A `D-n` in
# DECISIONS.md carries an `Accepts.` field, and each item under it names one
# finding as the check printed it -- check, class and anchor file, then the
# message after a dash -- or one part not evaluated, by its part:
#
#     - **Accepts.**
#       - `check_trace` `missing-field` `tasks/T-1.md` — T-1 has no **Discharges.**
#       - `check_refs` not evaluated: audits/x.md's findings
#
# There is no line number, so an edit above the anchor moves the line and
# leaves the finding accepted. The check reports what was accepted, names the
# decision on its line, and exits 0 when nothing else is found.
#
# The decision's P-26 class decides who makes it: the manager decides a
# REVERSIBLE acceptance alone, recorded as unreviewed (P-27), and the client
# decides a CHARTER one. So a decision that accepts anything must say who
# reviewed it -- the `Reviewed.` line is where P-27's record lives -- or it
# accepts nothing. Which class an acceptance IS stays the decider's judgement,
# because no check can tell.
#
# THE ZERO STAYS A SIGNAL (CONSOLIDATION 8a). An acceptance that matches
# nothing is `stale-acceptance`, so a fixed finding leaves no standing
# exemption for the next one to hide under. An acceptance the grammar cannot
# read accepts NOTHING and is reported, as `unparseable-acceptance` by
# check_refs, which owns DECISIONS.md's grammar -- the direction the run's own
# gate parser failed in, which was the right one (pricelog RECORD.md:430).
# Superseding the decision withdraws what it accepted (P-23).

PROJECT_CHECKS = ("check_trace", "check_refs", "check_report", "check_scope")

_DECISION = re.compile(r"^###\s+(D-\d+)\s*[—–-]")
_HEADING = re.compile(r"^#{1,3}\s")
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_ACCEPTS = re.compile(r"^-\s+\*\*Accepts\.\*\*\s*$")
# The field NAMED, however it is decorated -- `- **Accepts:**`, a paragraph's
# `**Accepts.**`, an item carried inline -- so a field written slightly wrong
# is reported instead of never seen (L-1.3).
_ACCEPTS_ISH = re.compile(r"^\s*(?:[-*+]\s+)?\**\s*Accepts\s*\**\s*[.:]", re.I)
_SUPERSEDES = re.compile(r"^-\s+\*\*Supersedes\.\*\*\s*(.*?)\s*$")
_REVIEWED = re.compile(r"^-\s+\*\*Reviewed\.\*\*\s*(.*?)\s*$")
_REVIEWED_OK = re.compile(r"^(?:client|unreviewed|proceeded-unreviewed \(Q-\d+\))$")
_ITEM = re.compile(r"^\s+[-*+]\s+(.*?)\s*$")
_A_FINDING = re.compile(r"^`(\w+)`\s+`([a-z][a-z0-9-]*)`\s+`([^`\s]+)`\s+[—–-]\s+(\S.*)$")
_A_PART = re.compile(r"^`(\w+)`\s+not evaluated:\s+(\S.*)$")
# A line number inside a message moves with the file, exactly as the anchor's
# does: `already declared at tasks/T-4.md:12`, `(also 14, 22)`.
_LINE_REF = re.compile(r"(\.[A-Za-z0-9]+):\d+(?:-\d+)?(?!\d)")
_ALSO = re.compile(r"\s*\(also \d+(?:, \d+)*\)")

Acceptance = collections.namedtuple("Acceptance", "decision line check cls file message part text")
Acceptance.key = property(lambda a: (a.check, a.cls, a.file, stable(a.message)))


class Accepted:
    """What DECISIONS.md accepts. `items` are applied; `unread` are reported,
    as `(where, detail)`; `quoted` is every line an acceptance occupies, which
    check_refs reads as quoted check output rather than as citations; and
    `unreadable` is why nothing could be read, when nothing could."""

    def __init__(self):
        self.items, self.unread, self.quoted, self.unreadable = [], [], set(), None


def stable(text):
    """A message as it stays when an edit above its anchor moves it: the line
    numbers inside it dropped, and its whitespace collapsed."""
    return " ".join(_LINE_REF.sub(r"\1", _ALSO.sub("", text or "")).split())


def identity(check, finding):
    """What a finding IS, apart from where it sits today: its check, class,
    anchor file and message, with no line number (L-1.6). An acceptance
    matches by it, and so does the gate, comparing HEAD with the candidate."""
    return (check, finding["class"], finding["file"], stable(finding["detail"]))


def acceptances(devteam):
    """Every acceptance in `devteam/DECISIONS.md`, read as git would show it
    (L-1.4): tracked, or untracked and not ignored."""
    got = Accepted()
    listing = listed(devteam, "DECISIONS.md")
    if not listing or "DECISIONS.md" not in listing[0]:
        return got
    try:
        with open(os.path.join(devteam, "DECISIONS.md"), "rb") as fh:
            text = fh.read().decode("utf-8")
    except UnicodeDecodeError as exc:
        got.unreadable = (f"DECISIONS.md is not UTF-8 (byte {exc.object[exc.start]:#04x} at "
                          f"offset {exc.start}), so no acceptance was read and none could be "
                          "found stale")
        return got
    except OSError as exc:
        got.unreadable = (f"DECISIONS.md cannot be read ({exc.strerror}), so no acceptance "
                          "was read and none could be found stale")
        return got
    return parse_acceptances(text.split("\n"), got)


def parse_acceptances(lines, got=None):
    """The `Accepts.` fields in DECISIONS.md's lines, into an `Accepted`."""
    got = got or Accepted()
    unread = lambda n, why: got.unread.append((f"DECISIONS.md:{n}", f"{why}, so it accepts nothing"))

    # Which decision each line sits in, outside fences, and what each decision
    # says about itself -- in either order, since fields are not ordered.
    owner, fenced, decision, inside = [], [], None, False
    reviewed, superseded = {}, set()
    for line in lines:
        if _FENCE.match(line):
            inside = not inside
            owner.append(None)
            fenced.append(True)
            continue
        fenced.append(inside)
        if inside:
            owner.append(None)
            continue
        m = _DECISION.match(line)
        if m:
            decision = m.group(1)
        elif _HEADING.match(line):
            decision = None
        owner.append(decision)
        if decision:
            r, s = _REVIEWED.match(line), _SUPERSEDES.match(line)
            if r:
                reviewed.setdefault(decision, r.group(1))
            if s:
                superseded.update(d for d in re.findall(r"\bD-\d+\b", s.group(1)) if d != decision)

    for i, line in enumerate(lines):
        if fenced[i] or not _ACCEPTS_ISH.match(line):
            continue
        d, n, under = owner[i], i + 1, continuation(lines, i)
        got.quoted.update(j + 1 for j in under)
        if d in superseded:
            continue                        # withdrawn with its decision (P-23)
        if not _ACCEPTS.match(line):
            unread(n, "the line names `Accepts.` and does not parse as `- **Accepts.**` "
                      "alone on its line, with each acceptance an indented item under it")
            continue
        if d is None:
            unread(n, "`Accepts.` sits in no decision's block (`### D-n — …`), so no "
                      "decision stands behind it (L-1.6)")
            continue
        if not _REVIEWED_OK.match(reviewed.get(d, "")):
            said = f"reads {reviewed[d]!r}" if d in reviewed else "is missing"
            unread(n, f"{d} accepts findings and its `Reviewed.` line {said}, not `client`, "
                      "`unreviewed` or `proceeded-unreviewed (Q-n)` — so nobody can tell "
                      "whether the client saw what it accepts (L-1.6, P-27)")
            continue
        items = [j for j in under if _ITEM.match(lines[j])]
        if not items:
            unread(n, f"{d}'s `Accepts.` has no indented item under it")
            continue
        for j in under:
            if j < items[0]:
                unread(j + 1, f"a line under {d}'s `Accepts.` is not an item")
        for k, j in enumerate(items):
            end = items[k + 1] if k + 1 < len(items) else len(lines)
            if any(j < x < end for x in under):
                unread(j + 1, f"{d}'s acceptance continues past its line, and an "
                              "acceptance is read from one line")
                continue
            body = _ITEM.match(lines[j]).group(1)
            f, p = _A_FINDING.match(body), _A_PART.match(body)
            m = f or p
            if not m:
                unread(j + 1, f"{d}'s acceptance does not parse as a backticked check, "
                              "class and file, then a dash and the message; or a backticked "
                              "check, then `not evaluated:` and the part")
            elif m.group(1) not in PROJECT_CHECKS:
                unread(j + 1, f"{d}'s acceptance names `{m.group(1)}`, which is not one of "
                              f"the project checks ({', '.join(PROJECT_CHECKS)})")
            elif p and m.group(1) == "check_report":
                unread(j + 1, f"{d} accepts a part check_report did not evaluate, and "
                              "check_report reads one task at a time with parts that name "
                              "no task, so no run could ever find the acceptance stale — "
                              "accept its findings, which name their task's file")
            elif f:
                got.items.append(Acceptance(d, j + 1, f.group(1), f.group(2), f.group(3),
                                            f.group(4), None, body))
            else:
                got.items.append(Acceptance(d, j + 1, p.group(1), None, None, None,
                                            " ".join(p.group(2).split()), body))
    return got


def _stale(a, check):
    """Why a covered acceptance that matched nothing is a finding."""
    if a.part is not None:
        return (f"{a.decision} accepts the part `{a.part}`, which {check} does not report "
                f"as not evaluated — evaluated since, or not the part as {check} prints "
                f"it, up to its dash. If it is evaluated now, supersede {a.decision} "
                "without it (P-23)")
    return (f"{a.decision} accepts `{a.cls}` at {a.file}, which {check} does not report — "
            f"fixed since, or not the finding as {check} prints it, less its line number. "
            f"If it is fixed, supersede {a.decision} without it (P-23). It reads: {a.message}")
