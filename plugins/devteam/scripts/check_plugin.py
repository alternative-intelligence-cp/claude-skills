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

Exit 0 clean, 1 findings, 2 could not run.
"""
import json
import os
import re
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

    if findings:
        print(f"devteam plugin: {len(findings)} finding(s)")
        for kind, where, detail in sorted(findings):
            print(f"  {kind:20} {where}  {detail}")
        return 1
    print(f"devteam plugin: clean  [{len(skills)} skills, "
          f"{len(os.listdir(agents_dir))} agents, {len(declared)} rules]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
