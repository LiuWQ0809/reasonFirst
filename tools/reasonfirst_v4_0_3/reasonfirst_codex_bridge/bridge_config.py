from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from pathlib import Path
import re
from typing import Any

import yaml


class BridgeConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutionTarget:
    type: str = "local"
    name: str = "local"
    host: str = ""
    repo: str = ""
    codex_backend: str = "global-config-local"
    remote_codex: str = "codex"
    ssh_connect_timeout: int = 8
    network_access: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def config_path() -> Path:
    return Path(os.getenv("RF_BRIDGE_CONFIG", "~/.config/reasonfirst/bridge.yaml")).expanduser().resolve()


def load_bridge_config() -> dict[str, Any]:
    """Load v4 config while remaining compatible with v3 state/config.

    v4 no longer requires the GitHub control section. Existing v3 config is
    accepted and migrated in memory so upgrades do not break active workspaces.
    """
    path = config_path()
    if not path.exists():
        return {
            "version": 4,
            "control": {},
            "defaults": {
                "target": "local",
                "codex_backend": "global-config-local",
            },
            "targets": {
