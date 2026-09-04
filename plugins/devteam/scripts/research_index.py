#!/usr/bin/env python3
"""A cross-project index of research digests.

A digest written for one project is invisible to every other, so the same
question gets paid for twice. This indexes them — and indexes them as
POINTERS, never as answers.

**The index holds no facts.** Topic, question, date, sensitivity, sources and
the path: enough to decide whether a digest is worth opening, and nothing you
could mistake for the digest itself. That is deliberate. An index that carried
the answer would be a second home for a fact (P-34), it would go stale
silently, and it would be read in preference to the digest precisely because
it is more convenient — which is how a cached wrong answer outlives the
document that corrected it.

**A hit is a lead, not an answer** (P-36's rule about sources, applied to our
own files). Open the digest, check its date, and re-verify anything stale
against its primary source. The tool prints that on every query because the
whole failure mode is somebody skipping it.

Usage:
  research_index.py build <root> [<root> ...]   scan for devteam/research/*.md
  research_index.py query <term> [<term> ...]   search the index
  research_index.py stale                       everything past its shelf life

The index lives at $DEVTEAM_RESEARCH_INDEX, or ~/.devteam/research-index.json.
It is the OPERATOR's file, not a project's (P-38): it spans projects, so no
single project's client owns it.
"""
import json
import os
import re
import sys
from datetime import date, datetime

DEFAULT = os.path.expanduser(
    os.environ.get("DEVTEAM_RESEARCH_INDEX") or "~/.devteam/research-index.json")

TITLE = re.compile(r"^#\s+(.*?)\s+[—–-]\s+research digest\s*$", re.M)
ASOF = re.compile(r"\*\*As of\s+(\d{4}-\d{2}-\d{2})\.?\*\*")
QUESTION = re.compile(r"Question:\s*(.+?)\s*$", re.M)
SENSITIVITY = re.compile(r"\*\*Sensitivity\.\*\*\s*(routine|security)", re.I)
URL = re.compile(r"https?://[^\s<>\)\"]+")

SHELF = {"security": 90, "routine": 180}


def parse(path):
    """(entry, None) for a digest, or (None, reason) for anything else.

    The reason is returned rather than discarded because a silent skip here is
    a FALSE NEGATIVE on the one lookup meant to prevent duplicate work: the
    searcher is told nothing exists and pays again for research filed one
    directory away. A project with three digests and one title typo used to be
    indistinguishable from a project with two.
    """
    try:
        body = open(path, encoding="utf-8").read()
    except OSError as exc:
        return None, f"unreadable: {exc}"
    title = TITLE.search(body)
    asof = ASOF.search(body)
    # A NEAR MISS carries one of the two markers: somebody was writing a digest
    # and got the shape wrong. A file with neither was never trying to be one.
    # The distinction decides whether it is named or merely counted -- listing
    # every markdown file in every research directory on a machine is a report
    # nobody reads, which is the same failure as saying nothing.
    if not title and not asof:
        return None, None
    if not title:
        return None, "has an `As of` line but no `# <topic> — research digest` heading"
    if not asof:
        return None, "is titled as a digest but has no `**As of <date>.**` line, so it cannot be aged"
    sens = SENSITIVITY.search(body)
    q = QUESTION.search(body)
    return {
        "topic": title.group(1).strip(),
        "question": (q.group(1).strip() if q else ""),
        "as_of": asof.group(1),
        "sensitivity": (sens.group(1).lower() if sens else "unstated"),
        "sources": sorted(set(URL.findall(body)))[:8],
        "path": path,
    }, None


SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
             "build", "dist", "target", ".tox", ".mypy_cache"}


def owning_project(path):
    """The nearest ancestor that is a repository, else the parent of research/."""
    cur = os.path.dirname(path)
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.dirname(os.path.dirname(path))
        cur = parent


def scan(roots):
    """Every `research/` directory under the roots, at any depth.

    THE SHAPE IS THE GATE, NOT THE PATH. An earlier version matched only
    `devteam/research`, which meant a properly written digest filed under a
    different convention -- `meta/research/`, say -- was invisible. The parser
    already rejects anything that is not a digest, so the directory name buys
    nothing and costs reach. A document with no `As of` line is skipped
    wherever it lives, because a digest that cannot be dated cannot be aged,
    and an entry that cannot be aged is worse than an absent one.
    """
    out, skipped, seen, ignored = [], [], set(), 0
    for root in roots:
        root = os.path.realpath(os.path.expanduser(root))
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.basename(base) != "research":
                continue
            # A `research/` directory holding a SKILL.md is a skill, not a
            # corpus -- the widened path match found the research SKILL itself.
            if "SKILL.md" in files:
                continue
            project = owning_project(base)
            for f in sorted(files):
                if not f.endswith(".md") or f in ("CURRENCY.md", "README.md"):
                    continue
                path = os.path.realpath(os.path.join(base, f))
                if path in seen:
                    continue
                d, why = parse(path)
                seen.add(path)
                if d:
                    d["project"] = os.path.basename(project)
                    out.append(d)
                elif why:
                    skipped.append((path, why))
                else:
                    ignored += 1
    return out, skipped, ignored


def age(entry):
    try:
        return (date.today() - datetime.strptime(entry["as_of"], "%Y-%m-%d").date()).days
    except ValueError:
        return None


def shelf_state(entry):
    days = age(entry)
    if days is None:
        return "undated"
    limit = SHELF.get(entry["sensitivity"])
    if limit is None:
        # An unstated sensitivity cannot be aged against a shelf life, so it is
        # reported as unknown rather than silently treated as routine -- the
        # cautious default would be the one that hides a stale security digest.
        return f"{days}d, sensitivity unstated"
    return f"{days}d, STALE (>{limit}d for {entry['sensitivity']})" if days > limit \
        else f"{days}d, fresh"


def load():
    try:
        return json.load(open(DEFAULT, encoding="utf-8"))
    except (OSError, ValueError):
        return {"roots": [], "digests": []}


def show(entries):
    if not entries:
        print("no digests match")
        return
    for e in entries:
        print(f"\n  {e['topic']}   [{e['project']}]")
        print(f"    {shelf_state(e)}   as of {e['as_of']}")
        if e["question"]:
            print(f"    Q: {e['question'][:100]}")
        print(f"    {e['path']}")
    print("\n  A hit is a LEAD, not an answer. Open the digest, check its date,")
    print("  and re-verify anything stale at its primary source before citing it.")


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().split("Usage:")[-1].strip(), file=sys.stderr)
        return 2
    cmd = argv[1]

    if cmd == "build":
        roots = argv[2:] or load().get("roots") or []
        if not roots:
            print("research_index: no roots given and none remembered", file=sys.stderr)
            return 2
        digests, skipped, ignored = scan(roots)
        os.makedirs(os.path.dirname(DEFAULT), exist_ok=True)
        json.dump({"roots": roots, "built": date.today().isoformat(),
                   "digests": digests}, open(DEFAULT, "w", encoding="utf-8"), indent=2)
        print(f"indexed {len(digests)} digest(s) from {len(roots)} root(s) -> {DEFAULT}")
        if ignored:
            print(f"({ignored} other file(s) in research/ directories are not "
                  "digests and were not trying to be)")
        if skipped:
            # Named, not counted. A skipped digest is invisible to the lookup
            # that exists to stop the next project paying for it again, so the
            # report says WHAT was ignored and WHY -- not merely how many
            # succeeded.
            print(f"\nNEAR MISSES — {len(skipped)} file(s) that look like an "
                  "attempted digest and did not parse:")
            for path, why in skipped:
                print(f"  {path}\n      {why}")
            print("\n  If one of these was meant to be a digest, it is currently "
                  "invisible to `query`\n  and the next project will pay for it "
                  "again.")
        return 0

    idx = load()
    if cmd == "query":
        terms = [t.lower() for t in argv[2:]]
        if not terms:
            print("research_index: query needs a term", file=sys.stderr)
            return 2
        hits = [e for e in idx["digests"]
                if all(t in " ".join([e["topic"], e["question"],
                                      " ".join(e["sources"])]).lower() for t in terms)]
        show(hits)
        return 0 if hits else 1

    if cmd == "stale":
        hits = [e for e in idx["digests"] if "STALE" in shelf_state(e)]
        show(hits)
        return 1 if hits else 0

    print(f"research_index: unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
