---
name: check
description: Run a devteam project's mechanical checks — traceability, references, report blocks, scopes — read what each result means, commit through the gate that runs them on the commit itself, and accept a finding by a decision. Run on every report before a verifier runs, before closing any task, and whenever a result or a refusal needs reading.
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git diff:*) Bash(git log:*) Read Grep Glob
---

# The checks

**Every hole this discipline has found was found by a check that diffs two
lists, and none of them by a test.** These are those diffs. They are scripts
with exit codes, not careful readings, and each ships a negative control
beside it because *a check that has never failed has not been shown to work*
(P-35).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py"  <project>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py"   <project>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_report.py" <project> T-n[.S-m]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py"  <project> [T-n[.S-m]]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_controls.py"          # prove the checks
```

## What a result means

**Every other skill points here for what a check's exit code means.** The
contract's home is `scripts/result.py`, and the plugin's
`templates/FORMATS.md` §"What each check reads" states it.

| Exit | Result | What to do |
|---|---|---|
| `0` | clean | Everything the check owns was evaluated, and nothing was found. **This is the only pass** |
| `1` | findings | Fix what each line names. The line also names any part the check did not evaluate |
| `2` | could not run | The fault is in the invocation — its arguments, no repository, no `devteam/` — and not in the project. Fix the command |
| `3` | not evaluated | No finding, and at least one part the check did not look at, each named with its reason: a row its grammar could not read, a piece of an identifier field that is not an identifier, or zero rows from a source that offered some. **Never clean** (P-50). The remedy is in the project: write the row in the shape FORMATS defines, keep an identifier field to identifiers and put the reason on a bullet of its own, or accept the part by a decision until the check can read it |

A PASS that rests on exit `3` is a claim about a part nobody read.

**Excluded is not the same as not evaluated.** A class a caller or the project
declares out of scope — `--pre-plan`, `--at-commit`, the harness classes on a
`guard-only` project — is named in the line and does not change the exit. The
difference is who said so: an exclusion has a declaration a reader can check,
and a gap has none (roadmap 0.3.1, L-1.2).

**Every check takes `--json`**, one schema for all of them. The line is
rendered from the same object, so the two cannot disagree. A program reads
the JSON, and a person reads the line. The line carries its denominators —
what was read, and how many of each kind — so a clean over zero rows is
visible as zero.

**The checks read what git would show.** `check_trace`, `check_refs` and
`check_scope` read tracked files and the untracked ones that no ignore rule
covers. Each untracked file they read is reported as `untracked-file`, so a
file you have not committed yet is read and reported rather than invisible
(F-131). Ignored files, `devteam/.run/` among them, stay invisible.

## Committing: the gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" commit -C "$REPO" -F "$msgfile" -- <each path, named>
```

It does what `git commit -F <msg> -- <paths>` does — the named paths'
working-tree content on HEAD, the project's commit hooks run as git runs them
— with the four project checks run on the commit itself before it exists, and
on HEAD. It makes the commit only if the commit adds nothing HEAD lacks, and
then makes exactly that commit (P-49).

**It is the only way an agent commits in a devteam project.** The
`commit_guard.py` hook refuses every other form: a git command that writes a
commit, and a branch pointed at a commit no branch holds. A worker inside a
sandbox commits with plain git, because promotion gates its commits (P-44).
The client's own terminal runs no hook.

- Give the message with `-m` or with `-F`, not both. Put every option before
  `--` and the paths after it.
- Name each path. A path naming the whole repository is refused, because it
  is `git add -A` by another name. A named directory commits what is under
  it, its untracked files included.
- `--dry-run` answers without committing. `--pre-plan` is for a commit that
  adds requirements before their tasks are planned — onboarding, and
  `iterate`'s charter gate. `--json` gives the result as JSON.
- A finding already at HEAD does not refuse your commit (F-12). It is printed
  as standing at every run, and it is its owner's to fix or accept.

| Result | What it asks of you |
|---|---|
| exit `0` | Committed. The line names the commit, and prints what stands, what this commit fixed, and anything it let through, with why |
| `adds-finding` | The commit adds a finding HEAD lacks, possibly in a file it did not touch — removing a declaration another file cites does that. Fix the commit. If the finding will not be fixed, accept it by a decision in the same commit |
| `adds-not-evaluated` | The commit adds a part no check can read. Write it in the shape FORMATS defines, or accept the part by a decision |
| `untracked-unnamed` | A file under `devteam/` is untracked and this commit does not name it. Name it, commit it first, or move it out of `devteam/` |
| `hook-refused` | The project's own commit hook refused. Fix what it names |
| `head-moved` | HEAD moved while the gate evaluated. Nothing was committed. Run it again |
| exit `2` | Nothing was committed. The message says whether the fault is in the invocation or in the gate — a check that could not run, or output the gate could not read |

**Never commit around a refusal.** A commit made another way is unchecked,
and the next gate run counts what it added as standing rather than refusing
it. The classes and their rules are in `docs/CHECKS.md`, under `gate.py`.

## Accepting a finding

A finding that will not be fixed, or a part a check cannot read yet, is
accepted **by a decision**: a `D-n` in `DECISIONS.md` with an `Accepts.`
field, each item naming a finding as the check printed it, without its line
number (P-51). The grammar is FORMATS §"Accepted findings", and the
`DECISIONS.md` template shows the field.

- **Who decides** is the decision's P-26 class. The manager makes a
  `REVERSIBLE` acceptance alone, with `Reviewed.` reading `unreviewed` (P-27).
  The client makes a `CHARTER` one. The check enforces that the `Reviewed.`
  line is there. It cannot enforce the class, so choosing it is your
  judgement, and it is recorded.
- **Cite the decision in the same commit** — a `RECORD.md` line saying what it
  accepted — and name both files. A decision nothing cites is itself a finding,
  `defined-uncited` (P-22), and the gate refuses the commit that adds it.
- **What the check then does:** it reports the finding as accepted, under the
  decision's number, and exits `0` if nothing else is found.
- **An acceptance restores the zero. It does not suppress a finding.** Every
  one is a finding the checks will never show again, so never accept one to
  get a commit through faster.
- **`stale-acceptance`** means the accepted finding no longer fires: someone
  fixed it. Supersede the accepting decision (P-23), carrying over whatever
  else it accepted that still stands, in the same commit as the fix. The gate
  refuses a fix that leaves its acceptance stale, because the stale acceptance
  is itself a finding the commit adds.
- **`unparseable-acceptance`** means an `Accepts.` line is outside the
  grammar, so it accepts nothing. Fix the line.

## Reading a finding

Every class, the rule it enforces and the two lists it compares are in
`docs/CHECKS.md`, which `check_plugin` keeps equal to the code (P-34). What the
rows there cannot say:

- **`unmotivated-task`** is either scope creep or a requirement nobody wrote
  down, and the second is far more common. A third cause is a fix under a
  requirement another task discharged: it takes no discharge, and names the
  requirement in `Re-establishes.` instead.
- **`defined-uncited`** is usually a requirement stating a rule and forgetting
  to attribute it. It is the highest-value finding `check_refs` makes.
- **`duplicate-id`**: the later declaration takes a new number. Never renumber
  the earlier, because its citations are already elsewhere.
- **`control-character`**: git commits such a document as binary and stops
  diffing it, which silently removes the file from every comparison an audit
  makes between documents and reality.
- **`dirty-tree`** measures only the task's own declared scope, because a
  supervisor controls nothing else, and a check nobody can satisfy gets
  ignored.
- **`misattributed-write`** is a commit that belongs to no task and touches a
  live task's scope, which is what `git add -A` does to a worker's in-flight
  file. Commits are attributed by subject prefix, so the manager's own
  `board: claim T-1` is not charged to T-1. The window is the task's current
  claim: the commits after the first one whose board's in-flight table carries
  the label its title names, `RUNNING (since <date>, <label>)`, exactly. A
  title written any other way names no claim, and the window is a part not
  evaluated until the title is fixed.
- **What `check_trace` cannot see.** It proves every goal has *a* requirement.
  It can never prove those requirements *cover* the goal. A goal can be fully
  traced and half built, and only reading the goal against the working thing
  finds that, which is what a checkpoint is for.
- **`check_report . T-n`** judges the task's latest task-level block and
  each step's latest block, so a malformed step report is found by the
  task's run as well as by the step's (F-37). An earlier block for the same
  id is a superseded attempt, and is not judged. Each finding names its block. A
  restarted task's previous close, the task-level block already in the file
  when its current claim began, is compared with nothing of the new run: not
  its title, the harness meter or the tree.
- **Run `check_report` before the verifier.** A malformed report is a
  re-dispatch, not a judgement call.

## Before you trust a clean run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_controls.py"
```

Every check has a control beside it that plants one fault per finding class
and demands exactly that class back. More than a third of each check's
control cases are false-positive controls, because a check that flags
legitimate work gets switched off, which is worse than no check.

**And a green control proves the script, never the deployment.** The guard's
control passed for an entire rehearsal during which the guard was not running.
If what you need to know is whether something is *live*, the only evidence is
watching it act.
