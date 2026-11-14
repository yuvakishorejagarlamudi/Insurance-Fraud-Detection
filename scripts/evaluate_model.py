"""Evaluate simple detected labels against separate ground truth (starter implementation)."""
import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
gt=list(csv.DictReader((ROOT/"data/ground_truth/ground_truth.csv").open()))
# This starter evaluation reports planted positive cases; extend with full detector output.
positive={r["claim_id"] for r in gt if r.get("expected_label")=="ANOMALOUS" and r.get("claim_id")}
print(f"Ground-truth anomalous claim IDs: {len(positive)}")
print("For full precision/recall, compare detector output labels with ground_truth.csv; benign labels are retained.")
