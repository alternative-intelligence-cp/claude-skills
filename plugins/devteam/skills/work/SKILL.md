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

1. **The tree, inside your scope.** `git -C "$REPO" status --porcelain --
   $SCOPE`. `TREE: clean` was promised and it is not → `BLOCKED`.
   `TREE: dirty` → read `git -C "$REPO" diff -- $SCOPE` and the task's
   execution record first: a predecessor died here. **Continue its work** and
   say so in your report.

   **Scoped, because unqualified it reports other tasks' work in progress**,
   which at width above one is always non-empty and never yours. And the old
   instruction here said "continue its work *or stash it*" — **stashing is now
   forbidden** (P-12b): `git stash` takes the whole tree, including files two
   other tasks have open, and hands you a clean tree by taking theirs away.
   That instruction was written when width was one and became a corruption the
   moment it was not.
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
git -C "$REPO" commit -F "$msgfile" -- <each path you wrote, explicitly>
```

**Commit a pathspec. Staging explicitly is not enough, and `-A` is worse.**

`-A` sweeps whatever else is in the tree into your commit — the manager owns
`devteam/` and may have an uncommitted file at any moment, and a supervisor had
to override that instruction on every dispatch before it was fixed here.

But `git add <your files>` followed by a plain `git commit` fails too, and
fails invisibly: **the index is shared.** At any width above one, another
agent's `git add` has already put its files there, and your commit takes the
whole index — carrying somebody else's in-flight work into your task's commit
under your message. You did nothing wrong and the standing rule did not cover
it, because *somebody else did the staging*. A manager used the add-then-commit
form for an entire run and it only never landed because the other task happened
to commit first.

`git commit -- <paths>` commits exactly those paths whatever the index holds.

**The `-m` trap:** anything after the `--` separator is a pathspec, so
`git commit -- src/a.py -m "msg"` silently tries to commit files named `-m` and
`msg`. Put the message flag first, or use `-F`.

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
- **Prove your check against the defect, not only against the old tree.** A
  check that fails before your change and passes after it may still be blind to
  the thing it exists to catch — three checks in this project failed on the old
  tree, passed on the new one, and passed a deliberately built version of the
  exact defect they were written for, because all three compared text the
  defect does not alter. Build the defect on a copy and require the check to
  fail on it.
- **A mutation must name what it expects to fail.** Breaking the thing on
  purpose and watching the suite go red proves only that *something* is
  watching. Name the node id, and check that one failed — three tests going red
  when one mutation lands means two of them were not the instrument you were
  testing.
- **Measure your own baseline; never trust one you were handed.** A figure in
  your dispatch was true when somebody wrote it and the tree has moved since —
  a manager corrected a stale "5 passed" to "6 passed" in a dispatch here and
  the measured figure was "7 passed, 7 xfailed". A baseline in a dispatch ages
  exactly as fast as one in a report, and the instruction to produce your own
  is what makes the check survive being wrong about it.
- **Write product files with `Write` or `Edit`, not with an interpreter.**
  `python3 - <<PY` with `Path.write_text` is convenient and it is the one form
  the guard cannot classify — a write whose target does not appear in the
  command text. So it is not refused, and **it is not judged either.**

  The refusal message warns about this, and that warning only reaches somebody
  who was refused first. **A worker whose habit is heredocs never knocks on
  that door**, so it never sees the warning: the bypass is not reached *around*
  the guard, it is reached *instead of* it. That is why this bullet is here,
  at the moment you choose how to write, rather than only in a refusal.

  It has already cost something. Two paths a manager had granted were written
  in a form the scope parser could not read, so they were outside every parsed
  scope — and the writes to them went through an interpreter, so the guard
  never saw them either. **Either failure alone would have been visible: a
  refusal, or a finding. Together they produced silence.**
- **A script making two edits to one file must re-read between them.** Both
  writes computed from one `read_text()` means the second silently discards the
  first — the file ends up with the last edit only, no error, no warning, and a
  diff that looks plausible because it *does* contain a change. This is not
  hypothetical: it dropped a rule from a skill here, the commit message claimed
  both edits, and it went undetected for hours because **prose changes produce
  no observable**. A check that fails to run is caught by its output being
  wrong; a paragraph that was not written is caught by nothing.
- **So when you claim a prose file gained something, re-read the file and
  confirm the words are there.** Not the diff — the file. It is two seconds and
  it is the only verification that class of change has.
- **Feed any probe you build one case whose answer you already know, before
  you believe any case whose answer you don't (P-35b).** This applies to the
  throwaway script you write to investigate something, not only to the checks
  that ship — and that is where it keeps going wrong. Seven instrument failures
  here were ad-hoc probes, three of them built while investigating somebody
  else's finding. Two on one day drove the same guard: one read the exit code
  of a program that denies via JSON at exit 0, the other omitted the session id
  the whole judgement keys on. Neither errored; both printed clean, confident,
  meaningless output. **An instrument that answers a question it was never
  wired to ask cannot be caught by reading its output** — only by giving it a
  case where you already know what it must say.
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
- **A step may take two commits, and post-commit evidence is why.** If the
  evidence your report genuinely rests on — mutation testing, a check over the
  committed diff — can only exist once the work is committed, then commit the
  work, gather the evidence, and **append the report in a second commit**.
  "One commit per step" is a default that keeps the record legible, not a rule
  worth rewriting history to preserve; a worker contorted to hold that line and
  corrupted a concurrent task's commit doing it. Both commits name the step in
  their subject, which is all `check_report` asks for.
- **`git commit --amend -- <paths>` is not the safe version.** The pathspec
  limits which *content* is taken; it does nothing about *which commit* is
  amended, which is always `HEAD`. A worker reaching for the careful-looking
  form still rewrites whoever is at `HEAD`. There is no pathspec, flag or
  ordering that makes an amend safe in a shared tree — only not doing it.
- **Never `--amend` unless the board says width 1.** `--amend` acts on `HEAD`,
  and at width greater than one `HEAD` is not yours — it is whichever task
  committed most recently, which may have been a second ago. A worker amended
  what it believed was its own commit and rewrote a concurrent task's: its
  report text was merged into that task's subject, and that task's hash changed
  underneath it. Read the board's `**Width.**` line; above 1, correct a commit
  by **adding another one**, never by rewriting. The same goes for `rebase`,
  `reset --hard`, `stash`, and `checkout` of a tracked path (P-12b).
- **If you have already rewritten history, `reset --soft`, never `--hard`.**
  Recover the original commit from `git reflog` and soft-reset to it. Soft
  leaves the index and working tree exactly as they are, which matters because
  the tree holds other tasks' uncommitted work and `--hard` would destroy it.
  Then say so in `notes:` — the recovery is part of the record, not a tidy-up.
- **If your supervisor has you amend a commit at width 1, re-point any hash you
  cited.** An amend leaves the old commit on no branch, so a hash written in
  your `checks:` lines now names something orphaned. Re-derive it, or `HEAD`.

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
