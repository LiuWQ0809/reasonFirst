# Review a PR locally and update the normal installation

Use Git, not manual ZIP copying. Keep three things distinct: this source repository, the per-user config, and the managed GitLab-workspace root. Switching the source ref does not apply or undo configuration migrations.

## Review without disturbing the original checkout

From your existing ReasonFirst clone, inspect it first:

```bash
git status --short
```

Keep any pending work. The following example uses PR 12, whose reviewed head is recorded explicitly. For another PR, replace **both** the PR number and expected SHA using its review record. The parenthesized block works in Bash/zsh and contains no interactive comments:

```bash
(
set -eu
PR=12
EXPECTED="53cd68d5f63674362fc96b371a03baaa45da671c"
REVIEW_DIR="../reasonFirst-pr${PR}-review"
test ! -e "$REVIEW_DIR"
test ! -L "$REVIEW_DIR"
git fetch --no-tags https://github.com/phoenixjyb/reasonFirst.git "refs/pull/${PR}/head"
ACTUAL="$(git rev-parse FETCH_HEAD)"
if [ "$ACTUAL" != "$EXPECTED" ]; then
  printf 'PR head changed. Expected %s; got %s\n' "$EXPECTED" "$ACTUAL"
  exit 1
fi
git worktree add --detach "$REVIEW_DIR" "$EXPECTED"
)
```

The fetch updates shared Git objects/FETCH_HEAD; the new worktree has its own files/index. It does not switch or reset the original worktree. Do not run competing fetches against shared `FETCH_HEAD` during this short sequence. Stop and inspect an existing review directory, not overwrite it.

Then, for this example:

```bash
cd ../reasonFirst-pr12-review
uv sync --python 3.12
uv run actual-coder-migrate-https --help
uv run python -m unittest discover -s tests -v
uv run python scripts/check_repo_secrets.py --history
```

Tests use synthetic local fixtures. Do not copy your real managed-workspace directory to rehearse a migration: its absolute metadata and Git links can still point to the original installation.

With GitHub CLI installed, `gh pr checkout 12 --repo phoenixjyb/reasonFirst` is an alternative **inside a clean/disposable checkout**. It changes that checkout's branch; do not treat it as the same operation as adding a separate worktree. For code changes while detached, create a development branch before committing. Pushing to a PR branch updates the PR and invalidates any earlier head-specific test claim.

## Return to a normal source installation after merge

These steps update source/dependencies, not GitLab URLs or credentials. In the original long-lived clone, save pending source edits, stop processes importing this checkout, and inspect the current branch and origin. Do not use `reset --hard`, force checkout, cleanup, or reclone to resolve uncertainty.

```bash
git status --short
git remote -v
git fetch origin
git switch main
git pull --ff-only origin main
uv sync --python 3.12
uv run actual-coder --help
uv run actual-coder-migrate-https --help
```

`origin` must be the intended source repository. If `main` is checked out in another worktree or has diverged, stop and inspect; do not force the operation. `uv sync` alone updates this checkout's environment, not a separate global tool environment.

If you use the global user installation, reinstall from this stable checkout:

```bash
bash scripts/install_user.sh
actual-coder config
actual-coder-migrate-https --help
```

On Windows, use `scripts/install_user.ps1` instead. The installers are editable and can replace command entry points; verify their source path and preserve the existing user `.env`. Never copy `.env.example` over a working config during an upgrade. Restart the existing MCP/tunnel launcher separately, checking service/environment overrides; restarting a shell does not restart a service.

Keep the review checkout until you know no global installation or service points at it. Preserve any review commits before removing it with normal `git worktree remove`; a clean working tree alone does not prove unpublished commits are expendable. There is no need to remove it just to finish a migration.

## Copy/paste troubleshooting

If interactive zsh reports a parse error near `do`, use the comment-free code blocks above. Do not paste prose or Markdown links such as `[URL](URL)` into shell arguments. Use the code block's copy button and plain URLs. Do not paste an angle-bracket placeholder unquoted as a shell command. Run commands one at a time and inspect errors rather than chaining destructive recovery steps.

References: [Git worktree](https://git-scm.com/docs/git-worktree), [GitHub CLI PR checkout](https://cli.github.com/manual/gh_pr_checkout), [uv tool environments](https://docs.astral.sh/uv/concepts/tools/).
