# The ledger

**Every item raised has one entry here, with a decision or the date by which
one is due** (P-52). An item is every finding an audit reports, every item a
report leaves for somebody to decide, and anything the manager raises itself —
from what the client said, or at a handoff. A report's findings for the
protocol are not items: they are the pipeline's, and they go to `RECORD.md`.
The plugin's `templates/FORMATS.md`, §"The ledger", says which lines of a
report are items.

**The manager writes this file, and nobody else** (P-13). An item's text stays
where it was raised, verbatim (P-17) — a REPORT block, an audit's answer
landed in a task file, a file in `audits/` — and its entry names where. A
supervisor or a worker relays an item upward in its report; it never writes an
entry.

**The disposition is one of five values**, and an open item names the task or
the checkpoint by which it must be decided. The vocabulary is the plugin's
`templates/FORMATS.md`, §"Status vocabularies". An entry that reads `open` with
no date is undecided with nobody due to decide it, and `check_refs` reports it,
as it reports an entry with no disposition at all. `check_trace` reports an
item whose date has passed — an open or routed item once its task's row leaves
`CLAIMED` at the close, an open item once its checkpoint is filed, a question
withdrawn — a routed item whose task's `Scope.` does not cover its `Needs.`,
and a fix that is not in HEAD's history. So decide what is due in the commit
that moves the row, or that files the checkpoint.
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py <project>` prints every
entry's disposition, and the counts by value.

---

<!-- example:begin -->
### ITM-1 — <the item, in one line>

- **Raised.** <where its text is — `T-n questions "<its opening words>"`, `T-n.S-m COR-n`, `audits/<file> SEC-n`, or `manager <YYYY-MM-DD>`>
- **Needs.**
  - <each path the item needs changed: required when it is routed>
- **Disposition.** open (until C-1)
<!-- example:end -->
