import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "selection" / "select_spider.py"
SPEC = importlib.util.spec_from_file_location("select_spider", SCRIPT)
select_spider = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(select_spider)


class SelectSpiderTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "id": f"row_{index}",
                "db_id": f"db_{index % 5}",
                "complexity": ("simple", "advanced", "nested")[index % 3],
                "pretrained_target_loss": float(index),
            }
            for index in range(30)
        ]

    def test_uncertainty_selects_highest_loss(self):
        selected = select_spider.uncertainty_select(self.rows, 4)
        self.assertEqual([row["pretrained_target_loss"] for row in selected], [29, 28, 27, 26])

    def test_random_is_reproducible(self):
        first = select_spider.random_select(self.rows, 8, 42)
        second = select_spider.random_select(self.rows, 8, 42)
        self.assertEqual(first, second)

    def test_diverse_selection_respects_budget_and_spreads_databases(self):
        selected = select_spider.diverse_uncertainty_select(self.rows, 12)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len({row["id"] for row in selected}), 12)
        self.assertGreaterEqual(len({row["db_id"] for row in selected}), 4)


if __name__ == "__main__":
    unittest.main()
