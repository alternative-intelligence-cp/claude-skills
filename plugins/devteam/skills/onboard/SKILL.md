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
3. **Check the project-family conventions.** Constraints the client has stated
   once, for a family of projects, that no single charter is the natural home
   for — a toolchain required or forbidden, a verification obligation, a
   standard, where shared resources live:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/conventions.py" match <project> [tags]
   ```

   **Put each one to the client as a question and record the answer either
   way.** They are not defaults and must never be applied silently:

   - **Confirmed** → it becomes a charter constraint or a numbered decision
     citing the convention id, so the project's own record stands alone.
   - **Declined** → a decision recording *that it was declined and why*. "This
     project deliberately does not follow the house rule" is information; an
     unnoticed omission is not, and is indistinguishable from an oversight six
     months later.

   **A `safety` convention is not declined casually.** Declining one is a
   `CHARTER` question (P-26): it stops, it needs the client to state **what
   makes this project different**, and that reason is recorded. A convention
   marked `safety` exists because somewhere in this family a wrong answer hurts
   somebody, and the most likely reason it is being declined here is not that
   the project is genuinely exempt — it is that nobody remembered to mention
   it, and the client is agreeing with an agent who sounded confident.

   **This is the case the whole feature is for.** A client onboarding one
   library out of many will not restate the family's safety constraints every
   time; they have said them once and reasonably believe that is enough. The
   agent noticing that strict constraints hold across the rest of the family
   and *asking whether they hold here too* is worth more than every other use
   of this registry combined — and it costs one question.

   The point is **recognition rather than recall**. The client already knows
   these; what costs them is having to remember to say so at the right moment,
   every time. A list they can confirm or reject in seconds is a different
   task from an empty page they must fill from memory — and the person paying
   the memory tax is the one who least needs another thing to hold in their
   head.

   **Report an empty result as loudly as a full one.** If nothing matches, say
   so explicitly — *"I have no standing constraints on record for this project;
   is that right?"* — rather than moving on in silence. This is the case the
   feature most exists for: a client running several projects at once can lose
   track of which agent was told what, and end up believing they told **this**
   one a constraint they only mentioned elsewhere. **The agent that was not
   told has no signal that anything is missing**, so it proceeds confidently on
   an incomplete picture while the client proceeds confidently believing it was
   covered, and nothing anywhere feels wrong. One line naming the absence is
   the only thing that gives them a chance to notice.

   **Nothing here was inferred, and nothing may be.** A convention exists
   because the client stated it. A pattern noticed in their past decisions is a
   hypothesis, and one that grows more confident with repetition whether or not
   it is true — most confident exactly where a real exception costs most. If
   you think you see a pattern, ask about it; do not record it.

4. **Then ask about what research cannot settle:** what the client wants, what
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

**Batch your questions, over whichever channel the client is on.** Four at a
time, each with a recommendation where you have one. Twenty separate prompts
get you twenty-word answers.

**Do not assume the client is a person at this terminal.** They may be another
session, an agent, or a script, and the channel is the charter's `Client
channel` row (P-9) — established at setup, before the interview, because you
cannot ask the client how to reach them.

| Channel | How you ask |
|---|---|
| `terminal` | `AskUserQuestion`, four options where they fit |
| `session <name>` | `SendMessage` to that name — same batching, same recommendation per question, and say plainly that you are waiting on an answer |
| `both` | `AskUserQuestion` for anything that fits four options; a message for the rest, and for anything long |
| `none` | there is no interview. Say so, write the charter from research and inference with **every** inferred value marked as an assumption, and get it signed at the first checkpoint instead |

Over a message channel you lose the four-option affordance, so **write the
options into the question and number them** — and keep the recommendation
first, because a reader scanning a wall of text reads the first line.

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
- **the checkpoint cadence** — after how many closed tasks, and at which
  milestones. Nothing else supplies it, and a project that reaches its first
  close with no cadence recorded has nothing to consult at exactly the moment
  it first needs one
- **the priority order** (P-20b) — what wins when two goods conflict
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

**Write `Requires-write.` in the same breath as the criterion** — every path the
criterion touches. It takes a line and it is the only moment anyone is in a
position to write it: you have just decided what the sentence means, and the
paths follow from that. Planning happens much later and draws scopes by module;
nobody is present at both moments, which is exactly why the mismatch kept
surviving to a verifier. `check_trace` compares the two lists so that neither
party has to.

If the tree does not exist yet, name the paths the plan will create. Guessing
slightly wrong is fine — the check misses rather than misfires on an understated
list, and a wrong guess is a declaration somebody can dispute. Writing nothing
is the only answer that buys nothing.

An observation is allowed where a command is not honest — *"a new user follows
the README and gets a running server without asking anyone"* is checkable by a
person even though no script can run it. What is **not** allowed is an
adjective with nothing behind it.

### Write requirements as rules, not as lists of cases

**This is the single most expensive mistake available at this stage**, and it is
invisible until late. A goal quantifies: *"the tool fails with a clear message
rather than a traceback"* is a claim about **every** failure. A requirement that
answers it with *"a missing file prints one line and exits non-zero"* has
answered it for one case and looks, to every check in this pipeline, like
complete coverage.

What follows is that each new gap — undecodable input, a broken pipe, memory
exhaustion, a filename containing a newline — arrives as a surprise, gets its own
requirement, and leaves the pattern intact. The list grows and never closes,
because a goal quantifies over a domain and a list cannot.

| Instead of | Write |
|---|---|
| "a missing file prints one line and exits non-zero" | "**any** failure to read the input prints one line naming the path and exits non-zero, with no traceback — a missing file, an unreadable one, a directory, undecodable bytes, an interrupted write" |
| "rejects an empty username" | "**every** field rejects input outside its stated domain, with a message naming the field" |
| "handles a 404 from the API" | "**every** non-success response is surfaced as a typed error; none is retried silently" |

**The enumerated cases become the acceptance criterion, not the requirement.**
The rule is what must hold; the list is how you check it, and it is allowed to be
incomplete because it is a sample rather than a definition. Then the next gap
found is a **missing test** against a requirement that already covered it —
cheap, and nobody's fault — rather than a missing requirement, which means the
charter promised something nobody owned.

**Ask the client the quantifier explicitly.** *"When you say it should fail
clearly — for every failure, or only the ones we have thought of?"* They will
almost always say every, and then the requirement has to say so.

Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_trace.py" --pre-plan .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_refs.py" .
```

**`--pre-plan` matters here and only here.** No task exists yet, so every
requirement is uncovered by construction and a plain run can never exit 0 at
this gate. The flag suppresses that one class and nothing else — `orphan-scope`
and `unverified-requirement`, the two this stage actually needs, still apply.
Drop the flag from `/devteam:plan` onward, where an uncovered requirement is a
real finding.

`orphan-scope` means you promised the client a goal no requirement covers.
`unverified-requirement` means one will be declared done by opinion. Both must
be clean before you show the client anything.

## 4b. Offer to record what generalises

At the end, when the answers are in, ask one question: **"do any of these apply
to your other projects too?"** If the client says a constraint is
family-wide — a toolchain rule, a standard, a shared location — offer to record
it as a convention so they are not asked to recall it next time:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/conventions.py" new CNV-<n>
```

**Ask; never decide.** The client saying "that goes for everything I build" is
a statement. Your noticing that they answered the same way twice is not, and
the difference is the whole safety property of this feature.

**This is not only an end-of-interview question.** Any time the client states
something that sounds family-wide — during the interview, at a checkpoint, in
answer to an escalation — offer to record it then. A constraint that lives only
in this conversation is one the next project cannot see, and the client will
reasonably remember having said it.

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
