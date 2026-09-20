# 团队接入：ChatGPT 负责推理，Tunnel 负责连接

[README](../README.md) · [English operator guide](SETUP_TUTORIAL.md) · [日常流程](WORKFLOW.md) · [ActualCoder 中文上手](QUICKSTART_CN.md)

**不需要 localhost Assistant。** 本文的推理界面是正常的 ChatGPT 对话；本机运行 `tunnel-client` 和 ReasonFirst 的只读 MCP 服务。真正实现任务时，再由用户在终端通过 ActualCoder 启动 Codex/Copilot CLI。不要把本地仪表盘的 Assistant 页当成 ChatGPT，也不要为它的审批错误放宽全局权限。

## 1. 必需与可选

```text
读取与审阅：
正常 ChatGPT 对话 <-> OpenAI Tunnel <-> 本机 tunnel-client
                  <-> ReasonFirst server.py <-> GitLab HTTPS API

实现：
批准的任务 -> 用户手工交接 -> ActualCoder + 编码 CLI
           -> 验证 / 人工确认 finish -> MR / CI -> 返回审阅
```

Tunnel 是传输，不需要第二个本地模型解释每次请求。MCP 目前不能提交本地编码任务，也不能读取尚未发布的本地 diff。TaskSpec/EvidencePack 是后续计划；[手工交接模板](TASK_HANDOFF_TEMPLATE.md)不是已经实现的配置格式。

| 组件 | 本流程是否需要 |
| --- | --- |
| 正常 ChatGPT 对话中的 GitLab 连接 | 需要，用于推理和实时读取 |
| tunnel-client 与 server.py | 这条隧道接入路径需要；CLI 单独使用不需要隧道 |
| ActualCoder 与所选编码 CLI | 实现任务时需要；单纯 MCP 读取不需要 |
| localhost Overview / Logs | 可选运维诊断 |
| localhost Assistant、Codex tunnel plugin、MCP Inspector | 不属于必需安装或验收项 |

关闭仪表盘网页不等于关闭隧道，也不保证停止上游软件附带的后台 Assistant helper。本说明没有卸载 Codex、修改上游程序或关闭 helper。Codex CLI 仍可作为编码 worker。

## 2. 四种值不要混淆

| 值 | 用途 | 正确位置 |
| --- | --- | --- |
| `GITLAB_TOKEN` | GitLab 只读 API | 私有用户配置或明确加载的环境变量 |
| `GITLAB_GIT_TOKEN` | ActualCoder 的 Git 写入凭证（需要写入时） | 私有用户配置；不要交给对话或参考笔记 |
| Tunnel ID | 标识已有隧道，不是 bearer secret，但属于部署信息 | profile 的 `control_plane.tunnel_id` |
| OpenAI runtime API key | 允许 tunnel-client 使用隧道 | 安全存储，通过 `env:` 或受保护 `file:` 引用加载 |

`control_plane.base_url` 是 OpenAI 隧道服务，不是 GitLab 地址。`api_key: "env:CONTROL_PLANE_API_KEY"` 是正确的环境引用；缺少变量不等于 key 已失效。不要把 `tunnel_...` ID 或 GitLab Token 填进 runtime key。

使用隧道需要适用 Platform 组织的 Tunnels Read + Use 权限；管理隧道和 Admin Key 是另外的权限。ChatGPT 接入资格、组织和 workspace 关联按[当前官方说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)与[Developer Mode 帮助](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)核对，不把某个订阅名称写成永久保证。key 的前缀不能证明权限或有效性。

GitLab 用户配置是明文加文件权限保护，不是加密 vault。当前 ReasonFirst 不会自动把 `GITLAB_TOKEN=keychain:...` 或 `file:...` 解析为秘密。macOS 可用 Keychain、Linux 可用受保护 secret file、Windows 可用 DPAPI/企业 secret manager，但加载方式应由用户或已批准的 launcher 明确实现；不要猜测别人机器上的 Keychain 条目。

## 3. 已有安装：只重启，不重新初始化

先停止该 profile 原有的前台进程（在对应终端按 Control+C）。若使用服务管理器，应通过原服务重启并更新它的环境，不要同时启动第二个前台实例，也不要杀掉所有 Python/Codex 进程。

```bash
tunnel-client profiles list
```

用返回的 profile 名称和路径。在本地编辑器私下检查 `mcp.commands` 的 `main` 命令，确认它指向长期使用的源码目录，而不是已弃用目录或临时 PR worktree。配置片段示例：

```yaml
mcp:
  commands:
    - channel: main
      command: "bash /absolute/path/to/reasonFirst/run_mcp.sh"
```

路径只是示例，必须替换。保留原 Tunnel ID 与凭证引用；不要重跑 `init` 或覆盖整份 profile。改变终端当前目录不会改变 profile 中的绝对路径。路径包含空格时，按已安装 tunnel-client 的命令引用规则处理并验证。

### macOS / Linux：环境引用 profile

在正确的源码目录打开 Terminal。下面显式使用 Bash，因此可从 macOS zsh 粘贴；不要求 zsh 支持交互注释或 Bash 风格的 `read`。替换示例 profile 名称，确认用户配置路径。只适用于 `env:CONTROL_PLANE_API_KEY`；已有 `file:` 配置继续用原安全引用，不必为了复制此段而改成环境引用。

```bash
bash <<'BASH'
set +x
set +v
set -eu
PROFILE="selfhosted-gitlab"
export GITLAB_AGENT_ENV_FILE="$HOME/.config/gitlab-agent/.env"
test -f "$GITLAB_AGENT_ENV_FILE"
test -f run_mcp.sh
unset GITLAB_BASE_URL
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

有已导出的 runtime key 就复用，否则在本地隐藏提示输入已有 key。不会保存新输入、打印 key 或将其字面值写入 shell history。环境只作用于子 shell 与其子进程。清除 base URL 覆盖是为了读取明确的用户配置，不会编辑 `.env`；有意使用环境覆盖的部署应保留其明确策略。GitLab Token 的旧导出值也会优先于文件，换 token 后需要清除对应旧值并重启。

### Windows PowerShell

保留现有 `run_mcp.ps1` profile 和 DPAPI/企业 secret loader；不要套用 Bash。先通过已批准的 loader 为 `env:` 引用设置当前会话变量，或者保留已有 `file:` 引用。在长期源码目录执行：

```powershell
$ProfileName = "selfhosted-gitlab"
$env:GITLAB_AGENT_ENV_FILE = Join-Path $HOME ".config\gitlab-agent\.env"
if (-not (Test-Path $env:GITLAB_AGENT_ENV_FILE)) { throw "Config file not found" }
Remove-Item Env:GITLAB_BASE_URL -ErrorAction SilentlyContinue
tunnel-client.exe doctor --profile $ProfileName --explain
if ($LASTEXITCODE -ne 0) { throw "Tunnel doctor failed; runtime was not started" }
tunnel-client.exe run --profile $ProfileName
```

此段不创建 secret store，也不修改 Windows ACL。不要把 key 字面值写进命令、profile 或公开文档。诊断失败时先处理首个失败项，而不是安装可选 plugin 或放宽 GitLab 权限。

## 4. 验收必须在正常 ChatGPT 中完成

保持 tunnel 进程运行；不需要打开 localhost Assistant。可在 Overview/Logs 查看进程状态，但 `started`、metadata fetched、health/readiness 都不能代替真实工具调用。

在正常 ChatGPT 中选择已有的 GitLab 连接。按实际连接名称、允许的项目和已知存在的文件替换示例：

```text
使用连接的 My GitLab MCP 调用 gitlab_whoami，然后读取 team/project-a
的 main 分支 README.md。报告认证用户名并根据实时工具结果概括文件。
若工具不可用或调用被阻断，请明确报告，不用之前的对话、本地凭证笔记、
网页搜索或带 token 的 shell 命令代替。
```

只有真实身份调用和文件读取都成功，才验收 ChatGPT 读路径。README 不存在时选一个已知文本文件。结果可能含私有身份/项目数据，只在批准范围内保存，不复制进公共 issue。

不要把 `/ui#codex` 中的 `approval policy is never` 当作正常 ChatGPT 隧道失败，也不要为这个可选界面设置全局自动批准或不受限执行。若正常 ChatGPT 找不到连接，核对当前对话是否选择它、目标 ChatGPT workspace 的关联与权限，以及 tunnel 是否仍运行。

## 5. 新成员首次接入

先按[中文快速上手](QUICKSTART_CN.md)配置源码与用户 GitLab 设置；不要覆盖已有 `.env`。MCP 只读场景不要求安装编码 backend；查看 doctor 具体检查，不把缺少 Codex/Copilot 当成读协议本身失败。

使用官方支持的 tunnel-client，先看 `--version`、`help quickstart` 和 `profiles list`。在 [Platform Tunnels](https://platform.openai.com/settings/organization/tunnels) 与 [Runtime API keys](https://platform.openai.com/settings/organization/api-keys)创建或复用授权对象。仅确实没有合适 profile 时，按[英文首次接入步骤](SETUP_TUTORIAL.md#first-time-connection)初始化；已有成员直接使用上面的重启路径。

不将 `smoke_test.py`、Inspector、localhost Assistant 或 Codex tunnel plugin 作为必需验收步骤。旧 smoke helper 不经过统一 Python TLS client。证书问题按[运行时 TLS 范围](HTTPS_API_TLS_CN.md)区分 API、native Git 与迁移探针；已完成的 URL 迁移无需重做。

## 6. 完成后停止重复诊断

完成的读验收不等于 Git push、完整应用构建或编码 CLI 登录成功；写入测试留给另行批准的真实任务。正常使用时可关闭仪表盘网页，但 tunnel 进程需继续运行。重启代码/配置时更新原 launcher，已有 profile/Tunnel ID 不因源码目录改名而需要重建。

下一步是[手工任务交接与返回证据](TASK_HANDOFF_TEMPLATE.md)，不是再增加一个聊天界面。统一 handoff、workspace locking、持久化 TaskSpec 与 EvidencePack 仍按 Issue #6 独立实现。

参考：[官方隧道说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)、[上游 end-user guide](https://github.com/openai/tunnel-client/blob/master/docs/end-user-guide.md)、[profile 与 secret reference](https://github.com/openai/tunnel-client/blob/master/docs/configuration.md)。上游界面/选项会变化，核对安装版本；本文不会自动关闭附带 helper 或改变本机部署。
