# 一个推理界面，一套受控实现流程

[English](WORKFLOW.md) · [项目说明](../README_CN.md) · [中文接入](OPENAI_TUNNEL_TEAM_SETUP_CN.md) · [CLI 快速上手](QUICKSTART_CN.md) · [任务交接模板](TASK_HANDOFF_TEMPLATE_CN.md)

<!-- Translation source: docs/WORKFLOW.md @ a3e33c72c55efef6a0dc3808fb9853c62ad15f9d -->

**使用普通 ChatGPT 对话进行推理与审查，使用 ActualCoder 配合选定的编程 CLI 完成实现。本地 localhost Assistant 不属于这条必需流程。** 也可以明确选择其他兼容的推理客户端，但开发机上不需要额外增加一个对话界面。

## 各项操作应该在哪里进行

| 界面或组件 | 职责 | 是否必需 |
| --- | --- | --- |
| 普通 ChatGPT 对话 | 通过选定连接读取代码、诊断问题、明确范围、审查结果 | 本指南选用的推理界面 |
| `tunnel-client` 与 ReasonFirst `server.py` | 转发并提供只读 GitLab MCP 调用 | Tunnel 接入需要；纯 CLI 使用不需要 |
| 终端中的 ActualCoder 与 Codex/Copilot CLI | 准备工作树、实现已批准任务、验证，并通过经审阅的 finish 流程发布 | 本地实现流程需要 |
| GitLab MR/CI 界面 | 检查仓库证据，由人工作出合并决定 | 审查或发布变更时使用 |
| 本地仪表盘 Overview/Logs | 诊断 Tunnel | 可选 |
| 本地仪表盘 Assistant（`/ui#codex`） | 上游提供的独立 Codex 界面 | **不是必需组件，也不是验收门槛** |
| Codex Tunnel 插件或 MCP Inspector | 独立的集成或调试工具 | 可选；标准 ChatGPT 读取测试不需要它们 |

不使用 localhost Assistant 不等于卸载 Codex：Codex CLI 仍可作为实现任务的执行者。关闭仪表盘不会停止 Tunnel，也不一定会禁用上游客户端附带的后台辅助进程。本指南没有修改该进程，也不声称将其禁用。

## 两条路径，通过人工明确交接

```text
读取与审查：
普通 ChatGPT <-> OpenAI Tunnel 服务 <-> tunnel-client
            <-> ReasonFirst 只读 MCP <-> GitLab HTTPS API

实现：
ChatGPT 对话中批准的任务
  -> 经人工审查的本地交接
  -> ActualCoder + 选定的编程 CLI
  -> 验证 / 经审阅的 finish
  -> 功能分支 / MR / CI
  -> ChatGPT 与人工审查证据
```

传输层负责转发请求，不需要本地语言模型解释请求。当前 MCP bridge 提供 GitLab 读取能力，**不提供**本地任务提交或执行能力。ChatGPT 不能通过该 bridge 读取尚未发布的本地 diff。可以人工分享经过审阅和脱敏的本地证据；或者，在明确批准发布之后，通过 MCP 读取已发布的 MR/CI。

当前尚无自动 TaskSpec 导入、持久化任务修订或统一 EvidencePack 接口。[人工模板](TASK_HANDOFF_TEMPLATE_CN.md)只是写作辅助，不是运行时数据格式或新增 CLI 功能。不同交接入口目前仍可能携带不同的项目上下文；需要检查返回的提示词，并自行保留已批准的要求。

## 日常任务循环

### 1. 在普通 ChatGPT 对话中读取并决策

在对话中选择目标 GitLab 连接，要求读取真实文件，并区分观察到的事实与改进建议。明确目标、非目标、涉及组件、验收标准和停止条件。不要将令牌、私有配置文件或含凭证的参考笔记放入任务上下文。

用人工模板记录已批准的要求。为某次任务更换编程后端，并不意味着允许更改任务目标或扩大范围。

### 2. 在终端准备并实现

对于真正获得批准的新任务，从源码检出目录运行；将示例项目和目标替换为实际值：

```bash
uv run actual-coder start team/project-a --task fix-timeout --goal "Fix the timeout bug; preserve the API and add regression coverage" --no-launch
```

这会获取上下文并创建工作树，不是离线或无写入的预览。检查返回的 workspace ID、路径、分支和交接内容，再使用返回的后端启动命令及提示词。继续同一工作区时，不要再次执行 `start`。新任务可以省略 `--no-launch`，直接以交互方式启动后端。执行者的登录状态和额度应通过其自身支持的流程检查，不能由“已安装可执行程序”推断。

### 3. 发布前验证并审查

将 `WS` 设置为真实返回的 ID；下面的值仅作示例：

```bash
WS="012345abcdef"
uv run actual-coder status "$WS"
uv run actual-coder finish "$WS" --message "fix: handle timeout and add regression coverage" --dry-run
```

检查 diff、验证结果、秘密扫描覆盖范围、受保护路径及目标 MR/分支。**Finish dry-run 会运行配置的验证命令，可能改变本地文件；它不会提交或推送。** 缺少 `.actualcoder.yaml` 表示没有加载项目专用验证项。只有先定义实际项目测试，才能将其称为项目测试门槛。

确认检查未被阻断、变更符合意图之后，才运行：

```bash
uv run actual-coder finish "$WS" --message "fix: handle timeout and add regression coverage"
uv run actual-coder ci "$WS"
```

Finish 会请求确认。仍需审查执行者提出的操作：低层 commit/push 命令，包括部分生成提示词仍提到的命令，不会执行全部 finish 检查。不要将本指南中的行为要求当作操作系统级强制约束。详见[安全边界](../SECURITY_CN.md)。

### 4. 返回证据，而不只是执行者声称成功

记录 base 与 HEAD、尚未提交的变更、实际验证命令及结果、MR 链接、CI SHA 和覆盖范围。成功的 docs-only 流水线不是完整构建；历史上成功且 SHA 匹配的流水线，不是发生了新推送的证据。HEAD 对应的 CI 不覆盖未提交变更。

对于确实失败且与当前 HEAD 匹配的 CI，`resume --from-ci` 会准备修复交接；它不会自动启动或完成修复。CI 已成功时，不要为了附带的 CI 上下文凭空修改代码。人工审查和合并仍是独立操作。

## 分层验收

| 证据 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| `actual-coder doctor` 的 API 检查成功 | 当前环境的 CLI API 认证成功 | Git 推送权限、编程代理登录、Tunnel 可用性 |
| `project-config` 获取成功 | 该次受管 Git 读取成功 | 应用测试已通过，或已经获得写入授权 |
| Tunnel 启动 / 获取到元数据 | 启动及所报告的控制平面操作成功 | ChatGPT 已发现或调用 GitLab 工具 |
| 本地 health/readiness 响应 | 已安装 Tunnel 版本定义的健康条件 | 某个具体 GitLab 工具调用成功 |
| 普通 ChatGPT 中实时读取身份和文件成功 | 实际 ChatGPT 读取连接可用 | 本地任务执行，或新的构建/推送 |
| 本地 Assistant 的审批错误 | 该可选 Codex 会话中发生了失败 | 独立的普通 ChatGPT 连接也失败了 |

最终读取验收位于 [ChatGPT MCP 接入指南](OPENAI_TUNNEL_TEAM_SETUP_CN.md)，不是在 `/ui#codex` 中进行。现有安装应按该指南重启，不必重复安装或迁移。

## 下一步产品工作

后续演进应保留这种职责划分：先统一交接，再协调工作区写入与恢复，随后实现持久化任务修订、执行尝试和有界证据访问。不要用增加另一个聊天界面来补偿任务与证据交接不连续的问题。这些改进由 [Issue #6](https://github.com/phoenixjyb/reasonFirst/issues/6) 跟踪，属于规划，而不是本指南已经交付的功能。
