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

**What remains: neither has run against a real charter.** 0.2.9 **§3.2** is
the first — the charter amendment that opens cycle 2 on `pricelog`. It was
§3.1 and the fixture's backfill until 0.2.9 was revised on 2026-09-07; the
fixture is no longer the target, so there is no backfill and the first real
charter is one this run writes from nothing. And the semantic half of this
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
audit.** 0.2.9 **§3.2** shows cycle 1's open findings to the client and routes
or declines each. This read *"the fixture's nine open findings"* until the
2026-09-07 revision — those findings still exist and are still undispositioned,
but the fixture has no principal to disposition them, which is the whole reason
the target moved.

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

**BUILT, at Randy's direction, before 0.2.9 runs** — `unparseable-protected-path`
in `check_trace`. It imports the guard's own regexes rather than restating them,
so the split rule keeps one home and this check cannot agree with itself instead
of with the guard (P-34). The rule it enforces is **declared** in
`templates/CHARTER.md`'s own `Protected paths` cell rather than proposed by the
check (F-113): one path per entry, comma-separated, nothing else.

**The first wording of this item named the wrong discriminator, and `_s9` caught
it before the code shipped.** It said *"an entry that does not resolve to a path
in the tree"*. **In-tree-ness is exactly wrong**: the row's designed use includes
**sibling repositories**, named as such in `guard.py`'s docstring, in the second
protected-path check that *"defends a path outside every devteam project"*, and
in `setup.py`'s own scaffolded cell text. The fixture's row is three absolute
sibling-repo paths, correct and load-bearing, and a resolve-in-tree check would
have reported three findings on it — and on `guard.py`'s own control fixture,
which uses `/etc/devteam-probe`.

The property actually measured was that the cell contained **prose** which
survived the comma-split and backtick-strip as non-path tokens, so the
discriminator is that each token is **path-shaped** — no interior whitespace —
not that it exists here. The shipped check uses that, and is clean against the
fixture's three sibling paths. **This is the ninth time in this cycle an
instrument nearly answered a question adjacent to the one asked, and the second
time a peer session caught one before it landed.**

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

### FOURTH INSTANCE, 2026-09-08 — and it is the evidence that a note is not enough

Recorded by the session that wrote the paragraph above, **within hours of
writing it.** Closing 0.2.10, the invocation was:

```
python3 .../check_refs.py >/dev/null; echo "check_refs exit=$?"
...
if [ "$RC" -ne 0 ]; then exit 1; fi        # $RC is run_controls', not check_refs'
git commit ...
```

Two mistakes compounding, and neither is exotic: the output went to
`/dev/null`, so the finding was never on screen; and the guard tested a
**different script's** status variable. `check_refs` exited 1 and the commit
went through.

What it had caught was real — two `leak` findings, an absolute home path pasted
into a tracked file **in a public repository**. Amended out before any push, so
the leak left the history; had it been pushed it could not have been.

**This is now four instances, and the count is the finding.** The shape has a
name, a numbered entry, a paragraph explaining that the repair is not "be
careful", a citation in a handoff, and a quotation in a commit message written
the same day — and a session under time pressure did it anyway. **A rule in a
document does not survive contact with a session under time pressure**, which
is this project's founding premise, demonstrated on its own author.

### The mechanism, its shape, and why it is 8b's sibling rather than a new family

**The property is: a commit should carry evidence that the tree it contains
passed.** Stated that way, 8b is the same rule read from the other side:

- **8b** — the tree being committed was not the tree that had been checked.
- **This** — the tree was the checked tree, and the check was **red**, and its
  status was discarded by the shape of the invocation.

Both are answered by one mechanism: **refuse `git commit` unless the fast
checks have been run green against the current tree state.** Not a wrapper
anyone can call past — `guard.py`'s history family already sits at the moment
of typing, which is the only place this can be enforced against a session that
did not intend to break the rule.

**Fast is load-bearing, and N-1 already decided the general principle.** A gate
that runs the full control suite costs minutes, and *"a check nobody will wait
for is a check that gets switched off."* `check_refs` and `check_plugin` are
sub-second and are what caught all four instances; `run_controls` belongs at a
release gate, where N-1 put `mutate.py` for the same reason.

**Entry condition, unchanged from N-2 and still unmet.** This changes
`guard.py`'s `judge()` — the file with the widest blast radius in the plugin,
where both 0.2.4 and 0.2.5 recorded their sharpest defects — so it wants a
subcycle that opens that file deliberately, with the 111-case control green
before and after. **0.2.10 did not open it**: `root_guard.py` is a separate
script by design, so the `PreToolUse` door being open is not the same as the
entry condition being met.

**Trigger: fired four times, and now something watches it** — this paragraph,
and the instruction to whoever plans 0.3 that a `guard.py` subcycle carries
8b and this together, because they are one property with two symptoms and
building either alone means opening that file twice.

## N-7. A worker's question is answered, and never measured — the rule exists one layer up

`resume` §0 states the principle exactly: **"Every question you have to ask is
a defect in the record… Treat the questions as a measurement: anything you had
to ask about is something the written state failed to carry, and it will fail
to carry it again for the next reader, who may not have anybody to ask."** It is
applied to an incoming session at a handoff, and to a manager at a rotation.

**It is not applied to a worker asking about the specification.** `run`'s
disposition table routes `NEEDS-DECISION` — *"the task stops; the question and
its recommendation go to the table"* — and the client answers it. Nothing
anywhere records that `REQUIREMENTS.md` should have answered it and did not. So
the pipeline measures the completeness of its own record and **not** the
completeness of the thing it is building against.

**The evidence is the owner's, from outside this project, and it is the worst
case of it anybody here has.** A 904-page engineering report, polished from a
draft, lost a great deal of content in the *polishing* stage. It was discovered
only when implementation began *"and the implementer started to ask me
questions that i know should have been answered in the report"* — after which
the polished report was abandoned and the draft used instead. **That question
stream was the only detector that ever fired, and it fired at the most
expensive possible moment.** A pipeline that logged it as a defect in the
specification would have had a running count of the report's incompleteness
from the first task onward.

**Why this passes the F-113 test:** the two sides are the questions a worker
had to escalate and the requirement set that was supposed to answer them. Both
are declared and both are already written down — `QUESTIONS.md` and
`REQUIREMENTS.md` — so the finding is a diff rather than a reading.

**What it is not.** Not every escalation is a specification defect: a genuine
`CHARTER`-class question about what the client *wants* is new information, not
a gap. The distinction is whether the answer, once given, belongs in the
requirements — and that is a judgement, so the mechanism should **record and
count** rather than classify, and let the checkpoint read the list. A count
that rises across a cycle is the signal; the individual rows are the evidence.

**Trigger: it has already fired, outside this repository, and nothing watches
it.** Recorded here rather than built, because 0.2.9 is a run rather than a
build subcycle — and because 0.2.9 will produce the first real corpus of worker
questions this project has ever had, which is exactly what a check like this
should be calibrated against before it is written.

## N-8. Five documents told the reader something the tree had stopped agreeing with, and the repair already exists unrun

**Five instances in two days, two of them inside the editing session's own
pass, and every one found by a person or a peer reading rather than by a check:**

| Where | Said | Truth |
|---|---|---|
| `README.md` (plugin) ×3 | 0.2.9 is *"cycle 2 on the fixture with a deliberately slow client"* | retargeted 2026-09-07; the fixture has no principal |
| `0.2/README.md` | same, in the cycle index | same |
| `README.md`:36 | `551` cases / `13` controls / `251` fp | `575` / `14` / `262` |
| `HANDOFF.md`:16–25, :52 | `558` cases, `13` controls, `15` scripts | `575`, `14`, `16` |
| `HANDOFF.md` §3 | manifests `0.2.0`, tag `v0.2.0`, *"It is not pushed"* | `0.2.0-rc`, `v0.2.0-rc`, pushed |

**The last one is the sharpest and it is the reason this is a check rather than
a discipline problem.** `HANDOFF.md` §3 was made false by *the same session's
own commit*, in *the same file* whose counts block it had just corrected, three
sections above. And that file's stated rule is **"Every number below was read
from the tree, with the command beside it"** — the rule the 0.1 handoff
established after its first draft wrote *"~500 control cases"* where the command
said `328`. **The document carrying the rule is where the rule failed, twice.**

`_s10` drew the class wider than index rows and is right to: §3 is prose, not a
table. The general shape is **a document's statement about a versioned artifact,
with nothing diffing it against the artifact.**

### The repair is already written down, and running it is the whole of the work

**`HANDOFF.md` lines 16–25 are a machine-checkable structure that nothing
executes:**

```
ls plugins/devteam/skills | wc -l                     ->  15 skills
python3 plugins/devteam/scripts/run_controls.py       ->  all 14 controls green, 575 cases
git rev-list --count 243059e..HEAD                    ->  74 commits this cycle
```

A command and its recorded output. **Side A is the recorded output, side B is
re-running the command** — two declared sides, both already on disk, so it
passes the F-113 test without anyone inventing a rule. Every count-shaped
instance above sits in exactly this block and would have been caught the moment
it drifted.

**And it makes the prose instances a decidable question rather than an NLP
one.** The convention becomes: *a claim about the tree lives in a claims block,
as a command and its output; prose may point at the block but not restate it.*
§3's three false statements were prose restating facts a command could have
produced — `plugin.json`'s version, `git tag -l`, `git ls-remote`. Rewritten as
a block they are checked; left as prose they cannot be. **A claim that cannot be
written as a command and an output is a claim nobody can check, and saying so
plainly is more useful than pretending a checker could read the sentence.**

**Cost and cadence, decided rather than left open.** Re-running a claims block
means running its commands, which for `run_controls` is the full suite —
minutes, not seconds. So this is a **release gate and a subcycle-close step**,
where N-1 put `mutate.py` for the same reason: a check nobody will wait for is a
check that gets switched off. The cheap subset — anything not invoking the
control suite — can run in the pre-commit path.

**Trigger: fired five times, and this paragraph is the first thing watching
it.** Not built here; 0.2.10 was a subcycle with its own scope and 0.2.9 is a
run, not a build. It wants the subcycle that next opens `check_plugin.py`, which
is where both the manifest diff and the roadmap-state checks already live.