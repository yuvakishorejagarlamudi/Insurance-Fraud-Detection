import csv
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".")
DATA = ROOT / "data/generated"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

results = {}

def check(name, passed, details):
    results[name] = {
        "status": "PASS" if passed else "NEEDS_WORK",
        "details": details
    }
    print(f"{results[name]['status']}: {name} - {details}")

def read_csv(name):
    path = DATA / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

claims = read_csv("claims.csv")
claimants = read_csv("claimants.csv")
providers = read_csv("providers.csv")
edges = read_csv("relationship_edges.csv")

check("Dataset scale",
      len(claims) == 5000 and len(claimants) == 2000
      and len(providers) == 500 and len(edges) == 8000,
      f"{len(claims)} claims, {len(claimants)} claimants, "
      f"{len(providers)} providers, {len(edges)} edges")

# Verify documented schema
dictionary = DOCS / "DATA_DICTIONARY.md"
check("Data dictionary", dictionary.exists(),
      "Present" if dictionary.exists() else "Missing")

# Verify event history in actual SQLite schema
db_path = ROOT / "insurance_fraud.db"
tables = []
if db_path.exists():
    conn = sqlite3.connect(db_path)
    tables = [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    ]
    conn.close()

history_tables = [
    t for t in tables
    if any(word in t.lower() for word in
           ("history", "event", "audit", "transition"))
]

check("Historical events",
      bool(history_tables),
      f"History/event tables: {history_tables}")

# Verify scenario coverage from actual generated records
ground_truth = ROOT / "data/step41_test/ground_truth/ground_truth.csv"
truth = []
if ground_truth.exists():
    with ground_truth.open(encoding="utf-8-sig", newline="") as f:
        truth = list(csv.DictReader(f))

issues = {row.get("issue_type") for row in truth}

required = {
    "PAYMENT_OVERAGE",
    "DUPLICATE_INVOICE",
    "MISSING_RELATIONSHIP_EDGE",
    "MISSING_POLICY_REFERENCE",
    "BENIGN_SHARED_ADDRESS"
}

check("Five required scenarios",
      required.issubset(issues),
      f"Found: {sorted(issues - {None})}")

# Check source manifest
manifest_path = DATA / "manifest.json"
manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

check("Manifest and seed",
      manifest.get("seed") == 20261022,
      f"Seed: {manifest.get('seed')}")

# Verify saved checksums against actual files
checksum_path = DATA / "checksums.json"
saved = {}
if checksum_path.exists():
    saved = json.loads(checksum_path.read_text(encoding="utf-8"))

actual = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(DATA.glob("*.csv"))
}

check("Dataset checksums",
      bool(saved) and all(
          saved.get(name) == digest
          for name, digest in actual.items()
      ),
      f"{len(actual)} CSV checksums checked")

# Check documentation
readme = ROOT / "README.md"
readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""

check("README",
      bool(readme_text) and
      "generate" in readme_text.lower() and
      "validate" in readme_text.lower(),
      "Basic generator and validation instructions")

# Report
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "checks": results
}

(DOCS / "COMPLIANCE_AUDIT.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\nAudit report: docs/COMPLIANCE_AUDIT.json")
print("Passed:", sum(v["status"] == "PASS" for v in results.values()))
print("Needs work:", sum(v["status"] != "PASS" for v in results.values()))
