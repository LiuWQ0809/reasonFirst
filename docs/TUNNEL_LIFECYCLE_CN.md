# 第一次 ChatGPT 对话之前，先启动 Tunnel

[English](TUNNEL_LIFECYCLE.md) · [索引](README_CN.md) · [项目访问](PROJECT_ACCESS_CN.md) · [人工接入教程](OPENAI_TUNNEL_TEAM_SETUP_CN.md)

<!-- Translation source: TUNNEL_LIFECYCLE.md in this same change; executable examples are checked together. -->

**对于 Tunnel 接入方式，每次服务停止后都必须重新启动；这不是安装时做一次即可的步骤。** 普通 ChatGPT 读取 GitLab 时，服务必须持续运行。本地 ActualCoder/Codex 工作流与此分开，localhost Assistant 不是必需组件。

`actual-coder-tunnel` 管理的是**已经存在、由操作者明确选择**的 profile。它不会创建远端 Tunnel、授予项目权限、轮换令牌、覆盖 Tunnel YAML，也不会自动执行开发任务。辅助程序监督上游标准的 `doctor` / `run --profile` 命令，不采用会生成 profile 的上游 `runtimes connect` 路径。

## 支持范围

第一版通过 POSIX 进程组、文件锁和私有 Unix 控制 socket，管理 macOS/Linux **前台**进程。Windows 可以显示帮助，但生命周期操作明确返回 `platform_unsupported`，应继续使用现有上游启动步骤。这里不安装 launchd/systemd 服务、登录项、后台守护程序或无人值守重启循环。

支持 `config_version: 1`、标准 `https://api.openai.com` 控制面、`env:NAME` 或 `file:/absolute/path` 形式的运行时凭证引用、指向所选检出目录 `run_mcp.sh` 的**唯一 main stdio 命令**，以及固定的回环健康端口。常用的 `log.level`、`log.format` 和 `admin_ui.open_browser` 字段可以保留。高级、多通道、HTTP、cloudflared、MTLS profile、额外字段、YAML alias、动态端口 0、远程 UI 监听与明文密钥会被明确拒绝，不会被悄悄改写；这些部署仍可使用上游工具。

上游 CLI、profile 和 `/api/status` 的实现已按 tunnel-client `0.0.14+0f870e50a973fa820d4c409000059e181e8d242b` 源码核对。这是适配器兼容基线，不代表仓库 CI 真的启动过 OpenAI Tunnel。已安装客户端或状态协议不兼容时，应报告失败，而不是编造就绪状态。

## 1. 从获批检出目录安装

按[源码更新指南](LOCAL_PR_REVIEW_CN.md)更新正常检出目录，保留本地修改。首次改由辅助程序管理之前，在旧手动 Tunnel **自己的 Terminal** 按 Control+C 停止它，不能在同一端口启动第二份。

在已审阅的 ReasonFirst 检出目录运行：

```bash
uv sync --python 3.12
bash scripts/install_user.sh
actual-coder-tunnel --help
```

也提供源码入口：

```bash
uv run python scripts/tunnel.py --help
```

## 2. 一次性保存不含秘密的启动设置

示例 `gitlab-work` 只是占位名称，必须替换为 `tunnel-client profiles list` 中**已存在**的 profile。在正确的正常源码检出目录执行，不要使用临时 PR worktree：

```bash
actual-coder-tunnel configure --profile gitlab-work --source-dir "$PWD" --keychain-service openai-tunnel-runtime --keychain-account "$USER"
```

这是明确选择 Keychain 的配置，要求已有 generic-password 项：service 为 `openai-tunnel-runtime`，account 为当前 macOS 用户名。辅助程序不创建凭证、不广泛搜索密码库、不打印密钥。需要保存该项时，请在本机 Keychain Access 的 login 钥匙串中新建密码项，填入上述名称和账号，以及已有、具备 Tunnels Read + Use 权限的 **OpenAI 运行时 API key**；不要填 Tunnel ID、GitLab token 或 admin key。不要允许所有应用访问；读取该明确条目时，macOS 可能要求确认。命令和聊天中都不能出现密钥值。

辅助程序只把路径和引用名称写入 `~/.config/reasonfirst/tunnel.json`，文件权限 0600、父目录私有。它检查原 profile，以及所选 GitLab 私有配置的文件元数据，不读取 GitLab token 内容。默认 profile 目录为 `~/.config/tunnel-client`，GitLab 配置为 `~/.config/gitlab-agent/.env`，进程锁/socket 目录为 `~/.local/share/reasonfirst/tunnels`。`configure --help` 提供明确的路径选项。已有不同设置需人工审阅后使用 `configure --replace`；configure 不允许覆盖仍有活动 owner 的设置。

不用 Keychain 时省略这两个 Keychain 参数。此时 `env:` 引用要求启动 shell **每次启动时**已经有该变量；此前在子 shell 或另一 Terminal 中 export，并不表示永久保存。`file:` profile 使用原有的绝对路径、0600 私有密钥文件；辅助程序只检查元数据，由上游读取值。不自动切换 env/file/Keychain 去找另一份凭证。明确选择 Keychain 后，每次 start/restart 都重新读取该项，即使父 shell 还残留旧值。

## 3. 启动并保持 owner Terminal 运行

一次性配置后，可从任何目录运行：

```bash
actual-coder-tunnel start
```

启动过程加载选定的运行时凭证、执行上游 doctor、启动既有 profile，并等待本地健康状态、运行时身份及元数据匹配，默认上限 30 秒。**辅助程序保持在前台。** 保持该 Terminal、Mac 和网络可用；Control+C 会停止它自己管理的运行时。没有另行审阅服务设计时，不要再套 `nohup`、`disown` 或第二套进程管理器。

保存的设置明确选择一份 GitLab 私有配置。子进程保留必要的系统、locale、uv、代理环境与所选运行时 key 变量，但不继承任意 Tunnel/MCP/health 或 `GITLAB_*` 覆盖项。辅助程序明确传入 `GITLAB_AGENT_ENV_FILE`，避免旧 shell 值替换已审阅 profile 或配置文件；父 shell 和原文件不改变。有意设置的 GitLab 参数应写在所选文件中。运行时 key 仍存在于受信任进程的环境内，Keychain 存储不是对同用户代码的操作系统隔离。

辅助程序不会转发或保存上游原始 stdout/stderr，只输出受限、结构化的 JSON 状态和错误，不复制 HTTP 响应正文、profile 内容或凭证。必要时可在本机私下检查既有 UI 的 Overview/Logs，不会调用 Assistant。Doctor 失败也不会把加载的 key 导回父 shell，因此之后在新 Terminal 直接运行上游命令时仍需独立、安全地加载 key。

## 4. 状态、停止与重启

在第二个 Terminal 中运行：

```bash
actual-coder-tunnel status
```

| 状态/结果 | 含义与下一步 |
| --- | --- |
| `ready_for_chatgpt_check` | 辅助程序拥有活动子进程；`/healthz` 和 `/readyz` 均为 200；`/api/status` 身份匹配，且报告已获取元数据。**现在去普通 ChatGPT 做真实调用。** |
| `running_not_ready`、`probe_stale`、`probe_failed` | Owner 存在，但就绪或证据尚未确立。检查状态/UI，不把整个流程说成已打通。 |
| `control_plane_error` | 上游元数据状态报告错误；私下核对运行时 key、组织、网络。不会输出原始错误正文。 |
| `not_running` | 所选设置下没有发现 owner 或监听服务，应运行 start。 |
| `unmanaged_listener` | 端口已被占用，但不属于此辅助程序。检查原 Terminal，不盲目启动、接管或结束进程。 |
| `configuration_changed` | 设置/profile 与 owner 保存的快照不同，或当前已无法读取。审阅后重启；运行中进程没有自动重载文件。 |
| `owner_unresponsive_or_starting` | Owner 锁存在，但没有可响应的控制端点。等待预检，或在 owner Terminal 按 Control+C；不提供按旧 PID 强制处理的后门。 |

`status` 只在本地就绪已验证时返回 0，其他情况返回 1。它不读取运行时密钥，停止状态下也不创建状态目录。输出始终把 `chatgpt_connection_verified: false`、`project_access_checked: false` 与本地就绪分开。缓存样本有年龄，过期样本不会保持绿色。元数据匹配不证明持续轮询、stdio 工具发现或任何 GitLab 项目权限。

只停止本辅助程序可响应、明确拥有的实例：

```bash
actual-coder-tunnel stop
```

停止请求发送给带实例身份校验的私有控制 socket。Owner 对**自己启动的子进程组**发送 SIGTERM，等待最多五秒；仍未结束时，才可能对该仍在跟踪的进程组发送 SIGKILL。不使用 `pkill`、`killall`、保存的 PID 或过期 PID 文件。已经停止时可幂等成功；不接管、不停止其他启动器管理或无法响应的进程。

重新加载凭证并重启：

```bash
actual-coder-tunnel restart
```

Restart 在请求旧 owner 停止之前，先校验替代进程的本地 profile、可执行文件及凭证来源。之后才执行 doctor/网络就绪检查；这些后续检查仍可能失败，导致 Tunnel 保持停止状态，不自动回滚或替换凭证。执行 restart 的 Terminal 成为**新的前台 owner**。正常 stop/status 不需要运行时 key；即使刚编辑的 profile 无法解析，也仍可停止原有、可响应的 owner。

同一状态目录下的并发启动共享 profile 锁与 Tunnel 锁。同一健康实例重复 start，只返回状态，不再启动一份；指定地址被其他进程占用时也阻止启动。但这不是跨其他端口、其他机器或其他状态目录的全局运行时发现。不要对同一 Tunnel 混用手动、上游 managed runtime 和此辅助程序三种启动方式。

## 5. 验收真实连接

源码更新时执行“stop → 更新/sync/install → start”。设置/profile 指纹不是完整源码修订校验，因此运行时代码升级后，即使没有配置变化也要重启。工具列表变化时刷新既有 ChatGPT 连接的工具发现，不需要创建新 Tunnel。

在普通 ChatGPT 中选择正确连接后发送：

```text
只使用已连接的 GitLab MCP，不使用 localhost Assistant、网页或旧结果。
先调用 gitlab_whoami，再针对我明确确认的项目/ref 调用 check_project_access。
ok=false 时说明失败层次及用户应做的操作，然后停止等待。
成功后才在 resolved_commit_sha 上读取所需源码，只报告真正返回的修订标识。
不要创建项目或自动授权。
```

真实成功的身份、访问预检和文件读取才是最终验收证据。[实战演练](PRACTICE_LAB_CN.md)的独立项目必须真实存在、已推送初始文件，并在 `GITLAB_ALLOWED_PROJECTS` 中获明确授权，才能继续。本地就绪不能代替这些步骤；localhost Assistant 不是前提或验收门槛。

## 局限与恢复

`runtime_key_missing`、`keychain_unavailable`、`launcher_mismatch`、`doctor_failed`、`startup_timeout` 是不同故障。启动超时只会停止此次新建、受管的运行时，不故意留下后台孤儿。强制结束 supervisor、内核故障或上游崩溃仍可能留下后代进程，此辅助程序刻意拒绝按过期 PID 不安全地恢复；应本地核实，并通过真实所属服务/Terminal 停止确定的进程。锁/socket 不含密钥值，不要删除活动锁文件来绕过所有权。

没有实现开机自启、分布式所有权、Windows 进程控制、全局权限绕过、TLS 降级、新授权 UI 或自动项目授权。测试使用真实辅助子进程、回环 HTTP 和模拟 tunnel 可执行文件，不访问 OpenAI 控制面，也不访问用户 Mac 的 Keychain。参见[安全边界](../SECURITY_CN.md)。

一手参考：[OpenAI Tunnel 指南](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)、[上游 run](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/cmd/client/run_command.go)、[managed runtime 生成 profile](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/cmd/client/runtimes_command.go)、[管理状态字段](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/pkg/adminui/fxmodule.go)、[配置优先级](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/pkg/runtimeconfig/config.go)。
