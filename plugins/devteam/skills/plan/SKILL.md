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
| **Verify** | the exact command that proves the gate, decided **now**, before anyone is invested in passing it |
| **Estimate** | tokens and minutes. Wrong is fine; absent is not, because an estimate never compared to a measurement stays wrong forever (P-41) |

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
