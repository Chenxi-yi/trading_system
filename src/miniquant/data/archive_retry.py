"""New lineage: bounded TLS EOF retries, each attempt counted by original collector."""
import ssl,time
from pathlib import Path
from urllib.error import URLError
from miniquant.data.archive_collection import collect_chunk,save_json


def collect_retry_chunk(run,state,fetch,budget,clock=time.time,sleep=time.sleep):
    if type(budget) is not int or not 0<budget<=100:raise ValueError('Invalid request budget')
    run=Path(run);used=0;retries=0
    while used<budget:
        failure={}
        def observed(day,suffix):
            try:return fetch(day,suffix)
            except (URLError,OSError) as exc:
                reason=exc.reason if isinstance(exc,URLError) else exc
                failure.update(exception_type=type(exc).__name__,reason_type=type(reason).__name__,ssl_eof=isinstance(reason,ssl.SSLEOFError))
                for name in ('errno','verify_code'):
                    value=getattr(reason,name,None)
                    if type(value) is int:failure[name]=value
                raise
        result=collect_chunk(run,state,observed,budget-used,clock());used+=result['requests']
        if failure:
            state.setdefault('transport_events',[]).append(dict(failure,attempt_counter=state['total_request_attempts']))
            save_json(run/'checkpoint.json',state)
        if failure.get('ssl_eof') and retries<2 and used<budget and not state.get('blocked_reason'):
            delay=(2,5)[retries];retries+=1
            state['transport_events'][-1].update(retry_delay_seconds=delay,replaced_backoff_epoch=state.get('retry_after_epoch'))
            state['retry_after_epoch']=clock()+delay
            state.pop('last_error',None) # Original error remains in immutable parent and transport_events.
            save_json(run/'checkpoint.json',state);sleep(delay);continue
        return dict(result,requests=used,tls_retries=retries)
    return dict(requests=used,status='budget_exhausted',tls_retries=retries)
