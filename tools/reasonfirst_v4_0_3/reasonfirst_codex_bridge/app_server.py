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
