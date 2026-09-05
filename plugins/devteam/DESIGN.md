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

### Then the build phase found the one that scopes cannot cover

Everything above arrived before the product had a line of code. The first
finding that came out of *building* is the most interesting one in the project,
because it is a hazard the central safety mechanism is structurally unable to
see.

**A worker rewrote a concurrent task's commit, and the guard could not have
stopped it.** Declared scopes (P-12) divide the working tree, and the guard
enforces that division by target path. They do not divide the branch, the index
or `HEAD` — those are shared by every task in flight, and no scope names them.
The worker had committed its code, gone away to gather evidence that could only
exist *after* that commit, and run `git commit --amend` on what it believed was
its own commit. In the interval, a concurrent task had committed. The amend
landed on that task's commit instead: the report text was merged into another
task's subject and its hash was rewritten underneath it. Every path written was
inside the amending task's declared scope, so nothing was violated in the terms
the guard understands.

The recovery was correct and is worth keeping: `git reflog` still held the
original, and `git reset --soft` restored it — **soft, because the shared tree
held a third task's uncommitted work that `--hard` would have destroyed.** The
worker then reported the whole thing in its own commit message rather than
quietly fixing it, which is the only reason this is written down.

**The cause was a rule of ours, not a git accident.** "One commit per step" is
stated everywhere; "post-commit evidence needs a second commit" was stated
nowhere. The skill had twice noticed the *shape* of the problem — a check that
inspects the committed diff cannot appear in a report inside that commit — and
resolved it narrowly, for `check_scope`, by demoting it to `notes:`. That did
not generalise to evidence the report genuinely rests on. So a worker facing
"my report must cite mutation results, and my report must be in this commit"
had exactly one move that satisfied both, and it was the unsafe one. **A worker
contorting to satisfy two of our rules is a defect in the rules**, and the fix
is P-12b plus an explicit statement that a step may take two commits.

**What it says about the model of safety.** The guard was built on the
assumption that a write is judged by where it lands. Git history is a write
whose target is not a path, and there is no path-shaped rule that catches it.
This is the second time the guard has been blind to something because of the
frame it judges in — the first was `2>&1`, where a file descriptor was read as
a path. Neither was a bug in the code; both were the frame being narrower than
the world.

### The first finding that made it simpler, and it came from a refusal to use it

A second team was offered the pipeline for real work and **declined at the
door** — before running a single command — and the reason is the most useful
report this project has received.

Their tree already enforces one writer per repository, and that orchestrator
held the lock. The briefing they were sent said, accurately, that a `devteam/`
directory makes the guard police the entire repository: while a claim is live,
every write landing in that tree is judged against that claim's declared
scopes, *regardless of which session makes it*. Their reading: that is two lock
regimes over one tree, and the collision would surface as intermittent refusals
in their own session, mid-run, for reasons originating in a run they were not
part of. They preferred to report it from the doorway.

Their diagnosis is better than the report. **The guard's name describes one
property and its mechanism covered a wider one, and the widening was implicit.**
The trigger is the mere existence of a directory; the consequence is authority
over every path in the repository. Nothing in the act of creating that
directory says "this repository now has a second lock owner". They pointed out
that this project has spent sixty-eight findings on the inverse shape — a check
that quietly under-covers — and had not once looked for the same shape with the
sign flipped.

**The fix follows from what a scope is actually for.** Declared scopes divide
the work of *one run* among *its own agents*. They were never authority over a
stranger's session. So the scope rule and the outward-facing refusal are now
conditioned on the writing session being part of the run — the board's writer,
or a worker sharing its id — and a session that is positively somebody else's
is left alone. `devteam/` itself and the charter's protected paths stay
enforced against everyone, because those are the run rather than the product,
and P-13's lock is exactly the rule that must hold against a session outside
it.

Two details make this a safe trim rather than a hole. It **fails closed**: a
payload with no session id is `unknown`, never `theirs`, because reading it as
a stranger would silently disable the scope rule for every write arriving
without one — which is precisely the defect that left this guard inert for a
whole rehearsal, and it would have been reintroduced through the door built to
fix an unrelated complaint. And the F-2 regressions still deny, because a
subagent carries its parent's session id: that was confirmed against a live
multi-hour run at width 3, where worker subagents wrote task files under a
board whose writer line named the manager, and were not refused.

**What the trim accepts, stated plainly.** A session outside the run can now
write the product tree during a run without being refused. That is the correct
trade — a repository with two owners is a coordination problem the pipeline
never had standing to solve, and pretending to solve it is what turned a user
away.

**The mitigation offered for it was false, and the same peer caught that too.**
The sentence originally written here was "nothing catches that automatically;
the manager finds it at verification". Their question — *does verification look
where the NEW gap is, or where the old one was?* — is the right one to ask of
any mitigation offered for a removed control, and the answer was: where the old
one was. `undeclared-write` inspects a **task's own** commits; `dirty-tree` is
scoped to the task's own paths. A stranger's writes were examined by nothing at
all. A claim about one's own system, written confidently, unchecked, in the
same commit that removed the control it was excusing.

So `check_scope` gained `foreign-write`, and the coverage is now worth stating
exactly rather than summarising, because a half-covered check that sounds whole
is this project's most repeated finding:

| A stranger's… | caught? |
|---|---|
| commit touching a live scope | **yes**, already — `misattributed-write`, since its subject names no task |
| uncommitted write outside every live scope | **yes** — `foreign-write` |
| commit outside every live scope | **no.** It touches nothing any task claims and names no task, so nothing in the run has a reason to look at it |

The third row is not a defect to fix later; it is the residual of the trade,
and naming it is the point.

**And the first control run caught a false positive in the new check.**
`git status --porcelain` collapses an untracked directory to its shortest
prefix, so a worker creating `src/loader/new/x.py` in a tree with nothing
tracked under `src/` came back as `src/` — which no scope covers, so the check
accused the run's own worker of being the stranger. `-uall` fixes it. This is
the entire argument for the rule that more than a third of a guard's cases must
be false-positive controls: the fault was in the *new* code, on its *first*
run, and it was the kind that gets a guard switched off rather than fixed.

**And it is the first change here that removed a rule rather than adding one.**
Sixty-eight findings had made this pipeline stricter and none had made it
simpler. The one that finally did could not have come from inside a run, because
it is about the **entry condition** — the cost of adopting the thing at all,
which is invisible to anyone already using it. That is worth remembering when
reading §21: the missing findings are not hiding in the runs, they are in the
people who did not start one.

### "Right" and "sufficient" are two claims, and only one of them was measured

A proposal arrived as two options for a false positive: exempt the case, or
reorder the startup so recovery precedes the plan check. The reordering was
**right** — asking whether the plan is whole before reconciling what is running
asks about a state that has not been established yet — and it was **not
sufficient**, because recovery finds the agent alive, correctly leaves the claim
alone, and the check then reads the same state and fires again.

Its author's diagnosis: *"I described the two as alternatives. My error was
treating 'the reordering is right' as 'the reordering is sufficient.' Both were
true of the reordering; I only had evidence for the first."* Two properties of
one proposal, one evidenced and one assumed, offered as a single claim — and a
client taking the reordering alone would have shipped a false positive believing
it closed.

**The diagnostic that catches it in one step is the sharper half, and it is
cheap: ask where the fact that decides the case lives.** Here, what separates a
healthy dispatch from a dead claim is *whether an agent is alive on it* — which
is in no file. So no rearrangement of files could decide it, however correct the
rearrangement. **A fix aimed at the wrong substrate cannot work no matter how
right it is**, and its rightness is exactly what makes that hard to see.

So before proposing a change: name the fact that distinguishes the cases, say
where it lives, and check that the thing you are changing is the thing that
holds it. If it is not, the change may still be worth making — it just is not
this fix.

### A sentence written to justify a measurement does not itself get measured

Three false sentences reached signed text on this project in one night, from an
author who was measuring everything else carefully. Their shapes differ and the
pattern underneath is the same one:

| | |
|---|---|
| a constraint row promising a bound | **stale** — true when written, falsified by a decline |
| "`repr()` enforces exact representability" | **never true** — a claim about floats, written while reasoning about integers |
| "not escapable by choosing a reader" | **true in conclusion, false in reason** — a reader exists that separates the texts, just not as numbers |

The author's own diagnosis is the finding: *"a sentence written to justify a
conclusion I had already measured does not itself get measured. The measurement
licenses the paragraph, and the paragraph then acquires claims the measurement
never covered."*

That is why haste does not explain it. Two of the three were written **inside
messages that were otherwise careful**, by someone actively measuring something
adjacent — integers while claiming something about floats, number-readers while
claiming something about readers. **The care was real and it was pointed one
clause away from the error.**

The practical form: when a measured result gets written up, the measurement
covers the *result*. Every supporting sentence in the same paragraph is
unmeasured prose that has borrowed the result's authority, and the borrowing is
invisible because the paragraph reads as one thing. Underline the claims that
are not the measurement, and check whether any of them is doing load-bearing
work — a criterion, a justification, a scope. Those are the ones that reach
signed text and stay wrong.

### Malicious compliance is a diagnostic, and it points at the rule

A rule this project follows without having stated it, from the author: *"if you
want me to follow the rule, just tell me why I should. If I find it logical,
from then on you probably couldn't pay me to break said rule. However, a rule
with no justification is just getting ignored, or worked around, or my
favourite, malicious compliance."*

Both halves are load-bearing. A justified rule gets **stronger** adherence than
an asserted one — not merely equal adherence more pleasantly obtained. And an
unjustified rule does not simply fail; it gets defeated in a way that
technically complies, which is the failure mode that leaves no trace.

**So a workaround is evidence about the rule, not about whoever found it.** When
an agent follows a rule to the letter and defeats its purpose, the first
question is not *why did they do that?* but **what does this rule fail to say
about why it exists?** That is the same shape as a test passing while measuring
a weaker proposition than its requirement — honest compliance with the letter of
something whose point was elsewhere — and it is worth checking for in the same
way: read what the rule *asks for* against what it is *for*.

**This is also a large part of why the design record is as long as it is**, and
it is worth saying plainly against the ceremony question. Every protocol rule
here carries the measured failure that produced it: the amend that rewrote a
concurrent task's commit, the seven ad-hoc probes that answered questions they
were never wired to ask, the two workers who met a conflicting ambient
instruction and reported it. None of them reads "do X." All of them read "do X,
and here is what happened when somebody did not."

Rules with their reasons attached are longer than rules. **They are longer on
purpose**, because the reason is the part that survives contact with somebody in
a hurry — and the pipeline is explicitly built for that person rather than for a
careful reader at their best.

### The shape that has cost the most: two rules that cannot both be satisfied

Stated by the manager running the live project, after it had hit the same thing
five times: **a rule a worker must break to do the work right is a defect in the
rule.** Four of the five instances were not one bad rule but a **pair** of rules
that could not both hold, with no indication anywhere that they were in tension:

| The pair | What the worker did |
|---|---|
| "one commit per step" **and** a report that must cite post-commit evidence | amended, and rewrote a concurrent task's commit |
| "no `rm`" **and** mutation testing that runs in a scratch directory | breached the prohibition, and reported itself |
| "no `rm`" **and** a file created in error under `devteam/` | left the tree dirty, disabling every later verification |
| P-20's two rules under one number | conflated a flaky check with a legitimate retry |

The failure is invisible to whoever wrote either rule, because **each one is
correct in isolation and neither mentions the other.** The author of "one commit
per step" was thinking about a legible record; the author of "the report cites
its evidence" was thinking about P-5. Nobody wrote the sentence where they meet,
so the worker is the first party in the system's history to hold both at once —
and it holds them under time pressure, with no standing to change either.

This is why the rules keep getting found by workers rather than by review. A
reviewer reads rules one at a time; a worker is the only party required to
satisfy all of them simultaneously. **So a worker reporting that it could not
comply is a higher-grade signal than a worker reporting a bug**, and the
instruction to report rather than work around is what converts it from a silent
workaround into a finding. Three of the four above were self-reported breaches.

The practical consequence for anyone adding a rule here: the question is not
"is this rule right?" but **"what else must be true at the same moment, and can
both hold?"** That question has a much better hit rate on this codebase than
re-reading the rule you just wrote.

### And the detector for it: count how many people found the same workaround

The manager supplied the method, from watching six workers on one task:
**four of six independently wrote near-identical paragraphs** about a check
that inspects a commit which cannot yet exist. Not four confusions —
*repeated independent discovery of the same workaround is evidence about the
rules, not about the workers.*

This is worth more than the finding it produced, because it is **cheap and
mechanical where the pairs problem is neither.** You cannot review a rulebook
for the pairs that cannot both hold; the space is quadratic and each rule reads
fine alone. But you can notice when several agents who never spoke to each
other arrive at the same departure, and that noticing needs no cleverness — it
needs someone reading more than one report at a time, which is exactly what a
supervisor and a manager already do.

It was applied within the hour, and **the first application counted the wrong
thing** — which turned out to be the more useful half of the story.

The claim made was that *three tasks had independently written their steps as
a table* rather than the recognised checklist form, and the grammar was widened
on that basis. Measured afterwards, **one** had. The other two wrote a checklist
declaration *and* a `### S-n` section carrying the prose — not a third layout
but the rich body hung off the declaration the grammar already had. Three
findings had been read as three departures without anyone counting what each
file contained. The detector was sound; the count fed into it was invented from
the finding total.

Worse, the obvious next move — recognising `### S-n` as a declaration too —
is wrong, and only running it says so: it produces **eleven `duplicate-id`
findings**, because the tasks using it are declaring correctly in the checklist
and elaborating under the heading. Two layouts that look identical under a grep
turned out to be one departure and one ordinary use of the grammar.

**So the detector needs a second half, and it is cheap: before widening a
grammar on a count, apply the widened rule to the corpus and read what it newly
reports.** That single step catches both errors — the fabricated count and the
duplicate-id trap — and it costs one command. Counting departures tells you
where to look; running the candidate rule tells you whether you were looking at
a departure at all.

The genuine instance stands: **four workers hit the post-commit-evidence
contradiction**, resolved upstream while the task was still running, which is
why it stopped at four rather than reaching every worker in the project.

The distinction that makes this usable: one agent departing from a rule is a
mistake, and the rule usually stands. **Several agents departing the same way,
independently, is a measurement of the rule** — and the burden shifts to
whoever wrote it to say why the natural path is the wrong one.


---

## 20b. Guidance goes where the temptation is, not where the documentation is

The single most reliable design lesson from the live run, and it was arrived at
twice independently before anyone stated it.

**The evidence.** The guard's refusal message names the interpreter heredoc that
would get around it — a nudge, the weakest instrument here, and the only one
with measured evidence of changing behaviour. A verifier that had never read the
finding met the refusal and reported that the message "explicitly names and
discourages the interpreter-based workaround, so I did not use it." The same
rule written in a skill would have been read at dispatch time, hours before the
moment it mattered, by an agent with no reason to remember it.

Then the manager reached the same principle from the other end. Discussing a
mechanism for recording accepted findings, it observed that the framing decides
who reaches for it: *a manager who reads the block as **suppress** adds entries
when the tree is annoying; a manager who reads it as **restore the zero** is
reluctant to add any, because every entry costs them the signal they are trying
to keep.* Same mechanism, opposite incentive — and its recommendation was to put
that sentence **in the block's own header rather than in the skill**, because
the header is read at the moment of temptation and the skill is not.

**So: for anything meant to resist a temptation, the placement is not a
presentation detail — it is most of whether it works.** A rule in a skill is
read once, early, by someone who has not yet met the situation. A sentence in a
refusal message, a check's finding text, or a file's own header is read by
someone standing in front of the decision, which is the only moment it can
change anything. This is why `cited-undefined` names the line that would fix it,
why the scope refusal carries the verifier's scratch recipe, and why the guard's
message says the heredoc is a limit rather than permission.

The corollary is a question worth asking of every rule here: **where will
somebody be standing when this matters, and is the rule there?**

### The working directory is not a mechanism, and a lint for it is not either

A session with a shell left in another project's directory ran
`git add -A && git commit` against a **live run's repository**. It did not fire
— an earlier command in the same `&&` chain failed on a path that did not exist
there — and the tree was verified untouched afterwards. **That is luck, not a
control**, and expecting anyone, person or agent, to remember `git -C` every
time is not a mechanism.

**The structural fix was to move an existing rule, not to add one.** The history
category — `--amend`, `add -A`, `reset --hard`, `rebase`, `stash` — sat *below*
the exit that stops policing a session which is not part of the run. So a
stranger could sweep a live run's index or rewrite its history, which is exactly
the case that nearly happened. It now sits **above** that exit, beside the
`devteam/` lock, on the same reasoning: **history is the run, in the same sense
that directory is, and P-12b says no scope covers it.**

The line that keeps this from being the over-reach that once turned a team away
is narrow and worth stating: **a stranger's writes to the product tree are still
their own business.** What is refused is an operation on *this run's shared
index and history* while a claim is live. Controls assert both halves.

The refusal message also names the likely cause, because the placement principle
applies here more than anywhere: somebody meeting it is standing in a directory
they did not mean to be in.

**And the lint was probed and rejected**, which is the part worth keeping. The
obvious follow-up is a check for bare `git` commands in the skills. Run over the
corpus it reported **24 hits across 9 skills** — and nearly all of them are
*prose discussing* git commands: "`git add -A` must be allowed", "never
`git add` followed by a bare `git commit`". Telling a command from a discussion
of a command is the semantic reading this project refuses everywhere, and the
signal-to-noise was the familiar 1-in-14 shape.

So four genuinely runnable commands were fixed by hand, and **no check was
built.** The guard covers the case that matters regardless of what any document
says, which is the better place for it anyway.

### The worst kind of check defect: one that fires on mandated behaviour

`check_refs` read a quoted finding as a citation. A supervisor had written its
check output verbatim into its report — which P-16 and P-17 require, and which
is the single behaviour this whole design leans on hardest — and the check
reported a new finding **against the file that quoted it.** The project's one
permanent agreed finding began spawning a second in every task file that
mentioned it.

The manager's statement of why this is the worst category is better than mine:
**a check that fires on the behaviour the protocol mandates puts the correct
response and the safe response in opposite directions.** Every other defect
here costs somebody time. This one teaches an agent that reporting honestly is
punished, and the lesson it teaches is learned quietly, by paraphrasing next
time.

It is also a mechanism by which a finding count grows **with nobody having
accepted a finding** — which the trigger written down for that problem does not
cover, because it assumed the count only grows when somebody decides to let it.

The check to apply, and it is cheap: **for each finding a check can emit, ask
what a correct report of it looks like, and run the check over that report.**
Fenced output was already skipped here; inline output was not, and every report
in the project quotes inline.

### The other failure between two agents: a loop that produces genuine findings

Assent is the first failure mode. This is the second, and it is harder to see
because it does not feel like a failure at any point.

The manager and the plugin's author exchanged roughly a dozen round trips, each
one a reply to the last, **with nothing on the question table and one task
running.** Every message contained real findings. Every reply was justified by
the message before it. And the manager's contribution over that window was
**zero dispatches and zero board moves** while its largest task ran unattended.

Its own diagnosis: *"a loop that is producing findings is the hardest kind to
notice, because the output is genuine and each reply is justified by the one
before it."* The loop's own rule already covered it — the run skill says
escalations go up as a **batch** — and a correspondence is what happens when
one message gets one reply.

**The tell is not the quality of the exchange, it is what stopped moving while
it happened.** So the question to ask of any long exchange between two agents
is not "is this productive?", which it plainly is, but *what has not advanced
since this started?* Both parties here answered "nothing" and neither had
noticed.

The fix is the rule that already existed, applied to the channel rather than to
escalations: **batch.** One dense message that closes several threads beats six
that each close one, and the cost of the second form is invisible because every
individual message is worth sending.

### Between two agents the failure mode is assent, and the escape is being wrong out loud

Named by the manager after it happened three times in one day, and it turns out
to be a principle several parts of this design already embody without anyone
having stated it.

Two capable agents reviewing each other's work drift toward agreement. Not
through deference — through the ordinary mechanics of a hedged claim, which
offers nothing to check. *"Checks that compare declared things tend to work
better"* produces a nod. **"Every check that works compares two declared lists;
every check that failed tried to read prose"** produces somebody going to their
own data to see whether it fits — and finding, in that case, that it does not.

Three times in one day one party stated something crisply enough for the other
to refute it **with data already in hand**: an account of why checks work,
refuted by the other's own measured candidate; a set of findings called
"benign", refuted by which task was still open; a diagnosis that a refused write
had been outside the repository, refuted by reproducing it. In every case the
sharp version was wrong and the correction was worth more than a hedge would
have been.

**The lesson is not to be confident. It is to make claims falsifiable**, which
usually means sharper and narrower than feels comfortable, and to state the
figure rather than the impression. A claim nobody can check is not modest; it is
inert.

This is already load-bearing in several roles and was not recognised as one
thing:

- **A verifier answers PASS or FAIL** (P-18), not "looks right". A hedged
  verdict cannot be refuted and therefore cannot be evidence.
- **An auditor is briefed to break a claim**, not to review it — and the
  restart shape (P-17b's neighbourhood) requires failed refutations as the
  evidence rather than a supervisor's concurrence.
- **An acceptance criterion is a command with an expected output**, never an
  adjective, for the same reason at the level of the product.

So it belongs in the dispatches too: a brief that asks for an opinion gets
assent, and a brief that asks for a refutation gets evidence.

### And name which side is the source of truth, or it is a spell-checker

A sharpening of the rule below, from the case that produced it. A file's
docstring claimed a set "holds eight key names". The claim appeared **twice** —
in the docstring and pinned verbatim in the file's own blind-spots entry — and
the file **compared them**. Measured on a clean archive:

| Edit | Result |
|---|---|
| change one prose copy to "nine" | **2 failed**, within a second |
| widen the **set** to nine, both copies still "eight" | **139 passed** |

**The count was not unguarded. It was guarded, rigorously, against a copy of
itself.** Which is why four careful repair rounds walked past it: from inside
the file the sentence is visibly checked, and the check is real — it simply
cannot fire on the fact, because neither side of the comparison is the set.

So: **whenever a check compares two things, name which one is the source of
truth. If neither is, it is a spell-checker.** Two copies of a fact checked
against each other are not redundancy; they are one claim with a second mouth,
and the agreement between them is evidence of nothing except careful
transcription.

This is also the argument for *refer, don't count* being structural rather than
stylistic. A description that points at the thing has no second copy to agree
with.

**And the same shape appears in a person's habit, not only in a file.** A
manager wrote that four remaining findings "are T-3's three … and nothing else",
where the four were T-3's three **and one more**. The count came from the
command — it had run the check and read `4`. The **enumeration** came from
memory, because it had dispatched T-3's three minutes earlier and the output was
already labelled in its head. It survived thirteen hours of running that same
command, because every later run was read against a pre-labelled expectation.

The narrow rule: **a sentence that states a total and names its members is two
claims, and the second is the one nobody re-derives — because the first one's
provenance launders it.** "And nothing else" is a completeness claim about a
set, writable only by somebody who has just read the set.

### Why a check works: name the rule whose two sides it compares

This design's own account of itself was wrong for most of a day, and the
correction is the most useful thing in it.

**The wrong version, stated confidently here and elsewhere:** every check that
works compares two declared lists; every check that failed tried to read prose.
It fits a lot of the evidence. It is refuted by one case in this project's own
data: a candidate check compared a task's `Discharges.` against the identifiers
appearing in its `Gate.` — **two identifier lists, no prose read anywhere** —
and produced fourteen findings on seven tasks, one of them real.

**What actually separated the good candidate from the bad one was whether a
rule already required the two sides to agree.** Nothing in the protocol, the
planning skill or the task template required a gate to name the requirements it
discharges. The check invented the agreement it was checking, and its thirteen
false findings were **the rule's absence showing up**. Parsing harder would have
made that worse, not better.

So there are two failure modes and they want opposite fixes:

| Mode | Looks like | The fix |
|---|---|---|
| **inventing an agreement no rule requires** | noise, at 1:14 or 1:3 | write the rule, or withdraw the check — never parse harder |
| **being unable to extract the thing to compare** | silence, not noise | a backstop after the fact, and a refusal that names the limit |

The second is the interpreter heredoc. A rule genuinely does require a write's
target to lie in a declared scope (P-12, P-13); the hole is that the target
cannot be determined from the command text at all. That is not fixable by
parsing and never will be, which is why its answer is `check_scope` afterwards
plus a refusal message that names the limit rather than pretending it is closed.

**The usable form: before building a check, name the rule whose two sides it
compares. If you cannot name one, you are proposing a rule rather than
enforcing one** — and that is a decision for whoever owns the rules, not
something a script gets to make by firing.

**Applied to this project's own recent checks, it found three that were
proposing rules.** `gate-omits-decision` enforced an agreement nothing
required, so its residual findings on a real project were the missing rule
rather than defects; `one-sided-link` rested on an entailment of two field
definitions that had never been written down; `template-drift` enforced
conformance to a current template with nothing stating that artifacts stay
conformant as templates change. All three rules are now stated, which is what
makes the checks legitimate. The alternative was to withdraw them, and stating
the rule was the right call in each case only because each rule survived being
looked at on its own.

### The path nobody walks: a habit built forward has no backward

Four times now this project has found the same shape — a mechanism that has
never produced output, so nothing says it is missing. The fourth instance is
the sharpest because the mechanism is not a check or a rule. **It is the
retraction of an approval.**

Approving a task changed four things: a charter constraint row, a decision, a
requirement's status, and a board claim. Declining it moved three. The charter
went on asserting *"the tool refuses any input whose predicted footprint
exceeds 4 GiB"* for four hours after the task that would have built that
refusal was stopped — and nothing in the tool had ever done it.

**The forward path was a habit built over eleven amendments. The backward path
had never been walked once**, because no task in the project had ever been
approved and then declined. Every other reversal *superseded* a decision with
another decision, which leaves both in place and reads correctly. **A decline
leaves a hole where the approval's consequences already are**, and nothing
generated the list of what to undo.

The fix was sitting unnoticed in machinery built for a different reason.
`Costs.` — the block a blocking question must carry, computed *before* the
client answers — is precisely the manifest of what approving will change. So it
is precisely what to reverse if the answer is later withdrawn. A field built so
a client could see a price turns out to be the reversal procedure, and neither
party spotted that until an approval had to come back.

**And the review that should have caught it failed in a way worth naming
separately.** The row's author reviewed it an hour after standing the task
down, and flagged only that its constants were fitted and unverified. They were
auditing the *numbers inside a claim they had stopped believing* and had not
noticed they had stopped believing it. That is the weaker-proposition failure
turned on a reviewer rather than on a test: **"are these constants right?"
presumes the answer to "is this sentence still true?"**, and a careful reviewer
can spend all their attention inside a predicate that no longer holds.

### The class of fix that cannot be observed is the class that silently fails

The manager supplied the edge and it is sharper than the incident that produced
it. **Every plugin fix it had recorded as landed, it had recorded after
observing an effect** — a check clearing a finding, a new check reporting three
real ones, a probe returning four denies and four allows. When told the
amendment-sweep rule had landed, it did not write that down, and not by luck:
*"F-96's fix is prose in a skill. It produces no observable, so there was
nothing to observe, and it never got written down as landed."*

**A check that does not run is caught by its output being wrong. A paragraph
that was not written is caught by nothing.** That is the shape of a mechanism
that has never produced output, applied to the *delivery* of a rule rather than
to the rule itself — and it is why a lost edit survived hours while every code
change in the same period was confirmed within minutes.

The mechanism that lost it was two edits to one file computed from one read, so
the second write discarded the first. The mechanism that hid it was that prose
has no output to be wrong.

**An automatic check for this was measured and rejected.** The idea: extract
backticked phrases from a commit message and require each to appear in the
commit's added lines. Run against five real commits it *did* flag the false
claim — the phrase naming the rule that never landed — but at roughly one real
finding to two or three spurious, because separating "a phrase I am claiming to
have added" from "a phrase I am referring to" is the English-parsing problem
this project refuses everywhere else. Same conclusion as every other time:
**declare, do not infer.**

The viable form is therefore the declared one — a commit trailer naming
`<path> :: <phrase>` for each claim, checked against the tree at that commit,
which is `check_report`'s `checks:` field pointed at an author's own commit
rather than a worker's. It is not built. It is self-declared and therefore
skippable, and the honest first move is the practice it would automate: **when
you claim a prose file gained something, re-read the file.**

### A second deferred mechanism: the unscoped commit

Recorded with its condition, at the manager's request, so it is not re-derived
the day the near-miss becomes a hit.

An unscoped `git commit` takes whatever is in the shared index, which is the
F-66 case exactly. It is **not** refused, and the evidence for that decision was
looked for rather than assumed: the one real bad commit used `git add -A`, which
is now refused outright, and the unscoped case was a near-miss that *"did not
land only because T-2 committed first."* One near-miss avoided by ordering, and
no instance of the unscoped form actually producing a bad commit. Against that,
a wrongly-refused commit is the worst false positive available in this system —
a worker unable to land finished work.

With `add -A` refused the blast radius is smaller but the shape is unchanged:
another agent can still stage its own files, and an unscoped commit still takes
them.

**The narrow form, if the trigger fires:** on an unscoped `git commit`, read
`git diff --cached --name-only` and refuse **only if a staged path lies outside
the caller's live scope.** That is F-66's condition precisely, it permits every
legitimate "commit what I staged", and it costs one git call at hook time. Its
limits, stated because they are real and would otherwise be discovered: it
**races** — another agent can stage between the check and the commit — and it
needs the caller's scope, which resolves for a manager (`devteam/`) but would
refuse everything for an agent holding no claim, the same blind spot that
stopped a verifier building a mutation.

The trigger is an instance, not an argument: **an unscoped commit that actually
carries another task's staged work.**

### The deferred mechanism, and the trigger that would justify it

Recorded so it is not re-derived, and so it is not built early.

Two findings on the live project may not be fixed — one names a checkpoint
before it is filed, in an append-only record; one cites another task's step from
inside an execution record that P-42 freezes. Both were left standing
deliberately. The worry is that **a tree expected to be red is a tree nobody
reads.**

The manager's measurement of the actual cost is better than the worry: it reads
`N finding(s)` first, and only reads the finding when the count differs from the
one it remembers. **So the discriminator degrades by one bit per accepted
finding, and it degrades silently** — the resting state was 1, then 2, and the
next new finding arrives as 3 against a remembered 2. The cost is not the noise;
it is that the count stops being a signal.

The trigger for building it is stated as a measurement rather than a feeling:
**the day a manager reads a count and does not read the finding under it.** Not
before. Asked directly, the manager reported "not yet" — and reported that it
had nearly sent an example of the rot, then checked the committed artifact and
found the slip was in the conversational layer while the artifact was correct.
That check is P-17b applied one message after P-17b was written.

The shape, if the trigger fires: an `## Accepted findings` block in `RECORD.md`,
each entry naming the finding kind, path, line, a reason and a decision; the
checks downgrading exactly those to notes; and — the half that stops it rotting
— **a stale acceptance that no longer matches anything is itself a finding**,
because an acceptance nobody revisits is a silence nobody chose.

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

### Half of it is now answered, by the author, and it is the comparison class

That number sat here as an accusation for a day. It is not one, and the reason
is that **the tool is not meant to suit small projects.** The author's
position, stated plainly: it *"will likely be not much use at all for small or
simple projects, as the tooling itself will outweigh them in complexity.
However, for when things really count, having something take a little longer
the first time through and getting it right is just preferable all around."*

So 1,865 lines for 200 is **the pipeline being run below its threshold on
purpose, to find out how it breaks** — which it did, 123 times. The useful
question was never *"is this heavy?"* It is **"is this heavy for work where
being wrong is expensive?"**, and that is a different question with different
evidence.

**And the baseline it is judged against is not the first build.** The obvious
objection — a model could produce the same artifact in ten minutes — is
conceded and answered: *"that would not have been tested at all, and if it even
came close to what the person actually wanted it would be a true miracle.
Redoing costs too, and sometimes more than the initial cost."* The comparison
is against **build, discover it is wrong, build it again**, which is the cost
this pipeline claims to remove. Efficiency remains a goal — the expectation is
that a well-tuned pipeline saves tokens overall, not that weight is a virtue.

**What stays open, narrowed.** Not "is this too heavy", but **which individual
steps buy nothing on *any* project**. A simplification justified by
small-project ergonomics is out of scope by construction. A simplification
justified by a step earning nothing anywhere is exactly what is still wanted,
and only two have ever been found — both from people who declined to use the
thing.

**And a third criterion, which is the purpose rather than the sizing.** The
pipeline exists so that *"a less experienced developer can build quality
software via the structure it forces"* — to **model best practice all the way
through the chain so the user does not have to already know it.** That makes a
specific kind of step indefensible regardless of its cost: **one that only
works when the operator already understands why it matters.** Such a step has
failed at the thing the pipeline is for, and its weight is the least of the
problem.


### The one nudge, and the only evidence either way

Almost everything in this design is a refusal, a check or a rule. One thing is
none of those: when the guard refuses a write, its message names the
**interpreter heredoc** that would get around it, says plainly that it is a
known limit rather than permission, and points at the check that would report
the write afterwards. It was added because a worker met the refusal, reached
for `python3 - <<PY` in one step, and did not experience it as evasion — the
bypass is the *ergonomic* path, and a refusal that says nothing about it leaves
every reader standing beside an unjudged door.

It is the weakest instrument here and it worked. A verifier that had never read
the finding met the refusal and reported, unprompted: *"its own refusal message
explicitly names and discourages the interpreter-based workaround, so I did not
use it."* One data point, from an agent with no stake in the outcome, under
exactly the conditions the message was written for.

**Worth recording because the alternative was to do nothing.** The hole cannot
be closed — an interpreter's writes are not classifiable from command text, and
refusing every heredoc would break the mutation testing that most of this
project's evidence is built from. The options were a nudge or silence, and
silence was losing. It is not a control and must never be counted as one; the
layer that catches the write is still detection, after the fact.

The same shape then fixed a worse defect. A verifier could not build a
mutation, because **a verifier holds no task claim and every in-tree write is
therefore "a path no live task has claimed" by construction** — so it concluded
mutation was unavailable, fell back to reading the code, and disclosed the
fallback. The refusal was correct and the conclusion drawn from it was wrong,
and nothing in the message offered the way out. It now carries the recipe.
Twice now the fix has been that a refusal was accurate and unhelpful.

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

### The model band is the same dial, seen twice

A floor and a ceiling look like one setting and answer two different questions.
**A ceiling controls cost. A floor prevents a class of error** — and which
class depends entirely on the axis above.

Where a wrong turn is cheap and immediately visible, there is no floor worth
paying for: a weak model produces something mediocre, you see it, you fix it.
Where a wrong turn is expensive and surfaces late, the floor is not buying
quality, it is buying *not being subtly wrong in a way nobody notices for
hours*. Those are different purchases and only the second justifies a floor
above the cheapest thing that runs.

So a project should be able to say "cheapest possible throughout" and mean it,
and another should be able to say "nothing below X touches design" and have
that enforced — and the charter's `Model band` row is where both already live
(P-40). What is missing is the reasoning, per class, rather than one band for
everything.

**One measurement from this project, against the obvious assumption.** The
verifier runs on a smaller model than the supervisor it checks, and it returned
a correct FAIL on work that supervisor had reported DONE in good faith. That is
evidence that *mechanical comparison* — re-run the exact command, diff the
output, check the block — is genuinely a cheap-model task, and that the floor
belongs where judgement is: design, planning, audit, and the interview. It is
one data point and it argues against the reflex of spending the expensive model
everywhere because verification sounds important.

### The ceremony cost grows with the record, and nothing bounds it

Found while revising estimates, and it is a scaling property of this design
rather than a defect in a plan.

The per-step cost is dominated by **fixed overhead**: reading the charter, the
requirements, every decision, the digests, then dispatching, verifying and
reporting. Measured at roughly 200,000 tokens per step-unit on the first real
task. But the decisions file is append-only and grows with the project, so
**every task from here reads a longer record than the one before it.** The
fixed cost is not fixed; it drifts up, and the drift is unbounded by anything
in the current design.

For a short project this never bites. For the projects this pipeline is
ultimately aimed at — a compiler, a library ecosystem, something worked on for
a year — it eventually dominates, and the discipline that makes the record
valuable is the same discipline that makes it expensive to consult.

The obvious answers all have costs worth naming before anyone reaches for one.
**Summarising the record** puts a second, lossy home next to the authoritative
one (P-34), and the summary is what gets read. **Scoping decisions to areas**
means a worker no longer sees a decision from a neighbouring area that
contradicts its own, which is precisely the cross-cutting contradiction audits
exist to catch. **Reading only recent decisions** inverts the value: the oldest
decisions are the load-bearing ones, which is why they are still cited.

No answer is proposed here. It is recorded so that the first person to notice
the cost does not reach for summarisation without seeing what it trades away.

### Why it is not built yet

Because the only person qualified to say which parts are ceremony is somebody
with real deliverables who did not build this, and no such person has used it.
Choosing now would be the author keeping his own favourites and calling the
result a medium. The `unnecessary` category in `docs/REPORTING-PROBLEMS.md`
exists to collect exactly this, and an empty result there is informative too —
it would mean either the weight is justified or nobody felt safe saying
otherwise, and those need telling apart.
