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

**`Exercises.` is what the acceptance criterion touches, and it is what makes
the criterion's LEVEL checkable.** A criterion written in process language —
*"exits non-zero"*, *"fails under the default and succeeds under
`--encoding cp1252`"* — cannot be discharged by a task that owns only a module:
the task can make the behaviour true and not the sentence true. That happened
three times in one project before this field existed, and each time it surfaced
late, from a verifier running the command end to end after the module task had
closed.

So list every path the criterion exercises. `check_trace` then reports
`unreachable-acceptance` when no single task discharging the requirement has
all of them in scope. It is set containment over two declared lists — no
guessing at English, and it cannot misfire on an ordinary plan, because an
understated list makes the check *miss* rather than invent.

**Write it here, when you write the criterion, and supersede rather than edit
it later.** The person writing the criterion knows what it touches; they do not
need to know the eventual scopes, which is why this works across the seam
between onboarding and planning. If planning finds the list wrong, that is a
recorded amendment (P-23) — because planning also draws the scopes, and an
author quietly editing *both* lists until they agree has turned the check off
without anyone seeing it happen. If the tree does not exist yet, name the paths
the plan will create.

---

<!-- example:begin -->
### R-1 — <short title>

- **Statement.** <what must be true of the finished thing, normatively>
- **Satisfies.** G-1
- **Source.** <interview 2026-09-03 · research/<topic>.md · a named standard>
- **Acceptance.** `<exact command>` → <the output that means it passed>
- **Exercises.**
  - `<every path the acceptance command touches>`
- **Priority.** must | should | may
- **Status.** open

### R-2 — <short title>

- **Statement.** <...>
- **Satisfies.** G-1, G-2
- **Source.** <...>
- **Acceptance.** `<...>` → <...>
- **Exercises.**
  - `<...>`
- **Priority.** must
- **Status.** open
<!-- example:end -->
