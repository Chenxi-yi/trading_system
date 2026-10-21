"""Bounded, resumable public archive collection; no trading or feature availability claims."""
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib import request,error
from collections import Counter
import hashlib,json,os,time,zipfile
from miniquant.data.okx_public import NoRedirect
from miniquant.data.binance_metrics import audit_metrics_zip


def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(temp,path)


class MetricsFetcher:
    def __init__(self):self.opener=request.build_opener(NoRedirect());self.last=0
    def __call__(self,day,suffix):
        if str(date.fromisoformat(day))!=day or suffix not in ('','.CHECKSUM'):raise ValueError('Invalid archive selector')
        url='https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/'+f'BTCUSDT-metrics-{day}.zip'+suffix
        time.sleep(max(0,.3-(time.monotonic()-self.last)));self.last=time.monotonic()
        with self.opener.open(request.Request(url,method='GET',headers={'User-Agent':'PersonalMiniQuantArchive/0.1'}),timeout=10) as response:
            body=response.read(3000001);modified=response.headers.get('Last-Modified')
        if len(body)>3000000:raise ValueError('Archive exceeds limit')
        return body,dict(url=url,ingested_at=datetime.now(timezone.utc).isoformat(),origin_last_modified=modified,note='Last-Modified is not certified original publication')


def collect_chunk(run,state,fetch,budget,now_seconds=None):
    if type(budget) is not int or not 0<budget<=100:raise ValueError('Request budget invalid')
    run=Path(run);now=time.time() if now_seconds is None else now_seconds
    if state.get('blocked_reason'):return dict(requests=0,status='blocked_requires_review')
    if state.get('retry_after_epoch',0)>now:return dict(requests=0,status='backoff_not_elapsed')
    used=0;day=date.fromisoformat(state['start']);end=date.fromisoformat(state['end_exclusive'])
    statefile=run/'checkpoint.json'
    while day<end:
        key=str(day)
        if state['days'].get(key,{}).get('status') in ('verified','missing'):
            day+=timedelta(days=1);continue
        try:
            bodies={}
            for suffix in ('','.CHECKSUM'):
                name=f'BTCUSDT-metrics-{key}.zip'+suffix;path=run/'raw'/name;meta=path.with_name(name+'.meta.json')
                if not path.exists():
                    if used>=budget:
                        save_json(statefile,state);return dict(requests=used,status='budget_exhausted')
                    used+=1;state['total_request_attempts']=state.get('total_request_attempts',0)+1;save_json(statefile,state)
                    body,metadata=fetch(key,suffix)
                    path.parent.mkdir(parents=True,exist_ok=True)
                    tmp=path.with_name(name+'.tmp');tmp.write_bytes(body);os.replace(tmp,path)
                    metadata=dict(metadata,sha256=hashlib.sha256(body).hexdigest());save_json(meta,metadata)
                if not meta.exists():raise ValueError('Orphan body has no provenance; do not invent ingestion')
                body=path.read_bytes();metadata=json.loads(meta.read_text())
                if hashlib.sha256(body).hexdigest()!=metadata['sha256']:raise ValueError('Saved raw hash mismatch')
                bodies[suffix]=body
            stats,rows=audit_metrics_zip(bodies[''],bodies['.CHECKSUM'],key)
            times=sorted(datetime.fromisoformat(r['create_time']) for r in rows)
            expected=[datetime.fromisoformat(key)+timedelta(minutes=5*i) for i in range(288)]
            stats.pop('label_times',None);stats.update(status='verified',sorted5m_label_grid_complete=times==expected,publication_certified=False)
            state['days'][key]=stats;state.pop('last_error',None);state.pop('retry_after_epoch',None)
            save_json(statefile,state);print(key,'verified',len(rows),flush=True)
        except error.HTTPError as exc:
            if exc.code in (404,410):state['days'][key]=dict(status='missing',http_status=exc.code);save_json(statefile,state);day+=timedelta(days=1);continue
            state['last_error']=dict(day=key,error_type='HTTPError',http_status=exc.code)
            if exc.code in (403,451):state['blocked_reason']='venue_access_denied_no_automatic_retry'
            else:state['retry_after_epoch']=now+600
            save_json(statefile,state);return dict(requests=used,status='access_blocked' if exc.code in (403,451) else 'network_or_rate_backoff')
        except (ValueError,zipfile.BadZipFile) as exc:
            state['last_error']=dict(day=key,error_type=type(exc).__name__)
            state['blocked_reason']='integrity_or_schema_requires_review'
            save_json(statefile,state);return dict(requests=used,status='integrity_blocked')
        except Exception as exc:
            state['last_error']=dict(day=key,error_type=type(exc).__name__)
            state['retry_after_epoch']=now+600;save_json(statefile,state)
            return dict(requests=used,status='integrity_or_network_error')
        day+=timedelta(days=1)
    state['collection_complete']=True;save_json(statefile,state)
    return dict(requests=used,status='collection_finished_coverage_not_certified')


def coverage_summary(state):
    counts=Counter(v['status'] for v in state['days'].values());verified=[v for v in state['days'].values() if v['status']=='verified']
    missing_fields=Counter()
    for v in verified:missing_fields.update(v['unknown_values'])
    total=(date.fromisoformat(state['end_exclusive'])-date.fromisoformat(state['start'])).days
    return dict(expected_days=total,completed_day_states=len(state['days']),status_counts=dict(counts),pending_days=total-len(state['days']),verified_rows=sum(v['rows'] for v in verified),incomplete_label_grid_days=sum(not v['sorted5m_label_grid_complete'] for v in verified),missing_metric_values=dict(missing_fields),collection_complete=state.get('collection_complete',False),historical_publication_certified=False,research_ready=False,orders_sent=0)
