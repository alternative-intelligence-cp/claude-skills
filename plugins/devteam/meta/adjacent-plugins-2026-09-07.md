# Three adjacent teams, and why they are one plugin's variations

Written 2026-09-07, from the owner's own notes, while 0.2.9 was planned and
before it ran. **This is not a plan and nothing here is committed to.** It is
the reasoning available at the moment the candidates were first written down,
recorded so that 0.3's planning starts from something rather than from a blank
page — and so that the reasoning can be argued with later rather than
reconstructed.

## 1. Where this came from

The owner keeps a notepad of tasks he needs done from time to time. Three
entries in it are team-shaped, and he asked whether `devteam` already covers
them or could be modified to. Reproduced exactly as written, because his
wording is the requirement and a paraphrase would lose it:

```
maintainanceTeam
 - file bug reports
 - triage
 - fix bugs
 - handle pull requests - entire process from verification/rejection to merge
 - update documentation

designTeam
 - discover full details of scope ,constraints, and expected producables
   - producables may involve
     - procurement/generation of audio,video,images
     - layouts
     - typography
     - branding
     - mockups
     - general design work
 - verify producables meet criteria

 researchTeam
 - discover full details of scope ,constraints, and expected producables
 - find and/or generate sources to get the requested data
   - web searches
   - tests
   - etc
 - aggregate data sources into something meaningful
 - create charts if neccessary
 - verify data in the producables as much as possible and cite all sources
 - verify producables meet criteria for content, formatting, etc.
```

## 2. The observation that organises all three

**The notes give it away themselves.** *"discover full details of scope,
constraints, and expected producables"* appears **verbatim in two of the
three**, and it is [`skills/onboard`](../skills/onboard/SKILL.md) almost word
for word — interview the client, press on ambiguity, produce numbered testable
requirements. All three then share the same spine after it: plan the work,
dispatch a worker per unit, verify each before it is accepted, deliver against
declared criteria.

**So these are not three plugins. They are three configurations of one**, and
exactly three things differ between them:

| | what a **producable** is | what **verified** means | what **triggers** the work |
|---|---|---|---|
| devteam | code | the verification command exits 0 | a client with an idea |
| research | a sourced digest, a chart, a report | an independent re-read of the cited source | a question |
| maintenance | a patch, a merged PR, a doc update | the existing suite still passes | **an event that arrives** |
| design | an image, a layout, a mockup, a brand | partly mechanical, mostly a reading | a brief |

Everything else — the sandbox, the promotion gate, the board, the writer lock,
the checks, the checkpoint, rotation, the escalation classes — is common.

## 3. What already exists, per team

**Substantially covered today:** `onboard` (scope discovery, for all three);
`research`/`researcher` (one fact, dated, sourced, primary source);
`review` (reads a PR against what it claims to discharge, comments and
recommends); `audit` (adversarial, reports without fixing — this is *file bug
reports* and the input to *triage*); the `documenter` agent (*update
documentation*); `checkpoint` (criterion-by-criterion against a signed charter
— this is *verify producables meet criteria*, for criteria that can be stated).

**The whole worker spine is common and already built**: `plan`, `supervise`,
`work`, `verify`, the sandbox, the promotion gate.

## 4. `researchTeam` — first, and it is not close

Smallest gap from what exists, one clean new mechanism, and it is **useful to
the other two**, both of which need sourced facts.

**The new mechanism, stated so it can be built:** `devteam:verify` re-runs a
command and reads an exit code. **A research claim has no exit code.** Its
verification is an *independent re-read of the cited source* — the same shape
as the existing verifier (an independent re-check before anything moves) with a
different instrument. That is a well-defined thing to build.

### 4.1 The requirements come from the owner's own experience, and they are specific

Asked what has gone wrong with aggregation work before, he named three failures
in this order. **They are the requirement set**, and each is stated here in the
form that makes it checkable:

1. **Omission is the first failure.** *"they would always leave out very
   important things."* A summary can be entirely true and still useless, and
   nothing in the artifact signals what is missing. **Checkable form:** scope
   discovery declares the questions; the deliverable answers each one **or says
   explicitly that it could not**. Two declared lists diffed against each other,
   which is the test this project uses for whether a check is worth having
   (F-113, see [`CHECKS.md`](../docs/CHECKS.md)).

2. **An uncited claim is ambiguous, and the ambiguity is what costs.** *"some
   had no sources listed sometimes and i couldn't tell if they were hallucinated
   or the source just got overlooked."* Those two states are entirely different
   problems and the artifact collapses them into one appearance. **Checkable
   form:** every claim carries a citation, or carries an explicit
   `unsourced: <reason>` marker. A bare claim is a finding. The rule's two
   sides are the claim set and the citation set.

3. **Verification currently costs as much as the original work.** *"you
   basically have to do the research yourself again to try to verify the first
   research."* **This is the metric the plugin should be designed against**, and
   it is a better one than accuracy: a deliverable nobody can afford to check is
   one that will be trusted without checking, which is the worst outcome
   available. Design for the cost of a *spot-check* — one claim, one click —
   rather than for the polish of the summary.

**And the reason this belongs in a tool rather than in a prompt.** He had
already built ad-hoc systems for briefing agents on aggregation work, and
abandoned relying on them: *"that required me to remember my own little systems
which were constantly in flux and that isn't very reliable either."* That is
this project's founding principle turned on its author — a process that depends
on the operator remembering it fails exactly when the operator is busy. The
answer is never *be careful about citations*; it is a declared structure in
which an uncited claim or an unanswered question **shows up as a finding**.

## 5. `maintainanceTeam` — the one real structural difference

**`devteam` is project-shaped: charter, requirements, task graph, GATE 4, the
cycle closes. Maintenance is event-shaped: bugs and pull requests arrive
forever, there is no charter to sign and no *done*.** That is not cosmetic.
The board is a queue rather than a graph, and the checkpoint has no signed goal
to diff against.

**Do not model it as continuous `iterate`.** A bug report resembles a very
small iteration and the resemblance is a trap: `iterate` exists to carry a
charter forward across a deliberate cycle boundary with the client re-affirming
it, and stretching it over a queue would distort the one mechanism 0.2.9 is
being run to prove.

**Its headline feature is the exact thing `devteam` deliberately refuses, and
that is the first design question rather than a detail.** `devteam:reviewer`
*cannot push, merge, close or approve*.
[`CONSOLIDATION.md`](../docs/CONSOLIDATION.md) item 5 closes with: the
outward-facing operations are *"still withheld by name rather than wrapped,
because their consequences outlive any sandbox and no overlay helps… if the
wrapper idea has a remaining home it is those, and no finding has asked for it
yet."*

**This note is that finding.** *"handle pull requests — entire process from
verification/rejection to merge"* is a request to build what item 5 left open.
Structural containment does not help: an overlay makes a worker's writes
harmless because they can be discarded, and a merge cannot be. So the mechanism
has to be the other one item 5 names — deliberate, on the record, having said
why — and it needs designing before anything else in this plugin.

## 6. `designTeam` — last, and scoped honestly

**Its verification story is the weakest of the three, and pretending otherwise
would be the failure.** *"Verify producables meet criteria"* is, for most design
criteria, a **reading** — and [`CONSOLIDATION.md`](../docs/CONSOLIDATION.md)
item 4 is explicit that separating a criterion naming a *method* from one naming
a *property* is a reading, and that this project refuses those everywhere.

**What genuinely can be checked**, and it is not nothing: contrast ratios
against a stated standard; asset dimensions and formats; font licences; every
screen a declared flow names actually existing; a palette matching declared
tokens. All of those are two declared sides.

**What cannot** is whether the design is any good. Item 4's own answer applies
unchanged: what you have instead is a **moment** — one place where every
criterion is read at once, by a person, deliberately.

**It also drags in a permission class the pipeline has never had.**
*Procurement* of audio, video and images means spending money and accepting
licence obligations, both outward-facing and both outliving any sandbox. That is
the same family as §5's merge question and should be answered with it, not
separately.

## 7. On extracting a shared core

The common half is large: the sandbox and promotion gate, the board, the writer
lock, the checks and their controls, `onboard`, the escalation classes,
rotation. Extracting it is clearly right **eventually**.

**Not yet, for two reasons.** With one consumer you are guessing at what is
common; with two you can see it — so the extraction should happen when the
second plugin exists and is shaped by both, not before. And `devteam` has still
never run on a real project, so extracting a core from it today means building
on the thing [`PAIRS.md`](../docs/PAIRS.md) row 20 says is *still surprising
itself*. Row 20's reasoning applies unchanged to a second plugin as it does to
self-application.

## 8. Recommended sequence

1. **Run 0.2.9.** It says whether the spine works at all. Everything below
   assumes it does, and row 20's judgement gates the rest.
2. **`researchTeam`.** Smallest gap, one clean new mechanism, useful to the
   other two, and the lowest stakes if it is wrong — a bad digest is visible,
   a bad merge is not.
3. **Extract the shared core**, shaped by two consumers rather than one.
4. **`maintainanceTeam`**, answering the merge-authority question first,
   because it is the plugin's premise and not a feature of it.
5. **`designTeam`**, scoped to the mechanical half plus a named review moment,
   with the procurement permission class answered alongside §5's.
