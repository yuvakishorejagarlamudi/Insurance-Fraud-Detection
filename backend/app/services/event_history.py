
import json
import sqlite3
from datetime import datetime, timezone

ALLOWED_TRANSITIONS = {
    "NEW": {"IN_PROGRESS"},
    "OPEN": {"IN_PROGRESS"},
    "IN_PROGRESS": {"CLOSED"},
    "CLOSED": set()
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def record_event(
    connection,
    entity_type,
    entity_id,
    event_type,
    previous_state=None,
    new_state=None,
    actor="SYSTEM",
    details=None
):
    connection.execute(
        """
        INSERT INTO event_history (
            entity_type, entity_id, event_type,
            previous_state, new_state,
            event_timestamp, actor, details
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_type,
            entity_id,
            event_type,
            previous_state,
            new_state,
            utc_now(),
            actor,
            json.dumps(details or {}, sort_keys=True)
        )
    )

def transition_investigation(
    connection,
    investigation_id,
    new_status,
    actor="SYSTEM"
):
    row = connection.execute(
        "SELECT status FROM investigations "
        "WHERE investigation_id = ?",
        (investigation_id,)
    ).fetchone()

    if row is None:
        raise ValueError("Investigation not found")

    old_status = row[0]

    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise ValueError(
            f"Invalid transition: {old_status} -> {new_status}"
        )

    with connection:
        connection.execute(
            "UPDATE investigations SET status = ? "
            "WHERE investigation_id = ?",
            (new_status, investigation_id)
        )

        record_event(
            connection,
            entity_type="INVESTIGATION",
            entity_id=investigation_id,
            event_type="STATUS_CHANGED",
            previous_state=old_status,
            new_state=new_status,
            actor=actor
        )

    return {
        "investigation_id": investigation_id,
        "previous_status": old_status,
        "new_status": new_status
    }
