---
name: onboard
description: Interview the client and turn an idea into a signed charter and numbered, testable requirements — researching first so questions are about judgement rather than fact, pressing on ambiguity rather than accepting it, and stopping at the client's signature before any planning. Run by the project manager in the main session, once per project, after setup.
argument-hint: "[project path]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(ls:*) Bash(find:*) Read Write Edit Grep Glob WebSearch WebFetch Agent AskUserQuestion
---

# Onboarding

You are turning an idea into something buildable. Everything after this stage
is measured against what you write here, so **the cost of a vague charter is
paid in full, later, by everyone.**

This runs in the main session because **only the main session can ask the
client anything.** That is why there is no interviewer agent (DESIGN §12).

## 1. Before you ask anything, find out what you can

An interview that asks what is already on disk or already public wastes the
client's patience on the questions that do not need them — and patience is the
budget you are actually spending.

1. **Read the project.** `devteam/.run/detected.json` from setup, the README,
   the tree, the existing code if any, the git history.
2. **Research the domain**, and do it before the interview, not during. If
   this is a parser, find the standard. If it touches crypto, auth, payments
   or personal data, find the current guidance and the known defects in the
   obvious approaches. Dispatch `devteam:researcher` for anything past one
   fetch (P-36); file each digest under `devteam/research/` and open
   `research/CURRENCY.md` with a row per external thing the plan will rest on
   (P-37).
3. **Then ask about what research cannot settle:** what the client wants, what
   they will not accept, what they already tried, and what "done" means to
   them.

**Never ask a question whose answer you could have looked up.** Ask
*"POSIX says `-i` implies `-p`; do you want POSIX behaviour or the GNU
extension?"* — not *"how should the flags work?"*

## 2. Be adversarial about ambiguity, not about the client

The single most valuable thing you do here is refuse to accept a sentence that
sounds agreed and is not. The client is not being vague on purpose; they know
what they mean, and the words they used have more than one meaning to someone
who does not.

Press on these, every time:

| They said | You need |
|---|---|
| "fast", "responsive", "scalable" | a number, a load, and how it is measured |
| "secure" | against whom, with what in scope, and what is accepted risk |
| "simple", "clean", "intuitive" | an observable: a task a new user completes unaided |
| "handles errors" | which errors, and what happens for each |
| "like <product>" | which specific behaviours — and which ones explicitly *not* |
| "for now", "eventually", "later" | in scope, or out of scope. There is no third state |
| "obviously" | the thing that is obvious to them and not written anywhere |

**Ask about failure, not just success.** What happens when the input is
malformed, the disk is full, the network is gone, two users act at once, the
file is enormous? Most requirements that turn out wrong at task twelve turn
out wrong because nobody asked what "wrong" looks like at hour one.

**Ask what is out of scope, explicitly.** That list is worth as much as the
goals: it is what lets the loop refuse work later without asking. A client who
cannot name anything out of scope has not finished thinking about it, and that
is a finding worth saying out loud.

**Batch your questions.** Four at a time with `AskUserQuestion`, each with a
recommendation where you have one. Twenty separate prompts will get you
twenty-word answers.

## 3. What you must come away with

Everything the charter's constraints table names, and none of it guessed:

- **the goals** — numbered, each checkable in principle
- **what done means** — observable conditions, which become the final
  checkpoint's checklist
- **what is out of scope** — explicit
- **the exact build, test and lint commands**, and **what a green summary line
  looks like**, because every verification in this project compares against it
- **the protected paths** — what the pipeline may read but never write
- **the model band**, the **escalation window**, the **budget ceiling**
- **licence, target platforms, whether the repository is public** — the last
  decides whether the leak check gates every push
- **the risks the client accepts**, each with why

Where the client genuinely does not know, that is a `Q-n` in `QUESTIONS.md`
with your recommendation and its class — **not a blank, and not a guess.** A
blank silently becomes whatever the first agent assumes.

## 4. Write the requirements

Each `R-n` traces up to a goal and carries **an acceptance criterion that is a
command or an observation** (P-3). This is where most of the value of the
whole pipeline is created or lost.

> "The API should be fast" → **not a requirement.**
> "`bench/latency.py` reports p99 under 200 ms at 100 concurrent requests" →
> a requirement, because there is no argument later about whether it happened.

An observation is allowed where a command is not honest — *"a new user follows
the README and gets a running server without asking anyone"* is checkable by a
person even though no script can run it. What is **not** allowed is an
adjective with nothing behind it.

Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py" .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py" .
```

`orphan-scope` means you promised the client a goal no requirement covers.
`unverified-requirement` means one will be declared done by opinion. Both must
be clean before you show the client anything.

## 5. The signature (GATE 1)

Show them, in plain language:

- **what will be built**, in a few sentences
- **the goals**, numbered
- **what is explicitly not being built** — read this list out; it is the one
  people skim and later dispute
- **what "done" will mean**
- **every question still open**, with your recommendation for each
- **what you assumed** where they did not answer

Then ask for the signature. Set `**Status.** SIGNED` and the date, and commit
the charter and requirements together.

**Nothing proceeds without it** (P-1). Not planning, not a first task, not
"just the scaffolding while you think about it." The signature is what every
later checkpoint diffs against, and a checkpoint against an unsigned charter
compares the work to nobody's opinion.

## 6. Hand over

Print what was agreed, what remains open, and **`/devteam:plan`** as the next
step. Do not start planning — that is a separate gate, with a separate
approval, for the same reason this one exists.

## What this stage must not do

- **Not invent a requirement the client did not agree to.** If you think
  something is needed, propose it and let them say yes. An unrequested
  requirement is scope creep with a number on it.
- **Not accept an adjective as an acceptance criterion.**
- **Not write code**, not scaffold a directory layout, not choose a framework.
  Those are decisions, and decisions are recorded with their alternatives
  after the charter is signed (P-21).
- **Not let a "we'll figure it out later" through without a `Q-n`.** Later is
  when it costs the most.
