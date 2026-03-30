"""Background job queue SQL helpers."""


def find_active_background_job(conn, job_type, job_key):
    normalized_job_type = str(job_type or "").strip()
    normalized_job_key = str(job_key or "").strip()
    if not normalized_job_type:
        return None

    return conn.execute(
        """
        SELECT
            id,
            job_type,
            job_key,
            status,
            payload_json,
            result_json,
            error_text,
            attempts,
            max_attempts,
            created_at,
            updated_at,
            started_at,
            finished_at
        FROM background_jobs
        WHERE job_type = ?
          AND job_key = ?
          AND status IN ('pending', 'running')
        ORDER BY id DESC
        LIMIT 1
        """,
        (normalized_job_type, normalized_job_key),
    ).fetchone()


def insert_background_job(
    conn,
    *,
    job_type,
    job_key="",
    payload_json="{}",
    max_attempts=3,
    created_at=0.0,
):
    normalized_job_type = str(job_type or "").strip()
    if not normalized_job_type:
        return 0

    safe_job_key = str(job_key or "").strip()
    safe_payload_json = str(payload_json or "{}")
    safe_max_attempts = max(int(max_attempts or 0), 1)
    now = float(created_at or 0.0)
    if now <= 0:
        now = 0.0

    cursor = conn.execute(
        """
        INSERT INTO background_jobs (
            job_type,
            job_key,
            status,
            payload_json,
            result_json,
            error_text,
            attempts,
            max_attempts,
            created_at,
            updated_at,
            started_at,
            finished_at
        )
        VALUES (?, ?, 'pending', ?, '{}', '', 0, ?, ?, ?, 0, 0)
        """,
        (
            normalized_job_type,
            safe_job_key,
            safe_payload_json,
            safe_max_attempts,
            now,
            now,
        ),
    )
    return int(cursor.lastrowid or 0)


def get_background_job(conn, job_id):
    try:
        normalized_job_id = int(job_id)
    except (TypeError, ValueError):
        return None

    if normalized_job_id <= 0:
        return None

    return conn.execute(
        """
        SELECT
            id,
            job_type,
            job_key,
            status,
            payload_json,
            result_json,
            error_text,
            attempts,
            max_attempts,
            created_at,
            updated_at,
            started_at,
            finished_at
        FROM background_jobs
        WHERE id = ?
        """,
        (normalized_job_id,),
    ).fetchone()


def claim_next_background_job(conn, claimed_at):
    now = float(claimed_at or 0.0)
    candidate = conn.execute(
        """
        SELECT id
        FROM background_jobs
        WHERE status = 'pending'
        ORDER BY created_at ASC, id ASC
        LIMIT 1
        """
    ).fetchone()
    if not candidate:
        return None

    job_id = int(candidate["id"])
    updated_cursor = conn.execute(
        """
        UPDATE background_jobs
        SET
            status = 'running',
            attempts = attempts + 1,
            updated_at = ?,
            started_at = CASE WHEN started_at <= 0 THEN ? ELSE started_at END
        WHERE id = ?
          AND status = 'pending'
        """,
        (now, now, job_id),
    )
    if int(updated_cursor.rowcount or 0) != 1:
        return None

    return get_background_job(conn, job_id)


def reset_stale_running_jobs(conn, *, stale_before, now):
    stale_limit = float(stale_before or 0.0)
    safe_now = float(now or 0.0)

    # Requeue stale running jobs that still have retries left.
    conn.execute(
        """
        UPDATE background_jobs
        SET
            status = 'pending',
            updated_at = ?,
            started_at = 0
        WHERE status = 'running'
          AND started_at > 0
          AND started_at <= ?
          AND attempts < max_attempts
        """,
        (safe_now, stale_limit),
    )

    # Mark stale running jobs as failed when retries are exhausted.
    conn.execute(
        """
        UPDATE background_jobs
        SET
            status = 'failed',
            error_text = CASE
                WHEN trim(error_text) = '' THEN 'Background worker timeout.'
                ELSE error_text
            END,
            updated_at = ?,
            finished_at = ?
        WHERE status = 'running'
          AND started_at > 0
          AND started_at <= ?
          AND attempts >= max_attempts
        """,
        (safe_now, safe_now, stale_limit),
    )


def mark_background_job_succeeded(conn, *, job_id, result_json, finished_at):
    safe_result_json = str(result_json or "{}")
    now = float(finished_at or 0.0)
    conn.execute(
        """
        UPDATE background_jobs
        SET
            status = 'succeeded',
            result_json = ?,
            error_text = '',
            updated_at = ?,
            finished_at = ?
        WHERE id = ?
        """,
        (safe_result_json, now, now, int(job_id)),
    )


def mark_background_job_failed(conn, *, job_id, error_text, failed_at):
    row = get_background_job(conn, job_id)
    if not row:
        return

    attempts = int(row["attempts"] or 0)
    max_attempts = max(int(row["max_attempts"] or 0), 1)
    retry_allowed = attempts < max_attempts

    safe_error_text = str(error_text or "").strip() or "Background job failed."
    now = float(failed_at or 0.0)
    if retry_allowed:
        conn.execute(
            """
            UPDATE background_jobs
            SET
                status = 'pending',
                error_text = ?,
                updated_at = ?,
                started_at = 0
            WHERE id = ?
            """,
            (safe_error_text, now, int(job_id)),
        )
        return

    conn.execute(
        """
        UPDATE background_jobs
        SET
            status = 'failed',
            error_text = ?,
            updated_at = ?,
            finished_at = ?
        WHERE id = ?
        """,
        (safe_error_text, now, now, int(job_id)),
    )


__all__ = [
    "find_active_background_job",
    "insert_background_job",
    "get_background_job",
    "claim_next_background_job",
    "reset_stale_running_jobs",
    "mark_background_job_succeeded",
    "mark_background_job_failed",
]
