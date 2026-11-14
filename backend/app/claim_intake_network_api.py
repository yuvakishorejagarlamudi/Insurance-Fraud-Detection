
from fastapi import APIRouter, HTTPException
from backend.app.claim_intake_api import connection, setup

router = APIRouter(
    prefix="/api/claim-intake-network",
    tags=["Claim Intake Network"]
)


def table_columns(db, table):
    return {
        row["name"]
        for row in db.execute(f"PRAGMA table_info({table})")
    }


@router.get("/{claim_id}")
def analyze_claim_network(claim_id: str):
    setup()

    with connection() as db:
        claim = db.execute("""
            SELECT * FROM claim_intake
            WHERE claim_id=?
        """, (claim_id,)).fetchone()

        if claim is None:
            raise HTTPException(404, "Claim not found")

        claimant_id = claim["claimant_id"]
        provider_id = claim["provider_id"]
        invoice_number = claim["invoice_number"]

        # Related claims from the original validated dataset.
        related_claims = []

        columns = table_columns(db, "claims")

        if {"claim_id", "claimant_id"}.issubset(columns):
            rows = db.execute("""
                SELECT claim_id
                FROM claims
                WHERE claimant_id=?
                LIMIT 30
            """, (claimant_id,)).fetchall()

            related_claims = [r["claim_id"] for r in rows]

        # Other newly submitted claims sharing the same provider.
        shared_provider = db.execute("""
            SELECT claim_id, claimant_id
            FROM claim_intake
            WHERE provider_id=?
              AND claim_id<>?
            LIMIT 30
        """, (provider_id, claim_id)).fetchall()

        # Other newly submitted claims sharing an invoice.
        shared_invoice = db.execute("""
            SELECT claim_id, claimant_id
            FROM claim_intake
            WHERE invoice_number=?
              AND claim_id<>?
            LIMIT 30
        """, (invoice_number, claim_id)).fetchall()

        evidence = {
            "existing_claims_same_claimant": related_claims,
            "shared_provider_claims": [
                dict(row) for row in shared_provider
            ],
            "shared_invoice_claims": [
                dict(row) for row in shared_invoice
            ]
        }

        return {
            "claim_id": claim_id,
            "claimant_id": claimant_id,
            "provider_id": provider_id,
            "network_evidence": evidence,
            "connection_counts": {
                "same_claimant": len(related_claims),
                "shared_provider": len(shared_provider),
                "shared_invoice": len(shared_invoice)
            },
            "note": (
                "Connections are investigative leads, "
                "not proof of fraud."
            )
        }
