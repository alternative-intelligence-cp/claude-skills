# Handoff — devteam 0.2.0 is released, and the run that tests it has not happened

Written 2026-09-07 by the session that closed cycle 0.2, for whoever picks this
up. The return date is unknown and may be a week, so this assumes you have
**none** of the conversation and cannot ask its author anything.

Read this file, then [`plugins/devteam/docs/CONSOLIDATION.md`](plugins/devteam/docs/CONSOLIDATION.md).
Everything else is a pointer.

**Every number below was read from the tree, with the command beside it.** The
0.1 handoff established that rule after its first draft wrote "~500 control
cases" where the command said 328; writing the command down is what makes the
claim checkable.

```
ls plugins/devteam/skills | wc -l                     ->  15 skills
ls plugins/devteam/agents | wc -l                     ->   9 agents
grep -c '^\*\*P-[0-9]* ' plugins/devteam/PROTOCOL.md  ->  48 numbered rules
ls plugins/devteam/scripts/*.py | grep -vc '/test_'   ->  16 scripts
python3 plugins/devteam/scripts/run_controls.py       ->  all 14 controls green,
                                                          575 cases, 262 of them
                                                          false-positive (45%)
python3 plugins/devteam/scripts/check_plugin.py       ->  clean
python3 plugins/devteam/scripts/check_refs.py         ->  clean
git rev-list --count 243059e..HEAD                    ->  74 commits this cycle
```

---

## 1. What 0.2 changed, in one paragraph

**A worker's writes are now impossible rather than refused.** On Linux each
worker runs headless inside a private copy-on-write overlay of the repository,
mounted at the repository's own absolute path so every path-shaped rule reads
the same inside and out. Its writes — files, index, refs, rewritten history —
exist nowhere but its own upper layer until a supervisor promotes them, and
promotion diffs the paths its commits touched against the task's declared scope.
The guard stays in front of that as **early warning**, because a refusal at the
moment of typing is where guidance works; it is no longer the thing standing
between a mistake and the repository.

The manager also rotates now, at every checkpoint, driven from outside the
session — a manager cannot measure its own context, so the trigger cannot be a
feeling. Every finding class the plugin emits names the rule whose two sides it
compares. And the rule set has been read looking for pairs that cannot both hold,
which nobody had ever done.

## 2. Where things are

| Path | What |
|---|---|
| `plugins/devteam/` | **the product.** 15 skills, 9 agents, 16 scripts, 575 control cases |
| `plugins/devteam/docs/CONSOLIDATION.md` | **the work queue.** The first run's nine items each answered; six new ones from 0.2 |
| `plugins/devteam/docs/CHECKS.md` | every finding class against the rule it enforces. The best single map of the plugin |
| `plugins/devteam/docs/PAIRS.md` | 17 moments where two imperatives bind at once, 21 pairs. **Read row 12 and row 20 whatever else you skip** |
| `plugins/devteam/docs/CEREMONY.md` | all 87 numbered steps against *does this only work for an operator who already understands why it matters* |
| `plugins/devteam/DESIGN.md` | why the pipeline is shaped as it is, and every lesson each run produced |
| `plugins/devteam/PROTOCOL.md` | the 48 numbered rules. Every one carries the measured failure that produced it |
| `plugins/devteam/meta/roadmap/done/` | **what happened** — cycle 0.2's eight closed subcycles, each with its findings and measured cost |
| `plugins/devteam/meta/roadmap/0.2/` | **what remains** — 0.2.9 and 0.2.10 |
| `.internal/scratch/` | **the retired fixture.** A CSV-to-JSON tool built by the pipeline as a test of it. Gitignored here; private remote. **No longer 0.2.9's target — see §4** |
| `~/Workspace/REPOS/pricelog` | **0.2.9's target.** A coin-price logger, the owner's own idea, built from nothing by the pipeline with him as the client. Outside this repository; the owner granted write permission for that one directory |

## 3. State: released, and untested by a real project

**`plugin.json` and the marketplace manifest say `0.2.0`.** The commit that
closes this subcycle carries the tag `v0.2.0`. **It is not pushed** — publishing
is the owner's (P-26), and the pipeline's own rule about irreversible
outward-facing actions applies to its own release.

**What is proved:** every mechanism ships with negative controls, and 0.2.8
walked one full `setup` → interview → plan → dispatch → promote → verify →
close on a throwaway project the pipeline had not written. That walk found two
defects no control could have caught, which is what it was for — see
CONSOLIDATION N-3, and the `model-mismatch` fix in `sandbox.py`.

**What is not proved, and it is the important half: no real project has run
under any of this.** Rotation has never rotated a project. The v3 estimate
model's bias is unmeasured. `amendment-omits-condition` has never met a real
charter. The unreviewed-decision path (P-27) has still never fired.
`/devteam:iterate` has still never run. **A mechanism that has never fired has
not been shown to work**, and the README's known-problems table now keeps a row
until the fix is shown to work rather than merely built.

**0.2.9 is that run**, and it is the next thing to do. **It was revised whole on
2026-09-07, before any of it ran** — the target moved off the fixture and the run
became two cycles on a new project. §4 says why, and the reason is the single
most important thing on this page for anyone judging PAIRS row 20.

## 4. What is not in any file

The part a written handoff loses.

**The credential copy dies with the sandbox, and a refresh inside it is lost.**
`dispatch` copies `~/.claude/.credentials.json` into the sandbox's tmpfs `HOME`
(509 bytes, mode 600) and it dies with the tmpfs. **If a token refresh happens
inside the sandbox it is lost, and if the provider rotates the refresh token
the host's copy may be invalidated.** That is `REASONED`, not measured — it has
not happened in any run so far, including 0.2.8's two live dispatches. 0.2.9
§3.4 makes it a stop rule: if a worker cannot authenticate mid-run, stop and
record exactly what was observed. It is the cycle's most important `REASONED`
line still waiting to become measured.

**Git identity inside is solved a way you may try to solve again.** `open`
records the host's `user.name` and `user.email` into `plan.json` and seeds them
into the overlay's own repository config. Do **not** also set `GIT_AUTHOR_*`
environment variables: 0.2.3 planned that, then declined it as built, because it
would give F-44 a second home. Verified at `sandbox.py:469` and `:542`.

**The network namespace is shared, deliberately, and the risk is accepted.**
The threat model is filesystem writes and the model API must be reachable, so a
worker can reach the network — it could exfiltrate, or `pip install` into its
overlay. Outward git is made impossible **structurally** instead: no
`SSH_AUTH_SOCK`, no `~/.ssh`, no `~/.gitconfig`, no `gh` config, no token in the
cleared environment, so `git push` has nothing to authenticate with. **The
trigger for unsharing the network is a worker observed contacting anything but
the model API, or a charter marking the project sensitive.**

**`guard-only` is not a lesser configuration of the same thing.** macOS,
Windows, and any Linux without unprivileged user namespaces or `bwrap` degrade
to it, loudly, with the mode written into the charter the client signs. It
leaves three measured holes open and the charter says so: an interpreter heredoc
writes unjudged, a git history rewrite has no path for a path-based guard to
see, and every agent shares one index.

**`ListAgents` cannot see a headless worker.** That is why liveness is a file
the harness writes at dispatch and rewrites at exit (P-14b), and why a
supervisor polls a path rather than asking a question. It is a cost accepted in
L-2, not an oversight.

**The client on the first run was played by an AI session**, unusually
available — eighteen blocking stops in fifteen hours, answered in minutes. A
human client would have been the bottleneck. That is a limit on what the run
proves. **Three client decisions run on one thread** — a memory-bound fix, a
docstring repair and a delimiter feature, all declined on the ground that the
fixture has no users. A successor reversing any should reverse the reasoning
explicitly rather than quietly. The owner was asked on 2026-09-07 and left all
three declined.

**AND THE DEEPER FINDING, WHICH COST 0.2.9 ITS ORIGINAL TARGET: the fixture has
no users because it has no PRINCIPAL.** 0.2.9 originally ran cycle 2 on it.
Asked for the positions the plan required him to write down before the
interview, the owner could not supply them, and the reason was structural
rather than forgetfulness — he did not choose the project, did not plan its
decisions, and does not know what was in or out of scope. His words: *"the test
project was just something that implementing agent for that test came up with
on their own and something i don't really have any experience with."* He then
used the tool at my request and found nothing wrong with it, correctly.

**So all three of `iterate` §3's interview areas were unanswerable, not merely
the first.** A session briefed to stand in for him would have produced a number
for every measurement in §3.3 while answering *"can the pipeline execute its
procedure against a synthetic principal?"* — which is not the question the run
exists to ask. **This is the four-subcycle failure shape at the scale of a
whole experiment**, and it was caught by asking the client for something the
record could not fake rather than by reading the plan.

**A pipeline validated only on a fixture it invented cannot exercise the parts
of itself that require a client.** That is the general form, and it is worth
more than the subcycle it cost.

**This repository is not itself a devteam project, and that is a decision.** It
has no `devteam/` directory, so none of the project checks run on the thing that
builds them. The reason is chronological — the pipeline did not exist when the
repository started — and the condition for revisiting is **0.2.9 completing
*and* being judged a good enough experiment**, not 0.2.9 completing.
[`PAIRS.md`](plugins/devteam/docs/PAIRS.md) row 20 carries the whole reasoning
and warns you off closing it early.

**The fixture's record has a remote and it must stay private.**
`alternative-intelligence-cp/devteam-run-01-csv2json` — it is a complete client
engagement record and this repository is public. Read from the tree:
238 commits, `git -C .internal/scratch status --porcelain` empty, and
`git -C .internal/scratch log origin/master..HEAD` empty, so nothing is unpushed
today. **Push it after any change to that tree.**

**The branch is `master`, not `main`, and this line said `main` when it was
first written.** `_s9` caught it on the run that follows. The conclusion was
right and the command beside it was not: `origin/main..HEAD` exits **128** with
*"unknown revision"*, so a successor following the protocol literally either
stalls on a fatal — or, having piped it into `| wc -l`, reads `0` and concludes
the tree is current. That is CONSOLIDATION N-6 for the third time in two days:
**a check whose failure is invisible from the shape of the invocation.** Run it
bare and read the exit code.

## 5. Where to start

1. **Read [`meta/roadmap/0.2/0.2.9.md`](plugins/devteam/meta/roadmap/0.2/0.2.9.md) whole before doing anything.** It is the run's protocol: what it exercises, what it measures, where its ceiling is, and — the part most likely to be skipped — **when to stop**. Five stop rules, written in advance so that stopping is a decision already made rather than a judgement under sunk cost. Its revision block at the top is not preamble; it is the subcycle's first finding.
2. **The owner's decisions in 0.2.9 §2 are ANSWERED** — as of 2026-09-07, L-9.6 through L-9.11, including the ceiling in dollars rather than in the estimate model's units. Do not re-ask them; read them. What is *not* settled is anything the onboarding interview will raise, and pre-empting that is explicitly forbidden by §6.
3. **0.2.10 is small, independent, and can go before or after.** It needs nothing from 0.2.9.
4. **Read `CONSOLIDATION.md`.** Item 8b's trigger has fired with a measured instance, and its recommended home is 0.2.10 — the reasoning for why not 0.2.8 is written out, so you do not have to re-derive it.

**And one habit that produced most of what is in `DESIGN.md`:** before building
a check, run it against the live corpus and read what it reports. Four checks
were rejected that way in one day — each looked obviously right and each would
have shipped green while measuring nothing.

**And its 0.2 successor, which cost this cycle four subcycles to learn:** every
subcycle so far has produced at least one instrument that passes while answering
a question *adjacent* to the one asked, and **not one was caught by reading the
output.** They were caught when a prediction and a measurement disagreed, or
when applying an edit put the old text on screen beside the new. So read your
plan against the documents it cites rather than against itself, and when an
instrument agrees with you, that is the moment to check it hardest.
