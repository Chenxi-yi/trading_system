"""022 supersedes021 dryrun: locked resumable inventories, no HTTP/trade path."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import fcntl,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import DataError
from miniquant.data.observation import normalize_observation
from miniquant.data.asof_snapshots import join_snapshots
from miniquant.data.future_features import four_hour_features
from miniquant.data.archive_collection import save_json


def build():
    protocol=ROOT/'research/audits/BTC-FUTURE-FEATURES-022.json'
    plan=json.loads(protocol.read_text())
    names=['tools/build_btc_future_features.py','src/miniquant/data/future_features.py',
        'src/miniquant/data/asof_snapshots.py','src/miniquant/data/observation.py',
        'src/miniquant/data/okx_public.py','src/miniquant/data/archive_collection.py',
        'src/miniquant/data/binance_metrics.py']
    code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    base=ROOT/'artifacts/BTC-FUTURE-FEATURES-022'
    base.mkdir(parents=True,exist_ok=True)
    manifest=base/'manifest.json'
    provenance=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code=code,inputs={})
    if manifest.exists():
        if json.loads(manifest.read_text())!=provenance:raise DataError('022 frozen provenance changed')
    else:
        save_json(manifest,provenance)
        for n in names:
            target=base/'source_snapshot'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'data/forward-observation/BTC').glob('*/*.raw.json'))
        if p.name in ('oi.raw.json','perp_book.raw.json')}
    ident=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    out=base/'inventories'/ident
    if (out/'summary.json').exists():print('022 inventory already evaluated');return
    out.mkdir(parents=True,exist_ok=True)
    inventory=out/'inputs.json'
    if inventory.exists() and json.loads(inventory.read_text())!=inputs:raise DataError('022 inventory changed')
    if not inventory.exists():save_json(inventory,inputs)
    interest,books=[],[]
    for name,digest in inputs.items():
        content=(ROOT/name).read_bytes()
        if hashlib.sha256(content).hexdigest()!=digest:raise DataError('Concurrent input change')
        raw=json.loads(content);parsed=urlparse(raw['url']);query=parse_qs(parsed.query)
        kind='open_interest' if Path(name).name=='oi.raw.json' else 'books'
        path='/api/v5/public/open-interest' if kind=='open_interest' else '/api/v5/market/books'
        if parsed.scheme!='https' or parsed.netloc!='openapi.okx.com' or parsed.path!=path or query.get('instId')!=['BTC-USDT-SWAP']:raise DataError('022 wrong source')
        row=normalize_observation(kind,raw,'BTC-USDT-SWAP')
        (interest if kind=='open_interest' else books).append(row)
    joined=join_snapshots(interest,books)
    features=four_hour_features(joined,plan['cutoff_ms'])
    save_json(out/'features.json',features)
    summary=dict(input_raw_files=len(inputs),cutoff_utc=plan['cutoff_utc'],features=len(features),
        status='features_available' if features else 'awaiting_full_post_cutoff_coverage',
        signals=0,pnl_tests=0,new_HTTP_attempts=0,orders=0)
    save_json(out/'summary.json',summary);save_json(base/'latest.json',dict(inventory=ident,**summary))
    print(json.dumps(summary,indent=2))


def main():
    base=ROOT/'artifacts/BTC-FUTURE-FEATURES-022'
    base.mkdir(parents=True,exist_ok=True)
    with (base/'builder.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        build()


if __name__=='__main__':main()
