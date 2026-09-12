# DEV TEAM — structure chart

Companion to [`v3-liaison-and-roles-2026-09-12.md`](v3-liaison-and-roles-2026-09-12.md),
which carries the reasoning and the measurements this chart is annotated from.

**Provenance.** The base sketch (`v0`, preserved at the bottom) is the
author's, drawn **before v2's planning and decisions existed**. He found it
again on 2026-09-12 while the Nitpick libraries were paused, kept it because
the **liaison** idea in it looks like it may solve a problem v2 actually hit,
and asked for it to live somewhere it would be found rather than in a folder
he would forget. **It is v0 brought forward, not v0 critiqued.**

**Status: PROVISIONAL.** The v2 cycle is still running and its results may
overtake any of this.

```text
DEV TEAM — STRUCTURE SKETCH
v1, 2026-09-12. Revised from the author's v0, preserved verbatim at the
bottom of this file.

**v0 PREDATES v2.** It is a sketch the author drew before v2's planning and
decisions existed, found again on 2026-09-12 while the Nitpick libraries
were paused, and kept because the LIAISON idea in it looks like it may solve
a problem v2 actually hit. That matters for how the marks below read: most
of them are not "this was dubious", they are "v2 settled this after you drew
it". Nothing here is a critique of v0. It is v0 brought forward.

  [v2]  v0 predates this; v2 answered it, and the answer is filled in
  [~]   changed, and the change is a v3 PROPOSAL rather than settled
  [+]   added, not in v0 at all
  [?]   still genuinely open — nobody has settled it

Reject any of them; the reasoning for each is in NOTES below.

===============================================================================
THE PEOPLE-AND-AGENTS SIDE
===============================================================================

CLIENT
  answers the interview, signs the charter, rules on escalations,
  inspects at checkpoints, accepts or iterates
  |
LIAISON                                          [cheap model; never rotates*]
  the only layer that talks to the client. initiates/resumes, relays,
  logs every interaction, answers common questions from the docs.
  mostly mechanical, little reasoning.
  [~] does NOT interview. dispatches an Interviewer. see NOTE 4.
  [+] applies the escalation CLASSIFICATION, does not exercise judgement:
         irreversible ................... escalate now
         reversible, inside charter ..... decide, log, carry on
         reversible, outside charter .... batch for next checkpoint
  [?] *"never rotates" may be wrong — see NOTE 1.
  |
SENIOR PROJECT MANAGER                                     [? see NOTE 2]
  high-level scheduling of the phases below, and routing.
  [?] does this need to be an agent, or is it the BOARD?
  |
  +-- PLANNING MANAGER ....... get a charter and plan drafted, reviewed, signed
  |     [v2] no supervisor tier — v2 dispatches these directly. NOTE 3.
  |     |
  |     +-- Interviewer ....... presses on ambiguity. HIGHEST-LEVERAGE ROLE.
  |     |                       needs the strongest model. NOTE 4.
  |     +-- Researcher ....... dated, sourced facts from outside the project
  |     +-- Planner .......... requirements -> task graph, scopes, gates
  |     +-- Budgeter ......... [+] estimates, and OWNS the ceiling. NOTE 7.
  |     +-- Plan Auditor ..... attacks the plan before anything is built
  |
  +-- IMPLEMENTATION MANAGER ...... turn the plan into a working product
  |     [v2] keeps the supervisor tier — this is where work HAS steps
  |     |
  |     +-- SUPERVISOR (one per task)
  |           decomposes a task into steps, dispatches one worker per step,
  |           verifies each step before accepting it, reports upward
  |           |
  |           +-- Implementer ..... writes the code for one step
  |           +-- Tester ......... writes/runs the tests for one step
  |           +-- Documenter ..... README, usage, API surface, changelog
  |           +-- Researcher ..... (same role, dispatched where needed)
  |
  +-- QA / ASSURANCE ....... [v2] NOT a phase. runs THROUGHOUT. NOTE 5.
        every one of these is dispatched BY the layer that needs it,
        and is always FRESH — never the agent that did the work.
        |
        +-- Verifier ........ re-runs a claim against the committed tree.
        |                     the single highest-value role in the v2 run.
        +-- Auditor ......... adversarial sweep of one dimension
        +-- Reviewer ........ reviews a branch against what it claimed

===============================================================================
[+] THE ARTIFACT SIDE — WHAT SURVIVES WHEN AN AGENT DOES NOT
===============================================================================
The v0 chart draws only agents. Every agent above is thrown away; none of
the files below is. The run's single clearest lesson was that what survives
a handoff is a FILE, and what dies is a convention or a message. NOTE 6.

  CHARTER .......... what is being built, done-means, constraints,
                     [+] and the resources the CLIENT provisioned
  REQUIREMENTS ..... numbered, testable, each with an acceptance command
  BOARD ............ live state: claims, the writer lock, the dependency
                     graph, open questions   [? is this the Senior PM?]
  TASK FILES ....... one per task: goal, scope, gate, verify, steps,
                     and every worker report verbatim
  DECISIONS ........ every D-n, with what it retired and what it cost
  QUESTIONS ........ every Q-n with its CLASS — no class, no question
  RECORD ........... append-only. the cross-task picture nobody else sees
  ROTATION LOG ..... [+] what the liaison did, readable from outside it

  read by ........ every layer, at every startup, before acting
  written by ..... exactly one writer at a time, enforced by a lock
===============================================================================

NOTES — the reasoning, so v3 does not have to re-derive it

1. THE LIAISON MAY NOT NEED TO BE UNROTATABLE.
   "The buck stops somewhere" is true of RESPONSIBILITY. It does not follow
   for CONTEXT. If everything the liaison needs is in files — and the design
   says it is — then a liaison IS rotatable, and only THE THING THAT STARTS
   THE NEXT ONE cannot be. That could be a hook or a cron line, which has no
   context to degrade. Making the whole role unrotatable accepts a growing,
   compacting context in the highest-consequence layer, which is the failure
   the design set out to avoid, moved up one level.
   Measured, and it cuts the other way too: the pricelog PM ran a full build
   phase — 207 requests, 60.1M tokens — and never compacted once.

2. DOES THE SENIOR PM EARN A LAYER?
   Its stated job is scheduling the phases and routing. In v2 the BOARD does
   that: the dependency graph decides what is available, the writer lock
   decides who may act, and both are deterministic and re-readable. An agent
   that schedules is re-implementing in judgement what a file already does
   by construction — and it costs a brief in and a brief out at every hop.
   If it stays, it should be because it does something a file cannot.

3. THE SUPERVISOR TIER IS SPECIFIC TO WORK THAT HAS STEPS.
   In v2 a PM dispatches a planner, a verifier, an auditor or a researcher
   DIRECTLY. It dispatches a SUPERVISOR only for an implementation task,
   because that is the only work that decomposes into ordered steps with a
   gate between each. Putting a supervisor tier under Planning and QA adds a
   hop with nothing to do in it. Each hop is a brief, and a brief is where
   things get lost (NOTE 6).

4. THE INTERVIEW IS A ROLE, NOT A LAYER, AND IT IS THE TOP FAILURE POINT.
   Onboarding requires "pressing on ambiguity rather than accepting it" —
   a call about the SHAPE of an answer, not a lookup. A weak model that
   accepts a vague answer produces a charter that LOOKS SIGNED AND IS NOT,
   and every plan downstream inherits it.
   Measured in the pricelog run: the charter's budget row named a tool that
   could not measure it, and its protected-paths row locked the manager out
   of its own board. Both were interview-time defects and both propagated
   for days before anyone noticed.
   A cheap liaison DISPATCHING a strong interviewer is CHEAPER than a strong
   liaison: the interview happens once; a layer lives for the whole run.

5. QA IS NOT A PHASE. IT IS A LAYER THAT RUNS THROUGHOUT.
   If QA is a phase after implementation, verification lands where it is
   cheapest to skip and most expensive to act on.
   Measured, twice, in one run:
     - a task was reported DONE, a FRESH verifier broke its gate, and the
       task RE-OPENED. `fetch_price("BT C")` — a space in a coin name —
       crashed with a raw traceback, live, with no adversary.
     - a task with an adversarial step WRITTEN INTO ITS PLAN found a
       log-integrity defect before that task ever reported done.
   The rule that made both work: the verifier is always FRESH and never the
   party that did the work — including never the verifier whose earlier
   findings are being re-checked.

6. THE HANDOFF IS THE HARD PART, AND DEPTH IS ITS COST.
   Measured on the compiler side: across one week of rotations, a protocol
   handed over as A QUOTED VALUE PLUS A PROCEDURE survived three handoffs;
   a CONVENTION merely practised and a CORRECTION merely explained were both
   lost at the FIRST.
   Measured on pricelog, three more times: everything that survived two
   rotations was a file; all ten "record defect" lines were things that
   lived only in a message; and one supervisor's workaround, put in its
   step dispatches rather than a file, was not inherited by the next
   supervisor, which paid three recoveries in one task.
   v0 is SIX levels deep — client, liaison, senior PM, phase manager,
   supervisor, worker. That is FIVE briefs between the client and the code,
   and the measurement says a convention does not survive ONE.
   This is not an argument against depth. It is the price of depth, and it
   should be paid deliberately: every level you add is a brief you must
   template rather than write in prose.

7. [+] THE BUDGETER, AND WHY IT IS A ROLE RATHER THAN A FIELD.
   In the pricelog run, NOBODY READ THE BUDGET CEILING across two rotations
   and six closed tasks. It had been amended into two measurable units
   precisely so it COULD be read. The third manager was the first party to
   ask, and only because it asked before dispatching rather than after.
   Worse, the ceiling cannot see its own largest category: a verifier
   dispatched as an agent has no sandbox and writes no budget file, so it
   is in NEITHER half of the ceiling. One task ran six of them — 572,082
   tokens — counted nowhere.
   A stop that nobody reads is a stop that cannot fire, and it is carried
   as protection meanwhile. Give it an owner or delete it.

8. [+] COUNT SEAMS, NOT ONLY BOXES.
   "Complexity where required is fine" is right, and "count requirements per
   part, not parts" is a good measure. Pair it with a second: COUNT THE
   JOINTS THE SPLIT CREATES.
   The largest process finding of the pricelog run was a SEAM, not a part:
   the work discipline tells every worker to append its report to the task
   file; the task file is in no step's scope by the design's own
   construction. So every COMPLIANT worker breaks promotion — and the one
   worker that escaped did so by DISOBEYING. Neither rule is wrong. They
   meet on every step.
   A decomposition that gives every part one requirement and creates six new
   handoffs can be worse than what it replaced.

9. OPEN QUESTIONS THIS CHART CANNOT SETTLE.
   - Does the liaison's "four touchpoints" drop traffic that matters? In the
     pricelog run the client channel carried far more than four exchanges,
     and at least two changed a later decision. Either most of it was
     narration a liaison could drop, or some was load-bearing and a
     four-touchpoint liaison silently removes it. Countable in cycle 2:
     how many PM->client exchanges changed a subsequent decision?
   - Does the liaison enforce a CLEAN BOARD at rotation, or hand over live
     claims? Automating rotation does not remove that judgement, it MOVES
     it. Three handoffs in the run, all chose the clean board, and the
     successor said the third was the cheapest of the three.
   - Can "knows very little about the project" survive the escalation
     classification? Deciding "reversible AND inside charter" requires
     reading the charter. That is project knowledge.

===============================================================================
APPENDIX — v0, AS RECEIVED, PRESERVED VERBATIM
===============================================================================
Client (Answer interview questions, sign off on charter, inspect at checkpoints, choose to accept output or iterate)
|
Liason (Interface to system for user. Initiate/resume process, relay questions (such as interview) from system and answers from user, log important details at interaction layer, answer common questions about system (from documentation), mostly mechanical with little reasoning)
|
Senior Project Manager (Provide high level management and scheduling of lower layers and routing)
|___ Planning Manager (Manage the process of getting a plan/charter drafter, reviewed, and approved)
|   |___ Supervisors
|   |   |___ Workers
|   |   |   |___ Interviewer
|   |   |   |___ Researcher
|   |   |   |___ Budgeting
|   |   |   |___ Planner
|   |   |   |___ Plan Auditor
|   |   |   |___ ?
|   |   |
|   |   |___ ?
|   |
|   |___ ?
|
|___ Implementation Manager (Turn the plan into a working product)
|   |___ Supervisors
|   |   |___ Workers (Need a list of implementation worker skils) 
|   |   |   |___ ?
|   |   |   
|   |   |___ ?
|   |
|   |___ ?
|
|___ QA Manager (Test and audit the working product to make sure it meets requirements)       
|   |___ Supervisors
|   |   |___ Workers (Need alist of QA worker skills)
|   |   |   |___ ?
|   |   |
|   |   |___ ?
|   |
|   |___ ?
|
|___ ?
```
