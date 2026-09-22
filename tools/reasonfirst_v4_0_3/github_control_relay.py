#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import subprocess
import sys
import time
from typing import Any

from reasonfirst_codex_bridge.controller import BridgeController, BridgeError, redact
from reasonfirst_codex_bridge.bridge_config import load_bridge_config

PREFIX = "[reasonfirst-control]"
RESULT_PREFIX = "[reasonfirst-result]"


TRANSIENT_GH_ERROR_MARKERS = (
    " eof",
    "eof",
    "connection reset",
    "connection refused",
    "connection timed out",
    "operation timed out",
    "timeout",
    "tls handshake timeout",
    "temporary failure",
    "temporarily unavailable",
    "unexpected end of json input",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
    "http 502",
    "http 503",
    "http 504",
)


def _is_transient_gh_error(message: str) -> bool:
    lower = message.lower()
    return any(marker in lower for marker in TRANSIENT_GH_ERROR_MARKERS)


def gh_json(
    args: list[str],
    *,
    input_obj: dict[str, Any] | None = None,
    max_attempts: int | None = None,
) -> Any:
    argv = ["gh", "api", *args]
    payload = None
    if input_obj is not None:
        argv += ["--input", "-"]
        payload = json.dumps(input_obj, ensure_ascii=False)

    attempts = max(1, int(max_attempts or os.getenv("RF_GH_API_MAX_ATTEMPTS", "5")))
    timeout_seconds = max(5.0, float(os.getenv("RF_GH_API_TIMEOUT_SECONDS", "30")))
    last_error = ""

    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(
                argv,
                input=payload,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            last_error = f"gh api timed out after {timeout_seconds:g}s"
            transient = True
        else:
            if proc.returncode == 0:
                text = proc.stdout.strip()
                if not text:
                    return None
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    last_error = f"gh api returned invalid JSON: {exc}"
                    transient = True
            else:
                detail = (proc.stderr or proc.stdout or "gh api failed").strip()
                last_error = f"gh api failed: {redact(detail, 2000)}"
                transient = _is_transient_gh_error(detail)

        if not transient or attempt >= attempts:
            raise BridgeError(last_error)

        delay = min(20.0, 1.0 * (2 ** (attempt - 1)))
        print(
            f"[reasonfirst] transient GitHub API error ({attempt}/{attempts}): "
            f"{redact(last_error, 500)}; retrying in {delay:g}s",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(delay)

    raise BridgeError(last_error or "gh api failed")


def require_private_repo(repo: str) -> None:
    data = gh_json([f"repos/{repo}"])
    if not isinstance(data, dict):
        raise BridgeError("Could not inspect GitHub control repository")
    if not bool(data.get("private")) and os.getenv("RF_CONTROL_ALLOW_PUBLIC", "false").lower() not in {"1", "true", "yes", "on"}:
        raise BridgeError("Control repository must be private. Refusing to use a public issue as a command queue.")


def fetch_comments(repo: str, issue: int) -> list[dict[str, Any]]:
    data = gh_json([f"repos/{repo}/issues/{issue}/comments?per_page=100", "--paginate", "--slurp"])
    pages = data if isinstance(data, list) else []
    if pages and all(isinstance(item, dict) for item in pages):
        # Older gh builds may ignore --slurp when only one page exists.
        return [item for item in pages if isinstance(item, dict)]
    out: list[dict[str, Any]] = []
    for page in pages:
        if isinstance(page, list):
            out.extend(item for item in page if isinstance(item, dict))
    return out


def post_result(repo: str, issue: int, command_comment_id: int, result: dict[str, Any]) -> None:
    payload = {"command_comment_id": command_comment_id, **result}
    body = RESULT_PREFIX + "\n" + json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    # Never cut raw JSON/base64 in the middle. If a caller exceeds the transport
    # budget, return a valid compact response and ask ChatGPT to request smaller
    # line ranges / fewer artifacts instead.
    if len(body) > 50000:
        compact = {
            "command_comment_id": command_comment_id,
            "ok": False,
            "error": "result_exceeds_control_comment_budget",
            "message": "Result exceeded 50k characters. Request a smaller read/diff range or fewer artifacts/previews.",
            "original_chars": len(body),
        }
        body = RESULT_PREFIX + "\n" + json.dumps(compact, ensure_ascii=False, indent=2)
    gh_json([f"repos/{repo}/issues/{issue}/comments"], input_obj={"body": body})


def publish_artifact(repo: str, ctrl: BridgeController, command: dict[str, Any]) -> dict[str, Any]:
    descriptor = ctrl.artifact_descriptor(
        workspace_id=str(command.get("workspace_id") or ""),
