import unittest

from examples.cscv_selection_demo import DEMO, cscv_mean


class CSCVTeachingTests(unittest.TestCase):
    def test_hand_calculated_example(self):
        result = cscv_mean(DEMO)
        self.assertEqual(result["split_count"], 6)
        self.assertAlmostEqual(result["pbo_strict"], 2 / 6)
        self.assertEqual(result["median_mass"], 0)
        first = result["splits"][0]["outcomes"][0]
        self.assertEqual(first["candidate"], 0)
        self.assertEqual(first["rank"], 1)
        self.assertEqual(first["oos_score"], -4.5)

    def test_constant_dominant_candidate(self):
        result = cscv_mean([[4, 2, 1]] * 4)
        self.assertEqual(result["pbo_strict"], 0)

    def test_zero_pbo_can_coexist_with_all_losses(self):
        result = cscv_mean([[-1, -2, -3]] * 4)
        self.assertEqual(result["pbo_strict"], 0)
        self.assertTrue(all(o["oos_score"] < 0 for s in result["splits"]
                            for o in s["outcomes"]))

    def test_ties_are_visible_not_arbitrarily_selected(self):
        result = cscv_mean([[1, 1, 1]] * 4)
        self.assertEqual(result["median_mass"], 1)
        self.assertEqual(len(result["splits"][0]["outcomes"]), 3)

    def test_candidate_permutation_preserves_result(self):
        permuted = [[row[j] for j in (3, 1, 0, 2)] for row in DEMO]
        self.assertEqual(cscv_mean(permuted)["pbo_strict"],
                         cscv_mean(DEMO)["pbo_strict"])

    def test_invalid_inputs_rejected(self):
        for matrix, blocks in [
            ([], 4), ([[1]] * 4, 4), ([[1, 2], [1]] * 2, 4),
            ([[float("nan"), 2]] * 4, 4), (DEMO, 3), (DEMO, 6),
            (DEMO + [[1, 2, 3, 4]], 4),
        ]:
            with self.subTest(matrix=matrix, blocks=blocks):
                with self.assertRaises(ValueError):
                    cscv_mean(matrix, blocks)


if __name__ == "__main__":
    unittest.main()
