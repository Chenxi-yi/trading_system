"""Bounded local public feed. No credentials, account endpoints, or LLM/API calls."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys,time,hashlib,fcntl,subprocess,signal
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=(('tools/observe_btc_public.py',),('tools/observe_btc_pressure.py',),('tools/run_oi_study.py','--mode','prepare'))
ACTIVE_CHILD=None
STOP_REQUESTED=False


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)


def admission(decision,cache_mtime,now,manual_pause,stop):
    if stop:return 'stop_requested'
    if manual_pause is not False:return 'manual_pause_or_unknown'
    if not isinstance(decision,dict) or decision.get('action')!='continue':return 'quota_not_allowed_or_unknown'
    if now-cache_mtime>1800 or cache_mtime>now+5:return 'quota_cache_stale_or_future'
    return None


def verify_sources(manifest):
    for key in ('code','inputs'):
        for name,digest in manifest[key].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen source/input changed')


def run_public_command(index,timeout_seconds=90):
    global ACTIVE_CHILD
    if type(index)is not int or not 0<=index<len(COMMANDS):raise ValueError('Command outside public allowlist')
    if isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,(int,float)) or not 0<timeout_seconds<=90:raise ValueError('Invalid bounded timeout')
    proc=subprocess.Popen([sys.executable,*COMMANDS[index]],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True);ACTIVE_CHILD=proc.pid
    try:
        stdout,stderr=proc.communicate(timeout=timeout_seconds)
        return dict(returncode=proc.returncode,stdout=stdout[-50000:],stderr=stderr[-5000:])
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.communicate()
        return dict(returncode=None,error_type='TimeoutExpired')
    finally:ACTIVE_CHILD=None


def handle_signal(signum,frame):
    global STOP_REQUESTED
    STOP_REQUESTED=True
    if ACTIVE_CHILD is not None:
        try:os.killpg(ACTIVE_CHILD,signal.SIGTERM)
        except ProcessLookupError:pass


def require_quality(index,bucket):
    if index<2:
        base='forward-observation' if index==0 else 'forward-pressure'
        value=json.loads((ROOT/'data'/base/'BTC'/str(bucket)/'summary.json').read_text())
        if value.get('complete')is not True or any(j.get('fresh')is not True for j in value.get('jobs',[])) or not value.get('jobs'):raise ValueError('Incomplete/stale observation')
    else:
        value=json.loads((ROOT/'artifacts/BTC-STUDY-GATE-028/latest_action.json').read_text())
        if value.get('status')!='dispatched' or value.get('mode')!='prepare' or value.get('action_dispatched')is not True:raise ValueError('Study quality guard blocked')


def freeze():
    protocol=ROOT/'research/audits/BTC-PUBLIC-WORKER-039.json';cfg=json.loads(protocol.read_text())
    names={str(p.relative_to(ROOT)) for p in (ROOT/'src').rglob('*.py')}
    names.update(['tools/observe_btc_worker.py','tools/observe_btc_public.py','tools/observe_btc_pressure.py','tools/run_oi_study.py','tools/build_btc_future_features.py','tools/prepare_oi_variance.py','tools/observe_btc_master.py','tools/evaluate_oi_variance.py','tools/okx_market_audit.py','tests/test_public_worker.py','pyproject.toml'])
    parents=['artifacts/BTC-FUTURE-FEATURES-022/manifest.json','artifacts/BTC-OI-FORECAST-024/manifest.json','artifacts/BTC-MASTER-027/manifest.json','artifacts/BTC-STUDY-GATE-028/manifest.json']
    manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),code={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)},inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in parents})
    out=ROOT/'artifacts/BTC-PUBLIC-WORKER-039';out.mkdir(exist_ok=True);mp=out/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Worker frozen provenance changed')
    if not mp.exists():
        save(mp,manifest)
        for name in sorted(names)+[str(protocol.relative_to(ROOT))]:
            dest=out/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    return cfg,manifest


def main():
    global STOP_REQUESTED
    runtime=ROOT/'runtime/research-loop/public-worker';runtime.mkdir(parents=True,exist_ok=True)
    with (runtime/'worker.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('Existing public worker owns lock');return
        cfg,manifest=freeze();started=time.time();mono=time.monotonic();deadline=started+cfg['lifetime_seconds'];last_bucket=None;ticks=0;reason=None
        run=ROOT/'data/public-worker/BTC'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+str(os.getpid()));run.mkdir(parents=True,exist_ok=False)
        state=dict(pid=os.getpid(),role='public_data_only',started_at_epoch=started,deadline_epoch=deadline,run=str(run.relative_to(ROOT)),ticks_completed=0,status='starting',orders=0,account_reads=0)
        save(run/'launch.json',dict(state,manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()))
        def guard():
            now=time.time()
            if now>=deadline:return 'bounded_deadline'
            if abs((now-started)-(time.monotonic()-mono))>60:return 'wallclock_discontinuity'
            try:
                checkpoint=json.loads((ROOT/'research/loop/checkpoint.json').read_text());quota_path=ROOT/'runtime/research-loop/quota-decision.json';quota=json.loads(quota_path.read_text())
                return admission(quota,quota_path.stat().st_mtime,now,checkpoint.get('pm_manual_pause'),STOP_REQUESTED or (run/'STOP').exists())
            except (OSError,ValueError):return 'quota_or_checkpoint_unreadable'
        try:
            for signum in (signal.SIGTERM,signal.SIGINT):signal.signal(signum,handle_signal)
            while True:
                reason=guard()
                if reason:break
                now=time.time()
                if now>=deadline:reason='bounded_deadline';break
                if ticks>=cfg['maximum_ticks']:reason='bounded_tick_limit';break
                bucket=int(now//900)*900000
                if last_bucket is not None and (bucket<=last_bucket or now<bucket/1000+2):
                    state.update(status='waiting_for_next_bucket');save(runtime/'status.json',state);time.sleep(15);continue
                verify_sources(manifest)
                receipt=dict(bucket=bucket,started_at_epoch=now,steps=[])
                state.update(status='collecting',current_bucket=bucket);save(runtime/'status.json',state)
                for index in range(len(COMMANDS)):
                    reason=guard()
                    if reason:break
                    try:
                        verify_sources(manifest);value=run_public_command(index,min(90,max(.001,deadline-time.time())));receipt['steps'].append(dict(command_index=index,**value))
                        if value['returncode']!=0:reason='child_failure_or_timeout';break
                        require_quality(index,bucket)
                    except Exception as exc:
                        reason='step_'+type(exc).__name__;break
                receipt.update(completed=reason is None,finished_at_epoch=time.time(),stop_reason=reason);save(run/(str(bucket)+'.json'),receipt)
                if reason:break
                ticks+=1;last_bucket=bucket;state.update(ticks_completed=ticks,last_complete_bucket=bucket,status='waiting_for_next_bucket');save(runtime/'status.json',state)
                print(json.dumps(dict(bucket=bucket,ticks_completed=ticks,status='public_tick_complete')),flush=True)
        except Exception as exc:reason=type(exc).__name__;state['error_type']=type(exc).__name__
        finally:
            state.update(status='stopped',stop_reason=reason or 'finished',stopped_at_epoch=time.time());save(run/'final.json',state);save(runtime/'status.json',state)
            print(json.dumps(dict(status='stopped',reason=state['stop_reason'],ticks=ticks)),flush=True)
if __name__=='__main__':main()
