# 中文文档索引

[English](README.md) · **简体中文**

<!-- Translation source: docs/README.md @ a3e33c72c55efef6a0dc3808fb9853c62ad15f9d; navigation, lifecycle/access gates and translation-maintenance sections maintained together with the English index. -->

这些指南描述的是包含它们的源码修订。某项功能已经合并，不代表最近的发布 tag 一定包含它。参见[项目说明](../README_CN.md)和 [Unreleased 更新记录](../CHANGELOG.md)。

## 当前文档入口

| 主题 | 简体中文 | English |
| --- | --- | --- |
| 产品与支持的能力 | [项目说明](../README_CN.md) | [ReasonFirst](../README.md) |
| 启动必需的 Tunnel 服务并管理生命周期 | [可靠启动、状态、停止与重启](TUNNEL_LIFECYCLE_CN.md) | [Reliable start/status/stop/restart](TUNNEL_LIFECYCLE.md) |
| 使用新提出的 GitLab 项目之前 | [项目预检与用户授权](PROJECT_ACCESS_CN.md) | [Access preflight and grants](PROJECT_ACCESS.md) |
| 演练 ChatGPT、Codex 与同一 MR 的三轮审查 | [实战演练](PRACTICE_LAB_CN.md) | [Practice lab](PRACTICE_LAB.md) |
| 各界面的用途，以及每项检查能证明什么 | [工作流程](WORKFLOW_CN.md) | [Workflow](WORKFLOW.md) |
| 源码安装与第一个受控任务 | [快速上手](QUICKSTART_CN.md) | [Quickstart](ACTUAL_CODER_QUICKSTART.md) |
| 普通 ChatGPT 的 GitLab 读取接入与重启 | [团队接入与重启](OPENAI_TUNNEL_TEAM_SETUP_CN.md) | [Operator guide](SETUP_TUTORIAL.md) |
| 人工交接已批准任务与结果证据 | [人工模板，并非运行时 API](TASK_HANDOFF_TEMPLATE_CN.md) | [Handoff template](TASK_HANDOFF_TEMPLATE.md) |
| 架构意图 | [设计理念](DESIGN_PHILOSOPHY_CN.md) | [Design philosophy](DESIGN_PHILOSOPHY.md) |
| HTTP 到 HTTPS 迁移 | [迁移指南](HTTPS_MIGRATION_CN.md) | [Migration](HTTPS_MIGRATION.md) |
| API/MCP 私有 CA、重定向与原生 Git 边界 | [运行时 TLS](HTTPS_API_TLS_CN.md) | [Runtime TLS](HTTPS_API_TLS.md) |
| PR 检出、测试与日常安装更新 | [本地 PR 审阅](LOCAL_PR_REVIEW_CN.md) | [Local PR review](LOCAL_PR_REVIEW.md) |
| 不弱化控制措施的诊断方式 | [分层故障排查](TROUBLESHOOTING_CN.md) | [Troubleshooting](TROUBLESHOOTING.md) |
| 贡献流程 | [贡献指南](../CONTRIBUTING_CN.md) | [Contributing](../CONTRIBUTING.md) |
| 安全报告与当前限制 | [安全策略](../SECURITY_CN.md) | [Security](../SECURITY.md) |
| 公开发布之前 | [维护者检查清单](PUBLIC_RELEASE_CHECKLIST_CN.md) | [Release checklist](PUBLIC_RELEASE_CHECKLIST.md) |

## 第一次 ChatGPT 对话之前的必需步骤

Tunnel 接入方式下，使用演练或仓库读取提示词之前，必须启动既有 Tunnel/MCP 并保持运行。[生命周期辅助程序](TUNNEL_LIFECYCLE_CN.md)只需一次保存不含秘密的启动引用，即可在 macOS/Linux 前台启动、检查真实本地状态，并按 owner 身份停止/重启。它不代替项目授权或实际 ChatGPT 调用验收，localhost Assistant 仍不是必需组件。操作指南中保留手动启动方式；不能混用两个启动器管理同一实例，也不能把早先 shell 的 export 当成永久保存凭证。

## 新项目访问门槛

项目名称或本地目录不能证明远端仓库已存在或获准。首次引入项目时，普通 ChatGPT 流程应在批量读取和任务交接前调用 `check_project_access`。`ok: false` 时展示诊断，等待用户/管理员处理。404 或过滤后的空列表不能区分不存在和不可访问。项目级授权在本地 MCP 配置的 `GITLAB_ALLOWED_PROJECTS`，不在 OpenAI Tunnel 设置中；仅明确批准后授权并重启现有 MCP。只读辅助检查不会授权或创建项目。参见上方中英文访问指南；按照较早的首任务示例操作前，也应先完成此门槛。

## 翻译范围与维护

此前只有英文的当前指南，已在上表补齐中文对应页。已有的中文快速上手、Tunnel、迁移和运行时 TLS 指南继续作为相应入口，不重复创建另一份译文。每个新增译文都链接到英文原文，并在 Markdown 注释中记录原文修订。行为变化时应同步维护两种语言，保留可执行命令、配置键、证据局限，以及“规划中”与“已实现”的区别。

历史版本说明和 CHANGELOG 保留原记录，LICENSE 不变。翻译不会产生新版本发布、改变权限、禁用可选 Assistant 后台辅助进程，也不会实现 TaskSpec/EvidencePack。

## 一个推理界面，而不是另加一个必需聊天工具

这些指南选用普通 ChatGPT 作为推理与审查界面。Tunnel/MCP 负责读取传输和工具调用；ActualCoder 配合选定编程 CLI，通过人工交接完成获批实现。本地仪表盘 Assistant 和 Codex Tunnel 插件是上游可选功能，不是前提或验收门槛。Overview/Logs 可辅助诊断。不使用 Assistant，不会禁用其附带辅助进程，也不会移除编程 CLI。

已有可用安装应从[重启流程](OPENAI_TUNNEL_TEAM_SETUP_CN.md)开始，而不是重新安装。连接验收是在普通 ChatGPT 中实时读取身份和文件，不是看 localhost Assistant 的回答。这些文档不会启用本地任务提交 MCP 接口，也不会自动导入 TaskSpec/EvidencePack。

供应商可用性和界面步骤可能变化，应遵循操作指南中的一手参考。根据当前 TLS 指南，分清 API/MCP 运行时信任、原生 Git 和维护探测。

## 历史设计与详细旧版操作示例

[旧中文 onboarding](ONBOARDING_GUIDE_CN.md)和[旧中文配置教程](SETUP_TUTORIAL_CN.md)保留历史部署示例，不是当前必需清单。重启、凭证、源码升级、读取验收及 `start -> finish -> ci -> resume` 流程，优先使用上方当前指南。不要执行旧的含令牌示例，不要覆盖工作中的 `.env`，也不要仅因历史教程提及就安装可选组件。

[V0.2 设计](V0.2_WRITE_ACCESS_DESIGN.md)、[V0.2 Codex 指南](V0.2_CODEX_QUICKSTART.md)、[兼容 CodingAgent 指南](CODINGAGENT_QUICKSTART.md)、[V0.3 路线图](V0.3_ROADMAP_CN.md)和 [V0.3 审计](V0.3_RELEASE_AUDIT_CN.md)提供历史背景，不是当前功能的权威清单。

`V0.3.1_*_CN.md` 是针对[发布安全](V0.3.1_PUBLICATION_SAFETY_CN.md)、[退出状态](V0.3.1_COMMAND_EXIT_CN.md)、[历史扫描](V0.3.1_SECRET_HISTORY_CN.md)和[日志证据](V0.3.1_SHARED_LOG_EVIDENCE_CN.md)的专项实现说明。它们的文件名不表示 v0.3.1 已发布。[Issue #6](https://github.com/phoenixjyb/reasonFirst/issues/6) 和 [Issue #10](https://github.com/phoenixjyb/reasonFirst/issues/10) 跟踪剩余任务循环与 HTTPS 工作。
