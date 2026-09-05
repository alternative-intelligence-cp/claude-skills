---
name: plan
description: Turn a devteam project's signed requirements into a task graph — one file per task with its goal, the requirements it discharges, its declared write scope, its dependencies, its gate, its verification command and its estimate — ordered so the riskiest unknown is answered first. Also decomposes one task into steps. Used by the project manager and the planner agent.
argument-hint: "[task]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git log:*) Bash(ls:*) Bash(find:*) Read Write Edit Grep Glob WebSearch WebFetch Agent AskUserQuestion
---

# Planning

Requirements say what must be true. A plan says **who makes it true, in what
order, and how anyone will know.** It is not a schedule — it is a set of
contracts small enough that one worker can hold one.

## What a task is

One file, `devteam/tasks/T-n.md`, from
`${CLAUDE_PLUGIN_ROOT}/templates/tasks/TASK.md`. Six things, none optional:

| Field | And what makes it wrong |
|---|---|
| **Discharges** | the `R-n` it makes true. **A task discharging none is scope creep, or a requirement nobody wrote down** — and the check will say so (P-4) |
| **Scope** | the paths it may write. Too wide and it collides with its neighbours; too narrow and it escalates mid-flight. Both are your error, not the worker's |
| **Depends on** | tasks that must be `DONE` first. A named task, never "after the backend" |
| **Gate** | what must be **true** afterwards — a condition, not a feeling |
| **Verify** | the exact command that proves the gate, decided **now**, before anyone is invested in passing it — and **scoped to this task's own files**, because at any width above one a whole-suite command measures other tasks' half-finished work and fails for reasons that have nothing to do with this one |
| **Estimate** | tokens and minutes. Wrong is fine; absent is not, because an estimate never compared to a measurement stays wrong forever (P-41) |

**A gate phrased over the whole project is a gate over everybody else's
in-flight work.** `pytest -q` expecting an unchanged count is a fine gate at
width 1 and meaningless at width 3 in one tree: a task watched the suite go
from 17 passed to 33 failed during its own work, none of it its own. Name the
files, or the node ids — `pytest -q tests/test_reader.py` — so the gate answers
a question about *this* task. Where a whole-suite figure is genuinely wanted,
it belongs to a checkpoint, which runs when nothing is in flight.

## Scopes are the hard part

**Two tasks that can run at once must declare disjoint scopes** (P-12). This
is what makes width greater than one safe inside one repository, and it is the
part of planning that actually requires thought.

- Split by **directory or file**, not by concept. "The parser" and "the
  formatter" overlap if they share `src/ast.py`; `src/parse/` and
  `src/format/` do not.
- A file two tasks both need is a **third task that runs first**, or a
  dependency edge. It is never a shared scope.
- A scope of `src/` is almost always wrong: it serialises the entire project
  behind one task.

Check it rather than eyeballing it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py" .
```

## Order

1. **The riskiest unknown first.** If something could invalidate the plan —
   an approach that may not work, a library that may not do what its README
   claims, a performance figure that may be unreachable — that is task one,
   and it is small. A day spent finding out now beats a fortnight built on it.
2. **Instruments before what they guard.** The test harness, the benchmark,
   the fixture loader come before the thing they will judge. A verification
   command written after the code is written to pass it.
3. **A task is one worker's worth of work.** If you cannot say what command
   proves it, it is too big or too vague — split it.

**Check the requirements quantify before you plan against them.** A requirement
that enumerates cases where its goal quantifies produces a task that discharges
cleanly and leaves the goal unmet — and `check_trace` reports the whole chain
clean, because every link exists. If a requirement reads as a list, that is an
escalation to the manager before it becomes a task, not something to plan
around. The signs: the requirement names a specific input where the goal names a
class; the acceptance criterion tests exactly the cases the statement lists; the
phrase "a missing X" or "an invalid Y" where the goal said "any" or "every".

**An acceptance criterion is an ORACLE, and an oracle derived from the thing
it judges is not one.** This is the principle behind the next two rules, and
worth stating once because both are instances of it.

Something independent has to say what *should* happen. Without it, whatever the
artifact does is correct by definition — not "probably right", not "unverified",
but **correct, because nothing exists that could disagree.** A compiler with no
grammar to check against cannot emit wrong output; a function with no
specification cannot behave wrongly; a test written after the code, to match
the code, tests that the code is the code. In every case the failure is not
that the check is weak. It is that there is no fact of the matter for it to be
weak about.

So the criterion is written **before** the work, from the requirement rather
than from the implementation, and it survives being read by someone who has
not seen the code.

**A requirement's `Status.` and a task's `Discharges.` are two views of one
fact, and they must agree.** The status vocabulary names tasks — `in-progress
(T-n)`, `discharged (T-n)` — so the two fields are already talking about the
same relationship, and only bookkeeping can make them disagree. Checked by
`one-sided-link`, in both directions, with PLANNED tasks exempt because a task
that has not started correctly leaves its requirement `open`.

**A criterion's LEVEL must match some task's scope, and this is the defect that
has recurred most.** Three times in one project, an acceptance criterion
written in process language — *"exits non-zero"*, *"fails under the default and
succeeds under `--encoding cp1252`"* — was assigned to a task scoped to a
single module. Each time the module task did its work correctly, and each time
the requirement was **still not discharged**, because the task could make the
*behaviour* true and could not make the *sentence* true: the sentence describes
a process only the wiring task can run. All three were caught late, by a
verifier invoking the command end to end, after the module task had closed.

It recurs because of *when* the two things are written. Onboarding writes
acceptance criteria with the client, in the client's language, which is
naturally the language of running the thing. Planning draws scopes much later,
by module. Nobody is present at both moments, so nothing compares them.

**So compare them, here, deliberately.** For each requirement, read its
criterion and ask: *which single task's scope contains everything this sentence
write to?* If the honest answer is "none — it needs this module **and** the
wiring", then the criterion belongs to the **wiring** task. The module task
*supports* the requirement; it does not discharge it. Say so in both task
files, because "supports" and "discharges" are different claims and only one of
them closes a requirement.

**A gate carries the obligations its requirements rest on.** If a requirement's
statement or acceptance cites a decision, some task discharging it must require
what that decision decided — in its `Gate.`, naming the decision. This is a
rule, stated here **before** the check that enforces it, because it was not one
until now: `gate-omits-decision` was written first and audited afterwards
against the question *which rule requires these two sides to agree?*, and the
answer was none. Its findings on a real project were therefore the missing rule
showing up rather than defects.

The rule earns its place on the case that prompted it. A task's gate listed
four things its requirement wanted and neither of the two caveats that same
requirement had gone to a charter amendment to establish. **The verifier reads
the gate**, and P-18 puts the verifier last, so a gate narrower than its
requirement passes everything and ships less. Naming the decision rather than
restating its substance is deliberate: it is what sends a verifier to the
reasoning instead of to a paraphrase.

**And it is now checked, because the level is declared rather than inferred.**
A script cannot reliably tell a process-level sentence from a module-level one,
and a heuristic that guessed would misfire on ordinary plans — which is how a
check gets switched off by whoever it obstructs, leaving less than none at all
(P-35). But it does not have to infer anything. Each requirement declares
`Requires-write.`, the paths its criterion touches; each task declares `Scope.`; and
`check_trace` reports **`unreachable-acceptance`** when no single task
discharging the requirement has all of them in scope. Set containment over two
declared lists, no English parsed.

It fails in the safe direction, which is the property that makes it worth
adding: an understated `Requires-write.` makes the check **miss** a real mismatch
and never invent one. The residual failure is a criterion whose author did not
understand what their criterion must write — and that at least leaves a
declaration somebody
can read and dispute, instead of a silence.

**You may not quietly widen either list to make it pass.** You draw the scopes,
so you could make any `Requires-write.` fit by editing one or the other, and the
check would go green having measured nothing — a judge trying his own case. If
the list is wrong, supersede it as a recorded amendment (P-23) and say which
you changed and why.

**For any set-valued decision, assert one member of its complement.** A suite
accumulates cases for what a thing *does*. **The cases for what it must not do
are the ones nobody writes**, and they are exactly the ones a later widening
slips past — because widening a set breaks no test that only ever tests
members.

Measured: a project decided that `true` and `false` are the only booleans it
infers. A verifier widened the accepted set to include `y` and `n` on a scratch
copy and the suite still reported **101 passed**. The shipped behaviour was
correct and nothing defended it. Bare `y`, `n` and `f` appeared in no fixture,
no test named the set, and a change making the decision false would have been
invisible.

The heuristic is cheaper than it sounds and it generalises past sets: **ask
what the thing rejects, excludes or refuses, and write one case for that.** Two
of the sharpest findings on that project came from exactly this move, one level
apart — one by asking which spellings a value set rejects, the other by asking
which cases a test classifier *excludes* from its corpus.

**And the rule behind both: a property only counts as decided if something
fails when it stops being true.** This holds for a decision, a charter
sentence, a risk entry, a README claim — anywhere a document asserts something
about behaviour. A property that is true because of how the code happens to be
written today is an accident, not a decision, however carefully it was argued.
The test of whether you have finished deciding something is not whether the
reasoning is written down; it is whether you can name the thing that goes red.

**Do not test an absence by asserting nothing happened.** A contract that
documents an absence — no exception, no warning, no rewrite — almost always
also specifies a **positive return**, and that is the thing to assert. "Assert
nothing was raised" passes on a function that does nothing at all, on one that
returns the wrong value, and on one that was never called. A worker argued a
gap could not be closed inside its task on exactly this basis; the verifier
disproved it by writing the test in the other direction. Ask what the caller
downstream is promised, and assert **that**.

**And when you prove it by mutation, name the node id you expect to fail.**
"The suite went red" is not evidence that the *instrument* went red. One
deliberate mutation in this project turned three tests red and only one was
under test — a step whose evidence was "it failed" would have been satisfied
by either of the other two, and the instrument could have been vacuous the
whole time behind a genuine failure somewhere else.

**And run it against the DEFECT you are avoiding, not only against the state
you are leaving.** These are different tests and only the second one matters.

A command that fails on the pre-change tree has been shown not to be
constant-green — necessary, and not sufficient. A check can fail on the old
tree, pass on the new one, and still be blind to the specific defect it was
written for, because it discriminates on the wrong axis. That happened here: a
step's three checks all failed before the change, all passed after it, and all
passed a deliberately built version of the exact defect they existed to catch.
Every one of them was comparing text that the defect does not alter.

**And mutate in BOTH directions, because "does the instrument catch this being
wrong?" and "does it catch this being absent?" are different questions.** Every
mutation discipline written down here asks only the first: break the thing, and
require the check to notice. A **narrowing** mutation — one that makes the code
do *less* rather than something wrong — is the case nobody builds, and it is
the one a suite tends to miss.

Measured. A tool inferring numeric types was narrowed to reject exponent-form
floats, so `1e+16` stayed a string: **zero failures across 277 tests.**
Narrowed to reject integers above fifteen digits: **zero failures.** The
behaviour was correct and nothing defended it. A *total* no-op failed 21 tests,
so the floor existed — it simply sat far below where the interesting narrowings
are.

The diagnosis matters as much as the finding, because it decides what it costs:
the requirement was fine. **It was a rule over a domain, and the corpus did not
span the domain** — seven numeric cells that did not cover the shapes inference
can be narrowed on. So the fix is a test, not a charter question. A requirement
written as an enumeration would have produced the expensive version of the same
gap.

So: build the defect on a copy, run the check, and require it to fail. If it
does not, the check is measuring something adjacent to the thing you care
about, and a green result from it means nothing at all.

**A verification command must be able to FAIL.** This is the one that is
easiest to get wrong and hardest to notice. A step's verify is evidence only
if it would have come out differently before the step was done — otherwise it
is a green light wired to nothing.

The test is mechanical and cheap: **run the command against the tree as it
stood before the change** (`git archive HEAD~1` into a scratch directory) and
confirm it *fails* there. A real supervisor found its planned command printed
identically on the pre-change tree, rejected the step, wrote a replacement —
and found that vacuous too, because `pytest` reports `configfile:
pyproject.toml` whether or not the table it was checking for exists. Only the
third command actually discriminated.

A command that cannot fail is worse than no command, because it converts "we
did not check" into "we checked and it was fine".

**When the task IS shared infrastructure, scoping the command is impossible —
pin a snapshot instead.** The table above says a verify must be scoped to the
task's own files, because at width above one a whole-suite command measures
other tasks' half-finished work. That advice runs out exactly where it is
needed most. A task that changes the test harness, a fixture module, a
`conftest.py` or a build file has a gate that is *inherently* about everybody's
tests: "the suite still passes" is the only thing such a change can mean, and
there is no subset of files that expresses it.

Writing `pytest -q` and an expected count is then not laziness, it is the
obvious reading — and it does not work. One harness task's gate expected an
unchanged count; the live tree went from 17 passed to 33 failed during the
task, **none of it caused by the task**. The number measured two concurrent
tasks' in-flight work and said nothing about the harness.

What makes the number mean something is a **pinned snapshot with only this
task's file substituted**: `git archive` the last commit into a scratch
directory, copy this task's changed file over it, and run the suite there.
Everything else is then held still by construction, and the count is a
statement about this change alone. At width 1 that is the same command as
running it in place, which is why the distinction is invisible until it costs
you. Write the snapshot form anyway — the width the task eventually runs at is
not the planner's to know.

**A tests-first step still needs something to import.** A step whose
verification is "the tests collect" cannot pass while the module those tests
import does not exist — collection fails before any assertion runs. So a
tests-first step's scope includes an unimplemented stub of the module
(`raise NotImplementedError` and nothing else), and the step after it replaces
the stub. This was found the first time a real supervisor ran a plan that got
it wrong: it had to widen the step's scope itself to make the step runnable,
which is work the plan should have done.

**Estimate the reading, not the typing.** The first measured task in this
system came in at **26x its token estimate** — 8,000 estimated against roughly
210,000 actual — because the estimate counted the code to be written. Almost
none of the cost is typing. It is reading the charter, the requirement and the
decisions; running the verification; writing the report; and the supervisor's
own dispatch and checking around all of that. A task that writes forty lines
of code is not a forty-line task. Estimate the whole loop or do not bother
(P-41).

**A per-step constant cannot carry the verification standard, because the
standard is paid twice.** This was measured over six tasks and it is the reason
two successive corrections to a per-step figure both came in low. The error is
not a bias with one number to fix; it is **two factors that multiply**:

| | |
|---|---|
| steps actually run vs steps estimated | **1.37x** |
| cost per step run vs cost per step modelled | **1.36x** |
| product | **1.86x** — the observed total |

The second factor is the one people expect: a verifier that rebuilds a worker's
adversary and measures it independently costs more than one re-running the
worker's commands. The first is the same standard seen from the other side —
**verification becoming its own steps.** One task planned four steps and ran
eight; two of the extras were a verifier step and an auditor step. No per-step
figure can express that, because it is not per step.

So state the model in units a planner actually holds at planning time —
**estimated** steps, not the steps that turn out to be needed — and let the
constant absorb both factors. On the project where this was measured, moving
from 237,500 to 260,000 per estimated unit reduced the total error from 1.86x
to 1.70x; **440,000 brought it to 1.00x** and cut the worst single-task error
from 148% to 42%.

**And leave the argument out of the fit.** One task in that set cost 454,400
per step against 290,905 for the other five, and it is excluded deliberately:
it measures a *disagreement*, not a task. A model that absorbed it would be
predicting how often the project argues with itself.

**Excluding an outlier is only honest if you know what it measures**, and this
one turned out to be more than an argument. Counting the project's verify
verdicts afterwards showed nine, of which two were FAIL — **and both were on
that same task.** The outlier and the rejections are one event seen twice: the
bar was argued three times because it was rejected twice and rebuilt. So the
excess cost is not noise, it is **the price of the verification layer catching
something**, and a constant fitted to absorb it would be predicting how often
the project catches itself. That is precisely the quantity you must not smooth
into a per-step figure, because the planner reading that figure would then be
budgeting for verification never working.

**Write a probe as `Kind. probe`, not as an implementation task.** A probe
discharges no requirement — that is what makes it a probe — so an
implementation task with an invented `Discharges` field is the wrong shape and
a permanent `unmotivated-task` finding is the wrong answer. It names
**Informs.** instead: the requirement or goal whose achievability it is
testing. A `chore` names **Because.** The check enforces the distinction, so
the riskiest unknown really can be task one and small, which is what this
section asks for.

**A probe and a spike are different things.** A probe asks *"is this even
possible?"* and its answer changes the design. A spike asks *"how big is
this?"* and **its thresholds are decided in advance**, so a bad number
produces a stop rather than an improvisation. Confusing them produces a probe
with no pass mark, which always comes back positive.

## Decisions belong here

Every choice the plan makes — the framework, the storage, the layout, the test
runner — is a `D-n` in `DECISIONS.md` **with the alternatives declined and why
they lost** (P-21). The alternatives are exactly what somebody will propose in
three weeks, and a decision that does not say why they lost gets re-litigated
by everyone who arrives fresh.

Anything you cannot settle from the charter, the requirements or research is a
`Q-n` with a recommendation and a class (P-25, P-26) — **not a guess buried in
a task file.**

## Before you show anyone

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py" .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py" .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py" .
```

All clean. A plan with an `uncovered-requirement` is a plan that silently
drops something the client signed for.

Then fill the board's **Tasks** table — every task, its requirements, its
dependencies, its scope, state `—`.

## The approval (GATE 2)

Show the client:

- the tasks in order, one line each, with what each makes true
- **which requirement each discharges**, so they can see nothing was dropped
- the dependency shape, and what can run at once
- the total estimate against the charter's budget ceiling
- **which task answers the riskiest unknown, and when they will know**
- every open `Q-n`

Get approval for the plan, the width, and the model band. Then
**`/devteam:run`**.

## Decomposing one task into steps

Same discipline, one level down. A step is one worker's work with one command
that judges it, carrying a complexity class (P-40). Steps live in the task
file under `## Steps`. A supervisor writes its own if the planner did not —
the person who has just read the task is well placed to split it.

## What planning must not do

- **Not write product code.** Not even a stub.
- **Not leave a `Verify` as "tests pass"** without naming the command.
- **Not size a task by how long you hope it takes.**
- **Not plan past the first risky unknown in detail.** Plan that task
  properly, sketch the rest, and re-plan when its answer arrives. Detailed
  plans built on unanswered questions are the most expensive kind to throw
  away.
