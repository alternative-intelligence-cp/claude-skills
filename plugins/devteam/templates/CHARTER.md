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
| Escalation window | <how long a REVERSIBLE question waits before the loop proceeds on its recommendation — P-26. Default 4h> |
| Licence | <e.g. Apache-2.0> |
| Repository | <remote, or `local only`> |
| Public? | <yes/no — decides whether the leak check gates every push> |

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
