#!/usr/bin/env python3
"""Negative control for commit_guard.py (P-35; roadmap 0.3.1 §3.6).

A green control proves the SCRIPT decides correctly, and says nothing about
whether the hook is registered and running (the `setup` skill, §3). 0.3.1's
Findings record the live refusal separately.

More than a third of the cases are false-positive controls, because a guard
that refuses legitimate work gets disabled by whoever it obstructs. The ones
that matter most: the gate's own command; P-12b's `git reset --soft` recovery
to a commit from the reflog; a repository with no `devteam/`, including one
whose `plugins/devteam/` is not a project; a worker inside a sandbox; and every
git command that reads.

Every refusing case names the refusal family it expects, because a verdict
alone cannot tell which rule fired (guard.py's control learned that the hard
way, and CHECKS.md records why guard.py's families still have no names).

The hook never runs a command; it only reads one. So one fixture serves every
case, and the last case checks that the hook changed nothing in it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
# Mutation testing points this at a mutated copy (scripts/mutate.py).
SUBJECT = (os.environ.get("DEVTEAM_SUBJECT_COMMIT_GUARD")
           or os.path.join(HERE, "commit_guard.py"))
GATE = os.path.join(os.path.dirname(SUBJECT), "gate.py")
HERMETIC = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "control",
            "GIT_AUTHOR_EMAIL": "control@example.invalid", "GIT_COMMITTER_NAME": "control",
            "GIT_COMMITTER_EMAIL": "control@example.invalid"}


def env_for(root, **extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("DEVTEAM_SANDBOX", "DEVTEAM_COMMIT_GUARD", "CLAUDE_PROJECT_DIR")
           and not k.startswith("GIT_")}
    env.update(HERMETIC, GIT_CONFIG_GLOBAL=os.path.join(root, "gitconfig"))
    env.update(extra)
    return env


def build():
    """The fixture, and the names the cases use.

    proj      a devteam project: main (A, B), side (from A), a commit L that
              main held and was reset away from (only main's reflog records
              it), a candidate K that no ref holds (what the gate leaves when
              it refuses), K2 on K (in no reflog, HEAD's included),
              origin/feature at K and origin/held at B, a stash made on K,
              and three aliases
    detached  a worktree of proj with HEAD detached at K
    sidewt    a worktree of proj on side
    plain     a repository with no devteam/
    mono      a repository whose plugins/devteam/ is not a project (this
              plugin's own repository has that shape)
    fresh     a repository whose devteam/ is scaffolded and not committed
    outside   a directory in no repository
    """
    root = os.path.realpath(tempfile.mkdtemp(prefix="devteam-commitguard-"))
    open(os.path.join(root, "gitconfig"), "w").close()
    env = env_for(root)

    def git(cwd, *args):
        return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                              env=env, check=True).stdout.strip()

    def repo(name, files):
        path = os.path.join(root, name)
        os.makedirs(path)
        git(path, "init", "-q", "-b", "main")
        for rel, body in files.items():
            os.makedirs(os.path.dirname(os.path.join(path, rel)) or path, exist_ok=True)
            with open(os.path.join(path, rel), "w", encoding="utf-8") as fh:
                fh.write(body)
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "A")
        return path

    fx = {"root": root, "gate": GATE}
    proj = fx["proj"] = repo("proj", {"devteam/BOARD.md": "# The board\n", "a.txt": "a\n"})
    git(proj, "branch", "side")
    with open(os.path.join(proj, "a.txt"), "a") as fh:
        fh.write("b\n")
    git(proj, "commit", "-q", "-am", "B")
    fx["B"] = git(proj, "rev-parse", "HEAD")
    with open(os.path.join(proj, "a.txt"), "a") as fh:
        fh.write("l\n")
    git(proj, "commit", "-q", "-am", "L")
    fx["L"] = git(proj, "rev-parse", "HEAD")
    git(proj, "reset", "-q", "--hard", fx["B"])
    fx["K"] = git(proj, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "a refused candidate")
    fx["K2"] = git(proj, "commit-tree", "HEAD^{tree}", "-p", fx["K"], "-m", "another, never out")
    # Detached at K and back: HEAD's reflog now records K, and main's does not. A
    # reflog test that read HEAD's would pass what a detour laundered.
    git(proj, "checkout", "-q", "--detach", fx["K"])
    git(proj, "checkout", "-q", "main")
    git(proj, "update-ref", "refs/remotes/origin/feature", fx["K"])
    git(proj, "update-ref", "refs/remotes/origin/held", fx["B"])
    git(proj, "config", "alias.ci", "commit")
    git(proj, "config", "alias.sci", "!git commit")
    git(proj, "config", "alias.lg", "log --oneline")
    fx["detached"] = os.path.join(root, "detached")
    git(proj, "worktree", "add", "-q", "--detach", fx["detached"], fx["K"])
    with open(os.path.join(fx["detached"], "a.txt"), "a") as fh:
        fh.write("stashed\n")
    git(fx["detached"], "stash", "-q")
    fx["sidewt"] = os.path.join(root, "sidewt")
    git(proj, "worktree", "add", "-q", fx["sidewt"], "side")
    fx["plain"] = repo("plain", {"a.txt": "a\n"})
    fx["mono"] = repo("mono", {"plugins/devteam/scripts/x.py": "x = 1\n", "README.md": "m\n"})
    fx["monoscripts"] = os.path.join(fx["mono"], "plugins", "devteam", "scripts")
    fx["fresh"] = repo("fresh", {"a.txt": "a\n"})
    os.makedirs(os.path.join(fx["fresh"], "devteam"))
    with open(os.path.join(fx["fresh"], "devteam", "BOARD.md"), "w") as fh:
        fh.write("# The board\n")
    fx["outside"] = os.path.join(root, "outside")
    os.makedirs(fx["outside"])
    return fx, env


def state(fx, env):
    """Everything the hook could change: refs, reflogs, the index, the stash."""
    out = []
    for key in ("proj", "detached", "sidewt"):
        run = lambda *a: subprocess.run(["git", "-C", fx[key], *a], capture_output=True,
                                        text=True, env=env).stdout
        out += [run("for-each-ref"), run("reflog", "--all", "--format=%H %gd"),
                run("status", "--porcelain"), run("stash", "list"), run("ls-files", "-s"),
                run("config", "--list", "--local")]
    return out


# (name, command, where it runs, the family expected or None, extra environment,
#  a fragment the reason must hold, a fragment it must not)
C = lambda name, cmd, cwd, family, env=None, want=None, forbid=None: (
    name, cmd, cwd, family, env or {}, want, forbid)
W, LANDS, TARGET, REPO = ("writes-commit", "lands-unheld-commit", "unresolved-target",
                          "unresolved-repository")
CASES = [
    # --- the known answers first (P-35b): one refusal, one pass ------------------
    C("a-direct-commit-in-a-project-is-refused", "git commit -m x", "proj", W),
    C("fp-a-direct-commit-in-a-repository-with-no-devteam-passes", "git commit -m x",
      "plain", None),

    # --- every form of `git commit` --------------------------------------------------
    C("a-pathspec-commit-is-refused", "git commit -F msg -- a.txt", "proj", W),
    C("git-dash-C-into-a-project-is-refused", "git -C {proj} commit -m x", "plain", W),
    C("cd-into-a-project-then-commit-is-refused", "cd {proj} && git commit -m x", "plain", W),
    C("pushd-into-a-project-then-commit-is-refused", "pushd {proj} && git commit -m x; popd",
      "plain", W),
    C("a-subshell-cd-into-a-project-is-refused", "(cd {proj} && git commit -m x)", "plain", W),
    C("a-subshells-cd-does-not-outlive-it", "(cd {plain}) && git commit -m x", "proj", W),
    C("a-config-option-before-commit-is-refused", "git -c user.name=y commit -m x", "proj", W),
    C("no-pager-then-dash-C-is-refused", "git --no-pager -C {proj} commit -m x", "plain", W),
    C("git-dir-and-work-tree-name-the-project", "git --git-dir={proj}/.git --work-tree={proj} "
      "commit -m x", "outside", W),
    C("GIT_DIR-in-the-commands-environment-names-the-project",
      "GIT_DIR={proj}/.git GIT_WORK_TREE={proj} git commit -m x", "outside", W),
    C("an-amend-is-refused", "git commit --amend --no-edit", "proj", W),
    C("no-verify-is-still-a-commit", "git commit --no-verify -m x", "proj", W),
    C("a-chained-commit-is-refused", "git add a.txt && git commit -m x", "proj", W),
    C("a-piped-commit-is-refused", "git commit -m x 2>&1 | tail -5", "proj", W),
    C("a-commit-inside-if-is-refused", "if git commit -m x; then echo ok; fi", "proj", W),
    C("a-commit-inside-a-loop-is-refused", 'for f in a.txt; do git commit -m x -- "$f"; done',
      "proj", W),
    C("a-directory-the-command-creates-is-inside-the-project",
      "mkdir -p sub/new && cd sub/new && git commit -m x", "proj", W),
    C("the-dashed-form-is-refused", "/usr/lib/git-core/git-commit -m x", "proj", W),
    C("an-absolute-git-is-refused", "/usr/bin/git commit -m x", "proj", W),
    # The variable is set for the COMMAND. The hook reads DEVTEAM_SANDBOX from its own
    # environment, which only the sandbox's mount plan sets.
    C("DEVTEAM_SANDBOX-in-the-text-exempts-nothing", "DEVTEAM_SANDBOX=1 git commit -m x",
      "proj", W),
    C("a-worktree-of-the-project-is-the-project", "git -C {sidewt} commit -m x", "plain", W),
    C("an-uncommitted-scaffold-is-a-project-and-says-whose-commit-it-is", "git commit -m x",
      "fresh", W, want="scaffold's first commit is the client's"),

    # --- variables, as the shell would expand them -----------------------------------
    C("a-variable-assigned-in-the-text-is-followed", 'DTCG_R={proj}; git -C "$DTCG_R" commit -m x',
      "plain", W),
    C("an-exported-variable-reaches-a-child-shell",
      "export DTCG_R={proj}; bash -c 'git -C \"$DTCG_R\" commit -m x'", "plain", W),
    # Not exported, and single-quoted: the child shell sees no DTCG_R, so `git -C ""`
    # runs where the command does -- in the project.
    C("an-unexported-variable-does-not-reach-a-child-shell",
      "DTCG_R={plain}; bash -c 'git -C \"$DTCG_R\" commit -m x'", "proj", W),
    C("fp-a-double-quoted-variable-is-expanded-before-the-child-shell",
      "DTCG_R={plain}; bash -c \"git -C $DTCG_R commit -m x\"", "proj", None),

    # --- wrappers, shells and substitutions --------------------------------------------
    C("env-before-git-is-refused", "env GIT_AUTHOR_NAME=y git commit -m x", "proj", W),
    C("env-dash-C-into-the-project-is-refused", "env -C {proj} git commit -m x", "plain", W),
    C("command-before-git-is-refused", "command git commit -m x", "proj", W),
    C("builtin-cd-moves-this-shell", "builtin cd {proj} && git commit -m x", "plain", W),
    C("timeout-before-git-is-refused", "timeout 60 git commit -m x", "proj", W),
    C("nohup-before-git-is-refused", "nohup git commit -m x", "proj", W),
    C("sudo-before-git-is-refused", "sudo -u root git commit -m x", "proj", W),
    C("xargs-before-git-is-refused", "xargs -a list git commit -m x", "proj", W),
    C("watch-runs-a-shell-string", "watch -n 5 git commit -m x", "proj", W),
    C("flock-dash-c-runs-a-shell-string", "flock /tmp/l -c 'git commit -m x'", "proj", W),
    C("sh-dash-c-is-refused", "sh -c 'git commit -m x'", "proj", W),
    C("bash-dash-lc-with-its-own-cd-is-refused", 'bash -lc "cd {proj} && git commit -m x"',
      "plain", W),
    C("eval-is-refused", 'eval "git commit -m x"', "proj", W),
    C("a-command-substitution-runs", "echo $(git commit -m x)", "proj", W),
    C("a-backtick-substitution-runs", "echo `git commit -m x`", "proj", W),
    C("a-heredoc-fed-to-a-shell-runs", "bash <<'EOF'\ngit commit -m x\nEOF", "proj", W),
    C("a-here-string-fed-to-a-shell-runs", 'bash <<< "git commit -m x"', "proj", W),
    C("a-substitution-in-an-unquoted-heredoc-runs", "cat <<EOF\n$(git commit -m x)\nEOF",
      "proj", W),
    C("fp-a-substitution-in-a-quoted-heredoc-is-data",
      "cat > notes.md <<'EOF'\n$(git commit -m x)\nEOF", "proj", None),
    C("fp-a-quoted-heredoc-to-cat-is-data", "cat > notes.md <<'EOF'\ngit commit -m x\nEOF",
      "proj", None),
    C("fp-a-quoted-string-mentioning-a-commit-is-data", 'echo "git commit -m x"', "proj", None),
    C("fp-grep-for-a-commit-is-a-read", 'grep -rn "git commit" .', "proj", None),
    C("fp-a-child-shell-that-echoes-is-not-a-commit", "bash -c 'echo git commit'", "proj", None),
    C("fp-command-dash-v-runs-nothing", "command -v git && git status", "proj", None),
    C("fp-a-comment-is-not-a-command", "git status  # then: git add a.txt && git commit -m x",
      "proj", None),

    # --- aliases -------------------------------------------------------------------------
    C("an-alias-for-commit-is-refused", "git ci -m x", "proj", W),
    C("a-shell-alias-that-commits-is-refused", "git sci -m x", "proj", W),
    C("an-alias-given-on-the-command-line-is-refused", "git -c alias.zz=commit zz -m x",
      "proj", W),
    C("fp-an-alias-for-log-passes", "git lg", "proj", None),

    # --- the other commands that write a commit ---------------------------------------
    C("merge-is-refused", "git merge side", "proj", W, want="--squash"),
    C("merge-no-commit-can-still-fast-forward", "git merge --no-commit side", "proj", W),
    C("merge-continue-is-refused", "git merge --continue", "proj", W),
    C("cherry-pick-is-refused", "git cherry-pick side", "proj", W, want="--no-commit"),
    C("cherry-pick-continue-is-refused", "git cherry-pick --continue", "proj", W),
    C("revert-is-refused-and-says-how", "git revert HEAD", "proj", W,
      want="git revert --quit"),
    C("am-is-refused", "git am patch.mbox", "proj", W, want="git apply"),
    C("rebase-is-refused", "git rebase side", "proj", W, want="client's to do"),
    C("pull-is-refused", "git pull", "proj", W),
    C("commit-tree-is-refused", "git commit-tree HEAD^{{tree}} -p HEAD -m x", "proj", W,
      want="checks left out"),
    C("filter-branch-is-refused", "git filter-branch --tree-filter true HEAD", "proj", W),
    C("fp-revert-no-commit-passes", "git revert --no-commit HEAD", "proj", None),
    C("fp-revert-dash-n-passes", "git revert -n HEAD", "proj", None),
    C("fp-revert-quit-passes", "git revert --quit", "proj", None),
    C("fp-cherry-pick-no-commit-in-a-cluster-passes", "git cherry-pick -xn side", "proj", None),
    C("fp-cherry-pick-abort-passes", "git cherry-pick --abort", "proj", None),
    C("fp-merge-abort-passes", "git merge --abort", "proj", None),
    C("fp-merge-squash-passes", "git merge --squash side", "proj", None),
    C("fp-merge-no-commit-no-ff-passes", "git merge --no-commit --no-ff side", "proj", None),
    C("fp-rebase-abort-passes", "git rebase --abort", "proj", None),
    C("fp-am-abort-passes", "git am --abort", "proj", None),

    # --- a branch pointed at a commit no branch holds --------------------------------
    C("reset-soft-to-a-refused-candidate-is-refused", "git reset --soft {K}", "proj", LANDS,
      want="no branch holds"),
    C("reset-keep-to-it-is-refused", "git reset --keep {K}", "proj", LANDS),
    C("a-variable-naming-it-is-followed", 'DTCG_SHA={K}; git reset --soft "$DTCG_SHA"', "proj", LANDS),
    C("update-ref-with-a-reason-is-refused",
      'git update-ref -m "moved by hand" refs/heads/main {K}', "proj", LANDS),
    C("a-redirection-does-not-hide-the-target", "git reset --soft {K} 2>/dev/null", "proj",
      LANDS),
    C("update-ref-of-the-branch-is-refused", "git update-ref refs/heads/main {K}", "proj", LANDS),
    C("update-ref-of-an-attached-HEAD-moves-the-branch", "git update-ref HEAD {K}", "proj",
      LANDS),
    C("branch-force-is-refused", "git branch -f side {K}", "proj", LANDS),
    C("creating-a-branch-at-it-is-refused", "git branch newb {K}", "proj", LANDS),
    C("checkout-b-at-it-is-refused", "git checkout -b newb {K}", "proj", LANDS),
    C("checkout-B-at-it-is-refused", "git checkout -B main {K}", "proj", LANDS),
    C("switch-c-at-it-is-refused", "git switch -c newb {K}", "proj", LANDS),
    # THE LAUNDERING ROUTE. Detach HEAD at the candidate, then create a branch "at
    # HEAD". Counting HEAD as held would let this through, and then `checkout -B
    # main` would too. A detached HEAD is not a branch, so it holds nothing.
    C("a-branch-created-at-a-detached-HEAD-on-it-is-refused", "git switch -c newb",
      "detached", LANDS),
    C("worktree-add-b-at-it-is-refused", "git worktree add -b newb {root}/wt2 {K}", "proj",
      LANDS),
    C("stash-branch-on-it-is-refused", "git stash branch newb", "proj", LANDS),
    C("fetch-from-this-repository-into-a-branch-is-refused",
      "git fetch . {K}:refs/heads/newb", "proj", LANDS),
    C("push-to-this-repository-into-a-branch-is-refused", "git push . {K}:newb", "proj",
      LANDS),
    C("fetch-from-outside-into-a-branch-is-refused", "git fetch origin main:main", "proj",
      LANDS, want="fetched from outside"),
    C("checkout-guessing-a-remote-branch-at-it-is-refused", "git checkout feature", "proj",
      LANDS),
    C("checkout-track-at-it-is-refused", "git checkout --track origin/feature", "proj", LANDS),
    # P-12b's recovery: the original commit, from the branch's own reflog.
    C("fp-reset-soft-to-a-commit-from-the-reflog-passes", "git reset --soft {L}", "proj", None),
    C("fp-reset-soft-to-an-ancestor-passes", "git reset --soft HEAD~1", "proj", None),
    C("fp-reset-of-a-path-passes", "git reset -- a.txt", "proj", None),
    C("fp-reset-of-a-path-without-dashes-passes", "git reset a.txt", "proj", None),
    C("fp-reset-to-HEAD-passes", "git reset", "proj", None),
    C("fp-reset-of-paths-from-a-commit-passes", "git reset {K} a.txt", "proj", None),
    C("fp-reset-of-paths-from-a-commit-after-dashes-passes", "git reset {K} -- a.txt", "proj",
      None),
    # K2 is in no reflog at all, HEAD's included, so only "a detached HEAD is not a
    # branch" lets this through.
    C("fp-moving-a-detached-HEAD-passes", "git reset --soft {K2}", "detached", None),
    C("fp-update-ref-deleting-a-sandbox-ref-passes",
      "git update-ref -d refs/devteam/sandbox/x", "proj", None),
    C("fp-update-ref-of-a-ref-that-is-not-a-branch-passes",
      "git update-ref refs/devteam/sandbox/x {K}", "proj", None),
    C("fp-update-ref-no-deref-detaches-and-moves-no-branch",
      "git update-ref --no-deref HEAD {K}", "proj", None),
    C("fp-a-branch-at-HEAD-passes", "git branch newb", "proj", None),
    C("fp-branch-force-to-a-commit-main-holds-passes", "git branch -f side HEAD", "proj", None),
    C("fp-listing-branches-that-contain-it-passes", "git branch --contains {K}", "proj", None),
    C("fp-deleting-a-branch-passes", "git branch -D side", "proj", None),
    C("fp-renaming-a-branch-passes", "git branch -m side side2", "proj", None),
    C("fp-checkout-b-at-HEAD-passes", "git checkout -b newb", "proj", None),
    C("fp-switch-c-at-HEAD-passes", "git switch -c newb", "proj", None),
    C("fp-switching-to-a-branch-passes", "git switch side", "proj", None),
    C("fp-checking-out-a-path-passes", "git checkout -- a.txt", "proj", None),
    C("fp-detaching-at-it-passes", "git checkout {K}", "proj", None),
    C("fp-guessing-a-remote-branch-at-a-held-commit-passes", "git checkout held", "proj", None),
    C("fp-worktree-add-at-HEAD-passes", "git worktree add {root}/wt3", "proj", None),
    C("fp-fetching-into-a-sandbox-ref-passes",
      "git fetch /tmp/x/meta/commits.bundle HEAD:refs/devteam/sandbox/x", "proj", None),
    C("fp-fetching-HEAD-into-a-branch-passes", "git fetch . HEAD:refs/heads/newb", "proj", None),
    C("fp-a-tag-is-not-a-branch", "git tag v1 {K}", "proj", None),

    # --- what the text does not say -----------------------------------------------------
    C("update-ref-stdin-is-refused", "git update-ref --stdin", "proj", TARGET),
    C("a-target-from-a-substitution-is-refused", 'git reset --soft "$(cat sha.txt)"', "proj",
      TARGET),
    C("a-branch-from-a-substitution-is-refused",
      'git update-ref "$(cat ref.txt)" {K}', "proj", TARGET),
    C("an-unreadable-directory-in-a-project-session-is-refused",
      'git -C "$(cat where.txt)" commit -m x', "proj", REPO),
    C("cd-dash-in-a-project-session-is-refused", "cd - && git commit -m x", "proj", REPO),
    C("an-unreadable-directory-where-the-session-is-a-project-is-refused",
      'git -C "$(cat where.txt)" commit -m x', "plain", REPO,
      env={"CLAUDE_PROJECT_DIR": "{proj}"}),
    C("fp-an-unreadable-directory-in-no-project-session-passes",
      'git -C "$(cat where.txt)" commit -m x', "plain", None,
      env={"CLAUDE_PROJECT_DIR": "{plain}"}),
    # Its own failure: more nesting than it will read, in a project session.
    C("the-guard-fails-closed-in-a-project", "eval " * 10 + "git status", "proj",
      "guard-failed"),
    C("fp-its-own-failure-outside-a-project-passes", "eval " * 10 + "git status", "plain",
      None, env={"CLAUDE_PROJECT_DIR": "{plain}"}),

    # --- what is never refused ------------------------------------------------------------
    C("fp-the-gate-itself-passes", "python3 {gate} commit -F msg -- a.txt", "proj", None),
    C("fp-a-worker-in-a-sandbox-passes", "git commit -m x", "proj", None,
      env={"DEVTEAM_SANDBOX": "probe1"}),
    C("fp-the-off-switch-passes", "git commit -m x", "proj", None,
      env={"DEVTEAM_COMMIT_GUARD": "off"}),
    C("fp-commit-help-passes", "git commit --help", "proj", None),
    C("fp-commit-dash-h-passes", "git commit -h", "proj", None),
    C("fp-git-help-commit-passes", "git help commit", "proj", None),
    C("fp-commit-dry-run-passes", "git commit --dry-run -- a.txt", "proj", None),
    C("fp-git-log-passes", "git log --oneline -3", "proj", None),
    C("fp-git-log-grep-commit-passes", "git log --grep=commit -- a.txt", "proj", None),
    C("fp-git-status-passes", "git status", "proj", None),
    C("fp-git-diff-passes", "git diff HEAD", "proj", None),
    C("fp-git-show-passes", "git show HEAD", "proj", None),
    C("fp-commit-graph-is-not-commit", "git commit-graph write", "proj", None),
    C("fp-stash-passes", "git stash", "proj", None),
    C("fp-notes-pass", "git notes add -m x", "proj", None),
    C("fp-bisect-passes", "git bisect start", "proj", None),
    C("fp-dash-C-to-a-repository-with-no-devteam-passes", "git -C {plain} commit -m x",
      "proj", None),
    C("fp-cd-to-a-repository-with-no-devteam-passes", "cd {plain} && git commit -m x", "proj",
      None),
    # guard.py's walk upward would call plugins/ a project here. The gate would not.
    C("fp-a-plugins-devteam-directory-is-not-a-project", "git commit -m x", "monoscripts",
      None),
    C("fp-a-directory-in-no-repository-passes", "git commit -m x", "outside", None),
]


def run(case, fx):
    name, cmd, cwd, family, extra, want, forbid = case
    fmt = lambda s: s.format(**fx)
    env = env_for(fx["root"], CLAUDE_PROJECT_DIR=fx[cwd])
    env.update({k: fmt(v) for k, v in extra.items()})
    payload = {"tool_name": "Bash", "cwd": fx[cwd], "session_id": "control",
               "tool_input": {"command": fmt(cmd)}}
    p = subprocess.run([sys.executable, SUBJECT], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, timeout=60)
    reason = ""
    if p.stdout.strip():
        try:
            reason = json.loads(p.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        except (ValueError, KeyError, TypeError):
            return f"printed something that is not a decision: {p.stdout.strip()[:200]}"
    if p.returncode != 0 or p.stderr.strip():
        return f"exit {p.returncode}: {p.stderr.strip()[-300:]}"
    got = reason.split("]", 1)[0].split("[", 1)[1] if reason.startswith("Refused [") else None
    if reason and got is None:
        return f"refused without naming a family: {reason[:200]}"
    if got != family:
        return (f"{'refused as ' + got if got else 'allowed'}, expected "
                f"{'refused as ' + family if family else 'allowed'}"
                + (f"\n        | {reason[:240]}" if reason else ""))
    if want and want not in reason:
        return f"refused, but the reason never says {want!r}\n        | {reason[:240]}"
    if forbid and forbid in reason:
        return f"the reason says {forbid!r}"
    return None


def main():
    fx, env = build()
    passed = failed = 0
    extra = []
    try:
        before = state(fx, env)
        for case in CASES:
            problem = run(case, fx)
            if problem:
                failed += 1
                print(f"FAIL  {case[0]}: {problem}")
            else:
                passed += 1

        # Every refusal carries the way through: the gate's command, what its exits
        # ask for, and that nothing else in the call ran.
        payload = {"tool_name": "Bash", "cwd": fx["proj"], "session_id": "control",
                   "tool_input": {"command": "git commit -m x"}}
        p = subprocess.run([sys.executable, SUBJECT], input=json.dumps(payload),
                           capture_output=True, text=True,
                           env=env_for(fx["root"], CLAUDE_PROJECT_DIR=fx["proj"]))
        reason = json.loads(p.stdout or "{}").get("hookSpecificOutput", {}).get(
            "permissionDecisionReason", "")
        missing = [s for s in (f"python3 {GATE} commit -F", "Accepts.", "FORMATS.md",
                               "head-moved", "NONE OF THEM RAN", "sandbox", "(P-49)")
                   if s not in reason]
        extra.append(("every-refusal-names-the-gate-and-its-exits",
                      f"the reason lacks {missing}" if missing else None))

        # A Write is not a commit.
        payload = {"tool_name": "Write", "cwd": fx["proj"], "session_id": "control",
                   "tool_input": {"file_path": os.path.join(fx["proj"], "a.txt")}}
        p = subprocess.run([sys.executable, SUBJECT], input=json.dumps(payload),
                           capture_output=True, text=True, env=env_for(fx["root"]))
        extra.append(("fp-a-write-tool-call-is-not-read",
                      f"printed {p.stdout.strip()[:120]}" if p.stdout.strip() else None))

        extra.append(("the-hook-changes-nothing-in-the-repository",
                      None if state(fx, env) == before else "a ref, reflog, index, stash "
                      "or config in the fixture changed while the hook read it"))

        # ONE TEST OF A DEVTEAM PROJECT, AND IT IS THE GATE'S. A hook that disagreed
        # with gate.locate would refuse a commit the gate then cannot make, or pass
        # one it would have checked.
        said = {}
        for key in ("plain", "monoscripts", "proj"):
            g = subprocess.run([sys.executable, GATE, "commit", "--dry-run", "-m", "x", "--",
                                "a.txt"], cwd=fx[key], capture_output=True, text=True,
                               env=env_for(fx["root"]), timeout=120)
            said[key] = "not a devteam project" in g.stderr
        bad = [k for k, v in (("plain", True), ("monoscripts", True), ("proj", False))
               if said[k] != v]
        extra.append(("agrees-with-the-gate-on-what-a-devteam-project-is",
                      f"gate.locate disagrees for {bad}" if bad else None))

        for name, problem in extra:
            if problem:
                failed += 1
                print(f"FAIL  {name}: {problem}")
            else:
                passed += 1
    finally:
        shutil.rmtree(fx["root"], ignore_errors=True)

    names = [c[0] for c in CASES] + [n for n, _ in extra]
    fp = sum(1 for n in names if n.startswith("fp-"))
    print(f"\ncommit_guard control: {passed} passed, {failed} failed, {len(names)} cases "
          f"({fp} of them false-positive controls, {100 * fp // len(names)}%)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
