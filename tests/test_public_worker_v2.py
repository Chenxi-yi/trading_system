import unittest,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
from tools.observe_btc_worker_v2 import inherited_code
from tools import observe_btc_worker as worker

class WorkerV2Tests(unittest.TestCase):
    def test_unrelated_files_do_not_expand_frozen_closure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'required.py').write_text('required');h=hashlib.sha256((p/'required.py').read_bytes()).hexdigest();manifest={'code':{'required.py':h},'inputs':{}}
            with patch.object(worker,'ROOT',p):
                (p/'unrelated_research.py').write_text('new');worker.verify_sources(manifest)
                (p/'required.py').write_text('changed')
                with self.assertRaises(ValueError):worker.verify_sources(manifest)
    def test_parent_source_cannot_be_overridden(self):
        with self.assertRaises(ValueError):inherited_code({'old.py':'frozen'},{'old.py':'new'})
        self.assertEqual(inherited_code({'old.py':'frozen'},{'wrapper.py':'new'}),{'old.py':'frozen','wrapper.py':'new'})
