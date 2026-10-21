"""Fixed four-hour descriptive features. No alpha, labels, or gap filling."""
from miniquant.data.asof_snapshots import milliseconds
from miniquant.data.okx_public import DataError, number


def four_hour_features(rows, cutoff_ms):
    points = {}
    for row in sorted(rows, key=lambda r:milliseconds(r['decision_at'])):
        received=milliseconds(row['decision_at'])
        if received < cutoff_ms or not row['eligible']:
            continue
        if milliseconds(row['oi_available_at']) < cutoff_ms:
            continue
        if milliseconds(row['oi_available_at']) > received:
            raise DataError('Future OI feature input')
        if number(row['oi_contract_count']) <= 0 or number(row['mid']) <= 0:
            continue
        points.setdefault(received//900_000, row)
    features=[]
    for end in sorted(points):
        if not all(index in points for index in range(end-16,end+1)):
            continue
        start,last=points[end-16],points[end]
        elapsed=milliseconds(last['decision_at'])-milliseconds(start['decision_at'])
        if not 13_500_000 <= elapsed <= 15_300_000:
            continue
        features.append(dict(decision_at=last['decision_at'],start_at=start['decision_at'],
            elapsed_ms=elapsed,observations=17,
            oi_fractional_change=str(number(last['oi_contract_count'])/number(start['oi_contract_count'])-1),
            mid_fractional_change=str(number(last['mid'])/number(start['mid'])-1),
            start_oi_sha256=start['oi_sha256'],end_oi_sha256=last['oi_sha256'],
            overlapping_descriptive_feature=True,pnl_generated=False))
    return features
