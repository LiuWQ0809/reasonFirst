# Documentation index

These guides describe the source revision containing them. A merged feature is not necessarily included in the last release tag. See [the main README](../README.md) and [Unreleased changes](../CHANGELOG.md).

## Current entry points

| Topic | Document |
| --- | --- |
| Product and supported capabilities | [ReasonFirst](../README.md) |
| Source setup and first controlled task | [Current quickstart](ACTUAL_CODER_QUICKSTART.md) |
| 当前中文安装与使用 | [中文快速上手](QUICKSTART_CN.md) |
| Architectural intent | [Design philosophy](DESIGN_PHILOSOPHY.md) |
| HTTP-to-HTTPS migration | [English](HTTPS_MIGRATION.md) / [中文](HTTPS_MIGRATION_CN.md) |
| API/MCP private-CA trust, redirects, and native Git boundaries | [English](HTTPS_API_TLS.md) / [中文](HTTPS_API_TLS_CN.md) |
| PR checkout, tests, and normal-install updates | [Local PR review](LOCAL_PR_REVIEW.md) |
| Contribution process | [Contributing](../CONTRIBUTING.md) |
| Security reporting and current limitations | [Security policy](../SECURITY.md) |
| Before announcing a public release | [Maintainer checklist](PUBLIC_RELEASE_CHECKLIST.md) |

## Optional client/deployment recipes

[MCP setup (English)](SETUP_TUTORIAL.md), [MCP 配置（中文）](SETUP_TUTORIAL_CN.md), and [team tunnel setup](OPENAI_TUNNEL_TEAM_SETUP_CN.md) describe optional reasoning-client connectivity, not prerequisites for the local CLI. Provider availability and UI instructions can change; verify the current provider documentation. These recipes do not enable a local task-execution MCP endpoint. Apply the current [runtime TLS guide](HTTPS_API_TLS.md) to their transport configuration: API redirects and disabled verification are no longer accepted, and native Git remains separate.

[Chinese onboarding](ONBOARDING_GUIDE_CN.md) contains detailed deployment recipes. Where older lower-level task/commit/push examples differ, use the current quickstart's `start -> finish -> ci -> resume` path and the current security policy. [Troubleshooting](TROUBLESHOOTING.md) retains earlier operational notes; an HTTP example is not the preferred configuration for a new installation.

## Historical designs and implementation notes

[V0.2 design](V0.2_WRITE_ACCESS_DESIGN.md), [V0.2 Codex guide](V0.2_CODEX_QUICKSTART.md), [compatibility CodingAgent guide](CODINGAGENT_QUICKSTART.md), [V0.3 roadmap](V0.3_ROADMAP_CN.md), and [V0.3 audit](V0.3_RELEASE_AUDIT_CN.md) are historical context, not the authoritative current feature list.

The `V0.3.1_*_CN.md` files are focused implementation notes for [publication safety](V0.3.1_PUBLICATION_SAFETY_CN.md), [exit status](V0.3.1_COMMAND_EXIT_CN.md), [history scanning](V0.3.1_SECRET_HISTORY_CN.md), and [log evidence](V0.3.1_SHARED_LOG_EVIDENCE_CN.md). Their filenames do not announce a v0.3.1 release. Open [Issue #6](https://github.com/phoenixjyb/reasonFirst/issues/6) and [Issue #10](https://github.com/phoenixjyb/reasonFirst/issues/10) track work beyond the merged source.
