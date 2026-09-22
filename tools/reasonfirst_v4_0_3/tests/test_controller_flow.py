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
        return {"goal": {"objective": objective}}

    def update_thread_metadata(self, thread_id, **kwargs):
        self.metadata = kwargs
        return {"thread": {"id": thread_id, **kwargs}}

    def list_threads(self, **kwargs):
        return {"data": [{"id": "thr_test", "name": self.name}]}

    def resume_thread(self, thread_id):
        return None

    def read_thread(self, thread_id, include_turns=False):
        return {"thread": {"id": thread_id, "name": self.name, "status": {"type": "idle"}}}

    def close(self):
        return None


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "workspace-root"
        worktree = root / "worktrees" / "abc123def456"
        (worktree / "src" / "perception").mkdir(parents=True)
        (worktree / "src" / "perception" / "a.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
        (worktree / "reports").mkdir()
        (worktree / "reports" / "metrics.json").write_text(json.dumps({"latency_ms": 12.3, "accuracy": 0.91}), encoding="utf-8")
        state = Path(tmp) / "bridge-state"
        os.environ["RF_CODEX_BRIDGE_STATE_DIR"] = str(state)

        original_app = controller.AppServerClient
        original_run = controller._run_json
        controller.AppServerClient = FakeApp

        def fake_run(argv, **kwargs):
            args = list(argv)
            if args[-1] == "config":
                return {
                    "workspace_root": str(root),
                    "api_token_set": False,
                    "git_token_set": True,
                    "gitlab_base_url": "https://gitlab.example.com",
                }
            if "project-config" in args:
                return {"project": "group/project", "found": False, "valid": True}
            if "start" in args:
                return {
                    "workspace": {"workspace_id": "abc123def456", "project": "group/project"},
                    "worktree_path": str(worktree),
                    "agent_prompt": "unused until start_codex",
