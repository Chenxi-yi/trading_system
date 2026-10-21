"""Create and verify an explicit public-research bundle. No credentials/account state.

A local recovery copy is not an off-device backup. Refuse dirty tracked sources,
symlinks, non-allowlisted data roots and accidental private tracked config files.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.okx_market_audit import atomic_json

PUBLIC_ROOTS = (
    'data/market-audit/btc-overnight-20261021',
    'data/market-audit/btc-perp-mark-20261021',
    'data/funding-archive/BTC-USDT-SWAP',
    'artifacts/BTC-NIGHT-001',
    'artifacts/BTC-NIGHT-001-PERP',
    'artifacts/BTC-LOOP-002',
    'artifacts/BTC-LOOP-003',
    'artifacts/BTC-LOOP-007',
    'artifacts/BTC-LOOP-008',
    'artifacts/BTC-EVENT-004',
    'artifacts/BTC-MATCH-005',
    'artifacts/BTC-PRESSURE-DATA-006',
    'artifacts/BTC-DERIVATIVES-DATA-009',
    'artifacts/BTC-DERIVATIVES-COLLECT-010',
    'artifacts/BTC-DERIVATIVES-RECHECK-011',
    'artifacts/BTC-ARCHIVE-TRANSPORT-012',
    'artifacts/BTC-DERIVATIVES-COLLECT-013',
    'artifacts/BTC-DERIVATIVES-COVERAGE-014',
    'artifacts/BTC-METRICS-CONTRACT-015',
    'artifacts/BTC-BINANCE-FORWARD-016',
    'artifacts/BTC-OKX-UNITS-017',
    'artifacts/BTC-OKX-SAVED-UNITS-018',
    'artifacts/BTC-HTTP-DIAGNOSTIC-019',
    'artifacts/BTC-CAUSAL-SNAPSHOT-020',
    'artifacts/BTC-FUTURE-FEATURES-021',
    'artifacts/BTC-FUTURE-FEATURES-022',
    'data/binance-metrics/BTCUSDT-2023-2026-retry-v2',
    'data/binance-metrics/BTCUSDT-2023-2026',
    'data/market-audit/btc-long-index-20261021',
    'data/forward-observation/BTC',
    'data/forward-pressure/BTC',
    'data/forward-binance/BTC',
    'data/market-audit/20261020T154059431686Z/instrumentsSWAP.json',
)


def main():
    if subprocess.run(['git', 'diff', '--quiet', 'HEAD'], cwd=ROOT).returncode:
        raise ValueError('Commit tracked work before creating recovery checkpoint')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [ROOT / p for p in tracked if p]
    if any(p.name == 'config.toml' or 'config/local' in str(p.relative_to(ROOT)) or p.name.startswith('.env') and p.name != '.env.example' for p in paths):
        raise ValueError('Private configuration tracked; refusing to package')
    for name in PUBLIC_ROOTS:
        public = ROOT / name
        if public.is_file():
            paths.append(public)
        else:
            paths.extend(p for p in public.rglob('*') if p.is_file() and p.suffix not in ('.lock', '.tmp'))
    paths = sorted(set(paths))
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('Only regular files are allowed')
    entries = {str(p.relative_to(ROOT)): dict(size=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
    manifest = dict(git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    files=entries, public_data_roots=PUBLIC_ROOTS, excludes='No config.toml, config/local, runtime, account snapshots or private ledgers')
    out = ROOT / 'artifacts/recovery'
    out.mkdir(exist_ok=True)
    target = out / ('BTC-NIGHT-001-' + manifest['git_head'][:12] + '.tar.gz')
    if target.exists():
        raise ValueError('Checkpoint already exists; do not silently replace')
    # Open with restrictive permissions at creation, not only after writing.
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream, tarfile.open(fileobj=stream, mode='w:gz', compresslevel=3) as archive:
        for p in paths:
            archive.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
    # Verify every archived byte; then extract only safe allowlisted regular paths
    # into a disposable tree and run tests plus a real preserved selected replay.
    with tempfile.TemporaryDirectory(prefix='btc-restore-') as temp:
        restore = Path(temp)
        with tarfile.open(target, 'r:gz') as archive:
            members = archive.getmembers()
            if len(members) != len(entries):
                raise ValueError('Archive membership mismatch')
            for member in members:
                if not member.isfile() or member.name not in entries or '..' in Path(member.name).parts or Path(member.name).is_absolute():
                    raise ValueError('Unsafe or unexpected archive entry')
                content = archive.extractfile(member).read()
                if hashlib.sha256(content).hexdigest() != entries[member.name]['sha256']:
                    raise ValueError('Archive content hash mismatch')
                dest = restore / member.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
        tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=restore, capture_output=True, text=True, timeout=60)
        if tests.returncode:
            raise ValueError('Restored offline tests failed: ' + tests.stderr[-2000:])
        code = """
import json,sys
from pathlib import Path
sys.path.insert(0,'src');sys.path.insert(0,'.')
from tools.run_btc_night import load_bars,stamp
from miniquant.backtest.replay import replay
name='trend_90_2024-01-01_2026-01-01_base.json'
prior=json.loads((Path('artifacts/BTC-NIGHT-001/runs')/name).read_text())
bars=load_bars(Path('data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'))
value=replay(bars,'trend',90,stamp('2024-01-01'),stamp('2026-01-01'))
assert value.daily == prior['daily'], 'Restored selected replay differs'
print('Restored selected BTC replay matches preserved daily NAV exactly')
"""
        replay = subprocess.run([sys.executable, '-c', code], cwd=restore, capture_output=True, text=True, timeout=60)
        if replay.returncode:
            raise ValueError('Restored replay failed: ' + replay.stderr[-2000:])
    manifest.update(archive=str(target.relative_to(ROOT)), archive_bytes=target.stat().st_size,
                    archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    restored_tests=tests.stderr[-300:], restored_replay=replay.stdout.strip(),
                    local_only=True, off_device_backup=False)
    atomic_json(out / (target.name + '.manifest.json'), manifest)
    os.chmod(out / (target.name + '.manifest.json'), 0o600)
    atomic_json(out / 'manifest.json', manifest)
    os.chmod(out / 'manifest.json', 0o600)
    print(json.dumps({k:manifest[k] for k in ('git_head', 'archive', 'archive_bytes', 'archive_sha256', 'restored_replay', 'local_only')}, indent=2))


if __name__ == '__main__':
    main()
