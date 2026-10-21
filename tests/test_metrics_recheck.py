import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tests.test_archive_collection as fixtures
from miniquant.data.archive_collection import collect_chunk
from tools.recheck_binance_metrics import recheck

class MetricsRecheckTests(unittest.TestCase):
    def fixture(self,path):
        helper=fixtures.ArchiveCollectionTests();state=helper.state();collect_chunk(path,state,helper.fetcher([]),2,0);return state
    def test_completed_cache_corruption_detected_despite_collector_skip(self):
        with tempfile.TemporaryDirectory() as d:
            state=self.fixture(d);self.assertTrue(recheck(d)['integrity_recheck_passed'])
            p=Path(d)/'raw/BTCUSDT-metrics-2024-01-01.zip';p.write_bytes(b'corrupted')
            self.assertEqual(collect_chunk(d,state,lambda *a:self.fail('No request allowed'),2,1000)['requests'],0)
            with self.assertRaisesRegex(ValueError,'SHA256'):recheck(d)
    def test_summary_tampering_detected_and_incomplete_grid_remains_visible(self):
        with tempfile.TemporaryDirectory() as d:
            self.fixture(d);out=recheck(d);self.assertEqual(out['incomplete_label_grid_days'],['2024-01-01']);self.assertFalse(out['coverage']['research_ready'])
            p=Path(d)/'checkpoint.json';state=json.loads(p.read_text());state['days']['2024-01-01']['rows']=999;p.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'summary differs'):recheck(d)
