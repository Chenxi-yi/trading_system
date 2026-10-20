"""Read-only Demo account/instrument/fee audit. Run: python3.11 -m tools.okx_capabilities.

Only whitelisted metadata enters the report. Private evidence stays in runtime/.
No permission, collateral or account mode changes are performed.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import time

from tools.okx_demo_audit import ROOT, AuditError, DemoClient, load_demo, save_report

SETTINGS = ("acctLv", "posMode", "autoLoan", "enableSpotBorrow", "spotBorrowAutoRepay",
            "feeType", "ctIsoMode", "mgnIsoMode", "perm")
INSTRUMENT_FIELDS = ("instId", "instType", "instCategory", "state", "baseCcy", "quoteCcy",
                     "settleCcy", "instFamily", "ctType", "ctVal", "ctMult", "ctValCcy",
                     "tickSz", "lotSz", "minSz", "lever", "groupId", "listTime", "expTime")
TARGETS = {
    "SPOT": ("BTC-USDT", "ETH-USDT", "SOL-USDT", "XAAPL-USDT", "XTSLA-USDT"),
    "SWAP": ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "AAPL-USDT-SWAP", "TSLA-USDT-SWAP"),
}


def numeric(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_fees(rows, instrument):
    """Never map a different group's rate to this product; negative API rate is cost."""
    for row in rows:
        if row.get("instType") != instrument.get("instType"):
            continue
        groups = row.get("feeGroup") or []
        if groups:
            group = instrument.get("groupId")
            if not group:
                return {"status": "unknown_fee_group"}
            matched = [x for x in groups if str(x.get("groupId")) == str(group)]
            if len(matched) != 1:
                return {"status": "fee_group_not_uniquely_matched"}
            source, values = "feeGroup", matched[0]
        else:
            # Caller must have requested this exact instId / instFamily.
            if instrument.get("instType") != "SPOT":
                return {"status": "derivative_fee_group_missing_requires_review"}
            source, values = "direct_instrument_legacy_fields", row
        maker, taker = numeric(values.get("maker")), numeric(values.get("taker"))
        if maker is None or taker is None:
            return {"status": "invalid_fee_values"}
        return {"status": "observed", "source": source,
                "groupId": instrument.get("groupId"),
                "maker_api_rate": str(maker), "taker_api_rate": str(taker),
                "maker_cost_bps": str(-maker * 10000), "taker_cost_bps": str(-taker * 10000),
                "note": "Positive cost_bps is a cost; negative is rebate. Demo snapshot only."}
    return {"status": "fee_type_not_matched"}


def assess_usdt_only(settings, exposure):
    """A conservative pre-trade checklist, not an implemented runtime risk engine."""
    issues = []
    if settings.get("acctLv") != "2":
        issues.append("account_mode_requires_separate_collateral_review")
    if settings.get("autoLoan") is not False:
        issues.append("auto_borrow_not_confirmed_disabled")
    if settings.get("enableSpotBorrow") is not False:
        issues.append("spot_borrow_not_confirmed_disabled")
    if settings.get("feeType") not in ("0", "1"):
        issues.append("spot_fee_currency_rule_unknown")
    if exposure.get("positions_read_status") != "ok" or exposure.get("open_position_count") != 0:
        issues.append("existing_or_unknown_positions_require_reconciliation")
    if exposure.get("orders_read_status") != "ok" or exposure.get("pending_order_count") != 0:
        issues.append("existing_or_unknown_orders_require_reconciliation")
    if exposure.get("balance_read_status") != "ok" or exposure.get("non_usdt_liabilities_present") is not False:
        issues.append("non_usdt_liability_state_requires_review")
    return {"status": "requires_review" if issues else "conditionally_feasible_not_trade_ready",
            "issues": issues,
            "required_runtime_controls": [
                "USDT-quoted cash spot or explicitly USDT-settled contracts only",
                "No borrowing, no coin-margined contracts, no use of protected inventory",
                "Per-strategy budgets plus total Bot cap and pending-order/margin/fee reserves",
                "Trade-time account-state and collateral checks; fail closed on changes",
                "Fee-adjusted spot inventory and fresh protected-inventory baseline",
                "Venue auto-transfer and fee-discount paths need separate pre-trade review"],
            "trading_authorized": False}


def capabilities_audit(client):
    report = {"kind": "capabilities_audit", "environment": "demo", "site": "global",
              "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "order_requests_sent": 0, "checks": [], "settings": {}, "products": [], "fees": {}}

    def read(label, path, params=None):
        try:
            rows = client.get(path, params)
            report["checks"].append({"check": label, "status": "ok", "records": len(rows)})
            print(label + ": ok", flush=True)
            return rows
        except Exception as error:
            reason = str(error) if isinstance(error, AuditError) else "processing_failed"
            report["checks"].append({"check": label, "status": "failed", "reason": reason})
            print(label + ": failed (" + reason + ")", flush=True)
            return None

    before = time.time() * 1000
    clock = read("clock", "/api/v5/public/time")
    if not clock:
        report["status"] = "authentication_not_attempted"
        return report
    try:
        client.offset_ms = int(clock[0]["ts"]) - (before + time.time() * 1000) / 2
    except Exception:
        report["status"] = "clock_schema_invalid"
        return report
    config = read("account_config", "/api/v5/account/config")
    if not config:
        report["status"] = "account_config_unavailable"
        return report
    report["settings"] = {k: config[0].get(k) for k in SETTINGS}

    exposure = {}
    positions = read("positions", "/api/v5/account/positions")
    exposure["positions_read_status"] = "ok" if positions is not None else "unknown"
    exposure["open_position_count"] = sum(numeric(x.get("pos")) != 0 for x in positions) if positions is not None else None
    orders = read("pending_orders", "/api/v5/trade/orders-pending", {"limit": "100"})
    exposure["orders_read_status"] = "ok" if orders is not None else "unknown"
    # Zero is sufficient for the no-preexisting-orders check; nonzero is a lower bound.
    exposure["pending_order_count"] = len(orders) if orders is not None else None
    balances = read("balance_risk_flags", "/api/v5/account/balance")
    exposure["balance_read_status"] = "ok" if balances else "unknown"
    details = [d for a in (balances or []) for d in a.get("details", [])]
    liability_values = [numeric(d.get("liab")) for d in details if d.get("ccy") != "USDT" and d.get("liab") not in (None, "")]
    exposure["non_usdt_liabilities_present"] = any(x != 0 for x in liability_values) if balances else None
    report["exposure_flags"] = exposure

    for kind in ("SPOT", "SWAP", "FUTURES"):
        rows = read("instruments_" + kind, "/api/v5/account/instruments", {"instType": kind})
        if rows is None:
            continue
        wanted = list(TARGETS.get(kind, ()))
        if kind == "FUTURES":
            candidates = sorted(x["instId"] for x in rows if x.get("settleCcy") == "USDT" and x.get("instId", "").startswith("BTC-USDT-"))
            wanted = candidates[:1]
        lookup = {x.get("instId"): x for x in rows}
        report.setdefault("inventory_counts", {})[kind] = len(rows)
        for inst_id in wanted:
            product = lookup.get(inst_id)
            if product is None:
                report["products"].append({"instId": inst_id, "instType": kind, "visibility": "not_returned", "order_tested": False})
                continue
            product = {k: product.get(k) for k in INSTRUMENT_FIELDS}
            product.update(visibility="returned", order_tested=False)
            report["products"].append(product)
            fee_params = {"instType": kind}
            if kind == "SPOT":
                fee_params["instId"] = inst_id
            elif product.get("instFamily"):
                fee_params["instFamily"] = product["instFamily"]
            else:
                report["fees"][inst_id] = {"status": "instrument_family_missing"}
                continue
            fees = read("fees_" + inst_id, "/api/v5/account/trade-fee", fee_params)
            report["fees"][inst_id] = normalize_fees(fees, product) if fees is not None else {"status": "request_failed"}

    report["usdt_only_assessment"] = assess_usdt_only(report["settings"], exposure)
    report["status"] = "audit_completed_with_limits"
    report["limitations"] = ["No order placement: visibility is not trading verification",
                             "Fees are demo observations, not live fee guarantees",
                             "No collateral settings, auto-transfer settings or permissions changed",
                             "Per-strategy budgets/inventory guards not yet implemented",
                             "Native bots/conditional orders are not exhaustively inventoried"]
    return report


def main():
    try:
        report = capabilities_audit(DemoClient(load_demo(ROOT / "config.toml")))
        path = save_report(report)
        summary = {k: report.get(k) for k in ("status", "settings", "inventory_counts", "exposure_flags", "fees", "usdt_only_assessment")}
        summary["product_visibility"] = {p["instId"]: p["visibility"] for p in report["products"]}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("Private report:", path)
        return 0 if report.get("status") == "audit_completed_with_limits" else 1
    except AuditError as error:
        print("Audit stopped:", error)
        return 1
    except Exception:
        print("Audit stopped: unexpected_error; details suppressed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
