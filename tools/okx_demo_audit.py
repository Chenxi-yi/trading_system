"""OKX Global demo-only, GET-only connection audit. Requires Python >= 3.11.

No live profile, writes, redirects, arbitrary hosts or raw response logging.
The default audit reads server time, account configuration and balance status.
"""
import argparse
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"openapi.okx.com", "www.okx.com"}
ALLOWED_PATHS = {
    "/api/v5/public/time": set(),
    "/api/v5/account/config": set(),
    "/api/v5/account/balance": {"ccy"},
    "/api/v5/account/instruments": {"instType", "instId"},
    "/api/v5/account/trade-fee": {"instType", "instId", "instFamily", "groupId"},
    "/api/v5/account/positions": {"instType", "instId"},
    "/api/v5/trade/orders-pending": {"instType", "instId", "limit"},
}


class AuditError(Exception):
    """Messages contain only fixed labels or numeric exchange error codes."""


@dataclass(frozen=True, repr=False)
class DemoCredentials:
    api_key: str = field(repr=False)
    secret_key: str = field(repr=False)
    passphrase: str = field(repr=False)


def load_demo(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise AuditError("configuration_not_regular_file")
    if path.stat().st_mode & 0o077:
        raise AuditError("configuration_permissions_require_0600")
    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except Exception:
        raise AuditError("configuration_parse_failed") from None
    profile = config.get("profiles", {}).get("demo")
    if not isinstance(profile, dict) or profile.get("demo") is not True:
        raise AuditError("explicit_demo_profile_required")
    keys = ("api_key", "secret_key", "passphrase")
    if not all(isinstance(profile.get(k), str) and profile[k].strip() for k in keys):
        raise AuditError("demo_credentials_missing")
    if any("\n" in profile[k] or "\r" in profile[k] for k in keys):
        raise AuditError("invalid_credential_format")
    return DemoCredentials(*(profile[k] for k in keys))


def signature(secret, timestamp, request_path):
    message = (timestamp + "GET" + request_path).encode()
    return base64.b64encode(hmac.new(secret.encode(), message, hashlib.sha256).digest()).decode()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AuditError("redirect_refused")


class DemoClient:
    def __init__(self, credentials, host="openapi.okx.com", opener=None):
        if host not in HOSTS:
            raise AuditError("host_not_allowed")
        self.credentials = credentials
        self.host = host
        self.offset_ms = 0
        self.opener = opener or urllib.request.build_opener(NoRedirect())

    def get(self, path, params=None):
        if path not in ALLOWED_PATHS:
            raise AuditError("endpoint_not_allowed")
        params = params or {}
        if set(params) - ALLOWED_PATHS[path]:
            raise AuditError("query_parameter_not_allowed")
        query = urllib.parse.urlencode(sorted(params.items()))
        request_path = path + ("?" + query if query else "")
        headers = {"User-Agent": "PersonalMiniQuant-DemoAudit/0.1",
                   "Content-Type": "application/json", "x-simulated-trading": "1"}
        if path != "/api/v5/public/time":
            timestamp = datetime.fromtimestamp((time.time() * 1000 + self.offset_ms) / 1000,
                                              timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            headers.update({"OK-ACCESS-KEY": self.credentials.api_key,
                            "OK-ACCESS-PASSPHRASE": self.credentials.passphrase,
                            "OK-ACCESS-TIMESTAMP": timestamp,
                            "OK-ACCESS-SIGN": signature(self.credentials.secret_key, timestamp, request_path)})
        request = urllib.request.Request("https://" + self.host + request_path,
                                         headers=headers, method="GET")
        try:
            with self.opener.open(request, timeout=12) as response:
                raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise AuditError("response_too_large")
        except urllib.error.HTTPError as error:
            code = ""
            try:
                body = json.loads(error.read(4096))
                value = str(body.get("code", ""))
                if re.fullmatch(r"\d{1,10}", value):
                    code = ":api_" + value
            except Exception:
                pass
            raise AuditError("http_" + str(error.code) + code) from None
        except AuditError:
            raise
        except Exception:
            raise AuditError("network_request_failed") from None
        try:
            data = json.loads(raw)
            code = str(data.get("code", ""))
        except Exception:
            raise AuditError("invalid_json_response") from None
        if code != "0":
            safe_code = code if re.fullmatch(r"\d{1,10}", code) else "unknown"
            raise AuditError("api_" + safe_code)
        if not isinstance(data.get("data"), list):
            raise AuditError("invalid_response_schema")
        return data["data"]


def connection_audit(client):
    report = {"environment": "demo", "site": "global", "host": client.host,
              "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "order_requests_sent": 0, "checks": []}
    steps = [("server_time", "/api/v5/public/time"),
             ("authenticated_account_config", "/api/v5/account/config"),
             ("authenticated_balance_read", "/api/v5/account/balance")]
    for label, path in steps:
        before = time.time() * 1000
        try:
            rows = client.get(path)
            after = time.time() * 1000
            if not rows:
                raise AuditError("empty_response")
            if label == "server_time":
                client.offset_ms = int(rows[0]["ts"]) - (before + after) / 2
                report["clock_offset_ms_estimate"] = round(client.offset_ms)
            report["checks"].append({"check": label, "endpoint": path, "status": "ok",
                                     "elapsed_ms": round(after - before)})
        except Exception as error:
            reason = str(error) if isinstance(error, AuditError) else "response_processing_failed"
            report["checks"].append({"check": label, "endpoint": path, "status": "failed", "reason": reason})
            report["status"] = "failed"
            return report
    report["status"] = "demo_authenticated"
    report["limitations"] = ["REST only; WebSocket not tested", "No orders or trading-permission test",
                             "Product inventory and fee audit not performed"]
    return report


def save_report(report):
    folder = ROOT / "runtime" / "okx-demo-audit"
    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(0o700)
    path = folder / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def main():
    parser = argparse.ArgumentParser(description="OKX Global demo connection audit; GET only")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--host", choices=sorted(HOSTS), default="openapi.okx.com")
    args = parser.parse_args()
    try:
        client = DemoClient(load_demo(args.config), host=args.host)
        report = connection_audit(client)
        output = save_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("Local report:", output)
        return 0 if report["status"] == "demo_authenticated" else 1
    except AuditError as error:
        print("Audit stopped:", error)
        return 1
    except Exception:
        print("Audit stopped: unexpected_error; details suppressed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
