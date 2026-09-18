# ChatGPT MCP for Self-Hosted GitLab Repositories

[![CI](https://github.com/phoenixjyb/chatgptMCPforOwnGitlabRepos/actions/workflows/ci.yml/badge.svg)](https://github.com/phoenixjyb/chatgptMCPforOwnGitlabRepos/actions/workflows/ci.yml)

A small, **read-only** MCP server that lets ChatGPT inspect repositories on a self-managed GitLab instance, including instances that are only reachable from your laptop, VPN, or private network.

The key idea is:

```text
ChatGPT
   │
   │ Secure MCP Tunnel (outbound HTTPS)
   ▼
OpenAI tunnel service
   ▲
   │
Your Mac / Linux host
   ├── tunnel-client
   └── this MCP server (stdio)
            │
            │ GitLab REST API (HTTP or HTTPS)
            ▼
      Self-hosted GitLab
```

The GitLab server does **not** need to be directly reachable from the public Internet. The machine running this project only needs to be able to reach both your GitLab instance and OpenAI over outbound HTTPS.

## What it exposes

The current server intentionally has no write tools:

- `gitlab_whoami`
- `list_projects`
- `get_repository_tree`
- `get_file`
- `search_code`
- `get_merge_request`
- `get_merge_request_diff`
- `get_pipelines`
- `get_pipeline_jobs`
- `get_job_log`

Large files, MR diffs, and CI logs are capped to avoid flooding the model context.

## Quick start

```bash
git clone https://github.com/phoenixjyb/chatgptMCPforOwnGitlabRepos.git
cd chatgptMCPforOwnGitlabRepos

cp .env.example .env
chmod 600 .env
# edit .env with your GitLab URL and read-only token

uv sync
uv run python smoke_test.py
uv run mcp dev server.py
```

If the Inspector tests work, connect the same stdio server to ChatGPT using OpenAI Secure MCP Tunnel.

## Documentation

- **English setup guide:** [docs/SETUP_TUTORIAL.md](docs/SETUP_TUTORIAL.md)
- **中文配置教程:** [docs/SETUP_TUTORIAL_CN.md](docs/SETUP_TUTORIAL_CN.md)
- **Troubleshooting:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)

## Security defaults

- `.env` is ignored by Git.
- Use a dedicated token with only `read_api` and `read_repository`.
- Prefer a project/group access token or a dedicated read-only account when practical.
- Set `GITLAB_ALLOWED_PROJECTS` to limit what ChatGPT can inspect.
- All MCP tools are declared read-only.
- Host proxy variables are ignored by default for GitLab traffic (`GITLAB_TRUST_ENV=false`).
- Never commit your GitLab token, OpenAI runtime API key, or tunnel ID unless you intentionally want the tunnel ID public.

## HTTP GitLab instances

The MCP-to-GitLab hop can use HTTP if that is how your internal GitLab is currently deployed. This does **not** make HTTP safe: the GitLab token and response content are not TLS-protected on that network segment. Keep the MCP host and GitLab on a trusted network/VPN and migrate to HTTPS when practical.

The ChatGPT-to-MCP side still uses OpenAI Secure MCP Tunnel over outbound HTTPS.

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/)
- A self-managed GitLab token with read permissions
- ChatGPT Developer Mode with custom MCP access appropriate to your plan
- OpenAI [`tunnel-client`](https://github.com/openai/tunnel-client) for private/local MCP servers

## Status

Initial public version: **0.1.0**.

This project started as a working setup for an internal self-hosted GitLab and has been generalized so the repository does not contain deployment secrets or a hard-coded private hostname.
