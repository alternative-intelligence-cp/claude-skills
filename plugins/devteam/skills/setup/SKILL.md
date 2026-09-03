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
client and have them confirm each line. A detected command that is wrong is
worse than one that was asked about, because nothing later will question it.

## 2. Agree the permissions (P-38)

The point of doing this now is that the loop later runs for hours unattended,
and a permission prompt at 3am stops it dead. So ask once, for exactly what
the loop needs — **no more**, so the grant stays reviewable, and **no less**,
so it does not stall.

Fill in `devteam/PERMISSIONS.md` from the confirmed build, test and lint
commands. Then put the matching allowlist in the project's
`.claude/settings.json` — `permissions.allow` — and **show the client the
diff before writing it.** A permission set nobody read is not a grant.

Three rules for what goes in it:

- **Commands, scoped.** `Bash(pytest:*)`, not `Bash(*)`. The narrow form is
  the one a client can actually review.
- **Nothing outward-facing.** No `git push`, no `gh`, no publish, no deploy.
  Those are `IRREVERSIBLE` (P-26) and belong to the client, who is asked at
  the moment it matters rather than pre-authorising it in the dark.
- **Nothing destructive.** No `rm`, no `sudo`. If the loop believes it needs
  one, that is a stop and an escalation (P-39), never a workaround.

Then ask the client for the two dials the charter needs and nothing else can
supply — **the escalation window** (how long a reversible question waits
before the loop proceeds on its recommendation; four hours is the default)
and **the model band** (a floor and a ceiling, P-40).

## 3. Confirm the guard is live

The guard is a `PreToolUse` hook and loads with the plugin. Confirm it is
working rather than assuming it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/test_guard.py
```

Thirty-two cases, twenty of them false-positive controls. If they do not all
pass, **say so and stop** — a guard believed to be running and not running is
worse than no guard, because the loop will be trusted with scopes nothing
enforces.

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
