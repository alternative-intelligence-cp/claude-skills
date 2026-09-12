# Backlog for v3 — the liaison layer, the specialist decomposition, and what the v2 run measured about both

**Status: PROVISIONAL. Nothing here is settled architecture.** Filed
2026-09-12 at the author's request, *while the v2 experiment is still
running*, expressly so that recording it does not interrupt the run. It is
a backlog to be worked into the roadmap later, not a plan.

The author's own caveat governs the whole document:

> *"That's still just an idea at the moment though. Don't want to get too far
> ahead of myself while the v2 test is still ongoing. Its results may end up
> changing my plans entirely."*

**Three voices, marked throughout.**

| Mark | Who | Weight |
|---|---|---|
| `[AUTHOR]` | Randy, in conversation 2026-09-12 | his, and the only ratified voice here |
| `[LIBS]` | `nitpick-libs_s4`, the library workbench's listener seat | suggested, unratified |
| `[PM]` | `claude-skills-devTeam_s12`, project manager for `pricelog` cycle 1 across its whole build phase | suggested, unratified |

**A provenance warning about the `[PM]` sections, because it changes what
their agreement is worth.** The PM undertook to write its own list *before*
reading the `[LIBS]` backlog, precisely so that agreement between two
independently-formed lists would mean something. **It did not manage to —
the backlog arrived in the same turn.** So every `[PM]` corroboration below
is **post-hoc**, and post-hoc agreement is a much weaker signal than
independent agreement. Where a `[PM]` note cites a *measured figure from the
v2 run*, the measurement is independent even though the framing is not, and
those are the parts to weigh.

---

# Part I — the backlog as received

## 1. The problem the liaison solves  [AUTHOR]

v2 rotates at both the **supervisor** and **project manager** levels to keep
context windows small. That works: *"superb at keeping context precise and
costs down."*

**But something has to rotate the PM, and that something is currently him.**
Opening a session and typing a command is trivial; that is not the problem.
The problem is that it **creates a hard pause waiting for the user to
return**, in a system *"meant to kind of run in the background for possibly
lengthy periods"* — and does so *"while not adding anything to safety or
quality in the way a planned verification checkpoint would."*

**The governing test for every human-in-the-loop step in v3:** a pause must
buy safety or quality. A checkpoint where the client reviews a plan, signs a
charter, rules on a question or verifies a claim earns its place. **A pause
that exists only because a mechanism was never automated buys nothing and
costs the whole idle interval.** Mechanism belongs inside the system.

## 2. The liaison, as described  [AUTHOR]

A layer between **client** and **project manager**.

- The **only** layer that talks to the client.
- **Spawns and rotates the PMs**, and keeps the process going.
- **It cannot rotate itself.** *"The buck has to stop somewhere … it must
  keep the thing afloat at all times."*
- **Idle most of the time.** Four touchpoints: the **interview and kickoff**,
  **rotations**, **escalations needing the client**, and the **end showoff
  and chance to iterate**.
- **Knows very little about the project** — how to relay, how the structure
  works, how to keep going. *"The research and planning would be handled
  underneath and then just be presented through the liaison for client to
  verify."*

## 3. The context problem  [AUTHOR]

Because it cannot rotate, the liaison will **auto-compact**. That bounds its
growth — *"it can't technically grow without bounds"* — but **reintroduces
the degraded-context problem rotation was built to solve.** His concern:
*"I don't know that it will receive any kind of notification itself that it
even happened."* Proposed mitigation: check its bearings on a schedule.

## 4. A better mitigation, already shipped in the Nitpick workbench  [LIBS]

**A `SessionStart` hook fires at the exact moment.** From
`nitpick-libs/hooks/hooks.json`, matcher `compact|resume`, running
`reinject_orchestrator.py`. The `[LIBS]` seat is the evidence it works: the
hook fired in that session and told it to re-read `BOARD.md`, reconcile the
in-flight table against `ListAgents`, not redo what the board shows done,
and take width and streams from the board header — *"not your memory."*

**Why a hook beats a schedule:** a schedule *polls for* a state change; a
hook **is** the state change. And a scheduled self-check costs tokens on
every tick that finds nothing, which for a mostly-idle layer is nearly all
of them.

## 5. The liaison needs a `BOARD.md`  [LIBS]

Everything it needs is **static** — how to relay, how the structure works,
the rotation procedure — and **belongs in files, not in context.** The only
thing acquired at runtime is **the client's standing answers from the
interview, which should be written to a file at interview time precisely so
a compaction cannot take them.**

Then *"checking its bearings"* stops being introspection of a degraded
context and becomes **re-reading a document**, and compaction loses only
working memory, which nobody minds losing.

## 6. Growth is linear in rotation count, not project size  [LIBS]

If the liaison acts only at the four touchpoints, its context grows by **one
brief in and one brief out per rotation** — budget ≈ *N rotations × brief
size*, estimable in advance.

**The invariant that keeps it true: the liaison never reads a worker's
output, only a PM's summary of one.** If it ever breaks you see superlinear
growth and know which rule leaked. **The one number worth instrumenting:
liaison tokens per rotation.** Flat means sound; creeping means something
below is leaking upward.

## 7. Model routing  [AUTHOR's framing; carve-outs LIBS]

**[AUTHOR]** The liaison *"can probably be a much cheaper model — it doesn't
do much reasoning … it's more a relay and overseer."* **Sonnet**, since
Sonnet usage on the $200 plan is *"practically unlimited"*. **Planning needs
Opus minimum, possibly Fable**, because any project simple enough for a
cheap planner does not need the tool: *"for simple projects the complexity
of the tool outweighs the cost. It's more for things you can't accomplish in
a one or two prompt session with one model."*

**[AUTHOR]** And the decomposition that makes it affordable: *"Perhaps
planner could be a separate role that is invoked for that task alone so
escalation to the higher model there wouldn't be a decision that propagated
to other parts."*

### Carve-out 1 — the interview is a ROLE, not a LAYER  [LIBS]

`devteam:onboard` requires **"pressing on ambiguity rather than accepting
it"** — a call about the **shape** of an answer, not a lookup. **A weaker
model that accepts a vague answer produces a charter that looks signed and
is not, and every plan downstream inherits it.**

**The fix follows the author's own planner insight.** A Sonnet liaison
**dispatches** the interview to an Opus/Fable interviewer and holds the
resulting charter file. **Cheaper than a smart liaison, not more expensive**
— the interview happens once; a premium layer lives for the whole run.

### Carve-out 2 — escalation as a classification, not a judgment  [LIBS]

A cheap model gets *"emergencies or verifications that need bubbling up"*
wrong in **both** directions: too much rebuilds the hard pause; too little
and the client meets a wrong decision at showoff.

`devteam:run` already batches by **reversibility class**. Written as a rule
the liaison applies rather than taste it exercises:

```
irreversible                          -> escalate now
reversible AND within charter         -> decide, log it, carry on
reversible BUT outside charter        -> batch for the next checkpoint
```

**That is what makes a cheap model safe: it applies a rule instead of
exercising taste.** Put it in the file the reinject hook points at.

### Condition — the liaison must be the MOST instrumented layer  [LIBS]

It is simultaneously the **cheapest-reasoning** and **highest-consequence**
layer, and **its failures are silent**: if it stops rotating or relays a
garbled brief, nothing errors — everything below simply waits, and waiting
is indistinguishable from working from outside.

**So its actions must be checkable from outside it: the liaison writes what
it did to a file, and something else reads it.** A rotation log the client
can open makes a Sonnet liaison *verifiable*. One that keeps its history in
context does not.

## 8. The hard part of rotation is the BRIEF, not the spawning  [LIBS]

Measured on the Nitpick **compiler** side: six sessions, more than one
model, one week. Three pieces of discipline in flight across one handoff:

| Item | Outcome | Form it was handed over in |
|---|---|---|
| the floor-move protocol | **survived 3 handoffs** | a **quoted value plus a procedure** (the previous digest, its byte count, and the reason) |
| the six-row digest ladder | **lost at the first** | a **convention** observed in practice |
| a numeric correction | **lost at the first** | **prose** about which number means what |

**Same sessions, same channel, same week. The only difference was form.**
The outgoing session's own account of the resulting error: *"invisible from
inside the session that made it."*

**What survives a rotation is what was handed over as a value with a
procedure attached. A convention merely practised and a correction merely
explained do not travel.** v3's PMs will rotate onto **different models with
cold caches** — precisely the condition under which prose briefs fail. **The
liaison's generated PM brief is a template problem, solvable in advance, and
it determines whether automated rotation works at all.**

## 9. A taxonomy of four error shapes  [LIBS]

Every error between two *disciplined* sessions that week fell into four
shapes. If v2's kinks look like these, the fix is structural, not more care.

1. **A count taken over the wrong denominator.** 264/747 reported against a
   real 145/170. `find` swept 563 gitignored files in; Python's `glob` with
   `**` silently skipped them. **Two methods wrong in opposite directions,
   neither the answer; `git ls-files` is authoritative** — and the repo's own
   check script had been printing the right number beside the wrong one.
2. **A true number wearing another number's name.** 368 manifest rows
   reported as 439 harness count; 137 symbols described against 85 with
   evidence; "7 residue" where the file's verdict word is `budget`.
3. **A citation that does not resolve** — a pointer to a section that
   existed only in an unlanded commit.
4. **A hand-written summary of a generated fact drifting from the fact.**
   The generated document was right all three times; the prose drifted.

**The rule: an unchecked restatement is not redundancy.** Where a fact is
generated, make the generated artefact the only statement of it. Where two
implementations can produce the same artefact, have both and compare — the
compiler's two syscall-table generators disagreed on their first joint run,
and the disagreement was a real defect no test of either would have caught.

## 10. The complexity principle  [AUTHOR]

> *"Complexity where required is fine. Complexity for complexity's sake is
> not. I see a lot of the latter sometimes and I think it's because people
> like to think that the more complex the thing you make is the smarter you
> are but I am of the opposite camp. Genius is taking the complex and making
> it simple, not the other way around."*

**[LIBS] The measure that reconciles this with adding a layer: count
requirements per part, not parts.** One layer smart enough to interview,
cheap enough to idle for days, and reliable enough never to drop the baton
carries **three contradictory requirements**. A cheap durable relay plus
expensive short-lived specialists gives each part **one**. The diagram gets
bigger and every decision gets easier. **Any structure in v3 should be
traceable to the requirement it isolates.**

---

# Part II — what the v2 run measured  [PM]

Post-hoc, as warned above. The **figures** are independent; the framing is
not. `<run>` below means the `pricelog` cycle-1 build phase, six of eight
tasks closed across three manager sessions.

## A. §8 is the strongest item here, and `<run>` corroborates it from a different project

Three independent instances, all matching *value-plus-procedure survives,
convention and prose do not*:

- **Everything that survived the two rotations was a file.** The board, the
  record, the task files, the decisions. Nothing that lived in a transcript
  survived.
- **Ten `record defect:` lines across two rotations — five each — and every
  one was something that lived only in a message.** The sharpest:
  `promote.lock`'s inertness was established at rotation 1, put in a
  *message* rather than a file, had to be re-asked at rotation 2, and was
  re-derived from source a third time at rotation 3. **A fact worked out and
  not written down is a fact the project does not have.**
- **F-31, and it is §8 with a cost attached.** One supervisor worked out that
  its step workers must not touch the task file, put that in its *step
  dispatches*, and its workers cited it. **Dispatches are not inherited.**
  The next task's supervisor never learned it and paid **three cherry-pick
  recoveries in one task** — three of four successful dispatches.

**`[PM]` recommendation: treat §8 as the load-bearing item and the liaison as
the thing that carries it.** The liaison's value is not that it spawns a PM;
it is that it is the only component positioned to emit a *templated* brief
rather than a prose one.

## B. A measured caution on the four-touchpoint duty cycle  [PM]

The liaison is described as idle but for four touchpoints. In `<run>` the
client channel carried **far more than four exchanges**, and at least two
produced course corrections that would otherwise have been lost — a batch of
five questions answered in one sitting, and one instruction (*"great. lets
continue."*) that **reached no file and was found missing by the next
manager**.

Two readings, and the difference matters:

- Most PM→client traffic in `<run>` was **narration** the liaison could drop
  without loss; four touchpoints is then right.
- Or some of it was **load-bearing** and a four-touchpoint liaison silently
  removes it.

**Not resolvable from `<run>` and worth deciding deliberately rather than by
omission.** The measurement that would settle it: count how many PM→client
exchanges in cycle 2 changed a subsequent decision.

## C. "Knows very little about the project" conflicts with carve-out 2  [PM]

To classify a question as *reversible AND within charter* you must **read the
charter and understand the question**. That is project knowledge, and it is
the judgment `<run>` most often got wrong.

**Evidence:** the escalation on `change.render`'s confidently-wrong outputs
was called *"the one with a deadline"* by one manager — which silently
classes it `REVERSIBLE`, something a window can expire. **It was `CHARTER`**,
which always blocks. The misclassification survived **because no class had
been written down at all** — there was no wrong answer to disagree with.

**So carve-out 2 is right and its failure mode is not the one stated.** The
risk is not that a cheap model classifies badly; it is that **nobody assigns
a class**, and prose around the question then implies one. **The mechanical
form: a question without a class is not a question, and the file the liaison
reads should refuse to carry one.**

## D. The one number §6 wants instrumented is the one the current meters cannot see  [PM]

§6 asks for **liaison tokens per rotation**. `<run>` found (**F-33**) that
the charter's budget ceiling measures exactly two things — `session_cost.py`
over manager sessions, and `cost_usd` from each worker sandbox's
`budget.json`. **An agent dispatched through the Agent tool is neither**: no
sandbox, no budget file, not the manager's session. One task alone ran six
such dispatches totalling **572,082 tokens**, attributable to neither half.

**A liaison would be exactly that kind of agent.** So §6's instrument does
not exist yet, and building it is a prerequisite rather than a follow-up.

**And the sharper half:** across two rotations and six closed tasks in
`<run>`, **nobody ever read the budget ceiling at all.** It was amended into
two measurable units specifically so it *could* be read. The incoming third
manager was the first party to ask, and asked before dispatching rather than
after. **A stop that is never read is a stop that cannot fire**, and it is
carried as protection meanwhile.

## E. A fifth error shape for §9, and it is a different class from the other four  [PM]

§9's four shapes are all about **a number being wrong**. `<run>` produced a
fifth about **a check not running**, and it is harder to see because the
output is indistinguishable from success:

> **An instrument returns the shape of "nothing wrong" when what actually
> happened is "nothing was looked at."**

Four mechanisms in one run, all with that signature:

1. **`check_trace && check_refs`** — `check_trace` exits non-zero
   *permanently* in that project over one approved finding, so the second
   check **never runs** and the silence reads exactly like a clean pass. A
   manager reported "checks clean" on output that was never produced.
2. **`check_refs` on an untracked file** — it enumerates with `git ls-files`,
   so a newly created file declaring an identifier is invisible, and
   `cited-undefined` fires on a declaration sitting on disk.
3. **`budget-mismatch` and the honest hedge** — the regex needs a digit after
   `=`; four workers wrote `tokens=~N` because none can read its own counter,
   and **four mismatches of 15×–36× went unflagged.** The check declined to
   parse the answer's honest form. **The incentive runs backwards.**
4. **A lookup whose log contains its own query** — the session-id-to-name
   grep works with `head -1` and returns an **empty name** with `tail -1`,
   because the transcript fills with the pattern as soon as two sessions
   discuss it. **It gets more broken the more it is adopted.**

**Why this belongs beside §9 rather than inside it:** §9's rule — *an
unchecked restatement is not redundancy* — fixes wrong numbers. It does not
reach a check that was never run, because there is no restatement to
compare. **The counterpart rule: every check must be shown to fail.** In
`<run>` the commit gate was mutation-tested three separate times, and each
time it had been made *more permissive* — twice it turned out to be keying on
the wrong fact and refused for the wrong reason. **A permissive branch that
has never been seen to refuse is indistinguishable from one that cannot.**

**And §9's own shape 4 has a `<run>` instance worth adding**: the metered
dollar figures survive **only because supervisors copied them out by hand
before closing their sandboxes**, since closing destroys the generated
`budget.json`. That is an unchecked restatement which is also *the only
surviving copy* — the generated fact is deliberately destroyed by the
protocol. If a supervisor ever stops copying, the numbers vanish silently.

## F. Where `[PM]` pushes back — the unrotatable liaison  [PM]

*"The buck has to stop somewhere"* is true of **responsibility**. It does not
follow that it is true of **context**, and the two are being merged.

**The proposal's own §5 undoes the premise.** If everything the liaison needs
is in files — the relay procedure, the structure, the classification rule,
the client's standing answers — then a liaison **is** rotatable, because a
successor could read those files exactly as `<run>`'s third manager read the
board and record. What genuinely cannot rotate is only *the thing that starts
the next one*.

**So the question worth asking is: what is the smallest component that cannot
be rotated?** Making the *whole liaison role* unrotatable means accepting a
growing, compacting context in the highest-consequence layer — which is the
exact failure the design set out to avoid, relocated one level up. Making
only *the restarter* unrotatable means a hook, a cron entry, or a few lines
of script, which has no context to degrade.

**`<run>` bears on this directly and in the design's favour on one point: the
PM session that wrote this document ran a full build phase — 207 requests,
60,144,065 tokens processed — and never compacted once.** So a mostly-idle
liaison honouring §6's invariant may well never compact either, and the
compaction worry may be smaller than feared. **But "may well never" is not a
property to build on**, and the cheap alternative — an unrotatable script
rather than an unrotatable agent — costs almost nothing to adopt.

## G. The rotation pause was partly a choice, not only a missing mechanism  [PM]

Worth flagging because it changes what automating rotation buys.

`run` §7b is explicit: *"Keep working. Nothing stops. The loop runs until the
successor takes the lock."* **Both of `<run>`'s outgoing managers
deliberately declined to dispatch the next task before handing over**, for a
reason each stated: *"handing you a live claim you never made, minutes before
the lock moves, is worse than a clean board."* The successor, having received
that clean board, confirmed it was right.

**So part of the pause was a judgment about handoff quality, not an absence
of automation.** A liaison that rotates PMs automatically does not remove
that judgment — **it moves it.** The incoming PM still inherits whatever the
outgoing one left, and "clean board versus keep working" still has to be
decided by someone.

**The design question that follows: does the liaison enforce a clean board at
rotation, or does it hand over live claims?** `<run>` has three data points
and they all favour the clean board — the third handoff was the cheapest of
the three, and the successor's stated reason was that *what earlier rotations
had to ask about was in the files this time.*

## H. On §10, one caution  [PM]

*Count requirements per part* is a good measure and `<run>` supports it. But
`<run>`'s single largest process finding was **a seam**, not a part:

**F-31** — the work discipline tells **every** worker to append its report to
the task file; the task file is in **no step's scope** by the design's own
construction. So every *compliant* worker leaves an out-of-scope uncommitted
edit and promotion refuses it. **The one worker that escaped did so by
disobeying.** Neither rule is wrong. They meet on every step.

**So pair the measure: count the requirements each part carries, and count
the seams the split creates.** A decomposition that gives every part one
requirement and introduces six new handoffs may be worse than what it
replaced, and the v2 run's most expensive defects were all at joints — F-31
between two rules, F-33 between two meters, the lost `promote.lock` fact
between two sessions.

---

## What `[PM]` would do first, if any of this is adopted

Ranked, and every one is cheap:

1. **§8's brief template.** Highest leverage, solvable in advance, and it is
   the thing that decides whether automated rotation works at all. `<run>`
   corroborates it three separate ways.
2. **Build §6's meter before the layer it measures.** F-33 says it does not
   exist. A layer you cannot meter is a layer whose invariant you cannot
   check, and §6's whole argument rests on watching one number stay flat.
3. **Make a missing escalation class a refusal.** Cheapest of all — the
   failure in `<run>` was an unassigned class, not a misassigned one.
4. **Decide the clean-board question (§G) deliberately.** It is free to
   decide now and expensive to discover later.
5. **Re-examine the unrotatable liaison (§F)** against the possibility that
   only the restarter needs to be unrotatable.

**And the one thing `[PM]` would not do:** treat any of this as settled while
cycle 2 is still running. The author's caveat is the correct posture, and
`<run>` has already produced two findings that reversed an earlier
conclusion — one of them a claim asserted as fact in two dispatch briefs and
refuted by a worker who contradicted its own manager.

---

# Part III — addendum, 2026-09-12: a provisioned resource nobody could see

## The observation  [LIBS]

The author was asked, before the v2 run, to open a session named
`claude-skills-devTeam-test_s1`. **He has kept it open for two days and
reports he cannot see where it was ever used** — *"perhaps they decided to go
a different route. In any case, I was not told that yet so I left it open."*

**The cost here is one idle session; the shape scales badly.** The client is
left maintaining state for a requirement that may no longer exist, with no
way to tell *"still needed later"* from *"quietly abandoned"* except by
asking — which spends the one resource the whole rotation design exists to
conserve.

**Suggested rule:** anything the plan asks the client to **provision, open,
install or keep alive is a commitment to the client.** If it stops being
needed, **say so at the moment the plan changes** — not at the close, and not
only when asked. The Nitpick compiler side models the discipline: when it
merged two planned subcycle steps it **declared the deviation in one
sentence with its reasoning** rather than taking it silently.

## What actually happened, checked rather than assumed  [PM]

**The route did not change. The reservation was real, explicit, and every
rotation ignored it.** `0.2.9.md:330–338`, verbatim:

> **Rotation needs a session with near-zero context, and one is standing
> by.** … an idle session opened earlier and never briefed satisfies it as
> well as a brand-new one does. **`claude-skills-devTeam-test_s1` is open,
> unbriefed and reserved for this.** … **If `-test_s1` is gone by the time
> the checkpoint arrives, ask the owner to open one — do not rotate into a
> session that has been carrying context.**

**Three rotations happened. None used it.** `_s10`→`_s11`, `_s11`→`_s12`,
`_s12`→`_s13` were all freshly opened sessions. The reserved seat sat idle
for two days doing precisely what it was reserved to do — hold near-zero
context — and was never called on.

## The finding is not a reporting failure, and that is the useful part  [PM]

**No manager in the run could have known it existed.**
`grep -rniE "test_s1|devTeam-test"` across the entire `pricelog/devteam/`
tree returns **nothing**. The reservation lives in the *experiment's roadmap
plan*, inside `claude-skills`; a project manager reads the *project's*
charter, board, record, questions and task files. **The two document sets
never touch.**

So this is not three managers each forgetting to report a deviation. **It is
a provisioned prerequisite recorded in a document that none of the parties
who would consume it ever read** — and each of three rotations independently
re-derived "open a fresh session" from `run` §7b's own wording, which is
exactly what the plan anticipated and tried to pre-empt.

**This manager is one of the three and states its own part plainly:** its
rotation announcement quoted §7b's *"start a fresh session in this
directory"* and never checked whether a session had already been provisioned
for the purpose. It had the plan available in its own launch repository and
did not look, because nothing in the project it was managing pointed at it.

## The rule that follows, and it is mechanical rather than remembered  [PM]

The `[LIBS]` rule — *say so at the moment the plan changes* — is right and
does not reach this case, because **the plan never changed.** The stronger
form:

> **A client-provisioned prerequisite must be recorded in the document the
> party who will consume it actually reads.** For a devteam run that is the
> charter or the board — not the roadmap plan, not the experiment's
> subcycle file, and not a message.

**Both halves are needed.** `[LIBS]`'s rule covers a prerequisite that stops
being necessary; this one covers a prerequisite that stays necessary and is
never seen. This run produced the second and the first is the one everybody
watches for.

**The natural home is the charter's constraints table**, which is already the
place a manager re-reads on a cadence, and which already carries rows that
bind the run — `Containment`, `Model band`, `Client channel`. A
`Provisioned by the client` row would have been read at every startup by
every one of the three managers.

**And the check that makes it verifiable rather than hopeful:** if such a row
exists, its live status can be checked the same way `run` §5b re-proves
containment at every startup. A prerequisite the client is maintaining should
be something the run *confirms it still wants* on a schedule, not something
the client asks about.

## Live status, for the author  [PM]

**One more rotation is likely.** Cycle 1 has T-6 and T-7 outstanding; closing
both makes eight, which triggers C-4 under the every-two cadence, and
rotation follows a checkpoint. **So `-test_s1` still has a use if the author
wants the plan honoured** — it remains unbriefed and idle, which is exactly
the state the reservation requires. Otherwise it can be closed, and the
reservation should be struck from the plan rather than left to look
unfulfilled.
