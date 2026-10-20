"""Resumable BTC-only overnight public collection, protected by an OS file lock."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import atomic_json,collect,summarize,page_payload
from miniquant.data.okx_public import PublicClient,INTERVALS


def main():
    run=ROOT/'data/market-audit/btc-overnight-20261021'
    (run/'raw').mkdir(parents=True,exist_ok=True)
    with (run/'collector.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Collector already active; no duplicate process started.');return
        client=PublicClient()
        if (run/'checkpoint.json').exists():state=json.loads((run/'checkpoint.json').read_text())
        else:
            envelope=client.get('time');atomic_json(run/'time.json',envelope)
            now=int(page_payload(envelope)[0]['ts'])
            if abs(now-int(time.time()*1000))>60000:raise ValueError('stale_clock')
            start=int(datetime(2020,1,1,tzinfo=timezone.utc).timestamp()*1000)
            jobs=[]
            def add(kind,inst,bar,since):
                end=now//INTERVALS[bar]*INTERVALS[bar]
                jobs.append(dict(id=f'{kind}_{inst}_{bar}',kind=kind,inst_id=inst,bar=bar,start=since,end=end,cursor=end,pages=[],status='collecting'))
            add('trade','BTC-USDT','4H',start)
            add('trade','BTC-USDT-SWAP','4H',start)
            add('trade','BTC-USDT','1H',start)
            add('trade','BTC-USDT','15m',int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000))
            for kind,inst in (('mark','BTC-USDT-SWAP'),('index','BTC-USDT')):add(kind,inst,'4H',now//86400000*86400000-90*86400000)
            sources=['tools/collect_btc_overnight.py','tools/okx_market_audit.py','src/miniquant/data/okx_public.py']
            provenance=dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                            code_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in sources},
                            python=sys.version,created_at=datetime.now(timezone.utc).isoformat())
            state=dict(schema_version=1,snapshot=dict(time=page_payload(envelope),provenance=provenance),jobs=jobs)
            atomic_json(run/'checkpoint.json',state)
        print('Run:',run,flush=True)
        collect(run,state,client,500)
        summarize(run,state)
        print('Remaining jobs:',sum(j['status']=='collecting' for j in state['jobs']),flush=True)


if __name__=='__main__':main()
