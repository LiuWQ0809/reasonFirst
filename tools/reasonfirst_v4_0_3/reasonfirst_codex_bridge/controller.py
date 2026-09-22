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
