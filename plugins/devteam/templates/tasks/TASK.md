# T-<n> — <title> — PLANNED

<The task file is the unit of claim (P-11), the contract the supervisor works
to, and the place its execution record lands. One file per task; the title line
carries the status and is the first thing recovery reads (P-14).>

<!-- example:begin -->
- **Kind.** implementation
- **Discharges.** R-1, R-4
- **Depends on.** none
- **Scope.**
  - `src/<area>/`
  - `tests/<area>/`
- **Gate.** <what must be true to call this task done — a condition, not a
  feeling>
- **Verify.** `<the exact command that proves the gate, and its expected summary
  line>`
- **Estimate.** tokens=<n> minutes=<n> model=<steps>x440000x1.78+150000
<!-- example:end -->

> **The estimate names its model, not just its number (P-41).**
> `tokens = steps × unit × (1 + r) + overhead`, with `unit` 440,000 per
> estimated step-unit (6 tasks, cycle 0.1), `r` 0.78 (10 tasks, C-3 §4) and
> `overhead` 150,000 per task. **Estimate the reading, not the typing** — the
> first measured task came in at 26x because the estimate counted the code to
> be written. A bare number can only be right or wrong; a model can be
> corrected, and the next measurement then fixes every remaining estimate at
> once. `r` is re-fitted at every checkpoint from the harness's own budgets.
> `steps` is the steps as planned: while this title reads `PLANNED`,
> `check_trace` compares it with the step lines under `## Steps`, struck ones
> included (`estimate-step-mismatch`). A step the supervisor adds once the
> task runs is what `r` prices, so the estimate is not re-stated for it.
>
> **`Kind.` decides what this task owes.** `implementation` (the default) owes
> at least one requirement. A `probe` or a `spike` owes an **Informs.** naming
> the requirement or goal it de-risks, and discharges nothing — that is what a
> probe *is*. A `chore` owes a **Because.** A task with neither a requirement
> nor a reason is one nobody agreed to.

> **`Discharges.`, `Depends on.`, `Informs.` and `Re-establishes.` hold
> identifiers and nothing else** — `none`, or bare identifiers separated by
> commas. The check reads a sentence in one of them as nothing and names it, so
> a task the sentence mentions is never a dependency and a requirement it
> mentions is never discharged. **Put the reason on a bullet of its own**,
> after the field, labelled by what it explains:
> `- **Why T-2 first.** it writes the schema this task reads`.
>
> **`Re-establishes.`** is for a fix under a requirement another task
> discharged: it names that requirement, whose status keeps its
> `discharged (T-n)`, and it is this task's motivation in place of a
> discharge. Write `- **Discharges.** none` beside it.

> **Scope is a promise about what this task writes** (P-10, P-12). The manager
> refuses to claim a task whose scope intersects a live claim, and the guard
> refuses a write outside it. A scope that turns out too small is an escalation,
> never a quiet widening.

## Steps

<One worker per step (P-8). Each carries a complexity class (P-40) and the
command that judges it. A step whose verification is "looks right" is not a
step.>

- [ ] **S-1** — <goal> · class: `standard` · verify: `<command>`
- [ ] **S-2** — <goal> · class: `mechanical` · verify: `<command>`

## Execution record

<Appended as work happens: what was done, what was found, what it cost. The
REPORT block is always the **last** entry (P-16), and `check_report.py` parses
it.>
