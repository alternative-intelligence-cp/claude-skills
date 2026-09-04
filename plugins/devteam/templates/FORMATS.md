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
| `P-` | a protocol rule | the plugin's `PROTOCOL.md` — **external**, cited here, never declared here |

**The rule: anything else that numbers something uses a prefix of three or
more letters.** `COR-1`, `SEC-5`, `HYG-3` for audit findings by dimension;
`REV-2` for a review finding. Never a new one- or two-letter prefix.

**Why, mechanically.** The citation scanner matches `[A-Z]{1,2}-<digits>`
anywhere in an artifact. A two-letter identifier is therefore *indistinguishable
from a citation* — there is no syntax that says "this is my own numbering, not
a reference to yours". A three-letter prefix cannot match, so it is safe
without any further agreement.

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
| requirement `Status.` | `open` · `in-progress (T-n)` · `discharged (T-n)` · `struck (D-n)` |
| task title | `PLANNED` · `RUNNING (since <date>, <label>)` · `READY-TO-AUDIT` · `BLOCKED (<why>)` · `DONE (<date>)` |
| step checkbox | `[ ]` pending · `[x]` done · `[~]` struck, with a reason on the line |
| question `Status.` | `open` · `answered D-n` · `proceeded-unreviewed D-n` · `withdrawn` |
| question `Class.` | `REVERSIBLE` · `IRREVERSIBLE` · `CHARTER` |
| checkpoint verdict | `ON-COURSE` · `DRIFTED` · `BLOCKED` |
| REPORT `status:` | `DONE` · `BLOCKED` · `NEEDS-DECISION` · `RED` · `READY-TO-AUDIT` |
| board task state | `—` · `CLAIMED <label>` · `BLOCKED on T-n` · `DONE` |

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
