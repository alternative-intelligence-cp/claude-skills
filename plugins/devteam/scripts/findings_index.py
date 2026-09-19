#!/usr/bin/env python3
"""One index of every finding the roadmap holds, generated rather than kept.

Findings sit in the roadmap's subcycle files, one `## Findings` section each.
Planning a round means reading every one of them, which is the "hunt all over
for them" cost this exists to remove. (No count is given here: a count in a
docstring is a number nothing verifies, and it was already stale once.)

**It is generated, never maintained.** A hand-written index is exactly the rule
a rushed session skips: it goes stale the first time somebody closes a cycle in
a hurry, and a stale index is worse than none because it still looks current.
Re-run this instead.

**The index holds POINTERS, not findings.** Title, file, line — enough to decide
whether an entry is worth opening, and nothing you could mistake for the entry
itself. Same reasoning as `research_index.py`: an index carrying the content
would be a second home for a fact, it would go stale silently, and it would be
read in preference to the source precisely because it is more convenient.

**TWO FORMATS EXIST AND A SCANNER THAT KNOWS ONE SILENTLY DROPS TWO FILES.**
`0.2.0` and `0.2.1` write findings as top-level `- **bold lead-in.**` bullets;
`0.2.2` onward use `### ` headings. Keying only on `###` returns zero for those
two files, which is indistinguishable from "that subcycle found nothing" — the
false negative this tool would exist to prevent. So the format is detected per
file, and **anything under a `## Findings` heading that matches neither shape is
REPORTED, never skipped quietly.**

Usage:
  findings_index.py <roadmap-dir> [--out FILE]

The devteam plugin's own index is generated with
  python3 scripts/findings_index.py meta/roadmap --out meta/FINDINGS-INDEX.md
run from the plugin's root. The output lives OUTSIDE the directory it scans,
or the next run would list the index itself as a subcycle with no findings.

Exit 0 with an index on stdout (or at --out). Exit 1 if any Findings section
could not be parsed at all — a loud failure, because the quiet version is a
subcycle that reads as having learned nothing.
"""
import os
import re
import sys

# A finding's heading in the `###` format. `####` is a subsection WITHIN a
# finding and must not be collected as one, so the count is anchored.
H3 = re.compile(r"^###\s+(?!#)(.+?)\s*$")
# The bullet format, top-level only. A nested bullet is detail inside a
# finding; a top-level one IS the finding. Column 0 is the whole distinction.
BULLET = re.compile(r"^-\s+\*\*(.+?)\*\*")
# Where a Findings section starts and what ends it.
FINDINGS = re.compile(r"^##\s+Findings\s*$")
SECTION = re.compile(r"^##\s+(?!#)")


def strip_md(s):
    """Flatten inline markdown so an index line reads as a sentence."""
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]*)\*", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s.strip().rstrip(".")


def findings_of(path):
    """(entries, unparsed, had_section) for one file.

    `entries` is [(line_no, title)]. `unparsed` is [(line_no, text)] for lines
    inside the section that look like they were meant to be something and were
    not recognised — returned rather than discarded, because a silent skip is a
    false negative on the one lookup this tool exists for.
    """
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except OSError as e:
        return [], [(0, f"unreadable: {e}")], False

    start = None
    for i, line in enumerate(lines):
        if FINDINGS.match(line):
            start = i + 1
            break
    if start is None:
        return [], [], False

    end = len(lines)
    for i in range(start, len(lines)):
        if SECTION.match(lines[i]):
            end = i
            break

    body = lines[start:end]
    # Format detection, per file. A `###` anywhere in the section means this
    # file uses headings, and its top-level bullets are detail rather than
    # findings. Without this, a modern file yields dozens of spurious entries.
    uses_h3 = any(H3.match(l) for l in body)

    entries, unparsed = [], []
    in_fence = False
    for off, line in enumerate(body):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        n = start + off + 1
        if uses_h3:
            m = H3.match(line)
            if m:
                entries.append((n, strip_md(m.group(1))))
        else:
            m = BULLET.match(line)
            if m:
                entries.append((n, strip_md(m.group(1))))

    if not entries:
        # The section exists and yielded nothing. That is either an empty
        # section or a third format nobody has told this tool about, and the
        # two must not look the same.
        text = "\n".join(body).strip()
        if text:
            unparsed.append((start + 1, "section has content but no recognised "
                                        "finding entries (a third format?)"))
    return entries, unparsed, True


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = argv[0]
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]

    if not os.path.isdir(root):
        print(f"findings_index: not a directory: {root}", file=sys.stderr)
        return 2

    files = []
    for dirpath, _, names in os.walk(root):
        for n in sorted(names):
            if n.endswith(".md") and n != "README.md":
                files.append(os.path.join(dirpath, n))
    files.sort()

    lines = ["# Findings index",
             "",
             "**Generated by `findings_index.py`. Do not edit — re-run it.**",
             "",
             "Pointers only. Open the subcycle file for the finding itself; an",
             "index that carried the content would be a second home for a fact.",
             ""]

    total, no_section, problems = 0, [], []
    for path in files:
        entries, unparsed, had = findings_of(path)
        rel = os.path.relpath(path, root)
        if not had:
            no_section.append(rel)
            continue
        for n, text in unparsed:
            problems.append(f"{rel}:{n}  {text}")
        if not entries:
            continue
        lines.append(f"## {rel}  ({len(entries)})")
        lines.append("")
        for n, title in entries:
            lines.append(f"- `{rel}:{n}` — {title}")
        lines.append("")
        total += len(entries)

    lines.insert(6, f"**{total} findings across "
                    f"{len(files) - len(no_section)} subcycle files.**")
    lines.insert(7, "")

    if no_section:
        lines += ["## Files with no `## Findings` section", ""]
        lines += [f"- `{r}`" for r in no_section] + [""]

    if problems:
        lines += ["## UNPARSED — a section this tool could not read", "",
                  "**Each line is a subcycle whose findings are missing from",
                  "the index above.** Fix the source or teach the parser; do",
                  "not ignore it.", ""]
        lines += [f"- {p}" for p in problems] + [""]

    text = "\n".join(lines)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"findings_index: {total} findings -> {out}")
    else:
        print(text)

    if problems:
        print(f"findings_index: {len(problems)} unparsed section(s)",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
