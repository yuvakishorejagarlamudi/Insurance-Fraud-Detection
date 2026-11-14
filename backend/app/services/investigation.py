from datetime import datetime, timezone
VALID = {
    "NEW":{"OPEN"},
    "OPEN":{"UNDER_REVIEW"},
    "UNDER_REVIEW":{"ESCALATED","RESOLVED"},
    "ESCALATED":{"UNDER_REVIEW","RESOLVED"},
    "RESOLVED":{"CLOSED"},
    "CLOSED":set(),
}
def transition(current: str, target: str) -> dict:
    if target not in VALID.get(current, set()):
        raise ValueError(f"Invalid investigation transition: {current} -> {target}")
    return {"from_status":current,"to_status":target,"event_at":datetime.now(timezone.utc).isoformat()}
