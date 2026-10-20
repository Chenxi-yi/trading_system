import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from miniquant.data.okx_public import DataError, PublicClient, candle, funding, coverage, INTERVALS
from tools.okx_market_audit import advance, collect, summarize, atomic_json

DAY = INTERVALS["1Dutc"]
ROW = [str(DAY), "100", "110", "90", "105", "10", "1050", "1050", "1"]


def envelope(rows):
    text = json.dumps({"code": "0", "data": rows})
    return {"body_text": text, "body_sha256": hashlib.sha256(text.encode()).hexdigest(), "ingested_at_ms": 10*DAY}


class MarketDataTests(unittest.TestCase):
    def test_unknown_publication_time_and_contract_units(self):
        row = candle(ROW, "trade", "BTC-USDT-SWAP", "1Dutc", 3*DAY, "hash")
        self.assertIsNone(row["available_at"])
        self.assertEqual(row["volume_unit"], "contracts")
        self.assertEqual(row["end_time_ms"], 2*DAY)

    def test_rejects_malformed_and_future_completed_bars(self):
        for index, value in ((1,"NaN"), (2,"99"), (3,"106"), (5,"-1"), (8,"unknown"), (0,str(DAY+1))):
            bad = ROW.copy(); bad[index] = value
            with self.assertRaises(DataError):
                candle(bad,"trade","BTC-USDT","1Dutc",3*DAY,"hash")
        with self.assertRaises(DataError):
            candle(ROW,"trade","BTC-USDT","1Dutc",DAY+100,"hash")

    def test_coverage_counts_holes_conflicts_and_incomplete(self):
        a = candle(ROW,"trade","BTC-USDT","1Dutc",5*DAY,"hash")
        b = {**a,"open_time_ms":3*DAY}
        unfinished = {**a,"open_time_ms":4*DAY,"complete":False}
        changed = {**a,"close":"106"}
        stats, rows = coverage([a,a,b,unfinished,changed],"trade","1Dutc",DAY,5*DAY)
        self.assertEqual(stats["records"],2)
        self.assertEqual(stats["missing_records"],2)
        self.assertEqual(stats["internal_missing_records"],1)
        self.assertEqual(stats["conflicting_revisions"],1)
        self.assertEqual(stats["incomplete_excluded"],1)
        self.assertFalse(stats["window_complete"])
        self.assertFalse(stats["research_ready"])

    def test_unknown_realized_funding_not_predicted_or_zero(self):
        r = funding({"instId":"BTC-USDT-SWAP","fundingTime":str(DAY),"fundingRate":"0.0001","realizedRate":""},"BTC-USDT-SWAP",3*DAY,"hash")
        self.assertIsNone(r["realized_rate"])
        stats,_ = coverage([r],"funding",None,0,3*DAY)
        self.assertEqual(stats["unknown_realized_rates"],1)
        self.assertIsNone(stats["missing_event_count"])
        with self.assertRaises(DataError):
            funding({"instId":"OTHER"},"BTC-USDT-SWAP",3*DAY,"hash")

    def test_pagination_does_not_skip_bad_page_or_loop(self):
        job={"kind":"trade","inst_id":"BTC-USDT","bar":"1Dutc","cursor":3*DAY,"start":0}
        cursor,status=advance(envelope([ROW]),job)
        self.assertEqual(cursor,DAY)
        self.assertIsNone(status)
        with self.assertRaises(DataError):
            advance(envelope([ROW]),{**job,"cursor":DAY})
        bad = envelope([ROW]);bad["body_text"] += " "
        with self.assertRaises(DataError): advance(bad,job)

    def test_checkpoint_restart_retries_same_uncommitted_cursor(self):
        class Fake:
            def __init__(self, fail=False): self.fail=fail; self.cursors=[]
            def get(self,kind,params):
                self.cursors.append(params["after"])
                if self.fail: raise DataError("network_failure")
                return envelope([ROW]) if int(params["after"])>DAY else envelope([])
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/"raw").mkdir()
            job={"id":"test","kind":"trade","inst_id":"BTC-USDT","bar":"1Dutc","cursor":3*DAY,"start":0,"end":3*DAY,"pages":[],"status":"collecting"}
            state={"jobs":[job]}
            first=Fake(True);collect(run,state,first,1)
            restored=json.loads((run/"checkpoint.json").read_text())
            self.assertEqual(restored["jobs"][0]["cursor"],3*DAY)
            second=Fake();collect(run,restored,second,1)
            third=Fake();collect(run,restored,third,1)
            self.assertEqual(second.cursors,[str(3*DAY)])
            self.assertEqual(third.cursors,[str(DAY)])
            self.assertEqual(restored["jobs"][0]["status"],"source_empty_boundary")

    def test_account_and_order_paths_rejected_before_network(self):
        client=PublicClient()
        for kind,params in (("orders",{}),("trade",{"apiKey":"never_send"}),("balance",{})):
            with self.assertRaises(DataError):client.get(kind,params)


if __name__ == "__main__": unittest.main()
