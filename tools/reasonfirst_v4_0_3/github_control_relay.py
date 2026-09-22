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
