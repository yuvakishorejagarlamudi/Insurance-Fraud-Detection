from collections import defaultdict
from .risk_scoring import score_claim

def detect_claim_indicators(claims, invoices, payments, edges):
    """Rule-based detection; returns indicators with evidence-linked descriptions."""
    by_claim_invoice = defaultdict(list)
    by_claim_payment = defaultdict(list)
    invoice_numbers = defaultdict(list)
    for inv in invoices:
        by_claim_invoice[inv["claim_id"]].append(inv)
        invoice_numbers[inv["invoice_number"]].append(inv)
    for pay in payments:
        by_claim_payment[pay["claim_id"]].append(pay)

    output = []
    for claim in claims:
        cid = claim["claim_id"]
        indicators = []
        paid = sum(float(p["amount"]) for p in by_claim_payment[cid])
        approved = float(claim["approved_amount"])
        if paid > approved:
            indicators.append({
                "indicator_type": "PAYMENT_OVERAGE",
                "description": f"Payments total {paid:.2f}, exceeding approved amount {approved:.2f}",
            })
        for inv in by_claim_invoice[cid]:
            dupes = invoice_numbers[inv["invoice_number"]]
            if len(dupes) > 1:
                indicators.append({
                    "indicator_type": "DUPLICATE_INVOICE",
                    "description": f"Invoice number {inv['invoice_number']} appears {len(dupes)} times",
                })
        risk = score_claim(claim, indicators)
        output.append({
            "claim_id": cid, "risk_score": risk.score,
            "risk_category": risk.category, "reasons": risk.reasons,
            "indicators": indicators,
        })
    return output
