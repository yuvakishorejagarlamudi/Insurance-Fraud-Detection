
#!/usr/bin/env python3
"""Populate fraud indicators, investigations, and audit history."""

import csv
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "step40_test" / "insurance_schema_v2.db"
GT_PATH = ROOT / "data" / "step38_test" / "ground_truth" / "ground_truth.csv"

BASE_TIME = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)

FRAUD_RULES = {
    "PAYMENT_OVERAGE": 70,
    "DUPLICATE_INVOICE": 35,
    "MISSING_RELATIONSHIP_EDGE": 25,
    "MISSING_POLICY_REFERENCE": 60,
}


def timestamp(minutes):
    return (BASE_TIME + timedelta(minutes=minutes)).isoformat()


def read_ground_truth():
    if not GT_PATH.is_file():
        raise FileNotFoundError(f"Missing ground truth: {GT_PATH}")

    with GT_PATH.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Missing database: {DB_PATH}. Run create_schema_v2.py first."
        )

    labels = read_ground_truth()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Do not overwrite existing investigation or evidence records.
        protected_tables = [
            "fraud_indicators",
            "investigations",
            "claim_events",
            "investigation_events",
        ]

        for table in protected_tables:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            if count:
                raise RuntimeError(
                    f"Stopped safely: {table} already has {count} records."
                )

        claims = {
            row[0]
            for row in connection.execute("SELECT claim_id FROM claims")
        }

        # The invalid-policy fixture is deliberately kept outside
        # the relational database because the FK constraint rejects it.
        excluded_issues = {"MISSING_POLICY_REFERENCE"}

        anomalous_labels = [
            row for row in labels
            if row["expected_label"] == "ANOMALOUS"
            and row["issue_type"] not in excluded_issues
        ]

        for row in anomalous_labels:
            if row["claim_id"] not in claims:
                raise ValueError(
                    f"Unknown claim in ground truth: {row['claim_id']}"
                )

            if row["issue_type"] not in FRAUD_RULES:
                raise ValueError(
                    f"Unsupported fraud rule: {row['issue_type']}"
                )

        # The ground truth is used to seed expected test evidence.
        # It is NOT an independently calculated detector result.
        with connection:
            for index, row in enumerate(anomalous_labels, start=1):
                evidence = json.dumps({
                    "source": "SYNTHETIC_GROUND_TRUTH",
                    "issue_type": row["issue_type"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "expected_detection": row["expected_detection"],
                }, sort_keys=True)

                connection.execute(
                    """
                    INSERT INTO fraud_indicators (
                        indicator_id, claim_id, indicator_type,
                        risk_score, evidence, detected_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"FI-2026-{index:06d}",
                        row["claim_id"],
                        row["issue_type"],
                        FRAUD_RULES[row["issue_type"]],
                        evidence,
                        timestamp(index),
                    ),
                )

            # Create one investigation for each distinct suspicious claim.
            suspicious_claims = sorted({
                row["claim_id"] for row in anomalous_labels
            })

            for index, claim_id in enumerate(suspicious_claims, start=1):
                investigation_id = f"INVG-2026-{index:06d}"

                score = connection.execute(
                    """
                    SELECT MIN(
                        100,
                        COALESCE(SUM(risk_score), 0)
                    )
                    FROM fraud_indicators
                    WHERE claim_id = ?
                    """,
                    (claim_id,),
                ).fetchone()[0]

                priority = (
                    "HIGH" if score >= 70
                    else "MEDIUM" if score >= 30
                    else "LOW"
                )

                analyst = f"Analyst {index}"

                connection.execute(
                    """
                    INSERT INTO investigations (
                        investigation_id, claim_id, priority,
                        assigned_analyst, status, outcome, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        investigation_id,
                        claim_id,
                        priority,
                        analyst,
                        "OPEN",
                        None,
                        timestamp(100 + index),
                    ),
                )

                # Initial investigation creation event.
                connection.execute(
                    """
                    INSERT INTO investigation_events (
                        event_id, investigation_id, event_type,
                        previous_status, new_status, event_time,
                        actor, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"IEVT-2026-{index * 2 - 1:06d}",
                        investigation_id,
                        "CREATED",
                        None,
                        "OPEN",
                        timestamp(100 + index),
                        "SYSTEM",
                        "Investigation created from synthetic test evidence",
                    ),
                )

                # Status transition is recorded as a new event.
                connection.execute(
                    """
                    INSERT INTO investigation_events (
                        event_id, investigation_id, event_type,
                        previous_status, new_status, event_time,
                        actor, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"IEVT-2026-{index * 2:06d}",
                        investigation_id,
                        "ASSIGNED",
                        "OPEN",
                        "IN_PROGRESS",
                        timestamp(120 + index),
                        analyst,
                        "Assigned for fraud analyst review",
                    ),
                )

                connection.execute(
                    """
                    UPDATE investigations
                    SET status = ?
                    WHERE investigation_id = ?
                    """,
                    ("IN_PROGRESS", investigation_id),
                )

            # Claim history records represent the known final claim
            # state and a synthetic creation event, not a full
            # reconstruction of historical state transitions.
            claim_rows = connection.execute(
                "SELECT claim_id, status FROM claims ORDER BY claim_id"
            ).fetchall()

            for index, (claim_id, status) in enumerate(
                claim_rows, start=1
            ):
                connection.execute(
                    """
                    INSERT INTO claim_events (
                        event_id, claim_id, event_type,
                        previous_status, new_status,
                        event_time, actor
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"CEVT-2026-{index:06d}",
                        claim_id,
                        "INITIAL_STATE_SNAPSHOT",
                        None,
                        status,
                        timestamp(200 + index),
                        "SYNTHETIC_GENERATOR",
                    ),
                )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign-key violations: {violations[:5]}"
            )

        print("\nSTEP 40F - FRAUD AND HISTORY RESULTS")
        print("=" * 48)

        for table in protected_tables:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            print(f"{table}: {count}")

        print("Foreign-key violations:", len(violations))
        print("STEP 40F: PASSED")


if __name__ == "__main__":
    main()
