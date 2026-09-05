# Handoff — the first live `devteam` run is complete

Written 2026-09-05 by the session that ran it, for whoever picks this up. The
return date is unknown and may be a week, so this assumes you have **none** of
the conversation and cannot ask its author anything.

Read this file, then `plugins/devteam/docs/CONSOLIDATION.md`. Everything else is
a pointer.

**Every number below was read from the tree at `243059e`, not carried from
memory** — `run_controls.py` for the case count, `rev-list --count` for the
commits, `bundle create` for the 1.5 MB. The first draft said "~500 control
cases" where the command says **328**; writing the command down is what made
that visible, which is the rule this project's own final review runs under.

---

## 1. The experiment's record is preserved, and where

**`.internal/scratch/` is gitignored by this repository and is therefore not in
its history.** It has its own remote:

**`alternative-intelligence-cp/devteam-run-01-csv2json`** — **private**, and it
must stay private. It is the complete working record of a client engagement,
and this repository is public.

All 238 commits are pushed and verified there by counting the remote HEAD's
ancestry rather than trusting the push. A further backup is one command:

```bash
git -C .internal/scratch push
```

**Push it after any change to that tree.** It was created because the record
existed on one disk with no remote at all, which is the state to avoid rather
than a historical note.

---

## 2. Where things are, and which is which

| Path | What |
|---|---|
| `plugins/devteam/` | **the product.** The pipeline: 15 skills, 9 agents, 9 scripts, 328 control cases |
| `plugins/devteam/docs/CONSOLIDATION.md` | **the work queue.** Nine items, each with why it was deferred |
| `plugins/devteam/DESIGN.md` | why the pipeline is shaped as it is, and every lesson the run produced |
| `plugins/devteam/PROTOCOL.md` | the numbered rules. Every one carries the measured failure that produced it |
| `.internal/scratch/` | **the fixture.** A CSV-to-JSON tool, built by the pipeline as a test of it. Gitignored, no remote |
| `.internal/scratch/devteam/` | the run's own record: charter, requirements, decisions, findings, checkpoints, audits |

**The fixture is not a deliverable.** `csv2json` has no users and will have
none — that is a signed decision (D-37) and it is load-bearing in several
others. Do not fix its remaining defects because they are defects; fix one only
if fixing it exercises something in the pipeline that has not been exercised.

---

## 3. State: the run is finished

Every task closed. **GATE 4 — the final review — fired for the first time and
returned `DRIFTED`**, filed at `.internal/scratch/devteam/checkpoints/`. The
client accepted it.

Nothing is broken: 531 tests passing, all four checks clean across eleven tasks,
13 of 13 requirements discharged, ~45 README claims verified against the shipped
code with zero divergences.

**It drifted because of the finding worth reading first.** A signed done-means
required *"the client runs it against a real export of their own"* — described
in the charter as *"the only condition that tests whether the tool solved the
problem rather than the specification."* A later client decision, made on
budget, recorded that the tool has no users and never will. **That made the
condition undischargeable**, the charter was amended three times afterwards, and
nobody re-read it. It is struck by amendment with the reason stated, rather than
silently, because striking it quietly would have deleted the project's only
check on itself.

**Nothing in that project is repairable in this cycle**, structurally: a write
scope is held only by an open task and every task is closed. The next cycle
opens with `/devteam:iterate`.

---

## 4. What is not in any file

The part a written handoff loses. These are things the run established that live
nowhere else.

**The client was played by an AI session, not by the owner.** Every decision
signed "the client" was made by the session that wrote this file, under the
owner's direction and consistent with positions he stated. That matters when
reading the decision log: the client was unusually available (answers in
minutes, at 3am, with the domain loaded) and **a human client would have been
the bottleneck at eighteen blocking stops in fifteen hours.**

**Three client decisions run on one thread and should stay consistent**: a
memory-bound fix declined at three step-units, a docstring repair declined at
one, and a delimiter feature declined at one — all on the ground that the
fixture has no users. A successor reversing any of them should reverse the
reasoning explicitly rather than quietly.

**`iterate` has never run.** It was deferred deliberately, to be exercised
against a small real target rather than tacked onto a finished fixture. That is
the last unexercised mechanism in the pipeline.

**A second team declined to trial the pipeline** and their refusal produced the
first change that ever made it *simpler*. The entry condition — what adopting it
costs a repository that already has an owner — is invisible from inside a run,
and both simplifications in this project's history came from people who did not
use it.

**The owner's standing constraints** are in the session memory files and will
load for you. The one to know before touching anything: **never write outside
the repository this session was started in without asking.**

---

## 5. Where to start

**A plan for the next cycle now exists** —
[`plugins/devteam/meta/roadmap/README.md`](plugins/devteam/meta/roadmap/README.md),
written 2026-09-05 from this file, `CONSOLIDATION.md`, the run's record and a
measured sandbox spec. It takes the queue below into subcycle files a fresh
session can implement. Read it after this file; the three points below still
hold and the plan is built on them.

1. **Ask about the bundle** (§1). It is the only item with a clock on it.
2. **Read `CONSOLIDATION.md`.** Nine items, ordered, each with the measurement
   behind it. Item 1 — manager rotation — is the one the owner named as most
   valuable.
3. **Do not build the two deferred mechanisms** until their triggers fire. Both
   triggers are written down and both were measured, not guessed.

**And one habit that produced most of what is in `DESIGN.md`:** before building
a check, run it against the live corpus and read what it reports. Four checks
were rejected that way in one day — each looked obviously right and each would
have shipped green while measuring nothing. The queue in `CONSOLIDATION.md`
records which ones and why.
