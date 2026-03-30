import json
import logging
import os
import time

from app.storage import queries

from .google_sheets_sync import JOB_TYPE_GOOGLE_SHEETS_SYNC, run_google_sheets_sync


def _env_positive_float(name, default):
    raw_value = str(os.environ.get(name, str(default)) or "").strip()
    try:
        parsed = float(raw_value)
    except ValueError:
        logging.warning("Invalid %s=%r, using %s", name, raw_value, default)
        return float(default)
    return max(parsed, 0.1)


def _worker_idle_sleep_seconds():
    return _env_positive_float("BACKGROUND_WORKER_IDLE_SECONDS", 1.0)


def _worker_stale_seconds():
    return _env_positive_float("BACKGROUND_WORKER_STALE_SECONDS", 900.0)


def _safe_json_parse(raw_value):
    try:
        parsed = json.loads(str(raw_value or "{}"))
    except (TypeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _claim_next_job():
    now = time.time()
    stale_before = now - _worker_stale_seconds()

    with queries.connect_auth_db() as conn:
        queries.create_tables(conn)
        queries.reset_stale_running_jobs(
            conn,
            stale_before=stale_before,
            now=now,
        )
        row = queries.claim_next_background_job(conn, claimed_at=now)
        conn.commit()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "job_type": str(row["job_type"] or "").strip(),
            "payload_json": str(row["payload_json"] or "{}"),
        }


def _mark_job_success(job_id, result):
    now = time.time()
    result_json = json.dumps(
        result if isinstance(result, dict) else {},
        separators=(",", ":"),
        ensure_ascii=True,
    )
    with queries.connect_auth_db() as conn:
        queries.mark_background_job_succeeded(
            conn,
            job_id=int(job_id),
            result_json=result_json,
            finished_at=now,
        )
        conn.commit()


def _mark_job_failed(job_id, error_text):
    now = time.time()
    with queries.connect_auth_db() as conn:
        queries.mark_background_job_failed(
            conn,
            job_id=int(job_id),
            error_text=str(error_text or "").strip(),
            failed_at=now,
        )
        conn.commit()


def _process_job(job):
    job_type = str(job.get("job_type", "")).strip()
    payload = _safe_json_parse(job.get("payload_json", "{}"))

    if job_type == JOB_TYPE_GOOGLE_SHEETS_SYNC:
        return run_google_sheets_sync(payload.get("schools"))

    raise RuntimeError(f"Unsupported background job type: {job_type or '<empty>'}")


def run_background_worker():
    logging.info("Background worker started")
    idle_sleep = _worker_idle_sleep_seconds()

    while True:
        job = _claim_next_job()
        if not job:
            time.sleep(idle_sleep)
            continue

        job_id = int(job["id"])
        try:
            result = _process_job(job)
            _mark_job_success(job_id, result)
        except Exception as exc:
            logging.exception("Background job %s failed: %s", job_id, exc)
            _mark_job_failed(job_id, str(exc))


__all__ = ["run_background_worker"]
