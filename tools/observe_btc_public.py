"""One bounded BTC public snapshot per15min bucket; no accounts, no orders/PnL."""
from datetime import datetime,timezone
import fcntl,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import PublicClient
from miniquant.data.observation import normalize_observation
from tools.okx_market_audit import atomic_json


def main():
    base=ROOT/'data/forward-observation/BTC';base.mkdir(parents=True,exist_ok=True)
    with (base/'collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        client=PublicClient();clock=client.get('time');server=int(json.loads(clock['body_text'])['data'][0]['ts'])
        if abs(server-int(time.time()*1000))>60000:raise ValueError('Server/local clock disagreement')
        bucket=str(server//900000*900000);out=base/bucket;out.mkdir(exist_ok=True)
        if (out/'summary.json').exists():
            existing=json.loads((out/'summary.json').read_text())
            if existing['complete']:print('Current bucket already observed; no duplicate');return
        atomic_json(out/'clock.json',clock)
        jobs=[('oi','open_interest',dict(instType='SWAP',instId='BTC-USDT-SWAP')),
              ('perp_book','books',dict(instId='BTC-USDT-SWAP',sz='5')),
              ('spot_book','books',dict(instId='BTC-USDT',sz='5')),
              ('perp_quote','ticker',dict(instId='BTC-USDT-SWAP')),
              ('spot_quote','ticker',dict(instId='BTC-USDT'))]
        results=[]
        for jid,kind,params in jobs:
            raw=out/(jid+'.raw.json');normal=out/(jid+'.json')
            try:
                if raw.exists():envelope=json.loads(raw.read_text())
                else:envelope=client.get(kind,params);atomic_json(raw,envelope)
                record=normalize_observation(kind,envelope,params['instId']);atomic_json(normal,record)
                results.append(dict(id=jid,status='observed',fresh=record['fresh'],available_at=record['available_at'],source_sha256=envelope['body_sha256']))
                print(jid,'observed',flush=True)
            except Exception as exc:
                results.append(dict(id=jid,status='failed',error_type=type(exc).__name__))
                print(jid,'failed',type(exc).__name__,flush=True)
        sources=('tools/observe_btc_public.py','src/miniquant/data/okx_public.py','src/miniquant/data/observation.py')
        summary=dict(bucket=bucket,observed_at=datetime.now(timezone.utc).isoformat(),complete=all(r['status']=='observed' for r in results),jobs=results,
                     code_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources},orders_sent=0,account_reads=0,pnl_generated=False,
                     note='Sparse REST observations, not continuous tick/WS data or a trading strategy. Never backfill availability or earlier fills.')
        atomic_json(out/'summary.json',summary);atomic_json(base/'checkpoint.json',summary)
        print('Observation checkpoint',bucket,'complete',summary['complete'],flush=True)


if __name__=='__main__':main()
