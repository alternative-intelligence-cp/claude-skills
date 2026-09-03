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

DECLARATIONS = (
    re.compile(r"^###\s+(R|D|Q)-(\d+)\s*" + DASH),          # REQUIREMENTS/DECISIONS/QUESTIONS
    re.compile(r"^-\s+\*\*(G|DM)-(\d+)\*\*\s*" + DASH),      # CHARTER goals / done-means
    re.compile(r"^#\s+(T|C)-(\d+)\s*" + DASH),               # a task or checkpoint title
    re.compile(r"^-\s+\[[ x~]\]\s+\*\*(S)-(\d+)\*\*"),       # a step inside a task
)

KNOWN = {"G", "DM", "R", "T", "S", "D", "Q", "C"}
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
    r"|^tasks/[^/]+\.md$"
    r"|^checkpoints/[^/]+\.md$"
    r"|^research/[^/]+\.md$"
)

# Each entry is scoped to the file it governs. `Status.` means different
# things in REQUIREMENTS.md and QUESTIONS.md, and a vocabulary applied to the
# wrong file is a false positive -- the failure mode that gets a check disabled
# (P-35).
VOCAB = (
    ("requirement-status",
     re.compile(r"(^|/)REQUIREMENTS\.md$"),
     re.compile(r"^-\s+\*\*Status\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(open|in-progress \(T-\d+\)|discharged \(T-\d+\)|struck \(D-\d+\))$")),
    ("question-class",
     re.compile(r"(^|/)QUESTIONS\.md$"),
     re.compile(r"^-\s+\*\*Class\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(REVERSIBLE|IRREVERSIBLE|CHARTER)$")),
    ("question-status",
     re.compile(r"(^|/)QUESTIONS\.md$"),
     re.compile(r"^-\s+\*\*Status\.\*\*\s+(.+?)\s*$"),
     re.compile(r"^(open|answered D-\d+|proceeded-unreviewed D-\d+|withdrawn)$")),
    ("task-title",
     re.compile(r"(^|/)tasks/[^/]+\.md$"),
     re.compile(r"^#\s+T-\d+\s*" + DASH + r".*?" + DASH + r"\s*(.+?)\s*$"),
     re.compile(r"^(PLANNED|RUNNING \(.+\)|READY-TO-AUDIT|BLOCKED \(.+\)|DONE \(.+\))$")),
    ("checkpoint-verdict",
     re.compile(r"(^|/)checkpoints/[^/]+\.md$"),
     re.compile(r"^#\s+C-\d+\s*" + DASH + r".*?" + DASH + r"\s*(.+?)\s*$"),
     re.compile(r"^(ON-COURSE|DRIFTED|BLOCKED)$")),
)

LEAKS = (
    (re.compile(r"(?<![\w.~])/(?:home|Users)/[A-Za-z0-9._-]+/"), "an absolute home path"),
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

    for path in files:
        rel = os.path.relpath(path, base)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError as exc:
            findings.append(("unreadable", rel, 0, str(exc)))
            continue

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

            for pre, num in CITATION.findall(line):
                if pre in EXTERNAL or pre not in KNOWN:
                    continue
                cited.setdefault(f"{pre}-{num}", []).append(f"{rel}:{n}")


    bare = {k.split(":", 1)[1] if ":" in k and k.split(":", 1)[1].startswith("S-") else k
            for k in declared}
    for ident, where in sorted(cited.items()):
        if ident not in bare:
            findings.append(("cited-undefined", where[0].split(":")[0],
                             int(where[0].split(":")[-1]), f"{ident} is cited but never declared"))
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
