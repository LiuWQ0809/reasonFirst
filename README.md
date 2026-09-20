# ReasonFirst

**English** · [简体中文](README_CN.md) · [Bilingual documentation index](docs/README.md)

> **Reasoning-first coding orchestration.**
> Use your strongest reasoning model for reasoning. Let coding agents do the coding.

[![CI](https://github.com/phoenixjyb/reasonFirst/actions/workflows/ci.yml/badge.svg)](https://github.com/phoenixjyb/reasonFirst/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

ReasonFirst connects interactive engineering reasoning with replaceable coding agents and a local GitLab workflow. A human and their chosen reasoning interface define the task; **ActualCoder** prepares a Git worktree, hands the task to **Codex CLI** or **GitHub Copilot CLI**, and supplies validation, Merge Request, and CI evidence for review.

The goal is to spend reasoning capacity on architecture, diagnosis, and review, while delegating implementation iterations to coding agents. ReasonFirst is not a model proxy, a quota-transfer service, or an auto-merge bot. It makes no direct model-inference calls; external coding tools use their own authentication and billing arrangements. Cost savings are a design goal, not a measured guarantee.

**Early-stage developer tooling:** use trusted repositories on a trusted development host. A Git worktree is not a security sandbox. Read [SECURITY.md](SECURITY.md) before using real credentials or executing repository code.

## Start here

| Goal | Guide |
| --- | --- |
| Know where reasoning, transport, and coding happen | [One reasoning interface, one implementation workflow](docs/WORKFLOW.md) |
| Install and run a first task | [Current quickstart](docs/ACTUAL_CODER_QUICKSTART.md) |
| 中文安装与日常使用 | [当前中文快速上手](docs/QUICKSTART_CN.md) |
| Connect or restart normal ChatGPT's GitLab reads | [MCP operator guide](docs/SETUP_TUTORIAL.md) · [中文](docs/OPENAI_TUNNEL_TEAM_SETUP_CN.md) |
| Carry approved requirements and return evidence | [Manual task handoff template](docs/TASK_HANDOFF_TEMPLATE.md) |
| Understand the architecture | [Design philosophy](docs/DESIGN_PHILOSOPHY.md) |
| Move an existing GitLab installation to HTTPS | [English migration guide](docs/HTTPS_MIGRATION.md) · [中文迁移指南](docs/HTTPS_MIGRATION_CN.md) |
| Configure API/MCP certificates and understand redirect errors | [Runtime TLS](docs/HTTPS_API_TLS.md) · [中文](docs/HTTPS_API_TLS_CN.md) |
| Check out a PR directly, without ZIP files | [Local PR review](docs/LOCAL_PR_REVIEW.md) |
| Contribute or report a problem | [Contributing](CONTRIBUTING.md) · [Security reporting](SECURITY.md#reporting-a-security-issue) |
| Find current versus historical documentation | [Documentation index](docs/README.md) |

## How it works

```text
Human + reasoning interface
  define goal, constraints, acceptance criteria
                  |
                  v
ActualCoder / gitlab-agent
  prepare workspace and bounded handoff
                  |
                  v
Codex CLI or Copilot CLI
  inspect -> implement -> test
                  |
                  v
finish review -> feature branch / GitLab MR -> CI evidence
                  |
                  v
Human + reasoning interface review and decide the next step
```

The optional read-only GitLab MCP bridge lets a reasoning client inspect repositories, MRs, and CI. **It does not currently submit or execute local coding tasks through MCP.** The human operates the local CLI and carries task/result context between the interfaces. Persistent task specifications and a unified evidence API are planned, not shipped.

**For the recommended ChatGPT workflow, no localhost Assistant is needed.** Use a normal ChatGPT conversation for reasoning and review; keep `tunnel-client` and `server.py` running for the tunnel-based read connection; use ActualCoder plus the selected coding CLI for implementation. The local dashboard's Overview/Logs are optional diagnostics. Its Assistant tab and Codex tunnel plugin are not onboarding requirements or acceptance gates. Not using that UI does not uninstall the coding CLI or guarantee that the upstream client's bundled helper is disabled.

Validate the read path with live identity and file calls in normal ChatGPT, not an answer in `/ui#codex`. The [workflow guide](docs/WORKFLOW.md) separates startup, API/Git access, read acceptance, and approved writes. The [manual handoff template](docs/TASK_HANDOFF_TEMPLATE.md) is a writing aid, not an implemented TaskSpec/EvidencePack format.

GitLab is the current target SCM/CI integration. This project's source is hosted on GitHub; that does not imply a GitHub-target task adapter exists. Architecture is provider-neutral in intent; the implemented coding adapters are currently `codex` and `copilot`.

## Try the source without production credentials

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/). Package metadata requires Python 3.10+; the current CI matrix exercises Python 3.12 on Ubuntu, macOS, and Windows. Use 3.12 to reproduce it.

Run from a new checkout, one command at a time; stop on errors:

```bash
git clone https://github.com/phoenixjyb/reasonFirst.git
cd reasonFirst
uv sync --python 3.12
uv run actual-coder --help
uv run actual-coder-migrate-https --help
uv run python -m unittest discover -s tests -v
uv run python scripts/check_repo_secrets.py --history
```

These regression tests use temporary repositories, mocked services, and loopback TLS fixtures, not production tokens or paid model sessions. Installing dependencies may access package indexes. Do not point test fixtures at a live workspace.

For real use, follow the [quickstart](docs/ACTUAL_CODER_QUICKSTART.md): configure your own GitLab HTTPS endpoint, least-privilege tokens, an explicit project allowlist, and a supported coding CLI. MCP/tunnel setup is optional for the local workflow.

## The recommended task loop

From the ReasonFirst source checkout, use `uv run` so you execute that checkout's environment. Replace `team/project-a` and the example workspace ID with your own values.

```bash
uv run actual-coder start team/project-a --task fix-timeout --goal "Fix the timeout bug; preserve the public API and add regression coverage" --no-launch
```

`--no-launch` prepares a real managed workspace and handoff, but does not invoke a coding model. It is **not** a no-side-effect dry run. Review the handoff, then use the returned backend command and prompt to perform the task, or omit `--no-launch` on a new `start` to launch interactively.

After implementation, review and finish the returned workspace:

```bash
WS="012345abcdef"
uv run actual-coder status "$WS"
uv run actual-coder finish "$WS" --message "fix: handle timeout and add regression test" --dry-run
uv run actual-coder finish "$WS" --message "fix: handle timeout and add regression test"
uv run actual-coder ci "$WS"
```

Run the actual `finish` only after inspecting the preview and confirming the intended writes. **Finish dry-run still executes configured project validation commands; it means no commit/push, not no code execution.** A missing `.actualcoder.yaml` is allowed but supplies no project-specific validation commands. Add real build/test requirements before relying on finish as a quality gate.

For a genuine CI failure, `resume --from-ci` returns a handoff tied to matching-HEAD CI. It does not launch a repair automatically. Success is not a reason to invent changes. Low-level `commit`/`push` commands and some existing generated handoffs expose manual routes; those routes do **not** run all finish gates. Review worker actions and use `finish` for the primary flow.

## What is available on `main`

The last documented release is **v0.3.0**. Post-release changes below are merged source changes; package version metadata still reads `0.3.0`. Identify bug reports by commit SHA as well as version. See [CHANGELOG.md](CHANGELOG.md).

| Capability | Current scope |
| --- | --- |
| Managed workspaces | Local Git caches/worktrees, feature branches, MR creation/update/recovery |
| Controlled finish | Base-policy validation, reviewability/protected-path checks, candidate and bounded commit-history secret scanning, human confirmation |
| Publication safety | Fresh remote evidence before ordinary cleanup; unpublished abandoned branches preserved |
| Command results | Nonzero child failures and timeouts propagate to the shell |
| CI feedback | Matching-HEAD evidence and shared bounded/sanitized CLI/MCP failed-job logs |
| HTTPS migration | Explicit offline preview and confirmed local URL updates, with private backups and forward recovery |
| API/MCP transport | Verified public roots plus optional Python-only private CA; request-destination checks and rejection of all API redirects |
| Read-only MCP | Project/file/MR/pipeline/job inspection; no local task execution endpoint |

**Not yet delivered:** native Git trust/destination-policy integration and layered API-versus-Git diagnostics, consistent project context on every handoff route, general workspace locking/transactional recovery, persistent TaskSpec/attempt records, and EvidencePack access. The migration-only lock does not provide these capabilities. [HTTPS work](https://github.com/phoenixjyb/reasonFirst/issues/10) and the [task-loop roadmap](https://github.com/phoenixjyb/reasonFirst/issues/6) track them.

**Transport upgrade:** Python API/MCP clients now reject `GITLAB_VERIFY_SSL=false` and every API redirect, including same-origin redirects. Configure the final endpoint directly. For a private CA, `GITLAB_CA_BUNDLE` adds certificates to public roots without enabling proxy inheritance. It does not configure native Git or the migration command’s optional `--check-tls` probe. Publicly trusted deployments normally need no extra CA setting. See [runtime TLS](docs/HTTPS_API_TLS.md).

## Names and compatibility

**ReasonFirst** is the project; **ActualCoder** (`actual-coder`) is the high-level CLI. `gitlab-agent` is the lower-level controller and `codingagent` is a compatibility alias. Python package `gitlab_agent`, distribution `chatgpt-selfhosted-gitlab-mcp`, user config `~/.config/gitlab-agent/.env`, and existing workspace paths are intentionally retained. Do not rename managed directories as part of a source update.

The user installer is editable: global commands follow the source checkout from which they were installed. Keep that checkout on a reviewed ref, and use a separate worktree for PR experiments. See [local PR review](docs/LOCAL_PR_REVIEW.md) for updating the normal installation without copying downloads.

## Contributing and license

Contributions, reproducible bug reports, documentation improvements, and regression tests are welcome. English and Chinese reports are both welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). Never attach private repositories, raw credentials, migration backups, or unreviewed logs to public issues.

Licensed under the **Apache License 2.0**; see [LICENSE](LICENSE). External coding tools and services have their own licenses and terms. This is an independent project, not an official OpenAI, GitHub, or GitLab product. Maintainers should use the [public-release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md) before announcing a release.
