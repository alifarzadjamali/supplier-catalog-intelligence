import argparse
import json
from pathlib import Path

from .core import compare, ingest, inventory, write_report


def run(config_path, output):
    config_path = Path(config_path).resolve()
    root = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    sources = config["sources"]
    manifest = inventory(root, sources)
    products, errors = ingest(root, sources)
    assumptions = config["comparison"]
    if int(assumptions["quantity"]) <= 0:
        raise ValueError("Quantity must be positive")
    if not 0 <= float(assumptions["tax_rate"]) <= 1:
        raise ValueError("Tax rate must be between 0 and 1")
    rates = assumptions["rates_to_target"]
    target = assumptions["target_currency"]
    if target not in rates or str(rates[target]) != "1":
        raise ValueError("Target currency needs a rate of 1")
    rows = compare(products, int(assumptions["quantity"]), target, rates, assumptions["tax_rate"])
    write_report(Path(output), rows, manifest, errors, assumptions)
    print(f"Wrote {len(rows)} options to {output}; {len(errors)} file errors")
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="Build a source-linked supplier comparison")
    parser.add_argument("config", help="JSON config with supplier files and comparison assumptions")
    parser.add_argument("-o", "--output", default="output")
    args = parser.parse_args()
    raise SystemExit(run(args.config, args.output))


if __name__ == "__main__":
    main()
