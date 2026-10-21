"""One-shot 017, four unsigned public GETs, persist raw before validation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import time
from urllib.request import build_opener, Request
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from miniquant.data.okx_public import NoRedirect, DataError, integer
from miniquant.data.okx_units import audit_units, body, URLS
from miniquant.data.archive_collection import save_json


class BoundedClient:
    """Each attempt counted, including failures; no hidden retry in older client."""
    def __init__(self):
        self.attempts = 0
        self.opener = build_opener(NoRedirect())

    def get(self, kind):
        if kind not in URLS or self.attempts >= 4:
            raise DataError('017 endpoint or budget rejected')
        self.attempts += 1
        started = time.time_ns()//1_000_000
        with self.opener.open(Request(URLS[kind], method='GET'), timeout=10) as response:
            raw = response.read(4_000_001)
        received = time.time_ns()//1_000_000
        if len(raw) > 4_000_000:
            raise DataError('017 response too large')
        return dict(url=URLS[kind], request_started_at_ms=started, ingested_at_ms=received,
                    body_text=raw.decode('utf-8'), body_sha256=hashlib.sha256(raw).hexdigest())


def main():
    out = ROOT/'artifacts/BTC-OKX-UNITS-017'
    out.mkdir(parents=True, exist_ok=False)
    names = ['tools/audit_okx_units.py', 'src/miniquant/data/okx_units.py',
             'src/miniquant/data/okx_public.py', 'src/miniquant/data/archive_collection.py',
             'src/miniquant/data/binance_metrics.py']
    protocol = ROOT/'research/audits/BTC-OKX-UNITS-017.json'
    code = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    save_json(out/'manifest.json', dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), code=code, inputs={}))
    for name in names:
        target = out/'source_snapshot'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    summary = dict(started_at=datetime.now(timezone.utc).isoformat(), complete=False,
                   request_attempts=0, account_reads=0, orders_sent=0, pnl_tests=0)
    jobs = ('time', 'instruments', 'open_interest', 'trade')
    client, raw = BoundedClient(), {}
    try:
        for kind in jobs:
            summary['request_attempts'] += 1
            raw[kind] = client.get(kind)
            save_json(out/(kind+'.raw.json'), raw[kind])
            if kind == 'time':
                data, received = body(raw[kind], kind)
                if abs(integer(data[0]['ts'])-received) > 60_000:
                    raise ValueError('Clock disagreement')
        result = audit_units(raw['instruments'], raw['open_interest'], raw['trade'])
        save_json(out/'unit-checks.json', result)
        summary.update(complete=True, quantity_conversion_consistent=result['quantity_conversion_consistent'])
    except Exception as exc:
        summary['error_type'] = type(exc).__name__
    save_json(out/'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
