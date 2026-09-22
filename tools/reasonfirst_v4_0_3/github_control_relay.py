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
