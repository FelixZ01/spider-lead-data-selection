import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "src" / "eval" / "export_spider_official.py"
SPEC = importlib.util.spec_from_file_location("export_spider_official", SCRIPT)
export_spider_official = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(export_spider_official)


class ExportSpiderOfficialTests(unittest.TestCase):
    def test_one_line_removes_newlines_and_tabs(self):
        self.assertEqual(
            export_spider_official.one_line("SELECT\t*\nFROM singer"),
            "SELECT * FROM singer",
        )


if __name__ == "__main__":
    unittest.main()
