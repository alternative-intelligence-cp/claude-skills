# Every step, and what it buys a practitioner who does not yet know why

**The pipeline exists so that a less experienced developer can build quality
software through the structure it forces** — to model best practice all the way
through the chain so the user does not have to already have it (DESIGN §21).
That makes one kind of step indefensible whatever it costs: **one that only
works when the operator already understands why it matters.** Such a step has
failed at the thing the pipeline is for, and its weight is the least of the
problem.

This file asks three questions of every numbered step and every gate in every
skill, and records the answer per row.

## The three questions, in this order

1. **What does this step buy, on a project where being wrong is expensive?**
   Name the failure it prevents. A step with no nameable failure is a candidate
   for deletion — not because it is heavy, but because nothing has ever shown it
   earns anything.
2. **Does this step work only if the operator already understands why it
   matters?** A step a rushed novice would skip, misapply or satisfy vacuously —
   because its reason lives in a document they will not open at that moment —
   has failed at the purpose. **Its fix is placement, not deletion** (DESIGN
   §20b: guidance goes where the temptation is, not where the documentation is).
3. **Is compliance visible in the product?** *Put the command beside the number*
   leaves evidence; *check your numbers* leaves none and is unenforceable by
   construction. A step of the second kind is rewritten to the first kind, or
   **recorded as a written rule with that limitation stated**.

## The rule this sweep is held to (L-7.3)

**A simplification is argued from a step earning nothing on any project, never
from small-project ergonomics.** The axis is the cost of being wrong, not
project size. The tool is deliberately too heavy for small work; *"is this
heavy?"* is not the question and never was. **Every `delete` verdict below names
what would go unprevented, or it is not a `delete`.**

## The verdicts

| Verdict | Means |
|---|---|
| `earns` | names a failure **and** leaves mechanical evidence. Nothing to do |
| `written-rule` | names a failure; compliance is a judgement and cannot be checked. **Kept, with the limitation stated** — awareness is not immunity |
| `placement` | the reason is not in the step's own text. A rushed reader meets the step without it. **The fix is to move the reason to the point of use** |
| `delete` | no failure nameable |

---

## The method, and the correction the calibration set forced

**Every row is written from the step's text alone**, as if the rest of the
record did not exist. That is the discipline the sweep is for: the author of a
step is the wrong person to judge whether it needs its reason written down,
because they cannot un-know it. Where a step's reason is elsewhere and correct,
the row still reads `placement` — the reason existing is not the same as the
reason being *there*.

**Question 1 has to be asked of a step's WIDTH, not only of its existence, and
the calibration set is what showed that.** Asked flatly — *what does this step
buy?* — both known instances answer "quite a lot", and both are still wrong.
Neither is a step that buys nothing. **Each buys something narrow and claims
something wide, and the widening is what buys nothing.** A sweep asking only
whether a step earns its place would have passed both.

## The calibration set — the two that came from outside

**Neither was found by anyone using the pipeline. Both came from people who
declined to use it**, and that is the finding under the finding: the missing
findings are not hiding in the runs, they are in the people who did not start
one. A defect is evidence and gets reported; *"that was tedious and bought me
nothing"* is a feeling, and everyone who has run this either built it or was
hunting for problems in it. **The forces all push one way, so it ratchets.**

### C1 — the scope rule reaching into a stranger's session

**Reproduced by question 1, asked of the rule's width.** Declared scopes exist
to divide the work of *one run* among *its own agents*. Asked what the wider
version buys — authority over a session that is not part of the run — the answer
on any project, at any cost of being wrong, is **nothing the narrow version does
not already buy**. It was never authority over a stranger's session.

What it *cost* was the adoption: a second team read the briefing, saw two lock
regimes over one tree, and declined at the door — before running a command.
Their diagnosis was better than their report: **the guard's name described one
property and its mechanism covered a wider one, and the widening was implicit.**

**The residual is stated rather than hidden**, which is the part a sweep must
not lose. A stranger's commit *outside* every live scope is now caught by
nothing. That is the trade, not an oversight.

### C2 — a `devteam/` directory as arbiter of every write in the tree

**Same shape, same answer, and the same reproduction.** The trigger is the mere
existence of a directory; the consequence was authority over every path in the
repository. Nothing in the act of creating that directory said *"this repository
now has a second lock owner"*.

Asked of its width: enforcing against strangers buys something real for
`devteam/` itself and for the charter's protected paths — those are **the run**,
and P-13's lock must hold against a session outside it. For the **product
tree** it buys nothing the narrow rule does not, and charges a stranger
intermittent refusals originating in a run they are not part of.

**If the method had not surfaced these two, the method would be wrong.** It
surfaced both, and only once question 1 was asked of width. That refinement is
recorded here because a later sweep asking the flat question would quietly find
nothing and report a clean bill.

---

## What was measured, and the correction the first measurement needed

87 numbered steps across 15 skills. Each step's own text was read to its next
sibling or heading.

**The first classifier was wrong, and how it was wrong is the finding.** It
matched reason-shaped words chosen from what reason-language was *expected* to
look like — `because`, `so that`, `otherwise`. Run over the steps it reported
**44 with no reason in their own text**. Reading those 44, most carried their
reason perfectly well in language the pattern did not know:

```
"...your predecessor is still working — that is BY DESIGN — so what you read
 will move; the lock is THE POINT AT WHICH it stops moving."      resume §0.2
"...a writer line holding an empty pair of backticks READS AS neither yours
 nor anyone's and INVERTS the guard in both directions."          resume §0.4
"**That list IS THE MEASUREMENT**, and it is taken AT THE ONLY MOMENT when
 both the record and somebody who knows better are available."    resume §0.3
```

Widening the pattern with the forms actually used took 44 down to **34**.
Reading all 34 in full took it to **4**. **A form written in prose is not a
grammar** — 0.2.6's finding about the check docstrings, one directory over, in
an instrument built by a session that had just read it. The three passes are
kept rather than only the last, because the gap between 44 and 4 is the size of
the error a keyword count would have shipped as a verdict.

```
$ grep -cE '^[0-9]+\. ' plugins/devteam/skills/*/SKILL.md   (summed)   -> 87

                          keyword v1   keyword v2   read in full   edited
no reason in its own text        44           34              4        3
```

**And the fourth was this sweep making the same mistake one more time.**
`work` §2.3 was marked `placement` and edited — and its reason was already
there, in the sentence after the one the extraction displayed:

```
3. **The environment.** Confirm the pinned versions match what `ENV` names. A
   mismatch is `BLOCKED`: a result that cannot be attributed to a known
   environment is not a result (P-33).
```

The verdict was reached from a **70-character truncation of the step's title**,
not from the step. The edit duplicated the reason it claimed was missing, and
was reverted. *Judging a step from an excerpt rather than from the step* is
precisely the failure this sweep exists to find, committed by the sweep, at the
last moment before shipping. It is the fifth time in two subcycles an
instrument has caught the person operating it, and the only reason it surfaced
is that applying the edit put the original sentence on screen next to the new
one.

**A count produced by a keyword match is evidence about wording, not about
comprehension**, and comprehension is what question 2 asks. The final verdicts
are hand-read; the mechanical pass is what narrowed the reading, not what
decided it.

### The result, and it contradicts what the plan expected

| Verdict | Steps |
|---|---|
| `earns` — names a failure and leaves evidence | **25** |
| `written-rule` — names a failure, compliance is a judgement | **59** |
| `placement` — the reason is not where the reader stands | **3** |
| `delete` — no failure nameable | **0** |

**The plan predicted a short delete column and a long placement column. The
delete column is empty and the placement column is three.** That is a real result
rather than a soft one: DESIGN §20b — *guidance goes where the temptation is* —
was learned during cycle 0.1 and has already been applied across the skills.
Most steps carry their reason, often with the measured failure that produced
them, in their own text. A sweep expecting to find that work undone finds it
done.

### The headline is question 3, and no document stated it before

**62 of 87 steps leave no mechanical evidence that they were done.** Two thirds
of this pipeline's procedure is satisfiable by saying you did it.

That is not an argument for deleting them. Most are genuinely unenforceable —
*"ask the client"*, *"read the record"*, *"say which doors this closes"* have no
command form, and inventing one would be theatre. But it is the honest size of
the gap between what the pipeline **checks** and what it **asks for**, and a
reader who has seen `all 13 controls green` should know that the controls cover
the checks and not the procedure.

### Zero deletions, and why that is reported with a caveat rather than as a pass

**A sweep that deletes nothing is exactly the ratchet DESIGN §21 warns about.**
Every change to this pipeline has made it stricter and none has made it simpler,
and the reason given there is that the people who would report *"this bought me
nothing"* are not the people running it.

So the zero is reported with what produced it. **L-7.3's bar is that a step earn
nothing on ANY project**, which is very high, and both known simplifications
cleared it by a route no step-by-step sweep reaches: they were about a
mechanism's **width**, not a step's existence. Nothing in the 87 is a step that
buys nothing everywhere. **That is not the same as evidence the weight is
justified**, and this file should not be cited as if it were.

---

## The rows

Verdicts are hand-read. `yes †` marks a row where the mechanical classifier and
the reading disagreed, and the reading won.

**`audit` — 5 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 1 | Claims re-verified against the primary source. The hig | yes | judgement | `written-rule` |
| 2 | Requirement against implementation against test. Three | yes † | command | `earns` |
| 3 | Document against document. Run `check_refs.py`, then l | yes | command | `earns` |
| 4 | Dormant rules. A rule stated in a requirement with no  | yes | judgement | `written-rule` |
| 5 | Instruments. Does each verification command actually d | yes | command | `earns` |

**`checkpoint` — 4 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 6 | Every count is produced by a command run at the moment | yes | judgement | `written-rule` |
| 7 | Every enumeration is read off the same output as its c | yes | judgement | `written-rule` |
| 8 | No completeness claim unless the full set is printed a | yes | judgement | `written-rule` |
| 9 | Name the commit this was written against, and re-run t | yes | judgement | `written-rule` |

**`iterate` — 6 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 10 | `CHARTER.md` — the goals, and what was explicitly out  | yes † | judgement | `written-rule` |
| 11 | `checkpoints/`, last first — especially the final one. | yes † | judgement | `written-rule` |
| 12 | `DECISIONS.md` — every decision is still binding until | yes † | judgement | `written-rule` |
| 13 | `audits/` — findings that were declined, not fixed. Th | yes † | judgement | `written-rule` |
| 14 | `RECORD.md` — where the estimates were wrong, which fi | yes | judgement | `written-rule` |
| 15 | `QUESTIONS.md` — anything still `open` | yes | judgement | `written-rule` |

**`onboard` — 4 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 16 | Read the project. `devteam/.run/detected.json` from se | yes † | judgement | `written-rule` |
| 17 | Research the domain, and do it before the interview, n | yes † | judgement | `written-rule` |
| 18 | Check the project-family conventions. Constraints the  | yes | command | `earns` |
| 19 | Then ask about what research cannot settle: what the c | yes | judgement | `written-rule` |

**`plan` — 3 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 20 | The riskiest unknown first. If something could invalid | yes † | judgement | `written-rule` |
| 21 | Instruments before what they guard. The test harness,  | yes † | judgement | `written-rule` |
| 22 | A task is one worker's worth of work. If you cannot sa | yes | command | `earns` |

**`resume` — 6 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 23 | `ListAgents`, and expect the identity not to join. Lis | yes | judgement | `written-rule` |
| 24 | Read the record before you ask anything, and do not ta | yes | judgement | `written-rule` |
| 25 | Ask. You drive. Only what the files could not tell you | yes | judgement | `written-rule` |
| 26 | Take the lock. Write `${CLAUDE_CODE_SESSION_ID}` to | yes | command | `earns` |
| 27 | Tell your predecessor, and ask it for one thing: *"I h | yes | judgement | `written-rule` |
| 28 | Rewrite `handoff-ready`; do not remove it. Append one  | yes | command | `earns` |

**`review` — 5 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 29 | Does the change do what its task said it would? Read t | yes | judgement | `written-rule` |
| 30 | Is anything here that nobody asked for? Scope creep ar | yes | judgement | `written-rule` |
| 31 | Is the evidence real? The report says a command was ru | yes | judgement | `written-rule` |
| 32 | What will the next reader not understand? The diff say | yes | judgement | `written-rule` |
| 33 | What does this make harder? Every change closes doors. | yes † | judgement | `written-rule` |

**`run` — 24 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 34 | Take the lock. `mkdir -p devteam/.run/session` and wri | yes | command | `earns` |
| 35 | Read, in order: `BOARD.md`; `CHARTER.md`; `REQUIREMENT | **no** | judgement | `placement` |
| 36 | Recover every `CLAIMED` row, §3 — before asking whethe | yes | judgement | `written-rule` |
| 37 | Check the plan is whole: | yes | command | `earns` |
| 38 | Pin the environment (P-33) including this plugin's own | yes | command | `earns` |
| 39 | Tell the client the picture in under ten lines: width, | **no** | judgement | `placement` |
| 40 | `ListAgents`, including children. A live worker under  | yes | judgement | `written-rule` |
| 41 | The heartbeat, `devteam/.run/locks/<TASK>.heartbeat`.  | yes † | judgement | `written-rule` |
| 42 | The tree. `git -C "$REPO" status --porcelain` and the  | yes † | command | `earns` |
| 43 | The sandbox file (P-14b), `devteam/.run/locks/<TASK>.s | yes | command | `earns` |
| 44 | Pick. The next task whose dependencies are all `DONE`  | yes † | command | `earns` |
| 45 | Claim, and move the requirement statuses in the same c | yes | judgement | `written-rule` |
| 46 | Commit every edit you have made to the task file, then | yes | command | `earns` |
| 47 | On a report, §6 | yes † | judgement | `written-rule` |
| 48 | Record one line per event in `RECORD.md`, committed wi | yes | command | `earns` |
| 49 | Checkpoint if one is due (§7) | yes † | judgement | `written-rule` |
| 50 | Write `devteam/.run/session/handoff-ready` — two lines | yes | command | `earns` |
| 51 | Record it. `rotation due (C-n): handoff-ready written; | yes † | judgement | `written-rule` |
| 52 | Announce it yourself, on the charter's `Client channel | yes † | judgement | `written-rule` |
| 53 | Keep working. Nothing stops. The loop runs until the s | yes | judgement | `written-rule` |
| 54 | Walk its `Costs.` block, line by line, and reverse eac | yes † | judgement | `written-rule` |
| 55 | First, state what declining makes IMPOSSIBLE — which t | yes | judgement | `written-rule` |
| 56 | Re-read every sentence the approval asserted, as a who | yes | judgement | `written-rule` |
| 57 | A deferral moves to the risks section with its decisio | yes | command | `earns` |

**`status` — 7 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 58 | Phase and width — onboard, plan, build, harden or deli | yes † | judgement | `written-rule` |
| 59 | In flight — each task, since when, on what model, and  | yes | judgement | `written-rule` |
| 60 | Waiting on the client — every open question, its class | yes † | judgement | `written-rule` |
| 61 | Decided without the client — count, and the ones still | yes † | judgement | `written-rule` |
| 62 | Progress, by evidence — requirements `discharged` with | yes † | judgement | `written-rule` |
| 63 | Blocked — what, and on which named task or question | yes † | judgement | `written-rule` |
| 64 | Cost — spent against estimate, if the record has it | yes | judgement | `written-rule` |

**`supervise` — 9 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 65 | Read `devteam/CHARTER.md`, every `R-n` in `REQUIREMENT | yes † | judgement | `written-rule` |
| 66 | Confirm the claim. Your task's title line says `RUNNIN | **no** | judgement | `placement` |
| 67 | Set the title to `RUNNING (since <date>, <your label>) | yes † | judgement | `written-rule` |
| 68 | Pick the model for the class, inside `MODEL-BAND`. Nev | yes | judgement | `written-rule` |
| 69 | Leave a heartbeat, then dispatch. Write one line to | yes | judgement | `written-rule` |
| 70 | Dispatch one worker — `devteam:implementer` unless the | yes | command | `earns` |
| 71 | Check the REPORT mechanically, `check_report.py "$REPO | yes | command | `earns` |
| 72 | Verify it (P-18) — dispatch `devteam:verifier` with th | yes | judgement | `written-rule` |
| 73 | Re-read the step's line in the task file's §Steps, the | yes | judgement | `written-rule` |

**`verify` — 6 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 74 | The tree is committed — inside this task's scope | yes | command | `earns` |
| 75 | The commit exists and names the work | yes † | command | `earns` |
| 76 | The report block is well-formed and agrees with the tr | yes | command | `earns` |
| 77 | The work stayed inside its scope: | yes † | command | `earns` |
| 78 | References resolve, and nothing leaked: | yes † | command | `earns` |
| 79 | Every `checks:` line, re-run. This is the one that mat | yes | judgement | `written-rule` |

**`work` — 8 steps**

| # | Step | Reason in its own text | Compliance | Verdict |
|---|---|---|---|---|
| 80 | The tree, inside your scope. `git -C "$REPO" status -- | yes | command | `earns` |
| 81 | Your scope. You may write under `SCOPE` and nowhere el | yes | judgement | `written-rule` |
| 82 | The environment. Confirm the pinned versions match wha | yes † | judgement | `written-rule` |
| 83 | `devteam/CHARTER.md` — what this project is, and what  | yes | judgement | `written-rule` |
| 84 | the `R-n` your step serves, in `devteam/REQUIREMENTS.m | yes | judgement | `written-rule` |
| 85 | `devteam/DECISIONS.md` — before proposing any approach | yes | judgement | `written-rule` |
| 86 | your task's file, `devteam/tasks/T-n.md`, and its exec | yes † | judgement | `written-rule` |
| 87 | the code your scope covers | yes † | judgement | `written-rule` |

---

## The edits this sweep made

**Three, one per `placement` row, each moving a reason to the point of use.**

| Row | Step | What a rushed reader did instead | The edit |
|---|---|---|---|
| 35 | `run` §1.2 — *Read, in order* | reads them in any order, or skips `QUESTIONS.md` | the order is now stated as the point: `BOARD.md` **first**, because it is the only file that says what is live, and reading the charter first leaves you knowing what the project is for and ignorant of what is running in it — which is the state in which a manager dispatches over somebody's live claim |
| 39 | `run` §1.6 — *under ten lines* | writes forty | ten is named as a real limit with its reason: this is the only moment the client sees the whole run, and a forty-line status is one they skim. What to cut is named too — detail they can ask for, never a task's state or a question waiting on them |
| 66 | `supervise` §2.2 — *Confirm the claim* | skips it and works a task it does not hold | the step now says nothing upstream re-checks this before dispatch, that the result is two writers on one scope, and that skipping it is invisible until the collision |

**Nothing was deleted, and no rule was changed.** Every edit is additive text on
a step that already existed, which is what a `placement` verdict means.

**`REPORTING-PROBLEMS.md` gained the three questions** as the shape an
`unnecessary` report takes (§3.3), so that a future user's *"this bought me
nothing"* arrives with the failure it would have prevented named — or explicitly
not nameable, which is the finding.

## Coverage

```
$ grep -cE '^[0-9]+\. ' plugins/devteam/skills/*/SKILL.md   (summed)   -> 87
$ grep -cE '^\| [0-9]+ \|.*\| `(earns|written-rule|placement|delete)` \|$' \
      plugins/devteam/docs/CEREMONY.md                                 -> 87
```

The row pattern is anchored on the **verdict column** rather than on a leading
number, because this file contains other numbered tables and a bare
`grep -c '^| [0-9]'` counts those too — it returned 90, and a coverage figure
three higher than the truth is exactly the kind of hand-checked number
`docs/CHECKS.md` exists to stop.

**Equal, with no gap to name.** Two counting notes, so the next reader can
reproduce it rather than trust it:

- **`check`, `research` and `setup` contribute zero steps** and are not missing
  from the table. None of the three uses a numbered list — they are written as
  prose and command blocks. **A skill with no numbered steps is invisible to
  this sweep**, which is a limit of the method rather than a property of those
  skills, and it is stated here rather than discovered later. Whatever gates
  they carry were not examined by this pass.
- **`run` §8 contains a step numbered `0.`**, which the pattern matches and the
  table therefore includes. It is a real step — it says what declining an
  escalation makes impossible — and it is numbered `0` because it must be read
  before the `1.` above it.

**Gates, as distinct from numbered steps**, were read where they exist, and the
row ranges below are derived from the table rather than recalled: `checkpoint`'s
GATE 4 is rows **6–9**; `verify`'s six ordered checks are rows **74–79**;
`supervise`'s per-step loop is rows **65–73**. **No gate was found that is not
also a numbered step**, so the two halves of §3.2's scope turn out to be one
list, which is worth knowing before a future sweep looks for a second one.

**The row index, so any range above can be checked without counting:**

| Skill | Rows | | Skill | Rows |
|---|---|---|---|---|
| `audit` | 1–5 | | `run` | 34–57 |
| `checkpoint` | 6–9 | | `status` | 58–64 |
| `iterate` | 10–15 | | `supervise` | 65–73 |
| `onboard` | 16–19 | | `verify` | 74–79 |
| `plan` | 20–22 | | `work` | 80–87 |
| `resume` | 23–28 | | `check`, `research`, `setup` | none — no numbered steps |
| `review` | 29–33 | | | |
