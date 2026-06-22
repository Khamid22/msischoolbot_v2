import math
from datetime import datetime

from werkzeug.security import generate_password_hash

from shared.academics import canonical
from shared.db import queries
from web.backend.domains.academics.postgres_service import ensure_academic_schema
from web.backend.domains.payments.service import (
    payment_row_to_record,
    summarize_payment_records,
)

PROGRAM_TOTAL_LESSONS = 180


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_text(value):
    return " ".join(str(value or "").strip().casefold().split())


def _subject_display_name(value):
    return canonical.canonical_subject_name(value) or str(value or "").strip()


def _subject_key(value):
    return _normalize_text(_subject_display_name(value))


def _safe_float(value, default=0.0):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_grade_half_up(value):
    return int(math.floor(float(value) + 0.5))


def _date_sort_value(value):
    # Unparseable dates sort first. Canonical date parsing lives in shared.academics.canonical.
    return canonical.date_sort_key(value, on_unparseable=datetime.min)


def _to_academic_indicator(row):
    subject_name = str(row["subject_name"] or "").strip()
    subject_display_name = _subject_display_name(subject_name)
    homework_average = _safe_float(row["homework_average"])
    stored_average = _safe_float(row["average_grade"])
    aap = homework_average if homework_average > 0 else stored_average

    present_count = _safe_int(row["present_count"])
    absent_count = _safe_int(row["absent_count"])
    justified_count = _safe_int(row["justified_count"])
    attendance_total = present_count + absent_count + justified_count
    ar = (
        round(((present_count + justified_count) / attendance_total) * 100)
        if attendance_total > 0
        else 0
    )

    exam_average = _safe_float(row["exam_average"])
    ep = _round_grade_half_up(exam_average) if exam_average > 0 else 0
    completed_lessons = max(0, min(PROGRAM_TOTAL_LESSONS, _safe_int(row["program_completed_lessons"])))
    completion_rate = (
        round((completed_lessons / PROGRAM_TOTAL_LESSONS) * 100)
        if PROGRAM_TOTAL_LESSONS > 0
        else 0
    )

    return {
        "enrollment_id": int(row["enrollment_id"]),
        "subject_name": subject_name,
        "subject_display_name": subject_display_name,
        "subject_key": _subject_key(subject_display_name),
        "subject_short": str(row["subject_short"] or "").strip(),
        "group_name": str(row["group_name"] or "").strip(),
        "aap": max(0.0, min(9.0, round(float(aap), 1))),
        "ar": max(0, min(100, int(ar))),
        "ep": max(0, min(9, int(ep))),
        "total_coins": _safe_int(row["total_coins"]),
        "program_completed_lessons": completed_lessons,
        "program_total_lessons": PROGRAM_TOTAL_LESSONS,
        "program_completion_rate": completion_rate,
        "updated_at": str(row["updated_at"] or "").strip(),
    }


def _to_subject_summary_indicator(row):
    subject_name = str(row["subject_name"] or "").strip()
    subject_display_name = _subject_display_name(subject_name)
    return {
        "enrollment_id": int(row["enrollment_id"]),
        "subject_name": subject_name,
        "subject_display_name": subject_display_name,
        "subject_key": _subject_key(subject_display_name),
        "subject_short": str(row["subject_short"] or "").strip(),
        "group_name": str(row["group_name"] or "").strip(),
        "aap": max(0.0, min(9.0, _safe_float(row["aap"]))),
        "ar": max(0, min(100, _safe_int(row["ar"]))),
        "ep": max(0, min(9, _safe_int(row["ep"]))),
        "total_coins": _safe_int(row["total_coins"]),
        "program_completed_lessons": 0,
        "program_total_lessons": PROGRAM_TOTAL_LESSONS,
        "program_completion_rate": 0,
        "rating_rank": _safe_int(row["rating_rank"]),
        "rating_total": _safe_int(row["rating_total"]),
        "updated_at": str(row["updated_at"] or "").strip(),
    }


def _to_recent_lesson(row):
    subject_name = str(row["subject_name"] or "").strip()
    subject_display_name = _subject_display_name(subject_name)
    return {
        "date": str(row["lesson_date"] or "").strip(),
        "subject_name": subject_name,
        "subject_display_name": subject_display_name,
        "subject_key": _subject_key(subject_display_name),
        "group_name": str(row["group_name"] or "").strip(),
        "lesson_number": str(row["lesson_number"] or "").strip(),
        "topic": str(row["lesson_topic"] or "").strip(),
        "attendance_status": str(row["attendance_status"] or "").strip().casefold(),
        "source": str(row["source"] or "").strip(),
    }


def _lesson_sort_key(row):
    return (
        _date_sort_value(row["lesson_date"]),
        _safe_int(row["lesson_order"]),
        str(row["updated_at"] or ""),
    )


def _list_child_academic_indicators(conn, child_row):
    student_row_id = int(child_row["id"])
    full_name = str(child_row["full_name"] or "").strip()
    try:
        ensure_academic_schema(conn)
        rows = queries.list_parent_subject_indicator_rows(conn, student_row_id, full_name)
    except Exception:
        rows = []

    indicators = [_to_academic_indicator(row) for row in rows]
    if indicators:
        return indicators

    try:
        queries.ensure_subject_summaries_schema(conn)
        summary_rows = queries.list_subject_summary_rows_by_full_name_norm(
            conn,
            _normalize_text(child_row["full_name"]),
        )
    except Exception:
        summary_rows = []

    return [
        _to_subject_summary_indicator(row)
        for row in summary_rows
        if str(row["group_name"] or "").strip().casefold() != "online"
    ]


def _list_child_recent_lessons(conn, child_row):
    student_row_id = int(child_row["id"])
    full_name = str(child_row["full_name"] or "").strip()
    try:
        ensure_academic_schema(conn)
        rows = queries.list_parent_recent_lesson_rows(
            conn,
            student_row_id,
            full_name,
            limit=200,
        )
    except Exception:
        rows = []

    lessons = []
    seen = set()
    subject_counts = {}
    for row in sorted(rows, key=_lesson_sort_key, reverse=True):
        lesson = _to_recent_lesson(row)
        dedupe_key = (
            lesson["date"].casefold(),
            lesson["subject_key"].casefold(),
            lesson["lesson_number"].casefold(),
            lesson["topic"].casefold(),
        )
        if dedupe_key in seen:
            continue
        subject_key = lesson["subject_key"]
        if subject_counts.get(subject_key, 0) >= 3:
            continue
        seen.add(dedupe_key)
        subject_counts[subject_key] = subject_counts.get(subject_key, 0) + 1
        lessons.append(lesson)
        if len(lessons) >= 30:
            break
    return lessons


def _list_child_payment_records(conn, child_row):
    try:
        queries.ensure_student_payments_schema(conn)
        rows = queries.list_student_payment_rows(conn, int(child_row["id"]))
    except Exception:
        return []
    return [payment_row_to_record(row) for row in rows]


def _average_program_completion(indicators):
    rates = []
    completed_values = []
    for indicator in indicators:
        try:
            rate = int(indicator.get("program_completion_rate", 0))
        except (TypeError, ValueError):
            rate = 0
        if rate > 0:
            rates.append(max(0, min(100, rate)))
        try:
            completed = int(indicator.get("program_completed_lessons", 0))
        except (TypeError, ValueError):
            completed = 0
        if completed > 0:
            completed_values.append(max(0, min(PROGRAM_TOTAL_LESSONS, completed)))

    if rates:
        return {
            "program_completion_rate": round(sum(rates) / len(rates)),
            "program_completed_lessons": round(sum(completed_values) / len(completed_values))
            if completed_values
            else 0,
            "program_total_lessons": PROGRAM_TOTAL_LESSONS,
        }
    return {
        "program_completion_rate": 0,
        "program_completed_lessons": 0,
        "program_total_lessons": PROGRAM_TOTAL_LESSONS,
    }


def _build_payment_summary(indicators, payment_records):
    progress = _average_program_completion(indicators)
    return summarize_payment_records(payment_records, progress=progress)


def _to_child(row, conn=None):
    student_row_id = int(row["id"])
    student_code = str(row["student_id"] or "").strip()
    child = {
        "id": student_row_id,
        "student_row_id": student_row_id,
        "studentRowId": student_row_id,
        "full_name": str(row["full_name"] or "").strip(),
        "student_id": student_code,
        "student_code": student_code,
        "studentCode": student_code,
        "password": str(row["password"] or ""),
        "subjects": str(row["subjects"] or "").strip(),
        "telegram_user_id": (
            int(row["telegram_user_id"])
            if row["telegram_user_id"] is not None
            else None
        ),
        "photo_url": str(row["photo_url"] or "").strip(),
        "profile_description": str(row["profile_description"] or "").strip(),
        "class_name": str(row["class_name"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip() or "School 5",
        "last_seen_at": row["last_seen_at"] if row["last_seen_at"] is not None else None,
        "assigned_at": str(row["assigned_at"] or "").strip(),
    }
    if conn is not None:
        child["academic_indicators"] = _list_child_academic_indicators(conn, row)
        child["recent_lessons"] = _list_child_recent_lessons(conn, row)
        payment_records = _list_child_payment_records(conn, row)
    else:
        child["academic_indicators"] = []
        child["recent_lessons"] = []
        payment_records = []
    try:
        child["payment_summary"] = _build_payment_summary(
            child["academic_indicators"],
            payment_records,
        )
    except Exception:
        child["payment_summary"] = summarize_payment_records(
            [],
            progress=_average_program_completion(child["academic_indicators"]),
        )
    return child


def _normalize_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _row_value(row, key):
    try:
        return str(row[key] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _to_parent(row, children=None, complaint_counts=None):
    counts = complaint_counts or {}
    parent_id = int(row["id"])
    bucket = counts.get(parent_id, {})
    display_name = _row_value(row, "display_name")
    login = str(row["login"] or "").strip()
    telegram_username = _row_value(row, "telegram_username")
    return {
        "id": parent_id,
        "login": login,
        "role": str(row["role"] or "").strip(),
        "display_name": display_name,
        "displayName": display_name,
        "display": display_name or login,
        "phone": _row_value(row, "phone"),
        "email": _row_value(row, "email"),
        "telegram_username": telegram_username,
        "telegramUsername": telegram_username,
        "notes": _row_value(row, "notes"),
        "telegram_user_id": (
            int(row["telegram_user_id"])
            if row["telegram_user_id"] is not None
            else None
        ),
        "created_at": str(row["created_at"] or "").strip(),
        "ticket_count": int(bucket.get("total", 0)),
        "open_ticket_count": int(bucket.get("open", 0)),
        "children": children or [],
    }


def _complaint_counts_map(conn):
    try:
        queries.ensure_parent_complaints_schema(conn)
        rows = queries.count_complaints_by_parent(conn)
    except Exception:
        return {}
    counts = {}
    for row in rows:
        counts[int(row["parent_admin_id"])] = {
            "total": int(row["total"] or 0),
            "open": int(row["open_count"] or 0),
        }
    return counts


def list_parent_accounts():
    with _connect() as conn:
        queries.ensure_admins_schema(conn)
        queries.ensure_parent_children_schema(conn)
        complaint_counts = _complaint_counts_map(conn)
        parent_rows = queries.list_parent_admin_rows(conn)
        parents = []
        for parent_row in parent_rows:
            child_rows = queries.list_parent_child_rows(conn, int(parent_row["id"]))
            parents.append(
                _to_parent(
                    parent_row,
                    [_to_child(row, conn=conn) for row in child_rows],
                    complaint_counts,
                )
            )
    return parents


def create_parent_account(login, password, profile=None):
    login_value = str(login or "").strip()
    password_value = str(password or "")
    if len(login_value) < 3:
        raise ValueError("Parent login must be at least 3 characters.")
    if len(password_value) < 6:
        raise ValueError("Temporary password must be at least 6 characters.")

    profile = profile or {}
    with _connect() as conn:
        queries.ensure_admins_schema(conn)
        existing = queries.get_admin_id_by_login(conn, login_value)
        if existing:
            raise ValueError("This login already exists.")

        parent_id = queries.insert_parent_admin(
            conn,
            login_value,
            generate_password_hash(password_value),
            _utc_now_iso(),
            display_name=str(profile.get("display_name") or "").strip(),
            phone=str(profile.get("phone") or "").strip(),
            email=str(profile.get("email") or "").strip(),
            telegram_username=str(profile.get("telegram_username") or "").strip(),
            notes=str(profile.get("notes") or "").strip(),
        )
        conn.commit()
        row = queries.get_parent_admin_row(conn, parent_id)

    if not row:
        raise ValueError("Unable to create parent account.")
    return _to_parent(row, [])


def update_parent_profile(parent_admin_id, payload):
    parent_id = _normalize_positive_int(parent_admin_id)
    if not parent_id:
        raise ValueError("Parent account is required.")
    payload = payload or {}

    with _connect() as conn:
        queries.ensure_admins_schema(conn)
        queries.ensure_parent_children_schema(conn)
        parent_row = queries.get_parent_admin_row(conn, parent_id)
        if not parent_row:
            raise ValueError("Parent account was not found.")

        queries.update_parent_profile(
            conn,
            parent_id,
            display_name=str(payload.get("display_name") or "").strip(),
            phone=str(payload.get("phone") or "").strip(),
            email=str(payload.get("email") or "").strip(),
            telegram_username=str(payload.get("telegram_username") or "").strip(),
            notes=str(payload.get("notes") or "").strip(),
        )
        conn.commit()
        complaint_counts = _complaint_counts_map(conn)
        updated = queries.get_parent_admin_row(conn, parent_id)
        child_rows = queries.list_parent_child_rows(conn, parent_id)
        children = [_to_child(row, conn=conn) for row in child_rows]

    if not updated:
        raise ValueError("Unable to update parent profile.")
    return _to_parent(updated, children, complaint_counts)


def list_parent_children(parent_admin_id):
    parent_id = _normalize_positive_int(parent_admin_id)
    if not parent_id:
        return []

    with _connect() as conn:
        queries.ensure_parent_children_schema(conn)
        rows = queries.list_parent_child_rows(conn, parent_id)
        children = [_to_child(row, conn=conn) for row in rows]
    return children


def assign_parent_child(parent_admin_id, student_row_id):
    parent_id = _normalize_positive_int(parent_admin_id)
    student_id = _normalize_positive_int(student_row_id)
    if not parent_id:
        raise ValueError("Parent account is required.")
    if not student_id:
        raise ValueError("Student is required.")

    with _connect() as conn:
        queries.ensure_admins_schema(conn)
        queries.ensure_parent_children_schema(conn)
        parent_row = queries.get_parent_admin_row(conn, parent_id)
        if not parent_row:
            raise ValueError("Parent account was not found.")
        student_row = queries.get_student_admin_row(conn, student_id)
        if not student_row:
            raise ValueError("Student was not found.")

        queries.insert_parent_child_row(conn, parent_id, student_id, _utc_now_iso())
        conn.commit()
        rows = queries.list_parent_child_rows(conn, parent_id)

        for row in rows:
            if int(row["id"]) == student_id:
                return _to_child(row, conn=conn)
    raise ValueError("Unable to assign this student.")


def remove_parent_child(parent_admin_id, student_row_id):
    parent_id = _normalize_positive_int(parent_admin_id)
    student_id = _normalize_positive_int(student_row_id)
    if not parent_id:
        raise ValueError("Parent account is required.")
    if not student_id:
        raise ValueError("Student is required.")

    with _connect() as conn:
        queries.ensure_admins_schema(conn)
        queries.ensure_parent_children_schema(conn)
        parent_row = queries.get_parent_admin_row(conn, parent_id)
        if not parent_row:
            raise ValueError("Parent account was not found.")
        removed = queries.delete_parent_child_row(conn, parent_id, student_id)
        conn.commit()
    return removed > 0


__all__ = [
    "assign_parent_child",
    "create_parent_account",
    "list_parent_accounts",
    "list_parent_children",
    "remove_parent_child",
    "update_parent_profile",
]
