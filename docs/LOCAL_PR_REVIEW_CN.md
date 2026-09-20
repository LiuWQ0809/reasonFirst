# 在本地审阅 PR，并更新日常安装

[English](LOCAL_PR_REVIEW.md) · [中文文档索引](README_CN.md)

<!-- Translation source: docs/LOCAL_PR_REVIEW.md @ a3e33c72c55efef6a0dc3808fb9853c62ad15f9d -->

使用 Git，不要手工复制 ZIP 中的文件。区分三个位置：本项目的源码仓库、用户配置，以及受管 GitLab 工作区根目录。切换源码 ref 不会应用或撤销配置迁移。

## 不干扰原检出目录的审阅方式

先在现有 ReasonFirst 克隆目录中检查：

```bash
git status --short
```

保留尚未提交的工作。下面以 PR 12 为例，并明确记录其审阅时的 head。审阅其他 PR 时，必须根据对应审阅记录，**同时替换** PR 编号和预期 SHA。括号中的代码块适用于 Bash/zsh，不含会影响交互式粘贴的注释：

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

Fetch 会更新共享的 Git 对象与 `FETCH_HEAD`；新工作树拥有独立的文件和索引。它不会切换或重置原工作树。执行这段短流程时，不要同时运行其他会竞争修改共享 `FETCH_HEAD` 的 fetch。审阅目录已经存在时，应停止并检查，而不是覆盖。

继续上述示例：

```bash
cd ../reasonFirst-pr12-review
uv sync --python 3.12
uv run actual-coder-migrate-https --help
uv run python -m unittest discover -s tests -v
uv run python scripts/check_repo_secrets.py --history
```

测试使用构造的本地测试数据。不要复制真实的受管工作区目录来演练迁移：其中的绝对路径元数据和 Git 链接可能仍指向原安装。

已安装 GitHub CLI 时，可以在**干净或可丢弃的检出目录内**使用 `gh pr checkout 12 --repo phoenixjyb/reasonFirst`。它会切换该目录的分支，不等同于新增独立 worktree。处于 detached HEAD 状态并要修改代码时，应先创建开发分支再提交。向 PR 分支推送会更新 PR，此前只针对旧 head 的测试结论不能自动用于新 head。

## 合并后回到日常源码安装

下列步骤更新源码和依赖，不修改 GitLab URL 或凭证。在长期使用的原克隆目录中，先保存待处理的源码修改，停止导入该目录代码的进程，并检查当前分支与 origin。不要用 `reset --hard`、强制 checkout、cleanup 或重新克隆来解决不确定状态。

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

`origin` 必须是预期的源码仓库。如果 `main` 已被另一个 worktree 检出，或本地历史发生分叉，应停止并检查，不要强制执行。仅运行 `uv sync` 只会更新该检出目录的环境，不会更新独立的全局工具环境。

使用全局用户安装时，从这个稳定检出目录重新安装：

```bash
bash scripts/install_user.sh
actual-coder config
actual-coder-migrate-https --help
```

Windows 使用 `scripts/install_user.ps1`。安装器采用 editable 方式，可能替换命令入口；应检查其源码路径，并保留现有用户 `.env`。升级时绝不能用 `.env.example` 覆盖可用配置。另行重启原有 MCP/Tunnel 启动器，并检查服务或环境变量覆盖；重启 shell 不等于重启服务。

在确认没有全局安装或服务指向审阅目录之前，保留该目录。通过普通 `git worktree remove` 删除之前，先保全其中的审阅提交；工作树干净不代表未发布提交可以丢弃。完成迁移本身不要求删除审阅目录。

## 复制粘贴故障排查

交互式 zsh 在 `do` 附近报解析错误时，使用上面的无注释代码块。不要把说明文字或 `[URL](URL)` 这样的 Markdown 链接作为 shell 参数粘贴进去。使用代码块的复制按钮和纯 URL。不要把未加引号的尖括号占位符当作 shell 命令。逐条运行并检查错误，不要串联破坏性的恢复步骤。

参考：[Git worktree](https://git-scm.com/docs/git-worktree)、[GitHub CLI PR checkout](https://cli.github.com/manual/gh_pr_checkout)、[uv 工具环境](https://docs.astral.sh/uv/concepts/tools/)。
