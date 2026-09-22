# ReasonFirst v4.0.2 历史设计记录

v4.0.3 的实际安装与网页接入说明以包根目录 [README.md](../README.md) 为准。

v4 replaces the GitHub-Issue polling bus with a **local MCP server**.

## Responsibility boundary

```text
ChatGPT Web or ChatGPT Desktop chat
        │
        │ analysis / plan / review / approval
        ▼
ReasonFirst MCP on Mac
        │
        ├── workspace / SSH / credentials / evidence / safety gates
        │
        └── dedicated local Codex app-server
                │
                │ implementation / build / test / reviewed push only
                ▼
        local workspace or SSH target workspace
```

**ChatGPT is the planner/reviewer. Codex is the executor.** Codex is not asked to choose architecture or redefine the task.

## What changed from v3

- No GitHub polling on the primary path.
- `run_reasonfirst.sh` starts the MCP STDIO server, **not** `github_control_relay.py`.
- ChatGPT Desktop can start ReasonFirst directly as a local STDIO MCP server.
- ChatGPT Web can use the same server through OpenAI Secure MCP Tunnel.
- GitHub relay remains only as an explicit legacy fallback/audit path.
- Codex runs locally and inherits the normal global Codex configuration/login state.
- SSH targets do **not** need Codex installed.
- Remote commit/push is performed by Codex only after ChatGPT approves the exact reviewed snapshot.

## Codex global configuration

ReasonFirst launches a dedicated local `codex app-server` so ChatGPT chat remains independent from the execution backend. The child process reads the normal Codex config stack, including:

- `~/.codex/config.toml`
- trusted project `.codex/config.toml`
- model/provider settings
- rules and skills
- all other configured MCP servers
- normal Codex authentication state

The only per-process override is:

```text
mcp_servers.reasonfirst.enabled=false
```

This prevents the executor Codex from recursively invoking the ReasonFirst MCP server. It does **not** modify `~/.codex/config.toml` and does not disable other global configuration.

## Install / upgrade

```bash
cd ~/Downloads/reasonfirst_codex_web_bridge_v4_0_2

./apply_to_reasonfirst.sh \
  /path/to/reasonFirst
```

Then configure once:

```bash
/path/to/reasonFirst/tools/codex_web_bridge/configure_v4.sh
```

`configure_v4.sh`:

1. migrates `~/.config/reasonfirst/bridge.yaml` to v4;
2. preserves named SSH targets;
3. backs up `~/.codex/config.toml`;
4. replaces only `[mcp_servers.reasonfirst]`;
5. preserves all other Codex global configuration.

Restart ChatGPT Desktop / Codex after changing MCP configuration.

## Doctor

```bash
/path/to/reasonFirst/tools/codex_web_bridge/run_reasonfirst.sh --doctor
```

## ChatGPT Desktop

After `configure_v4.sh`, restart ChatGPT Desktop. ReasonFirst is configured as a local STDIO MCP server. You can also inspect/add it under Desktop MCP server settings.

The MCP command is:

```bash
/path/to/reasonFirst/tools/codex_web_bridge/run_mcp_server.sh
```

Do not expect a normal log stream when launching `run_reasonfirst.sh` manually without `--doctor`; an MCP STDIO server normally waits for JSON-RPC on stdin.

## ChatGPT Web via Secure MCP Tunnel
