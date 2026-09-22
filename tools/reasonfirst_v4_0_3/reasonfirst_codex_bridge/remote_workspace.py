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

    def _ssh(self, command: str, *, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        # Send the shell script through stdin so OpenSSH cannot corrupt quoting
        # by rebuilding a remote `sh -lc <script>` command string.
        argv = [
            "ssh", "-T",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={self.target.ssh_connect_timeout}",
            "--", self.target.host,
            "sh -s",
        ]
        try:
            proc = subprocess.run(
                argv,
                input=command.rstrip("\n") + "\n",
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RemoteWorkspaceError(f"SSH command timed out on {self.target.host}") from exc
        if check and proc.returncode != 0:
            raise RemoteWorkspaceError(
                f"SSH command failed on {self.target.host} (exit {proc.returncode}): {proc.stderr[-3000:]}"
            )
        return proc

    def probe(self) -> dict[str, Any]:
        cmd = " && ".join([
            "printf 'host='; hostname",
            "printf 'user='; id -un",
            f"printf 'repo='; git -C {shlex.quote(self.target.repo)} rev-parse --show-toplevel",
            "printf 'codex='; command -v " + shlex.quote(self.target.remote_codex) + " || true",
        ])
        proc = self._ssh(cmd, timeout=30, check=False)
        return {
            "ok": proc.returncode == 0,
            "target": self.target.to_dict(),
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-3000:],
            "returncode": proc.returncode,
        }

    def _origin_url(self) -> str:
        repo = shlex.quote(self.target.repo)
        proc = self._ssh(f"git -C {repo} remote get-url origin", timeout=30)
        value = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        if not value:
            raise RemoteWorkspaceError("Remote repository has no origin URL")
        return value
