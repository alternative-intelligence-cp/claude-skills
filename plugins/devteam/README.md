# devteam — a development pipeline that leaves evidence

Takes a project from a client's idea to a working product, modelling how a real
development organisation actually works: a written charter signed before
building starts, requirements numbered and traced to the tasks and tests that
discharge them, supervisors who verify the workers they dispatch, and a
manager who verifies the supervisors.

It runs unattended for hours. It stops for exactly three things: a decision
that cannot be undone, a change to what is being built, and a checkpoint that
finds the work has drifted from the charter.

> **Status: run once end to end, then rebuilt around what that run
> exposed.** On 2026-09-04/05 the pipeline took one project — a CSV-to-JSON
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
> **What that has not yet done is run a whole project.** Every mechanism
> 0.2 built is proved by controls and by one end-to-end walk on a throwaway
> project; none has been through a second real cycle. Rows stay under
> [Known problems](#known-problems) until the fix has been *shown to work*,
> not merely built — so several rows below name a mechanism that shipped
> and say what has not yet measured it.
>
> Version 0.2.0. Fifteen skills, nine agents, 48 numbered rules, and 551
> control cases green across 13 controls, 251 of them false-positive
> controls (46%) — `python3 scripts/run_controls.py`, read from the tree,
> not carried from memory.

## Read these

| Document | What it is |
|---|---|
| [`docs/FOR-NEW-USERS.md`](docs/FOR-NEW-USERS.md) | **start here if you have been asked to run real work through this** — what it does, what it costs, and when to stop using it |
| [`docs/REPORTING-PROBLEMS.md`](docs/REPORTING-PROBLEMS.md) | the shape a finding should come back in, and the three kinds — including the one we have never received |
| [`DESIGN.md`](DESIGN.md) | **the architecture** — the three layers and why, the roster of agents and skills, every artifact the pipeline writes, the lifecycle and its five client gates, the two loops, the contracts that cross layer boundaries, the checks, the guard, the escalation policy, and what this deliberately is not |
| [`PROTOCOL.md`](PROTOCOL.md) | **the rules** — 48 numbered, normative rules that every skill and agent cites by number instead of restating. Each says what to do *and why* |
| [`docs/BRIEF.md`](docs/BRIEF.md) | the author's original statement of the idea, preserved, with the four deliberate departures noted |
| [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) | what the first run left to do — nine items, each deferred deliberately, each with the measurement behind it |
| [`meta/roadmap/`](meta/roadmap/README.md) | **what comes next** — `0.2/` is what remains, `done/` is what happened, each subcycle a file a fresh session can implement without the planning conversation |

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
the fix has been shown to work, not that it has been built. Cycle 0.2 shipped
a mechanism for most of these; a mechanism proved only by its own controls
has not yet met a project, so those rows stay, with the Plan column naming
what shipped and what has still to measure it. Every row was measured on the
first run; the evidence column says where.

| Problem | Evidence | Plan |
|---|---|---|
| **The write guard judges a write by parsing command text, and the world is wider than its frame.** Two measured holes: an interpreter heredoc (`python3 - <<PY` … `open(path, 'w')`) writes unjudged, and git history is a write with no path — at width above one, a worker's `git commit --amend` rewrote a *concurrent* task's commit. `check_scope` reports both after the fact; nothing prevents them | [`DESIGN.md`](DESIGN.md) §8, §20; [`PROTOCOL.md`](PROTOCOL.md) P-10b, P-12b | **closed for a worker on Linux, open elsewhere.** Structure replaces classification: a per-worker copy-on-write overlay in which neither the host tree nor anyone else's index exists, and a promotion gate that diffs what the commits touched against the declared scope — [`PROTOCOL.md`](PROTOCOL.md) P-43, P-44, P-10c, P-12c. The manager and the supervisors stay host-side and are still held by the guard; a `guard-only` machine keeps both holes and says so in its charter |
| **The manager never resets.** Every other role gets a fresh context; the manager runs for the whole project and, by the rule that makes it trustworthy, reads every worker report verbatim — roughly 230,000 tokens of task files on one run, plus a record, a decision log and a question log it re-reads. It cannot measure its own context, and compaction is a copy of a copy | [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) §1 | **shipped in 0.2.5**: rotation at every checkpoint, driven from outside the session, the incoming manager reading durable state and logging every question the files could not answer as a defect. It has never rotated a real project — 0.2.9 is the first run that will |
| **Two mechanisms have never produced output.** `/devteam:iterate` has never run. The path where a reversible question proceeds on its recommendation and resurfaces for review (P-27) has never fired, because the run's client answered all thirty questions within the hour. A mechanism that has never fired has not been shown to work | the run's final review, `C-3` §3, in the private record | a second run on a **real project with the owner as its client**, one-hour escalation window — roadmap 0.2.9 |
| **Estimates are biased, not noisy.** Ten of ten tasks over their estimate, 1.78× in total, after two upward revisions; the overruns were on *rounds* — steps re-run after a defect — which the model does not carry | final review `C-3` §4; findings F-101, F-102 | **shipped in 0.2.6**: the v3 estimate model carries a rounds term rather than a larger constant. Its bias is unmeasured — one run's constants cannot validate the model fitted to them, and 0.2.9 recomputes it |
| **A project learns forward only.** A signed decision made one of the charter's "done means" conditions undischargeable; the charter was amended three times afterwards and nobody re-read the condition. That is why the final review was `DRIFTED`. Nothing mechanical could see it | `C-3` §2; [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) §4 | **shipped in 0.2.6**: an amendment re-affirms the whole charter by enumeration, and `amendment-omits-condition` diffs that list against it. It has never run against a real charter; 0.2.9 §3.1 is the first |
| **The audit-finding namespace is unseen by design.** `COR-n`, `SEC-n`, `HYG-n` were given three-letter prefixes so the citation scanner could not mistake them for citations — which is the same fact as the scanner being unable to check them. Eleven of fifteen findings on one project were filed and never dispositioned before a field was added to watch them | [`templates/FORMATS.md`](templates/FORMATS.md) §namespace; CONSOLIDATION §7 | **shipped in 0.2.6**: `check_refs` resolves the reserved three-letter prefixes, and `open-finding-at-close` makes an audit finding still `open` at its task's close a finding. The disposition half has never been exercised on a live audit |
| **Rules that are each right alone and cannot both hold.** Nine instances so far, every one found by a worker hitting it under time pressure, because a worker is the only party required to satisfy every rule at the same moment. Nobody has read the rule set *looking* for the shape | [`DESIGN.md`](DESIGN.md) §20 "the shape that has cost the most"; CONSOLIDATION §2 | **swept in 0.2.7**: [`docs/PAIRS.md`](docs/PAIRS.md) — 17 moments, 21 pairs, the nine as calibration. Most are resolved or resolved structurally; **rows 18 and 19 are open and each needs a measurement rather than a decision**, and 0.2.9 is where row 18 becomes observable |
| **The evidence is one run, on a fixture, with an AI playing the client.** The client was unusually available — eighteen blocking stops in fifteen hours, answered in minutes with the domain loaded. A human client would have been the bottleneck. This is a limit on what the run proves, not a defect | [`../../HANDOFF.md`](../../HANDOFF.md) §4 | a second run whose client is the owner himself, so the limit below is removed rather than simulated — roadmap 0.2.9 |
| **The planned containment is Linux-only.** It rests on unprivileged user namespaces and `bubblewrap`; on macOS, Windows, or a Linux host without them, the pipeline will run in a `guard-only` mode that keeps the first row's holes open and says so | roadmap [`0.2/README.md`](meta/roadmap/0.2/README.md) §7 | **shipped in 0.2.4**: `setup` probes for user namespaces and `bwrap` and writes `Containment: structural` or `guard-only` into the charter the client signs. This row is a permanent limitation of the mechanism, not a defect awaiting a fix |
| **It is heavy, on purpose, and wrong for small work.** One project produced 1,865 lines of design documents for a tool of about 200 lines of code — the pipeline run below its threshold deliberately, to find out how it breaks. It is aimed at work where being wrong is expensive, and it will outweigh anything simple. Of some 150 findings, exactly one has made it simpler, and it came from a team that declined to use it | [`DESIGN.md`](DESIGN.md) §21; [`docs/FOR-NEW-USERS.md`](docs/FOR-NEW-USERS.md) | not on the list to fix. 0.2.7 applied the test that had never been applied — [`docs/CEREMONY.md`](docs/CEREMONY.md) walks all 87 numbered steps against *does this step only work for an operator who already understands why it matters*. The question of which steps buy nothing on **any** project still needs people with real deliverables, and no run can answer it |

## What comes next

Cycle 0.2 is [`meta/roadmap/0.2/`](meta/roadmap/0.2/README.md), and it is
nearly through. `ls meta/roadmap/done/` is what happened; `ls
meta/roadmap/0.2/` is what remains.

**Done:** the probes, the sandbox harness and its controls, extraction and
the promotion gate, the worker running headless inside, the pipeline wired
onto it, manager rotation, every finding class named against its rule, the
two sweeps, and this release.

**Remaining, and the order matters:**

- **0.2.9 — the second run.** **Two** cycles on a small real project of the
  owner's, built from nothing, with **the owner as its client** — cycle 1
  builds it, he uses it, cycle 2 runs `/devteam:iterate`, which only runs on a
  finished cycle. Workers sandboxed at width 2–3, rotation at a checkpoint, a
  one-hour escalation window so P-27 fires against a client who is genuinely
  asleep rather than performing lateness, and a budget ceiling that blocks
  rather than warns. **This is what the cycle was for.** Every mechanism 0.2
  built is currently proved by its own controls and by one walk on a throwaway
  project; 0.2.9 is where they meet a project.
  **Retargeted 2026-09-07, before it ran.** It was cycle 2 on the
  `.internal/scratch/` fixture with a session briefed to play a slow client,
  until the owner was asked for the positions the plan required and could not
  supply them — he did not choose that project, plan its decisions, or know
  what was in scope. **The fixture has no principal**, so every interview
  question would have been answered by an agent on behalf of an agent.
- **0.2.10 — the root-tree allowlist.** Small and independent of everything
  else: a declared table of what the repository root holds, a check that
  diffs the tree against it, and a hook that refuses a stray write at the
  root.

**And a decision that waits on 0.2.9 rather than on the roadmap finishing.**
This repository is not itself a devteam project — it has no `devteam/`
directory, so none of the project checks run on the thing that builds them.
That is a stated judgement, not an oversight: the pipeline did not exist
when the repository started, and applying it to itself while its own plans
were still surprising it would have cost more than it saved. The condition
for revisiting is **0.2.9 completing and being judged a good enough
experiment**, not 0.2.9 completing. [`docs/PAIRS.md`](docs/PAIRS.md) row 20
carries the reasoning, so a later reader who finds the roadmap finished asks
whether the experiment passed rather than inferring readiness from the
listing.

Each subcycle file is written for a session that has none of the planning
conversation.

## Licence

Apache 2.0, matching the repository. See [`../../LICENSE`](../../LICENSE).
