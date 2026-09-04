# The protocol — the rules the pipeline runs on

Numbered, normative rules. Every skill, agent and check in this plugin cites
them by number rather than restating them, because **a fact with two homes
drifts** (P-34) and this file is the one home.

Cite as `P-7`. A rule is amended by superseding it with a new number, never by
rewriting its text (P-23) — the old text records what was true when the
decision was made.

Each rule states what to do **and why**. A rule whose reason is not written is
a rule the next reader will litigate.

---

## 1. The charter is the authority

**P-1 — The charter is what the project is.** `devteam/CHARTER.md` states what
is being built, for whom, what "done" means, what is explicitly out of scope,
and the constraints that bound every later decision. It is written by the
interview, signed by the client, and versioned. Every requirement traces to it
and every checkpoint diffs against it.

**P-2 — Changing what is being built is a charter amendment, and the client
signs it.** Scope does not grow because a supervisor decided something would be
nice, and it does not shrink because a worker found something hard. A proposed
change is a `CHARTER` class question (P-26), which always stops for the client.
Silent drift is the single failure this whole pipeline exists to prevent.

**P-3 — Every requirement is numbered, normative and testable.**
`devteam/REQUIREMENTS.md` holds `R-n` entries, each with a statement, the
source it came from (an interview answer, a research digest, a standard), an
**acceptance criterion expressed as something that can be run or observed**,
and a priority. "The system should be fast" is not a requirement; "p99 latency
under 200 ms at 100 concurrent requests, measured by `bench/latency.py`" is.

**P-4 — Requirements, tasks and checks are diffed against each other, not read
in isolation.** The diff is mechanical, not a reading (P-35), and it reports:

| Finding | Means |
|---|---|
| `uncovered-requirement` | a requirement no task will implement |
| `unmotivated-task` | a task discharging no requirement — either scope creep, or a requirement nobody wrote down |
| `unverified-requirement` | a requirement with no acceptance check — it will be declared done by opinion |
| `orphan-scope` | a charter goal no requirement covers |

The middle two are the valuable ones, and they are the reason this diff exists
at all: the prior art this pipeline is drawn from records that **every hole it
ever found was found by a check that diffs two lists, and none of them by a
test.**

**P-5 — A requirement is discharged by evidence, never by assertion.** A task
closes when its acceptance criteria have been run and their output recorded —
not when a worker says it is finished.

---

## 2. The three layers, and who may write what

**P-6 — There are exactly three layers, and each has one job.**

| Layer | Who | Owns | Never |
|---|---|---|---|
| **Client** | the human | the charter, the answers, the sign-offs | is asked anything answerable from the charter, the record, or research |
| **Project manager** | the main session | the charter, the task graph, the board, the record, escalation, checkpoints | writes product code |
| **Supervisor** | one agent per in-flight task | decomposing its task into steps, dispatching workers, verifying each step, escalating | writes product code; talks to the client |
| **Worker** | one agent per step | doing exactly the step it was dispatched with | talks to the client; writes outside its task's declared scope |

**P-7 — The project manager writes no product code.** It assigns, gates,
verifies, records and routes escalations. A manager that also implements cannot
hold the gate role cleanly, because it ends up verifying its own work. This is
a discipline, not something a tool list can enforce — the manager is the main
session — and this rule is its text.

**P-8 — The supervisor writes no product code either, and is deliberately
thin.** It is a dispatch-and-verify loop, not a designer. Anything it might be
tempted to implement itself is a step, and a step gets a worker. A supervisor
that implements is a second, unverified writer inside a task.

**P-9 — Only the project manager speaks to the client, and the channel is
recorded rather than assumed.** A supervisor escalates to the manager; a worker
escalates to its supervisor. This keeps one voice, one batching policy (P-27),
and one record of what was asked and answered.

**The client is not necessarily a person at this terminal.** It may be another
session, an agent, a script, or nobody at all — so the charter names the
channel (`terminal`, `session <name>`, `both`, `none`) and every path that
reaches the client consults it. An interactive-only escalation is a defect, not
a simplification: it silently converts "the client did not answer" into "the
loop hung", and the two need different responses. Where the channel is `none`,
`REVERSIBLE` questions proceed on their recommendations and `IRREVERSIBLE` and
`CHARTER` questions stop the task and wait, which is the honest behaviour when
there is nobody to ask.

**P-10 — A worker writes only inside its task's declared scope.** Every task
names the paths it may write (P-12). Writing outside them is refused by the
guard, and needing to is a finding worth escalating, not a thing to work
around.

---

## 3. Claims, locks and running more than one thing

**P-11 — The board is the lock, and a claim is a commit.**
`devteam/BOARD.md` is simultaneously the live state and the mutex. Claiming a
task means committing a change to the board, so the board's git history *is*
the record of who worked what and when, at no extra cost. The board itself is
always writable — it is the lock, and a lock nobody can take is a deadlock.

**P-12 — One writer per scope, and scopes never overlap.** A task declares the
paths it writes. Two tasks in flight at the same time must have disjoint
declared scopes; the manager refuses to claim a task whose scope intersects a
live claim. This is what makes parallel work safe inside a single repository,
and it is checked before dispatch rather than discovered afterwards.

**P-13 — `devteam/` has one writer: the project manager.** Supervisors and
workers write into the product tree and into their own task file's execution
record, and nowhere else under `devteam/`. Findings for the charter, the
protocol or the requirements travel upward in a report (P-17) and the manager
lands them. The board's header names the writing session.

**P-14 — A claim is recoverable, and liveness covers the whole subtree.** The
board's in-flight table names, for every claim: the task, the agent label, the
start time, and the model. A claim is stale only when **no agent under it is
live, its heartbeat is absent or old, and its tree is not moving** — not merely
when the agent the board names has finished. A supervisor awaiting a worker
reports as completed, so the narrow reading declares a working claim dead and
puts a second writer on it, which is the failure P-12 exists to prevent. After a session restart *every* claim is stale, because agent
liveness is only visible within the session that spawned them.

**P-15 — Width is an argument, and the default is one.** The number of
concurrent tasks is a dial the client sets, never a constant. Helper agents
that **write nothing** — verifier, researcher, auditor, reviewer — do not
count against it, and several may run at once provided their dispatches
differ: three auditors on three dimensions collide over nothing, because none
of them can write. Two agents that *do* write never run against overlapping
scope, which is P-12 and is checked before dispatch rather than trusted.

---

## 4. Reports, and why nothing is believed

**P-16 — A report has one shape, in two places.** Every worker's and every
supervisor's final message is a `REPORT` block, and **that role's own block**
is committed as the last entry of the task file's execution record. A
supervisor commits its own block only — its workers have already appended
theirs, and committing the message whole would leave a worker's block last,
so the record check would validate the wrong one. A commit's own hash cannot
appear in a block committed inside it, so `- HEAD <subject>` names it and the
subject is what resolves it afterwards. One shape
means a script can check it (P-32); two places means the record cannot quietly
disagree with what was said.

**P-17 — Reports pass upward verbatim.** A supervisor's report to the manager
**appends every worker report it received, unedited**, and adds its own verdict
above them. A supervisor may judge; it may not paraphrase. This is the entire
mitigation for having a third layer: the manager reads what the worker actually
wrote, not a summary of a summary.

**P-18 — Reported green is not green.** Every report is verified by re-running
its stated check against the **committed** tree, by someone who did not do the
work:

- the **supervisor** verifies each step it dispatched, before accepting it;
- the **project manager** verifies the finished task independently, with a
  fresh verifier agent, before anything moves on the board.

Two verifications, at two layers, by parties with no stake in the result. This
is the most important rule in this file. An agent that has just spent an hour
on a task is the worst possible judge of whether it worked.

**P-19 — The verifier re-runs the exact command and compares the exact
output.** Not a similar command, not a summary — the literal command string
from the report, and a byte comparison of its summary line. A verifier that
re-derives what to run has become a second implementer.

**P-20 — A failing check is never retried into success.** A red result stops
the task and is reported. Re-running until it passes converts a real,
intermittent defect into a hidden one, and every timing-shaped bug looks like
flakiness first.

---

## 5. Decisions, questions and escalation

**P-20b — A project states what wins when two goods conflict, and every
trade-off cites it.** The charter carries a priority order — `safety >
correctness > performance` is the common one. It exists because these conflicts
are constant, individually reasonable, and settled differently by different
people on different days, which is how a system ends up fast and unsafe with
nobody having decided that. A decision that trades one priority for another
**names which it sacrificed and cites the order**; a decision that sacrifices
the highest priority is not a trade-off, it is a `CHARTER` question (P-26).

Where an audit dimension corresponds to a priority, **its findings outrank the
others in the same ordering.** A safety finding is not one voice among four.

**P-20c — Two attempts, then escalate — and the third attempt belongs to
whoever answers.** A supervisor dispatches a step, and on failure re-dispatches
once. After that it escalates rather than trying again, because a third attempt
is how an afternoon disappears into something the client could have settled in
ten seconds.

**This is not P-20 and must not be cited as it.** P-20 forbids re-running a red
*check* until it goes green, which hides intermittent defects. This governs
*attempts at a step*, and the two were conflated in one citation for long
enough to make a real decision look impossible.

**What distinguishes a forbidden repeat from permitted new work is evidence,
not labelling.** A third attempt is forbidden when you do not know why the last
one failed — repetition in hope. Work dispatched *after* an escalation, on
authority from whoever answered it, and identified by something measured since,
is the outcome of the rule rather than an evasion of it. The test is simple and
hard to fake: **can you state what changed, and did you observe it?** If the
only new thing is willingness to try again, it is the forbidden kind.

**P-21 — Every decision records the alternatives declined, and why they lost.**
`devteam/DECISIONS.md` holds `D-n` entries. The alternatives are exactly what a
later reader — human or agent — will propose, and a decision that does not say
why they lost will be re-litigated every time someone fresh arrives.

**P-22 — A decision cited must be declared, and a decision declared must be
cited.** Both halves are checked mechanically (P-35). The second half is the
valuable one: a declared-but-uncited decision is almost always a requirement or
a specification that states a rule and forgot to attribute it.

**P-23 — A settled decision is superseded, never rewritten.** The new decision
gets a new number and says what it supersedes and why. The old text stays,
dated, because it records what was true when it was made — and *how an error
survived* is itself the lesson.

**P-24 — An answered question is struck through with the decision number that
answered it, never deleted.** `devteam/QUESTIONS.md` is the record of how the
answers were reached, not just a to-do list that empties.

**P-25 — An escalation carries a recommendation, not a menu.** Whoever raises
a question has the context; spending it once, on a recommendation backed by
evidence, is what makes the handoff cheap. "Which database should we use?" is
an abdication. "Postgres, because R-12 needs transactional reads and the
research digest dated 2026-09-01 shows SQLite's writer lock fails the
concurrency figure in the charter — SQLite if the deployment target changes to
single-node" is a question the client can answer in five seconds.

**P-26 — Every escalation is classified, and the class decides whether the
loop may proceed.**

| Class | Examples | Behaviour |
|---|---|---|
| `IRREVERSIBLE` | spends money, deletes data, publishes outward, sends mail, picks a licence, names a public package, changes a released API | **always blocks.** Never auto-decided, at any timeout |
| `CHARTER` | changes what is being built, what "done" means, or what is out of scope | **always blocks.** P-2 |
| `REVERSIBLE` | a library choice, a module layout, a naming convention, a test framework — anything a later commit can undo cheaply | goes on the table with its recommendation; if unanswered when the window expires, the manager **proceeds on the recommendation** |

**P-27 — A reversible question that proceeds unreviewed is recorded as such,
and resurfaces.** The record says `proceeded unreviewed`, the decision entry
says the client never saw it, and **every such decision is listed at the next
checkpoint** for cheap confirmation or reversal. Autonomy is bought by making
the unreviewed set visible, not by pretending it is empty.

**P-27b — A role that can stop owns the record of having stopped.** Whoever
reports a stopping status sets the state that says so, before reporting, while
it still knows why. A checklist that covers only the paths which *complete* is
the ordinary shape of a checklist and the ordinary way a state ends up owned by
nobody — and the cost is specific: a stopped task whose title still reads
`RUNNING` is treated as live by every check and guard that reads it, with no
agent working and nothing to police. Nobody downstream can repair it, because
by then the party that knew has ended.

**P-28 — A stop stops its own task and nothing else.** A blocked task does not
idle the pipeline; the manager moves to the next task whose dependencies are
met. Only when no task can proceed does the loop end its turn.

**P-29 — Questions are batched.** The batch is sent when every running task is
stopped, when the table holds three, or when the oldest unanswered item reaches
the configured window — whichever comes first. Interrupting a client once with
three questions costs far less than three interruptions.

---

## 6. Checkpoints and audit

**P-30 — A checkpoint diffs the built thing against the charter and produces a
written verdict.** Not a status update — a verdict, one of `ON-COURSE`,
`DRIFTED` or `BLOCKED`, filed in `devteam/checkpoints/`, answering: does what
exists still satisfy every charter goal; what diverged and was the divergence
decided or accidental; which reversible decisions proceeded unreviewed; what it
cost against estimate. `DRIFTED` always goes to the client.

**P-31 — The audit precedes the close, and the auditor cannot write.** Before a
task or a milestone closes, an auditor reports findings without fixing any of
them — its agent definition genuinely has no write tools. An auditor that fixes
can hide what it changed, and its report stops being evidence. Findings are
triaged by a worker afterwards, under the ordinary discipline, in a commit that
says what it is.

**P-32 — An audit is adversarial, not confirmatory.** The question is never
"does this look right" — it will. The question is **"what would have to be true
for this to be wrong, and is it?"**

---

## 7. Environment, checks and research

**P-33 — The environment is pinned, and the pin is recorded.** Before any work
is dispatched, the manager records the exact toolchain the project builds
against — interpreter and compiler versions, lockfile hashes, container
digests, whatever the project actually depends on — into the board header and
`devteam/.run/env/`. Every worker is given the pin. **It is never re-pinned
while a claim is in flight**, because a result that cannot be attributed to a
known environment is not a result.

**P-34 — Facts have one home.** Skills carry procedure and pointers, never
content. The rules live here; the requirements live in `REQUIREMENTS.md`; the
decisions live in `DECISIONS.md`. A skill that copied any of them would be a
second home for one fact, and the copy is the one that goes stale.

**P-35 — The checks are scripts, and a check that has never failed has not
been shown to work.** Everything this protocol calls checkable — the
traceability diff (P-4), the decision citations (P-22), the report blocks
(P-16), leaked paths and credentials — is a script with an exit code, run
before a commit and again by the verifier, never a careful reading. And every
one of them ships a **negative control** beside it that plants one fault per
finding class and requires exactly that class back. **More than a third of a
guard's control cases are false-positive controls**, because a guard that
refuses legitimate work gets disabled by whoever it obstructs — which is
strictly worse than no guard at all.

**P-36 — Research has a shape.** One fetch may be inline; more is a request to
the researcher agent, whose context is disposable and whose caller's is not. A
digest is dated, cites a **primary** source, and is filed and cited by the
requester — the researcher never writes into the project. A claim that cites
only another document in this project is not verified.

**P-37 — External facts carry a checked date, and go stale.**
`devteam/research/CURRENCY.md` holds one row per external dependency the plan
names — a standard, a data release, an upstream version — with what is pinned,
when it was last checked, the source, and the decision that pins it. A row
unchecked for six months is stale; a security-relevant digest is stale after
ninety days. **Anything called "current" without a date beside it is an
unverified claim**, because the model's knowledge has a cutoff and the world
does not.

---

## 8. Permissions, models and budget

**P-38 — Permissions are declared, minimal and justified, and the client is
not the operator.** Setup writes `devteam/PERMISSIONS.md`, one entry per
permission with the reason the pipeline needs it, and prepares the matching
allowlist. **The declaration is the client's to approve; applying it to the
session's own settings is the operator's** — the account that will actually
run the commands. Where they are different people, the manager shows the
allowlist and asks the operator, and never treats a client's approval as
authority over a permission set. The point is to ask the client
once, up front, for exactly what the loop needs — no more, so the grant is
reviewable, and no less, so the loop does not stall overnight on a prompt
nobody is there to answer.

**P-39 — A permission the pipeline does not have is a stop, not a workaround.**
An agent that cannot run a command reports it; it does not find another route
to the same effect. The other route is the one nobody reviewed.

**P-40 — Model choice is bounded by the charter and recorded in the report.**
The charter names a floor and a ceiling. Each step declares a complexity class
— `mechanical` for checks and verification, `standard` for implementation and
tests, `deep` for design, audit and interview — and the supervisor picks within
the band. The report records what actually ran, because a result is not
comparable to another result run on a different model.

**P-41 — Budget is tracked per task and compared against estimate.** Tokens and
wall-clock go in every report. The manager compares them to the estimate at
each checkpoint and rebalances. An estimate never compared to a measurement
stays wrong forever.

**P-42 — The record is append-only, and it is the durable output.**
`devteam/RECORD.md` holds one line per event: dispatch, report, verify,
advance, release, escalate, answer, checkpoint, pin, stale claim, rebalance.
The manager composes from it the cross-task picture no single task can see —
which findings recurred, which estimates were wrong and by how much, which
dependencies actually bound. That picture exists only if the record is kept.
