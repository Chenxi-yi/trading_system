import csv,hashlib,io,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.data.binance_metrics import audit_metrics_zip,FIELDS

class BinanceMetricsTests(unittest.TestCase):
    def blob(self,rows=None,name='BTCUSDT-metrics-2024-01-01.csv'):
        s=io.StringIO();writer=csv.DictWriter(s,fieldnames=sorted(FIELDS));writer.writeheader()
        for r in rows or [dict(create_time='2024-01-01 00:05:00',symbol='BTCUSDT')]:writer.writerow({k:r.get(k,'1') for k in sorted(FIELDS)})
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr(name,s.getvalue())
        value=b.getvalue();check=(hashlib.sha256(value).hexdigest()+'  BTCUSDT-metrics-2024-01-01.zip').encode()
        return value,check
    def test_hash_and_layout_must_match(self):
        b,c=self.blob()
        with self.assertRaises(ValueError):audit_metrics_zip(b+b'X',c,'2024-01-01')
        b,c=self.blob(name='../secret.csv')
        with self.assertRaises(ValueError):audit_metrics_zip(b,c,'2024-01-01')
    def test_missing_nan_and_duplicate_labels_remain_visible(self):
        row=dict(create_time='2024-01-01 00:05:00',symbol='BTCUSDT',sum_open_interest='NaN')
        b,c=self.blob([row,row]);a,_=audit_metrics_zip(b,c,'2024-01-01')
        self.assertEqual(a['unknown_values']['sum_open_interest'],2);self.assertEqual(a['duplicate_labels'],1)
        self.assertIsNone(a['available_at'])
    def test_wrong_symbol_negative_metric_and_zoned_time_rejected(self):
        for extra in [dict(symbol='ETHUSDT'),dict(sum_open_interest='-1'),dict(create_time='2024-01-01T00:05:00+01:00')]:
            row=dict(create_time='2024-01-01 00:05:00',symbol='BTCUSDT');row.update(extra);b,c=self.blob([row])
            with self.assertRaises(ValueError):audit_metrics_zip(b,c,'2024-01-01')
