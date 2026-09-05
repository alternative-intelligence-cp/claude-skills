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

## 3b. Was the priority order honoured?

If the charter names one (P-20b), every decision that traded one priority for
another should cite it and say which was sacrificed. Read them. **A sequence of
individually reasonable trades in the same direction is how a project ends up
fast and unsafe with nobody having decided that** — no single decision looks
wrong, and the drift is only visible in aggregate, which is here.

Anything that sacrificed the *highest* priority should have been a `CHARTER`
question and stopped for the client. If one did not, that is the finding.

## 3c. Has the verification layer ever rejected anything?

Every check in this pipeline ships a negative control, because a check that has
never failed has not been shown to work (P-35). **The verification layer is
held to no such standard, and it is the layer everything else rests on.**

Count it:

```bash
grep -coE "verify [A-Za-z0-9-]+ PASS" devteam/RECORD.md
grep -coE "verify [A-Za-z0-9-]+ FAIL" devteam/RECORD.md
```

**A project whose verify step has never returned FAIL is indistinguishable from
a project with a rubber stamp**, and you cannot tell which one you have by
reading the verdicts — only by counting them. On the project where this was
first measured the answer was nine verdicts, seven PASS and two FAIL, both on
the same task. That does not prove no verifier ever waved something through; it
proves the layer *can* reject, which is the whole of what a negative control
establishes anywhere else.

Report the ratio in the checkpoint whatever it is. **Zero FAILs is not a
finding on a small project** — it is a question about whether the bar has been
tested, and the answer may honestly be "not yet". Treat it as one number that
must be looked at, not as a threshold to pass.

**This step can only count what the briefs asked for, and that is not a
caveat — it is the thing most likely to make it lie.** A clean §3c produced by
verifier briefs that never invited disclosure looks exactly like a clean §3c
produced by verifiers with nothing to disclose. The count is not a measurement
of the verification layer; it is a measurement of the layer *as the briefs
shaped it*. So read one dispatch before you believe the number, and if the
briefs did not ask for gaps as a result, say so here instead of reporting a
ratio.

**Then ask what the verifiers could not do.** A verifier that quietly downgrades
an independent rebuild to an independent reading and reports PASS is
indistinguishable from one that rebuilt, and nothing downstream can tell them
apart. The mitigation is in the dispatch, not here: **a verifier brief asks for
"anything you could not reproduce" as a result rather than as an apology**, and
says plainly that a disclosed gap is worth more than an undisclosed workaround.
Read the record for those disclosures and list them. A gap you can see is not
the risk; its invisibility would have been.

What stays unknowable by construction is whether a verifier had a gap it did
not disclose. The only mitigation for that is the two independent layers, and
an undisclosed gap would have to be common to both.

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

**Four rules on how this document is written, before anything about what it
contains.** GATE 4 requires **five count-and-enumeration pairs in one
document** — every done-means with its evidence, every requirement discharged
or struck, every decision the client never reviewed, cost against estimate, and
what is knowingly left undone. That is the shape of the worst writing failure
this project has recorded, five times over, in the document written *last* —
by whoever has just spent a run cataloguing that failure and is therefore most
likely to believe they are immune to it.

1. **Every count is produced by a command run at the moment of writing, with
   the command named beside the number.** Never a figure carried down from
   earlier in the record: every one of those was true when it was written.
2. **Every enumeration is read off the same output as its count.** One run, one
   command, one sitting. A total and its members are two claims, and the second
   is the one nobody re-derives — because the first one's provenance launders
   it.
3. **No completeness claim unless the full set is printed above it.** "And
   nothing else" is a statement about a set, writable only by somebody who has
   just read the set.
4. **Name the commit this was written against, and re-run the checks at
   signing** with their output pasted rather than summarised.

**None of these asks you to be careful, and that is the point.** They ask for a
command on the same line as its number — which is **visible in the finished
document whether or not you were careful**, so a reader can check compliance
without re-running anything. That is the only property that survives the fact
that attention does not: five times here somebody committed a failure in the
same artifact where they had just documented it.

They are written down rather than remembered because a mechanism that depends
on an agent recalling it at the moment of writing is not a mechanism.


**Walk the run's lessons backwards over the documents written before them.**
This is the only moment every requirement, goal and criterion is read at once,
and it is the last one — there will not be another pass over the artifacts this
project wrote early.

**A project learns forward only.** Three measured instances of the same gap:
a charter signed before a template gained a row never acquires it; a manifest
written for one purpose is never re-read for another; and a lesson about how to
write an acceptance criterion is applied to every subsequent criterion and
never backwards over the ones already in the file. Documents get written once
and improved only where somebody happens to be standing.

Most of that cannot be checked — telling a criterion that names a **method**
from one that names a **property** is the semantic reading this project refuses
everywhere. The measured case: a requirement whose acceptance said *parse with
`ast`, collect the roots, assert each is standard library*. A test doing
exactly that **over six of the seven shipped modules** satisfies every word of
it and reports green. A criterion that names a method cannot detect
under-application of that method.

So this is not a check, it is a reading, and these are the questions worth
spending it on:

- **Which acceptance criteria describe a practice rather than an obligation to
  demonstrate?** The good form is not *"the tests are marked"* but *"every
  unmarked case appears in the guard's input set or carries a named
  exclusion."*
- **Which documents predate a decision that would have changed them**, and were
  never revisited because nothing pointed at them?
- **Which artifacts were written before the rule they should follow existed?**
  The first requirements in a project are always the least informed, and
  nothing in the loop ever goes back.


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
