import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.data.observation import normalize_pressure_observation
from miniquant.data.okx_public import DataError

class PressureObservationTests(unittest.TestCase):
    def envelope(self,row,ingested=36000000):
        text=json.dumps(dict(code='0',data=[dict(instId='BTC-USDT-SWAP',**row)]))
        return dict(body_text=text,body_sha256=hashlib.sha256(text.encode()).hexdigest(),ingested_at_ms=ingested)
    def test_availability_is_actual_observed_not_settlement_and_signed_values_preserved(self):
        e=self.envelope(dict(fundingTime='28800000',realizedRate='-.001',fundingRate='99'))
        r=normalize_pressure_observation('funding',e,'BTC-USDT-SWAP')
        self.assertNotEqual(r['event_time'],r['available_at']);self.assertEqual(r['values']['realized_rate'],'-0.001')
        self.assertNotIn('fundingRate',r['values']);self.assertTrue(r['fresh'])
        p=normalize_pressure_observation('premium',self.envelope(dict(ts='35990000',premium='-.0001')),'BTC-USDT-SWAP')
        self.assertEqual(p['values']['premium'],'-0.0001');self.assertTrue(p['fresh'])
    def test_future_or_missing_realized_not_filled_from_prediction(self):
        for row in [dict(fundingTime='40000000',realizedRate='.001'),dict(fundingTime='28800000',realizedRate='',fundingRate='.001')]:
            with self.assertRaises(DataError):normalize_pressure_observation('funding',self.envelope(row),'BTC-USDT-SWAP')
    def test_integrity_instrument_and_age_controls(self):
        e=self.envelope(dict(ts='1',premium='.01'))
        self.assertFalse(normalize_pressure_observation('premium',e,'BTC-USDT-SWAP')['fresh'])
        with self.assertRaises(DataError):normalize_pressure_observation('premium',e,'ETH-USDT-SWAP')
        e['body_text']+=' '
        with self.assertRaises(DataError):normalize_pressure_observation('premium',e,'BTC-USDT-SWAP')
