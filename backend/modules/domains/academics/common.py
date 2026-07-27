"""Shared academic operation helpers."""

import re
from datetime import UTC, datetime

from backend.modules.domains.organization import canonical
from backend.modules.domains.academics.groups import repository as group_repository
from backend.modules.domains.academics.timetable import repository as timetable_repository


_LESSON_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")

def _now():
    return datetime.now(UTC)


def _legacy_or_v2_group_where():
    return "(g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))"


def _legacy_or_v2_enrollment_where():
    return "(gs.legacy_enrollment_id = %s)"


def _lesson_order_from_label(value):
    match = re.search(r"(\d+)", str(value or ""))
    if not match:
        return 0
    return int(match.group(1))


def _get_v2_enrollment(conn, enrollment_id):
    return group_repository.get_enrollment_by_legacy_id(conn, enrollment_id)


def _get_v2_lesson_session(conn, group_id, lesson_label):
    lesson_order = _lesson_order_from_label(lesson_label)
    if lesson_order <= 0:
        raise ValueError("Lesson label must include a lesson number.")
    row = timetable_repository.get_curriculum_lesson_session_by_order(
        conn, group_id, lesson_order
    )
    if not row:
        raise ValueError("Lesson not found in the clean subject program.")
    return row


def _get_v2_lesson_session_by_id(conn, group_id, lesson_session_id):
    lesson_session_id = int(lesson_session_id or 0)
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    row = timetable_repository.get_group_lesson_session(
        conn, group_id, lesson_session_id
    )
    if not row:
        raise ValueError("Lesson session was not found.")
    return row


def _lesson_session_for_payload(conn, enrollment, payload):
    lesson_session_id = int(payload.get("lesson_session_id") or payload.get("lesson_id") or 0)
    if lesson_session_id > 0:
        return _get_v2_lesson_session_by_id(conn, enrollment["group_id"], lesson_session_id)
    return _get_v2_lesson_session(conn, enrollment["group_id"], payload.get("lesson_label", ""))


def _parse_optional_lesson_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    parsed = canonical.parse_date(text)
    if not parsed:
        raise ValueError("Lesson date must be a valid date.")
    return parsed


def _normalize_lesson_status(value):
    status = str(value or "").strip().casefold()
    if status in {"", "scheduled", "completed", "cancelled", "canceled"}:
        return "cancelled" if status == "canceled" else status
    raise ValueError("Unsupported lesson status.")


def _parse_optional_lesson_time(value):
    """Normalize an HH:MM string; empty string clears the time (returns None)."""
    text = str(value or "").strip()
    if not text:
        return None
    if not _LESSON_TIME_RE.match(text):
        raise ValueError("Lesson time must be in HH:MM format.")
    return text.zfill(5)
