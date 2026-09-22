from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import shlex
import shutil
import subprocess
import sys
import threading
from typing import Any, Callable


class AppServerError(RuntimeError):
    pass


def resolve_codex_binary() -> str:
    explicit = os.getenv("CODEX_BRIDGE_CODEX_BIN", "").strip()
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    found = shutil.which("codex")
    if found:
        candidates.append(found)
    if sys.platform == "darwin":
        candidates.extend([
            "/Applications/ChatGPT.app/Contents/Resources/codex",
            "/Applications/Codex.app/Contents/Resources/codex",
            str(Path.home() / "Applications/ChatGPT.app/Contents/Resources/codex"),
            str(Path.home() / "Applications/Codex.app/Contents/Resources/codex"),
        ])
    for item in candidates:
        path = Path(item).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    raise AppServerError(
        "Codex executable not found. Install/login Codex or set CODEX_BRIDGE_CODEX_BIN."
    )




def resolve_desktop_or_codex_binary() -> str:
    """Honor an explicit binary, then prefer Desktop-bundled Codex over PATH.

    The launched process still reads the normal CODEX_HOME and ~/.codex/config.toml.
    """
    candidates: list[str] = []
    explicit = os.getenv("CODEX_BRIDGE_CODEX_BIN", "").strip()
    if explicit:
        candidates.append(explicit)
    if sys.platform == "darwin":
        candidates.extend([
            "/Applications/ChatGPT.app/Contents/Resources/codex",
            "/Applications/Codex.app/Contents/Resources/codex",
            str(Path.home() / "Applications/ChatGPT.app/Contents/Resources/codex"),
            str(Path.home() / "Applications/Codex.app/Contents/Resources/codex"),
        ])
    found = shutil.which("codex")
    if found:
        candidates.append(found)
    for item in candidates:
        path = Path(item).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    return resolve_codex_binary()

def managed_app_server_socket() -> Path:
    codex_home = Path(os.getenv("CODEX_HOME", "~/.codex")).expanduser().resolve()
    return codex_home / "app-server-control" / "app-server-control.sock"


class AppServerClient:
    """Synchronous Codex app-server client.

    It supports three execution topologies with one protocol surface:
    - local stdio: start `codex app-server` on this machine;
    - remote stdio: start `codex app-server` through SSH on a selected host;
    - managed Unix socket: attach to the user-private app-server socket used by
      Codex/ChatGPT Desktop when that managed daemon is available.
    """

    def __init__(
        self,
        *,
        codex_bin: str | None = None,
        launch_argv: list[str] | None = None,
        unix_socket: str | None = None,
        backend_name: str = "standalone-local",
        event_handler: Callable[[dict[str, Any]], None] | None = None,
        server_request_handler: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        request_timeout: float = 60.0,
    ) -> None:
        self.codex_bin = codex_bin or (resolve_codex_binary() if launch_argv is None and unix_socket is None else "")
        self.event_handler = event_handler
        self.server_request_handler = server_request_handler
        self.request_timeout = request_timeout
        self.backend_name = backend_name
