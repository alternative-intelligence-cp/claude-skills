---
name: research
description: Find and record one up-to-date fact from outside a devteam project — a standard's current edition, a release number, a known defect, current guidance — as a dated, sourced digest citing a primary source. Used by the researcher agent, and inline by anyone for a single fetch.
argument-hint: "[question]"
allowed-tools: WebSearch WebFetch Read Grep Glob
---

# Research

Everything a plan rests on that is not in this repository — a standard, a data
release, a library's behaviour, a known vulnerability — lives outside it and
**moves**. Your training data has a cutoff and the world does not, so anything
you "know" about a version number is a hypothesis with a date on it.

## Before you search, look

**Somebody may already have answered this, for another project.** Digests are
filed per project, so the same question gets paid for twice by default:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/research_index.py" query <terms>
```

**A hit is a lead, not an answer.** The index holds the topic, the question,
the date, the sensitivity and the path — deliberately no findings, because an
index carrying the answer becomes a second home for a fact (P-34), goes stale
silently, and gets read in preference to the digest precisely because it is
more convenient.

| The hit is | Do |
|---|---|
| fresh, and answers the question | cite it — `per <path>, as of <date>` — and say in your digest that you reused it rather than re-derived it |
| fresh, and answers a *neighbouring* question | read it for its sources, then do your own work. A digest about TOML's current version does not answer one about YAML's |
| stale | **re-verify at the primary source.** A stale hit is worth having — it says where to look and what the answer used to be — and is worth nothing as a citation |
| absent | ordinary research, and your digest becomes the next person's hit |

**Never cite a digest you have not opened.** The index is a finding aid; the
digest is the evidence. That is the same distinction this skill draws between
a search result and a primary source, pointed at our own files.

## When it is a request rather than a fetch

**One fetch may be inline.** More than one, or anything security-relevant, is
a request to the `devteam:researcher` agent, whose context is disposable and
whose caller's is not (P-36).

## What counts as a source

- **Primary — the only kind a claim may cite:** the standards body; the
  upstream project's own repository, release notes or tracker at a named
  revision; a defect registry (`cve.org`, `nvd.nist.gov`); the reference
  implementation itself.
- **Secondary — usable only with a primary named beside it:** a peer-reviewed
  paper, a vendor's own documentation.
- **Leads only, never cited:** blogs, answer sites, aggregators, and **this
  project's own documents**. A claim that cites only another document here is
  not verified — it is a rumour with an internal link.

## The request

The asker has the context and spends it once, in this shape:

```
RESEARCH REQUEST
question: <one sentence, answerable>
feeds: <the requirement, decision or checklist item the answer changes>
would-change-the-plan-if: <what answer would force a change>
sources-that-count: <specifically>
sensitivity: routine | security      (security: two independent primaries; stale after 90 days)
budget: <fetches; default 12>
```

## The procedure

Search to **locate** the primary; then open the primary, not a summary of it.
Record the exact version, the date, and the line that answers. For `security`,
find a second independent primary. **Stop at the budget** and say what is
unresolved — an honest gap is worth more than a confident guess, because the
gap gets checked and the guess does not.

## The digest

```
# <topic> — research digest

**As of <date>.** **Sensitivity.** routine | security
Question: <the question>.

## Answer
<one paragraph: the version, edition or fact, stated plainly>

## Evidence
- <URL> — retrieved <date> — "<the line that answers, quoted>"

## What would change this
<the request's would-change-the-plan-if, and whether it did>

## Confidence and gaps
<high | medium | low, and why; anything unresolved at the budget>
```

## Writing about bytes without writing the byte

**Name a control character; never embed one.** Write `U+0000`, or `\x00`, or
"the NUL byte" — not the byte itself. A document containing one is committed as
**binary**: git stops producing a diff for it, and the entire audit discipline
is diffing a document against the thing it describes. Decoding succeeds, so
nothing else notices; only git's own stat line does, and nobody reads it.

This is likeliest in exactly the digests where it hurts most — encodings,
protocols, terminal handling, anything with a byte-level answer — because the
natural way to write about a byte is to write the byte. `check_refs` reports
`control-character` for it, and it applies to commit messages too.

## Filing and citing

**The researcher never writes into the project.** Its final message is the
digest; the requester files it as `devteam/research/<topic>.md`, adds its row
to `research/CURRENCY.md`, and cites it — because the requester is the one who
knows what it was for.

A decision resting on a digest says `per research/<topic>.md, as of <date>`.

## Currency (P-37)

One row per external thing the plan names: what is pinned, when it was
checked, the source, the decision that pins it.

- unchecked for **six months** → `stale`
- a security digest older than **ninety days** → `stale`
- **a digest whose `Sensitivity.` is unstated cannot be aged at all**, and the
  index reports it as unknown rather than assuming `routine` — the convenient
  assumption is the one that hides a stale security digest
- **a task whose currency rows are stale is not ready to start**
- **anything called "current" with no date beside it is an unverified claim**

## Limits, stated

A large page is truncated — fetch the section's own URL. A long PDF is read in
ranges. A cross-host redirect is reported, not followed blindly. Results are
cached for about fifteen minutes, so an answer that "changed" inside that
window is the cache. **Nothing behind a login.**

And the honest one: **search fixes facts, not understanding.** Knowing the
current version of a spec is not knowing whether this design satisfies it.
