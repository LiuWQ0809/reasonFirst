# ReasonFirst

[English](README.md) · **简体中文** · **[首次完整接入](docs/GETTING_STARTED_CN.md)** · [文档索引](docs/README_CN.md)

<!-- Paired with README.md in this change; base 61f464ebbb8906817e32802be22df4012881ece5. -->

> **推理优先的编程编排。**
> 让你最强的推理模型负责推理，让编程代理负责写代码。

[![CI](https://github.com/phoenixjyb/reasonFirst/actions/workflows/ci.yml/badge.svg)](https://github.com/phoenixjyb/reasonFirst/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

ReasonFirst 将交互式工程推理、可替换编程代理和本地 GitLab 流程连接起来。人和选定的推理界面共同定义任务；**ActualCoder** 准备 Git worktree，将任务交给 **Codex CLI** 或 **GitHub Copilot CLI**，并提供验证、Merge Request 和 CI 证据供审阅。

目标是将推理能力用于架构、诊断和审查，把实现迭代交给编程代理。ReasonFirst 不是模型代理、额度转移服务或自动合并机器人。不直接调用模型推理接口，外部编程工具沿用各自认证和计费方式。节省成本是设计目标，不是已测得的保证。

**这是早期开发工具：**在可信开发机使用可信仓库，Git worktree 不是安全沙箱。使用真实凭证或执行仓库代码前，阅读 [SECURITY_CN.md](SECURITY_CN.md)。MCP 端点保持私有，不意味着选定数据不会返回给推理服务；应获得相应数据共享批准。

## 从这里开始：先接通，再让 ChatGPT 工作

**按顺序完成[首次完整接入指南](docs/GETTING_STARTED_CN.md)（[English](docs/GETTING_STARTED.md)）。** 指南包括安装命令、每种凭证的来源、Keychain 保存、本地 profile、服务启动、ChatGPT 应用选择，以及实时仓库读取测试。不应再依赖翻找以前的聊天记录拼接配置。

| 准备内容 | 为什么需要 |
| --- | --- |
| Git、uv/Python、ReasonFirst、单独的 `tunnel-client` | 新的管理助手不会安装上游隧道客户端。 |
| GitLab 地址、确认的项目/ref/文件、只读 token、本地明确 allowlist | 提议的项目名称或本地目录不能证明远端存在或有权访问。 |
| OpenAI Platform 隧道权限、Tunnel ID、runtime API key | 隧道标识与运行认证不是同一个值。 |
| ChatGPT 自定义应用/developer mode 权限与 workspace 关联 | 本地隧道运行不等于已经加入当前对话。 |
| Keychain 或其他明确、受支持的秘密来源 | 昨天的 shell export 不是持久存储。 |

Codex/Copilot 登录、Git 写权限和 CI runner 是**后续实现阶段**的前置条件，不是 ChatGPT 读取 GitLab 的前置条件。服务资格/权限见接入指南所链官方资料，不以某个订阅名称作保证。ReasonFirst 不直接调用模型 API，不等于隧道不需要 runtime key。

```text
首次：权限 -> 安装 -> GitLab 配置 -> Tunnel ID/key/profile
每次服务停止后：Start -> 本地 Status -> 在普通 ChatGPT 选择应用
每个新项目：gitlab_whoami -> check_project_access -> 固定提交读取
获批任务：ChatGPT 方案 -> 人工交接 -> Codex/ActualCoder -> MR/CI -> 审阅
```

配置完成后，Terminal A 运行 `actual-coder-tunnel start`，Terminal B 运行 `actual-coder-tunnel status`。**保持 Terminal A 运行。** `ready_for_chatgpt_check` 只代表本地就绪，不是端到端验收。在普通 ChatGPT 输入框中选择已有应用，完成指南中的实时身份/预检/文件读取，再开始工作。

**不需要 localhost Assistant。** Overview/Logs 仅为可选诊断。不使用 Assistant UI，不等于卸载 Codex，也不保证上游附带 helper 被禁用。不要为这个可选面板关闭审批控制。

## 按任务选择指南

| 目标 | 指南 |
| --- | --- |
| 从前置条件到第一条 ChatGPT 工作提示词 | **[完整首次接入](docs/GETTING_STARTED_CN.md)** · **[English](docs/GETTING_STARTED.md)** |
| 已配置后的启动/状态/停止/重启 | [隧道生命周期](docs/TUNNEL_LIFECYCLE_CN.md) · [English](docs/TUNNEL_LIFECYCLE.md) |
| 确认新项目存在/可访问并明确授权 | [项目访问](docs/PROJECT_ACCESS_CN.md) · [English](docs/PROJECT_ACCESS.md) |
| 演练推理、worker 和 MR 迭代 | [实战演练](docs/PRACTICE_LAB_CN.md) · [English](docs/PRACTICE_LAB.md) |
| 分清界面职责 | [工作流程](docs/WORKFLOW_CN.md) · [English](docs/WORKFLOW.md) |
| 纯本地安装与受控实现 | [CLI 快速上手](docs/QUICKSTART_CN.md) · [English](docs/ACTUAL_CODER_QUICKSTART.md) |
| 已批准要求与实际结果 | [人工交接模板](docs/TASK_HANDOFF_TEMPLATE_CN.md) · [English](docs/TASK_HANDOFF_TEMPLATE.md) |
| 架构 | [设计理念](docs/DESIGN_PHILOSOPHY_CN.md) · [English](docs/DESIGN_PHILOSOPHY.md) |
| 已有 HTTP 到 HTTPS 迁移 | [迁移指南](docs/HTTPS_MIGRATION_CN.md) · [English](docs/HTTPS_MIGRATION.md) |
| 证书、API 重定向与原生 Git 边界 | [运行时 TLS](docs/HTTPS_API_TLS_CN.md) · [English](docs/HTTPS_API_TLS.md) |
| 审阅 PR 或更新长期检出目录 | [本地 PR 审阅](docs/LOCAL_PR_REVIEW_CN.md) · [English](docs/LOCAL_PR_REVIEW.md) |
| 不受支持/高级 profile 或手工启动 | [手工运维/Windows](docs/OPENAI_TUNNEL_TEAM_SETUP_CN.md) · [English](docs/SETUP_TUTORIAL.md) |
| 排错、贡献、安全报告 | [故障排查](docs/TROUBLESHOOTING_CN.md) · [贡献指南](CONTRIBUTING_CN.md) · [安全](SECURITY_CN.md) |

## 实现任务如何流转

```text
人 + 推理界面：定义目标、约束、验收标准
    -> ActualCoder：准备 worktree 与有边界的交接
    -> Codex/Copilot：检查、实现、测试
    -> 人工审阅 finish：功能分支 / GitLab MR
    -> CI 证据与 ChatGPT 实时审阅
    -> 人决定继续还是合并
```

只读 MCP bridge 提供仓库/MR/CI 检查。**不能提交或执行本地编程任务，也不能读取未发布本地修改。** 用户操作本地 CLI，在界面间交接获批任务与结果。持久化 TaskSpec、EvidencePack 访问仍在规划中；人工交接模板只是写作辅助。

用[访问预检](docs/PROJECT_ACCESS_CN.md)确认真实项目后，按 [CLI 快速上手](docs/QUICKSTART_CN.md)或[演练](docs/PRACTICE_LAB_CN.md)执行。`start --no-launch` 创建真实本地工作区与交接，但不调用编程模型；不是无副作用预览。继续同一任务时保留 workspace ID，使用 `resume`，不要反复 `start`。

检查实际本地差异后运行 `finish --dry-run`，再明确批准实际 `finish`。**Dry-run 仍运行配置的验证命令，只意味着不提交/推送，不意味着不执行代码。** 缺少 `.actualcoder.yaml` 是允许的，但没有项目专用测试。没有真实必需测试的绿色结果不足以验收任务。

`resume --from-ci` 返回匹配 HEAD 的失败证据，不会自动执行修复。不要为成功 CI 编造修改。低层 `commit`/`push` 与部分生成交接不包含全部 finish 门槛；保留明确任务边界，使用审阅后的 finish 主流程。详见[工作流程](docs/WORKFLOW_CN.md)。

GitLab 是已实现的目标源码管理/CI 集成。本项目源码托管于 GitHub，不代表有 GitHub 目标任务适配器。当前编程后端为 `codex`、`copilot`。

## 无生产凭证试用源码

只想跑测试/help 的贡献者，安装 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。包元数据要求 Python 3.10+，CI 使用 3.12。在新检出目录逐条运行，遇错停止：

```bash
git clone https://github.com/phoenixjyb/reasonFirst.git
cd reasonFirst
uv sync --python 3.12
uv run actual-coder --help
uv run actual-coder-tunnel --help
uv run actual-coder-check-project --help
uv run python -m unittest discover -s tests -v
uv run python scripts/check_repo_secrets.py --history
```

测试使用临时仓库、模拟服务和回环测试环境，不需要生产凭证或真实隧道。安装依赖会访问包索引。本源码基线的 `uv sync` 可能生成未跟踪 `uv.lock`，保留它，不要忽略/重置其他文件。纯本地测试路径不要求 MCP/Tunnel 接入。

## main 上已有的能力

最近一个文档记录的发布版本为 **v0.3.0**。已合并源码不一定包含于该 tag，包元数据仍为 `0.3.0`。报告问题时记录 commit SHA 与版本，参见 [CHANGELOG.md](CHANGELOG.md)。

| 能力 | 当前范围 |
| --- | --- |
| 受管工作区 | 本地 Git 缓存/worktree、功能分支、MR 创建/更新/恢复 |
| 受控 finish | Base 策略测试、可审阅性/保护路径、候选与有界历史秘密检查、人工确认 |
| 发布安全 | 普通 cleanup 前的新鲜远端证据；保留未发布遗留工作 |
| 命令/CI 证据 | 传递非零失败；匹配 HEAD 的 CI 与有界、脱敏 job 日志 |
| 项目访问预检 | 本地 allowlist -> GitLab 项目/ref/文件；明确诊断和固定修订；不自动授权 |
| 隧道生命周期 | macOS/Linux 已有 profile 的 configure/start/status/stop/restart、可选准确 Keychain 读取、所属进程清理；仅前台 |
| HTTPS 迁移 | 离线预览、确认后本地 URL 更新、私有备份、向前恢复 |
| API/MCP 传输 | 验证根证书，可选仅 Python 的私有 CA；目的地检查，拒绝 API 重定向 |
| 只读 MCP | 文件、项目、MR、pipeline、job；没有本地任务执行接口 |

**仍在规划：**原生 Git 信任/目的地策略、各交接入口一致上下文、通用工作区锁/事务恢复、持久 TaskSpec/尝试记录、EvidencePack。迁移锁和 tunnel-owner 锁不是通用工作区并发保护。[Issue #6](https://github.com/phoenixjyb/reasonFirst/issues/6)与 [Issue #10](https://github.com/phoenixjyb/reasonFirst/issues/10)跟踪任务循环/HTTPS 工作。

API/MCP 客户端拒绝关闭 TLS 验证和所有 API 重定向，请配置最终端点。`GITLAB_CA_BUNDLE` 增加 Python API/MCP 信任，不配置原生 Git 或迁移 `--check-tls` 探针。范围不要混淆，详见[运行时 TLS](docs/HTTPS_API_TLS_CN.md)。

## 名称、兼容性与贡献

**ReasonFirst** 是项目；**ActualCoder**（`actual-coder`）是高层 CLI。`gitlab-agent` 是低层，`codingagent` 为兼容别名。分发名 `chatgpt-selfhosted-gitlab-mcp`、Python 包 `gitlab_agent`、私有配置 `~/.config/gitlab-agent/.env` 与已有工作区路径有意保留，更新时不要重命名受管目录。

全局 editable 命令跟随源码目录；PR 实验使用独立 worktree。欢迎贡献及中英文可复现报告：[贡献指南](CONTRIBUTING_CN.md)、[安全报告](SECURITY_CN.md)、[公开发布清单](docs/PUBLIC_RELEASE_CHECKLIST_CN.md)。不要在公共 issue 发布凭证文件、私有源码、迁移备份或未经审阅日志。

采用 **Apache License 2.0**，见 [LICENSE](LICENSE)。外部工具各有许可和条款。本项目独立维护，不是 OpenAI、GitHub 或 GitLab 官方产品。
