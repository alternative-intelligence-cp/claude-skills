# devteam — a development pipeline that leaves evidence

Takes a project from a client's idea to a working product, modelling how a real
development organisation actually works: a written charter signed before
building starts, requirements numbered and traced to the tasks and tests that
discharge them, supervisors who verify the workers they dispatch, and a
manager who verifies the supervisors.

It runs unattended for hours. It stops for exactly three things: a decision
that cannot be undone, a change to what is being built, and a checkpoint that
finds the work has drifted from the charter.

> **Status: run twice — once on a test fixture, once on a real project — and
> being rebuilt around what the second run measured.** On 2026-09-04/05 the
> pipeline took one project — a CSV-to-JSON
> tool built as a test fixture, with no users by design — from an
> underspecified paragraph to a final review: thirteen of thirteen
> requirements discharged, 531 tests green, every mechanical check clean,
> and a verdict of `DRIFTED` for a reason no check could see. It produced
> 149 findings, roughly five in six of them defects in this pipeline rather
> than in the fixture.
>
> **0.2.0 answers the largest of them: a worker's writes are now made
> impossible rather than refused.** On Linux each worker runs headless
> inside a private copy-on-write view of the repository, and its commits
> reach the host only through a promotion gate that diffs what they touched
> against what its task declared. The guard stays in front of that as early
> warning, not as the thing standing between a mistake and the repository.
>
> **Then it ran a real project, and was stopped.** From 2026-09-10 to
> 2026-09-19 the pipeline built `pricelog`, a small tool of the owner's,
> through two cycles with the owner as its client: nineteen tasks, fifteen
> manager rotations, `/devteam:iterate` and the unreviewed-decision path both
> fired, and containment held under heavy mutation. The owner stopped it at
> its second cycle's third blocking stop, and on 2026-09-23 judged it **not
> yet** a good enough experiment to trust the pipeline with real work
> ([`docs/PAIRS.md`](docs/PAIRS.md) row 20). Its 142 findings are sorted in
> [`meta/v3-findings-register-2026-09-19.md`](meta/v3-findings-register-2026-09-19.md),
> and the [Known problems](#known-problems) below were revised from them.
> Rows stay there until the fix has been *shown to work*, not merely built.
>
> Version **0.2.0-rc**. Fifteen skills, nine agents, 48 numbered rules, and
> 592 control cases green across 15 controls, 262 of them false-positive
> controls (44%) — `python3 scripts/run_controls.py`, read from the tree,
> not carried from memory.
>
> **`-rc`, and the suffix is load-bearing.** Every mechanism here ships with
> negative controls, and the one real run found checks that reported clean
> without having looked. The tag stays `-rc` until a run the owner judges
> sufficient says otherwise; [cycle 0.3](meta/roadmap/0.3/README.md) is the
> fix and that run.

## Read these

| Document | What it is |
|---|---|
| [`docs/FOR-NEW-USERS.md`](docs/FOR-NEW-USERS.md) | **start here if you have been asked to run real work through this** — what it does, what it costs, and when to stop using it |
| [`docs/REPORTING-PROBLEMS.md`](docs/REPORTING-PROBLEMS.md) | the shape a finding should come back in, and the three kinds — including the one we have never received |
| [`DESIGN.md`](DESIGN.md) | **the architecture** — the three layers and why, the roster of agents and skills, every artifact the pipeline writes, the lifecycle and its five client gates, the two loops, the contracts that cross layer boundaries, the checks, the guard, the escalation policy, and what this deliberately is not |
| [`PROTOCOL.md`](PROTOCOL.md) | **the rules** — 48 numbered, normative rules that every skill and agent cites by number instead of restating. Each says what to do *and why* |
| [`docs/BRIEF.md`](docs/BRIEF.md) | the author's original statement of the idea, preserved, with the four deliberate departures noted |
| [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) | what the first run left to do — nine items, each deferred deliberately, each with the measurement behind it |
| [`meta/roadmap/`](meta/roadmap/README.md) | **what comes next** — `0.3/` is the cycle in planning, `0.2/` holds the stopped second run, `done/` is what happened, each subcycle a file a fresh session can implement without the planning conversation |

## How it is used

```bash
/devteam:setup           # scaffold devteam/ in your project, agree the permissions
/devteam:onboard         # the interview → CHARTER.md + REQUIREMENTS.md → you sign
/devteam:plan            # requirements → a task graph → you approve
/devteam:run width=2     # the loop. Runs unattended; stops only when it must
/devteam:status          # where is it, at any time
/devteam:resume          # pick up after a crash, a reboot, or a day away
/devteam:iterate         # the next cycle, carrying the last one forward
/devteam:checkpoint      # diff what exists against the charter, on demand
```

### What it needs

The pipeline itself is Python 3 and git. **Structural containment is Linux
only**: it rests on unprivileged user namespaces plus `bubblewrap`, and
`setup` probes for both rather than assuming them.

| The machine has | What you get | Where it is written down |
|---|---|---|
| Linux, unprivileged user namespaces, `bwrap` | `Containment: structural` — per-worker overlays, headless workers, promotion gated by declared scope | the charter, from the probe |
| anything else — macOS, Windows, a hardened Linux | `Containment: guard-only` — the pipeline runs, and the two holes the guard cannot close stay open | the charter, **stated rather than assumed** |

`guard-only` degrades loudly and on purpose: the mode is written into the
charter the client signs, because a containment property believed and absent
is worse than one known to be absent (DESIGN §15).

## The shape

```
CLIENT ── charter, answers, sign-offs
   ▲
   │ batched questions, each with a recommendation and a class
   ▼
PROJECT MANAGER  (main session — the only layer that talks to you)
   │  owns the charter, the task graph, the board, the record
   │  verifies every finished task independently. Writes no code.
   ▼
SUPERVISOR  (one agent per in-flight task, scopes never overlap)
   │  decomposes into steps, dispatches one worker each,
   │  verifies every step before accepting it. Writes no code.
   ▼
WORKERS  implementer · tester · auditor · documenter · reviewer · researcher
        every report passes upward VERBATIM — a supervisor may judge,
        never paraphrase
```

## What makes it different from asking Claude to build something

- **A charter you signed**, that every checkpoint diffs the real work against —
  so scope drift is caught by a scheduled check rather than noticed at the end.
- **Requirements that are testable or they are not requirements**, each traced
  to the task that implements it and the check that proves it. A requirement no
  task covers, and a task no requirement motivates, are both mechanical
  findings.
- **Two independent verifications of every piece of work**, by parties that did
  not do it, re-running the exact command against the committed tree.
- **An auditor that structurally cannot write a file** — no `Write`, no `Edit`
  in its tool list — because an auditor that fixes can hide what it changed.
- **A write that cannot happen, rather than one that is refused.** On Linux each
  worker runs inside a private copy-on-write view of the repository: writing
  outside its task's declared paths, touching git history, or picking up another
  agent's staged work are not *forbidden* to it, they are unavailable, and its
  work reaches the repository only when it is applied deliberately and checked
  against what it said it would touch. A refusal can only catch what it manages
  to recognise; this catches what nobody thought to recognise.
- **A record of what was decided without you**, listed at every checkpoint while
  it is still cheap to reverse.

## Known problems

Stated here so that nobody who finds this repository is surprised by them,
and **removed from this list as each is addressed** — where *addressed* means
the fix has been shown to work, not that it has been built. Every row was
measured on a run — the first, on a fixture, or 0.2.9, on the owner's own
project — and the evidence column says where; F-numbers are 0.2.9's unless a
row says otherwise. **Revised 2026-09-23 from that run's
[findings register](meta/v3-findings-register-2026-09-19.md)**: the Plan column names the
[cycle 0.3](meta/roadmap/0.3/README.md) subcycle meant to remove each row, and a row goes only
when that fix has met a project.

| Problem | Evidence | Plan |
|---|---|---|
| **A check can report clean without having looked.** A check that parsed nothing exits exactly as one that looked and found nothing: in 0.2.9 `check_trace` reported clean having parsed zero goals, `board-drift` matched no rows, untracked files and wrapped fields were invisible, a new task file was invisible until staged, and `check_scope` and `check_report` read a restarted task as though it had never restarted. A permanently red exit code then taught managers to commit over red | [register](meta/v3-findings-register-2026-09-19.md) theme 2, area A6; F-70, F-85, F-131, F-135, F-136 | roadmap [0.3.1 and 0.3.2](meta/roadmap/0.3/README.md): a check never reports clean when it did not look, every check's control plants that case, and a commit gate ships in the plugin |
| **Open items reach no owner.** Items raised by adversaries, workers, auditors and outgoing managers reached no owner, to the end of 0.2.9: an auditor's item needing a client decision was read past by the supervisor and the manager alike, and an audit finding carried into the second cycle went four days without an owner. This row absorbs the audit-namespace row: the check 0.2.6 shipped to watch audit findings could not see any of the run's four gate audits, because they did not use its namespace | [register](meta/v3-findings-register-2026-09-19.md) theme 1, areas A5 and A6; F-99, F-104, F-112, F-139 | roadmap [0.3.3](meta/roadmap/0.3/README.md): one disposition ledger, and a check that fails any landing that leaves an item without an owner, a decision or an expiry |
| **The manager's bookkeeping is done by hand, and fails by hand.** In 0.2.9: six commits in a form the `run` skill forbids, the writer lock refused three times, check exit codes read through pipes, a heartbeat left naming an agent nobody awaited, a draft landed twice, a dispatch sent with no model. None was a failure of judgement, and every fix that held replaced a remembered step with a command | [register](meta/v3-findings-register-2026-09-19.md) theme 3, area A1; F-24, F-26, F-100, F-117 | roadmap [0.3.4](meta/roadmap/0.3/README.md): each recurring act is one command that checks its own preconditions |
| **The budget ceiling cannot see most of what is spent.** In 0.2.9 in-process supervisors, verifiers and auditors spent about 2.7 times the manager's counted tokens, in neither half of the ceiling; every successor's resume sat outside it, growing from 1.8 M to 7.0 M tokens; and the first cycle's manager figure cannot be recovered. The second cycle's ceiling was raised ten times, each raise overtaken before the first item it priced was finished | [register](meta/v3-findings-register-2026-09-19.md) theme 4, area A11; F-33, F-67, F-110, F-116 | roadmap [0.3.0 and 0.3.5](meta/roadmap/0.3/README.md): a meter over every session and in-process agent, reconciled against the owner's usage gauge |
| **Estimates are biased, not noisy, and the bias is adversarial rounds.** On the first run ten of ten tasks overran, 1.78× in total. The model shipped in 0.2.6 carries a term for rounds — steps re-run after a defect — and in 0.2.9 every task still overran but the last: the largest overruns, 4.52×, 5.17× and about 4.6×, were adversarial passes finding real defects, which the model does not price | first run: final review `C-3` §4 and that run's F-101, F-102; 0.2.9: [register](meta/v3-findings-register-2026-09-19.md) themes 4 and 5, area A8 | roadmap [0.3.5](meta/roadmap/0.3/README.md): a term for adversarial rounds and the stops they cause |
| **Rotation works; the handoff leaks.** The manager rotated fifteen times in 0.2.9, every time with its predecessor alive to ask, and the writer lock moved every time. What leaked, to the last rotation: what the client said after the outgoing manager's last write reached no file at all fifteen; work a successor needed kept surfacing outside the tree; an off-cadence rotation parked the loop for four hours beside an idle successor; and three checkpoints passed without a rotation, that one tenure costing 231 M tokens | [register](meta/v3-findings-register-2026-09-19.md) theme 6, area A2; F-21, F-119, F-129, F-134 | roadmap [0.3.6](meta/roadmap/0.3/README.md): a structured handoff record, and rotation after a checkpoint enforced rather than remembered; 0.3.0 probes whether a session can start its own successor |
| **A project learns forward only, and signed text drifts from the code faster than amendments catch it.** On the first run a signed decision made a done-means condition undischargeable and nobody re-read it. 0.2.6 made every amendment re-affirm the whole charter, and at 0.2.9's iteration that held — but the check behind it read past the entry it was checking, a re-affirmation cannot say a condition is in force and currently broken, requirements were edited in place five times against the pipeline's own rule, and one requirement written as a list of cases under a rule that quantifies cost seven blocking stops in one day | first run: `C-3` §2, [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) §4; 0.2.9: [register](meta/v3-findings-register-2026-09-19.md) theme 7, areas A6 and A9; F-36, F-68 | roadmap [0.3.2 and 0.3.9](meta/roadmap/0.3/README.md): the amendment check repaired, and requirements superseded, never edited ([`docs/PAIRS.md`](docs/PAIRS.md) row 18) |
| **Iterate's second half has never run, and a run cannot be stopped early.** `/devteam:iterate` ran once, in 0.2.9, and its mechanical half held. The half that makes an iteration more than an amendment — starting from what using the thing taught — never ran: the owner had not used the tool between cycles, and the skill has no path for that case. P-27 fired four times; its second half, showing those decisions first at the next iteration, has never run. And the protocol has no way to stop a run early, which is how 0.2.9 ended | [register](meta/v3-findings-register-2026-09-19.md) theme 8, area A12; F-141 | roadmap [0.3.10](meta/roadmap/0.3/README.md); the third run, 0.3.14, iterates twice |
| **Width above one contaminates workers.** Each sandbox's lower layer is the live repository, so a host write — the manager's record, another task's promotion — reads through into every open worker's view, and promotion then refuses the worker's step. At width 2 two supervisors contaminated each other's workers, and 0.2.9 dropped to width 1 | [register](meta/v3-findings-register-2026-09-19.md) theme 9, area A4; F-5, F-26, F-31, F-71 | roadmap [0.3.7](meta/roadmap/0.3/README.md): sandboxes frozen at a commit, with `devteam/` read-only inside them |
| **The platform moves under the pin and speaks to agents unasked.** The `claude` CLI updated under live claims, and the environment pin records the version without binding it; MCP server instructions and another plugin's skills reached agents as though they were instructions — three agents name their skills unqualified, so the auditors ran another plugin's audit procedure; and a harness memory heuristic killed workers with over 130 GiB free | [register](meta/v3-findings-register-2026-09-19.md) theme 10, area A14; F-42, F-65, F-69, F-92, F-101, F-102 | roadmap [0.3.7 and 0.3.11](meta/roadmap/0.3/README.md): bind what the pin names; injected instructions declared not to be instructions; every skill name qualified, with a check |
| **The write guard judges a write by parsing command text, and the world is wider than its frame.** Two measured holes: an interpreter heredoc (`python3 - <<PY` … `open(path, 'w')`) writes unjudged, and git history is a write with no path — at width above one, a worker's `git commit --amend` rewrote a *concurrent* task's commit. For a worker on Linux both are now closed by structure, and 0.2.9 measured it: containment held under more than 624 mutations, and a worker's `mktemp -d` landed on the sandbox's own tmpfs. The host-side roles are still held by the guard alone: the manager's heredoc writes under `devteam/` went unjudged (F-3), and the guard matches command text, so it refused harmless commands outside the project (F-6, F-137) | [`DESIGN.md`](DESIGN.md) §8, §20; [`PROTOCOL.md`](PROTOCOL.md) P-10b, P-12b; [register](meta/v3-findings-register-2026-09-19.md) area A7 | **closed for a worker on Linux, and shown working**: a per-worker copy-on-write overlay and a promotion gate that diffs what the commits touched against the declared scope — [`PROTOCOL.md`](PROTOCOL.md) P-43, P-44, P-10c, P-12c. Open for the manager and the supervisors, and on a `guard-only` machine: roadmap [0.3.11](meta/roadmap/0.3/README.md), the guard judging targets rather than command text |
| **Rules that are each right alone and cannot both hold.** Nine instances on the first run, every one found by a worker hitting it under time pressure, because a worker is the only party required to satisfy every rule at the same moment | [`DESIGN.md`](DESIGN.md) §20 "the shape that has cost the most"; CONSOLIDATION §2 | **swept in 0.2.7**: [`docs/PAIRS.md`](docs/PAIRS.md) — 17 moments, 21 pairs, the nine as calibration. Row 18 was decided by the client on 2026-09-23 from 0.2.9's count and is built by roadmap [0.3.9](meta/roadmap/0.3/README.md); row 19 is open; row 20's judgement is made, and it is *not yet* |
| **The evidence is two small runs, both in Python.** The first was a fixture with an AI playing the client — unusually available, eighteen blocking stops in fifteen hours, each answered in minutes. The second, 0.2.9, was the owner's own small project with the owner as its client, and he stopped it after two cycles. Neither was the kind of project the pipeline is for, nor written in the language it is meant for. This is a limit on what the runs prove, not a defect | [`../../HANDOFF.md`](../../HANDOFF.md) §4; [register](meta/v3-findings-register-2026-09-19.md), *The run in numbers* | a third run, in Nitpick, on a project of the owner's — roadmap [0.3.14](meta/roadmap/0.3/README.md) |
| **The planned containment is Linux-only.** It rests on unprivileged user namespaces and `bubblewrap`; on macOS, Windows, or a Linux host without them, the pipeline will run in a `guard-only` mode that keeps the first row's holes open and says so | roadmap [`0.2/README.md`](meta/roadmap/0.2/README.md) §7 | **shipped in 0.2.4**: `setup` probes for user namespaces and `bwrap` and writes `Containment: structural` or `guard-only` into the charter the client signs. This row is a permanent limitation of the mechanism, not a defect awaiting a fix |
| **It is heavy, on purpose, and wrong for small work.** One project produced 1,865 lines of design documents for a tool of about 200 lines of code — the pipeline run below its threshold deliberately, to find out how it breaks. It is aimed at work where being wrong is expensive, and it will outweigh anything simple. Of some 150 findings, exactly one has made it simpler, and it came from a team that declined to use it | [`DESIGN.md`](DESIGN.md) §21; [`docs/FOR-NEW-USERS.md`](docs/FOR-NEW-USERS.md) | not on the list to fix. 0.2.7 applied the test that had never been applied — [`docs/CEREMONY.md`](docs/CEREMONY.md) walks all 87 numbered steps against *does this step only work for an operator who already understands why it matters*. The question of which steps buy nothing on **any** project still needs people with real deliverables, and no run can answer it |

## What comes next

Cycle 0.2 is [`meta/roadmap/0.2/`](meta/roadmap/0.2/README.md), and it is
through. `ls meta/roadmap/done/` is what happened; 0.2.9 stays in
`meta/roadmap/0.2/` because it was stopped rather than finished.

**0.2.9, the second run, was stopped by the owner on 2026-09-19** after both of
its cycles had run on the owner's own project: `/devteam:iterate`, manager rotation and
the unreviewed-decision path all fired, and the run was then read whole. Its
findings are in [0.2.9's Findings](meta/roadmap/0.2/0.2.9.md), and the same
material is sorted for planning in
[`meta/v3-findings-register-2026-09-19.md`](meta/v3-findings-register-2026-09-19.md)
— what worked, what broke by area, and where v3 should start. **0.2.10**, the
root-tree allowlist, is done.

**Next is v3**, planned from that register and from the backlog in
[`meta/v3-liaison-and-roles-2026-09-12.md`](meta/v3-liaison-and-roles-2026-09-12.md).
Its plan is [`meta/roadmap/0.3/`](meta/roadmap/0.3/README.md), approved by
the owner on 2026-09-23: make the pipeline's own evidence trustworthy and
affordable, close the joints the run measured leaking, decide the liaison
layer by a probe, and run a third experiment — a cowsay clone written in
Nitpick. The Known problems table above was revised from the register on the
same day.

**And a decision that waits on a run rather than on the roadmap finishing.**
This repository is not itself a devteam project — it has no `devteam/`
directory, so none of the project checks run on the thing that builds them.
That is a stated judgement, not an oversight: the pipeline did not exist
when the repository started, and applying it to itself while its own plans
were still surprising it would have cost more than it saved. The condition
for revisiting was **0.2.9 completing and being judged a good enough
experiment**, not 0.2.9 completing — and on 2026-09-23 the owner judged it
*not yet*. The condition now waits on cycle 0.3's third run, judged the same
way. [`docs/PAIRS.md`](docs/PAIRS.md) row 20 carries the reasoning, so a
later reader who finds the roadmap finished asks whether the experiment
passed rather than inferring readiness from the listing.

Each subcycle file is written for a session that has none of the planning
conversation.

## Licence

Apache 2.0, matching the repository. See [`../../LICENSE`](../../LICENSE).
