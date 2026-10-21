"""Offline integrity recheck of acquired metrics, including completed days skipped on resume."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import fcntl,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.binance_metrics import audit_metrics_zip
from miniquant.data.archive_collection import coverage_summary,save_json


def recheck(run):
    run=Path(run);state=json.loads((run/'checkpoint.json').read_text());file_hashes={}
    for body in sorted((run/'raw').glob('*')):
        if not (body.name.endswith('.zip') or body.name.endswith('.CHECKSUM')):continue
        meta=body.with_name(body.name+'.meta.json')
        if not meta.exists():raise ValueError('Body missing download metadata')
        saved=json.loads(meta.read_text());digest=hashlib.sha256(body.read_bytes()).hexdigest()
        if digest!=saved['sha256']:raise ValueError('Acquired body SHA256 mismatch')
        file_hashes[body.name]=digest
    backward=[];duplicates=[];incomplete=[]
    for day,prior in sorted(state['days'].items()):
        if prior['status']!='verified':continue
        if not state['start']<=day<state['end_exclusive']:raise ValueError('Day outside frozen range')
        name='BTCUSDT-metrics-'+day+'.zip';stats,rows=audit_metrics_zip((run/'raw'/name).read_bytes(),(run/'raw'/(name+'.CHECKSUM')).read_bytes(),day)
        labels=sorted(datetime.fromisoformat(r['create_time']) for r in rows)
        grid=[datetime.fromisoformat(day)+timedelta(minutes=5*i) for i in range(288)]
        stats.pop('label_times',None);stats.update(status='verified',sorted5m_label_grid_complete=labels==grid,publication_certified=False)
        if stats!=prior:raise ValueError('Regenerated day summary differs from checkpoint')
        if any(int(k)<0 for k in stats['label_spacing_seconds']):backward.append(day)
        if stats['duplicate_labels']:duplicates.append(day)
        if labels!=grid:incomplete.append(day)
    return dict(coverage=coverage_summary(state),raw_body_hashes=file_hashes,raw_backward_order_days=backward,duplicate_label_days=duplicates,incomplete_label_grid_days=incomplete,integrity_recheck_passed=True,new_http_requests=0,pnl_tests=0,available_at_certified=False)


def main():
    run=ROOT/'data/binance-metrics/BTCUSDT-2023-2026'
    with (run/'collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        out=ROOT/'artifacts/BTC-DERIVATIVES-COLLECT-010/rechecks'/stamp;out.mkdir(parents=True,exist_ok=False)
        sources=['tools/recheck_binance_metrics.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/archive_collection.py','src/miniquant/data/okx_public.py']
        manifest=dict(protocol_sha256=hashlib.sha256((ROOT/'research/audits/BTC-DERIVATIVES-RECHECK-011.json').read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources})
        for n in sources:
            dest=out/'source_snapshot'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/n).read_bytes())
        save_json(out/'manifest.json',manifest);result=recheck(run);save_json(out/'summary.json',result)
        print(json.dumps(dict(report=str(out.relative_to(ROOT)),coverage=result['coverage'],verified_raw_bodies=len(result['raw_body_hashes']),raw_backward_order_days=len(result['raw_backward_order_days'])),indent=2))

if __name__=='__main__':main()
