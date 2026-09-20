from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import httpx

from gitlab_agent import project_access as access
from gitlab_agent.config import AgentSettings
from gitlab_agent.tls import api_client_options

BASE = "https://gitlab.example.invalid"
SHA = "a" * 40
PROJECT = "team/practice"


class UnreadBody(httpx.AsyncByteStream):
    def __init__(self):
        self.read = False
        self.closed = False

    async def __aiter__(self):
        self.read = True
        raise AssertionError("Do not read error/HEAD bodies")
        yield b""  # pragma: no cover

    async def aclose(self):
        self.closed = True


class ProjectAccessTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, responses, **overrides):
        self.requests = []
        def handler(req):
            self.requests.append(req)
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        def factory():
            return httpx.AsyncClient(
                transport=httpx.MockTransport(handler), trust_env=False,
                **api_client_options(BASE, asynchronous=True),
            )
        kwargs = dict(allowed={PROJECT}, token_present=True,
                      client_factory=factory, base_url=BASE, ref="main")
        kwargs.update(overrides)
        return await access.check_project_access(PROJECT, **kwargs)

    def metadata(self, **fields):
        return httpx.Response(200, json={"id": 12, "path_with_namespace": PROJECT,
                                      "default_branch": "main", **fields})

    def commit(self):
        return httpx.Response(200, json={"id": SHA})

    async def test_deny_precedes_client_and_credential_access(self):
        factory = Mock(side_effect=AssertionError("No client"))
        result = await self.probe([], allowed={"other/repo"}, token_present=False,
                                  client_factory=factory)
        factory.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertFalse(result["local_allowed"])
        self.assertFalse(result["remote_checked"])
        self.assertIsNone(result["project_exists"])
        self.assertEqual(result["project"], PROJECT)
        self.assertEqual(result["error"]["code"], "project_not_allowlisted")
        self.assertIn("local MCP configuration", result["error"]["next_steps"][0])
        self.assertIn("restart", result["error"]["next_steps"][0])

    async def test_empty_read_allowlist_keeps_existing_semantics(self):
        result = await self.probe([self.metadata(), self.commit()], allowed=set())
        self.assertTrue(result["ok"])

    async def test_numeric_alias_cannot_bypass_allowlist(self):
        factory = Mock(side_effect=AssertionError("No client"))
        result = await access.check_project_access("12", allowed={PROJECT}, token_present=True,
                                                 client_factory=factory, base_url=BASE)
        self.assertEqual(result["error"]["code"], "project_not_allowlisted")
        factory.assert_not_called()

    async def test_numeric_project_explicitly_authorized(self):
        responses = [self.metadata(), self.commit()]
        factory = lambda: httpx.AsyncClient(transport=httpx.MockTransport(lambda r: responses.pop(0)))
        result = await access.check_project_access("12", allowed={"12"}, token_present=True,
                                                 client_factory=factory, base_url=BASE)
        self.assertTrue(result["ok"])
        self.assertEqual(result["project_id"], 12)

    async def test_invalid_identifiers_do_not_echo_or_connect(self):
        for project in ("/team/practice", "https://bad.invalid/a", "../a", "team/../a", "team//a", "", "0", True):
            with self.subTest(project=project):
                factory = Mock(side_effect=AssertionError("No client"))
                result = await access.check_project_access(project, allowed=set(), token_present=True,
                                                         client_factory=factory, base_url=BASE)
                self.assertEqual(result["error"]["code"], "invalid_project")
                self.assertNotIn("project", result)
                factory.assert_not_called()

    async def test_missing_credential_has_no_network(self):
        result = await self.probe([], token_present=False)
        self.assertEqual(result["error"]["code"], "credential_missing")
        self.assertEqual(self.requests, [])

    async def test_missing_or_hidden_project_keeps_unknown_existence(self):
        result = await self.probe([httpx.Response(404, text="private error")])
        self.assertIsNone(result["project_exists"])
        self.assertEqual(result["error"]["code"], "project_missing_or_inaccessible")
        self.assertNotIn("private error", json.dumps(result))
        self.assertEqual(len(self.requests), 1)

    async def test_http_failure_categories_stop_at_first_failure(self):
        for status, code in ((401, "gitlab_unauthorized"), (403, "gitlab_forbidden"),
                             (429, "gitlab_rate_limited"), (502, "gitlab_unavailable"),
                             (418, "gitlab_http_error")):
            with self.subTest(status=status):
                stream = UnreadBody()
                result = await self.probe([httpx.Response(status, stream=stream)])
                self.assertEqual(result["error"]["code"], code)
                self.assertEqual(result["error"]["http_status"], status)
                self.assertEqual(len(self.requests), 1)
                self.assertFalse(stream.read)
                self.assertTrue(stream.closed)

    async def test_empty_repository_is_distinct_from_missing_project(self):
        result = await self.probe([self.metadata(empty_repo=True)])
        self.assertTrue(result["project_exists"])
        self.assertEqual(result["error"]["code"], "repository_empty")
        self.assertEqual(len(self.requests), 1)

    async def test_missing_default_branch_not_assumed_empty(self):
        result = await self.probe([self.metadata(default_branch=None)], ref="")
        self.assertTrue(result["project_exists"])
        self.assertEqual(result["error"]["code"], "default_branch_unavailable")

    async def test_explicit_ref_when_default_is_unavailable(self):
        result = await self.probe([self.metadata(default_branch=None), self.commit()], ref="develop")
        self.assertTrue(result["ok"])
        self.assertTrue(self.requests[1].url.path.endswith("/develop"))

    async def test_ref_404_is_not_project_404(self):
        result = await self.probe([self.metadata(), httpx.Response(404)])
        self.assertTrue(result["project_exists"])
        self.assertIsNone(result["resolved_commit_sha"])
        self.assertEqual(result["error"]["code"], "ref_missing_or_inaccessible")
        self.assertEqual(len(self.requests), 2)

    async def test_default_ref_and_file_heads_are_pinned_to_commit(self):
        streams = [UnreadBody(), UnreadBody()]
        result = await self.probe([self.metadata(), self.commit(), *[httpx.Response(200, stream=s) for s in streams]],
                                  ref="", required_files=["README.md", "tests/test.py"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["resolved_commit_sha"], SHA)
        self.assertEqual(result["ref"], "main")
        self.assertFalse(result["write_access_checked"])
        self.assertFalse(result["writes_performed"])
        self.assertEqual([r.method for r in self.requests], ["GET", "GET", "HEAD", "HEAD"])
        self.assertIn(b"team%2Fpractice", self.requests[0].url.raw_path)
        for r, stream in zip(self.requests[2:], streams):
            self.assertEqual(r.url.params["ref"], SHA)
            self.assertFalse(stream.read)
            self.assertTrue(stream.closed)
        self.assertNotIn("content", result["files"][0])

    async def test_file_failure_retains_evidence_and_stops_later_checks(self):
        result = await self.probe([self.metadata(), self.commit(), httpx.Response(200), httpx.Response(404)],
                                  required_files=["README.md", "EXERCISE.md", "AGENTS.md"])
        self.assertFalse(result["ok"])
        self.assertTrue(result["project_exists"])
        self.assertEqual(result["resolved_commit_sha"], SHA)
        self.assertEqual(len(result["files"]), 2)
        self.assertTrue(result["files"][0]["readable"])
        self.assertEqual(result["error"]["code"], "required_file_missing_or_inaccessible")
        self.assertEqual(len(self.requests), 4)

    async def test_malformed_success_does_not_invent_revision(self):
        for response in (httpx.Response(200, text="not-json"), httpx.Response(200, json=[]),
                         httpx.Response(200, json={"id": "short"})):
            result = await self.probe([self.metadata(), response])
            self.assertFalse(result["ok"])
            self.assertIsNone(result["resolved_commit_sha"])
            self.assertEqual(result["error"]["code"], "invalid_response")

    async def test_metadata_identity_mismatch_is_rejected(self):
        result = await self.probe([self.metadata(path_with_namespace="other/project")])
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_response")
        self.assertEqual(len(self.requests), 1)

    async def test_metadata_body_limit(self):
        result = await self.probe([httpx.Response(200, content=b"x" * (access.MAX_METADATA_BYTES + 1))])
        self.assertEqual(result["error"]["code"], "invalid_response")

    async def test_input_bounds_and_credential_paths_fail_before_network(self):
        for fields in ({"ref": "../main"}, {"ref": "https://bad.invalid/main"},
                       {"required_files": [".env"]}, {"required_files": ["../a"]},
                       {"required_files": ["/a"]}, {"required_files": ["a", "a"]},
                       {"required_files": [f"{x}.md" for x in range(17)]}):
            result = await self.probe([], **fields)
            self.assertEqual(result["error"]["code"], "invalid_probe_input")
            self.assertEqual(self.requests, [])

    async def test_redirects_never_followed_or_echoed(self):
        result = await self.probe([httpx.Response(302, headers={"Location": "https://other.invalid/secret"})])
        self.assertEqual(result["error"]["code"], "redirect_refused")
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn("other.invalid", json.dumps(result))

    async def test_transport_exception_text_is_not_returned(self):
        result = await self.probe([httpx.ConnectError("sensitive text")])
        self.assertEqual(result["error"]["code"], "transport_error")
        self.assertNotIn("sensitive text", json.dumps(result))
        self.assertIsNone(result["project_exists"])

    async def test_certificate_failure_is_not_an_auth_failure(self):
        exc = httpx.ConnectError("sensitive")
        exc.__cause__ = ssl.SSLCertVerificationError("private certificate details")
        result = await self.probe([exc])
        self.assertEqual(result["error"]["code"], "tls_verification_failed")

    async def test_time_budget_returns_incomplete_evidence(self):
        async def handler(req):
            await asyncio.sleep(1)
            return self.metadata()
        factory = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch.object(access, "PROBE_TIMEOUT_SECONDS", 0.01):
            result = await self.probe([], client_factory=factory)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "timeout")
        self.assertIsNone(result["project_exists"])

    async def test_mcp_wrapper_preserves_success_and_translates_only_safe_errors(self):
        async def success():
            return {"content": "hello"}
        async def denied():
            raise access.ProjectAccessError("project_not_allowlisted", stage="local_policy")
        async def unexpected():
            raise RuntimeError("not a classified error")
        self.assertEqual(await access.visible_access_errors(success)(), {"content": "hello"})
        result = await access.visible_access_errors(denied)()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["stage"], "local_policy")
        with self.assertRaises(RuntimeError):
            await access.visible_access_errors(unexpected)()


class ProjectAccessCLITests(unittest.TestCase):
    def env(self, root):
        return {"GITLAB_AGENT_ENV_FILE": str(root / "absent.env"), "GITLAB_BASE_URL": BASE,
                "GITLAB_ALLOWED_PROJECTS": PROJECT, "GITLAB_TOKEN": "fixture-token",
                "GITLAB_WORKSPACE_ROOT": str(root / "must-not-be-created")}

    def test_helper_denial_is_nonzero_json_and_creates_no_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {**os.environ, **self.env(root)}
            result = subprocess.run([sys.executable, "-m", "gitlab_agent.project_access", "other/repo"],
                                    env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["error"]["code"], "project_not_allowlisted")
            self.assertFalse(data["mcp_connection_checked"])
            self.assertFalse(data["workspace_policy_allowed"])
            self.assertFalse((root / "must-not-be-created").exists())

    def test_local_configuration_error_is_redacted(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.env(Path(tmp))):
            with patch.object(AgentSettings, "load", side_effect=ValueError("sensitive")):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = access.main([PROJECT])
        self.assertEqual(code, 1)
        self.assertNotIn("sensitive", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "configuration_error")

    def test_success_exit_and_read_policy_not_write_authorization(self):
        responses = [httpx.Response(200, json={"id": 12, "path_with_namespace": PROJECT, "default_branch": "main"}),
                     httpx.Response(200, json={"id": SHA})]
        real_client = httpx.AsyncClient
        factory = lambda **kw: real_client(transport=httpx.MockTransport(lambda r: responses.pop(0)), **kw)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {**self.env(Path(tmp)), "GITLAB_ALLOWED_PROJECTS": "", "GITLAB_REQUIRE_WRITE_ALLOWLIST": "true"}):
            with patch.object(access.httpx, "AsyncClient", side_effect=factory):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = access.main([PROJECT])
        data = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertFalse(data["workspace_policy_allowed"])
        self.assertFalse(data["write_access_checked"])

    def test_workspace_denial_explains_manual_grant_and_does_not_change_settings(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.env(Path(tmp))):
            settings = AgentSettings.load()
        before = set(settings.allowed_projects)
        with self.assertRaisesRegex(access.ProjectAccessError, "GITLAB_ALLOWED_PROJECTS") as cm:
            settings.assert_project_allowed_for_workspace("other/repo")
        self.assertIn("Ask the user", str(cm.exception))
        self.assertEqual(before, settings.allowed_projects)


if __name__ == "__main__":
    unittest.main()
