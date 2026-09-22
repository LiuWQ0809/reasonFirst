from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import github_control_relay as relay


class FakeCtrl:
    def dispatch_request(self, **kwargs):
        return {"ok": True, "auto_routed": True, **kwargs}

    def artifact_descriptor(self, **kwargs):
        return {
            "workspace_id": "abc123def456",
            "absolute_path": str(self.file),
            "path": "reports/curve.png",
            "name": "curve.png",
            "extension": ".png",
            "size": self.file.stat().st_size,
            "mime_type": "image/png",
        }



def test_gh_retry_behavior():
    class Proc:
        def __init__(self, code, stdout="", stderr=""):
            self.returncode = code
            self.stdout = stdout
            self.stderr = stderr

    original_run = relay.subprocess.run
    original_sleep = relay.time.sleep
    calls = []
    sleeps = []

    def transient_then_ok(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            return Proc(1, stderr='Get "https://api.github.com/...": EOF')
        return Proc(0, stdout='{"ok": true}')

    relay.subprocess.run = transient_then_ok
    relay.time.sleep = lambda seconds: sleeps.append(seconds)
    try:
        result = relay.gh_json(["repos/example/private"], max_attempts=3)
