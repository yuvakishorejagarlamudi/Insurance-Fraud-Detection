
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "insurance_fraud.db"

RULE_SCORES = {
    "PAYMENT_OVERAGE": 70,
    "DUPLICATE_INVOICE": 35,
    "MISSING_RELATIONSHIP_EDGE": 25,
}


def detect_fraud():
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    try:
        indicators = []
        seen = set()

        def add_indicator(claim_id, rule, evidence):
            key = (
                claim_id,
                rule,
                json.dumps(evidence, sort_keys=True)
            )

            if key not in seen:
                seen.add(key)

                indicators.append({
                    "claim_id": claim_id,
                    "indicator_type": rule,
                    "risk_score": RULE_SCORES[rule],
                    "evidence": evidence,
                })

        # RULE 1: PAYMENT OVERAGE
        # Compare total payments against approved claim amount.

        rows = conn.execute("""
            SELECT
                c.claim_id,
                c.approved_amount,
                SUM(p.amount) AS total_payment_amount,
                COUNT(p.payment_id) AS payment_count,
                GROUP_CONCAT(p.payment_id) AS payment_ids
            FROM claims c
            JOIN payments p ON p.claim_id = c.claim_id
            GROUP BY c.claim_id, c.approved_amount
            HAVING ROUND(SUM(p.amount), 2)
                 > ROUND(c.approved_amount, 2)
        """).fetchall()

        for row in rows:
            add_indicator(
                row["claim_id"],
                "PAYMENT_OVERAGE",
                {
                    "payment_ids": row["payment_ids"],
                    "payment_count": row["payment_count"],
                    "total_payment_amount": row["total_payment_amount"],
                    "approved_amount": row["approved_amount"],
                }
            )

        # RULE 2: CROSS-CLAIMANT DUPLICATE INVOICE
        # Flag subsequent records, not the original invoice.

        duplicates = conn.execute("""
            WITH claimant_counts AS (
                SELECT
                    i.invoice_number,
                    COUNT(DISTINCT c.claimant_id) AS claimant_count
                FROM invoices i
                JOIN claims c ON c.claim_id = i.claim_id
                GROUP BY i.invoice_number
                HAVING COUNT(DISTINCT c.claimant_id) > 1
            ),
            ranked_invoices AS (
                SELECT
                    i.invoice_id,
                    i.invoice_number,
                    i.claim_id,
                    c.claimant_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY i.invoice_number
                        ORDER BY i.invoice_id
                    ) AS invoice_rank
                FROM invoices i
                JOIN claims c ON c.claim_id = i.claim_id
            )
            SELECT
                r.invoice_id,
                r.invoice_number,
                r.claim_id,
                r.claimant_id,
                cc.claimant_count
            FROM ranked_invoices r
            JOIN claimant_counts cc
                ON cc.invoice_number = r.invoice_number
            WHERE r.invoice_rank > 1
        """).fetchall()

        for row in duplicates:
            add_indicator(
                row["claim_id"],
                "DUPLICATE_INVOICE",
                {
                    "invoice_id": row["invoice_id"],
                    "invoice_number": row["invoice_number"],
                    "claimant_id": row["claimant_id"],
                    "different_claimants": row["claimant_count"],
                }
            )

        # RULE 3: MISSING CLAIMANT-PROVIDER RELATIONSHIP EDGE
        # Verify service relationships using invoice and claim records.

        missing_edges = conn.execute("""
            SELECT DISTINCT
                c.claim_id,
                c.claimant_id,
                i.provider_id
            FROM claims c
            JOIN invoices i
                ON i.claim_id = c.claim_id
            WHERE i.provider_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM relationship_edges e
                  WHERE e.source_type = 'CLAIMANT'
                    AND e.source_id = c.claimant_id
                    AND e.target_type = 'PROVIDER'
                    AND e.target_id = i.provider_id
                    AND e.relationship_type = 'SERVICED_BY'
              )
        """).fetchall()

        for row in missing_edges:
            add_indicator(
                row["claim_id"],
                "MISSING_RELATIONSHIP_EDGE",
                {
                    "claimant_id": row["claimant_id"],
                    "provider_id": row["provider_id"],
                    "reason": "No matching relationship edge",
                }
            )

        # CALCULATE RISK SCORES

        by_claim = defaultdict(list)

        for indicator in indicators:
            by_claim[indicator["claim_id"]].append(indicator)

        results = []

        for claim_id, claim_indicators in by_claim.items():
            score = min(
                100,
                sum(
                    item["risk_score"]
                    for item in claim_indicators
                )
            )

            risk_level = (
                "HIGH" if score >= 70
                else "MEDIUM" if score >= 35
                else "LOW"
            )

            results.append({
                "claim_id": claim_id,
                "risk_score": score,
                "risk_level": risk_level,
                "indicators": claim_indicators,
            })

        results.sort(
            key=lambda item: (
                -item["risk_score"],
                item["claim_id"]
            )
        )

        return results

    finally:
        conn.close()


if __name__ == "__main__":
    results = detect_fraud()

    print("\nINSURANCE FRAUD DETECTION RESULTS")
    print("=" * 60)

    print("Suspicious claims detected:", len(results))

    for result in results:
        print(
            "\nClaim:", result["claim_id"],
            "| Risk Score:", result["risk_score"],
            "| Risk Level:", result["risk_level"]
        )

        for indicator in result["indicators"]:
            print(
                "  Indicator:",
                indicator["indicator_type"]
            )
            print(
                "  Evidence:",
                json.dumps(indicator["evidence"], indent=2)
            )

    print("\nSTEP 42: DETECTION ENGINE EXECUTED")
    print("=" * 60)
