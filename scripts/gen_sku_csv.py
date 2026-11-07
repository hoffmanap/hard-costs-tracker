#!/usr/bin/env python3
"""Regenerates data/prices/skus_template.csv from the union of every component across all BOM
tiers, so the SKU list can never silently drift out of sync with the BOMs again. One row per
component per store (2 rows per component: home_depot, lowes) -- leave a row blank/delete it if a
component genuinely isn't sold at that store (e.g. nothing, in practice, but kept for symmetry).
"""
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pull every distinct component + a human description from the BOMs themselves, plus whatever
# descriptions already exist in skus.json so a re-run doesn't lose manually-entered real SKUs.
existing = {}
skus_path = ROOT / "data/prices/skus.json"
if skus_path.exists():
    existing = json.loads(skus_path.read_text())["components"]

comps = {}
for f in sorted((ROOT / "data/boms").glob("*.json")):
    bom = json.loads(f.read_text())
    for cat, items in bom["components"].items():
        for key, spec in items.items():
            comps.setdefault(key, {"category": cat, "desc": spec.get("basis", "")})

rows = []
for comp in sorted(comps):
    prior = {s["store"]: s for s in existing.get(comp, [])}
    for store in ["home_depot", "lowes"]:
        p = prior.get(store, {})
        rows.append({
            "component": comp,
            "category": comps[comp]["category"],
            "store": store,
            "sku": p.get("sku", ""),
            "product_desc": p.get("desc", comps[comp]["desc"]),
            "unit_price": "",
            "purchase_unit": p.get("unit", ""),
            "notes": "",
        })

out = ROOT / "data/prices/skus_template.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["component", "category", "store", "sku", "product_desc",
                                        "unit_price", "purchase_unit", "notes"])
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {out} ({len(rows)} rows = {len(comps)} components x 2 stores)")
