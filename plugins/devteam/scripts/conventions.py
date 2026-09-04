#!/usr/bin/env python3
"""Project-family conventions: rules stated once, surfaced for confirmation.

A family of projects shares constraints that no single project's charter is
the natural home for — a toolchain that is required or forbidden, a coding
standard, a verification obligation, where the shared resources live. Restating
them at every onboarding is a memory tax, and the tax is paid by the person
least able to afford it: the one who already knows and has to remember to say.

**Everything here was STATED, never inferred.** A convention is something the
client said applies to a family. It is not a pattern noticed in their
decisions, because a pattern is a hypothesis that grows more confident with
repetition whether or not it is true — and it would be most confident exactly
where a genuine exception costs most.

**A convention is a QUESTION, not a default.** `onboard` lists the matching
ones and the client confirms or declines each, one at a time. A declined
convention is recorded with its reason, because "this project deliberately does
not follow the house rule" is information and an unnoticed omission is not.

Conventions live in $DEVTEAM_CONVENTIONS, or ~/.devteam/conventions/, one
markdown file each. They are the OPERATOR's: they span projects, so no single
project's client owns them, and they are meant to be read and edited by hand.

Usage:
  conventions.py list                       every convention, with what it applies to
  conventions.py match <project> [tag ...]  those applying to a path and/or tags
  conventions.py new <id>                   print a template to fill in
"""
import fnmatch
import os
import re
import sys

HOME = os.path.expanduser(
    os.environ.get("DEVTEAM_CONVENTIONS") or "~/.devteam/conventions")

TITLE = re.compile(r"^#\s+(CNV-\d+)\s+[—–-]\s+(.+?)\s*$", re.M)
FIELD = re.compile(r"^-\s+\*\*([A-Za-z][A-Za-z ]*)\.\*\*\s*(.*)$", re.M)

TEMPLATE = """# {id} — <the rule, as a claim, in one line>

- **Applies to.** <path globs and/or tags, comma separated — e.g. `~/work/proj*`, tag `alpha`>
- **Kind.** requirement | prohibition | resource | standard
- **Priority.** <safety | correctness | performance | none — from the family's
  priority order. A `safety` convention cannot be declined casually: doing so
  is a CHARTER question and the reason goes on the record>
- **Rule.** <what must or must not be true, stated normatively>
- **Because.** <the reason. A convention without one gets declined by whoever
  meets it and cannot argue with it>
- **Stated.** <YYYY-MM-DD> by <who>
"""


def parse(path):
    try:
        body = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = TITLE.search(body)
    if not m:
        return None
    fields = {k.strip(): v.strip() for k, v in FIELD.findall(body)}
    applies = fields.get("Applies to", "")
    globs = [g.strip().strip("`") for g in re.split(r"[,;]", applies)
             if g.strip() and not g.strip().lower().startswith("tag ")]
    tags = [t.strip().strip("`") for t in re.findall(r"tag\s+`?([\w-]+)`?", applies)]
    return {
        "id": m.group(1), "title": m.group(2),
        "kind": fields.get("Kind", "unstated"),
        "priority": fields.get("Priority", "unstated").strip().lower(),
        "rule": fields.get("Rule", ""),
        "because": fields.get("Because", ""),
        "stated": fields.get("Stated", ""),
        "globs": [g for g in globs if g], "tags": tags, "path": path,
    }


def load():
    out = []
    if not os.path.isdir(HOME):
        return out
    for f in sorted(os.listdir(HOME)):
        if f.endswith(".md"):
            c = parse(os.path.join(HOME, f))
            if c:
                out.append(c)
    return out


def matches(c, project, tags):
    if any(t in c["tags"] for t in tags):
        return True
    real = os.path.realpath(os.path.expanduser(project)) if project else None
    for g in c["globs"]:
        g = os.path.realpath(os.path.expanduser(g)) if not any(
            ch in g for ch in "*?[") else os.path.expanduser(g)
        if real and (fnmatch.fnmatch(real, g) or fnmatch.fnmatch(real, g + "/*")
                     or real.startswith(g.rstrip("/") + os.sep) or real == g):
            return True
    return False


def show(cs):
    if not cs:
        print("no conventions match")
        return
    for c in cs:
        flag = "  ** SAFETY **" if c["priority"].startswith("safety") else ""
        print(f"\n  {c['id']} — {c['title']}{flag}")
        print(f"    kind: {c['kind']}   priority: {c['priority']}   stated: {c['stated']}")
        if c["rule"]:
            print(f"    rule: {c['rule'][:150]}")
        if c["because"]:
            print(f"    because: {c['because'][:150]}")
        print(f"    {c['path']}")
    print("\n  These are QUESTIONS, not defaults. Put each to the client and record")
    print("  the answer either way — a declined convention is a decision, and an")
    print("  unnoticed one is an omission.")
    if any(c["priority"].startswith("safety") for c in cs):
        print("\n  One or more is a SAFETY convention. Declining one is a CHARTER")
        print("  question (P-26): it stops for the client, it needs a stated reason")
        print("  naming what makes THIS project different, and the reason goes on")
        print("  the record. Do not let it pass as an ordinary preference.")


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().split("Usage:")[-1].strip(), file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd == "list":
        show(load())
        return 0
    if cmd == "match":
        if len(argv) < 3:
            print("conventions.py match <project> [tag ...]", file=sys.stderr)
            return 2
        cs = [c for c in load() if matches(c, argv[2], argv[3:])]
        show(cs)
        return 0 if cs else 1
    if cmd == "new":
        if len(argv) < 3 or not re.fullmatch(r"CNV-\d+", argv[2]):
            existing = [int(c["id"].split("-")[1]) for c in load()]
            suggest = f"CNV-{max(existing) + 1 if existing else 1}"
            print(f"conventions.py new <id>   (next free id looks like {suggest})",
                  file=sys.stderr)
            return 2
        print(TEMPLATE.format(id=argv[2]))
        print(f"# save as {os.path.join(HOME, argv[2] + '.md')}", file=sys.stderr)
        return 0
    print(f"conventions.py: unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
