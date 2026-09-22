#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import secrets
import sys
from typing import Any

from reasonfirst_codex_bridge.controller import BridgeController, BridgeError, redact


def _doctor() -> int:
    ctrl = BridgeController()
    try:
        data = ctrl.doctor()
        data["transport"] = "mcp-http"
        data["reasonfirst_v4"] = True
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return 0 if bool(data.get("ok", True)) else 1
    finally:
        ctrl.close()


def build_server():
    # MCP Python SDK v2 (2026-07-28 protocol line).
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations

    ctrl = BridgeController()
    server = MCPServer(
        "ReasonFirst",
        instructions=(
            "ReasonFirst v4 is the local code-work orchestration server. ChatGPT is the planner/reviewer; "
            "Codex is only the implementation/build/test/push executor. Prefer dispatch -> files/read -> ChatGPT analysis -> "
            "codex_start -> review_bundle/diff -> authorize_push only after review. Never send passwords/tokens/keys as tool arguments. "
            "Execution targets are task-scoped; SSH workspaces are isolated and preserve the user's original checkout."
        ),
    )
    token_path = ctrl.state_dir / "control-token"
    if not token_path.exists():
        token_path.write_text(secrets.token_hex(32), encoding="ascii")
        token_path.chmod(0o600)

    @server.custom_route("/control", methods=["POST"], include_in_schema=False)
    async def control(request):
        from starlette.responses import JSONResponse
        from github_control_relay import dispatch
