#!/usr/bin/env python3
"""Negative control for check_plugin.py (P-35).

Written because check_plugin.py excludes itself from its own
`uncontrolled-check` scan, and a check that exempts itself from the rule it
enforces is precisely what an auditor is supposed to find.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
REAL = os.path.join(HERE, "check_plugin.py")

PROTOCOL = "# The protocol\n\n**P-1 — first rule.** Because.\n\n**P-2 — second rule.** Because.\n"
SKILL = """---
name: {name}
description: A fixture skill that does a thing, cited as (P-1).
---

# {name}

Run `python3 ${{CLAUDE_PLUGIN_ROOT}}/scripts/check_thing.py` and read
[the protocol](../../PROTOCOL.md).
"""
FORMATS = """# The formats

| Prefix | Numbers | Declared in |
|---|---|---|
| `R-` | a requirement | REQUIREMENTS.md |
| `T-` | a task | tasks/ |
| `P-` | a protocol rule | external |
"""

REFS = '''# a scanner
KNOWN = {"R", "T"}
EXTERNAL = {"P"}
'''

AGENT = """---
name: {name}
description: A fixture agent.
skills: [{skills}]
tools: Read
model: inherit
---
You are a fixture (P-2).
"""


def build(mutate=None):
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-plugincheck-"))
    plugin = os.path.join(root, "plugins", "devteam")
    for d in ("skills/alpha", "agents", "scripts", "templates", ".claude-plugin"):
        os.makedirs(os.path.join(plugin, d), exist_ok=True)
    w = lambda p, b: open(os.path.join(plugin, p), "w", encoding="utf-8").write(b)
    w("PROTOCOL.md", PROTOCOL)
    w("skills/alpha/SKILL.md", SKILL.format(name="alpha"))
    w("agents/runner.md", AGENT.format(name="runner", skills="alpha"))
    w("scripts/check_thing.py", "# a check\n")
    w("scripts/test_check_thing.py", "# its control\n")
    w("templates/FORMATS.md", FORMATS)
    w("scripts/check_refs.py", REFS)
    w("scripts/test_check_refs.py", "# its control\n")
    w(".claude-plugin/plugin.json", json.dumps({"name": "devteam", "version": "0.1.0"}))
    shutil.copy2(REAL, os.path.join(plugin, "scripts", "check_plugin.py"))
    if mutate:
        mutate(plugin)
    return root, plugin


def w(plugin, p, b):
    path = os.path.join(plugin, p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(b)


CASES = [
    ("clean", None, set()),
    ("missing-skill",
     lambda p: w(p, "agents/runner.md", AGENT.format(name="runner", skills="nowhere")),
     {"missing-skill"}),
    ("name-mismatch",
     lambda p: w(p, "skills/alpha/SKILL.md", SKILL.format(name="beta")),
     {"name-mismatch"}),
    ("bad-frontmatter",
     lambda p: w(p, "skills/alpha/SKILL.md", "# no frontmatter here\n"),
     {"bad-frontmatter"}),
    ("missing-script",
     lambda p: os.remove(os.path.join(p, "scripts/check_thing.py")),
     {"missing-script"}),
    ("unknown-rule",
     lambda p: w(p, "agents/runner.md",
                 AGENT.format(name="runner", skills="alpha").replace("(P-2)", "(P-99)")),
     {"unknown-rule"}),
    ("uncontrolled-check",
     lambda p: os.remove(os.path.join(p, "scripts/test_check_thing.py")),
     {"uncontrolled-check"}),
    ("broken-link",
     lambda p: w(p, "skills/alpha/SKILL.md",
                 SKILL.format(name="alpha").replace("../../PROTOCOL.md", "../../GONE.md")),
     {"broken-link"}),
    ("bad-manifest",
     lambda p: w(p, ".claude-plugin/plugin.json", json.dumps({"name": "wrong-name"})),
     {"bad-manifest"}),
    ("bad-manifest-unparseable",
     lambda p: w(p, ".claude-plugin/plugin.json", "{not json"),
     {"bad-manifest"}),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    ("fp-agent-with-no-skills-field",
     lambda p: w(p, "agents/runner.md",
                 AGENT.format(name="runner", skills="alpha").replace("skills: [alpha]\n", "")),
     set()),
    ("fp-external-links-are-not-checked",
     lambda p: w(p, "skills/alpha/SKILL.md",
                 SKILL.format(name="alpha") + "\nSee [docs](https://example.com/x).\n"),
     set()),
    ("fp-anchor-only-link",
     lambda p: w(p, "skills/alpha/SKILL.md",
                 SKILL.format(name="alpha") + "\nSee [below](#alpha).\n"),
     set()),
    ("fp-several-agents-share-one-skill",
     lambda p: w(p, "agents/second.md", AGENT.format(name="second", skills="alpha")),
     set()),
    # The reserved-prefix table and the scanner's sets are two lists of the
    # same thing. Three collisions in one project came from a prefix nobody
    # had reserved, so the two are diffed rather than trusted to agree.
    ("namespace-drift-table-ahead-of-scanner",
     lambda p: w(p, "templates/FORMATS.md", FORMATS + "| `XY-` | a new thing | somewhere |\n"),
     {"namespace-drift"}),
    ("namespace-drift-scanner-ahead-of-table",
     lambda p: w(p, "scripts/check_refs.py", REFS.replace('{"R", "T"}', '{"R", "T", "ZZ"}')),
     {"namespace-drift"}),
    ("fp-three-letter-prefixes-do-not-need-reserving",
     lambda p: w(p, "templates/FORMATS.md",
                 FORMATS + "\nAudit findings use `COR-n`, `SEC-n`, `HYG-n`.\n"),
     set()),
    ("fp-rule-cited-in-prose-and-parens",
     lambda p: w(p, "PROTOCOL.md", PROTOCOL + "\nP-1 and P-2 are both cited here.\n"),
     set()),
]


def main():
    passed = failed = 0
    for name, mutate, expected in CASES:
        root, plugin = build(mutate)
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(plugin, "scripts", "check_plugin.py")],
                capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (\S+)", proc.stdout, re.M)}
            want_exit = 1 if expected else 0
            if got == expected and proc.returncode == want_exit:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} exit {want_exit}")
                print(f"        got      {sorted(got) or 'clean'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n")[:6]:
                    print(f"        | {line}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "clean")
    print(f"\ncheck_plugin control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
