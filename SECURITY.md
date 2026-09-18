# Security notes

This project bridges ChatGPT to private source code. Treat the MCP host and its credentials as security-sensitive.

## Never commit

- `.env`
- a real `GITLAB_TOKEN`
- `CONTROL_PLANE_API_KEY`
- private certificates/keys
- copied CI logs or source files containing secrets

## Least privilege

Use a dedicated read-only identity/token and restrict projects with `GITLAB_ALLOWED_PROJECTS`.

The server intentionally exposes no write tools. If you add write actions later, review each tool, require the minimum GitLab scopes, and consider separating read-only and write-capable deployments.

## HTTP GitLab

HTTP can work on a trusted private network, but it does not encrypt the MCP-host-to-GitLab hop. Tokens and repository contents can be observed by an attacker on that network segment. Prefer HTTPS when possible.

## Prompt injection

Repository files, MR descriptions, issues, and CI logs are untrusted content. They can contain instructions intended to manipulate an AI system. Keep the MCP read-only, review any future write capability carefully, and do not expose unrelated secrets to the MCP process.
