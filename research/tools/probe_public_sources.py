"""Small, unsigned GET-only availability audit. No credentials or orders.

Writes raw public responses under ignored data/source-audit/. A successful
sample does not establish full history, continuity, licensing or entitlement.
"""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "source-audit"
URLS = {
    "okx_spot": "https://www.okx.com/api/v5/public/instruments?instType=SPOT",
    "okx_swap": "https://www.okx.com/api/v5/public/instruments?instType=SWAP",
    "okx_futures": "https://www.okx.com/api/v5/public/instruments?instType=FUTURES",
    "okx_daily": "https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1Dutc&limit=3",
    "okx_eth_4h": "https://www.okx.com/api/v5/market/history-candles?instId=ETH-USDT&bar=4H&limit=3",
    "okx_sol_4h": "https://www.okx.com/api/v5/market/history-candles?instId=SOL-USDT-SWAP&bar=4H&limit=3",
    "okx_btc_2020": "https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1Dutc&after=1578096000000&limit=3",
    "okx_aapl": "https://www.okx.com/api/v5/market/history-candles?instId=AAPL-USDT-SWAP&bar=1Dutc&limit=3",
    "okx_xaapl": "https://www.okx.com/api/v5/market/history-candles?instId=XAAPL-USDT&bar=1Dutc&limit=3",
    "okx_funding": "https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=3",
    "okx_oi": "https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP",
    "okx_book": "https://www.okx.com/api/v5/market/books?instId=BTC-USDT&sz=5",
    "okx_mark": "https://www.okx.com/api/v5/public/mark-price?instType=SWAP&instId=BTC-USDT-SWAP",
    "okx_index": "https://www.okx.com/api/v5/market/index-tickers?instId=BTC-USDT",
    "binance_spot": "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=3",
    "binance_funding": "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=3",
    "binance_archive_checksum": "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2025-01.zip.CHECKSUM",
    "bybit_oi": "https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1d&limit=3",
    "coinbase_daily": "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2025-01-01&end=2025-01-03",
    "coinmetrics": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD&frequency=1d&page_size=2&start_time=2025-01-01&end_time=2025-01-03",
}


def probe(item):
    name, url = item
    result = {"id": name, "url": url,
              "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "PersonalMiniQuantResearch/0.1"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            result["http_status"] = response.status
        result["sha256"] = hashlib.sha256(raw).hexdigest()
        (OUT / (name + ".raw")).write_bytes(raw)
        if name.endswith("checksum"):
            result["checksum_text"] = raw.decode().strip()
            result["status"] = "checksum_retrieved_not_archive_verified"
            return result
        data = json.loads(raw)
        result["api_code"] = data.get("code", data.get("retCode")) if isinstance(data, dict) else None
        records = data.get("data", data.get("result", {}).get("list", [])) if isinstance(data, dict) else data
        result["records"] = len(records)
        result["status"] = "sample_retrieved" if records and result["api_code"] in (None, "0", 0) else "empty_or_api_error"
        if name in ("okx_spot", "okx_swap", "okx_futures"):
            wanted = ("BTC-", "ETH-", "SOL-", "AAPL-", "XAAPL-", "TSLA-", "NVDA-", "QQQ-", "SPY-")
            result["selected_instruments"] = [
                {key: row.get(key) for key in ("instId", "instType", "state", "listTime", "expTime", "ctVal", "ctValCcy")}
                for row in records if row["instId"].startswith(wanted)
            ]
        elif records and isinstance(records[0], list):
            result["sample_timestamps"] = [row[0] for row in records]
        elif records:
            result["sample_fields"] = sorted(records[0])
    except urllib.error.HTTPError as error:
        result.update(http_status=error.code, status="http_error", error=str(error))
    except Exception as error:
        result.update(status="failed", error=str(error))
    return result


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(probe, URLS.items()))
    path = OUT / "audit-results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    for row in results:
        print(row["id"], row["status"], row.get("http_status"), row.get("records", ""))
    print("Evidence:", path)
