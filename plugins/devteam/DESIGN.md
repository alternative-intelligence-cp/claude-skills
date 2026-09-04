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
| **3** | one path end to end: `onboard` → `plan` → one task → `supervise` → `implementer` → `verify` → `checkpoint` | ◐ **written, not yet walked.** Ten skills, five agents and both hooks exist and are internally consistent. The phase is not done until a trivial project goes from idea to verified commit with no manual intervention between gates — writing the procedure is not the same as running it |
| **4** | rehearse on a throwaway project; fix what the rehearsal breaks | ◐ **first real dispatch done** — one task, two steps, two workers, green and correct. It found six defects (§15). Remaining: compaction, a killed agent, a deliberately failing check, a scope violation under a live guard |
| **5** | remaining roles: three audit dimensions, tester, documenter, reviewer | each dispatched and verified at least once in the rehearsal project |

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
reported. **Six defects surfaced, and every one of them was in this design
rather than in the agents' work.** They are recorded here because the pattern
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

**A seventh finding, about watching rather than running.** A supervisor is
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
