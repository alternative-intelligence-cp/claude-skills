# Currency

One row per external dependency the plan names — a standard, a data release, an
upstream version, a reference implementation (P-37). Every one of them moves,
and **anything called "current" without a date beside it is an unverified
claim**, because the model's knowledge has a cutoff and the world does not.

- A row **unchecked for six months is `stale`** to the auditor.
- A **security-relevant digest is `stale` after ninety days.**
- **A task whose currency rows are stale is not ready to start.**

| Depends on | Pinned | Checked | Source | Digest | Decision |
|---|---|---|---|---|---|
| <e.g. tzdata> | <2026c> | <YYYY-MM-DD> | <primary URL> | `<topic>.md` | D-3 |
