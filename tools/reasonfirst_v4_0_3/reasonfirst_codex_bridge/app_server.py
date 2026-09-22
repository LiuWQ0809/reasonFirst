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
        self._next_id = 1
        self._pending: dict[int, queue.Queue[dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._closed = False
        self._stderr_tail: list[str] = []
        self.proc: subprocess.Popen[str] | None = None
        self.ws: Any = None

        if unix_socket:
            self._connect_unix_socket(unix_socket)
            self._reader = threading.Thread(
                target=self._read_ws_loop,
                name="codex-app-server-ws-reader",
                daemon=True,
            )
            self._stderr_reader = None
            self._reader.start()
        else:
            argv = list(launch_argv or [self.codex_bin or resolve_codex_binary(), "app-server"])
            try:
                self.proc = subprocess.Popen(
                    argv,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
            except OSError as exc:
                raise AppServerError(f"Failed to launch Codex app-server: {argv!r}: {exc}") from exc
            if self.proc.stdin is None or self.proc.stdout is None or self.proc.stderr is None:
                raise AppServerError("Failed to open codex app-server stdio pipes")
            self._reader = threading.Thread(
                target=self._read_stdio_loop,
                name="codex-app-server-reader",
                daemon=True,
            )
            self._stderr_reader = threading.Thread(
                target=self._read_stderr,
                name="codex-app-server-stderr",
                daemon=True,
            )
            self._reader.start()
            self._stderr_reader.start()
        self._initialize()

    @classmethod
    def global_config_local(
        cls,
