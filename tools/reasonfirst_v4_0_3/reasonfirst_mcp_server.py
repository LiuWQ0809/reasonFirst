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
        expected = token_path.read_text(encoding="ascii").strip()
        provided = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(expected, provided):
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
            if not isinstance(body, dict) or not isinstance(body.get("command"), dict):
                return JSONResponse({"ok": False, "error": "invalid command"}, status_code=400)
            result = await asyncio.to_thread(dispatch, ctrl, body["command"],
                                             control_repo=str(body.get("control_repo") or ""))
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": redact(str(exc), 2000)}, status_code=400)
    @server.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(_request):
        from starlette.responses import JSONResponse
        return JSONResponse({"ok": True, "service": "reasonfirst", "version": "4.0.3"})
    read = ToolAnnotations(read_only_hint=True, idempotent_hint=True)
    write = ToolAnnotations(read_only_hint=False, idempotent_hint=False)

    @server.tool(name="reasonfirst_doctor", annotations=read)
    def reasonfirst_doctor() -> dict[str, Any]:
        """Check ReasonFirst, GitLab Git-only auth, Codex availability, and configured execution targets."""
        return ctrl.doctor()

    @server.tool(name="reasonfirst_target_probe", annotations=read)
    def reasonfirst_target_probe(execution: dict[str, Any] | str | None = None) -> dict[str, Any]:
        """Probe a local/SSH execution target without modifying source code."""
        return ctrl.target_probe(execution)

    @server.tool(name="reasonfirst_dispatch", annotations=write)
    def reasonfirst_dispatch(
        gitlab_url: str,
        module: str,
        request: str,
        intent: str = "analyze-optimize",
        base_ref: str = "main",
        execution: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        """Prepare an isolated real-code workspace for ChatGPT analysis. Does not start Codex."""
        return ctrl.dispatch_request(
            gitlab_url=gitlab_url,
            module=module,
            request=request,
            intent=intent,
            base_ref=base_ref,
            execution=execution,
        )

    @server.tool(name="reasonfirst_workspace_status", annotations=read)
