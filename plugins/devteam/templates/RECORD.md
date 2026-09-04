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

**A finding is declared here, and only here**, as `- **F-n** — <one line>`
before it is cited anywhere else. Findings are usually the largest numbered
set a project accumulates and the one most often cited from a charter or a
decision, so a finding that lives only in a message is a dangling citation in
an authority document. `check_refs` diffs them like every other identifier.

---

## <YYYY-MM-DD>

- <first entry>
