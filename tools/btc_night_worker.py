"""Approved non-interactive continuation pipeline; finite retries and OS lock.

No exchange account or order calls. Resume this command only if no worker lock is held.
"""
import fcntl,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import atomic_json


def main():
 runtime=ROOT/'runtime/overnight';runtime.mkdir(parents=True,exist_ok=True)
 with (runtime/'worker.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:print('Worker already active; exiting');return
  python=sys.executable
  def run(script):
   print('RUN',script,flush=True)
   result=subprocess.run([python,str(ROOT/script)],cwd=ROOT)
   if result.returncode:raise RuntimeError(f'{script} exited {result.returncode}')
  # Acquires collector lock; if first collector remains active it safely returns.
  for attempt in range(12):
   run('tools/collect_btc_overnight.py')
   state=json.loads((ROOT/'data/market-audit/btc-overnight-20261021/checkpoint.json').read_text())
   if all(j['status']!='collecting' for j in state['jobs']):break
   time.sleep(30)
  else:raise RuntimeError('Collector retry budget exceeded')
  run('tools/materialize_btc_overnight.py')
  if not(ROOT/'artifacts/BTC-NIGHT-001/summary.json').exists():run('tools/run_btc_night.py')
  for attempt in range(180):
   p=ROOT/'data/market-audit/btc-perp-mark-20261021/mark_BTC-USDT-SWAP_4H.json'
   if p.exists():break
   if attempt%6==0:run('tools/collect_btc_perp_mark.py')
   time.sleep(10)
  else:raise RuntimeError('Mark data wait budget exceeded')
  if not(ROOT/'data/funding-archive/BTC-USDT-SWAP/manifest.json').exists():run('tools/collect_okx_funding_archive.py')
  run('tools/run_btc_perpetual_night.py')
  run('tools/check_btc_grid_resolution.py')
  if(ROOT/'tools/report_btc_night.py').exists():run('tools/report_btc_night.py')
  atomic_json(runtime/'worker-status.json',dict(status='research_runs_finished',time=time.time(),orders_sent=0))


if __name__=='__main__':
 try:main()
 except Exception as exc:
  print(type(exc).__name__,str(exc),flush=True)
  atomic_json(ROOT/'runtime/overnight/worker-status.json',dict(status='failed',error=type(exc).__name__,message=str(exc),time=time.time(),orders_sent=0))
  raise
