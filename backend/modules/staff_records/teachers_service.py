"""Teacher application service.

This module owns teacher profile/account helper behavior.
"""

import re

from backend.core.passwords import generate_password_hash
from backend.modules.accounts.service import provision_teacher_account
from backend.modules.staff_records import teachers_repository as repository
from backend.modules.accounts.database import DB_LOCK, connect, utc_now_iso
from backend.modules.accounts.bootstrap import init_storage


def backfill_teacher_auth(conn):
    """Provision teacher_auth (login + default password) for any teacher missing it.

    Auto-provisioning, like students: the login is subject-aware
    (``matht001``, ``engt001``, ``biot001``...) and the default password equals
    the login (admins can reset). Idempotent — safe to call on every
    teacher-list load and right after a teacher is created.
    """
    missing = repository.list_teacher_ids_without_auth(conn)
    if not missing:
        return
    now = utc_now_iso()
    for row in missing:
        teacher_id = int(row["id"])
        login = repository.get_next_teacher_code(conn)
        repository.insert_teacher_auth(
            conn, teacher_id, login, login, generate_password_hash(login), now
        )
        auth = repository.get_teacher_auth_row_by_id(conn, teacher_id)
        staff_id = int(row_get(auth, "staff_id") or 0)
        if not staff_id:
            staff = repository.get_teacher_login_row(conn, login)
            staff_id = int(row_get(staff, "staff_id") or 0)
        if staff_id:
            provision_teacher_account(
                conn,
                teacher_id=teacher_id,
                staff_id=staff_id,
                full_name=row_get(row, "full_name") or login,
                canonical_login=login,
            )

TEACHER_CATEGORIES = {"junior", "trained", "experienced_igcse"}
TEACHER_SEMESTER_STAGES = {"1-2", "3-4", "5-6"}


def subject_teacher_login_prefix(subject_name):
    """Return the short subject prefix used for teacher logins."""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(subject_name or "").strip().lower())
    compact = normalized.replace(" ", "")
    if "math" in compact:
        return "math"
    if "english" in compact or compact in {"eng", "esl", "efl"}:
        return "eng"
    if "biology" in compact or compact.startswith("bio"):
        return "bio"
    if "physics" in compact or compact.startswith("phys"):
        return "phys"
    if "chemistry" in compact or compact.startswith("chem"):
        return "chem"
    letters = re.sub(r"[^a-z0-9]+", "", compact)
    return (letters[:6] or "tch").lower()


def normalize_teacher_category(value):
    normalized = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in {"experienced", "igcse", "experienced_teacher"}:
        normalized = "experienced_igcse"
    if normalized in TEACHER_CATEGORIES:
        return normalized
    return "junior"


def normalize_teacher_semester_stage(value):
    normalized = str(value or "").strip().replace("–", "-").replace("—", "-")
    if normalized in TEACHER_SEMESTER_STAGES:
        return normalized
    return "1-2"


def coerce_teacher_performance_score(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 7.0
    return min(10.0, max(0.0, parsed))


def coerce_supervised_lessons(value):
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = 0
    return max(0, parsed)


def row_get(row, key, default=None):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def teacher_payload(row):
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "pay_rate": float(row["pay_rate"] or 0),
        "assigned_group": str(row["assigned_group"]),
        "category": normalize_teacher_category(row_get(row, "category")),
        "semester_stage": normalize_teacher_semester_stage(
            row_get(row, "semester_stage")
        ),
        "performance_score": coerce_teacher_performance_score(
            row_get(row, "performance_score")
        ),
        "supervised_lessons": coerce_supervised_lessons(
            row_get(row, "supervised_lessons")
        ),
        "igcse_evidence": str(row_get(row, "igcse_evidence") or ""),
        "promotion_notes": str(row_get(row, "promotion_notes") or ""),
        "login": str(row_get(row, "login") or ""),
    }


def list_teachers():
    init_storage()
    with DB_LOCK:
        with connect() as conn:
            # Ensure every teacher has login credentials before listing them.
            backfill_teacher_auth(conn)
            conn.commit()
            rows = repository.list_teachers_rows(conn)
    return [teacher_payload(row) for row in rows]


def get_teacher_by_id(teacher_id):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        row = repository.get_teacher_by_id_row(conn, teacher_id)
    if not row:
        return None
    return teacher_payload(row)


def list_active_group_ids_for_teacher_group(group_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return []
    with connect() as conn:
        rows = repository.list_active_group_ids_by_name(conn, normalized_group)
    return [int(row["id"]) for row in rows]


def upsert_teacher(
    full_name,
    pay_rate,
    assigned_group,
    category="junior",
    semester_stage="1-2",
    performance_score=7,
    supervised_lessons=0,
    igcse_evidence="",
    promotion_notes="",
):
    normalized_name = str(full_name or "").strip()
    normalized_group = str(assigned_group or "").strip()
    if not normalized_name or not normalized_group:
        return False

    try:
        safe_pay_rate = float(pay_rate)
    except (TypeError, ValueError):
        return False

    if safe_pay_rate < 0:
        safe_pay_rate = 0
    init_storage()
    now = utc_now_iso()
    with DB_LOCK:
        with connect() as conn:
            repository.insert_teacher_row(
                conn,
                normalized_name,
                safe_pay_rate,
                normalized_group,
                normalize_teacher_category(category),
                normalize_teacher_semester_stage(semester_stage),
                coerce_teacher_performance_score(performance_score),
                coerce_supervised_lessons(supervised_lessons),
                str(igcse_evidence or "").strip(),
                str(promotion_notes or "").strip(),
                now,
                now,
            )
            new_teacher = repository.get_teacher_by_full_name_row(conn, normalized_name)
            if new_teacher:
                repository.set_teacher_group_assignment(conn, int(new_teacher["id"]), normalized_group)
            # Auto-provision login credentials for the newly created teacher.
            backfill_teacher_auth(conn)
            conn.commit()
    return True


def update_teacher_by_id(
    teacher_id,
    full_name,
    pay_rate,
    assigned_group,
    category="junior",
    semester_stage="1-2",
    performance_score=7,
    supervised_lessons=0,
    igcse_evidence="",
    promotion_notes="",
):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return False, "Teacher not found."

    normalized_name = str(full_name or "").strip()
    normalized_group = str(assigned_group or "").strip()
    if not normalized_name or not normalized_group:
        return False, "Teacher full name and group are required."

    try:
        safe_pay_rate = float(pay_rate)
    except (TypeError, ValueError):
        return False, "Pay rate must be a number."
    if safe_pay_rate < 0:
        safe_pay_rate = 0

    init_storage()
    now = utc_now_iso()
    with DB_LOCK:
        with connect() as conn:
            existing = repository.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False, "Teacher not found."

            group_owner = repository.get_teacher_by_group_row(conn, normalized_group)
            if group_owner and int(group_owner["id"]) != teacher_id:
                return False, "Selected group is already assigned to another teacher."

            repository.update_teacher_row_by_id(
                conn,
                teacher_id,
                normalized_name,
                safe_pay_rate,
                normalized_group,
                normalize_teacher_category(category),
                normalize_teacher_semester_stage(semester_stage),
                coerce_teacher_performance_score(performance_score),
                coerce_supervised_lessons(supervised_lessons),
                str(igcse_evidence or "").strip(),
                str(promotion_notes or "").strip(),
                now,
            )
            conn.commit()
    return True, ""


def delete_teacher_by_id(teacher_id):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return False

    init_storage()
    with DB_LOCK:
        with connect() as conn:
            existing = repository.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False
            repository.delete_teacher_row_by_id(conn, teacher_id)
            conn.commit()
    return True


def get_teacher_name_by_group(group_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return ""

    init_storage()
    with connect() as conn:
        row = repository.get_teacher_by_group_row(conn, normalized_group)
    if not row:
        return ""
    return str(row["full_name"]).strip()


def assign_teacher_to_group(group_name, teacher_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return False

    normalized_teacher = str(teacher_name or "").strip()
    init_storage()
    now = utc_now_iso()

    with DB_LOCK:
        with connect() as conn:
            if not normalized_teacher:
                repository.delete_teacher_by_group(conn, normalized_group)
                conn.commit()
                return True

            existing_teacher = repository.get_teacher_by_full_name_row(
                conn,
                normalized_teacher,
            )
            repository.insert_teacher_row(
                conn,
                normalized_teacher,
                float(existing_teacher["pay_rate"]) if existing_teacher else 0.0,
                normalized_group,
                normalize_teacher_category(row_get(existing_teacher, "category"))
                if existing_teacher
                else "junior",
                normalize_teacher_semester_stage(row_get(existing_teacher, "semester_stage"))
                if existing_teacher
                else "1-2",
                coerce_teacher_performance_score(row_get(existing_teacher, "performance_score"))
                if existing_teacher
                else 7,
                coerce_supervised_lessons(row_get(existing_teacher, "supervised_lessons"))
                if existing_teacher
                else 0,
                str(row_get(existing_teacher, "igcse_evidence") or "")
                if existing_teacher
                else "",
                str(row_get(existing_teacher, "promotion_notes") or "")
                if existing_teacher
                else "",
                now,
                now,
            )
            # Auto-provision login credentials for the newly created teacher.
            backfill_teacher_auth(conn)
            conn.commit()
    return True


__all__ = [
    "TEACHER_CATEGORIES",
    "TEACHER_SEMESTER_STAGES",
    "assign_teacher_to_group",
    "delete_teacher_by_id",
    "get_teacher_by_id",
    "get_teacher_name_by_group",
    "list_teachers",
    "subject_teacher_login_prefix",
    "update_teacher_by_id",
    "upsert_teacher",
]


def list_subject_options_for_teacher(teacher_id):
    """Subject options for the teacher workspace selects."""
    with connect() as conn:
        rows = repository.list_subject_options_for_teacher_rows(conn, teacher_id)
    return [dict(row) for row in rows]
