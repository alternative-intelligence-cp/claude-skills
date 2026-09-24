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
    # check_plugin imports the root table's ONE parser from root_guard rather
    # than carrying a second copy, so the throwaway tree needs it beside the
    # check. Absent, check_plugin degrades to a reported SKIP rather than
    # crashing -- but a control running against the degraded path would be
    # testing the fallback and calling it the check.
    shutil.copy2(os.path.join(HERE, "root_guard.py"),
                 os.path.join(plugin, "scripts", "root_guard.py"))
    # Every check ends in result.py's contract (roadmap 0.3.1, L-1.1) and
    # imports it, so the throwaway tree needs it too. Unlike root_guard there
    # is no degraded path: without it the check cannot start at all.
    shutil.copy2(os.path.join(HERE, "result.py"),
                 os.path.join(plugin, "scripts", "result.py"))
    os.makedirs(os.path.join(plugin, "docs"), exist_ok=True)
    w("docs/CHECKS.md", checks_md(plugin))
    if mutate:
        mutate(plugin)
    return root, plugin


def w(plugin, p, b):
    path = os.path.join(plugin, p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(b)


def roadmap(plugin, files):
    """Lay down a roadmap tree. `files` maps a path under `meta/roadmap/` to
    the file's TITLE LINE, because the title line is the whole of what the
    state convention reads (meta/roadmap/README.md)."""
    for rel, title in files.items():
        w(plugin, os.path.join("meta", "roadmap", *rel.split("/")),
          title + "\n\nBody, which the check never reads.\n")


def root_tree(plugin, rows, tracked=(), untracked=(), gitignore=None):
    """Make the throwaway root a git repository carrying a README root table.

    check_plugin's root check diffs WHAT GIT WOULD PUBLISH against the README's
    table, so a control needs both sides real: an actual repository with an
    actual commit, and a table to diff it against. Faking either side would
    test the parser and not the check.

    Built in the scratch tree and NEVER against this repository. A control that
    mutates the tree it is checking is exactly the window PAIRS row 12 removed:
    a concurrent `git add` reads the mutated state and ships it while the
    control, run in the working tree, reports green.
    """
    root = os.path.normpath(os.path.join(plugin, "..", ".."))
    if gitignore is not None:
        open(os.path.join(root, ".gitignore"), "w", encoding="utf-8").write(gitignore)
    for name in tracked:
        open(os.path.join(root, name), "w", encoding="utf-8").write("tracked\n")
    body = ["# fixture", "", "## What is in this repository", "",
            "| Entry | What |", "|---|---|"]
    body += [f"| `{r}` | a row |" for r in rows]
    open(os.path.join(root, "README.md"), "w", encoding="utf-8").write("\n".join(body) + "\n")
    git = lambda *a: subprocess.run(["git", "-C", root] + list(a),
                                    capture_output=True, text=True, check=True)
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("-c", "user.name=control", "-c", "user.email=control@example.invalid",
        "commit", "-qm", "fixture")
    # Untracked entries are written AFTER the commit, which is what makes them
    # untracked. Written before, `add -A` would take them and the case would
    # silently become the tracked one.
    for name in untracked:
        open(os.path.join(root, name), "w", encoding="utf-8").write("untracked\n")


# The root table's own rows for a bare fixture: `git add -A` takes the README
# and the plugin tree, and nothing else exists unless a case makes it.
BARE_ROOT = ["README.md", "plugins/"]


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

    ("stranded-done-subcycle",
     lambda p: roadmap(p, {"0.9/0.9.1.md": "# 0.9.1 — a thing — DONE (2026-01-01)"}),
     {"stranded-done-subcycle"}),
    ("undone-subcycle-in-done",
     lambda p: roadmap(p, {"done/0.9.1.md": "# 0.9.1 — a thing — PLANNED"}),
     {"undone-subcycle-in-done"}),
    ("subcycle-without-state",
     lambda p: roadmap(p, {"0.9/0.9.1.md": "# 0.9.1 — a title naming no state at all"}),
     {"subcycle-without-state"}),

    # --- FALSE-POSITIVE CONTROLS ------------------------------------------
    # The pair in its correct arrangement. Without this the three above are
    # satisfied by a check that fires on every subcycle file it sees.
    ("fp-subcycles-in-their-right-places",
     lambda p: roadmap(p, {"done/0.9.1.md": "# 0.9.1 — shipped — DONE (2026-01-01)",
                           "0.9/0.9.2.md": "# 0.9.2 — next — PLANNED"}),
     set()),
    ("fp-a-cycle-readme-is-not-a-subcycle",
     lambda p: roadmap(p, {"0.9/README.md": "# Cycle 0.9 — the map"}),
     set()),
    # STOPPED is NOT DONE, and the convention moves only what reached DONE.
    # A check that swept every finished-looking file into done/ would be
    # enforcing a rule nobody wrote.
    ("fp-stopped-stays-beside-its-cycle",
     lambda p: roadmap(p, {"0.9/0.9.1.md": "# 0.9.1 — abandoned — STOPPED (2026-01-01, superseded)"}),
     set()),
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
    # THE ROOT TREE AGAINST THE README'S TABLE (0.2.10). Two mechanisms cover
    # the root and they catch different things, so both halves are controlled:
    # the check reports a stray, and stays SILENT about the one `.gitignore`
    # already handles. A check that reported what the ignore rule handles is a
    # check that gets switched off.
    ("fp-root-table-matches-tree",
     lambda p: root_tree(p, BARE_ROOT),
     set()),
    ("stray-root-entry-tracked",
     lambda p: root_tree(p, BARE_ROOT, tracked=["stray.md"]),
     {"stray-root-entry"}),
    ("stray-root-entry-untracked",
     lambda p: root_tree(p, BARE_ROOT, untracked=["loose.md"]),
     {"stray-root-entry"}),
    # THE FALSE-POSITIVE TWIN, and the reason L-10.2 reads "what git would
    # publish" rather than "what is on disk": a root-level .py is ignored, so
    # it never reaches the remote and this check must not mention it.
    ("fp-root-ignored-py-is-gitignores-half",
     lambda p: root_tree(p, [".gitignore"] + BARE_ROOT,
                         gitignore="/*.py\n", untracked=["stray.py"]),
     set()),
    ("stale-root-row",
     lambda p: root_tree(p, BARE_ROOT + ["gone.md"]),
     {"stale-root-row"}),
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
    # --- zero rows, partial reads and wrapped fields (roadmap 0.3.1, L-1.3) --
    # A fourth element names the parts the case plants NOT EVALUATED. Each
    # used to be silence inside a clean line.
    #
    # ZERO ROWS: a prefix table whose every row is outside the grammar, so
    # namespace-drift compared two lists, one of them empty, and found nothing.
    ("zero-rows-a-prefix-table-that-parses-to-nothing",
     lambda p: w(p, "templates/FORMATS.md",
                 FORMATS.replace("`R-`", "`r-`").replace("`T-`", "`t-`").replace("`P-`", "`p-`")),
     set(), {"namespace-drift"}),
    # ...and a FORMATS.md with no prefix table at all offers no row, and one
    # side of the comparison is still empty.
    ("zero-rows-no-prefix-table-at-all",
     lambda p: w(p, "templates/FORMATS.md", "# The formats\n\nThe table moved.\n"),
     set(), {"namespace-drift"}),
    # A PARTIAL READ: one class row whose name the grammar rejects, and a
    # source heading written without its backticks, whose rows were dropped.
    ("partial-read-a-class-row-the-grammar-rejects",
     lambda p: w(p, "docs/CHECKS.md",
                 checks_md(p, extra_rows="| `Bad_Class` | P-1 | x ↔ y | `enforces` |\n")),
     set(), {"unruled-finding and stale-row"}),
    ("partial-read-a-source-heading-without-backticks",
     lambda p: w(p, "docs/CHECKS.md", checks_md(p).replace(
         "## `check_plugin.py`", "## check_plugin.py")),
     {"unruled-finding"}, {"unruled-finding and stale-row"}),
    ("partial-read-a-subcycle-named-outside-the-grammar",
     lambda p: roadmap(p, {"0.3/0.3.1-notes.md": "# 0.3.1 notes — PLANNED"}),
     set(), {"meta/roadmap/0.3/0.3.1-notes.md"}),
    ("partial-read-a-root-row-without-backticks",
     lambda p: (root_tree(p, BARE_ROOT),
                open(os.path.join(p, "..", "..", "README.md"), "a",
                     encoding="utf-8").write("| LICENSE | no backticks |\n")),
     set(), {"the root-table checks"}),
    ("an-emitter-gone-with-its-rows-still-in-the-table",
     lambda p: os.remove(os.path.join(p, "scripts", "check_refs.py")),
     set(), {"stale-row for check_refs.py", "namespace-drift"}),
    # A WRAPPED FIELD: `skills:` as a YAML block list is read from its first
    # line only. The finding is that old reading's artifact, and the gap
    # names its cause.
    ("wrapped-field-skills-as-a-block-list",
     lambda p: w(p, "agents/runner.md",
                 AGENT.format(name="runner", skills="alpha").replace("skills: [alpha]",
                                                                     "skills:\n  - alpha")),
     {"missing-skill"}, {"agents/runner.md's skills:"}),
    # A RULE NUMBER MAY CARRY A LETTER (the owner's answer, 2026-09-24). The
    # twelve suffixed rules were invisible both ways -- declared nothing,
    # cited nothing -- so a citation of one that does not exist passed.
    ("unknown-rule-for-a-suffixed-rule-nobody-declared",
     lambda p: w(p, "skills/alpha/SKILL.md", SKILL.format(name="alpha") + "\nThis refines P-2b.\n"),
     {"unknown-rule"}),
    ("fp-a-declared-suffixed-rule-is-cited-cleanly",
     lambda p: (w(p, "PROTOCOL.md", PROTOCOL + "\n**P-2b — a refinement of P-2.** Because.\n"),
                w(p, "skills/alpha/SKILL.md", SKILL.format(name="alpha") + "\nThis refines P-2b.\n")),
     set()),
    # A line numbering a rule that declares nothing, and whose rule nothing
    # else declares: offered, not read. Its own number then reads as a
    # citation of an undeclared rule -- the finding; the gap names the line.
    ("partial-read-a-rule-line-that-declares-nothing",
     lambda p: w(p, "PROTOCOL.md", PROTOCOL + "\n**P-3: a third rule.** Because.\n"),
     {"unknown-rule"}, {"PROTOCOL.md's rules"}),
    ("fp-a-note-about-a-declared-rule-is-not-a-declaration",
     lambda p: w(p, "PROTOCOL.md", PROTOCOL + "\n**P-2's text stands unedited** for the host.\n"),
     set()),
    # ...and what must stay quiet.
    ("fp-a-folded-description-is-not-a-wrapped-skills-field",
     lambda p: w(p, "agents/runner.md",
                 AGENT.format(name="runner", skills="alpha").replace(
                     "description: A fixture agent.", "description: >\n  A fixture agent.")),
     set()),
    ("fp-a-prose-table-under-another-heading-offers-no-class",
     lambda p: w(p, "docs/CHECKS.md", checks_md(p, extra_rows=(
         "\n## Coverage\n\n| Control | Cases |\n|---|---|\n| `test_x` | 12 |\n"))),
     set()),
    ("fp-a-cycle-readme-is-not-a-subcycle",
     lambda p: roadmap(p, {"0.3/README.md": "# The cycle"}),
     set()),

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
    for case in CASES:
        name, mutate, expected = case[:3]
        # Parts a case plants NOT EVALUATED, on top of what the fixture itself
        # cannot exercise (roadmap 0.3.1, L-1.3).
        planted = case[3] if len(case) > 3 else set()
        root, plugin = build(mutate)
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(plugin, "scripts", "check_plugin.py")],
                capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (?!not evaluated: |excluded: )(\S+)", proc.stdout, re.M)}
            gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            # WHAT THIS FIXTURE CANNOT EXERCISE, stated rather than hidden
            # (roadmap 0.3.1, L-1.1). No fixture here carries a setup.py, so the
            # template checks never run -- and until 0.3.1 they were reported
            # SKIPPED inside a CLEAN line, exit 0, so every clean case below
            # passed on a part it never ran. The root-table checks run only
            # when a case builds the README's table (root_tree).
            want_gaps = {"the template checks"}
            readme = os.path.join(root, "README.md")
            if not (os.path.isfile(readme)
                    and "## What is in this repository" in open(readme, encoding="utf-8").read()):
                want_gaps.add("the root-table checks")
            if not os.path.isdir(os.path.join(plugin, "docs")):
                want_gaps.add("unruled-finding and stale-row")
            want_gaps |= planted
            want_exit = 1 if expected else 3
            if got == expected and gaps == want_gaps and proc.returncode == want_exit:
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

    # --- THE TEMPLATE CHECKS, RUN (roadmap 0.3.1, found at step 3.1) --------
    # Every case above is a partial plugin with no setup.py, so the template
    # checks never ran in this control: `template-ships-a-finding` and
    # `template-scaffold-fails` were planted nowhere, and the CASES loop has no
    # clean case at all -- each expects a part not evaluated. A fixture that
    # can scaffold has to carry the real scaffolder, the real templates, and
    # every rule and script they cite, so it is the WHOLE plugin, copied under
    # a throwaway repository root with its root table. Nothing is planted in
    # the shipped tree.
    def whole_plugin():
        root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-plugincheck-whole-"))
        plugin = os.path.join(root, "plugins", "devteam")
        # meta/ comes too: the plugin's README and docs link into it, and a
        # copy without it is a plugin with broken links. So these cases are
        # green only while check_plugin is clean on the real plugin -- which
        # every step's commit requires anyway, and a failure here shows the
        # same finding.
        shutil.copytree(os.path.dirname(HERE), plugin,
                        ignore=shutil.ignore_patterns("__pycache__", ".run"))
        shutil.copy2(REAL, os.path.join(plugin, "scripts", "check_plugin.py"))
        return root, plugin

    def append_to(rel, text):
        return lambda p: open(os.path.join(p, rel), "a", encoding="utf-8").write(text)

    scaffold_cases = [
        # (name, plant, expected findings, expected parts not evaluated)
        ("clean-a-whole-plugin-scaffolds-a-clean-project", None, set(), set()),
        # A template citing something no scaffolded project declares: the
        # class 0.2.4 built this check for (`F-100`, `in-progress (T-2, T-5)`).
        ("template-ships-a-finding",
         append_to("templates/REQUIREMENTS.md", "\nSee R-99 for why.\n"),
         {"template-ships-a-finding"}, set()),
        ("template-scaffold-fails",
         lambda p: open(os.path.join(p, "scripts", "setup.py"), "w").write(
             "import sys\nsys.exit('refusing to scaffold')\n"),
         {"template-scaffold-fails"}, set()),
        # The scaffold's check_refs exits non-zero and prints nothing to read:
        # that was taken as no finding, so the scaffold was never shown clean
        # (L-1.3). Its source is unchanged, so the class scanner still reads it.
        ("a-scaffold-check-that-says-nothing-is-not-evaluated",
         lambda p: open(os.path.join(p, "scripts", "check_refs.py"), "w").write(
             "import sys\nif __name__ == '__main__':\n    sys.exit(2)\n"
             + open(os.path.join(HERE, "check_refs.py"), encoding="utf-8").read()),
         set(), {"the template checks"}),
    ]
    for name, plant, expected, want_gaps in scaffold_cases:
        root, plugin = whole_plugin()
        try:
            if plant:
                plant(plugin)
            # The plugin's README links to the repository's LICENSE, so the
            # throwaway root carries one, and lists it.
            root_tree(plugin, BARE_ROOT + ["LICENSE"], tracked=["LICENSE"])
            proc = subprocess.run(
                [sys.executable, os.path.join(plugin, "scripts", "check_plugin.py")],
                capture_output=True, text=True)
            got = {m for m in re.findall(r"^  (?!not evaluated: |excluded: )(\S+)", proc.stdout, re.M)}
            gaps = set(re.findall(r"^  not evaluated: (.+?) — ", proc.stdout, re.M))
            want_exit = 1 if expected else (3 if want_gaps else 0)
            if got == expected and gaps == want_gaps and proc.returncode == want_exit:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}")
                print(f"        expected {sorted(expected) or 'clean'} not evaluated "
                      f"{sorted(want_gaps) or 'none'} exit {want_exit}")
                print(f"        got      {sorted(got) or 'clean'} not evaluated "
                      f"{sorted(gaps) or 'none'} exit {proc.returncode}")
                for line in (proc.stdout + proc.stderr).strip().split("\n")[:8]:
                    print(f"        | {line[:200]}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
    CASES.extend([(c[0],) for c in scaffold_cases])

    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0].startswith("clean"))
    print(f"\ncheck_plugin control: {passed} passed, {failed} failed, "
          f"{len(CASES)} cases ({fp} of them false-positive controls, "
          f"{100 * fp // len(CASES)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
