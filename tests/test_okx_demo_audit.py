import base64
import hashlib
import hmac
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error

from tools.okx_demo_audit import (AuditError, DemoClient, DemoCredentials,
                                  NoRedirect, connection_audit, load_demo, signature)


class Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, limit):
        return self.body[:limit]


class FakeOpener:
    def __init__(self):
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        if request.full_url.endswith("/time"):
            return Response({"code": "0", "data": [{"ts": "1700000000000"}]})
        return Response({"code": "0", "data": [{"apiKey": "SHOULD_NEVER_APPEAR", "uid": "PRIVATE"}]})


class DemoAuditTests(unittest.TestCase):
    def setUp(self):
        self.credentials = DemoCredentials("FAKE_KEY", "FAKE_SECRET", "FAKE_PASSPHRASE")

    def test_signature_uses_exact_get_query_path(self):
        timestamp = "2026-10-20T00:00:00.000Z"
        path = "/api/v5/account/balance?ccy=BTC"
        expected = base64.b64encode(hmac.new(b"FAKE_SECRET", (timestamp+"GET"+path).encode(), hashlib.sha256).digest()).decode()
        self.assertEqual(signature("FAKE_SECRET", timestamp, path), expected)
        self.assertNotEqual(signature("FAKE_SECRET", timestamp, path), signature("FAKE_SECRET", timestamp, path.split("?")[0]))

    def test_explicit_demo_selected_even_if_default_is_live(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.toml"
            path.write_text('default_profile="live"\n[profiles.demo]\ndemo=true\napi_key="FAKE_KEY"\nsecret_key="FAKE_SECRET"\npassphrase="FAKE_PASSPHRASE"\n')
            path.chmod(0o600)
            self.assertEqual(load_demo(path).api_key, "FAKE_KEY")
            path.write_text(path.read_text().replace("demo=true", "demo=false"))
            with self.assertRaises(AuditError):
                load_demo(path)

    def test_write_endpoints_hosts_and_extra_queries_rejected(self):
        opener = FakeOpener()
        client = DemoClient(self.credentials, opener=opener)
        for path in ("/api/v5/trade/order", "/api/v5/asset/withdrawal", "/api/v5/account/set-leverage"):
            with self.assertRaises(AuditError):
                client.get(path)
        with self.assertRaises(AuditError):
            client.get("/api/v5/account/config", {"unknown": "value"})
        with self.assertRaises(AuditError):
            DemoClient(self.credentials, host="example.com")
        self.assertEqual(opener.requests, [])

    def test_demo_headers_get_and_sanitized_report(self):
        opener = FakeOpener()
        report = connection_audit(DemoClient(self.credentials, opener=opener))
        self.assertEqual(report["status"], "demo_authenticated")
        self.assertEqual(len(opener.requests), 3)
        for request in opener.requests:
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.get_header("X-simulated-trading"), "1")
        self.assertFalse(opener.requests[0].has_header("Ok-access-key"))
        self.assertEqual(opener.requests[1].get_header("Ok-access-key"), "FAKE_KEY")
        serialized = json.dumps(report)
        for secret in ("FAKE_KEY", "FAKE_SECRET", "FAKE_PASSPHRASE", "SHOULD_NEVER_APPEAR", "PRIVATE"):
            self.assertNotIn(secret, serialized)

    def test_redirect_refused(self):
        with self.assertRaises(AuditError):
            NoRedirect().redirect_request(None, None, 302, None, None, "https://example.com")

    def test_api_and_network_errors_do_not_echo_response(self):
        class BadOpener:
            def open(self, *args, **kwargs):
                raise urllib.error.HTTPError("https://www.okx.com", 401, "PRIVATE_SECRET", {}, io.BytesIO(b'{"code":"50101","msg":"PRIVATE_SECRET"}'))
        report = connection_audit(DemoClient(self.credentials, opener=BadOpener()))
        self.assertEqual(report["status"], "failed")
        self.assertIn("50101", json.dumps(report))
        self.assertNotIn("PRIVATE_SECRET", json.dumps(report))
        self.assertEqual(len(report["checks"]), 1)


if __name__ == "__main__":
    unittest.main()
