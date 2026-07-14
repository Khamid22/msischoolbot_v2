"""Attendance academic operations."""

import json

from backend.core.database import connect_auth_db
from backend.modules.academics.groups import repository as academic_repository
from backend.modules.academics.attendance import repository
from backend.modules.academics.common import (
    _now, _get_v2_enrollment, _lesson_session_for_payload,
)

def record_attendance_from_payload(payload, actor_staff_id=None):
    enrollment_id = int(payload.get("enrollment_id", 0))
    status = str(payload.get("status", "") or "").strip().casefold()
    status_aliases = {
        "p": "present",
        "present": "present",
        "a": "absent",
        "absent": "absent",
        "j": "justified",
        "justified": "justified",
        "justified absent": "justified",
        "a(i)": "justified",
        "ai": "justified",
        "l": "justified",
        "late": "justified",
    }
    status = status_aliases.get(status, status)
    if status not in {"", "present", "absent", "justified"}:
        raise ValueError("Unsupported attendance status.")
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        lesson = _lesson_session_for_payload(conn, enrollment, payload)
        if str(lesson["status"] or "").casefold() in {"cancelled", "canceled"}:
            raise ValueError("Attendance cannot be recorded for a cancelled lesson.")
        if not status:
            existing = repository.delete_attendance_record(
                conn,
                lesson_session_id=lesson["id"],
                student_id=enrollment["student_id"],
            )
            academic_repository.insert_audit_event(
                conn,
                event_type="academic.attendance_cleared",
                entity_type="lesson_session",
                entity_id=int(lesson["id"]),
                detail_json=json.dumps(
                    {"student_id": int(enrollment["student_id"]), "record_id": int(existing["id"]) if existing else None}
                ),
                actor_staff_id=actor_staff_id,
            )
            conn.commit()
            return int(existing["id"] or 0) if existing else 0
        row = repository.upsert_attendance_record(
            conn,
            lesson_session_id=lesson["id"],
            group_id=enrollment["group_id"],
            student_id=enrollment["student_id"],
            status=status,
            actor_staff_id=actor_staff_id,
            recorded_at=_now(),
        )
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.attendance_recorded",
            entity_type="attendance_record",
            entity_id=int(row["id"]),
            detail_json=json.dumps(
                {
                    "lesson_session_id": int(lesson["id"]),
                    "student_id": int(enrollment["student_id"]),
                    "status": status,
                }
            ),
            actor_staff_id=actor_staff_id,
        )
        conn.commit()
        return int(row["id"])
