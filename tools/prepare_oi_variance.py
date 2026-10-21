"""024 immutable prospective forecasts; never print real labels or scores."""
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import fcntl,hashlib,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import DataError
from miniquant.data.observation import normalize_observation
from miniquant.data.asof_snapshots import join_snapshots
from miniquant.data.archive_collection import save_json
from miniquant.research.oi_variance import samples,predict


def run():
    base=ROOT/'artifacts/BTC-OI-FORECAST-024'
    protocol=ROOT/'research/audits/BTC-OI-FORECAST-024.json'
    plan=ROOT/'research/contracts/BTC_FWD_OI_RISK_001.json'
    names=['tools/prepare_oi_variance.py','src/miniquant/research/oi_variance.py',
        'src/miniquant/data/asof_snapshots.py','src/miniquant/data/observation.py',
        'src/miniquant/data/okx_public.py','src/miniquant/data/archive_collection.py',
        'src/miniquant/data/binance_metrics.py']
    code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    cutoff_file=ROOT/'research/audits/BTC-FUTURE-FEATURES-022.json'
    provenance=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code=code,
        inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (plan,cutoff_file)},
        environment=dict(python=sys.version.split()[0],numpy=np.__version__,platform=sys.platform))
    manifest=base/'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())!=provenance:raise DataError('Frozen024 sources changed')
    else:
        save_json(manifest,provenance)
        for n in names:
            target=base/'source_snapshot'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    activation=base/'activation.json'
    if not activation.exists():
        frozen=int(time.time()*1000)
        cutoff=json.loads((ROOT/'research/audits/BTC-FUTURE-FEATURES-022.json').read_text())['cutoff_ms']
        start=max(frozen,cutoff)
        save_json(activation,dict(code_frozen_at_ms=frozen,start_ms=start,end_ms=start+60*86_400_000))
    schedule=json.loads(activation.read_text())
    now=int(time.time()*1000)
    if now>=schedule['end_ms']:
        print('024 fixed window ended; require registered final evaluator, no automatic score display');return
    inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'data/forward-observation/BTC').glob('*/*.raw.json'))
        if p.name in ('oi.raw.json','perp_book.raw.json')}
    ident=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    out=base/'inventories'/ident;out.mkdir(parents=True,exist_ok=True)
    if not (out/'inputs.json').exists():save_json(out/'inputs.json',inputs)
    elif json.loads((out/'inputs.json').read_text())!=inputs:raise DataError('024 input inventory mismatch')
    interest,books=[],[]
    for name,digest in inputs.items():
        content=(ROOT/name).read_bytes()
        if hashlib.sha256(content).hexdigest()!=digest:raise DataError('Input changed during read')
        raw=json.loads(content);url=urlparse(raw['url']);query=parse_qs(url.query)
        kind='open_interest' if Path(name).name=='oi.raw.json' else 'books'
        path='/api/v5/public/open-interest' if kind=='open_interest' else '/api/v5/market/books'
        if url.scheme!='https' or url.netloc!='openapi.okx.com' or url.path!=path or query.get('instId')!=['BTC-USDT-SWAP']:raise DataError('024 source identity mismatch')
        row=normalize_observation(kind,raw,'BTC-USDT-SWAP')
        (interest if kind=='open_interest' else books).append(row)
    rows=samples(join_snapshots(interest,books),books,schedule['start_ms'])
    # Internal labels are never printed or scored; do not inspect before end_ms.
    save_json(out/'internal_samples_no_peek.json',rows)
    summary=dict(observed_at=datetime.now(timezone.utc).isoformat(),start_ms=schedule['start_ms'],
        end_ms=schedule['end_ms'],raw_files=len(inputs),features=len(rows),
        completed_labels=sum(r['label_available_ms'] is not None for r in rows),
        new_predictions=0,alpha_candidates=0,pnl_tests=0,orders=0,new_HTTP_attempts=0)
    fresh=[r for r in rows if 0<=now-r['feature_at_ms']<=120_000]
    if fresh:
        point=fresh[-1];target=base/'predictions'/f"{point['feature_at_ms']}.json"
        if not target.exists():
            try:
                forecast=predict(rows,point,point['feature_at_ms'])
                if forecast is not None:
                    save_json(target,dict(generated_at_ms=now,feature_at_ms=point['feature_at_ms'],**forecast))
                    summary['new_predictions']=1
            except Exception as exc:summary['fit_error_type']=type(exc).__name__
    save_json(out/'quality.json',summary);save_json(base/'latest_quality.json',summary)
    print(json.dumps(summary,indent=2))


def main():
    base=ROOT/'artifacts/BTC-OI-FORECAST-024';base.mkdir(parents=True,exist_ok=True)
    with (base/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()


if __name__=='__main__':main()
