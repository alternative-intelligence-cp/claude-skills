#!/usr/bin/env python3
"""Reference integrity for a project's `devteam/` directory.

Diffs two lists, repeatedly, because that is what finds holes: identifiers
cited against identifiers declared, links against files, status values against
their closed vocabularies. Reading any one document never reveals the gap.

Findings:

  broken-link       a relative link whose target does not exist
  duplicate-id      one identifier declared twice
  cited-undefined   an identifier cited that was never declared
  defined-uncited   a DECISION declared that nothing cites -- almost always a
                    requirement stating a rule and forgetting to attribute it,
                    which is the whole reason this direction is checked (P-22)
  bad-status        a status value outside its closed vocabulary
  leak              an absolute home path or a credential in a tracked file

Reads GIT-TRACKED files only, so scratch work is never a finding.
Exit 0 clean, 1 findings, 2 could not run.

The grammar it implements is templates/FORMATS.md, which is its one home
(P-34). Its negative control is test_check_refs.py; a check that has never
failed has not been shown to work (P-35).
"""
import os
import re
import subprocess
import sys

# --- the grammar (templates/FORMATS.md) ----------------------------------

DASH = r"[—–-]"
# A title's separator is a dash SURROUNDED BY WHITESPACE. Neither greedy nor
# non-greedy matching on a bare dash works: non-greedy splits at the hyphen in
# "well-known", and greedy splits at the one inside "DONE (2026-09-03)". A
# hyphen inside a word or a date never has spaces around it; a separator always
# does.
SEP = r"(?:\s+[\u2014\u2013]\s+|\s+-\s+)"

DECLARATIONS = (
    re.compile(r"^###\s+(R|D|Q)-(\d+)\s*" + DASH),          # REQUIREMENTS/DECISIONS/QUESTIONS
    re.compile(r"^-\s+\*\*(G|DM|F)-(\d+)\*\*\s*" + DASH),    # goals, done-means, findings
    re.compile(r"^#\s+(T|C)-(\d+)\s*" + DASH),               # a task or checkpoint title
    re.compile(r"^-\s+\[[ x~]\]\s+\*\*(S)-(\d+)\*\*"),       # a step inside a task
)

KNOWN = {"G", "DM", "R", "T", "S", "D", "Q", "C", "F"}
TASK_FILE = re.compile(r"(^|/)tasks/[^/]+\.md$")
# `T-4.S-2` -- the only form that names which task's step it means.
QUALIFIED_STEP = re.compile(r"\bT-(\d+)\.S-(\d+)\b")
# A STEP TABLE DECLARES ITS STEPS, because a rich step carries a class, a role
# and a verify command, and those are columns rather than a run-on line.
#
# The count first given for this was wrong and the correction is worth keeping.
# It was claimed that THREE tasks had independently written tables; measured,
# ONE had. The other two wrote a checklist declaration AND a `### S-n` section
# holding the prose -- which is not a third layout but the rich body hung off
# the declaration this grammar already has. Three findings had been read as
# three departures without anyone counting what each file actually contained.
#
# `### S-n` is therefore NOT a declaration, and adding it here is the obvious
# next move and the wrong one: it produces `duplicate-id` on every task using
# the normal pattern -- eleven of them in one project -- because those tasks
# correctly declare in the checklist and elaborate under the heading.
#
# So: nobody writes the checklist AND the table, and a task that does gets
# `duplicate-id`, correctly. That reasoning holds for the table and does not
# transfer to the heading, which is why the heading stays a body.
TABLE_STEP = re.compile(r"^\|\s*\*{0,2}(S)-(\d+)\*{0,2}\s*\|")
# The tail of a qualified reference, immediately before the bare half.
# `CITATION` finds BOTH `T-9` and `S-4` inside `T-9.S-4`, and the `S-4` was
# charged to the CITING file -- so the one form offered for a cross-task step
# reference fired `cited-undefined` against the task using it, unless that task
# happened to declare the same number. Every control used the form on a task
# that did, which is the single case where the defect is invisible.
QUAL_TAIL = re.compile(r"\bT-\d+\.$")
# Prefixes that live outside devteam/ and are never declared here. `P-n` is a
# protocol rule; citing one is correct and must not be reported as undefined.
EXTERNAL = {"P"}
# Only decisions are required to be cited. A task or question that nothing
# else references is ordinary; an uncited DECISION is the valuable finding.
MUST_BE_CITED = {"D"}

CITATION = re.compile(r"\b([A-Z]{1,2})-(\d+)\b")
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# The identifier grammar governs the ARTIFACTS and nothing else. Paths are
# anchored at the devteam root, so `templates/tasks/TASK.md` -- a blank form
# full of example identifiers -- is not mistaken for `tasks/T-1.md`. Every
# other markdown file under devteam/ still gets its links and leaks checked;
# it just is not project state, and reporting its illustrations as dangling
# citations is the false positive that gets a check disabled (P-35).
ARTIFACTS = re.compile(
    r"^(CHARTER|REQUIREMENTS|DECISIONS|QUESTIONS|BOARD|RECORD|PERMISSIONS)\.md$"
    r"|^tasks/T-\d+\.md$"
    r"|^checkpoints/C-\d+[^/]*\.md$"
    r"|^research/(?!README\.md$)[^/]+\.md$"
)

# Each entry is scoped to the file it governs. `Status.` means different
# things in REQUIREMENTS.md and QUESTIONS.md, and a vocabulary applied to the
# wrong file is a false positive -- the failure mode that gets a check disabled
# (P-35).
VOCAB = (
    ("requirement-status",
     re.compile(r"(^|/)REQUIREMENTS\.md$"),
     re.compile(r"^-\s+\*\*Status\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(open"
                r"|in-progress \(T-\d+(?:,\s*T-\d+)*\)"
                r"|discharged \(T-\d+(?:,\s*T-\d+)*\)"
                r"|struck \(D-\d+\))$")),
    ("question-class",
     re.compile(r"(^|/)QUESTIONS\.md$"),
     re.compile(r"^-\s+\*\*Class\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(REVERSIBLE|IRREVERSIBLE|CHARTER)$")),
    ("question-status",
     re.compile(r"(^|/)QUESTIONS\.md$"),
     re.compile(r"^-\s+\*\*Status\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(open|answered D-\d+|proceeded-unreviewed D-\d+|withdrawn)$")),
    # NEEDS-DECISION is here because the two vocabularies OVERLAP IN MEANING
    # AND NOT IN SPELLING. `BLOCKED (<why>)` means "waiting on a named task",
    # deliberately -- the board legend forbids a bare "waiting". So a task
    # stopped on a question for the client had no title state at all, while
    # the REPORT vocabulary it had just used has exactly the right word. A
    # supervisor reached for `NEEDS-DECISION` and got `bad-status` for using
    # the correct term for its actual situation. That is the same gap as the
    # board once having no state for a task stopped on a question: the fix is
    # to add the state, not to police the word.
    ("task-title",
     re.compile(r"(^|/)tasks/[^/]+\.md$"),
     re.compile(r"^#\s+T-\d+" + SEP + r".*?" + SEP + r"(.+?)\s*$"),
     re.compile(r"^(PLANNED|RUNNING \(.+\)|READY-TO-AUDIT|NEEDS-DECISION \(.+\)"
                r"|BLOCKED \(.+\)|DONE \(.+\))$")),
    ("checkpoint-verdict",
     re.compile(r"(^|/)checkpoints/[^/]+\.md$"),
     re.compile(r"^#\s+C-\d+" + SEP + r".*?" + SEP + r"(.+?)\s*$"),
     re.compile(r"^(ON-COURSE|DRIFTED|BLOCKED)$")),
)

LEAKS = (
    (re.compile(r"(?<![\w.~])/(?:home|Users)/[A-Za-z0-9._-]+/"), "an absolute home path"),
    # A session-scoped temp path encodes a machine layout and a session id and
    # resolves for nobody else. Four were baked into a permanent task record
    # before this existed, and `check_refs` reported the tree clean -- a check
    # passing on the exact condition it exists to detect.
    #
    # Two shapes, because the first attempt at one pattern missed both. A home
    # path survives path-encoding as `-home-<user>-...`, which no `/home/` rule
    # can see; and a UUID under a temp root is a session id wherever it sits in
    # the path, not only in the segment after the root.
    (re.compile(r"(?<![\w-])-home-[A-Za-z0-9._]+-[A-Za-z0-9._-]{4,}"),
     "a path-encoded home directory"),
    (re.compile(r"(?<![\w.~])/(?:tmp|var/folders|private/var)/\S*?"
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}"),
     "a session-scoped temporary path"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), "a GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "an API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key)\s*[=:]\s*['\"][^'\"]{6,}"), "a credential"),
)

# A line that is teaching the grammar rather than using it. Without this the
# format documentation and the templates report themselves, and a check that
# cries wolf on its own examples is one nobody runs.
TEACHING = re.compile(r"<[A-Za-z][^>]*>|`[A-Z]{1,2}-<n>`|\bPREFIX\b")



# Where each kind is declared, and in what shape. A `cited-undefined` that only
# says an identifier is undeclared makes the reader go and find the grammar; a
# record has two grammars for a finding -- the narrative `finding: F-n ...`
# entry and the `- **F-n** --` register line -- and a manager who wrote four of
# the first and none of the second shipped a red tree that cost two of another
# task's agents time establishing the findings were not theirs. Naming the line
# to add turns a diagnosis into a paste, which is a fix; remembering to write
# both is vigilance, which is not.
HOMES = {
    "G":  ("CHARTER.md",      "- **{id}** — <one line>"),
    "DM": ("CHARTER.md",      "- **{id}** — <one line>"),
    "F":  ("RECORD.md",       "- **{id}** — <one line>"),
    "R":  ("REQUIREMENTS.md", "### {id} — <one line>"),
    "D":  ("DECISIONS.md",    "### {id} — <one line>"),
    "Q":  ("QUESTIONS.md",    "### {id} — <one line>"),
    "T":  ("tasks/{id}.md",   "# {id} — <title>"),
    "C":  ("checkpoints/",    "# {id} — <title>"),
    "S":  ("its task file",   "- [ ] **{id}** <one line>"),
}


def how_to_declare(ident):
    """The line that would declare this identifier, or "" for an unknown kind."""
    home = HOMES.get(ident.split("-")[0])
    if home is None:
        return ""
    where, shape = home
    return f". Declare it in {where.format(id=ident)} as `{shape.format(id=ident)}`"

def tracked_markdown(root: str):
    """Git-tracked .md files under root, as absolute paths."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "-z", "--", "*.md"],
            capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [os.path.join(root, p) for p in out.split("\0") if p]


def scan(files, base):
    declared, cited, findings = {}, {}, []
    step_cited = {}

    for path in files:
        rel = os.path.relpath(path, base)
        try:
            raw = open(path, "rb").read()
        except OSError as exc:
            findings.append(("unreadable", rel, 0, str(exc)))
            continue

        # A document that CONTAINS a control byte rather than naming it is
        # treated as binary by git, which then produces no diff for it -- and
        # the whole audit discipline is diffing a document against the thing it
        # describes. Decoding succeeds, so nothing else notices; only git's own
        # stat line does, and nobody reads that. A digest about encodings or
        # protocols is more likely to do this than an ordinary document,
        # because the natural way to write about a byte is to write the byte.
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            findings.append(("not-utf8", rel, 0,
                             f"byte {exc.object[exc.start]:#04x} at offset {exc.start}"))
            text = raw.decode("utf-8", errors="replace")
        for n_, line in enumerate(text.split("\n"), 1):
            bad = {c for c in line if ord(c) < 0x20 and c not in "\t\r"}
            if bad:
                names = ", ".join(f"U+{ord(c):04X}" for c in sorted(bad))
                findings.append(("control-character", rel, n_,
                                 f"{names} embedded in the text — name the byte, "
                                 "do not write it; git treats the file as binary "
                                 "and stops diffing it"))
        lines = text.split("\n")

        is_artifact = bool(ARTIFACTS.match(rel.replace(os.sep, "/")))
        in_fence = False
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue

            for pat, why in LEAKS:
                m = pat.search(line)
                if m:
                    findings.append(("leak", rel, n, f"{why}: {m.group(0)[:40]}"))

            if in_fence:
                continue

            for target in LINK.findall(line):
                target = target.split("#", 1)[0].strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), target))):
                    findings.append(("broken-link", rel, n, target))

            if not is_artifact:
                continue

            # Status vocabularies are checked BEFORE declarations are handled,
            # because a task's title line is both -- it declares T-n AND
            # carries the status. Checking after the declaration branch's
            # `continue` meant task and checkpoint statuses were never checked
            # at all, which the control caught.
            for name, scope, field, valid in VOCAB:
                if not scope.search(rel):
                    continue
                m = field.match(line)
                if m and not TEACHING.search(m.group(1)) and not valid.match(m.group(1)):
                    findings.append(("bad-status", rel, n,
                                     f"{name}: {m.group(1)!r} is not in the vocabulary"))

            # Recorded WITHOUT `continue`, unlike every other declaration,
            # because a step row's remaining cells carry real citations -- the
            # requirements it discharges, the decision its verify proves. The
            # step's own `S-n` then resolves against the declaration this line
            # just made, which is harmless: only decisions must be cited.
            tab = TABLE_STEP.match(line)
            if tab:
                key = f"{rel}:{tab.group(1)}-{tab.group(2)}"
                if key in declared:
                    findings.append(("duplicate-id", rel, n,
                                     f"S-{tab.group(2)} already declared at {declared[key]}"))
                else:
                    declared[key] = f"{rel}:{n}"

            # A declaration line declares; it does not also cite itself.
            decl = None
            for pat in DECLARATIONS:
                m = pat.match(line)
                if m:
                    decl = f"{m.group(1)}-{m.group(2)}"
                    break

            if decl:
                # Steps are numbered per task, so they are keyed by their file.
                key = f"{rel}:{decl}" if decl.startswith("S-") else decl
                if key in declared:
                    findings.append(("duplicate-id", rel, n,
                                     f"{decl} already declared at {declared[key]}"))
                else:
                    declared[key] = f"{rel}:{n}"
                continue

            # A STEP IS NUMBERED PER TASK, so a citation of one resolves
            # against a single file rather than the whole project. Flattening
            # the namespace made every `S-n` resolve against any task that
            # happened to declare that number: a task whose steps were written
            # in a form the grammar does not recognise declared NONE of its
            # own, and its S-1..S-5 passed anyway on other tasks' declarations.
            # Only S-6 -- the first number no task had ever used -- reported.
            # The check was measuring whether a number had ever been used
            # anywhere, which is not what it is for.
            owner = rel if TASK_FILE.search(rel) else None
            for m in QUALIFIED_STEP.finditer(line):
                step_cited.setdefault((f"tasks/T-{m.group(1)}.md", f"S-{m.group(2)}"),
                                      f"{rel}:{n}")
            for m in CITATION.finditer(line):
                pre, num = m.group(1), m.group(2)
                if pre in EXTERNAL or pre not in KNOWN:
                    continue
                if pre == "S":
                    # The bare half of `T-n.S-m`, already recorded against the
                    # task it names. Charging it to this file as well made the
                    # qualified form self-defeating. The `T-n` half is a real
                    # citation of that task and is deliberately left alone.
                    if QUAL_TAIL.search(line[:m.start()]):
                        continue
                    # Bare `S-n` outside a task file names no task and cannot
                    # be resolved -- `T-4.S-2` is the form that can. Skipping
                    # it beats guessing: the record legitimately discusses
                    # steps in prose, and a check that fires on prose is one
                    # somebody turns off.
                    if owner:
                        step_cited.setdefault((owner, f"S-{num}"), f"{rel}:{n}")
                    continue
                cited.setdefault(f"{pre}-{num}", []).append(f"{rel}:{n}")


    for (owner, ident), where in sorted(step_cited.items()):
        if f"{owner}:{ident}" not in declared:
            f, n = where.rsplit(":", 1)
            findings.append(("cited-undefined", f, int(n),
                             f"{ident} is cited but {owner} declares no such step "
                             "— steps are numbered per task, so a declaration in "
                             "another task file does not resolve this one"))

    bare = {k for k in declared if not k.startswith("tasks/")}
    for ident, where in sorted(cited.items()):
        if ident not in bare:
            findings.append(("cited-undefined", where[0].split(":")[0],
                             int(where[0].split(":")[-1]),
                             f"{ident} is cited but never declared{how_to_declare(ident)}"))
    for key, where in sorted(declared.items()):
        ident = key.split(":", 1)[1] if ":" in key else key
        if ident.split("-")[0] in MUST_BE_CITED and ident not in cited:
            f, n = where.rsplit(":", 1)
            findings.append(("defined-uncited", f, int(n),
                             f"{ident} is declared but nothing cites it"))
    return findings


def check(target: str):
    target = os.path.realpath(target)
    if os.path.basename(target) != "devteam" and os.path.isdir(os.path.join(target, "devteam")):
        target = os.path.join(target, "devteam")
    if not os.path.isdir(target):
        print(f"check_refs: not a directory: {target}", file=sys.stderr)
        return None
    files = tracked_markdown(target)
    if files is None:
        print(f"check_refs: not a git repository: {target}", file=sys.stderr)
        return None
    return scan(files, target), target


def main(argv):
    targets = argv[1:] or ["."]
    total, ran = 0, 0
    for t in targets:
        got = check(t)
        if got is None:
            return 2
        findings, resolved = got
        ran += 1
        label = os.path.relpath(resolved, os.getcwd())
        if findings:
            print(f"{label}: {len(findings)} finding(s)")
            for kind, path, line, detail in sorted(findings, key=lambda f: (f[0], f[1], f[2])):
                print(f"  {kind:16} {path}:{line}  {detail}")
            total += len(findings)
        else:
            print(f"{label}: clean")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
