"""Installed entry points and bilingual operational guide invariants."""
import os
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TunnelHelperTests(unittest.TestCase):
    def test_installed_console_and_source_helper_help(self):
        suffix = ".exe" if os.name == "nt" else ""
        command = Path(sysconfig.get_path("scripts")) / ("actual-coder-tunnel" + suffix)
        self.assertTrue(command.is_file(), "Run with the complete project installed, as in CI")
        for argv in ([str(command), "--help"], [sys.executable, str(ROOT / "scripts/tunnel.py"), "--help"]):
            with self.subTest(argv=argv):
                result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                for action in ("configure", "start", "status", "stop", "restart"):
                    self.assertIn(action, result.stdout)

    def test_bilingual_commands_and_evidence_limits(self):
        english = (ROOT / "docs/TUNNEL_LIFECYCLE.md").read_text(encoding="utf-8")
        chinese = (ROOT / "docs/TUNNEL_LIFECYCLE_CN.md").read_text(encoding="utf-8")
        commands = re.findall(r"```bash\n(.*?)\n```", english, re.S)
        self.assertEqual(len(commands), 7)
        self.assertEqual(commands, re.findall(r"```bash\n(.*?)\n```", chinese, re.S))
        for text in (english, chinese):
            for marker in ("platform_unsupported", "ready_for_chatgpt_check", "chatgpt_connection_verified: false",
                           "project_access_checked: false", "unmanaged_listener", "check_project_access",
                           "GITLAB_ALLOWED_PROJECTS", "SIGTERM", "SIGKILL"):
                self.assertIn(marker, text)
        for name, target in (("README.md", "TUNNEL_LIFECYCLE.md"), ("README_CN.md", "TUNNEL_LIFECYCLE_CN.md")):
            self.assertIn(target, (ROOT / "docs" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
