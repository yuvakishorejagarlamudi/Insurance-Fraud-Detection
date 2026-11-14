
#!/usr/bin/env python3
"""Validate the isolated synthetic insurance fraud test dataset."""

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "step38_test"
GENERATED = DATA_ROOT / "generated"
GROUND_TRUTH = DATA_ROOT / "ground_truth" / "ground_truth.csv"
EXCEPTIONS = DATA_ROOT / "exceptions" / "invalid_policy_claims.csv"

PRIMARY_KEYS = {
    "claimants": "claimant_id",
    "policies": "policy_id",
    "incidents": "incident_id",
    "providers": "provider_id",
    "claims": "claim_id",
    "invoices": "invoice_id",
    "payments": "payment_id",
    "relationship_edges": "edge_id",
}

EXPECTED_SCENARIOS = {
    "PAYMENT_OVERAGE",
    "DUPLICATE_INVOICE",
    "MISSING_RELATIONSHIP_EDGE",
    "BENIGN_SHARED_ADDRESS",
    "MISSING_POLICY_REFERENCE",
}


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def check(condition, description, failures):
    if condition:
        print(f"PASS: {description}")
    else:
        print(f"FAIL: {description}")
        failures.append(description)


def as_date(value):
    return date.fromisoformat(value)


def main():
    failures = []

    print("=" * 60)
    print("STEP 39 - SYNTHETIC DATA VALIDATION")
    print("=" * 60)

    tables = {
        name: read_csv(GENERATED / f"{name}.csv")
        for name in PRIMARY_KEYS
    }

    ground_truth = read_csv(GROUND_TRUTH)
    exceptions = read_csv(EXCEPTIONS)

    # 1. Primary keys
    for table_name, pk in PRIMARY_KEYS.items():
        rows = tables[table_name]
        ids = [row[pk] for row in rows]

        check(
            all(ids) and len(ids) == len(set(ids)),
            f"{table_name}: unique, nonempty primary keys",
            failures,
        )

    # 2. Parent entity lookup
    claimants = {
        row["claimant_id"]: row for row in tables["claimants"]
    }
    policies = {
        row["policy_id"]: row for row in tables["policies"]
    }
    incidents = {
        row["incident_id"]: row for row in tables["incidents"]
    }
    providers = {
        row["provider_id"]: row for row in tables["providers"]
    }
    claims = {
        row["claim_id"]: row for row in tables["claims"]
    }
    invoices = {
        row["invoice_id"]: row for row in tables["invoices"]
    }

    # 3. Foreign keys and ownership
    check(
        all(
            row["claimant_id"] in claimants
            for row in tables["policies"]
        ),
        "Policies reference existing claimants",
        failures,
    )

    check(
        all(
            row["claimant_id"] in claimants
            for row in tables["incidents"]
        ),
        "Incidents reference existing claimants",
        failures,
    )

    check(
        all(
            row["claimant_id"] in claimants
            and row["policy_id"] in policies
            and row["incident_id"] in incidents
            and policies[row["policy_id"]]["claimant_id"]
                == row["claimant_id"]
            and incidents[row["incident_id"]]["claimant_id"]
                == row["claimant_id"]
            for row in tables["claims"]
        ),
        "Claims have valid claimant, policy, incident and ownership",
        failures,
    )

    check(
        all(
            row["claim_id"] in claims
            and row["provider_id"] in providers
            for row in tables["invoices"]
        ),
        "Invoices reference existing claims and providers",
        failures,
    )

    check(
        all(
            row["claim_id"] in claims
            and row["invoice_id"] in invoices
            and invoices[row["invoice_id"]]["claim_id"]
                == row["claim_id"]
            for row in tables["payments"]
        ),
        "Payments reference matching claims and invoices",
        failures,
    )

    # 4. Date consistency
    try:
        valid_dates = all(
            as_date(incidents[row["incident_id"]]["incident_date"])
            <= as_date(row["claim_date"])
            and as_date(policies[row["policy_id"]]["start_date"])
            <= as_date(incidents[row["incident_id"]]["incident_date"])
            <= as_date(policies[row["policy_id"]]["end_date"])
            for row in tables["claims"]
        ) and all(
            as_date(row["payment_date"])
            >= as_date(claims[row["claim_id"]]["claim_date"])
            for row in tables["payments"]
        )
    except (ValueError, KeyError):
        valid_dates = False

    check(
        valid_dates,
        "Incident, policy, claim and payment dates are consistent",
        failures,
    )

    # 5. Financial amounts
    try:
        valid_claim_amounts = all(
            0 <= float(row["approved_amount"])
            <= float(row["claimed_amount"])
            for row in tables["claims"]
        )

        valid_invoice_amounts = all(
            0 <= float(row["amount"])
            <= float(claims[row["claim_id"]]["approved_amount"])
            for row in tables["invoices"]
        )
    except (ValueError, KeyError):
        valid_claim_amounts = False
        valid_invoice_amounts = False

    check(
        valid_claim_amounts,
        "Approved amounts do not exceed claimed amounts",
        failures,
    )
    check(
        valid_invoice_amounts,
        "Invoice amounts do not exceed approved amounts",
        failures,
    )

    # 6. Verify payment overage is the planted anomaly
    overages = []
    for payment in tables["payments"]:
        claim = claims.get(payment["claim_id"])
        if claim and float(payment["amount"]) > float(
            claim["approved_amount"]
        ):
            overages.append(payment["claim_id"])

    planted_claim_id = "CLM-2026-000001"

    check(
        overages == [planted_claim_id],
        "Exactly one planted payment overage exists",
        failures,
    )

    # 7. Verify duplicate invoice across different claimants
    by_number = defaultdict(list)

    for invoice in tables["invoices"]:
        by_number[invoice["invoice_number"]].append(invoice)

    cross_claimant_duplicates = []

    for invoice_number, rows in by_number.items():
        if len(rows) < 2:
            continue

        claimant_ids = {
            claims[row["claim_id"]]["claimant_id"]
            for row in rows
        }

        if len(claimant_ids) > 1:
            cross_claimant_duplicates.append(invoice_number)

    check(
        cross_claimant_duplicates == ["INVNUM-000001"],
        "Exactly one planted cross-claimant invoice duplication exists",
        failures,
    )

    # 8. Relationship edges
    edges = tables["relationship_edges"]

    check(
        all(
            edge["source_type"] == "CLAIMANT"
            and edge["source_id"] in claimants
            and edge["target_type"] == "PROVIDER"
            and edge["target_id"] in providers
            and edge["relationship_type"] == "SERVICED_BY"
            for edge in edges
        ),
        "All relationship edges reference valid entities",
        failures,
    )

    edge_pairs = {
        (edge["source_id"], edge["target_id"])
        for edge in edges
    }

    first_invoice = next(
        row for row in tables["invoices"]
        if row["claim_id"] == planted_claim_id
    )

    missing_pair = (
        claims[planted_claim_id]["claimant_id"],
        first_invoice["provider_id"],
    )

    check(
        missing_pair not in edge_pairs,
        "Planted missing service relationship is absent",
        failures,
    )

    # 9. Benign shared address
    first_claimant = claimants["CLT-2026-000001"]
    shared_address = first_claimant["address_hash"]

    household_members = [
        row for row in tables["claimants"]
        if row["address_hash"] == shared_address
    ]

    check(
        len(household_members) > 1,
        "Benign shared household address exists",
        failures,
    )

    # 10. Missing policy exception
    check(
        len(exceptions) == 1
        and exceptions[0]["policy_id"] not in policies
        and exceptions[0]["issue_type"] == "MISSING_POLICY_REFERENCE",
        "Missing policy reference is isolated in exceptions",
        failures,
    )

    # 11. Ground-truth labels
    scenario_counts = Counter(
        row["issue_type"] for row in ground_truth
    )

    check(
        set(scenario_counts) == EXPECTED_SCENARIOS
        and all(count == 1 for count in scenario_counts.values()),
        "All five ground-truth scenarios are present exactly once",
        failures,
    )

    benign_labels = [
        row for row in ground_truth
        if row["issue_type"] == "BENIGN_SHARED_ADDRESS"
    ]

    check(
        len(benign_labels) == 1
        and benign_labels[0]["expected_label"] == "BENIGN"
        and benign_labels[0]["entity_id"]
            == first_claimant["claimant_id"],
        "Shared household is explicitly labeled benign",
        failures,
    )

    # 12. Manifest counts
    manifest_path = GENERATED / "manifest.json"

    if manifest_path.exists():
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        check(
            all(
                manifest["counts"].get(name) == len(rows)
                for name, rows in tables.items()
            ),
            "Manifest counts match generated CSV records",
            failures,
        )
    else:
        check(False, "Manifest file exists", failures)

    print("\n" + "=" * 60)

    if failures:
        print(f"VALIDATION FAILED: {len(failures)} check(s)")
        for item in failures:
            print(f" - {item}")
        raise SystemExit(1)

    print("VALIDATION PASSED: All checks successful")
    print("=" * 60)


if __name__ == "__main__":
    main()
