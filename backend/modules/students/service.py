"""Student domain service facade.

DB-3 owns student profile/account/dashboard helper behavior here. Legacy
identity modules re-export these functions temporarily during migration.
"""

import logging
import os
import threading
import time

from backend.modules.academics import canonical
from backend.modules.identity.accounts import reset_student_password

from backend.modules.students import repository
from backend.modules.teachers.service import get_teacher_name_by_group
from backend.modules.identity.database import (
    DB_LOCK as _DB_LOCK,
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


def list_students_for_admin(school_filter = canonical.ADMIN_SCHOOL_FILTER_ALL):
    init_storage()
    normalized_filter = canonical.normalize_admin_school_filter(school_filter)
    school_key = (
        normalized_filter
        if normalized_filter != canonical.ADMIN_SCHOOL_FILTER_ALL
        else ""
    )
    with _connect() as conn:
        rows = repository.list_students_for_admin_rows(conn, school_key=school_key)
        online_only_rows = repository.list_online_only_student_rows(conn)

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
            existing = repository.get_student_admin_row(conn, student_row_id)
            if not existing:
                return False

            repository.update_student_admin_profile(
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


def split_name(full_name):
    parts = [part for part in str(full_name or "").strip().split() if part]
    if not parts:
        return {"surname": "", "name": ""}
    if len(parts) == 1:
        return {"surname": parts[0], "name": ""}
    return {"surname": parts[0], "name": " ".join(parts[1:])}


def extract_auto_student_context(full_name, student_row_id=None):
    # Resolve the student's active group + classmates. Prefer the student's
    # legacy id (reliable); fall back to a name match for name-only callers.
    context = {"groups": [], "group": "", "classmates": []}
    normalized_full_name = canonical.normalize_text(full_name)
    has_id = isinstance(student_row_id, int) and student_row_id > 0
    if not has_id and not normalized_full_name:
        return context

    try:
        with _connect() as conn:
            enrollment = None
            if has_id:
                enrollment = repository.get_active_enrollment_for_student_row(
                    conn,
                    student_row_id,
                )
            if not enrollment and normalized_full_name:
                for row in repository.list_active_student_enrollments(conn):
                    if canonical.normalize_text(row["full_name"]) == normalized_full_name:
                        enrollment = row
                        break

            if not enrollment:
                return context

            group_name = str(enrollment["group_name"] or "").strip()
            self_student_id = int(enrollment["student_id"])
            classmate_rows = repository.list_classmate_names(
                conn,
                int(enrollment["group_id"]),
                self_student_id,
            )

        classmates = [str(r["full_name"]).strip() for r in classmate_rows if r["full_name"]]
        context["groups"] = [group_name] if group_name else []
        context["group"] = group_name
        context["classmates"] = classmates
    except Exception:
        pass

    return context


def get_admin_student_profile(student_row_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        row = repository.get_student_admin_row(conn, student_row_id)
    if not row:
        return None

    full_name = str(row["full_name"]).strip()
    student_row_id = int(row["id"])
    auto_context = extract_auto_student_context(full_name, student_row_id=student_row_id)
    teacher_name = get_teacher_name_by_group(auto_context.get("group", ""))
    split = split_name(full_name)
    student_code = str(row["student_id"]).strip()

    return {
        "id": student_row_id,
        "student_row_id": student_row_id,
        "studentRowId": student_row_id,
        "full_name": full_name,
        "surname": split["surname"],
        "name": split["name"],
        "student_id": student_code,
        "student_code": student_code,
        "studentCode": student_code,
        "subjects": str(row["subjects"]).strip(),
        "photo_url": str(row["photo_url"] or "").strip(),
        "profile_description": str(row["profile_description"] or "").strip(),
        "class_name": str(row["class_name"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip() or canonical.DEFAULT_SCHOOL_NAME,
        "group": str(auto_context.get("group", "")).strip(),
        "groups": list(auto_context.get("groups", [])),
        "classmates": list(auto_context.get("classmates", [])),
        "teacher_name": teacher_name,
    }


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
            row = repository.get_student_admin_row_by_id(conn, student_db_id)
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
        mapping = repository.get_students_sheet_map_row(
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


def admin_change_student_password(student_row_id, new_password, actor_account_id=None):
    outcome = reset_student_password(
        student_row_id,
        new_password,
        actor_account_id=actor_account_id,
    )
    return outcome.changed, outcome.message


def school_code_from_name(school_name):
    normalized = canonical.normalize_text(school_name)
    if normalized == "sehriyo":
        return "sehriyo"
    if normalized in {"school 5", "school5"}:
        return "school5"
    return ""


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


def resolve_sheet_student_for_admin(student_row_id, get_admin_student_profile, load_dataset=None):
    _ = load_dataset
    student_profile = get_admin_student_profile(student_row_id)
    if not student_profile:
        return None, "Selected student was not found.", 404

    preferred_group = str(student_profile.get("group", "")).strip()
    school_name = str(student_profile.get("school_name", "")).strip()
    resolved = resolve_public_dashboard_for_student_row(
        student_row_id,
        preferred_group=preferred_group,
        school_code=school_code_from_name(school_name),
    )
    if not resolved:
        return None, "No dashboard data found for this student.", 404
    return resolved, "", 200


__all__ = [
    "admin_change_student_password",
    "change_student_password",
    "extract_auto_student_context",
    "get_admin_student_profile",
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "get_student_subject_enrollments",
    "list_enrolled_subject_options",
    "list_students_for_admin",
    "record_student_activity",
    "resolve_public_dashboard_for_student_row",
    "resolve_sheet_student_for_admin",
    "school_code_from_name",
    "split_name",
    "update_student_admin_profile",
]
