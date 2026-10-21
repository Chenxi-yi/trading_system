"""016: at most five GETs, no auth/retries; persistent access-block guard."""
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import sys
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
from miniquant.data.binance_observation import PublicClient, normalize
from miniquant.data.archive_collection import save_json

SOURCES = ['tools/observe_btc_binance.py', 'src/miniquant/data/binance_observation.py',
           'src/miniquant/data/okx_public.py', 'src/miniquant/data/archive_collection.py',
           'src/miniquant/data/binance_metrics.py']


def main():
    base = ROOT / 'data/forward-binance/BTC'
    base.mkdir(parents=True, exist_ok=True)
    with (base / 'collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (base / 'access_blocked.json').exists():
            print('Access block persists; no HTTP attempted')
            return
        client = PublicClient()
        summary = dict(observed_at=datetime.now(timezone.utc).isoformat(), complete=False,
                       jobs=[], account_reads=0, orders_sent=0, pnl_generated=False)
        # Save every invocation separately, including a failed clock request.
        out = base / 'invocations' / str(int(datetime.now(timezone.utc).timestamp()*1_000_000))
        out.mkdir(parents=True)
        code = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}
        save_json(out/'code-manifest.json', dict(code=code, protocol_sha256=hashlib.sha256(
            (ROOT/'research/audits/BTC-BINANCE-FORWARD-016.json').read_bytes()).hexdigest()))
        for name in SOURCES:
            target = out/'source_snapshot'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT/name).read_bytes())
        try:
            clock = client.get('time')
            save_json(out/'time.raw.json', clock)
            server = normalize('time', clock)['server_time_ms']
            bucket = str(server//900_000*900_000)
            complete = base/'buckets'/bucket
            if complete.exists():
                summary.update(complete=True, skipped_existing_bucket=bucket)
            else:
                for kind in ('open_interest_current', 'open_interest_history', 'global_ratio', 'taker_ratio'):
                    envelope = client.get(kind)
                    save_json(out/(kind+'.raw.json'), envelope)
                    normal = normalize(kind, envelope)
                    save_json(out/(kind+'.json'), normal)
                    summary['jobs'].append(dict(kind=kind, status='observed', available_at=normal['available_at']))
                summary['complete'] = True
                save_json(complete, dict(invocation=str(out.relative_to(ROOT))))
        except Exception as exc:
            summary['error_type'] = type(exc).__name__
            if isinstance(exc, HTTPError):
                summary['http_status'] = exc.code
                if exc.code in (403, 451):
                    save_json(base/'access_blocked.json', dict(observed_at=summary['observed_at'],
                              http_status=exc.code, action='Stop; no bypass or automatic retry'))
        summary['request_attempts'] = client.attempts
        save_json(out/'summary.json', summary)
        save_json(base/'checkpoint.json', summary)
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
