"""Instrument one unchanged frozen collector invocation; never store exception messages."""
from pathlib import Path
import hashlib,json,runpy,ssl,sys
from urllib.error import URLError
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.archive_collection import save_json
COLLECTOR_SOURCE=str(ROOT/'src/miniquant/data/archive_collection.py')


def observe(call):
    if sys.gettrace() is not None:raise RuntimeError('Existing tracer; do not replace it')
    events=[]
    def trace(frame,event,arg):
        if frame.f_code.co_filename!=COLLECTOR_SOURCE:return None
        if event=='exception' and len(events)<1000:
            exc=arg[1]
            if isinstance(exc,(URLError,OSError)):
                reason=exc.reason if isinstance(exc,URLError) else exc
                record=dict(exception_type=type(exc).__name__,reason_type=type(reason).__name__)
                for name in ('errno','verify_code'):
                    value=getattr(reason,name,None)
                    if type(value) is int:record[name]=value
                events.append(record)
        return trace
    sys.settrace(trace)
    try:result=call()
    finally:sys.settrace(None)
    return result,events


def main():
    out=ROOT/'artifacts/BTC-ARCHIVE-TRANSPORT-012';out.mkdir(parents=True,exist_ok=False)
    names=['tools/observe_archive_transport.py','tools/collect_binance_metrics.py','src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']
    protocol=ROOT/'research/audits/BTC-ARCHIVE-TRANSPORT-012.json'
    manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},inputs={})
    for n in names:
        dest=out/'source_snapshot'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/n).read_bytes())
    prior=ROOT/'data/binance-metrics/BTCUSDT-2023-2026/checkpoint.json';copy=out/'parent-checkpoint.json';copy.write_bytes(prior.read_bytes());manifest['inputs'][str(copy.relative_to(ROOT))]=hashlib.sha256(copy.read_bytes()).hexdigest();save_json(out/'manifest.json',manifest)
    old=sys.argv[:]
    try:
        sys.argv=['tools/collect_binance_metrics.py','--request-budget','100']
        _,events=observe(lambda:runpy.run_path(str(ROOT/'tools/collect_binance_metrics.py'),run_name='__main__'))
        save_json(out/'transport-events.json',dict(events=events,exception_messages_saved=False,collector_source_modified=False,extra_network_requests=0))
    finally:sys.argv=old
    print('Transport observation saved',len(events))

if __name__=='__main__':main()
