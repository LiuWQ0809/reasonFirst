from __future__ import annotations

import asyncio
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gitlab_agent.gitlab_api import GitLabAPI
from gitlab_agent.log_evidence import TraceReadError
from tls_fixtures import LocalAuthority


class RuntimeTLSIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.authority = LocalAuthority(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def api(self, url, *, ca=True, verify=True):
        return GitLabAPI(SimpleNamespace(
            gitlab_base_url=url, api_token="dummy-session", api_verify_ssl=verify,
            api_trust_env=False, api_ca_bundle=self.authority.ca_path if ca else None,
        ))

    def server(self, url):
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("MCP integration requires the installed project dependencies")
        path = Path(__file__).resolve().parents[1] / "server.py"
        spec = importlib.util.spec_from_file_location("reasonfirst_runtime_tls_test_server", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {
            "GITLAB_BASE_URL": url, "GITLAB_TOKEN": "dummy-session",
            "GITLAB_VERIFY_SSL": "true", "GITLAB_TRUST_ENV": "false",
            "GITLAB_CA_BUNDLE": str(self.authority.ca_path),
            "GITLAB_ALLOWED_PROJECTS": "team/project",
            "GITLAB_AGENT_ENV_FILE": str(self.root / "absent.env"),
        }, clear=True):
            spec.loader.exec_module(module)
        return module

    def test_sync_api_json_and_text_use_private_ca(self):
        with self.authority.serve() as (url, seen):
            api = self.api(url)
            self.assertEqual(api.get_json("/user")["username"], "loopback-test")
            self.assertIn("loopback-test", api.get_text("/user"))
            self.assertEqual(len(seen), 2)
            self.assertTrue(all(item["token"] == "dummy-session" for item in seen))

    def test_sync_trace_uses_same_private_ca(self):
        with self.authority.serve() as (url, seen):
            result = self.api(url).job_trace_tail("team/project", 1, tail_bytes=1000)
            self.assertEqual(result["content"], "build completed\n")
            self.assertTrue(result["read_complete"])
            self.assertTrue(result["sanitized"])
            self.assertEqual(len(seen), 1)

    def test_sync_api_rejects_untrusted_ca(self):
        with self.authority.serve() as (url, seen):
            with self.assertRaises(RuntimeError):
                self.api(url, ca=False).get_json("/user")
            self.assertEqual(seen, [])

    def test_sync_api_rejects_verification_disable_before_network(self):
        with self.authority.serve() as (url, seen):
            with self.assertRaisesRegex(ValueError, "cannot be disabled"):
                self.api(url, verify=False).get_json("/user")
            self.assertEqual(seen, [])

    def test_sync_api_redirect_does_not_forward_token(self):
        with self.authority.serve() as (target, target_seen):
            with self.authority.serve(redirect=target + "/api/v4/user") as (url, seen):
                with self.assertRaisesRegex(RuntimeError, "redirect refused"):
                    self.api(url).get_json("/user")
                self.assertEqual(len(seen), 1)
                self.assertEqual(target_seen, [])

    def test_sync_trace_redirect_returns_no_partial_evidence(self):
        with self.authority.serve(redirect="http://127.0.0.1:1/api/v4/user") as (url, seen):
            with self.assertRaisesRegex(TraceReadError, "no log evidence returned"):
                self.api(url).job_trace_tail("team/project", 1, tail_bytes=1000)
            self.assertEqual(len(seen), 1)

    def test_mcp_json_and_text_use_private_ca(self):
        with self.authority.serve() as (url, seen):
            module = self.server(url)
            self.assertEqual(asyncio.run(module.gitlab.request_json("GET", "/user"))["id"], 1)
            self.assertIn("loopback-test", asyncio.run(module.gitlab.request_text("GET", "/user")))
            self.assertEqual(len(seen), 2)

    def test_mcp_log_tool_uses_same_private_ca(self):
        with self.authority.serve() as (url, seen):
            module = self.server(url)
            result = asyncio.run(module.get_job_log("team/project", 1, tail_bytes=1000))
            self.assertEqual(result["content"], "build completed\n")
            self.assertTrue(result["read_complete"])
            self.assertEqual(seen[0]["token"], "dummy-session")

    def test_mcp_api_redirect_does_not_forward_token(self):
        with self.authority.serve() as (target, target_seen):
            with self.authority.serve(redirect=target + "/api/v4/user") as (url, seen):
                module = self.server(url)
                with self.assertRaisesRegex(RuntimeError, "redirect refused"):
                    asyncio.run(module.gitlab.request_json("GET", "/user"))
                self.assertEqual(len(seen), 1)
                self.assertEqual(target_seen, [])

    def test_mcp_api_untrusted_certificate_is_not_bypassed(self):
        with self.authority.serve() as (url, seen):
            module = self.server(url)
            module.gitlab.ca_bundle = None
            with self.assertRaises(RuntimeError):
                asyncio.run(module.gitlab.request_json("GET", "/user"))
            self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
