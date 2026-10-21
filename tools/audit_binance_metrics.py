"""Ten-request maximum official BTCUSDT metrics sample probe; no alpha/account API."""
from datetime import datetime,timezone
from pathlib import Path
import fcntl,hashlib,json,sys,time
from urllib import request,error
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import NoRedirect
from miniquant.data.binance_metrics import audit_metrics_zip
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-DERIVATIVES-DATA-009';out.mkdir(exist_ok=True)
    with (out/'audit.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'summary.json').exists():raise ValueError('Completed audit immutable')
        cfgpath=ROOT/'research/audits/BTC-DERIVATIVES-DATA-009.json';cfg=json.loads(cfgpath.read_text())
        names=['tools/audit_binance_metrics.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py','tools/okx_market_audit.py']
        manifest=dict(protocol_sha256=hashlib.sha256(cfgpath.read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},inputs={})
        if (out/'manifest.json').exists():
            if json.loads((out/'manifest.json').read_text())!=manifest:raise ValueError('Partial audit source changed')
        else:
            atomic_json(out/'manifest.json',manifest)
            for p in [ROOT/n for n in names]+[cfgpath]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        opener=request.build_opener(NoRedirect());results={};allrows={};requests=0
        for day in cfg['sample_dates']:
            zipname=f'BTCUSDT-metrics-{day}.zip';bodies={};metadata=[]
            try:
                for suffix in ('','.CHECKSUM'):
                    name=zipname+suffix;path=out/name;url='https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/'+name
                    if not path.exists():
                        requests+=1
                        if requests>10:raise ValueError('Request budget exceeded')
                        time.sleep(.3)
                        with opener.open(request.Request(url,method='GET',headers={'User-Agent':'PersonalMiniQuantDataAudit/0.1'}),timeout=10) as response:body=response.read(3000001)
                        if len(body)>3000000:raise ValueError('Oversized archive response')
                        path.write_bytes(body)
                        atomic_json(out/(name+'.meta.json'),dict(url=url,ingested_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(body).hexdigest()))
                    bodies[suffix]=path.read_bytes();metadata.append(json.loads((out/(name+'.meta.json')).read_text()))
                stats,rows=audit_metrics_zip(bodies[''],bodies['.CHECKSUM'],day);allrows[day]=rows
                results[day]=dict(status='sample_verified',**stats,raw_metadata=metadata);print(day,'verified',stats['rows'],flush=True)
            except Exception as exc:
                results[day]=dict(status='failed',error_type=type(exc).__name__,http_status=exc.code if isinstance(exc,error.HTTPError) else None);print(day,'failed',type(exc).__name__,flush=True)
        left={r['create_time']:r for r in allrows.get('2026-06-24',[])};right={r['create_time']:r for r in allrows.get('2026-06-25',[])}
        duplicates=[dict(label=k,same_values=left[k]==right[k]) for k in sorted(left.keys()&right.keys())]
        for stats in results.values():stats.pop('label_times',None)
        summary=dict(completed_at=datetime.now(timezone.utc).isoformat(),new_http_requests=requests,samples=results,june24_25_duplicate_labels=duplicates,new_candidates=0,return_tests=0,account_reads=0,orders_sent=0,limitations=['Samples only, not complete long history','Unverified user issue is quality-audit lead, not authoritative timestamp specification','Labels are not original publication times','No inference of stock-unit conversion or causality','Cross-venue features cannot replace OKX execution/costs'])
        atomic_json(out/'summary.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
