from datetime import datetime

from shared.db import queries


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
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _complaint_from_row(row):
    return {
        "id": int(row["id"]),
        "parent_admin_id": int(row["parent_admin_id"]),
        "student_row_id": int(row["student_row_id"] or 0),
        "category": str(row["category"] or "other").strip(),
        "topic": str(row["topic"] or "").strip(),
        "message": str(row["message"] or "").strip(),
        "status": _normalize_status(row["status"]),
        "reply": str(row["reply"] or "").strip(),
        "created_at": str(row["created_at"] or "").strip(),
        "updated_at": str(row["updated_at"] or "").strip(),
        "resolved_at": str(row["resolved_at"] or "").strip(),
        "parent_login": str(row["parent_login"] or "").strip(),
        "student_name": str(row["student_name"] or "").strip(),
        "student_code": str(row["student_code"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip(),
    }


def list_complaints(parent_admin_id=0):
    with _connect() as conn:
        queries.ensure_parent_complaints_schema(conn)
        rows = queries.list_parent_complaint_rows(conn, int(parent_admin_id or 0))
    return [_complaint_from_row(row) for row in rows]


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

    with _connect() as conn:
        queries.ensure_admins_schema(conn)
        queries.ensure_parent_children_schema(conn)
        queries.ensure_parent_complaints_schema(conn)
        parent_row = queries.get_parent_admin_row(conn, parent_id)
        if not parent_row:
            raise ValueError("Parent account was not found.")
        if student_id > 0:
            link = queries.get_parent_child_row(conn, parent_id, student_id)
            if not link:
                raise ValueError("This child is not linked to the selected parent.")

        inserted = queries.insert_parent_complaint_row(
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
        row = queries.get_parent_complaint_row(conn, int(inserted["id"]))

    if not row:
        raise ValueError("Unable to create complaint.")
    return _complaint_from_row(row)


def update_complaint(complaint_id, payload):
    complaint_id = int(complaint_id or 0)
    if complaint_id <= 0:
        raise ValueError("Complaint is required.")

    requested_status = _normalize_status(payload.get("status"))
    reply = str(payload.get("reply") or "").strip()
    now = _utc_now_iso()
    resolved_at = now if requested_status == "resolved" else ""

    with _connect() as conn:
        queries.ensure_parent_complaints_schema(conn)
        row = queries.get_parent_complaint_row(conn, complaint_id)
        if not row:
            return None
        existing_reply = str(row["reply"] or "").strip()
        queries.update_parent_complaint_row(
            conn,
            complaint_id,
            status=requested_status,
            reply=reply or existing_reply,
            updated_at=now,
            resolved_at=resolved_at,
        )
        conn.commit()
        updated = queries.get_parent_complaint_row(conn, complaint_id)

    return _complaint_from_row(updated) if updated else None


__all__ = [
    "create_complaint",
    "list_complaints",
    "update_complaint",
]
