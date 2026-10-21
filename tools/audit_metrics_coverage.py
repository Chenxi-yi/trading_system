"""Full frozen corpus audit. Labels remain uncertified observation-time proxies."""
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
from collections import Counter
import fcntl,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.archive_collection import save_json
from miniquant.data.binance_metrics import audit_metrics_zip,FIELDS
from tools.recheck_binance_metrics import recheck


def label_quality(day,rows):
    labels=[datetime.fromisoformat(r['create_time']) for r in rows];expected={datetime.fromisoformat(day)+timedelta(minutes=5*i) for i in range(288)}
    return dict(missing_labels=[str(x) for x in sorted(expected-set(labels))],outside_labels=[str(x) for x in sorted(set(labels)-expected)],duplicate_labels=len(labels)-len(set(labels)),raw_backward_steps=sum(b<a for a,b in zip(labels,labels[1:])))


def audit(run,prior_probe_root=None):
    verified=recheck(run);state=json.loads((run/'checkpoint.json').read_text());gaps={};outside={};backward={};owners={};cross_duplicates=0;zeros=Counter();wholly_missing={}
    for day,stats in sorted(state['days'].items()):
        if stats['status']!='verified':continue
        name='BTCUSDT-metrics-'+day+'.zip';_,rows=audit_metrics_zip((run/'raw'/name).read_bytes(),(run/'raw'/(name+'.CHECKSUM')).read_bytes(),day);q=label_quality(day,rows)
        if q['missing_labels']:gaps[day]=q['missing_labels']
        if q['outside_labels']:outside[day]=q['outside_labels']
        if q['raw_backward_steps']:backward[day]=q['raw_backward_steps']
        fields=[k for k,n in stats['unknown_values'].items() if n==stats['rows']]
        if fields:wholly_missing[day]=fields
        for row in rows:
            label=datetime.fromisoformat(row['create_time']);prior=owners.get(label)
            if prior is not None and prior!=day:cross_duplicates+=1
            owners[label]=day
            for key in FIELDS-{'create_time','symbol'}:
                try:value=Decimal(row[key])
                except (InvalidOperation,ValueError,TypeError):continue
                if value.is_finite() and value==0:zeros[key]+=1
    probes={}
    if prior_probe_root is not None:
        for day in ['2024-01-01','2026-06-24','2026-06-25','2026-09-30']:
            name='BTCUSDT-metrics-'+day+'.zip';new=(run/'raw'/name).read_bytes();old=(prior_probe_root/name).read_bytes();probes[day]=dict(prior_sha256=hashlib.sha256(old).hexdigest(),current_sha256=hashlib.sha256(new).hexdigest(),exact_bytes_match=new==old)
    return dict(coverage=verified['coverage'],raw_bodies_rechecked=len(verified['raw_body_hashes']),expected_label_rows=verified['coverage']['expected_days']*288,unique_label_timestamps=len(owners),missing_labels_by_day=gaps,total_missing_labels=sum(map(len,gaps.values())),outside_labels_by_day=outside,cross_file_duplicate_labels=cross_duplicates,raw_backward_steps_by_day=backward,numeric_zero_counts=dict(zeros),wholly_missing_fields_by_day=wholly_missing,prior_probe_comparison=probes,labels_are_available_at=False,units_certified=False,pnl_tests=0,imputed_rows=0)


def main():
    run=ROOT/'data/binance-metrics/BTCUSDT-2023-2026-retry-v2';out=ROOT/'artifacts/BTC-DERIVATIVES-COVERAGE-014'
    with (run/'collector.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);state=json.loads((run/'checkpoint.json').read_text())
        if not state.get('collection_complete'):raise ValueError('Expected completed collection before final corpus freeze')
        out.mkdir(parents=True,exist_ok=False)
        files={}
        for p in sorted((run/'raw').iterdir()):
            if not p.is_file() or p.is_symlink():raise ValueError('Only regular corpus files')
            files[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        save_json(out/'dataset-file-manifest.json',files)
        names=['tools/audit_metrics_coverage.py','tools/recheck_binance_metrics.py','src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']
        inputs=[out/'dataset-file-manifest.json',run/'checkpoint.json',ROOT/'artifacts/BTC-DERIVATIVES-COLLECT-013/manifest.json']
        probe=ROOT/'artifacts/BTC-DERIVATIVES-DATA-009'
        inputs.extend(probe/('BTCUSDT-metrics-'+d+'.zip') for d in ['2024-01-01','2026-06-24','2026-06-25','2026-09-30'])
        manifest=dict(protocol_sha256=hashlib.sha256((ROOT/'research/audits/BTC-DERIVATIVES-COVERAGE-014.json').read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
        for n in names:
            p=out/'source_snapshot'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
        save_json(out/'manifest.json',manifest);report=audit(run,probe);save_json(out/'summary.json',report)
        print(json.dumps({k:report[k] for k in ['coverage','raw_bodies_rechecked','total_missing_labels','cross_file_duplicate_labels','raw_backward_steps_by_day','numeric_zero_counts','wholly_missing_fields_by_day','prior_probe_comparison']},indent=2))

if __name__=='__main__':main()
