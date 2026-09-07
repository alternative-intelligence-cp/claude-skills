# The protocol — the rules the pipeline runs on

Numbered, normative rules. Every skill, agent and check in this plugin cites
them by number rather than restating them, because **a fact with two homes
drifts** (P-34) and this file is the one home.

Cite as `P-7`. A rule is amended by superseding it with a new number, never by
rewriting its text (P-23) — the old text records what was true when the
decision was made.

Each rule states what to do **and why**. A rule whose reason is not written is
a rule the next reader will litigate.

**A rule earns its place by catching its own author.** Prefer a test somebody
motivated to get around it cannot answer dishonestly without noticing they are
doing so — "can you state what changed, and did you observe it?" works on the
person asking it, where "use your judgement" only ever works on strangers. A
criterion that binds the writer is the only kind that survives being
inconvenient.

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

**P-10b — HOW a file is written is part of the scope mechanism, not a matter of
taste.** The guard judges a write by its target, and it can only see a target
it can read from the tool call or the command text. `Write` and `Edit` are
judged. A shell redirection is judged. **An interpreter heredoc is not** —
`python3 - <<PY` with `Path.write_text` gives the guard nothing to resolve, so
the write is neither refused nor recorded. So inside a devteam project, product
files are written with `Write` or `Edit`, and that is a protocol requirement
rather than a preference.

**This one has an outside cause, which is why it is a rule rather than a
bullet.** A harness may ship an ambient instruction to prefer shell tools,
`sed` and heredocs over `Write` and `Edit` — for perfectly good reasons of its
own, having nothing to do with this pipeline. **Such an instruction silently
disarms the scope guard**, and it does so invisibly: no refusal, no finding,
nothing in any record. It reached two consecutive workers and a supervisor on
one project. Both workers disregarded it, used `Edit`, and reported the
conflict, which is exactly right and was not something their dispatch told them
to do.

So: **the pipeline's write form wins inside a devteam project, and the conflict
is reported rather than silently resolved.** A worker that quietly follows the
ambient instruction leaves no trace that the guard was not watching, and
whoever reads the record afterwards will believe it was.

**The rule is about writes the guard would judge, and only those.** It was
written without that qualifier and was immediately unobeyable by the roles that
mutate most: a verifier and an auditor are given `Read` and `Bash` and **no
`Write` or `Edit` at all** — that is the point of them. Told to use `Write`,
they can comply with nothing. And their mutation work happens in a scratch
directory **outside the repository**, which the guard does not police in the
first place, so there is nothing there for a heredoc to evade.

So: inside the project tree, `Write` or `Edit`. Outside it, any tool, because no
judgement was available either way. Both verifiers that met this used Bash only
outside the repository and said so, rather than deciding the scratchpad was
exempt and not mentioning it — which is how the gap was found rather than
assumed.

**Two hours between writing this rule and a role reporting it could not be
followed.** That is the pairs shape again and this time in a rule written *by*
the person who keeps cataloguing it, which is worth recording rather than
quietly patching: knowing the failure mode does not confer immunity, and the
tell was available — the rule named a tool without checking which roles have it.

The general form is worth stating because it will recur with some other
setting: **this design's coverage can depend on an external variable nobody
inside it can see.** When a rule here assumes a mechanism is watching, say what
would make it stop watching — and prefer the arrangement where the failure is
loud.

**P-10c supersedes P-10b for a worker inside a sandbox** (P-43). Inside an
overlay the write form is free — `Write`, `Edit`, a redirect, a heredoc, an
interpreter — because nothing judges it and nothing needs to: every write lands
in that worker's own upper layer and reaches the host only through a promotion
that diffs the paths the commits touched against the task's declared scope. The
mechanism no longer depends on the guard being able to *read* the write, so the
form no longer matters.

**P-10b's text stands unedited and still governs the host** — the manager, the
supervisors, and every actor on a project whose charter says
`Containment: guard-only`. Keep its paragraph on the ambient instruction in
view when reading this one: it is the clearest statement in this file that
coverage can rest on an external variable nobody inside the run can see, and
P-43 has exactly that shape too, with the kernel in the variable's place.

**P-43 — A worker's writes land in a sandbox, and reach the host only through
promotion.** Under `Containment: structural` a worker is a headless process
inside a user-namespace overlay: the repository is mounted copy-on-write at its
own absolute path, its `.git` with it, and the whole of the rest of the
filesystem is read-only. Nothing it writes — a file, the index, a ref, a
rewritten commit — exists outside its own upper layer until a supervisor
promotes it.

*What this contains*, and each of these is a measured failure the guard could
not close: the working tree (F-80, the manager used the unjudged heredoc form
for a whole run; F-121, the refusal message cannot reach the case that matters),
**the index** (F-17, a `git add -A` stole a worker's commit; F-66, "stage
explicit files" defeated because somebody else did the staging), and **the
history** (F-71, a path-based guard structurally cannot see a rewrite; F-73 and
F-81, two independent instances of the amend trap; the worker's half of F-135).
The index and the history are the expensive class and the reason the mechanism
is an overlay rather than a bind-mount allow-list.

*What it does not contain, stated in the rule rather than a footnote:*

- **The network.** The worker's namespace is shared, because the model API must
  be reachable. A worker can therefore reach the network — it could exfiltrate,
  or install a package into its own overlay. What is made impossible instead is
  *outward git*, and structurally rather than by a rule: no `SSH_AUTH_SOCK`, no
  `~/.ssh`, no `~/.gitconfig`, no `gh` configuration and no token survive the
  cleared environment, so `git push` has nothing to authenticate with. **The
  trigger for closing this is a worker observed contacting anything but the
  model API, or a charter that marks the project sensitive.**
- **The manager and the supervisors.** Both stay host-side and share one index
  and one `HEAD`. F-129 and the manager–supervisor half of F-135 are theirs and
  are **not** closed by this rule; what holds them is what held them before —
  the pathspec commits their skills mandate, and P-12b's history refusal, which
  is why P-12c below keeps it in force on the host.
- **A `guard-only` project.** The mechanism is Linux user namespaces. Where the
  probe cannot get them the charter says `guard-only`, this rule does not
  apply, and P-10b is the whole of the coverage.

*Control:* `test_sandbox.py`, and `sandbox_probe.py` is what decides which of
the two a project gets.

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

**P-12b — History is shared, and no scope covers it.** *(Enforced: the guard
refuses these at the moment they are typed, not at the moment they are read.)* Declared scopes divide
the *working tree*. They do not divide the branch, the index or `HEAD`, which
every task in flight shares, and so **any git operation that rewrites or
discards existing history is forbidden while width is greater than one** —
`--amend`, `rebase`, `reset --hard`, `checkout` of a tracked path, `stash`.
Each of them acts on whatever `HEAD` is at the instant it runs, and at width
greater than one `HEAD` is not yours: it is whichever task committed most
recently. A worker did exactly this, ran `git commit --amend` against what it
believed was its own commit, and rewrote a concurrent task's commit — merging
its report text into that task's subject and changing its hash underneath it.
To correct a commit, **add another one**. If a rewrite has already happened,
recover with `git reset --soft` to the original commit from `git reflog`, never
`--hard`: soft leaves the index and working tree untouched, and the tree holds
other tasks' uncommitted work.

**P-12c supersedes P-12b for a worker inside a sandbox** (P-43). **History is
shared at promotion, not during work.** Inside an overlay a worker has its own
`.git`, so `--amend`, `reset`, `rebase` and `stash` act on its own copy and
nobody else's `HEAD` is reachable to rewrite. Those operations are therefore
**permitted inside, above the base commit the sandbox recorded at `open`** — the
thing P-12b exists to prevent cannot happen there. **A rewrite at or below the
base is refused by the promotion gate**, because that is the history the worker
shares with the host after all, and rewriting it is the original failure
arriving one layer down.

**On the host, P-12b's prohibition stands unchanged and unedited**, for every
host-side actor — the manager, every supervisor, and every actor on a
`guard-only` project — and the guard still enforces it at the moment of typing.

This **narrows** `CONSOLIDATION.md` item 8b, the deferred narrow
unscoped-commit refusal: a worker's unscoped commit inside its overlay can only
take that worker's own index, so the case shrinks to the host-side actors, whose
skills already mandate pathspec commits. **Its trigger is unchanged** — an
unscoped host-side commit that actually carries another party's staged work —
and the evidence for building it still does not exist.

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

**P-14b — Liveness has a fourth signal, and under `structural` it is the only
one that can see a worker at all.** A headless worker inside a sandbox is not an
`Agent`-tool subagent, so `ListAgents` cannot see it — that is L-2's accepted
cost, not a defect. The harness therefore writes
`devteam/.run/locks/<TASK>.sandbox` at dispatch and **rewrites it at exit,
never deleting it**, for the reason the heartbeats are never deleted: an absent
file and a file nobody has written read the same, and recovery has to tell *no
worker ran* from *a worker ran and we lost it*. The line carries the task, the
step, the sandbox id, the pid, the times, and the **sandbox root as an absolute
path** — the root is on the line so a reader never has to resolve a
machine-local environment variable the way the writer did, which would be a
second home for one path.

Read it **after** the three signals P-14 names, and it has two readings:

- **a live pid** under a claim whose supervisor is gone is a worker still
  writing its overlay — the claim is working, **not** stale;
- **a dead pid with a non-empty upper layer** is work to inspect with
  `close --keep`, never to discard.

After a session restart `--die-with-parent` has already killed every worker, so
every line reads `exited` or names a dead pid. That is P-14's "every claim is
stale after a restart" with a mechanism a reader can see, rather than a
statement they have to take.

**P-44 — Promotion is serialised, gated by the declared scope, and never
automatic.** Nothing a worker produces reaches the host because the worker
finished. A supervisor promotes it, under a lock so two promotions cannot
interleave, and the gate diffs the paths its commits touched against the task's
`Scope.` — the same declared list every other check here reads, because a diff
of two declared lists is the only kind of check that has ever worked in this
project (P-4).

**An uncommitted remainder is evidence, not work.** A worker that leaves changes
uncommitted has left something the gate cannot attribute to a step, so promotion
refuses rather than guessing. The remainder is captured and named so it can be
read; it is never applied.

**Cite a promoted commit by its subject, never by its hash.** Promotion is a
cherry-pick: the host `HEAD` has usually moved since the sandbox opened, so
every hash the worker reported is rewritten on the way in. A report citing hashes
is a report whose citations are wrong the moment they are true.

*Control:* `test_sandbox.py`; the finding classes are named in `sandbox.py`'s
gate and, from 0.2.6, each against the rule it enforces.

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

**P-17b — A relayed diagnosis is not a measurement, and must not be dressed as
one.** P-17 protects a report's *text*; this protects its *status*. When you
pass a subordinate's finding upward in your own words — to the client, or to
whoever maintains the tooling — say which parts you measured yourself and which
you are forwarding. The failure is not dishonesty; it is that a claim loses its
provenance in one hop and arrives looking like evidence.

**A wrong diagnosis pointing at a plausible fix is worse than no diagnosis**,
because the recipient acts on it. A verifier reported that a refused write had
been "to a path outside the repository entirely"; it was in-tree. Relayed
without measurement, that account would have sent the tooling's author hunting
for an exemption that already existed — and the nearest one to hand was the
blanket out-of-tree exemption the same message warned would make the guard stop
meaning anything.

And the tell was in the report itself: **an agent telling you it worked from
weaker evidence is the strongest available signal to check the rest of its
account, not the weakest.** That report opened by saying it could not build the
mutation. A disclosure of one limitation is a reason to re-read everything
around it, not a reason to trust the remainder more for having been honest
about the first part.

**P-17c — A measurement you took is not a conclusion you remember.** P-17b
covers a claim you are passing on. This covers the harder one: a number **you
produced yourself**, recorded, and thereafter reasoned about from memory of what
it meant rather than from the figures.

**When somebody generalises about work you did, re-read the numbers, not your
summary of them.** A generalisation is a claim about what your data means, so it
is exactly the input that should send you back to the data — and it is exactly
the input that instead feels like something to agree or disagree with.

Measured: a manager had run two candidate checks and recorded the figures — one
real finding in fourteen for the first, two in five for the second. Hours later
it agreed across two messages with a general account of *why* checks work that
its own first candidate refutes. Not carelessness: in the same period it
measured two candidates before proposing either, re-derived an estimate model
rather than taking a supervisor's, and probed a guard rather than trusting a
report. What it did not do was re-open a measurement it had already taken. The
failure does not feel like accepting somebody's word. **It feels like
remembering.**

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

**P-35b — A probe you build to answer one question is an instrument, and it
gets a case whose answer you already know.** P-35 governs the checks that ship.
It has never governed the throwaway script written to investigate a finding —
and **seven of this project's instrument failures were exactly those**, three
of them built while investigating somebody else's report, by people who had
just been thinking hard about instrument blindness.

Two on the same day, on the same question, are the pattern in miniature: one
probe read the exit code of a guard that denies via JSON at exit 0, so every
case came back "allowed" — including one already proved refused. The other
drove the same guard with a payload carrying **no session id**, the field the
entire judgement keys on, so every scope verdict was meaningless. Neither
errored. Both produced clean, readable, confident output.

**Both are the same failure: an instrument that returns an answer for a
question it was never wired to ask.** It cannot be caught by reading the
output, because the output looks exactly like the real thing. It is caught in
one step, before any of the interesting cases: **feed it something whose answer
you already know, and check you get that answer back.** One known-deny and one
known-allow would have caught both in seconds.

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

**P-38b supersedes P-38 in one respect: the grant has two halves, and only one
of them is a list.** A permission here is either *outward-facing* or
*filesystem-shaped*, and P-38 treated them alike because before P-43 there was
only one way to withhold anything.

- **Outward-facing** — `git push`, `gh`, `sudo`, `pip install`, `uv add`.
  Withheld **by name**, on the host by the allowlist and inside a sandbox by
  `--disallowedTools`. These are the ones whose consequences outlive the
  sandbox, so structure cannot help and a name is the whole mechanism.
- **Filesystem-shaped** — `rm`, `chmod`, `truncate`, `python3 -c`, a redirect,
  an interpreter. Under `Containment: structural` these are **granted inside**,
  because inside an overlay they can harm nothing that survives it, and the
  promotion gate judges the result rather than the command. Under `guard-only`
  they stay exactly as P-38 had them.

*Why the split, and it is four measured failures rather than a preference:*
F-30, F-64, F-76 and F-100 were each a command withheld for the guard's sake
that cost a verification chain — most sharply F-100, where a verifier had no
sanctioned place to build the mutation its own job is defined by, concluded
mutation was unavailable, and downgraded an independent re-measurement to an
independent reading. A grant tight enough to make the guard's job easy was
tight enough to stop the checking.

**The inside list has one home and is derived, never written twice.** It comes
from the role's own `agents/<role>.md` `tools:` line — the only enforced
restriction the 0.1 design had — minus the outward set. F-6, F-24 and F-30 were
each a grant and a rule disagreeing; a second list would be the fourth.

**P-39 — A permission the pipeline does not have is a stop, not a workaround.**
An agent that cannot run a command reports it; it does not find another route
to the same effect. The other route is the one nobody reviewed.

**P-40 — Model choice is bounded by the charter and recorded in the report.**
The charter names a floor and a ceiling. Each step declares a complexity class
— `mechanical` for checks and verification, `standard` for implementation and
tests, `deep` for design, audit and interview — and the supervisor picks within
the band. The report records what actually ran, because a result is not
comparable to another result run on a different model.

**P-41 — Budget is tracked per task, and estimates come from a stated model
rather than a number.** Tokens and wall-clock go in every report. The manager
compares them to the estimate at each checkpoint and rebalances; an estimate
never compared to a measurement stays wrong forever.

**Write the model down, not only the figure** — "steps × per-step-unit +
per-task overhead", with the numbers you used. A bare estimate can only be
right or wrong; a model can be *corrected*, and the next measurement then fixes
every remaining estimate at once instead of one at a time. It also makes the
estimate falsifiable in a useful direction: if the next task comes in at a
quarter of its figure, the fixed overhead is smaller than you thought and every
other number is wrong the same way.

**Estimate from what the work actually costs, not from the size of the
artifact.** The first measured task in this system came in at six times its
estimate because the estimate was built from the code to be written, which is
the smallest term. The cost is reading the charter, the requirements and the
decisions; dispatching; verifying independently; and writing the report.

**And say what your sample is.** A per-step figure drawn from one task is drawn
from one task, and a first task is usually the worst case.

**P-42 — The record is append-only, and it is the durable output.**
`devteam/RECORD.md` holds one line per event: dispatch, report, verify,
advance, release, escalate, answer, checkpoint, pin, stale claim, rebalance.
The manager composes from it the cross-task picture no single task can see —
which findings recurred, which estimates were wrong and by how much, which
dependencies actually bound. That picture exists only if the record is kept.
