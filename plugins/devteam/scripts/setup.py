#!/usr/bin/env python3
"""Scaffold `devteam/` in a target project.

Copies the templates, creates the untracked runtime directory, adds the one
gitignore line, and detects what the project already uses so the interview
starts from evidence rather than from questions whose answers are on disk.

It NEVER overwrites an existing devteam/ -- that directory is the project's
design record, and a setup script that can clobber it is a setup script that
eventually will.

Usage:  setup.py <project> [--force-detect]
Exit 0 done, 1 refused, 2 could not run.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
TEMPLATES = os.path.normpath(os.path.join(HERE, "..", "templates"))

GITIGNORE_LINE = "devteam/.run/"
RUNTIME_DIRS = ("session", "locks", "env", "scratch")

# The templates carry a worked example of each shape, so a human reading the
# template sees what one looks like. Installed verbatim those examples become
# real, broken content -- a brand-new project reported nine findings before any
# work had been done, which is exactly how a check earns a reputation for
# noise. Setup strips them; the plugin keeps them.
EXAMPLE = re.compile(r"^<!-- example:begin -->\n.*?^<!-- example:end -->\n", re.S | re.M)

# Forms that are instantiated per item live with the plugin, not in the
# project: the planner copies TASK.md when it creates a task. Installing them
# under tasks/ would make a blank form look like a real task.
NOT_INSTALLED = {"FORMATS.md", "tasks", "checkpoints"}

PLACEHOLDER_DIR_README = {
    "audits": "# Audits\n\nOne file per audit, named `<scope>-<dimension>-<date>.md`, filed by the\nmanager because the auditor has no tool that writes. An audit reports and\nnever fixes; a worker triages the findings afterwards under the ordinary\ndiscipline.\n",
    "tasks": "# Tasks\n\nOne file per task, named `T-1.md`, `T-2.md`. The planner writes them\nfrom the plugin's `templates/tasks/TASK.md`. A task file is the unit of\nclaim, the contract its supervisor works to, and where its execution\nrecord and REPORT block land.\n",
    "checkpoints": "# Checkpoints\n\nOne file per checkpoint, named `C-1-<date>.md`, written from the plugin's\n`templates/checkpoints/CHECKPOINT.md`. A checkpoint is a verdict with\nevidence and is never edited after it is filed.\n",
}


def detect(project):
    """What this project already tells us, so the interview need not ask."""
    found = {}
    j = lambda *p: os.path.join(project, *p)

    if os.path.isfile(j("package.json")):
        found["stack"] = "node"
        try:
            with open(j("package.json"), encoding="utf-8") as fh:
                scripts = (json.load(fh) or {}).get("scripts", {})
            if "test" in scripts:
                found["test"] = "npm test"
            if "build" in scripts:
                found["build"] = "npm run build"
            if "lint" in scripts:
                found["lint"] = "npm run lint"
        except (OSError, ValueError):
            pass
    if os.path.isfile(j("pyproject.toml")) or os.path.isfile(j("setup.py")):
        found["stack"] = "python"
        found.setdefault("test", "pytest")
        if os.path.isfile(j("pyproject.toml")):
            try:
                body = open(j("pyproject.toml"), encoding="utf-8").read()
                if "ruff" in body:
                    found["lint"] = "ruff check ."
                elif "black" in body:
                    found["lint"] = "black --check ."
            except OSError:
                pass
    if os.path.isfile(j("Cargo.toml")):
        found["stack"] = "rust"
        found.update(test="cargo test", build="cargo build", lint="cargo clippy")
    if os.path.isfile(j("go.mod")):
        found["stack"] = "go"
        found.update(test="go test ./...", build="go build ./...", lint="go vet ./...")
    if os.path.isfile(j("Makefile")):
        try:
            body = open(j("Makefile"), encoding="utf-8").read()
            targets = set(re.findall(r"^([A-Za-z0-9_-]+):", body, re.M))
        except OSError:
            targets = set()
        found.setdefault("stack", "make")
        if "test" in targets:
            found["test"] = "make test"
        if "build" in targets or "all" in targets:
            found["build"] = "make"
        for t in ("lint", "check", "fmt", "format"):
            if t in targets:
                found["lint"] = f"make {t}"
                break

    # Directories worth proposing as protected: not ours, not source.
    protected = [d for d in ("vendor", "third_party", "node_modules", "generated",
                             "dist", "build", ".venv")
                 if os.path.isdir(j(d))]
    if protected:
        found["protected"] = protected

    rc = subprocess.run(["git", "-C", project, "rev-parse", "--show-toplevel"],
                        capture_output=True, text=True)
    if rc.returncode == 0:
        found["git_root"] = rc.stdout.strip()
        remote = subprocess.run(["git", "-C", project, "remote", "get-url", "origin"],
                                capture_output=True, text=True)
        if remote.returncode == 0:
            found["remote"] = remote.stdout.strip()
    return found


def prefill(charter, found):
    """Replace charter placeholders the project has already answered."""
    swaps = {
        "| Build command | <the exact command> |":
            f"| Build command | `{found['build']}` |" if "build" in found else None,
        "| Test command | <the exact command, and what a green summary line looks like> |":
            f"| Test command | `{found['test']}` — green summary line: <fill in> |" if "test" in found else None,
        "| Lint / format command | <exact command, or `none`> |":
            f"| Lint / format command | `{found['lint']}` |" if "lint" in found else None,
        "| Repository | <remote, or `local only`> |":
            f"| Repository | {found['remote']} |" if found.get("remote") else None,
    }
    for old, new in swaps.items():
        if new:
            charter = charter.replace(old, new)
    if found.get("protected"):
        charter = charter.replace(
            "| Protected paths | <trees the pipeline may read but never write — vendored deps, generated output, sibling repos. The guard enforces these> |",
            "| Protected paths | " + ", ".join(f"`{p}/`" for p in found["protected"]) +
            " — confirm and add any others |")
    return charter


def ensure_gitignore(project):
    path = os.path.join(project, ".gitignore")
    try:
        body = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    except OSError:
        return False
    if GITIGNORE_LINE in body:
        return False
    with open(path, "a", encoding="utf-8") as fh:
        if body and not body.endswith("\n"):
            fh.write("\n")
        fh.write(f"\n# devteam runtime state — locks, session markers, scratch\n{GITIGNORE_LINE}\n")
    return True


def main(argv):
    if len(argv) < 2:
        print("usage: setup.py <project>", file=sys.stderr)
        return 2
    project = os.path.realpath(argv[1])
    if not os.path.isdir(project):
        print(f"setup: not a directory: {project}", file=sys.stderr)
        return 2
    if not os.path.isdir(TEMPLATES):
        print(f"setup: templates missing at {TEMPLATES}", file=sys.stderr)
        return 2

    devteam = os.path.join(project, "devteam")
    if os.path.exists(devteam):
        print(f"setup: {devteam} already exists — refusing to overwrite it.\n"
              f"       That directory is this project's design record. If you mean to\n"
              f"       start over, move it aside yourself first.", file=sys.stderr)
        return 1

    found = detect(project)

    os.makedirs(devteam)
    installed = 0
    for name in sorted(os.listdir(TEMPLATES)):
        if name in NOT_INSTALLED:
            continue                      # FORMATS.md stays with the plugin,
                                          # but its vocabularies do not -- see
                                          # STATUS_NOTE below
        src, dst = os.path.join(TEMPLATES, name), os.path.join(devteam, name)
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            for inner in sorted(os.listdir(src)):
                with open(os.path.join(src, inner), encoding="utf-8") as fh:
                    body = EXAMPLE.sub("", fh.read())
                with open(os.path.join(dst, inner), "w", encoding="utf-8") as fh:
                    fh.write(body)
                installed += 1
        else:
            with open(src, encoding="utf-8") as fh:
                body = EXAMPLE.sub("", fh.read())
            if name == "CHARTER.md":
                body = prefill(body, found)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(body)
            installed += 1

    for name, readme in PLACEHOLDER_DIR_README.items():
        os.makedirs(os.path.join(devteam, name), exist_ok=True)
        with open(os.path.join(devteam, name, "README.md"), "w", encoding="utf-8") as fh:
            fh.write(readme)

    for d in RUNTIME_DIRS:
        os.makedirs(os.path.join(devteam, ".run", d), exist_ok=True)
    with open(os.path.join(devteam, ".run", "detected.json"), "w", encoding="utf-8") as fh:
        json.dump(found, fh, indent=2, sort_keys=True)

    added = ensure_gitignore(project)

    print(f"devteam/ scaffolded in {project}")
    print(f"  {installed} artifacts, empty tasks/ and checkpoints/, .run/ (untracked)")
    if added:
        print(f"  added {GITIGNORE_LINE} to .gitignore")
    # A greenfield project detects `git_root` and nothing else. Printing the
    # header over an empty list reads as though detection ran and found things,
    # which is the opposite of what happened.
    substantive = {k: v for k, v in found.items() if k != "git_root"}
    if substantive:
        print("\nDetected, and pre-filled into the charter where confident:")
        for k in ("stack", "build", "test", "lint", "remote"):
            if k in found:
                print(f"  {k:9} {found[k]}")
        if found.get("protected"):
            print(f"  {'protected':9} {', '.join(found['protected'])}")
        print("\nEverything above is a PROPOSAL. The interview confirms each one —")
        print("a detected command that is wrong is worse than one that was asked about.")
    else:
        print("\nNOTHING was detected about this project's toolchain — no build,")
        print("test or lint command, no manifest, no remote. Every toolchain value")
        print("in the charter is therefore a RECOMMENDATION you must make and the")
        print("client must confirm. Do not present one as though it were found.")
    print("\nNext:  /devteam:onboard")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
