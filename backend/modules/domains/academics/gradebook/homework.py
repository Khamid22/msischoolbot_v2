"""Gradebook academic operations."""

import json

from backend.core.database import connect_auth_db
from backend.modules.domains.academics.groups import repository as academic_repository
from backend.modules.domains.academics.gradebook import repository
from backend.modules.domains.academics.common import (
    _now, _get_v2_enrollment, _lesson_session_for_payload,
)

def record_homework_from_payload(payload, actor_staff_id=None):
    enrollment_id = int(payload.get("enrollment_id", 0))
    score = float(payload.get("score", 0))
    if score < 1 or score > 9:
        raise ValueError("Homework score must be between 1 and 9.")
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        lesson = _lesson_session_for_payload(conn, enrollment, payload)
        if str(lesson["status"] or "").casefold() in {"cancelled", "canceled"}:
            raise ValueError("Homework cannot be recorded for a cancelled lesson.")
        if not lesson["program_item_id"] and str(lesson["source_kind"] or "").casefold() != "lesson":
            raise ValueError("Homework can only be recorded for lesson sessions.")
        row = repository.upsert_homework_score(
            conn,
            lesson_session_id=lesson["id"],
            group_id=enrollment["group_id"],
            student_id=enrollment["student_id"],
            score=score,
            actor_staff_id=actor_staff_id,
            recorded_at=_now(),
        )
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.homework_recorded",
            entity_type="homework_score",
            entity_id=int(row["id"]),
            detail_json=json.dumps(
                {
                    "lesson_session_id": int(lesson["id"]),
                    "student_id": int(enrollment["student_id"]),
                    "score": score,
                }
            ),
            actor_staff_id=actor_staff_id,
        )
        conn.commit()
        return int(row["id"])
