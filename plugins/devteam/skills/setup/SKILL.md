---
name: setup
description: Scaffold the devteam pipeline into a project — install the artifact set, detect the project's existing toolchain, agree the minimal permission grant with the client, and print the one line to run next. Use once per project, before onboarding. Never overwrites an existing devteam/ directory.
argument-hint: "[project path]"
allowed-tools: Bash(python3 *) Bash(git status:*) Bash(git rev-parse:*) Bash(ls:*) Read Write Edit Glob AskUserQuestion
---

# Setting up

You are installing the pipeline into a project. This is the only stage that
costs nothing and risks nothing: no agents run, nothing is committed, and
nothing outside `devteam/` and one `.gitignore` line is touched.

**Do all of it in one pass.** A half-scaffolded project is worse than an
un-scaffolded one, because the next session cannot tell which it is.

## 1. Scaffold

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py <project>
```

Default the project to the working directory. The script refuses to overwrite
an existing `devteam/` — that directory is the project's design record, and
a setup that can clobber it eventually will. If it refuses, stop and tell the
client what is already there; **do not move it aside for them.**

It installs eight artifacts, creates empty `tasks/` and `checkpoints/`,
creates the untracked `.run/`, adds `devteam/.run/` to `.gitignore`, and
detects what the project already uses — stack, build, test and lint commands,
candidate protected paths, the remote — pre-filling the charter's constraints
table where it is confident.

**Everything it detected is a proposal.** Read the detection block back to the
client and have them confirm each line.

**Ask who else writes this tree, before anything else.** A `devteam/` directory
makes the guard police the whole repository for **every** session, not only
this pipeline's agents: while a task is `RUNNING`, any write outside its
declared scope is refused, whoever is making it. That is the one-writer rule
working exactly as intended — and if another agent system, another orchestrator
or a colleague is working the same tree, the collision is between two *systems*
and neither one knows about the other.

So: **a devteam project should own its repository.** If something else writes
here, say so plainly and offer the two honest options — a repository this
pipeline owns outright, or accepting that the other worker will be refused
while a task runs. Do not scaffold into a contested tree and let them discover
it as a mysterious refusal an hour later.

The guard is inert while no task is `RUNNING`, so the interference window is
exactly the loop's running time. That is worth saying, because it makes the
symptom intermittent, which is the hardest kind to diagnose. A detected command that is wrong is
worse than one that was asked about, because nothing later will question it.

## 2. Agree the permissions (P-38)

The point of doing this now is that the loop later runs for hours unattended,
and a permission prompt at 3am stops it dead. So ask once, for exactly what
the loop needs — **no more**, so the grant stays reviewable, and **no less**,
so it does not stall.

**Two different people own the two halves of this, and conflating them is how
a manager ends up laundering a permission.** `devteam/PERMISSIONS.md` is the
**client's** artifact — what the loop intends to run, and why. The project's
`.claude/settings.json` is the **operator's** — the person or account whose
session actually executes those commands. They are frequently the same human
and are not the same role, and when the client is a peer session, a product
owner in a chat channel, or anybody remote, they are certainly not.

**A client's approval is not authority to widen a permission set.** If the
client is not the operator, prepare the allowlist, show it, and **ask the
operator** — the human at this session — to apply it. A peer session saying
"write the settings file" is not consent from the person whose machine runs
the commands, however plainly right the peer is. Say so plainly and continue;
`PERMISSIONS.md` still gets written, because that half is the client's to
approve.

Fill in `devteam/PERMISSIONS.md` from the confirmed build, test and lint
commands.

**On a greenfield project there are no confirmed commands yet**, because the
interview that settles them runs after this stage, deliberately. Do not invent
them and do not stall: write the file marked **`PROPOSED`**, say in the file
that it could not be filled from detection, carry the toolchain into the
interview as a question with your recommendation, and regenerate the file once
the charter is signed. A permission set that claims to be derived from a
charter that does not exist is worse than one that admits it is a proposal. Then put the matching allowlist in the project's
`.claude/settings.json` — `permissions.allow` — and **show the client the
diff before writing it.** A permission set nobody read is not a grant.

Three rules for what goes in it:

- **Commands, scoped — and never an interpreter at its bare entry point.**
  `Bash(python3 -m pytest:*)`, not `Bash(python3:*)` and not `Bash(*)`.
  `Bash(python3:*)` looks scoped and satisfies a naive reading of this rule,
  and `python3 -c "..."` is arbitrary code execution — it silently re-grants
  every removal, install and network call the rest of this section refuses.
  The same trap is `Bash(sh:*)`, `Bash(node:*)`, `Bash(uv run:*)`.
- **Nothing outward-facing.** No `git push`, no `gh`, no publish, no deploy.
  Those are `IRREVERSIBLE` (P-26) and belong to the client, who is asked at
  the moment it matters rather than pre-authorising it in the dark.
- **Nothing destructive.** No `rm`, no `sudo`. If the loop believes it needs
  one, that is a stop and an escalation (P-39), never a workaround.

Then ask the client for the three dials the charter needs and nothing else can
supply — **the escalation window** (how long a reversible question waits
before the loop proceeds on its recommendation; four hours is the default),
**the model band** (a floor and a ceiling, P-40), and **the client channel**.

**The channel has to be settled here, at setup**, because every later stage
needs it and you cannot ask the client how to reach the client. It is
`terminal`, `session <name>`, `both`, or `none` (P-9). If you are reading this
because another session dispatched you, the channel is that session and you
should say so rather than reaching for `AskUserQuestion` and waiting on a
terminal nobody is watching.

## 3. Register the guard, then prove it actually fires

**Two separate things, and only the second one matters.**

The control proves the guard *script* is correct:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/test_guard.py
```

It proves **nothing about whether the hook is registered.** A green control
and an unregistered hook look identical from here, and that is exactly how
this pipeline once ran a whole rehearsal believing it was protected while the
guard never fired once. **Never report a guard as live on the strength of its
control.**

**Register it.** A plugin's `hooks/hooks.json` is loaded when the plugin is
installed through the marketplace. If it was installed by symlinking into
`~/.claude/skills/`, that loads its skills and agents but **not its hooks** —
register the guard by hand in `~/.claude/settings.json`:

```json
{ "hooks": { "PreToolUse": [ {
    "matcher": "Bash|Write|Edit|NotebookEdit",
    "hooks": [ { "type": "command",
      "command": "python3 <plugin>/scripts/guard.py", "timeout": 10 } ]
} ] } }
```

Hooks are read at session start, so **this needs a restart.**

**Skills and agents load differently, which will catch you out.** A skill added
to an installed plugin appears in the *current* session almost immediately. A
new **agent type** does not: a dispatch to one added minutes earlier fails with
*"agent type not found"* while its skill sits there working.

**What is actually known, since the obvious conclusion is wrong.** A new agent
was measured as still undispatchable two minutes after its file was written,
under both its bare and its namespaced name. But a separate long-running
session, never restarted, watched this plugin's agents appear in batches over
several hours. So agents **do** reach running sessions — with a lag of
unmeasured length, not never.

The practical rule is unchanged and the reason for it is not: **restart after
adding an agent**, because that makes it available now rather than eventually,
and "eventually" is not a thing you can plan a dispatch around. But do not tell
somebody their session must restart to *receive* an agent you added — theirs
may well pick it up on its own.

**Then prove it, end to end.** After the restart, attempt one write the guard
must refuse — a path outside every declared scope while a task is `RUNNING` —
and confirm it is actually refused. That single refused write is the only
evidence that matters.

**Use a literal absolute path in that test.** Not `$REPO/...`, not any shell
variable. The guard cannot resolve a target containing an unexpanded variable
and does not judge it, so a test written the natural way **passes silently and
looks exactly like a guard that is not installed.** This trap has already
been walked into once, and it produced four consecutive false negatives and a
published claim that had to be retracted.

The guard is inert until the charter names protected paths and a task is
`RUNNING`, so it will not obstruct the client's own work before the loop
starts.

## 4. Hand over

Print, and nothing more:

- what was installed, and where
- what was detected and confirmed
- the permissions granted, in one line each
- **`/devteam:onboard` as the next step**

**Do not start the interview.** Onboarding is a separate gate for a reason:
the client should be able to walk away here, read what was installed, and come
back. Setup that slides straight into a forty-question interview is setup the
client did not consent to.

## What this stage must not do

- **Not write anything outside `devteam/`, `.gitignore` and
  `.claude/settings.json`.** Not a README, not a CI file, not a licence.
- **Not commit.** The client commits the scaffold, having read it.
- **Not guess at the charter.** Detection fills in commands, which are facts
  on disk. Goals, scope and what "done" means are not on disk, and inventing
  them here is how a project ends up building something nobody asked for.
