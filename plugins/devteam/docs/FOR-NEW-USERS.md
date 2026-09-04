# Using devteam on real work

You have been asked to run a piece of real work through this pipeline. This
says what it does, what it costs you, and — the part that matters most — what
to do when it gets in your way.

## What it is

A development pipeline made of skills and agents. It interviews you into a
written charter, turns that into numbered requirements, plans tasks against
them, and runs supervisors that dispatch workers and verify their output. Its
central claim is that **nothing is believed without evidence**: every report is
re-run against the committed tree by someone who did not do the work.

It is **not** autonomous. It stops for decisions that cannot be undone, and for
anything that changes what is being built.

## Install

The plugin loads from a symlink; ask the operator to add it if it is not there.
Then, in the project directory:

```
/devteam:setup        scaffold devteam/, agree permissions, prove the guard fires
/devteam:onboard      the interview → a charter you sign
/devteam:plan         requirements → a task graph you approve
/devteam:run          the loop
/devteam:status       where is it, at any time
/devteam:checkpoint   diff what exists against the charter
```

**Give it a repository it owns.** A `devteam/` directory makes its write guard
police that whole tree for *every* session, not only its own agents — so if
another agent or orchestrator writes the same repo, their writes get refused
while a task is running. The symptom is intermittent, which makes it miserable
to diagnose. Setup asks about this; answer it honestly.

## What it costs you

Say five gates where you must answer: the interview, the plan, an irreversible
or scope-changing question, a checkpoint that finds drift, and the final
review. Between those it runs unattended.

It is **front-loaded on purpose**. The interview and the plan will feel slow
relative to just writing the thing. Whether that trade pays is exactly what
we are trying to find out, and **your answer is data whichever way it goes.**

## The one instruction that matters

**When a skill tells you to do something impossible, wrong, or absurd — report
it. Do not work around it.**

This is the opposite of the usual instinct, and it is the whole point of the
exercise. A workaround makes your afternoon better and leaves the defect in
place for everyone after you. A report costs you three sentences.

The same goes for anything that is merely *tedious*. Eighteen findings so far
have made this pipeline stricter; **not one has made it simpler**, and that is
a suspicious record. If a step is ceremony that buys nothing, that is the most
useful thing you can tell us.

## When to stop using it

**If it is obstructing the actual work, stop, and say so.** That is a
legitimate outcome and a better finding than a grudging completion. You have
real deliverables; this must earn its place against them.

Tell us where you stopped and what made you stop. "I abandoned it at task three
because the ceremony was not paying for itself" is the single most valuable
sentence you could send back.

## What to send back

Problems in the shape of [`REPORTING-PROBLEMS.md`](REPORTING-PROBLEMS.md), and
at the end, four sentences on: what it was good at, what it was bad at, whether
you would use it again unprompted, and what you would delete.
