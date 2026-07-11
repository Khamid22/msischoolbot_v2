import json
from datetime import datetime, timezone

from backend.core.database import connect_auth_db


VALID_CANDIDATE_STATUSES = {
    "new",
    "interview",
    "math_test",
    "training_ready",
    "training_passed",
    "hired",
    "rejected",
    "withdrawn",
}


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_detail(value):
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_status(value):
    normalized = str(value or "").strip().lower()
    if normalized in VALID_CANDIDATE_STATUSES:
        return normalized
    return "new"


def _row_to_candidate(row):
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"] or ""),
        "phone": str(row["phone"] or ""),
        "telegram_username": str(row["telegram_username"] or ""),
        "email": str(row.get("email") or ""),
        "subject": str(row["subject"] or ""),
        "source": str(row["source"] or ""),
        "status": str(row["status"] or "new"),
        "notes": str(row["notes"] or ""),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
        "events": [],
    }


def _row_to_event(row):
    raw_score = row["score"]
    return {
        "id": int(row["id"]),
        "candidate_id": int(row["candidate_id"]),
        "event_type": str(row["event_type"] or ""),
        "result": str(row["result"] or ""),
        "score": float(raw_score) if raw_score is not None else None,
        "notes": str(row["notes"] or ""),
        "created_by": str(row["created_by"] or ""),
        "created_at": str(row["created_at"] or ""),
        "detail": _parse_detail(row["detail_json"]),
    }


def _subject_id_for_label(conn, subject):
    raw = str(subject or "").strip()
    if not raw:
        return None
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.subjects
        WHERE lower(subject_name) = lower(%s)
           OR lower(subject_short) = lower(%s)
           OR lower(subject_key) = lower(%s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (raw, raw, raw),
    ).fetchone()
    return int(row["id"]) if row else None


def list_teacher_candidates():
    with connect_auth_db() as conn:
        candidate_rows = conn.execute(
            """
            SELECT
                c.id,
                c.full_name,
                c.phone,
                c.telegram_username,
                '' AS email,
                COALESCE(s.subject_name, '') AS subject,
                c.source,
                c.status,
                c.notes,
                c.created_at::text AS created_at,
                c.updated_at::text AS updated_at
            FROM msi_v2.teacher_candidates c
            LEFT JOIN msi_v2.subjects s ON s.id = c.subject_id
            ORDER BY c.updated_at DESC, c.id DESC
            """
        ).fetchall()
        event_rows = conn.execute(
            """
            SELECT
                id,
                candidate_id,
                event_type,
                result,
                score,
                notes,
                created_by,
                created_at::text AS created_at,
                detail_json::text AS detail_json
            FROM msi_v2.teacher_candidate_events
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    candidates = [_row_to_candidate(row) for row in candidate_rows]
    by_id = {candidate["id"]: candidate for candidate in candidates}
    for row in event_rows:
        event = _row_to_event(row)
        candidate = by_id.get(event["candidate_id"])
        if candidate is not None:
            candidate["events"].append(event)
    return candidates


def create_teacher_candidate(
    *,
    full_name,
    phone="",
    telegram_username="",
    email="",
    subject="",
    source="",
    notes="",
    created_by="",
):
    normalized_name = str(full_name or "").strip()
    if not normalized_name:
        return False, "Candidate name is required."

    now = _utc_now_iso()
    with connect_auth_db() as conn:
        subject_id = _subject_id_for_label(conn, subject)
        row = conn.execute(
            """
            INSERT INTO msi_v2.teacher_candidates (
                full_name,
                phone,
                telegram_username,
                subject_id,
                source,
                status,
                notes,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 'new', %s, %s::timestamptz, %s::timestamptz)
            RETURNING id
            """,
            (
                normalized_name,
                str(phone or "").strip(),
                str(telegram_username or "").strip(),
                subject_id,
                str(source or "").strip(),
                str(notes or "").strip(),
                now,
                now,
            ),
        ).fetchone()
        candidate_id = int(row["id"])
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_candidate_events (
                candidate_id,
                event_type,
                result,
                notes,
                created_by,
                created_at
            )
            VALUES (%s, 'created', 'created', %s, %s, %s::timestamptz)
            """,
            (
                candidate_id,
                str(notes or "").strip(),
                str(created_by or "").strip(),
                now,
            ),
        )
        conn.commit()

    return True, ""


def _normalize_detail(detail):
    if isinstance(detail, dict):
        try:
            return json.dumps(detail)
        except (TypeError, ValueError):
            return "{}"
    if isinstance(detail, str) and detail.strip():
        # Already-serialized JSON string; keep it if it parses, else drop it.
        return json.dumps(_parse_detail(detail))
    return "{}"


def update_teacher_candidate_status(
    *,
    candidate_id,
    status,
    event_type="stage",
    result="",
    score=None,
    notes="",
    created_by="",
    detail=None,
):
    try:
        parsed_candidate_id = int(candidate_id)
    except (TypeError, ValueError):
        return False, "Candidate not found."
    if parsed_candidate_id <= 0:
        return False, "Candidate not found."

    normalized_status = _normalize_status(status)
    normalized_event_type = str(event_type or "stage").strip() or "stage"
    normalized_result = str(result or normalized_status).strip() or normalized_status
    parsed_score = None
    if score not in (None, ""):
        try:
            parsed_score = float(score)
        except (TypeError, ValueError):
            return False, "Score must be a number."
    detail_json = _normalize_detail(detail)

    now = _utc_now_iso()
    with connect_auth_db() as conn:
        existing = conn.execute(
            "SELECT id FROM msi_v2.teacher_candidates WHERE id = %s",
            (parsed_candidate_id,),
        ).fetchone()
        if not existing:
            return False, "Candidate not found."

        conn.execute(
            """
            UPDATE msi_v2.teacher_candidates
            SET status = %s, updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (normalized_status, now, parsed_candidate_id),
        )
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_candidate_events (
                candidate_id,
                event_type,
                result,
                score,
                notes,
                created_by,
                created_at,
                detail_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz, %s::jsonb)
            """,
            (
                parsed_candidate_id,
                normalized_event_type,
                normalized_result,
                parsed_score,
                str(notes or "").strip(),
                str(created_by or "").strip(),
                now,
                detail_json,
            ),
        )
        conn.commit()

    return True, ""


def get_teacher_candidate(candidate_id):
    try:
        parsed_candidate_id = int(candidate_id)
    except (TypeError, ValueError):
        return None
    if parsed_candidate_id <= 0:
        return None
    with connect_auth_db() as conn:
        row = conn.execute(
            """
            SELECT c.id, c.full_name, c.phone, c.telegram_username, '' AS email,
                   COALESCE(s.subject_name, '') AS subject, c.source, c.status,
                   c.notes, c.created_at::text AS created_at, c.updated_at::text AS updated_at
            FROM msi_v2.teacher_candidates c
            LEFT JOIN msi_v2.subjects s ON s.id = c.subject_id
            WHERE c.id = %s
            """,
            (parsed_candidate_id,),
        ).fetchone()
    if not row:
        return None
    return _row_to_candidate(row)


def get_teacher_candidate_training_summary(candidate_id):
    try:
        parsed_candidate_id = int(candidate_id)
    except (TypeError, ValueError):
        return {"accepted_lessons": 0, "average_score": 7.0}
    if parsed_candidate_id <= 0:
        return {"accepted_lessons": 0, "average_score": 7.0}

    with connect_auth_db() as conn:
        rows = conn.execute(
            """
            SELECT result, score, detail_json
            FROM msi_v2.teacher_candidate_events
            WHERE candidate_id = %s AND event_type = 'training_evaluation'
            """,
            (parsed_candidate_id,),
        ).fetchall()

    accepted_scores = []
    fallback_scores = []
    for row in rows:
        detail = _parse_detail(row["detail_json"])
        outcome = str(detail.get("outcome") or row["result"] or "").strip().lower()
        raw_score = row["score"]
        score = None
        if raw_score is not None:
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = None
        if score is not None:
            fallback_scores.append(score)
        if outcome != "redo":
            if score is not None:
                accepted_scores.append(score)

    scores = accepted_scores or fallback_scores
    average_score = round(sum(scores) / len(scores), 1) if scores else 7.0
    return {
        "accepted_lessons": len(accepted_scores),
        "average_score": average_score,
    }


def _coerce_event_ids(candidate_id, event_id):
    try:
        parsed_candidate_id = int(candidate_id)
        parsed_event_id = int(event_id)
    except (TypeError, ValueError):
        return None, None
    if parsed_candidate_id <= 0 or parsed_event_id <= 0:
        return None, None
    return parsed_candidate_id, parsed_event_id


def update_candidate_event(
    *,
    candidate_id,
    event_id,
    result="",
    score=None,
    notes="",
    detail=None,
):
    """Edit an existing training-evaluation event. Other event types are immutable."""
    parsed_candidate_id, parsed_event_id = _coerce_event_ids(candidate_id, event_id)
    if parsed_candidate_id is None:
        return False, "Evaluation not found."

    parsed_score = None
    if score not in (None, ""):
        try:
            parsed_score = float(score)
        except (TypeError, ValueError):
            return False, "Score must be a number."
    detail_json = _normalize_detail(detail)
    now = _utc_now_iso()

    with connect_auth_db() as conn:
        existing = conn.execute(
            """
            SELECT id, event_type FROM msi_v2.teacher_candidate_events
            WHERE id = %s AND candidate_id = %s
            """,
            (parsed_event_id, parsed_candidate_id),
        ).fetchone()
        if not existing:
            return False, "Evaluation not found."
        if str(existing["event_type"]) != "training_evaluation":
            return False, "Only training evaluations can be edited."

        conn.execute(
            """
            UPDATE msi_v2.teacher_candidate_events
            SET result = %s, score = %s, notes = %s, detail_json = %s::jsonb
            WHERE id = %s AND candidate_id = %s
            """,
            (
                str(result or "").strip(),
                parsed_score,
                str(notes or "").strip(),
                detail_json,
                parsed_event_id,
                parsed_candidate_id,
            ),
        )
        conn.execute(
            "UPDATE msi_v2.teacher_candidates SET updated_at = %s::timestamptz WHERE id = %s",
            (now, parsed_candidate_id),
        )
        conn.commit()

    return True, ""


def delete_candidate_event(*, candidate_id, event_id):
    """Hard-delete a training-evaluation event. Other event types are immutable."""
    parsed_candidate_id, parsed_event_id = _coerce_event_ids(candidate_id, event_id)
    if parsed_candidate_id is None:
        return False, "Evaluation not found."

    now = _utc_now_iso()
    with connect_auth_db() as conn:
        existing = conn.execute(
            """
            SELECT id, event_type FROM msi_v2.teacher_candidate_events
            WHERE id = %s AND candidate_id = %s
            """,
            (parsed_event_id, parsed_candidate_id),
        ).fetchone()
        if not existing:
            return False, "Evaluation not found."
        if str(existing["event_type"]) != "training_evaluation":
            return False, "Only training evaluations can be deleted."

        conn.execute(
            "DELETE FROM msi_v2.teacher_candidate_events WHERE id = %s AND candidate_id = %s",
            (parsed_event_id, parsed_candidate_id),
        )
        conn.execute(
            "UPDATE msi_v2.teacher_candidates SET updated_at = %s::timestamptz WHERE id = %s",
            (now, parsed_candidate_id),
        )
        conn.commit()

    return True, ""
