"""Bounded public-data audit. No credentials, account calls or orders.

python3.11 tools/okx_market_audit.py [--resume RUN_DIRECTORY] [--page-budget 120]
Raw pages/checkpoints/data stay under ignored data/market-audit/.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from miniquant.data.okx_public import PublicClient, DataError, candle, funding, coverage, digest, utc, INTERVALS


def atomic_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def page_payload(envelope):
    if digest(envelope["body_text"]) != envelope["body_sha256"]:
        raise DataError("raw_page_checksum_mismatch")
    return json.loads(envelope["body_text"])["data"]


def normalize_page(envelope, job):
    payload = page_payload(envelope)
    rows = []
    for row in payload:
        if job["kind"] == "funding":
            rows.append(funding(row, job["inst_id"], envelope["ingested_at_ms"], envelope["body_sha256"]))
        else:
            rows.append(candle(row, job["kind"], job["inst_id"], job["bar"], envelope["ingested_at_ms"], envelope["body_sha256"]))
    return rows


def advance(envelope, job):
    """Validate entire page before committing a cursor. Never advance on malformed rows."""
    rows = normalize_page(envelope, job)
    if not rows:
        return None, "source_empty_boundary"
    key = "event_time_ms" if job["kind"] == "funding" else "open_time_ms"
    oldest = min(r[key] for r in rows)
    if oldest >= job["cursor"]:
        raise DataError("pagination_did_not_move_backwards")
    return oldest, "requested_start_reached" if oldest <= job["start"] else None


def build_jobs(end):
    start = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
    jobs = []
    def add(kind, inst, bar, begin, stop):
        jobs.append({"id": f"{kind}_{inst}_{bar or 'events'}", "kind": kind, "inst_id": inst,
                     "bar": bar, "start": begin, "end": stop, "cursor": stop,
                     "pages": [], "status": "collecting"})
    daily_end = end // INTERVALS["1Dutc"] * INTERVALS["1Dutc"]
    four_end = end // INTERVALS["4H"] * INTERVALS["4H"]
    for coin in ("BTC", "ETH", "SOL"):
        for suffix in ("-USDT", "-USDT-SWAP"):
            add("trade", coin+suffix, "1Dutc", start, daily_end)
        add("mark", coin+"-USDT-SWAP", "1Dutc", daily_end-90*86_400_000, daily_end)
        add("index", coin+"-USDT", "1Dutc", daily_end-90*86_400_000, daily_end)
        add("funding", coin+"-USDT-SWAP", None, start, end)
    add("trade", "BTC-USDT", "4H", four_end-180*86_400_000, four_end)
    return jobs


def collect(run, state, client, budget):
    used = 0
    for job in state["jobs"]:
        if job["status"] != "collecting":
            continue
        while used < budget:
            params = {"instId": job["inst_id"], "after": str(job["cursor"]),
                      "limit": "300" if job["kind"] == "trade" else "100"}
            if job["bar"]:
                params["bar"] = job["bar"]
            try:
                envelope = client.get(job["kind"], params)
                used += 1
                filename = "raw/" + uuid.uuid4().hex + ".json"
                atomic_json(run / filename, envelope)
                # A crash before checkpointing leaves an orphan raw page, never a skipped cursor.
                oldest, terminal = advance(envelope, job)
                job["pages"].append(filename)
                if oldest is not None:
                    job["cursor"] = oldest
                if terminal:
                    job["status"] = terminal
                job.pop("last_error", None)
                atomic_json(run / "checkpoint.json", state)
                print(job["id"], len(page_payload(envelope)), job["status"], flush=True)
                if terminal:
                    break
            except DataError as exc:
                job["last_error"] = str(exc)
                atomic_json(run / "checkpoint.json", state)
                print(job["id"], str(exc), flush=True)
                break
        if used >= budget:
            break
    return used


def summarize(run, state):
    report = {"schema_version": 1, "observed_at": utc(int(time.time()*1000)),
              "source": "OKX unsigned public market; not demo fills", "run": str(run.relative_to(ROOT)),
              "snapshot": state["snapshot"], "jobs": [], "limitations": [
                  "Current instrument metadata is not historical point-in-time metadata",
                  "Raw historical publication times unknown; no signal PnL evaluated",
                  "Pre-2020 data and listing boundary inference not certified",
                  "Funding completeness needs schedule history; missing funding never filled with zero",
                  "Checkpoint resume implemented; continuous scheduling/alerts/incremental merge not implemented"]}
    for job in state["jobs"]:
        records = []
        for name in job["pages"]:
            records.extend(normalize_page(json.loads((run/name).read_text()), job))
        stats, normalized = coverage(records, job["kind"], job["bar"], job["start"], job["end"])
        item = {k: job[k] for k in ("id", "kind", "inst_id", "bar", "status")}
        item.update(stats)
        if "last_error" in job:
            item["last_error"] = job["last_error"]
        report["jobs"].append(item)
        atomic_json(run / (job["id"] + ".json"), normalized)
    atomic_json(run / "coverage.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--page-budget", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.page_budget <= 500:
        parser.error("page-budget must be 1..500")
    base = ROOT/"data"/"market-audit"
    client = PublicClient()
    if args.resume:
        run = args.resume.resolve()
        if run.parent != base.resolve():
            parser.error("resume directory must be an immediate child of data/market-audit")
        state = json.loads((run/"checkpoint.json").read_text())
    else:
        run = base / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        (run/"raw").mkdir(parents=True)
        snapshot = {}
        for kind, params in (("time", {}), ("ticker", {"instId": "BTC-USDT"}),
                             ("instruments", {"instType": "SPOT"}), ("instruments", {"instType": "SWAP"})):
            envelope = client.get(kind, params)
            name = kind + params.get("instType", "")
            atomic_json(run/(name+".json"), envelope)
            rows = page_payload(envelope)
            snapshot[name] = rows if kind != "instruments" else [r for r in rows if r.get("instId") in {c+s for c in ("BTC","ETH","SOL") for s in ("-USDT","-USDT-SWAP")}]
        server_ms = int(snapshot["time"][0]["ts"])
        ticker_ms = int(snapshot["ticker"][0]["ts"])
        snapshot["server_local_skew_ms"] = server_ms-int(time.time()*1000)
        snapshot["ticker_age_from_server_ms"] = server_ms-ticker_ms
        if abs(snapshot["server_local_skew_ms"]) > 60_000 or abs(server_ms-ticker_ms) > 60_000:
            raise DataError("clock_or_ticker_stale")
        state = {"schema_version": 1, "snapshot": snapshot, "jobs": build_jobs(server_ms)}
        atomic_json(run/"checkpoint.json", state)
    print("Run:", run, flush=True)
    used = collect(run, state, client, args.page_budget)
    report = summarize(run, state)
    print("Pages this invocation:", used)
    print("Coverage:", run/"coverage.json")
    for job in report["jobs"]:
        print(job["id"], "records", job["records"], "missing", job.get("missing_records", "schedule_unknown"), "status", job["status"])
    return 0 if all(j["status"] != "collecting" for j in state["jobs"]) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DataError as exc:
        print("Audit stopped:", exc)
        raise SystemExit(1)
