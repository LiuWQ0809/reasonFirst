"""Fresh loopback TLS fixtures. No private key or real credential is committed."""
from __future__ import annotations

import ipaddress
import json
import ssl
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class LocalAuthority:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.counter = 0
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ReasonFirst ephemeral test CA")])
        self.cert = (
            x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(self.key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=3)).not_valid_after(now + timedelta(days=3))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
            .sign(self.key, hashes.SHA256())
        )
        self.ca_path = root / "ca.pem"
        self.ca_path.write_bytes(self.cert.public_bytes(serialization.Encoding.PEM))

    def server_context(self, *, expired: bool = False, wrong_host: bool = False) -> ssl.SSLContext:
        self.counter += 1
        now = datetime.now(timezone.utc)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "loopback test")])
        cert = (
            x509.CertificateBuilder().subject_name(subject).issuer_name(self.cert.subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.key.public_key()), critical=False)
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("wrong.example.invalid") if wrong_host
                else x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(self.key, hashes.SHA256())
        )
        cert_path = self.root / f"server-{self.counter}.pem"
        key_path = self.root / f"server-{self.counter}.key"
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                              serialization.PrivateFormat.PKCS8,
                                              serialization.NoEncryption()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        return context

    @contextmanager
    def serve(self, *, expired: bool = False, wrong_host: bool = False, redirect: str | None = None):
        requests: list[dict[str, str]] = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_GET(self) -> None:
                requests.append({"path": self.path, "token": self.headers.get("PRIVATE-TOKEN", "")})
                if redirect is not None:
                    self.send_response(302)
                    self.send_header("Location", redirect)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if self.path.endswith("/trace"):
                    body = b"build completed\n"
                    mime = "text/plain"
                else:
                    body = json.dumps({"id": 1, "username": "loopback-test"}).encode()
                    mime = "application/json"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        server.socket = self.server_context(expired=expired, wrong_host=wrong_host).wrap_socket(
            server.socket, server_side=True,
        )
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield f"https://127.0.0.1:{server.server_port}", requests
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
