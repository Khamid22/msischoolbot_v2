"""Parent CLIENT (Telegram/invite) account service.

Parents are customers linked to students via the invite flow (no web password
login, no admin records). All reads/writes target msi_v2.parents /
msi_v2.parent_student_links. Child academic indicators come from the msi_v2
gradebook tables.
"""

import math
from datetime import datetime

from database.academics import canonical
from database import queries
from backend.domains.payments.service import (
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
        rows = queries.list_parent_subject_indicator_rows(conn, student_row_id, full_name)
    except Exception:
        rows = []
    return [_to_academic_indicator(row) for row in rows]


def _list_child_recent_lessons(conn, child_row):
    student_row_id = int(child_row["id"])
    full_name = str(child_row["full_name"] or "").strip()
    try:
        rows = queries.list_parent_recent_lesson_rows(conn, student_row_id, full_name, limit=200)
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
        queries.ensure_payments_schema(conn)
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


def _to_invite_child(row, conn=None):
    student_row_id = _normalize_positive_int(_row_value(row, "student_row_id"))
    if not student_row_id:
        return None
    child = {
        "id": student_row_id,
        "student_row_id": student_row_id,
        "studentRowId": student_row_id,
        "full_name": _row_value(row, "student_full_name"),
        "student_id": _row_value(row, "student_id"),
        "student_code": _row_value(row, "student_id"),
        "studentCode": _row_value(row, "student_id"),
        "password": _row_value(row, "password"),
        "subjects": _row_value(row, "subjects"),
        "telegram_user_id": (
            int(row["student_telegram_user_id"])
            if row["student_telegram_user_id"] is not None
            else None
        ),
        "photo_url": _row_value(row, "photo_url"),
        "profile_description": _row_value(row, "profile_description"),
        "class_name": _row_value(row, "class_name"),
        "school_name": _row_value(row, "school_name") or "School 5",
        "last_seen_at": row["last_seen_at"] if row["last_seen_at"] is not None else None,
        "assigned_at": _row_value(row, "linked_at"),
    }
    if conn is not None:
        child["academic_indicators"] = _list_child_academic_indicators(conn, {
            "id": student_row_id,
            "full_name": child["full_name"],
        })
        child["recent_lessons"] = _list_child_recent_lessons(conn, {
            "id": student_row_id,
            "full_name": child["full_name"],
        })
        payment_records = _list_child_payment_records(conn, {"id": student_row_id})
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


def _to_invite_parent(parent_id, rows, conn=None):
    first = rows[0]
    full_name = _row_value(first, "full_name")
    phone = _row_value(first, "phone")
    telegram_username = _row_value(first, "telegram_username")
    children = []
    seen_student_row_ids = set()
    for row in rows:
        child = _to_invite_child(row, conn=conn)
        if not child:
            continue
        student_row_id = int(child["student_row_id"])
        if student_row_id in seen_student_row_ids:
            continue
        seen_student_row_ids.add(student_row_id)
        children.append(child)

    display_name = full_name or phone or telegram_username or f"Parent {parent_id}"
    login = (
        phone
        or (f"@{telegram_username}" if telegram_username else "")
        or f"parent-{parent_id}"
    )
    return {
        "id": -int(parent_id),
        "parent_id": int(parent_id),
        "parentId": int(parent_id),
        "source": "invite",
        "sourceLabel": "Registered",
        "login": login,
        "role": "parent",
        "display_name": display_name,
        "displayName": display_name,
        "display": display_name,
        "phone": phone,
        "email": "",
        "telegram_username": telegram_username,
        "telegramUsername": telegram_username,
        "notes": "",
        "telegram_user_id": (
            int(first["telegram_user_id"])
            if first["telegram_user_id"] is not None
            else None
        ),
        "created_at": _row_value(first, "created_at"),
        "ticket_count": 0,
        "open_ticket_count": 0,
        "disabled": False,
        "status": "active",
        "children": children,
    }


def _list_invite_parent_accounts(conn):
    try:
        rows = queries.list_invite_parent_rows(conn)
    except Exception:
        return []

    grouped = {}
    for row in rows or []:
        parent_id = _normalize_positive_int(_row_value(row, "parent_id"))
        if not parent_id:
            continue
        grouped.setdefault(parent_id, []).append(row)

    return [
        _to_invite_parent(parent_id, parent_rows, conn=conn)
        for parent_id, parent_rows in sorted(
            grouped.items(),
            key=lambda item: (
                _row_value(item[1][0], "full_name").casefold(),
                item[0],
            ),
        )
    ]


def list_parent_accounts():
    with _connect() as conn:
        return _list_invite_parent_accounts(conn)


def list_linked_parents_for_student(student_row_id):
    """Parent CLIENT accounts linked to a student via the invite-link flow."""
    student_id = _normalize_positive_int(student_row_id)
    if not student_id:
        return []

    with _connect() as conn:
        rows = queries.get_parents_for_student(conn, student_id)

    parents = []
    for row in rows or []:
        parents.append(
            {
                "id": int(row["id"]),
                "fullName": str(row["full_name"] or "").strip(),
                "phone": str(row["phone"] or "").strip(),
                "telegramUsername": str(row["telegram_username"] or "").strip(),
                "linkedAt": str(row["linked_at"] or "").strip(),
            }
        )
    return parents


def list_parent_children(parent_id):
    parent_id = _normalize_positive_int(parent_id)
    if not parent_id:
        return []
    with _connect() as conn:
        rows = queries.list_parent_client_child_rows(conn, parent_id)
        return [child for child in (_to_invite_child(row, conn=conn) for row in rows) if child]


def assign_parent_child(parent_id, student_row_id):
    parent_id = _normalize_positive_int(parent_id)
    student_id = _normalize_positive_int(student_row_id)
    if not parent_id:
        raise ValueError("Parent account is required.")
    if not student_id:
        raise ValueError("Student is required.")

    with _connect() as conn:
        parent = conn.execute(
            "SELECT id FROM msi_v2.parents WHERE id = %s", (parent_id,)
        ).fetchone()
        if not parent:
            raise ValueError("Parent account was not found.")
        student = conn.execute(
            "SELECT id FROM msi_v2.students WHERE legacy_student_row_id = %s", (student_id,)
        ).fetchone()
        if not student:
            raise ValueError("Student was not found.")
        conn.execute(
            """
            INSERT INTO msi_v2.parent_student_links (parent_id, student_id, relationship, status)
            VALUES (%s, %s, 'parent', 'active')
            ON CONFLICT (parent_id, student_id) DO UPDATE SET status = 'active'
            """,
            (parent_id, int(student["id"])),
        )
        conn.commit()
        rows = queries.list_parent_client_child_rows(conn, parent_id)
        for row in rows:
            if int(row["student_row_id"]) == student_id:
                return _to_invite_child(row, conn=conn)
    raise ValueError("Unable to assign this student.")


def remove_parent_child(parent_id, student_row_id):
    parent_id = _normalize_positive_int(parent_id)
    student_id = _normalize_positive_int(student_row_id)
    if not parent_id:
        raise ValueError("Parent account is required.")
    if not student_id:
        raise ValueError("Student is required.")

    with _connect() as conn:
        deleted = conn.execute(
            """
            DELETE FROM msi_v2.parent_student_links l
            USING msi_v2.students st
            WHERE l.student_id = st.id
              AND l.parent_id = %s
              AND st.legacy_student_row_id = %s
            """,
            (parent_id, student_id),
        )
        conn.commit()
    return int(deleted.rowcount or 0) > 0


__all__ = [
    "assign_parent_child",
    "list_linked_parents_for_student",
    "list_parent_accounts",
    "list_parent_children",
    "remove_parent_child",
]
