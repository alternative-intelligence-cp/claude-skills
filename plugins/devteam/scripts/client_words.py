#!/usr/bin/env python3
"""What the client typed into a session, read from that session's own transcript.

WHAT THE CLIENT SAID DURING A HANDOFF REACHED NO FILE, AT ANY OF FIFTEEN
ROTATIONS (F-21). The outgoing manager stops writing once it hands over, its
successor has not yet taken the lock, and the client goes on talking to the
session in front of them: *"great. lets continue."* at pricelog's C-3 rotation,
*"sweet. I did it and kicked it off. …"* at C-4, *"sounds good"* in s24's
tenure. Nothing in `devteam/` can hold what is said in that gap, because the
writer lock is the point of the gap. The harness already writes every prompt
into the session's transcript, with its time, and the transcript is outside the
lock. So this reads them from there (roadmap 0.3.3, L-3.7). The `resume` skill's
§0 runs it for the outgoing session that `handoff-ready` names, since that
session's last write, and minutes what it prints.

    python3 client_words.py <session> [--since <commit>|<time>] [--root <dir>] [--json]

THE TRANSCRIPT IS FOUND BY ITS ID, NOT BY ITS PROJECT'S PATH. The harness keeps
it at `<root>/<directory>/<session>.jsonl`, the directory named after the path
the session ran in, with both `/` and `.` turned into `-`. The meter's lookup
turned only `/`, so it could not find a session that ran under a path holding a
dot (the cycle README's §4.8). So every directory under the root is looked in,
one level down, and the id alone decides. The root is `~/.claude/projects/`
unless `--root` names another, which is how a control reads synthetic
transcripts and never a real one.

AN ENTRY IS PLACED BY THE HARNESS'S OWN LABELS, NEVER BY ITS SHAPE. The harness
marks who originated an entry, in `origin.kind` and `promptSource`, and those
labels, not the entry's shape, decide what it is. Shape alone misreads it both
ways. A task notification is injected, is written like a prompt, and carries no
`isMeta` flag. The harness's `[Request interrupted by user]` is a list holding a
text block, which is how a prompt can be written. A message typed while the
model is busy can be absorbed into its turn as an attachment, and it appears in
no other entry. Printed, a line of the harness's own would put words in the
client's mouth. Skipped, one of the client's would be lost. So every entry
that could hold words is placed, and one this cannot place is named by its
line, never guessed at (roadmap 0.3.3, L-3.13: the owner's answer, from a
survey of every transcript on the owner's machine).

Printed, each marked with how it arrived:

    typed                   a prompt the client typed: origin `human`, source
                            `typed`
    typed, queued           typed while the model was busy, and delivered after
                            its turn: source `queued`
    typed, mid-turn         typed while the model was busy, and absorbed into
                            the turn: a `queued_command` attachment whose origin
                            is `human`
    accepted suggestion     the harness's suggested prompt, which the client sent:
                            source `suggestion_accepted`
    interrupted             the harness's `[Request interrupted by user]`, or
                            `… for tool use]`, written when the client pressed
                            Esc
    sdk                     a prompt a program sent through the SDK: source `sdk`
    opened a background     the first prompt of a background session, labelled
      session               `typed` whoever wrote it. On the owner's machine a
                            session wrote every one, with `claude --bg`

Skipped, as the harness's own: tool results; compaction summaries
(`isCompactSummary`); anything flagged `isMeta`, which is peer messages, skill
text, reminders and the notices around them; task notifications and peer
messages by their origin, flagged or not; slash commands (`<command-name>`,
`<command-message>`) and their local output (`<local-command-stdout>`,
`<local-command-stderr>`); a subagent's side chain (`isSidechain`); and a
`queued_command` attachment that is a peer message or a task notification.
Every other type of entry is the harness's own record, and holds no prompt.

A prompt is printed JSON-quoted, one to a line, with its local time and its
mark, so a prompt of several lines stays on one line: `\\n` in it is a newline.
Nothing in it is trimmed.

WHAT THIS PRINTS IS MINUTED IN A TRACKED FILE, so it holds nothing check_refs
would name a leak there, fenced or not. A home path is written from `~`, which
loses nothing to a reader on the same machine: `/home/<user>/Workspace/x`
becomes `~/Workspace/x`. Anything else leak-shaped, such as a key or a
session's temporary path, is replaced by its name in angle brackets, such as
`<an API key>`. The line counts what was masked, and the transcript keeps the
words as typed (roadmap 0.3.3, L-3.13). The patterns are check_refs.py's own,
so the two cannot disagree (P-34). They are matched in the printed line as
well as in the words, because quoting turns a newline into two characters
that a path can then run across. For the same reason the transcript is named
by its session id alone: the directory the harness keeps it in spells out the
client's home.

`--since` keeps what came at or after a time. The time is a commit's committer
time, read in the repository of the current directory, or an ISO 8601 time,
local unless it names its offset. A committer time is whole seconds, so a
prompt in the commit's own second is kept although it may have come just
before the commit: kept, it is read once too often; dropped, it is lost.

Exit 0 clean, 2 could not run (no transcript for the session, or two), 3 not
evaluated: a line that is not a JSON object, or an entry of a kind this does not
place, each named by its line, with everything it could place still printed. The
contract is result.py's (roadmap 0.3.1, L-1.1). It reports no finding, so it
never exits 1.

It depends on the transcript's format, as session_cost.py does (L-18). A kind
the harness adds later is named, not printed, until it is placed here.

Its control is test_client_words.py.
"""
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_refs  # noqa: E402 -- LEAKS, what a tracked file may not hold
import result  # noqa: E402 -- the four-result contract (roadmap 0.3.1, L-1.1)

USAGE = "usage: client_words.py <session> [--since <commit>|<time>] [--root <dir>] [--json]"
# A session id is a transcript's file name, and never a path.
SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{3}|\.\d{6})?)?"
                  r"(?:Z|[+-]\d{2}:\d{2})?$")
INTERRUPTED = ("[Request interrupted by user]", "[Request interrupted by user for tool use]")
COMMAND = ("<command-name>", "<command-message>")
COMMAND_OUTPUT = ("<local-command-stdout>", "<local-command-stderr>")
# The harness's `promptSource` for a prompt whose origin is `human`, and the
# mark each is printed with.
HUMAN = {"typed": "typed", "queued": "typed, queued", "suggestion_accepted": "accepted suggestion"}
BACKGROUND = "opened a background session"
HOME_PATH = "an absolute home path"     # check_refs.LEAKS' name for one
GRAMMAR = "a JSON object"
PLACES = ("a prompt the harness labels as the client's, or an entry of its own that "
          "this skips (client_words.py's docstring lists both)")


def instant(text):
    """A timestamp as an aware datetime, or None. `Z` is read as UTC on every
    Python, and a time with no offset is local."""
    try:
        t = datetime.datetime.fromisoformat(re.sub(r"Z$", "+00:00", text.strip()))
    except (ValueError, AttributeError):
        return None
    return t if t.tzinfo else t.astimezone()


def shown(t):
    """An instant as the client's clock reads it."""
    return t.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def text_of(content):
    """(text, None) for a string, or a list holding only text blocks, joined by
    newlines; (None, why) for any other content."""
    if isinstance(content, str):
        return content, None
    if isinstance(content, list) and content:
        blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"
                  and isinstance(b.get("text"), str)]
        if len(blocks) == len(content):
            return "\n".join(b["text"] for b in blocks), None
        kinds = sorted({b.get("type", "?") if isinstance(b, dict) else type(b).__name__
                        for b in content} - {"text"})
        return None, f"it holds a block of type {', '.join(kinds)}, which is not text"
    return None, "its content is neither a string nor a list of text blocks"


def masked(text):
    """(text, how many pieces were masked): every piece check_refs would name
    a leak, masked until none is left. A home path is written from `~`, and
    anything else becomes its name in angle brackets. Neither replacement
    holds a quote or a backslash, so a JSON-quoted line stays JSON."""
    total = 0
    for _ in range(len(check_refs.LEAKS) + 1):
        changed = 0
        for pattern, why in check_refs.LEAKS:
            text, n = pattern.subn("~/" if why == HOME_PATH else f"<{why}>", text)
            changed += n
        total += changed
        if not changed:
            break
    return text, total


def kind_of(kind):
    return kind.get("kind") if isinstance(kind, dict) else None


def place(entry, first_prompt):
    """What one entry is: ("print", mark, text), ("skip", what, None),
    ("other", None, None) for an entry that holds no prompt, or
    ("unplaced", why, None)."""
    if entry.get("type") == "attachment":
        a = entry.get("attachment")
        if not isinstance(a, dict) or a.get("type") != "queued_command":
            return "other", None, None
        origin = kind_of(a.get("origin"))
        if origin == "human" and a.get("commandMode") == "prompt":
            text, why = text_of(a.get("prompt"))
            if text is None:
                return "unplaced", f"a mid-turn prompt whose text cannot be read: {why}", None
            return "print", "typed, mid-turn", text
        if origin == "peer" or a.get("isMeta"):
            return "skip", "peer message", None
        if origin == "task-notification" or (origin is None and a.get("commandMode") == "task-notification"):
            return "skip", "task notification", None
        return "unplaced", (f"a queued_command attachment with origin {origin!r} and "
                            f"commandMode {a.get('commandMode')!r}"), None
    if entry.get("type") != "user":
        return "other", None, None

    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                         for b in content):
        return "skip", "tool result", None
    if entry.get("isSidechain"):
        return "skip", "subagent", None
    if entry.get("isCompactSummary"):
        return "skip", "compaction summary", None
    if entry.get("isMeta"):
        return "skip", "injected", None
    origin, source = kind_of(entry.get("origin")), entry.get("promptSource")
    if origin == "task-notification":
        return "skip", "task notification", None
    if origin == "peer":
        return "skip", "peer message", None
    text, why = text_of(content)
    lead = (text or "").lstrip()
    if lead.startswith(COMMAND):
        return "skip", "slash command", None
    if lead.startswith(COMMAND_OUTPUT):
        return "skip", "local command output", None
    if origin == "human" and source in HUMAN:
        if text is None:
            return "unplaced", f"a prompt whose text cannot be read: {why}", None
        if source == "typed" and first_prompt and entry.get("sessionKind") == "bg":
            return "print", BACKGROUND, text
        return "print", HUMAN[source], text
    if origin is None and source == "sdk":
        if text is None:
            return "unplaced", f"an sdk prompt whose text cannot be read: {why}", None
        return "print", "sdk", text
    if origin is None and source is None and text is not None and text in INTERRUPTED:
        return "print", "interrupted", text
    return "unplaced", f"a user entry with origin {origin!r} and promptSource {source!r}", None


def find(root, session):
    """(path, None), or (None, why it could not be found)."""
    try:
        dirs = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    except OSError as exc:
        return None, f"{root} cannot be listed ({exc.strerror})"
    found = [os.path.join(root, d, session + ".jsonl") for d in dirs
             if os.path.isfile(os.path.join(root, d, session + ".jsonl"))]
    if not found:
        return None, (f"no transcript for session {session}: {root}/*/{session}.jsonl names no "
                      "file. The id is the transcript's file name, as `handoff-ready` and the "
                      "board's writer line carry it")
    if len(found) > 1:
        return None, (f"session {session} has {len(found)} transcripts, "
                      f"{', '.join(found)}, and which one it spoke in is not guessed at")
    return found[0], None


def since_of(value):
    """(instant, what it was read from, None), or (None, None, why not)."""
    if TIME.match(value):
        t = instant(value)
        if t is None:
            return None, None, f"--since {value!r} is not a time"
        return t, shown(t), None
    def git(*args):
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True)
        except OSError as exc:
            return subprocess.CompletedProcess(args, 127, "", str(exc))
    if git("rev-parse", "--show-toplevel").returncode:
        return None, None, (f"--since {value!r} is not a time, and the current directory is not "
                            "a git repository, so it names no commit")
    sha = git("rev-parse", "--verify", "--quiet", f"{value}^{{commit}}")
    if sha.returncode:
        return None, None, (f"--since {value!r} is neither a time (YYYY-MM-DDTHH:MM[:SS] and an "
                            "optional offset) nor a commit in this repository")
    t = instant(git("show", "-s", "--format=%cI", sha.stdout.strip()).stdout)
    if t is None:
        return None, None, f"the committer time of {value!r} could not be read"
    return t, f"{value} ({shown(t)})", None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json, argv = result.flag(argv, "--json")
    options = {}
    for name in ("--since", "--root"):
        if name in argv:
            i = argv.index(name)
            if i + 1 >= len(argv):
                return result.could_not_run("client_words", USAGE, as_json)
            options[name], argv = argv[i + 1], argv[:i] + argv[i + 2:]
    if len(argv) != 1 or argv[0].startswith("-"):
        return result.could_not_run("client_words", USAGE, as_json)
    session = argv[0]
    if not SESSION_ID.match(session):
        return result.could_not_run("client_words", f"{session!r} is not a session id: a "
                                    "transcript's file name, without `.jsonl`", as_json)
    root = os.path.realpath(options.get("--root") or os.path.expanduser("~/.claude/projects"))
    if not os.path.isdir(root):
        return result.could_not_run("client_words", f"{root} is not a directory of transcripts",
                                    as_json)
    since, since_text = None, None
    if "--since" in options:
        since, since_text, why = since_of(options["--since"])
        if why:
            return result.could_not_run("client_words", why, as_json)
    path, why = find(root, session)
    if why:
        return result.could_not_run("client_words", why, as_json)
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        return result.could_not_run("client_words", f"{path} cannot be read ({exc.strerror})",
                                    as_json)

    where = f"{session}.jsonl"
    res = result.Result("client_words", f"session {session}"
                        + (f" since {since_text}" if since_text else ""))
    unread, unplaced, lines, offered = [], [], 0, 0
    printed, earlier, skipped = [], 0, {}
    first_prompt = True
    for n, line in enumerate(raw.split(b"\n"), 1):
        if not line.strip():
            continue
        lines += 1
        try:
            entry = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            entry = None
        if not isinstance(entry, dict):
            unread.append((where, n))
            continue
        verdict, what, text = place(entry, first_prompt)
        if verdict == "other":
            continue
        if verdict == "print":
            first_prompt = False
        at = instant(entry.get("timestamp")) if isinstance(entry.get("timestamp"), str) else None
        if since and at is not None and at < since:
            earlier += 1
            continue
        offered += 1
        if verdict == "skip":
            skipped[what] = skipped.get(what, 0) + 1
        elif verdict == "unplaced":
            unplaced.append(((where, n), what))
        elif at is None:
            unplaced.append(((where, n), f"a {what} prompt with no time it can read"))
        else:
            printed.append((at, what, text))

    if unread:
        res.gap(f"{where}'s lines", result.unparsed(
            unread, lines, "lines", GRAMMAR, "whatever they hold was not read"))
    if unplaced:
        res.gap(f"{where}'s entries", result.unparsed(
            [w for w, _ in unplaced], offered, "entries that could hold words", PLACES,
            "none of them was printed. They are: " + "; ".join(
                f"line {w[1]}, {why}" for w, why in unplaced)))
    notes, hidden = [], 0
    for at, mark, text in printed:
        words, n = masked(text)
        line, m = masked(json.dumps(words, ensure_ascii=False))
        notes.append((f"{shown(at)} {mark}", line))
        hidden += n + m
    res.count(len(printed), "printed")
    res.count(hidden, "masked")
    if since:
        res.count(earlier, "earlier")
    res.count(sum(skipped.values()), "skipped")
    res.count(lines, "lines")
    for label, line in notes:
        res.note(label, line)
    return result.emit([res], as_json)


if __name__ == "__main__":
    sys.exit(main())
