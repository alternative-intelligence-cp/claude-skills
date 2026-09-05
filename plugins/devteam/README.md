# devteam — a development pipeline that leaves evidence

Takes a project from a client's idea to a working product, modelling how a real
development organisation actually works: a written charter signed before
building starts, requirements numbered and traced to the tasks and tests that
discharge them, supervisors who verify the workers they dispatch, and a
manager who verifies the supervisors.

It runs unattended for hours. It stops for exactly three things: a decision
that cannot be undone, a change to what is being built, and a checkpoint that
finds the work has drifted from the charter.

> **Status: run once, end to end, and found wanting in known ways.** On
> 2026-09-04/05 the pipeline took one project — a CSV-to-JSON tool built as
> a test fixture, with no users by design — from an underspecified paragraph
> to a final review: thirteen of thirteen requirements discharged, 531 tests
> green, every mechanical check clean, and a verdict of `DRIFTED` for a
> reason no check could see. It produced 149 findings along the way, roughly
> five in six of them defects in this pipeline rather than in the fixture.
> Those that could be fixed during the run were. Those that need the whole
> run read at once are listed under [Known problems](#known-problems), and
> the plan for them is [`meta/roadmap/`](meta/roadmap/README.md).
>
> Version 0.1.0. Fifteen skills, nine agents, 42 numbered rules, and 328
> control cases green (`python3 scripts/run_controls.py`, read from the tree
> at `243059e`).

## Read these

| Document | What it is |
|---|---|
| [`docs/FOR-NEW-USERS.md`](docs/FOR-NEW-USERS.md) | **start here if you have been asked to run real work through this** — what it does, what it costs, and when to stop using it |
| [`docs/REPORTING-PROBLEMS.md`](docs/REPORTING-PROBLEMS.md) | the shape a finding should come back in, and the three kinds — including the one we have never received |
| [`DESIGN.md`](DESIGN.md) | **the architecture** — the three layers and why, the roster of agents and skills, every artifact the pipeline writes, the lifecycle and its five client gates, the two loops, the contracts that cross layer boundaries, the checks, the guard, the escalation policy, and what this deliberately is not |
| [`PROTOCOL.md`](PROTOCOL.md) | **the rules** — 42 numbered, normative rules that every skill and agent cites by number instead of restating. Each says what to do *and why* |
| [`docs/BRIEF.md`](docs/BRIEF.md) | the author's original statement of the idea, preserved, with the four deliberate departures noted |
| [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) | what the first run left to do — nine items, each deferred deliberately, each with the measurement behind it |
| [`meta/roadmap/`](meta/roadmap/README.md) | **what comes next** — cycle 0.2, planned as subcycle files a fresh session can implement without the planning conversation |

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
- **A record of what was decided without you**, listed at every checkpoint while
  it is still cheap to reverse.

## Known problems

Stated here so that nobody who finds this repository is surprised by them,
and **removed from this list as each is addressed** — the roadmap subcycle in
the last column is what removes it. Every row was measured on the first run;
the evidence column says where.

| Problem | Evidence | Plan |
|---|---|---|
| **The write guard judges a write by parsing command text, and the world is wider than its frame.** Two measured holes: an interpreter heredoc (`python3 - <<PY` … `open(path, 'w')`) writes unjudged, and git history is a write with no path — at width above one, a worker's `git commit --amend` rewrote a *concurrent* task's commit. `check_scope` reports both after the fact; nothing prevents them | [`DESIGN.md`](DESIGN.md) §8, §20; [`PROTOCOL.md`](PROTOCOL.md) P-10b, P-12b | replace classification with structure: a per-worker copy-on-write sandbox in which the host tree does not exist, and a promotion gate — roadmap 0.2.0–0.2.4 |
| **The manager never resets.** Every other role gets a fresh context; the manager runs for the whole project and, by the rule that makes it trustworthy, reads every worker report verbatim — roughly 230,000 tokens of task files on one run, plus a record, a decision log and a question log it re-reads. It cannot measure its own context, and compaction is a copy of a copy | [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) §1 | rotate the manager at every checkpoint into a fresh session that reads the durable state and asks the outgoing one what the files could not say — roadmap 0.2.5 |
| **Two mechanisms have never produced output.** `/devteam:iterate` has never run. The path where a reversible question proceeds on its recommendation and resurfaces for review (P-27) has never fired, because the run's client answered all thirty questions within the hour. A mechanism that has never fired has not been shown to work | the run's final review, `C-3` §3, in the private record | a second cycle on the fixture with a deliberately slow client — roadmap 0.2.9 |
| **Estimates are biased, not noisy.** Ten of ten tasks over their estimate, 1.78× in total, after two upward revisions; the overruns were on *rounds* — steps re-run after a defect — which the model does not carry | final review `C-3` §4; findings F-101, F-102 | a rounds term, corrected from measured budgets at every checkpoint — roadmap 0.2.6 |
| **A project learns forward only.** A signed decision made one of the charter's "done means" conditions undischargeable; the charter was amended three times afterwards and nobody re-read the condition. That is why the final review was `DRIFTED`. Nothing mechanical could see it | `C-3` §2; [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) §4 | every amendment enumerates every done-means condition and constraint with a verdict, and a check diffs that list against the charter — roadmap 0.2.6 |
| **The audit-finding namespace is unseen by design.** `COR-n`, `SEC-n`, `HYG-n` were given three-letter prefixes so the citation scanner could not mistake them for citations — which is the same fact as the scanner being unable to check them. Eleven of fifteen findings on one project were filed and never dispositioned before a field was added to watch them | [`templates/FORMATS.md`](templates/FORMATS.md) §namespace; CONSOLIDATION §7 | the scanner resolves the five reserved three-letter prefixes; an audit finding still `open` when its task closes is a finding — roadmap 0.2.6 |
| **Rules that are each right alone and cannot both hold.** Nine instances so far, every one found by a worker hitting it under time pressure, because a worker is the only party required to satisfy every rule at the same moment. Nobody has read the rule set *looking* for the shape | [`DESIGN.md`](DESIGN.md) §20 "the shape that has cost the most"; CONSOLIDATION §2 | a sweep by moment rather than by rule, with the nine as its calibration set — roadmap 0.2.7 |
| **Some checks predate the test that legitimises a check.** "Name the rule whose two sides this compares; if you cannot, it is proposing a rule, and its false positives are the missing rule showing up." Applied to three checks late in the run, it found all three proposing rules. The rest have not been audited against it | [`DESIGN.md`](DESIGN.md) §20 "why a check works"; CONSOLIDATION §3 | one table naming the rule for every finding class, and a self-check that a class with no row is a finding — roadmap 0.2.6 |
| **The evidence is one run, on a fixture, with an AI playing the client.** The client was unusually available — eighteen blocking stops in fifteen hours, answered in minutes with the domain loaded. A human client would have been the bottleneck. This is a limit on what the run proves, not a defect | [`../../HANDOFF.md`](../../HANDOFF.md) §4 | a second run with a client briefed to be slow on reversible questions — roadmap 0.2.9 |
| **The planned containment is Linux-only.** It rests on unprivileged user namespaces and `bubblewrap`; on macOS, Windows, or a Linux host without them, the pipeline will run in a `guard-only` mode that keeps the first row's holes open and says so | roadmap [`0.2/README.md`](meta/roadmap/0.2/README.md) §7 | detected at setup and stated in the charter rather than assumed — roadmap 0.2.4 |
| **It is heavy, on purpose, and wrong for small work.** One project produced 1,865 lines of design documents for a tool of about 200 lines of code — the pipeline run below its threshold deliberately, to find out how it breaks. It is aimed at work where being wrong is expensive, and it will outweigh anything simple. Of some 150 findings, exactly one has made it simpler, and it came from a team that declined to use it | [`DESIGN.md`](DESIGN.md) §21; [`docs/FOR-NEW-USERS.md`](docs/FOR-NEW-USERS.md) | not on the list to fix. The open question is which individual steps buy nothing on *any* project, and only people with real deliverables can answer it — roadmap 0.2.7 applies the one test that has never been applied |

## What comes next

Cycle 0.2, planned on 2026-09-05 and not yet started, in
[`meta/roadmap/`](meta/roadmap/README.md). In order: probes for the riskiest
unknowns; the sandbox harness and its controls; extraction and the promotion
gate; the worker running inside; the pipeline wired to run on it; manager
rotation; the checks audited and extended; the two sweeps; a 0.2.0 release;
and a second run that exercises everything that has never fired. The cycle
map says which of those to build first if the budget forces a choice, and
why. Each subcycle file is written for a session that has none of the
planning conversation.

## Licence

Apache 2.0, matching the repository. See [`../../LICENSE`](../../LICENSE).
