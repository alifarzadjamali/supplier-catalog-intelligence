"""Create a deterministic, invented three-supplier chair benchmark."""
import csv
import json
from pathlib import Path

import pymupdf
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1] / "demo"
ROOT.mkdir(exist_ok=True)
HEADERS = ["sku", "name", "category", "material", "finish", "dimensions", "variant", "pack_size", "currency", "unit_price", "moq", "availability", "delivery_charge", "delivery_condition", "lead_time_days", "image"]


def item(i, supplier):
    material = ["oak", "ash", "walnut"][i % 3]
    finish = ["natural", "black"][i % 2]
    return {"sku": f"{supplier}-{i:02d}", "name": f"Studio dining chair {i + 1}", "category": "dining chair", "material": material, "finish": finish, "dimensions": "48x52x78 cm", "variant": "standard", "pack_size": "1", "currency": "GBP", "unit_price": str(90 + i * 3 + {"A": 0, "B": 4, "C": 8}[supplier]), "moq": "2" if supplier == "B" else "1", "availability": "in stock", "delivery_charge": "" if supplier == "C" and i % 4 == 0 else str(15 + i), "delivery_condition": "per order" if not (supplier == "C" and i % 4 == 0) else "", "lead_time_days": "5-8" if supplier != "C" else "10-14", "image": ""}


with open(ROOT / "supplier_a.csv", "w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, HEADERS)
    writer.writeheader()
    writer.writerows(item(i, "A") for i in range(12))

book = Workbook()
sheet = book.active
sheet.title = "Chairs"
sheet.append(HEADERS)
for i in range(12):
    sheet.append([item(i, "B")[k] for k in HEADERS])
book.save(ROOT / "supplier_b.xlsx")

doc = pymupdf.open()
for start in (0, 6):
    page = doc.new_page(width=1600, height=900)
    page.insert_text((45, 45), "Supplier C | invented chair catalogue", fontsize=20)
    for offset, i in enumerate(range(start, start + 6)):
        row = item(i, "C")
        line = "PRODUCT | " + " | ".join(f"{key}={value}" for key, value in row.items() if value)
        page.insert_text((45, 95 + 110 * offset), line, fontsize=8)
doc.save(ROOT / "supplier_c.pdf")
doc.close()

config = {"sources": [{"supplier": name, "files": [{"path": path, "access_terms": "invented demo", "reuse_terms": "MIT project fixture"}]} for name, path in [("Supplier A", "supplier_a.csv"), ("Supplier B", "supplier_b.xlsx"), ("Supplier C", "supplier_c.pdf")]], "comparison": {"quantity": 4, "target_currency": "GBP", "rates_to_target": {"GBP": 1}, "rate_date": "2026-11-10", "tax_rate": 0, "tax_note": "Demo assumes no added tax; prices are invented"}}
(ROOT / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
print(f"Created demo files in {ROOT}")
