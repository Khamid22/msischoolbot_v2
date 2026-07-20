"""Student domain service facade.

DB-3 owns student profile/account/dashboard helper behavior here. Legacy
identity modules re-export these functions temporarily during migration.
"""

import logging
import os
import threading
import time

from backend.modules.organization import canonical

from backend.modules.people.students import repository
from backend.modules.people.teachers.service import get_teacher_name_by_group
from backend.modules.identity.database import (
    connect as _connect,
    utc_now_iso as _utc_now_iso,
)
from backend.modules.identity.bootstrap import init_storage

_STUDENT_ACTIVITY_STATE_LOCK = threading.Lock()
_STUDENT_ACTIVITY_IN_FLIGHT = set()
_STUDENT_ACTIVITY_LAST_FLUSHED = {}
_STUDENT_ACTIVITY_MAX_TRACKED_IDS = 4096
_STUDENT_ACTIVITY_WRITE_INTERVAL_SECONDS = max(
    int(str(os.environ.get("STUDENT_ACTIVITY_WRITE_INTERVAL_SECONDS", "10") or "10")),
    5,
)

def _begin_student_activity_write(student_row_id, now_monotonic):
    with _STUDENT_ACTIVITY_STATE_LOCK:
        if student_row_id in _STUDENT_ACTIVITY_IN_FLIGHT:
            return False
        last_flushed = float(_STUDENT_ACTIVITY_LAST_FLUSHED.get(student_row_id, 0.0))
        if now_monotonic - last_flushed < _STUDENT_ACTIVITY_WRITE_INTERVAL_SECONDS:
            return False
        _STUDENT_ACTIVITY_IN_FLIGHT.add(student_row_id)
    return True


def _finish_student_activity_write(student_row_id, now_monotonic, succeeded):
    with _STUDENT_ACTIVITY_STATE_LOCK:
        _STUDENT_ACTIVITY_IN_FLIGHT.discard(student_row_id)
        if not succeeded:
            return
        _STUDENT_ACTIVITY_LAST_FLUSHED[student_row_id] = now_monotonic
        if len(_STUDENT_ACTIVITY_LAST_FLUSHED) <= _STUDENT_ACTIVITY_MAX_TRACKED_IDS:
            return
        sorted_entries = sorted(
            _STUDENT_ACTIVITY_LAST_FLUSHED.items(),
            key=lambda item: float(item[1]),
        )
        to_prune = len(_STUDENT_ACTIVITY_LAST_FLUSHED) - _STUDENT_ACTIVITY_MAX_TRACKED_IDS
        for stale_student_row_id, _ in sorted_entries[:to_prune]:
            _STUDENT_ACTIVITY_LAST_FLUSHED.pop(stale_student_row_id, None)


def record_student_activity(student_db_id):
    if not isinstance(student_db_id, int) or student_db_id <= 0:
        return {
            "updated": False,
            "skipped": False,
            "reason": "invalid_student_id",
            "last_seen_at": "",
        }
    now_monotonic = time.monotonic()
    if not _begin_student_activity_write(student_db_id, now_monotonic):
        return {
            "updated": False,
            "skipped": True,
            "reason": "throttled",
            "last_seen_at": "",
        }
    updated = False
    now = _utc_now_iso()
    result = {
        "updated": False,
        "skipped": False,
        "reason": "",
        "last_seen_at": now,
    }
    try:
        with _connect() as conn:
            rowcount = repository.update_student_last_seen(conn, student_db_id, now)
            if rowcount <= 0:
                conn.rollback()
                result["reason"] = "student_not_found"
                return result
            conn.commit()
            updated = True
            result["updated"] = True
            return result
    except Exception:
        logging.exception(
            "Failed to record student activity for student_db_id=%s",
            student_db_id,
        )
        result["reason"] = "activity_write_failed"
        return result
    finally:
        _finish_student_activity_write(
            student_db_id,
            now_monotonic,
            updated,
        )












def get_dashboard_student_profile(
    student_db_id,
    full_name,
    group_name,
    subject_name,
    load_dataset=None,
):
    _ = subject_name, load_dataset
    profile = {
        "full_name": str(full_name or "").strip(),
        "photo_url": "",
        "profile_description": "",
        "class_name": "",
        "school_name": canonical.DEFAULT_SCHOOL_NAME,
        "group_name": str(group_name or "").strip(),
        "teacher_name": "",
        "classmates": [],
    }
    row = None

    if isinstance(student_db_id, int) and student_db_id > 0:
        init_storage()
        with _connect() as conn:
            row = repository.get_student_dashboard_row_by_id(conn, student_db_id)
        if row:
            profile["photo_url"] = str(row["photo_url"] or "").strip()
            profile["profile_description"] = str(row["profile_description"] or "").strip()
            profile["class_name"] = str(row["class_name"] or "").strip()
            profile["school_name"] = (
                str(row["school_name"] or "").strip() or canonical.DEFAULT_SCHOOL_NAME
            )

    profile["teacher_name"] = get_teacher_name_by_group(group_name)

    auto_context = extract_auto_student_context(
        full_name,
        student_row_id=(
            int(row["id"])
            if isinstance(student_db_id, int) and student_db_id > 0 and row and row["id"]
            else None
        ),
    )
    if auto_context.get("classmates"):
        profile["classmates"] = auto_context["classmates"]
    return profile


def get_student_db_id_by_enrollment_id(enrollment_id, school_code=None):
    try:
        normalized_enrollment_id = int(enrollment_id)
    except (TypeError, ValueError):
        return None
    if normalized_enrollment_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        mapping = repository.get_student_enrollment_map_row(
            conn,
            normalized_enrollment_id,
            school_key=canonical.normalize_school_code(school_code),
        )
    if not mapping:
        return None
    try:
        return int(mapping["student_db_id"])
    except (TypeError, ValueError, KeyError):
        return None


def get_student_subject_enrollments(public_dashboard_id):
    """All active subject/group enrollments for the student behind a dashboard id."""
    try:
        dashboard_id = int(public_dashboard_id)
    except (TypeError, ValueError):
        return []
    if dashboard_id <= 0:
        return []

    try:
        with _connect() as conn:
            ref = repository.get_student_ref_by_public_dashboard_id(conn, dashboard_id)
            if not ref:
                return []
            rows = repository.list_subject_enrollment_rows_for_student(
                conn,
                int(ref["student_id"]),
                int(ref["school_id"]),
            )
    except Exception:
        return []

    return [
        {
            "student_id": int(row["id"]),
            "subject": str(row["subject"] or "").strip(),
            "group": str(row["grp"] or "").strip(),
        }
        for row in rows
        if row["id"]
    ]


def list_enrolled_subject_options(student_id, school_code="", fallback_subject_name=""):
    subject_name = str(fallback_subject_name or "").strip()
    fallback = [{"id": 0, "name": subject_name}] if subject_name else []
    try:
        dashboard_id = int(student_id)
    except (TypeError, ValueError):
        return fallback
    if dashboard_id <= 0:
        return fallback

    try:
        with _connect() as conn:
            current = repository.get_student_ref_by_public_dashboard_id_and_school(
                conn,
                dashboard_id,
                school_code,
            )
            if not current:
                return fallback
            rows = repository.list_active_subject_options_for_student(
                conn,
                int(current["internal_student_id"]),
            )
    except Exception:
        return fallback

    subjects = [
        {"id": int(row["id"]), "name": str(row["name"] or "").strip()}
        for row in rows
        if row.get("id") and str(row.get("name") or "").strip()
    ]
    return subjects or fallback






def _dashboard_candidate_from_row(row, *, preferred_group="", fallback_school_code=""):
    group_name = str(row["group_name"] or "").strip()
    return {
        "student_id": int(row["public_dashboard_id"]),
        "subject": str(row["subject_name"] or "").strip(),
        "group": group_name,
        "school": str(row["school_key"] or fallback_school_code).strip() or fallback_school_code,
        "group_match": bool(preferred_group and group_name == preferred_group),
    }


def resolve_public_dashboard_for_student_row(student_row_id, *, preferred_group="", school_code=""):
    try:
        parsed_student_row_id = int(student_row_id)
    except (TypeError, ValueError):
        return None
    if parsed_student_row_id <= 0:
        return None

    try:
        with _connect() as conn:
            rows = repository.list_public_dashboard_targets_for_student_row(
                conn,
                parsed_student_row_id,
            )
    except Exception:
        rows = []
    if not rows:
        return None

    candidates = [
        _dashboard_candidate_from_row(
            row,
            preferred_group=str(preferred_group or "").strip(),
            fallback_school_code=str(school_code or "").strip(),
        )
        for row in rows
    ]
    candidates.sort(
        key=lambda item: (
            0 if item.get("group_match") else 1,
            canonical.subject_sort_key(item.get("subject", "")),
            str(item.get("group", "")).casefold(),
            int(item.get("student_id", 0)),
        )
    )
    candidate = dict(candidates[0])
    candidate.pop("group_match", None)
    return candidate




__all__ = [
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "get_student_subject_enrollments",
    "list_enrolled_subject_options",
    "record_student_activity",
    "resolve_public_dashboard_for_student_row",
]
