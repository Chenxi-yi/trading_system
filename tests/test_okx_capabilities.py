import json
import unittest
from tools.okx_capabilities import assess_usdt_only, normalize_fees, capabilities_audit


class CapabilitiesTests(unittest.TestCase):
    def test_fee_sign_and_group_matching(self):
        rows = [{"instType": "SWAP", "maker": "-9", "taker": "-9", "feeGroup": [
            {"groupId": "4", "maker": "-0.0002", "taker": "-0.0005"},
            {"groupId": "6", "maker": "0.0001", "taker": "-0.001"}]}]
        result = normalize_fees(rows, {"instType": "SWAP", "groupId": "4"})
        self.assertEqual(result["maker_cost_bps"], "2.0000")
        self.assertEqual(result["taker_cost_bps"], "5.0000")
        rebate = normalize_fees(rows, {"instType": "SWAP", "groupId": "6"})
        self.assertEqual(rebate["maker_cost_bps"], "-1.0000")
        unknown = normalize_fees(rows, {"instType": "SWAP", "groupId": "missing"})
        self.assertNotEqual(unknown["status"], "observed")
        legacy = normalize_fees([{"instType": "SWAP", "maker": "-0.001", "taker": "-0.002"}], {"instType": "SWAP"})
        self.assertNotEqual(legacy["status"], "observed")

    def test_malformed_fees_not_treated_as_zero(self):
        for value in (None, "", "NaN", "Infinity", "bad"):
            result = normalize_fees([{"instType": "SPOT", "maker": value, "taker": "-0.001"}], {"instType": "SPOT"})
            self.assertNotEqual(result["status"], "observed")

    def test_usdt_assessment_requires_known_account_and_exposure(self):
        settings = {"acctLv": "2", "autoLoan": False, "enableSpotBorrow": False, "feeType": "0"}
        exposure = {"positions_read_status": "ok", "open_position_count": 0,
                    "orders_read_status": "ok", "pending_order_count": 0,
                    "balance_read_status": "ok", "non_usdt_liabilities_present": False}
        self.assertEqual(assess_usdt_only(settings, exposure)["status"], "conditionally_feasible_not_trade_ready")
        self.assertFalse(assess_usdt_only(settings, exposure)["trading_authorized"])
        for change in ({"acctLv": "3"}, {"autoLoan": None}):
            self.assertEqual(assess_usdt_only({**settings, **change}, exposure)["status"], "requires_review")
        self.assertEqual(assess_usdt_only(settings, {**exposure, "open_position_count": 1})["status"], "requires_review")

    def test_report_drops_secret_and_account_identity_fields(self):
        class FakeClient:
            offset_ms = 0
            def get(self, path, params=None):
                if path.endswith("/time"):
                    return [{"ts": "1700000000000"}]
                if path.endswith("/config"):
                    return [{"apiKey": "SENSITIVE_KEY", "uid": "SENSITIVE_UID", "acctLv": "2", "autoLoan": False}]
                if path.endswith("/balance"):
                    return [{"details": [{"ccy": "BTC", "eq": "SENSITIVE_BALANCE", "liab": "0"}]}]
                return []
        report = capabilities_audit(FakeClient())
        text = json.dumps(report)
        for value in ("SENSITIVE_KEY", "SENSITIVE_UID", "SENSITIVE_BALANCE"):
            self.assertNotIn(value, text)
        self.assertEqual(report["order_requests_sent"], 0)


if __name__ == "__main__":
    unittest.main()
