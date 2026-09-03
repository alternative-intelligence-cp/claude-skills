---
name: status
description: Report where a devteam project actually stands — what is running, what is blocked, what is waiting on the client, what was decided without them, and what the evidence says has genuinely been discharged. Reads the board, the record and the tree; changes nothing.
argument-hint: "[project path]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git log:*) Read Grep Glob
---

# Status

Answer the question **"where is it?"** honestly, from evidence, in under
twenty lines. **Change nothing** — not the board, not a title line, not a
stale claim you happen to notice. Say it is stale and let the loop recover it.

## Read, then report

`BOARD.md` for the live picture · the last entries of `RECORD.md` · task title
lines for real states · `git log` for what actually landed.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py" .
```

## Report, in this order

1. **Phase and width** — onboard, plan, build, harden or deliver.
2. **In flight** — each task, since when, on what model, and *what its
   supervisor last reported*. A claim with no live agent is **stale**: say so.
3. **Waiting on the client** — every open question, its class, and how long it
   has been waiting. Put this above "done" if anything is here; it is the only
   part the client can act on.
4. **Decided without the client** — count, and the ones still cheap to
   reverse (P-27).
5. **Progress, by evidence** — requirements `discharged` **with acceptance
   evidence recorded**, out of the total. Not tasks closed; not a percentage
   of anything. A task closed without its acceptance criterion run has not
   discharged its requirement (P-5).
6. **Blocked** — what, and on which named task or question.
7. **Cost** — spent against estimate, if the record has it.

## Be accurate rather than encouraging

- Distinguish **`DONE` and verified** from **reported done and not yet
  verified**. They are not the same claim and the second is worth less.
- If `check_trace` reports findings, say so here. A project that looks 80%
  done and has three uncovered requirements is not 80% done.
- If the last checkpoint said `DRIFTED` and nothing has changed since, that is
  the headline, not a footnote.
- If nothing has happened since the last status, say that plainly. Padding a
  status report is how a project loses a week without anyone noticing.
