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
- **Estimate.** tokens=<n> minutes=<n>
<!-- example:end -->

> **`Kind.` decides what this task owes.** `implementation` (the default) owes
> at least one requirement. A `probe` or a `spike` owes an **Informs.** naming
> the requirement or goal it de-risks, and discharges nothing — that is what a
> probe *is*. A `chore` owes a **Because.** A task with neither a requirement
> nor a reason is one nobody agreed to.

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
