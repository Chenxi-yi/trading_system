"""Linear USDT research ledger with signed target notional and partial resizing."""
from dataclasses import dataclass,field
import math


@dataclass
class SizedPerpAccount:
    cash: float=10000
    quantity: float=0.0
    entry: float=0.0
    fee_rate: float=0.0005
    slippage: float=0.0005
    step: float=0.0001
    fees: float=0.0
    funding_pnl: float=0.0
    fills: list=field(default_factory=list)
    funding_events: list=field(default_factory=list)

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.cash,self.quantity,self.entry,self.fee_rate,self.slippage,self.step)) or self.cash<=0 or self.quantity!=0 or self.entry!=0 or not 0<=self.fee_rate<1 or not 0<=self.slippage<1 or self.step<=0:
            raise ValueError('Invalid initial research ledger')

    def equity(self,mark):
        if not math.isfinite(mark) or mark<=0:raise ValueError('Invalid mark')
        return self.cash+self.quantity*(mark-self.entry)

    def _trade(self,delta,price,ts,reason):
        if not math.isfinite(delta) or not math.isfinite(price) or price<=0:raise ValueError('Invalid trade')
        if abs(delta)<self.step/2:return
        px=price*(1+self.slippage if delta>0 else 1-self.slippage)
        old=self.quantity;new=old+delta
        realized=0.0
        if old*delta<0:
            closed=min(abs(old),abs(delta));realized=closed*(px-self.entry)*(1 if old>0 else -1)
        if abs(new)<self.step/2:new=0.0
        if new==0:entry=0.0
        elif old==0 or old*new<0:entry=px
        elif old*delta>0:entry=(abs(old)*self.entry+abs(delta)*px)/abs(new)
        else:entry=self.entry
        fee=abs(delta)*px*self.fee_rate
        self.cash+=realized-fee;self.fees+=fee;self.quantity=new;self.entry=entry
        self.fills.append(dict(ts=ts,side='buy' if delta>0 else 'sell',quantity=abs(delta),price=px,fee=fee,realized_pnl=realized,resulting_quantity=new,reason=reason))

    def target(self,weight,price,mark,ts):
        if not math.isfinite(weight) or abs(weight)>.75:raise ValueError('Research cap exceeded')
        nav=self.equity(mark)
        if nav<=0:raise ArithmeticError('Insolvent research ledger')
        adverse=price*(1+self.slippage if weight>0 else 1-self.slippage)
        desired=math.floor(abs(weight)*nav/adverse/self.step+1e-10)*self.step*(1 if weight>0 else -1) if weight else 0
        self._trade(desired-self.quantity,price,ts,'target_rebalance')

    def close(self,price,ts,reason):
        self._trade(-self.quantity,price,ts,reason)

    def funding(self,rate,mark,ts):
        if not math.isfinite(rate):raise ValueError('Unknown realized funding')
        self.equity(mark)
        pnl=-self.quantity*mark*rate
        self.cash+=pnl;self.funding_pnl+=pnl
        self.funding_events.append(dict(ts=ts,rate=rate,mark=mark,quantity=self.quantity,pnl=pnl))
