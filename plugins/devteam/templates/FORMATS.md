# The formats — the grammar the checks parse

Every artifact in `devteam/` is markdown a human reads and a script parses. This
file is the **one home** for that grammar (P-34): the templates beside it are
instances of it, and `scripts/check_*.py` implement it. A format changes here
first, then in the templates, then in the checks — and its control (P-35) is
what proves the three still agree.

**The parsing contract, and why it is this shape.**

- **Identifiers are `<PREFIX>-<n>`**, declared in a heading and cited in running
  prose. `G-` goals · `R-` requirements · `T-` tasks · `S-` steps · `D-`
  decisions · `Q-` questions · `C-` checkpoints. Prefixes never collide, so a
  citation is unambiguous without knowing what file it is in.
- **Fields are bold-labelled bullets**: `- **Label.** value`. Not YAML, because
  these files are read far more often than they are parsed, and a reader should
  never have to decode a data format to learn what a project decided. Not free
  prose, because then nothing can be diffed against anything.
- **A field's absence is a finding, not a default.** Every check reports
  `missing-field` rather than inventing a value. A default is a decision nobody
  made.
- **One field is a deliberate exception, and it is named here so the rule above
  keeps its credibility.** A task's `Kind.` defaults to `implementation` when
  absent. The reason is compatibility and nothing grander: the field was added
  after task files existed, and reading its absence as a finding would have
  reported every task ever written. **The exception has the cost the rule
  predicts** — a probe written by somebody who has not read the `Kind.` row is
  silently treated as an implementation task — so the `unmotivated-task`
  finding names `Kind.` in its own text, which is where a person meets the
  problem. Any future default needs the same two things: a stated reason, and a
  finding that points at the field.
- **Everything is line-oriented.** A field's value may continue onto the lines
  under it, indented, and the checks read it whole: its first line and every
  line that continues it, joined, so a value reads the same wrapped or not
  (roadmap 0.3.2, L-2.3). A check never needs to parse markdown beyond that.

---

## Identifier declarations

| Artifact | Declared by | Example |
|---|---|---|
| goal | a bullet in `CHARTER.md` §Goals | `- **G-1** — the tool reads a config file` |
| requirement | an `###` heading in `REQUIREMENTS.md` | `### R-1 — config is read from disk` |
| task | the `#` title of `tasks/T-1.md` | `# T-1 — config loader — PLANNED` |
| step | a checklist bullet in a task's §Steps | `- [ ] **S-1** — parse the file` |
| decision | an `###` heading in `DECISIONS.md` | `### D-1 — TOML over YAML` |
| question | an `###` heading in `QUESTIONS.md` | `### Q-1 — which config format?` |
| checkpoint | the `#` title of `checkpoints/C-1-<date>.md` | `# C-1 — 2026-09-03 — ON-COURSE` |
| finding | a bullet in `RECORD.md` | `- **F-9** — a client is not an operator` |

**A citation is the bare identifier in prose or in a field value** — `R-3`,
`D-1`, `T-2`. `check_refs.py` diffs declarations against citations in both
directions (P-22).

**A field read as identifiers holds identifiers, and nothing else** (roadmap
0.3.2, L-2.3):

| Field | Holds |
|---|---|
| requirement `Satisfies.` | goals, `G-n` |
| task `Discharges.` | requirements, `R-n`: the ones this task makes true |
| task `Re-establishes.` | requirements, `R-n`: the ones whose acceptance this task re-establishes **without** taking the discharge — a fix under a requirement another task discharged, which keeps its `discharged (T-n)` |
| task `Depends on.` | tasks, `T-n`, that must be `DONE` first |
| task `Informs.` | the requirements or goals a probe or spike de-risks |

Each holds `none`, or bare identifiers of its kind separated by commas, and
may continue onto indented lines. `check_trace` reads a piece that is anything
else — a sentence, an identifier of another kind, `none` beside an identifier —
as nothing: it names the field as not evaluated, quotes the piece, and reads
no identifier out of it. So a task a sentence mentions is never a dependency,
and a requirement it mentions is never discharged (F-95, F-132). **The reason
goes on a bullet of its own**, after the field:

```
- **Depends on.** T-11, T-14
- **Why T-11 and T-14.** both write `tests/test_failures.py`; a scope
  collision, not a prerequisite.
```

`Re-establishes.` motivates a task as `Discharges.` does, so an implementation
task with either is not `unmotivated-task`. It is not a link: a requirement's
`Status.` names the tasks that discharge it, and a task that only
re-establishes it is not one of them.

**A path list is the field, then one path per indented list item** —
`Scope.` on a task, `Requires-write.` on a requirement — backticked or not,
with nothing else on the item: a reason goes on its own line after the list.
`check_scope` reports an item that is not a bare path as
`unparseable-scope-entry`, and `check_trace` names it as not evaluated.
**Write the list form.** A value written beside the field is read three ways
today: `guard.py` reads only the list items, `check_trace` splits the value at
commas, and `check_scope` reads it as one entry and reports it when it is not
one path. Both checks read it whole, across its continuation lines.

---

## The namespace, and how not to collide with it

**Every short prefix is reserved. This table is the whole of it.**

| Prefix | Numbers | Declared in |
|---|---|---|
| `G-` | a charter goal | `CHARTER.md` |
| `DM-` | a "done means" condition | `CHARTER.md` |
| `R-` | a requirement | `REQUIREMENTS.md` |
| `T-` | a task | `tasks/T-n.md` |
| `S-` | a step within a task | that task's §Steps |
| `D-` | a decision | `DECISIONS.md` |
| `Q-` | an open question | `QUESTIONS.md` |
| `C-` | a checkpoint | `checkpoints/` |
| `F-` | a finding against the pipeline or the project | `RECORD.md`, as `- **F-n** — <one line>` |
| `P-` | a protocol rule | the plugin's `PROTOCOL.md` — **external**, cited here, never declared here |
| `COR-` | a correctness audit finding | `audits/*.md`, as `## COR-n — <title>` |
| `SEC-` | a security audit finding | `audits/*.md`, as `## SEC-n — <title>` |
| `HYG-` | a hygiene audit finding | `audits/*.md`, as `## HYG-n — <title>` |
| `REV-` | a review finding | `audits/*.md`, as `## REV-n — <title>` |
| `CNV-` | a project-family convention | outside any project; cited from the decision that adopts or declines it |

**The five three-letter prefixes above are CHECKED, and no others are.**
`check_refs` resolves them in both directions exactly as it does `D-n`, and
`check_plugin`'s `namespace-drift` diffs this table against the scanner's own
sets so the two cannot part company. **Every other three-letter prefix is still
ignored**, deliberately and by name: the scanner reads `[A-Z]{1,3}` and then
discards anything whose prefix is not reserved, which is why `UTF-8` — 639
occurrences in one project's record — is not a citation.

**The rule: anything else that numbers something uses a prefix of three or
more letters.** `COR-1`, `SEC-5`, `HYG-3` for audit findings by dimension;
`REV-2` for a review finding; `CNV-1` for a project-family convention, which
lives outside any project and is cited from a decision that adopts or declines
it. Never a new one- or two-letter prefix.

**Why, mechanically.** The citation scanner matches `[A-Z]{1,2}-<digits>`
anywhere in an artifact. A two-letter identifier is therefore *indistinguishable
from a citation* — there is no syntax that says "this is my own numbering, not
a reference to yours". A three-letter prefix cannot match, so it is safe
without any further agreement.

**"Safe from collision" also meant "unseen", and 0.2.6 closed that half.** The
scanner that cannot mistake `COR-6` for a citation also could not check it, so
the audit namespace had **no citation integrity at all, in either direction**.
That was not hypothetical. Run over one project's record the first time the
scanner was widened, it reported **thirteen dangling citations** — including
`COR-13`, `COR-14` and `COR-15` cited from a task file and declared nowhere,
and `SEC-2` cited from `DECISIONS.md`. Every one had been invisible for the
whole of cycle 0.1.

**What watches the namespace now, and what still does not.** `cited-undefined`
and `duplicate-id` apply to these five as they do to `D-n`. `defined-uncited`
deliberately does **not**: a finding nobody cites is the ordinary state of one
still `Disposition. open`. In its place is `undispositioned-finding` — a
finding whose `Disposition.` is `open` or missing.

**And the citation is not an escape from the disposition, which is the part
that took a measurement to get right.** The obvious rule is *"cited, **or**
dispositioned"*. Measured over a real project it reports **zero**, against five
findings that carry no `Disposition.` line at all — because they are mentioned
in `RECORD.md`, `QUESTIONS.md` and the charter. **Mention is not disposition.**
A finding logged in the record and never routed is exactly the case the field
was added for, so a citation cannot excuse a missing one.

Treat a namespace exemption as a debt rather than a solution, and say what is
covering it.

**The general form, because it will recur:** a thing exempted from a checker
for its own protection is a thing the checker cannot see. Whenever you carve
something out of a check, name what watches it instead, or record that nothing
does.

**Why it matters, from experience.** This has now bitten three times, in three
different disguises, and each time it cost a real finding:

- a supervisor recommending a new requirement wrote `R-3` inside the
  recommendation. It read as a citation to a requirement nobody had declared,
  reported `cited-undefined`, and the proposal had to be reworded.
- a security audit numbered its findings `S-1 … S-12`. Citing one from a task
  file reported `cited-undefined` against a *step* that does not exist, so the
  finding ended up referred to in prose and nearly lost.
- both times the instinct was to obfuscate the identifier to get past the
  check. **Do not.** A worker once wrote a plausible path that did not exist
  for the same reason. If you need to name something the grammar does not
  cover, give it a three-letter prefix and add it here.

**Proposing something by number is not the same as citing it.** When you
recommend a requirement that should exist, describe it — *"a requirement for
undecodable input, same one-line form as R-2"*. The manager allocates the
number on accepting it, because numbering is how a project records that it
agreed to something.

---

## Status vocabularies

Closed sets. A value outside its set is `bad-status`, never a guess.

| Where | Values |
|---|---|
| requirement `Status.` | `open` · `in-progress (T-n)` · `discharged (T-n)` · `partly-discharged (T-n; D-n)` · `awaiting-judgement (T-n; Q-n)` · `struck (D-n)`. **The task list may name several** — `in-progress (T-2, T-5)` — because a requirement is frequently advanced by one task and completed by another, and forcing one id makes the record say something untrue. **`partly-discharged`** names the tasks that discharged part of it and the decision that records what remains; **`awaiting-judgement`** names the tasks that built and evidenced it and the question that asks the client whether it is discharged (roadmap 0.3.2, L-2.4). Either may be left over a closed task that it names, where `open` may not. A parenthetical holds identifiers only: what remains is written in the decision or the question |
| task title | `PLANNED` · `RUNNING (since <date>, <label>)` · `READY-TO-AUDIT` · `BLOCKED (<why>)` · `NEEDS-DECISION (<what>)` · `ACCEPTED (<date>, D-n)` · `DONE (<date>)` |
| task `Kind.` | `implementation` (default when absent) · `probe` · `spike` · `chore` |
| step checkbox | `[ ]` pending · `[x]` done · `[~]` struck, with a reason on the line |
| question `Status.` | `open` · `answered D-n` · `proceeded-unreviewed D-n` · `withdrawn` |
| question `Class.` | `REVERSIBLE` · `IRREVERSIBLE` · `CHARTER` |
| checkpoint verdict | `ON-COURSE` · `DRIFTED` · `BLOCKED` |
| REPORT `status:` | `DONE` · `BLOCKED` · `NEEDS-DECISION` · `RED` · `READY-TO-AUDIT` |
| board task state | `—` · `CLAIMED <label>` · `BLOCKED on T-n` · `BLOCKED on Q-n` · `DONE` · `ACCEPTED (<date>, D-n)`. **Several blockers are comma-separated** — `BLOCKED on T-2, Q-4` — for the reason a requirement's status may name several tasks. The cell holds the state and nothing after it: a reason goes in the in-flight table's `Note`. `check_trace` reads the state from the Tasks table, the one whose header names `Task` first and has a `State` column, and a row may name its task bare, as a link, in bold or in backticks (roadmap 0.3.2, L-2.1) |
| charter `Containment` | `structural` · `guard-only`. Written by `/devteam:setup` from `sandbox_probe.py`'s exit code and re-checked at every `/devteam:run` startup. **Not a preference and never copied from an example** — it is a fact about the machine |
| promotion findings | `promote-base-disagreement` · `promote-conflict` · `promote-extraction-failed` · `promote-fetch-failed` · `promote-foreign-subject` · `promote-history-rewrite` · `promote-host-index-dirty` · `promote-no-commits` · `promote-no-scope` · `promote-no-task-file` · `promote-out-of-scope` · `promote-task-file-unparsed` · `promote-task-file-untracked` · `promote-uncommitted`. Check output, closed set, emitted by `sandbox.py promote` and by its `--dry-run`. 0.2.6 is where each is named against the rule it enforces |
| `check_report` harness findings | `budget-mismatch` · `model-mismatch`. Silent on a `guard-only` project, which has no harness meter — **an absent measurement is not a finding** |

---

## The liveness files under `.run/locks/`

Two files per task, both **rewritten and never deleted** — an absent file and a
file nobody wrote read identically, and recovery has to tell *no worker ran*
from *a worker ran and we lost it*.

```
<TASK>.heartbeat   waiting on S-n (<role>, dispatched <time>, sandbox <id>)
                   closed <date>, verified PASS
<TASK>.sandbox     T-n S-m <id> pid <n> started <iso> step-timeout <s> root <abs>
                   T-n S-m <id> exited <code> at <iso> root <abs>
```

The supervisor writes the heartbeat; the harness writes the `.sandbox` line.
**The root is an absolute path on the line itself**, not derivable from the id:
resolving one to the other means reading a machine-local environment variable
the way the writer did, which is a second home for a path, and the second home
is the one that is wrong. `check_report` finds `meta/budget.json` through it.

Both live under `devteam/.run/`, **which must be git-ignored** — `/devteam:setup`
writes that line, and `sandbox.py dispatch` refuses if it is missing, because
otherwise the harness's own file lands in the worker's uncommitted remainder and
`promote` refuses the promotion for it.

---

## The REPORT block

Defined in [`../DESIGN.md`](../DESIGN.md) §6 and repeated nowhere. It is the one
format that is **not** bold-labelled bullets — its keys start at column one and
continuations are indented — because it is emitted by an agent as its final
message, where markdown decoration is exactly what goes wrong.

`check_report.py` parses it out of a task file's `## Execution record` section
and compares what it claims against the tree.

---

## What each check reads

| Check | Reads | Diffs |
|---|---|---|
| `check_trace.py` | `CHARTER.md`, `REQUIREMENTS.md` and its committed history, `tasks/*.md`, `BOARD.md`'s Tasks table — and its in-flight table while a task is `CLAIMED` — and `audits/` | goals ↔ requirements ↔ tasks ↔ acceptance criteria; the board ↔ the task titles |
| `check_refs.py` | every `.md` git would show under `devteam/` | citations ↔ declarations; links ↔ files; leaks |
| `check_report.py` | one `tasks/T-n.md`, `git`, and the harness's `.run/locks/T-n.sandbox` line | the REPORT block ↔ the committed tree |
| `check_scope.py` | `BOARD.md`, `tasks/*.md`, `git log` and `git status` | declared scopes ↔ each other, and ↔ what was written |

`check_trace`, `check_refs` and `check_scope` read **what git would show**
under `devteam/`: tracked files, and untracked ones that no ignore rule
covers. Each untracked file a check reads is a finding of its own,
`untracked-file`, because a file in no commit is invisible to a clone, a
review and the gate (roadmap 0.3.1, L-1.4; F-131). Ignored files,
`devteam/.run/` among them, stay invisible, so scratch belongs outside
`devteam/` or under an ignore rule. `check_report` reads the one task file
it is given. Every project check also reads `DECISIONS.md`'s `Accepts.`
fields, for what a decision accepted (§"Accepted findings").
Every check exits `0` clean · `1` findings · `2` could not run · `3` not
evaluated, and takes `--json` and `--at-commit`. `--at-commit` says the tree is
a clean checkout of one commit, which is how the commit gate reads it
(`scripts/gate.py`, P-49). It excludes the classes that read the working
state, each named in the line. `3` means the check ran and names a part it did
not look at, with the reason — which is never clean (P-50). The contract, and
what each result means, is `scripts/result.py`'s (roadmap 0.3.1, L-1.1).

A part is not looked at when its source **offered a row the grammar did not
read** — a heading, list item, table row or field line written in a shape
this file does not define, each named by file and line — or when **an
identifier field holds a piece that is not an identifier**, which is named
with the piece (§"Identifier declarations"). Zero rows parsed from a source
that offered some is the same thing. A source that offers nothing is
genuinely empty, and clean, with its zero shown in the line (roadmap 0.3.1,
L-1.3). So a row written slightly wrong is never silently skipped: fix the
row, or, for an identifier field, keep the identifiers in the field and move
the explanation to a bullet of its own, which is how pricelog's T-19 repaired
its `Discharges.` field (F-132). `check_trace`, `check_refs` and
`check_scope` read every field whole, across its continuation lines (roadmap
0.3.2, L-2.3). `check_report` still reads a REPORT block's `status:` from its
first line, and names one that continues.

**The gate reads the checks, and an agent commits only through it** (P-49).
`scripts/gate.py commit -F <message file> -- <paths>` builds the commit
without moving any ref, then runs the four project checks with `--at-commit`
and `--json` on HEAD and on that commit. It makes the commit only if the
commit adds no finding and no part not evaluated that HEAD lacks, counted by
the identity an acceptance matches by. A finding already at HEAD stands, and
it is printed at every run. The gate exits `0` committed · `1` refused · `2`
could not run, and nothing is committed on `1` or `2`. `docs/CHECKS.md` lists
its refusal classes. In a devteam project, the `commit_guard.py` hook refuses
an agent's commit made any other way: a git command that writes a commit, or
a branch pointed at a commit no branch holds. A worker inside a sandbox is not
refused, because promotion gates its commits (P-44).

## Accepted findings

A finding that will not be fixed is **accepted by a decision**: a `D-n` in
`DECISIONS.md` carrying an `Accepts.` field. It is never accepted by a
baseline file, a flag or a comment (P-51). Each item names one
finding as the check prints it: the check, the class and the anchor file, each
in backticks, then a dash and the message. A part not evaluated is named by its
part, up to its dash. One acceptance, one line.

```
- **Supersedes.** none
- **Reviewed.** unreviewed
- **Accepts.**
  - `check_trace` `missing-field` `tasks/T-1.md` — T-1 has no **Discharges.**
  - `check_refs` not evaluated: audits/x.md's findings
```

- **No line number.** The anchor's line is left out, and so is any line number
  inside the message, so an edit above the anchor does not un-accept it. What
  is matched is the finding's identity: its check, class, anchor file and
  message. The gate compares HEAD with the commit it is about to make by the
  same identity.
- **Who decides.** The decision's P-26 class decides who makes it. The
  manager decides a `REVERSIBLE` acceptance alone, recorded as unreviewed under
  P-27; the client decides a `CHARTER` one. A decision carrying `Accepts.` must
  have a `Reviewed.` line reading `client`, `unreviewed` or
  `proceeded-unreviewed (Q-n)`, or it accepts nothing, because that line is
  where P-27's record lives. **The check enforces that the line is there. It
  cannot enforce which class an acceptance is**, because no check can tell what
  a finding means to the charter: that stays the decider's judgement.
- **Cited, like every decision.** A decision nothing cites is
  `defined-uncited` (P-22). So the commit that adds an accepting decision also
  cites it, normally with a `RECORD.md` line saying what it accepted.
- **What the check does.** It reports each accepted finding under the number
  of the decision that accepted it, says how many on its result line, and exits
  `0` when nothing else is found. An accepted part is still a part nobody looked
  at, so a line that accepted one never says the whole was read.
- **Stale.** An acceptance whose finding no longer fires is
  `stale-acceptance`, so the count returns to zero and stays a signal
  (CONSOLIDATION §8a). So fixing an accepted finding means superseding the
  decision that accepted it, carrying over whatever else it accepted that
  still stands.
- **Withdrawn.** A decision named in another decision's `Supersedes.` line
  accepts nothing (P-23).
- **Outside the grammar.** An `Accepts.` line or item outside this grammar
  accepts nothing, and `check_refs` reports it as `unparseable-acceptance`.
  That covers a field line that is not exactly `- **Accepts.**`, a field with no
  item, an item in neither shape or wrapped past its line, a check that is not
  one of the four project checks, a field in no decision, and a decision with
  no `Reviewed.` line.
- **Runs that read one task.** `check_report` runs for one task, so an
  acceptance of its finding covers the run for that task, and never another
  task's run or a step's. A part of `check_report` cannot be accepted: its parts
  name no task, so no run could ever find such an acceptance stale.
  `check_scope`'s `undeclared-write` is judged only by the run for the task it
  names.
- **An acceptance cites nothing.** It is quoted check output, so `check_refs`
  reads no identifier from its lines. Otherwise, accepting a finding that names
  an undeclared `T-99` would cite `T-99` from `DECISIONS.md`, and a new finding
  would appear there in place of the one accepted.

## The identifier prefixes are reserved

`G` `DM` `R` `T` `S` `D` `Q` `C` `F` are this project's namespace, and
`check_refs` resolves every occurrence of `<prefix>-<number>` in a tracked
artifact against a declaration. **Do not number anything else this way** —
product test cases, fixtures, error codes, probe scenarios.

The failure is delayed and therefore easy to miss. A probe script numbering its
cases `C-1`, `C-2` is harmless right up until the project files its first
checkpoint, at which point a document quoting `C-1` resolves it against that
checkpoint and says nothing is wrong. A supervisor reported this one while it
was still latent, which is the only time it is cheap: afterwards the two
meanings are both in the record and neither can be renamed without rewriting
history.

If product code needs numbered cases, give them a prefix that is not a single
or double capital followed by a dash — `case_1`, `FC1`, `probe-1` all avoid it.

## An artifact conforms to the template it came from, at the current version

The templates are the grammar, and a project's artifacts are instances of them.
**An artifact stays conformant as the template changes** — a row or field added
later belongs in artifacts already created, not only in ones scaffolded
afterwards. Checked by `template-drift`.

Stated because it was not, and a check was enforcing it anyway. The test worth
applying to any check here: **name the rule whose two sides it compares. If you
cannot name one, the check is proposing a rule rather than enforcing one** —
and that is a decision for whoever owns the rules, not something a script gets
to make by firing.
