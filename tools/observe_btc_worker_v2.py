"""040 startup fix: freeze executed dependency closure, not mutable SRC namespace.

039 runtime remains byte-for-byte intact; explicit freeze provider changes only
provenance admission. No extra request/credential/order permissions.
"""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import observe_btc_worker as worker


def inherited_code(parent,new):
    overlap=set(parent)&set(new)
    if overlap:raise ValueError('Cannot override a frozen parent file')
    return dict(parent,**new)


def freeze_v2():
    protocol=ROOT/'research/audits/BTC-PUBLIC-WORKER-040.json';cfg=json.loads(protocol.read_text());parent_path=ROOT/'artifacts/BTC-PUBLIC-WORKER-039/manifest.json';parent=json.loads(parent_path.read_text())
    worker.verify_sources(parent)
    new={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('tools/observe_btc_worker_v2.py','tests/test_public_worker_v2.py')}
    inputs=dict(parent['inputs']);inputs[str(parent_path.relative_to(ROOT))]=hashlib.sha256(parent_path.read_bytes()).hexdigest()
    manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code=inherited_code(parent['code'],new),inputs=inputs)
    out=ROOT/'artifacts/BTC-PUBLIC-WORKER-040';out.mkdir(exist_ok=True);mp=out/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('040 frozen provenance changed')
    if not mp.exists():
        worker.save(mp,manifest)
        for name in list(manifest['code'])+[str(protocol.relative_to(ROOT))]:
            dest=out/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    return cfg,manifest

if __name__=='__main__':
    worker.freeze=freeze_v2
    worker.main()
