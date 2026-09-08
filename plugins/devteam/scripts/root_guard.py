#!/usr/bin/env python3
"""Refuse a write that would create a new entry at THIS repository's root.

The stated pain: a root that fills with temporary scripts until the README sits
pages down the GitHub file tree, and every clean-up means stopping work.

THREE MECHANISMS COVER THE ROOT AND THEY CATCH DIFFERENT THINGS. `.gitignore`
keeps a root-level `*.py` off the remote, and shows nothing in `git status`, so
it is invisible locally. `check_plugin.py` reports everything else, after the
fact, with an exit code a release step can read. THIS refuses the write at the
moment it is typed, which is where guidance works -- a refusal that arrives
when somebody is about to do the thing is worth more than a finding they read
later (DESIGN 20b), so the message names where the file SHOULD go.

THE ALLOWLIST IS NOT HERE. It is the table in the root README, read at hook
time, and `root_allowlist()` below is the one parser for it -- `check_plugin.py`
imports this function rather than writing a second one. Two parsers of one table
can disagree, and a hook that refuses what the check calls fine is worse than
either alone.

SCOPE, DELIBERATELY NARROW. Only a write whose resolved target sits DIRECTLY in
this repository's root is judged. Reads are never judged. `cd` is not judged.
Every write below the root -- `plugins/`, `.internal/`, anywhere -- is somebody
else's business: during a run it is the devteam guard's, and otherwise it is the
author's.

FAILS OPEN, ON PURPOSE. If the README or its table is missing, or the target
cannot be resolved (an unexpanded `"$VAR"`, inherited from guard.py's resolver
and stated again here), nothing is refused. This is guidance rather than
containment -- the tree it protects is a file listing, not anyone's work -- and
a guard that refuses on a parse failure is a guard that gets switched off.
`check_plugin.py` announces the same missing table as a SKIP, so the gap is
reported by the mechanism that can afford to be loud.

NOT REGISTERED IN THE PLUGIN'S hooks.json. That file loads into every project
that installs devteam, and this rule is this repository's alone. It goes in
`.claude/settings.json` at the root, which the operator applies (P-38).

Exit 0 always; a refusal is the JSON on stdout, not a status.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))

# The section ends at the next `## ` or at end of file. Anchoring only on a
# following heading would make both readers silently stop seeing the table if
# it were ever moved last in the file.
ROOT_SECTION = re.compile(r"^## What is in this repository\n(.*?)(?=^## |\Z)", re.S | re.M)
ROOT_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|", re.M)

REFUSAL = (
    "{name} is not listed in README.md's root table, and the repository root "
    "is an allowlist.\n"
    "A temporary script, probe or experiment belongs in .internal/scratch/ "
    "(or this session's scratchpad), which is ignored.\n"
    "If it is a permanent part of the repository, add its row to README.md's "
    "\"What is in this repository\" table in the same change that creates it."
)


def root_allowlist(repo):
    """Names permitted directly at `repo`'s root, or None if undeclared.

    None and the empty set are different answers and the caller must keep them
    apart: None means no table was found, which is not a statement that the
    root should be empty. Collapsing them would make a missing README refuse
    every write at the root -- the loudest possible response to the quietest
    possible cause.

    A trailing slash is how a directory is written for a reader; neither git
    nor a filesystem path carries one. It is stripped here so the table can be
    written in the shape a person expects.
    """
    readme = os.path.join(repo, "README.md")
    try:
        body = open(readme, encoding="utf-8").read()
    except OSError:
        return None
    m = ROOT_SECTION.search(body)
    if not m:
        return None
    return {r.rstrip("/") for r in ROOT_ROW.findall(m.group(1))}


def judge_root(target, allowed, repo=None):
    """A refusal reason, or None. `target` is absolute and real, or None.

    `repo` is a parameter rather than the module constant so the control can
    judge a throwaway tree. A guard testable only against the tree it guards
    is one whose control has to mutate that tree, which is the window
    PAIRS row 12 removed.
    """
    if target is None or allowed is None:
        return None
    parent = os.path.dirname(target)
    if os.path.realpath(parent) != os.path.realpath(repo or REPO):
        return None
    name = os.path.basename(target)
    if not name or name in allowed:
        return None
    return REFUSAL.format(name=name)


def main():
    if (os.environ.get("DEVTEAM_ROOT_GUARD") or "").lower() in ("off", "0", "false"):
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Bash", "Write", "Edit", "NotebookEdit"):
        return 0

    allowed = root_allowlist(REPO)
    if allowed is None:
        return 0

    # Imported HERE rather than at module scope: `root_allowlist` is the one
    # parser of the root table and `check_plugin.py` imports it, so this module
    # must load without guard.py present in the tree beside it.
    sys.path.insert(0, HERE)
    from guard import targets, resolve, strip_heredocs

    cwd = os.path.realpath(data.get("cwd") or os.getcwd())
    ti = data.get("tool_input") or {}
    reason = None
    if data["tool_name"] == "Bash":
        # A newline separates commands as surely as `;`, and a heredoc BODY is
        # data rather than command -- both inherited from guard.py, which
        # learned each the expensive way.
        cmd = strip_heredocs(ti.get("command") or "").replace("\n", " ; ")
        for target, _what, category in targets(cmd, cwd):
            if category != "write":
                continue
            reason = judge_root(target, allowed)
            if reason:
                break
    else:
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        reason = judge_root(resolve(path, cwd), allowed)

    if reason is None:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
