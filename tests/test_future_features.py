import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from miniquant.data.future_features import four_hour_features
from miniquant.data.okx_public import utc, DataError

START=1_790_000_100_000//900_000*900_000


def rows():
    return [dict(decision_at=utc(START+i*900_000),oi_available_at=utc(START+i*900_000-1),
        eligible=True,oi_contract_count=str(100+i),mid=str(1000+i),oi_sha256=str(i)) for i in range(17)]


class FutureFeaturesTests(unittest.TestCase):
    def test_complete_future_window(self):
        features=four_hour_features(rows(),START-1)
        self.assertEqual(len(features),1)
        self.assertEqual(features[0]['oi_fractional_change'],'0.16')
        self.assertEqual(features[0]['elapsed_ms'],14_400_000)

    def test_missing_bucket_or_pre_cutoff_cannot_fill(self):
        self.assertEqual(four_hour_features(rows()[1:],START),[])
        self.assertEqual(four_hour_features(rows(),START+1),[])
        self.assertEqual(four_hour_features(rows(),START),[])
        sample=rows();sample[8]['eligible']=False
        self.assertEqual(four_hour_features(sample,START),[])

    def test_zero_inventory_rejected_without_imputation(self):
        sample=rows();sample[8]['oi_contract_count']='0'
        self.assertEqual(four_hour_features(sample,START),[])

    def test_later_same_bucket_cannot_replace_earliest(self):
        sample=rows();later=dict(sample[0],decision_at=utc(START+1),mid='999999')
        self.assertEqual(four_hour_features(sample+[later],START-1),four_hour_features(sample,START-1))

    def test_future_dependency_rejected(self):
        sample=rows();sample[0]['oi_available_at']=utc(START+1)
        with self.assertRaises(DataError):four_hour_features(sample,START)

    def test_interrupted_inventory_is_resumed_not_silently_skipped(self):
        from tools import build_btc_future_features as builder
        actual=Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as temp:
            root=Path(temp)
            names=['tools/build_btc_future_features.py','src/miniquant/data/future_features.py',
                'src/miniquant/data/asof_snapshots.py','src/miniquant/data/observation.py',
                'src/miniquant/data/okx_public.py','src/miniquant/data/archive_collection.py',
                'src/miniquant/data/binance_metrics.py','research/audits/BTC-FUTURE-FEATURES-022.json']
            for name in names:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((actual/name).read_bytes())
            with patch.object(builder,'ROOT',root):
                builder.main()
                base=root/'artifacts/BTC-FUTURE-FEATURES-022'
                inventory=next((base/'inventories').iterdir())
                (inventory/'summary.json').unlink()
                builder.main()
                self.assertTrue((inventory/'summary.json').exists())
                before=(inventory/'summary.json').read_bytes()
                builder.main()
                self.assertEqual((inventory/'summary.json').read_bytes(),before)
