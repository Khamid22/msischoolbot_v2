"""Parent CLIENT (Telegram/invite) account service.

Parents are customers linked to students via the invite flow (no web password
login, no admin records). All reads/writes target msi_v2.parents /
msi_v2.parent_student_links. Child academic indicators come from the msi_v2
gradebook tables.
"""

import hashlib
import math
import secrets
from datetime import UTC, datetime, timedelta

from backend.core.database import connect_auth_db
from backend.modules.payments.service import (
    list_student_payments,
    payment_summary_for_student,
    summarize_payment_records,
)
from backend.modules.parents import repository as parent_repository
from backend.modules.identity.accounts import (
    claim_parent_telegram_identity,
    load_account_auth_result,
    provision_parent_account,
)
from backend.modules.students.service import resolve_public_dashboard_for_student_row
from backend.modules.academics import canonical

def _connect():
    return connect_auth_db()


def _utc_now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_at(days=14):
    return (datetime.now(UTC) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_unique_violation(exc):
    return (
        getattr(exc, "sqlstate", "") == "23505"
        or exc.__class__.__name__ == "UniqueViolation"
    )


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
    program_total_lessons = max(0, _safe_int(row["program_total_lessons"]))
    raw_completed_lessons = max(0, _safe_int(row["program_completed_lessons"]))
    completed_lessons = (
        min(program_total_lessons, raw_completed_lessons)
        if program_total_lessons > 0
        else raw_completed_lessons
    )
    completion_rate = (
        round((completed_lessons / program_total_lessons) * 100)
        if program_total_lessons > 0
        else 0
    )

    return {
        "enrollment_id": _safe_int(row["enrollment_id"]),
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
        "program_total_lessons": program_total_lessons,
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
        rows = parent_repository.list_parent_subject_indicator_rows(conn, student_row_id, full_name)
    except Exception:
        rows = []
    return [_to_academic_indicator(row) for row in rows]


def _list_child_recent_lessons(conn, child_row):
    student_row_id = int(child_row["id"])
    full_name = str(child_row["full_name"] or "").strip()
    try:
        rows = parent_repository.list_parent_recent_lesson_rows(conn, student_row_id, full_name, limit=200)
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


def _list_child_payment_records(_conn, child_row):
    try:
        return list_student_payments(int(child_row["id"]))
    except Exception:
        return []


def parent_account_exists(parent_id):
    parsed_parent_id = _normalize_positive_int(parent_id)
    if not parsed_parent_id:
        return False
    with _connect() as conn:
        return bool(parent_repository.get_parent_exists_row(conn, parsed_parent_id))


def _average_program_completion(indicators):
    completed_total = 0
    lesson_total = 0
    for indicator in indicators:
        try:
            completed = max(0, int(indicator.get("program_completed_lessons", 0)))
        except (TypeError, ValueError):
            completed = 0
        try:
            total = max(0, int(indicator.get("program_total_lessons", 0)))
        except (TypeError, ValueError):
            total = 0
        if total <= 0:
            continue
        completed_total += min(completed, total)
        lesson_total += total

    return {
        "program_completion_rate": (
            round((completed_total / lesson_total) * 100) if lesson_total > 0 else 0
        ),
        "program_completed_lessons": completed_total,
        "program_total_lessons": lesson_total,
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


def link_parent_via_invite(
    student_row_id,
    full_name,
    phone="",
    telegram_username="",
    telegram_user_id=None,
):
    """Create/update a parent CLIENT record and link it to a student."""
    now = _utc_now_iso()
    with _connect() as conn:
        parent = parent_repository.link_parent_from_invite(
            conn,
            student_row_id=int(student_row_id),
            full_name=full_name,
            phone=phone,
            telegram_username=telegram_username,
            telegram_user_id=telegram_user_id,
            now=now,
        )
        if parent:
            identity_kwargs = {
                "parent_id": int(parent["id"]),
                "full_name": str(parent["full_name"] or full_name or "").strip(),
                "phone": str(parent["phone"] or phone or "").strip(),
                "telegram_username": str(
                    parent["telegram_username"] or telegram_username or ""
                ).strip(),
            }
            if telegram_user_id:
                account_id = claim_parent_telegram_identity(
                    conn,
                    telegram_user_id=int(telegram_user_id),
                    **identity_kwargs,
                )
            else:
                account_id = provision_parent_account(
                    conn,
                    telegram_user_id=None,
                    **identity_kwargs,
                )
            if account_id <= 0:
                raise RuntimeError("Unable to provision the parent identity.")
    return dict(parent) if parent else None


def parent_from_telegram_user_id(telegram_user_id):
    parsed = _normalize_positive_int(telegram_user_id)
    if not parsed:
        return None
    with _connect() as conn:
        row = parent_repository.get_parent_by_telegram_id(conn, parsed)
    return dict(row) if row else None


def parent_children(parent_id):
    parsed = _normalize_positive_int(parent_id)
    if not parsed:
        return []
    with _connect() as conn:
        rows = parent_repository.list_parent_client_child_rows(conn, parsed)
    return [dict(row) for row in rows or []]


def _invite_code_hash(code):
    normalized = str(code or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def create_parent_invite_code(student_row_id, issued_by=0, *, expires_days=14):
    student_row_id = int(student_row_id or 0)
    issued_by = int(issued_by or 0) or None
    if student_row_id <= 0:
        raise ValueError("student_row_id is required")

    with _connect() as conn:
        student_db_id = parent_repository.get_student_v2_id_by_legacy_row(conn, student_row_id)
        if student_db_id is None:
            raise ValueError("Selected student was not found.")
        staff_db_id = parent_repository.get_staff_db_id_for_admin_id(conn, issued_by)
        for _ in range(5):
            code = secrets.token_urlsafe(9).rstrip("=")
            try:
                parent_repository.insert_parent_invite_row(
                    conn,
                    token_hash=_invite_code_hash(code),
                    student_db_id=student_db_id,
                    staff_db_id=staff_db_id,
                    created_at=_utc_now_iso(),
                    expires_at=_expires_at(expires_days),
                )
                return code
            except Exception as exc:
                conn.rollback()
                if not _is_unique_violation(exc):
                    raise
        raise RuntimeError("Could not generate a unique parent invite code")


def load_parent_invite_code_payload(code):
    code = str(code or "").strip()
    if not code:
        return None
    with _connect() as conn:
        row = parent_repository.get_pending_parent_invite_payload(
            conn,
            _invite_code_hash(code),
        )
    if not row:
        return None
    return {
        "invite_id": int(row["id"]),
        "student_row_id": int(row["student_row_id"] or 0),
        "canonical_student_id": int(row["canonical_student_id"] or 0),
        "student_code": str(row["student_code"] or "").strip(),
        "student_name": str(row["student_name"] or "").strip(),
        "issued_by": int(row["issued_by"] or 0),
    }


def claim_parent_invite_code(
    code,
    *,
    full_name,
    phone="",
    telegram_username="",
    telegram_user_id=None,
):
    digest = _invite_code_hash(code)
    if not digest:
        return None
    with _connect() as conn:
        invite = parent_repository.get_pending_parent_invite_payload(
            conn,
            digest,
            for_update=True,
        )
        if not invite or int(invite["student_row_id"] or 0) <= 0:
            return None
        parent = parent_repository.link_parent_from_invite(
            conn,
            student_row_id=int(invite["student_row_id"]),
            full_name=full_name,
            phone=phone,
            telegram_username=telegram_username,
            telegram_user_id=telegram_user_id,
            now=_utc_now_iso(),
        )
        if not parent:
            raise RuntimeError("Unable to create the parent account.")

        identity_kwargs = {
            "parent_id": int(parent["id"]),
            "full_name": str(parent["full_name"] or full_name or "").strip(),
            "phone": str(parent["phone"] or phone or "").strip(),
            "telegram_username": str(
                parent["telegram_username"] or telegram_username or ""
            ).strip(),
        }
        if telegram_user_id:
            account_id = claim_parent_telegram_identity(
                conn,
                telegram_user_id=int(telegram_user_id),
                **identity_kwargs,
            )
        else:
            account_id = provision_parent_account(
                conn,
                telegram_user_id=None,
                **identity_kwargs,
            )
        if account_id <= 0:
            raise RuntimeError("Unable to provision the parent identity.")
        auth_result = load_account_auth_result(
            account_id,
            conn=conn,
            record_login=True,
        )
        if not auth_result:
            raise RuntimeError("Unable to initialize the parent account session.")
        consumed = parent_repository.consume_parent_invite(
            conn,
            int(invite["id"]),
            parent_id=int(parent["id"]),
            telegram_user_id=telegram_user_id,
        )
        if not consumed:
            raise RuntimeError("The parent invite was already used.")
        claimed_parent = dict(parent)
        claimed_parent["account_id"] = account_id
        claimed_parent["auth_result"] = auth_result
        return claimed_parent


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
        rows = parent_repository.list_invite_parent_rows(conn)
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
        rows = parent_repository.get_parents_for_student(conn, student_id)

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
        rows = parent_repository.list_parent_client_child_rows(conn, parent_id)
        return [child for child in (_to_invite_child(row, conn=conn) for row in rows) if child]


def assign_parent_child(parent_id, student_row_id):
    parent_id = _normalize_positive_int(parent_id)
    student_id = _normalize_positive_int(student_row_id)
    if not parent_id:
        raise ValueError("Parent account is required.")
    if not student_id:
        raise ValueError("Student is required.")

    with _connect() as conn:
        parent = parent_repository.get_parent_exists_row(conn, parent_id)
        if not parent:
            raise ValueError("Parent account was not found.")
        student_v2_id = parent_repository.get_student_v2_id_by_legacy_row(conn, student_id)
        if student_v2_id is None:
            raise ValueError("Student was not found.")
        parent_repository.insert_parent_student_link(conn, parent_id, student_v2_id)
        conn.commit()
        rows = parent_repository.list_parent_client_child_rows(conn, parent_id)
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
        deleted = parent_repository.delete_parent_student_link(conn, parent_id, student_id)
        conn.commit()
    return int(deleted.rowcount or 0) > 0


def delete_parent_account(parent_id):
    parent_id = _normalize_positive_int(parent_id)
    if not parent_id:
        raise ValueError("Parent account is required.")

    with _connect() as conn:
        parent = parent_repository.get_parent_exists_row(conn, parent_id)
        if not parent:
            raise ValueError("Parent account was not found.")

        link_count = parent_repository.count_parent_child_links(conn, parent_id)
        if _safe_int(link_count["count"] if link_count else 0) > 0:
            raise ValueError("Unlink all students before deleting this parent.")

        ticket_count = parent_repository.count_parent_support_tickets(conn, parent_id)
        if _safe_int(ticket_count["count"] if ticket_count else 0) > 0:
            raise ValueError("Resolve or reassign this parent's tickets before deleting.")

        message_count = parent_repository.count_parent_ticket_messages(conn, parent_id)
        if _safe_int(message_count["count"] if message_count else 0) > 0:
            raise ValueError("This parent has ticket messages and cannot be deleted safely.")

        deleted = parent_repository.delete_parent_row(conn, parent_id)
        conn.commit()

    return int(deleted.rowcount or 0) > 0


def list_parent_client_children(parent_id):
    """Children for a parent CLIENT account, shaped for the parent portal."""
    raw_rows = parent_children(parent_id)
    if not raw_rows:
        return []
    with _connect() as conn:
        return [
            child
            for child in (_to_invite_child(row, conn=conn) for row in raw_rows)
            if child
        ]


def parent_can_access_student(parent_id, student_row_id):
    """True when this parent client is linked to the requested student row."""
    parsed_parent_id = _normalize_positive_int(parent_id)
    parsed_student_row_id = _normalize_positive_int(student_row_id)
    if not parsed_parent_id or not parsed_student_row_id:
        return False
    with _connect() as conn:
        row = parent_repository.get_parent_child_link(conn, parsed_parent_id, parsed_student_row_id)
    return bool(row)


def parent_can_access_dashboard(parent_id, dashboard_student_id):
    """True when this parent client is linked to a dashboard enrollment id."""
    parsed_parent_id = _normalize_positive_int(parent_id)
    parsed_dashboard_student_id = _normalize_positive_int(dashboard_student_id)
    if not parsed_parent_id or not parsed_dashboard_student_id:
        return False
    with _connect() as conn:
        row = parent_repository.get_parent_child_link_by_dashboard_id(
            conn,
            parsed_parent_id,
            parsed_dashboard_student_id,
        )
    return bool(row)


def resolve_parent_child_dashboard(student_row_id):
    """Resolve a linked child row to the default student dashboard route params."""
    return resolve_public_dashboard_for_student_row(student_row_id)


__all__ = [
    "assign_parent_child",
    "claim_parent_invite_code",
    "create_parent_invite_code",
    "delete_parent_account",
    "link_parent_via_invite",
    "list_parent_client_children",
    "list_linked_parents_for_student",
    "list_parent_accounts",
    "list_parent_children",
    "list_student_payments",
    "load_parent_invite_code_payload",
    "parent_can_access_dashboard",
    "parent_can_access_student",
    "parent_account_exists",
    "parent_children",
    "parent_from_telegram_user_id",
    "payment_summary_for_student",
    "remove_parent_child",
    "resolve_parent_child_dashboard",
]
