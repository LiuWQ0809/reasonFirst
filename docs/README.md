# Documentation index

These guides describe the source revision containing them. A merged feature is not necessarily included in the last release tag. See [the main README](../README.md) and [Unreleased changes](../CHANGELOG.md).

## Current entry points

| Topic | Document |
| --- | --- |
| Product and supported capabilities | [ReasonFirst](../README.md) |
| Which interface to use and what each check proves | [One reasoning interface, one implementation workflow](WORKFLOW.md) |
| Source setup and first controlled task | [Current quickstart](ACTUAL_CODER_QUICKSTART.md) |
| 当前中文安装与使用 | [中文快速上手](QUICKSTART_CN.md) |
| Connect/restart normal ChatGPT's GitLab reads | [English operator guide](SETUP_TUTORIAL.md) / [中文团队接入与重启](OPENAI_TUNNEL_TEAM_SETUP_CN.md) |
| Manual approved-task handoff and result evidence | [Writing template, not a runtime API](TASK_HANDOFF_TEMPLATE.md) |
| Architectural intent | [Design philosophy](DESIGN_PHILOSOPHY.md) |
| HTTP-to-HTTPS migration | [English](HTTPS_MIGRATION.md) / [中文](HTTPS_MIGRATION_CN.md) |
| API/MCP private-CA trust, redirects, and native Git boundaries | [English](HTTPS_API_TLS.md) / [中文](HTTPS_API_TLS_CN.md) |
| PR checkout, tests, and normal-install updates | [Local PR review](LOCAL_PR_REVIEW.md) |
| Diagnosis without weakening controls | [Troubleshooting by layer](TROUBLESHOOTING.md) |
| Contribution process | [Contributing](../CONTRIBUTING.md) |
| Security reporting and current limitations | [Security policy](../SECURITY.md) |
| Before announcing a public release | [Maintainer checklist](PUBLIC_RELEASE_CHECKLIST.md) |

## One reasoning interface, not another required chatbot

Normal ChatGPT is the chosen reasoning/review interface in these guides. The tunnel/MCP are read transport and tools; ActualCoder plus a selected coding CLI performs approved implementation through a manual handoff. The local dashboard Assistant and Codex tunnel plugin are optional upstream features, not prerequisites or acceptance gates. Overview/Logs may help diagnosis. Not using the Assistant does not disable its bundled helper or remove the coding CLI.

For an existing working installation, start at [restart](SETUP_TUTORIAL.md#restart-an-existing-profile), not first-time setup. Accept the connection with a live identity/file read in normal ChatGPT, not a localhost Assistant answer. No local task-submission MCP endpoint or automatic TaskSpec/EvidencePack ingestion is enabled by these documents.

Provider availability and UI instructions can change; follow the primary references in the operator guide. Keep API/MCP runtime trust, native Git, and the maintenance probe distinct using the current TLS guide.

## Historical designs and detailed legacy recipes

[Chinese onboarding](ONBOARDING_GUIDE_CN.md) and the older [Chinese setup tutorial](SETUP_TUTORIAL_CN.md) retain legacy deployment examples; they are not the current required checklist. Prefer the current guides above for restart, credentials, source updates, read acceptance, and the `start -> finish -> ci -> resume` workflow. Do not execute old token-bearing examples, overwrite a working `.env`, or install optional components solely because a historical recipe mentions them.

[V0.2 design](V0.2_WRITE_ACCESS_DESIGN.md), [V0.2 Codex guide](V0.2_CODEX_QUICKSTART.md), [compatibility CodingAgent guide](CODINGAGENT_QUICKSTART.md), [V0.3 roadmap](V0.3_ROADMAP_CN.md), and [V0.3 audit](V0.3_RELEASE_AUDIT_CN.md) are historical context, not the authoritative current feature list.

The `V0.3.1_*_CN.md` files are focused implementation notes for [publication safety](V0.3.1_PUBLICATION_SAFETY_CN.md), [exit status](V0.3.1_COMMAND_EXIT_CN.md), [history scanning](V0.3.1_SECRET_HISTORY_CN.md), and [log evidence](V0.3.1_SHARED_LOG_EVIDENCE_CN.md). Their filenames do not announce a v0.3.1 release. [Issue #6](https://github.com/phoenixjyb/reasonFirst/issues/6) and [Issue #10](https://github.com/phoenixjyb/reasonFirst/issues/10) track remaining task-loop and HTTPS work.
