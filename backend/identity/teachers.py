"""Teacher identity/profile helpers."""

from werkzeug.security import generate_password_hash

from database import queries
from backend.identity.common import DB_LOCK, connect, utc_now_iso
from backend.identity.storage import init_storage


def backfill_teacher_auth(conn):
    """Provision teacher_auth (login + default password) for any teacher missing it.

    Auto-provisioning, like students: the login is ``TCH00N`` and the default
    password equals the login (admins can reset). Idempotent — safe to call on
    every teacher-list load and right after a teacher is created.
    """
    missing = queries.list_teacher_ids_without_auth(conn)
    if not missing:
        return
    now = utc_now_iso()
    for row in missing:
        teacher_id = int(row["id"])
        login = queries.get_next_teacher_code(conn)
        queries.insert_teacher_auth(
            conn, teacher_id, login, login, generate_password_hash(login), now
        )

TEACHER_CATEGORIES = {"junior", "trained", "experienced_igcse"}
TEACHER_SEMESTER_STAGES = {"1-2", "3-4", "5-6"}


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
        "password": str(row_get(row, "password") or ""),
    }


def list_teachers():
    init_storage()
    with DB_LOCK:
        with connect() as conn:
            # Ensure every teacher has login credentials before listing them.
            backfill_teacher_auth(conn)
            conn.commit()
            rows = queries.list_teachers_rows(conn)
    return [teacher_payload(row) for row in rows]


def get_teacher_by_id(teacher_id):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        row = queries.get_teacher_by_id_row(conn, teacher_id)
    if not row:
        return None
    return teacher_payload(row)


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
            queries.insert_teacher_row(
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
            existing = queries.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False, "Teacher not found."

            group_owner = queries.get_teacher_by_group_row(conn, normalized_group)
            if group_owner and int(group_owner["id"]) != teacher_id:
                return False, "Selected group is already assigned to another teacher."

            queries.update_teacher_row_by_id(
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
            existing = queries.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False
            queries.delete_teacher_row_by_id(conn, teacher_id)
            conn.commit()
    return True


def get_teacher_name_by_group(group_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return ""

    init_storage()
    with connect() as conn:
        row = queries.get_teacher_by_group_row(conn, normalized_group)
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
                queries.delete_teacher_by_group(conn, normalized_group)
                conn.commit()
                return True

            existing_teacher = queries.get_teacher_by_full_name_row(
                conn,
                normalized_teacher,
            )
            queries.insert_teacher_row(
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
    "update_teacher_by_id",
    "upsert_teacher",
]
