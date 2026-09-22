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
        thread_id=str(command.get("thread_id") or ""),
        path=str(command["path"]),
        max_bytes=int(command.get("max_bytes") or 8 * 1024 * 1024),
    )
    if descriptor.get("remote"):
        payload = str(descriptor.pop("base64"))
        safe_name = Path(str(descriptor.get("path") or "artifact.bin")).name.replace("/", "_")
    else:
        source = Path(str(descriptor.pop("absolute_path")))
        raw = source.read_bytes()
        payload = base64.b64encode(raw).decode("ascii")
        safe_name = source.name.replace("/", "_")
    stamp = int(time.time())
    dest = f"artifacts/{descriptor['workspace_id']}/{stamp}-{safe_name}"
    data = gh_json(
        [f"repos/{repo}/contents/{quote(dest, safe='/')}", "--method", "PUT"],
        input_obj={
            "message": f"artifact: {descriptor['workspace_id']} {safe_name}",
            "content": payload,
        },
    )
    content = data.get("content") if isinstance(data, dict) and isinstance(data.get("content"), dict) else {}
    return {
        "ok": True,
        "artifact": descriptor,
        "published": {
            "repository": repo,
            "path": dest,
            "sha": content.get("sha"),
            "html_url": content.get("html_url"),
            "download_url": content.get("download_url"),
        },
        "note": "Published to the private control repository. ChatGPT can retrieve text/base64 through the GitHub connector; visual previews are also available via the artifacts op.",
    }


def dispatch(ctrl: BridgeController, command: dict[str, Any], *, control_repo: str = "") -> dict[str, Any]:
    op = command.get("op")
    if op == "doctor":
        return ctrl.doctor()
    if op == "target_probe":
        return ctrl.target_probe(command.get("execution"))
    if op == "dispatch":
        return ctrl.dispatch_request(
            gitlab_url=str(command["gitlab_url"]),
            module=str(command.get("module") or ""),
            request=str(command.get("request") or ""),
            intent=str(command.get("intent") or "analyze-optimize"),
            base_ref=str(command.get("base_ref") or ""),
            execution=command.get("execution"),
        )
    if op == "prepare":
        return ctrl.prepare(
            project=str(command["project"]),
            task=str(command.get("task") or "chatgpt-analysis"),
            goal=str(command.get("goal") or "Prepare repository for ChatGPT analysis only; do not modify files."),
            base_ref=str(command.get("base_ref") or ""),
            execution=command.get("execution"),
        )
    if op == "files":
        return ctrl.files(
            workspace_id=str(command.get("workspace_id") or ""),
            thread_id=str(command.get("thread_id") or ""),
            path=str(command.get("path") or "."),
            recursive=bool(command.get("recursive", False)),
            max_entries=int(command.get("max_entries") or 300),
        )
    if op == "read":
        return ctrl.read(
            workspace_id=str(command.get("workspace_id") or ""),
            thread_id=str(command.get("thread_id") or ""),
            path=str(command["path"]),
            start_line=int(command.get("start_line") or 1),
            end_line=int(command.get("end_line") or 0),
            max_chars=int(command.get("max_chars") or 32000),
        )
    if op == "diff":
        return ctrl.diff(
            workspace_id=str(command.get("workspace_id") or ""),
            thread_id=str(command.get("thread_id") or ""),
        )
    if op == "artifacts":
        return ctrl.artifacts(
            workspace_id=str(command.get("workspace_id") or ""),
            thread_id=str(command.get("thread_id") or ""),
            path=str(command.get("path") or "."),
            changed_only=bool(command.get("changed_only", True)),
            max_entries=int(command.get("max_entries") or 80),
            max_text_chars=int(command.get("max_text_chars") or 20000),
            max_visual_previews=int(command.get("max_visual_previews") or 2),
        )
    if op == "publish_artifact":
        if not control_repo:
            raise BridgeError("control repository is required to publish artifacts")
        return publish_artifact(control_repo, ctrl, command)
    if op == "review_bundle":
        return ctrl.review_bundle(
            thread_id=str(command["thread_id"]),
            artifact_path=str(command.get("artifact_path") or "."),
        )
