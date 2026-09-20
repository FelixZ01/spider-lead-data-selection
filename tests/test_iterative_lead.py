import random
import unittest

from src.selection.iterative_lead import (
    allocate_evenly,
    assign_quantile_clusters,
    choose_arm,
    exp3_probabilities,
    observed_idu_proxy,
    proportional_task_select,
    update_exp3,
)


class IterativeLeadTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "id": f"row_{index}",
                "db_id": "a" if index < 6 else "b",
                "loss": float(index),
                "utility": float(index),
            }
            for index in range(10)
        ]

    def test_quantile_clusters_are_balanced_and_ordered(self):
        clusters = assign_quantile_clusters(self.rows, 2, "loss")
        self.assertEqual(sum(value == 0 for value in clusters.values()), 5)
        self.assertEqual(sum(value == 1 for value in clusters.values()), 5)
        self.assertEqual(clusters["row_0"], 0)
        self.assertEqual(clusters["row_9"], 1)

    def test_allocate_evenly_preserves_total(self):
        self.assertEqual(allocate_evenly(1500, 5), [300, 300, 300, 300, 300])
        self.assertEqual(allocate_evenly(11, 3), [4, 4, 3])

    def test_allocate_evenly_rejects_too_many_parts(self):
        with self.assertRaises(ValueError):
            allocate_evenly(2, 3)

    def test_observed_idu_proxy_matches_equation(self):
        value = observed_idu_proxy(4.0, 5.0, 6.0, 0.5)
        self.assertAlmostEqual(value, 4.5)

    def test_observed_idu_proxy_respects_nonnegative_loss_boundary(self):
        value = observed_idu_proxy(1.0, 9.0, 9.0, 0.1)
        self.assertAlmostEqual(value, 0.9)

    def test_loss_reduction_produces_positive_proxy_reward(self):
        before = observed_idu_proxy(1.0, 9.0, 9.0, 0.1)
        after = observed_idu_proxy(0.2, 1.0, before, 0.1)
        self.assertGreater(before - after, 0.0)

    def test_exp3_update_accepts_negative_feedback(self):
        probabilities = exp3_probabilities([1.0, 1.0], 0.1)
        updated = update_exp3([1.0, 1.0], 0, -0.5, probabilities[0], 0.1)
        self.assertLess(updated[0], 1.0)
        self.assertEqual(updated[1], 1.0)

    def test_exp3_update_rewards_selected_arm(self):
        probabilities = exp3_probabilities([1.0, 1.0], 0.1)
        updated = update_exp3([1.0, 1.0], 1, 0.5, probabilities[1], 0.1)
        self.assertEqual(updated[0], 1.0)
        self.assertGreater(updated[1], 1.0)

    def test_choose_arm_respects_eligibility(self):
        arm = choose_arm([0.9, 0.1], [False, True], random.Random(42))
        self.assertEqual(arm, 1)

    def test_task_selection_keeps_both_databases(self):
        selected = proportional_task_select(self.rows, 5, "utility")
        self.assertEqual(len(selected), 5)
        self.assertEqual({row["db_id"] for row in selected}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
