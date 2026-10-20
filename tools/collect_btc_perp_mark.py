"""Collect independently checkpointed historical mark bars for perpetual risk research."""
import fcntl
import json
from datetime import datetime,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import atomic_json,collect,summarize
from miniquant.data.okx_public import PublicClient


def main():
    run=ROOT/'data/market-audit/btc-perp-mark-20261021';(run/'raw').mkdir(parents=True,exist_ok=True)
    with (run/'collector.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        statefile=run/'checkpoint.json'
        if statefile.exists():state=json.loads(statefile.read_text())
        else:
            since=int(datetime(2022,1,1,tzinfo=timezone.utc).timestamp()*1000)
            end=int(datetime(2026,10,1,tzinfo=timezone.utc).timestamp()*1000)
            job=dict(id='mark_BTC-USDT-SWAP_4H',kind='mark',inst_id='BTC-USDT-SWAP',bar='4H',start=since,end=end,cursor=end,pages=[],status='collecting')
            state=dict(schema_version=1,snapshot=dict(note='BTC perpetual mark history; archive funding ends September2026'),jobs=[job]);atomic_json(statefile,state)
        collect(run,state,PublicClient(),300);summarize(run,state)


if __name__=='__main__':main()
