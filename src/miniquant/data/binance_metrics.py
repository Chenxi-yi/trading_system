"""Audit official public archive samples; label times are not availability times."""
import csv,hashlib,io,re,zipfile
from collections import Counter
from datetime import datetime
from decimal import Decimal,InvalidOperation

FIELDS={'create_time','symbol','sum_open_interest','sum_open_interest_value','count_toptrader_long_short_ratio','sum_toptrader_long_short_ratio','count_long_short_ratio','sum_taker_long_short_vol_ratio'}


def audit_metrics_zip(blob,checksum,day):
    filename=f'BTCUSDT-metrics-{day}.zip'
    parts=checksum.decode('ascii').strip().split()
    if len(parts)!=2 or not re.fullmatch('[0-9a-fA-F]{64}',parts[0]) or parts[1].lstrip('*')!=filename:raise ValueError('Unexpected checksum declaration')
    if hashlib.sha256(blob).hexdigest()!=parts[0].lower():raise ValueError('Checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        entries=archive.infolist()
        if len(entries)!=1 or entries[0].filename!=filename[:-4]+'.csv' or entries[0].file_size>10000000:raise ValueError('Unexpected archive layout/size')
        text=archive.read(entries[0]).decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text))
    if set(reader.fieldnames or [])!=FIELDS:raise ValueError('Metrics schema changed')
    rows=list(reader);labels=[];unknown=Counter()
    for row in rows:
        if row['symbol']!='BTCUSDT':raise ValueError('Wrong metrics symbol')
        ts=datetime.fromisoformat(row['create_time'])
        if ts.tzinfo is not None:raise ValueError('Timestamp convention changed; inspect before use')
        labels.append(ts)
        for key in FIELDS-{'create_time','symbol'}:
            try:value=Decimal(row[key])
            except (InvalidOperation,ValueError,TypeError):unknown[key]+=1;continue
            if not value.is_finite():unknown[key]+=1
            elif value<0:raise ValueError('Negative unsigned metric')
    if not labels:raise ValueError('Empty metrics archive')
    return dict(rows=len(rows),header=reader.fieldnames,first_label=str(min(labels)),last_label=str(max(labels)),duplicate_labels=len(labels)-len(set(labels)),label_spacing_seconds=dict(Counter(str(int((b-a).total_seconds())) for a,b in zip(labels,labels[1:]))),unknown_values=dict(unknown),available_at=None,availability_basis='Historical original publication time unknown',label_timezone='UTC assumed for inspection only; not source-certified availability',label_times=[r['create_time'] for r in rows]),rows
