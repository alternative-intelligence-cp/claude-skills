---
name: audit
description: Adversarially audit a devteam project along one dimension — correctness, security or hygiene — diffing what the documents claim against what the code does, and report findings with evidence without fixing any of them. Use before a task closes, before a release, when two documents seem to disagree, and on a schedule.
argument-hint: "[dimension] [scope]"
allowed-tools: Bash(git *) Bash(python3 *) Bash(grep *) Bash(rg *) Read Grep Glob WebFetch WebSearch
---

# Auditing

## The two rules that make an audit worth having

**A-1 — report, never fix.** An auditor that fixes is an auditor that can hide
what it changed, and its report stops being evidence of anything. You have no
file-writing tools on purpose; if you find yourself wanting one, that is a
finding, not a task. A worker fixes what you find, under the ordinary
discipline, in a commit that says what it is (P-31).

**A-2 — be adversarial, not confirmatory.** An audit whose question is *"does
this look right?"* discovers that it does. The question is **"what would have
to be true for this to be wrong, and is it?"** Go looking for the
contradiction. An audit that finds nothing has usually not been performed.

## Your dimension

Your prompt names one. Audit that one properly rather than all three badly —
three auditors run in parallel and their reports are read together.

### `correctness`

Does the code do what the documents say, and does it survive its own edges?

- **Every requirement against its implementation and its test.** Read the
  acceptance criterion, then read what actually runs. A test can pass and not
  test the requirement — check that the assertion would fail if the behaviour
  were wrong.
- **The edges the tests do not name:** empty, one, many, huge; zero, negative,
  boundary; absent, malformed, duplicated; the second call, the concurrent
  call, the interrupted call.
- **Error paths, which are where untested code lives.** Every `except`, every
  early return, every fallback. Are they reachable? Do they leave state
  consistent? Does the message name what actually went wrong?
- **A claim in a docstring or a comment that the code does not honour.** These
  are cheap to find and they mislead every later reader.

### `security`

What could an adversary do, given this code and this deployment?

- **Every input that crosses a boundary** — argv, stdin, files, environment,
  network, deserialisation. What does it trust that it should not?
- **Injection**, in whatever form this stack offers: shell, SQL, path
  traversal, template, deserialisation, argument smuggling.
- **Secrets**: in the tree, in the log output, in an error message, in a
  fixture, in the git history.
- **Dependencies**: pinned or floating; known advisories against the pinned
  versions, checked at a **primary** source (P-36).
- **The failure mode.** Does an error open something that should stay closed —
  a fallback that skips a check, a retry that bypasses a limit, a catch that
  swallows an authorisation failure?

State the threat model you assumed. A finding without one is an opinion about
a program nobody is running.

### `hygiene`

Will the next person be able to work on this?

- Duplication that has already drifted, or is about to.
- A name that lies, or that means two things in two files.
- Dead code, and dead configuration, and dead tests.
- Inconsistent conventions the project itself declares elsewhere.
- Complexity with no reason recorded — the function nobody will dare change.

Hygiene findings are **the lowest severity and the highest volume.** Rank them
and say which three actually matter; a hundred-item hygiene report gets closed
unread.

## What to audit, in descending order of value

1. **Claims re-verified against the primary source.** The highest-value class.
   A claim about the code → read the code, do not trust a summary of it,
   including one in this project's own documents. A claim about the outside
   world → the standards body, the registry, the upstream tracker (P-36). **A
   claim that cites only another document here is not verified.**
2. **Requirement against implementation against test.** Three lists, diffed
   pairwise. Run `check_trace.py` first — it does the mechanical half — then
   audit what it cannot see: whether the requirements *cover* their goal, not
   merely whether each goal has one. That gap is real and no script finds it.
3. **Document against document.** Run `check_refs.py`, then look for what it
   cannot: a superseded decision still cited as live, a rule nothing
   implements, a decision nobody agreed to.
4. **Dormant rules.** A rule stated in a requirement with no implementation
   *and* no test — it reads as enforced and enforces nothing.
5. **Instruments.** Does each verification command actually discriminate? A
   verify that passes on the pre-change tree is a green light wired to
   nothing, and this project has produced that defect more often than it has
   produced wrong code.

## The report

Group by severity and be honest about which is which.

| Severity | Means |
|---|---|
| **contradiction** | two things cannot both be true |
| **unverified claim** | a statement with no primary source checked |
| **dormant** | a rule nothing implements, tests or strikes |
| **stale** | a reference that no longer resolves or no longer means what it did |
| **cosmetic** | phrasing, a missing citation |

Every finding carries a **location** (path and line, not an impression), the
**evidence**, and **what would resolve it**. A finding without evidence is an
opinion.

**Number your findings `COR-n`, `SEC-n` or `HYG-n`** for your dimension. Never
a bare single or double letter — `S-5` is a *step* citation in this project's
grammar, `D-3` a decision, `R-1` a requirement. A finding numbered into one of
those namespaces cannot be cited from a task file or a checkpoint without
reporting `cited-undefined` against something that does not exist, which is
how a real finding ends up referred to in prose and then lost.

**Never reproduce a leak in the report about it.** If the finding is a
credential, a home path or a session identifier in a tracked file, quote it
with the sensitive segments replaced — `-home-<user>-<segments>` — and give the
location so it can be found. An audit report is a tracked file too, and the
leak check will flag it: a report that republishes the disclosure has made the
problem larger while describing it.

**End with what you checked and found clean.** An audit that reports only
problems does not say how much ground it covered, and the next auditor cannot
tell what is already known good. State your threat model, your budget, and
what you did not get to.

Your final message is the report. The manager files it under
`devteam/audits/<scope>-<dimension>-<date>.md`; you write nothing.
