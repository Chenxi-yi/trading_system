"""028 approved entry: metadata guard before prospective preparation/scoring."""
from pathlib import Path
import argparse,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.research.study_gate import dispatch
from miniquant.data.archive_collection import save_json
from tools import observe_btc_master,build_btc_future_features,prepare_oi_variance,evaluate_oi_variance


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['prepare','evaluate'],default='prepare')
    args=parser.parse_args()
    out=ROOT/'artifacts/BTC-STUDY-GATE-028';out.mkdir(parents=True,exist_ok=True)
    protocol=ROOT/'research/audits/BTC-STUDY-GATE-028.json'
    names=['tools/run_oi_study.py','src/miniquant/research/study_gate.py',
           'src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']
    parent_names=[f'artifacts/{ident}/manifest.json' for ident in
        ('BTC-FUTURE-FEATURES-022','BTC-OI-FORECAST-024','BTC-OI-EVALUATOR-025','BTC-MASTER-027')]
    activation='artifacts/BTC-OI-FORECAST-024/activation.json'
    inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in parent_names+[activation]}
    provenance=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},inputs=inputs)
    manifest=out/'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())!=provenance:raise ValueError('028 frozen provenance changed')
    else:
        save_json(manifest,provenance)
        for n in names:
            saved=out/'source_snapshot'/n;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes((ROOT/n).read_bytes())
    for parent in parent_names:
        for name,expected in json.loads((ROOT/parent).read_text())['code'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Parent production source changed')
    schedule=json.loads((ROOT/activation).read_text())
    base=ROOT/'data/instrument-master/BTC-USDT-SWAP'
    def prepare():
        build_btc_future_features.main();prepare_oi_variance.main()
    result=dispatch(args.mode,int(time.time()*1000),schedule['end_ms'],observe_btc_master.main,
        lambda:json.loads((base/'latest_quality.json').read_text()),lambda:(base/'study_invalidated.json').exists(),
        prepare,evaluate_oi_variance.main)
    result['observed_at_ms']=int(time.time()*1000)
    save_json(out/'latest_action.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
