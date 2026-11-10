import csv
import json
import tempfile
import unittest
from pathlib import Path

from catalog_intel.core import compare, read_csv


class WorkflowTests(unittest.TestCase):
    def test_semicolon_csv_and_week_ranges(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chairs.csv"
            path.write_text("sku;name;category;material;finish;dimensions;variant;pack_size;currency;unit_price;delivery_charge;lead_time_days\nA1;Chair;chair;oak;natural;50 × 60 cm;plain;1;£;100;0;2-3 weeks\n", encoding="utf-8")
            product = list(read_csv(path, "chairs.csv", "A"))[0]
            self.assertEqual(product["raw"]["currency"], "GBP")
            self.assertEqual(product["normalized"]["lead_min_days"], 14)
            self.assertEqual(product["normalized"]["lead_max_days"], 21)
            self.assertEqual(product["normalized"]["delivery_charge"], "0")

    def test_missing_shipping_and_pack_math(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chairs.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["sku", "name", "category", "material", "finish", "dimensions", "variant", "pack_size", "currency", "unit_price", "moq", "delivery_charge", "lead_time_days"])
                writer.writeheader()
                writer.writerow({"sku": "A1", "name": "Chair", "category": "chair", "material": "oak", "finish": "natural", "dimensions": "50 cm", "variant": "plain", "pack_size": "2", "currency": "GBP", "unit_price": "100", "moq": "5", "delivery_charge": "", "lead_time_days": "5-8"})
                writer.writerow({"sku": "A2", "name": "Chair", "category": "chair", "material": "oak", "finish": "natural", "dimensions": "50 cm", "variant": "plain", "pack_size": "2", "currency": "GBP", "unit_price": "110", "moq": "1", "delivery_charge": "0", "lead_time_days": "5"})
            products = list(read_csv(path, "chairs.csv", "A"))
            rows = compare(products, 3, "GBP", {"GBP": 1}, 0)
            self.assertEqual(rows[0]["units_ordered"], 6)
            self.assertEqual(rows[0]["subtotal_source_currency"], "300")
            self.assertEqual(rows[0]["price_per_unit_source_currency"], "50")
            self.assertEqual(rows[0]["delivered_total_target_currency"], "")
            self.assertEqual(rows[1]["delivered_total_target_currency"], "220.00")
            self.assertEqual(json.loads(rows[0]["evidence"])["unit_price"]["location"], "row 2, column 10")
            self.assertEqual(rows[0]["lead_max_days"], 8)


if __name__ == "__main__":
    unittest.main()
