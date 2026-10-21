import errno,json,sys,tempfile,unittest
from pathlib import Path
from urllib.error import URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tests.test_archive_collection as fixtures
from miniquant.data.archive_collection import collect_chunk
from tools.observe_archive_transport import observe

class TransportObservationTests(unittest.TestCase):
    def test_network_exception_sanitized_without_changed_retry(self):
        with tempfile.TemporaryDirectory() as d:
            state=fixtures.ArchiveCollectionTests().state();calls=[]
            def fetch(*args):calls.append(args);raise URLError(ConnectionRefusedError(errno.ECONNREFUSED,'SECRET_TEST_DO_NOT_LOG'))
            result,events=observe(lambda:collect_chunk(d,state,fetch,2,0))
            self.assertEqual(result['requests'],1);self.assertEqual(len(calls),1);self.assertEqual(events,[dict(exception_type='URLError',reason_type='ConnectionRefusedError',errno=errno.ECONNREFUSED)])
            self.assertNotIn('SECRET_TEST',json.dumps(events));self.assertEqual(state['retry_after_epoch'],600);self.assertIsNone(sys.gettrace())
            result,events=observe(lambda:collect_chunk(d,state,fetch,2,10));self.assertEqual(result['status'],'backoff_not_elapsed');self.assertEqual(events,[]);self.assertEqual(len(calls),1)
    def test_success_results_identical_and_no_network_events(self):
        with tempfile.TemporaryDirectory() as d:
            fixture=fixtures.ArchiveCollectionTests();state=fixture.state();calls=[]
            result,events=observe(lambda:collect_chunk(d,state,fixture.fetcher(calls),2,0))
            self.assertEqual(result['status'],'collection_finished_coverage_not_certified');self.assertEqual(events,[]);self.assertEqual(calls,['','.CHECKSUM']);self.assertIsNone(sys.gettrace())
