---
name: resume
description: Pick a devteam project back up after an interruption — a crash, a killed session, a machine reboot, or simply coming back tomorrow. Reconciles what the record claims against what the tree actually holds, reports the difference, and gets the client's confirmation before re-dispatching anything that could destroy work.
argument-hint: "[project path]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git log:*) Bash(git diff:*) Bash(git show:*) Bash(ls:*) Bash(stat:*) Bash(date:*) Read Grep Glob AskUserQuestion
---

# Resuming

Something interrupted the loop. **Your first job is to find out what actually
happened, not to get going again** — because the cheapest-looking recovery
action, re-dispatching a task whose agent is gone, is also the one that can
destroy work nobody knew was there.

`/devteam:run` already reconciles and recovers on startup. This exists because
it does so *immediately*, and after an interruption the record and the tree can
disagree in ways only a human can settle.

## 1. Do not take the lock yet

Read first, write nothing. **Do not** set the board's writer line, re-pin the
environment, or touch a title. If another session is genuinely still alive you
have not yet trampled it, and if it is not, nothing was lost by looking.

## 2. Establish what the record claims

- `devteam/BOARD.md` — what is claimed, by which agent label, since when, and
  which session holds the writer lock
- `devteam/RECORD.md`, last entries — the last thing that was known to happen
- every task title under `devteam/tasks/` — the states as the supervisors left
  them
- `devteam/QUESTIONS.md` — anything `open` was waiting on the client, and may
  have been waiting for days

## 3. Establish what the tree actually holds

The record is what somebody meant to be true. These are facts:

```bash
git -C "$REPO" status --porcelain
git -C "$REPO" log --oneline -15
ls -la devteam/.run/locks/            # heartbeats: which step, since when
ls -la devteam/.run/session/          # which session believed it held the lock
```

Then run all four checks. They compare the two directly and are the fastest
route to the disagreement:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py"  .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py"   .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py"  .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_report.py" . <each claimed task>
```

## 4. Reconcile, and look for the cases that mislead

For every `CLAIMED` row, apply the recovery table in `run` §3 — liveness over
the **whole agent subtree**, then the heartbeat, then the tree's mtimes (P-14).
Then check specifically for these, because each one makes a lost task look like
a finished one or the reverse:

| Looks like | Might actually be | How to tell |
|---|---|---|
| the work was lost — `RUNNING`, clean tree | committed under **somebody else's message** (F-17) | `check_scope` reporting `misattributed-write`; `git log` for the scope's paths |
| a finished task — title `DONE` | never verified; the verifier ran and FAILed, or never ran | `RECORD.md` has no `verify … PASS` line for it |
| nothing in flight — no heartbeat | a supervisor that died **before** its first dispatch | the task file is dirty but no commit exists |
| a live claim | a task stopped for a question, whose title was never updated | `QUESTIONS.md` has an open item naming it (P-27b) |
| a stale claim | a live worker under a completed supervisor | a live child in `ListAgents` (P-14) |

**An uncommitted change under a claimed task's scope is work, not debris.**
Read it before deciding anything. A predecessor's uncommitted diff is
frequently the most valuable thing in the tree — it is what the worker had
learned and had not yet said.

## 5. Report before you act

Tell the client, on the charter's `Client channel`, in under twenty lines:

- **what was in flight** and how long ago it last moved
- **what is uncommitted**, path by path, and whether it looks like work or debris
- **what the checks say**, especially where the record and the tree disagree
- **what has been waiting for them** — open questions, and for how long
- **what you propose to do**, task by task: continue, re-dispatch, or ask
- **what re-dispatching would destroy**, if anything

**Then stop and wait.** This is a gate, not a courtesy. The client may know
something the record cannot: that a task was finished and the commit did not
land, that the interruption was a machine reboot rather than a failure, that
the whole thing should be abandoned. Re-dispatching a task whose worker had
uncommitted findings costs all of them, silently.

**Where the channel is `none`**, proceed on the safest reading — continue what
is clearly live, leave anything ambiguous stopped, and record every judgement
as an assumption for the next checkpoint. Do not re-dispatch anything whose
loss you cannot rule out.

## 6. Only then, hand back to the loop

On the client's word: take the writer lock, record a `resumed` line and a
`stale claim` line per recovery in `RECORD.md`, and run `/devteam:run`. The
loop's own startup will reconcile again, which is harmless and is one more
chance to notice something.

## What resuming must never do

- **Never re-dispatch before reporting.** The whole point.
- **Never stash or discard an uncommitted change** to get to a clean tree. A
  clean tree is not the goal; an accurate one is.
- **Never take the lock from a session you have not established is gone.** Two
  writers is the failure the design exists to prevent, and an interruption is
  exactly when it is most tempting.
- **Never quietly repair the record.** If the board and a task file disagree,
  say so, fix it deliberately, and record that you did — a resume that tidies
  is a resume that erases the evidence of what went wrong.
