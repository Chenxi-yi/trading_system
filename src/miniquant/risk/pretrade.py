"""Fail-closed spot research/demo checks, separate from strategy signals.

This is a pure checker: real account reconciliation, atomic budget reservation,
and a venue order adapter must be verified independently before any submission.
"""
import math


def assess_spot_order(intent,context):
    required=('environment','now_ms','snapshot_ms','max_snapshot_age_ms','bot_initial_nav','bot_nav',
              'max_initial_loss_fraction','bot_available_usdt','strategy_available_usdt','account_available_usdt',
              'bot_inventory','strategy_inventory','account_available_base','protected_base',
              'max_order_notional','maximum_buy_fee_rate','lot','minimum_quantity')
    if any(k not in context for k in required):return dict(allow=False,reason='missing_risk_configuration')
    if context['environment'] not in ('paper','demo'):return dict(allow=False,reason='environment_not_authorized')
    for key in required:
        if key=='environment':continue
        value=context[key]
        if not isinstance(value,(float,int)) or not math.isfinite(value) or value<0:return dict(allow=False,reason='invalid_risk_configuration')
    if context['bot_initial_nav']<=0 or context['lot']<=0 or not 0<context['max_initial_loss_fraction']<1 or context['maximum_buy_fee_rate']>=1:return dict(allow=False,reason='invalid_risk_configuration')
    age=context['now_ms']-context['snapshot_ms']
    if age<0 or age>context['max_snapshot_age_ms']:return dict(allow=False,reason='stale_or_future_account_snapshot')
    if intent.get('inst_id')!='BTC-USDT' or intent.get('mode')!='cash':return dict(allow=False,reason='product_or_borrowing_not_authorized')
    quantity=intent.get('quantity');price=intent.get('maximum_price')
    if not all(isinstance(x,(float,int)) and math.isfinite(x) and x>0 for x in (quantity,price)):return dict(allow=False,reason='invalid_order')
    units=quantity/context['lot']
    if abs(units-round(units))>1e-5 or quantity<context['minimum_quantity']:return dict(allow=False,reason='quantity_rule')
    notional=quantity*price
    if notional>context['max_order_notional']+1e-8:return dict(allow=False,reason='order_concentration_limit')
    if intent.get('side')=='buy':
        if context['bot_nav']<=context['bot_initial_nav']*(1-context['max_initial_loss_fraction']):return dict(allow=False,reason='initial_capital_loss_stop')
        needed=notional*(1+context['maximum_buy_fee_rate'])
        available=min(context['bot_available_usdt'],context['strategy_available_usdt'],context['account_available_usdt'])
        if needed>available+1e-8:return dict(allow=False,reason='insufficient_reserved_budget')
    elif intent.get('side')=='sell':
        safe=min(context['bot_inventory'],context['strategy_inventory'],max(0,context['account_available_base']-context['protected_base']))
        if quantity>safe+1e-10:return dict(allow=False,reason='protected_or_unowned_inventory')
    else:return dict(allow=False,reason='invalid_side')
    return dict(allow=True,reason='pure_pretrade_check_passed',submission_authorized=False,
                note='Passing this check does not reserve funds or authorize an exchange order.')
