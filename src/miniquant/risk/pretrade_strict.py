"""Versioned exact-type boundary around the immutable legacy spot checker.

Pure validation only. No budget reservation, exchange adapter, or order authority.
"""
import math
from miniquant.risk.pretrade import assess_spot_order as legacy_assess

NUMERIC_FIELDS=('now_ms','snapshot_ms','max_snapshot_age_ms','bot_initial_nav','bot_nav',
    'max_initial_loss_fraction','bot_available_usdt','strategy_available_usdt','account_available_usdt',
    'bot_inventory','strategy_inventory','account_available_base','protected_base',
    'max_order_notional','maximum_buy_fee_rate','lot','minimum_quantity')


def finite_nonnegative(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value) and value>=0
    except (OverflowError,TypeError,ValueError):return False


def assess_spot_order(intent,context):
    def reject(reason):return dict(allow=False,reason=reason,submission_authorized=False)
    if not isinstance(intent,dict) or not isinstance(context,dict):return reject('invalid_risk_payload')
    if any(k not in context for k in NUMERIC_FIELDS+('environment',)):return reject('missing_risk_configuration')
    if any(not finite_nonnegative(context[k]) for k in NUMERIC_FIELDS):return reject('invalid_risk_configuration')
    quantity,price=intent.get('quantity'),intent.get('maximum_price')
    if not all(finite_nonnegative(x) and x>0 for x in (quantity,price)):return reject('invalid_order')
    if context['lot']<=0:return reject('invalid_risk_configuration')
    try:
        quotient=quantity/context['lot']
        if not math.isfinite(quotient):return reject('quantity_ratio_overflow')
        result=legacy_assess(intent,context)
    except (ArithmeticError,ValueError,TypeError):
        return reject('numeric_risk_check_failed')
    return dict(result,submission_authorized=False,risk_input_version=2)
