from __future__ import annotations

import asyncio
import os
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from gitlab_agent.tls import (
    MAX_CA_BUNDLE_BYTES, api_client_options, ca_bundle_path,
    validate_base_url, verified_context,
)
from gitlab_agent.config import AgentSettings
from tls_fixtures import LocalAuthority


class TLSPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.authority = LocalAuthority(self.root)
        self.base = "https://gitlab.example.invalid"

    def test_valid_plain_endpoint_and_prefix(self):
        for value in (self.base, self.base + "/gitlab", "https://[::1]:8443", "http://localhost"):
            with self.subTest(value=value):
                self.assertEqual(validate_base_url(value), value)

    def test_credential_endpoint_is_rejected_without_echo(self):
        value = "https://" + "user:never-a-real-secret" + "@gitlab.example.invalid"
        with self.assertRaises(ValueError) as error:
            validate_base_url(value)
        self.assertNotIn("never-a-real-secret", str(error.exception))

    def test_ambiguous_endpoints_are_rejected(self):
        for value in ("", "ftp://gitlab.example.invalid", self.base + "?x=1", self.base + "#part",
                      self.base + "?", self.base + "/../x", self.base + "/%2f", self.base + "//x",
                      self.base + "\\x", self.base + ":0", self.base + ":99999", "https://[broken",
                      "https://gitlab\n.example.invalid", "https://%65xample.invalid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_base_url(value)

    def test_relative_ca_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            ca_bundle_path("certificates/ca.pem")

    def test_empty_ca_uses_public_roots(self):
        context = verified_context(self.base)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertGreater(context.cert_store_stats()["x509_ca"], 0)
        self.assertIsNone(ca_bundle_path(""))

    def test_custom_ca_keeps_public_roots(self):
        public = verified_context(self.base).cert_store_stats()["x509_ca"]
        private = verified_context(self.base, ca_bundle=self.authority.ca_path)
        self.assertEqual(private.cert_store_stats()["x509_ca"], public + 1)
        self.assertTrue(private.check_hostname)

    def test_verification_cannot_be_disabled(self):
        for base in (self.base, "http://gitlab.example.invalid"):
            with self.subTest(base=base), self.assertRaisesRegex(ValueError, "cannot be disabled"):
                verified_context(base, verify_ssl=False)

    def test_missing_empty_invalid_or_directory_bundle_rejected(self):
        empty = self.root / "empty.pem"
        empty.write_bytes(b"")
        invalid = self.root / "invalid.pem"
        invalid.write_bytes(b"not a certificate")
        for value in (self.root / "missing.pem", empty, invalid, self.root):
            with self.subTest(path=value), self.assertRaisesRegex(ValueError, "GITLAB_CA_BUNDLE"):
                verified_context(self.base, ca_bundle=value)

    def test_oversized_bundle_is_rejected(self):
        large = self.root / "large.pem"
        large.write_bytes(b"x" * (MAX_CA_BUNDLE_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "4 MiB"):
            verified_context(self.base, ca_bundle=large)

    def test_private_key_bundle_is_rejected(self):
        value = self.root / "mixed.pem"
        value.write_bytes(self.authority.ca_path.read_bytes() + ("-----BEGIN " + "PRIVATE KEY-----").encode())
        with self.assertRaisesRegex(ValueError, "no private keys"):
            verified_context(self.base, ca_bundle=value)

    def test_implicit_ssl_environment_does_not_choose_trust(self):
        with patch.dict(os.environ, {"SSL_CERT_FILE": str(self.root / "missing"),
                                     "SSL_CERT_DIR": str(self.root / "missing-dir")}):
            context = verified_context(self.base, ca_bundle=self.authority.ca_path)
        self.assertTrue(context.check_hostname)

    def test_sync_explicit_off_origin_request_sends_nothing(self):
        sent = []
        with httpx.Client(headers={"PRIVATE-TOKEN": "dummy-session"}, trust_env=False,
                          transport=httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200)),
                          **api_client_options(self.base)) as client:
            with self.assertRaisesRegex(httpx.RequestError, "destination rejected"):
                client.get("https://other.example.invalid/api/v4/user")
        self.assertEqual(sent, [])

    def test_sync_prefix_escape_sends_nothing(self):
        sent = []
        with httpx.Client(transport=httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200)),
                          trust_env=False, **api_client_options(self.base + "/gitlab")) as client:
            for path in ("/api/v4/user", "/gitlab/api/v4evil", "/gitlab/sign_in", "/gitlab/api/v4/../../sign_in"):
                with self.subTest(path=path), self.assertRaises(httpx.RequestError):
                    client.get(self.base + path)
        self.assertEqual(sent, [])

    def test_scheme_port_and_host_header_changes_send_nothing(self):
        sent = []
        with httpx.Client(trust_env=False,
                transport=httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200)),
                **api_client_options(self.base)) as client:
            for url in (self.base.replace("https:", "http:") + "/api/v4/user",
                        self.base + ":444/api/v4/user"):
                with self.subTest(url=url), self.assertRaises(httpx.RequestError):
                    client.get(url)
            with self.assertRaises(httpx.RequestError):
                client.get(self.base + "/api/v4/user", headers={"Host": "other.example.invalid"})
        self.assertEqual(sent, [])

    def test_encoded_traversal_or_backslash_sends_nothing(self):
        sent = []
        with httpx.Client(trust_env=False,
                transport=httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200)),
                **api_client_options(self.base)) as client:
            for path in ("/api/v4/%2e%2e/sign_in", "/api/v4/%5cother", "/api/v4/%00hidden"):
                with self.subTest(path=path), self.assertRaises(httpx.RequestError):
                    client.get(self.base + path)
        self.assertEqual(sent, [])

    def test_sync_correct_prefix_and_encoded_project_work(self):
        sent = []
        with httpx.Client(transport=httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200)),
                          trust_env=False, **api_client_options(self.base + "/gitlab")) as client:
            self.assertEqual(client.get(self.base + "/gitlab/api/v4/projects/team%2Fproject").status_code, 200)
        self.assertEqual(len(sent), 1)

    def test_all_redirect_statuses_are_refused_before_second_request(self):
        for status in (301, 302, 303, 307, 308):
            sent = []
            def respond(req):
                sent.append(req)
                return httpx.Response(status, headers={"Location": "/api/v4/other"})
            with self.subTest(status=status), httpx.Client(
                transport=httpx.MockTransport(respond), trust_env=False,
                **api_client_options(self.base),
            ) as client:
                # Even a caller's per-request follow_redirects=True cannot bypass the hook.
                with self.assertRaisesRegex(httpx.RequestError, "redirect refused"):
                    client.get(self.base + "/api/v4/user", follow_redirects=True)
            self.assertEqual(len(sent), 1)

    def test_async_off_origin_and_redirect_are_guarded(self):
        async def check():
            sent = []
            def respond(req):
                sent.append(req)
                return httpx.Response(302, headers={"Location": "http://other.example.invalid/api/v4/user"})
            async with httpx.AsyncClient(trust_env=False, transport=httpx.MockTransport(respond),
                                         **api_client_options(self.base, asynchronous=True)) as client:
                with self.assertRaisesRegex(httpx.RequestError, "destination rejected"):
                    await client.get("https://other.example.invalid/api/v4/user")
                self.assertEqual(sent, [])
                with self.assertRaisesRegex(httpx.RequestError, "redirect refused"):
                    await client.get(self.base + "/api/v4/user", follow_redirects=True)
            self.assertEqual(len(sent), 1)
        asyncio.run(check())

    def test_redirect_response_body_is_never_read(self):
        class NoRead(httpx.SyncByteStream):
            def __iter__(self):
                raise AssertionError("redirect body must not be read")
                yield b""
        def respond(req):
            return httpx.Response(302, headers={"Location": "https://other.example.invalid/private"},
                                  stream=NoRead())
        with httpx.Client(trust_env=False, transport=httpx.MockTransport(respond),
                          **api_client_options(self.base)) as client:
            with self.assertRaisesRegex(httpx.RequestError, "redirect refused"):
                client.get(self.base + "/api/v4/user")

    def test_config_loads_ca_without_proxy_inheritance(self):
        env_file = self.root / ".env"
        env_file.write_text("GITLAB_BASE_URL=" + self.base + "\nGITLAB_CA_BUNDLE=" + str(self.authority.ca_path) + "\n")
        # Config precedence tests isolate all environment variables. Supply a
        # workspace path explicitly instead of relying on an OS home lookup
        # (Windows needs USERPROFILE/HOMEDRIVE, intentionally cleared here).
        with patch.dict(os.environ, {"GITLAB_AGENT_ENV_FILE": str(env_file),
                                     "GITLAB_WORKSPACE_ROOT": str(self.root / "workspaces")}, clear=True):
            settings = AgentSettings.load()
        self.assertEqual(settings.api_ca_bundle, self.authority.ca_path)
        self.assertFalse(settings.api_trust_env)

    def test_exported_ca_setting_keeps_precedence(self):
        env_file = self.root / ".env"
        env_file.write_text("GITLAB_BASE_URL=" + self.base + "\nGITLAB_CA_BUNDLE=/unused.pem\n")
        with patch.dict(os.environ, {"GITLAB_AGENT_ENV_FILE": str(env_file),
                                     "GITLAB_WORKSPACE_ROOT": str(self.root / "workspaces"),
                                     "GITLAB_CA_BUNDLE": str(self.authority.ca_path)}, clear=True):
            settings = AgentSettings.load()
        self.assertEqual(settings.api_ca_bundle, self.authority.ca_path)


class LoopbackTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.authority = LocalAuthority(Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_sync_private_ca_with_trust_env_false(self):
        with self.authority.serve() as (url, seen):
            with httpx.Client(trust_env=False, headers={"PRIVATE-TOKEN": "dummy-session"},
                              **api_client_options(url, ca_bundle=self.authority.ca_path)) as client:
                response = client.get(url + "/api/v4/user")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(seen[0]["token"], "dummy-session")

    def test_proxy_environment_is_not_needed_for_private_ca(self):
        with self.authority.serve() as (url, seen):
            with patch.dict(os.environ, {"HTTPS_PROXY": "http://127.0.0.1:1", "NO_PROXY": ""}):
                with httpx.Client(trust_env=False,
                        **api_client_options(url, ca_bundle=self.authority.ca_path)) as client:
                    self.assertEqual(client.get(url + "/api/v4/user").status_code, 200)
            self.assertEqual(len(seen), 1)

    def test_async_private_ca_with_trust_env_false(self):
        async def check(url):
            async with httpx.AsyncClient(trust_env=False,
                    **api_client_options(url, ca_bundle=self.authority.ca_path, asynchronous=True)) as client:
                return await client.get(url + "/api/v4/user")
        with self.authority.serve() as (url, seen):
            self.assertEqual(asyncio.run(check(url)).status_code, 200)
            self.assertEqual(len(seen), 1)

    def test_untrusted_ca_fails_before_credential_request(self):
        with self.authority.serve() as (url, seen), httpx.Client(
            trust_env=False, headers={"PRIVATE-TOKEN": "dummy-session"}, **api_client_options(url),
        ) as client:
            with self.assertRaises(httpx.ConnectError):
                client.get(url + "/api/v4/user")
            self.assertEqual(seen, [])

    def test_wrong_hostname_fails_before_credential_request(self):
        with self.authority.serve(wrong_host=True) as (url, seen), httpx.Client(
            trust_env=False, headers={"PRIVATE-TOKEN": "dummy-session"},
            **api_client_options(url, ca_bundle=self.authority.ca_path),
        ) as client:
            with self.assertRaises(httpx.ConnectError):
                client.get(url + "/api/v4/user")
            self.assertEqual(seen, [])

    def test_expired_certificate_fails_before_credential_request(self):
        with self.authority.serve(expired=True) as (url, seen), httpx.Client(
            trust_env=False, headers={"PRIVATE-TOKEN": "dummy-session"},
            **api_client_options(url, ca_bundle=self.authority.ca_path),
        ) as client:
            with self.assertRaises(httpx.ConnectError):
                client.get(url + "/api/v4/user")
            self.assertEqual(seen, [])

    def test_cross_origin_redirect_does_not_contact_target(self):
        with self.authority.serve() as (target, target_seen):
            with self.authority.serve(redirect=target + "/api/v4/user") as (url, seen):
                with httpx.Client(trust_env=False, headers={"PRIVATE-TOKEN": "dummy-session"},
                        **api_client_options(url, ca_bundle=self.authority.ca_path)) as client:
                    with self.assertRaisesRegex(httpx.RequestError, "redirect refused"):
                        client.get(url + "/api/v4/user")
                self.assertEqual(len(seen), 1)
                self.assertEqual(target_seen, [])

    def test_async_redirect_never_contacts_target(self):
        async def check(url):
            async with httpx.AsyncClient(trust_env=False, headers={"PRIVATE-TOKEN": "dummy-session"},
                    **api_client_options(url, ca_bundle=self.authority.ca_path, asynchronous=True)) as client:
                with self.assertRaisesRegex(httpx.RequestError, "redirect refused"):
                    await client.get(url + "/api/v4/user")
        with self.authority.serve() as (target, target_seen):
            with self.authority.serve(redirect=target + "/api/v4/user") as (url, seen):
                asyncio.run(check(url))
                self.assertEqual(len(seen), 1)
                self.assertEqual(target_seen, [])

    def test_https_downgrade_is_not_followed(self):
        with self.authority.serve(redirect="http://127.0.0.1:1/api/v4/user") as (url, seen):
            with httpx.Client(trust_env=False,
                    **api_client_options(url, ca_bundle=self.authority.ca_path)) as client:
                with self.assertRaisesRegex(httpx.RequestError, "redirect refused"):
                    client.get(url + "/api/v4/user")
            self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
