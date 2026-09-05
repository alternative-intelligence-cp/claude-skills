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
- **Everything is line-oriented.** No field's value spans lines except an
  explicit sub-list, so a check never needs to parse markdown properly.

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

**And "safe from collision" also means "unseen", which is the half this said
nothing about.** The scanner that cannot mistake `COR-6` for a citation also
cannot check it. So a three-letter namespace has **no citation integrity at
all, in either direction**: an audit may cite `COR-99`, which exists nowhere,
and nothing reports it; an audit finding may be declared and referenced by
nobody, and nothing reports that either. The exemption that protects the
namespace is the same fact that blinds every tool to it.

That is a fair trade only if something else watches the namespace. For audit
findings that is now the `Disposition.` field, and it is the **only** thing
watching — so treat a namespace exemption as a debt rather than a solution, and
say what is covering it.

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
| requirement `Status.` | `open` · `in-progress (T-n)` · `discharged (T-n)` · `struck (D-n)`. **The task list may name several** — `in-progress (T-2, T-5)` — because a requirement is frequently advanced by one task and completed by another, and forcing one id makes the record say something untrue |
| task title | `PLANNED` · `RUNNING (since <date>, <label>)` · `READY-TO-AUDIT` · `BLOCKED (<why>)` · `DONE (<date>)` |
| task `Kind.` | `implementation` (default when absent) · `probe` · `spike` · `chore` |
| step checkbox | `[ ]` pending · `[x]` done · `[~]` struck, with a reason on the line |
| question `Status.` | `open` · `answered D-n` · `proceeded-unreviewed D-n` · `withdrawn` |
| question `Class.` | `REVERSIBLE` · `IRREVERSIBLE` · `CHARTER` |
| checkpoint verdict | `ON-COURSE` · `DRIFTED` · `BLOCKED` |
| REPORT `status:` | `DONE` · `BLOCKED` · `NEEDS-DECISION` · `RED` · `READY-TO-AUDIT` |
| board task state | `—` · `CLAIMED <label>` · `BLOCKED on T-n` · `BLOCKED on Q-n` · `DONE` |

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
| `check_trace.py` | `CHARTER.md`, `REQUIREMENTS.md`, `tasks/*.md` | goals ↔ requirements ↔ tasks ↔ acceptance criteria |
| `check_refs.py` | every tracked `.md` under `devteam/` | citations ↔ declarations; links ↔ files; leaks |
| `check_report.py` | one `tasks/T-n.md` plus `git` | the REPORT block ↔ the committed tree |
| `check_scope.py` | `BOARD.md`, `tasks/*.md` | declared scopes ↔ each other, and ↔ what was written |

All four read **git-tracked files only**, so scratch work is never a finding,
and all four exit `0` clean · `1` findings · `2` could not run.

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
