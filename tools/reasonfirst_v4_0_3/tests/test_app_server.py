from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reasonfirst_codex_bridge.app_server import AppServerClient


def test_callback_failure_does_not_kill_reader():
    fake = str(ROOT / "tests" / "fake_codex.py")
    seen = {"raised": False}
    def flaky(event):
        if not seen["raised"]:
            seen["raised"] = True
            raise RuntimeError("synthetic callback failure")
    client = AppServerClient(codex_bin=fake, event_handler=flaky)
    tid = client.start_thread(cwd=str(ROOT))
    assert tid == "thr_fake"
    client.close()



def test_dynamic_tool_roundtrip():
    fake = str(ROOT / "tests" / "fake_codex.py")
    events = []
    seen = []
    def handle(msg):
        seen.append(msg)
        return {
            "contentItems": [{"type": "inputText", "text": '{"ok":true,"head":"abc"}'}],
            "success": True,
        }
    client = AppServerClient(
        codex_bin=fake,
        event_handler=events.append,
        server_request_handler=handle,
    )
    tools = [{
        "type": "namespace",
        "name": "reasonfirst_remote",
        "description": "remote",
        "tools": [{
            "type": "function",
            "name": "status",
            "description": "status",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        }],
    }]
    tid = client.start_thread(cwd=str(ROOT), dynamic_tools=tools, sandbox_mode="read-only")
