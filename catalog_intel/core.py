import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS = ["sku", "name", "category", "material", "finish", "dimensions", "variant", "pack_size", "currency", "unit_price", "moq", "availability", "delivery_charge", "delivery_condition", "lead_time_days", "image"]
ALIASES = {"product": "name", "product_name": "name", "price": "unit_price", "price_per_unit": "unit_price", "shipping": "delivery_charge", "shipping_fee": "delivery_charge", "lead_time": "lead_time_days", "lead_days": "lead_time_days", "minimum_order_quantity": "moq", "pack": "pack_size", "size": "dimensions", "photo": "image"}
MONEY = {"GBP", "USD", "EUR"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root, sources):
    entries = []
    seen = set()
    for source in sources:
        supplier = source["supplier"]
        for item in source["files"]:
            path = (root / item["path"]).resolve()
            if not path.is_file() or not path.is_relative_to(root.resolve()):
                raise ValueError(f"Missing or outside project: {item['path']}")
            if path in seen:
                raise ValueError(f"File listed more than once: {item['path']}")
            seen.add(path)
            entries.append({"supplier": supplier, "path": item["path"], "sha256": sha256(path), "bytes": path.stat().st_size, "format": path.suffix.lower(), "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), "access_terms": item.get("access_terms", "unknown"), "reuse_terms": item.get("reuse_terms", "unknown")})
    return entries


def text(value):
    return "" if value is None else str(value).strip()


def decimal(value):
    cleaned = re.sub(r"[£$€,\s]", "", text(value))
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def norm_key(value):
    key = re.sub(r"[^a-z0-9]+", "_", text(value).lower()).strip("_")
    return ALIASES.get(key, key)


def labelled_row(line):
    if not line.startswith("PRODUCT |"):
        return None
    values = {}
    for part in line.split("|")[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            values[norm_key(key)] = value.strip()
    return values


def lead_days(value):
    match = re.fullmatch(r"\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*(days?|weeks?)?\s*", value, re.I)
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2) or match.group(1))
    if end < start:
        return None
    factor = 7 if (match.group(3) or "").lower().startswith("week") else 1
    return start * factor, end * factor


def record(supplier, path, values, locations, method):
    raw = {field: text(values.get(field)) for field in FIELDS}
    currency_aliases = {"£": "GBP", "$": "USD", "€": "EUR"}
    if raw["currency"]:
        raw["currency"] = currency_aliases.get(raw["currency"], raw["currency"].upper())
    evidence = {field: {"file": path, "location": locations.get(field, "unknown"), "method": method} for field in FIELDS if raw[field]}
    issues = []
    if not raw["sku"] and not raw["name"]:
        return None
    if not raw["name"]:
        issues.append("missing product name")
    if not raw["sku"]:
        issues.append("missing SKU")
    if raw["currency"] not in MONEY:
        issues.append("missing or unsupported currency")
    price = decimal(raw["unit_price"])
    if price is None or price < 0:
        issues.append("missing or invalid unit price")
    pack = decimal(raw["pack_size"] or "1")
    moq = decimal(raw["moq"] or "1")
    if pack is None or pack <= 0 or pack != int(pack):
        issues.append("invalid pack size")
    if moq is None or moq <= 0 or moq != int(moq):
        issues.append("invalid MOQ")
    shipping = decimal(raw["delivery_charge"])
    if not raw["delivery_charge"]:
        issues.append("delivery charge unknown")
    elif shipping is None or shipping < 0:
        issues.append("invalid delivery charge")
    lead = lead_days(raw["lead_time_days"])
    if not lead:
        issues.append("lead time unknown or invalid")
    return {"supplier": supplier, "raw": raw, "evidence": evidence, "issues": issues, "normalized": {"unit_price": str(price) if price is not None and price >= 0 else None, "pack_size": int(pack) if pack and pack > 0 and pack == int(pack) else None, "moq": int(moq) if moq and moq > 0 and moq == int(moq) else None, "delivery_charge": str(shipping) if shipping is not None and shipping >= 0 else None, "lead_min_days": lead[0] if lead else None, "lead_max_days": lead[1] if lead else None}}


def read_csv(path, rel, supplier):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        sample = stream.read(4096)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(stream, dialect)
        headers = next(reader, None)
        if not headers:
            return
        keys = [norm_key(h) for h in headers]
        for row_number, row in enumerate(reader, 2):
            if not any(text(cell) for cell in row):
                continue
            values = dict(zip(keys, row))
            locations = {key: f"row {row_number}, column {i + 1}" for i, key in enumerate(keys)}
            result = record(supplier, rel, values, locations, "csv cell")
            if result:
                yield result


def read_xlsx(path, rel, supplier):
    from openpyxl import load_workbook
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in book:
            rows = sheet.iter_rows()
            header = next(rows, None)
            if not header:
                continue
            keys = [norm_key(c.value) for c in header]
            for cells in rows:
                values = dict(zip(keys, [c.value for c in cells]))
                locations = {key: f"{sheet.title}!{cell.coordinate}" for key, cell in zip(keys, cells)}
                result = record(supplier, rel, values, locations, "xlsx cell")
                if result:
                    yield result
    finally:
        book.close()


def read_pdf(path, rel, supplier):
    import pymupdf
    with pymupdf.open(path) as doc:
        for page_number, page in enumerate(doc, 1):
            lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
            method = "pdf text"
            if not lines:
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
                    image = Image.open(io.BytesIO(pix.tobytes("png")))
                    lines = [line.strip() for line in pytesseract.image_to_string(image).splitlines() if line.strip()]
                    method = "pdf page OCR"
                except (ImportError, FileNotFoundError) as exc:
                    raise RuntimeError(f"Page {page_number} has no text; install Tesseract OCR") from exc
            for line_number, line in enumerate(lines, 1):
                # The starter parser expects a labelled, pipe-delimited product row.
                values = labelled_row(line)
                if values is None:
                    continue
                locations = {key: f"page {page_number}, text line {line_number}" for key in values}
                result = record(supplier, rel, values, locations, method)
                if result:
                    yield result


def read_image(path, rel, supplier):
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageFilter
        image = ImageOps.autocontrast(Image.open(path).convert("L")).filter(ImageFilter.MedianFilter(3))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        lines = defaultdict(list)
        for i, word in enumerate(data["text"]):
            if word.strip():
                lines[(data["page_num"][i], data["block_num"][i], data["par_num"][i], data["line_num"][i])].append(word)
        # OCR lines use the same explicit row format as digital PDFs.
        for line_number, words in enumerate(lines.values(), 1):
            line = " ".join(words)
            values = labelled_row(line)
            if values is not None:
                result = record(supplier, rel, values, {k: f"OCR line {line_number}" for k in values}, "tesseract OCR")
                if result:
                    yield result
    except (ImportError, FileNotFoundError) as exc:
        raise RuntimeError(f"OCR unavailable for {rel}: install pytesseract and the Tesseract executable") from exc


def ingest(root, sources):
    products, errors = [], []
    readers = {".csv": read_csv, ".xlsx": read_xlsx, ".pdf": read_pdf, ".png": read_image, ".jpg": read_image, ".jpeg": read_image}
    for source in sources:
        for item in source["files"]:
            rel = item["path"]
            path = root / rel
            reader = readers.get(path.suffix.lower())
            if not reader:
                errors.append(f"Unsupported file: {rel}")
                continue
            try:
                for product in reader(path, rel, source["supplier"]):
                    image_ref = product["raw"]["image"]
                    if image_ref:
                        image_path = (root / image_ref).resolve()
                        if not image_path.is_file() or not image_path.is_relative_to(root.resolve()):
                            product["issues"].append("image reference missing or outside project")
                        else:
                            product["image_sha256"] = sha256(image_path)
                    products.append(product)
            except Exception as exc:
                errors.append(f"{rel}: {exc}")
    return products, errors


def compare(products, quantity, target_currency, rates, tax_rate):
    groups = defaultdict(list)
    for index, product in enumerate(products):
        raw = product["raw"]
        # Exact specifications are the baseline. Images never establish equivalence.
        key = tuple(raw[k].casefold() for k in ("category", "material", "finish", "dimensions", "variant", "pack_size"))
        if not all(key[:4]):
            key = ("unmatched", index)
            product["issues"].append("insufficient specs for matching")
        groups[key].append(product)
    rows = []
    for group_index, (key, members) in enumerate(groups.items(), 1):
        for product in members:
            raw, norm = product["raw"], product["normalized"]
            price = Decimal(norm["unit_price"]) if norm["unit_price"] else None
            pack, moq = norm["pack_size"], norm["moq"]
            ordered = max(quantity, moq or quantity)
            packs = (ordered + pack - 1) // pack if pack else None
            units = packs * pack if packs else None
            subtotal = price * packs if price is not None and packs else None
            rate = Decimal(str(rates.get(raw["currency"]))) if raw["currency"] in rates else None
            shipping = Decimal(norm["delivery_charge"]) if norm["delivery_charge"] else None
            total = (subtotal + shipping) * (1 + Decimal(str(tax_rate))) * rate if subtotal is not None and shipping is not None and rate is not None else None
            if rate is None:
                product["issues"].append("exchange rate missing")
            rows.append({"group": group_index, "match_reason": "exact category, material, finish, dimensions, variant and pack size" if len(members) > 1 and key[0] != "unmatched" else "no verified comparable option", "confidence": "candidate" if len(members) > 1 and key[0] != "unmatched" else "review", "supplier": product["supplier"], **raw, "image_sha256": product.get("image_sha256", ""), "quantity_requested": quantity, "price_per_unit_source_currency": str(price / pack) if price is not None and pack else "", "units_ordered": units, "subtotal_source_currency": str(subtotal) if subtotal is not None else "", "delivered_total_target_currency": str(total.quantize(Decimal("0.01"))) if total is not None else "", "target_currency": target_currency, "lead_min_days": norm["lead_min_days"], "lead_max_days": norm["lead_max_days"], "review_status": "needs review" if product["issues"] else "ready", "issues": "; ".join(product["issues"]), "evidence": json.dumps(product["evidence"], ensure_ascii=False)})
    return rows


def write_report(out, rows, inventory_rows, errors, assumptions):
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(inventory_rows, indent=2), encoding="utf-8")
    (out / "assumptions.json").write_text(json.dumps(assumptions, indent=2), encoding="utf-8")
    (out / "ingestion_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
    if rows:
        with open(out / "comparison.csv", "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "Comparison"
    if rows:
        sheet.append(list(rows[0]))
        for row in rows:
            sheet.append(list(row.values()))
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    book.save(out / "comparison.xlsx")
    complete = sum(bool(row["delivered_total_target_currency"]) for row in rows)
    flagged = sum(bool(row["issues"]) for row in rows)
    summary = f"# Comparison summary\n\n{len(rows)} purchase options from {len(set(r['supplier'] for r in rows))} suppliers. {complete} have a calculable delivered total; {flagged} need review.\n\n"
    summary += "Groups use exact category, material, finish, dimensions, variant and pack size. A group is a comparison suggestion, not a claim that products are identical. Evidence for each populated field is in the CSV and Excel `evidence` column.\n\n"
    by_group = defaultdict(list)
    for row in rows:
        by_group[row["group"]].append(row)
    summary += "## Lowest complete totals by group\n\n"
    for group, members in by_group.items():
        complete_members = [r for r in members if r["delivered_total_target_currency"]]
        if not complete_members:
            continue
        best = min(complete_members, key=lambda r: Decimal(r["delivered_total_target_currency"]))
        summary += f"- Group {group}: {best['supplier']} {best['sku'] or best['name']} — {best['delivered_total_target_currency']} {best['target_currency']} for {best['units_ordered']} units. {len(members) - len(complete_members)} option(s) have unknown totals.\n"
    summary += "\nThese are lowest known totals under the stated assumptions. Unknown totals could be lower.\n\n"
    summary += "## Review queue\n\n" + ("\n".join(f"- {r['supplier']} {r['sku'] or r['name']}: {r['issues']}" for r in rows if r["issues"]) or "No flagged rows.") + "\n"
    if errors:
        summary += "\n## Files needing attention\n\n" + "\n".join(f"- {e}" for e in errors) + "\n"
    (out / "summary.md").write_text(summary, encoding="utf-8")
