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
                "local": {"type": "local", "codex_backend": "global-config-local"}
            },
        }
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise BridgeConfigError(f"Could not read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BridgeConfigError(f"Bridge config must be a YAML object: {path}")
    version = int(data.get("version", 3))
    if version not in {3, 4}:
        raise BridgeConfigError(f"Unsupported bridge config version in {path}")
    data["version"] = 4
    data.setdefault("control", {})  # optional legacy/audit config only
    data.setdefault("defaults", {})
    data.setdefault("targets", {})
    defaults = data["defaults"]
    if isinstance(defaults, dict):
        defaults.setdefault("target", "local")
        # Preserve an explicit v3 backend, but v4 defaults to a dedicated
        # app-server that inherits the user's global Codex config.
        defaults.setdefault("codex_backend", "global-config-local")
    targets = data["targets"]
    if isinstance(targets, dict):
        targets.setdefault("local", {"type": "local", "codex_backend": str(defaults.get("codex_backend") or "global-config-local")})
    return data


def _parse_ssh_shorthand(value: str) -> ExecutionTarget | None:
    match = re.fullmatch(r"(?P<host>[^:\s]+):(?P<repo>/[^\n\r]+)", value.strip())
    if not match:
        return None
    return ExecutionTarget(
        type="ssh",
        name=value.strip(),
        host=match.group("host"),
        repo=match.group("repo"),
        codex_backend="desktop-proxy",
    )


def resolve_target(spec: Any = None, *, config: dict[str, Any] | None = None) -> ExecutionTarget:
    cfg = config or load_bridge_config()
    defaults = cfg.get("defaults") if isinstance(cfg.get("defaults"), dict) else {}
    targets = cfg.get("targets") if isinstance(cfg.get("targets"), dict) else {}

    if spec in (None, "", {}):
        spec = str(defaults.get("target") or "local")

    if isinstance(spec, str):
