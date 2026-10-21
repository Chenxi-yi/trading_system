import math
import unittest
from unittest.mock import Mock
from miniquant.data.okx_public import DataError
from miniquant.research.variance_evaluation import (
    DAY,FOUR_HOURS,EvaluationNotDue,planned_anchors,qlike,calendar_bootstrap,evaluate_when_due,evaluate)

START=DAY;END=START+60*DAY


def synthetic():
    anchors=planned_anchors(START,END)
    rows=[dict(feature_at_ms=a+1000,label_available_ms=a+FOUR_HOURS+1000,next_rv=1e-5) for a in anchors]
    predictions=[]
    for row in rows:
        at=row['feature_at_ms'];fit=at//DAY*DAY
        training=sum(r['label_available_ms']<fit for r in rows)
        if training<120:continue
        predictions.append(dict(feature_at_ms=at,generated_at_ms=at+100,
            fit_at_ms=fit,training_samples=training,forecasts=dict(B0=2e-5,M1=1e-5)))
    return rows,predictions


class VarianceEvaluationTests(unittest.TestCase):
    def test_gate_does_not_call_loader(self):
        loader=Mock(side_effect=AssertionError('Must not read real labels'))
        with self.assertRaises(EvaluationNotDue):evaluate_when_due(loader,START,END,END-1)
        loader.assert_not_called()

    def test_qlike_hand_calculation_and_invalid_input(self):
        self.assertAlmostEqual(qlike(2,1)-qlike(1,1),math.log(2)-.5)
        for forecast,target in [(0,1),(1,-1),(math.inf,1)]:
            with self.assertRaises(DataError):qlike(forecast,target)

    def test_complete_positive_forecast_evidence_never_trading_admission(self):
        result=evaluate(*synthetic(),START,END)
        self.assertEqual(result['status'],'incremental_forecast_evidence')
        self.assertFalse(result['trading_qualified'])
        self.assertAlmostEqual(result['mean_qlike_gain'],math.log(2)-.5)
        self.assertEqual(result['primary']['replications'],10000)

    def test_insufficient_pairs_returns_no_score(self):
        rows,predictions=synthetic();result=evaluate(rows,predictions[:119],START,END)
        self.assertEqual(result['status'],'inconclusive')
        self.assertNotIn('mean_qlike_gain',result)

    def test_late_or_forged_training_predictions_rejected(self):
        rows,predictions=synthetic()
        for field,value in [('generated_at_ms',predictions[0]['feature_at_ms']+120001),('training_samples',9999)]:
            bad=[dict(predictions[0],**{field:value})]+predictions[1:]
            with self.assertRaises(DataError):evaluate(rows,bad,START,END)

    def test_calendar_gaps_preserved_and_bootstrap_deterministic(self):
        pairs=[(START+100,1),(START+5*DAY+100,2)]
        a=calendar_bootstrap(pairs,START,START+10*DAY,2,100)
        self.assertEqual(a,calendar_bootstrap(pairs,START,START+10*DAY,2,100))
        self.assertEqual(a['calendar_days'],10)
        self.assertGreater(a['invalid_replicates'],0)

    def test_negative_gain_cannot_pass(self):
        rows,predictions=synthetic()
        for p in predictions:p['forecasts']=dict(B0=1e-5,M1=2e-5)
        self.assertEqual(evaluate(rows,predictions,START,END)['status'],'not_supported')
