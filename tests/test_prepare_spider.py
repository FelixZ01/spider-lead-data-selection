import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "data" / "prepare_spider.py"
SPEC = importlib.util.spec_from_file_location("prepare_spider", SCRIPT)
prepare_spider = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prepare_spider)


class PrepareSpiderTests(unittest.TestCase):
    def setUp(self):
        self.schema = {
            "db_id": "concert_singer",
            "table_names_original": ["singer", "concert"],
            "column_names_original": [[-1, "*"], [0, "name"], [1, "year"]],
        }

    def test_render_and_convert(self):
        record = {
            "db_id": "concert_singer",
            "question": "List singer names.",
            "query": "SELECT name FROM singer",
        }
        converted = prepare_spider.convert_record(record, 0, {"concert_singer": self.schema})
        self.assertIn("singer(name)", converted["input_text"])
        self.assertEqual(converted["target_sql"], record["query"])
        self.assertEqual(converted["complexity"], "simple")

    def test_sql_complexity(self):
        self.assertEqual(prepare_spider.sql_complexity("SELECT * FROM a JOIN b ON a.id=b.id"), "advanced")
        self.assertEqual(
            prepare_spider.sql_complexity("SELECT * FROM a WHERE id IN (SELECT id FROM b)"),
            "nested",
        )


if __name__ == "__main__":
    unittest.main()
