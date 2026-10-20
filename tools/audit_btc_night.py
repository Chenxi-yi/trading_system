"""Read-only audit of preserved bars/results; no strategy selection or new trials."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from miniquant.backtest.replay import aggregate, HOUR
from miniquant.research.validation import daily_returns
from tools.okx_market_audit import atomic_json
from tools.run_btc_night import load_bars


def main():
    source = ROOT / 'data/market-audit/btc-overnight-20261021'
    spot = ROOT / 'artifacts/BTC-NIGHT-001'
    perp = ROOT / 'artifacts/BTC-NIGHT-001-PERP'
    hourly = load_bars(source / 'trade_BTC-USDT_1H.json')
    agg = {b['ts']: b for b in aggregate(hourly, 4 * HOUR)}
    native = load_bars(source / 'trade_BTC-USDT_4H.json')
    differences = []
    for b in native:
        if b['ts'] not in agg:
            continue
        fields = {k: dict(hourly=agg[b['ts']][k], native=b[k]) for k in ('o', 'h', 'l', 'c') if abs(agg[b['ts']][k] - b[k]) > 0.100001}
        if fields:
            differences.append(dict(ts=b['ts'], utc=datetime.fromtimestamp(b['ts']/1000, timezone.utc).isoformat(), fields=fields))
    zero = {}
    ledger_checks = []
    for directory, data_name, is_perp in [(spot, 'trade_BTC-USDT_1H.json', False), (perp, 'trade_BTC-USDT-SWAP_4H.json', True)]:
        bars = json.loads((source / data_name).read_text())
        zero_times = {x['open_time_ms'] for x in bars if float(x['volume']) == 0}
        hits = []
        bytime = {x['open_time_ms']: x for x in bars}
        for file in sorted((directory / 'runs').glob('*.json')):
            value = json.loads(file.read_text())
            if isinstance(value, list):
                # Spot fills are stored next to their metrics; audit once per run.
                continue
            fills = value['fills'] if is_perp else json.loads(file.with_name(file.stem + '.fills.json').read_text())
            hits.extend(dict(run=file.name, ts=f['ts'], reason=f.get('reason')) for f in fills if f['ts'] in zero_times)
            if is_perp:
                cash = 10000 + sum(f.get('realized_pnl', 0) - f['fee'] for f in fills) + sum(f['pnl'] for f in value['funding_events'])
                error = abs(cash - value['daily'][-1]['nav'])
                funding_error = max((abs(f['pnl'] + f['quantity'] * f['mark'] * f['rate']) for f in value['funding_events']), default=0)
                # Funding is applied before all orders at exactly the same boundary.
                position_error = max((abs(f['quantity'] - sum(v['quantity'] * (1 if v['side'] == 'buy' else -1) for v in fills if v['ts'] < f['ts'])) for f in value['funding_events']), default=0)
                ledger_checks.append(dict(run=str(file.relative_to(ROOT)), nav_error=error, funding_formula_error=funding_error, funding_position_error=position_error))
            else:
                cash, qty = 10000.0, 0.0
                for f in fills:
                    if f['side'] == 'buy':
                        cash -= f['notional']; qty += f['quantity']
                    else:
                        cash += f['notional'] - f['fee']; qty -= f['quantity']
                    if cash < -1e-7 or qty < -1e-10:
                        raise ValueError('Cached spot ledger violates finite cash/inventory')
                end = int(datetime.fromisoformat(value['end']).replace(tzinfo=timezone.utc).timestamp()*1000)
                px = float(bytime[end - HOUR]['close'])
                error = abs(cash + qty * px - value['daily'][-1]['nav'])
                fee_error = abs(sum(f['fee'] for f in fills) - value['fees'])
                ledger_checks.append(dict(run=str(file.relative_to(ROOT)), nav_error=error, fee_sum_error=fee_error))
        zero[data_name] = dict(zero_volume_count=len(zero_times), zero_volume_timestamps=sorted(zero_times), cached_fills_at_zero_volume=hits)
    source_checks = []
    for directory, key in [(spot, 'code_hashes'), (perp, 'code')]:
        manifest = json.loads((directory / 'manifest.json').read_text())
        for name, expected in manifest[key].items():
            snapshot = directory / 'source_snapshot' / name
            source_checks.append(dict(path=str(snapshot.relative_to(ROOT)), matches=hashlib.sha256(snapshot.read_bytes()).hexdigest() == expected))
    summary = json.loads((spot / 'summary.json').read_text())
    families = {k:v for k,v in summary['families'].items() if 'daily_walk_forward' in v}
    families['breakout'] = json.loads((perp / 'summary.json').read_text())
    names = list(families)
    arrays = [daily_returns(families[k]['daily_walk_forward']) for k in names]
    timestamps = [[r['ts'] for r in families[k]['daily_walk_forward']] for k in names]
    if any(t != timestamps[0] for t in timestamps):
        raise ValueError('Return correlation requires identical time windows')
    output = dict(updated_at=datetime.now(timezone.utc).isoformat(), no_new_strategy_trials=True,
                  aggregation_differences=differences, zero_volume_audit=zero,
                  cached_ledger_audits=ledger_checks, source_snapshot_audits=source_checks,
                  correlation=dict(names=names, daily_net_pearson=np.corrcoef(arrays).tolist()),
                  notes=['No-price-gap coverage does not certify uninterrupted trading or executable quotes.',
                         'Zero-volume bars must not be treated as demonstrated liquidity. No audited cached fill falls on those bars.',
                         'Observed Dec2022 discrepancies remain unresolved; the exact outage cause was not established from primary sources.',
                         'Existing results remain rejected/insufficient. No sample or parameter selection was altered.',
                         'Original perpetual fingerprint omitted imported replay/validation dependencies; this limits original provenance completeness.'])
    if any(not x['matches'] for x in source_checks) or any(x['nav_error'] > 1e-6 or x.get('funding_position_error', 0) > 1e-9 for x in ledger_checks):
        raise ValueError('Preserved result/source consistency audit failed')
    atomic_json(spot / 'continuation-audit.json', output)
    print(json.dumps(dict(aggregation_differences=len(differences), cached_runs=len(ledger_checks), zero_volume_fills=sum(len(x['cached_fills_at_zero_volume']) for x in zero.values()), snapshot_files=len(source_checks), max_nav_error=max(x['nav_error'] for x in ledger_checks)), indent=2))


if __name__ == '__main__':
    main()
