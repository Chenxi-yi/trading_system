import copy,json,hashlib
import unittest
from datetime import datetime,timezone
from urllib.request import Request
from urllib.error import HTTPError
from unittest.mock import Mock
from miniquant.data.instrument_master import master,check_units
from miniquant.data.okx_public import DataError

NOW=1_790_000_000_000


def raw(kind,received,row):
    path='instruments?instType=SWAP' if kind=='master' else 'open-interest?instType=SWAP&instId=BTC-USDT-SWAP'
    text=json.dumps(dict(code='0',data=[row]))
    return dict(url='https://openapi.okx.com/api/v5/public/'+path,ingested_at_ms=received,
        body_text=text,body_sha256=hashlib.sha256(text.encode()).hexdigest())


def specification(received,**changes):
    row=dict(instId='BTC-USDT-SWAP',instType='SWAP',ctType='linear',ctVal='.01',ctMult='1',
        ctValCcy='BTC',settleCcy='USDT',lotSz='.01',minSz='.01',tickSz='.1',state='live')
    row.update(changes);return master(raw('master',received,row))


def oi(received,count='100',coins='1'):
    return raw('oi',received,dict(instType='SWAP',instId='BTC-USDT-SWAP',oi=count,oiCcy=coins))


class InstrumentMasterTests(unittest.TestCase):
    def test_future_master_never_backfills_old_OI(self):
        report=check_units([specification(NOW+100)],[oi(NOW)],NOW+200,NOW-100)
        self.assertEqual(report['checks'][0]['status'],'no_prior_master')
        self.assertFalse(report['study_supported'])

    def test_face_change_invalidates_but_tick_change_only_reviews_execution(self):
        old=specification(NOW-1000)
        changed=specification(NOW,ctVal='.001')
        result=check_units([old,changed],[oi(NOW+1,coins='.1')],NOW+2,NOW-10)
        self.assertTrue(result['unit_break_detected'])
        self.assertFalse(result['study_supported'])
        result=check_units([old,specification(NOW,tickSz='.01')],[oi(NOW+1)],NOW+2,NOW-10)
        self.assertTrue(result['study_supported']);self.assertEqual(len(result['execution_review_changes']),1)

    def test_zero_not_deleveraging_and_poststart_unit_error_invalidates(self):
        old=specification(NOW-1000)
        result=check_units([old],[oi(NOW,'0','0')],NOW+1,NOW-10)
        self.assertEqual(result['checks'][0]['status'],'zero_not_checkable')
        self.assertFalse(result['unit_break_detected'])
        self.assertTrue(check_units([old],[oi(NOW,coins='2')],NOW+1,NOW-10)['unit_break_detected'])

    def test_stale_master_or_tampered_raw_refused(self):
        self.assertFalse(check_units([specification(NOW-27*3600000)],[oi(NOW)],NOW,NOW-1)['study_supported'])
        envelope=oi(NOW);envelope['body_text']='{}'
        with self.assertRaises(DataError):check_units([specification(NOW-1000)],[envelope],NOW,NOW-1)

    def test_counted_physical_failures_and_daily_boundary(self):
        from tools.observe_btc_master import CountedOpener
        day=datetime.now(timezone.utc).strftime('%Y-%m-%d');inner=Mock()
        inner.open.side_effect=HTTPError('https://test',500,'sensitive',{},None)
        counted=CountedOpener(inner,day)
        request=Request('https://openapi.okx.com/api/v5/public/time',method='GET')
        for _ in range(6):
            with self.assertRaises(HTTPError):counted.open(request,timeout=10)
        with self.assertRaises(DataError):counted.open(request,timeout=10)
        self.assertEqual(inner.open.call_count,6)
        self.assertFalse(counted.events[0]['access_block'])
        inner.open.side_effect=HTTPError('https://test',403,'sensitive',{},None)
        counted=CountedOpener(inner,day)
        with self.assertRaises(HTTPError):counted.open(request,timeout=10)
        with self.assertRaises(DataError):counted.open(request,timeout=10)
        self.assertTrue(counted.events[0]['access_block'])
        counted=CountedOpener(inner,'1900-01-01')
        with self.assertRaises(DataError):counted.open(request,timeout=10)

    def test_numeric_format_does_not_falsely_flag_change(self):
        report=check_units([specification(NOW-1000),specification(NOW,ctVal='0.01000',ctMult='1.0')],
            [oi(NOW+1)],NOW+2,NOW-10)
        self.assertEqual(report['material_changes'],[])
