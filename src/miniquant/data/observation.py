"""Normalize actually observed public snapshots, with conservative availability."""
import json
from miniquant.data.okx_public import DataError,number,integer,utc


def normalize_observation(kind,envelope,inst_id):
    payload=json.loads(envelope['body_text'])
    if payload.get('code')!='0' or len(payload.get('data',[]))!=1:raise DataError('snapshot_schema')
    row=payload['data'][0];ingested=envelope['ingested_at_ms'];event=integer(row['ts'])
    if event>ingested+60000:raise DataError('snapshot_future_clock')
    if row.get('instId',inst_id)!=inst_id:raise DataError('wrong_instrument')
    result=dict(schema_version=1,venue='OKX',environment='public_market',kind=kind,inst_id=inst_id,event_time=utc(event),available_at=utc(ingested),ingested_at=utc(ingested),availability_basis='first_observed_HTTP_response; no earlier availability asserted',source_sha256=envelope['body_sha256'],age_ms=ingested-event)
    if kind=='open_interest':
        for field in ('oi','oiCcy','oiUsd'):
            if field not in row or number(row[field])<0:raise DataError('invalid_OI')
        result['values']={k:row[k] for k in ('oi','oiCcy','oiUsd')}
        result['units']=dict(oi='venue_contract_count',oiCcy='venue_reported_underlying',oiUsd='venue_reported_USD')
        result['fresh']=0<=result['age_ms']<=60000
    elif kind=='books':
        bids=row['bids'];asks=row['asks']
        if not bids or not asks:raise DataError('empty_orderbook')
        for levels in (bids,asks):
            for level in levels:
                if len(level)<2 or number(level[0])<=0 or number(level[1])<0:raise DataError('bad_book_level')
        bid=number(bids[0][0]);ask=number(asks[0][0])
        if ask<bid:raise DataError('crossed_book')
        result['values']=dict(bids=bids,asks=asks,spread_bps=str((ask-bid)/((ask+bid)/2)*10000),seqId=row.get('seqId'))
        result['size_unit']='venue_contract_count for SWAP; base currency for SPOT; do not mix without instrument master'
        result['fresh']=0<=result['age_ms']<=30000
    elif kind=='ticker':
        for k in ('last','bidPx','askPx'):
            if number(row[k])<=0:raise DataError('invalid_quote')
        if number(row['askPx'])<number(row['bidPx']):raise DataError('crossed_quote')
        result['values']={k:row[k] for k in ('last','bidPx','askPx')}
        result['fresh']=0<=result['age_ms']<=30000
    else:raise DataError('unsupported_observation')
    return result
