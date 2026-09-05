# What the first live run left to do

The queue after `devteam`'s first end-to-end run: one project, ~24 hours,
around 130 findings, of which roughly five in six were defects in this pipeline
rather than in the software it was building.

Everything here was **deferred deliberately**, with a reason. Nothing on this
list is a bug report — those were fixed as they arrived. This is the work that
only makes sense once the run has stopped and the whole thing can be read at
once.

---

## 1. Manager rotation — the one layer that never resets

**The problem, measured.** Every role in this design gets a fresh context except
one. A worker is disposable: fresh context, one step, gone. A supervisor lives
for a single task and dies with it, so its context is bounded by task size. The
**manager runs for the whole project** — and P-17 requires every supervisor
report to arrive with every worker report appended verbatim, so it reads
everything.

On the first run that was **897 KB of task files, roughly 230,000 tokens**,
passed upward verbatim — plus a 240 KB record, a 76 KB decision log and a 43 KB
question log that it re-reads throughout.

The tension is structural rather than accidental: **the rule that makes the
manager trustworthy is the rule that makes it the bottleneck.** Verbatim
passing exists so nothing is laundered through a summary. Its cost is that the
single role everything flows through is the one that never resets.

**Why compaction is not the answer.** Repeated compaction is a copy of a copy —
each pass is a lossy re-encoding and the result drifts from the original. A
fresh context reading the **durable state** does not drift, because the board,
the record, the task files and the decisions *are* the state. That was already
the design; nothing had used it for this.

**The shape.** Rotate the manager at a checkpoint: the outgoing one releases the
writer lock, the incoming one takes it, reads the state, and — per `resume` §0 —
**asks the outgoing session what it could not determine from the files** while
that session is still alive. Every question asked is logged as a defect in the
record, because a record that needed a conversation to interpret is a record
that will fail the next reader, who may have nobody to ask.

**The open question, and it is a real constraint.** *When* to rotate. "When
context warrants it" is not implementable, because **a manager cannot measure
its own context** — there is no observable it can read. So the trigger has to be
external and countable: every checkpoint, every N closed tasks, or a wall-clock
figure. And the cadence should be set so that compaction is **rare rather than
merely survivable**, since the whole argument for rotating is that compacting
repeatedly degrades.

This matters most for the case the pipeline is aimed at: a project running
mostly unattended for days or weeks.

---

## 2. Sweep for pairs of rules that cannot both hold

Nine known instances, each one two rules that are correct alone and contradict
in conjunction, with nothing anywhere noting the tension. They were found by
**workers hitting them**, one at a time, over a full run.

A reviewer reads rules one at a time; a worker is the only party required to
satisfy all of them simultaneously — which is why every instance was found from
below. Nobody has ever read the rule set *looking* for the shape.

The question that has a good hit rate on this codebase: not *"is this rule
right?"* but **"what else must be true at the same moment, and can both hold?"**

---

## 3. Audit every check against F-113

**Name the rule whose two sides a check compares. If you cannot name one, the
check is proposing a rule rather than enforcing one** — and its false positives
are that missing rule showing up, not noise to tune away.

That test arrived late. It has been applied to three checks and found all three
proposing rules; the rules were then stated, which is what made the checks
legitimate. **Every other check predates the test and none has been audited
against it.**

---

## 4. The backwards pass

**A project learns forward only.** Three measured instances: a charter signed
before a template gained a row never acquires it; a manifest written for one
purpose is never re-read for another; a lesson about how to write an acceptance
criterion is applied to every later criterion and never backwards over those
already in the file.

Most of this cannot be checked — telling a criterion that names a **method**
from one that names a **property** is a semantic reading, and this project
refuses those everywhere. What it can have is a **moment**, and the final review
is the only place every criterion is read at once.

Applies to this plugin too, not only to projects using it: the earliest skills
here were written before most of what the run taught.

---

## 5. Two mechanisms deferred with their triggers

Neither is a good idea yet. Both are recorded so they are not re-derived from
scratch, and neither should be built before its trigger fires.

**Accepted findings.** A block recording a finding that may not be fixed, so the
resting count returns to zero and stays a signal. The framing decides who
reaches for it: read as *suppress*, a manager adds entries when the tree is
annoying; read as *restore the zero*, they are reluctant, because every entry
costs the signal they are keeping. **Trigger:** the day a manager reads a
finding count and does not read the finding under it. Reported as *not yet*.

**The narrow unscoped-commit refusal.** On an unscoped `git commit`, read
`git diff --cached --name-only` and refuse only if a staged path lies outside
the caller's live scope. It races, and it needs a scope the caller may not have.
**Trigger:** an unscoped commit that actually carries another task's staged
work. The evidence for building it does not exist — it was looked for.

---

## 6. The ceremony question, narrowed

Not *"is this too heavy?"* — it is, for small work, deliberately, and a
simplification argued from small-project ergonomics is out of scope by
construction. The tool is aimed at work where being wrong is expensive, and its
baseline is **build, discover it is wrong, build it again**.

What stays open: **which individual steps buy nothing on any project?** Only two
such findings exist and both came from people who **declined to use the thing** —
which says where the rest are, and it is not inside a run.

And a third test, from the purpose rather than the sizing: **a step that only
works when the operator already understands why it matters has failed at what
this is for.** That one has never been applied to anything.
