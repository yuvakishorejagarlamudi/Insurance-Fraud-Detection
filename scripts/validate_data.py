import csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/"data"/"generated"
def read(name):
    with (D/f"{name}.csv").open(encoding="utf-8") as f: return list(csv.DictReader(f))
data={n:read(n) for n in ["claimants","policies","incidents","providers","claims","invoices","payments","relationship_edges"]}
errors=[]
def ids(table,key): return {r[key] for r in data[table]}
for table,key in [("claimants","claimant_id"),("policies","policy_id"),("incidents","incident_id"),("providers","provider_id"),("claims","claim_id"),("invoices","invoice_id"),("payments","payment_id"),("relationship_edges","edge_id")]:
    vals=[r[key] for r in data[table]]
    if len(vals)!=len(set(vals)): errors.append(f"{table}: duplicate {key}")
for r in data["policies"]:
    if r["claimant_id"] not in ids("claimants","claimant_id"): errors.append(f"policy {r['policy_id']}: bad claimant")
for r in data["claims"]:
    for t,k in [("claimants","claimant_id"),("policies","policy_id"),("incidents","incident_id")]:
        if r[k] not in ids(t,k): errors.append(f"claim {r['claim_id']}: bad {k}")
for r in data["invoices"]:
    if r["claim_id"] not in ids("claims","claim_id") or r["provider_id"] not in ids("providers","provider_id"): errors.append(f"invoice {r['invoice_id']}: bad FK")
for r in data["payments"]:
    if r["claim_id"] not in ids("claims","claim_id") or r["invoice_id"] not in ids("invoices","invoice_id"): errors.append(f"payment {r['payment_id']}: bad FK")
report={"counts":{k:len(v) for k,v in data.items()},"errors":errors,"valid":not errors}
(ROOT/"data"/"generated"/"validation_report.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if errors: raise SystemExit(1)
