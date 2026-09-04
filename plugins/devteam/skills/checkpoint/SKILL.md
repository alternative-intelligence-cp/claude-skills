---
name: checkpoint
description: Diff what a devteam project has actually built against its signed charter and file a dated verdict — goal by goal with the evidence recorded, what diverged and whether anyone decided it, which reversible questions the loop settled without the client, and cost against estimate. Run on a schedule, at milestones, and on demand.
argument-hint: "[project path]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git log:*) Bash(git diff:*) Bash(git add:*) Bash(git commit:*) Read Write Edit Grep Glob AskUserQuestion
---

# Checkpointing

**A verdict with evidence, not a status update.** This is the mechanism that
answers the question the whole pipeline exists for: *is what is being built
still the thing that was asked for?*

Nobody notices drift from inside a task. Every task can be correct, verified
and on time while the sum of them quietly becomes a different product. Only a
scheduled diff against the charter catches that, and only if it is adversarial
(P-32): the question is **"what would have to be true for this to have gone
wrong, and is it?"** — never "does this look about right", which it always
will.

## 1. Does what exists satisfy the charter?

Walk **every charter goal** down the chain and record what you find at each
step. Do not skip a goal because you remember it being handled.

```
G-n  →  the R-n that satisfy it
     →  the tasks that discharged those
     →  the acceptance evidence ACTUALLY RECORDED in their reports
```

**A goal you cannot walk down that chain is the finding**, and it does not
matter how confident anyone is that the work was done. "Discharged" means the
acceptance criterion was run and its output is in the record (P-5).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py" .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py" .
```

Then go past what the scripts can see: **read the acceptance criteria and ask
whether what was built actually satisfies them**, rather than whether a
command exited zero. A test can pass and still not test the requirement.

**And ask the question no script can: do the requirements under this goal
*cover* it, or merely exist under it?** A goal that quantifies — "any failure",
"every field", "all responses" — answered by requirements that enumerate two
cases is a goal that will keep producing surprises, one per missed member. The
trace is clean and the goal is half built. When you find one, the finding is not
the missing case; it is the requirement's shape, and the fix is to restate it as
a rule with the cases as its tests.

## 2. What diverged, and did anyone decide it?

Divergence recorded as a `D-n` is normal and healthy — plans meet reality.
**Divergence nobody recorded is what this exists to catch.**

Read the diff since the last checkpoint against the plan that was approved:

- something built that no requirement asked for → scope creep, or a
  requirement nobody wrote down
- something in a requirement that quietly did not get built
- a decision visible in the code that is in no `D-n`
- a task whose scope grew

For each: **decided, or drifted?** Say which, with the path and line.

## 3. What proceeded without the client?

Every `REVERSIBLE` question the loop settled on its own recommendation (P-27)
— from the board's **Decided without the client** table and the record.

List each with what was decided and **whether it is still cheap to reverse**.
That last column is the one that matters: a reversible decision stops being
reversible once six tasks are built on it, and this is the last moment it is
free.

**This section is why the autonomy is honest.** If it is empty because nothing
timed out, say so. If it is long, that is a signal the escalation window is
too short or the client is not reading their batches — and that is worth
saying too.

## 4. Is the plan still right?

- **requirements that turned out wrong** — and whether anyone said so
- **tasks that were mis-sized** — estimate against measured (P-41). A task
  that cost triple is a finding about the plan, not just a number
- **dependencies that actually bound**, versus what the graph predicted
- **findings that recurred** across more than one task — the same mistake
  twice is a process problem, not two accidents
- **currency rows now stale** (P-37)

## 5. The verdict

| Verdict | Means | Then |
|---|---|---|
| `ON-COURSE` | every goal traceable to evidence; divergence all recorded | file it, keep going, **do not interrupt the client** |
| `DRIFTED` | a goal unsatisfied, or divergence nobody decided | **goes to the client** on the charter's `Client channel` (P-9), with what drifted and a recommendation |
| `BLOCKED` | the loop cannot proceed | to the client, with exactly what is needed |

Be willing to write `DRIFTED`. A checkpoint that has never returned anything
but `ON-COURSE` is a checkpoint nobody should trust — it has not been shown to
be capable of failing, which is the same standard the checks are held to
(P-35).

## 6. File it

`devteam/checkpoints/C-n-<date>.md`, from
`${CLAUDE_PLUGIN_ROOT}/templates/checkpoints/CHECKPOINT.md`. Commit it, and
add `checkpoint C-n <verdict>` to `RECORD.md`.

**Never edit a filed checkpoint.** A checkpoint that could be revised in the
light of later events is not evidence of anything — it is a description of
what was believed after the fact. If it was wrong, the next one says so.

## The final checkpoint (GATE 4)

At delivery, the same procedure plus:

- **every** `DM-n` from the charter's "Done means", each with its evidence
- every requirement `discharged` or explicitly `struck` with a decision
- the complete list of decisions the client never reviewed
- total cost against the original estimate
- what is knowingly left undone, and why

Then the client chooses one of three, and they are different things:

- **accept** — the cycle is closed and the project is done;
- **amend** — findings come back as new requirements under the same goals,
  which is a charter amendment (P-2) and not a bug list;
- **iterate** — the goals held, and using the thing taught something the
  specification could not. `/devteam:iterate` opens the next cycle carrying
  the charter, decisions, record and audits forward.

**Offer the third explicitly.** A client who is not told iteration exists will
either ask for a bug fix that is really a redesign, or start again from an
empty directory and throw away every decision this cycle recorded — and the
second cycle's whole advantage is that the first one's reasoning is still on
disk.
