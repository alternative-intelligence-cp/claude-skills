---
name: check
description: Run a devteam project's mechanical checks — traceability, references, report blocks, scopes — and interpret what each finding means and what resolves it. Run before every commit that touches devteam/, before closing any task, and on every report before a verifier runs.
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git diff:*) Bash(git log:*) Read Grep Glob
---

# The checks

**Every hole this discipline has found was found by a check that diffs two
lists, and none of them by a test.** These are those diffs. They are scripts
with exit codes, not careful readings, and each ships a negative control
beside it because *a check that has never failed has not been shown to work*
(P-35).

All four exit `0` clean, `1` findings, `2` could not run, and read
**git-tracked files only** — so scratch work is never a finding, and a file
you have not committed yet is invisible to them.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py"  <project>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py"   <project>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_report.py" <project> T-n[.S-m]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py"  <project> [T-n[.S-m]]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_controls.py"          # prove the checks
```

## What each finding means

### `check_trace` — goal to requirement to task to evidence

| Finding | What it is, and what to do |
|---|---|
| `orphan-scope` | a charter goal no requirement covers. You promised the client something nobody owns |
| `uncovered-requirement` | a requirement no task will implement. It will silently not happen |
| `unmotivated-task` | a task discharging no requirement. **Either scope creep, or a requirement nobody wrote down** — and the second is far more common |
| `unverified-requirement` | a requirement with no runnable acceptance criterion. It will be declared done by opinion (P-5) |
| `missing-field` | a required field absent. Never defaulted: a default is a decision nobody made |
| `unknown-reference` | a `Satisfies`, `Discharges` or `Depends on` naming something that does not exist |
| `dependency-cycle` | tasks that can never start, because they wait on each other |

**What it cannot see.** It proves every goal has *a* requirement. It can never
prove those requirements *cover* the goal. A goal can be fully traced and half
built, and only reading the goal against the working thing finds that — which
is what a checkpoint is for.

### `check_refs` — citations, links, statuses, leaks

| Finding | What it is |
|---|---|
| `cited-undefined` | an identifier cited that was never declared. Often a typo; sometimes a proposal written by number, which is why you never propose a requirement by number |
| `defined-uncited` | a **decision** nothing cites. Usually a requirement stating a rule and forgetting to attribute it — **the highest-value finding here** |
| `duplicate-id` | one identifier declared twice. The later one needs a new number; never renumber the earlier, its citations are already elsewhere |
| `broken-link` | a relative link whose target does not exist |
| `bad-status` | a status outside its closed vocabulary |
| `leak` | an absolute home path or a credential in a tracked file |
| `control-character` | a document containing a control byte rather than naming it. Git commits it as **binary** and stops diffing it, which silently removes the file from every document-against-reality comparison an audit makes |
| `not-utf8` | a tracked document that is not valid UTF-8 |

### `check_report` — a committed REPORT block against the tree

`no-report`, `wrong-task`, `missing-field`, `bad-report-status`,
`status-mismatch`, `unknown-commit`, `head-subject`, `dirty-tree`,
`no-evidence`. Run it **before** the verifier: a malformed report is a
re-dispatch, not a judgement call.

`dirty-tree` measures only the task's own declared scope, because a supervisor
controls nothing else — a check nobody can satisfy is a check that gets
ignored.

### `check_scope` — declared scopes against each other and against writes

`overlapping-scope`, `undeclared-write`, `empty-scope`, `scope-escapes-tree`.
This is what makes width greater than one safe inside a single repository
(P-12). Commits are attributed by **subject prefix**, so the manager's own
`board: claim T-1` is not charged to T-1.

## Before you trust a clean run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_controls.py"
```

Every check has a control beside it that plants one fault per finding class
and demands exactly that class back — and **more than half of the cases are
false-positive controls**, because a check that flags legitimate work gets
switched off, which is worse than no check.

**And a green control proves the script, never the deployment.** The guard's
control passed for an entire rehearsal during which the guard was not running.
If what you need to know is whether something is *live*, the only evidence is
watching it act.
