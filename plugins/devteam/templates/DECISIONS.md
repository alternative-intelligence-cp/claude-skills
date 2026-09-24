# Decisions

Numbered, dated, and **each one records the alternatives declined and why they
lost** (P-21). The alternatives are exactly what the next reader will propose,
and a decision that does not say why they lost gets re-litigated by everyone who
arrives fresh.

**A settled decision is superseded, never rewritten** (P-23). The old text stays,
dated, because it records what was true when it was made — and how an error
survived is itself the lesson.

**Every decision must be cited by something** (P-22). A decision nothing cites is
almost always a requirement that states a rule and forgot to attribute it, which
is exactly the finding `defined-uncited` exists to surface.

**A decision can accept a finding a check reports, with an `Accepts.` field**
(P-51). The grammar is the plugin's `templates/FORMATS.md`, §"Accepted
findings". **An acceptance restores the zero. It does not suppress a finding.**
The checks exist so that a clean result means something, and every acceptance
is a finding they will never show you again. So accept a finding only once you
have decided it will not be fixed, and supersede the decision on the day that
changes. An acceptance whose finding has stopped firing is `stale-acceptance`,
and the checks report it until the decision is superseded. The decision's P-26
class decides who makes it. Its `Reviewed.` line reads `client`, `unreviewed`
for a `REVERSIBLE` decision the manager made alone (P-27), or
`proceeded-unreviewed (Q-n)`. Without that line, the acceptance accepts
nothing.

---

<!-- example:begin -->
### D-1 — <the choice, stated as a claim>

- **Decision.** <what was decided, in one sentence>
- **Because.** <the reason, tied to a requirement, a measurement or a digest>
- **Alternatives declined.**
  - <alternative> — <why it lost, specifically>
  - <alternative> — <why it lost, specifically>
- **Date.** <YYYY-MM-DD>
- **Supersedes.** none
- **Reviewed.** client

### D-2 — <the finding accepted, and why it will not be fixed>

- **Decision.** Accept <the finding>, because <why it is not a defect here, or cannot be fixed yet>
- **Because.** <the reason, tied to a requirement, a measurement or a digest>
- **Alternatives declined.**
  - fix it now — <why not, specifically>
- **Date.** <YYYY-MM-DD>
- **Supersedes.** none
- **Reviewed.** unreviewed
- **Accepts.**
  - `check_trace` `missing-field` `tasks/T-1.md` — T-1 has no **Discharges.**
<!-- example:end -->
