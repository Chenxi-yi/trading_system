"""First-observed BTC master versions and exact OI unit consistency, not flows."""
import hashlib,json
from decimal import Decimal
from urllib.parse import urlparse,parse_qs
from miniquant.data.okx_public import DataError,integer,number

INSTRUMENT='BTC-USDT-SWAP'
MATERIAL=('ctType','ctVal','ctMult','ctValCcy','settleCcy')
EXECUTION=('lotSz','minSz','tickSz','maxLmtSz','maxMktSz','state')


def unpack(raw,path):
    if hashlib.sha256(raw['body_text'].encode()).hexdigest()!=raw['body_sha256']:raise DataError('Master/OI hash mismatch')
    url=urlparse(raw['url']);query=parse_qs(url.query)
    expected={'instType':['SWAP']} if path.endswith('instruments') else {'instType':['SWAP'],'instId':[INSTRUMENT]}
    if url.scheme!='https' or url.netloc!='openapi.okx.com' or url.path!=path or query!=expected:raise DataError('Master/OI endpoint mismatch')
    payload=json.loads(raw['body_text']);received=integer(raw['ingested_at_ms'])
    if received<1_000_000_000_000 or payload.get('code')!='0' or not isinstance(payload.get('data'),list):raise DataError('Master/OI schema')
    return payload['data'],received


def master(raw):
    rows,received=unpack(raw,'/api/v5/public/instruments')
    rows=[r for r in rows if r.get('instId')==INSTRUMENT]
    if len(rows)!=1 or rows[0].get('instType')!='SWAP':raise DataError('Master instrument not unique')
    row=rows[0];fields={}
    for name in MATERIAL+EXECUTION:
        value=row.get(name)
        if name in ('ctVal','ctMult','lotSz','minSz','tickSz','maxLmtSz','maxMktSz'):
            if value in (None,''):
                if name not in ('ctMult','maxLmtSz','maxMktSz'):raise DataError('Missing master quantity')
                value=None
            else:
                value=number(value)
                if value<=0:raise DataError('Nonpositive master quantity')
                value=format(value.normalize(),'f')
        elif not isinstance(value,str) or not value:raise DataError('Missing master identity/state')
        fields[name]=value
    admitted=fields['ctType']=='linear' and fields['ctValCcy']=='BTC' and fields['settleCcy']=='USDT' and fields['ctMult']=='1'
    return dict(inst_id=INSTRUMENT,available_at_ms=received,effective_at_ms=None,
        effective_time_certified=False,source_sha256=raw['body_sha256'],fields=fields,
        fingerprint=hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest(),admitted=admitted)


def check_units(masters,observations,now_ms,start_ms):
    versions=sorted(masters,key=lambda m:m['available_at_ms'])
    if not versions:raise DataError('No master version')
    drift=[];execution=[];invalid=False
    for old,new in zip(versions,versions[1:]):
        if old['available_at_ms']==new['available_at_ms'] and old['fingerprint']!=new['fingerprint']:raise DataError('Conflicting master receive time')
        changed=[k for k in MATERIAL if old['fields'][k]!=new['fields'][k]]
        if changed:
            drift.append(dict(observed_at_ms=new['available_at_ms'],fields=changed))
            invalid|=new['available_at_ms']>=start_ms
        trade_changed=[k for k in EXECUTION if old['fields'][k]!=new['fields'][k]]
        if trade_changed:execution.append(dict(observed_at_ms=new['available_at_ms'],fields=trade_changed))
    checks=[]
    for raw in observations:
        rows,received=unpack(raw,'/api/v5/public/open-interest')
        if len(rows)!=1 or rows[0].get('instId')!=INSTRUMENT or rows[0].get('instType')!='SWAP':raise DataError('OI identity mismatch')
        count,coins=number(rows[0]['oi']),number(rows[0]['oiCcy'])
        if min(count,coins)<0:raise DataError('Negative OI')
        prior=[m for m in versions if m['available_at_ms']<=received]
        item=dict(oi_received_at_ms=received,source_sha256=raw['body_sha256'])
        if not prior:item['status']='no_prior_master'
        else:
            chosen=prior[-1];item['master_received_at_ms']=chosen['available_at_ms']
            if not chosen['admitted']:item['status']='unsupported_master'
            elif count==0 and coins==0:item['status']='zero_not_checkable'
            else:
                error=abs(coins-count*number(chosen['fields']['ctVal']))
                item.update(status='consistent' if error<=Decimal('0.00000001') else 'unit_disagreement',absolute_btc_error=str(error))
                invalid|=item['status']=='unit_disagreement' and received>=start_ms
        checks.append(item)
    past=[m for m in versions if m['available_at_ms']<=now_ms]
    current=past[-1] if past else None
    fresh=current is not None and now_ms-current['available_at_ms']<=26*3_600_000
    scope_ready=all(c['oi_received_at_ms']<start_ms or c['status'] in ('consistent','zero_not_checkable') for c in checks)
    supported=fresh and current['admitted'] and current['fields']['state']=='live' and not invalid and scope_ready
    return dict(study_supported=bool(supported),unit_break_detected=invalid,
        master_fresh=bool(fresh),master_scope_ready=scope_ready,material_changes=drift,execution_review_changes=execution,
        checks=checks,historical_effective_time_certified=False,sided_counting_certified=False)
