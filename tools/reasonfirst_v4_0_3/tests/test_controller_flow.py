from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import reasonfirst_codex_bridge.controller as controller


class FakeApp:
    def __init__(self, event_handler=None, backend_name="standalone-local", **kwargs):
        self.backend_name = backend_name
        self.event_handler = event_handler
        self.name = ""
        self.goal = ""
        self.metadata = {}


    @classmethod
    def global_config_local(cls, *, event_handler=None, server_request_handler=None):
        return cls(event_handler=event_handler, server_request_handler=server_request_handler, backend_name="global-config-local")

    @classmethod
    def desktop_preferred(cls, *, event_handler=None, server_request_handler=None, required=False):
        return cls(event_handler=event_handler, server_request_handler=server_request_handler, backend_name="desktop-managed-test")

    @classmethod
    def remote_ssh(cls, host, *, remote_codex="codex", event_handler=None, server_request_handler=None, connect_timeout=8):
        return cls(event_handler=event_handler, server_request_handler=server_request_handler, backend_name=f"ssh:{host}")

    def admin_requirements(self):
        return {}

    def start_thread(self, *, cwd, dynamic_tools=None, sandbox_mode="workspace-write"):
        return "thr_test"

    def start_turn(self, *, thread_id, cwd, prompt, network_access=False, sandbox_mode="workspace-write"):
        assert thread_id == "thr_test"
        assert "implement reviewed plan" in prompt
        return "turn_test"

    def set_thread_name(self, thread_id, name):
        self.name = name

    def set_thread_goal(self, thread_id, objective):
        self.goal = objective
