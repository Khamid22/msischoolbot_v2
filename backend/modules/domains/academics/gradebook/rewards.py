"""Gradebook academic operations."""


from backend.core.database import connect_auth_db
from backend.modules.domains.academics.common import (
    _now, _get_v2_enrollment,
)
from backend.modules.domains.academics.gradebook import repository

def record_coin_from_payload(payload):
    enrollment_id = int(payload.get("enrollment_id", 0))
    amount = int(payload.get("amount", 0))
    source = str(payload.get("source", "manual") or "manual").strip()
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        row = repository.insert_coin_event(
            conn,
            student_id=enrollment["student_id"],
            group_id=enrollment["group_id"],
            amount=amount,
            source=source,
            occurred_at=_now(),
        )
        conn.commit()
        return int(row["id"])
