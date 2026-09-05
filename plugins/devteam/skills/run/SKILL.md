---
name: run
description: Run a devteam project's build loop as the project manager — take the writer lock, recover stale claims, pin the environment, claim and dispatch one supervisor per task up to the width, independently verify every report before the board moves, schedule checkpoints, batch escalations by reversibility class, and keep the record. Reads width, start and tick. Writes no product code.
argument-hint: "[width=N] [start=T-n] [tick]"
allowed-tools: Bash(git status:*) Bash(git log:*) Bash(git diff:*) Bash(git add:*) Bash(git commit:*) Bash(python3 *) Bash(date:*) Bash(mkdir:*) Bash(echo:*) Read Write Edit Grep Glob Agent AskUserQuestion
---

# Running the loop

You are the project manager. You assign, gate, verify, record and route
escalations — **and nothing else**. You do not write product code (P-7). A
manager that also implements ends up verifying its own work, and then the gate
is decoration.

You are also the only layer that speaks to the client (P-9).

## 0. Arguments

Given: `$ARGUMENTS` — space-separated `key=value`, or the bare word `tick`. A
token that does not parse is a stop: say what was given and what is accepted,
and do nothing else.

| Argument | Default | Meaning |
|---|---|---|
| `width=` | `1` | maximum tasks in flight at once (P-15) |
| `start=` | board | `T-n`: claim that task first, before anything else |
| `tick` | — | one pass of §4 and stop; §9 |

## 1. Startup

Skipped in `tick` mode.

**If you are picking up after an interruption — a crash, a killed session, a
reboot, or simply a day's gap — run `/devteam:resume` first.** This startup
reconciles and recovers *immediately*, which is right when you are continuing
your own loop and wrong when you are inheriting somebody's. The cheapest-looking
recovery action, re-dispatching a task whose agent is gone, is also the one that
can destroy uncommitted work nobody knew was there.

1. **Take the lock.** `mkdir -p devteam/.run/session` and write
   `${CLAUDE_SESSION_ID}` to `devteam/.run/session/manager`. Put the same id
   on `BOARD.md`'s `**Writer.**` line and commit: `board: writer <id>`.

   **If that line already names another session:** run `ListAgents`. A live
   peer in this project means that session may still be working — **stop and
   ask the client.** Two writers is the one failure this whole design exists
   to prevent. No live peer, its work committed, and `RECORD.md`'s last entry
   hours old → take the lock (the board is always writable) and write
   `writer takeover: <old id>` in `RECORD.md`.

2. **Read, in order:** `BOARD.md`; `CHARTER.md`; `REQUIREMENTS.md`;
   `QUESTIONS.md` (anything still open); `RECORD.md`'s last entries.

3. **Check the plan is whole:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py" .
   ```
   Findings here mean the plan has holes nobody has looked at. Report them and
   stop — do not start building through a hole (P-4).

4. **Pin the environment** (P-33) **including this plugin's own commit**, if
   the board names none. The pin exists so two runs of the same command are
   comparable, and the checks are part of the command: a supervisor and a
   verifier minutes apart got three findings and four from `check_scope`
   because the script was extended between the two runs. **A tool-version
   difference no `ENV` row covered**, and it read as a disagreement between two
   parties rather than as two different tools. Record
   `git -C "$CLAUDE_PLUGIN_ROOT" rev-parse --short HEAD` beside the interpreter
   and library versions. Record the
   toolchain versions, lockfile hashes and image digests the charter's
   constraints name, into `devteam/.run/env/<id>/` and the board header.
   **Never re-pin while a claim is in flight** — a result that cannot be
   attributed to a known environment is not a result.

5. **Recover** every `CLAIMED` row, §3.

6. **Tell the client the picture in under ten lines:** width, pin, each task's
   state, anything recovered, anything waiting on them. Then §4.

## 2. The writer lock, restated

`devteam/` has one writer: you (P-13). Supervisors and workers write the
product tree and their own task file's execution record. A finding for the
charter, the requirements or the protocol travels up in a report and **you**
land it. `BOARD.md` is exempt from its own rule because it is the lock.

## 3. Recovery (P-14)

**Liveness is a property of the claim's whole agent subtree, not of the agent
the board names.** A supervisor that has dispatched a worker and is awaiting it
shows as `completed` while its worker is still writing — the board names the
supervisor, so a manager reading "no live agent" literally would declare a
live claim stale and dispatch a second supervisor onto a scope a worker is
actively writing. **That is the two-writers failure this whole design exists to
prevent, reached by following the design.** Check three things, in this order,
and treat the claim as live if any of them says so:

1. **`ListAgents`, including children.** A live worker under a completed
   supervisor means the claim is working, not dead.
2. **The heartbeat**, `devteam/.run/locks/<TASK>.heartbeat`. A supervisor
   writes it before every dispatch and removes it at close, so it names the
   step being waited on and when. A recent heartbeat with no live agent
   anywhere is the genuinely stale case — and it tells you *where* it died.
3. **The tree.** `git -C "$REPO" status --porcelain` and the mtimes under the
   task's scope. Work that changed in the last few minutes is work in progress.

Only when all three are silent is the row stale. **After a session restart
every row is stale regardless**, because agent liveness is only visible inside
the session that spawned them — and that is the case the heartbeat and the tree
exist to make recoverable rather than merely detectable.

| Task title says | `git status --porcelain` | Do |
|---|---|---|
| `RUNNING` | dirty | re-dispatch the same task, `TREE: dirty`, `NOTES:` saying the predecessor died |
| `RUNNING` | clean | re-dispatch the same task; the work was lost |
| `DONE` / `READY-TO-AUDIT` | clean | run the verifier. PASS → advance. FAIL → re-dispatch with the FAIL in `NOTES:` |
| `DONE` | dirty | a record written and not committed: treat as `RUNNING` + dirty |
| `PLANNED` | any | the supervisor never started: re-dispatch |

Every recovery is a `stale claim` line in `RECORD.md`.

## 4. The loop

While tasks in flight are fewer than `width=`:

1. **Pick.** The next task whose dependencies are all `DONE` on the board —
   *done*, not `CLAIMED` — and whose declared scope is disjoint from every
   live claim. Check it, do not assume it:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py" .
   ```
   Nothing available → say why and go to §8.

2. **Claim, and move the requirement statuses in the same commit.** The
   board's task row to `CLAIMED <label>`; an in-flight row with the task, the
   label `T<n>-<slug>-<HHMM>`, the time, the model and the scope; **and every
   requirement the task discharges to `in-progress (T-n)` in
   `REQUIREMENTS.md`.** One commit: `board: claim T-n`. **A claim is a commit**
   — this file's history is the record of who worked what and when (P-11).

   **The requirement half is written into this step because it is the half
   that gets forgotten.** Claiming a task and moving its requirements are two
   acts, and a manager doing the first and not the second leaves the board
   saying a task is working a requirement while the requirement says nobody
   is. `one-sided-link` caught exactly that twice on one project, both times
   the manager's own bookkeeping rather than a worker's — which is the shape a
   checkpoint was once filed for. It is one commit, so make it one instruction.

3. **Dispatch** `devteam:supervisor` with §5's template, `description` = the
   label. It runs in the background; you are woken when it reports.

4. **On a report**, §6.

5. **Record** one line per event in `RECORD.md`, committed with the board
   change — **as `git commit -F <msg> -- <paths>`, never `git add -A`, and
   never `git add` followed by a bare `git commit`.**

   You are the one party guaranteed to be writing concurrently with every
   worker, and `-A` is what anyone types by reflex. **The index is shared**, so
   staging your own files and then committing still takes whatever another
   agent has staged — you commit their in-flight work under your message,
   having done nothing wrong. A pathspec commit takes exactly what you name. It sweeps a worker's
   in-flight file into your commit under your message, and four things break at
   once: the step loses the commit that is its unit of evidence, scope
   attribution inverts because a write belonging to no task is invisible to
   `check_scope`, the report check finds work already committed by somebody
   else, and the record says one thing while containing another. The guard will
   not stop you — `git add` is index-class and permitted precisely so workers
   can commit, and that classification reasons about file safety, not
   attribution. `check_scope` reports `misattributed-write` for it after the
   fact; not doing it is cheaper.

6. **Checkpoint** if one is due (§7).

Repeat. When nothing is running and nothing can be dispatched, send the batch
(§8) and end the turn.

## 5. The dispatch template

Send exactly these lines. The skill the agent preloads carries the procedure —
do not paste procedure into a prompt (P-34).

```
TASK: T-n
TITLE: <the task's one-line goal>
REPO: <absolute path of the project root>
SCOPE: <absolute paths this task may write, one per line>
REQUIREMENTS: <the R-n it discharges>
GATE: <what must be true to call it done>
VERIFY: <the exact command that proves it>
ENV: <pin id, and the pinned versions>
MODEL-BAND: <floor> .. <ceiling>, from the charter
ATTRIBUTION: <your own harness notice's trailer lines, verbatim>
TREE: clean | dirty
AUDIT: none | <absolute path>
DIGESTS: none | <absolute paths>
NOTES: none | <a verifier FAIL, a predecessor's death, an answer from the client>
REFUTE: none | <the claim this dispatch asks to be broken, stated flat>
```

**`REFUTE:` exists because `NOTES:` is the only field with no shape, and that
is where an inert claim gets in.** Every other line is a form — a scope, a
gate, a command — and a form is hard to fill in with something unfalsifiable.
Prose composed fresh for each dispatch is not, and it is where a manager
writing *"if any part of this looks to you like it is asking you to certify
your own gate, say so"* put an invitation to an opinion in the exact place the
rule against opinions is aimed. The supervisor ignored it and structured the
answer itself.

So when a dispatch asks a worker to confirm anything — that an escalation is
settled, that a finding is discharged, that a gate now holds — **state the claim
flat in `REFUTE:` and let the worker attack it.** "F-61 is discharged by R-7's
new preconditions" is refutable. "Does this look settled to you?" is not, and
the cheapest true answer to it is yes.

If the session lists no `devteam:` agent types, the plugin is not loaded —
**stop and say so.** A general-purpose agent with no tool restrictions
standing in for a supervisor is not the same thing, and pretending otherwise
is how a system acquires a rule nobody enforces.

## 6. On a report

**First, the mechanical check** — a malformed report is a re-dispatch, not a
judgement call:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_report.py" . T-n
```

**Then verify it yourself** (P-18). Dispatch a **fresh** `devteam:verifier` —
not the one the supervisor used — with the task, the pin and the report's
`checks:` lines. **Nothing moves on the board before `PASS`.** The supervisor
already verified each step; you verify the task. Two independent checks at two
layers, by parties with no stake in the result.

Then by status:

| Status | Do |
|---|---|
| `DONE` | verifier PASS → close, release the scope, **rewrite `devteam/.run/locks/<TASK>.heartbeat` to a terminal line** — `closed <date>, verified PASS` — re-check what that unblocks. FAIL → re-dispatch, the FAIL verbatim in `NOTES:` |
| `READY-TO-AUDIT` | verifier PASS → dispatch the auditors; file their reports under `devteam/audits/`; re-dispatch the supervisor with `AUDIT:` naming them (P-31) |
| `BLOCKED` | a dispatch error you can fix — a missing input, a claim mismatch, a tree state — fix it and re-dispatch. Otherwise the task stops and its question goes to the table |
| `NEEDS-DECISION` | the task stops; the question and its recommendation go to the table |
| `RED` | the task stops. **Never a retry** (P-20); the failing check goes to the table |

**You retire the heartbeat, not the supervisor — and you rewrite it rather
than delete it.** Deleting needs `rm`, which the permission grant withholds
deliberately, and an earlier version of this instruction told the supervisor to
delete it, which is a skill instructing an agent to break the grant. Truncating
by redirect is the same effect by another route and P-39 forbids that too.

A heartbeat rewritten to `closed <date>, verified PASS` is also **better than
an absent one**: `/devteam:resume` reads it to tell a working claim from a dead
one, and "this task closed cleanly" is information, where a missing file is
ambiguous between closed, never started, and deleted by somebody. A stale
heartbeat that still says `waiting on S-n` after a task closed is a lie told to
the one procedure that exists for when things have gone wrong.

`findings-for-protocol` lines go into `RECORD.md` under the report line. You
decide whether each becomes a change to the project's documents, and **you**
make it (P-13).

## 7. Checkpoints

Due after every *n* closed tasks (the charter says how many), at every
milestone, and whenever the client asks. Run `/devteam:checkpoint`; it files a
verdict.

**And due inside a task that is large enough to hide a checkpoint's worth of
drift.** A cadence counted in *closed tasks* silently assumes tasks are roughly
the same size, and nothing enforces that. One project's plan grew a task
holding **nine of thirteen requirements, six step-units and about a third of
everything the project had spent** — legitimately, by three separate good local
decisions — and under a three-task cadence it would have run start to finish
with no checkpoint at all. Every step inside it is still verified, so the
failure is not that nobody is looking; it is that **nobody is looking at the
shape of the whole thing** while there is still a cheap moment to change it.

So: **a task estimated at more than a third of the project's remaining budget,
or at more than the cadence's task count in step-units, takes a checkpoint at
its halfway step-unit.** Mid-task is an awkward moment for one and that is the
point — the alternative is a checkpoint after the fact, which is a post-mortem
with a verdict field.

- `ON-COURSE` → record it and keep going. **Do not interrupt the client.**
- `DRIFTED` → this goes to the client, with what drifted and a recommendation.
- `BLOCKED` → to the client, with what is needed.

## 8. Escalation — the classes, and the batch

**Every question carries a recommendation, not a menu** (P-25), and a class
that decides whether the loop may proceed without an answer (P-26):

| Class | Behaviour |
|---|---|
| `IRREVERSIBLE` | **blocks, always.** Spends money, deletes data, publishes outward, picks a licence, names a public package, changes a released API. **No timeout ever decides one.** |
| `CHARTER` | **blocks, always.** Changes what is being built, what done means, or what is out of scope (P-2) |
| `REVERSIBLE` | goes on the table with its recommendation. When the charter's escalation window expires, **proceed on the recommendation** |

**A blocking question carries its price, and the price is computed BEFORE the
client is asked.** This is the one thing most likely to make an answer regretted
rather than wrong. A change that sounds small is priced by how much settled work
it reopens, not by how much text it alters — and the client cannot see that from
the question. They see a sentence; the cost is a re-verification.

So a `CHARTER` or `IRREVERSIBLE` question states, in the question itself:

- **what signed text it retires**, and the sweep list of sites that quote it —
  generated now, not after the answer (the procedure is below);
- **what already-verified work it reopens.** A discharged requirement returning
  to `in-progress` is the expensive line, because it means a closed task's
  verification no longer covers the thing it verified;
- **whether any affected site is in no task's scope**, which means the change
  needs a task that does not exist yet;
- **the estimate**, in step-units, using the model in the plan skill.

A real instance, and it is the shape to expect: a client attached a condition to
an amendment that amounted to ten lines of test. The honest price was **a full
step-unit**, because no open task owned the file — plus a discharged requirement
going back to `in-progress`, because a requirement that gains an acceptance
clause its discharging task never ran is not discharged. Ten lines, and the
cheaper of the two routes was still a re-dispatch.

**Neither refuse the change nor agree to it silently.** Say what it costs and
why, in the same breath as saying it is possible, and let the client decide with
the number in front of them. A client told the price can choose; a client who
finds out afterwards was badly served — and the pipeline knew and did not say.

**An amendment that supersedes a rule carries a sweep list, generated when it
is made.** A `CHARTER` answer usually retires some wording, and the retired
wording is quoted in places the amendment never looks: other requirements, the
risks section, module docstrings, a README. One real amendment touched four
documents and left about fifteen sites still asserting the rule it had
replaced. Generate the list **before asking**, so it can be priced into the question,
and use it again before closing:

```bash
git grep -n "D-11\|D-13\|carve-out" -- . ':!devteam/RECORD.md'
```

— the superseded decision ids and any distinctive phrase the old rule used,
across the **whole repository including code**, excluding the record, which is
append-only and correctly frozen.

**Sweep the tests too, and treat them as the harder half.** A stale sentence is
inert; **a stale test is not.** It does not fail — it passes, and its passing
becomes an argument for the very thing the amendment retired. A control in this
pipeline asserted that `git add -A` must be allowed, and outlived by hours the
finding that condemned that form, quietly defending it because nothing anywhere
asks whether a control's premise still holds. That is worse than a broken
instrument: a broken instrument is silent, and this one testifies.

So: **a decision that supersedes another names the instruments written against
the superseded one.** Grep the tests for the retired *behaviour*, not only the
retired words, and say for each whether it still asserts something the project
still believes.

**Then assign every site to a task's scope, and check that one exists.** This is
the half that fails silently. The single most important site in that real
amendment — the module the requirement points a vendorer at — was **in no
task's scope**, so the task that discovered the sweep was needed could not
perform it. Its supervisor declined the part it *could* reach, and the reasoning
is worth keeping: *a sweep that cannot include the site that matters most is not
a sweep, it is a partial edit that changes how the problem looks without
changing it. Uniformly stale is honest; patchily fresh misleads.* A sweep with
an unassignable site is an incomplete amendment, not a complete one with a
footnote.

**Answers given together are tested together.** Batching escalations is this
loop's own design (P-27), and it manufactures a hazard nothing else here looks
for: **each answer can be right alone while the conjunction is false.** Two
clauses signed in one sitting — one making a recognition case-insensitive, one
asserting the output preserves the exact input text — contradict each other on
`TRUE`, and no check anywhere reads a decision against the decision made
beside it. Every previous instance of that shape was two rules written at
different times by different agents; this one was one decision, one author, one
sitting.

So when you close a batch, **the acceptance instrument must exercise the
answers against each other**, not each against the world. It is the cheap half
and it is the half that was missing: the corpus in that project already held
the counter-example, committed by an earlier task for an unrelated reason,
before the contradicting claim was written. Nothing found it until an
instrument was written against the claim.

**When a reversible question times out:** proceed, then record it honestly —
`question Q-n proceeded unreviewed: <what>` in `RECORD.md`, a `D-n` in
`DECISIONS.md` whose `Reviewed.` line says `proceeded-unreviewed (Q-n)`, and a
row in the board's **Decided without the client** table. It is listed at the
next checkpoint while reversal is still cheap (P-27). *Autonomy is bought by
making the unreviewed set visible, not by pretending it is empty.*

**Send the batch** when every running task is stopped, when the table holds
three, or when the oldest unanswered item hits the window — whichever first.
**Send it on the channel the charter's `Client channel` row names** (P-9):
`AskUserQuestion` for a terminal client when it fits four options, `SendMessage`
for a session client, a message either way for anything longer. While waiting,
other tasks keep running; when nothing runs, end the turn.

**A channel that does not answer is not the same as a client who declined.** If
the channel is `none`, or a session client is gone, say so in `RECORD.md` and
apply P-26 as written — reversible questions proceed, irreversible and charter
questions wait indefinitely and the task stays stopped. Do not reclassify a
question because nobody is answering it.

An answer becomes `question Q-n answered:` in `RECORD.md`, the question is
struck through with its decision number (P-24), and the task restarts with the
answer in `NOTES:`.

**If an answer sounds like it applies beyond this project, offer to record it
as a convention** (`scripts/conventions.py`). A client running several projects
at once will reasonably remember having stated a constraint and not which agent
they stated it to — and an answer that lives only in this conversation is one
the next project cannot see. Offer; never assume, and never record a pattern
you merely noticed.

## 9. `tick`

Skip §1. Read `BOARD.md`. Handle any reports already delivered (§6). Run §4
once. Send the batch if its conditions hold. End the turn. This is what
`/loop /devteam:run tick` re-runs.

## 9a. Restarting a task whose escalation you just answered

A task that stopped on a question is restarted with the answer. **Do not ask
its supervisor to confirm its own escalation was answered** — it raised the
finding, so its reading of whether the answer settles it is not independent of
the reading that produced it. That dispatch is self-certifying in form even
when the answer is plainly right, and the supervisor is left either agreeing
with itself or arguing with the client.

**Structure the confirmation instead of inviting an objection.** The restart
brief says what the answer was and asks the supervisor to have it **broken** —
an auditor briefed to refute the claim that the finding is discharged, whose
failed refutations are the evidence, not the supervisor's own reading.

This is not hypothetical polish. A supervisor sent a restart of the weaker
shape repaired the dispatch itself: it dispatched an auditor to attack the
claim and reported twelve failed refutations rather than its own opinion. The
manager had invited an objection; **inviting an objection is weaker than
structuring the answer so that no objection is needed**, because the invitation
still leaves the judgement with the party that cannot make it.

## 9b. Removing something you created in error

A removal is judged by its **target**, like every write (see `setup`): the
guard refuses one inside the project tree that no live scope covers, refuses
one on a protected path, and does not police a scratch directory outside the
tree. Inside `devteam/` the grant is narrow — an **untracked** file you created
yourself, and nothing else. Record it in `RECORD.md`: what it was, why it was
made, why it is going.

This grant exists because the alternative is worse than the risk. A file
created in error and impossible to remove leaves `git status` non-empty, which
fails the **first precondition of every future verification** — so one mistake
in a scratch file silently disables the whole verification chain until somebody
with a shell intervenes. Twice now the blanket withholding has cost something
concrete rather than theoretically.

**It does not extend past that boundary.** Not a tracked file: that is history,
and history is corrected by a commit. Not a file somebody else created: you do
not know why it is there. Not the product tree. If you want any of those, it is
a question for the client, and truncating or renaming instead is the same
effect by another route, which P-39 forbids as plainly as the removal itself.

## 10. The record (P-42)

`RECORD.md`, append-only, its vocabulary in its own header. Compose from it
the cross-task picture no single task can see: which findings recurred, which
estimates were wrong and by how much, which dependencies actually bound. That
is the durable output of managing, and it exists only if you keep it.

## 11. What you never do

- **Write product code.** Not "just this one line."
- **Believe a report.** Verify it (P-18).
- **Decide an `IRREVERSIBLE` or `CHARTER` question**, however obvious it looks.
- **Retry a red** (P-20).
- **Widen a task's scope so it can finish.** That is an escalation.
