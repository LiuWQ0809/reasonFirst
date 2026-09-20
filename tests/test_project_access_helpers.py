"""Packaged helper and bilingual onboarding checks; no live credentials/network."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectAccessHelperTests(unittest.TestCase):
    def test_installed_console_and_source_helper_help(self):
        suffix = ".exe" if os.name == "nt" else ""
        command = Path(sysconfig.get_path("scripts")) / ("actual-coder-check-project" + suffix)
        self.assertTrue(command.is_file(), "Run with the project installed, as in CI")
        for argv in ([str(command), "--help"],
                     [sys.executable, str(ROOT / "scripts" / "check_project_access.py"), "--help"]):
            with self.subTest(argv=argv):
                result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--require-file", result.stdout)
                self.assertIn("--ref", result.stdout)

    def test_bilingual_guides_keep_commands_and_preflight_gate(self):
        pattern = r"```bash\n(.*?)\n```"
        for stem in ("PROJECT_ACCESS", "PRACTICE_LAB"):
            english = (ROOT / "docs" / (stem + ".md")).read_text(encoding="utf-8")
            chinese = (ROOT / "docs" / (stem + "_CN.md")).read_text(encoding="utf-8")
            self.assertEqual(re.findall(pattern, english, re.S), re.findall(pattern, chinese, re.S))
            for text in (english, chinese):
                self.assertIn("check_project_access", text)
                self.assertIn("resolved_commit_sha", text)
                self.assertIn("GITLAB_ALLOWED_PROJECTS", text)
                self.assertIn("404", text)
                self.assertIn("ok=false" if stem == "PRACTICE_LAB" else "ok: false", text)


if __name__ == "__main__":
    unittest.main()
