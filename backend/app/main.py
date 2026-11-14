from backend.app.claim_intake_network_api import router as claim_intake_network_router

from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, func

from .database import Base, engine, SessionLocal
from .models.entities import (
    Claim, Claimant, Provider, Invoice,
    RelationshipEdge, Investigation, FraudIndicator,
)
from backend.app.fraud_engine import detect_fraud
from backend.app.fraud_api import router as fraud_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Insurance Fraud Detection API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Risk Helpers ----------

def fraud_scores_by_claim():
    return {
        item["claim_id"]: item
        for item in detect_fraud()
    }


def effective_risk_score(claim, fraud_by_claim):
    fraud = fraud_by_claim.get(claim.claim_id)
    if fraud is not None:
        return fraud["risk_score"]
    return claim.risk_score


def risk_category(score):
    if score >= 70:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


# ---------- Health ----------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Dashboard ----------

@app.get("/api/dashboard")
def dashboard():
    with SessionLocal() as db:
        return {
            "claimants": db.scalar(
                select(func.count()).select_from(Claimant)
            ) or 0,
            "claims": db.scalar(
                select(func.count()).select_from(Claim)
            ) or 0,
            "providers": db.scalar(
                select(func.count()).select_from(Provider)
            ) or 0,
            "investigations": db.scalar(
                select(func.count()).select_from(Investigation)
            ) or 0,
        }


# ---------- Claims ----------

@app.get("/api/claims")
def claims(limit: int = 100):
    fraud_by_claim = fraud_scores_by_claim()

    with SessionLocal() as db:
        rows = db.scalars(
            select(Claim)
            .order_by(Claim.claim_id)
            .limit(max(0, min(limit, 5000)))
        ).all()

        return [
            {
                "claim_id": row.claim_id,
                "claimant_id": row.claimant_id,
                "policy_id": row.policy_id,
                "incident_id": row.incident_id,
                "claimed_amount": row.claimed_amount,
                "approved_amount": row.approved_amount,
                "status": row.status,
                "risk_score": effective_risk_score(
                    row, fraud_by_claim
                ),
            }
            for row in rows
        ]


# ---------- Investigation Creation ----------

class InvestigationCreate(BaseModel):
    claim_id: str
    assigned_analyst: str | None = None


@app.post("/api/investigations", status_code=201)
def create_investigation(payload: InvestigationCreate):
    fraud_by_claim = fraud_scores_by_claim()

    with SessionLocal() as db:
        claim = db.get(Claim, payload.claim_id)

        if claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        score = effective_risk_score(
            claim, fraud_by_claim
        )

        if score < 35:
            raise HTTPException(
                status_code=400,
                detail="Only medium- or high-risk claims can be investigated",
            )

        existing = db.scalar(
            select(Investigation).where(
                Investigation.claim_id == payload.claim_id,
                Investigation.status != "CLOSED",
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="An open investigation already exists for this claim",
            )

        investigation = Investigation(
            investigation_id=f"INV-{uuid4().hex[:12].upper()}",
            claim_id=claim.claim_id,
            status="NEW",
            priority=risk_category(score),
            assigned_analyst=payload.assigned_analyst,
            outcome=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        db.add(investigation)
        db.commit()
        db.refresh(investigation)

        return {
            "investigation_id": investigation.investigation_id,
            "claim_id": investigation.claim_id,
            "status": investigation.status,
            "priority": investigation.priority,
            "assigned_analyst": investigation.assigned_analyst,
            "outcome": investigation.outcome,
            "created_at": investigation.created_at,
        }


# ---------- Investigation List ----------

@app.get("/api/investigations")
def list_investigations():
    with SessionLocal() as db:
        investigations = db.scalars(
            select(Investigation)
            .order_by(Investigation.created_at.desc())
        ).all()

        return [
            {
                "investigation_id": item.investigation_id,
                "claim_id": item.claim_id,
                "status": item.status,
                "priority": item.priority,
                "assigned_analyst": item.assigned_analyst,
                "outcome": item.outcome,
                "created_at": item.created_at,
            }
            for item in investigations
        ]


# ---------- Investigation Update ----------

class InvestigationUpdate(BaseModel):
    status: Literal["NEW", "IN_PROGRESS", "CLOSED"]
    outcome: str | None = None


@app.patch("/api/investigations/{investigation_id}")
def update_investigation(
    investigation_id: str,
    payload: InvestigationUpdate,
):
    with SessionLocal() as db:
        investigation = db.get(
            Investigation, investigation_id
        )

        if investigation is None:
            raise HTTPException(
                status_code=404,
                detail="Investigation not found",
            )

        allowed = {
            "NEW": {"IN_PROGRESS"},
            "IN_PROGRESS": {"CLOSED"},
            "CLOSED": set(),
        }

        if payload.status not in allowed.get(
            investigation.status, set()
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid investigation status transition",
            )

        if payload.status == "CLOSED":
            if not (
                payload.outcome and payload.outcome.strip()
            ):
                raise HTTPException(
                    status_code=400,
                    detail="An outcome is required to close an investigation",
                )

        investigation.status = payload.status

        if payload.status == "CLOSED":
            investigation.outcome = payload.outcome.strip()

        db.commit()
        db.refresh(investigation)

        return {
            "investigation_id": investigation.investigation_id,
            "claim_id": investigation.claim_id,
            "status": investigation.status,
            "priority": investigation.priority,
            "assigned_analyst": investigation.assigned_analyst,
            "outcome": investigation.outcome,
            "created_at": investigation.created_at,
        }


# ---------- Fraud Evidence ----------
# Updated: combine stored evidence with fraud-engine evidence.

@app.get("/api/claims/{claim_id}/evidence")
def get_claim_evidence(claim_id: str):
    fraud_by_claim = fraud_scores_by_claim()

    with SessionLocal() as db:
        claim = db.get(Claim, claim_id)

        if claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        stored = db.scalars(
            select(FraudIndicator)
            .where(FraudIndicator.claim_id == claim_id)
            .order_by(FraudIndicator.indicator_type)
        ).all()

        score = effective_risk_score(
            claim, fraud_by_claim
        )

        indicators = []
        seen_types = set()

        # Existing database indicators
        for item in stored:
            indicator_type = item.indicator_type

            if indicator_type in seen_types:
                continue

            seen_types.add(indicator_type)

            indicators.append({
                "indicator_id": item.indicator_id,
                "indicator_type": indicator_type,
                "description": item.description,
                "score": item.score,
                "detected_at": item.detected_at,
            })

        # New fraud-engine indicators
        fraud = fraud_by_claim.get(claim_id, {})
        engine_indicators = fraud.get("indicators", [])

        for index, item in enumerate(engine_indicators):
            if isinstance(item, str):
                indicator_type = item
                description = item.replace("_", " ").title()
                indicator_score = 0

            elif isinstance(item, dict):
                indicator_type = (
                    item.get("indicator_type")
                    or item.get("type")
                    or item.get("code")
                    or item.get("name")
                )

                description = (
                    item.get("description")
                    or item.get("reason")
                    or (
                        ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in item.get("evidence", {}).items())
                        if isinstance(item.get("evidence"), dict) else None
                    )
                    or str(indicator_type)
                )

                indicator_score = (
                    item.get("score")
                    or item.get("risk_score")
                    or item.get("weight")
                    or 0
                )

            else:
                continue

            if not indicator_type:
                continue

            if indicator_type in seen_types:
                continue

            seen_types.add(indicator_type)

            indicators.append({
                "indicator_id": f"ENGINE-{claim_id}-{index + 1}",
                "indicator_type": indicator_type,
                "description": description,
                "score": indicator_score,
                "detected_at": None,
            })

        return {
            "claim_id": claim.claim_id,
            "claimant_id": claim.claimant_id,
            "risk_score": score,
            "risk_category": risk_category(score),
            "claimed_amount": claim.claimed_amount,
            "approved_amount": claim.approved_amount,
            "indicators": indicators,
            "indicator_count": len(indicators),
        }


# ---------- Suspicious Network ----------

@app.get("/api/network/{claim_id}")
def get_claim_network(claim_id: str):
    fraud_by_claim = fraud_scores_by_claim()

    with SessionLocal() as db:
        claim = db.get(Claim, claim_id)

        if claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        score = effective_risk_score(
            claim, fraud_by_claim
        )

        nodes = {}
        links = []
        link_keys = set()

        def add_node(node_type, node_id, label, **details):
            key = f"{node_type}:{node_id}"

            nodes[key] = {
                "id": key,
                "type": node_type,
                "label": label,
                **details,
            }

            return key

        def add_link(source, target, relationship):
            key = (source, target, relationship)

            if key not in link_keys:
                link_keys.add(key)

                links.append({
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                })

        claim_node = add_node(
            "CLAIM",
            claim.claim_id,
            claim.claim_id,
            risk_score=score,
        )

        claimant = db.get(
            Claimant, claim.claimant_id
        )

        if claimant:
            claimant_node = add_node(
                "CLAIMANT",
                claimant.claimant_id,
                claimant.claimant_name,
            )

            add_link(
                claimant_node,
                claim_node,
                "FILED_CLAIM",
            )

        invoices = db.scalars(
            select(Invoice).where(
                Invoice.claim_id == claim_id
            )
        ).all()

        for invoice in invoices:
            invoice_node = add_node(
                "INVOICE",
                invoice.invoice_id,
                invoice.invoice_number,
                amount=invoice.amount,
            )

            add_link(
                claim_node,
                invoice_node,
                "HAS_INVOICE",
            )

            provider = db.get(
                Provider, invoice.provider_id
            )

            if provider:
                provider_node = add_node(
                    "PROVIDER",
                    provider.provider_id,
                    provider.provider_name,
                )

                add_link(
                    invoice_node,
                    provider_node,
                    "BILLED_BY",
                )

        node_ids = {
            (
                node["type"],
                node["id"].split(":", 1)[1],
            )
            for node in nodes.values()
        }

        edges = db.scalars(
            select(RelationshipEdge)
        ).all()

        stored_relationship_count = 0

        for edge in edges:
            source_key = (
                edge.source_type.upper(),
                edge.source_id,
            )

            target_key = (
                edge.target_type.upper(),
                edge.target_id,
            )

            if (
                source_key in node_ids
                and target_key in node_ids
            ):
                before = len(links)

                add_link(
                    f"{source_key[0]}:{source_key[1]}",
                    f"{target_key[0]}:{target_key[1]}",
                    edge.relationship_type,
                )

                if len(links) > before:
                    stored_relationship_count += 1

        return {
            "claim_id": claim_id,
            "risk_score": score,
            "node_count": len(nodes),
            "link_count": len(links),
            "stored_relationship_count": stored_relationship_count,
            "nodes": list(nodes.values()),
            "links": links,
        }


# ---------- Fraud Intelligence Routes ----------

app.include_router(fraud_router)

from .claimant_api import router as claimant_router
app.include_router(claimant_router)

from backend.app.claim_intake_api import router as claim_intake_router
app.include_router(claim_intake_router)

app.include_router(claim_intake_network_router)
