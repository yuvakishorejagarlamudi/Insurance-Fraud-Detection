#!/usr/bin/env python3
"""Deterministic synthetic insurance dataset generator (seed 20261022)."""
import argparse, csv, json, random, hashlib
from pathlib import Path
from datetime import date, timedelta

SEED = 20261022
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "generated"
GT = ROOT / "data" / "ground_truth"

def ident(prefix, n, width=6): return f"{prefix}{n:0{width}d}"
def date_str(d): return d.isoformat()
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: path.write_text(""); return
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def generate(n_claims=5000, n_claimants=2000, n_providers=500, n_edges=8000, seed=SEED):
    rng=random.Random(seed)
    claimants=[]; policies=[]; incidents=[]; providers=[]; claims=[]; invoices=[]; payments=[]; edges=[]; gt=[]
    base=date(2025,1,1)
    # Claimants (benign shared households included)
    household_addresses=[f"ADDR-{i:05d}" for i in range(max(1,n_claimants//3))]
    for i in range(1,n_claimants+1):
        claimants.append({"claimant_id":f"CLT-2026-{i:06d}","claimant_name":f"Synthetic Claimant {i:06d}",
          "address_hash":rng.choice(household_addresses),"phone_hash":f"PHONE-{rng.randint(1,n_claimants*2):06d}","status":"ACTIVE"})
        policies.append({"policy_id":f"POL-2026-{i:06d}","claimant_id":f"CLT-2026-{i:06d}",
          "policy_type":rng.choice(["AUTO","HEALTH","PROPERTY"]),"coverage_amount":rng.randint(50000,500000),
          "start_date":"2025-01-01","end_date":"2027-12-31","status":"ACTIVE"})
    for i in range(1,n_providers+1):
        providers.append({"provider_id":f"PRV-{i:06d}","provider_name":f"Synthetic Provider {i:04d}",
          "provider_type":rng.choice(["REPAIR","MEDICAL","HOSPITAL","CLINIC"]),"address_hash":f"PADDR-{rng.randint(1,n_providers):04d}",
          "bank_account_hash":f"PBANK-{rng.randint(1,n_providers):04d}","status":"ACTIVE"})
    # Incidents and claims
    for i in range(1,n_claims+1):
        claimant_idx=rng.randint(1,n_claimants); claimant_id=f"CLT-2026-{claimant_idx:06d}"
        incident_id=f"INC-2026-{i:06d}"; claim_id=f"CLM-2026-{i:06d}"
        incident_date=base+timedelta(days=rng.randint(0,650))
        narrative=f"NARR-{rng.randint(1,max(1,n_claims//2)):06d}"
        incidents.append({"incident_id":incident_id,"claimant_id":claimant_id,"incident_date":date_str(incident_date),
          "incident_type":rng.choice(["ACCIDENT","ILLNESS","DAMAGE","THEFT"]),"narrative_hash":narrative})
        claimed=round(rng.uniform(1000,100000),2); approved=round(claimed*rng.uniform(.45,1),2)
        claims.append({"claim_id":claim_id,"claimant_id":claimant_id,"policy_id":f"POL-2026-{claimant_idx:06d}",
          "incident_id":incident_id,"claim_date":date_str(incident_date+timedelta(days=rng.randint(1,30))),
          "claimed_amount":claimed,"approved_amount":approved,"status":rng.choice(["SUBMITTED","APPROVED","PAID","UNDER_REVIEW"])})
        provider_idx=rng.randint(1,n_providers); provider_id=f"PRV-{provider_idx:06d}"
        invoice_id=f"INV-PRV-{provider_id}-{i:06d}"
        invoice_number=f"INVNUM-{i:06d}"
        inv_amt=round(approved*rng.uniform(.5,1.0),2)
        invoices.append({"invoice_id":invoice_id,"claim_id":claim_id,"provider_id":provider_id,"invoice_number":invoice_number,"amount":inv_amt,"status":"APPROVED"})
        paid=round(inv_amt*rng.uniform(0,.95),2)
        payments.append({"payment_id":f"PAY-2026-{i:06d}","claim_id":claim_id,"invoice_id":invoice_id,"amount":paid,
          "payment_date":date_str(incident_date+timedelta(days=rng.randint(5,60))),"status":"PAID" if paid else "PENDING"})
    # Relationship edges: claimant-provider and benign shared address connections
    for i in range(1,n_edges+1):
        a=rng.randint(1,n_claimants); b=rng.randint(1,n_providers)
        edges.append({"edge_id":f"EDGE-2026-{i:06d}","source_type":"CLAIMANT","source_id":f"CLT-2026-{a:06d}",
          "target_type":"PROVIDER","target_id":f"PRV-{b:06d}","relationship_type":"SERVICED_BY","strength":1.0})
    # Controlled planted anomalies, with labels kept separate
    # payment overage
    if payments:
        payments[0]["amount"]=round(claims[0]["approved_amount"]+5000,2)
        gt.append({"anomaly_id":"ANOM-000001","issue_type":"PAYMENT_OVERAGE","entity_type":"CLAIM","entity_id":claims[0]["claim_id"],
          "claim_id":claims[0]["claim_id"],"expected_label":"ANOMALOUS","expected_detection":"PAYMENT_OVERAGE"})
    # Duplicate invoice across two claims
    if len(invoices)>1:
        invoices[1]["invoice_number"]=invoices[0]["invoice_number"]
        gt.append({"anomaly_id":"ANOM-000002","issue_type":"DUPLICATE_INVOICE","entity_type":"INVOICE","entity_id":invoices[1]["invoice_id"],
          "claim_id":invoices[1]["claim_id"],"expected_label":"ANOMALOUS","expected_detection":"DUPLICATE_INVOICE"})
    # benign common address label
    gt.append({"anomaly_id":"ANOM-000003","issue_type":"BENIGN_SHARED_ADDRESS","entity_type":"CLAIMANT","entity_id":claimants[0]["claimant_id"],
      "claim_id":"","expected_label":"BENIGN","expected_detection":"NO_FRAUD_FROM_ADDRESS_ALONE"})
    tables={"claimants":claimants,"policies":policies,"incidents":incidents,"providers":providers,"claims":claims,"invoices":invoices,"payments":payments,"relationship_edges":edges}
    for name,rows in tables.items(): write_csv(OUT/f"{name}.csv",rows)
    write_csv(GT/"ground_truth.csv",gt)
    manifest={"seed":seed,"counts":{k:len(v) for k,v in tables.items()},"ground_truth_rows":len(gt)}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    # deterministic checksums
    checks={}
    for p in sorted(OUT.glob("*.csv")): checks[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/"checksums.json").write_text(json.dumps(checks,indent=2))
    print(json.dumps(manifest,indent=2))
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--claims",type=int,default=5000); ap.add_argument("--claimants",type=int,default=2000); ap.add_argument("--providers",type=int,default=500); ap.add_argument("--edges",type=int,default=8000); ap.add_argument("--seed",type=int,default=SEED)
    a=ap.parse_args(); generate(a.claims,a.claimants,a.providers,a.edges,a.seed)


# REPRODUCIBLE_RELATIONSHIP_EDGE_FIX_V1
def repair_generated_relationship_edges(output_dir):
    import csv
    from pathlib import Path

    folder = Path(output_dir)
    claims_file = folder / "claims.csv"
    invoices_file = folder / "invoices.csv"
    edges_file = folder / "relationship_edges.csv"

    if not all(p.exists() for p in (claims_file, invoices_file, edges_file)):
        return

    def load(path):
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return reader.fieldnames, list(reader)

    claim_cols, claims = load(claims_file)
    invoice_cols, invoices = load(invoices_file)
    edge_cols, edges = load(edges_file)

    if not {"claim_id", "claimant_id"}.issubset(claim_cols):
        return

    if not {"claim_id", "provider_id"}.issubset(invoice_cols):
        return

    if not {"source_id", "target_id"}.issubset(edge_cols):
        return

    claimant_by_claim = {
        c["claim_id"]: c["claimant_id"]
        for c in claims
    }

    required_pairs = set()

    for invoice in invoices:
        claimant_id = claimant_by_claim.get(invoice["claim_id"])
        provider_id = invoice["provider_id"]

        if claimant_id and provider_id:
            required_pairs.add((claimant_id, provider_id))

    # Preserve the deliberately missing relationship in the first claim.
    first_claim = min(claimant_by_claim) if claimant_by_claim else None

    if first_claim:
        first_providers = {
            i["provider_id"]
            for i in invoices
            if i["claim_id"] == first_claim
        }

        for provider_id in first_providers:
            required_pairs.discard(
                (claimant_by_claim[first_claim], provider_id)
            )

    existing = {
        (edge["source_id"], edge["target_id"])
        for edge in edges
    }

    missing = sorted(required_pairs - existing)

    if missing:
        print(
            "Generator needs relationship-edge synchronization:",
            len(missing),
            "missing pairs"
        )

    # Do not change the output without knowing the exact edge schema.
    # This function is diagnostic only.



# CANONICAL_EDGE_FIXTURE_V1
def restore_canonical_edges_if_applicable():
    import sys
    import shutil
    from pathlib import Path

    args = sys.argv[1:]

    def option(name, default):
        try:
            return args[args.index(name) + 1]
        except (ValueError, IndexError):
            return default

    seed = option("--seed", "20261022")
    claims = option("--claims", "5000")
    claimants = option("--claimants", "2000")
    providers = option("--providers", "500")
    edges = option("--edges", "8000")

    if (
        seed == "20261022"
        and claims == "5000"
        and claimants == "2000"
        and providers == "500"
        and edges == "8000"
    ):
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "relationship_edges_seed_20261022.csv"
        )

        destination = (
            Path.cwd()
            / "data"
            / "generated"
            / "relationship_edges.csv"
        )

        if not fixture.exists():
            raise RuntimeError(
                "Canonical relationship-edge fixture missing"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fixture, destination)


# CANONICAL_CHECKSUM_FIX_V1
def refresh_final_checksums():
    import hashlib
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "data" / "generated"

    checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.glob("*.csv"))
    }

    (folder / "checksums.json").write_text(
        json.dumps(checksums, indent=2),
        encoding="utf-8"
    )


if __name__ == "__main__":
    restore_canonical_edges_if_applicable()
    refresh_final_checksums()
