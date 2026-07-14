"""Assessments academic operations."""

import json

from backend.core.database import connect_auth_db
from backend.modules.academics.groups import repository as academic_repository
from backend.modules.academics.assessments import repository
from backend.modules.academics.common import (
    _now, _get_v2_enrollment,
)

def record_exam_from_payload(payload, actor_staff_id=None):
    enrollment_id = int(payload.get("enrollment_id", 0))
    exam_name = str(payload.get("exam_name") or payload.get("label") or "").strip()
    if not exam_name:
        raise ValueError("Exam name is required.")
    attempt = str(payload.get("attempt", "") or "").strip()
    score = float(payload.get("score", 0))
    if score < 1 or score > 9:
        raise ValueError("Exam score must be between 1 and 9.")
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        program_item = repository.find_exam_program_item(
            conn, group_id=enrollment["group_id"], exam_name=exam_name
        )
        recorded_at = _now()
        row = repository.insert_exam_result_if_missing(
            conn,
            group_id=enrollment["group_id"],
            program_item_id=program_item["id"] if program_item else None,
            student_id=enrollment["student_id"],
            exam_name=exam_name,
            attempt=attempt,
            score=score,
            actor_staff_id=actor_staff_id,
            recorded_at=recorded_at,
        )
        if not row:
            row = repository.update_exam_result(
                conn,
                group_id=enrollment["group_id"],
                program_item_id=program_item["id"] if program_item else None,
                student_id=enrollment["student_id"],
                exam_name=exam_name,
                attempt=attempt,
                score=score,
                actor_staff_id=actor_staff_id,
                recorded_at=recorded_at,
            )
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.exam_recorded",
            entity_type="exam_result",
            entity_id=int(row["id"]),
            detail_json=json.dumps(
                {
                    "student_id": int(enrollment["student_id"]),
                    "exam_name": exam_name,
                    "attempt": attempt,
                    "score": score,
                }
            ),
            actor_staff_id=actor_staff_id,
        )
        conn.commit()
        return int(row["id"])
