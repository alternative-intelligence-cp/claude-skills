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

## 5. Wrappers for irreversible operations

**The idea:** rather than hoping an agent remembers the rules, wrap the tools
that can cause unrecoverable loss so the wrapper enforces them — a `git` wrapper
that requires an absolute path and refuses a relative one, and similar for
anything else destructive.

**The hard part, and the author named it when proposing it:** *provided we can
get the agents to use them with consistency.* A wrapper an agent can bypass by
calling the real tool is a rule, not a mechanism — the same class of failure as
the interpreter heredoc, where the safe path exists and the ergonomic path goes
around it.

**There is an answer and the pipeline already owns it: the permission
allowlist.** Setup writes it. An allowlist that grants `Bash(devteam-git:*)` and
does *not* grant `Bash(git:*)` makes the bare call require a prompt, which is
enforcement at the harness rather than convention in a document. The cost is
real and has to be priced: every uncovered subcommand becomes a stop, which
fights the unattended-operation goal. PATH shadowing is the other option and is
worse — invisible, and its failure is silent.

**Where a wrapper genuinely beats the guard, and it is not "safer".** The guard
*refuses*. A wrapper can make a dangerous thing **deliberate rather than
forbidden** — an explicit flag, a required reason, a logged justification. That
matters because outright refusal is what produced several of this run's worst
findings: a rule a worker must break to do the work right, met three times, each
time because the only options were comply-and-fail or breach-and-report. A
wrapper offers a third: do it, on the record, having said why.

So the shape worth exploring is not "wrap git to be safe". It is **wrap the
operations whose refusal currently creates a rule conflict**, and let them
through under a signature.

---

## 6. Keeping a long-lived role's context fresh

**The idea:** long-lived roles periodically re-read the important material, so
it stays in the attended part of the context rather than drifting into the
middle. Since context usage is not measurable from inside, some external trigger
— time, or a count.

**What exists already:** a `SessionStart` hook re-injects a manager's bearings
after a **compaction or a resume**. That covers the discontinuous cases. It does
nothing for **slow drift**, where nothing has been compacted and the charter is
simply two hundred thousand tokens back.

**The correction worth making before building anything.** A periodic refresh is
the *fallback*, not the primary. The stronger form is **re-read at the point of
use**: a manager about to answer a charter-class question re-opens the charter
*then*; a supervisor about to close re-reads the gate *then*. That puts the text
immediately before the decision instead of hoping it is still attended, and it
costs nothing when the decision is not being made.

**So the split is by what the material constrains.** Anything governing one
decision is re-read at that decision. Only what constrains **every** decision —
the priority order, the protected paths, the width, the current claims — is
worth a periodic refresh, and that set is small enough to be cheap. Re-reading a
34 KB charter and a 27 KB requirements file on a timer is not affordable and not
what makes the difference.

**The open question is the trigger**, and time is the weakest of the candidates
because it is uncorrelated with how much has happened. Better: a count of
reports handled, or board moves made, since both track actual context growth.
Worth measuring against a real run before choosing.

---

## 7. A check for undispositioned audit findings

**The gap:** two audits produced fifteen findings; three became client questions,
one entered a task brief, and **eleven were never dispositioned** — filed in a
report that nothing pointed at again. A finding filed is not a finding routed and
nothing distinguished them.

**Measured before designing, and the measurement rules out the obvious check.**
A "declared in an audit, cited nowhere else" rule reports **zero** on that
project, because all eleven *were* mentioned — the manager had logged them in
the record. **Mention is not disposition**, and the difference between "written
down" and "decided about" is invisible in a citation graph.

**So it needs a declared status**, which is now in the audit skill: every finding
carries `Disposition.`, written `open` by the auditor and filled in by the
manager as `routed T-n`, `raised Q-n` or `declined (D-n)`. The check is then two
declared sides — a finding still `open` when its audited task closes — and passes
the name-the-rule test.

**What it costs to build:** the identifier grammar currently matches one- and
two-letter prefixes, so `COR-n`, `SEC-n` and `HYG-n` are invisible to
`check_refs` entirely. Extending it interacts with an existing control asserting
three-letter prefixes need no reserving. Worth doing deliberately rather than in
passing.

**And the reason to do it eventually, stated plainly.** The three-letter prefix
was chosen *because* the scanner cannot mistake it for a citation — which is the
same fact as the scanner being unable to check it. **The audit namespace has no
citation integrity in either direction**: a report may cite `COR-99`, which
exists nowhere, and nothing says so. `Disposition.` is now the only thing
watching that namespace, and one field carrying a whole namespace's integrity is
a thin arrangement.

The general form is worth carrying past this instance: **a thing exempted from a
check for its own protection is a thing the check cannot see.** Whenever
something is carved out, name what watches it instead — or record that nothing
does, which is a legitimate answer and a very different one from "it is safe".

---

## 8. Two mechanisms deferred with their triggers

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

## 9. The ceremony question, narrowed

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
