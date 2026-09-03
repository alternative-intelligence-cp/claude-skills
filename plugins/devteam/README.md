# devteam — a development pipeline that leaves evidence

Takes a project from a client's idea to a working product, modelling how a real
development organisation actually works: a written charter signed before
building starts, requirements numbered and traced to the tasks and tests that
discharge them, supervisors who verify the workers they dispatch, and a
manager who verifies the supervisors.

It runs unattended for hours. It stops for exactly three things: a decision
that cannot be undone, a change to what is being built, and a checkpoint that
finds the work has drifted from the charter.

> **Status: in development.** The design, the checks, the guard and all ten
> skills and five agents are written and internally consistent — 127 control
> cases green. What has *not* happened yet is a real project running end to
> end through it, which is what [`DESIGN.md` §14](DESIGN.md) phase 3 actually
> requires. Writing a procedure is not the same as running it, so treat this
> as buildable-but-unproven until the rehearsal in phase 4.

## Read these

| Document | What it is |
|---|---|
| [`DESIGN.md`](DESIGN.md) | **the architecture** — the three layers and why, the roster of agents and skills, every artifact the pipeline writes, the lifecycle and its five client gates, the two loops, the contracts that cross layer boundaries, the checks, the guard, the escalation policy, and what this deliberately is not |
| [`PROTOCOL.md`](PROTOCOL.md) | **the rules** — 42 numbered, normative rules that every skill and agent cites by number instead of restating. Each says what to do *and why* |
| [`docs/BRIEF.md`](docs/BRIEF.md) | the author's original statement of the idea, preserved, with the four deliberate departures noted |

## How it will be used

```bash
/devteam:setup           # scaffold devteam/ in your project, agree the permissions
/devteam:onboard         # the interview → CHARTER.md + REQUIREMENTS.md → you sign
/devteam:plan            # requirements → a task graph → you approve
/devteam:run width=2     # the loop. Runs unattended; stops only when it must
/devteam:status          # where is it, at any time
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

## Licence

Apache 2.0, matching the repository. See [`../../LICENSE`](../../LICENSE).
