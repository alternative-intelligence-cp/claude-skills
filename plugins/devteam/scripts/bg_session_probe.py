#!/usr/bin/env python3
"""Can a session start, message and replace another, with nobody at the keyboard?

Cycle 0.3 decides its liaison layer on this probe (the cycle README's L-2), and
0.2's L-8 rests on the premise that a session cannot spawn its own interactive
successor. CLI 2.1.281 has `claude --bg`, which starts a session in the
background and prints an id that `claude attach`, `logs`, `stop` and `rm`
take. Whether that is enough to rotate a project manager with nobody at the
keyboard cannot be read off `--help`; it is found out by doing it. So each
question is a step that starts a real background session in a scratch git
repository, gives it one small job whose result is a FILE ON DISK, and reads
the file -- a result on disk rather than in anybody's context.

  a1  start       a background session starts, is listed, does its job, and
                  can see the devteam plugin's skills
  a1b in place    a session told not to isolate writes a file where it was
                  started, once with the Write tool and once from its shell.
                  MEASURED 2026-09-23 on 2.1.281: a background session's system
                  prompt says file edits in the shared checkout "are rejected
                  until you isolate" with EnterWorktree -- and a manager's job
                  is writing devteam/ in exactly that checkout
  a2  depth/wake  it dispatches a subagent that dispatches another, and a
                  background shell command's completion wakes it from idle --
                  the manager's loop in miniature
  a3  succession  a session starts a second one with `claude --bg`, messages
                  it, is answered, and stops itself -- the probe's centre
  a4  the client  observe only: a session that asks the user a question, for
                  a human to attach to and answer. Not part of the verdict
  a5  permission  observe only: a session asked to run a command it was never
                  granted, under `--permission-mode manual`

Findings. The first group means no background manager at all:

  no-cli          `claude` is not on PATH
  no-bg           the CLI does not offer --bg, or refuses it when run
  no-listing      `claude agents --json` is missing or does not parse, and
                  nothing below can be observed without it
  not-listed      a session was started and never appeared in the listing
  no-work         a session never wrote its result file inside the timeout
  no-plugin       a background session sees no `devteam:` skill, so it could
                  not run /devteam:resume
  no-subagent     a2's subagent wrote nothing
  no-depth2       a2's subagent could not dispatch one of its own
  no-wake         a2's background command finished and nothing ever acted on it

These mean a session can start its successor but not hand over to it:

  no-spawn        a3's starter never started its target
  no-message      the target never received the starter's message
  no-reply        the starter never wrote the target's reply
  wake-unobserved a2's result file exists, but its transcript does not show
                  the turn ENDING after the background launch and a
                  task-notification ARRIVING after that -- the session may
                  have slept or polled, so waking is not established. Read
                  from the transcript, not the listing: MEASURED 2026-09-23,
                  a session whose turn has ended with a background task
                  pending is listed `busy` until the task finishes

This one means the probe could not ask its question at all:

  untrusted       the CLI refused to start a background session because the
                  directory was never trusted. MEASURED 2026-09-23 on 2.1.281:
                  `--bg` refuses where `-p` skips the dialog, and no command
                  grants trust -- a human runs `claude` there once and accepts
                  the prompt. Not the capability's absence: a precondition

And these are noted, not blockers:

  worktree        a git worktree appeared, so a session's files are not where
                  its starter looks unless it reads the listing's cwd. On 2.1.281
                  the session makes it itself, with EnterWorktree, as its system
                  prompt tells a background session to before any edit
  in-place-refused a1b's Write in the starting checkout was refused -- the
                  isolation rule is enforced, not merely advised
  blocked         a session sat waiting on a permission prompt; only the
                  listing shows it, and nobody is told
  no-self-stop    a3's starter was still running after its last step; the
                  probe stops it
  ceiling         the spend ceiling was reached and every probe session was
                  stopped; nothing after that point was measured

Exit 0 a1 to a3 hold: a successor can be started and handed over to by message
(0.3.0 §4's first branch). 1 a1 or a2 failed: no background manager. 2 a1 and
a2 held and a3 did not, or a step could not be decided, or not all of a1 to
a3 ran, or the workspace is untrusted. 3 stopped at the ceiling.

**Every probe session spends real tokens on the account that runs it.** So the
probe meters its own sessions from their transcripts as it goes -- every
request, subagents included, one row per request id across all of them -- and
stops them all at `--ceiling` processed tokens rather than spending through it
(0.3.0's L-0.4). There is no default: whoever runs it states the number.

Sessions are started with every `CLAUDE*` variable removed from the
environment, as a user's own shell would start them -- so a1 and a2 ask
whether a background session works at all. a3 asks the nested question, a
session starting a session, on purpose: its starter runs `claude --bg` from
inside its own shell, with its own environment.

The seams -- `run`, `read`, `mtime`, `which`, `clock`, `pause` and
`transcripts` -- exist so that the control can plant each fault without
starting anything or spending anything.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import session_cost  # noqa: E402  -- one per-request dedupe in the plugin, not two

HOME = os.path.expanduser("~")


def launch_env():
    """This environment minus everything the harness sets for its children."""
    return {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}


# --- the seams -----------------------------------------------------------


def run(argv, timeout=60, cwd=None):
    """Run a command. Returns (returncode, stdout, stderr, the command)."""
    printable = " ".join(shlex.quote(a) for a in argv)
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           cwd=cwd, env=launch_env())
        return p.returncode, p.stdout, p.stderr, printable
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s", printable
    except OSError as exc:
        return 127, "", str(exc), printable


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def which(name):
    return shutil.which(name, path=launch_env().get("PATH"))


def clock():
    return time.time()


def pause(seconds):
    time.sleep(seconds)


def transcripts(session_id):
    """Every transcript a session wrote: its own, then its subagents'.

    Found by globbing every project directory rather than by computing the
    directory's name, because the harness turns `.` into `-` as well as `/`
    and `session_cost.py`'s lookup does not (cycle 0.3 README §4.8) -- and
    these sessions run under `.internal/`.
    """
    root = os.path.join(HOME, ".claude", "projects")
    own = glob.glob(os.path.join(root, "*", f"{session_id}.jsonl"))
    subs = glob.glob(os.path.join(root, "*", session_id, "subagents", "*.jsonl"))
    return sorted(own) + sorted(subs)


# --- what the sessions are asked to do -------------------------------------
# Every prompt reserves git for the user. Without that, a background session
# commits whatever it wrote -- its system prompt says to, "you don't need to
# ask", and to push if there is a remote -- and a commit is a shell command
# that acceptEdits does not grant, so it stalls on a permission prompt nobody
# sees. MEASURED 2026-09-23: probe-a1's first run did exactly that.

GIT = " Git is reserved for the user: do not run git, commit or push."

A1 = ("Write the word ready to a1.txt, then list every skill you can invoke whose "
      "name begins devteam: into a1-skills.txt, and stop." + GIT)

A1B = ("You are probe-a1b, a test session. Do NOT use the EnterWorktree tool: work in "
       "the directory you started in. (1) Use the Write tool to write the word inplace "
       "to a1b.txt in the current directory. (2) Run the shell command  printf bash > "
       "a1b-bash.txt  with the Bash tool. (3) Write nothing else. In your final message, "
       "quote verbatim any error either step returned. Then end your turn." + GIT)

A2 = ("You are probe-a2, a test session in a scratch directory. Do these steps in "
      "order, then end your turn.\n"
      "(a) Use the Agent tool to dispatch one general-purpose subagent with exactly "
      "these instructions: 'Write the file a2-depth1.txt in the current directory "
      "containing the line depth 1. Then use the Agent tool to dispatch one "
      "general-purpose subagent with exactly these instructions: Write the file "
      "a2-depth2.txt in the current directory containing the line depth 2.' "
      "Wait for it to finish.\n"
      "(b) Run the shell command  sleep 60 && date +%s  with the Bash tool, with "
      "run_in_background set to true.\n"
      "(c) Do not wait for it, poll it or sleep: end your turn now. When the notice "
      "that the background command finished reaches you, write the command's "
      "output, exactly as printed, to a2-woke.txt, and end your turn again." + GIT)

A3T = ("You are probe-a3t, a test session. End your turn now. Later a message from "
       "the session probe-a3s will arrive. When it does, answer it with the "
       "SendMessage tool, addressed to probe-a3s, with the text: pong from "
       "probe-a3t. Then end your turn. Do nothing else.")

A3S = ("You are probe-a3s, a test session in a scratch directory. Work in the current "
       "directory. Do exactly these steps, in order, and nothing else.\n"
       "Write every file below with the Write tool, never with a shell redirect or "
       "tee.\n"
       "1. Run this shell command exactly -- it starts from the directory you were "
       "started in, which is trusted -- then write everything it printed to "
       "a3-start.txt:\n"
       "   cd {workdir} && claude --bg --name probe-a3t --model {model} --permission-mode acceptEdits "
       "'" + A3T + "'\n"
       "2. Use the ListAgents tool, and write everything it returns to a3-list.txt.\n"
       "3. Use the SendMessage tool (load it with ToolSearch first if it is not "
       "loaded) to send probe-a3t the message: ping from probe-a3s. Then run  date +%s  "
       "and write its output to a3-sent.txt.\n"
       "4. End your turn. Do not poll, sleep or check for a reply. When probe-a3t's "
       "reply reaches you, write it verbatim to a3.txt.\n"
       "5. Then stop yourself: run  claude agents --json , find the entry whose name "
       "is probe-a3s, write into a3-stop.txt the exact stop command you are about "
       "to run, and run  claude stop <id>  with that entry's id." + GIT)

A4 = ("You are probe-a4, a test session. If you have a tool that sends the user a "
      "push notification, first use it to say that probe-a4 has a question waiting. "
      "Then use the AskUserQuestion tool to ask the user one question -- probe-a4: "
      "red or blue? -- with the two options red and blue. When the answer comes "
      "back, write it to a4.txt and end your turn." + GIT)

A5 = ("You are probe-a5, a test session. Run the shell command  date +%s  with the "
      "Bash tool and write its output to a5.txt. Then end your turn." + GIT)

# Status values the listing has been seen to use for a session mid-turn. Any
# other value -- including one nobody has seen yet -- counts as settled, and is
# recorded verbatim either way.
WORKING = {"busy", "running", "starting", "working", "thinking"}
GONE = {"absent", "stopped", "exited", "completed", "done", "killed", "dead"}

BLOCKS_A1_A2 = {"no-cli", "no-bg", "no-listing", "not-listed", "no-work",
                "no-plugin", "no-subagent", "no-depth2", "no-wake"}
BLOCKS_A3 = {"no-spawn", "no-message", "no-reply"}
UNDECIDED = {"wake-unobserved", "untrusted", "a1b-undecided"}


class Ceiling(Exception):
    pass


class Session:
    def __init__(self, name, step):
        self.name, self.step = name, step
        self.printed = ""          # everything `claude --bg` printed
        self.handle = None         # the id `stop`, `logs` and `rm` take
        self.entry = None          # the latest listing entry
        self.first = None          # the first listing entry seen
        self.cwds = []             # every cwd the listing ever gave it: a
                                   # stopped session is listed at the checkout
                                   # it started in, not the worktree it wrote in
        self.statuses = []         # [(seconds since the probe began, status)]
        self.since = clock()       # it cannot have been listed before this

    def status(self):
        return self.statuses[-1][1] if self.statuses else "absent"


def describe(entry):
    """One status word per listing read. A background entry carries `state`
    (working, blocked, stopped) and, while its turn runs or waits, `status`
    (busy, waiting) with `waitingFor` -- an interactive one only `status`. The
    first read of a new session has `state` alone. MEASURED 2026-09-23."""
    if not entry:
        return "absent"
    word = str(entry.get("status") or entry.get("state") or "unknown")
    return f"{word}({entry['waitingFor']})" if entry.get("waitingFor") else word


def base(status):
    return status.split("(", 1)[0]


def stamp(text):
    try:
        return dt.datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def turns(path):
    """[(kind, epoch, detail)] from one transcript, in file order: `launch` for
    a Bash call run in the background, `end` for an assistant message that
    ended its turn, `notice` for a task-notification delivered as the user's
    message -- which is how a finished background task starts a new turn."""
    out = []
    for line in (read(path) or "").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        when = stamp(e.get("timestamp"))
        m = e.get("message")
        if when is None or not isinstance(m, dict):
            continue
        if e.get("type") == "assistant":
            for b in m.get("content") or []:
                if (b.get("type") == "tool_use" and b.get("name") == "Bash"
                        and (b.get("input") or {}).get("run_in_background")):
                    out.append(("launch", when, (b.get("input") or {}).get("command", "")))
            if m.get("stop_reason") == "end_turn":
                out.append(("end", when, ""))
        elif e.get("type") == "user":
            c = m.get("content")
            if isinstance(c, str) and c.lstrip().startswith("<task-notification>"):
                out.append(("notice", when, c[:200]))
    return out


def printed_id(text):
    """The id `claude --bg` printed, or None. Its format is not documented, so
    the command it suggests is preferred to any guess about the id's shape."""
    m = re.search(r"claude (?:attach|logs|stop|kill|rm) ([^\s`'\"]+)", text)
    if m:
        return m.group(1)
    m = re.search(r"\bid[:=\s]+([^\s`'\",]+)", text, re.I)
    if m:
        return m.group(1)
    words = text.split()
    return words[0] if len(words) == 1 else None


ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class Probe:
    def __init__(self, workdir, model, ceiling, state_path, poll=5, timeouts=None,
                 observe=120):
        self.workdir, self.model, self.ceiling = workdir, model, ceiling
        self.state_path, self.poll, self.observe_secs = state_path, poll, observe
        self.timeouts = {"a1": 300, "a2": 420, "a3": 600}
        self.timeouts.update(timeouts or {})
        self.sessions = {}
        self.rows, self.findings = [], []
        self.spent = 0
        self.t0 = self.step_began = clock()
        self.state = {"sessions": {}}
        text = read(state_path) if state_path else None
        if text:
            self.state = json.loads(text)

    # --- bookkeeping --------------------------------------------------------

    def row(self, step, name, value, cmd=""):
        self.rows.append((step, name, str(value), cmd))

    def finding(self, kind, step, detail):
        self.findings.append((kind, step, detail))

    def save(self):
        """Write this run's sessions into the state file, keyed by id.

        Keyed by the session's own id, never by its name: a re-run reuses the
        names, and a record overwritten by name drops the earlier session's
        spend out of the ceiling. And MERGED, not rewritten: every other record
        is taken from the file as it is NOW, not as this run loaded it. Two
        runs -- or a run and a person repairing the file -- would otherwise
        each write back the copy they started with, and the later write would
        silently erase the other's records. MEASURED 2026-09-23: a repair made
        during a run was undone when that run saved."""
        if not self.state_path:
            return
        text = read(self.state_path)
        disk = json.loads(text).get("sessions", {}) if text else {}
        for s in self.sessions.values():
            if not s.handle and (s.entry or s.first):
                s.handle = (s.entry or s.first).get("id")
            key = s.handle or f"{s.name}@unlisted"
            if s.handle:
                # A session some other session started is saved under a
                # placeholder until it is listed; once it has an id, the
                # placeholder is dropped, or cleanup would chase a ghost.
                disk.pop(f"{s.name}@unlisted", None)
            rec = disk.setdefault(key, {})
            rec.update({"name": s.name, "step": s.step, "handle": s.handle,
                        "sessionId": (s.entry or s.first or {}).get("sessionId") or rec.get("sessionId"),
                        "cwd": (s.entry or {}).get("cwd") or rec.get("cwd")})
        self.state["sessions"] = disk
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(self.state, fh, indent=2)
        os.replace(tmp, self.state_path)

    def session_ids(self):
        ids = {r.get("sessionId") for r in self.state["sessions"].values()}
        ids |= {(s.entry or {}).get("sessionId") for s in self.sessions.values()}
        return sorted(i for i in ids if i)

    # --- the meter and the stop ---------------------------------------------

    def meter(self, ids=None):
        """(processed tokens, requests, {model: counter}) over every transcript
        of the sessions named -- by default every session this probe has ever
        started, in any run -- with one row per request id across all files."""
        per = {}
        for sid in (self.session_ids() if ids is None else ids):
            for path in transcripts(sid):
                rows, _, _ = session_cost.read(path)
                for rid, value in rows.items():
                    per.setdefault(rid, value)
        overall, by_model = session_cost.totals(per)
        return session_cost.processed(overall), overall["requests"], by_model

    def check_ceiling(self):
        self.spent, _, _ = self.meter()
        if self.spent >= self.ceiling:
            self.stop_all()
            raise Ceiling(self.spent)

    def stop_all(self):
        # A session never seen in the listing is still stopped if it printed a
        # handle: not being listed is no evidence that it is not running.
        for s in self.sessions.values():
            handle = s.handle or (s.entry or {}).get("sessionId")
            if handle and base(s.status()) not in GONE - {"absent"}:
                rc, out, err, cmd = run(["claude", "stop", handle], timeout=60)
                self.row(s.step, f"{s.name} stopped", f"exit {rc} {(out + err).strip()[:120]}", cmd)

    # --- starting and watching ----------------------------------------------

    def start(self, step, name, prompt, mode="acceptEdits", allowed=()):
        argv = ["claude", "--bg"]
        if allowed:
            # One argument per rule, the form the CLI documents: its help
            # calls the list "comma or space-separated", and a rule such as
            # `Bash(claude --bg:*)` has a space inside it.
            argv += ["--allowedTools", *allowed]
        argv += ["--name", name, "--model", self.model, "--permission-mode", mode, prompt]
        self.step_began = clock()
        rc, out, err, cmd = run(argv, timeout=120, cwd=self.workdir)
        s = Session(name, step)
        s.printed = (out + "\n" + err).strip()
        self.sessions[name] = s
        shown = cmd if len(cmd) < 160 else cmd[:150] + " ...'"
        self.row(step, f"{name} start", f"exit {rc}: {s.printed[:400]}", shown)
        if rc != 0:
            return None
        s.handle = printed_id(s.printed)
        self.save()
        return s

    def refused(self, step):
        """File the finding for a `--bg` that exited non-zero. An untrusted
        workspace is a precondition the probe can name the remedy for; anything
        else is the capability refusing."""
        said = self.rows[-1][2]
        if "not trusted" in said.lower():
            self.finding("untrusted", step, f"{said} -- run `claude` in {self.workdir} "
                         "once, accept the trust prompt, exit, and re-run the probe")
        else:
            self.finding("no-bg", step, "`claude --bg` exited non-zero: " + said)

    def listing(self):
        rc, out, err, cmd = run(["claude", "agents", "--json", "--all"], timeout=30)
        if rc != 0:
            return None, f"exit {rc}: {(err or out).strip()[:200]}"
        try:
            data = json.loads(out)
        except ValueError:
            return None, f"not JSON: {out.strip()[:200]}"
        if not isinstance(data, list):
            return None, f"not a list: {type(data).__name__}"
        return data, None

    def match(self, s, data):
        """The listing entry for a session: by the id it printed if it has
        one, otherwise by name among entries started since it could exist.
        A name alone is not enough -- an earlier run's session of the same
        name, stopped and still listed, would stand in for one that never
        started, and a failed spawn would pass."""
        if s.handle:
            exact = [e for e in data if e.get("id") == s.handle
                     or str(e.get("sessionId", "")).startswith(s.handle)]
            if exact:
                return exact[0]
        named = [e for e in data if e.get("name") == s.name
                 and (e.get("startedAt") or 0) / 1000 >= s.since - 5]
        return max(named, key=lambda e: e.get("startedAt") or 0) if named else None

    def observe(self, names):
        data, why = self.listing()
        if data is None:
            self.row("-", "listing unreadable", why)
            return
        now = round(clock() - self.t0)
        for name in names:
            s = self.sessions.get(name)
            if s is None:                  # a session some other session started
                s = self.sessions[name] = Session(name, "a3")
                s.since = self.step_began
            entry = self.match(s, data)
            status = describe(entry)
            if not s.statuses or s.statuses[-1][1] != status:
                s.statuses.append((now, status))
            if entry:
                s.entry = entry
                if s.first is None:
                    s.first = dict(entry)
                if entry.get("cwd") and entry["cwd"] not in s.cwds:
                    s.cwds.append(entry["cwd"])
        self.save()

    def watch(self, names, done, timeout):
        """Poll until done() or the timeout. The ceiling is read on every poll."""
        deadline = clock() + timeout
        while True:
            self.observe(names)
            self.check_ceiling()
            if done():
                return True
            if clock() >= deadline:
                return False
            pause(self.poll)

    def dirs(self, s):
        """Where a session's files may be: the cwd the listing gives it first,
        because `--bg` may have put it in a worktree, then the probe's own."""
        out = []
        for d in list(reversed(s.cwds)) + [self.workdir]:
            if d and d not in out:
                out.append(d)
        return out

    def result(self, s, fname):
        for d in self.dirs(s):
            path = os.path.join(d, fname)
            text = read(path)
            if text is not None:
                return text, path
        return None, None

    def settled(self, s):
        return base(s.status()) not in WORKING and s.status() != "absent"

    def tail_logs(self, s):
        handle = s.handle or (s.entry or {}).get("sessionId")
        if not handle:
            return
        rc, out, err, cmd = run(["claude", "logs", handle], timeout=30)
        lines = [ANSI.sub("", l).rstrip() for l in (out + err).splitlines()]
        lines = [l for l in lines if l.strip()][-12:]
        self.row(s.step, f"{s.name} logs (last lines)", " | ".join(lines)[:900], cmd)

    def statuses_row(self, s):
        seq = ", ".join(f"{st}@{t}s" for t, st in s.statuses) or "never listed"
        self.row(s.step, f"{s.name} statuses", seq)
        if s.cwds:
            self.row(s.step, f"{s.name} cwds", " -> ".join(s.cwds))
        if any("permission" in st for _, st in s.statuses):
            self.finding("blocked", s.step, f"{s.name} waited on a permission prompt: {seq}")

    # --- the steps ------------------------------------------------------------

    def worktrees(self):
        rc, out, err, cmd = run(["git", "-C", self.workdir, "worktree", "list", "--porcelain"])
        return [l.split(" ", 1)[1] for l in out.splitlines() if l.startswith("worktree ")], cmd

    def step_a1(self):
        before, _ = self.worktrees()
        s = self.start("a1", "probe-a1", A1)
        if s is None:
            self.refused("a1")
            return
        self.watch([s.name], lambda: (self.result(s, "a1-skills.txt")[0] is not None
                                      and self.settled(s)), self.timeouts["a1"])
        self.row("a1", "printed id", s.handle or "none found in: " + s.printed[:200])
        self.row("a1", "listing entry, first seen", json.dumps(s.first) if s.first else "never")
        self.row("a1", "listing entry, last seen", json.dumps(s.entry) if s.entry else "never")
        self.statuses_row(s)
        if s.first is None:
            self.finding("not-listed", "a1", f"{s.name} never appeared in `claude agents --json --all`")
        ready, path = self.result(s, "a1.txt")
        self.row("a1", "a1.txt", f"{ready.strip()!r} at {path}" if ready is not None else "absent")
        if ready is None or "ready" not in ready:
            self.finding("no-work", "a1", "a1.txt was never written with the word ready")
        skills, path = self.result(s, "a1-skills.txt")
        found = sorted(set(re.findall(r"devteam:[a-z-]+", skills or "")))
        self.row("a1", "devteam skills a background session sees",
                 f"{len(found)}: {', '.join(found)}" if found else f"none ({'no file' if skills is None else 'file lists none'})")
        if skills is not None and not found:
            self.finding("no-plugin", "a1", "a1-skills.txt names no devteam: skill")
        self.tail_logs(s)
        trees, cmd = self.worktrees()
        new = [t for t in trees if t not in before]
        self.row("a1", "git worktrees", f"{len(trees)}, of which new in this step: "
                 f"{', '.join(new) or 'none'}", cmd)
        if new:
            self.finding("worktree", "a1", f"a worktree appeared: {', '.join(new)}")

    def step_a1b(self):
        s = self.start("a1b", "probe-a1b", A1B, allowed=("Bash(printf:*)",))
        if s is None:
            self.refused("a1b")
            return
        self.watch([s.name], lambda: self.settled(s) and len(s.statuses) > 1,
                   self.timeouts["a1"])
        self.statuses_row(s)
        for fname, how in (("a1b.txt", "the Write tool"), ("a1b-bash.txt", "the shell")):
            path = os.path.join(self.workdir, fname)
            text = read(path)
            self.row("a1b", f"{fname} in the starting checkout ({how})",
                     repr(text.strip()) if text is not None else "absent")
        isolated = [d for d in s.cwds if "/.claude/worktrees/" in d]
        if isolated:
            # It isolated despite being told not to, so the in-place question
            # was never put to the harness -- not an answer either way.
            self.row("a1b", "entered a worktree anyway", ", ".join(isolated))
            self.finding("a1b-undecided", "a1b",
                         "the session entered a worktree despite the instruction")
        elif read(os.path.join(self.workdir, "a1b.txt")) is None:
            self.finding("in-place-refused", "a1b", "the Write tool did not write in the "
                         "checkout the session started in")
        sid = (s.entry or s.first or {}).get("sessionId")
        said = ""
        for path in transcripts(sid) if sid else []:
            for line in (read(path) or "").splitlines():
                if '"tool_result"' in line and ("rejected" in line or "isolat" in line or "EnterWorktree" in line):
                    said = line
        m = re.search(r'"content":\s*"([^"]{0,400})', said)
        self.row("a1b", "what the refusal said", m.group(1) if m else (said[:400] or "no refusal in the transcript"))

    def step_a2(self):
        s = self.start("a2", "probe-a2", A2, allowed=("Bash(sleep:*)", "Bash(date:*)"))
        if s is None:
            self.refused("a2")
            return
        self.watch([s.name], lambda: self.result(s, "a2-woke.txt")[0] is not None,
                   self.timeouts["a2"])
        self.statuses_row(s)
        if s.first is None:
            self.finding("not-listed", "a2", f"{s.name} never appeared in the listing")
        for n in (1, 2):
            text, path = self.result(s, f"a2-depth{n}.txt")
            when = mtime(path) if path else None
            self.row("a2", f"a2-depth{n}.txt",
                     f"{text.strip()!r} at +{round(when - self.t0)}s" if text is not None else "absent")
            if text is None:
                self.finding("no-subagent" if n == 1 else "no-depth2", "a2",
                             f"a2-depth{n}.txt was never written")
        woke, path = self.result(s, "a2-woke.txt")
        if woke is None:
            self.finding("no-wake", "a2", "a2-woke.txt was never written; the background "
                         "command's completion was not acted on inside the timeout")
            return
        t_woke = mtime(path)
        m = re.search(r"\d{9,}", woke)
        gap = round(t_woke - int(m.group(0))) if (m and t_woke) else None
        self.row("a2", "a2-woke.txt", f"{woke.strip()!r}; written {gap}s after the command "
                 "finished" if gap is not None else f"{woke.strip()!r}; finish time unreadable")
        # Woken means, in the session's own transcript: the background launch,
        # then its turn ENDING, then a task-notification ARRIVING, then the
        # file. Anything short of that may be a session that slept or polled,
        # which would pass a test that only looked for the file. The order
        # matters: the measured session ended a turn BEFORE the launch too,
        # waiting on its subagents, and that turn end proves nothing here.
        sid = (s.entry or s.first or {}).get("sessionId")
        own = [pth for pth in (transcripts(sid) if sid else []) if "/subagents/" not in pth]
        marks = turns(own[0]) if own else []
        launch = next((t for k, t, d in marks if k == "launch" and "sleep" in d), None)
        ended = next((t for k, t, _ in marks if k == "end" and launch is not None and t >= launch), None)
        notice = next((t for k, t, _ in marks if k == "notice" and ended is not None and t >= ended), None)
        if None in (launch, ended, notice) or (t_woke is not None and t_woke + 1 < notice):
            self.finding("wake-unobserved", "a2", "the transcript does not show launch, then a turn "
                         f"end, then a task-notification, then the file (launch {launch}, end "
                         f"{ended}, notice {notice}, file {t_woke})")
        else:
            self.row("a2", "the wake, from the transcript",
                     f"the turn ended {ended - launch:.0f}s after the launch; the notice came "
                     f"{notice - ended:.0f}s later; the file {t_woke - notice:.0f}s after that")

    def step_a3(self):
        # The target is started from the trusted checkout, not from the
        # starter's worktree: a worktree is a path nobody has trusted, and a
        # refusal on that ground would answer a different question. A manager
        # starting its successor starts it at the project's root.
        # The grant names the three `claude` subcommands the starter needs,
        # not `claude:*`: a starter that picked the wrong id could otherwise
        # stop somebody else's session. `tee` is there because a starter once
        # piped the launch through it (MEASURED 2026-09-23) and a command
        # nobody granted blocks a background session with nobody told.
        s = self.start("a3", "probe-a3s", A3S.format(model=self.model, workdir=self.workdir),
                       allowed=("Bash(claude --bg:*)", "Bash(claude agents:*)", "Bash(claude stop:*)",
                                "Bash(cd:*)", "Bash(date:*)", "Bash(tee:*)"))
        if s is None:
            self.refused("a3")
            return
        names = [s.name, "probe-a3t"]
        self.watch(names, lambda: (self.result(s, "a3.txt")[0] is not None
                                   and base(s.status()) in GONE | {"idle"}), self.timeouts["a3"])
        # Give the starter a minute to carry out its own stop, which comes
        # after a3.txt.
        self.watch(names, lambda: base(s.status()) in GONE, 60)
        t = self.sessions["probe-a3t"]
        for x in (s, t):
            self.statuses_row(x)
        if t.first is None:
            self.finding("no-spawn", "a3", "probe-a3t never appeared in the listing")
        for fname in ("a3-start.txt", "a3-list.txt", "a3-sent.txt", "a3-stop.txt"):
            text, _ = self.result(s, fname)
            self.row("a3", fname, " | ".join((text or "absent").strip().splitlines())[:400])
        listed, _ = self.result(s, "a3-list.txt")
        self.row("a3", "the starter could see its target",
                 "yes" if listed and "probe-a3t" in listed else "no")
        target_ids = [(t.entry or t.first or {}).get("sessionId")] if (t.entry or t.first) else []
        heard = any("ping from probe-a3s" in (read(p) or "")
                    for sid in target_ids if sid for p in transcripts(sid))
        self.row("a3", "the target's transcript holds the message", "yes" if heard else "no")
        if t.first is not None and not heard:
            self.finding("no-message", "a3", "probe-a3t's transcript never shows the ping")
        reply, path = self.result(s, "a3.txt")
        sent, _ = self.result(s, "a3-sent.txt")
        m = re.search(r"\d{9,}", sent or "")
        rtt = round(mtime(path) - int(m.group(0))) if (reply is not None and m and mtime(path)) else None
        self.row("a3", "a3.txt", f"{reply.strip()!r}" + (f"; {rtt}s after the ping was sent" if rtt is not None else "")
                 if reply is not None else "absent")
        if reply is None or "pong" not in reply:
            self.finding("no-reply", "a3", "a3.txt never held probe-a3t's reply")
        if base(s.status()) not in GONE:
            self.finding("no-self-stop", "a3", f"probe-a3s is still {s.status()!r} after its last step")
        # A6: what a rotation cost the starter -- the backlog's liaison tokens
        # per rotation, measured once.
        sid = (s.entry or s.first or {}).get("sessionId")
        if sid:
            tokens, reqs, _ = self.meter([sid])
            self.row("a3", "a6: the starter's own spend", f"{reqs} requests, {tokens:,} processed tokens")

    def step_observe(self, step, prompt, mode="acceptEdits", stop=True):
        s = self.start(step, f"probe-{step}", prompt, mode=mode)
        if s is None:
            self.refused(step)
            return
        self.watch([s.name], lambda: False, self.observe_secs)
        self.statuses_row(s)
        self.tail_logs(s)
        handle = s.handle or (s.entry or {}).get("sessionId")
        self.row(step, "to answer it by hand", f"claude attach {handle}")
        for fname in (f"{step}.txt",):
            text, path = self.result(s, fname)
            self.row(step, fname, f"{text.strip()!r}" if text is not None else "absent")
        if stop:
            self.stop_all()

    # --- cleanup ----------------------------------------------------------------

    def cleanup(self, keep_dir):
        """Copy every probe session's transcripts somewhere that outlives `rm`,
        stop and remove each session, then read the listing to show none is
        left -- and whether `rm` took the transcripts with it."""
        os.makedirs(keep_dir, exist_ok=True)
        originals = []
        for key, rec in sorted(self.state["sessions"].items()):
            name = rec.get("name", key)
            sid, handle = rec.get("sessionId"), rec.get("handle") or rec.get("sessionId")
            for path in transcripts(sid) if sid else []:
                rel = os.path.relpath(path, os.path.join(HOME, ".claude", "projects"))
                dest = os.path.join(keep_dir, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(path, dest)
                originals.append(path)
            if handle:
                for verb in ("stop", "rm"):
                    rc, out, err, cmd = run(["claude", verb, handle], timeout=60)
                    self.row("cleanup", f"{name} {verb}", f"exit {rc} {(out + err).strip()[:160]}", cmd)
        data, why = self.listing()
        left = sorted({e.get("name") for e in (data or []) if str(e.get("name", "")).startswith("probe-a")})
        self.row("cleanup", "probe sessions still listed (--all)",
                 ", ".join(left) if left else ("none" if data is not None else f"unknown: {why}"))
        gone = [p for p in originals if read(p) is None]
        self.row("cleanup", "transcripts kept", f"{len(originals)} copied to {keep_dir}; "
                 f"{len(gone)} of the originals no longer exist after rm")

    # --- the verdict --------------------------------------------------------------

    def verdict(self, ran):
        kinds = {k for k, _, _ in self.findings}
        if "ceiling" in kinds:
            return 3, "stopped at the ceiling -- undecided"
        if kinds & BLOCKS_A1_A2:
            return 1, "no background manager -- a1 or a2 failed"
        if kinds & BLOCKS_A3:
            return 2, "a session can start its successor but not hand over to it by message"
        if "untrusted" in kinds:
            return 2, "undecided -- the workspace is not trusted, so nothing was asked"
        if kinds & UNDECIDED:
            return 2, "undecided -- a step could not be decided"
        if not {"a1", "a2", "a3"} <= set(ran):
            return 2, f"partial -- ran {', '.join(ran)}; the verdict needs a1, a2 and a3"
        return 0, "a successor can be started and handed over to by message"


def preflight(p):
    """The checks that cost nothing. Returns False if the probe cannot go on."""
    path = which("claude")
    if not path:
        p.finding("no-cli", "a1", "`claude` is not on PATH")
        return False
    rc, out, err, cmd = run(["claude", "--version"])
    p.row("-", "claude CLI", f"{(out or err).strip()} ({path})", cmd)
    rc, out, err, cmd = run(["claude", "--help"])
    has_bg = re.search(r"(^|\s)--bg\b|--background\b", out + err) is not None
    p.row("-", "--bg in --help", "listed" if has_bg else "not listed", cmd)
    if not has_bg:
        p.finding("no-bg", "a1", "`claude --help` does not list --bg")
        return False
    data, why = p.listing()
    p.row("-", "claude agents --json --all", f"{len(data)} sessions" if data is not None else why,
          "claude agents --json --all")
    if data is None:
        p.finding("no-listing", "a1", why)
        return False
    return True


def ensure_repo(workdir):
    """The scratch repository the sessions work in: one commit, nothing else."""
    if os.path.isdir(os.path.join(workdir, ".git")):
        return
    os.makedirs(workdir, exist_ok=True)
    with open(os.path.join(workdir, "README.md"), "w") as fh:
        fh.write("Scratch repository for bg_session_probe.py. Disposable.\n")
    ident = ["-c", "user.name=bg-probe", "-c", "user.email=bg-probe@localhost"]
    for argv in (["git", "init", "-q"], ["git", "add", "README.md"],
                 ["git", *ident, "commit", "-q", "-m", "probe: one commit"]):
        subprocess.run(argv, cwd=workdir, check=True, capture_output=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bg_session_probe.py",
                                 description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", required=True,
                    help="a scratch git repository for the sessions to work in; "
                         "created with one commit if absent")
    ap.add_argument("--ceiling", type=int, required=True,
                    help="processed tokens across every session this probe has "
                         "started, in any run, at which it stops them all")
    ap.add_argument("--steps", default="a1,a2,a3",
                    help="comma-separated: a1 a2 a3 (the verdict), a4 a5 (observe only)")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--state", help="where the probe keeps the sessions it started "
                                    "(default: <workdir>/../bg-probe-state.json)")
    ap.add_argument("--observe", type=int, default=120,
                    help="seconds to watch an observe-only step")
    ap.add_argument("--leave-running", action="store_true",
                    help="observe steps: do not stop the session (a4, for a human to attach)")
    ap.add_argument("--cleanup", metavar="KEEP_DIR",
                    help="copy every probe session's transcripts to KEEP_DIR, then "
                         "stop and remove every session the state file names")
    ap.add_argument("--out", help="also write the rows and findings here as JSON")
    ap.add_argument("--poll", type=int, default=5)
    args = ap.parse_args(argv)

    workdir = os.path.abspath(args.workdir)
    state = args.state or os.path.join(os.path.dirname(workdir), "bg-probe-state.json")
    p = Probe(workdir, args.model, args.ceiling, state, poll=args.poll, observe=args.observe)
    steps = [x.strip() for x in args.steps.split(",") if x.strip()]
    ran = []
    print("devteam background-session probe\n")

    if args.cleanup:
        p.cleanup(os.path.abspath(args.cleanup))
    elif preflight(p):
        ensure_repo(workdir)
        try:
            p.check_ceiling()
            for step in steps:
                if step == "a4":
                    p.step_observe("a4", A4, stop=not args.leave_running)
                elif step == "a5":
                    p.step_observe("a5", A5, mode="manual")
                else:
                    getattr(p, f"step_{step}")()
                ran.append(step)
                if any(k in ("no-bg", "untrusted") for k, _, _ in p.findings):
                    break
        except Ceiling as exc:
            p.finding("ceiling", "-", f"{exc.args[0]:,} processed tokens >= the ceiling of "
                      f"{p.ceiling:,}; every probe session was stopped")

    tokens, reqs, by_model = p.meter()
    p.row("-", "spent by every probe session so far",
          f"{reqs} requests, {tokens:,} processed tokens of a {p.ceiling:,} ceiling; "
          + "; ".join(f"{m} {c['requests']} requests" for m, c in sorted(by_model.items())))
    width = max((len(n) for _, n, _, _ in p.rows), default=10)
    for step, name, value, cmd in p.rows:
        print(f"  {step:<7} {name:<{width}}  {value}")
        if cmd:
            print(f"  {'':<7} {'':<{width}}  {cmd}")
    print()
    for kind, step, detail in p.findings:
        print(f"  {kind:<16} {step:<4} {detail}")
    code, text = (0, "cleanup done") if args.cleanup else p.verdict(ran)
    print(f"\nverdict: {text}")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"rows": p.rows, "findings": p.findings, "verdict": text, "exit": code,
                       "spent": tokens, "requests": reqs,
                       "sessions": {n: {"statuses": s.statuses, "first": s.first, "last": s.entry,
                                        "handle": s.handle, "printed": s.printed}
                                    for n, s in p.sessions.items()}}, fh, indent=2)
    return code


if __name__ == "__main__":
    sys.exit(main())
