from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
from urllib.parse import unquote, urlparse

from .app_server import AppServerClient, AppServerError, managed_app_server_socket, resolve_codex_binary
from .artifacts import artifact_file, scan_artifacts
from .bridge_config import ExecutionTarget, config_path, load_bridge_config, resolve_target
from .remote_workspace import RemoteWorkspaceManager


class BridgeError(RuntimeError):
    pass


SECRET_PATTERNS = [
    (re.compile(r"glpat-[A-Za-z0-9_-]{12,}"), "glpat-[REDACTED]"),
    (re.compile(r"(?i)(PRIVATE-TOKEN\s*[:=]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)((?:GITLAB_TOKEN|GITLAB_GIT_TOKEN|GITLAB_GIT_PASSWORD|CONTROL_PLANE_API_KEY)\s*=\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"sk-[A-Za-z0-9_-]{16,}"), "sk-[REDACTED]"),
]


def redact(text: str, limit: int = 4000) -> str:
    out = text
    for pattern, replacement in SECRET_PATTERNS:
        out = pattern.sub(replacement, out)
    return out[:limit]


def _private_state_dir() -> Path:
    raw = os.getenv("RF_CODEX_BRIDGE_STATE_DIR", "~/.local/share/reasonfirst/codex-web-bridge")
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise BridgeError(f"State path is not a directory: {path}")
    return path


def _module_command(module: str, *args: str) -> list[str]:
    return [sys.executable, "-m", module, *args]


def _run_json(argv: list[str], *, timeout: int = 360, allow_failure_json: bool = False) -> dict[str, Any]:
    try:
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False, env=os.environ.copy())
    except subprocess.TimeoutExpired as exc:
        raise BridgeError(f"Command timed out: {argv[0]} ...") from exc
    except OSError as exc:
        raise BridgeError(f"Could not launch command: {argv[0]}") from exc
    stdout = proc.stdout.strip()
    try:
        data = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        raise BridgeError(f"Expected JSON from command, got invalid output. stderr={redact(proc.stderr)}") from exc
    if proc.returncode != 0 and not allow_failure_json:
        detail = data if data else redact(proc.stderr)
        raise BridgeError(f"Command failed with exit {proc.returncode}: {detail}")
    if not isinstance(data, dict):
        raise BridgeError("Expected a JSON object from ReasonFirst command")
    data.setdefault("_returncode", proc.returncode)
    return data


class BridgeController:
    def __init__(self) -> None:
        self.state_dir = _private_state_dir()
        self.state_file = self.state_dir / "state.json"
        self._lock = threading.RLock()
        self._state = self._load_state()
        self.bridge_config = load_bridge_config()
        self._apps: dict[str, AppServerClient] = {}
        self._app_current_thread: dict[str, str] = {}

    def _load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {"version": 3, "sessions": {}, "workspaces": {}, "finish_approvals": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BridgeError(f"Could not read bridge state: {self.state_file}") from exc
        if not isinstance(data, dict) or int(data.get("version", 0)) not in {2, 3, 4}:
            raise BridgeError("Unsupported bridge state version")
        if int(data.get("version", 0)) == 2:
            data["version"] = 3
            for ws in data.get("workspaces", {}).values():
                if isinstance(ws, dict):
                    ws.setdefault("kind", "local")
                    ws.setdefault("target", {"type": "local", "name": "local", "codex_backend": "desktop-preferred"})
            for session in data.get("sessions", {}).values():
                if isinstance(session, dict):
                    session.setdefault("target", {"type": "local", "name": "local", "codex_backend": "desktop-preferred"})
        data["version"] = 3
        data.setdefault("sessions", {})
        data.setdefault("workspaces", {})
        data.setdefault("finish_approvals", {})
        return data

    def _save_state(self) -> None:
        payload = json.dumps(self._state, ensure_ascii=False, indent=2, sort_keys=True)
        fd, temp_name = tempfile.mkstemp(prefix="state.", suffix=".tmp", dir=self.state_dir)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload); f.flush(); os.fsync(f.fileno())
            os.replace(temp_name, self.state_file)
            try: self.state_file.chmod(0o600)
            except OSError: pass
        finally:
            if os.path.exists(temp_name): os.unlink(temp_name)

    def _session(self, thread_id: str) -> dict[str, Any]:
        session = self._state["sessions"].get(thread_id)
        if not isinstance(session, dict):
            raise BridgeError(f"Unknown thread_id: {thread_id}")
        return session

    def _workspace_record(self, wid: str) -> dict[str, Any]:
        item = self._state.get("workspaces", {}).get(wid)
        if not isinstance(item, dict):
            raise BridgeError(f"Unknown bridge workspace_id: {wid}")
        return item

    def _target_from_dict(self, data: Any) -> ExecutionTarget:
        return resolve_target(data, config=self.bridge_config)

    def _remote_manager(self, target: ExecutionTarget) -> RemoteWorkspaceManager:
        # Reuse the already-configured ReasonFirst Git credential for remote HTTPS
        # fetches without persisting it on the target. The remote manager forwards
        # it only after a credential-less fetch fails and only to the configured
        # GitLab host.
        try:
            from gitlab_agent.config import AgentSettings
            settings = AgentSettings.load()
            host = (urlparse(settings.gitlab_base_url).hostname or "").lower()
            return RemoteWorkspaceManager(
                target,
                gitlab_host=host,
                git_username=settings.git_username,
                git_password=settings.git_token,
            )
        except Exception:
            return RemoteWorkspaceManager(target)

    def _is_remote_proxy_target(self, target: ExecutionTarget) -> bool:
        return target.type == "ssh" and target.codex_backend != "remote-ssh"

    @staticmethod
    def _probe_remote_codex_path(probe: dict[str, Any]) -> str:
        stdout = str(probe.get("stdout") or "")
        for line in stdout.splitlines():
            if line.startswith("codex="):
                return line.split("=", 1)[1].strip()
        return ""

    def _migrate_legacy_remote_target_if_needed(
        self, workspace_id: str, rec: dict[str, Any], target: ExecutionTarget
    ) -> tuple[ExecutionTarget, bool]:
        """Reuse v3.0.2 SSH workspaces when the remote host has no Codex.

        v3.0.2 stored SSH targets as ``remote-ssh``. v3.0.3 defaults to a
        local Desktop/app-server proxy. When an existing workspace still says
        ``remote-ssh`` but the target has no Codex binary, transparently migrate
        only the execution backend; the remote worktree, branch and base SHA stay
        untouched.
        """
        if rec.get("kind") != "ssh" or target.codex_backend != "remote-ssh":
            return target, False
        probe = self._remote_manager(target).probe()
        if self._probe_remote_codex_path(probe):
            return target, False
        migrated = ExecutionTarget(
            type="ssh",
            name=target.name,
            host=target.host,
            repo=target.repo,
            codex_backend="desktop-proxy",
            remote_codex=target.remote_codex,
            ssh_connect_timeout=target.ssh_connect_timeout,
            network_access=False,
        )
        with self._lock:
            rec["target"] = migrated.to_dict()
            rec["updated_at"] = int(time.time())
            rec["execution_migration"] = {
                "from": "remote-ssh",
                "to": "desktop-proxy",
                "reason": "remote Codex binary not found",
                "at": int(time.time()),
            }
            self._state["workspaces"][workspace_id] = rec
            self._save_state()
        return migrated, True

    def _app_key(self, target: ExecutionTarget) -> str:
        if target.type == "ssh" and target.codex_backend == "remote-ssh":
            return f"ssh:{target.host}:{target.remote_codex}"
        if target.type == "ssh":
            return f"proxy:{target.codex_backend}"
        return f"local:{target.codex_backend}"

    def _get_app(self, target: ExecutionTarget) -> tuple[str, AppServerClient]:
        key = self._app_key(target)
        existing = self._apps.get(key)
        if existing is not None:
            return key, existing
        handler = lambda event, app_key=key: self._on_event(event, app_key)
        request_handler = lambda msg, app_key=key: self._handle_dynamic_tool_request(app_key, msg)
        if target.type == "ssh" and target.codex_backend == "remote-ssh":
            app = AppServerClient.remote_ssh(
                target.host,
                remote_codex=target.remote_codex,
                event_handler=handler,
                server_request_handler=request_handler,
                connect_timeout=target.ssh_connect_timeout,
            )
        elif target.codex_backend in {"global-config-local", "desktop-proxy"}:
            app = AppServerClient.global_config_local(
                event_handler=handler, server_request_handler=request_handler
            )
        elif target.codex_backend == "desktop-required":
            app = AppServerClient.desktop_preferred(
                event_handler=handler, server_request_handler=request_handler, required=True
            )
        elif target.codex_backend == "desktop-managed":
            app = AppServerClient.desktop_preferred(
                event_handler=handler, server_request_handler=request_handler, required=True
            )
        elif target.codex_backend == "standalone-local":
            app = AppServerClient(
                event_handler=handler,
                server_request_handler=request_handler,
                backend_name="standalone-local",
            )
        else:
            # v3 compatibility. Prefer v4 dedicated global-config app-server.
            app = AppServerClient.global_config_local(
                event_handler=handler, server_request_handler=request_handler
            )
        self._apps[key] = app
        return key, app

    def _proxy_workspace(self, workspace_id: str, rec: dict[str, Any]) -> str:
        root = self.state_dir / "proxy" / workspace_id
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            root.chmod(0o700)
        except OSError:
            pass
        note = root / "REMOTE_WORKSPACE.md"
        note.write_text(
            "# ReasonFirst remote workspace proxy\n\n"
            "This local directory is a control surface only. The source of truth is remote.\n\n"
            f"Project: {rec.get('project')}\n"
            f"Remote host: {(rec.get('target') or {}).get('host')}\n"
            f"Remote worktree: {rec.get('worktree_path')}\n"
            f"Branch: {rec.get('branch')}\n"
            f"Base SHA: {rec.get('base_sha')}\n\n"
            "Use the ReasonFirst remote dynamic tools for all source reads, writes, commands and diffs.\n",
            encoding="utf-8",
        )
        return str(root.resolve())

    @staticmethod
    def _remote_dynamic_tools() -> list[dict[str, Any]]:
        def fn(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
            schema: dict[str, Any] = {
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            }
            if required:
                schema["required"] = required
            return {
                "type": "function",
                "name": name,
                "description": description,
                "inputSchema": schema,
            }
        return [{
            "type": "namespace",
            "name": "reasonfirst_remote",
            "description": "Operate only on the managed remote ReasonFirst worktree selected for this task.",
            "tools": [
                fn("status", "Read the remote Git worktree status and pinned branch/base information.", {}),
                fn("files", "List files inside the remote managed worktree.", {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean"},
                    "max_entries": {"type": "integer", "minimum": 1, "maximum": 500},
                }),
                fn("read", "Read one UTF-8 source/config/test file from the remote managed worktree.", {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer", "minimum": 1, "maximum": 2097152},
                }, ["path"]),
                fn("write", "Replace one file inside the remote managed worktree. Parent directories may be created.", {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                }, ["path", "content"]),
                fn("apply_patch", "Apply a unified Git patch to the remote managed worktree.", {
                    "patch": {"type": "string"},
                }, ["patch"]),
                fn("run", "Run a build/test/inspection command on the remote host with cwd constrained to this worktree. Destructive/admin/network-hop commands are blocked.", {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1800},
                }, ["command"]),
                fn("snapshot", "Read the exact remote review snapshot digest. Use before requesting ChatGPT push approval.", {}),
                fn("commit_push", "Commit and push the exact ChatGPT-approved snapshot. This succeeds only after an explicit ReasonFirst push approval for the unchanged digest; force-push and protected branches are never allowed.", {}),
                fn("diff", "Read the real remote Git diff against the pinned base SHA.", {}),
            ],
        }]

    def _handle_dynamic_tool_request(self, app_key: str, msg: dict[str, Any]) -> dict[str, Any]:
        if str(msg.get("method") or "") != "item/tool/call":
            raise BridgeError("Unsupported dynamic server request")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        thread_id = str(params.get("threadId") or "")
        namespace = str(params.get("namespace") or "")
        tool = str(params.get("tool") or "")
        args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if namespace != "reasonfirst_remote":
            raise BridgeError(f"Unsupported dynamic tool namespace: {namespace!r}")
        session = self._session(thread_id)
        if str(session.get("app_key") or "") != app_key:
            raise BridgeError("Dynamic tool request arrived on the wrong app-server")
        rec = self._workspace_record(str(session["workspace_id"]))
        if rec.get("kind") != "ssh":
            raise BridgeError("ReasonFirst remote tools require an SSH workspace")
        target = self._target_from_dict(rec.get("target") or {})
        manager = self._remote_manager(target)
        if tool == "status":
            result = manager.status(rec)
        elif tool == "files":
