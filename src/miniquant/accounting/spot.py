"""Finite cash/inventory spot ledger; explicit base-currency buy commission."""
from dataclasses import dataclass, field
import math


@dataclass
class SpotAccount:
    cash: float
    quantity: float = 0.0
    fee_rate: float = 0.001
    slippage: float = 0.0005
    lot: float = 1e-8
    minimum: float = 2e-5
    fees: float = 0.0
    turnover: float = 0.0
    fills: list = field(default_factory=list)

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.cash,self.quantity,self.fee_rate,self.slippage,self.lot,self.minimum)) or self.cash<0 or self.quantity<0 or not 0<=self.fee_rate<1 or not 0<=self.slippage<1 or self.lot<=0 or self.minimum<0:
            raise ValueError('Invalid spot account')

    def nav(self,price):
        if not math.isfinite(price) or price<=0:raise ValueError('Invalid price')
        return self.cash+self.quantity*price

    def buy(self,budget,price,ts,reason='target',limit=False):
        if not math.isfinite(budget) or budget<0:raise ValueError('Invalid budget')
        px=price if limit else price*(1+self.slippage)
        self.nav(px)
        budget=min(budget,self.cash)
        gross=math.floor(budget/px/self.lot)*self.lot
        if gross+1e-15<self.minimum:return 0.0
        spent=gross*px
        received=gross*(1-self.fee_rate)
        self.cash-=spent;self.quantity+=received
        fee=spent*self.fee_rate;self.fees+=fee;self.turnover+=spent
        self.fills.append(dict(ts=ts,side='buy',gross_quantity=gross,quantity=received,price=px,notional=spent,fee=fee,reason=reason))
        self.check()
        return received

    def sell(self,quantity,price,ts,reason='target',limit=False):
        if not math.isfinite(quantity) or quantity<0:raise ValueError('Invalid quantity')
        if quantity>self.quantity+1e-10:raise ValueError('Protected or unavailable inventory')
        px=price if limit else price*(1-self.slippage)
        self.nav(px)
        qty=math.floor(min(quantity,self.quantity)/self.lot+1e-8)*self.lot
        if qty+1e-15<self.minimum:return 0.0
        gross=qty*px;fee=gross*self.fee_rate
        self.quantity-=qty;self.cash+=gross-fee
        self.fees+=fee;self.turnover+=gross
        self.fills.append(dict(ts=ts,side='sell',quantity=qty,price=px,notional=gross,fee=fee,reason=reason))
        self.check()
        return qty

    def target(self,weight,price,ts,reason='target'):
        if not math.isfinite(weight) or not 0<=weight<=0.95:raise ValueError('Spot risk weight limit')
        difference=self.nav(price)*weight-self.quantity*price
        if difference>0:self.buy(difference,price,ts,reason)
        elif difference<0:self.sell(min(self.quantity,-difference/price),price,ts,reason)

    def check(self):
        if self.cash < -1e-7 or self.quantity < -1e-10 or not math.isfinite(self.cash+self.quantity):
            raise ArithmeticError('Ledger invariant violated')
