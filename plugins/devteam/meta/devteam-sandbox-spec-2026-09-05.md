# Structural sandboxing for devteam workers — implementation spec

> *Relocated 2026-09-05 into `plugins/devteam/meta/`, as the note below asks.
> Nothing under this line was edited. The source it names — the owner's
> original idea, fleshed out by Gemini — stays private on the owner's machine;
> the plan that builds on this spec is [`roadmap/`](roadmap/README.md).*

**For the implementing agent.** Written 2026-09-05 by `nitpick-libs-42`.
Distilled; no preamble. Every number below was measured on the target machine
on 2026-09-05 unless a line says **REASONED**, which marks a claim that was
argued rather than run. Do not promote a REASONED line to a fact without
running it.

**This file is in the wrong repository, deliberately.** It belongs in the
`devteam` project (`../claude-skills/`). The session that wrote it may only
write inside `nitpick-libs` (the owner's standing rule; `devteam`'s own
`HANDOFF.md` repeats it as *never write outside the repository this session was
started in without asking*). Move it; do not treat its location as meaningful.

**Source.** `../claude-skills/.internal/Structural Sandboxing for Autonomous
Agents.md` — the owner's idea, fleshed out by Gemini. The idea is right. Four
things in that document are wrong for this machine and one architectural gap
would reintroduce the problem it solves. All five are corrected below; read §3
before reusing any of its shell.

---

## 1. Objective and threat model

Replace *classification* of writes with *structural impossibility* of writes.

The current mechanism is a `PreToolUse` hook that decides, from command text,
whether a write lands somewhere forbidden. That is an adversarial parsing game
and it is being lost in both directions — measured on the sibling workbench:

| Form | Judged? |
|---|---|
| `echo x > <protected>/f` | DENIED, correct |
| `sed -i s/a/b/ <protected>/f` | DENIED, correct |
| `Write` / `Edit` tool at the same path | DENIED, correct |
| `python3 - <<PY` … `open(path,'w')` … `PY` | **ALLOWED, silently** |
| `git worktree list` (a **read**) | **DENIED** — false positive |

**MUST STOP:** a worker mutating any path outside its declared write scope,
by any means, including means nobody has thought of.

**MUST NOT BREAK:** reads of anything the worker is allowed to read; running
arbitrary build and test commands; the worker's own network access to the
model API.

**NON-GOAL:** correctness of what the worker writes *inside* its scope. See §8.

---

## 2. Measured environment baseline

Re-run these before building. If any answer differs, the design changes.

```
uname -r                                   -> 7.0.0-30-generic
command -v bwrap                           -> /usr/bin/bwrap
bwrap --version                            -> bubblewrap 0.9.0
apt-cache policy bubblewrap                -> Candidate: 0.9.0-1ubuntu0.1
command -v fuse-overlayfs                  -> MISSING
sysctl -n kernel.unprivileged_userns_clone -> 1
cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns -> 0
unshare --user --map-root-user true        -> exit 0
```

Two consequences that decide the architecture:

- **`fuse-overlayfs` is absent and is not needed.** Kernel OverlayFS mounts
  unprivileged *inside a user namespace* on this kernel. Verified.
- **`bwrap` 0.9.0 has no `--overlay` / `--tmp-overlay` / `--ro-overlay`.**
  Those options exist in bubblewrap **0.10.0+**, and the distribution offers
  no such package. **REASONED** (version attribution not verified here).
  If you can obtain 0.10+, §3's two-stage composition collapses into `bwrap`
  alone — check this first, it removes a whole layer.

---

## 3. Four corrections to the source document

**3.1 — Its dependency check inverts on this machine.** The script prefers
`fuse-overlayfs` and falls back to `mount -t overlay`. Here the preferred path
is missing and the fallback needs `CAP_SYS_ADMIN`, so the script cannot mount
at all. The fallback is decorative.

**3.2 — The mount must happen INSIDE the user namespace.** The script mounts
first, then enters `bwrap`. Unprivileged overlay mounting only works within a
userns, so that ordering fails as a normal user.

**3.3 — And therefore the merged view dies with the namespace.** This is the
structural consequence of 3.2 and it invalidates the script's §4: it extracts
the patch *after* `bwrap` exits, from a `$MERGED_DIR` that no longer exists.
**Patch extraction must run inside the namespace**, or the upper layer must be
interpreted directly (harder — see §6.1).

**3.4 — `git diff HEAD` is the wrong reference.** `HEAD` lives in the overlay
and the worker can move it. If a worker commits, `git diff HEAD` returns empty
while real work sits in the overlay's history — a green result meaning "nothing
examined". **Record the base SHA on the host before entering, and diff against
that literal SHA.** `git diff <BASE_SHA>` captures committed *and* uncommitted
work in one patch. (The `git diff <SHA>` form is verified; the specific
worker-commits case is **REASONED**.)

---

## 4. The gap that would reintroduce the problem

**Gemini sandboxed a shell. A devteam worker is not a shell — it is an agent
with tools.**

`bwrap … /bin/bash` isolates Bash invocations. `Write`, `Edit` and `Read`
execute in the harness process, **outside** that sandbox. Wrapping only Bash
produces a hole that is the exact mirror of today's: currently heredocs escape
and `Write` is judged; there, `Write` escapes and heredocs are contained. You
would have swapped which half is unwatched, and moved the hole into the tool
the current guard covers best.

**The agent process must run inside the sandbox.** That forces three decisions
the source document treats as footnotes:

- **Network.** `--unshare-net` severs the model API and the agent cannot run.
  A filtered egress path is **mandatory and is a subsystem, not a flag**.
  Minimum viable: keep the net namespace unshared, run a proxy on the host,
  bind only its unix socket into the sandbox, allowlist the API host.
- **Credentials.** `--clearenv` is correct, and the agent still needs its API
  credential inside. The sandbox therefore contains the one secret it is
  isolating, plus a network path out. Design for this explicitly: inject the
  minimum credential, never the host's `.gitconfig`, `SSH_AUTH_SOCK`, or full
  `~/.claude`.
- **Scratch sizing.** Do not default the upper layer to a small tmpfs. The
  sibling project has a compile whose measured peak was **30.9 GiB** before it
  was fixed. Back the upper layer with disk, or size for the worst build.

---

## 5. Architecture, as verified

Two-stage composition, because `bwrap` 0.9.0 cannot mount the overlay itself.
This exact shape was run end to end and is the thing to build on:

```
host
 └─ unshare --user --map-root-user --mount        # userns + mountns
     └─ mount -t overlay (lower=repo ro, upper=scratch, work=scratch)
         └─ bwrap --bind <merged> /workspace ...   # the isolation boundary
             └─ worker (agent + its shell)
     └─ git -C <merged> diff <BASE_SHA>            # extraction, INSIDE the ns
```

Verified behaviour of that composition:

- worker writes to `tracked.txt` and creates `added.txt` → both land in `upper`
- host lower layer after exit: `tracked.txt` still `v1`, no new files
- worker writing to the **host's absolute path** fails with
  **`No such file or directory`** — not a permission error. The path is not in
  the worker's mount namespace at all, which is the property being bought.
- extraction inside the namespace produced the correct patch:
  `added.txt | 1 +`, `tracked.txt | 2 +-`

---

## 6. Gotchas

**6.1 — The upper layer is not a diff.** A deletion is recorded as a character
device `0/0`:

```
c--------- 2 randy randy 0, 0 file.txt      <- whiteout, not a file
```

Directory deletions use opaque-directory xattrs and behave differently again.
**Never walk `upperdir` to compute what changed.** Diff the merged view. If you
ever must read `upperdir` directly, handle whiteouts and opaque markers
explicitly and write a control for each.

**6.2 — `--new-session` is not optional.** Without it a sandboxed process can
inject keystrokes into the parent terminal via `ioctl(TIOCSTI)`. That is an
escape from an otherwise sound sandbox.

**6.3 — `--die-with-parent` plus `--unshare-pid`**, or orphaned build processes
survive the worker and hold the overlay busy.

**6.4 — `--ro-bind-try`, not `--ro-bind`, for `/bin`, `/sbin`, `/lib`,
`/lib64`.** On merged-`/usr` systems these are symlinks and `--ro-bind` aborts
sandbox setup.

**6.5 — The lower layer must include `.git`.** The worker needs a real
repository. Its `.git` writes land in `upper`, so the host's git state is
untouched — that is what makes §3.4's base-SHA diff work.

---

## 7. Build order

Each step has a verification command and an expected output. Do not proceed on
a step whose verification did not produce the stated output.

- [ ] **S-1. Baseline.** Re-run §2. Expected: the stated values. If `bwrap` is
      ≥ 0.10, stop and re-plan around native `--overlay`; it deletes S-2.
- [ ] **S-2. Overlay in a userns.** Mount, write through, exit. Expected: host
      lower byte-identical; `upper` holds the new file and a `c---------`
      whiteout for the deleted one.
- [ ] **S-3. Compose with bwrap.** §5's nesting, worker writes only.
      Expected: writes land in `upper`; host lower unchanged.
- [ ] **S-4. Negative controls.** §7b. Expected: every escape attempt fails,
      and each failure is `No such file or directory` rather than `Permission
      denied` — a permission error means you built DAC, not structure.
- [ ] **S-5. Extraction.** Record base SHA on host; extract inside the ns
      against that SHA. Expected: a patch containing both tracked edits and new
      files. Add a case where the worker **commits** before exit — expected:
      the patch still contains its work (this is §3.4's REASONED claim; S-5 is
      where it becomes measured).
- [ ] **S-6. Put the agent inside.** Network proxy, credential injection,
      sizing. Expected: an agent completes one trivial task end to end and its
      `Write` tool call lands in `upper`, not on the host. **This step is the
      one that matters; S-1…S-5 are only the substrate.**
- [ ] **S-7. Promotion gate.** Host-side review and apply. Never auto-apply.
- [ ] **S-8. Wire to declared scope.** §9.

### 7b. Negative controls — mandatory

A sandbox that has never refused has not been shown to work. Model this on
`devteam`'s own control discipline: every blocking case gets an allowing twin,
and the suite reports its **denominator and false-positive share**, because a
suite of only-blocking cases can only ever get stricter. At minimum:

| Must be BLOCKED | Must be ALLOWED |
|---|---|
| absolute path write outside scope | write anywhere inside `/workspace` |
| `../../` traversal out of `/workspace` | reading the read-only base |
| symlink planted to a host path | following a symlink within the overlay |
| `python3 -c "open('<host>','w')"` | the same call inside `/workspace` |
| `git -C <host repo> commit` | `git commit` inside `/workspace` |
| writing to the read-only base | building, running tests, `rm -rf` in scope |

The interpreter case is the point of the exercise: it is the form the current
hook cannot see. If it is not blocked, this project has bought nothing.

---

## 8. What this does not solve

State this in the project's own docs so nobody over-reads the guarantee. The
sandbox stops a worker writing **where** it should not. It does nothing about:

- a worker writing **wrong content** where it legitimately may
- two agents both believing they hold the same claim (coordination, not isolation)
- a report citing evidence it does not have
- a check that passes because it measured nothing

Of `devteam`'s ~130 first-run findings, roughly five in six were pipeline
defects, and the escape-the-permissions class was a small minority. This is a
permanent fix to a real and annoying class — not to the class that produced
most of the findings.

**What it does retire**, and this is worth claiming: the rule-pair defect where
the harness's standing instruction prefers heredocs while the guard can only
judge `Write`/`Edit`. With structural bounds there is no guard to evade, so the
two rules stop contradicting. It also settles `CONSOLIDATION.md` item 5 — a
wrapper an agent can bypass by calling the real tool is a rule, not a
mechanism, and a namespace cannot be bypassed. Note the shape item 5 wanted:
a sandbox makes dangerous operations **deliberate rather than forbidden**,
since inside the overlay anything is permitted and deliberateness is expressed
once, at promotion.

---

## 9. The goal state: the declared scope IS the mount spec

Build S-1…S-7 first; this is the payoff.

A `devteam` task already declares the paths it writes, and `check_scope`
verifies compliance by reading text after the fact. **Compile that declaration
into the sandbox's bind arguments instead:** everything read-only, the declared
scope bound read-write, everything else absent from the mount namespace.

The rule and the mechanism stop being two artifacts that can disagree — which
is `devteam`'s own *"name which side is the source of truth, or it is a
spell-checker"* applied to permissions. A scope violation becomes
unrepresentable rather than detectable, and `check_scope` degrades from an
enforcement mechanism to a reporting one, which is a better job for it.

The same applies to the sibling workbench, where `BOARD.md`'s `CLAIMED` column
is the identical declaration in a different grammar.
