# claude-skills

A marketplace of agentic workflows for [Claude Code](https://claude.com/claude-code).

Each plugin here is a **complete working system**, not a prompt — a set of
skills, agents, hooks and checks that carry a piece of work end to end with a
written record of what was decided and evidence that it was verified.

## Install

```bash
/plugin marketplace add alternative-intelligence-cp/claude-skills
/plugin install devteam@claude-skills
```

Or, to develop against a local checkout:

```bash
claude --plugin-dir ~/path/to/claude-skills/plugins/devteam
```

## The plugins

| Plugin | What it does |
|---|---|
| [**devteam**](plugins/devteam/) | A three-layer development pipeline — project manager, task supervisors, specialist workers — that takes a project from a client's idea to a working product under a signed charter, with numbered requirements traced to tasks and tests, independent verification of every report, scheduled checkpoints that diff the built thing against the charter, and escalations classified by reversibility so the loop keeps running without guessing on anything that matters |

## The ideas these are built on

Every plugin here shares a small number of convictions, learned from running
multi-agent work on real projects and finding out which parts break:

**Reported green is not green.** An agent that has just spent an hour on a task
is the worst available judge of whether it worked. Every claim of success is
re-verified by re-running the exact stated command against the committed tree,
by someone who did not do the work.

**Every hole is found by a check that diffs two lists.** Requirements against
tasks. Decisions cited against decisions declared. What a report claims against
what the tree contains. Not by reading, and not by a test.

**A check that has never failed has not been shown to work.** Every check ships
a negative control that plants one fault per finding class and demands exactly
that class back — including false-positive controls, because a guard that
blocks legitimate work gets switched off, which is worse than no guard.

**A fact has one home.** Skills carry procedure and pointers, never content. A
fact with two homes drifts, and the copy is the one that goes stale.

**Decisions record the alternatives declined.** The alternatives are exactly
what the next reader will propose, and a decision that does not say why they
lost gets re-litigated by everyone who arrives fresh.

**Stop for what cannot be undone.** Autonomy comes from classifying decisions by
consequence — not from deciding everything, and not from asking about
everything.

## Licence

Apache 2.0. See [`LICENSE`](LICENSE).
