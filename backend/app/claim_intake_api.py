
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import uuid
import json

router = APIRouter(prefix="/api/claim-intake", tags=["Claim Intake"])

DB = Path(__file__).resolve().parents[2] / "insurance_fraud.db"


class NewClaim(BaseModel):
    claimant_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    incident_description: str = Field(min_length=5)
    provider_id: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    claimed_amount: float = Field(gt=0)
    approved_amount: float = Field(ge=0)
    payment_amount: float = Field(ge=0)
    incident_date: str


def connection():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def setup():
    with connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS claim_intake (
                claim_id TEXT PRIMARY KEY,
                claimant_id TEXT NOT NULL,
                policy_id TEXT NOT NULL,
                incident_description TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                claimed_amount REAL NOT NULL,
                approved_amount REAL NOT NULL,
                payment_amount REAL NOT NULL,
                incident_date TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                indicators_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS claim_intake_investigations (
                investigation_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'OPEN',
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claim_intake(claim_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS claim_intake_events (
                event_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id)
                    REFERENCES claim_intake(claim_id)
            )
        """)


setup()


def exists(db, table, column, value):
    allowed = {
        ("claimants", "claimant_id"),
        ("policies", "policy_id"),
        ("providers", "provider_id"),
    }

    if (table, column) not in allowed:
        raise ValueError("Unsupported lookup")

    return db.execute(
        f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1",
        (value,)
    ).fetchone() is not None


def analyze(db, data):
    indicators = []

    def flag(code, score, evidence):
        indicators.append({
            "code": code,
            "score": score,
            "evidence": evidence
        })

    if not exists(db, "claimants", "claimant_id", data.claimant_id):
        raise HTTPException(422, "Claimant does not exist")

    if not exists(db, "providers", "provider_id", data.provider_id):
        raise HTTPException(422, "Provider does not exist")

    if not exists(db, "policies", "policy_id", data.policy_id):
        raise HTTPException(422, "Policy does not exist")

    owner = db.execute(
        "SELECT claimant_id FROM policies WHERE policy_id=?",
        (data.policy_id,)
    ).fetchone()

    if owner["claimant_id"] != data.claimant_id:
        raise HTTPException(
            422, "Policy does not belong to this claimant"
        )

    try:
        incident_day = datetime.fromisoformat(data.incident_date).date()
    except ValueError:
        raise HTTPException(422, "Use YYYY-MM-DD for incident_date")

    if incident_day > datetime.now(timezone.utc).date():
        raise HTTPException(422, "Incident date cannot be in the future")

    if data.approved_amount > data.claimed_amount:
        raise HTTPException(
            422, "Approved amount exceeds claimed amount"
        )

    if data.payment_amount > data.approved_amount:
        flag(
            "PAYMENT_OVERAGE",
            70,
            {
                "payment_amount": data.payment_amount,
                "approved_amount": data.approved_amount,
                "overage": round(
                    data.payment_amount - data.approved_amount, 2
                )
            }
        )

    # Check duplicate invoice against previously submitted intake claims.
    duplicates = db.execute("""
        SELECT claim_id, claimant_id
        FROM claim_intake
        WHERE invoice_number=?
          AND claimant_id<>?
        LIMIT 5
    """, (data.invoice_number, data.claimant_id)).fetchall()

    if duplicates:
        flag(
            "DUPLICATE_INVOICE",
            35,
            {
                "invoice_number": data.invoice_number,
                "matching_claim_ids": [
                    row["claim_id"] for row in duplicates
                ]
            }
        )

    # Also check invoices already stored in the main database.
    invoice_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(invoices)")
    }

    if {"invoice_number", "claim_id"}.issubset(invoice_columns):
        existing = db.execute("""
            SELECT i.claim_id, c.claimant_id
            FROM invoices i
            JOIN claims c ON c.claim_id=i.claim_id
            WHERE i.invoice_number=?
              AND c.claimant_id<>?
            LIMIT 5
        """, (data.invoice_number, data.claimant_id)).fetchall()

        if existing and not any(
            item["code"] == "DUPLICATE_INVOICE"
            for item in indicators
        ):
            flag(
                "DUPLICATE_INVOICE",
                35,
                {
                    "invoice_number": data.invoice_number,
                    "matching_claim_ids": [
                        row["claim_id"] for row in existing
                    ]
                }
            )

    score = min(100, sum(item["score"] for item in indicators))

    level = (
        "HIGH" if score >= 70
        else "MEDIUM" if score >= 30
        else "LOW"
    )

    return {
        "risk_score": score,
        "risk_level": level,
        "indicators": indicators,
        "decision": (
            "REQUIRES_REVIEW" if indicators else "NORMAL_REVIEW"
        )
    }


@router.post("/submit", status_code=201)
def submit_claim(data: NewClaim):
    setup()

    with connection() as db:
        db.execute("BEGIN IMMEDIATE")

        result = analyze(db, data)

        claim_id = "CLM-INTAKE-" + uuid.uuid4().hex[:12].upper()
        timestamp = datetime.now(timezone.utc).isoformat()

        db.execute("""
            INSERT INTO claim_intake (
                claim_id, claimant_id, policy_id,
                incident_description, provider_id,
                invoice_number, claimed_amount,
                approved_amount, payment_amount,
                incident_date, risk_score, risk_level,
                indicators_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_id,
            data.claimant_id,
            data.policy_id,
            data.incident_description,
            data.provider_id,
            data.invoice_number,
            data.claimed_amount,
            data.approved_amount,
            data.payment_amount,
            data.incident_date,
            result["risk_score"],
            result["risk_level"],
            json.dumps(result["indicators"]),
            timestamp
        ))

        # AUTO_INVESTIGATION_V1
        investigation_id = None

        if result["risk_level"] in ("HIGH", "MEDIUM"):
            investigation_id = "INV-AUTO-" + uuid.uuid4().hex[:12].upper()

            db.execute("""
                INSERT INTO claim_intake_investigations (
                    investigation_id, claim_id, status,
                    risk_level, risk_score, evidence_json,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                investigation_id,
                claim_id,
                "OPEN",
                result["risk_level"],
                result["risk_score"],
                json.dumps(result["indicators"]),
                timestamp,
                timestamp
            ))

        for event_type, details in (
            ("CLAIM_SUBMITTED", data.model_dump()),
            ("FRAUD_ANALYZED", result),
        ):
            db.execute("""
                INSERT INTO claim_intake_events
                (event_id, claim_id, event_type, details_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                claim_id,
                event_type,
                json.dumps(details),
                timestamp
            ))

        if investigation_id:
            db.execute("""
                INSERT INTO claim_intake_events
                (event_id, claim_id, event_type, details_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                claim_id,
                "INVESTIGATION_CREATED",
                json.dumps({"investigation_id": investigation_id}),
                timestamp
            ))

        db.commit()

        return {
            "claim_id": claim_id,
            "investigation_id": investigation_id,
            "status": "SUBMITTED",
            **result
        }


@router.get("/{claim_id}")
def get_claim(claim_id: str):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM claim_intake WHERE claim_id=?",
            (claim_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(404, "Claim not found")

        result = dict(row)
        result["indicators"] = json.loads(
            result.pop("indicators_json")
        )

        events = db.execute("""
            SELECT event_id, event_type, details_json, created_at
            FROM claim_intake_events
            WHERE claim_id=?
            ORDER BY created_at, rowid
        """, (claim_id,)).fetchall()

        result["events"] = [
            {
                **dict(event),
                "details": json.loads(event["details_json"])
            }
            for event in events
        ]

        for event in result["events"]:
            del event["details_json"]

        return result


@router.get("/investigations/all")
def list_auto_investigations():
    setup()
    with connection() as db:
        rows = db.execute("""
            SELECT * FROM claim_intake_investigations
            ORDER BY created_at DESC
        """).fetchall()

        return [
            {
                **dict(row),
                "evidence": json.loads(row["evidence_json"])
            }
            for row in rows
        ]


class InvestigationUpdate(BaseModel):
    status: str


@router.patch("/investigations/{investigation_id}")
def update_auto_investigation(
    investigation_id: str,
    data: InvestigationUpdate
):
    allowed = {"OPEN", "IN_PROGRESS", "CLOSED"}

    if data.status not in allowed:
        raise HTTPException(
            422,
            "Status must be OPEN, IN_PROGRESS or CLOSED"
        )

    timestamp = datetime.now(timezone.utc).isoformat()

    with connection() as db:
        row = db.execute("""
            SELECT claim_id, status
            FROM claim_intake_investigations
            WHERE investigation_id=?
        """, (investigation_id,)).fetchone()

        if row is None:
            raise HTTPException(404, "Investigation not found")

        # Validate investigation lifecycle before updating
        allowed_transitions = {
            "OPEN": {"IN_PROGRESS"},
            "IN_PROGRESS": {"CLOSED"},
            "CLOSED": set()
        }

        previous_status = row["status"]
        requested_status = data.status

        if requested_status not in allowed_transitions.get(
            previous_status, set()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid investigation transition: "
                    f"{previous_status} -> {requested_status}"
                )
            )

        db.execute("""
            UPDATE claim_intake_investigations
            SET status=?, updated_at=?
            WHERE investigation_id=?
        """, (data.status, timestamp, investigation_id))

        db.execute("""
            INSERT INTO claim_intake_events
            (event_id, claim_id, event_type, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            row["claim_id"],
            "INVESTIGATION_STATUS_CHANGED",
            json.dumps({
                "investigation_id": investigation_id,
                "previous_status": row["status"],
                "new_status": data.status
            }),
            timestamp
        ))

        db.commit()

        return {
            "investigation_id": investigation_id,
            "status": data.status,
            "updated_at": timestamp
        }
