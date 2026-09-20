# Start the tunnel before the first ChatGPT prompt

[简体中文](TUNNEL_LIFECYCLE_CN.md) · [Index](README.md) · [Project access](PROJECT_ACCESS.md) · [Manual connection setup](SETUP_TUTORIAL.md)

**For the tunnel-based workflow, startup is a prerequisite every time the service is stopped—not a one-time installation step.** Keep the service running while normal ChatGPT reads GitLab. Local ActualCoder/Codex operation is separate. The localhost Assistant is not required.

`actual-coder-tunnel` manages an **existing, operator-selected** profile. It does not create a remote tunnel, grant project access, rotate a token, overwrite the tunnel YAML, or implement automatic task execution. It supervises the ordinary upstream `doctor` / `run --profile` commands, rather than adopting the upstream `runtimes connect` path that writes generated profiles.

## Supported scope

This first implementation manages macOS/Linux foreground processes using POSIX process groups, file locks and a private Unix control socket. Windows can display help, but lifecycle actions explicitly return `platform_unsupported`; continue using the existing upstream startup procedure there. This is not a launchd/systemd service, login item, background daemon installer, or unattended restart loop.

Supported profiles have `config_version: 1`, the canonical `https://api.openai.com` control plane, a runtime-key `env:NAME` or `file:/absolute/path` reference, **one main stdio command** pointing to the selected checkout's `run_mcp.sh`, and a fixed loopback health port. The usual `log.level`, `log.format` and `admin_ui.open_browser` fields are accepted. Advanced/multiple-channel/HTTP/cloudflared/MTLS profiles, additional profile fields, YAML aliases, dynamic port 0, remote UI binds and inline keys are rejected with an explanation, not silently rewritten. Such installations may keep using upstream tooling.

The upstream CLI/profile and `/api/status` layout were source-checked at tunnel-client `0.0.14+0f870e50a973fa820d4c409000059e181e8d242b`. This is an adapter compatibility baseline, not a claim to have run a real OpenAI tunnel in repository CI. An incompatible installed binary or status schema must fail closed rather than produce an invented ready result.

## 1. Install from the approved checkout

Update your normal checkout using the [source-update guide](LOCAL_PR_REVIEW.md), preserving local edits. Stop an old manually launched tunnel with Control+C in **its own Terminal** before handing lifecycle ownership to this helper. Do not run a second copy on the same port.

From the approved ReasonFirst checkout:

```bash
uv sync --python 3.12
bash scripts/install_user.sh
actual-coder-tunnel --help
```

The source helper is also available:

```bash
uv run python scripts/tunnel.py --help
```

## 2. Save non-secret startup settings once

The example profile `gitlab-work` is a placeholder for a profile that **already exists**; replace it with the name shown by `tunnel-client profiles list`. Run this from the correct source checkout, not a temporary PR worktree:

```bash
actual-coder-tunnel configure --profile gitlab-work --source-dir "$PWD" --keychain-service openai-tunnel-runtime --keychain-account "$USER"
```

This opt-in Keychain setup expects an existing generic-password item whose service is `openai-tunnel-runtime` and whose account is your macOS account name. It does not create, search broadly for, or print credentials. To save that item, use Keychain Access locally: login keychain → new password item → that item/service name and account → your existing **OpenAI runtime API key with Tunnels Read + Use**, not the tunnel ID, GitLab token, or an admin key. Do not grant all applications access; macOS may request access confirmation when the exact item is read. No key value belongs in chat or the command above.

The helper saves only paths/reference names in `~/.config/reasonfirst/tunnel.json` (0600, private parent directory). It checks the existing profile and the private GitLab configuration's metadata, not the GitLab token's contents. Defaults are `~/.config/tunnel-client` for profiles, `~/.config/gitlab-agent/.env` for the selected GitLab configuration, and `~/.local/share/reasonfirst/tunnels` for owner locks/socket. `configure --help` exposes explicit path overrides. A different existing settings file needs an intentional `configure --replace`; live owner settings cannot be replaced by configure.

Without Keychain, omit the two Keychain options. An `env:` reference then requires its value in the launching shell **on each start**; exporting it in an earlier subshell or Terminal never saved it permanently. A `file:` profile uses its existing absolute, private 0600 key file; the helper checks metadata, and upstream resolves the value. No automatic env/file/Keychain fallback chooses a different credential. With an explicitly selected Keychain source, retrieval happens every start/restart, even when the parent shell has an older exported value.

## 3. Start and keep the owner Terminal open

After one-time configuration, this works from any directory:

```bash
actual-coder-tunnel start
```

Start loads the chosen runtime key, runs upstream doctor, starts the selected profile, and waits up to 30 seconds for local readiness and matching runtime identity/metadata. **It remains in the foreground.** Keep this Terminal and the Mac/network available. Control+C stops its owned runtime. Do not add `nohup`, `disown`, or a second process manager around it without a separately reviewed service design.

Settings select a specific private GitLab file. Child processes inherit operational OS/locale/uv/proxy variables and the selected runtime-key variable, but not arbitrary tunnel/MCP/health or `GITLAB_*` overrides. The helper supplies `GITLAB_AGENT_ENV_FILE` explicitly. This avoids stale shell values replacing the reviewed profile or file; the parent shell and the file are unchanged. Put intended GitLab options in that selected file. Runtime keys still exist in the trusted process environment; Keychain storage is not OS isolation from same-user code.

Raw upstream stdout/stderr are not replayed or saved by the helper. It emits bounded, structured JSON status/errors without HTTP bodies, profile contents or credentials. The existing local Overview/Logs UI may be inspected privately for upstream detail; the helper never invokes its Assistant. A doctor failure does not export the loaded key back to the parent shell, so a later bare upstream command in a new Terminal still needs its own secure key loading.

## 4. Status, stop and restart

In a second Terminal:

```bash
actual-coder-tunnel status
```

| State/result | Meaning and action |
| --- | --- |
| `ready_for_chatgpt_check` | The helper owns a live child; `/healthz` and `/readyz` returned 200; `/api/status` matches the configured tunnel and reports fetched metadata. **Now test normal ChatGPT.** |
| `running_not_ready`, `probe_stale`, `probe_failed` | The owner exists but readiness/evidence is not established. Inspect status/UI; do not call the whole pipeline healthy. |
| `control_plane_error` | Upstream metadata state reports an error. Check the runtime key/organization/network privately. No raw error text is returned. |
| `not_running` | No owner or listener was found for the selected setup. Run start. |
| `unmanaged_listener` | The selected port is occupied, but not owned by this helper. Inspect the original Terminal; do not launch, adopt, or kill blindly. |
| `configuration_changed` | Settings/profile differ from the owner's snapshot or are no longer readable. Review and restart; a running process did not reload the file. |
| `owner_unresponsive_or_starting` | An owner lock exists, but no responsive control endpoint is available. Wait for preflight or use Control+C in the owner Terminal. No PID-based fallback is provided. |

`status` returns 0 only for verified local readiness and 1 otherwise. It never retrieves the runtime key and does not create state when stopped. It always separates `chatgpt_connection_verified: false` and `project_access_checked: false` from local readiness. A cached sample has an age; stale samples are not green. Matching metadata is not continuous polling evidence, stdio tool discovery, or authorization to any GitLab project.

Stop only the responsive helper-owned instance:

```bash
actual-coder-tunnel stop
```

Stop targets the current owner's instance-specific private control socket. The owner signals **its own child process group** with SIGTERM, waits up to five seconds, then may use SIGKILL only for that still-tracked group. It never uses `pkill`, `killall`, a saved PID, or a stale PID file. An already stopped setup is an idempotent success. An unmanaged/unresponsive process is not adopted or stopped.

Restart with fresh key loading:

```bash
actual-coder-tunnel restart
```

Restart validates the replacement's local profile/executable/key before asking the old owner to stop. It then performs doctor/network readiness checks; these later checks can fail and leave the tunnel stopped. There is no automatic rollback or credential substitution. The Terminal running restart becomes the **new foreground owner**. Normal stop/status do not need a runtime key, and an owned instance can be stopped even when its edited profile no longer parses.

Concurrent helper starts share per-profile and per-tunnel locks in the same configured state directory. A repeated start on the same healthy instance returns its status without launching another process. Port conflicts block unmanaged duplicates at the selected address. This is not global discovery of every raw tunnel process using another port, another machine, or another state directory. Do not mix manual, upstream-managed and helper-managed launchers for one tunnel.

## 5. Accept the real connection

After a source update, stop → update/sync/install → start. A settings/profile fingerprint is not a complete source-code revision check; restart after runtime-code updates even when status shows no configuration change. Refresh the existing ChatGPT connection's tool discovery when tools changed. No new tunnel is required.

In normal ChatGPT with the intended connection selected:

```text
Use the connected GitLab MCP, not localhost Assistant, web search or old results.
Call gitlab_whoami, then check_project_access for the exact project/ref I confirm.
On ok=false, report the failing layer and needed user action, then stop and wait.
On success, read the required source files at resolved_commit_sha and report only
the revision identifiers actually returned. Do not create projects or grant access.
```

A real successful identity/preflight/file read is the final acceptance evidence. Continue the [practice lab](PRACTICE_LAB.md) only after its dedicated project exists, is seeded, and is explicitly granted in `GITLAB_ALLOWED_PROJECTS`. Local readiness never replaces those steps. The localhost Assistant is not a prerequisite or acceptance gate.

## Limits and recovery

`runtime_key_missing`, `keychain_unavailable`, `launcher_mismatch`, `doctor_failed`, and `startup_timeout` are distinct failures. Startup timeout stops only the new owned runtime; no background orphan is deliberately left running. A force-killed supervisor, kernel failure, or upstream crash may still leave descendants; the helper intentionally refuses unsafe stale-PID recovery. Inspect locally and stop the actual known process through its owning service/Terminal. The locks/socket contain no key values; do not delete live lock files to bypass ownership.

No boot auto-start, distributed ownership, Windows process control, blanket permission bypass, TLS downgrade, new authorization UI, or automatic project grant is implemented. Tests use real helper subprocesses and loopback HTTP with a synthetic tunnel executable, not the OpenAI control plane or the user's Mac Keychain. Follow [security boundaries](../SECURITY.md).

Primary sources: [OpenAI tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels), [upstream run](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/cmd/client/run_command.go), [managed runtime profile generation](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/cmd/client/runtimes_command.go), [admin status fields](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/pkg/adminui/fxmodule.go), [configuration precedence](https://github.com/openai/tunnel-client/blob/0f870e50a973fa820d4c409000059e181e8d242b/pkg/runtimeconfig/config.go).
