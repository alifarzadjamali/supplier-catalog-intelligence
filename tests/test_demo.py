import csv
import tempfile
import unittest
from pathlib import Path

from catalog_intel.cli import run


class DemoBenchmark(unittest.TestCase):
    def test_three_supplier_answer_key(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(run(root / "demo" / "config.json", folder), 0)
            with open(Path(folder) / "comparison.csv", encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 36)
            self.assertEqual({row["supplier"] for row in rows}, {"Supplier A", "Supplier B", "Supplier C"})
            self.assertEqual(sum(bool(row["delivered_total_target_currency"]) for row in rows), 33)
            by_sku = {row["sku"]: row for row in rows}
            self.assertEqual(by_sku["A-00"]["delivered_total_target_currency"], "375.00")
            self.assertEqual(by_sku["B-00"]["delivered_total_target_currency"], "391.00")
            self.assertEqual(by_sku["C-00"]["delivered_total_target_currency"], "")
            self.assertIn("delivery charge unknown", by_sku["C-00"]["issues"])


if __name__ == "__main__":
    unittest.main()
