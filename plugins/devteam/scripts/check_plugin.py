#!/usr/bin/env python3
"""Internal consistency of the devteam plugin itself.

The plugin imposes a discipline on the projects it runs; this holds it to the
same one. Every finding here is a diff between two lists (P-4) -- what is
referenced against what exists.

  missing-skill        an agent preloads a skill that does not exist
  name-mismatch        a skill's directory and its frontmatter name disagree
  bad-frontmatter      a skill or agent with no parseable frontmatter, or no
                       name/description
  missing-script       a skill, agent or hook names a script that is not there
  unknown-rule         a P-n cited that PROTOCOL.md does not declare
  uncontrolled-check   a check script with no negative control beside it (P-35)
  broken-link          a relative markdown link whose target does not exist
  bad-manifest         plugin.json or the marketplace entry does not resolve
  template-ships-a-finding
                       a freshly scaffolded project reports a finding before
                       any work has been done -- almost always an identifier in
                       an installed template that resolves HERE and nowhere
                       else, or one invented to illustrate a grammar
  template-scaffold-fails
                       setup.py could not scaffold a fresh project at all

Exit 0 clean, 1 findings, 2 could not run.
"""
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
        documented = set(re.findall(r"^\|\s*`([A-Z]{1,2})-`\s*\|", body, re.M))
        src = open(refs, encoding="utf-8").read()
        recognised = set()
        for name in ("KNOWN", "EXTERNAL"):
            m = re.search(rf"^{name}\s*=\s*\{{([^}}]*)\}}", src, re.M)
            if m:
                recognised |= set(re.findall(r'"([A-Z]{1,2})"', m.group(1)))
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

    if findings:
        print(f"devteam plugin: {len(findings)} finding(s)")
        for kind, where, detail in sorted(findings):
            print(f"  {kind:20} {where}  {detail}")
        return 1
    print(f"devteam plugin: clean  [{len(skills)} skills, "
          f"{len(os.listdir(agents_dir))} agents, {len(declared)} rules"
          + ("]" if scaffolded else ", scaffold check SKIPPED — no setup.py or templates/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
