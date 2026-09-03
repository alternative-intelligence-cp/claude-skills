#!/usr/bin/env python3
"""SessionStart hook (matcher: compact|resume): give a compacted or resumed
PROJECT MANAGER its bearings back, and say nothing to anybody else.

A manager that has lost its context mid-loop is the dangerous case: it does
not know which claims it made, so it can claim a second supervisor onto a task
that already has one -- the single failure the board's lock exists to prevent.
It cannot know that from a summary, because a summary of a loop reads like a
description of a loop.

Keyed on the marker the `run` skill writes at startup:
`<project>/devteam/.run/session/manager` holds the session id. This prints
only when that id equals the session being restored. Every other session, in
every other directory, gets nothing -- a hook that talks to sessions it was
not meant for is a hook that gets removed.

The block is a POINTER AND A PROCEDURE, never the rules themselves (P-34).
The rules have one home: skills/run/SKILL.md.
"""
import json
import os
import sys

BLOCK = """PROJECT MANAGER — context restored after compaction or resume.

You are the project manager for the devteam project at {project}.
Procedure: skills/run/SKILL.md — the loop is §4, reports are §6, escalation
classes are §8. Live state: devteam/BOARD.md. Past: devteam/RECORD.md.

Before any further action:
  1. re-read devteam/BOARD.md — it, not your memory, is the state;
  2. run ListAgents and reconcile the in-flight table. A row with no live
     agent is STALE: §3 Recovery. After a resume, EVERY row is stale;
  3. do not redo what the board shows done — the environment pin, the
     claims already made, the questions already on the table;
  4. width, the model band and the escalation window come from the board
     header and the charter, never from what you remember deciding.

Then continue the loop. If you cannot tell whether a task is claimed, read
the board's git history — a claim is a commit."""


def find_project(start):
    cur = os.path.realpath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "devteam")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    sid = str(data.get("session_id") or "")
    if not sid:
        return 0
    start = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    project = find_project(start)
    if project is None:
        return 0
    marker = os.path.join(project, "devteam", ".run", "session", "manager")
    try:
        with open(marker, encoding="utf-8") as fh:
            marked = fh.read().strip()
    except OSError:
        return 0
    if marked == sid:
        print(BLOCK.format(project=project))
    return 0


if __name__ == "__main__":
    sys.exit(main())
