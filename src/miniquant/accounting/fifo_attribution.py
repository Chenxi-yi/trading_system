"""FIFO accounting attribution; never infer missing grid cell IDs."""
import math
from collections import deque


def fifo_attribution(fills,marks,initial=10000):
    if not marks or any(b['ts']<=a['ts'] for a,b in zip(marks,marks[1:])) or any(b['ts']<a['ts'] for a,b in zip(fills,fills[1:])):raise ValueError('Clock ordering')
    if not math.isfinite(initial) or initial<=0:raise ValueError('Invalid capital')
    lots=deque();cash=initial;quantity=0.;realized=0.;i=0;reasons={};daily=[]
    for j,mark in enumerate(marks):
        if not math.isfinite(mark['price']) or mark['price']<=0:raise ValueError('Invalid valuation')
        while i<len(fills) and (fills[i]['ts']<mark['ts'] or j==len(marks)-1 and fills[i]['ts']==mark['ts']):
            f=fills[i];i+=1
            if any(not math.isfinite(f[k]) or f[k]<0 for k in ('quantity','notional','fee')) or f['quantity']<=0:raise ValueError('Invalid fill')
            q=f['quantity'];entry=reasons.setdefault(f['reason'],dict(fills=0,fifo_realized=0.,notional=0.,fees=0.));entry['fills']+=1;entry['notional']+=f['notional'];entry['fees']+=f['fee']
            if f['side']=='buy':
                cash-=f['notional'];quantity+=q;lots.append([q,f['notional']/q])
            elif f['side']=='sell':
                if q>quantity+1e-10:raise ValueError('Unowned inventory')
                left=q;basis=0.
                while left>1e-12:
                    if not lots:raise ValueError('Missing cost basis')
                    amount=min(left,lots[0][0]);basis+=amount*lots[0][1];left-=amount;lots[0][0]-=amount
                    if lots[0][0]<=1e-12:lots.popleft()
                pnl=f['notional']-f['fee']-basis;realized+=pnl;entry['fifo_realized']+=pnl;cash+=f['notional']-f['fee'];quantity-=q
            else:raise ValueError('Invalid side')
        basis=sum(q*p for q,p in lots);inventory=quantity*mark['price'];unrealized=inventory-basis;nav=cash+inventory
        error=abs(nav-initial-realized-unrealized)
        if error>1e-6:raise ValueError('FIFO equity identity failed')
        daily.append(dict(ts=mark['ts'],nav=nav,realized=realized,unrealized=unrealized,inventory_weight=inventory/nav,identity_error=error))
    if i!=len(fills):raise ValueError('Unvalued future fills')
    return dict(daily=daily,reasons=reasons,final_pnl=daily[-1]['nav']-initial,final_realized=realized,final_unrealized=daily[-1]['unrealized'],worst_unrealized=min(x['unrealized'] for x in daily),max_inventory_weight=max(x['inventory_weight'] for x in daily),max_identity_error=max(x['identity_error'] for x in daily),cell_cycle_profit_certified=False)
