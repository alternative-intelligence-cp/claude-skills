# Requirements

Numbered, normative, and **testable or they are not requirements** (P-3). Each
traces up to a charter goal and down to the task that discharges it; the diff
between these three lists is mechanical and is where holes are actually found
(P-4).

> **The manager owns this file** (P-13). A worker that finds a requirement wrong
> reports it; it does not edit here.

**`Status.` is one of:** `open` · `in-progress (T-n)` · `discharged (T-n)` ·
`struck (D-n)`. **Name every task involved** — `in-progress (T-2, T-5)` — where
one task advances a requirement and another completes it. A single id there
would be a compromise recorded as a fact. A requirement whose task is closed is `discharged`, not `open`
— nothing reconciles the two automatically, and a record that says `open` for
work that is finished makes every later reading of this file wrong.

**Acceptance is a command or an observation, never an adjective.** "Fast" is not
a requirement. "`bench/latency.py` reports p99 under 200 ms at 100 concurrent
requests" is one, because there is no argument about whether it happened.

---

<!-- example:begin -->
### R-1 — <short title>

- **Statement.** <what must be true of the finished thing, normatively>
- **Satisfies.** G-1
- **Source.** <interview 2026-09-03 · research/<topic>.md · a named standard>
- **Acceptance.** `<exact command>` → <the output that means it passed>
- **Priority.** must | should | may
- **Status.** open

### R-2 — <short title>

- **Statement.** <...>
- **Satisfies.** G-1, G-2
- **Source.** <...>
- **Acceptance.** `<...>` → <...>
- **Priority.** must
- **Status.** open
<!-- example:end -->
