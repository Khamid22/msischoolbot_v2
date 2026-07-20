"""PostgreSQL persistence for Recruitment appointments."""

from __future__ import annotations

from typing import Any


def _appointment_columns() -> str:
    return """
        appointment.id, appointment.candidate_id, appointment.appointment_type,
        appointment.starts_at::text AS starts_at,
        appointment.ends_at::text AS ends_at,
        appointment.responsible_account_id, appointment.appointment_format,
        appointment.location_or_link, appointment.topic, appointment.note,
        appointment.status, appointment.version, appointment.cancellation_reason,
        appointment.completed_at::text AS completed_at,
        appointment.cancelled_at::text AS cancelled_at,
        appointment.no_show_at::text AS no_show_at,
        appointment.started_at::text AS started_at,
        appointment.started_by_account_id,
        COALESCE(started_by.full_name, started_by.login, '') AS started_by_name,
        appointment.created_at::text AS created_at,
        appointment.updated_at::text AS updated_at,
        candidate.full_name AS candidate_name,
        candidate.status AS candidate_status,
        candidate.subject_id,
        COALESCE(subject.subject_name, '') AS subject,
        COALESCE(responsible.full_name, responsible.login, '') AS responsible_name,
        responsible.role AS responsible_role,
        COALESCE(demo_evaluator.full_name, demo_evaluator.login, '') AS evaluated_by_name
    """


def list_appointment_rows(
    conn: Any,
    *,
    candidate_id: int | None = None,
    visible_account_id: int | None = None,
    visible_subject_ids: set[int] | None = None,
    starts_from: str = "",
    starts_to: str = "",
    appointment_type: str = "",
    status: str = "",
    responsible_account_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Any], int]:
    clauses: list[str] = []
    params: list[Any] = []
    if candidate_id:
        clauses.append("appointment.candidate_id = %s")
        params.append(int(candidate_id))
    else:
        clauses.append("candidate.status <> 'trash_bin'")
    if visible_account_id:
        if visible_subject_ids is not None and not visible_subject_ids:
            clauses.append("FALSE")
        else:
            subject_clause = ""
            if visible_subject_ids is not None:
                subject_clause = "AND visibility.subject_id = ANY(%s::bigint[])"
            clauses.append(
                f"""EXISTS (
                    SELECT 1 FROM msi_v2.teacher_candidate_assignments visibility
                    WHERE visibility.candidate_id = appointment.candidate_id
                      AND visibility.assignee_account_id = %s
                      AND visibility.status = 'active'
                      {subject_clause}
                )"""
            )
            params.append(int(visible_account_id))
            if visible_subject_ids is not None:
                params.append(sorted(visible_subject_ids))
    if starts_from:
        clauses.append("appointment.starts_at >= %s::timestamptz")
        params.append(starts_from)
    if starts_to:
        clauses.append("appointment.starts_at < %s::timestamptz")
        params.append(starts_to)
    if appointment_type:
        clauses.append("appointment.appointment_type = %s")
        params.append(appointment_type)
    if status:
        status_values = [
            item.strip() for item in str(status).split(",") if item.strip()
        ]
        if len(status_values) == 1:
            clauses.append("appointment.status = %s")
            params.append(status_values[0])
        elif status_values:
            clauses.append("appointment.status = ANY(%s::text[])")
            params.append(status_values)
    if responsible_account_id:
        clauses.append("appointment.responsible_account_id = %s")
        params.append(int(responsible_account_id))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    base_sql = f"""
        FROM msi_v2.teacher_candidate_appointments appointment
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
        LEFT JOIN msi_v2.accounts responsible ON responsible.id = appointment.responsible_account_id
        LEFT JOIN msi_v2.accounts started_by ON started_by.id = appointment.started_by_account_id
        LEFT JOIN msi_v2.teacher_candidate_demo_lessons demo_evaluation
          ON demo_evaluation.appointment_id = appointment.id
         AND demo_evaluation.voided_at IS NULL
        LEFT JOIN msi_v2.accounts demo_evaluator
          ON demo_evaluator.id = demo_evaluation.evaluator_account_id
        {where_sql}
    """
    total_row = conn.execute(
        f"SELECT count(*) AS total {base_sql}",
        tuple(params) if params else None,
    ).fetchone()
    rows = conn.execute(
        f"""
        SELECT {_appointment_columns()}
        {base_sql}
        ORDER BY appointment.starts_at ASC, appointment.id ASC
        LIMIT %s OFFSET %s
        """,
        tuple([*params, int(limit), int(offset)]),
    ).fetchall()
    return rows, int(total_row["total"] or 0) if total_row else 0


def get_appointment_row(
    conn: Any,
    *,
    candidate_id: int,
    appointment_id: int,
    for_update: bool = False,
) -> Any:
    suffix = "FOR UPDATE OF appointment" if for_update else ""
    return conn.execute(
        f"""
        SELECT {_appointment_columns()}
        FROM msi_v2.teacher_candidate_appointments appointment
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
        LEFT JOIN msi_v2.accounts responsible ON responsible.id = appointment.responsible_account_id
        LEFT JOIN msi_v2.accounts started_by ON started_by.id = appointment.started_by_account_id
        LEFT JOIN msi_v2.teacher_candidate_demo_lessons demo_evaluation
          ON demo_evaluation.appointment_id = appointment.id
         AND demo_evaluation.voided_at IS NULL
        LEFT JOIN msi_v2.accounts demo_evaluator
          ON demo_evaluator.id = demo_evaluation.evaluator_account_id
        WHERE appointment.id = %s AND appointment.candidate_id = %s
        {suffix}
        """,
        (int(appointment_id), int(candidate_id)),
    ).fetchone()


def list_appointment_conflicts(
    conn: Any,
    *,
    responsible_account_id: int,
    starts_at: str,
    ends_at: str,
    exclude_appointment_id: int | None = None,
) -> list[Any]:
    exclude_sql = "AND appointment.id <> %s" if exclude_appointment_id else ""
    params: list[Any] = [int(responsible_account_id), ends_at, starts_at]
    if exclude_appointment_id:
        params.append(int(exclude_appointment_id))
    return conn.execute(
        f"""
        SELECT appointment.id, appointment.candidate_id, appointment.appointment_type,
               appointment.starts_at::text AS starts_at,
               appointment.ends_at::text AS ends_at,
               candidate.full_name AS candidate_name
        FROM msi_v2.teacher_candidate_appointments appointment
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        WHERE appointment.responsible_account_id = %s
          AND appointment.status IN ('scheduled', 'in_progress')
          AND appointment.starts_at < %s::timestamptz
          AND appointment.ends_at > %s::timestamptz
          {exclude_sql}
        ORDER BY appointment.starts_at ASC, appointment.id ASC
        """,
        tuple(params),
    ).fetchall()


def insert_appointment(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_appointments (
            candidate_id, appointment_type, starts_at, ends_at,
            responsible_account_id, appointment_format, location_or_link,
            topic, note, status, created_by_account_id, updated_by_account_id,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s::timestamptz, %s::timestamptz,
            %s, %s, %s, %s, %s, 'scheduled', %s, %s,
            %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            int(candidate_id),
            values["appointment_type"],
            values["starts_at"],
            values["ends_at"],
            values.get("responsible_account_id"),
            values.get("appointment_format", ""),
            values.get("location_or_link", ""),
            values.get("topic", ""),
            values.get("note", ""),
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def active_appointment_for_type(
    conn: Any,
    *,
    candidate_id: int,
    appointment_type: str,
) -> Any:
    return conn.execute(
        """
        SELECT id, version, status, starts_at::text AS starts_at,
               started_at::text AS started_at
        FROM msi_v2.teacher_candidate_appointments
        WHERE candidate_id = %s AND appointment_type = %s
          AND status IN ('scheduled', 'in_progress')
        ORDER BY starts_at ASC, id ASC
        LIMIT 1
        """,
        (candidate_id, appointment_type),
    ).fetchone()


def update_appointment(
    conn: Any,
    *,
    appointment_id: int,
    candidate_id: int,
    expected_version: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET starts_at = %s::timestamptz, ends_at = %s::timestamptz,
            responsible_account_id = %s, appointment_format = %s,
            location_or_link = %s, topic = %s, note = %s,
            updated_by_account_id = %s, updated_at = %s::timestamptz,
            version = version + 1
        WHERE id = %s AND candidate_id = %s AND status = 'scheduled' AND version = %s
        RETURNING id, version
        """,
        (
            values["starts_at"],
            values["ends_at"],
            values.get("responsible_account_id"),
            values.get("appointment_format", ""),
            values.get("location_or_link", ""),
            values.get("topic", ""),
            values.get("note", ""),
            actor_account_id,
            now,
            int(appointment_id),
            int(candidate_id),
            int(expected_version),
        ),
    ).fetchone()


def set_appointment_status(
    conn: Any,
    *,
    appointment_id: int,
    candidate_id: int,
    expected_version: int,
    status: str,
    reason: str,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET status = %s,
            cancellation_reason = CASE WHEN %s = 'cancelled' THEN %s ELSE cancellation_reason END,
            completed_at = CASE WHEN %s = 'completed' THEN %s::timestamptz ELSE completed_at END,
            cancelled_at = CASE WHEN %s = 'cancelled' THEN %s::timestamptz ELSE cancelled_at END,
            no_show_at = CASE WHEN %s = 'no_show' THEN %s::timestamptz ELSE no_show_at END,
            updated_by_account_id = %s, updated_at = %s::timestamptz,
            version = version + 1
        WHERE id = %s AND candidate_id = %s
          AND status IN ('scheduled', 'in_progress') AND version = %s
        RETURNING id, version
        """,
        (
            status,
            status,
            reason,
            status,
            now,
            status,
            now,
            status,
            now,
            actor_account_id,
            now,
            int(appointment_id),
            int(candidate_id),
            int(expected_version),
        ),
    ).fetchone()


def complete_appointment(
    conn: Any,
    *,
    appointment_id: int,
    candidate_id: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET status = 'completed', completed_at = %s::timestamptz,
            updated_by_account_id = %s, updated_at = %s::timestamptz,
            version = version + 1
        WHERE id = %s AND candidate_id = %s
          AND status IN ('scheduled', 'in_progress')
        RETURNING id, version
        """,
        (now, actor_account_id, now, int(appointment_id), int(candidate_id)),
    ).fetchone()


def complete_historical_appointment(
    conn: Any,
    *,
    appointment_id: int,
    candidate_id: int,
    completed_at: str,
    actor_account_id: int | None,
    now: str,
) -> Any:
    """Complete a restored appointment at its real historical end time."""

    return conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET status = 'completed', completed_at = %s::timestamptz,
            updated_by_account_id = %s, updated_at = %s::timestamptz,
            version = version + 1
        WHERE id = %s AND candidate_id = %s
          AND status IN ('scheduled', 'in_progress')
        RETURNING id, version
        """,
        (
            completed_at,
            actor_account_id,
            now,
            int(appointment_id),
            int(candidate_id),
        ),
    ).fetchone()


def cancel_active_appointments(
    conn: Any,
    *,
    candidate_id: int,
    reason: str,
    actor_account_id: int | None,
    now: str,
) -> list[int]:
    rows = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET status = 'cancelled', cancellation_reason = %s,
            cancelled_at = %s::timestamptz, updated_by_account_id = %s,
            updated_at = %s::timestamptz, version = version + 1
        WHERE candidate_id = %s AND status IN ('scheduled', 'in_progress')
        RETURNING id
        """,
        (reason, now, actor_account_id, now, int(candidate_id)),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def cancel_scheduled_appointments(
    conn: Any,
    *,
    candidate_id: int,
    reason: str,
    actor_account_id: int | None,
    now: str,
) -> list[int]:
    """Compatibility name; active now includes scheduled and in-progress sessions."""
    return cancel_active_appointments(
        conn,
        candidate_id=candidate_id,
        reason=reason,
        actor_account_id=actor_account_id,
        now=now,
    )


def start_interview_session(
    conn: Any,
    *,
    appointment_id: int,
    candidate_id: int,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET status = 'in_progress', started_at = %s::timestamptz,
            started_by_account_id = %s, updated_by_account_id = %s,
            updated_at = %s::timestamptz, version = version + 1
        WHERE id = %s AND candidate_id = %s
          AND appointment_type = 'job_interview'
          AND status = 'scheduled' AND version = %s
          AND %s::timestamptz >= starts_at - interval '30 minutes'
        RETURNING id, version, status, started_at::text AS started_at
        """,
        (
            now,
            actor_account_id,
            actor_account_id,
            now,
            int(appointment_id),
            int(candidate_id),
            int(expected_version),
            now,
        ),
    ).fetchone()


def complete_interview_session(
    conn: Any,
    *,
    appointment_id: int,
    candidate_id: int,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_appointments
        SET status = 'completed', completed_at = %s::timestamptz,
            updated_by_account_id = %s, updated_at = %s::timestamptz,
            version = version + 1
        WHERE id = %s AND candidate_id = %s
          AND appointment_type = 'job_interview'
          AND status = 'in_progress' AND version = %s
        RETURNING id, version, status, started_at::text AS started_at,
                  completed_at::text AS completed_at
        """,
        (
            now,
            actor_account_id,
            now,
            int(appointment_id),
            int(candidate_id),
            int(expected_version),
        ),
    ).fetchone()


__all__ = [
    "active_appointment_for_type",
    "cancel_active_appointments",
    "cancel_scheduled_appointments",
    "complete_appointment",
    "complete_historical_appointment",
    "complete_interview_session",
    "get_appointment_row",
    "insert_appointment",
    "list_appointment_conflicts",
    "list_appointment_rows",
    "set_appointment_status",
    "start_interview_session",
    "update_appointment",
]
