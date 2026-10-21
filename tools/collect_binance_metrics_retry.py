"""Independent retry-v2 lineage. Original010 files remain unchanged and locally preserved."""
from pathlib import Path
import argparse,fcntl,hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.archive_collection import MetricsFetcher,coverage_summary,save_json
from miniquant.data.archive_retry import collect_retry_chunk
from tools.recheck_binance_metrics import recheck


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request-budget',type=int,default=100);args=parser.parse_args()
    if not 0<args.request_budget<=100:raise ValueError('Budget outside protocol')
    cfgpath=ROOT/'research/audits/BTC-DERIVATIVES-COLLECT-013.json';cfg=json.loads(cfgpath.read_text());run=ROOT/cfg['new_root'];parent=ROOT/cfg['parent_root'];art=ROOT/'artifacts/BTC-DERIVATIVES-COLLECT-013'
    names=['tools/collect_binance_metrics_retry.py','src/miniquant/data/archive_retry.py','tools/recheck_binance_metrics.py','src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']
    fingerprint=dict(protocol_sha256=hashlib.sha256(cfgpath.read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names})
    # The parent lock prevents a simultaneous old writer during import. The new lock
    # prevents duplicate retry-v2 writers; neither lock modifies market data.
    with (parent/'collector.lock').open('a') as parent_lock:
        fcntl.flock(parent_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not (run/'checkpoint.json').exists():
            if run.exists() or art.exists():raise ValueError('Partial import requires review; do not overwrite')
            audit=recheck(parent);state=json.loads((parent/'checkpoint.json').read_text())
            if state['start']!=cfg['start'] or state['end_exclusive']!=cfg['end_exclusive']:raise ValueError('Parent date range mismatch')
            if state.get('blocked_reason'):raise ValueError('Parent integrity/access block requires review')
            run.mkdir(parents=True);art.mkdir(parents=True)
            raw=run/'raw';raw.mkdir();copied={}
            for p in sorted((parent/'raw').iterdir()):
                if p.suffix=='.tmp':continue
                if not p.is_file() or p.is_symlink():raise ValueError('Only regular parent raw files')
                dest=raw/p.name;shutil.copyfile(p,dest);digest=hashlib.sha256(dest.read_bytes()).hexdigest()
                if digest!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('Parent copy differs')
                copied[str(dest.relative_to(ROOT))]=digest
            parent_copy=art/'parent-checkpoint.json';parent_copy.write_bytes((parent/'checkpoint.json').read_bytes());save_json(art/'import-audit.json',audit);save_json(art/'imported-body-manifest.json',copied)
            state.update(fingerprint=fingerprint,parent_lineage='BTC-DERIVATIVES-COLLECT-010',imported_day_states=len(state['days']),imported_request_attempts=state['total_request_attempts'])
            state['inherited_last_error']=state.pop('last_error',None) # Kept in copied parent and here; never labeled a new successful request.
            # Inherit retry_after_epoch without clearing it: a new lineage is not a way around backoff.
            manifest=dict(fingerprint,inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [parent_copy,art/'import-audit.json',art/'imported-body-manifest.json']})
            for n in names:
                dest=art/'source_snapshot'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/n).read_bytes())
            save_json(art/'manifest.json',manifest);save_json(run/'checkpoint.json',state)
            recheck(run)
        else:
            state=json.loads((run/'checkpoint.json').read_text())
            if state['fingerprint']!=fingerprint:raise ValueError('Frozen retry-v2 source changed')
            manifest=json.loads((art/'manifest.json').read_text())
            for p,digest in manifest['inputs'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest:raise ValueError('Immutable parent provenance changed')
        with (run/'collector.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=collect_retry_chunk(run,state,MetricsFetcher(),args.request_budget)
            report=coverage_summary(state);save_json(run/'coverage.json',report)
            print(json.dumps(dict(run_result=result,coverage=report,new_lineage=True,parent_source_modified=False),indent=2),flush=True)

if __name__=='__main__':main()
