import math
import unittest
from miniquant.data.okx_public import utc,DataError
from miniquant.research.oi_variance import samples,predict,rv,BUCKET

START=1_790_000_000_000//14_400_000*14_400_000


def fixtures():
    joined=[];books=[]
    for i in range(33):
        at=START+i*BUCKET;mid=100+i
        book=dict(kind='books',venue='OKX',environment='public_market',inst_id='BTC-USDT-SWAP',
            available_at=utc(at),ingested_at=utc(at),event_time=utc(at),source_sha256=str(i),
            values=dict(bids=[[str(mid-.1),'1']],asks=[[str(mid+.1),'1']]))
        books.append(book)
        if i<17:joined.append(dict(eligible=True,decision_at=utc(at),oi_available_at=utc(at),
            oi_contract_count=str(100-i),mid=str(mid)))
    return joined,books


def training():
    rows=[]
    for i in range(125):
        past=1e-6*(1+(i%17)/20);contraction=(i%7)/100
        rows.append(dict(feature_at_ms=START-(140-i)*14_400_000,
            label_available_ms=START-(139-i)*14_400_000,past_rv=past,
            contraction=contraction,next_rv=math.exp(-2+.7*math.log(past+1e-12)+.4*contraction)))
    return rows


class OIVarianceTests(unittest.TestCase):
    def test_future_OI_not_required_for_price_target(self):
        joined,books=fixtures();result=samples(joined,books,START)
        self.assertEqual(len(result),1)
        self.assertIsNotNone(result[0]['next_rv'])
        self.assertEqual(result[0]['feature_at_ms'],START+16*BUCKET)
        self.assertEqual(result[0]['label_available_ms'],START+32*BUCKET)

    def test_missing_future_price_keeps_unlabelled_features(self):
        joined,books=fixtures();result=samples(joined,books[:25]+books[26:],START)
        self.assertEqual(len(result),1)
        self.assertIsNone(result[0]['next_rv'])
        self.assertIsNone(result[0]['label_available_ms'])

    def test_future_price_changes_label_never_past_features(self):
        joined,books=fixtures();before=samples(joined,books,START)[0]
        books[-1]['values']=dict(bids=[['999','1']],asks=[['1001','1']])
        after=samples(joined,books,START)[0]
        self.assertEqual(before['past_rv'],after['past_rv'])
        self.assertEqual(before['contraction'],after['contraction'])
        self.assertNotEqual(before['next_rv'],after['next_rv'])

    def test_daily_fit_excludes_future_labels(self):
        data=training();point=dict(feature_at_ms=START,past_rv=1.1e-6,contraction=.02)
        expected=predict(data,point,START)
        self.assertIsNotNone(expected)
        late=dict(data[-1],label_available_ms=START,next_rv=999)
        self.assertEqual(predict(data+[late],point,START),expected)
        self.assertGreater(expected['forecasts']['M1'],0)

    def test_minimum_samples_and_future_features(self):
        point=dict(feature_at_ms=START,past_rv=1e-6,contraction=.02)
        self.assertIsNone(predict(training()[:119],point,START))
        with self.assertRaises(DataError):predict(training(),dict(point,feature_at_ms=START+1),START)

    def test_rank_deficiency_and_nonfinite_RV_rejected(self):
        data=training()
        for row in data:row['contraction']=0
        with self.assertRaises(DataError):predict(data,dict(feature_at_ms=START,past_rv=1e-6,contraction=0),START)
        with self.assertRaises(DataError):rv([float('inf')]*17)
