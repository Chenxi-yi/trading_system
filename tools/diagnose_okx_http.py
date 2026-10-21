"""019 same-wire one-request diagnosis; never rerun old017 or change headers."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.audit_okx_units import BoundedClient
from miniquant.data.okx_units import body
from miniquant.data.public_failures import failure_record
from miniquant.data.archive_collection import save_json


def main():
    out = ROOT/'artifacts/BTC-HTTP-DIAGNOSTIC-019'
    out.mkdir(parents=True, exist_ok=False)
    names = ['tools/diagnose_okx_http.py', 'tools/audit_okx_units.py',
             'src/miniquant/data/public_failures.py', 'src/miniquant/data/okx_units.py',
             'src/miniquant/data/okx_public.py', 'src/miniquant/data/archive_collection.py',
             'src/miniquant/data/binance_metrics.py']
    protocol = ROOT/'research/audits/BTC-HTTP-DIAGNOSTIC-019.json'
    code = {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    save_json(out/'manifest.json',dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code=code,inputs={}))
    for n in names:
        target=out/'source_snapshot'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    summary=dict(observed_at=datetime.now(timezone.utc).isoformat(),complete=False,
                 request_attempts=1,account_reads=0,orders_sent=0,pnl_tests=0)
    try:
        envelope=BoundedClient().get('time')
        save_json(out/'time.raw.json',envelope)
        rows,received=body(envelope,'time')
        summary.update(complete=True,received_at_ms=received)
    except Exception as exc:
        summary.update(failure_record(exc))
        if summary.get('access_block'):
            save_json(out/'access_blocked.json',summary)
    save_json(out/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
