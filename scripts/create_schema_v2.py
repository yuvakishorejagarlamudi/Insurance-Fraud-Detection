
#!/usr/bin/env python3
"""Create an isolated relational schema for insurance fraud testing."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "step40_test" / "insurance_schema_v2.db"


def create_schema():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
        CREATE TABLE IF NOT EXISTS claimants (
            claimant_id TEXT PRIMARY KEY,
            claimant_name TEXT NOT NULL,
            address_hash TEXT NOT NULL,
            phone_hash TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY,
            claimant_id TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            coverage_amount REAL NOT NULL CHECK (coverage_amount >= 0),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (claimant_id) REFERENCES claimants(claimant_id),
            CHECK (end_date >= start_date)
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            claimant_id TEXT NOT NULL,
            incident_date TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            narrative_hash TEXT NOT NULL,
            FOREIGN KEY (claimant_id) REFERENCES claimants(claimant_id)
        );

        CREATE TABLE IF NOT EXISTS providers (
            provider_id TEXT PRIMARY KEY,
            provider_name TEXT NOT NULL,
            provider_type TEXT NOT NULL,
            address_hash TEXT NOT NULL,
            bank_account_hash TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            claimant_id TEXT NOT NULL,
            policy_id TEXT NOT NULL,
            incident_id TEXT NOT NULL,
            claim_date TEXT NOT NULL,
            claimed_amount REAL NOT NULL CHECK (claimed_amount >= 0),
            approved_amount REAL NOT NULL CHECK (
                approved_amount >= 0 AND approved_amount <= claimed_amount
            ),
            status TEXT NOT NULL,
            FOREIGN KEY (claimant_id) REFERENCES claimants(claimant_id),
            FOREIGN KEY (policy_id) REFERENCES policies(policy_id),
            FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount >= 0),
            status TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount >= 0),
            payment_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
        );

        CREATE TABLE IF NOT EXISTS relationship_edges (
            edge_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            strength REAL NOT NULL CHECK (strength BETWEEN 0 AND 1)
        );

        CREATE TABLE IF NOT EXISTS fraud_indicators (
            indicator_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            indicator_type TEXT NOT NULL,
            risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
            evidence TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS investigations (
            investigation_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            priority TEXT NOT NULL,
            assigned_analyst TEXT,
            status TEXT NOT NULL,
            outcome TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS claim_events (
            event_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            event_time TEXT NOT NULL,
            actor TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS investigation_events (
            event_id TEXT PRIMARY KEY,
            investigation_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            event_time TEXT NOT NULL,
            actor TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (investigation_id)
                REFERENCES investigations(investigation_id)
        );

        CREATE TABLE IF NOT EXISTS claim_providers (
            claim_id TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            role TEXT NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT,
            PRIMARY KEY (claim_id, provider_id, role, effective_from),
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY (provider_id) REFERENCES providers(provider_id),
            CHECK (
                effective_to IS NULL OR effective_to >= effective_from
            )
        );

        CREATE INDEX IF NOT EXISTS idx_claims_claimant
            ON claims(claimant_id);

        CREATE INDEX IF NOT EXISTS idx_claims_policy
            ON claims(policy_id);

        CREATE INDEX IF NOT EXISTS idx_invoices_claim
            ON invoices(claim_id);

        CREATE INDEX IF NOT EXISTS idx_payments_claim
            ON payments(claim_id);

        CREATE INDEX IF NOT EXISTS idx_fraud_indicators_claim
            ON fraud_indicators(claim_id);

        CREATE INDEX IF NOT EXISTS idx_investigations_claim
            ON investigations(claim_id);

        CREATE INDEX IF NOT EXISTS idx_claim_events_claim
            ON claim_events(claim_id);

        CREATE INDEX IF NOT EXISTS idx_investigation_events_investigation
            ON investigation_events(investigation_id);
        """)

        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print("DATABASE:", DB_PATH)
        print("TABLE COUNT:", len(tables))
        print("INTEGRITY CHECK:", integrity)
        print("\nTABLES:")

        for (name,) in tables:
            print(" -", name)


if __name__ == "__main__":
    create_schema()
