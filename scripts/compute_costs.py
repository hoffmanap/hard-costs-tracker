#!/usr/bin/env python3
"""
Compute aggregate + disaggregated hard-cost totals for each BOM tier against a price snapshot,
and append the result to the running cost history (CSV + JSON) that the dashboard reads.

Usage:
    python3 scripts/compute_costs.py data/prices/snapshot_2026-11_SAMPLE.json

Price snapshot format: {"snapshot_date": "YYYY-MM-DD", "prices_per_bom_unit": {component: $/unit}}
BOM format: data/boms/*.json, with components nested under category -> item -> {"qty": n}

Missing prices for a component are skipped (not zeroed) and reported, so a partial snapshot still
produces a (labeled) partial total rather than silently underpricing the home.
"""
import json
import sys
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOM_DIR = ROOT / "data" / "boms"
HISTORY_CSV = ROOT / "data" / "cost_history.csv"
HISTORY_JSON = ROOT / "data" / "cost_history.json"


def load_boms():
    return {p.stem: json.loads(p.read_text()) for p in sorted(BOM_DIR.glob("*.json"))}


def compute_tier_cost(bom, prices):
    category_totals = {}
    missing = []
    grand_total = 0.0
    for category, items in bom["components"].items():
        cat_total = 0.0
        for comp_key, spec in items.items():
            qty = spec["qty"]
            price = prices.get(comp_key)
            if price is None:
                missing.append(comp_key)
                continue
            cat_total += qty * price
        category_totals[category] = round(cat_total, 2)
        grand_total += cat_total
    return round(grand_total, 2), category_totals, missing


def main():
    if len(sys.argv) != 2:
        print("Usage: compute_costs.py <snapshot.json>", file=sys.stderr)
        sys.exit(1)

    snapshot_path = Path(sys.argv[1])
    snapshot = json.loads(snapshot_path.read_text())
    snapshot_date = snapshot["snapshot_date"]
    prices = snapshot["prices_per_bom_unit"]
    is_sample = "SAMPLE" in snapshot_path.stem.upper() or snapshot.get("source") == "placeholder"

    boms = load_boms()
    results = []
    for tier_id, bom in boms.items():
        total, by_category, missing = compute_tier_cost(bom, prices)
        total_sqft = bom["floor_area_sqft"]
        results.append({
            "snapshot_date": snapshot_date,
            "tier_id": tier_id,
            "floor_area_sqft": total_sqft,
            "total_cost": total,
            "cost_per_sqft": round(total / total_sqft, 2),
            "by_category": by_category,
            "missing_components": missing,
            "is_sample_data": is_sample,
        })
        print(f"[{tier_id}] total=${total:,.0f}  ${total/total_sqft:.2f}/sqft"
              + (f"  (missing prices for: {', '.join(missing)})" if missing else ""))

    # Append to history JSON (list of snapshot results across runs)
    history = []
    if HISTORY_JSON.exists():
        history = json.loads(HISTORY_JSON.read_text())
    history = [h for h in history if not (h["snapshot_date"] == snapshot_date)]  # replace same-date rerun
    history.extend(results)
    history.sort(key=lambda r: (r["snapshot_date"], r["tier_id"]))
    HISTORY_JSON.write_text(json.dumps(history, indent=2))

    # Flat CSV for easy external use (Excel, other tools)
    fieldnames = ["snapshot_date", "tier_id", "floor_area_sqft", "total_cost", "cost_per_sqft",
                  "is_sample_data", "missing_components"]
    with open(HISTORY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in history:
            w.writerow({
                "snapshot_date": row["snapshot_date"],
                "tier_id": row["tier_id"],
                "floor_area_sqft": row["floor_area_sqft"],
                "total_cost": row["total_cost"],
                "cost_per_sqft": row["cost_per_sqft"],
                "is_sample_data": row["is_sample_data"],
                "missing_components": ";".join(row["missing_components"]),
            })

    print(f"\nWrote {HISTORY_JSON} and {HISTORY_CSV} ({len(history)} total snapshot-tier rows)")
    if is_sample:
        print("NOTE: this snapshot is placeholder data -- history now contains a SAMPLE row, "
              "clearly flagged is_sample_data=true. Re-run with a real snapshot to supersede it.")


if __name__ == "__main__":
    main()
