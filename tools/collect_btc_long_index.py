"""Separate frozen BTC index4H2023-Sep2026 snapshot; never mutate old cohorts."""
from datetime import datetime,timezone
import fcntl,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.okx_market_audit import atomic_json,collect,summarize
from miniquant.data.okx_public import PublicClient


def main():
    run=ROOT/'data/market-audit/btc-long-index-20261021';(run/'raw').mkdir(parents=True,exist_ok=True)
    with (run/'collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        statefile=run/'checkpoint.json'
        names=['tools/collect_btc_long_index.py','tools/okx_market_audit.py','src/miniquant/data/okx_public.py']
        hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
        if statefile.exists():
            state=json.loads(statefile.read_text())
            if hashes!=state['snapshot']['code_hashes']:raise ValueError('Source changed during frozen collection')
        else:
            start=1672531200000;end=1790812800000
            job=dict(id='index_BTC-USDT_4H',kind='index',inst_id='BTC-USDT',bar='4H',start=start,end=end,cursor=end,pages=[],status='collecting')
            state=dict(schema_version=1,snapshot=dict(created_at=datetime.now(timezone.utc).isoformat(),reason='006 older-index probes succeeded; isolate snapshot to preserve prior research',code_hashes=hashes),jobs=[job])
            atomic_json(statefile,state)
            for n in names:
                p=run/'source_snapshot'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
        collect(run,state,PublicClient(),100)
        report=summarize(run,state)
        print(json.dumps(report['jobs'],indent=2),flush=True)

if __name__=='__main__':main()
