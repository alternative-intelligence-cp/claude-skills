# Cycle 0.3 — evidence the pipeline can trust, handoffs that carry, and a run that closes

> **For the implementing session.** You have none of the planning conversation
> and cannot ask its author anything. This file is the map; the subcycle files
> are the territory. Read this whole file first, then §3's reading list, then
> the subcycle you are working, in full, before touching the tree.

**Status: PLANNING since 2026-09-23.** The owner reviewed the map on
2026-09-23 — *"it all looks fine to me. I say go ahead with it"* — and the
decisions in §6 marked *owner* bind. It stays `PROVISIONAL` in one sense only:
0.3.0's probes exist to change it, and a probe result that does supersedes the
line it overturns here, with a new number. §10 lists what is still open and
which subcycle each question blocks.

## 1. What this cycle is for

Cycle 0.2 built structural containment and manager rotation, then ran the
pipeline on a real project of the owner's — `pricelog`, two cycles, nineteen
tasks — as subcycle 0.2.9. The owner stopped the run on 2026-09-19 and it was
read whole: 142 findings, sorted for planning in the
[findings register](../../v3-findings-register-2026-09-19.md). On 2026-09-23
the owner judged, under [PAIRS row 20](../../../docs/PAIRS.md), that the run was
**not yet** a good enough experiment to trust the pipeline with real work
(L-1). This cycle is what that judgement asks for — fix, then run again — in
three parts.

1. **Make the pipeline's own evidence trustworthy and affordable** — the
   register's themes 1 to 4. The pipeline's central promise is that it leaves
   evidence, and the run measured four ways that promise failed: items raised
   by adversaries, auditors and outgoing managers reached no owner; checks
   reported clean without having looked; the manager's bookkeeping was done by
   hand and failed by hand; and the meters could not see the largest part of
   what was spent. Subcycles 0.3.1 to 0.3.5.
2. **Close the joints the run measured leaking** — themes 5 to 10: the handoff
   between rotations, the adversarial layer's coverage and price, signed text
   drifting from the code, iterate's missing paths, the sandbox's edges, and
   the platform moving under the pin. Subcycles 0.3.6 to 0.3.11.
3. **Decide the liaison by measurement, then run a third experiment.** The
   liaison layer is the owner's answer to the hard pause at every rotation.
   0.3.0 measures whether the platform can carry one, and 0.3.12 builds it only
   if so (L-2). Then 0.3.14 runs the pipeline again on a real project of the
   owner's — a cowsay clone written in Nitpick (L-10) — designed to see what
   0.2.9 could not: an iteration whose owner has used what was built, a second
   iteration after unreviewed decisions exist, and a cycle that closes rather
   than stops. Because the language is one no model has seen, 0.3.15 first
   teaches the pipeline to run a toolchain it cannot assume it knows. Row 20's
   judgement is made again after the run.

Throughout, *theme n* is one of the register's ten themes (*Where v3 should
start*), and *An* is one of its fourteen areas (*Findings by area*). F-numbers
are `pricelog`'s, and the register's last table maps each to the 0.2.9 entry
that writes it up.

## 2. The finding that decides the architecture

**The manager's recurring failures were bookkeeping, and every bookkeeping fix
that held replaced a remembered step with a command.**

The manager is the one role that writes concurrently with every other, and
theme 3 counts what went wrong with it. Its judgement failed too — twice it
relayed or closed on a claim it had not measured (F-57, F-58) — but those are
two findings. The bookkeeping failures are most of the theme, and they recurred
to the last rotation:

- six commits in the `git add -A` form `run` §4.5 forbids (A1);
- the writer lock refused three times, because the board edit and the session
  pointer shared one command (A2);
- check exit codes read through pipes, and the board once advanced on a report
  `run` §6 sends back (F-24, F-117);
- board values typed by hand (F-26); a dispatch sent with no model, and a draft
  landed twice (F-100);
- the checkpoint cadence missed at eight tasks, with rotation and budget
  reading lapsing alongside it (A12);
- three checkpoints passed without a rotation, and that one tenure cost 231 M
  tokens (A2);
- what the client said after the outgoing manager's last write reached no file,
  at all fifteen rotations (F-21);
- question status kept in two files that disagreed in both directions (F-63,
  F-64);
- a heartbeat left naming an agent nobody awaited, at each of T-19's three
  stops (A3).

Against them, the register's *What worked* lists the bookkeeping fixes that
held, and **every one replaced a remembered step with a mechanism**:

- lock commits made by a command written to abort unless `HEAD` was the named
  last write and nothing else had changed — from the ninth lock move on, and at
  the last three the guard refused nothing;
- `check_refs` caught every absolute-path leak in its slice, the manager's own
  included, and once commits depended on its exit code the gate held (F-89,
  F-117);
- controlled-vocabulary cells that refused the manager's prose, every refusal
  correct;
- briefs landed whole before sending and generated by script from the one
  before, so every carried line was byte-identical (F-119);
- a finding-set baseline gate that refused a commit correctly on a real
  transient state, and failed closed on an empty set (F-85).

**So this cycle's architecture is a rule about where work lives** (L-5): an
act the skills ask a session to repeat is a command with an exit code that
checks its own preconditions, and the skill says only when to call it and what
to do when it refuses. That is the owner's standing design rule — prevent the
mistake structurally rather than rely on the practitioner to remember — applied
to the practitioner the run measured failing.

**It also decides the shape of the liaison question.** The backlog's case for a
cheap-model liaison is that it *applies a rule instead of exercising taste*
([`v3-liaison-and-roles`](../../v3-liaison-and-roles-2026-09-12.md) §7,
carve-out 2). A liaison can only apply rules that exist as commands; driven by
prose, it inherits every failure above with a weaker model. So the primitives
come first (0.3.4), and the liaison — if 0.3.0's probe says the platform can
carry one — is built on them (0.3.12).

## 3. Read, in this order

Everything below is a pointer; nothing here restates content (P-34).

1. This file, all of it.
2. [`../../v3-findings-register-2026-09-19.md`](../../v3-findings-register-2026-09-19.md)
   — all of it. Its themes are this cycle's structure, its area tables are each
   subcycle's worklist, and its *What worked* is the list of things not to
   break.
3. The entries of [`../0.2/0.2.9.md`](../0.2/0.2.9.md) `## Findings` that the
   register cites for the subcycle you are working — not all 3,400 lines.
4. [`../../v3-liaison-and-roles-2026-09-12.md`](../../v3-liaison-and-roles-2026-09-12.md)
   and [`../../v3-structure-chart-2026-09-12.md`](../../v3-structure-chart-2026-09-12.md)
   — the liaison backlog, `PROVISIONAL`. Required for 0.3.0 and 0.3.12;
   background for the rest.
5. [`../../../PROTOCOL.md`](../../../PROTOCOL.md) — you will add and supersede
   rules, and a rule is superseded by a new number, never edited (P-23).
6. [`../../../templates/FORMATS.md`](../../../templates/FORMATS.md) — the
   grammar the checks parse. Most subcycles here change it.
7. [`../../../docs/CHECKS.md`](../../../docs/CHECKS.md) — every finding class and
   the rule it enforces.
8. [`../0.2/README.md`](../0.2/README.md) §6 and §9 — 0.2's settled decisions
   still bind unless §6 below supersedes one by name, and its conventions carry
   forward with §9's additions below.
9. [`../../../docs/PAIRS.md`](../../../docs/PAIRS.md) rows 18 and 20 — both
   decided at this planning.

## 4. What the planning session measured

All `MEASURED` on 2026-09-23, on this machine, unless marked `REASONED`.

**4.1 The inputs are all here.** The staging area `~/Workspace/META/DEV_TEAM`
holds only four `MOVED` pointer files, and each target exists: the roll-up,
merged into 0.2.9's Findings (its line 1083 marks where); the structure chart,
with the owner's original sketch verbatim in its appendix; `findings_index.py`
and its control in `scripts/` (17 of 17 cases pass); and `FINDINGS-INDEX.md`,
byte-identical to a fresh regeneration (298 findings). The register lists F-1
to F-142 exactly once each, and `pricelog`'s record declares none beyond F-142.
`pricelog` is at `a88990b`, with only its ignored `devteam/.run/` uncommitted.
**One gap, stated:** `META/DEV_TEAM` was never committed to META's own history,
so the originals from before the move survive only as they were merged here.

**4.2 The baseline this cycle starts from.** Plugin `0.2.0-rc`
(`.claude-plugin/plugin.json`, tag `v0.2.0-rc`).
`python3 scripts/check_plugin.py` →
`devteam plugin: clean  [15 skills, 9 agents, 48 rules, 7 root entries]`.
`python3 scripts/run_controls.py` → `all 15 controls green`. The `claude` CLI
is `2.1.281`; it was `2.1.268` when 0.2.9 started, and it moved under that
run's pin more than once (F-42, F-96).

**4.3 Workers read `devteam/`, so it cannot leave their view.** The backlog's
narrow fix ([`v3-liaison-and-roles`](../../v3-liaison-and-roles-2026-09-12.md)
Part IV) proposed a sandbox that mounts the product tree only, and named what
had to be checked first: whether any worker legitimately reads `devteam/`. The
[`work` skill](../../../skills/work/SKILL.md) §3 tells every worker to read
four files there — `CHARTER.md`, its requirement in `REQUIREMENTS.md`,
`DECISIONS.md`, and its task file — and its report section tells the worker to
append the report to that task file. So L-3 keeps `devteam/` visible and
read-only, and moves the report instead.

**4.4 The sandbox's lower layer is the live tree.**
[`scripts/sandbox.py`](../../../scripts/sandbox.py) mounts each overlay with
`lowerdir=<repo>` — its docstring's mount plan, and the options string it
builds — which is the host repository as it stands at every moment. That is
why a host write reads through into every open overlay (F-5, F-26, F-71). L-3
replaces it with a commit.

**4.5 In-process agents can be metered from their transcripts; the run did it
once, by hand.** `pricelog`'s RECORD.md:1143 sums every in-process agent
transcript that one manager session held, deduplicated by request id:
546,345,463 tokens over 2,171 requests across 40 supervisors and verifiers,
all Sonnet 5 — 2.7 times the manager half, and in neither half of the ceiling.
It is a floor, because agents whose transcripts were not kept are absent. So
theme 4's meter is a script to write, not a capability to discover. What 0.3.0
still has to measure is how the meter's total relates to the owner's `/usage`
reading, which blends model families: at cycle 2's opening he read 84% on the
all-model gauge, and *"fable was 50% of that"* (RECORD.md:932).

**4.6 A session can now start another session in the background.**
`claude --help` on 2.1.281 lists `--bg, --background`: *"Start the session in
the background and return immediately. Prints the id that `claude attach`,
`logs`, `stop` and `rm` take; `claude agents` lists them."*
`claude agents --json` prints every active session, interactive and
background, as JSON records with `cwd`, `kind`, `name`, `pid`, `sessionId`,
`startedAt` and `status` — nine sessions on this machine when read.

This bears directly on L-2, and on 0.2's L-8, which rested on *a session cannot
spawn its own interactive successor*. A background session is not interactive,
but the client can `claude attach` to it, and starting one needs no keyboard.
Whether a background session can run `/devteam:resume`, dispatch the
supervisor tree, and reach the client is `REASONED` until 0.3.0 runs it. The
same listing is also a scriptable join between a session's id and its name
(F-118) and a liveness reading for sessions — `REASONED` until a subcycle reads
it under load. Whether it lists headless `claude -p` workers is not known.

**4.7 The Nitpick compiler is under active development, and the user guides
for it were written by another model.** The compiler
(`~/Workspace/REPOS/nitpick`) is self-hosted. Its `main` branch last moved on
2026-09-19 — steps 3 to 6 of cycle 1.5.8b, each commit carrying its own
reference-document changes — and on the day this was planned its current work
was committed on two branches in separate worktrees (`s12-158b-6b` and
`s12-158b-6c`, both at `c88bfd8`, 2026-09-23 21:23). **Corrected at planning:**
an earlier version of this paragraph, and of L-12, said step 1.5.8b landed on
the planning day; that was read from the step numbers without checking the
dates. A pinned build is therefore a commit on `main`, never a work branch. The
language's authority is its `meta/specs/` directory — seventeen references,
from `LEXICAL_REFERENCE.md` to `VERIFICATION_REFERENCE.md` — and the compiler
has no tags; its version reads `0.0.0`, so a build is pinned by commit.
Building it needs LLVM **20.1.2** exactly (`llc` and `ld.lld`; its
`nitpick.toml` pins the version), and on this machine that is a trap for a
sandbox: `/usr/bin/llc` does not exist, `/usr/bin/ld.lld` is LLD 18, and the
LLVM 20 names are symlinks in `~/.local/bin`, which a sandbox's private `HOME`
hides. The compiler itself reads no environment variable, writes only its
output file, and links statically. A program reads its arguments through
`main`'s fixed signature and its standard input through the builtin
`read_stdin`, and it imports only by relative or absolute path — the compiler
searches no library path. No program in the compiler's own tests reads
standard input. Separately,
`~/Workspace/REPOS/nitpick-docs` holds three user guides (quick start, cheat
sheet, driver model) and two examples, written by another model on 2026-09-21
and reviewed by the owner, who reports finding and fixing a couple of errors
and possibly missing more. Its history names where the model went wrong: two
same-day fixes, for numeric literal syntax and suffixes, `pick`, address-of,
and explicit error declarations. **That is a measurement of the very risk
L-10 accepts** — a model writing Nitpick fills gaps from languages it does
know — and it is why 0.3.15 admits those guides as worker input only once every
example in them has been compiled and run against the pinned build. No
benchmark files are in the tracked tree.

**4.8 Four defects the planning reads turned up, each assigned.**
- **The session meter cannot find a session whose project path contains a
  dot.** The harness names a project's transcript directory by turning both `/`
  and `.` into `-` — `…claude-skills--internal-scratch` is on disk — while
  `session_cost.py` turns only `/`, so
  `session_cost.py --project ~/Workspace/REPOS/claude-skills/.internal/scratch`
  exits `no-transcript`. Every session this cycle's probes start from
  `.internal/scratch` is affected. 0.3.0 passes transcript paths directly;
  0.3.5 fixes the lookup.
- **Workers leave no transcript.** `sandbox.py` dispatches every worker with
  `--no-session-persistence`, so a worker's spend exists only in its sandbox's
  `meta/budget.json`, which `close` deletes (F-9) — and the message `close
  --keep` prints, that the worker's transcript is kept under
  `home/.claude/projects/`, cannot be true of a session that saved none. 0.3.5
  and 0.3.7.
- **The outgoing manager is never told to answer the question its successor
  must ask.** `resume` §0 has the successor ask for *"the sha of your last
  intended write"*; `run` §2, which tells the outgoing manager how to stop,
  never says to reply with it. 0.3.6.
- **The sandbox probe's control cites a file that has moved.**
  `scripts/test_sandbox_probe.py` cites `meta/roadmap/0.2/0.2.0.md`, which is
  now under `done/`, and `check_plugin` does not read citations inside
  Python files. 0.3.2 gives the reference check a reach it does not have.

## 5. The map

| Subcycle | What it produces | Depends on | Core? |
|---|---|---|---|
| [0.3.0](0.3.0.md) — probes | four probes — **the liaison** (can a background session run the manager's loop to a checkpoint and be replaced with nobody at the keyboard, with a decision rule for L-2), **the meter** (every session and in-process agent from transcripts, reconciled against `/usage` readings the owner supplies), **the frozen overlay** (a commit as the lower layer, `devteam/` read-only, promotion correct at width 2), and **the Nitpick compiler inside a sandbox** (a compiler built from a pinned commit, bound read-only, compiling and running a program that reads its arguments and standard input — L-10) | — | **yes — first, small, and it can change the design** |
| 0.3.1 — the check contract | one result contract for every check — clean, findings, or `not-evaluated` with its reason (L-6); zero rows parsed is `not-evaluated`; untracked files read (F-131); accepted findings as a reasoned, first-class baseline; a commit gate shipped in the plugin that commits only on green, scoped so that a concurrent task's red file cannot block an unrelated commit (F-12, F-19, F-24), with a post-commit re-run of history-derived checks (F-114) | 0.3.0 | yes — every later check is built to it |
| 0.3.2 — what the checks read | the silent-clean and wrong-window defects, check by check: `check_trace` (F-36 and F-68's slice, F-95's prose edges, F-132's two parses, partial and re-established requirement states, the header against the newest amendment, estimates against `S-` lines); `check_report` (F-34, F-37 and F-88 fail loudly; F-32's hedged figures; per-block meters, F-103 and F-109; `added` and `reconstructed`, F-86); `check_scope` and `check_report` keyed to the current claim window (F-135, F-136); board state against task title (F-107); checkpoint tallies from parsed verdicts (A12) | 0.3.1 | yes |
| 0.3.3 — the disposition ledger | one ledger for every open item — raised by an adversary, a worker, an auditor, an outgoing manager, or the client between writes — each a countable line with an owner and a decision or an expiry; report grammars that carry open items as lines (F-139); a check that fails any landing that leaves one without; question status in one home (F-63, F-64); the audit skill's output and `check_refs`' audit namespace made one contract (F-99, F-104, F-112); a place outside the writer lock for what the client says during a handoff (F-21) | 0.3.1 | yes |
| 0.3.4 — manager primitives | one command each, each checking its own preconditions (L-5): **claim** (generates every board value that restates another; counts in-flight and stopped rows against width, F-130), **take the lock**, **land** a brief, report or verdict whole with its digest, **commit** named paths on a green gate, **close** a task (title, board row and requirement in one commit — F-78, F-90, F-98, F-107), **dispatch** (a model field required, real CLI ids — F-7, F-25, F-73, F-121), **re-claim** (F-39) and **stop**; `run` and `resume` rewritten to call them | 0.3.1, 0.3.3 | **yes — §2** |
| 0.3.5 — meters that see what the gauge sees | the meter from 0.3.0 made the ceiling's instrument (L-7): every session and in-process agent; a rotation's window opened at the successor's first request and closed at the predecessor's true close (F-110, F-116); a running total at every report; each dispatch's model recorded; worker meters and reports kept outside the overlay and the dispatching process (F-9, F-76, F-87); the estimate model given a term for adversarial rounds and the stops they cause (A8), and a tenure priced at the measured average plus resume and tail (A11) | 0.3.0 | yes |
| 0.3.6 — the handoff | `handoff-ready` made a structured record whose required fields are what fifteen successors had to ask for — client words since the last write, work outside the tree, probe directories, open items from the ledger, the session's name, the trigger if off-cadence — with a check on it; rotation after a checkpoint enforced rather than remembered; `cancelled` and `stopped` states the guard reads (F-141); a direct handoff to an open successor (F-129); the recovery table's missing rows — resume in place (F-17), a quota stop (F-106), a stopped claim (F-130) | 0.3.3, 0.3.4, 0.3.5 | yes |
| 0.3.7 — frozen sandboxes and the worker's edges | L-3: a commit as each overlay's lower layer, `devteam/` read-only, the report returned in the worker's final message and committed by its supervisor (F-5, F-26, F-31, F-71); an inventory that survives `close` — pid, spent or promoted, budget (F-9, F-66, F-124); `close` refusing to discard an abnormal exit's overlay (F-43, F-51, F-56); a probe directory the record can cite, for workers too (F-134); every pinned tool bound from the pin — the CLI, and for a Nitpick project the compiler (F-42, F-81, F-96); `--model` and `--step` validated before `open` (F-111, F-121); a worker able to amend its own unpromoted commit (F-122); trailers added at promotion (F-8, F-27); scope-aware whole-suite gates (F-74); then width 2 measured again | 0.3.0, 0.3.1 | yes — it is what restores width above 1 |
| 0.3.8 — verification and the adversarial layer | a coverage field in every verdict — what was attacked and what was not, with acceptance and gate answered separately; *shown able to fail* required of every test step and trip-wire (F-77, F-79, F-91); a fresh task verifier on every `NEEDS-DECISION`, aimed at the supervisor's recommendation (F-133); verifier briefs that carry no expected result (F-115); the literal acceptance command (F-16, F-29); a structural comparison for claims that code is unchanged (F-120); no published reproduction that was not run (F-40, F-41); audits inside the build loop, and metered; the verify fallback made a clone (F-94); a stated precedence between a dispatch and a skill (F-108) | 0.3.3 | yes — the register calls this layer where the value was |
| 0.3.9 — signed text | L-4: superseding a requirement made one command, an in-place edit of a signed requirement made a check failure, and P-46 superseded so that its shape review counts supersessions; a shape review at onboarding that flags a list of cases under a goal that quantifies — R-4 cost seven `CHARTER` stops in one day — and an acceptance worded as a method rather than a property (A9); an amendment grammar that can say *in force, currently broken* and records which amendments the client approved; a check for code-level exclusions that no signed text names (F-48); plans that cite a prototype's measurement as the prototype's (F-140) | 0.3.1 | yes |
| 0.3.10 — iterate, checkpoints and the stop | iterate's opening records whether the tool was used and names any substitute input; the new cycle priced after its scope exists; carried audit findings dispositioned before the charter gate (F-99); the short close that `stop` runs — claims, heartbeats, a pending rotation, signed text left false, and everything deferred to a next cycle (F-141); the checkpoint triggered at its cadence by the loop rather than by memory, with P-30's size trigger naming its meter; the keepalive on by default, with window expiry computed on its tick (F-84, F-138) | 0.3.4, 0.3.5, 0.3.9 | yes — the third run iterates twice |
| 0.3.11 — the guard and the platform | agent definitions that say injected instructions — MCP server blocks, another plugin's skills — are not instructions (F-69, F-101, F-102); every skill name qualified, with a check; the guard judging targets rather than command text, against the command's real working directory (F-6), honouring P-10b outside the project, and telling a read-only `git remote` from a push; the push grant settled (§10.3); a manager launched from another repository warned whose guards reach its agents (F-137) | 0.3.1 | yes, and small |
| 0.3.12 — the liaison | **only if 0.3.0's probe passes** (L-2): the restarter, the relay, the escalation classification applied as a rule, the rotation log, and liaison tokens per rotation as its instrument ([`v3-liaison-and-roles`](../../v3-liaison-and-roles-2026-09-12.md) §6–§8) | 0.3.0's decision; 0.3.4, 0.3.5, 0.3.6 | conditional |
| 0.3.13 — release 0.3.0 | version, self-check and controls; DESIGN and PROTOCOL brought level; the README's Known problems rows removed only where the fix has been shown working; the register's rows marked with the subcycle that closed each; a fresh `setup` on a throwaway Nitpick project | everything shipped | yes |
| 0.3.14 — the third run | a cowsay clone written in Nitpick, in its own repository beside `pricelog` (L-10, L-11) — cycle 1 one animal and the most basic behaviour, `/devteam:iterate` adding animals and flags — planned from §8's model once 0.3.5 exists: a cycle that closes, the owner using what it built before iterating, a second iteration after unreviewed decisions exist, width 2, rotation at every checkpoint, the liaison if it was built, and one pinned compiler build throughout (L-12); then row 20's judgement | 0.3.13 | **yes — it is what the cycle is for** |
| 0.3.15 — a toolchain no model knows | L-10's price, because no model has seen Nitpick: `setup` detects a Nitpick project and its toolchain; a compiler built from a pinned commit rather than taken from the compiler's working tree, recorded in the environment pin and bound into every sandbox through 0.3.7 (L-12); the language reference made a worker input — the compiler's own `meta/specs/` at the pinned commit, with the user guides in `nitpick-docs` admitted only once every example in them has been compiled and run against that build, each failure a finding carried to the owner; every finding in a run tagged with its cause — the pipeline, the language or compiler, the model's knowledge of the language, or the product; a compiler defect recorded with a reproduction and never fixed mid-run (L-12) | 0.3.0, 0.3.3, 0.3.7 | yes, for this run — it is L-10's price |

**Order.** 0.3.0 → 0.3.1 → 0.3.3 → 0.3.4 → 0.3.6 → 0.3.13 → 0.3.14 is the
critical path. 0.3.2 follows 0.3.1 at any point before 0.3.13. 0.3.5 needs
only 0.3.0's meter probe, and 0.3.6 needs it. 0.3.7 needs 0.3.0's overlay probe
and 0.3.1, and is otherwise independent: it changes `sandbox.py`, `supervise`
and `work`, which nothing on the critical path touches. 0.3.8, 0.3.9 and 0.3.11
are independent of each other. 0.3.10 needs 0.3.4, 0.3.5 and 0.3.9. 0.3.12
waits on 0.3.0's decision and, if it goes ahead, on 0.3.6. 0.3.15 needs 0.3.0's
compiler probe, 0.3.3 and 0.3.7, and comes before 0.3.13 although its number
sorts last. *Independent* means no dependency, not that two sessions may work
one tree at once. Numbers above 0.3.9 sort before 0.3.2 in a directory listing;
this table is authoritative over that order.

**One deviation from the map as approved, declared here.** The plugin README's
status and Known problems were to be revised from the register as 0.3.0's
first act. They were revised at planning instead, on 2026-09-23, because the
register was already loaded and the README was telling any visitor that
rotation had never rotated a project. 0.3.0 is therefore probes only.

**CONSOLIDATION 8a is included.** The accepted-findings block
([`docs/CONSOLIDATION.md`](../../../docs/CONSOLIDATION.md) §8a) was excluded
from 0.2 until its trigger fired — *the day a manager reads a finding count and
does not read the finding under it*. It fired in the run: a permanently red
exit code taught managers to commit over red (F-78, F-85, F-95). 0.3.1 builds
it as the first-class baseline.

**If the budget forces a choice**, build all of it and shrink the run, not the
reverse. §8's anchors say why: each of 0.2's build subcycles moved the weekly
gauge by about a point, while the run that followed them ran into the weekly
limit. A small third run on a hardened pipeline answers row 20. A large run on
an unhardened one repeats 0.2.9's findings at 0.2.9's price. The one subcycle
whose absence leaves the third run able to answer its question is 0.3.12, and
L-2 already makes it conditional. Every other subcycle closes defects the third
run would otherwise meet again. Deferring one accepts that its findings recur
in the run, and whoever defers it should name which findings those are.

## 6. Decisions settled at planning

Numbered `L-n` and local to this cycle. 0.2's `L-1` to `L-10` are a separate
series: they still bind unless superseded here by name, and are cited as
*0.2's L-n*. Each decision records the alternatives declined (P-21). Do not
re-litigate them in a subcycle. If one proves wrong, record why in the
subcycle file, and supersede it here with a new number (P-23).

**Settled by** says who made each decision. The *owner* made his on
2026-09-23, each by selecting one of the options quoted; the planning
session's recommendation is marked. *Planning* decisions follow from the
evidence cited, and stand until the owner overrules one.

- **L-1 — 0.2.9 was not yet a sufficient experiment: fix, then run again.**
  *Settled by:* owner, choosing *"Not yet: fix, then run again
  (Recommended)"* over *"Good enough for the spine"*. *Why:* the run was stopped
  rather than closed; iterate's use-half never ran; several checks were measured
  reporting clean without looking (theme 2). *So:* applying `devteam` to this
  repository and building the adjacent teams stay out of this cycle (§7), and
  PAIRS row 20's judgement is made again after 0.3.14. *Declined:* treating
  v2's architecture as proven, which would have admitted self-application or a
  research team here.
- **L-2 — the liaison is decided by a probe.** *Settled by:* owner, choosing
  *"Probe first, decide on the result (Recommended)"* over *"Build it in 0.3
  regardless"* and *"Leave it for 0.4"*. 0.3.0 measures whether a session can
  start and rotate a project manager with nobody at the keyboard. If it can,
  0.3.12 builds the liaison so that the third run tests it. If it cannot, the
  liaison is excluded with the failed probe as its trigger (§7). The handoff
  record, the meters and the primitives it would stand on are built either
  way, because they are themes 1, 3, 4 and 6. *Why not regardless:* the
  liaison rests on platform behaviour nobody has measured, and §4.6 shows the
  platform now offers something 0.2's L-8 assumed it did not. *Why not in 0.4:*
  a separate cycle needs a separate run, and 0.2.9's counted about 743 M
  manager tokens before its in-process agents.
- **L-3 — sandboxes are frozen at a commit, `devteam/` is read-only inside
  them, and a worker's report travels in its final message.** *Settled by:*
  owner, choosing *"Freeze sandboxes; devteam/ read-only (Recommended)"* over
  *"Move project state to a separate repo"* and *"Narrow promote's check to
  declared paths"*. Each overlay's lower layer is the commit the step starts
  from, not the live host tree (§4.4), so no host write after `open` can reach
  a worker. Workers still read the four `devteam/` files the `work` skill names
  (§4.3), and never write under `devteam/`. The supervisor, host-side, commits
  the report the worker returned. `devteam/` stays in the product repository,
  so a claim is still a commit and there is one history. This **refines 0.2's
  L-1** — the overlay stays, and its lower layer changes — and leaves 0.2's L-5
  as it is, because promotion by cherry-pick already assumes a base that does
  not move. *Declined:* the full partition, which leaves two histories for a
  later reader to line up and makes `setup` manage a second repository
  ([`v3-liaison-and-roles`](../../v3-liaison-and-roles-2026-09-12.md) Part IV,
  *the honest trade*); narrowing promote's uncommitted check to declared paths,
  the record's own remedy (RECORD.md:735–736) — the smallest change, and it
  leaves a worker able to build on a file that changes under it.
- **L-4 — a requirement is superseded, never edited, and superseding is made
  cheap.** *Settled by:* owner, choosing *"Supersede only; make it cheap
  (Recommended)"* over *"Allow edits with a recorded change"*. This closes
  [PAIRS row 18](../../../docs/PAIRS.md) with the count 0.2.9 produced: one
  supersession and five in-place edits of signed requirements, across the only
  real second cycle. A requirement's number never changes meaning, because
  closed records cite it — the discipline of a blueprint, where a symbol never
  changes meaning between pages. The five edits say the rule was right and too
  expensive to follow. So 0.3.9 makes superseding one command, makes an
  in-place edit of a signed requirement a check failure, and supersedes P-46 so
  that its shape review fires on a requirement's third supersession rather than
  its third edit. *Declined:* recorded in-place edits, under which closed
  records citing a requirement would point at text that has changed since.
- **L-5 — every act a skill asks a session to repeat is a command with an exit
  code.** *Settled by:* planning, from §2. The command checks its own
  preconditions and refuses rather than proceeding. The skill says when to call
  it and what to do when it refuses, and stops describing the steps inside it.
  0.3.4 applies this to the manager, and every other subcycle applies it to
  whatever it touches. *Declined:* more precise prose in the skills, measured
  failing in §2 by sessions that had the prose in front of them.
- **L-6 — a check never reports clean when it did not look.** *Settled by:*
  planning, from theme 2. Clean means *looked and found nothing*; a check that
  parsed none of what it exists to read, or skipped part of it, says so with
  its reason and does not exit as clean. Whether `not-evaluated` shares exit 2
  with today's *could not run* or gets a code of its own is for 0.3.1 to
  settle, with a control either way. *Declined:* leaving each check to decide,
  which is how the run found several that decided differently (theme 2).
- **L-7 — the ceiling's instrument is reconciled against the owner's gauge,
  and a percentage is read, never derived.** *Settled by:* planning, from
  theme 4 and 0.2's §8. The meter counts every session and in-process agent
  from transcripts (§4.5). 0.3.0 reconciles its total, over an interval, against
  `/usage` readings the owner takes at both ends, and a meter that cannot be
  reconciled is not the ceiling's instrument. Percentages in this cycle's
  records are always the owner's readings, never computed from tokens: 0.2's §8
  records a token estimate out by more than an order of magnitude against the
  gauge, and the gauge blends model families (§4.5). *Declined:* a ceiling in
  processed tokens alone, which cycle 2 of 0.2.9 raised ten times without it
  ever governing anything.
- **L-8 — this cycle is implemented directly by sessions, not by running
  `devteam` on itself.** *Settled by:* L-1, and 0.2's L-9, whose reasoning is
  unchanged: the mechanisms being changed are the ones the pipeline would be
  running under. The third run is where the pipeline runs.
- **L-9 — version 0.3.0; rules superseded, never rewritten (P-23); every new
  check ships its control (P-35), including a case where it must refuse to
  report clean (L-6); every claim marked `MEASURED` or `REASONED`; every figure
  from 0.2.9 cited as that run's.** Bookkeeping, recorded so that nobody argues
  about it mid-cycle. The last clause is F-140's lesson applied to this plan: a
  measurement taken on a prototype belongs to the prototype.
- **L-10 — the third run builds a cowsay clone in Nitpick.** *Settled by:*
  owner, who proposed it — *"a simple nitpick app? Something like a cowsay
  clone … Could start with just one animal and the most basic funtionality and
  then add more animals and maybe flags or whatnot in iterate"* — and then chose
  *"Yes, in Nitpick (Recommended)"* over *"Yes, but in Python"* once the price
  below was put to him. *Why:* use actually happens, because cowsay's output is
  visual and is judged in seconds, so iterate's interview finally has real use
  to start from; one animal first and more animals and flags second is a
  natural iteration, whose second-cycle request can be expected to collide with
  a first-cycle promise — a width flag against a bubble promised to align for
  any input, say (`REASONED`) — which is the hidden cost an iteration exists to
  price; and it points `devteam` at the language every project the owner has
  named for it is written in, making the run a consumer of the compiler as well.
  *Price, accepted:* 0.3.15; a compiler pinned for the whole run (L-12); a run
  that will stop more often than a Python one, with some stops Nitpick's rather
  than the pipeline's, so every finding carries its cause. *Declined:* Python,
  which compares directly with `pricelog` and says nothing about `devteam` on
  Nitpick.
- **L-11 — the run's repository is its own, beside `pricelog`.** *Settled by:*
  owner, choosing *"Its own repo, beside pricelog (Recommended)"* over *"In
  nitpick-apps from the start"*. The experiment stays out of the `nitpick-apps`
  registry and the libraries' board while it is an experiment. Adopting what it
  builds into `nitpick-apps` afterwards is the owner's decision, made then.
  *Declined:* registering it in `nitpick-apps` from the start, under which the
  run's sessions would have to satisfy the ecosystem's process and `devteam`'s at
  once.
- **L-12 — a compiler defect the run finds is recorded, never fixed mid-run.**
  *Settled by:* owner, choosing *"Record it; never fix it mid-run
  (Recommended)"* over *"Fix it in the compiler as it comes up"*. The run uses
  one compiler, built from a pinned commit, for its whole length; a defect in it
  is recorded with a reproduction, and the run works around it or stops; the
  compiler takes it up on its own schedule. *Why:* the compiler is under active
  development — its current work was committed on two branches on the day this
  was planned (§4.7) — so a run that tracked it would measure two moving things
  at once, and fixing the compiler
  mid-run would interleave bug-fixing with the compiler's roadmap work, which
  the owner keeps apart. *Declined:* fixing as it comes up — faster for the run,
  and it moves the pin mid-run.
- **L-13 — a client profile is taken at the interview, minimally, in 0.3.9.**
  *Settled by:* owner, accepting §10.2's recommendation in prose — *"I'm fine
  with your recommendation"*. The interview asks how comfortable the client is
  with development and how involved they want to be; the answers are recorded
  in the charter and set two things only — how often the loop asks rather than
  proceeding on its recommendation, and whether an escalation arrives as a
  recommendation or as options with their trade-offs. Rigour never varies with
  the profile (§7). *Declined:* the fuller set of dials in the owner's proposal
  of 2026-09-11 — check-in frequency and the register of explanations — until
  a run has measured these two.
- **L-14 — onboarding refuses to record a push grant the guard will not
  honour; pushing stays the owner's.** *Settled by:* owner, accepting §10.3's
  recommendation in prose — *"also fine with this recommendation"*. Publishing
  outward is `IRREVERSIBLE` under P-26 and always blocks. The guard learns to
  allow a read-only `git remote -v`. *Declined:* a guard that reads a charter's
  push grant, which would widen what an agent can do outward on the strength of
  a document an agent drafted.

*The last two were accepted in prose rather than by selecting an option; each
grants what its recommendation said and nothing adjacent to it.*

## 7. Excluded from this cycle, with the trigger that would include it

| Not built | Why not | Trigger |
|---|---|---|
| `devteam` applied to this repository | L-1; [PAIRS row 20](../../../docs/PAIRS.md) | 0.3.14 closes and the owner judges it sufficient — a judgement made after the run, not the run finishing |
| the adjacent teams — research, maintenance and design — and a shared core extracted from `devteam` | [`adjacent-plugins`](../../adjacent-plugins-2026-09-07.md) §7–§8 gate all of them on the spine being proven, and a core cannot be extracted from one consumer | row 20 met; then the research team first, as that document recommends |
| the liaison, if 0.3.0's probe fails | L-2 | a platform release that supplies what the failed probe lacked — re-run the probe, which 0.3.0 leaves as a script |
| network isolation for workers | 0.2's L-4, unchanged | 0.2's trigger, unchanged: a worker seen reaching anything but the model API, or a charter marking the project sensitive |
| compiling the declared scope into the mount table | 0.2's §7 reasoning, which L-3 does not change: a frozen lower layer changes what a worker sees, not how scope is enforced | 0.2's trigger, unchanged |
| macOS and Windows containment | unchanged | a user on either platform |
| a reduced-rigour profile for small projects | refused by the owner: what may differ between a novice client and an expert is the interface, never the strictness, because a novice cannot see what a skipped check would have caught | none — this row is refused, not deferred |

## 8. Cost, as a model rather than a number

**The unit is percent of a weekly window, and it is read from `/usage`, never
derived** (L-7). Two anchors exist, both measured during 0.2.

- **A build subcycle costs about a point.** 0.2's §8 table records the owner's
  readings for ten build sessions, from 58 to 256 requests each, and each moved
  the weekly gauge by about one point. This cycle has fifteen build
  subcycles — 0.3.0 to 0.3.13, and 0.3.15 — one of them conditional, so about
  fifteen points if they are the same size. That is `REASONED`: 0.3.1, 0.3.2 and 0.3.4
  touch more files than any 0.2 subcycle did, and 0.2.4, the one that touched
  the most, was the most expensive in tokens.
- **The run costs far more, and how much more is not known in points.** 0.2.9
  counted about 743 M processed manager tokens over nineteen tasks, with 43.7 M
  of resumes and about 2.7 times the manager half again in in-process agents
  outside that count, and about `$170` of workers (the register's *The run in
  numbers*). It ran into the owner's weekly limit on 2026-09-14. No pair of
  gauge readings brackets the run alone, so its cost in points was never
  measured — theme 4's finding about the pipeline's meters, applied to this
  plan.

**The model changed under both anchors.** Every figure above was measured on
Claude Opus 5, and 0.2.9's in-process agents ran on Claude Sonnet 5. This cycle
is being planned on Claude Opus 5.5, whose list prices, as the API reference
bundled with the `claude` CLI gives them, are $4 input and $20 output per
million tokens against Opus 5's $5 and $25 — 20% lower — and $0.20 per million
for cache reads against $0.50, 60% lower. Cache reads dominate a long session's
processed tokens, so the blended saving on this pipeline's sessions should sit
well above 20%; the owner's own reading is *"about 40% cheaper"*. Two
consequences, both `REASONED` until measured: the anchors above are probably
high for Opus 5.5 work, and Opus 5.5's cache reads now cost the same per token
as Sonnet 5's ($0.20), which narrows the price case for running supervisors and
verifiers on Sonnet — an input to §10.4. **Whether the owner's weekly gauge
moves in proportion to list price is not known**, and L-7 forbids deriving it:
0.3.0's reconciliation measures it on the current model mix, and records which
model ran each session.

**So this section is not finished, and cannot be until 0.3.0 runs.** 0.3.0's
meter probe produces the missing conversion: metered tokens over an interval
the owner brackets with two `/usage` readings, split by model family. 0.3.14's
plan is then priced from that conversion and from 0.2.9's per-task figures,
once 0.3.5 exists. Until then the recommendation in §5 rests on the two anchors
above: the build costs points, the run costs far more, and the run's size is
the lever.

**Size 0.3.14's ceiling for the failure path.** `REASONED` from 0.2.9: every
ceiling raise in its cycle 2 was overtaken before the first item it priced was
finished, because each task with an adversarial pass stopped more than once
(theme 5). So the third run's ceiling is priced at the observed stops per
adversarial task, not at one incident, and the owner sets it by choosing among
options, as he did in 0.2.9.

**Every subcycle file records its closing cost** in the owner's percentage,
beside `session_cost.py`'s requests and processed tokens, as 0.2's §8 table
does. The owner's display reports percent, so a figure recorded only in tokens
is one he cannot check.

## 9. Conventions for whoever implements this

0.2's §9 carries forward whole: every number comes from a command; run a check
against the live corpus before trusting it; a control that cannot fail proves
nothing; do not write outside this repository; an authorisation is scoped by
the question that obtained it; and when a subcycle tells you to do something
impossible, stop and record it under `## Findings`. Four additions:

- **The live corpus is now `pricelog`'s record**, `~/Workspace/REPOS/pricelog/devteam/`
  at `a88990b`: nineteen tasks, fifteen rotations, 142 findings, and most of
  the states the checks in 0.3.1 to 0.3.3 must handle, restarted claims and a
  stopped cycle included. Read it; never write it. It is private, so a tracked
  file cites it by file and line, as the register does, and reproduces what a
  reader needs.
- **Every check you build ships a control that plants the did-not-look case**
  — zero rows, an untracked file, a wrapped field — and demands that the check
  refuse to call it clean (L-6).
- **Name the register row you are closing** in the commit body — its area and
  heading, or its F-number — so that 0.3.13 can strike README rows and register
  rows from the history rather than from memory.
- **A remedy the register marks `(suggested here, not in the record)` is a
  reader's suggestion, not a measured fix.** Test it before adopting it, as the
  register itself asks of F-5's two candidate repairs (A4).

## 10. Open questions for the owner

Each blocks only the subcycle it names. None blocks 0.3.0.

1. ~~**The third run's project.**~~ **Answered 2026-09-23** — a cowsay clone in
   Nitpick (L-10), in its own repository (L-11), on one pinned compiler (L-12).
2. ~~**A client profile taken at the interview.**~~ **Answered 2026-09-23** —
   minimally, in 0.3.9 (L-13).
3. ~~**The push grant.**~~ **Answered 2026-09-23** — refused at onboarding
   unless the guard honours it; pushing stays the owner's (L-14).
4. **Which model runs which role — blocks 0.3.12, and the model field in
   0.3.4's `dispatch`.** The backlog proposes a Sonnet liaison and an
   Opus-or-Fable interviewer and planner
   ([`v3-liaison-and-roles`](../../v3-liaison-and-roles-2026-09-12.md) §7). The
   owner, 2026-09-23: *"lets see what the probe says."* Asked again with 0.3.0's
   figures, alongside §8's note that Opus 5.5's cache reads now cost the same
   per token as Sonnet 5's.
