"""Post-result ordering/grid audit, preserves original ZIP and initial report."""
from datetime import datetime,timedelta
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.binance_metrics import audit_metrics_zip


def main():
    out=ROOT/'artifacts/BTC-DERIVATIVES-DATA-009';summary=json.loads((out/'summary.json').read_text());audit={}
    for day,v in summary['samples'].items():
        if v['status']!='sample_verified':continue
        name=f'BTCUSDT-metrics-{day}.zip';stats,rows=audit_metrics_zip((out/name).read_bytes(),(out/(name+'.CHECKSUM')).read_bytes(),day)
        raw=[datetime.fromisoformat(r['create_time']) for r in rows];sorted_times=sorted(raw)
        expected=[datetime.fromisoformat(day)+timedelta(minutes=5*i) for i in range(288)]
        record=dict(raw_backward_steps=sum(b<a for a,b in zip(raw,raw[1:])),sorted_unique5m_grid_matches_declared_day=sorted_times==expected,rows=len(rows),original_order_preserved=True,publication_known=False)
        audit[day]=record
        # A separate inspection output is not an available-at-certified feature table.
        path=out/(day+'.label-sorted-inspection.json')
        if path.exists():raise ValueError('Preserve completed inspection')
        path.write_text(json.dumps(sorted(rows,key=lambda r:r['create_time']),indent=2)+'\n')
    path=out/'label-order-audit.json'
    if path.exists():raise ValueError('Preserve completed ordering audit')
    path.write_text(json.dumps(dict(post_result_descriptive=True,samples=audit,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_candidates=0,note='Sorting labels neither establishes observation interval nor historical publication. No disputed issue timeline inferred.'),indent=2)+'\n')
    saved=out/'source_snapshot/tools/audit_binance_metrics_order.py';saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(Path(__file__).read_bytes())
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
