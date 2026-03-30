import json
import os
import time
from datetime import datetime, timezone

from app.storage import queries

from .google_sheets_sync import (
    JOB_TYPE_GOOGLE_SHEETS_SYNC,
    build_google_sheets_sync_payload,
    parse_google_sheets_sync_payload,
)


def is_async_webhook_sync_enabled():
    raw_value = str(os.environ.get("ASYNC_WEBHOOK_SYNC_ENABLED", "1") or "").strip()
    return raw_value.casefold() in {"1", "true", "yes", "on"}


def _epoch_to_iso(value):
    try:
        parsed = float(value or 0.0)
    except (TypeError, ValueError):
        parsed = 0.0
    if parsed <= 0:
        return ""
    return datetime.fromtimestamp(parsed, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_json_parse(raw_value):
    try:
        parsed = json.loads(str(raw_value or "{}"))
    except (TypeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _serialize_job_row(row):
    if not row:
        return {}

    payload = _safe_json_parse(row["payload_json"])
    if str(row["job_type"] or "").strip() == JOB_TYPE_GOOGLE_SHEETS_SYNC:
        payload = parse_google_sheets_sync_payload(row["payload_json"])

    return {
        "id": int(row["id"]),
        "job_type": str(row["job_type"] or "").strip(),
        "job_key": str(row["job_key"] or "").strip(),
        "status": str(row["status"] or "").strip(),
        "payload": payload,
        "result": _safe_json_parse(row["result_json"]),
        "error": str(row["error_text"] or "").strip(),
        "attempts": int(row["attempts"] or 0),
        "max_attempts": int(row["max_attempts"] or 0),
        "created_at": _epoch_to_iso(row["created_at"]),
        "updated_at": _epoch_to_iso(row["updated_at"]),
        "started_at": _epoch_to_iso(row["started_at"]),
        "finished_at": _epoch_to_iso(row["finished_at"]),
    }


def enqueue_google_sheets_sync_job(target_school_codes):
    payload = build_google_sheets_sync_payload(target_school_codes)
    schools = payload.get("schools", [])
    dedupe_key = ",".join(sorted(str(code).strip() for code in schools if str(code).strip()))
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    now = time.time()

    with queries.connect_auth_db() as conn:
        queries.create_tables(conn)
        existing = queries.find_active_background_job(
            conn,
            JOB_TYPE_GOOGLE_SHEETS_SYNC,
            dedupe_key,
        )
        if existing:
            conn.commit()
            return int(existing["id"]), False

        job_id = queries.insert_background_job(
            conn,
            job_type=JOB_TYPE_GOOGLE_SHEETS_SYNC,
            job_key=dedupe_key,
            payload_json=payload_json,
            max_attempts=3,
            created_at=now,
        )
        conn.commit()
        return job_id, True


def get_background_job_status(job_id):
    with queries.connect_auth_db() as conn:
        queries.create_tables(conn)
        row = queries.get_background_job(conn, job_id)
    if not row:
        return None
    return _serialize_job_row(row)


__all__ = [
    "is_async_webhook_sync_enabled",
    "enqueue_google_sheets_sync_job",
    "get_background_job_status",
]
