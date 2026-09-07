#!/usr/bin/env python3
"""Internal consistency of the devteam plugin itself.

The plugin imposes a discipline on the projects it runs; this holds it to the
same one. Every finding here is a diff between two lists (P-4) -- what is
referenced against what exists.

The finding classes it emits, and the rule each enforces, are in
docs/CHECKS.md -- one home (P-34). This docstring deliberately does not
list them: it used to, and ten classes were emitted, controlled, and
absent from the lists here. `unruled-finding` in check_plugin.py keeps
docs/CHECKS.md and the code equal in both directions.

Exit 0 clean, 1 findings, 2 could not run.
"""
import ast
import json
import os
import re
import tempfile
import subprocess
import shutil
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(PLUGIN, "..", ".."))

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
RULE = re.compile(r"\bP-(\d+)\b")
SCRIPT_REF = re.compile(r"(?:\$\{CLAUDE_PLUGIN_ROOT\}|\$\{CLAUDE_SKILL_DIR\}/\.\.)/(\S+?\.py)")
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def field(fm, key):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    return m.group(1).strip() if m else None


def walk_md(root):
    for base, _dirs, files in os.walk(root):
        if os.sep + ".git" in base:
            continue
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(base, f)


class _SkipScaffold(Exception):
    """The scaffold check's inputs are not present in this tree."""


# --- docs/CHECKS.md <-> the code -------------------------------------------
# The classes a check emits are read from its AST, never from its docstring.
# The docstrings used to carry their own lists and TEN classes were emitted,
# controlled, and absent from them; the parsing convention (two leading spaces,
# a hyphenated name) silently dropped both single-word classes and the longest
# names, giving 44, 46 or 47 depending on how it was written against 57 from
# the AST. A check taking the docstring as its declared side would have been
# blind to exactly the classes with no rule written -- the instrument answering
# an adjacent question (P-35b), inside the check added to catch that shape.

CHECKS_MD = os.path.join(PLUGIN, "docs", "CHECKS.md")
EMITTERS = ("check_trace.py", "check_refs.py", "check_report.py",
            "check_scope.py", "check_plugin.py")


class UncountableEmit(Exception):
    """An emit site whose class name is not a string literal."""


def emitted_classes(path):
    """The finding classes a check script emits, from its AST.

    Matches BARE `add(...)` and `findings.append((...))` only. Two shapes look
    like emit sites and are not: the dispatcher's own definition

        add = lambda kind, where, detail: findings.append((kind, where, detail))

    whose first argument is the parameter `kind`, and `set.add()` --
    `seen.add(name)`, `discharged.add(r)` -- an unrelated method sharing the
    name. `X.add()` is excluded by requiring a bare Name; the lambda is
    excluded by skipping the assignment that defines it.

    The append arm is bound to the list named `findings` specifically, not to
    any `.append`. Accepting any tuple append made two ordinary list builds --
    `out.append((path, n, text))` in check_report and `unparsed.append(...)` in
    check_scope -- look like emit sites with a computed class. The tripwire
    below caught that on its first run, against its author rather than against
    the code it watches, which is the correct outcome for a loud failure.

    It then RAISES on any surviving non-literal rather than skipping it. A
    parser that skipped silently would handle both shapes correctly by
    accident and would also skip a genuine emit site written with a computed
    name -- blinding this check to precisely the class most likely to need a
    rule. The assertion fires on nothing today. It is a tripwire, not a filter.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    lambda_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Lambda):
            for sub in ast.walk(node.value):
                lambda_lines.add(getattr(sub, "lineno", None))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or node.lineno in lambda_lines:
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "add" and node.args:
            first = node.args[0]
        elif (isinstance(fn, ast.Attribute) and fn.attr == "append"
              and isinstance(fn.value, ast.Name) and fn.value.id == "findings"
              and node.args and isinstance(node.args[0], ast.Tuple)
              and node.args[0].elts):
            first = node.args[0].elts[0]
        else:
            continue
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            raise UncountableEmit(
                f"{os.path.basename(path)}:{node.lineno} emits a finding whose "
                f"class is not a string literal; docs/CHECKS.md cannot be "
                f"diffed against it")
        out.append(first.value)
    return dict.fromkeys(out)


CHECKS_HEADING = re.compile(r"^## `([^`]+)`")
CHECKS_ROW = re.compile(r"^\|\s*`([a-z][a-z0-9-]*)`")


def checks_table(path):
    """{source: [class, ...]} as docs/CHECKS.md declares them."""
    table, source = {}, None
    for line in open(path, encoding="utf-8"):
        m = CHECKS_HEADING.match(line)
        if m:
            source = m.group(1)
            table.setdefault(source, [])
            continue
        m = CHECKS_ROW.match(line)
        if m and source:
            table[source].append(m.group(1))
    return table


def main():
    findings = []
    add = lambda kind, where, detail: findings.append((kind, where, detail))
    rel = lambda p: os.path.relpath(p, PLUGIN)

    proto = os.path.join(PLUGIN, "PROTOCOL.md")
    if not os.path.isfile(proto):
        print("check_plugin: PROTOCOL.md missing", file=sys.stderr)
        return 2
    declared = {int(n) for n in re.findall(r"^\*\*P-(\d+) ", open(proto).read(), re.M)}

    skills_dir = os.path.join(PLUGIN, "skills")
    skills = {}
    for name in sorted(os.listdir(skills_dir)) if os.path.isdir(skills_dir) else []:
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            add("bad-frontmatter", f"skills/{name}", "no SKILL.md")
            continue
        # Register the skill by its DIRECTORY name before parsing. The skill
        # exists either way; its frontmatter is a separate defect. Skipping it
        # here made every agent that preloads it report `missing-skill` too --
        # one fault, three findings, with the cause buried among them.
        skills[name] = path
        m = FRONTMATTER.match(open(path).read())
        if not m:
            add("bad-frontmatter", rel(path), "no YAML frontmatter")
            continue
        declared_name = field(m.group(1), "name")
        if not declared_name or not field(m.group(1), "description"):
            add("bad-frontmatter", rel(path), "missing name or description")
        if declared_name and declared_name != name:
            add("name-mismatch", rel(path), f"directory {name!r} vs name {declared_name!r}")

    agents_dir = os.path.join(PLUGIN, "agents")
    for name in sorted(os.listdir(agents_dir)) if os.path.isdir(agents_dir) else []:
        path = os.path.join(agents_dir, name)
        m = FRONTMATTER.match(open(path).read())
        if not m:
            add("bad-frontmatter", rel(path), "no YAML frontmatter")
            continue
        if not field(m.group(1), "name") or not field(m.group(1), "description"):
            add("bad-frontmatter", rel(path), "missing name or description")
        raw = field(m.group(1), "skills") or ""
        for s in re.findall(r"[A-Za-z0-9_-]+", raw):
            if s not in skills:
                add("missing-skill", rel(path), f"preloads {s!r}, which does not exist")

    for path in walk_md(PLUGIN):
        body = open(path, encoding="utf-8", errors="replace").read()
        for n in {int(x) for x in RULE.findall(body)}:
            if n not in declared:
                add("unknown-rule", rel(path), f"cites P-{n}, which PROTOCOL.md does not declare")
        for script in set(SCRIPT_REF.findall(body)):
            if not os.path.isfile(os.path.join(PLUGIN, script)):
                add("missing-script", rel(path), script)
        for target in LINK.findall(body):
            t = target.split("#", 1)[0].strip()
            if not t or t.startswith(("http://", "https://", "mailto:")):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), t))):
                add("broken-link", rel(path), t)

    for name in sorted(os.listdir(HERE)):
        if name.startswith("check_") and name.endswith(".py") and name != "check_plugin.py":
            if not os.path.isfile(os.path.join(HERE, "test_" + name)):
                add("uncontrolled-check", f"scripts/{name}",
                    f"no test_{name} beside it — a check that has never failed "
                    "has not been shown to work")

    # The reserved-prefix table and the scanner's own sets are two lists of the
    # same thing, so they are diffed rather than trusted to agree. A prefix
    # documented and not recognised is a citation nobody validates; one
    # recognised and not documented is a collision waiting for whoever numbers
    # something next.
    formats = os.path.join(PLUGIN, "templates", "FORMATS.md")
    refs = os.path.join(HERE, "check_refs.py")
    if os.path.isfile(formats) and os.path.isfile(refs):
        body = open(formats, encoding="utf-8").read()
        # WIDENED WITH THE SCANNER IN 0.2.6. When the audit namespace became
        # checked, leaving this at two letters would have made namespace-drift
        # silently stop covering the five prefixes just reserved -- the
        # "carved out means unseen" failure, one level up, inside the check
        # that exists to catch it.
        documented = set(re.findall(r"^\|\s*`([A-Z]{1,3})-`\s*\|", body, re.M))
        src = open(refs, encoding="utf-8").read()
        recognised = set()
        for name in ("KNOWN", "EXTERNAL", "AUDIT"):
            m = re.search(rf"^{name}\s*=\s*\{{([^}}]*)\}}", src, re.M)
            if m:
                recognised |= set(re.findall(r'"([A-Z]{1,3})"', m.group(1)))
        if documented and recognised:
            for p_ in sorted(documented - recognised):
                add("namespace-drift", "templates/FORMATS.md",
                    f"`{p_}-` is reserved in the table and not recognised by check_refs.py")
            for p_ in sorted(recognised - documented):
                add("namespace-drift", "scripts/check_refs.py",
                    f"`{p_}-` is recognised by the scanner and not reserved in FORMATS.md")

    hooks = os.path.join(PLUGIN, "hooks", "hooks.json")
    if os.path.isfile(hooks):
        try:
            body = open(hooks).read()
            json.loads(body)
            for script in set(SCRIPT_REF.findall(body)):
                if not os.path.isfile(os.path.join(PLUGIN, script)):
                    add("missing-script", "hooks/hooks.json", script)
        except ValueError as exc:
            add("bad-manifest", "hooks/hooks.json", str(exc))

    manifest = os.path.join(PLUGIN, ".claude-plugin", "plugin.json")
    try:
        pj = json.load(open(manifest))
        if pj.get("name") != os.path.basename(PLUGIN):
            add("bad-manifest", ".claude-plugin/plugin.json",
                f"name {pj.get('name')!r} != directory {os.path.basename(PLUGIN)!r}")
    except (OSError, ValueError) as exc:
        add("bad-manifest", ".claude-plugin/plugin.json", str(exc))

    market = os.path.join(REPO, ".claude-plugin", "marketplace.json")
    if os.path.isfile(market):
        try:
            mj = json.load(open(market))
            for entry in mj.get("plugins", []):
                src = entry.get("source")
                if isinstance(src, str):
                    if not os.path.isdir(os.path.normpath(os.path.join(REPO, src))):
                        add("bad-manifest", "../../.claude-plugin/marketplace.json",
                            f"{entry.get('name')}: source {src!r} does not exist")
        except ValueError as exc:
            add("bad-manifest", "../../.claude-plugin/marketplace.json", str(exc))

    # --- the templates, as a CLIENT's project sees them (roadmap 0.2.4) ----
    #
    # THE ONLY INSTRUMENT THAT SEES THIS CLASS IS A SCAFFOLD-AND-CHECK, and
    # until now that was a person deciding to do it. Two live instances shipped:
    #
    #   PERMISSIONS.md   cited `F-100` -- a real finding IN THIS REPOSITORY,
    #                    and a dangling citation in every project downstream
    #   REQUIREMENTS.md  wrote `in-progress (T-2, T-5)` to illustrate the
    #                    grammar -- ids that exist NOWHERE, in this repository
    #                    or any other
    #
    # The second is the one that outlived the fix for the first, and the reason
    # is worth stating: a reader who knows the record can spot a dangling F-n,
    # and nothing at all marks an invented T-n as invented. The class that
    # catches both is `any bare identifier in an installed template that
    # survives the example strip and is not declared by the scaffold`.
    #
    # Neither is visible from inside this repository: `F-100` resolves here,
    # and `T-2` is never checked here because the templates are not a project.
    # So the check has to BE a scaffold -- install the templates the way
    # `setup.py` does, into a throwaway, and run the client's own `check_refs`
    # against it. Zero findings, on a project where no work has been done.
    #
    # It reuses `setup.py` itself rather than reimplementing the install, so
    # the two cannot drift: a check that scaffolds differently from the
    # scaffolder is a check that passes on a project nobody will ever have.
    # GATED ON ITS INPUTS, AND THE SKIP IS PRINTED. This check needs the real
    # scaffolder and the real templates; a partial plugin tree (this file's own
    # control builds several) has neither, and reporting `scaffold failed`
    # there would be the check answering a question nobody asked -- P-35b, in
    # the check that exists to catch a related shape. A skip that says nothing
    # is the other half of that mistake, so the summary line names it.
    setup_py = os.path.join(PLUGIN, "scripts", "setup.py")
    scaffolded = os.path.isfile(setup_py) and os.path.isdir(os.path.join(PLUGIN, "templates"))
    tmp = tempfile.mkdtemp(prefix="devteam-template-check-") if scaffolded else None
    try:
        if not scaffolded:
            raise _SkipScaffold
        proj = os.path.join(tmp, "p")
        os.makedirs(proj)
        for cmd in (["init", "-q", "."], ["config", "user.name", "check"],
                    ["config", "user.email", "check@devteam.invalid"]):
            subprocess.run(["git", "-C", proj, *cmd], capture_output=True)
        rc = subprocess.run([sys.executable, setup_py, proj],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            add("template-scaffold-fails", "scripts/setup.py",
                f"setup.py could not scaffold a fresh project: "
                f"{(rc.stdout + rc.stderr).strip()[:200]}")
        else:
            subprocess.run(["git", "-C", proj, "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", proj, "commit", "-qm", "scaffold"],
                           capture_output=True)
            out = subprocess.run(
                [sys.executable, os.path.join(PLUGIN, "scripts", "check_refs.py"), proj],
                capture_output=True, text=True)
            if out.returncode != 0:
                for line in out.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        add("template-ships-a-finding", "templates/",
                            f"a freshly scaffolded project reports: {line.strip()}")
    except _SkipScaffold:
        pass
    except OSError as exc:
        add("template-scaffold-fails", "templates/", str(exc))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- unruled-finding / stale-row (L-6.1) -------------------------------
    # A check is legitimate only when it enforces a rule that exists, and a
    # rule exists only when something checks it. docs/CHECKS.md is one half of
    # that pair; this is the other. Both directions, because a table that has
    # drifted is as bad as one that is short: a row for a class nobody emits
    # sends a reader looking for a check that is not there.
    # GATED ON ITS INPUTS, AND THE SKIP IS PRINTED. This control's own fixtures
    # build partial plugin trees with no docs/ at all, and reporting "CHECKS.md
    # is missing" there would be the check answering a question nobody asked
    # (P-35b) -- the same gate 0.2.4 had to give template-ships-a-finding, for
    # the same reason. A tree that HAS docs/ and lacks CHECKS.md is a real
    # finding; a tree with no docs/ is not a plugin this check can speak about.
    ruled = os.path.isdir(os.path.join(PLUGIN, "docs"))
    if not ruled:
        pass
    elif not os.path.isfile(CHECKS_MD):
        add("unruled-finding", "docs/CHECKS.md",
            "docs/CHECKS.md is missing; no finding class has a rule named")
    else:
        table = checks_table(CHECKS_MD)
        for script in EMITTERS:
            spath = os.path.join(PLUGIN, "scripts", script)
            if not os.path.isfile(spath):
                continue
            try:
                emits = emitted_classes(spath)
            except (UncountableEmit, SyntaxError) as exc:
                add("unruled-finding", f"scripts/{script}", str(exc))
                continue
            rows = table.get(script, [])
            for cls in emits:
                if cls not in rows:
                    add("unruled-finding", f"scripts/{script}",
                        f"`{cls}` is emitted and has no row in docs/CHECKS.md, "
                        f"so it names no rule")
            for cls in rows:
                if cls not in emits:
                    add("stale-row", "docs/CHECKS.md",
                        f"`{cls}` has a row under {script} and no check emits it")
        # `sandbox.py promote` carries its classes as literals rather than
        # through add(), and FORMATS.md already declares the closed set.
        sbx = os.path.join(PLUGIN, "scripts", "sandbox.py")
        if os.path.isfile(sbx):
            emits = set(re.findall(r"promote-[a-z-]+",
                                   open(sbx, encoding="utf-8").read()))
            rows = set(table.get("sandbox.py promote", []))
            for cls in sorted(emits - rows):
                add("unruled-finding", "scripts/sandbox.py",
                    f"`{cls}` is emitted and has no row in docs/CHECKS.md")
            for cls in sorted(rows - emits):
                add("stale-row", "docs/CHECKS.md",
                    f"`{cls}` has a promotion row and sandbox.py does not emit it")
        # guard.py is deliberately NOT diffed: its refusals have no names in
        # the code at all, so there is no second list to compare. docs/CHECKS.md
        # names the eight families and says so.

    if findings:
        print(f"devteam plugin: {len(findings)} finding(s)")
        for kind, where, detail in sorted(findings):
            print(f"  {kind:20} {where}  {detail}")
        return 1
    skipped = []
    if not scaffolded:
        skipped.append("scaffold check SKIPPED — no setup.py or templates/")
    if not ruled:
        skipped.append("unruled-finding SKIPPED — no docs/")
    tail = ("; " + "; ".join(skipped)) if skipped else ""
    print(f"devteam plugin: clean  [{len(skills)} skills, "
          f"{len(os.listdir(agents_dir))} agents, {len(declared)} rules{tail}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
