"""Describe a frozen public BTC snapshot, without signals or strategy PnL."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import atomic_json
from miniquant.data.okx_public import utc


def describe(bars, ticker):
    result = {"kind":"descriptive_exploration_not_alpha_test", "ticker":ticker,
              "windows":[], "selection_note":"PM selected BTC after observing recent range; these windows are already known exploratory data."}
    for count in (7,30,90):
        sample=bars[-count:]
        if len(sample)!=count:
            continue
        if any(b["open_time_ms"]-a["open_time_ms"]!=86_400_000 for a,b in zip(sample,sample[1:])):
            raise ValueError("Cannot describe a gapped daily window as consecutive days")
        first,last=float(sample[0]["close"]),float(sample[-1]["close"])
        low=min(float(r["low"]) for r in sample)
        high=max(float(r["high"]) for r in sample)
        result["windows"].append({"completed_daily_bars":count,
            "start_open_utc":utc(sample[0]["open_time_ms"]),"end_exclusive_utc":utc(sample[-1]["end_time_ms"]),
            "min_low":low,"max_high":high,"first_close":first,"last_close":last,
            "first_to_last_close_change_pct":100*(last/first-1),
            "close_return_span_intervals":count-1,
            "note":"Close-to-close change spans N-1 intervals; high/low range covers all N bars. No reversion probability inferred."})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",required=True,type=Path)
    args=parser.parse_args()
    run=args.run.resolve()
    raw=(run/"trade_BTC-USDT_1Dutc.json").read_bytes()
    bars=json.loads(raw)
    coverage=json.loads((run/"coverage.json").read_text())
    job=next(j for j in coverage["jobs"] if j["id"]=="trade_BTC-USDT_1Dutc")
    if job["conflicting_revisions"] or job["status"]=="collecting":
        raise ValueError("BTC daily audit incomplete or conflicting")
    result=describe(bars,coverage["snapshot"]["ticker"])
    result["source_run"]=str(run.relative_to(ROOT))
    result["normalized_file_sha256"]=hashlib.sha256(raw).hexdigest()
    atomic_json(run/"btc_range_observation.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
