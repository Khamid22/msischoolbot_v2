from datetime import datetime, timezone

from backend.core.database import connect_auth_db
from backend.modules.complaints import repository
from backend.modules.parent_access.service import parent_account_exists, parent_can_access_student


VALID_COMPLAINT_STATUSES = {"new", "in_progress", "escalated", "resolved"}
VALID_COMPLAINT_CATEGORIES = {
    "complaint",
    "direct_contact",
    "payment",
    "teacher",
    "lesson_quality",
    "schedule",
    "attendance",
    "technical",
    "account",
    "other",
}


def _connect():
    return connect_auth_db()


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_status(value):
    normalized = str(value or "").strip().casefold()
    aliases = {
        "progress": "in_progress",
        "open": "in_progress",
        "done": "resolved",
        "closed": "resolved",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in VALID_COMPLAINT_STATUSES else "new"


def _normalize_category(value):
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    return normalized if normalized in VALID_COMPLAINT_CATEGORIES else "other"


def _row_value(row, key):
    try:
        return str(row[key] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _message_from_row(row):
    return {
        "id": int(row["id"]),
        "author_role": str(row["author_role"] or "system").strip(),
        "author_login": str(row["author_login"] or "").strip(),
        "body": str(row["body"] or "").strip(),
        "created_at": str(row["created_at"] or "").strip(),
    }


def _complaint_base(row):
    parent_login = str(row["parent_login"] or "").strip()
    parent_display_name = _row_value(row, "parent_display_name")
    parent_id = int(row["parent_admin_id"] or 0)
    return {
        "id": int(row["id"]),
        "parent_admin_id": parent_id,
        "parent_id": parent_id,
        "student_row_id": int(row["student_row_id"] or 0),
        "category": str(row["category"] or "other").strip(),
        "topic": str(row["topic"] or "").strip(),
        "message": str(row["message"] or "").strip(),
        "status": _normalize_status(row["status"]),
        "reply": str(row["reply"] or "").strip(),
        "assigned_to": _row_value(row, "assigned_to"),
        "created_at": str(row["created_at"] or "").strip(),
        "updated_at": str(row["updated_at"] or "").strip(),
        "resolved_at": str(row["resolved_at"] or "").strip(),
        "parent_login": parent_login,
        "parent_display_name": parent_display_name,
        "parent_display": parent_display_name or parent_login,
        "parent_phone": _row_value(row, "parent_phone"),
        "parent_email": _row_value(row, "parent_email"),
        "parent_telegram_username": _row_value(row, "parent_telegram_username"),
        "student_name": str(row["student_name"] or "").strip(),
        "student_code": str(row["student_code"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip(),
    }


def _build_thread(conn, base):
    """Build the full conversation stored in ``msi_v2.ticket_messages``."""
    message_rows = [_message_from_row(r) for r in repository.list_complaint_message_rows(conn, base["id"])]
    if message_rows:
        staff_rows = [m for m in message_rows if m["author_role"] != "parent"]
        latest = staff_rows[-1] if staff_rows else message_rows[-1]
        return {
            "messages": message_rows,
            "reply_count": len(staff_rows),
            "latest_reply": latest["body"] if latest else "",
            "latest_reply_at": latest["created_at"] if latest else "",
        }

    messages = []
    if base["message"]:
        messages.append(
            {
                "id": 0,
                "author_role": "parent",
                "author_login": base["parent_login"],
                "body": base["message"],
                "created_at": base["created_at"],
            }
        )
    if base["reply"]:
        messages.append(
            {
                "id": 0,
                "author_role": "admin",
                "author_login": base["assigned_to"],
                "body": base["reply"],
                "created_at": base["updated_at"],
            }
        )

    staff_rows = [m for m in messages if m["author_role"] != "parent"]
    latest = staff_rows[-1] if staff_rows else None
    return {
        "messages": messages,
        "reply_count": len(staff_rows),
        "latest_reply": latest["body"] if latest else "",
        "latest_reply_at": latest["created_at"] if latest else "",
    }


def _complaint_payload(conn, row):
    base = _complaint_base(row)
    base.update(_build_thread(conn, base))
    return base


def list_complaints(parent_admin_id=0):
    with _connect() as conn:
        rows = repository.list_parent_complaint_rows(conn, int(parent_admin_id or 0))
        return [_complaint_payload(conn, row) for row in rows]


def get_complaint(complaint_id):
    complaint_id = int(complaint_id or 0)
    if complaint_id <= 0:
        return None
    with _connect() as conn:
        row = repository.get_parent_complaint_row(conn, complaint_id)
        if not row:
            return None
        return _complaint_payload(conn, row)


def create_complaint(parent_admin_id, student_row_id, payload):
    parent_id = int(parent_admin_id or 0)
    student_id = int(student_row_id or 0)
    if parent_id <= 0:
        raise ValueError("Parent account is required.")

    message = str(payload.get("message") or "").strip()
    if len(message) < 5:
        raise ValueError("Complaint message is too short.")

    category = _normalize_category(payload.get("category"))
    topic = str(payload.get("topic") or "").strip()
    if len(topic) < 2:
        raise ValueError("Topic is required.")
    now = _utc_now_iso()

    if not parent_account_exists(parent_id):
        raise ValueError("Parent account was not found.")
    if student_id > 0 and not parent_can_access_student(parent_id, student_id):
        raise ValueError("This child is not linked to the selected parent.")

    with _connect() as conn:
        inserted = repository.insert_parent_complaint_row(
            conn,
            parent_admin_id=parent_id,
            student_row_id=student_id if student_id > 0 else None,
            category=category,
            topic=topic,
            message=message,
            status="new",
            created_at=now,
            updated_at=now,
        )
        conn.commit()
        row = repository.get_parent_complaint_row(conn, int(inserted["id"]))
        if not row:
            raise ValueError("Unable to create complaint.")
        return _complaint_payload(conn, row)


def update_complaint(complaint_id, payload):
    """Status / assignment update (Escalate, Resolve, Reopen, assign)."""
    complaint_id = int(complaint_id or 0)
    if complaint_id <= 0:
        raise ValueError("Complaint is required.")

    now = _utc_now_iso()
    with _connect() as conn:
        row = repository.get_parent_complaint_row(conn, complaint_id)
        if not row:
            return None

        # Only override the status when one was explicitly supplied; otherwise keep it.
        if str(payload.get("status") or "").strip():
            requested_status = _normalize_status(payload.get("status"))
        else:
            requested_status = _normalize_status(row["status"])

        reply = str(payload.get("reply") or "").strip()
        existing_reply = str(row["reply"] or "").strip()
        if "assigned_to" in (payload or {}):
            assigned_to = str(payload.get("assigned_to") or "").strip()
        else:
            assigned_to = _row_value(row, "assigned_to")
        resolved_at = now if requested_status == "resolved" else ""

        repository.update_parent_complaint_row(
            conn,
            complaint_id,
            status=requested_status,
            reply=reply or existing_reply,
            updated_at=now,
            resolved_at=resolved_at,
            assigned_to=assigned_to,
        )
        conn.commit()
        updated = repository.get_parent_complaint_row(conn, complaint_id)
        return _complaint_payload(conn, updated) if updated else None


def add_complaint_reply(complaint_id, payload, *, author_role="admin", author_login=""):
    """Append a reply to the ticket thread and advance its status."""
    complaint_id = int(complaint_id or 0)
    if complaint_id <= 0:
        raise ValueError("Complaint is required.")

    body = str(payload.get("body") or payload.get("reply") or "").strip()
    if len(body) < 1:
        raise ValueError("Reply message is required.")

    now = _utc_now_iso()
    with _connect() as conn:
        row = repository.get_parent_complaint_row(conn, complaint_id)
        if not row:
            return None

        current_status = _normalize_status(row["status"])
        # An explicit status update wins; otherwise a reply moves a new/in_progress
        # ticket to in_progress but never reopens a resolved/escalated one.
        if str(payload.get("status") or "").strip():
            next_status = _normalize_status(payload.get("status"))
        elif current_status in {"resolved", "escalated"}:
            next_status = current_status
        else:
            next_status = "in_progress"

        resolved_at = now if next_status == "resolved" else ""
        assigned_to = (
            str(payload.get("assigned_to") or "").strip()
            or _row_value(row, "assigned_to")
            or str(author_login or "").strip()
        )

        repository.insert_complaint_message_row(
            conn,
            complaint_id=complaint_id,
            author_role=author_role,
            author_login=author_login,
            body=body,
            created_at=now,
        )
        repository.update_parent_complaint_row(
            conn,
            complaint_id,
            status=next_status,
            reply=body,
            updated_at=now,
            resolved_at=resolved_at,
            assigned_to=assigned_to,
        )
        conn.commit()
        updated = repository.get_parent_complaint_row(conn, complaint_id)
        return _complaint_payload(conn, updated) if updated else None


__all__ = [
    "add_complaint_reply",
    "create_complaint",
    "get_complaint",
    "list_complaints",
    "update_complaint",
]
