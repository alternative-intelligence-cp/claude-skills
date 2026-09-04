---
name: iterate
description: Open a second or later cycle on a finished devteam project — carrying the charter, decisions, record and audits forward, re-interviewing only what using the thing actually taught, and amending rather than starting over. Use when the client has accepted a cycle and wants more, or has used it and found it wrong.
argument-hint: "[project path]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git log:*) Bash(git diff:*) Bash(git add:*) Bash(git commit:*) Read Write Edit Grep Glob WebSearch WebFetch Agent AskUserQuestion
---

# Iterating

A finished cycle is not a finished project. This is how the next one starts
**without throwing away what the last one learned** — which is the whole reason
the record, the decisions and the audits were kept.

## 1. Is this actually an iteration?

Three different things, and picking the wrong one is expensive:

| The client says | It is | Do |
|---|---|---|
| "one more thing" — an addition inside the existing goals | **an amendment** | add requirements to the current charter, plan, build. No new cycle |
| "now that I've used it…" — the goals were right and something under them was wrong or missing | **an iteration** | this skill |
| "actually I need something else" — the goals themselves were wrong | **a new project** | a fresh charter. Say so; do not iterate a charter into a different product |

**The distinguishing question is whether the goals survive.** If they do, iterate.
If G-1 has to change to describe what the client now wants, that is a new
charter wearing an old one's clothes, and pretending otherwise buries the
history of both.

## 2. Read the last cycle before asking anything

The client's time is the scarce resource, and most of what you need is already
written. Read, in this order:

1. **`CHARTER.md`** — the goals, and what was explicitly out of scope
2. **`checkpoints/`, last first** — especially the final one. What did it say
   was left undone, and why?
3. **`DECISIONS.md`** — every decision is **still binding** until superseded
4. **`audits/`** — findings that were declined, not fixed. Those are the ones
   that come back
5. **`RECORD.md`** — where the estimates were wrong, which findings recurred
6. **`QUESTIONS.md`** — anything still `open`

**Never re-ask something the record answers.** Arriving at an iteration and
asking the client to re-explain their project is how a pipeline proves it did
not read its own files.

## 3. The interview, which is short and specific

An iteration interview is not the onboarding interview again. Three areas, and
you already know most of the context:

**What did using it teach?** This is the whole point and it is the only
question the record cannot answer. What broke, what was awkward, what turned
out unnecessary, what they reached for and found missing. **DM-7-style
observations are gold here** — the client has now done the thing the last cycle
only predicted.

**Which decisions do you want to revisit?** Show them, and **show the
`proceeded-unreviewed` ones first** (P-27). Those were taken on the client's
behalf under a timeout and this is the moment they were promised a look. Some
have since become expensive to reverse — say which, and say so plainly, because
"we can still change this cheaply" and "this is now load-bearing" are different
answers to the same question.

**What is now out of scope that was in, or in that was out?** Scope moves
between cycles, legitimately. It moves *silently* between cycles, illegitimately.

## 4. Amend; never rewrite

- **The charter gets a new `Version.`**, a new dated entry under `##
  Amendments` saying what changed and why, and **the previous text stays**
  (P-23). A reader must be able to see what the project was asked to be at
  each point, or the checkpoints of earlier cycles become unreadable.
- **Requirements keep their numbers.** A requirement that changes is
  **superseded by a new one** that says what it replaces; it is not edited.
  `R-3` cited in a closed task's record must still mean what it meant then.
- **A decision that is reversed gets a new number** recording what it
  supersedes and what changed to justify it. This is where the last cycle's
  declined alternatives earn their keep: the argument is already written, and
  usually the new evidence is exactly the thing that alternative predicted.
- **Requirements discharged in the last cycle stay `discharged`.** They are not
  reopened because a new cycle started. If one is now wrong, supersede it.

## 5. Then the ordinary loop

New tasks are numbered onward — `T-8`, not `T-1` again — because the record and
the git history refer to the old ones and reused numbers make both unreadable.
`RECORD.md` gets a `cycle 2 opened` line and continues; it is append-only across
cycles, and the cross-cycle picture is the thing no single cycle can see.

Then `/devteam:plan` and `/devteam:run` as normal, and the gates are the same:
the client approves the amended charter, then the plan.

## 6. What an iteration is for, and what it is not

**It is for** the things only use can teach, the decisions taken without the
client, and the findings an audit raised and a cycle declined.

**It is not** a way to avoid saying a cycle failed. If the last cycle did not
meet its charter, the checkpoint says `DRIFTED` and that is the honest record;
opening a new cycle on top does not discharge the old one's requirements and
must not read as though it did.

**And it is not a fresh start.** The value of the second cycle is precisely
that the first one's reasoning is still on disk. A project that iterates by
deleting `devteam/` and running `/devteam:setup` again has thrown away the only
thing that makes the second cycle cheaper than the first.
