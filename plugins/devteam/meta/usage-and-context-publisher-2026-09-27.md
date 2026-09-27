# Usage and context numbers that agents can read — a candidate companion plugin

Written 2026-09-27 by `nitpick-libs_s8`, the Nitpick library workbench's
orchestrator, at the owner's request, so that this idea is waiting here when
`devteam` work resumes. **This is not a plan and nothing here is committed to.**
It records what was built and measured that day in the owner's own
configuration, and why it may deserve to become a small plugin that `devteam`
uses.

## 1. The problem, in the owner's words

`devteam` needs the usage figures after every turn — the pipeline is being
optimised and its costs predicted — and today an agent can only get them by
stopping and waiting for the owner to run `/usage` and paste the result:

> "I'm hoping anthropic is gonna give us a clean API for it at some point as I
> am far from the only person who needs an easier way to get that data that the
> agents themselves can access. Otherwise they have to stop and wait for me to
> run the command and provide the data. If i'm at the workstation currently that
> is no big deal at all … However, if i am not at the workstation then i'm
> fucked."

What was tried before, and set aside:

- a downloaded script that impersonated a Claude Code session to call an
  endpoint with "experimental" in its name — unsafe to depend on, and deleted;
- a clone of the public `claude_usage` tool, which reads the OAuth token and
  calls the usage API — it did not give the pipeline what it needed; removed
  from META on 2026-09-27;
- a `pexpect` screen-scraper of `/usage` written by Gemini
  (`META/DEV_TEAM/claude_info.py`) — partly worked, but terminal rendering got in
  the way of the numbers;
- `META/DEV_TEAM/get_usage_probe.py`, which asks a headless `claude` for
  structured usage through the Agent SDK's control protocol (`get_usage`).
  **Unverified:** whether that request is a documented, supported part of the
  SDK. Check the SDK documentation first — if it is documented, it may be the
  cleanest route of all.

## 2. What exists now (MEASURED 2026-09-27, on the owner's machine)

**Claude Code already hands the numbers to every status-line command**, on
stdin, on each refresh (`refreshInterval` 60 s in the owner's settings):

- `rate_limits.five_hour` and `rate_limits.seven_day`, each with
  `used_percentage` and `resets_at` (a Unix epoch) — **the only two keys
  present**: no separate Fable meter and no cloud-credit balance;
- `context_window`, per session: `used_percentage`, `remaining_percentage`,
  `context_window_size`, `total_input_tokens`, `total_output_tokens`, and
  `current_usage` (`input_tokens`, `output_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`) — **token counts
  per session, which may serve cost prediction better than percentages**;
- `session_id` and `session_name`.

**The owner's status line now publishes them** (`~/.claude/statusline.sh`, the
originals kept as `statusline.sh.bak-2026-09-27` and `…-27b`), atomically and
without printing anything extra:

- `~/.claude/usage-latest.json` — `{written_at, written_at_iso, rate_limits}`;
  read with `jq . ~/.claude/usage-latest.json`;
- `~/.claude/context/<session_id>.json` — the session's name, model and whole
  `context_window` block; a session finds its own by name with
  `jq -r --arg n <name> 'select(.session_name==$n) | .context_window.used_percentage' ~/.claude/context/*.json`.
  Files idle for a week are pruned.

**And a hook warns a session before compaction**
(`~/.claude/hooks/context_warn.sh`, a `PostToolUse` hook — on trial in the
library workbench only, through its untracked `.claude/settings.local.json`):
one line into the session, and the same line to the owner, when its context
first crosses 80 % and again at 90 %; silent otherwise; re-armed when the
context falls below 70 % after a compaction, because the second compaction is
the dangerous one. **MEASURED with a probe subagent:** a subagent's hook input
carries the parent's `session_id` AND the parent's `transcript_path`, and only
`agent_id` / `agent_type` tell it apart — so the hook checks those, and a
worker cannot consume its seat's warning.

## 3. What it could become (REASONED — nothing below was run)

A small plugin — call it `session-meter` until something better turns up —
bundling three things:

1. **The publisher**, as a script. Two modes: called from an existing status
   line (`echo "$input" | publish`) for people who have one, or installed as the
   status-line command itself and printing nothing, for people who want the
   files without a custom status line. A `statusLine` is a settings key, not a
   plugin component in the settings schema seen that day, so installing it is
   probably one documented line for the user to add rather than something the
   plugin can do alone.
2. **The context warning hook**, shipped in the plugin's `hooks/hooks.json`
   with `${CLAUDE_PLUGIN_ROOT}`, its thresholds configurable.
3. **A skill** telling agents how to read both files and what to do at each
   threshold.

`devteam` would consume it for the per-turn figures its cost predictions need.
The owner's view: *"there seems to be some potential in it at least until
anthropic provides a more formal way of doing it."*

**Before building, check:** whether `rate_limits` is in Claude Code's documented
status-line schema (it was observed, not looked up); how the library
workbench's trial of the hook went; and whether Anthropic has shipped an
official interface in the meantime, which would make most of this unnecessary.
