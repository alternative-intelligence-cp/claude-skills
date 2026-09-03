# Open questions

Every question carries a **recommendation, not a menu** (P-25), and a **class
that decides whether the loop may proceed without an answer** (P-26).

| Class | Behaviour |
|---|---|
| `IRREVERSIBLE` | **always blocks.** Spends money, deletes data, publishes outward, picks a licence, names a public package, changes a released API |
| `CHARTER` | **always blocks.** Changes what is being built, what done means, or what is out of scope |
| `REVERSIBLE` | proceeds on the recommendation when the escalation window expires, recorded as `proceeded-unreviewed` and listed at the next checkpoint (P-27) |

**An answered question is struck through with the decision that answered it,
never deleted** (P-24) — the question is part of the record of how the answer
was reached.

---

### Q-1 — <the question, in one sentence, answerable>

- **Class.** REVERSIBLE
- **Recommendation.** <what to do, and the reason — the asker has the context and
  spends it once, here, so the client can answer in seconds>
- **Evidence.** <the measurement, digest or requirement that backs it>
- **Would change if.** <what would make the recommendation wrong>
- **Raised.** <YYYY-MM-DD> by <T-n>
- **Status.** open
