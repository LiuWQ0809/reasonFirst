# 手工与高级 GitLab MCP 接入操作

[English](SETUP_TUTORIAL.md) · **[首次完整接入](GETTING_STARTED_CN.md)** · [受管日常生命周期](TUNNEL_LIFECYCLE_CN.md)

**新用户应顺序完成 [GETTING_STARTED_CN.md](GETTING_STARTED_CN.md)，不要从备用方案拼接首次部署。** 完整指南包含前置条件、安装、Platform/workspace 权限、runtime key、Keychain、profile、新生命周期助手及第一条普通 ChatGPT 请求。本文保留手工/高级和 Windows 替代操作。

## 首次接入

使用[完整指南](GETTING_STARTED_CN.md)。复用既有 GitLab 配置、Tunnel ID 和本地 profile；不为排查重启而运行 `init --force`、覆盖 `.env` 或创建替代隧道。ReasonFirst 与上游 `tunnel-client` 分别安装。隧道客户端是此连接的必需组件；编程后端只在后续实现时需要。

OpenAI Platform 隧道管理/使用权限、ChatGPT workspace 自定义应用权限、GitLab/本地 MCP 项目授权分属不同层。`CONTROL_PLANE_API_KEY` 是 OpenAI runtime key，`tunnel_...` 是 ID，`GITLAB_TOKEN` 是 GitLab API 凭证。本地私有 `GITLAB_ALLOWED_PROJECTS` 管理项目授权，不是 OpenAI Tunnel 设置。

## 重启既有 profile

已配置 macOS/Linux 助手时，使用[生命周期命令](TUNNEL_LIFECYCLE_CN.md)，保持前台 Terminal。服务管理器启动的 runtime 应通过原 supervisor 和秘密加载器操作。**同一隧道不要混用手工、助手管理和服务管理。**

仅在明确采用手工/高级 profile 时使用下文。在已知旧实例的原 Terminal 按 Control+C，不使用 `pkill`、`killall` 或猜测保存的 PID。

```bash
tunnel-client profiles list
```

用本地编辑器检查返回的 profile，不把文件内容发送到对话。main stdio 命令应指向长期已审阅源码目录。下文只是片段，不是整份替代配置：

```yaml
mcp:
  commands:
    - channel: main
      command: 'bash "/absolute/path/to/reasonFirst/run_mcp.sh"'
```

切换 Terminal 当前目录不会更新绝对路径。`run_mcp.sh` 只启动本地 stdio MCP，不会自行连接隧道。保留 ID 和凭证引用；高级 profile 不被保守的生命周期助手支持，不代表上游配置一定无效。

<a id="credential-alternatives"></a>
## 凭证替代方式

首次 Mac 路径使用准确、已有的 Keychain 条目。Keychain 可选，但**必须有明确 runtime-key 来源**。助手只保存引用，加载失败时不会自动切换凭证来源。

**助手配合 env/file：**运行 `actual-coder-tunnel configure` 时不带两个 Keychain 选项，明确选择 source/profile/私有 GitLab 配置。`env:CONTROL_PLANE_API_KEY` 要求每次启动的 shell 都有变量，通过批准的秘密加载器或隐藏本地提示输入。`file:/absolute/path` 使用用户所有、常规、非符号链接、0600 权限的私有文件，由上游读取。已有不同助手设置时，先审阅再明确 `configure --replace`，不能在 owner 运行时替换。

**手工 env 引用启动：**先在真实长期源码目录打开 Terminal。下文显式调用 Bash，只在当前 shell 没有 runtime key 时提示输入。替换示例 profile 名；输入不会持久保存，也不会作为字面值写入命令历史：

```bash
bash <<'BASH'
set +x
set +v
set -eu
PROFILE="selfhosted-gitlab"
export GITLAB_AGENT_ENV_FILE="$HOME/.config/gitlab-agent/.env"
test -f "$GITLAB_AGENT_ENV_FILE"
test -f run_mcp.sh
unset GITLAB_BASE_URL GITLAB_TOKEN GITLAB_GIT_TOKEN GITLAB_ALLOWED_PROJECTS
if [ -z "${CONTROL_PLANE_API_KEY:-}" ]; then
  read -r -s -p 'OpenAI tunnel runtime API key (hidden): ' CONTROL_PLANE_API_KEY </dev/tty
  printf '\n'
fi
if [ -z "${CONTROL_PLANE_API_KEY:-}" ]; then
  printf 'No runtime key supplied. Nothing was started.\n'
  exit 1
fi
export CONTROL_PLANE_API_KEY
tunnel-client doctor --profile "$PROFILE" --explain && tunnel-client run --profile "$PROFILE"
BASH
```

unset 仅在子 shell 中选择私有 GitLab 文件里的对应值，其他有意覆盖值需操作者核对。旧 shell export 不是持久存储；变量缺失不等于 key 过期。不要把字面 key 写入 `.zshrc`、仓库或含 token 的 curl 示例。这不是对同用户进程的隔离。

已有 **file 引用 profile** 时保留私有文件/loader，不为套用上述示例而改成环境变量。通过获准服务或 shell 为原 profile 执行上游 doctor/run，不必额外提示输入 key。

GitLab `.env` loader 不解析 `GITLAB_TOKEN` 内的 Keychain/file 引用。GitLab 明文文件权限与 tunnel key 的秘密来源是两件事。API/MCP CA、原生 Git TLS 和迁移探针也要区分，详见[运行时 TLS](HTTPS_API_TLS_CN.md)，不要关闭验证解决 CA 问题。

<a id="windows-powershell"></a>
## Windows PowerShell

`actual-coder-tunnel` 生命周期操作不支持 Windows；不要执行 Mac Keychain/Bash 步骤。保留现有 `run_mcp.ps1` profile 和批准的 DPAPI/企业 secret loader。由 loader 为 env 引用准备当前会话变量，或保留 file 引用；本文不创建秘密存储、不更改 Windows ACL。

在实际长期源码目录执行，替换示例 profile 名：

```powershell
$ProfileName = "selfhosted-gitlab"
$env:GITLAB_AGENT_ENV_FILE = Join-Path $HOME ".config\gitlab-agent\.env"
if (-not (Test-Path $env:GITLAB_AGENT_ENV_FILE)) { throw "Config file not found" }
Remove-Item Env:GITLAB_BASE_URL -ErrorAction SilentlyContinue
tunnel-client.exe doctor --profile $ProfileName --explain
if ($LASTEXITCODE -ne 0) { throw "Tunnel doctor failed; runtime was not started" }
tunnel-client.exe run --profile $ProfileName
```

核对可能覆盖私有文件的旧 `GITLAB_*` 环境值，但不打印秘密。前台服务需保持运行。doctor 失败时处理首个失败项，不安装无关插件、不放宽权限。首次 Windows 客户端安装/profile 创建遵循[上游平台说明](https://github.com/openai/tunnel-client/blob/master/docs/end-user-guide.md)，不要把本文当成自动安装程序。

## 诊断运行中的服务

上游 localhost Overview/Logs、`/healthz`、`/readyz` 是可选诊断，不是最终验收。用你实际 profile 报告的地址，管理界面保持 loopback。**不需要**成功运行仪表盘 Assistant、Codex tunnel plugin 或 Inspector。

仅在 `/ui#codex` 出现 `approval policy is never`，不能证明普通 ChatGPT 隧道失败。不要为可选面板放宽全局审批或无限制 shell 权限。关闭浏览器不会停止 tunnel，也不保证上游附带 helper 被禁用。

## 在普通 ChatGPT 验收读取

保持所选 runtime 运行，在正确 workspace 的普通 ChatGPT 选择已有应用；更新工具集后刷新发现。替换已确认项目/ref/文件和应用名：

```text
只使用连接的 My GitLab MCP。先调用 gitlab_whoami，再调用
check_project_access(project="team/project-a", ref="main", required_files=["README.md"])。
若工具不可用或 ok=false，报告诊断和所需用户操作，停止等待。
不要把隐藏/缺失项目断言为一定不存在。
成功后调用 get_file：project="team/project-a"、file_path="README.md"、
ref 使用返回的 resolved_commit_sha。概括真实内容，仅报告实际返回修订字段。
不使用网页、旧对话、shell、凭证文件代替；不创建项目、不自动授权、
不实现、不发布、不合并。
```

身份成功不等于项目访问，过滤列表为空不等于项目不存在。访问需要本地 MCP allowlist 与独立 GitLab 权限，不靠重建隧道。按[项目预检](PROJECT_ACCESS_CN.md)操作；不要以生产应用替换未准备好的练习仓库。

实际身份/预检/文件读取成功，只验收读取路径，不证明 Git push、编程客户端登录或完整应用构建。批准任务后再按[工作流程](WORKFLOW_CN.md)和[人工交接](TASK_HANDOFF_TEMPLATE_CN.md)推进。当前 MCP 没有本地执行入口。旧 `smoke_test.py` 未使用统一 runtime TLS factory，不是本指南的验收门槛。

## 一手参考

[OpenAI 隧道与当前 ChatGPT 连接界面](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)、[developer mode 资格](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)、[上游配置](https://github.com/openai/tunnel-client/blob/master/docs/configuration.md)、[上游运维指南](https://github.com/openai/tunnel-client/blob/master/docs/end-user-guide.md)。
