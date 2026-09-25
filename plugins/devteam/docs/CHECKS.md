# Every finding class, and the rule whose two sides it compares

**A check is legitimate only when it enforces a rule that exists, and a rule
exists only when something checks it.** This file is one half of that pair for
every finding class the pipeline emits. Its other half is `unruled-finding` in
`check_plugin.py`, which diffs this file against the code and fails if they
disagree.

## The test each row is held to (L-6.1, from F-113)

**Name the rule whose two sides the check compares.** If you cannot name one,
the check is *proposing* a rule rather than enforcing one — and its false
positives are that missing rule showing up, not noise to tune away. A class
that proposes gets its rule written, or gets withdrawn. It never gets tuned.

Each row therefore carries four things: the **class**, the **rule** (a `P-n`,
a section of `templates/FORMATS.md`, or a template's own declaration), the
**two sides** the check actually diffs, and a **verdict** — `enforces` or
`proposes`.

## Why the class list here is machine-derived, and the docstrings no longer carry one

This table was built by parsing the **abstract syntax tree** of each check for
the string literal in the first argument of every bare `add(...)` and
`findings.append((...))` call — not by reading the docstrings.

The docstrings used to carry their own class lists. **Ten classes were emitted,
carried control cases, and appeared in no docstring**, and the convention for
parsing them (two leading spaces and a hyphenated name) silently dropped both
single-word classes and the longest names, giving 44, 46 or 47 depending on how
it was written, against 57 from the AST. A check that took the docstring as its
declared side would have been blind to precisely the ten classes with no rule
written — the instrument answering an adjacent question (P-35b).

So the class enumerations were **removed from the five docstrings** and their
rationale moved here. This file is the one home (P-34); the drift surface is
deleted rather than watched.

**Rows are keyed by (check, class), not by class.** `broken-link` is emitted by
both `check_refs` and `check_plugin`, and `missing-field` by both `check_trace`
and `check_report`. A shared name is not a shared rule: a missing field in a
task file and a missing key in a REPORT block are different defects with
different remedies.

**The parser fails loudly rather than skipping.** Two shapes look like emit
sites and are not — the dispatcher's own definition
(`add = lambda kind, where, detail: ...`, whose first argument is a parameter)
and `set.add()`. A parser that silently skips any non-literal first argument
handles both correctly *by accident*, and would also skip a genuine emit site
written with a computed name. It therefore matches bare `add(...)` only,
excludes the lambda's assignment, and raises on any surviving non-literal. That
assertion fires on nothing today. It is a tripwire, not a filter.

---

## `check_trace.py` — 26 classes

Reads `CHARTER.md`, `REQUIREMENTS.md`, `tasks/*.md`, `BOARD.md` and `audits/`,
tracked or untracked and not ignored, and `DECISIONS.md`'s acceptances. Diffs
goals ↔ requirements ↔ tasks ↔ acceptance criteria.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `unparseable-protected-path` | `templates/CHARTER.md`'s `Protected paths` cell — *"one path per entry, comma-separated, and nothing else in this cell"* | each entry the **guard** splits out of the charter's row ↔ that grammar. The guard's own regexes are imported, not restated (P-34). A cell that is one placeholder, as the template ships it, is tested whole before it is split, and is clean (roadmap 0.3.2, L-2.11) | `enforces` |
| `orphan-scope` | P-1 — the charter is what the project is | charter goals ↔ the `Satisfies.` fields of every requirement | `enforces` |
| `uncovered-requirement` | P-4, P-5 | requirements ↔ the `Discharges.` fields of every task | `enforces` |
| `unmotivated-task` | P-4 | an implementation task's `Discharges.` and `Re-establishes.`, each read as bare identifiers (`FORMATS.md` §"Identifier declarations"; roadmap 0.3.2, L-2.3, L-2.4) ↔ the declared requirements | `enforces` |
| `unverified-requirement` | P-3 — every requirement is numbered, normative and **testable** | a requirement's `Acceptance.` ↔ the set of runnable criteria | `enforces` |
| `missing-field` | `FORMATS.md` §"Identifier declarations" — the field list per artifact | the fields a template declares ↔ the fields the artifact carries | `enforces` |
| `unknown-reference` | P-22 — a decision cited must be declared | the bare identifiers in `Satisfies.`, `Discharges.`, `Re-establishes.`, `Informs.` and `Depends on.` ↔ identifiers declared. A sentence in one of those fields names nothing: it is a part not evaluated, quoting the piece (roadmap 0.3.2, L-2.3) | `enforces` |
| `dependency-cycle` | P-45 — a task graph is acyclic | a task's `Depends on.` closure, its edges the field's bare task identifiers only, so a task a sentence mentions is no edge (F-95; roadmap 0.3.2, L-2.3) ↔ itself | `enforces` (P-45, written here) |
| `gate-omits-decision` | P-18 — reported green is not green; P-5 | decisions a requirement's `Statement.`/`Acceptance.` rests on ↔ the `Gate.` of every discharging task | `enforces` |
| `re-litigated-requirement` | P-46 — rewritten three times means shape review | a requirement's revision count ↔ the threshold 3 | `enforces` (P-46, written here) |
| `board-drift` | P-11 — the board is the lock; P-34 — facts have one home | the `State` of each row of `BOARD.md`'s Tasks table — the table whose header names `Task` first and has a `State` column — ↔ each task file's own title status. `CLAIMED` allows the title a supervisor writes at a close or a stop while the task has a row in the in-flight table (roadmap 0.3.2, L-2.2) | `enforces` |
| `bad-board-state` | `FORMATS.md` §"Status vocabularies", board task state | a Tasks-table `State` cell, bold and backticks removed ↔ the closed set `—` · `CLAIMED <label>` · `BLOCKED on T-n` or `Q-n`, several comma-separated · `DONE` · `ACCEPTED (<date>, D-n)`, matched whole (roadmap 0.3.2, L-2.1) | `enforces` |
| `one-sided-link` | P-4 | a requirement's `Status.` task list ↔ that task's `Discharges.`, read as bare identifiers. A RUNNING task's requirement reads `in-progress` naming it; a closed task's reads `discharged`, `partly-discharged` or `awaiting-judgement` naming it, or `in-progress` naming another task that has not finished (roadmap 0.3.2, L-2.4). A task that only re-establishes a requirement is not one its status may name | `enforces` |
| `template-drift` | `FORMATS.md` §"An artifact conforms to the template it came from, at the current version" | the charter's constraint rows ↔ the **current** template's rows | `enforces` |
| `amendment-omits-condition` | P-48 — an amendment re-affirms every done-means and constraint row | the charter's current `DM-n` list and constraint row labels ↔ the `Re-affirmed.` enumeration of the latest entry — the highest `Version n` — read from its heading to the next entry heading or the section's end, each item whole. A verdict is `holds`, `amended (this entry)`, `added (this entry)` or `struck (D-n, why)`. An entry that lists conditions under any other opener is a part not evaluated, naming the entry (roadmap 0.3.2, L-2.9) | `enforces` |
| `amendment-names-unknown` | P-48 | the latest entry's `Re-affirmed.` names, `added (this entry)` among them ↔ the charter's current conditions | `enforces` |
| `stale-version-header` | `templates/CHARTER.md` — the header's `Version.`, and *"Entries are numbered `Version <n>` … The number is what identifies the latest entry"*; `FORMATS.md` §"Status vocabularies", charter header | the charter header's `**Version.** <n>` ↔ the newest amendment entry's number, or 1 with no entry (roadmap 0.3.2, L-2.9; pricelog's Version 18, RECORD.md:1350) | `enforces` |
| `unrecorded-amendment` | P-2 — changing what is being built is a charter amendment | a requirement's committed `Requires-write.` ↔ its current one | `enforces` |
| `unreachable-acceptance` | P-10 — a worker writes only inside its declared scope; P-5 | a requirement's `Requires-write.` ↔ the `Scope.` of each single discharging task | `enforces` |
| `unparseable-task` | `FORMATS.md` §"Status vocabularies", task title | the file's first line ↔ the `# T-n — <title> — <status>` grammar | `enforces` |
| `untracked-file` | `FORMATS.md` §"What each check reads" — a check reads every file git would show, and names each one no commit holds (roadmap 0.3.1, L-1.4) | the files the check reads ↔ git's index | `enforces` |
| `stale-acceptance` | P-51 — an accepted finding is a decision, and an acceptance whose finding no longer fires is itself a finding, so the count returns to zero; `FORMATS.md` §"Accepted findings" (CONSOLIDATION 8a) | each acceptance of a `check_trace` finding or part ↔ what this run reported, less any class a declaration excluded | `enforces` |
| `estimate-step-mismatch` | P-41 — estimates come from a stated model; `FORMATS.md` §"Identifier declarations", the estimate | a `PLANNED` task's `Estimate.` `model=<n>x…` ↔ the step lines under its `## Steps`, struck ones included, a step named twice counted once. Compared only while the title reads `PLANNED`: the model counts the steps as planned, and its rounds rate prices each step a supervisor adds once the task runs (roadmap 0.3.2, L-2.10, the owner's answer of 2026-09-24). No `## Steps` is compared with nothing | `enforces` |
| `bad-kind` | `FORMATS.md` §"Status vocabularies", task `Kind.` | the declared `Kind.` ↔ the closed set `implementation · probe · spike · chore` | `enforces` |
| `open-finding-at-close` | P-31 — the audit precedes the close | an audit file's `Disposition.` values, read whole, open when the first word is `open` ↔ the audited task's title status | `enforces` |
| `unjustified-task` | P-45 — a probe names what it de-risks | a probe/spike's `Informs.`, read as bare identifiers ↔ the declared requirements and goals | `enforces` (P-45, written here) |

## `check_refs.py` — 11 classes

Reads every `.md` under `devteam/` that git would show: tracked, or untracked
and not ignored. Diffs citations ↔ declarations, links ↔ files, and scans for
leaks.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `cited-undefined` | P-22 | identifiers cited ↔ identifiers declared | `enforces` |
| `defined-uncited` | P-22 — *and a decision declared must be cited* | decisions declared ↔ decisions cited | `enforces` |
| `duplicate-id` | `FORMATS.md` §"Identifier declarations" — one declaration per identifier | declaration sites ↔ each other | `enforces` |
| `broken-link` | `FORMATS.md` §"What each check reads" | relative link targets ↔ files on disk | `enforces` |
| `bad-status` | `FORMATS.md` §"Status vocabularies" | a written status value, a `Status.` or `Class.` field read whole across its continuation lines ↔ its closed set | `enforces` |
| `leak` | P-47 — a tracked artifact contains only what a reader can see, and no credential | tracked file content ↔ the absolute-path and credential patterns | `enforces` |
| `control-character` | P-47 | file bytes ↔ the printable set, outside tab and newline | `enforces` |
| `untracked-file` | `FORMATS.md` §"What each check reads" — a check reads every file git would show, and names each one no commit holds (roadmap 0.3.1, L-1.4) | the files the check reads ↔ git's index | `enforces` |
| `undispositioned-finding` | CONSOLIDATION 7; `FORMATS.md` §"The namespace" — an exemption is a debt, and something must watch it | an audit finding's `Disposition.`, read whole ↔ the set of dispositions that are not `open`. `open` is the value's first word, so a note after it leaves the finding open | `enforces` |
| `stale-acceptance` | P-51 — an accepted finding is a decision, and an acceptance whose finding no longer fires is itself a finding, so the count returns to zero; `FORMATS.md` §"Accepted findings" (CONSOLIDATION 8a) | each acceptance of a `check_refs` finding or part ↔ what this run reported | `enforces` |
| `unparseable-acceptance` | P-51; `FORMATS.md` §"Accepted findings" — an `Accepts.` line outside the grammar accepts nothing, and is reported | each line of `DECISIONS.md` naming `Accepts.`, and each item under one ↔ the acceptance grammar, including the decision's `Reviewed.` line | `enforces` |

## `check_report.py` — 14 classes

Reads one `tasks/T-n.md` plus `git`, the harness's `.sandbox` line, and
`DECISIONS.md`'s acceptances. Judges the task's latest task-level block and each
step's latest block, and diffs each ↔ the committed tree; an earlier block for the
same id is a superseded attempt, and is not judged (roadmap 0.3.2, L-2.7; F-37).
Each finding names its block, and is anchored at its header.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `no-file` | P-16 — a report has one shape, in two places | the task id reported ↔ `tasks/` | `enforces` |
| `no-report` | P-16 | the task file ↔ the required `## Execution record` REPORT block | `enforces` |
| `wrong-task` | P-16 | the block's task id ↔ the file it is committed in | `enforces` |
| `missing-field` | `FORMATS.md` §"The REPORT block" | the block's keys ↔ the required key set. A key may carry an annotation, `checks (<why>):`, and is read as its key (roadmap 0.3.2, L-2.7; F-88) | `enforces` |
| `bad-report-status` | `FORMATS.md` §"Status vocabularies", REPORT `status:` | the reported status, read whole ↔ the closed set of five, which may carry one qualifier, `(reconstructed: <by whom, and why>)` (roadmap 0.3.2, L-2.8; F-86) | `enforces` |
| `status-mismatch` | P-34 — facts have one home | the task's current report's `status:` ↔ the task title's status. A task-level block already in the file when the claim its `RUNNING` title names began is the previous claim's, and is compared with nothing of the current run: not the title, the meter or the tree (roadmap 0.3.2, L-2.7; F-136) | `enforces` |
| `unknown-commit` | P-5 — discharged by evidence, never assertion | each commit under `commits:` ↔ HEAD's history: a hash names an ancestor of HEAD, not merely an object, and a subject is one a commit in HEAD's history has. At the gate HEAD is the commit being judged, so another branch's commits, a promotion's leftovers under `refs/devteam/sandbox/` and a refused gate candidate resolve nothing (roadmap 0.3.2, L-2.6) | `enforces` |
| `head-subject` | P-16 | the subjects in HEAD's history ↔ one beginning with the task this report closes (roadmap 0.3.2, L-2.6) | `enforces` |
| `dirty-tree` | P-44 — promotion is gated; P-5 | `git status --porcelain` ↔ empty, on the task's current report's closing status | `enforces` |
| `unfinished-scope` | P-5 | TODO/FIXME/XXX/`NotImplementedError` inside `Scope.` ↔ empty, on the task's current report's closing status | `enforces` |
| `no-evidence` | P-5 — a requirement is discharged by evidence, never by assertion | a closing status ↔ the presence of `checks:` lines | `enforces` |
| `budget-mismatch` | P-41 — budget is tracked per task, estimates from a stated model | a step's block's `tokens=`/`minutes=` ↔ the meter the `.sandbox` line names for that step; `~N` is read as N, marked approximate, at the same tolerance (roadmap 0.3.2, L-2.8; F-32). A task-level block is a supervisor's, which the harness never meters, and is excluded by name; a step whose block that meter does not belong to — another step's (F-103), or a later attempt's, whose sandbox opened with the block already in the file — is not evaluated, and named (L-2.7) | `enforces` (**advisory**) |
| `model-mismatch` | P-40 — model choice is bounded by the charter and recorded | a step's block's `model:` ↔ the model the harness ran for that step, on the same terms: a supervisor's task-level block is never compared with its last worker's meter (F-109) | `enforces` (**blocking**) |
| `stale-acceptance` | P-51 — an accepted finding is a decision, and an acceptance whose finding no longer fires is itself a finding, so the count returns to zero; `FORMATS.md` §"Accepted findings" (CONSOLIDATION 8a) | each acceptance of this task's findings ↔ what a run for the task reported. A run for another task, or for a step, covers none | `enforces` |

**The advisory/blocking split is itself a rule, and 0.2.4 measured why.** A
supervisor met `budget-mismatch` on correct work and could not close: the
finding is recorded, never corrected, a non-zero exit is a FAIL, and no
re-dispatch can help because the next worker cannot see the harness counter
either. `--blocking-only` changes the **verdict** and never the report — every
advisory finding is still printed and the verifier copies each into its verdict.
`model-mismatch` is deliberately not advisory: a report naming a model that did
not run is a report about a different run (P-40).

## `check_scope.py` — 9 classes

Reads `BOARD.md`'s history and `tasks/*.md`, tracked or untracked and not
ignored, and `DECISIONS.md`'s acceptances. Diffs declared scopes ↔ each other
and ↔ what was written.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `overlapping-scope` | P-12 — one writer per scope, and scopes never overlap | the `Scope.` of each live task ↔ every other live task's | `enforces` |
| `undeclared-write` | P-10 — a worker writes only inside its declared scope | paths touched by the commits in HEAD's history whose subject begins `T-n:` or `T-n.S-m:` ↔ the task's `Scope.` (roadmap 0.3.2, L-2.6) | `enforces` |
| `empty-scope` | P-12 | a claimed task's `Scope.` ↔ non-empty | `enforces` |
| `scope-escapes-tree` | P-10, P-43 | a scope entry ↔ the project root | `enforces` |
| `unparseable-scope-entry` | `FORMATS.md` §"Identifier declarations" — a `Scope.` item is a bare path | a list item under `Scope.`, or the value written beside it read whole as one entry (roadmap 0.3.2, L-2.3) ↔ the bare-path grammar | `enforces` |
| `foreign-write` | P-12 | uncommitted paths ↔ the union of every live scope | `enforces` |
| `misattributed-write` | P-10, P-12 | the paths touched by each commit naming no task, after a RUNNING task's current claim ↔ that task's scope and its own file. The claim is the label its title names, `RUNNING (since <date>, <label>)`, and it began at the first commit in HEAD's history whose board carries that label in the in-flight table, on the task's row (roadmap 0.3.2, L-2.5; `claim.py`). **What the window does not see:** a commit made before the current claim, while the task was stopped, is judged by nothing here, and neither is a stranger's commit outside every live scope; a title that names no claim, or a label no board commit carries, leaves the window a part not evaluated | `enforces` |
| `untracked-file` | `FORMATS.md` §"What each check reads" — a check reads every file git would show, and names each one no commit holds (roadmap 0.3.1, L-1.4) | the files the check reads ↔ git's index | `enforces` |
| `stale-acceptance` | P-51 — an accepted finding is a decision, and an acceptance whose finding no longer fires is itself a finding, so the count returns to zero; `FORMATS.md` §"Accepted findings" (CONSOLIDATION 8a) | each acceptance of a `check_scope` finding or part ↔ what this run reported. `undeclared-write` is judged only by a run for the task it names | `enforces` |

## `check_plugin.py` — 18 classes

Internal consistency of the plugin itself. Every finding is a diff between two
lists (P-4).

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `missing-skill` | P-34 | an agent's preloaded skills ↔ `skills/` | `enforces` |
| `name-mismatch` | P-34 | a skill's directory name ↔ its frontmatter `name` | `enforces` |
| `bad-frontmatter` | `FORMATS.md` §"Identifier declarations" | a skill/agent file ↔ the required frontmatter keys | `enforces` |
| `missing-script` | P-34 | scripts named by skills, agents and hooks ↔ `scripts/` | `enforces` |
| `unknown-rule` | P-22 | `P-n` cited anywhere in the plugin ↔ `PROTOCOL.md`'s declarations | `enforces` |
| `uncontrolled-check` | P-35 — a check that has never failed has not been shown to work | check scripts ↔ their negative controls | `enforces` |
| `broken-link` | `FORMATS.md` §"What each check reads"; for a script, roadmap 0.3.2, L-2.13 | relative link targets in plugin docs, and each path under the plugin's own directories that a Python file backticks in a docstring or comment, read from the plugin's root ↔ files on disk. A path holding a `<placeholder>` is a pattern and is not looked up, a glob must match something, and a project's path is written from its root — `devteam/…`, `<project>/…` — because a project may have a `meta/` or a `docs/` of its own | `enforces` |
| `bad-manifest` | P-34 | `plugin.json` and the marketplace entry ↔ the tree they describe | `enforces` |
| `namespace-drift` | `FORMATS.md` §"The namespace" — *this table is the whole of it* | prefixes reserved in `FORMATS.md` ↔ prefixes recognised by `check_refs.py` | `enforces` |
| `template-ships-a-finding` | P-35b; the general rule that an installed template declares nothing of this repository | a freshly scaffolded project's `check_trace --pre-plan`, `check_refs` and `check_scope` output ↔ empty (roadmap 0.3.2, L-2.11; `check_refs` alone until then) | `enforces` |
| `template-scaffold-fails` | P-35b | `setup.py`'s exit ↔ success, before any other template check runs | `enforces` |
| `unruled-finding` **(new)** | L-6.1 / this file | classes emitted by each check (AST) ↔ the rows of `docs/CHECKS.md` | `enforces` |
| `stale-row` **(new)** | L-6.1 / this file | the rows of `docs/CHECKS.md` ↔ classes emitted by each check (AST) | `enforces` |
| `stranded-done-subcycle` | `meta/roadmap/README.md` — *"when a subcycle reaches `DONE`, move its file to `done/`"* | a subcycle file's title-line state ↔ the directory it sits in | `enforces` |
| `undone-subcycle-in-done` | `meta/roadmap/README.md` — *"`ls done/` is what happened"* | the contents of `done/` ↔ each title line reading `DONE` | `enforces` |
| `subcycle-without-state` | `meta/roadmap/README.md` — *"the title line of a subcycle file is the one home for its state"* | a subcycle file's title line ↔ the four declared states | `enforces` |
| `stray-root-entry` | `README.md` §"What is in this repository" — *"everything at the repository root is listed here"* | what git would publish at the root ↔ the README's root table | `enforces` |
| `stale-root-row` | `README.md` §"What is in this repository" — the same sentence, read the other way | the README's root table ↔ what git would publish at the root | `enforces` |

## `gate.py` — 5 refusal classes

`gate.py commit` makes a commit only once the project checks have been run on
it (P-49; roadmap 0.3.1, L-1.5). It runs them with `--at-commit` in a clean
checkout of HEAD and then of the candidate: the three plan checks, `check_scope`
once per task, and `check_report` per task that has reported or says it is
closed. It compares the two by the identity an acceptance matches by
(`result.identity`), and it reads the working state from the live checkout. It
exits `0` committed, `1` refused, or `2` could not run. *Could not run* is
never a class: it covers the invocation, a check that exits 2 or prints
output the gate cannot read, and a project with nothing at HEAD to compare
with. Nothing is committed on 1 or 2.

`--pre-plan` holds back `uncovered-requirement` for a requirement the commit
adds, and for none HEAD already has: before a requirement's task is planned —
at onboarding, and at every later cycle's charter gate — it is uncovered by
construction, while one that loses its task is a finding (settled by the owner,
2026-09-24). Once committed, it stands and is printed until a task discharges
it.

`--at-commit` is the declaration each project check reads for this. It excludes
the classes that read the working state, which no commit holds, each listed in
its check's `WORKING_STATE`: `untracked-file` in the three plan checks,
`foreign-write` in `check_scope`, and `dirty-tree`, `budget-mismatch` and
`model-mismatch` in `check_report`. The gate reads those classes from the live
checkout instead.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `adds-finding` | P-49 — a commit is checked before it is made, and a finding already at HEAD does not refuse it | each unaccepted finding's identity, counted, at the candidate ↔ the same at HEAD, less F-19's window: a DONE task's `one-sided-link` whose requirement names a task in the in-flight table | `enforces` |
| `adds-not-evaluated` | P-49; P-50 — a check never reports clean when it did not look | each part not evaluated at the candidate, by name ↔ the parts at HEAD | `enforces` |
| `untracked-unnamed` | P-49; `FORMATS.md` §"What each check reads" (F-131) | each untracked file under `devteam/` the live checkout's checks read ↔ the paths the commit names | `enforces` |
| `hook-refused` | P-49 — the commit is made as `git commit` makes it | the project's `pre-commit`, `prepare-commit-msg` and `commit-msg` hooks, run on the candidate ↔ exit 0 | `enforces` |
| `head-moved` | P-49 — the commit made is the commit checked | the branch HEAD named, and its commit, when the gate began ↔ the same at the compare-and-swap | `enforces` |

## `commit_guard.py` — 5 refusal families

`commit_guard.py` is the `PreToolUse` hook that makes the gate the way an agent
commits into a devteam project (roadmap 0.3.1, L-1.7; P-49). It reads a Bash
command as a shell reads it, finds every git command the text runs, and
refuses two things in a repository whose top level holds `devteam/`, which is
`gate.locate`'s own test:

- a git command that writes a commit — `commit`, `merge`, `cherry-pick`,
  `revert`, `am`, `rebase`, `pull`, `commit-tree`, `filter-branch`,
  `filter-repo`, `fast-import` — except its forms that write none;
- a command that points a branch at a commit that no local branch reaches and
  that the branch's own reflog does not record. So P-12b's recovery,
  `git reset --soft` to a commit from `git reflog`, is never refused.

The owner settled both on 2026-09-24. The hook exempts a worker inside a
sandbox, read from `DEVTEAM_SANDBOX` in the hook's own environment, because
promotion gates its commits (P-44). It never runs in the client's terminal. It
refuses as `guard.py` does, with a deny decision at exit 0. Unlike `guard.py`'s
families, each of these has a name in the code, and the reason begins
`Refused [<family>]:`, so its control asserts which rule fired.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `writes-commit` | P-49 — a commit is checked before it is made | each git command the text runs, with its options ↔ the commands that write a commit, less their forms that write none; and the repository git resolves for it ↔ a top level holding `devteam/` | `enforces` |
| `lands-unheld-commit` | P-49; P-12b's recovery is left open | the commit a branch is pointed at ↔ the commits a local branch reaches, and the moved branch's own reflog | `enforces` |
| `unresolved-target` | P-49 | the branch and the commit a ref move names ↔ what the command text resolves them to | `enforces` |
| `unresolved-repository` | P-49 | the directory a commit-writing or branch-moving command runs in ↔ what the command text resolves, where the call's directory or the session's project is a devteam project | `enforces` |
| `guard-failed` | P-49 — like the gate, its guard fails closed on its own failure | the hook's reading of the command ↔ a reading that finished, where the call's directory or the session's project is a devteam project | `enforces` |

## `sandbox.py promote` — 14 classes

Declared as a closed set in `FORMATS.md` §"Status vocabularies". Emitted by
`promote` and by its `--dry-run`.

| Class | Rule | The two sides | Verdict |
|---|---|---|---|
| `promote-no-commits` | P-43 — a worker's writes reach the host only through promotion | the sandbox's commit range ↔ non-empty | `enforces` |
| `promote-no-scope` | P-12 | the task's `Scope.` ↔ non-empty, before any promotion | `enforces` |
| `promote-out-of-scope` | P-10, P-44 — promotion is gated by the declared scope | paths in the promoted commits ↔ the task's `Scope.` | `enforces` |
| `promote-uncommitted` | P-44 | the sandbox tree's `git status --porcelain` ↔ empty | `enforces` |
| `promote-history-rewrite` | P-12b — history is shared, and no scope covers it | the sandbox's base ↔ an ancestor of its tip | `enforces` |
| `promote-base-disagreement` | P-12b | the base recorded at `open` ↔ the base on disk at `promote` | `enforces` |
| `promote-foreign-subject` | P-16, P-17 — a report has one shape and passes upward verbatim | each commit's subject ↔ the task/step it claims | `enforces` |
| `promote-conflict` | P-44 — promotion is serialised | the cherry-pick's result ↔ clean application | `enforces` |
| `promote-host-index-dirty` | P-44 | the **host** index ↔ empty, before promotion begins | `enforces` |
| `promote-no-task-file` | P-16 | the task id promoted ↔ `tasks/` on the host | `enforces` |
| `promote-task-file-untracked` | P-42 — the record is append-only and is the durable output | the task file ↔ `git ls-files` | `enforces` |
| `promote-task-file-unparsed` | `FORMATS.md` §"Status vocabularies", task title | the task file's title line ↔ the grammar | `enforces` |
| `promote-extraction-failed` | P-43 | the bundle extracted ↔ a usable commit range | `enforces` |
| `promote-fetch-failed` | P-43 | `git fetch` from the sandbox ↔ success | `enforces` |

## `guard.py` — eight refusal families, **none of which has a name in the code**

`judge()` returns a formatted prose string or `None`. There is no category
constant, no enum, and `category=` takes exactly one value at every call site:

```
$ grep -o 'category="[a-z-]*"' guard.py | sort -u    ->  category="write"
```

So the guard — the most safety-critical component in the plugin — **cannot have
its refusals counted, cited, or asserted by name.** Its controls match
substrings of the message text, which is how 0.2.5's rotation refusal could
regress to the generic message with the suite green. The families are named
here so they can be referred to at all; the names below exist in **this file
only**.

| Family (named here) | Rule | The two sides |
|---|---|---|
| `protected-path-target-side` | P-10, and the charter's `Protected paths` row | the write target ↔ the charter of the project **containing the target** |
| `protected-path-session-side` | P-10 | the write target ↔ the charter of the project **containing the session** |
| `devteam-not-writer` | P-13 — `devteam/` has one writer | the writing session id ↔ `BOARD.md`'s `**Writer.**` line |
| `devteam-replaced-manager` | P-13, P-14b | the writing session id ↔ `.run/session/handoff-ready` |
| `history-rewrite` | P-12b | the git operation ↔ the set that rewrites shared history |
| `publish-outward` | P-26 — every escalation is classified; publishing is irreversible | the command ↔ the outward-facing set |
| `sandbox-early-half` | P-43 | the write target ↔ the sandbox's overlay boundary |
| `no-claim-guidance` | P-14 | the session ↔ the set of live claims |

**Naming these in `guard.py` is deliberately not done in this subcycle.** It
changes the return contract of the file with the widest blast radius in the
plugin — the hook that runs on every tool call, whose failure to import breaks
everything — and both 0.2.4 and 0.2.5 recorded their sharpest defects on this
file's refusal path. The entry condition for doing it is stated in
`meta/roadmap/done/0.2.6.md` §Findings.

---

## Withdrawals and rules written

§3.1 requires that a sweep either write the rule or withdraw the class, and
warns that a sweep withdrawing nothing has not been adversarial. Six classes
failed the test. Two are withdrawn; four have rules written.

### Withdrawn: `unreadable` and `not-utf8` (`check_refs`)

Both report **"the check could not read a file"** as an exit-1 finding. The
script already distinguishes that case with exit 2, and `FORMATS.md`
§"What each check reads" states the three-way contract: `0` clean, `1` findings,
`2` could not run. A file the checker cannot decode is not a defect *in the
project*; it is the checker unable to answer. Reporting it as a finding makes a
clean project indistinguishable from an unreadable one at the exit code, which
is the only signal the verifier reads (P-19).

**They are not deleted silently — they become exit-2 conditions**, so the
information survives and moves to the code path that means what it says.

**Moved again in roadmap 0.3.1 (L-1.1), to exit 3 — not evaluated.** Exit 2
now means only that the tool cannot answer, whose remedy is the invocation.
A project file the check cannot decode is the project's state, whose remedy
is in the project, so it ends the run as not evaluated and names the file.
The reasoning above — that it is not a *finding* — still holds.

### Rules written

- **P-45 — a task graph is acyclic, and a probe names what it de-risks.**
  Covers `dependency-cycle` and `unjustified-task`. Neither had a rule; both
  are real. A cycle means no task in it can ever start, and a probe that
  de-risks nothing identifiable is work nobody can judge.
- **P-46 — a requirement rewritten three or more times is re-opened for shape
  review, not merely rewritten again.** Covers `re-litigated-requirement`,
  whose own docstring conceded it reports *"not a defect: a signal"*. A check
  reporting a non-defect is the precise thing L-6.1 targets. The rule makes the
  signal actionable: the count is the trigger for a review, and the review is
  the remedy.
- **P-47 — a tracked artifact contains only what a reader can see, and no
  credential.** Covers `leak` and `control-character`, which had no rule at all
  despite `leak` being the highest-severity class in the pipeline.

---

## Coverage

`unruled-finding` and `stale-row` keep this table and the code equal in both
directions. The arithmetic is asserted by the controls rather than stated here,
because a count written by hand is the thing this subcycle exists to stop.
