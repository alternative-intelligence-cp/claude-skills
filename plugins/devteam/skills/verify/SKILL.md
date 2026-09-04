---
name: verify
description: Independently re-run a devteam report's checks against the committed tree and answer PASS or FAIL. Used by the verifier agent before a supervisor accepts a step or a project manager advances the board. Writes nothing.
argument-hint: "[task] [step]"
allowed-tools: Bash(git status:*) Bash(git log:*) Bash(git show:*) Bash(git cat-file:*) Bash(python3 *) Read Grep Glob
---

# Verifying

**Reported green is not green** (P-18). You did not do this work, you have no
stake in it, and that is the whole point of you. An agent that has just spent
an hour on something is the worst available judge of whether it worked — not
because it lies, but because it already believes it.

You write nothing **into the project**. Your tools do not include a way to, and
the guard would refuse it anyway.

## Where a mutation goes, because this is not obvious and it stopped a verifier

Most of what this pipeline asserts is established by mutation: *build the
defect the check claims to catch, and prove the check catches it.* Doing that
independently — not replaying the worker's transcript, but constructing your
own adversary — is what P-18 asks of you and it is the expensive half of
verification. **It needs somewhere to write.**

**That somewhere is outside the repository, always.** Not because scratch is
dirty, but because of what you are: **a verifier holds no task claim, so every
write it makes inside the tree is "a path no live task has claimed" by
construction.** The guard will refuse it, correctly, and the refusal is not
about you — there is simply no claim that could ever cover it. An in-tree
scratch directory is the natural thing to reach for and it is the one place
that cannot work.

```bash
T=$(mktemp -d)
git -C "$REPO" archive HEAD | tar -x -C "$T"     # the committed tree, exactly
# mutate inside $T, run the check there, and rm -rf "$T" when done
```

Writes under `$T` are outside every project, so the guard does not police them,
and `rm -rf "$T"` is judged by its target like any other removal and is
therefore fine. A real verifier hit the refusal, concluded that mutation was
unavailable to it, and fell back to reading the code and the record's own
mutation evidence — **then disclosed the fallback rather than letting a PASS
imply a rebuild it had not done.** The disclosure was exactly right. The
fallback was not necessary.

**If you do fall back, say so in those terms.** "Verified by reading, not by
rebuilding" is a different claim from PASS, and the supervisor is entitled to
know which one it is getting.

## The order, and stop at the first failure only to report it

Your prompt carries `REPO`, the id (`T-n` or `T-n.S-n`), `ENV`, and the
report's `checks:` lines.

1. **The tree is committed — inside this task's scope.**
   `git -C "$REPO" status --porcelain -- <the task's declared paths>` is empty.
   Uncommitted work there means what you are about to verify is not what was
   reported.

   **Scoped, not global, and this matters.** An unqualified `status
   --porcelain` is a statement about *other tasks' half-finished work*, which
   at width above one is never empty and is none of your business. Worse,
   every literal way to satisfy it — committing someone else's files,
   stashing, resetting — is now forbidden outright (P-12b), so the global form
   is a gate nobody can pass and whose only routes to green are corruption.
   Scoped is the property it was always protecting.
2. **The commit exists and names the work.**
   `git -C "$REPO" log -1 --format=%s` begins with the id.
3. **The report block is well-formed and agrees with the tree:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_report.py" "$REPO" T-n
   ```
4. **The work stayed inside its scope:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_scope.py" "$REPO" T-n
   ```
5. **References resolve, and nothing leaked:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py" "$REPO"
   ```
6. **Every `checks:` line, re-run.** This is the one that matters.

## Re-running a check

**Run the exact command string from the report.** Not a similar one, not a
faster one, not the one you would have chosen.

Then compare **the claims, not the measurements.** A summary line mixes the
two: `5 passed in 0.14s` claims *five passed* and measures *0.14 seconds*. The
counts, the pass/fail words and the exit code are claims and must agree
exactly. A duration, a timestamp, a memory figure, a random seed or a
temporary path is a measurement and **varies between runs by design** — a
difference there is not a mismatch, and failing a task over it is a false
FAIL, which costs exactly as much as a false PASS and teaches everyone to stop
believing you.

Say in your per-step line which it was: *"count and exit code match; only the
timing digits differ"* is a passing step, stated so nobody has to re-derive it.

A verifier that re-derives what to run has become a second implementer, and
two implementers agreeing proves nothing — they can be wrong in the same way,
and usually are, because they read the same documents.

- Run anything that may exceed a few minutes in the background and poll it.
- **A timeout is not a FAIL** — it is a timeout, and you say so.
- A command that no longer exists, or that cannot run in this environment, is
  a FAIL with that as the reason. It is not something to substitute for.

## Your answer

```
VERIFY T-n PASS
```
or
```
VERIFY T-n FAIL
```

then **one line per step**: what you ran, and what came back. Nothing else —
no summary, no advice, no suggested fixes. Fixing is somebody else's job and
mixing the two makes your report stop being evidence.

**FAIL is a normal outcome and costs nothing.** It sends the work back with
your line in `NOTES:` and it is re-dispatched. A PASS you were not sure about
costs the whole project, because everything downstream is then built on it and
nobody will check again.
