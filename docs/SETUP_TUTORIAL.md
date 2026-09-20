# Connect normal ChatGPT to the read-only GitLab MCP

[中文](OPENAI_TUNNEL_TEAM_SETUP_CN.md) · [Workflow](WORKFLOW.md) · [CLI quickstart](ACTUAL_CODER_QUICKSTART.md) · [Troubleshooting](TROUBLESHOOTING.md)

**The localhost Assistant is not required.** ChatGPT is the reasoning interface; `tunnel-client` is transport; ReasonFirst's `server.py` exposes GitLab reads. ActualCoder and the selected coding CLI are the separate implementation workflow. There is no local task-execution MCP endpoint today.

```text
Normal ChatGPT <-> OpenAI tunnel <-> tunnel-client on your host
               <-> ReasonFirst stdio MCP <-> GitLab HTTPS API
```

Do not enter the acceptance prompt into the dashboard's Assistant tab (`/ui#codex`). That is a separate upstream Codex interface with separate approval behavior. Overview/Logs are optional diagnostics; neither the Assistant nor its Codex plugin is a prerequisite. Closing the browser dashboard does not stop the tunnel or necessarily disable its bundled background helper.

## Choose the right starting point

| Current state | Next action |
| --- | --- |
| CLI API/Git already work and a tunnel profile exists | [Restart the existing profile](#restart-an-existing-profile) |
| CLI works but no tunnel/profile exists | [First-time connection](#first-time-connection) |
| CLI configuration or HTTPS is not ready | [CLI quickstart](ACTUAL_CODER_QUICKSTART.md) / [migration](HTTPS_MIGRATION.md) |
| Tunnel started and fetched metadata | [Accept the read connection](#accept-the-read-connection) in normal ChatGPT |
| Only the localhost Assistant refuses a tool call | Leave that optional panel aside; do not loosen approvals to test ChatGPT |

Do not repeat a completed migration, reinstall tools, rotate working keys, or create another tunnel as generic troubleshooting. An actually exposed credential is different: revoke/rotate it and remove credential-bearing notes, not just the displayed URL.

## Keep the settings separate

| Setting | Meaning | Storage / consumer |
| --- | --- | --- |
| `GITLAB_BASE_URL` | Your final GitLab HTTPS endpoint | Private user `.env`, read by ReasonFirst |
| `GITLAB_TOKEN` | GitLab API credential | Private user config or explicitly loaded environment |
| `GITLAB_GIT_TOKEN` | Separate repository-write credential when needed | ActualCoder; not needed for the MCP read path |
| `control_plane.tunnel_id` | Existing OpenAI tunnel identifier | Local tunnel profile; not a bearer secret, but deployment information |
| `CONTROL_PLANE_API_KEY` | OpenAI runtime API key authorized for tunnel use | Approved secret storage, supplied to tunnel-client |
| `control_plane.base_url` | OpenAI tunnel control-plane endpoint | Tunnel profile; **not** the GitLab URL |

The profile reference `api_key: "env:CONTROL_PLANE_API_KEY"` asks for an environment variable; it is not the key itself. A `tunnel_...` ID is not an API key. Key-prefix appearance does not establish validity or permissions. Tunnel use needs the applicable Platform organization and Tunnels Read + Use permissions; management/admin permissions are separate. Do not substitute an admin key or a GitLab token. Current provider eligibility and workspace association are described in the [official tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) and [Developer Mode help](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt).

ReasonFirst's user config is plaintext protected by filesystem permissions, not a secret vault. Its loader does not resolve Keychain/file/env references placed inside `GITLAB_TOKEN`; keep secret retrieval separate. Use [SECURITY.md](../SECURITY.md) and operator-approved storage. Never put credentials in reference notes, command arguments, screenshots, or public logs.

## Restart an existing profile

These steps are for an interactive macOS/Linux Terminal session. A service-managed tunnel must be restarted through its existing supervisor and service environment; do not start a competing foreground instance. Windows users should use the [team guide](OPENAI_TUNNEL_TEAM_SETUP_CN.md).

### 1. Stop the specific old process and inspect the launcher

Press Control+C in the Terminal running this profile. Do not kill every Python/Codex process. List the profiles:

```bash
tunnel-client profiles list
```

Use the returned profile name and file path. Inspect that file privately in a local editor, without printing the full profile into a chat. A stdio command should point to the long-lived, reviewed checkout, not a removed directory or a temporary PR worktree. Example fragment only:

```yaml
mcp:
  commands:
    - channel: main
      command: "bash /absolute/path/to/reasonFirst/run_mcp.sh"
```

Replace the illustrative absolute path before using it. Preserve the existing tunnel ID, key reference, and other profile settings. Changing Terminal's directory does not change an absolute path stored in YAML. `run_mcp.sh` changes into its own directory and launches `server.py`; running it alone is not a tunnel connection. For paths containing spaces, use the installed client's supported quoting syntax and verify it with `doctor`.

### 2. Load the intended config and runtime credential, then start

Open the long-lived source checkout in Terminal first. Confirm `run_mcp.sh` exists. The following block is explicitly executed by **Bash**, so it can be pasted from macOS zsh without relying on zsh's interactive-comment or `read` behavior. Replace `selfhosted-gitlab` with the existing profile name and adjust the config path only if your installation uses another file.

This block is for profiles using `env:CONTROL_PLANE_API_KEY`. It reuses an exported key or reads your existing runtime key at a hidden local prompt. It does not save the entered key. For an existing `file:` secret reference, keep that reference and use `doctor`/`run` with its existing secure loader instead of prompting unnecessarily.

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

The base-URL unset applies only in this child shell and selects the value from the explicit user config. Deliberate exported overrides require deliberate handling; do not edit a working `.env` to fix a stale launcher environment. GitLab credentials already exported by the launcher also override the file. After a credential/config update, clear stale overrides in that launcher and restart it.

A missing environment key is not evidence that the key was revoked. Retrieve it from your approved secret store; do not recreate a tunnel. This block never prints the key or puts its literal value into shell history. It is not protection against arbitrary same-user processes, and it does not implement a new Keychain integration.

If `doctor` fails, `run` is not started. `RESULT ok`, startup, and metadata-fetch logs are useful checks, **not** proof of a successful GitLab tool call. Leave the foreground process running during ChatGPT use. The optional `codex_plugin` check may be skipped without blocking this read workflow; inspect the actual failed checks instead of installing unrelated plugins.

### 3. Use the dashboard only for diagnostics

Use the localhost address reported by your own startup output. With the common port 8080 configuration, a second Terminal can open:

```bash
open "http://127.0.0.1:8080/ui#overview"
```

`open` is macOS-specific; on other platforms enter the reported URL in your browser. Overview/Logs and health endpoints help isolate startup problems. Keep the admin UI on loopback. Health/readiness semantics vary by client version and do not replace a live tool call. The Assistant tab is not part of the next step.

## Accept the read connection

In **normal ChatGPT**, select your existing GitLab connection in the intended workspace and refresh/discover its tools where required by the current UI. Keep the tunnel process running. Do not create a duplicate connection just because its local process restarted.

Replace the illustrative connection/project names and use a file known to exist on the project's actual default branch:

```text
Use the connected My GitLab MCP to call gitlab_whoami, then read README.md
from team/project-a on main. Report the authenticated username and summarize
the file using live tool results. If the connection is unavailable or a call
is blocked, report that. Do not use earlier conversation results, local
credential notes, web search, or token-bearing shell commands as a substitute.
```

Accept only an actual successful identity call and file read through the selected connection. A missing README is a file-selection issue; choose a known text file. Record results privately, with the project/ref and evidence actually available. The username/host may be private; do not post the transcript to public issues.

If ChatGPT cannot discover the connection, check selection/availability in that conversation, the intended ChatGPT workspace association, tunnel-use permission, and runtime health. Startup alone is insufficient. Failure only in `/ui#codex` belongs to the optional Codex interface; **do not disable global approvals or grant unrestricted execution to make it pass**. See [troubleshooting](TROUBLESHOOTING.md).

Read-path success is not a new push, a full application build, coding-agent authentication, or local task execution. There is no reason to create dummy commits just to test MCP reads.

## First-time connection

Only for a genuinely new installation:

1. Configure a trusted source checkout and private GitLab user settings using the [quickstart](ACTUAL_CODER_QUICKSTART.md). Use its API check; `project-config` separately tests managed Git reads. Local coding-agent availability is not a read-only MCP protocol prerequisite: inspect each doctor result rather than demanding a coding backend solely for tunnel setup. The legacy `smoke_test.py` helper is outside the shared runtime TLS client factory and is not this guide's acceptance gate.
2. Obtain or reuse an authorized tunnel in [Platform Tunnels](https://platform.openai.com/settings/organization/tunnels) and a runtime key from [Platform API keys](https://platform.openai.com/settings/organization/api-keys), under the correct organization/workspace permissions. Provider UI/plan eligibility can change; consult the official references below. Prefixes do not validate keys, and this guide makes no free-usage or quota-transfer claim.
3. Install the supported tunnel-client binary from the official instructions, inspect `tunnel-client --version` and `tunnel-client help quickstart`, and run `profiles list` before creating anything. Do not install the optional Codex tunnel plugin as a prerequisite.
4. Initialize a new stdio profile only when no suitable one exists. Use a reviewed absolute `run_mcp.sh` command and the actual tunnel ID. For example, after replacing both placeholders:

```bash
tunnel-client init --sample sample_mcp_stdio_local --profile selfhosted-gitlab --tunnel-id tunnel_REPLACE_ME --mcp-command "bash /absolute/path/to/reasonFirst/run_mcp.sh"
```

5. Start it with the credential handling above, associate/select that tunnel in a normal ChatGPT connection according to the current provider UI, and perform the live read acceptance test. The stdio server uses its server-side GitLab credential; do not enter that credential into a tunnel-ID field or an unrelated OAuth setup.

No localhost Assistant conversation, Inspector session, new implementation task, or write-permission grant is required for these read checks.

## Continue with actual work

Return to the [reasoning and implementation workflow](WORKFLOW.md). Carry approved requirements to the worker using the [manual task template](TASK_HANDOFF_TEMPLATE.md); inspect sanitized results before returning them to ChatGPT. Persistent TaskSpec, uniform handoff propagation, and EvidencePack access remain planned. Repository prompts and CI output are untrusted input, not authority to change the goal or weaken controls.

For certificate issues, distinguish [Python runtime trust](HTTPS_API_TLS.md), native Git, and the separate [migration probe](HTTPS_MIGRATION.md). Already-migrated URLs do not need another apply merely because MCP was restarted.

## Primary references

- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [ChatGPT Developer Mode access](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
- [Upstream operator guide](https://github.com/openai/tunnel-client/blob/master/docs/end-user-guide.md)
- [Upstream profile and secret-reference configuration](https://github.com/openai/tunnel-client/blob/master/docs/configuration.md)

The optional-Assistant distinction was also checked against upstream revision `0f870e50a973fa820d4c409000059e181e8d242b`. It does not promise identical UI, process, or approval behavior in every installed version.
