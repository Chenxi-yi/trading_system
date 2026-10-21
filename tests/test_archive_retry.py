import json,ssl,sys,tempfile,unittest
from pathlib import Path
from urllib.error import HTTPError,URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.data.archive_retry import collect_retry_chunk
import tests.test_archive_collection as fixtures

class ArchiveRetryTests(unittest.TestCase):
    def setup_case(self):
        f=fixtures.ArchiveCollectionTests();calls=[];clock=[1000.]
        return f.state(),f.fetcher(calls),calls,clock,lambda delay:clock.__setitem__(0,clock[0]+delay)
    def test_eof_retry_counts_failure_and_success_within_budget(self):
        with tempfile.TemporaryDirectory() as d:
            s,f,c,t,sleep=self.setup_case();attempts=[]
            def fetch(*args):
                attempts.append(args)
                if len(attempts)==1:raise URLError(ssl.SSLEOFError(8,'SECRET_NOT_SAVED'))
                return f(*args)
            out=collect_retry_chunk(Path(d),s,fetch,3,lambda:t[0],sleep)
            self.assertEqual(out['requests'],3);self.assertEqual(out['tls_retries'],1);self.assertEqual(s['total_request_attempts'],3);self.assertEqual(s['days']['2024-01-01']['status'],'verified');self.assertNotIn('SECRET',json.dumps(s));self.assertEqual(t[0],1002.)
    def test_max_two_retries_then_backoff_and_no_busy_retry(self):
        with tempfile.TemporaryDirectory() as d:
            s,f,c,t,sleep=self.setup_case();attempts=[]
            def fetch(*args):attempts.append(args);raise URLError(ssl.SSLEOFError(8,'eof'))
            out=collect_retry_chunk(Path(d),s,fetch,100,lambda:t[0],sleep)
            self.assertEqual(out['requests'],3);self.assertEqual(out['tls_retries'],2);self.assertEqual(s['retry_after_epoch'],1607.)
            again=collect_retry_chunk(Path(d),s,fetch,100,lambda:t[0],sleep);self.assertEqual(again['requests'],0);self.assertEqual(len(attempts),3)
    def test_budget_does_not_expand_on_failed_get(self):
        with tempfile.TemporaryDirectory() as d:
            s,f,c,t,sleep=self.setup_case()
            def fetch(*args):raise URLError(ssl.SSLEOFError(8,'eof'))
            out=collect_retry_chunk(Path(d),s,fetch,1,lambda:t[0],sleep);self.assertEqual(out['requests'],1);self.assertEqual(out['tls_retries'],0);self.assertEqual(s['retry_after_epoch'],1600.)
    def test_no_retry_access_denial_certificate_or_other_network_error(self):
        errors=[HTTPError('https://data.binance.vision',451,'blocked',{},None),URLError(ssl.SSLCertVerificationError(1,'cert')),URLError(TimeoutError('timeout'))]
        for failure in errors:
            with tempfile.TemporaryDirectory() as d:
                s,f,c,t,sleep=self.setup_case();attempts=[]
                def fetch(*args):attempts.append(args);raise failure
                out=collect_retry_chunk(Path(d),s,fetch,100,lambda:t[0],sleep);self.assertEqual(len(attempts),1);self.assertEqual(out['tls_retries'],0)
    def test_partial_zip_preserved_when_checksum_eof_retries(self):
        with tempfile.TemporaryDirectory() as d:
            s,f,c,t,sleep=self.setup_case();checksum_calls=[]
            def fetch(day,suffix):
                if suffix:
                    checksum_calls.append(suffix)
                    if len(checksum_calls)==1:raise URLError(ssl.SSLEOFError(8,'eof'))
                return f(day,suffix)
            out=collect_retry_chunk(Path(d),s,fetch,3,lambda:t[0],sleep);self.assertEqual(out['requests'],3);self.assertEqual(c,['','.CHECKSUM']);self.assertEqual(s['days']['2024-01-01']['status'],'verified')
