# ReasonFirst

[English](README.md) · **简体中文** · [中文文档索引](docs/README_CN.md)

<!-- Translation source: README.md @ a3e33c72c55efef6a0dc3808fb9853c62ad15f9d -->

> **推理优先的编程编排。**
> 让你最强的推理模型负责推理，让编程代理负责写代码。

[![CI](https://github.com/phoenixjyb/reasonFirst/actions/workflows/ci.yml/badge.svg)](https://github.com/phoenixjyb/reasonFirst/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

ReasonFirst 将交互式工程推理、可替换的编程代理和本地 GitLab 工作流程连接起来。人和选定的推理界面共同定义任务；**ActualCoder** 准备 Git worktree，将任务交给 **Codex CLI** 或 **GitHub Copilot CLI**，并提供验证、Merge Request 和 CI 证据供审查。

目标是把推理能力用于架构、诊断与审查，把实现迭代交给编程代理。ReasonFirst 不是模型代理、额度转移服务或自动合并机器人。它不直接调用模型推理接口；外部编程工具沿用各自的认证与计费方式。节省成本是设计目标，不是已经测得的保证。

**这是早期开发工具：**请在可信开发机上使用可信仓库。Git worktree 不是安全沙箱。在使用真实凭证或执行仓库代码前，请阅读 [SECURITY_CN.md](SECURITY_CN.md)。

## 从这里开始

| 目标 | 指南 |
| --- | --- |
| 分清推理、传输和编程各自发生在哪里 | [一个推理界面，一套实现流程](docs/WORKFLOW_CN.md) |
| 安装并执行第一个任务 | [当前中文快速上手](docs/QUICKSTART_CN.md) · [English](docs/ACTUAL_CODER_QUICKSTART.md) |
| 连接或重启普通 ChatGPT 的 GitLab 读取 | [中文接入与重启](docs/OPENAI_TUNNEL_TEAM_SETUP_CN.md) · [English](docs/SETUP_TUTORIAL.md) |
| 交接已批准要求并返回证据 | [人工任务交接模板](docs/TASK_HANDOFF_TEMPLATE_CN.md) |
| 理解架构 | [设计理念](docs/DESIGN_PHILOSOPHY_CN.md) |
| 将现有 GitLab 安装迁移至 HTTPS | [中文迁移指南](docs/HTTPS_MIGRATION_CN.md) · [English](docs/HTTPS_MIGRATION.md) |
| 配置 API/MCP 证书并理解重定向错误 | [运行时 TLS](docs/HTTPS_API_TLS_CN.md) · [English](docs/HTTPS_API_TLS.md) |
| 直接检出 PR，不手工复制 ZIP | [本地 PR 审阅](docs/LOCAL_PR_REVIEW_CN.md) |
| 贡献或报告问题 | [贡献指南](CONTRIBUTING_CN.md) · [安全报告](SECURITY_CN.md) |
| 区分当前与历史文档 | [中文文档索引](docs/README_CN.md) |

## 工作原理

```text
人 + 推理界面
  明确目标、约束和验收标准
                  |
                  v
ActualCoder / gitlab-agent
  准备工作区和有边界的任务交接
                  |
                  v
Codex CLI 或 Copilot CLI
  检查 -> 实现 -> 测试
                  |
                  v
finish 审阅 -> 功能分支 / GitLab MR -> CI 证据
                  |
                  v
人 + 推理界面审查，并决定下一步
```

可选的只读 GitLab MCP bridge 让推理客户端读取仓库、MR 和 CI。**当前不能通过 MCP 提交或执行本地编程任务。** 由人工操作本地 CLI，在界面之间传递任务与结果上下文。持久化任务规格和统一证据 API 仍在规划中，尚未交付。

**推荐的 ChatGPT 工作流程不需要 localhost Assistant。** 使用普通 ChatGPT 对话推理与审查；Tunnel 读取连接依赖运行中的 `tunnel-client` 和 `server.py`；实现工作由 ActualCoder 配合选定编程 CLI 完成。本地仪表盘 Overview/Logs 仅供可选诊断。Assistant 标签页和 Codex Tunnel 插件不是上手要求或验收门槛。不使用该界面，不等于卸载编程 CLI，也不保证上游附带的后台辅助进程被禁用。

读取验收应在普通 ChatGPT 中实时调用身份与文件工具，而不是查看 `/ui#codex` 的回答。[工作流程指南](docs/WORKFLOW_CN.md)区分了启动、API/Git 访问、读取验收和已批准写入。[人工交接模板](docs/TASK_HANDOFF_TEMPLATE_CN.md)是写作辅助，不是已实现的 TaskSpec/EvidencePack 格式。

GitLab 是当前目标源码管理与 CI 集成。本项目源码托管于 GitHub，不代表已有面向 GitHub 的任务适配器。架构意图是供应商中立，目前实现的编程适配器是 `codex` 和 `copilot`。

## 无生产凭证试用源码

安装 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。包元数据要求 Python 3.10+，当前 CI 矩阵在 Ubuntu、macOS 和 Windows 上测试 Python 3.12。复现 CI 时使用 3.12。

在新检出目录中逐条运行，遇错停止：

```bash
git clone https://github.com/phoenixjyb/reasonFirst.git
cd reasonFirst
uv sync --python 3.12
uv run actual-coder --help
uv run actual-coder-migrate-https --help
uv run python -m unittest discover -s tests -v
uv run python scripts/check_repo_secrets.py --history
```

这些回归测试使用临时仓库、模拟服务和本地回环 TLS 测试环境，不需要生产令牌或付费模型会话。安装依赖可能访问软件包索引。不要把测试环境指向真实工作区。

实际使用时，按[快速上手](docs/QUICKSTART_CN.md)配置自己的 GitLab HTTPS 端点、最小权限令牌、明确项目允许列表和受支持的编程 CLI。纯本地工作流程不要求 MCP/Tunnel。

## 推荐的任务循环

在 ReasonFirst 源码检出目录中使用 `uv run`，确保执行的是该目录的环境。将 `team/project-a` 和示例 workspace ID 替换为实际值。

```bash
uv run actual-coder start team/project-a --task fix-timeout --goal "Fix the timeout bug; preserve the public API and add regression coverage" --no-launch
```

`--no-launch` 会准备真实的受管工作区和交接，但不调用编程模型。它**不是**无副作用的 dry-run。审阅交接后，使用返回的后端命令和提示词执行任务；也可在新的 `start` 中省略 `--no-launch`，以交互方式直接启动。

实现完成后，对返回的工作区进行审查与 finish：

```bash
WS="012345abcdef"
uv run actual-coder status "$WS"
uv run actual-coder finish "$WS" --message "fix: handle timeout and add regression test" --dry-run
uv run actual-coder finish "$WS" --message "fix: handle timeout and add regression test"
uv run actual-coder ci "$WS"
```

只有检查预览并确认写入符合意图后，才运行实际 `finish`。**Finish dry-run 仍会运行项目配置的验证命令；它意味着不提交/推送，而不是不执行代码。** 缺少 `.actualcoder.yaml` 是允许的，但没有项目专用验证命令。依赖 finish 作为质量门槛前，应先加入真实构建和测试要求。

对于真实 CI 失败，`resume --from-ci` 返回与 HEAD 匹配的 CI 交接，不会自动启动修复。CI 成功不是凭空修改代码的理由。低层 `commit`/`push` 和部分现有生成交接仍暴露手工路径；这些路径**不执行**全部 finish 门槛。应审查执行者操作，并将 `finish` 作为主要流程。

## `main` 上已有的能力

最近一个文档记录的发布版本为 **v0.3.0**。下面的发布后变更是已合并源码，包版本元数据仍为 `0.3.0`。报告问题时，同时记录 commit SHA 和版本。参见 [CHANGELOG.md](CHANGELOG.md)。

| 能力 | 当前范围 |
| --- | --- |
| 受管工作区 | 本地 Git 缓存/worktree、功能分支、MR 创建/更新/恢复 |
| 受控 finish | Base 策略验证、可审阅性/受保护路径检查、候选与有界提交历史秘密扫描、人工确认 |
| 发布安全 | 普通 cleanup 前获取新鲜远端证据；保留含未发布提交的遗留分支 |
| 命令结果 | 将子进程非零退出和超时反映到 shell |
| CI 反馈 | 与 HEAD 匹配的证据，以及 CLI/MCP 共享的有界、脱敏失败 job 日志 |
| HTTPS 迁移 | 显式离线预览与确认后本地 URL 更新，附带私有备份和向前恢复 |
| API/MCP 传输 | 验证公共根证书，可选仅供 Python 使用的私有 CA；请求目的地检查，并拒绝全部 API 重定向 |
| 只读 MCP | 检查项目、文件、MR、流水线和 job；无本地任务执行接口 |

**尚未交付：**原生 Git 信任/目的地策略集成与 API/Git 分层诊断、所有交接入口一致的项目上下文、通用工作区锁与事务式恢复、持久化 TaskSpec/执行尝试记录，以及 EvidencePack 访问。仅用于迁移的锁不提供这些能力。[HTTPS 工作](https://github.com/phoenixjyb/reasonFirst/issues/10)和[任务循环路线图](https://github.com/phoenixjyb/reasonFirst/issues/6)负责跟踪。

**传输升级：**Python API/MCP 客户端拒绝 `GITLAB_VERIFY_SSL=false` 和所有 API 重定向，包括同源跳转。请直接配置最终端点。使用私有 CA 时，`GITLAB_CA_BUNDLE` 将证书加入公共根信任，无需启用代理环境继承。它不配置原生 Git，也不配置迁移命令可选的 `--check-tls` 探测。使用受公共信任证书的部署通常无需额外 CA 设置。详见[运行时 TLS](docs/HTTPS_API_TLS_CN.md)。

## 名称与兼容性

**ReasonFirst** 是项目名；**ActualCoder**（`actual-coder`）是高层 CLI。`gitlab-agent` 是低层控制器，`codingagent` 是兼容别名。Python 包 `gitlab_agent`、分发名 `chatgpt-selfhosted-gitlab-mcp`、用户配置 `~/.config/gitlab-agent/.env` 和已有工作区路径被有意保留。不要在更新源码时重命名受管目录。

用户安装器采用 editable 方式：全局命令跟随其安装来源的源码检出目录。让该目录停留在已审阅 ref，PR 实验使用独立 worktree。参见[本地 PR 审阅](docs/LOCAL_PR_REVIEW_CN.md)，无需手工复制下载文件即可更新日常安装。

## 贡献与许可证

欢迎贡献、可复现问题报告、文档改进和回归测试。中文和英文报告均欢迎，详见 [CONTRIBUTING_CN.md](CONTRIBUTING_CN.md)。不要在公开 Issue 中附上私有仓库、原始凭证、迁移备份或未经审查的日志。

采用 **Apache License 2.0**，以 [LICENSE](LICENSE) 为准。外部编程工具与服务有各自的许可和条款。本项目独立维护，不是 OpenAI、GitHub 或 GitLab 的官方产品。维护者应在宣布发布前检查[公开发布清单](docs/PUBLIC_RELEASE_CHECKLIST_CN.md)。
