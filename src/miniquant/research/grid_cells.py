"""Accounting-only cell trace. Never supplies execution prices or strategy targets."""
from collections import deque
import math


class GridCellTrace:
    def __init__(self,initial):
        self.initial=initial;self.cash=initial;self.owners={};self.cycles=[];self.events=[];self.daily=[];self.resets=[]
    def owner(self,cid):
        return self.owners.setdefault(cid,dict(lots=deque(),realized=0.,buys=0))
    def buy(self,cid,fill,index):
        q=fill['quantity'];cost=fill['notional']
        if q<=0 or not math.isfinite(q+cost) or cost<=0:raise ValueError('Invalid buy')
        owner=self.owner(cid);owner['buys']+=1
        lot=dict(cycle_id=cid+':'+str(owner['buys']),quantity=q,unit_cost=cost/q,initial_quantity=q,buy_at=fill['ts'],buy_reason=fill['reason'],realized=0.)
        owner['lots'].append(lot);self.cycles.append(lot);self.cash-=cost
        self.events.append(dict(fill_index=index,ts=fill['ts'],side='buy',reason=fill['reason'],cell_id=cid,cycle_id=lot['cycle_id'],quantity=q,cost=cost,fee=fill['fee']))
    def _take(self,cid,q,proceeds,when):
        owner=self.owner(cid);remaining=q;parts=[]
        while remaining>1e-12:
            if not owner['lots']:raise ValueError('No owned cost basis')
            lot=owner['lots'][0];amount=min(remaining,lot['quantity']);cash=proceeds*amount/q;cost=amount*lot['unit_cost'];profit=cash-cost
            lot['quantity']-=amount;remaining-=amount;lot['realized']+=profit;owner['realized']+=profit
            parts.append(dict(cell_id=cid,cycle_id=lot['cycle_id'],quantity=amount,net_proceeds=cash,basis=cost,realized=profit))
            if lot['quantity']<=1e-12:
                lot['closed_at']=when;owner['lots'].popleft()
        return parts
    def sell(self,cid,fill,index,reset_flags=None):
        q=fill['quantity'];net=fill['notional']-fill['fee']
        if q<=0 or not math.isfinite(q+net):raise ValueError('Invalid sell')
        if cid is not None:
            available=sum(x['quantity'] for x in self.owner(cid)['lots'])
            if q>available+1e-10:raise ValueError('Sell exceeds cell inventory')
            parts=self._take(cid,q,net,fill['ts'])
        else:
            quantities=[(key,sum(x['quantity'] for x in o['lots'])) for key,o in self.owners.items()]
            quantities=[(key,qty) for key,qty in quantities if qty>1e-12];total=sum(qty for _,qty in quantities)
            if q>total+1e-10 or total<=0:raise ValueError('Aggregate inventory mismatch')
            left=q;cash_left=net;parts=[]
            for j,(key,qty) in enumerate(quantities):
                amount=min(qty,left) if j==len(quantities)-1 else min(qty,q*qty/total)
                proceeds=cash_left if j==len(quantities)-1 else net*amount/q
                if amount>1e-12:parts.extend(self._take(key,amount,proceeds,fill['ts']))
                left-=amount;cash_left-=proceeds
            if abs(left)>1e-10:raise ValueError('Unallocated sale')
        self.cash+=net
        if abs(sum(x['quantity'] for x in parts)-q)>1e-9 or abs(sum(x['net_proceeds'] for x in parts)-net)>1e-6:raise ValueError('Sale allocation mismatch')
        self.events.append(dict(fill_index=index,ts=fill['ts'],side='sell',reason=fill['reason'],cell_id=cid,quantity=q,net_proceeds=net,fee=fill['fee'],parts=parts,reset_flags=reset_flags or []))
    def mark(self,when,price,cash,quantity):
        q=sum(lot['quantity'] for o in self.owners.values() for lot in o['lots']);basis=sum(lot['quantity']*lot['unit_cost'] for o in self.owners.values() for lot in o['lots']);realized=sum(o['realized'] for o in self.owners.values())
        if abs(q-quantity)>1e-9 or abs(self.cash-cash)>1e-6:raise ValueError('Trace disagrees with account')
        unrealized=q*price-basis;nav=cash+quantity*price;error=abs(nav-self.initial-realized-unrealized)
        if error>1e-6:raise ValueError('Trace PnL identity')
        row=dict(ts=when,cash=cash,quantity=quantity,nav=nav,basis=basis,realized=realized,unrealized=unrealized,identity_error=error)
        if self.daily and self.daily[-1]['ts']==when:self.daily[-1]=row
        else:self.daily.append(row)
    def export(self):
        return dict(events=self.events,cycles=self.cycles,daily=self.daily,resets=self.resets,ownership='Same-cell FIFO; aggregate exit proportional by inventory, dust retained',cell_cycle_profit_certified=False,live_fill_certified=False)
