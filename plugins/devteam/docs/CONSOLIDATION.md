# The queue after cycle 0.2

Rewritten whole at the 0.2.0 release, as the cycle's plan requires. The
previous version was the queue left by the **first live run** — one project,
~24 hours, around 130 findings, five in six of them defects in this pipeline
rather than in the software it was building. That queue is now answered, item
by item, in part 1. Part 2 is what cycle 0.2 itself left.

**Nothing on this list is a bug report.** Bugs were fixed as they arrived.
This is the work that only makes sense once the running has stopped and the
whole thing can be read at once — which is a different activity from running,
and is why this file exists at all.

**A trigger written here is a trigger nobody watches unless something does.**
Three times now this project has deferred something with a stated trigger and
had nothing check the trigger, and two of those were found only when the
deferred thing failed. Where a trigger below has an owner or a check, it says
so. Where nothing watches it, it says that instead, because "nothing watches
this" is a legitimate answer and a very different one from "it is safe".

---

# Part 1 — the first run's nine items, answered

## 1. Manager rotation — the one layer that never resets — **taken (0.2.5)**

The manager was the only role that never got a fresh context, and the rule
that makes it trustworthy — every worker report passed upward verbatim (P-17)
— is the rule that makes it the bottleneck. One run put 897 KB of task files,
roughly 230,000 tokens, through it.

**What landed:** rotation at every checkpoint, triggered from **outside** the
session, because a manager cannot measure its own context and so cannot be
asked to notice. The outgoing manager releases the writer lock, the incoming
one reads the durable state, and every question it has to ask the outgoing
session is **logged as a defect in the record** — a record that needed a
conversation to interpret is a record that will fail the next reader, who may
have nobody to ask. Cadence is tuned to roughly **one compaction**, which is
the owner's stated budget: one is survivable, after two you have lost enough
that you go back and re-read the source anyway, which defeats the purpose.

**Rotation also turned out to be the largest available lever on usage**, which
this item did not know when it was written. `/usage` attributes the majority of
a week to long-context sessions — 83% at >150k context on the reading taken at
0.2.8 — and rotation is a real reduction rather than a redistribution, because
resetting context to near zero integrates to fewer cached tokens across the
same work. The quality argument and the cost argument do not always both apply,
and a cadence argued only from quality rotates later than it should.

**What remains: it has never rotated a real project.** 0.2.9 is the first run
that will.

## 2. Sweep for pairs of rules that cannot both hold — **taken (0.2.7)**

Nine known instances, each two rules correct alone and contradictory together,
every one found by a **worker hitting it** rather than by anyone reading. A
reviewer reads rules one at a time; a worker is the only party required to
satisfy all of them at the same moment.

**What landed:** [`PAIRS.md`](PAIRS.md) — the rule set read by **moment**
rather than by rule, 17 moments and 21 pairs, with the nine as its calibration
set. Most are resolved, several structurally.

**What remains: rows 18 and 19 are open, and each needs a measurement rather
than a decision.** Row 18 — P-46 counts requirement rewrites while `iterate`
§4 says a requirement is superseded and never edited, so if the second holds
the count can never reach three. **0.2.9 is the run where that becomes
observable**, because it is the first real second cycle. Row 19 — whether a new
template constraint row propagates into a client-signed amendment on every
existing project — is half closed; the half that reaches a human is untested
and needs a release cadence, not a reading.

## 3. Audit every check against F-113 — **taken (0.2.6)**

*Name the rule whose two sides a check compares. If you cannot name one, the
check is proposing a rule rather than enforcing one, and its false positives
are that missing rule showing up.* The test arrived late and had been applied
to three checks, finding all three proposing rules.

**What landed:** [`CHECKS.md`](CHECKS.md) — every finding class in the plugin
against the rule it enforces, and `unruled-finding` / `stale-row` keeping the
table and the code equal **in both directions**, from the AST rather than from
a docstring anyone can forget to update. A class with no row is a finding; a
row for a class nobody emits is a finding.

## 4. The backwards pass — **partly taken (0.2.6)**

A project learns forward only: a charter signed before a template gained a row
never acquires it. That is why the first run's final review returned `DRIFTED`
— a signed done-means condition was made undischargeable by a later decision,
three amendments passed afterwards, and nobody re-read it.

**What landed:** an amendment now **re-affirms the whole charter by
enumeration** — every done-means condition and constraint gets a verdict — and
`amendment-omits-condition` diffs that list against the charter. `template-drift`
covers the other direction: a charter lacking a row the current template
declares.

**What remains: neither has run against a real charter.** 0.2.9 §3.1 is the
first, and it is also the fixture's backfill. And the semantic half of this
item is still not mechanical and probably never will be — telling a criterion
that names a *method* from one that names a *property* is a reading, and this
project refuses those everywhere. What it has is a **moment**: the final review
is the only place every criterion is read at once.

## 5. Wrappers for irreversible operations — **closed (0.2.0–0.2.4), by a mechanism this item was circling without naming**

The item's insight was the right one — *make a dangerous thing deliberate
rather than forbidden* — and it named its own hard part: a wrapper an agent can
bypass by calling the real tool is a rule, not a mechanism.

**Structural containment delivers it and removes the hard part.** A worker
inside a copy-on-write overlay may run every operation this item wanted to
wrap: `rm`, `git reset --hard`, an interpreter, a history rewrite. None can
harm anything that outlives the sandbox, so none needs to be forbidden, and the
permission grant **widens** inside precisely because the blast radius went to
zero (P-38b). The deliberate step is `promote` — the work exists, a supervisor
asks for it to be applied, and a gate diffs what it touched against what the
task declared (P-44). That is "do it, on the record, having said why", and
**there is no real tool to reach past, because inside the sandbox every tool is
the wrapped one.** That is the difference between a wrapper and a wall.

**What remains:** the outward-facing operations — `git push`, `gh`, publishing,
spending — are still withheld **by name** rather than wrapped, because their
consequences outlive any sandbox and no overlay helps. If the wrapper idea has
a remaining home it is those, and no finding has asked for it yet.

## 6. Keeping a long-lived role's context fresh — **taken (0.2.5)**

A `SessionStart` hook already re-injected a manager's bearings after compaction
or resume, covering the discontinuous cases and doing nothing for slow drift.

**What landed:** the stronger form — **re-read at the point of use**. A manager
about to answer a charter-class question re-opens the charter *then*; a
supervisor about to close re-reads the gate *then*. That puts the text
immediately before the decision rather than hoping it is still attended, and
costs nothing when the decision is not being made. Only what constrains *every*
decision — the priority order, the protected paths, the width, the current
claims — is worth a periodic refresh, and that set is small.

## 7. A check for undispositioned audit findings — **taken (0.2.6)**

Two audits produced fifteen findings; eleven were never dispositioned. The
measurement ruled out the obvious check: all eleven *were* mentioned in the
record, so "declared in an audit, cited nowhere else" reports zero. **Mention
is not disposition.**

**What landed:** a declared `Disposition.` field, written `open` by the auditor
and filled by the manager as `routed T-n`, `raised Q-n` or `declined (D-n)`;
`check_refs` resolving the reserved three-letter prefixes so the audit
namespace has citation integrity in both directions at last; and
`open-finding-at-close` — a finding still `open` when its audited task closes.

**What remains: the disposition half has never been exercised on a live
audit.** 0.2.9 §3.1 shows the fixture's nine open findings to the client and
routes or declines each.

## 8. Two mechanisms deferred with their triggers

### 8a. The accepted-findings block — **remains, trigger not fired**

A block recording a finding that may not be fixed, so the resting count returns
to zero and stays a signal. The framing decides who reaches for it: read as
*suppress*, a manager adds entries when the tree is annoying; read as *restore
the zero*, they are reluctant, because every entry costs the signal.
**Trigger:** the day a manager reads a finding count and does not read the
finding under it. Reported as *not yet*, and **nothing watches this trigger**.

### 8b. The narrow unscoped-commit refusal — **THE TRIGGER HAS FIRED**

Deferred through two cycles because the evidence did not exist. It exists now,
measured, on this repository, on 2026-09-07.

A session ran `git add -A` while a peer session's mutation harness had
`check_plugin.py` deliberately broken. The commit took the mutated file;
the harness's `finally` restored the working tree moments later. **Both
sessions ran the controls, both saw green, and both were telling the truth
about the tree they looked at** — the controls ran in the working tree, the
`git add` had read the mutated one. `check_plugin.py` shipped with a defect at
`6f2f389` and the next session found it.

Structural containment narrowed this rather than retiring it: a worker has its
own index, so its unscoped commit can only take its own staging (P-43). The
case shrank to the **host-side** actors — the manager and the supervisors — and
that is exactly where it fired.

**The property to build is narrower than "refuse `git add -A`", and stating it
matters, because a refusal built to stop `-A` for its own sake will be argued
down by the first person it inconveniences.** The damage was not the unscoped
stage; it was that **the tree being committed was not the tree that had been
checked**. The cheap mechanical proxy is refusing an unscoped stage while any
claim is live.

**Recommended home: 0.2.10**, not 0.2.8, for three reasons of descending
weight. `guard.py` already owns this family — the history category (`--amend`,
`add -A`, `reset --hard`, `rebase`, `stash`) sits above the exit that stops
policing a session outside a run, and an unscoped-commit refusal is the same
family at the same position, so anywhere else is a second home for one
judgement. 0.2.10 is already opening that door with a `PreToolUse` hook and a
refusal-at-the-moment-of-typing, and it is the only item on the board that
meets `CHECKS.md`'s entry condition for touching `judge()`. And a release
subcycle must not change the file with the widest blast radius in the plugin.

## 9. The ceremony question, narrowed — **taken (0.2.7)**

Not *"is this too heavy?"* — it is, for small work, deliberately. The tool is
aimed at work where being wrong is expensive and its baseline is *build,
discover it is wrong, build it again*.

**What landed:** [`CEREMONY.md`](CEREMONY.md) walks all 87 numbered steps
against the third test, the one from the purpose rather than the sizing: **a
step that only works when the operator already understands why it matters has
failed at what this is for.** That test had never been applied to anything.

**What remains:** *which individual steps buy nothing on any project* still
cannot be answered from inside a run. The only two such findings ever produced
came from people who **declined to use the thing**, which says where the rest
are.

---

# Part 2 — what cycle 0.2 left

## N-1. `mutate.py` is a real instrument that nothing anywhere mentions

Built mid-subcycle to satisfy an entry condition 0.2.6 wrote for a rule it then
declined to number. It answers the question 0.2.6 named as its blocker — *per
control case, which mutations flip it* — and it has **no plan, no roadmap row,
no entry here until now**, and `run_controls.py` does not discover it.
`check_plugin`'s `uncontrolled-check` cannot see it either, because that scan
matches `check_*.py`.

**The limit is the reason it is queued rather than finished.** Its
`COMPLETE_FOR` list covers **five cases out of 32 in one control of
thirteen**, so its verdict is narrow by construction and says so. The
vacuous-twin rule it was built to enable is **still unnumbered** because that
coverage is too thin to carry a rule. Extending it is cheap — a mutation is a
five-line tuple.

**Cadence, decided rather than left open: a release gate, not the pre-commit
path.** It runs a full suite per mutation, so it is minutes rather than
seconds, and a check nobody will wait for is a check that gets switched off.

## N-2. `guard.py`'s eight refusal families have no names in the code

`CHECKS.md` names them so they can be referred to at all, but the code returns
message text, which is why 0.2.5's rotation refusal could regress to the
generic message with the suite still green. **Entry condition, written in
0.2.6 and unchanged:** a subcycle already touching `judge()`, with the 111-case
control green before and after, and a mutation showing each named category
fails its own case and no other. It changes the return contract of the file
with the widest blast radius in the plugin, and both 0.2.4 and 0.2.5 recorded
their sharpest defects on that file's refusal path.

## N-3. Nothing compares a template's shipped form against the documents describing it

**Measured in 0.2.8's end-to-end walk.** `setup.py` strips `example:` blocks
from templates, correctly. The charter's **entire constraints table** was
inside one, so a scaffolded charter carried three paragraphs on how to write a
constraint row and no table to write one into — while three documents
(`setup/SKILL.md`, `onboard/SKILL.md`, `FORMATS.md`) told the reader to write
the `Containment` row into it. All three were green.

Fixed for this instance by splitting the overloaded marker into `example:`
(stripped) and `schema:` (ships, markers removed), with controls both ways.
**The general gap remains: no check reads an installed artifact and asks
whether the documents that describe it are still true of it.** That is a diff
of two declared lists and therefore checkable, which is the test this project
uses for whether a check is worth having.

## N-4. A charter row that reads correctly to a human can silently disarm the guard

**Measured in 0.2.8's walk.** The `Protected paths` cell was written as prose —
`` `devteam/` — the pipeline's own record, written only by the manager `` — and
the guard splits that cell on commas and strips backticks, so it resolved two
non-paths and protected **nothing**. A write into the protected tree was
allowed, silently, and no check anywhere said so.

This is the second instance of a shape the `setup` skill already warns about
for a different case: *a test written the natural way passes silently and looks
exactly like a guard that is not installed*. The first cost four consecutive
false negatives and a retracted claim.

**Trigger: it has already fired, and nothing watches it.** The cheap form is a
project check reporting a `Protected paths` entry that does not resolve to a
path in the tree — two declared sides, so it passes the F-113 test. Not built
in 0.2.8, which is a release.

## N-5. Self-application waits for a passing experiment, not a finished roadmap

This repository has no `devteam/` directory, so none of the project checks run
on the thing that builds them — which is why `check_scope`'s
`misattributed-write` **could never have fired** on 8b's commit above.

**This is a decision with a reason, not a gap.** The pipeline did not exist when
the repository started, and one experiment was run and judged *"nowhere near
ready for prime time"*. The condition for revisiting is **0.2.9 completing
*and* being judged a good enough experiment** — not 0.2.9 completing. A run
that finishes while leaving the mechanisms it was meant to exercise unproven
does not meet it.

The reason is the sharper half: the plans themselves keep containing things
that do not work out as expected when the plan was written, and **a process
whose plans are still surprising it is not a process to run on the thing
producing the surprises.** Setting it up may warrant a cycle of its own.
[`PAIRS.md`](PAIRS.md) row 20 carries the whole reasoning, and warns the next
reader off closing it early.

## N-6. A verification command's failure can be invisible from how it was invoked

**Measured in 0.2.8, by the session writing the release.** `run_controls.py`
printed `FAILED: test_check_trace.py` in plain sight, but it had been invoked
as `run_controls.py | tail -3 && … && git commit`. A pipeline exits with the
status of its **last** command, so `tail` reported success for a run that had
failed, and the `&&` chain committed over a red control.

Recorded because the repair is not "be careful". The general shape — *a check
whose exit code is discarded by the shape of the invocation* — is the same
family as the unexpanded-variable trap and N-4, and it is the one where the
operator is a session under time pressure, which is every session.
