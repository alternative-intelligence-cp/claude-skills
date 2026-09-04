#!/usr/bin/env python3
"""Negative control for research_index.py (P-35).

The failures that matter here are not "no results". They are indexing
something that is not a digest, aging a digest wrongly, and — worst — the
index growing into a second copy of the answer.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.realpath(__file__))
TOOL = os.path.join(HERE, "research_index.py")


def digest(topic, days_ago, sensitivity="routine", question="what is the current edition?",
           answer="The current edition is 8, published 2024."):
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    sens = f"**Sensitivity.** {sensitivity}\n" if sensitivity else ""
    return f"""# {topic} — research digest

**As of {d}.** {sens}Question: {question}

## Answer
{answer}

## Evidence
- https://example.org/spec — retrieved {d} — "the answering line"

## Confidence and gaps
high
"""


def build(tmp, files):
    for rel, body in files.items():
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)


def run(index, *args):
    env = {**os.environ, "DEVTEAM_RESEARCH_INDEX": index}
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def main():
    passed = failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {name}   {detail}")

    tmp = tempfile.mkdtemp(prefix="devteam-idx-")
    index = os.path.join(tmp, "index.json")
    try:
        build(tmp, {
            "proj-a/devteam/research/posix.md": digest("POSIX utilities", 10),
            "proj-b/devteam/research/tls.md": digest("TLS ciphers", 200, "security"),
            "proj-b/devteam/research/toml.md": digest("TOML spec", 20, "routine"),
            "proj-b/devteam/research/CURRENCY.md": "| Depends on | Pinned |\n|---|---|\n",
            "proj-b/devteam/research/README.md": "# Digests live here\n",
            "proj-b/devteam/research/notes.md": "# just some notes\n\nNot a digest.\n",
            "proj-c/notes/stray.md": digest("Not in a research dir", 5),
            "proj-d/meta/research/other-convention.md": digest("Other layout", 5),
        })
        rc, out = run(index, "build", tmp)
        idx = json.load(open(index))
        topics = {d["topic"] for d in idx["digests"]}

        # The SHAPE gates, not the path: a properly written digest under a
        # different convention (meta/research/) must still be found.
        check("indexes real digests wherever research/ lives",
              topics == {"POSIX utilities", "TLS ciphers", "TOML spec", "Other layout"},
              f"got {sorted(topics)}")
        check("skips CURRENCY.md and README.md", "Depends on" not in json.dumps(idx))
        check("skips a file that is not in the digest shape", "just some notes" not in json.dumps(idx))
        check("skips a .md that is not in a research/ directory",
              "Not in a research dir" not in topics)
        check("records the project each came from",
              {d["project"] for d in idx["digests"]} == {"proj-a", "proj-b", "proj-d"},
              f"got {sorted({d['project'] for d in idx['digests']})}")

        # THE property that matters: pointers, never answers.
        blob = json.dumps(idx)
        check("index holds no findings", "The current edition is 8" not in blob,
              "the answer text leaked into the index")
        check("index holds no quoted evidence", "the answering line" not in blob)
        check("index does hold the path", all(os.path.isfile(d["path"]) for d in idx["digests"]))

        rc, out = run(index, "query", "toml")
        check("query finds by topic", rc == 0 and "TOML spec" in out)
        check("query prints the lead-not-answer warning", "LEAD, not an answer" in out)
        rc, out = run(index, "query", "nothing-like-this")
        check("query exits 1 on no match", rc == 1)
        rc, out = run(index, "query", "posix", "utilities")
        check("query ANDs its terms", rc == 0 and "POSIX" in out)
        rc, out = run(index, "query", "posix", "toml")
        check("query ANDs across digests", rc == 1, "should match neither")

        rc, out = run(index, "stale")
        check("security digest past 90d is stale", "TLS ciphers" in out)
        check("routine digest at 20d is not stale", "TOML spec" not in out)
        check("routine digest at 10d is not stale", "POSIX utilities" not in out)
        check("stale exits 1 when something is stale", rc == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # an unstated sensitivity must not be quietly aged as routine
    tmp = tempfile.mkdtemp(prefix="devteam-idx2-")
    index = os.path.join(tmp, "index.json")
    try:
        build(tmp, {"p/devteam/research/x.md": digest("Unstated", 200, sensitivity=None)})
        run(index, "build", tmp)
        rc, out = run(index, "query", "unstated")
        check("unstated sensitivity is reported, not assumed",
              "sensitivity unstated" in out and "STALE" not in out)
        rc, out = run(index, "stale")
        check("unstated sensitivity is not silently called fresh either",
              "Unstated" not in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = passed + failed
    print(f"\nresearch_index control: {passed} passed, {failed} failed, {total} cases")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
