#!/usr/bin/env python3
"""Negative control for session_cost.py (P-35).

The defect this script exists to prevent is a plausible wrong number, so the
cases here are mostly about the shapes a transcript takes that would produce
one: the same request written across several rows, a usage object with no
request behind it, a line that will not parse, a file with nothing in it.

More than a third are false-positive controls, and they matter more than usual
here. Over-collapsing is as wrong as under-collapsing and much harder to
notice: a dedupe that merged two genuinely distinct requests would report a
smaller, tidier, entirely fictional figure, and nothing downstream would
disagree with it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.path.join(HERE, "session_cost.py")


def row(rid, model="claude-opus-5", inp=0, out=0, read=0, write=0, usage=True):
    e = {"type": "assistant", "message": {"id": "msg_" + (rid or "x"),
                                          "model": model}}
    if rid:
        e["requestId"] = rid
    if usage:
        e["message"]["usage"] = {
            "input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": read, "cache_creation_input_tokens": write}
    return json.dumps(e)


def write_transcript(root, name, lines):
    path = os.path.join(root, name + ".jsonl")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def run(path=None, extra=(), env_session=None, project=None):
    argv = [sys.executable, SCRIPT]
    if path:
        argv += ["--transcript", path]
    if project:
        argv += ["--project", project]
    argv += list(extra)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
    if env_session:
        env["CLAUDE_CODE_SESSION_ID"] = env_session
    p = subprocess.run(argv, capture_output=True, text=True, env=env)
    doc = None
    if "--json" in extra and p.stdout.strip():
        try:
            doc = json.loads(p.stdout)
        except ValueError:
            doc = None
    return p.returncode, p.stdout, p.stderr, doc


# Three rows, one request: what the harness actually writes for a turn that
# emitted thinking, text and a tool call.
TRIPLE = [row("req_A", out=100, read=1000, write=10),
          row("req_A", out=100, read=1000, write=10),
          row("req_A", out=100, read=1000, write=10)]


def cases(root):
    out = []
    add = lambda name, fn: out.append((name, fn))

    def triple_is_one(_):
        p = write_transcript(root, "triple", TRIPLE)
        rc, _o, _e, d = run(p, ["--json"])
        if rc != 0:
            return f"exited {rc}"
        if d["requests"] != 1:
            return f"counted {d['requests']} requests, wanted 1"
        if d["tokens"]["output_tokens"] != 100:
            return f"output {d['tokens']['output_tokens']}, wanted 100 counted once"
        if abs(d["row_inflation"] - 3.0) > 1e-6:
            return f"row_inflation {d['row_inflation']}, wanted 3.0"
    add("triple-counted-rows-are-one-request", triple_is_one)

    def distinct(_):
        p = write_transcript(root, "distinct", [
            row("req_A", out=10), row("req_B", out=20), row("req_C", out=30)])
        rc, _o, _e, d = run(p, ["--json"])
        if d is None or rc != 0:
            return f"exited {rc}"
        if d["requests"] != 3:
            return f"collapsed 3 distinct requests into {d['requests']}"
        if d["tokens"]["output_tokens"] != 60:
            return f"output {d['tokens']['output_tokens']}, wanted 60"
    add("fp-distinct-requests-stay-distinct", distinct)

    def mixed(_):
        p = write_transcript(root, "mixed", TRIPLE + [
            row("req_B", out=7, read=70), row("req_B", out=7, read=70),
            row("req_C", out=3, read=30)])
        rc, _o, _e, d = run(p, ["--json"])
        if d["requests"] != 3:
            return f"{d['requests']} requests, wanted 3"
        if d["tokens"]["output_tokens"] != 110:
            return f"output {d['tokens']['output_tokens']}, wanted 110"
        if d["tokens"]["cache_read_input_tokens"] != 1100:
            return f"cache read {d['tokens']['cache_read_input_tokens']}, wanted 1100"
        if d["processed"] != 110 + 1100 + 10 + 0:
            return f"processed {d['processed']}, wanted 1220"
    add("fp-totals-are-the-sum-of-the-deduped-requests", mixed)

    def no_usage(_):
        p = write_transcript(root, "nousage", [
            row("req_A", out=10),
            json.dumps({"type": "user", "message": {"content": "hello"}}),
            row("req_B", usage=False)])
        rc, _o, _e, d = run(p, ["--json"])
        if d["requests"] != 1:
            return f"{d['requests']} requests; rows without usage must not count"
    add("rows-without-usage-are-ignored", no_usage)

    def orphan(_):
        p = write_transcript(root, "orphan", [
            row("req_A", out=10), row(None, model="<synthetic>", out=999)])
        rc, _o, _e, d = run(p, ["--json"])
        if d["requests"] != 1:
            return f"{d['requests']} requests, wanted 1"
        if d["tokens"]["output_tokens"] != 10:
            return "a usage row with no request was counted into the total"
        if d["rows_without_a_request"] != {"<synthetic>": 1}:
            return (f"the orphan row was dropped silently: "
                    f"{d['rows_without_a_request']}")
    add("a-usage-row-with-no-request-is-reported-not-dropped", orphan)

    def broken(_):
        p = write_transcript(root, "broken", [
            row("req_A", out=10), "{not json at all", row("req_B", out=20)])
        rc, _o, _e, d = run(p, ["--json"])
        if rc != 0:
            return f"exited {rc}; one bad line must not lose the file"
        if d["requests"] != 2:
            return f"{d['requests']} requests, wanted 2"
        if d["unparseable_lines"] != 1:
            return f"unparseable_lines {d['unparseable_lines']}, wanted 1"
    add("an-unparseable-line-is-skipped-and-counted", broken)

    def empty(_):
        p = write_transcript(root, "empty", [
            json.dumps({"type": "user", "message": {"content": "hi"}})])
        rc, _o, err, _d = run(p, ["--json"])
        if rc != 2:
            return f"exited {rc}, wanted 2 -- no usage is a finding, not a zero"
        if "empty" not in err:
            return f"stderr does not name the finding: {err.strip()[:120]!r}"
    add("a-transcript-with-no-usage-is-a-finding-not-a-zero", empty)

    def missing(_):
        rc, _o, err, _d = run(os.path.join(root, "does-not-exist.jsonl"))
        if rc != 2 or "no-transcript" not in err:
            return f"exited {rc}: {err.strip()[:120]!r}"
    add("a-missing-transcript-exits-2", missing)

    def conflict(_):
        p = write_transcript(root, "conflict", [
            row("req_A", out=10), row("req_A", out=999)])
        rc, _o, _e, d = run(p, ["--json"])
        if d["usage_conflicts"] != 1:
            return ("two rows disagreed about one request's usage and it was "
                    "not flagged -- the dedupe key would be silently wrong")
    add("disagreeing-usage-on-one-request-is-flagged", conflict)

    def models(_):
        p = write_transcript(root, "models", [
            row("req_A", model="claude-opus-5", out=10),
            row("req_B", model="claude-haiku-4-5-20251001", out=5),
            row("req_B", model="claude-haiku-4-5-20251001", out=5)])
        rc, _o, _e, d = run(p, ["--json"])
        by = d["by_model"]
        if set(by) != {"claude-opus-5", "claude-haiku-4-5-20251001"}:
            return f"models {sorted(by)}"
        if by["claude-haiku-4-5-20251001"]["requests"] != 1:
            return "the duplicated haiku request was counted twice per model"
    add("fp-per-model-split-dedupes-too", models)

    def share_usd(_):
        p = write_transcript(root, "share", [row("req_A", out=10)])
        rc, _o, _e, d = run(p, ["--json", "--anchor", "12.23:1.0", "--usd", "9.81"])
        want = 9.81 / 12.23
        if abs(d["derived_share_percent"] - want) > 0.01:
            return f"{d['derived_share_percent']} vs {want:.3f}"
    add("fp-a-share-derived-from-usd-is-the-usd-ratio", share_usd)

    def share_differs(_):
        # The trap --help names, demonstrated rather than asserted: the same
        # session against the same anchor gives a different answer by tokens
        # than by dollars, because output tokens and cache reads are not the
        # same unit of cost. If these two ever agree, the warning in --help
        # has stopped being true and should be re-derived, not deleted.
        p = write_transcript(root, "share2", [row("req_A", out=10, read=1_000_000)])
        _rc, _o, _e, by_tok = run(p, ["--json", "--anchor", "15.8e6:1.0"])
        _rc, _o, _e, by_usd = run(p, ["--json", "--anchor", "12.23:1.0",
                                      "--usd", "9.81"])
        if abs(by_tok["derived_share_percent"]
               - by_usd["derived_share_percent"]) < 0.01:
            return ("a token-derived share and a USD-derived share agreed; "
                    "the --help warning is no longer demonstrated")
    add("a-token-derived-share-is-not-a-usd-derived-share", share_differs)

    def no_session(_):
        empty_project = tempfile.mkdtemp(prefix="devteam-cost-project-", dir=root)
        rc, _o, err, _d = run(None, ["--json"], project=empty_project)
        if rc != 2 or "no-session" not in err:
            return f"exited {rc}: {err.strip()[:160]!r}"
        if "coin flip" not in err:
            return "it did not say why it refuses to guess by modification time"
    add("no-session-id-lists-candidates-rather-than-guessing", no_session)

    def human(_):
        p = write_transcript(root, "human", TRIPLE)
        rc, out_, _e, _d = run(p)
        if rc != 0:
            return f"exited {rc}"
        for want in ("requests", "total processed", "the naive reading"):
            if want not in out_:
                return f"the human report omits {want!r}"
        if "3.00x" not in out_:
            return "the human report does not show what the naive reading would say"
    add("fp-the-human-report-shows-the-naive-reading-it-avoided", human)

    def cache_share(_):
        p = write_transcript(root, "cache", [row("req_A", inp=0, read=99, write=1)])
        rc, out_, _e, _d = run(p)
        if "99.0% of input" not in out_:
            return f"cache hit share wrong: {out_.strip()[:160]!r}"
    add("fp-the-cache-hit-share-is-a-share-of-input", cache_share)

    def zeroes(_):
        p = write_transcript(root, "zeroes", [row("req_A")])
        rc, _o, _e, d = run(p, ["--json"])
        if rc != 0 or d["requests"] != 1 or d["processed"] != 0:
            return f"a request with all-zero usage broke it: rc={rc} {d}"
    add("fp-an-all-zero-request-does-not-break-it", zeroes)

    return out


def main():
    root = tempfile.mkdtemp(prefix="devteam-session-cost-control-")
    try:
        passed = failed = 0
        all_cases = cases(root)
        for name, fn in all_cases:
            try:
                why = fn(root)
            except Exception as exc:                # noqa: BLE001
                why = f"raised {type(exc).__name__}: {exc}"
            if why:
                failed += 1
                print(f"FAIL  {name}: {why}")
            else:
                passed += 1
        total = len(all_cases)
        fp = sum(1 for n, _ in all_cases if n.startswith("fp-"))
        print(f"\nsession_cost control: {passed} passed, {failed} failed, "
              f"{total} cases ({fp} of them false-positive controls, "
              f"{100 * fp // total}%)")
        return 1 if failed else 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
