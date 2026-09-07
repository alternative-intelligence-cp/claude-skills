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
# THE SUBJECT IS OVERRIDABLE SO THAT MUTATION TESTING NEED NOT WRITE THE
# SHIPPED TREE. scripts/mutate.py used to apply each mutation to the real
# file and restore it in a `finally`, which is safe in time and not in the
# tree: a concurrent `git add -A` read check_plugin.py mid-mutation and
# shipped the defect, with this control green in the working tree the whole
# while. Two trees, one report. The window is now removed rather than
# declared -- mutate.py writes a mutated COPY and names it here.
REAL = (os.environ.get("DEVTEAM_SUBJECT_CHECK_PLUGIN")
       or os.path.join(HERE, "check_plugin.py"))

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


def scan():
    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))
    seen = set()
    seen.add("not-an-emit")          # set.add() is a different thing entirely
    add("alpha-finding", "x", "y")
    findings.append(("beta-finding", "x", 0, "y"))
    return findings
'''

# The fixture's docs/CHECKS.md is built with a REGEX over the copied scripts,
# not with check_plugin's own AST walker. A control that derived its expected
# set with the instrument under test would agree with it by construction and
# could never fail -- the vacuous-control shape 0.2.5 caught by mutating.
CHECKS_HEAD = "# Every finding class, and the rule whose two sides it compares\n"


def checks_md(plugin, extra_rows="", drop=()):
    import re as _re
    out = [CHECKS_HEAD]
    for script in ("check_refs.py", "check_plugin.py"):
        path = os.path.join(plugin, "scripts", script)
        if not os.path.isfile(path):
            continue
        src = open(path, encoding="utf-8").read()
        names = []
        for m in _re.finditer(r'(?<![.\w])add\(\s*"([a-z][a-z0-9-]*)"', src):
            if m.group(1) not in names:
                names.append(m.group(1))
        for m in _re.finditer(r'findings\.append\(\(\s*"([a-z][a-z0-9-]*)"', src):
            if m.group(1) not in names:
                names.append(m.group(1))
        out.append(f"\n## `{script}` — {len(names)} classes\n\n")
        out.append("| Class | Rule | The two sides | Verdict |\n|---|---|---|---|\n")
        for n in names:
            if n in drop:
                continue
            out.append(f"| `{n}` | P-1 | one list ↔ the other | `enforces` |\n")
    out.append(extra_rows)
    return "".join(out)

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
    os.makedirs(os.path.join(plugin, "docs"), exist_ok=True)
    w("docs/CHECKS.md", checks_md(plugin))
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
    # DELIBERATELY INVERTED IN 0.2.6. This case used to assert that a
    # three-letter prefix needs no reserving, which was true while the scanner
    # could not see one. Five are now reserved and checked, so the property
    # worth pinning is the opposite: a RESERVED three-letter prefix must be
    # resolved in both directions, and every other one must still be ignored.
    #
    # The reason for keeping the second half is F-63/F-64: widening a grammar
    # without asking what it newly matches turned a green tree into 62
    # `cited-undefined` at once. `UTF-8` alone occurs 639 times in one
    # project's record and matches [A-Z]{3}-\d+ perfectly.
    ("namespace-drift-audit-prefix-reserved-not-recognised",
     lambda p: w(p, "templates/FORMATS.md",
                 FORMATS + "| `COR-` | a correctness finding | audits/ |\n"),
     {"namespace-drift"}),
    ("namespace-drift-audit-prefix-recognised-not-reserved",
     lambda p: w(p, "scripts/check_refs.py",
                 REFS.replace('KNOWN = {"R", "T"}',
                              'KNOWN = {"R", "T"}\nAUDIT = {"COR"}')),
     {"namespace-drift"}),
    ("fp-unreserved-three-letter-prefixes-still-need-no-reserving",
     lambda p: w(p, "templates/FORMATS.md",
                 FORMATS + "\nEncoded UTF-8 per RFC-2119; see ABC-1 and XYZ-9.\n"),
     set()),
    # --- unruled-finding / stale-row (L-6.1, 0.2.6) -----------------------
    # A check is legitimate only when it enforces a rule that exists. These two
    # keep docs/CHECKS.md and the code equal in BOTH directions: a class with
    # no row names no rule, and a row with no class sends a reader looking for
    # a check that is not there.
    ("unruled-finding",
     lambda p: w(p, "docs/CHECKS.md", checks_md(p, drop=("alpha-finding",))),
     {"unruled-finding"}),
    ("unruled-finding-append-arm",
     lambda p: w(p, "docs/CHECKS.md", checks_md(p, drop=("beta-finding",))),
     {"unruled-finding"}),
    ("stale-row",
     lambda p: w(p, "docs/CHECKS.md", checks_md(p) +
                 "| `ghost-finding` | P-1 | nothing ↔ nothing | `enforces` |\n"),
     {"stale-row"}),
    # THE TRIPWIRE. A parser that silently skipped a non-literal class name
    # would handle set.add() and the lambda definition correctly by accident
    # and would ALSO go blind to a genuine emit site written with a computed
    # name -- exactly the class most likely to need a rule. It must fail loudly.
    ("unruled-finding-computed-class-name",
     lambda p: w(p, "scripts/check_refs.py", REFS + '''

def more(kind):
    findings = []
    add = lambda k, w_, d: findings.append((k, w_, d))
    add(kind, "computed", "class name is not a literal")
    return findings
'''),
     {"unruled-finding"}),

    # --- FALSE-POSITIVE TWINS for the above -------------------------------
    # The skip must be real: this control's own fixtures are partial plugin
    # trees, and reporting "CHECKS.md is missing" on a tree with no docs/ at
    # all would be the check answering a question nobody asked (P-35b).
    ("fp-no-docs-directory-skips-the-check",
     lambda p: shutil.rmtree(os.path.join(p, "docs")),
     set()),
    ("fp-a-row-may-carry-any-rule-text",
     lambda p: w(p, "docs/CHECKS.md",
                 checks_md(p).replace("| P-1 |", "| `FORMATS.md` §Whatever |")),
     set()),
    ("fp-set-add-and-the-lambda-are-not-emit-sites",
     lambda p: w(p, "docs/CHECKS.md", checks_md(p)),
     set()),
    # AN ORDINARY LIST APPEND IS NOT AN EMIT SITE, and this case exists because
    # the first draft of the parser accepted ANY `.append((tuple))`. Two real
    # ones -- `out.append((path, n, text))` in check_report and
    # `unparsed.append((rel, n, line))` in check_scope -- then looked like emit
    # sites with a computed class, and the tripwire fired against its own
    # author on its first run. Without this case the mutation that widens the
    # arm back out survives the whole suite: nothing else in the fixture
    # appends a tuple to a list that is not `findings`.
    ("fp-an-ordinary-list-append-is-not-an-emit-site",
     lambda p: w(p, "scripts/check_refs.py", REFS + '''

def collect(paths):
    out = []
    for n, path in enumerate(paths):
        out.append((path, n, "not a finding"))
    return out
'''),
     set()),
    ("fp-rule-cited-in-prose-and-parens",
     lambda p: w(p, "PROTOCOL.md", PROTOCOL + "\nP-1 and P-2 are both cited here.\n"),
     set()),

    # --- A MENTION IS NOT A CITATION (0.2.7) ------------------------------
    # `unknown-rule` read every P-n in a raw body as a citation, so a document
    # REPORTING a rule number could not be committed. It refused a record
    # paragraph that proposed a rule by number -- correctly, FORMATS.md forbids
    # that -- and then refused the paragraph describing the refusal, because
    # describing it means quoting the identifier. Reporting the finding created
    # the finding, and the only remaining move was to disguise the number,
    # which FORMATS.md forbids in the same breath.
    #
    # EACH OF THESE FOUR HAS BEEN SHOWN TO FLIP. 0.2.6's closing finding is
    # that a false-positive twin no mutation can move is decoration, so the
    # mutation that moves each one is named on its case rather than assumed.
    ("fp-a-rule-number-inside-a-fenced-block-is-not-a-citation",
     # flips when: the fence skip is removed.
     # This is the one that resolves the case above, and it resolves it in the
     # direction the house style already prefers -- paste the output that
     # refused you rather than describing it in prose.
     lambda p: w(p, "skills/alpha/SKILL.md", SKILL.format(name="alpha") + '''
An earlier draft proposed a rule by number and was refused:

```
unknown-rule  skills/alpha/SKILL.md  cites P-99, which PROTOCOL.md does not declare
```
'''),
     set()),
    ("fp-a-rule-number-in-quoted-check-output-is-not-a-citation",
     # flips when: the CHECK_OUTPUT blanking is removed.
     # check_refs learned this from a supervisor who reported a finding
     # accurately, inline, and was punished by the scanner for doing so.
     lambda p: w(p, "skills/alpha/SKILL.md", SKILL.format(name="alpha") +
                 "\nIt reported `unknown-rule  PROTOCOL.md:12  cites P-98` and stopped.\n"),
     set()),
    ("fp-the-teaching-form-of-a-rule-number-is-not-a-citation",
     # flips when: the TEACHING skip is removed.
     # Without it the format documentation reports itself, and a check that
     # cries wolf on its own examples is one nobody runs (P-35).
     lambda p: w(p, "templates/FORMATS.md", FORMATS +
                 "\nCite a protocol rule as `P-<n>`, so P-97 in a table header reads as a form.\n"),
     set()),
    # THE EXEMPTIONS MUST NOT SWALLOW THE FINDING, and this is the case that
    # says so. A fence skip written per FILE rather than per LINE would make
    # every document containing one fenced example blind to every citation
    # under it -- the exemption eating the check, which is the shape FORMATS.md
    # names: a thing exempted from a checker for its own protection is a thing
    # the checker cannot see. Here the fenced P-99 is quoted and the prose
    # P-96 four lines later is a real citation, in ONE file.
    ("unknown-rule-still-fires-in-prose-below-an-exempt-fence",
     lambda p: w(p, "skills/alpha/SKILL.md", SKILL.format(name="alpha") + '''
```
unknown-rule  somewhere.md  cites P-99, which PROTOCOL.md does not declare
```

This step is required by P-96.
'''),
     {"unknown-rule"}),
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
