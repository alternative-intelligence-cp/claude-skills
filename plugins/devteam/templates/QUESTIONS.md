# Open questions

Every question carries a **recommendation, not a menu** (P-25), and a **class
that decides whether the loop may proceed without an answer** (P-26).

| Class | Behaviour |
|---|---|
| `IRREVERSIBLE` | **always blocks.** Spends money, deletes data, publishes outward, picks a licence, names a public package, changes a released API |
| `CHARTER` | **always blocks.** Changes what is being built, what done means, or what is out of scope |
| `REVERSIBLE` | waits `open` until its `Window.`, then proceeds on the recommendation, recorded as `proceeded-unreviewed D-n` and listed at the next checkpoint (P-26b, P-27) |

**An answered question is struck through with the decision that answered it,
never deleted** (P-24) — the question is part of the record of how the answer
was reached.

**This file is the one home of a question's state** (P-26b, P-34). Whether it
waits on the client, was answered, proceeded on its recommendation or was
withdrawn is its `Status.`, and when a `REVERSIBLE` one proceeds unanswered is
its `Window.`. The board keeps none of it, and `status` and `checkpoint` read
what is waiting and what proceeded from here. **A proceeded question reads
`proceeded-unreviewed D-n` until the client reviews D-n** (P-27): confirmed, it
reads `answered D-n`; reversed, it reads `answered` with the number of the new
decision that supersedes D-n (P-23). D-n itself is never edited. The plugin's
`templates/FORMATS.md` §"A question's state" says where each fact lives.

**A blocking question carries `Costs.`, and it is computed before the client is
asked.** The size of a change is a bad predictor of its price: what it costs is
the settled work it reopens, and the client cannot see that from the question.
They read a sentence; the bill is a re-verification. So say what it retires,
what verified work it returns to `in-progress`, whether any affected site is in
no task's scope, and the estimate in step-units — **beside the recommendation,
not after the answer.**

Neither refuse the change nor agree to it silently. A client told the price can
choose. A client who finds out afterwards was badly served by a pipeline that
knew and did not say.

---

<!-- example:begin -->
### Q-1 — <the question, in one sentence, answerable>

- **Class.** REVERSIBLE
- **Recommendation.** <what to do, and the reason — the asker has the context and
  spends it once, here, so the client can answer in seconds>
- **Evidence.** <the measurement, digest or requirement that backs it>
- **Costs.** <required on CHARTER and IRREVERSIBLE. What this reopens: signed
  text retired and the sites quoting it; requirements returning to
  `in-progress`; any affected path no task owns; the estimate in step-units.
  `none` is a legitimate answer and must be stated rather than left off>
- **Would change if.** <what would make the recommendation wrong>
- **Raised.** <YYYY-MM-DD> by <T-n>
- **Window.** <YYYY-MM-DD HH:MM, when the charter's escalation window expires and
  the loop proceeds on the recommendation; `none` for `CHARTER` and
  `IRREVERSIBLE`, which always block>
- **Status.** open
<!-- example:end -->
