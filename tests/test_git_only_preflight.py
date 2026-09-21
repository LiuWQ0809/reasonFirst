from __future__ import annotations

import unittest

from gitlab_agent.cli import _build_parser, _git_only_preflight


class GitOnlyPreflightTests(unittest.TestCase):
    def test_missing_api_token_is_non_blocking_in_git_only_mode(self) -> None:
        result = {
            "ok": False,
            "overall": "fail",
            "offline": True,
            "summary": {"pass": 2, "skip": 1, "warn": 0, "fail": 1},
            "checks": [
                {"name": "gitlab_url", "status": "pass", "message": "HTTPS"},
                {
                    "name": "gitlab_api_token",
                    "status": "fail",
                    "message": "GITLAB_TOKEN is missing",
                },
                {
                    "name": "git_credential",
                    "status": "pass",
                    "message": "A Git credential is configured",
                },
                {
                    "name": "gitlab_api_connectivity",
                    "status": "skip",
                    "message": "offline",
                },
            ],
        }

        rewritten = _git_only_preflight(result)

        self.assertTrue(rewritten["ok"])
        self.assertTrue(rewritten["git_only"])
        checks = {item["name"]: item for item in rewritten["checks"]}
        self.assertEqual(checks["gitlab_api_token"]["status"], "skip")
        self.assertEqual(rewritten["summary"]["fail"], 0)

    def test_git_only_does_not_hide_other_failures(self) -> None:
        result = {
            "ok": False,
            "overall": "fail",
            "offline": True,
            "summary": {"pass": 0, "skip": 0, "warn": 0, "fail": 2},
            "checks": [
                {
                    "name": "gitlab_api_token",
                    "status": "fail",
                    "message": "missing",
                },
                {
                    "name": "git_credential",
                    "status": "fail",
                    "message": "missing",
                },
            ],
        }

        rewritten = _git_only_preflight(result)

        self.assertFalse(rewritten["ok"])
        self.assertEqual(rewritten["summary"]["fail"], 2)

    def test_cli_accepts_git_only_for_doctor_and_start(self) -> None:
        parser = _build_parser(prog="actual-coder")
        doctor = parser.parse_args(["doctor", "--offline", "--git-only"])
        self.assertTrue(doctor.git_only)

        start = parser.parse_args(
            [
                "start",
                "team/project",
                "--goal",
                "test",
                "--no-launch",
                "--offline-doctor",
                "--git-only",
            ]
        )
        self.assertTrue(start.git_only)


if __name__ == "__main__":
    unittest.main()
