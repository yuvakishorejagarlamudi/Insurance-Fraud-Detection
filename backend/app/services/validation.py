from collections import Counter

def validate_dataset(data: dict) -> list[dict]:
    errors = []
    # Primary keys
    for table, key in [
        ("claimants", "claimant_id"), ("policies", "policy_id"),
        ("claims", "claim_id"), ("incidents", "incident_id"),
        ("providers", "provider_id"), ("invoices", "invoice_id"),
        ("payments", "payment_id"), ("relationship_edges", "edge_id")
    ]:
        ids = [row.get(key) for row in data.get(table, [])]
        for value, count in Counter(ids).items():
            if value is None or count > 1:
                errors.append({"table": table, "key": value, "error": "NULL_OR_DUPLICATE_PRIMARY_KEY"})
    # FK integrity
    sets = {t: {r[k] for r in data.get(t, [])} for t, k in [
        ("claimants","claimant_id"), ("policies","policy_id"),
        ("incidents","incident_id"), ("providers","provider_id"),
        ("claims","claim_id"), ("invoices","invoice_id")
    ]}
    for row in data.get("policies", []):
        if row["claimant_id"] not in sets["claimants"]:
            errors.append({"table":"policies","key":row["policy_id"],"error":"INVALID_CLAIMANT_FK"})
    for row in data.get("claims", []):
        for field, parent in [("claimant_id","claimants"),("policy_id","policies"),("incident_id","incidents")]:
            if row[field] not in sets[parent]:
                errors.append({"table":"claims","key":row["claim_id"],"error":f"INVALID_{field.upper()}_FK"})
    for row in data.get("invoices", []):
        if row["claim_id"] not in sets["claims"] or row["provider_id"] not in sets["providers"]:
            errors.append({"table":"invoices","key":row["invoice_id"],"error":"INVALID_INVOICE_FK"})
    for row in data.get("payments", []):
        if row["claim_id"] not in sets["claims"] or row["invoice_id"] not in sets["invoices"]:
            errors.append({"table":"payments","key":row["payment_id"],"error":"INVALID_PAYMENT_FK"})
    return errors
