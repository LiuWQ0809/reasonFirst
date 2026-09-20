# Confirm project access before planning a task

[简体中文](PROJECT_ACCESS_CN.md) · [Documentation index](README.md) · [Workflow](WORKFLOW.md)

**A proposed project name is not a verified remote repository. A local folder, successful tunnel startup, or `gitlab_whoami` response does not establish project access.** For every newly introduced project, check access before requesting many files, defining repository-grounded acceptance criteria, or creating an ActualCoder workspace.

## Three separate permission layers

| Layer | What the user/operator controls | What it does not grant |
| --- | --- | --- |
| ChatGPT connection / OpenAI tunnel | Access to the intended connection and tunnel | GitLab project membership or local project allowlisting |
| ReasonFirst MCP process | `GITLAB_ALLOWED_PROJECTS` in its effective private configuration/environment | GitLab token permissions or existence of a project |
| GitLab | Project existence, membership, repository visibility, credential scopes | Permission through the local MCP allowlist |

When a user says “grant it in tunnel settings,” identify the actual layer. In the current implementation, **the per-project grant belongs to ReasonFirst's local MCP configuration, not `control_plane` in the tunnel YAML or a project picker in OpenAI settings**. Keep the existing tunnel. Do not claim this repository provides an authorization UI.

## First action in normal ChatGPT

Use the selected live GitLab MCP to call:

```text
check_project_access(
  project="team/project-a",
  ref="main",
  required_files=["README.md"]
)
```

These are example identifiers, not evidence that the project exists. Replace them with the exact user-confirmed GitLab `namespace/project` or a positive numeric project ID; do not supply a URL or leading slash. Include the files needed for the actual task (up to 16 unique paths).

The check is read-only: local policy first, then project metadata, then the requested/default ref, then file metadata using **HEAD requests pinned to the resolved commit**. It never downloads file contents, creates a project/branch/workspace, grants access, changes a token, or runs a coding backend. It has a 30-second overall budget and a 128-KiB cap per metadata response. It stops at the first failed dependency, preserving evidence collected so far.

On `ok: true`, use `resolved_commit_sha` for subsequent file reads so the planning snapshot stays consistent. A successful metadata preflight does not replace reading the actual source, and does not prove Git push permission, a successful test suite, or a future unchanged branch. `required_files_complete` refers only to the explicitly supplied files. Empty `required_files` does not test any file.

On `ok: false`, **show the diagnostic and wait for the user**. Do not repeat seven failing file requests, switch to an allowed production project, use GitHub as a substitute for the requested GitLab instance, or invent missing source evidence. Expected failures are returned as structured diagnostic data so clients that mask ordinary tool exceptions still receive them. MCP transport success with `ok: false` is not successful repository access.

## What the result means

| Error code | Evidence | Required next action |
| --- | --- | --- |
| `project_not_allowlisted` | Local grant missing; no GitLab request; `project_exists: null` | Ask the user/operator to approve this exact project in the local MCP configuration, then restart and retry. |
| `credential_missing` / `gitlab_unauthorized` | Missing process credential / HTTP 401 | Operator checks the GitLab credential privately. Never ask for its value in chat. |
| `gitlab_forbidden` | HTTP 403 | User/administrator checks GitLab access/scopes/instance policy. |
| `project_missing_or_inaccessible` | Project lookup returned HTTP 404 | Confirm the instance, path/ID and membership. **Do not assert nonexistence.** |
| `repository_empty` | GitLab explicitly reported `empty_repo: true` | User initializes the intended repository after approving the seed. |
| `default_branch_unavailable` | Metadata returned no usable default branch | Confirm an explicit ref or initialize the intended branch; null default alone is not proof of an empty/missing project. |
| `ref_missing_or_inaccessible` | Project metadata succeeded; ref lookup returned 404 | Confirm the requested branch/tag/commit and access. Do not silently use another ref. |
| `required_file_missing_or_inaccessible` | Pinned file metadata request returned 404 | Confirm seed contents, exact path and read access; stop source-based task planning. |
| `resource_missing_or_inaccessible` | A direct file/tree/MR request returned 404 without a staged preflight | Run the preflight to identify the failing layer; no project-nonexistence claim. |
| `gitlab_rate_limited`, `gitlab_unavailable`, `timeout`, transport/TLS errors | Service or transport failure, not proof of an authorization problem | Diagnose that layer; do not weaken TLS, recreate the tunnel or expand permissions as a generic fix. |

Raw HTTP bodies, redirect destinations, exception text, token values and private configuration contents are not included in these diagnostics. Numeric IDs and paths are exact allowlist keys: authorization for one representation is not permission to probe another representation outside the list. A fully filtered `list_projects` page may be empty; its `next_page` is a candidate based on the upstream page size, not a guarantee of another visible project. Membership-filtered listings are not a complete inventory of everything a credential can access.

## User-controlled grant procedure

First confirm whether the remote project already exists on the intended GitLab instance. **Only if the user verifies nonexistence and approves creation**, create/seed that specific project through the normal GitLab workflow. A 404 alone never authorizes creation.

For a deliberate local grant, the operator privately edits the effective user configuration selected by `GITLAB_AGENT_ENV_FILE` (normally `~/.config/gitlab-agent/.env`). Append the exact approved project to `GITLAB_ALLOWED_PROJECTS`, preserving the other intended entries. Never clear it: the existing MCP read policy treats an empty list as all token-accessible projects. No code in this change modifies this policy automatically.

Restart the **existing** MCP/tunnel process. An exported `GITLAB_ALLOWED_PROJECTS` may override the file; the operator must resolve that locally. The assistant must not inspect `.env`, password stores or shell profiles to find credentials. If the shared daemon is administered by someone else, ask that operator rather than changing a different local file. Refresh the existing ChatGPT connection's tool discovery after deploying a version containing the new tool, then retry the same preflight. No new tunnel, OpenAI runtime key or localhost Assistant is needed solely to authorize a project.

## Optional local helper

From a reviewed source checkout with dependencies installed:

```bash
uv run actual-coder-check-project team/project-a --ref main --require-file README.md
```

Equivalent source helper:

```bash
uv run python scripts/check_project_access.py team/project-a --ref main --require-file README.md
```

These commands print JSON and return **0 only for `ok: true`, otherwise 1**. They use the selected user configuration, verified Python API transport, explicit CA policy, and existing proxy policy. They do not create caches/workspaces or launch Git/Codex. Native Git trust and write permissions remain separate. `mcp_connection_checked: false` makes clear that a local CLI probe is not proof of the running ChatGPT connection's settings.

`workspace_policy_allowed` separately reports the configured local workspace policy; it is not GitLab write authorization. With the existing default empty-list policies, read preflight can succeed while local/write workflows still require an explicit allowlist. This helper does not auto-run inside every `start`/`resume` or alter Git-only workflows. The documented new-project workflow and MCP instructions require preflight; actual project reads still independently enforce the local allowlist. Nothing here is an OS sandbox or an approval mechanism for autonomous writers.

## Reusable first-conversation prompt

```text
Use only the selected GitLab MCP for the exact project and ref I have confirmed.
Call gitlab_whoami, then check_project_access with all files needed for this task.
If the tool is unavailable, explain that the running MCP needs updating/discovery;
do not claim a preflight happened. If ok=false, report error.code, stage, HTTP
status when returned, known versus unknown existence, and the user action needed.
Stop and wait. Do not create a project, change an allowlist, request credentials,
try another repository, or begin the implementation handoff.
Only after successful preflight, read the required files at resolved_commit_sha,
then prepare the approved stage's plan and acceptance tests.
```

Record the exact instance/project, grant status, resolved commit, required-file results and missing evidence in the manual handoff. For the practice kit, the required files are README.md, EXERCISE.md, AGENTS.md, .actualcoder.yaml, .gitlab-ci.yml, clip_summary.py and tests/test_clip_summary.py.

Primary references: [GitLab projects API](https://docs.gitlab.com/api/projects/), [commits API](https://docs.gitlab.com/api/commits/), [file metadata API](https://docs.gitlab.com/api/repository_files/), [authentication](https://docs.gitlab.com/api/rest/authentication/). API responses can be ambiguous; preserve uncertainty rather than guessing.
