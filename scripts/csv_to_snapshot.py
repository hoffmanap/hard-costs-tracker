#!/usr/bin/env python3
"""Converts a filled-in data/prices/skus_template.csv into a snapshot JSON that
compute_costs.py can consume. `unit_price` in the CSV must already be expressed per BOM unit
(e.g. $/board-ft for lumber_board_ft, $/cy for slab_concrete_cy) -- convert from the store's
sale unit (per stud, per bag, per roll) when filling the CSV. Where both stores have a price,
the snapshot uses their average; where only one does, it uses that one.

Usage: python3 scripts/csv_to_snapshot.py data/prices/skus_template.csv 2026-12 > data/prices/snapshot_2026-12.json
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: csv_to_snapshot.py <filled.csv> <YYYY-MM>", file=sys.stderr)
        sys.exit(1)
    csv_path, period = sys.argv[1], sys.argv[2]

    by_comp = defaultdict(list)
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            price = (row.get("unit_price") or "").strip()
            if not price:
                continue
            try:
                by_comp[row["component"]].append(float(price))
            except ValueError:
                print(f"WARNING: non-numeric unit_price for {row['component']}/{row['store']}: "
                      f"{price!r} -- skipped", file=sys.stderr)

    if not by_comp:
        print("WARNING: no unit_price values found -- is the CSV actually filled in?",
              file=sys.stderr)

    prices = {c: round(sum(v) / len(v), 4) for c, v in by_comp.items()}
    snapshot = {
        "snapshot_date": f"{period}-01",
        "source": f"csv:{Path(csv_path).name}",
        "prices_per_bom_unit": prices,
    }
    print(json.dumps(snapshot, indent=2))

if __name__ == "__main__":
    main()
