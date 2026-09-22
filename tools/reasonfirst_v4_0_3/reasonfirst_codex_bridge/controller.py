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
