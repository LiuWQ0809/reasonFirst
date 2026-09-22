#!/usr/bin/env python3
"""Migrate ReasonFirst and register the single local MCP endpoint in Codex."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil
import tempfile
import tomllib

import yaml


def strip_reasonfirst_mcp(value: str) -> str:
    out, skip = [], False
    header = re.compile(r"^\s*\[\[?([^]]+)\]\]?\s*(?:#.*)?$")
    for line in value.splitlines(keepends=True):
        if line.strip() in {"# BEGIN REASONFIRST V4 MANAGED", "# END REASONFIRST V4 MANAGED"}:
            continue
        match = header.match(line)
        if match:
            name = match.group(1).strip()
            skip = name == "mcp_servers.reasonfirst" or name.startswith("mcp_servers.reasonfirst.")
        if not skip:
            out.append(line)
    return "".join(out).rstrip() + ("\n" if out else "")


def backup(path: Path, directory: Path) -> None:
    if path.exists():
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(path, directory / f"{path.name}.{stamp}.bak")


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as f:
        tmp = Path(f.name)
        f.write(value)
        f.flush()
    try:
        tmp.chmod(0o600)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

