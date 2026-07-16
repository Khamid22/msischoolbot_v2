"""PostgreSQL queries for the essential recruitment dashboard."""

from __future__ import annotations

from typing import Any


ACTIVE_STAGES = (
    "new_candidate",
    "responded",
    "job_interview",
    "test_and_demo",
    "under_review",
)


def _candidate_filters(
    *,
    date_from: str,
    date_to: str,
    source: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
    alias: str = "candidate",
) -> tuple[str, list[Any]]:
    clauses = [f"{alias}.application_date BETWEEN %s::date AND %s::date"]
    params: list[Any] = [date_from, date_to]
    if source:
        clauses.append(f"{alias}.source = %s")
        params.append(source)
    if position:
        clauses.append(f"{alias}.applied_position = %s")
        params.append(position)
    if subject_id:
        clauses.append(f"{alias}.subject_id = %s")
        params.append(int(subject_id))
    if responsible_account_id:
        clauses.append(
            f"""EXISTS (
                SELECT 1 FROM msi_v2.teacher_candidate_stage_history responsible_history
                WHERE responsible_history.candidate_id = {alias}.id
                  AND responsible_history.responsible_account_id = %s
            )"""
        )
        params.append(int(responsible_account_id))
    return " AND ".join(clauses), params


def options_rows(conn: Any) -> dict[str, list[Any]]:
    return {
        "sources": conn.execute(
            "SELECT DISTINCT source AS value FROM msi_v2.teacher_candidates WHERE COALESCE(source, '') <> '' ORDER BY source"
        ).fetchall(),
        "positions": conn.execute(
            "SELECT DISTINCT applied_position AS value FROM msi_v2.teacher_candidates WHERE COALESCE(applied_position, '') <> '' ORDER BY applied_position"
        ).fetchall(),
        "subjects": conn.execute(
            """SELECT DISTINCT subject.id, subject.subject_name AS name
               FROM msi_v2.teacher_candidates candidate
               JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
               ORDER BY subject.subject_name"""
        ).fetchall(),
        "responsible_people": conn.execute(
            """SELECT DISTINCT account.id,
                      COALESCE(account.full_name, account.login) AS name
               FROM msi_v2.teacher_candidate_stage_history history
               JOIN msi_v2.accounts account ON account.id = history.responsible_account_id
               ORDER BY name"""
        ).fetchall(),
    }


def dashboard_rows(
    conn: Any,
    *,
    date_from: str,
    date_to: str,
    month_from: str,
    month_to: str,
    now: str,
    source: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
) -> dict[str, Any]:
    where_sql, params = _candidate_filters(
        date_from=date_from,
        date_to=date_to,
        source=source,
        position=position,
        subject_id=subject_id,
        responsible_account_id=responsible_account_id,
    )
    month_where, month_params = _candidate_filters(
        date_from=month_from,
        date_to=month_to,
        source=source,
        position=position,
        subject_id=subject_id,
        responsible_account_id=responsible_account_id,
    )
    successful = "('teacher_academy', 'active_teacher')"
    kpis = conn.execute(
        f"""SELECT
              COUNT(*) FILTER (WHERE candidate.status = ANY(%s::text[])) AS active_candidates,
              COUNT(*) FILTER (WHERE {month_where}) AS new_this_month,
              COUNT(*) FILTER (
                WHERE decision.decision IN {successful}
                  AND decision.voided_at IS NULL
                  AND decision.created_at >= %s::timestamptz
                  AND decision.created_at < %s::timestamptz
              ) AS hired_this_month,
              ROUND(AVG(EXTRACT(EPOCH FROM (decision.created_at - candidate.created_at)) / 86400.0)
                FILTER (WHERE decision.decision IN {successful} AND decision.voided_at IS NULL), 1)
                AS average_time_to_hire_days,
              ROUND(100.0 * COUNT(*) FILTER (
                WHERE decision.decision IN {successful} AND decision.voided_at IS NULL
              ) / NULLIF(COUNT(*), 0), 1) AS overall_conversion_percentage
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN LATERAL (
              SELECT final_decision.decision, final_decision.created_at, final_decision.voided_at
              FROM msi_v2.teacher_candidate_final_decisions final_decision
              WHERE final_decision.candidate_id = candidate.id AND final_decision.voided_at IS NULL
              ORDER BY final_decision.created_at DESC, final_decision.id DESC LIMIT 1
            ) decision ON true
            WHERE {where_sql}""",
        tuple([list(ACTIVE_STAGES), *month_params, month_from, month_to, *params]),
    ).fetchone()
    funnel = conn.execute(
        f"""WITH cohort AS (
              SELECT candidate.id FROM msi_v2.teacher_candidates candidate WHERE {where_sql}
            )
            SELECT history.stage, COUNT(DISTINCT history.candidate_id) AS candidates
            FROM msi_v2.teacher_candidate_stage_history history
            JOIN cohort ON cohort.id = history.candidate_id
            GROUP BY history.stage""",
        tuple(params),
    ).fetchall()
    sources = conn.execute(
        f"""SELECT COALESCE(candidate.source, 'Not set') AS source,
                   COUNT(*) AS candidates,
                   COUNT(*) FILTER (WHERE decision.decision IN {successful}) AS hired,
                   ROUND(100.0 * COUNT(*) FILTER (WHERE decision.decision IN {successful}) /
                         NULLIF(COUNT(*), 0), 1) AS conversion_percentage
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN LATERAL (
              SELECT final_decision.decision
              FROM msi_v2.teacher_candidate_final_decisions final_decision
              WHERE final_decision.candidate_id = candidate.id AND final_decision.voided_at IS NULL
              ORDER BY final_decision.created_at DESC, final_decision.id DESC LIMIT 1
            ) decision ON true
            WHERE {where_sql}
            GROUP BY COALESCE(candidate.source, 'Not set')
            ORDER BY candidates DESC, source""",
        tuple(params),
    ).fetchall()
    stage_time = conn.execute(
        f"""SELECT history.stage,
                   ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(history.exited_at, %s::timestamptz) - history.entered_at)) / 86400.0), 1)
                     AS average_days,
                   COUNT(*) FILTER (WHERE history.sla_due_at IS NOT NULL AND
                     COALESCE(history.exited_at, %s::timestamptz) > history.sla_due_at) AS sla_breaches,
                   COUNT(*) AS entries
            FROM msi_v2.teacher_candidate_stage_history history
            JOIN msi_v2.teacher_candidates candidate ON candidate.id = history.candidate_id
            WHERE {where_sql}
            GROUP BY history.stage
            ORDER BY average_days DESC NULLS LAST""",
        tuple([now, now, *params]),
    ).fetchall()
    overdue = conn.execute(
        f"""SELECT task.id, task.candidate_id, candidate.full_name AS candidate_name,
                   task.title, task.due_at::text AS due_at
            FROM msi_v2.teacher_candidate_tasks task
            JOIN msi_v2.teacher_candidates candidate ON candidate.id = task.candidate_id
            WHERE task.status = 'pending' AND task.due_at < %s::timestamptz AND {where_sql}
            ORDER BY task.due_at ASC LIMIT 20""",
        tuple([now, *params]),
    ).fetchall()
    appointments = conn.execute(
        f"""SELECT appointment.id, appointment.candidate_id,
                   candidate.full_name AS candidate_name, appointment.appointment_type,
                   appointment.starts_at::text AS starts_at,
                   COALESCE(account.full_name, account.login, '') AS responsible_name
            FROM msi_v2.teacher_candidate_appointments appointment
            JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
            LEFT JOIN msi_v2.accounts account ON account.id = appointment.responsible_account_id
            WHERE appointment.status = 'scheduled' AND appointment.starts_at >= %s::timestamptz
              AND {where_sql}
            ORDER BY appointment.starts_at ASC LIMIT 20""",
        tuple([now, *params]),
    ).fetchall()
    return {
        "kpis": kpis,
        "funnel": funnel,
        "source_conversion": sources,
        "time_in_stage": stage_time,
        "overdue_actions": overdue,
        "upcoming_appointments": appointments,
    }


__all__ = ["dashboard_rows", "options_rows"]
