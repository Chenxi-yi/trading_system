import copy
import unittest
from datetime import datetime,timezone
from miniquant.data.asof_snapshots import join_snapshots
from miniquant.data.okx_public import DataError


def stamp(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
NOW=1_790_000_000_000


def row(kind,received,event=None):
    return dict(kind=kind,venue='OKX',environment='public_market',inst_id='BTC-USDT-SWAP',
                available_at=stamp(received),ingested_at=stamp(received),event_time=stamp(event or received),
                source_sha256=str(received),values=dict(oi='10',bids=[['100','1']],asks=[['101','1']]))


class AsOfTests(unittest.TestCase):
    def test_future_received_OI_cannot_influence_decision(self):
        oi=row('open_interest',NOW-1000);book=row('books',NOW)
        expected=join_snapshots([oi],[book])
        future=row('open_interest',NOW+1,NOW-100);future['values']['oi']='999999'
        self.assertEqual(join_snapshots([oi,future],[book]),expected)
        self.assertTrue(expected[0]['eligible'])

    def test_no_prior_or_stale_source_not_filled(self):
        book=row('books',NOW)
        self.assertFalse(join_snapshots([row('open_interest',NOW+1)],[book])[0]['eligible'])
        self.assertEqual(join_snapshots([row('open_interest',NOW-60_001)],[book])[0]['reason'],'stale_OI_no_gap_fill')
        self.assertFalse(join_snapshots([row('open_interest',NOW)],[row('books',NOW,NOW-30_001)])[0]['eligible'])

    def test_conflicting_reception_and_future_source_rejected(self):
        source=row('open_interest',NOW);other=copy.deepcopy(source);other['values']['oi']='11'
        with self.assertRaises(DataError):join_snapshots([source,other],[row('books',NOW)])
        with self.assertRaises(DataError):join_snapshots([row('open_interest',NOW,NOW+1)],[row('books',NOW)])

    def test_identity_and_actual_reception_contract_rejected(self):
        for field,value in [('inst_id','ETH-USDT-SWAP'),('available_at',stamp(NOW-1))]:
            source=row('open_interest',NOW);source[field]=value
            with self.assertRaises(DataError):join_snapshots([source],[row('books',NOW)])

    def test_order_invariance_and_identical_duplicate(self):
        a=row('open_interest',NOW-1000);b=row('open_interest',NOW)
        books=[row('books',NOW-500),row('books',NOW+500)]
        self.assertEqual(join_snapshots([b,a,a],list(reversed(books))),join_snapshots([a,b],books))
