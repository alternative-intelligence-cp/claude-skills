#!/usr/bin/env python3
"""What did this session cost? Read from its own transcript, keyed correctly.

A devteam subcycle closes by writing its measured cost into its record, and
half of that figure is readable without asking anybody: the harness writes a
JSONL transcript per session under `~/.claude/projects/<slug>/<id>.jsonl`, and
every assistant entry carries the API `usage` for the request that produced it.

**This script exists because the obvious way to read that file is wrong, and
wrong in the way that is hardest to catch.** One API request is written to the
transcript ONCE PER CONTENT BLOCK -- thinking, text, and each tool use -- and
every one of those rows repeats the whole message-level `usage` object
unchanged. Summing rows therefore counts one request two, three or six times,
depending on how many tool calls it batched.

Two things make that a trap rather than a bug:

  * the inflated total is PLAUSIBLE. Measured on the two sessions of roadmap
    cycle 0.2, summing rows gave 2.11x and 2.02x the true figure -- close
    enough to each other that a reader who sampled both would conclude the
    factor is two and halve it. It is not a constant: it rises with tool
    calls per request, so scaling is wrong by an amount that grows with
    exactly the batching that makes a session efficient.
  * the inflated total AGREED with the only independent anchor available. The
    row-summed figure for subcycle 0.2.1 landed within 2% of the previous
    subcycle's harness-reported total, on both token count and request count.
    Checking the naive method against the anchor would have confirmed it.

So: key on `requestId`, one entry per request, and never scale.

  no-transcript    the named session has no transcript file
  no-session       no session id was given and none is in the environment;
                   the candidates are listed rather than guessed at, because
                   picking the newest by mtime returns whichever session on
                   this project wrote last, which during a handoff is a coin
                   flip between two files with the same minute stamp
  empty            the transcript carries no usage at all. Reported as a
                   finding, never as a cost of zero
  usage-conflict   two rows share a requestId and disagree about its usage.
                   Nothing observed does this; if it starts, the dedupe key
                   is wrong and this says so instead of silently picking one

Exit 0 a figure was produced, 2 it could not be.

What this does NOT report, and cannot: the percentage of a subscription
window. That is account-wide server state spanning every session on the
account, so no single session can compute it even in principle -- `MEASURED`
2026-09-07: no CLI flag or subcommand exposes it, the telemetry directory
holds only stale dumps, and `~/.claude/.credentials.json` carries the tier
rather than the consumption. The percentage has to be asked for. `--anchor`
will derive an estimate from a previously measured pair, and the derivation
has a trap of its own that its help text names.
"""
import argparse
import collections
import glob
import json
import os
import sys

HOME = os.path.expanduser("~")


def transcript_dir(project):
    """The harness names a project's directory after its path, `/` -> `-`."""
    return os.path.join(HOME, ".claude", "projects",
                        os.path.abspath(project).replace(os.sep, "-"))


def find_transcript(session, project):
    """(path, None) or (None, a finding and what to do about it)."""
    d = transcript_dir(project)
    if session:
        path = os.path.join(d, f"{session}.jsonl")
        if os.path.isfile(path):
            return path, None
        return None, ("no-transcript",
                      f"{path} does not exist. The session id is the name of "
                      "the file, not the `session_...` id in a share URL.")
    candidates = sorted(glob.glob(os.path.join(d, "*.jsonl")))
    listing = "\n".join(
        f"    {os.path.basename(c)[:-6]}  {os.path.getsize(c):>10,} bytes"
        for c in candidates) or "    (none under " + d + ")"
    return None, ("no-session",
                  "no session id given and CLAUDE_CODE_SESSION_ID is not set.\n"
                  "  Pass --session <id>. Candidates on this project:\n"
                  + listing +
                  "\n  Not guessed at by modification time: during a handoff "
                  "two live sessions\n  write in the same minute, and the "
                  "newest is a coin flip between them.")


KEYS = ("input_tokens", "output_tokens",
        "cache_read_input_tokens", "cache_creation_input_tokens")


def read(path):
    """Fold a transcript into one record per API request.

    Returns (per_request, stats). `per_request` maps requestId -> (model,
    usage). `stats` counts what was seen, so the caller can report the
    inflation the naive reading would have produced rather than merely
    avoiding it.
    """
    per, stats = {}, collections.Counter()
    conflicts, no_request = [], collections.Counter()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            stats["lines"] += 1
            try:
                entry = json.loads(line)
            except ValueError:
                stats["unparseable"] += 1
                continue
            message = entry.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            stats["usage_rows"] += 1
            rid = entry.get("requestId")
            if not rid:
                # A synthetic row -- an API error the harness recorded itself.
                # It has a usage object and no request behind it. Counted
                # apart rather than dropped: a row silently discarded is a
                # row nobody knows to ask about.
                no_request[message.get("model") or "unknown"] += 1
                continue
            model = message.get("model") or "unknown"
            if rid in per:
                stats["duplicate_rows"] += 1
                if per[rid][1] != usage:
                    conflicts.append(rid)
                continue
            per[rid] = (model, usage)
    stats["conflicts"] = len(set(conflicts))
    return per, stats, no_request


def totals(per):
    by_model = collections.defaultdict(collections.Counter)
    overall = collections.Counter()
    for model, usage in per.values():
        by_model[model]["requests"] += 1
        overall["requests"] += 1
        for k in KEYS:
            by_model[model][k] += usage.get(k) or 0
            overall[k] += usage.get(k) or 0
    return overall, by_model


def processed(c):
    return sum(c[k] for k in KEYS)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="session_cost.py",
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"),
                    help="session id; defaults to $CLAUDE_CODE_SESSION_ID")
    ap.add_argument("--project", default=os.getcwd(),
                    help="the project the session ran in (default: cwd)")
    ap.add_argument("--transcript", help="a transcript path, bypassing the lookup")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable; the caller may be another session")
    ap.add_argument("--anchor", metavar="TOKENS:PERCENT",
                    help="derive a share of a quota window from a measured "
                         "pair, e.g. 15.8e6:1.0. BEWARE: a token ratio is not "
                         "a cost ratio -- output tokens cost many times a "
                         "cache read, so two sessions with the same token "
                         "count and different output shares do not cost the "
                         "same. Prefer USD:PERCENT from a usage report")
    ap.add_argument("--usd", type=float,
                    help="this session's cost in USD from a usage report; with "
                         "--anchor given as USD:PERCENT this is the honest "
                         "derivation and the token one is not used")
    args = ap.parse_args(argv)

    path = args.transcript
    if not path:
        path, problem = find_transcript(args.session, args.project)
        if problem:
            kind, detail = problem
            print(f"session_cost: {kind} -- {detail}", file=sys.stderr)
            return 2
    elif not os.path.isfile(path):
        print(f"session_cost: no-transcript -- {path} does not exist",
              file=sys.stderr)
        return 2

    per, stats, no_request = read(path)
    if not per:
        print(f"session_cost: empty -- {path} carries no usage for any request. "
              "That is a finding, not a cost of zero.", file=sys.stderr)
        return 2
    overall, by_model = totals(per)
    naive = stats["usage_rows"]
    inflation = naive / overall["requests"]

    if args.anchor:
        try:
            a_amount, a_pct = (float(x) for x in args.anchor.split(":"))
        except ValueError:
            print("session_cost: --anchor wants AMOUNT:PERCENT", file=sys.stderr)
            return 2
        mine = args.usd if args.usd is not None else processed(overall)
        share = mine / a_amount * a_pct if a_amount else 0.0
        basis = "USD" if args.usd is not None else "tokens (see --help)"
    else:
        share = None

    if args.json:
        out = {
            "transcript": path, "requests": overall["requests"],
            "tokens": {k: overall[k] for k in KEYS},
            "processed": processed(overall),
            "by_model": {m: dict(c) for m, c in by_model.items()},
            "usage_rows": naive, "row_inflation": round(inflation, 3),
            "rows_without_a_request": dict(no_request),
            "usage_conflicts": stats["conflicts"],
            "unparseable_lines": stats["unparseable"],
        }
        if share is not None:
            out["derived_share_percent"] = round(share, 3)
        print(json.dumps(out, indent=2))
        return 0

    inp = overall["input_tokens"] + overall["cache_read_input_tokens"] \
        + overall["cache_creation_input_tokens"]
    print(f"session {os.path.basename(path)[:-6]}")
    print(f"  requests            {overall['requests']:,}")
    print(f"  uncached input      {overall['input_tokens']:,}")
    print(f"  output              {overall['output_tokens']:,}")
    print(f"  cache read          {overall['cache_read_input_tokens']:,}")
    print(f"  cache write         {overall['cache_creation_input_tokens']:,}")
    print(f"  total processed     {processed(overall):,}")
    if inp:
        print(f"  cache hit share     {100 * overall['cache_read_input_tokens'] / inp:.1f}% of input")
    if len(by_model) > 1:
        for model, c in sorted(by_model.items()):
            print(f"  {model:<20}{c['requests']:,} requests, "
                  f"{c['output_tokens']:,} output")
    if share is not None:
        print(f"  derived share       {share:.2f}% of a quota window, from "
              f"{basis}")
    print(f"\n  the naive reading would have said {naive:,} requests and "
          f"{inflation:.2f}x these tokens")
    if no_request:
        print(f"  {sum(no_request.values())} usage row(s) carried no request "
              f"and are excluded: {dict(no_request)}")
    if stats["unparseable"]:
        print(f"  {stats['unparseable']} line(s) would not parse and were skipped")
    if stats["conflicts"]:
        print(f"  WARNING: {stats['conflicts']} requestId(s) carry disagreeing "
              "usage -- the dedupe key may be wrong here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
