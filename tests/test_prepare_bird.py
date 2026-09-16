import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "data" / "prepare_bird.py"
SPEC = importlib.util.spec_from_file_location("prepare_bird", SCRIPT)
prepare_bird = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prepare_bird)


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


if __name__ == "__main__":
    unittest.main()
