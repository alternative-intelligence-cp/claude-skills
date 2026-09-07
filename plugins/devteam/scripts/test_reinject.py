#!/usr/bin/env python3
"""Negative control for reinject.py (P-35).

The failure that matters is not silence — it is speaking to a session that is
not the manager. A hook that injects "you are the project manager" into an
unrelated session is worse than one that never fires, so most of these cases
check that it stays quiet.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
HOOK = os.path.join(HERE, "reinject.py")
MANAGER = "session-manager-1"


def build(marker=MANAGER, nested=False, no_devteam=False, handoff=None):
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-reinject-"))
    if not no_devteam:
        d = os.path.join(root, "devteam", ".run", "session")
        os.makedirs(d)
        if marker is not None:
            open(os.path.join(d, "manager"), "w").write(marker + "\n")
        if handoff is not None:
            open(os.path.join(d, "handoff-ready"), "w").write(handoff)
    sub = os.path.join(root, "src", "deep")
    os.makedirs(sub, exist_ok=True)
    return root, (sub if nested else root)


def run(cwd, session, project_dir=None):
    env = {**os.environ}
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    proc = subprocess.run([sys.executable, HOOK],
                          input=json.dumps({"session_id": session, "cwd": cwd}),
                          capture_output=True, text=True, env=env)
    return proc.stdout.strip()


OUTGOING = "session-outgoing-0"
WELL_FORMED = f"session {OUTGOING}\ncheckpoint C-3\n"

# (name, build kwargs, session id, speaks at all, rotation expectation)
#
# The rotation expectation is the half that is easy to get backwards. The line
# fires for the SUCCESSOR mid-handoff -- it holds the lock, so it matches the
# marker, but `handoff-ready` still names the predecessor it has not yet told
# to stop. It must NOT fire for the outgoing manager that wrote the file and
# is still working (`run` §7b step 4), which is the case that names itself.
CASES = [
    ("fires-for-the-manager", dict(), MANAGER, True, None),
    ("fires-from-a-nested-directory", dict(nested=True), MANAGER, True, None),
    ("silent-for-another-session", dict(), "session-other", False, None),
    ("silent-when-no-marker", dict(marker=None), MANAGER, False, None),
    ("silent-outside-a-devteam-project", dict(no_devteam=True), MANAGER, False, None),
    ("silent-for-empty-session-id", dict(), "", False, None),

    ("rotation-line-when-handoff-names-another",
     dict(handoff=WELL_FORMED), MANAGER, True, OUTGOING),
    ("fp-no-rotation-line-when-handoff-names-you",
     dict(handoff=f"session {MANAGER}\ncheckpoint C-3\n"), MANAGER, True, None),
    ("fp-no-rotation-line-without-a-handoff-file",
     dict(), MANAGER, True, None),
    ("fp-silent-entirely-for-a-stranger-even-mid-rotation",
     dict(handoff=WELL_FORMED), "session-other", False, None),

    ("rotation-malformed-when-checkpoint-missing",
     dict(handoff=f"session {OUTGOING}\n"), MANAGER, True, "MALFORMED"),
    ("rotation-malformed-when-session-id-is-blank",
     dict(handoff="session \ncheckpoint C-3\n"), MANAGER, True, "MALFORMED"),
    ("rotation-malformed-when-file-is-empty",
     dict(handoff=""), MANAGER, True, "MALFORMED"),
]


def check(name, out, root, expect, rotation):
    """The reasons this case failed, as a list. Empty means it passed."""
    got = bool(out)
    if got != expect:
        return [f"{'spoke' if got else 'silent'}, expected "
                f"{'to speak' if expect else 'silence'}"]
    if not expect:
        return []
    bad = [f"block missing {needed!r}"
           for needed in ("re-read devteam/BOARD.md", "STALE",
                          "skills/run/SKILL.md", root)
           if needed not in out]
    # Asserted in BOTH directions on every case, not only where a rotation is
    # expected: a rotation notice that fires when none is happening tells a
    # working manager it has been replaced, which is the more expensive error
    # of the two and the one a positive-only assertion cannot see.
    said = "ROTATION IS IN PROGRESS" in out or "MALFORMED" in out
    if rotation is None:
        if said:
            bad.append("announced a rotation with none in progress")
    elif rotation == "MALFORMED":
        if "MALFORMED" not in out:
            bad.append("did not report the malformed handoff-ready")
    else:
        if "ROTATION IS IN PROGRESS" not in out:
            bad.append("did not announce the rotation")
        elif rotation not in out:
            bad.append(f"rotation notice does not name {rotation!r}")
    return bad


def main():
    passed = failed = 0
    for name, kw, session, expect, rotation in CASES:
        root, cwd = build(**kw)
        try:
            out = run(cwd, session, project_dir=cwd)
            bad = check(name, out, root, expect, rotation)
            if bad:
                failed += 1
                for why in bad:
                    print(f"FAIL  {name}: {why}")
                if out:
                    print(f"        | {out.splitlines()[0]}")
            else:
                passed += 1
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- the two readers of handoff-ready must not drift apart -------------
    # `reinject.handoff_state` and `guard.handoff_names` both parse this file,
    # and NEITHER hook may import the other: a hook that fails to import is a
    # hook that breaks every tool call, which is why both are stdlib-only and
    # standalone. So the duplication is deliberate and the drift is what needs
    # controlling.
    #
    # What is asserted is the property they genuinely share -- **they extract
    # the same session id** -- and not boolean equality, which they correctly
    # do NOT have: a file naming a session but carrying no checkpoint is
    # `malformed` to reinject and still a rotation to the guard, and both are
    # right. Demanding identical verdicts would force a false equivalence,
    # which is an instrument answering a question adjacent to the one asked.
    sys.path.insert(0, HERE)
    import guard
    import reinject

    AGREEMENT = [
        (f"session {MANAGER}\ncheckpoint C-3\n", MANAGER),
        (f"checkpoint C-3\nsession {MANAGER}\n", MANAGER),
        (f"session {MANAGER}\ncheckpoint C-3\nsession someone-else\n", MANAGER),
        ("session \ncheckpoint C-3\n", None),
        ("", None),
    ]
    for text, expect_id in AGREEMENT:
        root, _ = build(handoff=text)
        try:
            state, detail = reinject.handoff_state(root)
            got = detail if state == "named" else None
            names = guard.handoff_names(root, expect_id) if expect_id else False
            wrong = guard.handoff_names(root, "an-id-that-is-not-in-the-file")
            if got != expect_id:
                failed += 1
                print(f"FAIL  readers-agree[{text!r}]: reinject read {got!r}, "
                      f"expected {expect_id!r}")
            elif expect_id and not names:
                failed += 1
                print(f"FAIL  readers-agree[{text!r}]: guard does not name "
                      f"{expect_id!r}, which reinject read from the same file")
            elif wrong:
                failed += 1
                print(f"FAIL  readers-agree[{text!r}]: guard named a session "
                      "that is nowhere in the file")
            else:
                passed += 1
        finally:
            shutil.rmtree(root, ignore_errors=True)

    total = len(CASES) + len(AGREEMENT)
    quiet = sum(1 for c in CASES if not c[3] or c[4] is None)
    print(f"\nreinject control: {passed} passed, {failed} failed, {total} cases "
          f"({quiet} of them checking it stays quiet, {100 * quiet // total}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
