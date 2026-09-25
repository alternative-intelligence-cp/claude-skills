#!/usr/bin/env python3
"""Negative control for bg_session_probe.py (P-35).

The probe starts real background sessions, and every one of them spends real
tokens on the account that runs it. So this control starts none. It plants
each fault in a DESCRIBED WORLD -- a CLI, a listing, files and transcripts that
change on a virtual clock -- through the probe's seams (`run`, `read`, `mtime`,
`which`, `clock`, `pause`, `transcripts`), and demands the matching finding and
exit code. Three of the faults were met for real on 2026-09-23 and are planted
here because of it: a workspace nobody had trusted, a session whose files were
in a worktree the listing stopped naming once it stopped, and a session that
sat on a permission prompt nobody was told about.

**State the limit, so nobody reads more into a green line than is there.**
This control proves the verdict logic -- that each fault produces its finding,
that a blocker outranks the rest, that the ceiling stops every session, and
that what merely differs from the first measured run is not reported. It does
**not** prove a background session works: that was measured by hand on
2026-09-23 and is recorded in `meta/roadmap/done/0.3.0.md` §3.1. The two
last cases are the join between the two: the real script, as a subprocess,
against a fake `claude` on PATH -- the planted case 0.3.0 asks for, kept.
"""
import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import bg_session_probe as probe  # noqa: E402

EPOCH = 1_790_000_000
WORKDIR = "/w/bg"
TREE = WORKDIR + "/.claude/worktrees/one"


class World:
    """A CLI and a filesystem that change on a virtual clock."""

    def __init__(self, tmp, scripts, help_has_bg=True, bg="ok", listing_ok=True,
                 hidden=(), printed="standard", stale_trees=(), old=()):
        self.tmp, self.scripts = tmp, scripts
        self.help_has_bg, self.bg, self.listing_ok = help_has_bg, bg, listing_ok
        self.hidden, self.printed = set(hidden), printed
        self.stale_trees = list(stale_trees)
        self.t = EPOCH
        self.sessions = {}                 # sessionId -> entry dict
        self.pending = []                  # (due, sessionId, event)
        for n, name in enumerate(old):     # an earlier run's session, stopped, still listed
            sid = f"0ld{n:05x}-0000-4000-8000-000000000000"
            self.sessions[sid] = {"id": sid[:8], "cwd": WORKDIR, "kind": "background",
                                  "startedAt": (EPOCH - 3600) * 1000, "sessionId": sid,
                                  "name": name, "state": "stopped", "_origin": WORKDIR}
        self.files = {}                    # path -> (text, mtime)
        self.transcripts = {}              # sessionId -> [paths]
        self.calls, self.stopped = [], []
        self.n = 0

    # --- the seams ---------------------------------------------------------

    def run(self, argv, timeout=60, cwd=None):
        cmd = " ".join(argv)
        self.calls.append(argv)
        if argv[:2] == ["claude", "--version"]:
            return 0, "2.1.281 (Claude Code)\n", "", cmd
        if argv[:2] == ["claude", "--help"]:
            flag = "  --bg, --background   Start the session in the background\n" if self.help_has_bg else ""
            return 0, "Usage: claude [options]\n" + flag, "", cmd
        if argv[:4] == ["claude", "agents", "--json", "--all"]:
            if not self.listing_ok:
                return 1, "", "error: unknown command 'agents'", cmd
            shown = [dict(e) for e in self.sessions.values() if e["name"] not in self.hidden]
            return 0, json.dumps(shown), "", cmd
        if argv[:2] == ["claude", "--bg"]:
            if self.bg == "unknown-option":
                return 1, "", "error: unknown option '--bg'", cmd
            if self.bg == "untrusted":
                return 1, "", ("Workspace not trusted. Run `claude` in /w/bg once and "
                               "accept the trust prompt, then retry."), cmd
            name = argv[argv.index("--name") + 1]
            sid = self.spawn(name, cwd or WORKDIR)
            short = sid[:8]
            if self.printed == "variant":
                return 0, f"started id={short} ({name})\n", "", cmd
            return 0, (f"backgrounded · {short} · {name}\n  claude attach {short}    open in this "
                       f"terminal\n  claude stop {short}      stop this session\n"), "", cmd
        if argv[:2] == ["claude", "logs"]:
            return 0, "● a line of output\n", "", cmd
        if argv[:2] in (["claude", "stop"], ["claude", "rm"]):
            self.stopped.append((argv[1], argv[2]))
            for e in self.sessions.values():
                if e["id"] == argv[2] or e["sessionId"] == argv[2]:
                    e.pop("status", None)
                    e.pop("waitingFor", None)
                    e["state"] = "stopped"
                    e["cwd"] = e["_origin"]
            return 0, f"stopped {argv[2]}\n", "", cmd
        if argv[:2] == ["git", "-C"] and argv[3:5] == ["worktree", "list"]:
            trees = sorted({e["cwd"] for e in self.sessions.values() if "/.claude/worktrees/" in e["cwd"]}
                           | {p.rsplit("/", 1)[0] for p in self.files if "/.claude/worktrees/" in p})
            return 0, "".join(f"worktree {t}\n" for t in [WORKDIR] + self.stale_trees + trees), "", cmd
        raise AssertionError(f"the control was not asked about: {cmd}")

    def read(self, path):
        if path in self.files:
            return self.files[path][0]
        if path and path.startswith(self.tmp) and os.path.isfile(path):
            with open(path) as fh:
                return fh.read()
        return None

    def mtime(self, path):
        return self.files[path][1] if path in self.files else None

    def pause(self, seconds):
        self.t += seconds
        self.due()

    # --- the world ------------------------------------------------------------

    def spawn(self, name, cwd):
        self.n += 1
        sid = f"{self.n:08x}-0000-4000-8000-000000000000"
        self.sessions[sid] = {"id": sid[:8], "cwd": cwd, "kind": "background",
                              "startedAt": self.t * 1000, "sessionId": sid, "name": name,
                              "state": "working", "_origin": cwd}
        path = os.path.join(self.tmp, f"{sid}.jsonl")
        open(path, "w").close()
        self.transcripts[sid] = [path]
        for delay, *event in self.scripts.get(name, []):
            self.pending.append((self.t + delay, sid, event))
        self.due()
        return sid

    def due(self):
        ready = sorted([p for p in self.pending if p[0] <= self.t], key=lambda p: p[0])
        self.pending = [p for p in self.pending if p[0] > self.t]
        for when, sid, event in ready:
            self.apply(when, sid, event)

    def apply(self, when, sid, event):
        e = self.sessions[sid]
        if e.get("state") == "stopped":
            return                                    # a stopped session does nothing
        op, *args = event
        if op == "status":
            e.pop("waitingFor", None)
            e.update(args[0])
            if args[0].get("state") == "stopped":
                # MEASURED 2026-09-23: once stopped, a session is listed at
                # the checkout it started in, not the worktree it wrote in.
                e["cwd"] = e["_origin"]
        elif op == "cwd":
            e["cwd"] = args[0]
        elif op == "file":
            text = args[1].replace("{EPOCH_NOW}", str(int(when)))
            self.files[os.path.join(e["cwd"], args[0])] = (text, when)
        elif op == "inplace":                        # a write that ignores cwd
            self.files[os.path.join(WORKDIR, args[0])] = (args[1], when)
        elif op == "tokens":
            self.usage(e["sessionId"], args[0], args[1] if len(args) > 1 else None)
        elif op == "text":
            self.line(e, {"type": "user", "message": {"content": args[0]}}, when)
        elif op == "launch":                         # a Bash call run in the background
            self.line(e, {"type": "assistant", "message": {"stop_reason": "tool_use", "content": [
                {"type": "tool_use", "name": "Bash",
                 "input": {"command": "sleep 60 && date +%s", "run_in_background": True}}]}}, when)
        elif op == "end-turn":
            self.line(e, {"type": "assistant", "message": {"stop_reason": "end_turn",
                                                           "content": [{"type": "text", "text": "."}]}}, when)
        elif op == "notice":                         # a finished task starts a new turn
            self.line(e, {"type": "user", "message": {
                "content": "<task-notification>\n<task-id>b0000</task-id>\n</task-notification>"}}, when)
        elif op == "spawn":
            self.spawn(args[0], WORKDIR)
        elif op == "state-edit":                     # somebody repairs the state mid-run
            path = os.path.join(self.tmp, "state.json")
            d = json.load(open(path)) if os.path.exists(path) else {"sessions": {}}
            d["sessions"]["repaired"] = {"name": "probe-old", "sessionId": "repaired-by-hand"}
            json.dump(d, open(path, "w"))
        elif op == "subagent-dup":
            # the same request in the parent transcript and a subagent's
            sid = e["sessionId"]
            sub = os.path.join(self.tmp, f"{sid}-agent-x.jsonl")
            open(sub, "a").close()
            self.transcripts[sid].append(sub)
            for path in (self.transcripts[sid][0], sub):
                self.row(path, "req_dup", args[0])

    def line(self, e, row, when):
        row["timestamp"] = dt.datetime.fromtimestamp(when, dt.timezone.utc).isoformat().replace("+00:00", "Z")
        with open(self.transcripts[e["sessionId"]][0], "a") as fh:
            fh.write(json.dumps(row) + "\n")

    def usage(self, sid, n, rid=None):
        self.row(self.transcripts[sid][0], rid or f"req_{sid[:8]}_{self.t}_{n}", n)

    @staticmethod
    def row(path, rid, n):
        with open(path, "a") as fh:
            fh.write(json.dumps({"type": "assistant", "requestId": rid, "message": {
                "model": "claude-sonnet-5", "usage": {
                    "input_tokens": 0, "output_tokens": 0,
                    "cache_read_input_tokens": n, "cache_creation_input_tokens": 0}}}) + "\n")


BUSY, IDLE = {"status": "busy", "state": "working"}, {"status": "idle", "state": "working"}


def healthy():
    """The world as 2026-09-23 measured it, working."""
    return {
        "probe-a1": [(0, "tokens", 50_000), (5, "status", BUSY), (8, "cwd", TREE),
                     (9, "file", "a1.txt", "ready\n"),
                     (10, "file", "a1-skills.txt", "devteam:run\ndevteam:resume\n"),
                     (12, "status", IDLE), (12, "tokens", 60_000)],
        "probe-a1b": [(5, "status", BUSY), (8, "inplace", "a1b.txt", "inplace"),
                      (9, "inplace", "a1b-bash.txt", "bash"), (12, "status", IDLE)],
        "probe-a2": [(5, "status", BUSY), (6, "cwd", TREE + "2"), (8, "end-turn"),
                     (20, "file", "a2-depth1.txt", "depth 1\n"),
                     (22, "file", "a2-depth2.txt", "depth 2\n"), (23, "notice"),
                     (25, "launch"), (26, "end-turn"), (90, "notice"),
                     (92, "file", "a2-woke.txt", "{EPOCH_NOW}\n"), (95, "status", IDLE)],
        "probe-a3s": [(5, "status", BUSY), (6, "spawn", "probe-a3t"), (10, "cwd", TREE + "3"),
                      (11, "file", "a3-start.txt", "backgrounded · x · probe-a3t\n"),
                      (11, "file", "a3-list.txt", "probe-a3t  background  idle\n"),
                      (12, "file", "a3-sent.txt", "{EPOCH_NOW}\n"), (13, "status", IDLE),
                      (30, "status", BUSY), (31, "file", "a3.txt", "pong from probe-a3t\n"),
                      (33, "file", "a3-stop.txt", "claude stop x\n"), (35, "tokens", 90_000),
                      (36, "status", {"state": "stopped", "status": None})],
        "probe-a3t": [(2, "status", BUSY), (3, "status", IDLE),
                      (20, "text", "ping from probe-a3s"), (20, "status", BUSY),
                      (22, "status", IDLE)],
    }


def without(scripts, name, match):
    """The same world with one of a session's events removed."""
    out = {k: list(v) for k, v in scripts.items()}
    out[name] = [ev for ev in out[name] if not match(ev)]
    return out


def with_events(scripts, name, *events):
    out = {k: list(v) for k, v in scripts.items()}
    out[name] = out.get(name, []) + list(events)
    return out


def file_named(fname):
    return lambda ev: ev[1] in ("file", "inplace") and ev[2] == fname


H = healthy()
ALL = "a1,a1b,a2,a3"

CASES = [
    # name, world kwargs, steps, extra args, expected findings, expected exit
    ("healthy", dict(scripts=H), ALL, [], {"worktree"}, 0),

    # --- no background manager: exit 1 ---------------------------------------
    ("no-cli", dict(scripts=H, no_cli=True), ALL, [], {"no-cli"}, 1),
    ("no-bg-in-help", dict(scripts=H, help_has_bg=False), ALL, [], {"no-bg"}, 1),
    # THE planted case, in-process: --help lists the flag and running it fails.
    # A probe that trusted --help would pass this machine.
    ("no-bg-refused-when-run", dict(scripts=H, bg="unknown-option"), ALL, [], {"no-bg"}, 1),
    ("no-listing", dict(scripts=H, listing_ok=False), ALL, [], {"no-listing"}, 1),
    # Git sees the worktree whether or not the listing shows the session.
    ("not-listed", dict(scripts=H, hidden={"probe-a1"}), "a1", [],
     {"not-listed", "no-work", "worktree"}, 1),
    ("no-work", dict(scripts=without(H, "probe-a1", file_named("a1.txt"))), "a1", [],
     {"no-work", "worktree"}, 1),
    ("no-plugin", dict(scripts=with_events(without(H, "probe-a1", file_named("a1-skills.txt")),
                                           "probe-a1", (10, "file", "a1-skills.txt", "(none)\n"))),
     "a1", [], {"no-plugin", "worktree"}, 1),
    ("no-subagent", dict(scripts=without(without(H, "probe-a2", file_named("a2-depth1.txt")),
                                         "probe-a2", file_named("a2-depth2.txt"))),
     "a2", [], {"no-subagent", "no-depth2"}, 1),
    ("no-depth2", dict(scripts=without(H, "probe-a2", file_named("a2-depth2.txt"))),
     "a2", [], {"no-depth2"}, 1),
    ("no-wake", dict(scripts=without(H, "probe-a2", file_named("a2-woke.txt"))),
     "a2", [], {"no-wake"}, 1),

    # --- a successor, but no handover: exit 2 ----------------------------------
    ("no-spawn", dict(scripts=without(without(H, "probe-a3s", lambda ev: ev[1] == "spawn"),
                                      "probe-a3s", file_named("a3.txt"))),
     "a3", [], {"no-spawn", "no-reply"}, 2),
    # An earlier run's probe-a3t, stopped and still listed, must not stand in
    # for a target that never started. Matched by name alone, it would.
    ("no-spawn-while-an-old-target-of-the-same-name-is-listed",
     dict(scripts=without(without(H, "probe-a3s", lambda ev: ev[1] == "spawn"),
                          "probe-a3s", file_named("a3.txt")), old=["probe-a3t"]),
     "a3", [], {"no-spawn", "no-reply"}, 2),
    ("no-message", dict(scripts=without(without(H, "probe-a3t", lambda ev: ev[1] == "text"),
                                        "probe-a3s", file_named("a3.txt"))),
     "a3", [], {"no-message", "no-reply"}, 2),
    ("no-reply", dict(scripts=without(H, "probe-a3s", file_named("a3.txt"))),
     "a3", [], {"no-reply"}, 2),
    # Woken is read from the transcript: the launch, then the turn ENDING, then
    # a notice ARRIVING, then the file. A session that never ended its turn
    # slept or polled -- and would pass a probe that only looked for the file.
    ("wake-unobserved", dict(scripts=without(H, "probe-a2", lambda ev: ev[1] == "end-turn")),
     "a2", [], {"wake-unobserved"}, 2),
    # The trap in the real transcripts: a turn end BEFORE the launch, while it
    # waited on its subagents. Counting that one would pass a session that
    # launched the command and then slept on it.
    ("wake-unobserved-when-the-only-turn-end-came-before-the-launch",
     dict(scripts=without(H, "probe-a2", lambda ev: ev[1] == "end-turn" and ev[0] == 26)),
     "a2", [], {"wake-unobserved"}, 2),
    ("wake-unobserved-when-no-notice-arrived",
     dict(scripts=without(H, "probe-a2", lambda ev: ev[1] == "notice" and ev[0] == 90)),
     "a2", [], {"wake-unobserved"}, 2),
    ("untrusted", dict(scripts=H, bg="untrusted"), ALL, [], {"untrusted"}, 2),
    ("a1b-isolated-anyway", dict(scripts=with_events(without(H, "probe-a1b", file_named("a1b.txt")),
                                                     "probe-a1b", (6, "cwd", TREE + "b"))),
     "a1b", [], {"a1b-undecided"}, 2),
    ("partial-run-is-not-a-go", dict(scripts=H), "a1,a2", [], {"worktree"}, 2),

    # --- noted, not blockers ------------------------------------------------------
    ("in-place-refused", dict(scripts=without(H, "probe-a1b", file_named("a1b.txt"))),
     ALL, [], {"in-place-refused", "worktree"}, 0),
    ("no-self-stop", dict(scripts=without(H, "probe-a3s", lambda ev: ev[1] == "status" and ev[0] == 36)),
     ALL, [], {"no-self-stop", "worktree"}, 0),
    ("blocked-on-a-permission-prompt",
     dict(scripts=with_events(H, "probe-a1", (13, "status", {"status": "waiting", "state": "blocked",
                                                            "waitingFor": "permission prompt"}))),
     ALL, [], {"blocked", "worktree"}, 0),

    # --- the stop -----------------------------------------------------------------
    ("ceiling", dict(scripts=with_events(H, "probe-a2", (40, "tokens", 9_000_000))),
     ALL, ["--ceiling", "5000000"], {"ceiling", "worktree"}, 3),

    # --- FALSE-POSITIVE CONTROLS --------------------------------------------------
    # Each differs from the first measured run and none is a fault.
    # A stopped session is listed at the checkout it STARTED in, not the
    # worktree it wrote in. A probe that read only the latest cwd would call a
    # working session's files missing. Found by running it, 2026-09-23.
    ("fp-files-in-a-worktree-the-listing-forgot",
     dict(scripts=with_events(H, "probe-a1", (14, "status", {"state": "stopped", "status": None}))),
     ALL, [], {"worktree"}, 0),
    # The id's printed format is not documented; the listing's name is the join.
    ("fp-id-printed-in-another-format", dict(scripts=H, printed="variant"), ALL, [], {"worktree"}, 0),
    # A status word nobody has seen is recorded verbatim and counts as settled.
    ("fp-unknown-status-word",
     dict(scripts=with_events(H, "probe-a1", (13, "status", {"status": "pondering"}))),
     ALL, [], {"worktree"}, 0),
    # THE FALSE FINDING THE LIVE RUN MADE, 2026-09-23: listed `busy` from the
    # launch to the file, because a pending background task keeps a session
    # busy in the listing after its turn has ended. The transcript shows the
    # wake; the listing cannot.
    ("fp-listed-busy-the-whole-time-it-waited",
     dict(scripts=without(H, "probe-a2", lambda ev: ev[1] == "status" and ev[0] == 95)),
     ALL, [], {"worktree"}, 0),
    # An earlier run's worktree is not this step's.
    ("fp-a-worktree-left-by-an-earlier-run",
     dict(scripts=without(H, "probe-a1", lambda ev: ev[1] == "cwd"), stale_trees=[TREE + "-old"]),
     ALL, [], set(), 0),
]


def run_case(tmp, kwargs, steps, extra):
    kwargs = dict(kwargs)
    no_cli = kwargs.pop("no_cli", False)
    world = World(tmp, **kwargs)
    probe.run, probe.read, probe.mtime = world.run, world.read, world.mtime
    probe.which = (lambda n: None) if no_cli else (lambda n: "/fake/bin/" + n)
    probe.clock, probe.pause = (lambda: world.t), world.pause
    probe.transcripts = lambda sid: list(world.transcripts.get(sid, []))
    probe.ensure_repo = lambda w: None
    args = ["--workdir", WORKDIR, "--state", os.path.join(tmp, "state.json"),
            "--steps", steps] + (extra or ["--ceiling", "10000000"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = probe.main(args)
    text = buf.getvalue()
    got = {line.split()[0] for line in text.splitlines() if line.startswith("  ") and
           line.split() and line.split()[0] in KINDS}
    return got, code, text, world


KINDS = {"no-cli", "no-bg", "no-listing", "not-listed", "no-work", "no-plugin", "no-subagent",
         "no-depth2", "no-wake", "no-spawn", "no-message", "no-reply", "wake-unobserved",
         "untrusted", "worktree", "no-self-stop", "ceiling", "in-place-refused", "blocked",
         "a1b-undecided"}

SEAMS = ("run", "read", "mtime", "which", "clock", "pause", "transcripts", "ensure_repo")


def main():
    saved = {n: getattr(probe, n) for n in SEAMS}
    passed = failed = 0
    extra_cases = 0
    try:
        for name, kwargs, steps, extra, expected, want in CASES:
            tmp = tempfile.mkdtemp(prefix="bgprobe-")
            try:
                got, code, text, world = run_case(tmp, kwargs, steps, extra)
                ok = got == expected and code == want
                if name == "ceiling":
                    # The stop means every session that was started is stopped,
                    # not only the one that crossed the line.
                    started = {e["id"] for e in world.sessions.values()}
                    stopped = {h for verb, h in world.stopped if verb == "stop"}
                    ok = ok and started <= stopped
                if name == "no-bg-in-help":
                    # Nothing that could spend is ever run.
                    ok = ok and not any(a[:2] == ["claude", "--bg"] for a in world.calls)
                if ok:
                    passed += 1
                else:
                    failed += 1
                    print(f"FAIL  {name}")
                    print(f"        expected {sorted(expected) or 'clean'} exit {want}")
                    print(f"        got      {sorted(got) or 'clean'} exit {code}")
                    for line in text.strip().split("\n")[-8:]:
                        print(f"        | {line}")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

        # The meter: a request a parent transcript and a subagent transcript
        # both carry is ONE request. Counted twice, the ceiling fires early; the
        # opposite error, dropping rows, lets it spend through.
        extra_cases += 1
        tmp = tempfile.mkdtemp(prefix="bgprobe-")
        try:
            scripts = with_events(H, "probe-a1", (11, "subagent-dup", 1_000_000))
            got, code, text, world = run_case(tmp, dict(scripts=scripts), "a1", [])
            m = re.search(r"(\d+) requests, ([\d,]+) processed tokens", text)
            want_tokens = 50_000 + 60_000 + 1_000_000
            if m and int(m.group(2).replace(",", "")) == want_tokens and int(m.group(1)) == 3:
                passed += 1
            else:
                failed += 1
                print("FAIL  meter-counts-a-request-in-two-transcripts-once")
                print(f"        wanted 3 requests, {want_tokens:,} tokens; got {m.groups() if m else text[-300:]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        for n, f in saved.items():
            setattr(probe, n, f)

    # The state file is shared. A record written to it DURING a run -- by a
    # person repairing it, or by another run -- must survive that run's own
    # save. A run that writes back the copy it loaded at the start erases it,
    # and with it that session's spend from the ceiling. MEASURED 2026-09-23.
    extra_cases += 1
    saved2 = {n: getattr(probe, n) for n in SEAMS}
    tmp = tempfile.mkdtemp(prefix="bgprobe-")
    try:
        scripts = with_events(H, "probe-a1", (7, "state-edit"))
        run_case(tmp, dict(scripts=scripts), "a1", [])
        d = json.load(open(os.path.join(tmp, "state.json")))
        if d["sessions"].get("repaired", {}).get("sessionId") == "repaired-by-hand":
            passed += 1
        else:
            failed += 1
            print("FAIL  a-record-written-during-a-run-survives-its-save")
            print(f"        sessions after the run: {sorted(d['sessions'])}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for n, f in saved2.items():
            setattr(probe, n, f)

    # --- the join: the real script against a fake `claude` on PATH ----------
    # 0.3.0's planted case, kept: a CLI that LISTS --bg and REFUSES it. Then
    # the refusal 2026-09-23 actually met, which is a precondition and not the
    # capability's absence. Neither starts anything or spends anything.
    for name, refusal, want_kind, want_exit in (
            ("planted-fake-refuses-bg", "error: unknown option '--bg'", "no-bg", 1),
            ("planted-fake-untrusted", "Workspace not trusted. Run `claude` in X once and "
                                       "accept the trust prompt, then retry.", "untrusted", 2)):
        extra_cases += 1
        tmp = tempfile.mkdtemp(prefix="bgprobe-")
        try:
            fake = os.path.join(tmp, "bin", "claude")
            os.makedirs(os.path.dirname(fake))
            with open(fake, "w") as fh:
                fh.write("#!/bin/sh\n"
                         "for a in \"$@\"; do case \"$a\" in --bg) echo \"" + refusal.replace("`", "\\`")
                         + "\" >&2; exit 1;; esac; done\n"
                         "case \"$1\" in --version) echo '2.1.0 (fake)';; "
                         "--help) echo '  --bg, --background  Start in the background';; "
                         "agents) echo '[]';; *) exit 2;; esac\n")
            os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
            env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
            env["PATH"] = os.path.dirname(fake) + ":/usr/bin:/bin"
            proc = subprocess.run([sys.executable, os.path.join(HERE, "bg_session_probe.py"),
                                   "--workdir", os.path.join(tmp, "bg"), "--ceiling", "1000"],
                                  capture_output=True, text=True, env=env, timeout=60)
            if proc.returncode == want_exit and re.search(rf"^\s+{want_kind}\s", proc.stdout, re.M) \
                    and "0 processed tokens" in proc.stdout:
                passed += 1
            else:
                failed += 1
                print(f"FAIL  {name}: exit {proc.returncode}")
                print(f"        | {(proc.stdout + proc.stderr).strip()[-400:]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    total = len(CASES) + extra_cases
    fp = sum(1 for c in CASES if c[0].startswith("fp-") or c[0] == "healthy")
    print(f"\nbg_session_probe control: {passed} passed, {failed} failed, "
          f"{total} cases ({fp} of them false-positive controls, {100 * fp // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
