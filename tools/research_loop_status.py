"""Read-only registry/budget/provenance checks before a research-loop heartbeat."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    registry=json.loads((ROOT/'research/loop/registry.json').read_text())
    policy=json.loads((ROOT/'research/loop/policy.json').read_text())
    checkpoint=json.loads((ROOT/'research/loop/checkpoint.json').read_text())
    ids=[x['id'] for x in registry['experiments']]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate cohort IDs')
    if sum(x['alpha_candidates'] for x in registry['experiments'])!=registry['cumulative_alpha_candidates'] or sum(x['controls'] for x in registry['experiments'])!=registry['cumulative_controls']:
        raise ValueError('Cumulative trial count mismatch')
    today=datetime.now(ZoneInfo('Asia/Shanghai')).date()
    launched_today=0
    snapshots=0
    for item in registry['experiments']:
        protocol=json.loads((ROOT/item['protocol']).read_text())
        if item['id'].startswith('BTC-LOOP-'):
            if item['alpha_candidates']>policy['maximum_alpha_candidates_per_batch'] or item['controls']>policy['maximum_fixed_controls_per_batch']:
                raise ValueError('Batch exceeds declared search budget')
            date=datetime.fromisoformat(protocol['created_at']).astimezone(ZoneInfo('Asia/Shanghai')).date()
            launched_today+=date==today
            manifest=json.loads((ROOT/'artifacts'/item['id']/'manifest.json').read_text())
            expected=hashlib.sha256((ROOT/item['protocol']).read_bytes()).hexdigest()
            saved_protocol_hash=manifest.get('protocol_sha256') or manifest['inputs']['protocol']['sha256']
            if expected!=saved_protocol_hash:raise ValueError('Frozen protocol modified')
            for name,digest in manifest['code'].items():
                saved=ROOT/'artifacts'/item['id']/'source_snapshot'/name
                if hashlib.sha256(saved.read_bytes()).hexdigest()!=digest:
                    raise ValueError('Frozen source snapshot mismatch')
                snapshots+=1
    daily_limit=policy['maximum_new_batches_per_shanghai_day']
    if daily_limit is not None and launched_today>daily_limit:
        raise ValueError('Daily search budget exceeded')
    print(json.dumps(dict(cumulative_alpha_candidates=registry['cumulative_alpha_candidates'],cumulative_controls=registry['cumulative_controls'],
                          todays_new_batches=launched_today,remaining_new_batches_today=daily_limit-launched_today if daily_limit is not None else 'no_clock_pacing_limit; batch/review/evidence_limits_still_apply',
                          frozen_source_files_verified=snapshots,next_action=checkpoint['next_action'],research_qualified=checkpoint['research_qualified'],demo_ready=checkpoint['demo_ready']),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
