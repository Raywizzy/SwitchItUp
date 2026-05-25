import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.style_reports import export_sample_report


class StyleReportTests(unittest.TestCase):
    def test_export_sample_report(self):
        with TemporaryDirectory() as temp_dir:
            output = export_sample_report(Path(temp_dir) / "style.csv")
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertIn("White Oxford Shirt", rows[0]["outfit_items"])
        self.assertIn("Tami Looks", rows[0]["recommended_stylists"])


if __name__ == "__main__":
    unittest.main()
