"""Bounded actual first-observed pressure snapshots; separate from immutable OI buckets."""
from datetime import datetime,timezone
from pathlib import Path
import fcntl,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import PublicClient
from miniquant.data.observation import normalize_pressure_observation
from tools.okx_market_audit import atomic_json


def main():
    base=ROOT/'data/forward-pressure/BTC';base.mkdir(parents=True,exist_ok=True)
    with (base/'collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        client=PublicClient();clock=client.get('time');now=int(json.loads(clock['body_text'])['data'][0]['ts'])
        if abs(now-int(datetime.now(timezone.utc).timestamp()*1000))>60000:raise ValueError('Clock disagreement')
        out=base/str(now//900000*900000);out.mkdir(exist_ok=True)
        if (out/'summary.json').exists() and json.loads((out/'summary.json').read_text())['complete']:print('Pressure bucket already observed');return
        names=['tools/observe_btc_pressure.py','src/miniquant/data/observation.py','src/miniquant/data/okx_public.py']
        provenance=dict(code_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names})
        codefile=out/'code-manifest.json'
        if codefile.exists() and json.loads(codefile.read_text())['code_sha256']!=provenance['code_sha256']:raise ValueError('Partial pressure observation source changed')
        if not codefile.exists():
            atomic_json(codefile,provenance)
            for n in names:
                saved=out/'source_snapshot'/n;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes((ROOT/n).read_bytes())
        atomic_json(out/'clock.json',clock);jobs=[]
        for kind in ('funding','premium'):
            try:
                raw=out/(kind+'.raw.json')
                if raw.exists():env=json.loads(raw.read_text())
                else:env=client.get(kind,dict(instId='BTC-USDT-SWAP',limit='1'));atomic_json(raw,env)
                normal=normalize_pressure_observation(kind,env,'BTC-USDT-SWAP');atomic_json(out/(kind+'.json'),normal)
                jobs.append(dict(kind=kind,status='observed',available_at=normal['available_at'],fresh=normal['fresh']))
            except Exception as exc:jobs.append(dict(kind=kind,status='failed',error_type=type(exc).__name__))
        summary=dict(observed_at=datetime.now(timezone.utc).isoformat(),complete=all(x['status']=='observed' for x in jobs),jobs=jobs,account_reads=0,orders_sent=0,pnl_generated=False)
        atomic_json(out/'summary.json',summary);atomic_json(base/'checkpoint.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
