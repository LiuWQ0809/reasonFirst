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

