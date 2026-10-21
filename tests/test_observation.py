import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.data.observation import normalize_observation
from miniquant.data.okx_public import DataError


class ObservationTests(unittest.TestCase):
    def envelope(self,row):return dict(body_text=json.dumps(dict(code='0',data=[row])),ingested_at_ms=100000,body_sha256='fixture')
    def test_availability_is_observation_not_source_timestamp(self):
        x=normalize_observation('open_interest',self.envelope(dict(ts='99000',instId='BTC-USDT-SWAP',oi='10',oiCcy='.1',oiUsd='8000')),'BTC-USDT-SWAP')
        self.assertNotEqual(x['event_time'],x['available_at']);self.assertEqual(x['available_at'],x['ingested_at']);self.assertTrue(x['fresh'])
    def test_crossed_or_empty_book_rejected(self):
        for bids,asks in [([['101','1']],[['100','1']]),([],[['100','1']])]:
            with self.assertRaises(DataError):normalize_observation('books',self.envelope(dict(ts='99000',bids=bids,asks=asks)),'BTC-USDT')
    def test_stale_data_retained_but_flagged_and_no_unit_conversion(self):
        x=normalize_observation('books',self.envelope(dict(ts='1000',bids=[['99','1']],asks=[['101','2']])),'BTC-USDT-SWAP')
        self.assertFalse(x['fresh']);self.assertEqual(x['values']['bids'][0][1],'1')
    def test_negative_oi_or_wrong_instrument_rejected(self):
        for inst,oi in [('BTC-USDT-SWAP','-1'),('OTHER','1')]:
            with self.assertRaises(DataError):normalize_observation('open_interest',self.envelope(dict(ts='99000',instId=inst,oi=oi,oiCcy='1',oiUsd='1')),'BTC-USDT-SWAP')
