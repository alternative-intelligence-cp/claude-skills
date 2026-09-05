# The devteam roadmap

The cycles of the `devteam` plugin, because the plugin *is* the working system:
the skills, the agent definitions, the guard, the hooks, the checks and their
controls, and the documents the manager runs on.

| Cycle | Plugin | What it is | State |
|---|---|---|---|
| 0.1 | 0.1.0 | the three-layer pipeline, written 2026-09-03 and run end to end once on a CSV-to-JSON fixture (`.internal/scratch/`, private remote `alternative-intelligence-cp/devteam-run-01-csv2json`) — 149 findings, a `DRIFTED` final review the client accepted | shipped, run once |
| [0.2](0.2/README.md) | 0.2.0 | **structural containment and the queue the run left**: workers run inside a per-worker copy-on-write sandbox and reach the host only through a promotion gate; the manager rotates instead of compacting; the checks are audited against the rule each one enforces; the rule set is swept for pairs that cannot both hold; then a second run that exercises `iterate`, rotation and the unreviewed-decision path | planned 2026-09-05 |

Cycle numbers sort lexically only to `0.9`; this table is authoritative over
lexical order.

## How this directory is used

- **One file per subcycle**, `0.2/0.2.n.md`. Each is written so that a fresh
  session with none of the planning conversation can implement it: where the
  tree is when you arrive, what to read, the decisions already settled, the
  artifacts to produce with their exact shapes, the verification commands with
  their expected output, and the condition under which it is done.
- **The title line of a subcycle file is the one home for its state** —
  `PLANNED`, `IN-PROGRESS (since <date>)`, `DONE (<date>)`, or
  `STOPPED (<date>, <why>)`. When a subcycle reaches `DONE`, move its file to
  `done/`. `ls 0.2/` is then what remains; `ls done/` is what happened.
- **Every factual claim in these files is marked.** `MEASURED` means the
  planning session ran the command on this machine on 2026-09-05 and the
  figure is what it printed. `REASONED` means it was argued, not run — do not
  build on a `REASONED` line without first running it. This is the convention
  of the spec these plans descend from ([`../devteam-sandbox-spec-2026-09-05.md`](../devteam-sandbox-spec-2026-09-05.md)).
- **This directory is tracked and public; the experiment it plans against
  is not.** The first run's fixture and its full `devteam/` record live in
  `.internal/scratch/` on the owner's machine, gitignored here and pushed to a
  private remote, and will be deleted once the experiment stops being useful.
  Every path below of the form `.internal/...` is therefore a **private
  input**: the plan reproduces from it what an implementer needs, and cites
  it for the implementer who has it locally.

## Where the inputs are

**Tracked, in this repository:**

| Input | Where |
|---|---|
| the handoff from the session that ran cycle 0.1 | [`HANDOFF.md`](../../../../HANDOFF.md) at the repository root |
| the work queue the run left, nine items each with its measurement | [`docs/CONSOLIDATION.md`](../../docs/CONSOLIDATION.md) |
| every lesson the run produced | [`DESIGN.md`](../../DESIGN.md) §15–§21 |
| the numbered rules, each with the failure that produced it | [`PROTOCOL.md`](../../PROTOCOL.md) |
| the grammar the checks parse | [`templates/FORMATS.md`](../../templates/FORMATS.md) |
| the sandbox idea corrected and measured on this machine, as a build order — "the spec" wherever a subcycle says so | [`../devteam-sandbox-spec-2026-09-05.md`](../devteam-sandbox-spec-2026-09-05.md) |

**Private, on the owner's machine** (paths as the subcycle files cite them):

| Input | Path |
|---|---|
| the owner's original sandbox idea, fleshed out by Gemini | `.internal/Structural Sandboxing for Autonomous Agents.md` |
| the run's own record: charter, decisions, questions, findings, checkpoints, audits | `.internal/scratch/devteam/` |
| the final review of the run, `DRIFTED`, and why | `.internal/scratch/devteam/checkpoints/C-3-2026-09-05.md` |
