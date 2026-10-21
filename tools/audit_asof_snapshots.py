"""020 offline raw identity/hash validation and as-of join; no research returns."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import DataError
from miniquant.data.observation import normalize_observation
from miniquant.data.asof_snapshots import join_snapshots
from miniquant.data.archive_collection import save_json


def main():
    protocol=ROOT/'research/audits/BTC-CAUSAL-SNAPSHOT-020.json'
    plan=json.loads(protocol.read_text())
    out=ROOT/'artifacts/BTC-CAUSAL-SNAPSHOT-020';out.mkdir(parents=True,exist_ok=False)
    names=['tools/audit_asof_snapshots.py','src/miniquant/data/asof_snapshots.py',
           'src/miniquant/data/observation.py','src/miniquant/data/okx_public.py',
           'src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py']
    code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    save_json(out/'manifest.json',dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code=code,inputs=plan['inputs']))
    for name in names:
        target=out/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    interest,books=[],[]
    for name,expected in plan['inputs'].items():
        content=(ROOT/name).read_bytes()
        if hashlib.sha256(content).hexdigest()!=expected:raise DataError('Frozen raw input changed')
        raw=json.loads(content);url=urlparse(raw['url']);query=parse_qs(url.query)
        kind='open_interest' if Path(name).name=='oi.raw.json' else 'books'
        path='/api/v5/public/open-interest' if kind=='open_interest' else '/api/v5/market/books'
        if url.scheme!='https' or url.netloc!='openapi.okx.com' or url.path!=path or query.get('instId')!=['BTC-USDT-SWAP']:
            raise DataError('Raw endpoint identity mismatch')
        row=normalize_observation(kind,raw,'BTC-USDT-SWAP')
        (interest if kind=='open_interest' else books).append(row)
    rows=join_snapshots(interest,books)
    save_json(out/'joined.json',rows)
    gaps=[milliseconds_gap(a,b) for a,b in zip(rows,rows[1:])]
    summary=dict(complete=True,raw_files_verified=len(plan['inputs']),books=len(books),oi=len(interest),
                 eligible=sum(r['eligible'] for r in rows),excluded=sum(not r['eligible'] for r in rows),
                 max_decision_gap_ms=max(gaps,default=0),continuous_sampling_certified=False,
                 alpha_candidates=0,pnl_tests=0,new_HTTP_attempts=0)
    save_json(out/'summary.json',summary);print(json.dumps(summary,indent=2))


def milliseconds_gap(a,b):
    from miniquant.data.asof_snapshots import milliseconds
    return milliseconds(b['decision_at'])-milliseconds(a['decision_at'])


if __name__=='__main__':main()
