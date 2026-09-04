# The design

How a client's idea becomes a working product, and what every piece of this
plugin is for. The rules it enforces are [`PROTOCOL.md`](PROTOCOL.md), cited
here by number and never restated (P-34). The idea this answers to is
[`docs/BRIEF.md`](docs/BRIEF.md); §12 records where the design departs from it
and why.

---

## 1. The shape of the thing

A real development organisation does four things this pipeline has to
reproduce, and one thing it must not.

It **pins the goal in writing before building** — a charter, signed, that
outsiders can read. It **decomposes** that goal into work small enough for one
person to hold. It **checks work it did not do**, because nobody reviews their
own commit. And it **escalates on a schedule**, batching decisions for whoever
owns them rather than interrupting constantly or guessing silently.

What it must not reproduce is the telephone game: a status report that is a
summary of a summary of a summary, where the failure three layers down arrives
at the top as "mostly on track." Every structural choice below is aimed at one
of those five things.

```
        CLIENT ──── charter, answers, sign-offs ────────────┐
          ▲                                                 │
          │ batched questions, each with a recommendation    ▼
          │ and a reversibility class (P-25, P-26)     PROJECT MANAGER
          │                                            main session
          └────────────────────────────────────────────  · owns charter, task
                                                          graph, board, record
                                                        · verifies every task
                                                          independently (P-18)
                                                        · writes no code (P-7)
                                                             │
                             ┌───────────────────────────────┼───────────────┐
                             ▼                               ▼               ▼
                      SUPERVISOR T-1                  SUPERVISOR T-2       ...
                      one agent per task              disjoint scope (P-12)
                      · decomposes into steps
                      · dispatches one worker per step
                      · verifies each step before accepting
                      · writes no code (P-8)
                             │
              ┌──────────────┼──────────────┬───────────────┐
              ▼              ▼              ▼               ▼
        implementer       tester        auditor         documenter
              │              │              │               │
              └──── REPORT blocks, passed upward VERBATIM (P-17) ────┘
```

**Why three layers and not two.** Two layers is the proven shape and it works;
the third is bought deliberately, to let several tasks run at once without the
manager holding every task's detail in one context. The cost of a third layer
is that reports can be paraphrased on the way up, so P-17 removes that: a
supervisor **appends every worker report unedited** and adds its verdict above
them. It may judge. It may not summarise. That single rule is what makes the
extra layer safe.

**Why the manager is the main session and not an agent.** Only the main session
can put a question to the client. That is a hard property of the harness, and
it decides the whole topology: the client-facing role must be the top of the
tree, which makes it the natural owner of the board, the record and the
escalation batch.

---

## 2. The roster

Nine agents, thirteen skills. Every agent preloads the skill that is its
procedure, so the procedure has one home (P-34) and the agent definition holds
only what a tool list can enforce.

### Agents

| Agent | Preloads | Restricted so it cannot | Model |
|---|---|---|---|
| `supervisor` | `supervise` | write product code — its scope is its task file's record and dispatch | inherit |
| `planner` | `plan`, `research` | write code; it produces tasks and steps | inherit |
| `implementer` | `work` | write outside its task's declared scope (P-10) | per class (P-40) |
| `tester` | `work`, `check` | write outside the test tree and its task scope | per class |
| `documenter` | `work` | write outside the documentation paths its task declares | `mechanical`/`standard` |
| `reviewer` | `review` | push, merge, or close — it comments and recommends | `standard` |
| `auditor` | `audit` | **write any file at all** — no `Write`, no `Edit` (P-31) | `deep` |
| `verifier` | `verify` | write anything; read-only plus a shell to re-run commands | `mechanical` |
| `researcher` | `research` | write any file — the requester files the digest (P-36) | `standard` |

The two genuinely enforced restrictions are the auditor's and the researcher's:
an agent definition's tool list actually removes the tool, so neither *can*
write, whatever it decides. Everything else in the table is discipline plus the
guard (§8). A skill's `allowed-tools` only pre-approves; it never restricts,
and pretending otherwise is how a system acquires a rule nobody enforces.

**There is no interviewer agent, deliberately.** The brief asks for one, but a
subagent cannot ask the client a question — only the main session can. So the
interview is the `onboard` **skill**, run by the manager in the main session,
dispatching researchers to inform its questions. §12 records this as a
departure.

### Skills

| Skill | Run by | For |
|---|---|---|
| `setup` | client, once | scaffold `devteam/` in a target project, negotiate permissions, print what to run next |
| `onboard` | manager | the interview → `CHARTER.md` → `REQUIREMENTS.md`, signed by the client |
| `plan` | manager, planner | the task graph: tasks, scopes, dependencies, gates, estimates |
| `run` | manager | the loop — pin, claim, dispatch, verify, record, escalate, checkpoint |
| `status` | manager | answer "where is it" from the board and record, at any time |
| `checkpoint` | manager | diff the built thing against the charter; file a verdict (P-30) |
| `supervise` | supervisor | one task: decompose, dispatch, verify each step, report |
| `work` | worker | the worker discipline: inputs, scope, commit form, REPORT block |
| `verify` | verifier | re-run the exact command against the committed tree (P-19) |
| `audit` | auditor | adversarial review in three dimensions; report, never fix |
| `review` | reviewer | pull requests: what to check and what to say |
| `research` | any | one dated, sourced digest from a primary source (P-36) |
| `check` | all | the mechanical scripts: traceability, references, reports, leaks |

---

## 3. What setup installs, and what each file is for

One visible root in the **target** project. The design record is committed,
because `git log devteam/CHARTER.md` is the history of how the product's
definition changed, and because a reviewer should meet it in a pull request.
Only genuinely ephemeral state hides.

```
devteam/
├── CHARTER.md            what we are building, for whom, what done means,
│                         what is out of scope, the constraints. Signed. P-1
├── REQUIREMENTS.md       R-n: statement · source · acceptance criterion ·
│                         priority · status. Testable or it is not a
│                         requirement. P-3
├── DECISIONS.md          D-n: choice · alternatives declined and why they
│                         lost · date · supersedes. Never rewritten. P-21,23
├── QUESTIONS.md          Q-n: question · recommendation · class · status.
│                         Answered ones struck with their D-n. P-24,25,26
├── BOARD.md              live state AND the lock. The manager owns it. P-11
├── RECORD.md             append-only event log. The durable output. P-42
├── PERMISSIONS.md        every permission, with why the loop needs it. P-38
├── tasks/
│   └── T-1.md            goal · requirements discharged · declared write
│                         scope · steps · gate · verification command ·
│                         execution record (REPORT blocks land here). P-16
├── checkpoints/
│   └── C-1-2026-09-03.md verdict: ON-COURSE | DRIFTED | BLOCKED. P-30
├── audits/
│   └── T-1-security-2026-09-03.md    filed by the manager; the auditor
│                                     cannot write it itself. P-31
├── research/
│   ├── CURRENCY.md       external dependency · pinned · checked · source ·
│   │                     decision. Stale at six months, ninety days if
│   │                     security-relevant. P-37
│   └── <topic>.md        dated digests, primary sources quoted. P-36
└── .run/                 GITIGNORED — nothing here is worth keeping
    ├── session/          which session holds the writer lock
    ├── locks/            in-flight claim markers
    ├── env/              the pinned toolchain: versions, lockfile hashes,
    │                     image digests. P-33
    └── scratch/          agent working files
```

**The split is the point.** Everything above `.run/` is evidence: it is
reviewable, diffable, and survives the session that produced it. Everything
inside `.run/` is a detail of one run and is regenerated. A file that cannot
decide which it is belongs in the tracked half — the cost of keeping something
is a few kilobytes, and the cost of losing the reason a decision was made is a
week.

---

## 4. The lifecycle, and the five times the client is needed

The brief asks for the loop to run with as little client input as possible
outside initial planning, planned checkpoints and final review. That is exactly
five gates, and everything else is designed to not need a sixth.

```
  ┌── 0 INSTALL ────────────────────────────────────────────────────────────┐
  │  /devteam:setup                                                          │
  │  scaffolds devteam/, negotiates the permission set (P-38), prints the     │
  │  one line to run next. No agents, no cost, nothing irreversible.          │
  └──────────────────────────────────────────────────────────────────────────┘
                                     │
  ┌── 1 ONBOARD ─────────────────────┼───────────────────────────── GATE 1 ──┐
  │  /devteam:onboard                                                        │
  │  The manager interviews the client — adversarially, per §5 — dispatching  │
  │  researchers to turn "what do you think about X" into "the standard says  │
  │  X, dated; do you want it". Produces CHARTER.md and REQUIREMENTS.md.      │
  │  ► THE CLIENT SIGNS THE CHARTER. Nothing proceeds without it.             │
  └──────────────────────────────────────────────────────────────────────────┘
                                     │
  ┌── 2 PLAN ────────────────────────┼───────────────────────────── GATE 2 ──┐
  │  /devteam:plan                                                           │
  │  Requirements become a task graph: each task's goal, the R-n it           │
  │  discharges, its declared write scope, its dependencies, its gate, its    │
  │  estimate. check_trace must be clean — every requirement covered, every   │
  │  task motivated — before the graph is shown.                             │
  │  ► THE CLIENT APPROVES THE PLAN, the width, and the model band.           │
  └──────────────────────────────────────────────────────────────────────────┘
                                     │
  ┌── 3 BUILD ───────────────────────┼──────────────────── GATES 3 (as due) ─┐
  │  /devteam:run [width=N]                                                  │
  │  The loop, §5. Runs unattended. Stops for exactly three things: an        │
  │  IRREVERSIBLE question, a CHARTER question, or a DRIFTED checkpoint.      │
  │  Reversible questions proceed on their recommendation and are listed for  │
  │  review at the next checkpoint (P-27).                                    │
  │  ► CHECKPOINTS ARE SCHEDULED, and only a DRIFTED one demands an answer.   │
  └──────────────────────────────────────────────────────────────────────────┘
                                     │
  ┌── 4 HARDEN ──────────────────────┼───────────────────────────────────────┐
  │  Three audits in parallel — correctness, security, hygiene — each         │
  │  reporting without fixing (P-31). Findings triaged by workers under the   │
  │  ordinary discipline. Currency rows re-checked (P-37). Then re-verified.  │
  └──────────────────────────────────────────────────────────────────────────┘
                                     │
  ┌── 5 DELIVER ─────────────────────┼───────────────────────────── GATE 4 ──┐
  │  Documentation brought current, the reviewer's pass, the final            │
  │  checkpoint: every R-n discharged with its evidence, every unreviewed     │
  │  decision listed, the whole budget against estimate.                      │
  │  ► THE CLIENT ACCEPTS, or sends findings back as new requirements.        │
  └──────────────────────────────────────────────────────────────────────────┘
```

The fifth gate is unscheduled and always available: **an IRREVERSIBLE or
CHARTER question, at any moment** (P-26). Those never wait for a checkpoint and
never auto-proceed.

**And the lifecycle is a loop, not a line.** At gate 4 the client accepts,
amends, or **iterates** — `/devteam:iterate` reopens at stage 1 with the
charter, decisions, record and audits carried forward, re-interviewing only
what using the thing actually taught. The second cycle is cheaper than the
first exactly to the extent that the first one's reasoning is still on disk,
which is why iterating must never mean starting from an empty directory.
Requirements keep their numbers and are superseded rather than edited; the
charter gains a version and keeps its old text; and the `proceeded-unreviewed`
decisions are the first thing the client is shown, because this is the moment
they were promised a look at them (P-27).

---

## 5. The two loops

### The manager's loop — `/devteam:run`

1. **Startup.** Read `BOARD.md`. Take or confirm the writer lock, recording the
   session id in the board header and `.run/session/`. Run recovery (P-14) over
   every `CLAIMED` row. If no environment is pinned, pin it (P-33) — **never**
   while a claim is in flight. Then tell the client the picture in under ten
   lines: width, pin, each task's state, anything recovered, anything waiting.
2. **Pick.** The next task whose dependencies are all `DONE` on the board — not
   `CLAIMED`, *done* — and whose declared write scope is disjoint from every
   live claim (P-12). None available → the loop idles and says why.
3. **Claim.** A board row plus an in-flight row naming the task, the agent
   label `T<n>-<slug>-<HHMM>`, the time and the model. One commit:
   `board: claim T-n`.
4. **Dispatch** the supervisor with §6's template. It runs in the background;
   the manager is woken when it reports.
5. **On a report.** Run `check_report.py` first — a malformed report is a
   re-dispatch, not a judgement call. Then dispatch a **fresh verifier** (P-18)
   with the task, the pin and the report's `checks:` lines. Nothing moves on
   the board before `PASS`.
6. **Advance or release.** `PASS` closes the task, releases its scope, and
   checks whether any blocked task just became free. `FAIL` re-dispatches with
   the failure verbatim in `NOTES:`.
7. **Checkpoint** if one is due (§10).
8. **Escalate** per §9 if the batch conditions hold.
9. **Record** one line per event (P-42), committed with the board change.
10. Repeat. When nothing runs and nothing can be dispatched, send the batch and
    end the turn.

### The supervisor's loop — one task

1. **Read** the task file, the charter, the `R-n` it discharges, and
   `DECISIONS.md` — the last one **before proposing anything**, because it is
   recorded why the obvious alternative lost.
2. **Decompose** into steps if the task file does not already carry them. Each
   step gets a goal, a complexity class (P-40) and a verification command.
3. **Per step:** pick the model within the charter band; dispatch one worker;
   receive its `REPORT`; **verify it** by running the step's verification
   command against the committed tree. Accept, or re-dispatch **once** with the
   failure in `NOTES:`, or escalate. A second failure is always an escalation,
   never a third attempt (P-20).
4. **Compose** the task report: the supervisor's own verdict, then **every
   worker report appended verbatim** (P-17).
5. **Return.** The supervisor writes nothing under `devteam/` except its own
   task file's execution record (P-13).

**What a supervisor escalates rather than deciding:** anything the charter,
requirements and decisions do not settle; a step that failed twice; a
dependency that turned out to be missing; a scope it needs that it was not
given; any question whose class is `IRREVERSIBLE` or `CHARTER`. It resolves
what it can from the documents and from research, and it guesses at nothing.

---

## 6. The contracts

Three fixed shapes. Everything crossing a layer boundary uses one of them, so
that a script can check it (P-35) and a reader can diff two of them.

### Dispatch: manager → supervisor

```
TASK: T-n
TITLE: <the task's one-line goal>
REPO: <absolute path of the project root>
SCOPE: <absolute paths this task may write, one per line>
REQUIREMENTS: R-3, R-7          the requirements this task discharges
GATE: <what must be true to call this task done>
VERIFY: <the exact command that proves it>
ENV: <pin id>  <the pinned versions, verbatim>
MODEL-BAND: <floor> .. <ceiling>
ATTRIBUTION: <commit trailer lines, verbatim>
TREE: clean | dirty
AUDIT: none | <absolute path of an audit report to triage>
DIGESTS: none | <absolute paths of research digests to cite>
NOTES: none | <a verifier FAIL, a predecessor's death, a client's answer>
```

### Dispatch: supervisor → worker

The same, minus `MODEL-BAND` and plus `STEP:`, `ROLE:` and `STEP-VERIFY:`. A
worker is told one step and the command that will judge it — never the whole
task, because a worker that can see the whole task will start optimising it.

### The REPORT block

The final message of every worker and every supervisor, and the last entry of
the task file's execution record (P-16). **Parsed by a script — keys start at
column one, continuations are indented, nothing is decorated.**

```
REPORT <role> <T-n>[.<S-n>]
status: DONE | BLOCKED | NEEDS-DECISION | RED | READY-TO-AUDIT
model: <the model id the system prompt names>
env: <pin id>
requirements: none | R-3, R-7
scope: <paths actually written>
commits:
  - <hash> <subject>
checks:
  - <exact command> -> <its summary line, verbatim> [exit <n>]
questions: none | - <question> | <recommendation> | REVERSIBLE|IRREVERSIBLE|CHARTER
findings-for-protocol: none | - <one line each>
budget: tokens=<n> minutes=<n>
notes: none | <free text>
```

A supervisor's block adds `verdict:` per step, and then, below everything:

```
--- WORKER REPORTS (verbatim, P-17) ---
<every worker REPORT block, unedited, in dispatch order>
```

**`status:` values are not interchangeable.** `BLOCKED` means an input was
missing or wrong and the manager can fix it. `NEEDS-DECISION` means a question
must be answered. `RED` means a check failed — and per P-20 that is reported,
never retried. `READY-TO-AUDIT` means the work is done but has not yet been
audited, and it is the only status that does not close a task.

---

## 7. The checks

Four scripts, each with a negative control beside it (P-35). They are the
mechanical half of the discipline — the half that does not depend on anyone
being careful.

| Script | Diffs | Findings |
|---|---|---|
| `check_trace.py` | charter ↔ requirements ↔ tasks ↔ acceptance checks | `orphan-scope`, `uncovered-requirement`, `unmotivated-task`, `unverified-requirement` |
| `check_refs.py` | citations ↔ declarations, and links ↔ files | `broken-link`, `cited-undefined`, `defined-uncited`, `duplicate-id`, `dangling-question`, `leak` |
| `check_report.py` | a committed REPORT block ↔ the tree it claims | `no-report`, `wrong-task`, `missing-field`, `bad-report-status`, `status-mismatch`, `unknown-commit`, `head-subject`, `dirty-tree`, `no-evidence` |
| `check_scope.py` | a task's declared scope ↔ every other live claim, and ↔ what it actually wrote | `overlapping-scope`, `undeclared-write`, `empty-scope`, `scope-escapes-tree` |

**`defined-uncited` and `unmotivated-task` are the ones that earn their keep.**
A decision nothing cites is usually a requirement that states a rule and forgot
to attribute it; a task discharging no requirement is either scope creep or a
requirement nobody wrote down. Both are invisible to a reader and obvious to a
diff.

**`leak` runs before anything is pushed.** Absolute home paths, tokens, keys.
These projects may be public and the check costs milliseconds.

**Scope checking lives in one script.** An earlier draft of this table put
`scope-violation` in `check_report.py` and `undeclared-write` in
`check_scope.py` — two names for one question, in two places, which is exactly
what P-34 forbids. `check_scope.py` owns everything about scopes: whether two
live tasks overlap, and whether a task's commits stayed inside what it
declared. `check_report.py` owns the block's own consistency with the tree.

**A task is live when its own title line says `RUNNING`** — the same source
stale-claim recovery reads (P-14), rather than a second parse of the board's
table, which could disagree with it.

**One fault produces one finding.** Both `check_report` and `check_scope`
suppress the consequences of a fault they have already reported: an invalid
status is not also compared against the title, and a scope emptied by
rejecting its entries is not also reported as empty. Cascading findings bury
the cause under its own consequences and make a report harder to triage than
the defect that caused it.

Every script exits `0` clean, `1` findings, `2` could not run, and reads
**git-tracked files only**, so scratch work is never a finding.

---

## 8. The guard

A `PreToolUse` hook on `Bash`, `Write`, `Edit` and `NotebookEdit` — one script,
covering both the file tools and the shell, because a guard that covers one and
not the other has a hole exactly where somebody will walk.

1. **Protected paths are read-only.** The charter declares them: vendored
   dependencies, generated trees, sibling repositories, production config.
   Reading, grepping and listing them is always fine.
2. **A write must land inside the declared scope of a live claim** (P-10,
   P-12), unless the session was started inside the target itself.
3. **`devteam/` is written only by the session the board names**, with
   `BOARD.md` itself exempt — it *is* the lock, and a lock nobody can take is a
   deadlock.

Three properties it must have, each learned the expensive way in the prior art:

- **A write is judged by its target, never by what the command text mentions.**
  The first version of the guard this is drawn from refused a heredoc because
  the *body* of the document being written mentioned a protected path.
- **It scopes on the session's project directory, not the shell's working
  directory**, because the latter follows `cd` — and a `cd` into a protected
  tree, which is a read and allowed, would otherwise disarm it for the next
  call.
- **More than a third of its control cases are false-positive controls**
  (P-35). A guard that blocks legitimate work gets switched off by whoever it
  obstructs, and a guard that is off is worse than one that never existed.

**Its limits, stated rather than hidden:** an interpreter heredoc that writes
(`python3 - <<PY`) cannot be classified from the command text, and a target
containing an unexpanded variable cannot be resolved and is not judged. The
airtight mechanism for the first is the sandbox's own write-deny list, and the
guard is a second layer, not the only one.

---

## 9. Escalation and autonomy

The question this pipeline has to answer is: **how does it keep going for hours
without either guessing at something that matters or waking the client every
twenty minutes?** The answer is that not all questions are the same question.

Every escalation carries a recommendation, its evidence, and a class (P-26).
The class alone decides what happens:

```
        question raised by a worker
                  │
                  ▼
      can the supervisor answer it from
      the charter, the requirements, the
      decisions, or one research fetch?
          │                    │
        yes → answered      no → escalate to the manager
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
              IRREVERSIBLE       CHARTER       REVERSIBLE
              spends money,      changes       library choice,
              deletes data,      what is       layout, naming,
              publishes,         being         framework
              picks a licence    built
                     │              │              │
                     ▼              ▼              ▼
                  BLOCKS         BLOCKS      goes on the table
                  always         always      with its recommendation
                     │              │              │
                     └──────┬───────┘              ▼
                            ▼               window expires?
                   batched to the client     │         │
                   (all stopped · three     no        yes
                    waiting · window)        │         │
                                        still waits    ▼
                                              proceed on the recommendation,
                                              record `proceeded unreviewed`,
                                              list it at the next checkpoint
```

**Why this is safe.** The irreversible set is defined by consequence, not by
importance: anything that spends money, destroys data, reaches outside the
machine, or cannot be undone by a later commit. Getting a reversible call wrong
costs one commit to undo. Getting an irreversible one wrong can cost real
money or a published mistake, so no timeout ever decides one.

**Why it is honest.** The record distinguishes `question answered` from
`proceeded unreviewed`, the decision entry says the client never saw it, and
every checkpoint lists the unreviewed set explicitly. The client always knows
the size of what was decided on their behalf.

---

## 10. Checkpoints

A checkpoint is the answer to the brief's requirement that things not diverge
from the design and that the design still meets the project's goals. It is a
**verdict with evidence**, not a status update, and it is scheduled — after
every *n* closed tasks, at every milestone, and on demand.

It answers five questions, in this order:

1. **Does what exists satisfy the charter?** Every charter goal → its `R-n` →
   the tasks that discharged them → the acceptance evidence actually recorded.
   A goal that cannot be walked down that chain is the finding.
2. **What diverged, and was it decided?** Divergence recorded as a decision is
   normal. Divergence nobody recorded is the thing checkpoints exist to catch.
3. **What proceeded unreviewed?** Every `REVERSIBLE` question the loop decided
   on the client's behalf, listed, each still cheap to reverse (P-27).
4. **Is the plan still right?** Requirements that turned out wrong, tasks that
   turned out mis-sized, estimates against measured cost (P-41).
5. **Verdict.** `ON-COURSE` — recorded, loop continues, client not
   interrupted. `DRIFTED` — **goes to the client**, with what drifted and a
   recommendation. `BLOCKED` — goes to the client with what is needed.

Filed in `devteam/checkpoints/`, committed, and never edited afterwards: a
checkpoint that could be revised in the light of later events is not evidence
of anything.

---

## 11. Models and budget

The charter names a floor and a ceiling. Every step declares a class, and the
supervisor picks inside the band:

| Class | Work | Why |
|---|---|---|
| `mechanical` | verification, link and format checks, mechanical edits | every judgement is a command with an exit code; a larger model adds cost and no accuracy |
| `standard` | implementation, tests, documentation, review | the bulk of the work |
| `deep` | interview, planning, audit, architecture, anything ambiguous | mistakes here are expensive and propagate into everything downstream |

The report records what actually ran (P-40), because two results produced on
different models are not comparable. Tokens and wall-clock go in every report
(P-41), the manager compares them to the estimate at each checkpoint, and a
task that cost triple its estimate is a finding about the plan, not just a
number.

---

## 12. Where this departs from the brief

Four departures, each deliberate, recorded here so the brief and the design can
be diffed rather than silently reconciled (P-2 applied to the pipeline itself).

| Brief | Design | Why |
|---|---|---|
| a `.claude-skills/` directory, hidden | `devteam/` tracked, `devteam/.run/` ignored | the design record is worth reviewing in a pull request, and `git log CHARTER.md` is the history of how the product's definition changed. Only ephemera hides |
| an **Interviewer worker** among the worker types | the `onboard` **skill**, run by the manager in the main session | a subagent cannot ask the client a question — only the main session can. The role survives; its home moved |
| escalations go up and wait | escalations are **classified by reversibility**, and reversible ones proceed on their recommendation after a window | the brief asks for minimal client input *and* for no guessing. Classification is how both are true at once |
| one repository of skills | the repository is a **marketplace**; this is the first plugin in it | the brief anticipates other workflows later; a marketplace is the shape that accepts them without rearranging this one |

The brief's three-layer structure, its worker taxonomy, its
supervisor-verifies-workers rule, its escalation chain and its
permissions-up-front requirement are all adopted as written.

---

## 13. What this is deliberately not

- **Not an autonomous system.** It stops for decisions and for anything
  irreversible, on purpose, because those are the two places where guessing is
  expensive. It is a loop that runs unattended, which is a different claim.
- **Not a replacement for reading the diff.** It produces evidence a human can
  check quickly. It does not remove the human from the end of the process, and
  the final gate exists for exactly that reason.
- **Not a home for project content.** The skills carry procedure and pointers
  only (P-34). Every fact about the product being built lives in that product's
  `devteam/`, never in this plugin.
- **Not language- or stack-specific.** Everything the pipeline needs from a
  project — how it builds, how it tests, what is protected, what "done" means —
  is asked for in the interview and written into the charter, rather than
  assumed here.

---

## 14. Build order

The walking skeleton first, because this pipeline's own advice is that the
riskiest unknown goes earliest and a probe that fails changes the design.

| Phase | What | Done when |
|---|---|---|
| **0** | this document and `PROTOCOL.md` | ✅ **done** |
| **1** | marketplace, plugin manifest, repository housekeeping | ✅ **done** — the plugin loads and its manifests resolve |
| **2** | `setup`, the checks with their controls, the guard with its control | ✅ **done** — 127 control cases green, 57% of them false-positive controls; a freshly scaffolded project checks clean |
| **3** | one path end to end: `onboard` → `plan` → one task → `supervise` → `implementer` → `verify` → `checkpoint` | ✅ **done** — walked in §15, and the walking is what found the six defects |
| **4** | rehearse on a throwaway project; fix what the rehearsal breaks | ✅ **done** — three tasks, a killed supervisor recovered, a correct verifier FAIL, a live guard refusal, and a DRIFTED checkpoint; §15–§17 |
| **5** | remaining roles: three audit dimensions, tester, documenter, reviewer | ✅ **done** — three auditors dispatched in parallel against the rehearsal project, none able to write; §18 |
| **6** | a client the pipeline did not write: another session, briefed only with an underspecified paragraph, interviewed and run end to end | ◐ **in flight** — eighteen findings before the product had a line of code; §20 |

Phase 3 is the one that matters. Everything before it is scaffolding, and
everything after it is filling in a loop already known to work.

**The plugin checks itself.** `scripts/check_plugin.py` diffs what the plugin
references against what it contains — an agent preloading a skill that does
not exist, a rule cited that `PROTOCOL.md` does not declare, a script named in
a hook that is not there, a check with no negative control beside it. It is
the same discipline this pipeline imposes on the projects it runs, pointed at
itself, and it caught its own self-exemption: it had excluded itself from its
own `uncontrolled-check` scan.


---

## 15. What the first real dispatch found

One task — a word counter with five tests — dispatched to a live supervisor
which dispatched two workers. The work came back green, correct and honestly
reported. **Eleven defects surfaced from the first task alone, and every one of them
was in this design rather than in the agents' work.** A second task, run after
they were fixed, found seven more (§16). They are recorded here because the pattern
matters more than the list: each was invisible on paper and obvious within
one real run.

1. **Commit attribution charged the manager's commits to the task.**
   `check_scope` matched `git log --grep T-1`, which also matched the
   manager's own `board: claim T-1` and `plan: T-1 and T-2`. A supervisor
   could therefore never close a task cleanly, through no fault of its own.
   Attribution is now by **subject prefix** — the commit form the `work`
   skill already mandates.

2. **A report cannot contain the hash of the commit it is committed in.**
   P-16 puts the block in the same commit as the work, so the content would
   have to hash to a value written inside the content. Both workers hit this
   and **refused to invent a placeholder**, which was the right call. The
   form is now `- HEAD <subject>`: `HEAD` marks this commit, and the subject
   is what resolves it afterwards.

3. **P-16, P-17 and the record check could not all hold for a supervisor.**
   Committing the final message whole would leave a *worker's* block last in
   the file, so the check validated a worker's step report instead of the
   supervisor's. A supervisor now commits its own block alone; the workers'
   blocks already stand above it, and the *message* carries them appended.

4. **The supervisor had no `git add` or `git commit`**, while §6 required it
   to close with a clean tree and a title line only it writes.

5. **A tests-first step was not runnable as planned.** Its verification was
   `pytest --collect-only`, which cannot pass while the module the tests
   import does not exist. The supervisor widened the step's scope to include
   a stub — work the plan should have done, now in the `plan` skill.

6. **The estimate was 26x low.** 8,000 tokens estimated against ~210,000
   actual, because it counted the code to be written. Almost none of the cost
   is typing; it is reading, verifying and reporting.

**The verifier caught what the supervisor's own check missed, and said so.**
The supervisor ran `check_scope` and `check_refs` before closing and both were
clean, so it reported `DONE` in good faith. An independent verifier, dispatched
by the manager with no stake in the work, ran `check_report` as well — the one
check the supervisor had not run on itself — and returned **FAIL** on a real
defect: its `commits:` entry for the closing commit was an explanatory
parenthetical rather than a resolvable subject.

This is the whole design working. Reported green was not green (P-18); the
party that had spent eighteen minutes on the task was not the party that
caught the problem; and the verifier, having no `Write` tool at all, could not
have quietly fixed it even had it wanted to. **A `FAIL` that is correct is the
most valuable output this system produces**, and it cost three minutes.

**A seventh finding, from that same run: "byte for byte" was literally
false.** P-19 told the verifier to compare output byte for byte, which is
right in spirit and wrong for any command whose output embeds a duration —
`5 passed in 0.14s` against `5 passed in 0.12s`. Taken literally it fails
every passing task. The verifier handled it correctly anyway, but only because
it was told to; the skill now distinguishes **claims** (counts, pass/fail
words, exit codes — must agree exactly) from **measurements** (durations,
timestamps, seeds, temporary paths — vary by design). A false FAIL costs
exactly as much as a false PASS, because both teach people to stop believing
the verifier.

**Three findings about the guard, from installing it and then trying to walk
through it.** These are the worst of the eleven, because for the whole first
dispatch the guard was believed to be protecting the work and was not.

**Ninth: the guard derived the project from the session, not the target.** Its
own docstring says a write is judged by its target — and then `find_project()`
walked up from `CLAUDE_PROJECT_DIR`, so a write into any project the session
was not inside went unjudged. That is *every subagent*, which inherits the
parent's project directory. The rule was right and was broken one level above
where it was written down. The project is now discovered from the target path.

**Tenth: the writer lock used a substring test.** `session in writer` matched
a short session id inside an ordinary word — `me` inside `names` — and handed
the lock to a session that never held it. It is now an exact token match.

**Eleventh — and this one is a finding about how the guard is tested, not
about the guard.** Four consecutive live attempts to walk through it appeared
to succeed, and were reported as "the hook is not firing". They were invalid
tests. Every one wrote to `$R/devteam/RECORD.md` — a shell variable — and the
guard's own docstring states that **a target containing an unexpanded variable
cannot be resolved and is not judged.** It declined to judge, exactly as
documented. Repeating the attempt with a literal absolute path was refused
immediately, as was the same write through the `Write` tool.

This is worth more than an ordinary bug, because it is a trap the guard sets
for anyone who tests it the obvious way. A shell variable in the path is the
natural way to write a test, it produces a silent pass, and a silent pass
reads as a broken guard. **A live guard test must use a literal absolute
path**, and that is now what the `setup` skill requires.

It also produced a false claim that was committed before it was checked: that
a plugin symlinked into `~/.claude/skills/` does not load its
`hooks/hooks.json`. **That remains unproven.** The guard was registered in
`settings.json` at the same time, so the two cannot be told apart from here,
and the prior art's identical duplication is not evidence either way. It is
recorded as unknown rather than quietly dropped, and the honest test is to
remove the `settings.json` entry at some future restart and see whether a
literal-path write is still refused.

**The lesson underneath all of it is one error, made twice, and it is the
error this whole pipeline exists to prevent.** First: thirty-two control cases
proved the guard *script* behaved correctly, and not one proved the guard was
*running* — the artifact was verified and the deployment was reported. Then,
correcting that, a broken test was trusted over a working mechanism and a
conclusion was published from four runs of it. Both are "reported green is not
green" (P-18), committed by the author of P-18, against his own guard, while
building a system whose central claim is that nobody may verify their own
work. The `setup` skill now separates registering the guard from proving it
fires, says a green control is evidence of neither, and requires one
deliberately refused write **with a literal path** as the only proof.

**A twelfth finding, about watching rather than running.** A supervisor is
blocked for the entire time its worker runs, so it emits nothing — no tokens,
no output, no progress. From outside, a supervisor doing its job is
indistinguishable from a hung one, and during the first dispatch that read as
a stall for six minutes before the child's transcript proved otherwise. This
is inherent to a three-layer design and cannot be removed, so it is made
visible instead: a supervisor writes `waiting on S-n` into its task's
execution record *before* it dispatches. That line is what separates blocked
from dead, for a human watching and for the recovery procedure alike (P-14).

**What did not go wrong is worth as much.** The tests-first ordering survived
— the worker wrote five genuinely failing tests before any implementation,
rather than tests shaped around code it had already written. Both workers
reported red honestly at the step where red was correct. The supervisor
verified each step, accepted each after one attempt, passed both worker
reports upward verbatim, raised two well-formed reversible questions with
recommendations, and **reported four of the six defects above itself** rather
than working around them silently. That is the behaviour the whole protocol
is trying to buy.


---

## 16. What the second dispatch found

T-2 ran after every fix above, with the guard live and a real
`devteam:supervisor`. It closed `DONE` with `check_report` clean — which was
the point: the corrected report format works. Three steps, four workers, one
step rejected and re-run, seven further findings.

**The rejection is the most interesting thing in this project so far.** The
supervisor refused step S-0 not because the artifact was wrong — it was
correct at both attempts — but because **its verification command could not
have failed.** The planned command printed identically against a tree exported
from before the change. Its own first replacement was vacuous too, because
`pytest` reports `configfile: pyproject.toml` whether or not the table being
checked for exists. Only the third command discriminated, and the worker then
demonstrated it three independent ways, including running the same command
unmodified against a `git archive HEAD~1` export in a separate directory.

This is a class of defect nothing in the design had named: **a green light
wired to nothing**. A command that cannot fail converts "we did not check"
into "we checked and it was fine", which is strictly worse than an admitted
gap. Both the `plan` and `supervise` skills now require a verify command to be
shown capable of failing, and rejecting a step for a vacuous instrument is
stated as a legitimate FAIL even when the work is perfect.

The other six:

1. **The heartbeat added two commits earlier contradicted the verifier.** A
   heartbeat in the task file dirties the tree; a verifier requires a clean
   one. A supervisor blocked for fourteen minutes on a verifier had no
   sanctioned way to show it was alive. The heartbeat now goes in untracked
   `.run/locks/`.
2. **`check_report` on a mid-flight task fell back to a step's block** and
   compared its `DONE` to the task's `RUNNING` title — a spurious
   `status-mismatch` on every step verification, since a finished step sits
   under a running task by definition.
3. **Neither check accepted a dotted id**, so a verifier judging one step had
   no script-level check aimed at it. Both now take `T-n.S-m`.
4. **An agent cannot propose a new requirement by number.** `R-3` written
   inside a recommendation *arguing one should exist* is read as a citation,
   and fails as `cited-undefined`. The system punished an agent for
   recommending exactly the thing it should recommend. Proposals now describe
   the requirement; the manager allocates the number on accepting it.
5. **`python3 -m` prepends the invoking cwd** to the child's path, so a
   subprocess test that does not pin `cwd=` can pass by shadowing the import
   defect it exists to catch.
6. **A relative ref in a `checks:` line is not stable** — `HEAD~1` names
   something else once another commit lands.

**And a real defect in the product, found and correctly not fixed.** Charter
goal G-2 says the tool fails with a clear message rather than a traceback;
requirement R-2 covers only a missing path. A file of invalid UTF-8 still
prints a full `UnicodeDecodeError` traceback. The supervisor reproduced it,
the verifier reproduced it independently, and **it was left unfixed** — R-2
does not ask for it, and `REQUIREMENTS.md` is manager-owned. It came up the
chain as a recommendation instead.

That is the traceability check's real limit, worth stating plainly:
`check_trace` proves every goal has *a* requirement, never that its
requirements *cover* it. A goal can be fully traced and still half-built, and
no script will say so. Only reading the goal against the work does — which is
what a checkpoint is for.

**The estimate missed again, by 7x** — 90,000 tokens against roughly 625,000,
after already being raised 13x from T-1's measurement. Most of it went to one
`mechanical` step, because proving an instrument discriminates costs more than
writing the thing it measures.


---

## 17. What killing a supervisor found

The last untested mechanic. A supervisor was dispatched on T-3 and killed
mid-flight, deliberately, to exercise stale-claim recovery (P-14). The claim
was detected stale, classified `RUNNING` + dirty, re-dispatched with the
predecessor's state explained, and the task closed `DONE`.

**The recovery worked because the dead supervisor's work was uncommitted.**
That is not luck — the `work` skill forbids committing a title line on its own,
on the grounds that *if you die before the real commit, the uncommitted line is
exactly what the next worker needs to see.* It was written as an assertion and
is now a demonstration. What the predecessor left was worth more than a title
line: it had found S-1's planned verify vacuous, proved it against an export of
the pre-change tree, and written a replacement. Its successor re-proved that
finding rather than inheriting it, and kept the amendment.

**And the new discriminating-verify rule was applied unprompted, twice**, by
agents that had only the skill text to go on — including by the supervisor
that was then killed for its trouble.

Six more findings, five of them mine:

1. **`git add -A` in the worker's commit form is actively wrong.** The manager
   owns `devteam/` and may have an uncommitted file at any moment; `-A` sweeps
   it into a worker's commit, where it becomes an undeclared write against the
   task. A supervisor overrode this on all three of its dispatches before it
   was fixed. Workers now stage explicit paths.
2. **`dirty-tree` measured the whole tree**, so one uncommitted manager-owned
   file made a clean close unreachable from inside a task. A check nobody can
   satisfy is a check that gets ignored (P-35). It is now scoped to the task's
   declared paths.
3. **And fixing that exposed a bug the original had masked.** The `git()`
   helper stripped its output, which eats the leading space of
   `git status --porcelain`'s two-character code and shifts every path by one.
   The old check only counted lines, so it never noticed; scoping it to paths
   made it matter in the first run.
4. **A check that can only run after the commit cannot appear in the report
   inside it.** `check_scope` reads the committed diff. Same shape as the
   commit-hash problem, and now stated for both.
5. **Amending a commit orphans any hash already cited in a report.**
6. **Telling a worker to keep `/home/...` out of its report produced an
   invented path.** The instruction now names the form to use —
   `${CLAUDE_PLUGIN_ROOT}/scripts/...` — which is runnable and leak-free.

**The finding worth keeping is the one about instruments.** Building a gate
check, a supervisor wrote invalid bytes with `printf '\xff\xfe'` under `sh`,
which does not expand `\x`. The file came out as valid text, the tool
correctly succeeded, and the check reported a pass. **A negative test proves
nothing if its bad input is not actually bad** — and this was caught only
because the check was phrased to *report what it saw* rather than to assert a
result. That habit is now in both skills, alongside the rule that a verify must
be able to fail. Three tasks in, this project's characteristic defect is not
wrong code. It is instruments that cannot detect what they were built to
detect.

**Twice now a step has been rejected for bad evidence behind correct work.**
T-2's S-0 had a vacuous verify; T-3's S-1 misread a diff hunk header as a
count of added lines. Both artifacts were right; both reports were wrong; both
were caught by a verifier and re-run. That ratio — evidence failing more often
than work — is the clearest sign the gate is pointed at the right thing.


---

## 18. What three parallel audits found

Correctness, security and hygiene, dispatched together against the rehearsal
project — the first exercise of P-15 as corrected, and it held: three agents
that cannot write cannot collide. **All three wrote nothing**, which the
harness enforced rather than the prose.

Each obeyed its dimension's discipline. The hygiene auditor was told its
findings are the highest volume and lowest severity and led with *"the three
that actually matter"*. The security auditor was told to state its threat
model and did, then labelled two findings as needing a different model and
declined to inflate them. That is the difference between an audit and a list.

**The single most valuable finding is a vulnerability the project had already
documented without noticing.** `python -m` puts the current directory at the
front of `sys.path`, so the prescribed invocation executes a `wordfreq/`
package found in the cwd — an unpacked tarball, a cloned repo, a shared
scratch directory. `tests/test_cli.py` **explains this mechanism in its own
comments**, defends the test suite against it with `cwd=tmp_path`, treats it
as test hygiene, and ships the undefended invocation to the user. One file
stated the mechanism; no file stated the consequence.

That is a class worth naming: **a hazard recorded as an implementation detail
by the one worker who understood it.** No check finds it, because nothing is
missing — the knowledge is present, in prose, in the wrong register.

**And an audit found the audit tooling failing at its own job.** `check_refs`
reported a tree clean while four committed lines carried an absolute session
path — the home directory survived path-encoding as
`-home-<user>-<segments>`, which no `/home/` pattern can see. A check passing
on the exact condition it exists to detect. Fixed with two patterns and four
controls; it now reports all four.

**The characteristic defect reached five instances.** C-1 counted three and
said so; the audits found a fourth in the charter (`make lint` is
`compileall`, green on code that cannot run) and a fifth in the tests
(`"Traceback" not in stderr` passes on Python's `BrokenPipeError` spew, which
does not contain that word). The count in C-1 is wrong, and it is filed and
never edited (P-30), so the correction belongs in the next checkpoint.

Three fixes landed in the plugin, each from a finding an auditor raised about
the tooling rather than the project:

1. **`head-subject` checked HEAD**, so every finished task reported it the
   moment any later task committed. An audit run afterwards saw a false
   positive against every historical task. It now looks for the task's own
   commit, which stays true forever.
2. **The leak pattern missed path-encoded homes and session UUIDs.**
3. **`setup` never created `devteam/audits/`**, though two skills file into it.

**The deepest finding is about requirements, not code.** All three auditors
converged on it independently: *the requirements enumerate where their goals
quantify.* G-2 promises a clear failure for **every** failure; R-2 and R-3
name two, and each new gap — undecodable input, a broken pipe, memory
exhaustion — gets closed by adding one more member to the enumeration. The
durable fix is requirements phrased as **rules over a domain**, with the
enumerated cases as their *tests* rather than as their *scope*. That belongs
in the `onboard` and `plan` skills, and is the most transferable thing this
rehearsal has produced.


---

## 19. Fixing a leak in a record that cannot be rewritten

The audits found four absolute session paths committed inside worker REPORT
blocks. Removing them ran straight into the rule that a filed report is
evidence and is not rewritten — the same rule that kept T-1's broken report in
the tree as proof the verifier worked.

**The resolution is that a redaction is not a rewrite.** Each path became its
repo-relative form: the identical claim, naming the identical file, in the form
the other two tasks' reports already used. No status, check, commit, count or
conclusion changed, and a reader diffing the file sees only a machine-specific
prefix disappear. The change is disclosed in the file itself, in `RECORD.md`,
and in the git history. **The append-only rule protects claims from being
quietly changed; it does not require a project to keep publishing a path that
means nothing to anyone else.**

Doing it produced two further findings, both from the act of writing the fix:

**The audit report reproduced the leak it was reporting**, and the leak check
flagged the report on the same rule that flagged the original. An audit that
republishes a disclosure has made the problem larger while describing it. The
audit skill now requires the sensitive segments to be replaced and the location
given instead.

**Audit findings numbered `S-n` collide with the step-id namespace.** Citing
one from a task file reports `cited-undefined` against a step that does not
exist — so a real finding gets referred to in prose and then lost. This is the
same defect the audits themselves identified for requirements (`R-3` written
inside a proposal reads as a citation), reappearing in a namespace nobody had
thought to reserve. Audit findings are now `COR-n`, `SEC-n`, `HYG-n`.

The pattern across all three is one thing: **an identifier grammar is a shared
namespace, and every document that numbers anything is competing in it.** The
grammar in `templates/FORMATS.md` reserved seven prefixes and said nothing
about what else might want to number something.


---

## 20. What a client the pipeline had not written found

The rehearsal in §15–§18 had one weakness that could not be designed away: the
manager was the author of the thing it was testing. So a second session was
given an underspecified paragraph — *"turns CSV files into JSON… reliable…
handles bad input gracefully. Python. Nothing fancy."* — and told to run the
pipeline as written, reporting anything impossible rather than working around
it. The client's positions were written down **before** the interview so the
run could be scored on what it extracted rather than on what the client
invented to fit the questions.

**Eighteen findings arrived before the product had a line of code**, and the
distribution is the interesting part: the last dozen were contradictions
between documents this project wrote, not defects in the manager's work.

### The ones that changed the design

**The guard's git rule was dead exactly where git runs.** `judge()` searched
from the target's parent, so a target that *is* a project root found no project
— and every `git -C <root> …` resolves to precisely that. `git reset --hard`,
`git clean -fd` and `git push` were all permitted at a project root while
`touch <root>/x` on the same project was refused. Fixing it required splitting
git by what each subcommand can *destroy*, because one undifferentiated set
either blocks every worker's commit or permits `reset --hard`.

**Protected paths protected nothing outside the project.** The feature the
guard's own docstring advertises by name — sibling repositories — was the exact
case it could not cover, because the early return for "target is in no project"
came before the protected-path check.

**The guard refused `2>&1`.** A file-descriptor number belongs to the redirect,
not the command, so `2` was read as a positional argument and resolved to
`<project>/2`. Constant false refusals on correct work, and none of the 27
existing false-positive controls carried an explicit fd.

**A client is not an operator.** Setup had the manager write the client's
approved allowlist into `.claude/settings.json` — executable only while the
client *is* the operator of the session. The manager **refused the
instruction**, correctly, and that refusal is the finding: a manager that
complied because the client sounded authoritative would be laundering a
permission.

**A probe discharges nothing, and the checks made it unexpressible.** The plan
skill demands the riskiest unknown as "task one, and it is small"; a probe
answers a question rather than a requirement, and `unmotivated-task` fired on
exactly that. A plan had to choose between an untrue field and a permanent
finding.

**Recovery could not tell a waiting supervisor from a dead one.** The board
names the supervisor; a supervisor awaiting its worker reports as completed. A
manager applying the recovery rule literally would declare a live claim stale
and put a second writer on a scope a worker was writing — **the two-writers
failure the whole design exists to prevent, reached by following the design.**
Observed rather than suffered, and only because `ListAgents` happened to show
the child.

**`git add -A` steals a worker's commit.** The rule existed for workers and not
for the manager, which is backwards: the manager is the one party guaranteed to
be writing concurrently with every worker.

**A document that contains a control byte stops being diffable.** A digest
documented a NUL by containing it; git committed the file as binary and
produced no diff for it. Every audit is a diff of a document against what it
describes, so the file had silently left every comparison — and only git's own
stat line noticed.

### What the run says about the method

**Three defects were found by adding a feature, not by testing one.** Task
kinds exposed a default that contradicted the parsing contract seventy lines
above it; the research index exposed a digest format that recorded a date but
never a sensitivity, so shelf life could not be computed from the file. The
features were cheap; what they bought was a forcing function on the shapes.

**Two fixes overshot and had to be corrected.** Naming every skipped file in
the research index produced 125 lines against a real tree — a report nobody
reads, which fails the same way silence does, wearing the opposite coat. The
correction was to name *near misses* and count the rest.

**The instrument problem did not go away.** Four broken instruments across the
project's history, two of them built during this run while *verifying other
people's findings*: a leak probe that classified URL fragments as prose, and a
pipe test that redirected the wrong stream. The only defence that has ever
worked is refusing to trust a summary over the structure.

**And the interview worked.** It researched before asking and found that RFC
4180 is Informational rather than Standards Track, so "RFC 4180 compliant" is
not a promise anyone can make; it asked the quantifier question in the skill's
own words; it changed the client's mind twice with evidence and was overruled
once; and it declined to generalise a good rule the client had agreed for one
case, on the grounds that an unrequested requirement is scope creep with a
number on it — a line from this project's own onboarding skill, applied against
its own good idea.


---

## 21. The open question: how much of this is ceremony

Deliberately unanswered, and recorded so it is not re-derived from scratch.

**Every change to this pipeline has made it stricter. Not one has made it
simpler.** That is not evidence the weight is justified — it is a property of
who has used it. A defect is evidence and gets reported; *"that was tedious and
bought me nothing"* is a feeling, and everyone who has run this either built it
or was hunting for problems in it. The forces all push one way, so it ratchets.

The measurement: one project produced **1,865 lines of design documents for a
tool that will be about 200 lines of code**, across five gates, before any
product code existed.

### The axis is the cost of being wrong, not the size of the project

This is the framing to build on, and it is not "big project, heavy process".

Where a single verification run takes **hours**, a wrong design costs hours per
iteration, and the interview and the plan are cheap by comparison — they buy
back their own cost the first time they prevent one wrong turn. Where the whole
artifact can be rewritten in an afternoon, front-loading a day of ceremony can
never pay, because the thing it is protecting against is cheaper than the
protection.

So the dial is not project size, complexity, or team count. It is: **how
expensive is a wrong turn here, and how late would you find out?**

### What may scale, and what may not

The load-bearing parts are cheap and stay whatever the setting:
**independent verification** (the one thing that makes a report worth reading),
**the guard** (free once installed), **reports passed upward verbatim** (costs
nothing), and **evidence over assertion** (a command instead of an opinion).

The expensive parts are ceremony, and all of them scale: interview depth, how
formally a requirement states its acceptance, whether a decision records its
declined alternatives, the number of gates, audit dimensions, checkpoint
frequency, and whether a plan needs a full task graph.

A plausible shape is a charter constraint — `Rigor. light | standard | full` —
set at setup, with the honest asymmetry stated: **you can move up but not
down.** Light work that turns out to matter can be re-planned; heavy ceremony
spent on a throwaway is simply gone.

### Why it is not built yet

Because the only person qualified to say which parts are ceremony is somebody
with real deliverables who did not build this, and no such person has used it.
Choosing now would be the author keeping his own favourites and calling the
result a medium. The `unnecessary` category in `docs/REPORTING-PROBLEMS.md`
exists to collect exactly this, and an empty result there is informative too —
it would mean either the weight is justified or nobody felt safe saying
otherwise, and those need telling apart.
