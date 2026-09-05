# Charter — <PROJECT NAME>

**Version.** 1 · **Status.** DRAFT · **Signed.** <not yet> · **Client.** <who>

> **This file is the authority** (P-1). Every requirement traces to a goal here,
> every checkpoint diffs the real work against it, and changing what is being
> built means amending it — which the client signs (P-2). Nothing about the
> project is settled anywhere else.
>
> **The manager owns this file** (P-13). It is amended by a new version, with
> the previous version's text kept below the amendment, because the history of
> what the project was asked to be is part of the record.

## What we are building

<Two or three sentences a stranger could read and understand. What it is, who
uses it, and what they use it for. If this cannot be written plainly, the
interview is not finished.>

## Goals

<Numbered, and each one checkable in principle. Every requirement must trace to
one of these, and a goal no requirement covers is an `orphan-scope` finding
(P-4).>

<!-- example:begin -->
- **G-1** — <one sentence>
- **G-2** — <one sentence>
<!-- example:end -->

## Done means

<The observable conditions under which this project is finished. Not "it works"
— the specific things that will be true. These become the final checkpoint's
checklist.>

<!-- example:begin -->
- **DM-1** — <observable condition>
- **DM-2** — <observable condition>
<!-- example:end -->

## Out of scope

<Explicit, and worth more than it looks: this is the list that lets the pipeline
refuse work without asking. Something here is not built, and a request for it is
a `CHARTER` class question (P-26), which always stops for the client.>

<!-- example:begin -->
- <thing we are deliberately not building, and why>
<!-- example:end -->

## Constraints

**A row states what is true of the tool as it stands, not what is planned for
it.** Two failures, both measured on one project, both in signed text:

**A number that describes something still changing does not belong here.** A
charter said a vendored caller sees "ten lines of traceback"; the figure moved
three times in one day as the code grew, and correcting ten to thirteen would
have bought a day. Cite the requirement that governs the behaviour and let the
number live where it is measured. **The test: if this figure changes when
somebody refactors, it is a measurement and not a promise.**

**And a row must never promise a mechanism that does not exist yet.** A
constraint stating a memory budget *and the formula enforcing it* was signed
while the task building that enforcement was still running — and the task was
then stood down. The row survived, promising a bound nothing applies. **That is
worse than a stale number**, because a stale number is wrong about a detail and
this is wrong about whether the tool does the thing at all. If the mechanism is
deferred, the row says what the tool actually does and what it costs; the
deferral belongs in the risks section with its decision.

**Fitted constants are a special case of both.** A model measured against one
interpreter and one set of data structures is evidence, not verification. If
one must appear, say in the row that it is fitted and unverified — and give it
a test asserting **the model still predicts the measured cost**, which fails
when the model drifts rather than when the code breaks.

<!-- example:begin -->
| Constraint | Value |
|---|---|
| Language / runtime | <e.g. Python 3.12> |
| Build command | <the exact command> |
| Test command | <the exact command, and what a green summary line looks like> |
| Lint / format command | <exact command, or `none`> |
| Target platforms | <e.g. Linux x86-64> |
| Protected paths | <trees the pipeline may read but never write — vendored deps, generated output, sibling repos. The guard enforces these> |
| Model band | <floor> .. <ceiling> |
| Budget ceiling | <tokens, wall-clock, or `none`> |
| Checkpoint cadence | <after how many closed tasks, plus any milestone — e.g. `every 3 tasks, and at each release`. A count of tasks assumes tasks are a similar size and nothing enforces that, so this also carries a size trigger: a task above a stated share of the remaining budget checkpoints at its halfway step-unit. P-30> |
| Priority order | <what wins when two goods conflict, most important first — e.g. `safety > correctness > performance`. Every decision that trades one against another cites this row and says which it sacrificed> |
| Client channel | <how the client is reached, and it is never assumed: `terminal` (a person at this session), `session <name>` (another session or agent, over SendMessage), `both`, or `none — proceed on recommendations and report at checkpoints`. See P-9> |
| Escalation window | <how long a REVERSIBLE question waits before the loop proceeds on its recommendation — P-26. Default 4h> |
| Licence | <e.g. Apache-2.0> |
| Repository | <remote, or `local only`> |
| Public? | <yes/no — decides whether the leak check gates every push> |
<!-- example:end -->

## Risks accepted

<Things known to be true and chosen anyway, so that meeting one later is not
treated as a discovery. Each with the reason it was accepted.>

<!-- example:begin -->
- <risk> — accepted because <reason>
<!-- example:end -->

## Amendments

<Each amendment is a new dated entry naming what changed, why, and the decision
that carries it. The superseded text stays (P-23).>

_None yet._
