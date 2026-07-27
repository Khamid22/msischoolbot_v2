"""PostgreSQL persistence for durable outbox jobs."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.unit_of_work import Connection
from backend.modules.jobs.schemas import EnqueueJobCommand, JobRecord


def _job_record(row: Any) -> JobRecord:
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return JobRecord.model_validate(
        {
            "job_id": row["id"],
            "topic": row["topic"],
            "payload": payload or {},
            "idempotency_key": row["idempotency_key"],
            "status": row["status"],
            "attempts": row["attempts"],
            "max_attempts": row["max_attempts"],
            "available_at": row["available_at"],
            "lease_owner": row.get("lease_owner") or "",
            "lease_expires_at": row.get("lease_expires_at"),
            "created_at": row["created_at"],
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
            "last_error": row.get("last_error") or "",
        }
    )


def insert_job(conn: Connection, command: EnqueueJobCommand) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.outbox_jobs (
            topic, payload, idempotency_key, status, attempts, max_attempts,
            available_at, created_at, updated_at
        )
        VALUES (%s, %s::jsonb, %s, 'pending', 0, %s, COALESCE(%s, now()), now(), now())
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
        """,
        (
            command.topic,
            json.dumps(command.payload, separators=(",", ":"), sort_keys=True),
            command.idempotency_key,
            command.max_attempts,
            command.available_at,
        ),
    ).fetchone()
    if row:
        return int(row["id"])
    existing = conn.execute(
        "SELECT id FROM msi_v2.outbox_jobs WHERE idempotency_key = %s",
        (command.idempotency_key,),
    ).fetchone()
    return int(existing["id"]) if existing else 0


def claim_due_jobs(
    conn: Connection,
    *,
    worker_id: str,
    limit: int,
    lease_seconds: int,
) -> list[JobRecord]:
    rows = conn.execute(
        """
        WITH claimable AS (
            SELECT id
            FROM msi_v2.outbox_jobs
            WHERE status IN ('pending', 'retry')
              AND available_at <= now()
              AND (lease_expires_at IS NULL OR lease_expires_at <= now())
            ORDER BY available_at ASC, id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT %s
        )
        UPDATE msi_v2.outbox_jobs AS job
        SET status = 'running',
            attempts = job.attempts + 1,
            lease_owner = %s,
            lease_expires_at = now() + make_interval(secs => %s),
            started_at = COALESCE(job.started_at, now()),
            updated_at = now()
        FROM claimable
        WHERE job.id = claimable.id
        RETURNING job.*
        """,
        (int(limit), worker_id, int(lease_seconds)),
    ).fetchall()
    return [_job_record(row) for row in rows]


def complete_job(conn: Connection, *, job_id: int, worker_id: str) -> bool:
    result = conn.execute(
        """
        UPDATE msi_v2.outbox_jobs
        SET status = 'completed',
            lease_owner = NULL,
            lease_expires_at = NULL,
            completed_at = now(),
            last_error = NULL,
            updated_at = now()
        WHERE id = %s AND status = 'running' AND lease_owner = %s
        """,
        (int(job_id), worker_id),
    )
    return int(getattr(result, "rowcount", 0) or 0) > 0


def record_job_failure(
    conn: Connection,
    *,
    job_id: int,
    worker_id: str,
    next_available_at: datetime,
    error_summary: str,
    is_dead: bool,
) -> bool:
    result = conn.execute(
        """
        UPDATE msi_v2.outbox_jobs
        SET status = %s,
            available_at = %s,
            lease_owner = NULL,
            lease_expires_at = NULL,
            completed_at = CASE WHEN %s THEN now() ELSE NULL END,
            last_error = %s,
            updated_at = now()
        WHERE id = %s AND status = 'running' AND lease_owner = %s
        """,
        (
            "dead" if is_dead else "retry",
            next_available_at,
            bool(is_dead),
            error_summary,
            int(job_id),
            worker_id,
        ),
    )
    return int(getattr(result, "rowcount", 0) or 0) > 0


def release_expired_leases(conn: Connection) -> int:
    result = conn.execute(
        """
        UPDATE msi_v2.outbox_jobs
        SET status = CASE
                WHEN attempts >= max_attempts THEN 'dead'
                ELSE 'retry'
            END,
            lease_owner = NULL,
            lease_expires_at = NULL,
            available_at = now(),
            completed_at = CASE
                WHEN attempts >= max_attempts THEN now()
                ELSE completed_at
            END,
            last_error = COALESCE(last_error, 'Worker lease expired.'),
            updated_at = now()
        WHERE status = 'running' AND lease_expires_at <= now()
        """
    )
    return int(getattr(result, "rowcount", 0) or 0)


def replay_dead_job(conn: Connection, *, job_id: int) -> bool:
    result = conn.execute(
        """
        UPDATE msi_v2.outbox_jobs
        SET status = 'retry',
            attempts = 0,
            available_at = now(),
            lease_owner = NULL,
            lease_expires_at = NULL,
            started_at = NULL,
            completed_at = NULL,
            last_error = NULL,
            updated_at = now()
        WHERE id = %s AND status = 'dead'
        """,
        (int(job_id),),
    )
    return int(getattr(result, "rowcount", 0) or 0) > 0


def find_job(conn: Connection, job_id: int) -> JobRecord | None:
    row = conn.execute(
        "SELECT * FROM msi_v2.outbox_jobs WHERE id = %s",
        (int(job_id),),
    ).fetchone()
    return _job_record(row) if row else None


__all__ = [
    "claim_due_jobs",
    "complete_job",
    "find_job",
    "insert_job",
    "record_job_failure",
    "replay_dead_job",
    "release_expired_leases",
]
