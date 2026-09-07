# Cycle 0.2 — structural containment, rotation, and the queue the run left

> **For the implementing session.** You have none of the planning conversation
> and cannot ask its author anything. This file is the map; the subcycle files
> are the territory. Read this whole file first, then §3's reading list, then
> the subcycle you are working, in full, before touching the tree.

## 1. What this cycle is for

Cycle 0.1 ran the pipeline end to end once. It worked — thirteen of thirteen
requirements discharged, 531 tests green, every check clean — and produced
149 findings, roughly five in six of them defects in the pipeline rather than
in the fixture it built. The fixes that could land during the run landed
during the run. What remained is of three kinds, and this cycle takes all
three:

1. **A class of defect the guard cannot close**, because it judges writes by
   parsing command text and the world is wider than its frame. Two measured
   holes: an interpreter heredoc writes unjudged (F-80, F-121), and git
   history is a write with no path (F-71). The owner's answer is to stop
   classifying writes and make the forbidden ones **structurally impossible**
   — a per-worker copy-on-write sandbox. That is subcycles 0.2.0–0.2.4.
2. **The queue in `CONSOLIDATION.md`** — nine items deferred deliberately
   because each only makes sense once the whole run can be read at once.
   Subcycles 0.2.5–0.2.7 take the seven that are ready; the two in item 8 stay
   deferred because their triggers have not fired, and §7 says so.
3. **Two mechanisms that have never produced output**: `/devteam:iterate` has
   never run, and the unreviewed-decision path (P-27) has never had a decision
   to show, because the run's client answered all thirty questions. A
   mechanism that has never fired has not been shown to work. Subcycle 0.2.9
   is the run that fires both.

## 2. The finding that decides the architecture

The spec ([`devteam-sandbox-spec-2026-09-05.md`](../../devteam-sandbox-spec-2026-09-05.md)) treats the sandbox as a fix for
the heredoc hole. **The run's own data says the more expensive class was the
shared git index and history**, which no bind-mount sandbox touches because
`.git` must stay writable. Count them in `.internal/scratch/devteam/RECORD.md`:

| Finding | What happened |
|---|---|
| F-17 | the manager's `git add -A` stole a worker's commit |
| F-66 | a shared index defeated "stage explicit files" — somebody else did the staging |
| F-71 | a path-based guard structurally cannot see a history rewrite |
| F-73 | a second independent instance of the amend trap, different task, different worker |
| F-81 | `git commit --amend -- <paths>` limits content, not which commit is amended |
| F-135 | manager and supervisor share a task file and `git commit -- <path>` cannot split it — **the worker's half of this only**; see the residual below |
| P-12b | the rule that exists only because history is shared |

**A per-worker overlay fixes this class as a side effect of fixing the other.**
Each worker's `.git` writes land in its own upper layer; an `--amend` can only
rewrite that worker's own overlay history; `git add -A` sweeps only that
worker's overlay; the host's index and `HEAD` are untouched until a single,
serialised promotion step applies exactly that task's commits.

**The residual, stated so nobody over-reads the claim.** The manager and the
supervisors stay host-side (L-2) and still share one index and one `HEAD`.
F-129 (a claim commit that incriminates itself) and the manager–supervisor
half of F-135 are theirs and are **not** fixed by this cycle; what protects
them is what protected them in 0.1 — pathspec commits mandated by `run` §4
and `supervise` §6, and the guard's history refusal (P-12b stays in force on
the host). That half is the smaller one: neither role writes product code,
and both write under skills that already forbid the unscoped forms.

Bind-mount designs — including the harness's own built-in Bash sandbox (§4) — leave
`.git` shared and fix only the hypothetical class. That is why this cycle
builds the owner's overlay idea rather than the cheaper variants, and it is
recorded as L-1 below.

## 3. Read, in this order

Everything below is a pointer; nothing here restates content (P-34).

1. `HANDOFF.md` — the state of the record, and what lives in no file
2. `plugins/devteam/docs/CONSOLIDATION.md` — the nine items and their measurements
3. [`../../devteam-sandbox-spec-2026-09-05.md`](../../devteam-sandbox-spec-2026-09-05.md) — the sandbox as measured, §3 corrections and §6 gotchas especially. Then §4 of this file, which corrects it further
4. `plugins/devteam/DESIGN.md` §8 (the guard), §20 ("the one that scopes cannot cover"), §20b (guidance goes where the temptation is), §21 (ceremony)
5. `plugins/devteam/PROTOCOL.md` — all of it; you will be superseding P-10b and P-12b and adding rules, and a rule is amended by a new number, never by editing (P-23)
6. `plugins/devteam/templates/FORMATS.md` — the grammar the checks parse
7. `plugins/devteam/scripts/guard.py` docstring and `check_scope.py` docstring
8. `.internal/scratch/devteam/checkpoints/C-3-2026-09-05.md` — what a final review looks like, and what the run left undone

## 4. What the planning session measured that the spec did not know

Read against the spec's §2 and §4. All `MEASURED` 2026-09-05 unless marked.

**4.1 The baseline still holds.** `uname -r` → `7.0.0-30-generic`;
`bwrap --version` → `bubblewrap 0.9.0` (apt candidate `0.9.0-1ubuntu0.1`);
`fuse-overlayfs` missing; `kernel.unprivileged_userns_clone` → `1`;
`apparmor_restrict_unprivileged_userns` → `0`;
`unshare --user --map-root-user true` → exit 0. So the two-stage composition
in spec §5 stands. Root filesystem 6.9 TB with 5.5 TB free; 157 GiB RAM — the
upper layer goes on disk and sizing is not a constraint on this machine.

**4.2 The harness already ships a bubblewrap sandbox, and it is not the one
we need.** `strings ~/.local/bin/claude` (Claude Code 2.1.261, a native ELF)
contains a Linux sandbox that wraps a **Bash command string** in `bwrap` with
`--ro-bind / /`, a `--bind` per allowed write path, `--unshare-net` with an
HTTP/SOCKS bridge over unix sockets, `--unshare-pid`,
`--unshare-user --cap-drop ALL`, `--new-session --die-with-parent`, an
optional seccomp filter (needs `@anthropic-ai/sandbox-runtime`), and a
violation tracker. Its settings keys are `autoAllowBashIfSandboxed`,
`allowUnsandboxedCommands`, `excludedCommands`, `enableWeakerNestedSandbox`,
`allowUnixSockets`, `allowLocalBinding`, `allowedDomains`, and
`filesystem.{allowWrite,denyWrite,allowRead,denyRead}`. The owner's
`~/.claude/settings.json` has no `sandbox` key — it is off.
**Corrected 2026-09-07 by 0.2.0**: it now has one — a `filesystem.denyWrite`
entry naming a sibling repository, and no `enabled` — so the built-in Bash
sandbox is still not wrapping commands, but the sentence above is no longer
true as written and the next reader would have trusted it. The binary it was
read from (`2.1.261`) is also no longer the installed one (`2.1.263`).
**Re-read this section before making any flag in it a dependency**; it is a
measurement of a moving target, and it moved within two days.

Three consequences. It sandboxes **Bash only** — `Write` and `Edit` still
execute in the harness process, which is spec §4's objection exactly. Its
configuration is **per session**, so it cannot express a per-task scope. And
its `.git` is shared, so it does not touch §2's class. It is therefore not the
mechanism, but it is **prior art for every bwrap flag we use**, it is what the
guard's docstring meant by "the sandbox's own write-deny list", and it is a
**nesting hazard**: a user who has it enabled will run our `bwrap` inside
theirs. Subcycle 0.2.0 detects that.

**4.3 `PreToolUse` hooks can rewrite tool input.** The binary carries
`updatedInput` (361 occurrences) and `permissionDecision`. That makes a
cheaper architecture possible — the guard rewriting every worker `Bash` call
into a per-task `bwrap` invocation — which closes the heredoc hole without a
headless worker. It does not touch §2's class, so it is **not** this cycle's
main line. It is the fallback if the headless-worker probe fails, specified in
`0.2.0.md` §6, and it is `REASONED` until 0.2.0 measures it.

**4.4 The headless CLI has what a sandboxed worker needs.** `claude --help`
lists `-p/--print`, `--output-format` (json, stream-json), `--json-schema`,
`--allowedTools`/`--disallowedTools`, `--permission-mode`, `--plugin-dir`,
`--model`, `--settings <file-or-json>`, `--session-id`,
`--no-session-persistence`, `--bare` (skips hooks and plugins — **do not use
it** for a worker; the worker needs the `work` skill), `--system-prompt`,
`--append-system-prompt`, `--add-dir`. Whether a headless run inside a cleared
environment can authenticate, load a plugin, and invoke a skill is `REASONED`
and is the first thing 0.2.0 measures.

**4.5 The `Bash` tool's foreground timeout is ten minutes** (its `timeout`
parameter caps at 600000 ms). A worker step routinely runs longer — T-2's
estimate was 150 minutes. A supervisor dispatching a headless worker therefore
**must** run it with `run_in_background`, and `--die-with-parent` then binds
the worker's life to a background shell whose lifetime is not documented.
`REASONED`; 0.2.0 measures it before anything is built on it.

## 5. The map

| Subcycle | What it produces | Depends on | Core? |
|---|---|---|---|
| [0.2.0](../done/0.2.0.md) — probes | the baseline as a script; the overlay smoke test; the headless-worker probe; the background-lifetime probe; the nesting detector; the decision rule for the fallback branch | — | **yes — first, small, and it can change the design** |
| [0.2.1](0.2.1.md) — the harness | `scripts/sandbox.py` with `open`, `run`, `exec`, `status`, `close`; the mount plan; `test_sandbox.py` with the blocked/allowed twins and the interpreter case | 0.2.0 | yes |
| [0.2.2](0.2.2.md) — extraction and promotion | extraction inside the namespace; `sandbox.py promote` with its gate, its lock and its finding classes; controls | 0.2.1 | yes |
| [0.2.3](0.2.3.md) — the worker inside | headless dispatch through the harness; credentials; the guard's parent-session identity; the inside permission set; the liveness file; measured budget | 0.2.2 | yes — **the step that matters** |
| [0.2.4](0.2.4.md) — wiring | the skills, templates, rules, agents, docs and permissions changed to run on the sandbox; P-10b and P-12b superseded; `guard-only` degradation; CONSOLIDATION 5 and 8b closed | 0.2.3 | yes |
| [0.2.5](0.2.5.md) — rotation | **DONE** — manager rotation at every checkpoint, driven from outside the session; questions-as-defects measured and all three fixed; point-of-use re-reads | 0.2.4 (uses measured budget) | yes |
| [0.2.6](0.2.6.md) — the checks | every finding class named against its rule (`docs/CHECKS.md` and an `unruled-finding` check); the audit namespace checked and `open-finding-at-close`; amendment re-affirms every DM; estimate model v3 | 0.2.4 | partly — the F-113 audit is core, the rest can wait |
| [0.2.7](0.2.7.md) — two sweeps | the rule-pairs sweep and the ceremony test, each with a method, a calibration set and a deliverable | 0.2.4 | deferrable |
| [0.2.8](0.2.8.md) — release 0.2.0 | version, self-check, controls, DESIGN §14, CONSOLIDATION rewritten, a new handoff, a fresh `setup` on a throwaway project | everything shipped | yes |
| [0.2.9](0.2.9.md) — the second run | cycle 2 on the fixture through `/devteam:iterate`, client channel set so P-27 fires, rotation at a checkpoint, sandboxed workers at width 2–3, a budget ceiling; what to measure and when to stop | 0.2.8 | yes — it is what the cycle is for |
| [0.2.10](0.2.10.md) — the root-tree allowlist | a declared table of what the repository root holds, a `check_plugin` finding pair that diffs the tree against it, and a hook that refuses a stray write at the root; the mechanism behind the `.gitignore` line | — | small, independent; any time |

**Order.** 0.2.0 → 0.2.1 → 0.2.2 → 0.2.3 → 0.2.4 → 0.2.8 is the shortest
path to a shippable 0.2.0 with structural containment; 0.2.5 fits before 0.2.8
and is the item the owner named most valuable in the queue. 0.2.6 and 0.2.7
are independent of each other and of 0.2.5, and can be dropped or deferred
without invalidating anything else. 0.2.9 needs 0.2.8. 0.2.10 depends on
nothing and is small enough to do in the gap between any two others; its
number sorts after `0.2.1` in a directory listing, and this table is
authoritative over that order.

**If the budget forces a choice**, this is the recommendation and the
reasoning: ship 0.2.0–0.2.4 + 0.2.8 (the sandbox), then run 0.2.9 at a small
width with a hard ceiling. Those exercise every mechanism that has never
fired. 0.2.5–0.2.7 improve a pipeline that already runs; the sandbox and the
second run answer whether the design is right, and that is the information
worth buying first.

## 6. Decisions settled at planning

Numbered `L-n`, local to this cycle. Each records the alternatives declined
(P-21). Do not re-litigate them in a subcycle; if one turns out wrong, record
why in the subcycle file and supersede it here with a new number (P-23).

- **L-1 — a per-worker copy-on-write overlay, not bind-mount allow/deny.**
  *Why:* §2 — the measured expensive class is the shared index and history,
  and only per-worker `.git` isolation removes it. *Declined:* the harness's
  built-in Bash sandbox (per-session, Bash-only, `.git` shared); a hook
  rewriting each `Bash` call into `bwrap` (closes the heredoc hole, leaves the
  index shared, leaves `Write`/`Edit` under a rule). The second is the
  fallback branch, not a competitor.
- **L-2 — the worker is a headless `claude -p` process inside the sandbox.**
  *Why:* spec §4 — an `Agent`-tool subagent executes `Write`/`Edit` in the
  harness process, outside any `bwrap`. Wrapping Bash alone swaps which half
  is unwatched. *Declined:* subagent plus Bash-only sandbox (the fallback if
  0.2.0's probe fails). *Cost accepted:* `ListAgents` cannot see a headless
  worker, so liveness needs a file (0.2.3 §3.5); the worker's transcript is
  not visible from the parent session.
- **L-3 — the merged view is bound at the host repository's own absolute
  path, not at `/workspace`.** *Why:* every dispatch line, task file, check
  and refusal message uses absolute host paths (`REPO:`, `SCOPE:`, `Scope.`).
  Path translation is the F-2 / F-12 class waiting to happen — a rule that
  is right and broken one level above where it is written. *Declined:*
  `/workspace` (the spec's choice; tidy, and it makes every path-shaped rule
  in the pipeline wrong inside the sandbox).
- **L-4 — the network namespace is shared in this cycle.** *Why:* the threat
  model is filesystem writes; the model API must be reachable; the harness's
  own egress bridge (§4.2) is internal to its Bash sandbox and not reusable;
  outward git is made impossible **structurally** by the environment instead
  — no `SSH_AUTH_SOCK`, no `~/.ssh`, no `~/.gitconfig`, no `gh` config, no
  token in the cleared environment, so `git push` has nothing to authenticate
  with. *Accepted risk, stated:* a worker can reach the network — exfiltrate,
  or `pip install` into its overlay. *Trigger for unsharing:* a worker observed
  contacting anything but the model API, or a charter marking the project
  sensitive. *Declined:* building the proxy now — a subsystem no finding has
  asked for.
- **L-5 — promotion is `git bundle` out, `git cherry-pick` in, under a lock,
  gated by the declared scope, and never automatic.** *Why:* at width above
  one the host `HEAD` has moved by the time a worker finishes, so its commits
  must be re-applied, not fast-forwarded; cherry-pick keeps authorship and
  handles binary; the gate is a diff of two declared lists — paths touched
  by the commits against the task's `Scope.` — which is the only kind of
  check that has ever worked here (P-4, F-113). *Declined:* `format-patch` +
  `git am` (kept as the fallback if cherry-pick misbehaves on a measured
  case); fetch and fast-forward (fails whenever `HEAD` moved); promoting at
  sandbox exit (spec S-7: never auto-apply).
- **L-6 — the guard stays: as the lock and protected-path mechanism on the
  host, and as early warning inside the sandbox.** *Why:* the manager stays
  host-side and P-13 must hold against it and against strangers; inside, a
  refusal at the moment of typing is where guidance works (DESIGN §20b) and a
  worker that only learns at promotion that it built on an out-of-scope edit
  has lost the work. *Declined:* turning the guard off inside (loses the
  early message); making the guard the mechanism inside (it is the thing
  being replaced).
- **L-7 — inside the sandbox the permission grant widens to everything
  filesystem-shaped; only outward-facing entries stay withheld by name.**
  *Why:* F-30, F-64, F-76, F-100 — four findings where a command withheld for
  the guard's sake cost a verification chain. Inside an overlay `rm`,
  `python3 -c`, `chmod` and `truncate` can harm nothing that survives the
  sandbox. What stays withheld: `git push`, `gh`, `sudo` (a no-op under
  `--cap-drop ALL` anyway), `pip install` / `uv add` (a design decision, not a
  build step, and it would land in the overlay regardless). *Declined:*
  keeping today's grant inside (pays the guard's price without its need).
- **L-8 — rotation triggers at every checkpoint and is driven from outside
  the session.** *Why:* a manager cannot measure its own context, so the
  trigger must be external and countable, and a checkpoint is already
  countable and already a moment the client may be interrupted; a session
  cannot spawn its own interactive successor. *Declined:* a token or
  wall-clock trigger (uncorrelated with what happened); compaction (a copy of
  a copy — CONSOLIDATION 1).
- **L-9 — this plan is implemented directly by a session, not by running
  `devteam` on itself.** *Why:* the mechanisms being changed — the guard, the
  lock, the dispatch path — are the ones the pipeline would be running under;
  a system modifying its own containment while contained by it is the
  two-writers problem in a mirror. *Cost:* the plugin change is not itself
  a devteam run and gets no independent verifier; each subcycle's §4
  verification commands are the substitute, and 0.2.8's fresh `setup` on a
  throwaway project is the end-to-end check. The second run (0.2.9) is where
  the pipeline runs.
- **L-10 — version 0.2.0; rules superseded, never rewritten (P-23); every
  new check ships its control (P-35); every claim marked `MEASURED` or
  `REASONED`.** Bookkeeping, recorded so nobody argues about it mid-cycle.

## 7. Excluded from this cycle, with the trigger that would include it

| Not built | Why not | Trigger |
|---|---|---|
| the accepted-findings block (CONSOLIDATION 8a) | its trigger has not fired; the manager reported "not yet" when asked | the day a manager reads a finding count and does not read the finding under it |
| the narrow unscoped-commit refusal (CONSOLIDATION 8b) | **narrowed, not retired**: a worker's unscoped commit inside its overlay takes only its own index, so the case shrinks to the host-side actors (manager, supervisors), whose skills already mandate pathspec commits. 0.2.4 records the narrowing | unchanged — an unscoped host-side commit that actually carries another party's staged work |
| network isolation for workers (spec §4's egress subsystem) | L-4 | a worker observed reaching anything but the model API; a sensitive project |
| compiling the declared scope into the mount table (spec §9's mount spec) | a bind cannot express a file that does not exist yet, and binding the parent widens the scope; the promotion gate enforces scope exactly and the guard warns early (L-6) | a worker repeatedly building on out-of-scope edits and losing the work at promotion — the early refusal was not enough |
| the hook-rewrite Bash sandbox (§4.3) | not the main line (L-1, L-2) | 0.2.0's headless probe fails in a way one session cannot fix |
| macOS and Windows | the mechanism is Linux user namespaces; the harness's own sandbox uses seatbelt on macOS and nothing on Windows | a user on either platform. Until then `setup` degrades to `guard-only` loudly (0.2.4 §3.6) |
| the manager's own commit-message claims checked against the tree (F-112) | self-declared and therefore skippable; DESIGN §20b records the shape | somebody asks for it with a measured false claim in hand |

## 8. Cost, as a model rather than a number

> **Corrected 2026-09-07 by 0.2.0, which is the only row that has been run.**
> The token figures below are **not** in a unit that maps to a subscription
> quota, and reading them as if they were will mislead by more than an order
> of magnitude. 0.2.0 is estimated here at `0.3–0.6 M`; its requests actually
> processed `~15.8 M` tokens and cost `$12.23`, because cache reads dominate
> and scale with conversation length rather than with work done.
>
> **The ratios below survive; the absolute numbers do not.** Anchor on the one
> measured row: 0.2.0 cost **1% of a weekly window**, and this table's
> midpoint for it is `0.45 M`. So read every row as `1%` of a week per `0.45 M`
> of the units below, and the remaining core path (0.2.1–0.2.5, 0.2.8) is
> **≈13% of a week** rather than any figure in tokens.
>
> **Write the closing cost of each subcycle in percent of a weekly window**,
> not only in tokens — the owner's display reports percent, so a correction
> recorded in tokens is one he cannot check. See
> [`../done/0.2.0.md`](../done/0.2.0.md) for the worked figures.
>
> **Measured so far, and what it says about sequencing.** Requests are
> `MEASURED` by `scripts/session_cost.py` from each session's own transcript;
> percentages come from the owner's `/usage` and are marked where they do not.
>
> | Subcycle | Requests | Processed | Cost | Share of a week |
> |---|---|---|---|---|
> | 0.2.0 — probes | 104 | `~15.8 M` | `$12.23` | `1%` (read) |
> | 0.2.1 — the harness | 58 | `9.34 M` | `$9.81` | `0.80%` (read) |
> | 0.2.2 — extraction and promotion | 83 | `14.73 M` | `$13.51` | `1.10%` (read) |
> | 0.2.3 — the worker inside | 100 | `18.35 M` | `$14.73` | `0.6–1.2%` (see below) |
> | 0.2.4 — wiring | 256 | `67.4 M` | `$41.81` | `~1` (read; 0–2 by tick) |
> | 0.2.5 — rotation | 159 | `31.80 M` | `$23.92` | `91% → 92%`, one window, boost on: **~1 point** |
> 
> **Four rows now price the same one-point movement at `$12.23`, `$23.92` and
> `$41.81`.** That is a 3.4× spread on an identical reading, measured rather
> than argued, and it is the end of any conversion factor: the dollar column
> and the percentage column are not two views of one quantity. Read the gauge.
>
> **The boundary that breaks comparability first is the WEEKLY RESET, not the
> boost's expiry, and 0.2.5 got this wrong before it got it right.** The boost
> ends **13 September** and that date is salient, so it became the thing to
> plan around. But the window itself **resets on 9 September, 7:59pm** — four
> days earlier. A subcycle whose opening and closing readings sit either side
> of a reset has two readings of two different windows, and subtracting them is
> the same error as summing this column. **Check the reset date in the same
> breath as asking for the reading**; it is printed directly under it, and
> neither number means anything without the other.
>
> So the boost's expiry falls inside the window that begins on **9 September**.
> Whichever subcycle runs in that window should be told before it writes a row
> rather than after — but **not** that it inherits a mid-flight denominator
> change, which is what an earlier version of this note predicted and is
> probably wrong.
>
> **Observed behaviour, from the owner, 2026-09-07: the last promo expiry came
> with a COMPLETE QUOTA RESET, mid-cycle.** So the likely shape on 13 September
> is a refill, not a rescaling — and those break comparability differently. A
> rescaling gives two readings against different scales inside one window; a
> reset gives two readings of two different windows. **Ask which happened
> rather than assuming either.**
>
> His explanation is the convincing one: at expiry, anyone sitting above the
> unboosted cap would be instantly over quota through no action of their own,
> and every alternative — lock them out, grandfather them, prorate — is harder
> to build and harder to explain than resetting everybody. A reset makes the
> question moot, which is very likely why it is the answer.
>
> **And the more important half: RESETS ARE NOT PREDICTABLE FROM THE CALENDAR.**
> The second reset in that week was unscheduled — the owner's reading is that it
> followed a day of API outages and failed requests, where retries would have
> consumed quota for work nobody received, and that a blanket reset got ahead of
> it. **So never infer from "no reset was scheduled" that none happened.** That
> inference is available, cheap, and wrong, and it is exactly the shape of error
> this section already exists to prevent. The reset state is asked for, every
> time, alongside the reading.
>
> **Why the dollar column and the percentage column can never be reconciled,
> asked and answered by the owner 2026-09-07.** He did the obvious arithmetic —
> `$12.28` against a `$200` subscription is 6% of a month, yet the gauge moved
> under 1% of a week — and observed that summing every session's dollars would
> come to three or four times what he pays. Both observations are correct, and
> the explanation is the cache.
>
> **About two-thirds of the dollar figure is the charge for re-reading the
> session's own conversation.** 128 requests against `21.27 M` cache-read
> tokens is one ~166,000-token conversation read 128 times, and the API bills
> every read. Solving the rates from his own four numbers against Opus 5's
> published `$5/M` input and `$25/M` output puts cache reads near `$0.5–0.6/M`,
> which decomposes a typical session here as **~67% cache read, ~20% output,
> ~13% cache write, input negligible**.
>
> Two rules follow, and they are stronger than the ones above because they say
> *why*:
>
> - **Never sum the dollar column.** It adds the same conversation counted once
>   per turn. A session doing identical work in twice as many turns shows twice
>   the dollars, so the sum measures turn count, not spend.
> - **Do not look for a conversion factor.** It cannot be a constant: it depends
>   on the cache profile, and across this project's own sessions output ranges
>   from **0.25% to 1.6%** of tokens processed — a sixfold spread driven purely
>   by session length. What the weekly meter counts is not published. Say so
>   rather than producing a number that looks like an answer.
>
> **So record OUTPUT TOKENS alongside the dollars from here on.** Output is the
> only measured component that tracks work produced rather than conversation
> length, and it is the one plausible correlate of the gauge. It is free to
> record and it is falsifiable — if output-per-point turns out as unstable as
> dollars-per-point, that kills the hypothesis and the column can go.
>
> **The `/usage` output has a lower half, and it answers the question the whole
> table has been circling.** Read in full on 2026-09-07 it said: **"52% of your
> usage came from sessions active for 8+ hours"** and **"17% from
> subagent-heavy sessions"**, plus a breakdown by skill and plugin. Ask for the
> whole output, not the percentage — the top half says how much, the lower half
> says **which behaviour**, and only the second is actionable.
>
> **That is external confirmation of this cycle's premise, from the vendor
> rather than from us.** Cost scales with context size times request count, so
> a session's usage grows superlinearly in its own length — which is exactly
> what the cache decomposition above showed from the other direction. **More
> than half of this account's weekly usage comes from the single thing manager
> rotation (0.2.5) exists to prevent.**
>
> And it is a real reduction, not a redistribution: rotating resets context to
> near zero before it grows again, so the same total work integrated over a
> series of short sessions reads fewer cached tokens than over one long one.
> CONSOLIDATION item 1 argued for rotation on *quality* grounds — compaction is
> a copy of a copy. This says it is also the largest available lever on usage,
> and nobody had noticed because the instrument was in the half of the output
> nobody had pasted.
>
> **One caution before anyone plans against it.** A long session is not
> *wasteful* merely for being long; it may be doing proportionally more work.
> What the two measurements together justify is the weaker and still useful
> claim: **length is a cost driver independent of work done**, so a session
> that has finished a piece of work is worth ending even when it feels cheaper
> to continue.
>
> **The second weekly meter is a SUB-CAP, not a separate budget.** The output
> carries a per-model figure as well as "all models" — on 2026-09-07, `92%`
> all-models against `98%` Fable. The owner's reading, which matches what the
> chart shows: **a model family may consume at most half the total quota**, so
> 100% of the Fable meter is 50% of the whole. Fable at `98%` therefore means
> that family has taken about half the week and is nearly closed out, while the
> account still has 8% of the total left for everything else. **Read both.** A
> subcycle planning against the all-models figure alone can be stopped by a
> per-family cap it never looked at.
>
> **Do not sum this column.** The owner's quota was **reset twice** during the
> week 0.2.0–0.2.4 ran. The display read `88%` at the cycle's start and `91%`
> after all five, which invites *"five subcycles cost three points"* — **it did
> not.** Two full window refills sit inside that span, so the real consumption
> is three points **plus about two windows**, and a plan built on the
> three-point figure underestimates what remains by close to an order of
> magnitude. A reset is invisible in the output; only the owner knows one
> happened. **Ask.**
>
> ### 0.2.4 retired the DERIVED percentage. The READ one stays — it is what the owner plans with.
>
> **`$41.81` moved the weekly display about one point**, against a chained-anchor
> prediction of `3.42%` and an aggregate prediction of `0.91–1.82%`. The
> derivation overestimates by roughly threefold.
>
> **The first version of this note said it moved ZERO points**, because the
> reading was taken while the subcycle was still closing and the display had not
> yet ticked; it read `91%` shortly after. The correction is left visible
> because it is the most useful thing here: **a whole-percent gauge read at the
> wrong moment is indistinguishable from a gauge that did not move**, and a
> session that reads its own cost before it has finished paying it will record a
> zero and believe it.
>
> **The owner supplied the reason, and it is two reasons.** He offered the cause
> as a guess and it is labelled that way in `0.2.4.md`; what follows is enough
> to stop anyone re-deriving the error.
>
> 1. **The numerator may be in the wrong currency.** `MEASURED`, from him: he
>    pays **$200 a month** on a subscription, a single week's `/usage` total
>    would be *"well over $200"*, and the figures matched real billing only when
>    he had fallen through to **API overage**. His hypothesis — `REASONED`, his
>    words, his caveat — is that the dollar column is **API-equivalent pricing**.
>    If so it is not convertible to subscription quota by any fixed ratio,
>    because the ratio moves with model mix and cache profile, which differ
>    between every row above.
> 2. **The gauge is reset without warning, and the display cannot show it.**
>    `MEASURED`, from him: his quota was **reset twice during the week 0.2.4
>    ran** — *"this week I have actually had three weeks worth of usage in
>    one"*. A reset zeroes the numerator, so the `90%` before and the `90%`
>    after are **not two points on one curve**: they are readings from
>    different windows, the second having filled to 90% again. **The comparison
>    that produced this whole finding was never a comparison.**
>
> **This corrects an earlier version of this note**, which gave the second
> reason as a moving denominator and cited the 50% boost. That was wrong: the
> boost has run **since May**, covered all five readings uniformly, and
> therefore explains nothing about their inconsistency. It is left visible
> rather than replaced, because reaching a plausible cause before the owner had
> finished describing what happened is the more instructive failure.
>
> **The boost still matters forward: it ends September 13**, and any reading
> after that is against a denominator 50% smaller than every reading above.
>
> **Do not fit a fifth anchor to it.** Fitting is how the four rows above
> acquired their false precision, and a series whose largest spend produced its
> smallest movement is not one to fit a line through.
>
> **And never tell the owner a subcycle "cost" its dollar figure.** Under a
> subscription that number is a valuation, not his bill. Report it as a size
> measure comparable *between sessions*, which is the one thing it is good for.
>
> **What to write instead, and it is less work rather than more:**
>
> 1. **Dollars and requests**, both read from the owner's `/usage`. Exact, and
>    comparable across subcycles.
> 2. **The gauge reading before and after, as raw observations** — **plus the
>    boost state, and any reset you are told about.** Both are invisible in the
>    output and both silently destroy comparability: a boost changes what `1%`
>    is, a reset means the two numbers are not on the same curve at all. Ask;
>    the owner knows and the display does not say.
> 3. **No share of a week.** Not from tokens, not from dollars, not from a
>    chained anchor. Every session that has computed one has been wrong.
>
> **Keep asking for the dollar figure.** That instruction is what produced this
> finding: a session deriving its own number would have written `3.42%` into
> this table and the fifth reader in a row would have inherited it.
>
> **The one thing worth watching:** 0.2.4 was 98.8% cache reads over `66.4 M`
> cache-read tokens — expensive in dollars, possibly cheap in whatever the gauge
> meters. A subcycle with a different cache profile that *does* move the display
> is the measurement that would settle it. Nobody should model it before then.
>
> **And size the next subcycle in dollars, from what it BUILDS.** 0.2.4 cost
> `2.8x` 0.2.3 for `2.6x` the requests: it rewrote six rules, eight skills,
> four templates, three agents, five documents and four scripts, added a
> thirteenth control, and ran a live end-to-end. A handed-off subcycle that
> builds one mechanism has cost `$10-15`; one that rewires the whole pipeline
> costs `$40`.
>
> **0.2.3 adds a second cost line the table has never had: `$0.3134` of live
> model spend INSIDE the sandbox, over 8 headless runs.** From here on a
> subcycle can spend the quota twice — once as the session, once as the workers
> it dispatches — and the two are metered differently and must be reported
> separately: the session's from the owner's `/usage`, the workers' by summing
> `total_cost_usd` across each sandbox's `meta/budget.json`. A real worker is
> not a probe: 0.2.0's four probes cost `$0.062` between them, and one
> implementer doing one real step cost `$0.117` on its own, because it took 20
> turns where a probe takes 2. Budget a subcycle that dispatches by the number
> of ROUNDS it expects, not the number of runs.
>
> **0.2.3's dollar figure is exact and its percentage is a RANGE, because the
> two honest methods disagree and saying so is the finding.** Asked for, and
> read from the owner's display: `$14.73`, 100 requests, and the weekly gauge
> at `90%` where 0.2.2 left it at `89%`.
>
> - **Chaining the dollar anchors gives `1.20%`**, and all three agree to two
>   decimal places (`13.51:1.10`, `12.23:1.0`, `9.81:0.80`). That agreement is
>   an illusion: every one of those anchors descends from the same single
>   integer tick, so they cannot disagree.
> - **The aggregate gives `0.59%` to `1.17%`.** Four subcycles have now cost a
>   measured `$50.28` while the display moved `87% → 90%` — 3 ticks, so true
>   movement is in (2, 4), so `$12.57` to `$25.14` per percent. The rounding
>   error is amortised across four readings instead of resting on one.
>
> **Prefer the aggregate and quote the range.** A single number here would be
> false precision of exactly the kind this table has now been corrected for
> twice. What the record can say without qualification is the dollars, and that
> is what the next subcycle should be sized in.
>
> `session_cost.py --usd <figure> --anchor <usd>:<pct>` does this arithmetic;
> it existed one subcycle before anyone used it, because the input it needs
> cannot be read from inside a session. **Ask for the dollar figure before
> writing a percentage down.**
>
> **The dollar figures are exact and every PERCENTAGE here is uncertain by up
> to a factor of three. Corrected 2026-09-07 by the owner, who spotted it.**
> The display read `~87%` when this cycle began and `89%` after three completed
> subcycles whose measured costs sum to **`$35.55`**. At 0.2.0's anchor of
> `$12.23 = 1%` that spend should have moved it about 2.9 points. It moved 2.
>
> The reason is that **every percentage in this record descends from a single
> integer display tick.** 0.2.0's `1%` was the display going `87% → 88%`, which
> at whole-percent resolution is any true value from just over 0 to just under
> 2 — so the anchor was never as precise as three subcycles have been quoting
> it, this table included. The aggregate is the better instrument because its
> rounding error is amortised across three subcycles instead of resting on one
> tick: `$35.55` for a true movement somewhere in `(1.0, 3.0)` points gives
> **`$12` to `$35` per percent**. Every `%` below is therefore the pessimistic
> end of a range whose optimistic end is about a third of it.
>
> **So quote the dollars, which are measured, and quote the percentage as a
> range or as an upper bound.** The unit to REPORT in is still percent — it is
> what the owner can act on — but a single subcycle's share cannot be measured
> by a display with whole-percent granularity, and three of us in a row have
> written one down as though it could.
>
> **Derive the share from DOLLARS against a dollar anchor, never from tokens
> and never from the display's own movement.** 0.2.2 first published `≈0.9%`
> from a token ratio and the reading said `1.10%` — the same error 0.2.1
> recorded, one subcycle after `session_cost.py --usd` was built to prevent it,
> because the dollar figure it needs has to be asked for. And the display
> reports whole percent while a subcycle costs about one, so it cannot resolve
> a single subcycle: it read `89%` before and after this one.
>
> A cold session spent 104 requests where a handed-off one spent 58 and 83, so
> **the handoff removes the exploration rather than the work** — and 58 is not
> a floor: 0.2.2 built two mechanisms and 22 controls where 0.2.1 built one and
> 29. Size the next subcycle by what it BUILDS, and treat the handoff as
> removing a roughly fixed block of orientation, not as a multiplier.


`REASONED` — nothing in this cycle has been measured, and cycle 0.1's lesson
(C-3 §4) is that estimates miss on **rounds**, not typing: ten of ten tasks
over, 1.78× in total, after two upward revisions. Model each subcycle as
`reading + rounds × round-cost`, where reading is the §3 list plus the
subcycle's own files, and a round is build → run the verification → read what
it reports → fix. Assume three rounds where a control has to be made to fail
before it passes.

| Subcycle | Sessions | Tokens (order of magnitude) |
|---|---|---|
| 0.2.0 | 1 short | 0.3–0.6 M |
| 0.2.1 | 1 | 0.8–1.5 M |
| 0.2.2 | 1 | 0.6–1.2 M |
| 0.2.3 | 1–2 | 0.8–1.5 M |
| 0.2.4 | 1–2 | 1.0–2.0 M — many files, each small · **MEASURED: 1 session, 67.4 M processed, `$41.81`.** The token estimate is out by more than an order of magnitude for the same reason 0.2.0's was: cache reads scale with conversation length, not with work done. "Many files, each small" was right about the work and told nobody anything about the cost |
| 0.2.5 | 1 | 0.5–1.0 M |
| 0.2.6 | 1 | 0.8–1.5 M |
| 0.2.7 | 1 | 0.8–1.5 M |
| 0.2.8 | 1 short | 0.3–0.6 M |
| 0.2.10 | 1 short | 0.2–0.4 M |
| **build, core path** (0.2.0–0.2.5, 0.2.8) | 7–9 | **4.3–8.4 M** |
| 0.2.9 — the run | days | 4–8 M, against cycle 0.1's measured 13.5 M for ten tasks; three or four tasks at width 2 with a ceiling |

Write the measured figure into each subcycle's title line when it closes, so
the next cycle's model can be corrected rather than re-guessed (P-41).

## 9. Conventions for whoever implements this

- **Every number from a command, with the command beside it** — the rule the
  run's final review was written under, applied to your own reports.
- **Before building a check, run it against the live corpus** — the fixture's
  `devteam/` in `.internal/scratch/` — and read what it reports. Four checks
  were rejected that way in one day of cycle 0.1; each looked obviously right.
- **A control that cannot fail proves nothing.** Every control here plants
  the fault and demands the finding, and the false-positive twin beside it.
- **Do not write into `.internal/scratch/devteam/`** except through the
  pipeline: it is another session's board and the guard will refuse you.
  Reading it is the point.
- **Do not write outside this repository.** The owner runs concurrent sessions
  in sibling repositories; a write there is a write into work you cannot see.
- **An authorisation is scoped by the question that obtained it, so record the
  framing beside the grant.** Two sessions asked the owner for the same
  permission within one hour — one in prose, one as explicit options — and got
  two different grants. Neither answer was wrong: he answers each question as
  asked, precisely, which is what a literal communicator does. The prose ask
  produced "we can proceed" with no model and no ceiling, and the reader of it
  (me) then supplied a scope he had not stated. The options ask produced a
  model, a run count, a spend ceiling, an instruction to stop and re-ask at it,
  and *list only, no read, no write* chosen over a read option sitting right
  beside it.
  **So: when the scope of a permission matters, ask with options rather than in
  prose; the narrower, more explicit grant is the operative one; and never let
  one session inherit another's authorisation as though it were general.** If a
  grant turns out too narrow to make a control actually control, go back and
  say so — do not widen it quietly because asking again is inconvenient, and do
  not keep a control that proves nothing because widening needs another ask.
- **When a subcycle tells you to do something impossible, stop and record it
  in the subcycle file** under a `## Findings` heading, with what you tried.
  Do not work around it; the workaround is the defect nobody will find.
