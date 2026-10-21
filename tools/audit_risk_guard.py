"""026 one-shot synthetic guard demonstration. No account/API/order path."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniquant.risk.pretrade import assess_spot_order as legacy
from miniquant.risk.pretrade_strict import assess_spot_order as strict
from miniquant.data.archive_collection import save_json


def main():
    out=ROOT/'artifacts/BTC-RISK-GUARD-026';out.mkdir(parents=True,exist_ok=False)
    names=['tools/audit_risk_guard.py','src/miniquant/risk/pretrade.py','src/miniquant/risk/pretrade_strict.py',
        'src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']
    protocol=ROOT/'research/audits/BTC-RISK-GUARD-026.json'
    save_json(out/'manifest.json',dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},inputs={}))
    for n in names:
        target=out/'source_snapshot'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    context=dict(environment='paper',now_ms=1000,snapshot_ms=999,max_snapshot_age_ms=100,
        bot_initial_nav=1000,bot_nav=1000,max_initial_loss_fraction=.4,
        bot_available_usdt=200,strategy_available_usdt=100,account_available_usdt=5000,
        bot_inventory=.01,strategy_inventory=.01,account_available_base=1.01,protected_base=1,
        max_order_notional=100,maximum_buy_fee_rate=.001,lot=1,minimum_quantity=1)
    intent=dict(inst_id='BTC-USDT',mode='cash',side='buy',quantity=True,maximum_price=1)
    a=legacy(intent,context);b=strict(intent,context)
    context.update(lot=1e-308,minimum_quantity=1e-308);intent['quantity']=1e308
    try:legacy(intent,context);old_error=None
    except Exception as exc:old_error=type(exc).__name__
    c=strict(intent,context)
    result=dict(legacy_bool_allowed=a['allow'],strict_bool_rejected=not b['allow'],
        legacy_extreme_error_type=old_error,strict_extreme_rejected=not c['allow'],
        strict_submission_authorized=c['submission_authorized'],new_HTTP_attempts=0,orders_sent=0,pnl_tests=0)
    save_json(out/'summary.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
