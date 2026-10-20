"""Official monthly BTC funding archive. Unsigned metadata + bounded static.okx.com ZIPs."""
import csv
from datetime import datetime,timezone
from decimal import Decimal
import fcntl
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib import request,parse
import zipfile
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.data.okx_public import PublicClient,NoRedirect,number,integer
from tools.okx_market_audit import atomic_json


def parse_funding_csv(text):
    rows=[]
    reader=csv.DictReader(io.StringIO(text))
    if set(reader.fieldnames or [])!={'instrument_name','funding_rate','funding_time'}:raise ValueError('Archive schema changed')
    for r in reader:
        if r['instrument_name']!='BTC-USDT-SWAP':raise ValueError('Wrong archive instrument')
        rows.append(dict(inst_id=r['instrument_name'],event_time_ms=integer(r['funding_time']),realized_rate=str(number(r['funding_rate'])),source='OKX official funding archive'))
    return rows


def main():
    out=ROOT/'data/funding-archive/BTC-USDT-SWAP';out.mkdir(parents=True,exist_ok=True)
    with (out/'archive.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('Archive collector already active');return
        client=PublicClient();downloads={}
        months=[(y,m) for y in range(2022,2027) for m in range(1,13) if (2022,3)<=(y,m)<=(2026,9)]
        for i in range(0,len(months),9):
            group=months[i:i+9];a,b=group[0],group[-1]
            tag=f'{a[0]}-{a[1]:02}_{b[0]}-{b[1]:02}'
            path=out/(tag+'.metadata.json')
            if path.exists():envelope=json.loads(path.read_text())
            else:
                epoch=lambda x:str(int(datetime(x[0],x[1],1,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()*1000))
                envelope=client.get('archive',dict(module='3',instType='SWAP',instFamilyList='BTC-USDT',dateAggrType='monthly',begin=epoch(a),end=epoch(b)))
                atomic_json(path,envelope)
            payload=json.loads(envelope['body_text'])['data']
            for response in payload:
                for detail in response.get('details',[]):
                    for file in detail.get('groupDetails',[]):
                        if file['filename'].startswith('BTC-USDT-SWAP-fundingrates-'):
                            downloads[file['filename']]=file
        events={};records=[];conflicts=0;failures=[]
        opener=request.build_opener(NoRedirect())
        for name,info in sorted(downloads.items()):
            try:
                url=info['url'];parts=parse.urlsplit(url)
                if parts.scheme!='https' or parts.hostname!='static.okx.com' or parts.username or parts.password:raise ValueError('Archive host not allowed')
                path=out/name
                if path.exists():raw=path.read_bytes()
                else:
                    with opener.open(request.Request(url,headers={'User-Agent':'PersonalMiniQuantResearch/0.2'}),timeout=12) as response:raw=response.read(2_000_001)
                    if len(raw)>2_000_000:raise ValueError('Archive too large')
                    temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(path)
                digest=hashlib.sha256(raw).hexdigest()
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    if len(z.infolist())!=1 or z.infolist()[0].file_size>10_000_000:raise ValueError('Unexpected archive contents')
                    parsed=parse_funding_csv(z.read(z.infolist()[0]).decode('utf-8-sig'))
                records.append(dict(filename=name,url=url,sha256=digest,bytes=len(raw),records=len(parsed)))
                for event in parsed:
                    ts=event['event_time_ms'];event['lineage_id']=digest
                    if ts in events and Decimal(events[ts]['realized_rate'])!=Decimal(event['realized_rate']):conflicts+=1
                    events[ts]=event
                print(name,len(parsed),flush=True)
            except Exception as exc:
                failures.append(dict(filename=name,error=type(exc).__name__))
                print(name,type(exc).__name__,flush=True)
        normalized=[events[t] for t in sorted(events)]
        rest_path=ROOT/'data/market-audit/20261020T154059431686Z/funding_BTC-USDT-SWAP_events.json'
        matched=mismatch=0
        if rest_path.exists():
            for r in json.loads(rest_path.read_text()):
                t=r['event_time_ms']
                if t in events:
                    if abs(Decimal(r['realized_rate'])-Decimal(events[t]['realized_rate']))<=Decimal('1e-12'):matched+=1
                    else:mismatch+=1
        intervals={}
        for a,b in zip(normalized,normalized[1:]):
            h=str(Decimal(b['event_time_ms']-a['event_time_ms'])/Decimal(3600000));intervals[h]=intervals.get(h,0)+1
        manifest=dict(source='https://www.okx.com/docs-v5/en/#public-data-rest-api-get-historical-market-data',
                      module='3',date_aggregation_timezone='UTC+8',files=records,failures=failures,
                      records=len(normalized),conflicts=conflicts,interval_hours=intervals,
                      first=normalized[0]['event_time_ms'] if normalized else None,last=normalized[-1]['event_time_ms'] if normalized else None,
                      rest_overlap_matched=matched,rest_overlap_mismatch=mismatch,
                      note='Interval regularity plus overlap check is evidence, not complete certification of historical schedule.')
        atomic_json(out/'normalized.json',normalized);atomic_json(out/'manifest.json',manifest)
        print('Funding archive manifest:',out/'manifest.json',flush=True)


if __name__=='__main__':main()
