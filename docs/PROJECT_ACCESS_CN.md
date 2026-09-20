# 先确认项目访问权限，再规划任务

[English](PROJECT_ACCESS.md) · [中文文档索引](README_CN.md) · [工作流程](WORKFLOW_CN.md)

**提出一个项目名称，不等于远端仓库已经存在。创建本地目录、Tunnel 启动成功，或 `gitlab_whoami` 成功，都不能证明拥有项目访问权限。** 每次引入新项目时，应先检查访问条件，再批量读取文件、制定基于代码的验收标准或创建 ActualCoder 工作区。

## 三层独立权限

| 层次 | 用户或管理员控制什么 | 不能因此获得什么 |
| --- | --- | --- |
| ChatGPT 连接 / OpenAI Tunnel | 使用相应连接和 Tunnel 的权限 | GitLab 项目成员权限或本地项目允许列表授权 |
| ReasonFirst MCP 进程 | 生效的私有配置/环境中的 `GITLAB_ALLOWED_PROJECTS` | GitLab 令牌权限，也不会创建项目 |
| GitLab | 项目是否存在、成员关系、仓库可见性、令牌 scopes | 不会自动通过本地 MCP 允许列表 |

用户说“在 Tunnel 设置里授权”时，应指出真正需要修改的层次。当前实现中，**项目级授权位于 ReasonFirst 本地 MCP 配置，不在 Tunnel YAML 的 `control_plane` 中，也不是 OpenAI 设置中的项目选择器**。保留现有 Tunnel，不要声称本仓库已经提供授权界面。

## 普通 ChatGPT 中首先进行的检查

通过选定的实时 GitLab MCP 调用：

```text
check_project_access(
  project="team/project-a",
  ref="main",
  required_files=["README.md"]
)
```

这里都是示例，不代表项目已经存在。替换为用户确认的准确 `namespace/project` 或正整数项目 ID，不使用 URL 或带前导斜杠的路径。列出真实任务需要的文件，最多 16 个不同的仓库相对路径。

检查过程只读：先验证本地授权，再获取项目元数据、解析指定或默认 ref，最后通过 **HEAD 请求检查固定 commit 下的文件元数据**。不会下载文件内容，不会创建项目、分支或工作区，不会授权、更改令牌或启动编程后端。整体超时为 30 秒，每个元数据响应最多 128 KiB。遇到第一个失败的依赖就停止，并保留此前已获得的证据。

`ok: true` 后，用 `resolved_commit_sha` 继续读取文件，让规划依据固定在同一修订。元数据检查不能替代实际阅读源码，也不证明 Git 推送权限、测试通过或分支之后不会变化。`required_files_complete` 仅表示所列文件的检查是否完成；空文件列表不会检查任何文件。

`ok: false` 时，**向用户说明诊断结果并等待处理**。不要接连重试七个文件，不要换成已获准的生产项目，不要用 GitHub 替代指定的 GitLab 实例，更不能编造源码证据。预期的访问失败会作为结构化诊断数据返回，使屏蔽普通异常文字的客户端仍能显示原因。MCP 调用传输成功但结果为 `ok: false`，不代表仓库读取成功。

## 如何理解结果

| 错误码 | 已有证据 | 下一步 |
| --- | --- | --- |
| `project_not_allowlisted` | 未获得本地授权；没有发送 GitLab 请求；`project_exists: null` | 请用户/MCP 管理员仅授权这个准确项目，重启后重试。 |
| `credential_missing` / `gitlab_unauthorized` | 进程缺少凭证 / HTTP 401 | 管理员私下检查 GitLab 凭证，不在聊天中索取令牌内容。 |
| `gitlab_forbidden` | HTTP 403 | 用户/管理员核对 GitLab 成员权限、scopes 和实例策略。 |
| `project_missing_or_inaccessible` | 项目查询返回 HTTP 404 | 核对实例、路径/ID、权限；**不得断言项目不存在**。 |
| `repository_empty` | GitLab 明确返回 `empty_repo: true` | 用户批准初始文件后，初始化目标仓库。 |
| `default_branch_unavailable` | 元数据没有可用默认分支 | 确认显式 ref 或初始化分支；默认分支为空不等于项目缺失。 |
| `ref_missing_or_inaccessible` | 项目元数据可读，但 ref 查询返回 404 | 确认分支/tag/commit 和访问权限，不静默换 ref。 |
| `required_file_missing_or_inaccessible` | 固定 commit 下所需文件的元数据查询返回 404 | 核对初始化内容、准确路径和可读性，停止基于源码的规划。 |
| `resource_missing_or_inaccessible` | 未做分层预检的直接文件/目录/MR 查询返回 404 | 调用预检区分失败层次，不声称项目不存在。 |
| `gitlab_rate_limited`、`gitlab_unavailable`、`timeout`、传输/TLS 错误 | 服务或传输失败，不是权限问题的证明 | 排查对应层次，不把放宽 TLS、重建 Tunnel 或扩大权限当通用修复。 |

诊断不会包含原始 HTTP body、重定向目的地、异常原文、令牌值或私有配置内容。数字 ID 与路径都是精确允许列表键；其中一种写法获准，不允许绕过列表探测另一种写法。`list_projects` 在本地过滤后可能返回空页；`next_page` 只是按上游页长度提供的候选页，不保证下一页有可见项目。按成员关系过滤的列表，也不等于令牌可访问的完整项目清单。

## 由用户控制授权

先确认目标 GitLab 实例上是否已有该项目。**只有用户确认不存在，并单独批准创建后**，才按正常 GitLab 流程创建和初始化。一个 404 不能授权自动创建。

需要本地授权时，由管理员私下编辑 `GITLAB_AGENT_ENV_FILE` 选中的有效用户配置，通常是 `~/.config/gitlab-agent/.env`。把准确项目追加到 `GITLAB_ALLOWED_PROJECTS`，保留其他需要的项目。不得清空列表：现有 MCP 读取策略把空列表视为允许令牌可访问的全部项目。本次代码不会自动修改授权。

重启**现有** MCP/Tunnel 进程。导出的 `GITLAB_ALLOWED_PROJECTS` 可能覆盖文件，须管理员在本地处理；助手不得读取 `.env`、密码库或 shell 配置来寻找秘密。如果是共享服务，由实际服务管理员处理，不要改错另一台机器的配置。部署包含新工具的版本后，刷新现有 ChatGPT 连接的工具发现，再对同一项目预检。仅为项目授权，不需要新 Tunnel、新 OpenAI runtime key 或 localhost Assistant。

## 可选本地辅助命令

在已经安装依赖、经过审阅的源码目录中：

```bash
uv run actual-coder-check-project team/project-a --ref main --require-file README.md
```

等效源码辅助入口：

```bash
uv run python scripts/check_project_access.py team/project-a --ref main --require-file README.md
```

命令输出 JSON，**仅 `ok: true` 时退出码为 0，否则为 1**。使用选定的用户配置、验证证书的 Python API 传输、显式 CA 策略及现有代理策略。不创建缓存/工作区，不启动 Git/Codex。原生 Git 的信任和写权限仍独立。`mcp_connection_checked: false` 明确说明：本地 CLI 检查不能证明正在运行的 ChatGPT/MCP 进程使用同样设置。

`workspace_policy_allowed` 单独报告本地工作区策略，不代表 GitLab 写授权。按现有默认策略，读取预检可能在空允许列表下通过，但本地写入流程仍要求显式列表。本辅助检查不会自动插入每个 `start`/`resume`，也不改变仅使用 Git 的流程。文档的新项目流程与 MCP 指令要求先预检，实际项目读取仍会独立执行允许列表检查。它不是操作系统沙箱，也不是自主执行者的授权机制。

## 可复用的首次对话提示

```text
仅通过指定 GitLab MCP 处理我确认的准确项目与 ref。
先调用 gitlab_whoami，再调用 check_project_access，列出任务需要的全部文件。
如果没有此工具，说明运行中的 MCP 需要更新/重新发现，不得声称已做预检。
如果 ok=false，报告 error.code、stage、返回的 HTTP 状态、已知/未知的存在性，
以及用户应进行的操作，然后停止等待。不得自动创建项目、修改允许列表、索取凭证、
换用另一仓库或进入实现交接。
预检成功后才在 resolved_commit_sha 上读取所需文件，再制定已批准阶段的方案和验收项。
```

人工交接记录应包含准确实例/项目、授权状态、解析到的 commit、所需文件检查结果及缺失证据。练习项目需要 README.md、EXERCISE.md、AGENTS.md、.actualcoder.yaml、.gitlab-ci.yml、clip_summary.py 和 tests/test_clip_summary.py。

一手参考：[GitLab 项目 API](https://docs.gitlab.com/api/projects/)、[提交 API](https://docs.gitlab.com/api/commits/)、[文件元数据 API](https://docs.gitlab.com/api/repository_files/)、[认证](https://docs.gitlab.com/api/rest/authentication/)。API 结果可能有歧义，应保留不确定性，不猜测。
