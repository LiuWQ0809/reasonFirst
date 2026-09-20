"""Check the teaching kit, without production GitLab or a coding-model session."""
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

import yaml

from gitlab_agent.project_config import parse_project_config


KIT = Path(__file__).resolve().parents[1] / "examples" / "practice-lab"
ARGV = ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]


class PracticeLabTests(unittest.TestCase):
    def test_baseline_runs_without_dependencies(self):
        result = subprocess.run(
            [sys.executable, *ARGV[1:]], cwd=KIT, capture_output=True,
            text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Ran 5 tests", result.stderr)
        self.assertIn("OK", result.stderr)

    def test_contract_parses_with_existing_production_parser(self):
        settings = SimpleNamespace(
            default_base_ref="main", allowed_executables={"python3"},
            command_timeout_seconds=300,
        )
        contract = parse_project_config(
            (KIT / ".actualcoder.yaml").read_text(encoding="utf-8"),
            settings=settings, source_ref="main",  # type: ignore[arg-type]
        )
        self.assertTrue(contract.found)
        self.assertTrue(contract.valid, contract.errors)
        command = contract.effective["validation_commands"][0]
        self.assertEqual(command["argv"], ARGV)
        self.assertTrue(command["required"])
        self.assertEqual(command["timeout_seconds"], 120)
        self.assertIn(".gitlab-ci.yml", contract.effective["protected_paths"])
        self.assertIn("EXERCISE.md", contract.effective["protected_paths"])

    def test_ci_runs_actual_tests_for_merge_requests(self):
        ci = yaml.safe_load((KIT / ".gitlab-ci.yml").read_text(encoding="utf-8"))
        self.assertEqual(ci["stages"], ["test"])
        self.assertIn('merge_request_event', ci["workflow"]["rules"][0]["if"])
        self.assertEqual(ci["workflow"]["rules"][1]["when"], "never")
        self.assertIn("CI_OPEN_MERGE_REQUESTS", ci["workflow"]["rules"][1]["if"])
        self.assertIn(" ".join(ARGV), ci["unit-tests"]["script"])
        self.assertFalse(ci["unit-tests"].get("allow_failure", False))

    def test_seed_files_are_regular_and_documents_are_present(self):
        for name in (
            "clip_summary.py", "tests/test_clip_summary.py", "AGENTS.md",
            "EXERCISE.md", "README.md", ".actualcoder.yaml", ".gitlab-ci.yml", ".gitignore",
        ):
            with self.subTest(name=name):
                file = KIT / name
                self.assertTrue(file.is_file())
                self.assertFalse(file.is_symlink())
        for name in ("PRACTICE_LAB.md", "PRACTICE_LAB_CN.md"):
            self.assertTrue((KIT.parents[1] / "docs" / name).is_file())


if __name__ == "__main__":
    unittest.main()
