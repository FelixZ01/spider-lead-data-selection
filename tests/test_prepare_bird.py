import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "data" / "prepare_bird.py"
SPEC = importlib.util.spec_from_file_location("prepare_bird", SCRIPT)
prepare_bird = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prepare_bird)

BASELINE_SCRIPT = Path(__file__).parents[1] / "src" / "data" / "create_baselines.py"
BASELINE_SPEC = importlib.util.spec_from_file_location("create_baselines", BASELINE_SCRIPT)
create_baselines = importlib.util.module_from_spec(BASELINE_SPEC)
assert BASELINE_SPEC.loader is not None
BASELINE_SPEC.loader.exec_module(create_baselines)

GENERATION_SCRIPT = Path(__file__).parents[1] / "src" / "eval" / "generate_sql.py"


class PrepareBirdTests(unittest.TestCase):
    def test_convert_record_contains_schema_question_and_sql(self):
        record = {
            "db_id": "movie_platform",
            "question": "Who directed the movie?",
            "evidence": "Use the movie title.",
            "SQL": "SELECT director_name FROM movies;",
        }
        schema = {
            "db_id": "movie_platform",
            "table_names_original": ["movies"],
            "column_names_original": [[-1, "*"], [0, "movie_title"], [0, "director_name"]],
            "column_types": ["text", "text", "text"],
            "foreign_keys": [],
        }

        converted = prepare_bird.convert_record(record, 0, {"movie_platform": schema})

        self.assertEqual(converted["dataset"], "bird")
        self.assertIn("CREATE TABLE movies", converted["messages"][1]["content"])
        self.assertEqual(converted["messages"][-1]["content"], record["SQL"])

    def test_jsonl_sample_is_readable(self):
        sample = Path(__file__).parents[1] / "data" / "sample" / "bird_sample.jsonl"
        rows = prepare_bird.read_records(sample)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["db_id"], "movie_platform")

    def test_random_baseline_is_reproducible(self):
        rows = [{"id": number} for number in range(10)]
        first = create_baselines.sample_random(rows, 4, seed=42)
        second = create_baselines.sample_random(rows, 4, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)

    def test_bird_prediction_separator_is_exact(self):
        source = GENERATION_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('SEPARATOR = "\\t----- bird -----\\t"', source)


if __name__ == "__main__":
    unittest.main()
