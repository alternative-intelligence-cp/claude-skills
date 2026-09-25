# The record

The manager's execution record (P-42): what was dispatched, what came back,
what it cost, which estimates were wrong and by how much, which dependencies
actually bound, and every question answered. **Append-only; never rewritten.**
[`BOARD.md`](BOARD.md) is the present; this is the past.

The durable output of running the pipeline is the cross-task picture no single
task can see — which findings recurred, which parts cost triple their estimate,
where the plan was wrong. That picture exists only if this file is kept.

**Entry vocabulary:**

`dispatch <label>` · `report <label> <status> <tokens> <minutes>` ·
`verify <label> PASS|FAIL` · `advance T-n` · `release T-n` ·
`pin <id>` · `stale claim T-n: <found>, <done>` ·
`question Q-n answered: <answer>` · `question Q-n proceeded unreviewed: <what>` ·
`checkpoint C-n <verdict>` · `rebalance: <what moved and why>` ·
`audit T-n <dimension> filed` · `finding: <one line, and where it went>` ·
`writer takeover: <old id>` · `charter amended: v<n>, <what>`

**A verdict is counted, so write it exactly.** The checkpoint's tally, the
plugin's `scripts/tally.py`, reads each top-level item whose backticks hold
`verify <label> PASS` or `verify <label> FAIL` and nothing else. The label is
the claim's, `T<n>-<slug>-<HHMM>`, a task's `T-n`, or a step's `T-n.S-m`, and
whatever else there is to say goes after the backticks, after a dash. An item
whose entry is `verify` and that the tally cannot read is named at every
checkpoint from then on, because this file is never rewritten (roadmap 0.3.2,
L-2.12).

**Adopting this on a project that already has findings** turns a green tree
into one `cited-undefined` per finding, all at once, because they were cited by
id long before anything required declaring them. That is a migration cost
rather than a defect: declare the backlog in one dated block, oldest first,
saying it is a backfill. It is tedious exactly once.

**A finding is declared here, and only here**, as `- **F-n** — <one line>`
before it is cited anywhere else. Findings are usually the largest numbered
set a project accumulates and the one most often cited from a charter or a
decision, so a finding that lives only in a message is a dangling citation in
an authority document. `check_refs` diffs them like every other identifier.

---

## <YYYY-MM-DD>

- <first entry>
