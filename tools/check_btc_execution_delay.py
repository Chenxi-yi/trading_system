"""Post-result fixed-choice latency stress. No selection, tuning or account calls."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from miniquant.backtest.replay import replay
from miniquant.backtest.perpetual import replay_perpetual
from miniquant.research.validation import metrics, daily_returns
from tools.okx_market_audit import atomic_json
from tools.run_btc_night import load_bars, stamp


def main():
    spot = ROOT / 'artifacts/BTC-NIGHT-001'
    perp = ROOT / 'artifacts/BTC-NIGHT-001-PERP'
    out = spot / 'delay-audit'
    out.mkdir(exist_ok=True)
    with (out / 'audit.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cfg = ROOT / 'research/experiments/BTC-NIGHT-001-DELAY-AUDIT.json'
        plan = json.loads(cfg.read_text())
        if (out / 'summary.json').exists():
            raise ValueError('Audit already complete; preserve evidence rather than overwrite')
        bars = load_bars(ROOT / 'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json')
        pbars = load_bars(ROOT / 'data/market-audit/btc-overnight-20261021/trade_BTC-USDT-SWAP_4H.json')
        marks = load_bars(ROOT / 'data/market-audit/btc-perp-mark-20261021/mark_BTC-USDT-SWAP_4H.json')
        funding = json.loads((ROOT / 'data/funding-archive/BTC-USDT-SWAP/normalized.json').read_text())
        choices = json.loads((spot / 'sealed_choices.json').read_text())['walk_forward_choices']
        pc = json.loads((perp / 'sealed_choices.json').read_text())['walk_forward']
        # Default-path regression against every original selected WF year.
        default_checks = []
        for family, years in choices.items():
            for year, param in years.items():
                start, end = f'{year}-01-01', f'{int(year)+1}-01-01'
                value = replay(bars, family, param, stamp(start), stamp(end))
                prior = json.loads((spot / f'runs/{family}_{param}_{start}_{end}_base.json').read_text())
                default_checks.append(dict(family=family, year=year, matches=value.daily == prior['daily']))
        for year, param in pc.items():
            start, end = f'{year}-01-01', f'{int(year)+1}-01-01'
            value = replay_perpetual(pbars, marks, funding, param, stamp(start), stamp(end))
            prior = json.loads((perp / f'runs/{param}_{start}_{end}_False.json').read_text())
            default_checks.append(dict(family='breakout', year=year, matches=value['daily'] == prior['daily'] and value['fills'] == prior['fills']))
        if not all(x['matches'] for x in default_checks):
            atomic_json(out / 'regression-failure.json', default_checks)
            raise ValueError('Default replay changed; do not reinterpret preserved results')
        results = {}
        for family, years in choices.items():
            results[family] = {}
            for lag in plan['spot_execution_lag_hours']:
                rows, nav = [], 10000.0
                for year, param in sorted(years.items()):
                    start, end = f'{year}-01-01', f'{int(year)+1}-01-01'
                    value = replay(bars, family, param, stamp(start), stamp(end), execution_lag_hours=lag)
                    atomic_json(out / f'{family}_{year}_{lag}h.json', dict(daily=value.daily, fills=value.fills))
                    for row, r in zip(value.daily, daily_returns(value.daily)):
                        nav *= 1 + float(r); rows.append(dict(ts=row['ts'], nav=nav))
                results[family][f'{lag}h'] = metrics(rows)
                print(family, lag, 'completed', flush=True)
        results['breakout'] = {}
        for lag in plan['perpetual_execution_lag_4h_bars']:
            rows, nav = [], 10000.0
            for year, param in sorted(pc.items()):
                start, end = f'{year}-01-01', f'{int(year)+1}-01-01'
                value = replay_perpetual(pbars, marks, funding, param, stamp(start), stamp(end), execution_lag_bars=lag)
                atomic_json(out / f'breakout_{year}_{lag}bars.json', value)
                for row, r in zip(value['daily'], daily_returns(value['daily'])):
                    nav *= 1 + float(r); rows.append(dict(ts=row['ts'], nav=nav))
            results['breakout'][f'{lag*4}h'] = metrics(rows)
            print('breakout', lag, 'completed', flush=True)
        files = ('src/miniquant/backtest/replay.py', 'src/miniquant/backtest/perpetual.py', 'tools/check_btc_execution_delay.py')
        atomic_json(out / 'summary.json', dict(results=results, default_regression=default_checks,
                    code_hashes={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
                    protocol_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    post_sealed_exploratory_audit=True, no_strategy_selection=True,
                    note='Stress scenarios do not grant admission or new untouched OOS evidence.'))


if __name__ == '__main__':
    main()
