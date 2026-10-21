"""025: gate BEFORE real data loading; fixed-window risk forecast evaluation."""
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
from miniquant.research.oi_variance import samples
from miniquant.research.variance_evaluation import evaluate_when_due,EvaluationNotDue


def load_after_end(parent,schedule):
    manifest=json.loads((parent/'manifest.json').read_text())
    for name,expected in manifest['code'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise DataError('024 source changed')
    if manifest['environment']!=dict(python=sys.version.split()[0],numpy=np.__version__,platform=sys.platform):
        raise DataError('024 numerical environment changed')
    inventories=[]
    for folder in (parent/'inventories').iterdir():
        if (folder/'quality.json').exists() and (folder/'inputs.json').exists():
            inventories.append(json.loads((folder/'inputs.json').read_text()))
    if not inventories:return [],[]
    inputs=max(inventories,key=len)
    for earlier in inventories:
        if any(inputs.get(n)!=h for n,h in earlier.items()):raise DataError('Non-nested024 inventories')
    interest,books=[],[]
    for name,expected in inputs.items():
        path=ROOT/name
        if not path.resolve().is_relative_to((ROOT/'data/forward-observation/BTC').resolve()) or path.is_symlink():raise DataError('Input outside public scope')
        content=path.read_bytes()
        if hashlib.sha256(content).hexdigest()!=expected:raise DataError('024 raw hash mismatch')
        raw=json.loads(content);url=urlparse(raw['url']);query=parse_qs(url.query)
        kind='open_interest' if path.name=='oi.raw.json' else 'books'
        endpoint='/api/v5/public/open-interest' if kind=='open_interest' else '/api/v5/market/books'
        if url.scheme!='https' or url.netloc!='openapi.okx.com' or url.path!=endpoint or query.get('instId')!=['BTC-USDT-SWAP']:raise DataError('024 wrong raw endpoint')
        row=normalize_observation(kind,raw,'BTC-USDT-SWAP')
        (interest if kind=='open_interest' else books).append(row)
    rows=samples(join_snapshots(interest,books),books,schedule['start_ms'])
    predictions=[json.loads(p.read_text()) for p in sorted((parent/'predictions').glob('*.json'))]
    return rows,predictions


def main():
    parent=ROOT/'artifacts/BTC-OI-FORECAST-024'
    schedule=json.loads((parent/'activation.json').read_text())
    if schedule['end_ms']-schedule['start_ms']!=60*86_400_000:raise DataError('Window changed')
    out=ROOT/'artifacts/BTC-OI-EVALUATOR-025';out.mkdir(parents=True,exist_ok=True)
    with (out/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        names=['tools/evaluate_oi_variance.py','src/miniquant/research/variance_evaluation.py',
            'src/miniquant/research/oi_variance.py','src/miniquant/data/asof_snapshots.py',
            'src/miniquant/data/observation.py','src/miniquant/data/okx_public.py',
            'src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py']
        protocol=ROOT/'research/audits/BTC-OI-EVALUATOR-025.json'
        input_names=['artifacts/BTC-OI-FORECAST-024/manifest.json','artifacts/BTC-OI-FORECAST-024/activation.json',
                     'research/contracts/BTC_FWD_OI_RISK_001.json']
        provenance=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
            code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
            inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in input_names})
        target=out/'manifest.json'
        if target.exists():
            if json.loads(target.read_text())!=provenance:raise DataError('025 provenance changed')
        else:
            save_json(target,provenance)
            for n in names:
                saved=out/'source_snapshot'/n;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes((ROOT/n).read_bytes())
        now=int(time.time()*1000)
        try:
            if now<schedule['end_ms']:
                # The callable has not been invoked; no raw/labels/predictions read.
                result=evaluate_when_due(lambda:load_after_end(parent,schedule),schedule['start_ms'],schedule['end_ms'],now)
            elif (out/'final.json').exists():
                print('025 fixed final result already saved');return
            else:
                result=evaluate_when_due(lambda:load_after_end(parent,schedule),schedule['start_ms'],schedule['end_ms'],now)
        except EvaluationNotDue:
            result=dict(status='not_due',checked_at_ms=now,end_ms=schedule['end_ms'],
                        real_outcomes_loaded=False,real_scores_computed=False)
            save_json(out/'gate.json',result);print(json.dumps(result,indent=2));return
        save_json(out/'final.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
