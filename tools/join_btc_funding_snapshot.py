"""New immutable funding snapshot, archive + audited recent REST, no old-file edits."""
from decimal import Decimal
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'artifacts/BTC-PRESSURE-DATA-006'
    target=out/'funding-joined.json'
    if target.exists():raise ValueError('Preserve completed funding join')
    archive=ROOT/'data/funding-archive/BTC-USDT-SWAP/normalized.json'
    raw=out/'funding_latest.raw.json'
    env=json.loads(raw.read_text())
    if hashlib.sha256(env['body_text'].encode()).hexdigest()!=env['body_sha256']:raise ValueError('REST hash mismatch')
    rows={r['event_time_ms']:dict(r) for r in json.loads(archive.read_text())}
    overlap=added=0;start=1672531200000;end=1790812800000
    for r in json.loads(env['body_text'])['data']:
        t=int(r['fundingTime'])
        if not start<=t<end:continue
        if r['instId']!='BTC-USDT-SWAP':raise ValueError('Wrong funding product')
        if t in rows:
            if Decimal(rows[t]['realized_rate'])!=Decimal(r['realizedRate']):raise ValueError('Funding sources disagree')
            overlap+=1
        else:
            rate=Decimal(r['realizedRate'])
            if not rate.is_finite():raise ValueError('Invalid realized rate')
            rows[t]=dict(inst_id=r['instId'],event_time_ms=t,realized_rate=str(rate),source='OKX unsigned REST historical realizedRate',lineage_id=env['body_sha256'],formula_type=r['formulaType'],method=r['method'],historical_available_at=None)
            added+=1
    selected=[rows[t] for t in sorted(rows) if start<=t<end]
    if [r['event_time_ms'] for r in selected]!=list(range(start,end,28800000)):raise ValueError('Eight-hour schedule coverage incomplete')
    with target.open('x') as f:json.dump(selected,f,indent=2)
    manifest=dict(inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (archive,raw)},source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),matched_overlaps=overlap,added_from_rest=added,output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),records=len(selected),start_ms=start,end_exclusive_ms=end,note='8H schedule observed for this BTC period only; past publication not established; no old archive edits')
    (out/'funding-join-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    dest=out/'source_snapshot/tools/join_btc_funding_snapshot.py';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:manifest[k] for k in ('matched_overlaps','added_from_rest','records')},indent=2))

if __name__=='__main__':main()
