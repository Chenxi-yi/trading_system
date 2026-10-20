"""Materialize only completed collector jobs from an atomic checkpoint snapshot."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import normalize_page,atomic_json
from miniquant.data.okx_public import coverage


def main():
    run=ROOT/'data/market-audit/btc-overnight-20261021'
    state=json.loads((run/'checkpoint.json').read_text())
    for job in state['jobs']:
        if job['status']=='collecting':continue
        target=run/(job['id']+'.json')
        if target.exists():continue
        rows=[]
        for name in job['pages']:rows.extend(normalize_page(json.loads((run/name).read_text()),job))
        stats,records=coverage(rows,job['kind'],job['bar'],job['start'],job['end'])
        atomic_json(target,records);atomic_json(run/(job['id']+'.coverage.json'),stats)
        print(job['id'],stats['records'],stats.get('missing_records'),flush=True)


if __name__=='__main__':main()
