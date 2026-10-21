import csv,hashlib,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from urllib.error import HTTPError,URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.data.archive_collection import collect_chunk,coverage_summary
from miniquant.data.binance_metrics import FIELDS

class ArchiveCollectionTests(unittest.TestCase):
    def state(self):return dict(start='2024-01-01',end_exclusive='2024-01-02',days={})
    def fetcher(self,calls):
        s=io.StringIO();w=csv.DictWriter(s,fieldnames=sorted(FIELDS));w.writeheader();row={k:'1' for k in FIELDS};row.update(create_time='2024-01-01 00:00:00',symbol='BTCUSDT');w.writerow(row)
        f=io.BytesIO()
        with zipfile.ZipFile(f,'w') as z:z.writestr('BTCUSDT-metrics-2024-01-01.csv',s.getvalue())
        body=f.getvalue();check=(hashlib.sha256(body).hexdigest()+'  BTCUSDT-metrics-2024-01-01.zip').encode()
        def fetch(day,suffix):calls.append(suffix);return (body if not suffix else check),dict(ingested_at='observed_test')
        return fetch
    def test_partial_budget_resume_downloads_checksum_only_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            state=self.state();calls=[];fetch=self.fetcher(calls)
            self.assertEqual(collect_chunk(d,state,fetch,1,0)['status'],'budget_exhausted')
            raw=Path(d)/'raw/BTCUSDT-metrics-2024-01-01.zip';before=raw.read_bytes()
            self.assertEqual(collect_chunk(d,state,fetch,1,0)['requests'],1)
            self.assertEqual(calls,['','.CHECKSUM']);self.assertEqual(raw.read_bytes(),before)
            self.assertEqual(collect_chunk(d,state,fetch,1,0)['requests'],0)
            c=coverage_summary(state);self.assertEqual(c['incomplete_label_grid_days'],1);self.assertFalse(c['research_ready'])
    def test_corrupt_or_orphan_raw_blocks_without_invented_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            state=self.state();raw=Path(d)/'raw';raw.mkdir();(raw/'BTCUSDT-metrics-2024-01-01.zip').write_bytes(b'orphan')
            calls=[];r=collect_chunk(d,state,self.fetcher(calls),2,0)
            self.assertEqual(r['status'],'integrity_blocked');self.assertEqual(calls,[])
            self.assertEqual(collect_chunk(d,state,self.fetcher(calls),2,10000)['status'],'blocked_requires_review')
    def test_404_retained_and_access_denial_not_retried(self):
        for status in (404,451):
            with tempfile.TemporaryDirectory() as d:
                state=self.state();calls=[]
                def fetch(day,suffix):calls.append(day);raise HTTPError('https://data.binance.vision',status,'test',{},None)
                collect_chunk(d,state,fetch,2,0)
                self.assertEqual(len(calls),1)
                if status==404:self.assertEqual(state['days']['2024-01-01']['status'],'missing')
                else:
                    self.assertEqual(collect_chunk(d,state,fetch,2,10000)['status'],'blocked_requires_review');self.assertEqual(len(calls),1)
    def test_network_backoff_does_not_busy_retry(self):
        with tempfile.TemporaryDirectory() as d:
            state=self.state();calls=[]
            def fetch(day,suffix):calls.append(day);raise URLError('offline')
            collect_chunk(d,state,fetch,2,0)
            self.assertEqual(collect_chunk(d,state,fetch,2,500)['status'],'backoff_not_elapsed');self.assertEqual(len(calls),1)
    def test_existing_hash_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            state=self.state();calls=[];f=self.fetcher(calls);collect_chunk(d,state,f,1,0)
            raw=Path(d)/'raw/BTCUSDT-metrics-2024-01-01.zip';raw.write_bytes(b'changed')
            self.assertEqual(collect_chunk(d,state,f,2,0)['status'],'integrity_blocked');self.assertEqual(calls,[''])
