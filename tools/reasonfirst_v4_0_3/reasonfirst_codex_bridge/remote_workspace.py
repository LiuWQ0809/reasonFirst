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

    @staticmethod
    def _safe_origin_url(origin_url: str) -> str:
        parsed = urlparse(origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return origin_url
        host = parsed.hostname
        if parsed.port is not None:
            host += f":{parsed.port}"
        return parsed._replace(netloc=host).geturl()

    def _can_forward_git_credential(self, origin_url: str) -> bool:
        if not (self.git_username and self.git_password and self.gitlab_host):
            return False
        parsed = urlparse(origin_url)
        return (
            parsed.scheme in {"http", "https"}
            and (parsed.hostname or "").lower() == self.gitlab_host
        )

    def _git_fetch_script(self, *, base: str, with_forwarded_credential: bool) -> str:
        qrepo = shlex.quote(self.target.repo)
        qbase = shlex.quote(base)
        lines = [
            "set -eu",
            f"repo={qrepo}",
            'git -C "$repo" rev-parse --is-inside-work-tree >/dev/null',
            "export GIT_TERMINAL_PROMPT=0",
        ]
        if with_forwarded_credential:
            lines += [
                'rf_auth_dir=$(mktemp -d "${TMPDIR:-/tmp}/reasonfirst-git.XXXXXX")',
                'trap \'rm -rf "$rf_auth_dir"\' EXIT HUP INT TERM',
                'cat >"$rf_auth_dir/askpass" <<\'RF_ASKPASS\'',
                '#!/bin/sh',
                'case "$1" in',
                '  *sername*|*SERNAME*) printf \'%s\\n\' "$RF_GIT_USERNAME" ;;',
                '  *) printf \'%s\\n\' "$RF_GIT_PASSWORD" ;;',
                'esac',
                'RF_ASKPASS',
                'chmod 700 "$rf_auth_dir/askpass"',
                f"export RF_GIT_USERNAME={shlex.quote(self.git_username)}",
                f"export RF_GIT_PASSWORD={shlex.quote(self.git_password)}",
                'export GIT_ASKPASS="$rf_auth_dir/askpass"',
            ]
        lines.append(f'git -C "$repo" fetch --prune origin {qbase}')
        return "\n".join(lines) + "\n"

    def create_workspace(self, *, project: str, base_ref: str, task: str) -> dict[str, Any]:
        repo = self.target.repo
        base = str(base_ref or "main").strip()
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", base) or base.startswith("-") or ".." in base.split("/"):
            raise RemoteWorkspaceError(f"Unsafe base ref: {base!r}")

        origin = self._origin_url()
        safe_origin = self._safe_origin_url(origin)
        fetch = self._ssh(
            self._git_fetch_script(base=base, with_forwarded_credential=False),
            timeout=180,
            check=False,
        )
        auth_forwarded = False
        if fetch.returncode != 0 and self._can_forward_git_credential(origin):
            fetch = self._ssh(
                self._git_fetch_script(base=base, with_forwarded_credential=True),
                timeout=180,
                check=False,
            )
            auth_forwarded = True
        if fetch.returncode != 0:
            raise RemoteWorkspaceError(
                "Remote Git fetch failed. SSH login and GitLab repository authentication are separate. "
                f"git stderr: {fetch.stderr[-2500:]}"
            )

        workspace_id = "ssh-" + uuid.uuid4().hex[:12]
        branch = f"chatgpt/{_slug(task)}-{workspace_id[-6:]}"
        qrepo = shlex.quote(repo)
        qbranch = shlex.quote(branch)
        qremote_base = shlex.quote("origin/" + base)
        qorigin = shlex.quote(safe_origin)
        cmd = f"""
set -eu
repo={qrepo}
base_sha=$(git -C "$repo" rev-parse --verify {qremote_base})
root="$HOME/.local/share/reasonfirst/worktrees"
mkdir -p "$root"
wt="$root/{workspace_id}"
if [ -e "$wt" ]; then echo 'worktree already exists' >&2; exit 9; fi
git -C "$repo" worktree add -b {qbranch} "$wt" "$base_sha" >/dev/null
printf '{{"workspace_id":"%s","worktree_path":"%s","base_sha":"%s","branch":"%s","origin_url":"%s"}}\n' \\
  {shlex.quote(workspace_id)} "$wt" "$base_sha" {qbranch} {qorigin}
"""
        proc = self._ssh(cmd, timeout=120)
        line = proc.stdout.strip().splitlines()[-1]
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RemoteWorkspaceError(f"Remote workspace creation returned invalid JSON: {line!r}") from exc
        data.update({
