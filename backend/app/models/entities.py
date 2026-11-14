from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from . import __init__
from ..database import Base

class Claimant(Base):
    __tablename__ = "claimants"
    claimant_id: Mapped[str] = mapped_column(String, primary_key=True)
    claimant_name: Mapped[str] = mapped_column(String)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    address_hash: Mapped[str] = mapped_column(String, index=True)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")

class Policy(Base):
    __tablename__ = "policies"
    policy_id: Mapped[str] = mapped_column(String, primary_key=True)
    claimant_id: Mapped[str] = mapped_column(ForeignKey("claimants.claimant_id"), index=True)
    policy_type: Mapped[str] = mapped_column(String)
    coverage_amount: Mapped[float] = mapped_column(Float)
    start_date: Mapped[str] = mapped_column(String)
    end_date: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")

class Incident(Base):
    __tablename__ = "incidents"
    incident_id: Mapped[str] = mapped_column(String, primary_key=True)
    claimant_id: Mapped[str] = mapped_column(ForeignKey("claimants.claimant_id"), index=True)
    incident_date: Mapped[str] = mapped_column(String)
    incident_type: Mapped[str] = mapped_column(String)
    narrative_hash: Mapped[str] = mapped_column(String, index=True)

class Provider(Base):
    __tablename__ = "providers"
    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_name: Mapped[str] = mapped_column(String)
    provider_type: Mapped[str] = mapped_column(String)
    address_hash: Mapped[str] = mapped_column(String, index=True)
    bank_account_hash: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")

class Claim(Base):
    __tablename__ = "claims"
    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    claimant_id: Mapped[str] = mapped_column(ForeignKey("claimants.claimant_id"), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.policy_id"), index=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.incident_id"), index=True)
    claim_date: Mapped[str] = mapped_column(String)
    claimed_amount: Mapped[float] = mapped_column(Float)
    approved_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id: Mapped[str] = mapped_column(String, primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.provider_id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="SUBMITTED")

class Payment(Base):
    __tablename__ = "payments"
    payment_id: Mapped[str] = mapped_column(String, primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.invoice_id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="PAID")

class RelationshipEdge(Base):
    __tablename__ = "relationship_edges"
    edge_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_type: Mapped[str] = mapped_column(String)
    source_id: Mapped[str] = mapped_column(String, index=True)
    target_type: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String, index=True)
    relationship_type: Mapped[str] = mapped_column(String)
    strength: Mapped[float] = mapped_column(Float, default=1.0)

class FraudIndicator(Base):
    __tablename__ = "fraud_indicators"
    indicator_id: Mapped[str] = mapped_column(String, primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id"), index=True)
    indicator_type: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    detected_at: Mapped[str] = mapped_column(String)

class Investigation(Base):
    __tablename__ = "investigations"
    investigation_id: Mapped[str] = mapped_column(String, primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id"), index=True)
    status: Mapped[str] = mapped_column(String, default="NEW")
    priority: Mapped[str] = mapped_column(String)
    assigned_analyst: Mapped[str | None] = mapped_column(String, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String)
