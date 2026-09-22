from __future__ import annotations

import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import shlex
import subprocess
import time
from typing import Any
from urllib.parse import urlparse
import uuid

from .bridge_config import ExecutionTarget


class RemoteWorkspaceError(RuntimeError):
    pass


def _slug(value: str, limit: int = 40) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return (text or "task")[:limit]


def _safe_relative(path: str) -> str:
    raw = str(path or ".").strip() or "."
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts:
        raise RemoteWorkspaceError(f"Path must stay inside the managed remote worktree: {path!r}")
    return str(p)


class RemoteWorkspaceManager:
    def __init__(
        self,
        target: ExecutionTarget,
        *,
        gitlab_host: str = "",
        git_username: str = "",
        git_password: str = "",
    ) -> None:
        if target.type != "ssh":
            raise RemoteWorkspaceError("RemoteWorkspaceManager requires an SSH target")
        self.target = target
        self.gitlab_host = str(gitlab_host or "").strip().lower()
        self.git_username = str(git_username or "")
        self.git_password = str(git_password or "")

