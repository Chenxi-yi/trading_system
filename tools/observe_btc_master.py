"""027 daily reserved public master acquisition plus offline as-of OI check."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import PublicClient,DataError
from miniquant.data.public_failures import failure_record
from miniquant.data.instrument_master import master,check_units
from miniquant.data.archive_collection import save_json

URLS={'https://openapi.okx.com/api/v5/public/time','https://openapi.okx.com/api/v5/public/instruments?instType=SWAP'}


class CountedOpener:
    def __init__(self,inner,day):self.inner=inner;self.day=day;self.events=[];self.blocked=False
    def open(self,request,**kwargs):
        if self.blocked or datetime.now(timezone.utc).strftime('%Y-%m-%d')!=self.day or request.full_url not in URLS or request.get_method()!='GET' or len(self.events)>=6 or any(k.lower()!='user-agent' for k,v in request.header_items()):raise DataError('027 request boundary')
        item=dict(attempt=len(self.events)+1,started_at_ms=int(time.time()*1000));self.events.append(item)
        try:
            response=self.inner.open(request,**kwargs);item['status']='response';return response
        except Exception as exc:
            item.update(failure_record(exc));self.blocked=bool(item.get('access_block'));raise


def run(base):
    protocol=ROOT/'research/audits/BTC-MASTER-027.json';plan=json.loads(protocol.read_text())
    out=ROOT/'artifacts/BTC-MASTER-027';out.mkdir(parents=True,exist_ok=True)
    names=['tools/observe_btc_master.py','src/miniquant/data/instrument_master.py',
        'src/miniquant/data/public_failures.py','src/miniquant/data/okx_public.py',
        'src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py']
    provenance=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},inputs={plan['baseline']:plan['baseline_sha256']})
    manifest=out/'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())!=provenance:raise DataError('027 frozen provenance changed')
    else:
        save_json(manifest,provenance)
        for n in names:
            target=out/'source_snapshot'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    baseline=(ROOT/plan['baseline']).read_bytes()
    if hashlib.sha256(baseline).hexdigest()!=plan['baseline_sha256']:raise DataError('Baseline changed')
    masters=[master(json.loads(baseline))]
    day=datetime.now(timezone.utc).strftime('%Y-%m-%d');folder=base/'days'/day
    folder.mkdir(parents=True,exist_ok=True)
    reservation=folder/'reservation.json'
    if not reservation.exists() and not (base/'access_blocked.json').exists():
        save_json(reservation,dict(reserved_at_ms=int(time.time()*1000),maximum_HTTP_attempts=6,policy='No second acquisition thisUTCday, even after crash'))
        client=PublicClient();counted=CountedOpener(client.opener,day);client.opener=counted
        attempt=dict(complete=False)
        try:
            clock=client.get('time');save_json(folder/'time.raw.json',clock)
            server=int(json.loads(clock['body_text'])['data'][0]['ts'])
            if abs(server-clock['ingested_at_ms'])>60_000:raise DataError('027 clock disagreement')
            raw=client.get('instruments',dict(instType='SWAP'));save_json(folder/'master.raw.json',raw)
            normalized=master(raw);save_json(folder/'master.json',normalized);attempt['complete']=True
        except Exception as exc:attempt.update(failure_record(exc))
        attempt['HTTP_attempts']=len(counted.events);attempt['events']=counted.events
        if any(e.get('access_block') for e in counted.events):save_json(base/'access_blocked.json',attempt)
        save_json(folder/'attempt.json',attempt)
    for file in sorted((base/'days').glob('*/master.raw.json')):
        masters.append(master(json.loads(file.read_text())))
    paths=sorted((ROOT/'data/forward-observation/BTC').glob('*/oi.raw.json'))
    observations=[json.loads(p.read_text()) for p in paths]
    start=json.loads((ROOT/'artifacts/BTC-OI-FORECAST-024/activation.json').read_text())['start_ms']
    result=check_units(masters,observations,int(time.time()*1000),start)
    invalidation=base/'study_invalidated.json'
    if result['unit_break_detected'] and not invalidation.exists():save_json(invalidation,result)
    if invalidation.exists():result.update(study_supported=False,persistent_invalidation=True)
    inventory={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for p in sorted((base/'days').glob('*/master.raw.json')):inventory[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    ident=hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest()
    report=out/'inventories'/ident
    if not report.exists():
        report.mkdir(parents=True);save_json(report/'inputs.json',inventory);save_json(report/'unit_checks.json',result)
    summary=dict(observed_at=datetime.now(timezone.utc).isoformat(),study_supported=result['study_supported'],
        unit_break_detected=result['unit_break_detected'],persistent_invalidation=invalidation.exists(),
        master_fresh=result['master_fresh'],master_versions=len(masters),OI_observations=len(observations),
        unit_disagreements=sum(c['status']=='unit_disagreement' for c in result['checks']),
        material_changes=len(result['material_changes']),execution_review_changes=len(result['execution_review_changes']),
        today_acquisition_complete=(folder/'master.json').exists(),
        account_reads=0,orders=0,pnl_tests=0)
    save_json(base/'latest_quality.json',summary);print(json.dumps(summary,indent=2))


def main():
    base=ROOT/'data/instrument-master/BTC-USDT-SWAP';base.mkdir(parents=True,exist_ok=True)
    with (base/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(base)


if __name__=='__main__':main()
