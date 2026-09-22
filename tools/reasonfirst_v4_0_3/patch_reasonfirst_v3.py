#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


def patch_cli(path: Path) -> bool:
    s = path.read_text(encoding="utf-8")
    if "def _git_only_preflight(" in s and s.count('"--git-only"') >= 2:
        return False

    marker = "\ndef _build_parser(prog: str = \"gitlab-agent\") -> argparse.ArgumentParser:\n"
    helper = r'''

def _git_only_preflight(result: dict[str, object]) -> dict[str, object]:
    """Treat missing GitLab API token as non-blocking for explicit Git-only flows.

    Git-only still requires every other doctor check to pass, including the Git
    HTTPS credential, workspace permissions, disk state, and coding backend.
    """
    checks = result.get("checks")
    if not isinstance(checks, list):
        return result
    blocking = [
        item for item in checks
        if isinstance(item, dict)
        and item.get("status") == "fail"
        and item.get("name") != "gitlab_api_token"
    ]
    api_missing = any(
        isinstance(item, dict)
        and item.get("name") == "gitlab_api_token"
        and item.get("status") == "fail"
        for item in checks
    )
    if blocking or not api_missing:
        return result

    out = dict(result)
    rewritten: list[dict[str, object]] = []
    for item in checks:
        if not isinstance(item, dict):
            continue
        copy = dict(item)
        if copy.get("name") == "gitlab_api_token" and copy.get("status") == "fail":
            copy["status"] = "skip"
            copy["message"] = (
                "GITLAB_TOKEN is intentionally absent in Git-only mode; "
                "GitLab REST API/MCP/CI features are unavailable"
