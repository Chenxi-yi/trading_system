"""Linear USDT perpetual research ledger. Explicit quantities, fees and funding.

This does not implement historical OKX margin tiers or real liquidation rules.
"""
from dataclasses import dataclass,field
import math


@dataclass
class LinearPerpAccount:
    cash: float
    quantity: float=0.0
    entry: float=0.0
    fee_rate: float=0.0005
    slippage: float=0.0005
    max_weight: float=0.75
    contract_value: float=0.01
    contract_lot: float=0.01
    fees: float=0.0
    funding_pnl: float=0.0
    fills: list=field(default_factory=list)
    funding_events: list=field(default_factory=list)

    def equity(self,mark):
        if not math.isfinite(mark) or mark<=0:raise ValueError('Invalid mark')
        return self.cash+self.quantity*(mark-self.entry)

    def close(self,price,ts,reason='close'):
        if self.quantity==0:return
        px=price*(1-self.slippage if self.quantity>0 else 1+self.slippage)
        realized=self.quantity*(px-self.entry);fee=abs(self.quantity)*px*self.fee_rate
        self.cash+=realized-fee;self.fees+=fee
        self.fills.append(dict(ts=ts,side='sell' if self.quantity>0 else 'buy',quantity=abs(self.quantity),price=px,fee=fee,realized_pnl=realized,reason=reason))
        self.quantity=0;self.entry=0

    def target(self,direction,price,ts):
        if direction not in (-1,0,1):raise ValueError('Invalid direction')
        if not 0<=self.max_weight<=0.75:raise ValueError('Research notional risk cap')
        if self.quantity and (1 if self.quantity>0 else -1)==direction:return
        self.close(price,ts,'direction_change')
        if direction==0 or self.cash<=0:return
        px=price*(1+self.slippage if direction>0 else 1-self.slippage)
        step=self.contract_value*self.contract_lot
        quantity=math.floor(self.cash*self.max_weight/px/step)*step
        if quantity<=0:return
        fee=quantity*px*self.fee_rate
        if fee>self.cash:raise ArithmeticError('Fee exceeds available cash')
        self.cash-=fee;self.fees+=fee;self.quantity=direction*quantity;self.entry=px
        self.fills.append(dict(ts=ts,side='buy' if direction>0 else 'sell',quantity=quantity,contracts=quantity/self.contract_value,price=px,fee=fee,reason='entry'))

    def settle_funding(self,rate,mark,ts):
        if not math.isfinite(rate):raise ValueError('Unknown realized funding')
        payment=-self.quantity*mark*rate
        self.cash+=payment;self.funding_pnl+=payment
        self.funding_events.append(dict(ts=ts,rate=rate,mark=mark,quantity=self.quantity,pnl=payment))
        return payment
