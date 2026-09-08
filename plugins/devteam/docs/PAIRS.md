# Rules that meet, and whether they can both hold

A reviewer reads rules one at a time, and every rule in `PROTOCOL.md` is
individually correct — each was written because something went wrong, and each
says why. **The failures this file is for are not in any single rule.** They are
in the moments where two of them bind at once and one party has to satisfy both.

**The party who finds them is always a worker under time pressure**, because a
worker is the only role required to satisfy every rule at the same instant. A
reviewer reading the protocol top to bottom will not find one; eleven of the
twelve instances below were found by somebody trying to finish something.

## How to read a row

Every row names a **moment**, the imperatives that bind at it, and a verdict:

| Verdict | Means |
|---|---|
| `holds` | both bind and both can be satisfied. Recorded anyway, because the next reader would otherwise re-derive it |
| `conflicts` | no party can satisfy both. **A resolution and an edit are required in the same subcycle** (L-7.2) |
| `resolved` | it conflicted once; the rule that resolved it is named |
| `open` | it conflicts, and the resolution is somebody else's decision. Named, never left implicit |

**A conflicting pair is resolved in one of three ways** and never a fourth:

1. **a rule naming the meeting** — the sentence nobody wrote: *"at this moment,
   X yields to Y, because …"*;
2. **a superseding rule** (P-23), where one of the two is simply wrong in this
   case;
3. **a wrapper letting the operation through under a signature** — do it, on the
   record, having said why.

**Never by adding a third rule that restates one of the two more loudly.** The
missing sentence is the one about the *meeting*.

**And prefer the structural resolution to the stated one.** Where a conflict can
be removed by changing a mechanism so the two never meet, that beats a rule
telling a tired reader to remember which yields. Row 12 is the worked example:
the resolution was not "declare the window and do not commit during it" but
"remove the window".

---

## The method

For every imperative in `PROTOCOL.md` and every numbered step in every skill,
the *moment* it binds was written down — "when a worker commits", "when a
supervisor closes", "when the manager takes the lock", "when a verifier needs a
mutation". Grouped by moment; every moment with two or more imperatives asks
CONSOLIDATION 2's question: **what else must be true at the same moment, and can
both hold?**

**The second half of the detector is a count, not a reading** (DESIGN §20 — count
how many people found the same workaround). It is at the end of this file.

---

## The seventeen moments

Every rule in `PROTOCOL.md` binds at one or more of these. The coverage table at
the foot of this file assigns all sixty.

| # | The moment | What binds |
|---|---|---|
| M1 | a worker is about to write a file | P-10, P-10b, P-10c, P-43, P-38b, P-39, `work` §2 |
| M2 | a worker commits | P-12b, P-12c, P-16, P-42, `work` §Commit |
| M3 | a supervisor verifies a step | P-18, P-19, P-20, P-35, `supervise` §4.4–4.6, `verify` 1–6 |
| M4 | a supervisor accepts or closes a step | P-5, P-16, P-17, P-17b, P-20c, P-27b |
| M5 | the manager claims a task | P-11, P-12, P-14, P-15, P-33, P-45, `run` §4.1–4.3 |
| M6 | the manager takes the lock at startup | P-13, P-14, P-14b, `run` §1, `resume` §0 |
| M7 | a checkpoint is due | P-30, P-27, P-41, P-48, `checkpoint` GATE 4, `run` §7b |
| M8 | an escalation is raised | P-9, P-20c, P-25, P-26, P-29, P-39, `run` §8 |
| M9 | the client is asked | P-2, P-9, P-26, P-27, P-38 |
| M10 | a verifier or auditor needs a mutation | P-10b, P-31, P-35, P-35b, P-38b, `audit` item 5 |
| M11 | an audit is filed and a task closes | P-5, P-20b, P-30, P-31, P-32 |
| M12 | a document names a rule that does not exist yet | P-22, P-23, `FORMATS.md` §Namespace |
| M13 | a requirement changes | P-2, P-3, P-23, P-46, `iterate` §4 |
| M14 | an amendment is written | P-2, P-48, `template-drift`, `checkpoint` GATE 4 |
| M15 | promotion runs | P-12c, P-14b, P-16, P-43, P-44 |
| M16 | a rotation happens | P-13, P-14b, P-42, `run` §7b, `resume` §0 |
| M17 | a check is run against a directory | P-19, P-34, P-35, the three-way exit contract |

---

## The calibration set — the nine known instances

**L-7.1: a sweep that misses a known instance has a method defect, and its new
findings are not yet evidence.** All nine were re-found from the current text
before any row below them was written. Two are `resolved` and the rule that
resolved each is named; one is `resolved` for one class of actor and **live for
another**, which the original statement of it did not distinguish.

| # | Moment | The pair | Verdict, from current text |
|---|---|---|---|
| 1 | M2 | one commit per step **and** a report citing post-commit evidence | **resolved** — P-12b: *"To correct a commit, add another one."* The two-commit allowance is the sentence about the meeting. Found by an `--amend` that rewrote a concurrent task's commit |
| 2 | M10 | no `rm` **and** mutation testing in a scratch directory | **resolved** — P-38b splits the grant: filesystem-shaped commands are granted *inside* an overlay, where they can harm nothing that survives it. **Live descendant, row 12** |
| 3 | M1 | no `rm` **and** a file created in error under `devteam/` | **resolved** — `run` §9b, *"Removing something you created in error"*. A file that cannot be removed leaves `git status` non-empty forever, and a verifier requires a clean tree |
| 4 | M3 | never retry a red **and** two attempts, under one number | **resolved by splitting them** — P-20 governs re-running a *check*; P-20c governs *attempts at a step*. P-20c's own text says it "must not be cited as" P-20, because the conflation "made a real decision look impossible" |
| 5 | M2, M4 | commit your own block **and** append workers' verbatim **and** the record check reading the last block | **holds, and only just** — P-16 resolves it by ordering: a supervisor commits *its own block only*, because committing the message whole would leave a worker's block last and the check would validate the wrong one. **Verified unchanged this subcycle**; `check_report`'s diff since 0.2.6 is docstring-only |
| 6 | M3 | the heartbeat in the task file **and** a verifier requiring a clean tree | **resolved** — `supervise` §4.2 carries the sentence: a heartbeat written into a *tracked* file dirties the tree, so it goes to `.run/locks/`, which is ignored |
| 7 | M2 | stage explicit paths **and** a shared index another agent stages into | **RESOLVED FOR WORKERS, LIVE FOR HOST-SIDE ACTORS.** `work` §Commit says *"Commit a pathspec. Staging explicitly is not enough, and `-A` is worse"* and P-43 gives each worker its own index. **No such mechanism holds the manager or a supervisor**, and P-12c says so in as many words. **Fired during this subcycle — row 12** |
| 8 | M10 | `Write`/`Edit` required **and** roles that have neither tool | **resolved** — P-10b's last paragraphs: the rule governs writes *the guard would judge*, and a verifier's mutation work happens outside the repository where no judgement was available either way. Resolved two hours after the rule was written, by the role that could not follow it |
| 9 | M8, M10 | a closing checklist requiring a command **and** the grant withholding it | **resolved** — P-38b, from four measured instances. Most sharply the one where a verifier had no sanctioned place to build the mutation its own job is defined by, concluded mutation was unavailable, and downgraded an independent re-measurement to an independent reading |

**What re-finding them measured.** Six of the nine were resolved by *a rule
naming the meeting*, one by *splitting a rule in two*, one by *widening a grant*,
and one — #5 — by **ordering**, which is the cheapest resolution in this file and
the only one that required no new text at all. None was resolved by deleting one
of the two rules. That is worth knowing before reading the new rows: **the
expected outcome of a conflict is a sentence, not a deletion.**

**And #7 is the reason a calibration set is worth re-finding rather than
trusting.** It is written in the plan as a single settled instance. Measured
against current text it is **two instances with one resolution**, and the half
with no resolution is the half that fired during this subcycle.

---

## New rows

### The moments where two or more imperatives bind, and both hold

Recorded because the next reader would otherwise re-derive them.

| # | Moment | The pair | Verdict |
|---|---|---|---|
| 10 | M5 | the board is the lock and always writable (P-11) **and** `devteam/` has one writer (P-13) | `holds` — P-11 carves the board out explicitly: *"a lock nobody can take is a deadlock."* The carve-out is the resolution and it is stated |
| 11 | M8 | an escalation carries a recommendation, not a menu (P-25) **and** questions are batched (P-29) | `holds` — they bind at different instants. P-25 governs composing one question; P-29 governs when the batch is sent |
| 13 | M3, M4 | a red stops the task (P-20) **and** a stop stops its own task and nothing else (P-28) | `holds` — P-28 is the scope of P-20's stop, not a competitor. Recorded because a reader meeting P-20 first will ask |
| 14 | M15 | promotion is gated by the declared scope (P-44) **and** a worker's write form is free inside (P-10c) | `holds`, and this is the *designed* pair: P-10c can free the write form precisely because P-44 judges the result rather than the command |
| 15 | M6 | every claim is stale after a restart (P-14) **and** a live pid under a claim is not stale (P-14b) | `holds` — P-14b resolves it with a mechanism rather than a precedence: `--die-with-parent` has already killed every worker, so after a restart every line reads `exited` or names a dead pid. The two cannot disagree |
| 16 | M9 | only the manager speaks to the client (P-9) **and** the client may be nobody at all | `holds` — P-9's own second half. Where the channel is `none`, reversible questions proceed and irreversible ones stop the task, *"which is the honest behaviour when there is nobody to ask"* |

### The conflicting pairs

---

#### 12 · `conflicts` → **resolved structurally** · M2, M10

**A mutation harness must make the shipped tree wrong, and the index is shared
and no scope covers it.**

The two sides:

- **P-35 and P-35b** require every check to be shown to fail, and require an
  instrument to be given a case whose answer is already known. Doing that means
  running the control against a deliberately broken source.
- **P-12b** — *"History is shared, and no scope covers it"* — and `work`
  §Commit's *"Commit a pathspec. Staging explicitly is not enough, and `-A` is
  worse."* The index is shared by every host-side actor.

Both bind at the same instant, and the harness has to mutate the *real* file
because every control resolved its subject to one fixed path. The window between
mutation and restore is a window in which the shipped tree is knowingly wrong,
and **nothing anywhere said a concurrent writer must not commit during it.**

**Measured, in this subcycle, on this repository.** A peer session ran
`git add -A` inside the window. `check_plugin.py` shipped with the defect:

```
$ git archive 6f2f389 | tar -x && python3 scripts/test_check_plugin.py
FAIL  unknown-rule-still-fires-in-prose-below-an-exempt-fence
        expected ['unknown-rule'] exit 1
        got      clean exit 0
check_plugin control: 31 passed, 1 failed, 32 cases
```

**Both sessions reported the tree green, and both were telling the truth about
the tree they looked at.** The controls were run in the working tree, where the
`finally` had already restored the file; the `git add` had read the mutated one.
*Running a check in the working tree says nothing about the commit unless the
commit is the working tree*, and an unscoped `git add` is exactly what breaks
that identity.

**Two sessions reached the mutate-in-place design independently** — 0.2.6's and
this one — which is DESIGN §20's second-half detector firing, and is calibration
instance #2's live descendant with two named workers.

**Resolution: the window is removed, not declared** (`d62a720`). The stated
resolution — *declare the window, forbid committing during it* — was rejected
for two reasons. It is a rule a rushed session skips, and **it does not cover
the case with no peer at all**: a hook, a scheduled task or an interrupted run
has the same exposure, and an interruption leaves the mutation applied
permanently, which looks exactly like a suite that passes. So each control now
resolves its subject through `DEVTEAM_SUBJECT_<NAME>` before its shipped path —
one line each, four controls — and `scripts/mutate.py` writes the mutated source
to a temporary file and names it there. There is no window to protect, no marker
to remember, and nothing an interruption can leave behind.

**What is NOT resolved, and it is named rather than left implicit:** the
host-side unscoped commit itself. `README.md` §7 excluded the narrow
unscoped-commit refusal with its trigger written out — *"an unscoped host-side
commit that actually carries another party's staged work"* — and **that trigger
has now fired, with a measured instance.** Building the refusal is not a sweep
and is not 0.2.7's; the trigger is recorded here so it is not missed twice.

---

#### 17 · `conflicts` → **resolved** · M12

**A document may not disguise an identifier to get past a check, and the check
read every mention as a citation.**

The two sides:

- **`FORMATS.md`** — *"both times the instinct was to obfuscate the identifier to
  get past the check. **Do not.**"* — and, in the same section, *"Proposing
  something by number is not the same as citing it."*
- **`check_plugin`'s `unknown-rule`**, which matched every `P-<n>` in the raw
  body of every markdown file in the plugin, with none of the three exemptions
  `check_refs` carries.

They meet whenever a plugin document reports a finding *about* a rule number —
which is what a record, a findings section and this file all do for a living.

**Measured, twice in twenty minutes, against the author of the subcycle whose
entire purpose was making rules and checks agree.** The first refusal was
correct: a paragraph proposed a rule by number, and `FORMATS.md` forbids that.
**The second refused the correction** — the rewrite described the mistake, which
means quoting the identifier, and the check reported it again. **Reporting the
finding created the finding.** The only remaining move was to write "the next
free protocol number" instead of the number, which is precisely the obfuscation
the first rule forbids.

**A rule that forbids the workaround while another rule makes the workaround the
only option is the shape**, and it is stronger evidence than the false positives
alone. A check with noisy false positives can be argued about; a check that
leaves an honest author no compliant sentence cannot.

**Resolution: `check_refs`'s three exemptions, unchanged** (`c4d3f26`) — fenced
blocks, inline quoted check output, and the teaching form. The shape is
identical and a second answer to one question would be a second home (P-34).
`check_refs` had already learned all three, at length, with the reasoning in its
source; `unknown-rule` had learned none, and it is the check guarding the files
most likely to discuss a rule that does not exist yet.

**The fence exemption resolves it in the direction the house style already
prefers.** The compliant sentence is not a rephrasing — it is *paste the output
that refused you*, which is what every findings section in this repository
already does. The refusal message now says so.

**What watches the carve-out: nothing, and that is recorded rather than left to
be discovered.** `FORMATS.md` requires it — *"a thing exempted from a checker for
its own protection is a thing the checker cannot see; name what watches it
instead, or record that nothing does."* A rule number inside a fence, inside
quoted check output, or in the teaching form is now read by no check in this
repository in either direction. The live cost is a rule cited from a *command* in
a skill's fenced block. Accepted on evidence rather than hope: `check_refs` has
carried exactly this debt over the whole project namespace for a full cycle
without it costing a finding. It is the same debt, not a new class of one.

---

#### 18 · `conflicts` → **open, and it is the client's** · M13

**A requirement is superseded and not edited, and a check counts how many times
one was edited.**

The two sides:

- **`iterate` §4** — *"a requirement that changes is superseded by a new one; it
  is not edited."*
- **P-46** — a requirement whose `Statement.` or `Acceptance.` changed three or
  more times is re-opened for shape review, enforced by
  `re-litigated-requirement`.

If the first holds, the count can never reach three and the second is dead. If
the count ever reaches three, the first is being disregarded and the count is
measuring **how often the pipeline's own procedure is ignored** — which is a
finding about the procedure, not about the requirement.

**Both readings are useful and they are not the same check**, which is why this
is `open` rather than resolved here. Under the first, P-46 is a tripwire on a
rule nothing else watches. Under the second, it is what its text says it is. The
rule's own wording — *"re-opened for shape review, not merely rewritten again"* —
assumes rewriting happens, which reads as the second.

**Not resolved in this subcycle, deliberately.** Deciding it changes what a
check *means* on every existing project, and the deciding evidence is a count
nobody has taken: whether any requirement in any real project has ever been
edited rather than superseded. The fixture cannot answer it — its requirements
carry no revision history in the tree.

**As of 2026-09-07 there is a run that can.** 0.2.9 was revised to build a new
project through **two** cycles with the owner as its actual client, so cycle 2's
requirements are amended by someone with standing to amend them, against a
first cycle whose history is in the tree. **The row closes either way**: a
requirement edited rather than superseded says P-46 measures what its text says;
none edited across a real second cycle says P-46 is a tripwire on a rule nothing
else watches. 0.2.9 §3.3 records the count as a named measurement so that
neither answer depends on anyone remembering to look.

**Named as the row it is**, because the alternative is a check whose two possible
meanings are both plausible and neither written down, which is how a finding gets
tuned away by the first person it inconveniences (L-6.1).

---

#### 19 · `conflicts` → **open** · M14

**Shipping a template row obliges every existing project to obtain a client
signature.**

The two sides:

- **`template-drift`** fires when a charter lacks a constraint row the *current
  template* declares, on the reasoning that *"a charter signed before the
  template gained a row never acquires it, and nothing else would ever say so."*
- **P-2** — changing what is being built is a charter amendment and the client
  signs it — **and P-48**, which requires an amendment to enumerate every
  done-means condition and every constraint row with a verdict.

Fixing a `template-drift` finding means editing the charter's constraints table.
That is charter text. Under P-2 that is an amendment; under P-48 that amendment
must enumerate everything. **So a plugin-side edit — adding one row to a
template — propagates into a client-signed amendment on every existing
project.**

Half of it is already closed and was checked at 0.2.6: the implementation reads
constraint rows from the *project's own* charter rather than the template, so the
new row is not itself demanded in the enumeration. **The propagation through P-2
is untested**, and it is the half that reaches a human.

**Open, and it is genuinely a question about cost rather than correctness.** The
cheap resolutions are all available and each gives something up: a template row
could be marked as acquired-without-amendment; `template-drift` could be advisory
the way `budget-mismatch` is; or an amendment could be permitted to cite the
template version rather than enumerate. Choosing between them needs one measured
number nobody has — **how often a template gains a constraint row** — and the
answer is a release cadence rather than a reading.

---

#### 20 · `conflicts` → **deferred, with a trigger that is now watched** · M17

**The plugin imposes one-writer-per-scope on its clients and runs none of the
project checks on itself.**

The two sides:

- **P-12** — one writer per scope, and scopes never overlap — with
  `check_scope`'s `misattributed-write`: *a commit's touched paths inside the
  live scope of a task that did not author it*.
- **The repository that builds the plugin has no scopes at all**, because it is
  not a devteam project:

```
$ ls -d devteam                         ->  No such file or directory
$ python3 scripts/check_scope.py .      ->  check_scope: not a devteam project, or not a git repository
```

So the check that would have caught row 12's commit **could never have fired**,
and the row was written into `docs/CHECKS.md` four commits before the violation
it describes.

**This is not an oversight, and the row must not read as one.** Asked directly,
Randy gave the reason and it is chronological: the directory does not exist
because *the pipeline did not exist yet*. One experiment was run — the fixture
still in `.internal/scratch` — and *"it was nowhere near ready for prime time so
applying it too hastily to itself seemed a bit risky."* **Self-application was
held back on a stated judgement**, which is a decision with a reason, not a gap.

**The finding is therefore not "the plugin does not police itself". It is that
the carve-out was conditional on a readiness, and nothing re-checks the
condition.** That shape has now occurred three times in this project: the `F`
namespace, the audit namespace, and §7's unscoped-commit refusal — **a thing
deferred with a trigger, where nothing watches the trigger.** Two of the three
were found only when the deferred thing failed.

**Whether the pipeline is now ready to run on itself was Randy's decision, and
he has now made it. `open` → `deferred, with a trigger that is watched`.**

**Not yet, and the sequence is the answer:** finish the roadmap that exists,
**run the experiment on the scratch fixture**, and if it pans out, apply the
pipeline to itself in the following cycle — and to any other skills developed
alongside it from then on.

**The experiment is 0.2.9, and the trigger is a judgement made after it rather
than a condition met by it.** Asked whether 0.2.9 — *"cycle 2 on the fixture,
with the mechanisms that have never fired"* — is the experiment he meant, the
owner said he may not have remembered it was already planned, and put the
trigger this way: **if 0.2.9 seems like a good enough experiment to verify the
pipeline is ready to apply to real things, then decide what to do after that.**
Setting it up may warrant a cycle of its own, before or after 0.2.10.

**So the gate is not "0.2.9 completes" and must not be recorded as if it were.**
It is *0.2.9 completes, and is then judged sufficient.* A run that finishes
while leaving the mechanisms it was meant to exercise unproven does not meet
it — which is the same distinction 0.2.5 drew about its own instrument being
written and not run.

**The reason, in his terms, and it is the sharper half.** The pipeline is still
working out kinks, and *the plans themselves keep containing things that do not
work out the way they were expected to when the plan was written.* This
subcycle is evidence for that rather than against it: §3.2 predicted a long
placement column and measured three, §3.1's calibration instance #7 was one
settled pair and measured as two, and §3.1's own resolution had to be found
structurally because the stated one did not cover the case with no peer. **A
process whose plans are still surprising it is not a process to run on the
thing that is producing the surprises**, and self-application while that is
true costs more than it saves.

**So the condition is now written down, which is the whole point of this row.**
The shape it belongs to — *a thing deferred with a trigger, where nothing
watches the trigger* — is closed for this instance, because the trigger is
here: **the roadmap complete, and a scratch experiment that passes.** Not the
roadmap alone. A later reader who finds the roadmap finished should ask whether
the experiment has been run, not infer readiness from the roadmap.

**Do not treat this row as a defect to fix.** A row reading *"the plugin does
not police itself"* invites the next reader to close the gap, and closing it
early is precisely what was ruled out.

---

#### 21 · `conflicts` → **resolved by naming the meeting** · M17

**Two checks disagree about whether a directory is a project, and the one with
no gate answers anyway.**

`check_scope` refuses a directory that is not a devteam project. `check_trace`
has no such gate, so on this repository it reports sixteen findings against a
charter that does not exist:

```
$ python3 scripts/check_trace.py .
.: 16 finding(s)  [0 goals, 0 requirements, 0 tasks]
  template-drift  CHARTER.md  the charter has no `Budget ceiling` row, which the current template declares
  template-drift  CHARTER.md  the charter has no `Build command` row, which the current template declares
  … 14 more
```

**Every one is false, and each reads exactly like a true one.** `[0 goals, 0
requirements, 0 tasks]` is the tell, and it is on a different line from the
findings. A reader who greps the finding lines — which is what a verifier does —
sees sixteen charter defects on a project that has no charter.

This is P-35b at the level of the check suite rather than a probe: **an
instrument returning an answer for a question it was never wired to ask.** The
correct answer is the exit-2 one that `FORMATS.md` §"What each check reads"
already defines — *could not run* — and 0.2.6 used exactly that reasoning to
withdraw two `check_refs` classes.

0.2.6 noticed the halves of this and stopped short of the conclusion: it recorded
that the two checks *"enumerate differently, and that difference is real and
undocumented"*, and judged it cost nothing. It costs sixteen false findings.

**Resolution, and it is the cheapest kind: the gate `check_scope` already has,
applied to the check that lacks it.** Not a new rule — the three-way exit
contract is already written, and one of the four checks does not honour it. The
edit is in `check_trace.py` with a case each way, and the case that matters is
the false-positive twin: a real project with a real charter must still report its
real `template-drift`.

---

## The second-half detector

DESIGN §20: **count how many people found the same workaround.** A departure two
or more workers made independently is a rule pair the text-only method may have
missed, because each worker met it alone and none of them was reading the
protocol as a whole.

**Method**, run over the fixture corpus at `.internal/scratch/devteam/tasks/`
(11 task files, 267 `findings-for-protocol:` entries and 81 `notes:` entries,
read-only):

```
$ grep -lEi "<pattern>" T-*.md | wc -l          # task files, i.e. independent workers
```

Counting **task files** rather than matches is deliberate: several agents work
one task and read each other's reports, so a repeated departure inside one file
is not independent. Across files it is.

| Workers | The departure | Where |
|---|---|---|
| **4** | an ambient harness instruction to prefer `sed`/heredocs over `Write`/`Edit`, against P-10b | T-3, T-6, T-7, T-10 |
| **6** | a probe or mutation run outside the repository, in a scratch copy | T-1, T-3, T-6, T-7, T-9, T-10 |
| **4** | a role told to use `Write`/`Edit` that has neither tool | T-1, T-5, T-7, T-10 |
| **3** | the guard refusing a whole **compound** command for one of its halves | T-1, T-2, T-7 |
| **3** | build artifacts dirtying a tree a verifier requires clean | T-1, T-8, T-9 |
| 1 | `rm` withheld where removal was the remedy | T-1 |

**Five departures were made independently by three or more workers. Every one
of them is already a row above** — #8, #2/#12, #8, and #3/#6 respectively — which
is the result the detector is supposed to give when the text-only method has
worked. **It found no sixth pair the reading missed.**

**The one that is not a pair and is the most interesting number here.** The
compound-command refusal (3 workers) is not two rules meeting; it is one
mechanism being coarser than its rule. The guard judges a compound command as a
unit, so `mkdir x && echo y > z/out` is refused entirely for the half that
resolves out of scope. No rule says that; the implementation does. **A departure
several workers make independently is not always a rule pair — sometimes it is a
mechanism nobody wrote down**, and the detector cannot tell those apart. Stated
here so the count is not over-read.

**A caution on the second row.** Six workers running probes outside the
repository is P-38b working as designed, not a workaround — the grant was
widened *because* of it. It is listed because the detector found it and
suppressing a hit because it has a known cause is how a detector stops being
one.

---

## Coverage

All **60** bolded rule identifiers in `PROTOCOL.md` are assigned to at least one
moment. The plan's command reports 61:

```
$ grep -cE '^\*\*P-' plugins/devteam/PROTOCOL.md          -> 61
$ grep -oE '^\*\*P-[0-9]+[a-z]*' … | sort -u | wc -l      -> 60
```

**The 61st is not a rule.** `PROTOCOL.md:165` begins *"**P-10b's text stands
unedited and still governs the host** — …"*, an ordinary prose sentence that the
line-anchored pattern matches because it starts with a bolded reference.
Recording it as a second declaration would put a duplicate into this file that
does not exist. `check_plugin` counts **48**, which is base numbers with lettered
sub-rules collapsed into their parents; that is the right denominator for a
citation check and the wrong one here, because P-10b, P-12c and P-20c bind at
their own moments and P-20/P-20c **is** calibration instance #4.

| Moment | Rules assigned |
|---|---|
| M1 | P-10, P-10b, P-10c, P-38b, P-39, P-43 |
| M2 | P-12b, P-12c, P-16, P-42 |
| M3 | P-18, P-19, P-20, P-35 |
| M4 | P-5, P-16, P-17, P-17b, P-17c, P-20c, P-27b |
| M5 | P-11, P-12, P-14, P-15, P-33, P-45 |
| M6 | P-13, P-14, P-14b |
| M7 | P-27, P-30, P-41, P-48 |
| M8 | P-9, P-20c, P-25, P-26, P-28, P-29, P-39 |
| M9 | P-2, P-9, P-26, P-27, P-38 |
| M10 | P-10b, P-31, P-35, P-35b, P-38b |
| M11 | P-5, P-20b, P-30, P-31, P-32 |
| M12 | P-21, P-22, P-23, P-24 |
| M13 | P-2, P-3, P-23, P-46 |
| M14 | P-1, P-2, P-48 |
| M15 | P-12c, P-14b, P-16, P-43, P-44 |
| M16 | P-13, P-14b, P-42 |
| M17 | P-4, P-19, P-34, P-35, P-47 |
| **no moment — they bind always, not at an instant** | P-6, P-7, P-8, P-36, P-37, P-40 |

**Six rules bind at no single moment and that is a finding rather than a gap in
the sweep.** P-6, P-7 and P-8 are role definitions; P-36, P-37 and P-40 are
standing properties of research and model choice. **A rule that binds at no
moment cannot conflict with another rule at one** — which is a useful thing to
know about this method's reach, and the honest statement of what a pairs sweep
cannot see. The failures those six have produced are of a different kind, and
`docs/CEREMONY.md` is where they are read.

**Rows: 21. Moments with two or more imperatives: 17, all recorded. Conflicting
pairs: 6 — three resolved with edits in this subcycle, **one deferred with a
trigger that is now written down** (row 20), and two open, each needing a
measurement nobody has taken.**
