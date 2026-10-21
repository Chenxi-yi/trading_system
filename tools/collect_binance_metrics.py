"""Frozen BTCUSDT2023-Sep2026 archive collection, max100requests/invocation."""
from pathlib import Path
import argparse,fcntl,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.archive_collection import MetricsFetcher,collect_chunk,coverage_summary,save_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request-budget',type=int,default=100);args=parser.parse_args()
    if not 0<args.request_budget<=100:raise ValueError('Request budget outside frozen bound')
    run=ROOT/'data/binance-metrics/BTCUSDT-2023-2026';run.mkdir(parents=True,exist_ok=True)
    with (run/'collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cfgpath=ROOT/'research/audits/BTC-DERIVATIVES-COLLECT-010.json';cfg=json.loads(cfgpath.read_text())
        names=['tools/collect_binance_metrics.py','src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']
        fingerprint=dict(protocol_sha256=hashlib.sha256(cfgpath.read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names})
        path=run/'checkpoint.json'
        if path.exists():
            state=json.loads(path.read_text())
            if state['fingerprint']!=fingerprint:raise ValueError('Frozen collection source changed')
        else:
            state=dict(start=cfg['start'],end_exclusive=cfg['end_exclusive'],fingerprint=fingerprint,days={},total_request_attempts=0)
            save_json(path,state)
            for p in [ROOT/n for n in names]+[cfgpath]:
                dest=run/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        result=collect_chunk(run,state,MetricsFetcher(),args.request_budget)
        report=coverage_summary(state);save_json(run/'coverage.json',report)
        print(json.dumps(dict(run_result=result,coverage=report),indent=2),flush=True)

if __name__=='__main__':main()
