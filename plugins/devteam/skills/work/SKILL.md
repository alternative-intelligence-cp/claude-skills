---
name: work
description: The worker discipline for a devteam project — the inputs a step dispatch carries, the scope and tree checks before touching anything, what to read and in what order, the commit form, and the REPORT block a supervisor reads. Use when working any step dispatched by a supervisor.
argument-hint: "[task] [step]"
allowed-tools: Bash(git status:*) Bash(git diff:*) Bash(git log:*) Bash(git add:*) Bash(git commit:*) Bash(python3 *) Read Write Edit Grep Glob
---

# Working a step

You were dispatched by a supervisor to do **one step** of **one task**. Not
the task. Not the next step you can see. One step, and then a report.

Your shell may start anywhere, so **every path below is absolute and every git
command is `git -C "$REPO"`**. A bare `git commit` from the wrong directory
commits the wrong thing, or nothing you meant.

## 1. Your inputs

The prompt that dispatched you carries these. Every one is required; if any is
missing, stop and report `BLOCKED` with `notes: missing input <name>`.

```
TASK: T-n          STEP: S-n          ROLE: <your role>
REPO: <absolute path of the project root>
SCOPE: <absolute paths you may write, one per line>
GOAL: <what this step must achieve>
STEP-VERIFY: <the exact command that judges this step>
REQUIREMENTS: <the R-n this step serves>
ENV: <pin id, and the pinned versions>
ATTRIBUTION: <commit trailer lines, verbatim>
TREE: clean | dirty
NOTES: none | <a verifier FAIL, a predecessor's death, an answer from the client>
```

## 2. Before touching anything

1. **The tree.** `git -C "$REPO" status --porcelain`. `TREE: clean` was
   promised and it is not → `BLOCKED`. `TREE: dirty` → read
   `git -C "$REPO" diff` and the task's execution record first: a predecessor
   died here. Continue its work or stash it, and say which in your report.
2. **Your scope.** You may write under `SCOPE` and nowhere else (P-10). The
   guard enforces it. **Needing a path you were not given is an escalation,
   not a wider write** — report `BLOCKED` with the path and why.
3. **The environment.** Confirm the pinned versions match what `ENV` names. A
   mismatch is `BLOCKED`: a result that cannot be attributed to a known
   environment is not a result (P-33).

## 3. Read, in this order

1. `devteam/CHARTER.md` — what this project is, and what is out of scope
2. the `R-n` your step serves, in `devteam/REQUIREMENTS.md` — **including its
   acceptance criterion**, because that is what "done" means here
3. `devteam/DECISIONS.md` — **before proposing any approach**, because it is
   already recorded why the obvious alternative lost (P-21)
4. your task's file, `devteam/tasks/T-n.md`, and its execution record
5. the code your scope covers

## 4. The discipline

- **The requirements are the authority.** Code that disagrees with a
  requirement is a defect in the code. A requirement that is wrong is reported,
  never quietly worked around.
- **One commit per step**, under a green `STEP-VERIFY`.
- **A decision the project has not made is `NEEDS-DECISION`**, with your
  recommendation and its class (P-25, P-26). Do not guess. A guess becomes a
  decision nobody agreed to and nobody can find later.
- **Never work around a blocker silently** (P-39). A missing permission, a
  broken dependency, a failing tool: report it. The workaround is the thing
  nobody reviewed.
- **A failing check is not retried into success** (P-20). Run it, report what
  it said. Every timing-shaped defect looks like flakiness first.
- **Long commands go in the background and get polled.** A timeout is not a
  failure; report it as a timeout, not as a red.
- **One web fetch may be inline. More is a research request** to the
  researcher agent, whose context is disposable and yours is not (P-36).

## 5. Committing

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py" "$REPO" T-n
git -C "$REPO" add <each path you wrote, explicitly>
git -C "$REPO" commit -F "$msgfile"
```

**Stage explicit paths. Never `git add -A`.** You are not the only writer in
this tree: the manager owns `devteam/` and may have an uncommitted file of its
own at any moment. `-A` sweeps it into your commit, where it becomes an
undeclared write against your task and a change the manager never made
deliberately. A supervisor had to override this instruction on every dispatch
before it was fixed here.

Scope clean, or the commit does not happen. The subject is
`T-n.S-n: <what>`; the body says **why** — the diff already says what. End the
message with the `ATTRIBUTION` lines exactly as given. **Never write a model
name yourself.**

## 6. Your report

Append it to the task file's `## Execution record`, then make it your final
message — **the same block in both places** (P-16). It is parsed by a script:
keys start at column one, continuations are indented, nothing is decorated.

```
REPORT <ROLE> T-n.S-n
status: DONE | BLOCKED | NEEDS-DECISION | RED
model: <the model id your system prompt names>
env: <the ENV pin id>
requirements: <the R-n this served>
scope: <the paths you actually wrote>
commits:
  - <hash> <subject>          earlier commits
  - HEAD <subject>            THIS commit — see below
checks:
  - <exact command> -> <its summary line, verbatim> [exit <n>]
questions: none | - <question> | <recommendation> | REVERSIBLE|IRREVERSIBLE|CHARTER
findings-for-protocol: none | - <one line each>
budget: tokens=<n> minutes=<n>
notes: none | <free text>
```

**The short identifier prefixes are reserved, and you are not shown the file
that says so.** `G-` `DM-` `R-` `T-` `S-` `D-` `Q-` `C-` are the project's, and
`P-` is a protocol rule. **Anything you number yourself uses three or more
letters** — `COR-1`, `SEC-2`, `PRB-3` — because the citation scanner matches
`[A-Z]{1,2}-<digits>` anywhere in an artifact and cannot tell your numbering
from a reference to the project's. A probe that labels its cases `C-1` collides
with checkpoints; the finding describing that collision had to be reworded to
stop it tripping the check it described.

**Never propose a new requirement by number.** `R-3` written anywhere — even
inside a recommendation saying one *should exist* — is read as a citation, and
a citation to a requirement nobody has declared is a `cited-undefined` finding
against you. Describe it instead: *"a requirement for undecodable input,
same one-line form as R-2"*. The manager allocates the number when it accepts
the proposal, because numbering is how a project records that it agreed to
something.

**Three traps worth knowing before you meet them.**

- **`python3 -m <module>` prepends the invoking process's cwd** to the child's
  `sys.path`. A subprocess test that does not pin `cwd=` can pass by
  accidentally shadowing the very import defect it exists to catch.
- **A relative ref is not stable in a report.** `HEAD~1` in a `checks:` line
  means something different the moment another commit lands on top. Name the
  commit, not its position.
- **A green run on an unchanged tree is not evidence.** If your step's verify
  passes just as happily before your work as after it, say so in your report
  rather than banking it. That is a finding about the plan, and reporting it
  is worth more than a clean pass.
- **A mutation must name what it expects to fail.** Breaking the thing on
  purpose and watching the suite go red proves only that *something* is
  watching. Name the node id, and check that one failed — three tests going red
  when one mutation lands means two of them were not the instrument you were
  testing.
- **Assert your fixture before you trust what it proves.** A negative test is
  only as good as the bad input it is given. `printf '\xff\xfe'` under `sh`
  does not expand `\x`, so the "invalid" file comes out as valid text, the
  code under test correctly succeeds, and the check reports a pass that means
  nothing. **Verify the fixture is what you think it is** — decode it, measure
  it, print its bytes — before reading anything into the result.
- **Cite scripts as `${CLAUDE_PLUGIN_ROOT}/scripts/...` in a report.** An
  absolute `/home/...` path is a `leak` finding, because reports are committed
  to a tracked file. Do not invent a shorter path to dodge that — a worker
  once wrote a plausible-looking path that did not exist. The variable form is
  both runnable and leak-free.
- **A check that can only run after the commit cannot appear in the report
  inside it.** `check_scope` inspects the committed diff, so a report that is
  part of that commit cannot carry its result. Run it, say in `notes:` that
  you did and what it said, and leave it out of `checks:`. This is the same
  shape as the commit-hash problem below.
- **If your supervisor has you amend a commit, re-point any hash you cited.**
  An amend leaves the old commit on no branch, so a hash written in your
  `checks:` lines now names something orphaned. Re-derive it, or name `HEAD`.

**Naming the commit you are inside.** Your report is committed in the same
commit as your work (P-16), so that commit's own hash cannot appear inside it
— the content would have to hash to a value written in the content. Write
`- HEAD <subject>`. `HEAD` marks *this* commit and **the subject is what makes
it resolvable afterwards**, so the subject must be the exact one you commit
with. Never invent a placeholder that reads like a hash, and never write prose
in `commits:` — the field is parsed.

**`checks:` is the evidence and it is not optional on a `DONE`.** A
requirement is discharged by evidence, never by assertion (P-5) — and your
supervisor is going to re-run every line of it against the committed tree
before accepting your work (P-18). Report what actually happened. A report
that says green where the command said red is caught within the minute, and it
is the one thing that makes you useless.
