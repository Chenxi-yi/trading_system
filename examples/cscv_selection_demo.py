"""Original CSCV teaching example, not a production validation engine.

Score: arithmetic mean of supplied per-period returns/scores, NOT Sharpe.
Rows are synchronous observations; columns are fixed candidates.
IS ties: average their OOS outcomes (equivalent to uniform tie selection).
OOS ties: midrank. Report strict below-median and exact median separately.
"""

from itertools import combinations
from math import isfinite, log
from statistics import mean


def cscv_mean(matrix, blocks=4):
    rows = [tuple(row) for row in matrix]
    if not rows or len(rows[0]) < 2:
        raise ValueError("Require observations and at least two candidates")
    n = len(rows[0])
    if any(len(row) != n for row in rows):
        raise ValueError("Rows must be rectangular and synchronous")
    if any(not isfinite(value) for row in rows for value in row):
        raise ValueError("Missing or non-finite observations are not allowed")
    if not isinstance(blocks, int) or blocks < 2 or blocks % 2:
        raise ValueError("Block count must be an even integer >= 2")
    if len(rows) < blocks or len(rows) % blocks:
        raise ValueError("Require equal nonempty contiguous blocks; no silent truncation")
    block_size = len(rows) // blocks
    splits = []
    for chosen in combinations(range(blocks), blocks // 2):
        train = [row for i, row in enumerate(rows) if i // block_size in chosen]
        test = [row for i, row in enumerate(rows) if i // block_size not in chosen]
        train_scores = [mean(row[j] for row in train) for j in range(n)]
        test_scores = [mean(row[j] for row in test) for j in range(n)]
        best = max(train_scores)
        winners = [j for j, score in enumerate(train_scores) if score == best]
        outcomes = []
        for j in winners:
            score = test_scores[j]
            lower = sum(other < score for other in test_scores)
            equal = sum(other == score for other in test_scores)
            rank = lower + (equal + 1) / 2
            omega = rank / (n + 1)
            outcomes.append({
                "candidate": j, "oos_score": score, "rank": rank,
                "logit": log(omega / (1 - omega)),
                "below_median": rank < (n + 1) / 2,
                "at_median": rank == (n + 1) / 2,
            })
        splits.append({
            "is_blocks": chosen,
            "outcomes": outcomes,
            "below_fraction": mean(o["below_median"] for o in outcomes),
            "median_fraction": mean(o["at_median"] for o in outcomes),
        })
    return {
        "pbo_strict": mean(s["below_fraction"] for s in splits),
        "median_mass": mean(s["median_fraction"] for s in splits),
        "split_count": len(splits),
        "splits": splits,
    }


DEMO = [
    [9, 3, -4, 1],
    [8, 3, -5, 1],
    [-5, 3, 8, 1],
    [-4, 3, 9, 1],
]


if __name__ == "__main__":
    result = cscv_mean(DEMO)
    print("Synthetic scores; not real market data and not Sharpe.")
    for split in result["splits"]:
        outcomes = ", ".join(
            f"{'ABCD'[o['candidate']]}: OOS={o['oos_score']:g}, "
            f"rank={o['rank']:g}, logit={o['logit']:.3f}"
            for o in split["outcomes"]
        )
        print(f"IS blocks {tuple(i + 1 for i in split['is_blocks'])}: {outcomes}")
    print(f"PBO (strict below median) = {result['pbo_strict']:.2%}")
    shifted = cscv_mean([[value - 10 for value in row] for row in DEMO])
    print(f"After subtracting 10 from every score: PBO = {shifted['pbo_strict']:.2%}")
    print("All shifted scores are negative: relative ranks do not measure profitability.")
