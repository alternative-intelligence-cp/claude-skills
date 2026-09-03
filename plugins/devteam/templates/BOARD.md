# The board

**Live state, and the lock** (P-11). What is claimed, what is blocked, what is
done. The durable plan is [`REQUIREMENTS.md`](REQUIREMENTS.md) and
[`tasks/`](tasks/); the past is [`RECORD.md`](RECORD.md).

> **The manager owns this file** (P-13). A supervisor or worker never edits it —
> the manager claims before dispatching and releases when the task closes. That
> is what keeps two agents out of one scope and removes every merge conflict by
> construction.
>
> **A claim is a commit.** The history of this file is the record of who worked
> what and when, at no extra cost.

**Updated.** <date> · **Width.** 1 · **Phase.** <onboard | plan | build | harden | deliver>
**Environment.** <pin id> · `.run/env/<pin>/` · pinned <date>
**Writer.** `<session id>` since <date> — one writer here (P-13). If this names
a session that is not you, do not write in `devteam/`. This file is exempt: it
**is** the lock, and taking it is always possible and always in the history.

---

## Legend

| State | Means |
|---|---|
| `—` | not started, nothing blocking it |
| `CLAIMED <label>` | a supervisor owns this task; the in-flight table says what it is doing |
| `BLOCKED on T-n` | cannot start until that task is `DONE`. The reason is always a named task, never "waiting" |
| `DONE` | closed, verified, and released |

## In flight

| Task | Title | Agent label | Since | Model | Scope | Note |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | nothing running |

## Tasks

| Task | Title | Discharges | Depends on | Scope | State |
|---|---|---|---|---|---|
<!-- example:begin -->
| `T-1` | <title> | R-1 | none | `src/…` | — |
<!-- example:end -->

## Questions for the client

| # | Class | Raised | Question | Recommendation | Window expires |
|---|---|---|---|---|---|
| — | — | — | nothing pending | — | — |

## Decided without the client

<Every `REVERSIBLE` question the loop proceeded on (P-27). Listed at every
checkpoint while reversal is still cheap. This table emptying is not the goal —
the client confirming or reversing each row is.>

| # | Decision | Proceeded | Reviewed at |
|---|---|---|---|
| — | — | — | — |

---

## Claim protocol

1. The manager writes `CLAIMED <label>` against the task, adds an in-flight row
   naming the task, the label `T<n>-<slug>-<HHMM>`, the time, the model and the
   **declared scope**, and commits: `board: claim T-n`.
2. A claim is refused if its scope intersects any live claim (P-12). Scope
   overlap is checked before dispatch, never discovered afterwards.
3. One supervisor works that task. When it reports, a **fresh verifier** runs
   (P-18). Nothing moves here before `PASS`.
4. On `PASS` the claim is released, the scope is freed, and any task blocked on
   it is re-checked.
5. A claim with no live agent in this session is stale — recovery runs before
   any new dispatch (P-14). After a session restart, **every** claim is stale.
