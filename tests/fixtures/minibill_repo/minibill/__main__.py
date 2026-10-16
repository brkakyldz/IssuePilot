import argparse
import json
import sys

from minibill.models import Invoice, LineItem
from minibill.pricing import total


def load(path: str) -> Invoice:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    items = [LineItem(**item) for item in data["items"]]
    return Invoice(
        items=items,
        discount_rate=data.get("discount_rate", "0"),
        tax_rate=data.get("tax_rate", "0.20"),
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m minibill")
    parser.add_argument("invoice", help="path to an invoice JSON file")
    parser.add_argument("--currency", default="TRY", help="currency code to print (default: TRY)")
    args = parser.parse_args(argv[1:])
    print(f"{total(load(args.invoice)):.2f} {args.currency}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
