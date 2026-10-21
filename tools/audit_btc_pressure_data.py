"""Bounded public probes and historical input feasibility; no return labels/PnL."""
from datetime import datetime,timezone
from collections import Counter
from pathlib import Path
import fcntl,hashlib,json,sys,platform
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import PublicClient,utc
from miniquant.research.pressure_data import prepare_funding,lagged_funding,synchronized_close_premium
from miniquant.backtest.replay import HOUR,DAY
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-PRESSURE-DATA-006';out.mkdir(exist_ok=True)
    with (out/'audit.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'summary.json').exists():raise ValueError('Completed data audit immutable')
        cfg=ROOT/'research/audits/BTC-PRESSURE-DATA-006.json'
        names=['src/miniquant/data/okx_public.py','src/miniquant/research/pressure_data.py','tools/audit_btc_pressure_data.py','src/miniquant/backtest/replay.py','src/miniquant/accounting/spot.py','tools/okx_market_audit.py']
        inputs=['data/market-audit/btc-overnight-20261021/trade_BTC-USDT-SWAP_4H.json','data/market-audit/btc-overnight-20261021/index_BTC-USDT_4H.json','data/funding-archive/BTC-USDT-SWAP/normalized.json']
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        manifest=dict(protocol_sha256=sha(cfg),code={n:sha(ROOT/n) for n in names},inputs={n:sha(ROOT/n) for n in inputs},python=platform.python_version())
        if (out/'manifest.json').exists():
            if json.loads((out/'manifest.json').read_text())!=manifest:raise ValueError('Partial run fingerprint changed')
        else:
            atomic_json(out/'manifest.json',manifest)
            for p in [ROOT/n for n in names]+[cfg]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        clockpath=out/'clock.json';client=PublicClient()
        if not clockpath.exists():atomic_json(clockpath,client.get('time'))
        now=int(json.loads(json.loads(clockpath.read_text())['body_text'])['data'][0]['ts'])
        jobs=[('premium_latest','premium',dict(instId='BTC-USDT-SWAP',limit='100')),
              ('premium_90d','premium',dict(instId='BTC-USDT-SWAP',after=str(now-90*DAY),limit='100')),
              ('premium_200d','premium',dict(instId='BTC-USDT-SWAP',after=str(now-200*DAY),limit='100')),
              ('index_2024','index',dict(instId='BTC-USDT',bar='4H',after='1704067200000',limit='2')),
              ('index_2023','index',dict(instId='BTC-USDT',bar='4H',after='1672531200000',limit='2')),
              ('funding_latest','funding',dict(instId='BTC-USDT-SWAP',limit='100')),
              ('funding_2024','funding',dict(instId='BTC-USDT-SWAP',after='1704067200000',limit='2'))]
        probes={}
        for name,kind,params in jobs:
            raw=out/(name+'.raw.json')
            try:
                if not raw.exists():atomic_json(raw,client.get(kind,params))
                env=json.loads(raw.read_text());assert sha_text(env['body_text'])==env['body_sha256']
                data=json.loads(env['body_text'])['data']
                times=[int(r[0] if isinstance(r,list) else r['fundingTime'] if kind=='funding' else r['ts']) for r in data]
                probes[name]=dict(status='ok',records=len(data),first=utc(min(times)) if times else None,last=utc(max(times)) if times else None,available_at=utc(env['ingested_at_ms']),fields=sorted(data[0]) if data and isinstance(data[0],dict) else None)
                print(name,len(data),flush=True)
            except Exception as exc:probes[name]=dict(status='failed',error_type=type(exc).__name__);print(name,'failed',type(exc).__name__,flush=True)
        trade=json.loads((ROOT/inputs[0]).read_text());index=json.loads((ROOT/inputs[1]).read_text());funding=json.loads((ROOT/inputs[2]).read_text())
        prepared=prepare_funding(funding)
        clean=[x for x in prepared if x[0]>=1672531200000]
        decisions=[r['end_time_ms'] for r in trade if r['complete'] and 1672531200000<=r['end_time_ms']<=1790812800000]
        features=[lagged_funding(clean,t) for t in decisions]
        availability=Counter(f['status'] for f in features)
        bytime={r['open_time_ms']:r for r in index if r['complete']}
        proxies=[synchronized_close_premium(r,bytime[r['open_time_ms']]) for r in trade if r['complete'] and r['open_time_ms'] in bytime]
        summary=dict(completed_at=datetime.now(timezone.utc).isoformat(),probes=probes,local_funding=dict(events=len(funding),post2023=len(clean),first=utc(prepared[0][0]),last=utc(prepared[-1][0]),non8h_aligned_total=sum(t%(8*HOUR)!=0 for t,_ in prepared),post2023_interval_hours=dict(Counter(str((b[0]-a[0])/HOUR) for a,b in zip(clean,clean[1:]))),formula_method_fields_in_archive=False),funding_feature=dict(decisions=len(decisions),status_counts=dict(availability),lag_hours=4,max_age_hours=24,earliest_decision=utc(min(decisions)),latest_decision=utc(max(decisions))),premium_proxy=dict(rows=len(proxies),first=utc(proxies[0]['event_time_ms']) if proxies else None,last=utc(proxies[-1]['event_time_ms']) if proxies else None,official_premium=False),new_alpha_candidates=0,return_tests=0,orders_sent=0,limitations=['Probe sample is not continuous coverage','Historical actual publication unavailable; settlement+4H is sensitivity assumption not guarantee','Trade/index close ratio is not official impact premium','Funding formula/method missing in long archive; rate comparability can change'])
        atomic_json(out/'summary.json',summary)
        print(json.dumps(summary,indent=2))


def sha_text(text):return hashlib.sha256(text.encode()).hexdigest()
if __name__=='__main__':main()
