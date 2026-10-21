import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.collect_binance_metrics_retry as cli
import tests.test_archive_collection as fixtures
from miniquant.data.archive_collection import collect_chunk

class RetryLineageTests(unittest.TestCase):
    def setup_parent(self,root):
        parent=root/'parent';helper=fixtures.ArchiveCollectionTests();s=helper.state();collect_chunk(parent,s,helper.fetcher([]),2,0)
        s.update(retry_after_epoch=10**12,last_error=dict(error_type='URLError'));(parent/'checkpoint.json').write_text(json.dumps(s))
        cfg=root/'research/audits/BTC-DERIVATIVES-COLLECT-013.json';cfg.parent.mkdir(parents=True);cfg.write_text(json.dumps(dict(start=s['start'],end_exclusive=s['end_exclusive'],new_root='child',parent_root='parent')))
        for n in ['tools/collect_binance_metrics_retry.py','src/miniquant/data/archive_retry.py','tools/recheck_binance_metrics.py','src/miniquant/data/archive_collection.py','src/miniquant/data/binance_metrics.py','src/miniquant/data/okx_public.py']:
            p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test source bytes')
        return parent
    def test_import_preserves_parent_metadata_backoff_and_freezes_new_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);parent=self.setup_parent(root);before={p.name:p.read_bytes() for p in (parent/'raw').iterdir()};state_before=(parent/'checkpoint.json').read_bytes()
            with patch.object(cli,'ROOT',root),patch.object(sys,'argv',['tool']),patch.object(cli,'MetricsFetcher',return_value=lambda *args:self.fail('No HTTP before parent backoff')):
                cli.main();self.assertEqual((parent/'checkpoint.json').read_bytes(),state_before)
                for name,body in before.items():self.assertEqual((root/'child/raw'/name).read_bytes(),body)
                child=json.loads((root/'child/checkpoint.json').read_text());self.assertEqual(child['retry_after_epoch'],10**12);self.assertEqual(child['inherited_last_error'],dict(error_type='URLError'));self.assertEqual(child['total_request_attempts'],2)
                (root/'src/miniquant/data/archive_retry.py').write_text('changed')
                with self.assertRaisesRegex(ValueError,'source changed'):cli.main()
    def test_corrupt_parent_rejected_before_child_or_requests(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);parent=self.setup_parent(root);(parent/'raw/BTCUSDT-metrics-2024-01-01.zip').write_bytes(b'broken')
            with patch.object(cli,'ROOT',root),patch.object(sys,'argv',['tool']),patch.object(cli,'MetricsFetcher',side_effect=AssertionError('No HTTP allowed')):
                with self.assertRaisesRegex(ValueError,'SHA256'):cli.main()
            self.assertFalse((root/'child').exists())
