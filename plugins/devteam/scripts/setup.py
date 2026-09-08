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

# Build artifacts a project's own TEST COMMAND creates, per detected stack.
#
# These are here because of a measured dead end, not out of tidiness. F-37, on
# the first live run: every suite run wrote `__pycache__/`, so
# `git status --porcelain` was never empty again -- including immediately after
# a verifier ran the suite, which is that verifier's own FIRST check. It could
# not be tidied beforehand, because running the suite recreates it, and `rm` is
# withheld by the grant. The manager fixed it by hand and the fix never became
# a mechanism, so it recurs on every new project; roadmap 0.2.4's own
# end-to-end reproduced it on a fresh one a whole cycle later.
#
# P-44 raises the cost. A dirty tree used to fail a precondition; now an
# uncommitted remainder REFUSES THE PROMOTION, so a worker's finished step does
# not land, for a file its own verification command created. That is a
# supervisor reading `promote-uncommitted` and going to look at the worker.
#
# Proposed like everything else `detect()` finds -- printed back for the client
# to confirm, and theirs to remove.
STACK_IGNORES = {
    "python": ["__pycache__/", "*.py[cod]", ".pytest_cache/"],
    "node": ["node_modules/"],
    "rust": ["target/"],
    "go": [],
    "make": [],
}
RUNTIME_DIRS = ("session", "locks", "env", "scratch")

# The templates carry a worked example of each shape, so a human reading the
# template sees what one looks like. Installed verbatim those examples become
# real, broken content -- a brand-new project reported nine findings before any
# work had been done, which is exactly how a check earns a reputation for
# noise. Setup strips them; the plugin keeps them.
EXAMPLE = re.compile(r"^<!-- example:begin -->\n.*?^<!-- example:end -->\n", re.S | re.M)

# TWO MARKERS, BECAUSE ONE WAS BEING READ TWO OPPOSITE WAYS.
# `example:` means "this is an illustration of ours; do not ship it". But
# check_trace's `template_names()` read the SAME marker to learn which rows a
# charter must have, so the block meant "strip this" to setup and "this is the
# required schema" to the drift check. The charter's constraints table is where
# the conflict bites, because it has to do both: ship, so a client has a table
# to fill in, and be declared, so `template-drift` can tell a charter that
# predates a row. 0.2.8 found it by removing the markers -- the table then
# shipped and `template-drift` went permanently silent, which no check caught
# because the check that went quiet was the one being disarmed.
# `schema:` is the second reading with its own name: the CONTENT ships, the
# marker lines do not.
SCHEMA_MARK = re.compile(r"^<!-- schema:(?:begin|end) -->\n", re.M)

# Forms that are instantiated per item live with the plugin, not in the
# project: the planner copies TASK.md when it creates a task. Installing them
# under tasks/ would make a blank form look like a real task.
NOT_INSTALLED = {"FORMATS.md", "tasks", "checkpoints"}

PLACEHOLDER_DIR_README = {
    "audits": "# Audits\n\nOne file per audit, named `<scope>-<dimension>-<date>.md`, filed by the\nmanager because the auditor has no tool that writes. An audit reports and\nnever fixes; a worker triages the findings afterwards under the ordinary\ndiscipline.\n",
    "tasks": "# Tasks\n\nOne file per task, named `T-1.md`, `T-2.md`. The planner writes them\nfrom the plugin's `templates/tasks/TASK.md`. A task file is the unit of\nclaim, the contract its supervisor works to, and where its execution\nrecord and REPORT block land.\n",
    "checkpoints": "# Checkpoints\n\nOne file per checkpoint, named `C-1-<date>.md`, written from the plugin's\n`templates/checkpoints/CHECKPOINT.md`. A checkpoint is a verdict with\nevidence and is never edited after it is filed.\n",
}


def artifact_stack(project, declared):
    """The stack whose BUILD ARTIFACTS this tree will produce.

    Deliberately a WEAKER question than `detect()` asks. `detect()` reports
    what the project DECLARES, and its answer becomes a charter recommendation
    a client must confirm, so it rightly insists on a manifest. Whether a
    directory is going to grow `__pycache__/` is not a matter of declaration:
    it is a matter of there being `.py` files in it.

    MEASURED, 0.2.8's end-to-end walk on a project the pipeline had not
    written: a tree with `slugify.py`, `test_slugify.py` and a green pytest
    suite has no manifest, so `detect()` correctly found nothing, so NO python
    ignore lines were written -- and the first promotion of the first step was
    REFUSED with `promote-uncommitted` naming two `.pyc` files that the step's
    own STEP-VERIFY command had just created.

    That is F-37 exactly, one whole cycle after the mechanism built to prevent
    it, and it is worse now than when it was found: F-37 made a tree dirty, and
    P-44 makes an uncommitted remainder refuse the promotion outright, so a
    finished step does not land. The gate was right to refuse -- the defect is
    that the artifact was never ignored.
    """
    if declared:
        return declared
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if d not in (".git", "devteam")]
        if any(f.endswith(".py") for f in filenames):
            return "python"
    return None


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


def ensure_gitignore(project, stack=None):
    """Add what the loop needs ignored. Returns the lines actually added.

    Two groups, and they are separate because they are owed to different
    parties: `devteam/.run/` is OURS and the loop cannot run without it
    ignored (`sandbox.py dispatch` refuses otherwise), while the stack lines
    are the PROJECT'S build artifacts and are a proposal the client may drop.
    Both are appended only when absent, so re-running setup is a no-op and a
    client who deleted a line does not get it back silently.
    """
    path = os.path.join(project, ".gitignore")
    try:
        body = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    except OSError:
        return []
    existing = {l.strip() for l in body.splitlines()}
    added, chunks = [], []

    if GITIGNORE_LINE not in existing:
        chunks.append(f"\n# devteam runtime state — locks, session markers, scratch\n"
                      f"{GITIGNORE_LINE}\n")
        added.append(GITIGNORE_LINE)

    want = [l for l in STACK_IGNORES.get(stack or "", []) if l not in existing]
    if want:
        chunks.append("\n# build artifacts this project's own test command creates.\n"
                      "# Without these the tree is never clean after a test run, which\n"
                      "# fails every verifier's first check and refuses every promotion.\n"
                      + "".join(f"{l}\n" for l in want))
        added += want

    if not chunks:
        return []
    with open(path, "a", encoding="utf-8") as fh:
        if body and not body.endswith("\n"):
            fh.write("\n")
        fh.write("".join(chunks))
    return added


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
                    body = SCHEMA_MARK.sub("", EXAMPLE.sub("", fh.read()))
                with open(os.path.join(dst, inner), "w", encoding="utf-8") as fh:
                    fh.write(body)
                installed += 1
        else:
            with open(src, encoding="utf-8") as fh:
                body = SCHEMA_MARK.sub("", EXAMPLE.sub("", fh.read()))
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

    added = ensure_gitignore(
        project, artifact_stack(project, found.get("stack")))

    print(f"devteam/ scaffolded in {project}")
    print(f"  {installed} artifacts, empty tasks/ and checkpoints/, .run/ (untracked)")
    if added:
        print(f"  added to .gitignore: {', '.join(added)}")
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
