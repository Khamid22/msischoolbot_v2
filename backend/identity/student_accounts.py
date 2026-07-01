import logging
import os
import threading
import time

from database.academics import canonical
from database import queries
from backend.identity.common import (
    DB_LOCK as _DB_LOCK,
    connect as _connect,
    utc_now_iso as _utc_now_iso,
)
from backend.identity.storage import init_storage

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


def record_student_activity(student_row_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return {
            "updated": False,
            "skipped": False,
            "reason": "invalid_student_id",
            "last_seen_at": "",
        }
    now_monotonic = time.monotonic()
    if not _begin_student_activity_write(student_row_id, now_monotonic):
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
            rowcount = queries.update_student_last_seen(conn, student_row_id, now)
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
            "Failed to record student activity for student_row_id=%s",
            student_row_id,
        )
        result["reason"] = "activity_write_failed"
        return result
    finally:
        _finish_student_activity_write(
            student_row_id,
            now_monotonic,
            updated,
        )


def list_students_for_admin(school_filter = canonical.ADMIN_SCHOOL_FILTER_ALL):
    init_storage()
    normalized_filter = canonical.normalize_admin_school_filter(school_filter)
    school_key = (
        normalized_filter
        if normalized_filter != canonical.ADMIN_SCHOOL_FILTER_ALL
        else ""
    )
    with _connect() as conn:
        rows = queries.list_students_for_admin_rows(conn, school_key=school_key)
        online_only_rows = conn.execute(
            """
            SELECT DISTINCT st.full_name, s.school_name AS school_name
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE gs.enrollment_status = 'active'
              AND lower(g.group_name) = 'online'
              AND NOT EXISTS (
                SELECT 1
                FROM msi_v2.group_students other_gs
                JOIN msi_v2.groups other_g ON other_g.id = other_gs.group_id
                JOIN msi_v2.students other_st ON other_st.id = other_gs.student_id
                WHERE other_g.school_id = g.school_id
                  AND lower(trim(other_st.full_name)) = lower(trim(st.full_name))
                  AND other_gs.enrollment_status = 'active'
                  AND lower(other_g.group_name) <> 'online'
              )
            """
        ).fetchall()

    online_only_student_keys = {
        f"{str(row['school_name'] or canonical.DEFAULT_SCHOOL_NAME).strip() or canonical.DEFAULT_SCHOOL_NAME}|{canonical.normalize_text(row['full_name'])}"
        for row in online_only_rows
    }

    grouped = {}
    for row in rows:
        full_name = str(row["full_name"]).strip()
        student_school_name = (
            str(row["school_name"] if row["school_name"] is not None else "").strip()
            or canonical.DEFAULT_SCHOOL_NAME
        )
        key = f"{student_school_name}|{canonical.normalize_text(full_name)}"
        if key in online_only_student_keys:
            continue
        item = grouped.get(key)

        row_subjects = canonical.split_subjects(row["subjects"])
        row_last_seen_at = row["last_seen_at"] if row["last_seen_at"] is not None else None
        if item is None:
            grouped[key] = {
                "id": int(row["id"]),
                "full_name": full_name,
                "student_id": str(row["student_id"]),
                "password": str(row["password"]),
                "subjects_set": set(row_subjects),
                "school_name": student_school_name,
                "telegram_user_id": (
                    int(row["telegram_user_id"])
                    if row["telegram_user_id"] is not None
                    else None
                ),
                "last_seen_at": row_last_seen_at,
            }
            continue

        item["subjects_set"].update(row_subjects)
        if row_last_seen_at and (
            not item.get("last_seen_at")
            or str(row_last_seen_at) > str(item.get("last_seen_at"))
        ):
            item["last_seen_at"] = row_last_seen_at

    results = []
    grouped_items = sorted(
        grouped.values(),
        key=lambda item: (
            str(item.get("school_name", "")).casefold(),
            int(item.get("id", 0)),
            canonical.normalize_text(item.get("full_name", "")),
        ),
    )
    for index, item in enumerate(grouped_items, start=1):
        subjects_sorted = sorted(item["subjects_set"], key=canonical.subject_sort_key)
        results.append(
            {
                "display_id": index,
                "id": int(item["id"]),
                "student_row_id": int(item["id"]),
                "studentRowId": int(item["id"]),
                "full_name": str(item["full_name"]),
                "student_id": str(item["student_id"]),
                "student_code": str(item["student_id"]),
                "studentCode": str(item["student_id"]),
                "password": str(item["password"]),
                "subjects": ", ".join(subjects_sorted),
                "school_name": str(item.get("school_name", "")).strip() or canonical.DEFAULT_SCHOOL_NAME,
                "telegram_user_id": item["telegram_user_id"],
                "last_seen_at": item.get("last_seen_at"),
            }
        )
    return results


def update_student_admin_profile(
    student_row_id,
    photo_url,
    profile_description,
    class_name,
    school_name,
    teacher_name,
):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            existing = queries.get_student_admin_row(conn, student_row_id)
            if not existing:
                return False

            queries.update_student_admin_profile(
                conn,
                student_row_id,
                str(photo_url or "").strip(),
                str(profile_description or "").strip(),
                str(class_name or "").strip(),
                str(school_name or "").strip(),
                str(teacher_name or "").strip(),
            )
            conn.commit()
    return True
