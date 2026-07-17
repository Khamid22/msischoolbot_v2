"""PostgreSQL queries for the recruitment analytics dashboard."""

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
    date_from: str = "",
    date_to: str = "",
    source: str = "",
    subsource: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
    alias: str = "candidate",
) -> tuple[str, list[Any]]:
    clauses = [f"{alias}.status <> 'trash_bin'"]
    params: list[Any] = []
    if date_from and date_to:
        clauses.append(f"{alias}.application_date BETWEEN %s::date AND %s::date")
        params.extend([date_from, date_to])
    if source:
        if str(source).isdigit():
            clauses.append(f"{alias}.source_option_id = %s")
            params.append(int(source))
        else:
            clauses.append(f"lower({alias}.source) = lower(%s)")
            params.append(source)
    if subsource:
        clauses.append(f"{alias}.subsource_option_id = %s")
        params.append(int(subsource))
    if position:
        if str(position).isdigit():
            clauses.append(f"{alias}.position_option_id = %s")
            params.append(int(position))
        else:
            clauses.append(
                f"""EXISTS (
                    SELECT 1
                    FROM msi_v2.teacher_recruitment_settings position_filter
                    WHERE position_filter.id = {alias}.position_option_id
                      AND lower(position_filter.label) = lower(%s)
                )"""
            )
            params.append(position)
    if subject_id:
        clauses.append(f"{alias}.subject_id = %s")
        params.append(int(subject_id))
    if responsible_account_id:
        clauses.append(
            f"""EXISTS (
                SELECT 1
                FROM msi_v2.teacher_candidate_stage_history responsible_history
                WHERE responsible_history.candidate_id = {alias}.id
                  AND responsible_history.responsible_account_id = %s
            )"""
        )
        params.append(int(responsible_account_id))
    return " AND ".join(clauses), params


def options_rows(conn: Any) -> dict[str, list[Any]]:
    return {
        "sources": conn.execute(
            """SELECT setting.id, setting.label
               FROM msi_v2.teacher_recruitment_settings setting
               WHERE setting.category = 'source' AND setting.is_active
               ORDER BY setting.sort_order, lower(setting.label), setting.id"""
        ).fetchall(),
        "subsources": conn.execute(
            """SELECT setting.id, setting.parent_id, setting.label
               FROM msi_v2.teacher_recruitment_settings setting
               WHERE setting.category = 'subsource' AND setting.is_active
               ORDER BY setting.sort_order, lower(setting.label), setting.id"""
        ).fetchall(),
        "positions": conn.execute(
            """SELECT setting.id, setting.label
               FROM msi_v2.teacher_recruitment_settings setting
               WHERE setting.category = 'position' AND setting.is_active
               ORDER BY setting.sort_order, lower(setting.label), setting.id"""
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


def _cohort_summary(
    conn: Any,
    *,
    where_sql: str,
    params: list[Any],
    now: str,
) -> Any:
    return conn.execute(
        f"""SELECT
              COUNT(*) AS applications,
              COUNT(*) FILTER (
                WHERE EXISTS (
                  SELECT 1
                  FROM msi_v2.teacher_candidate_stage_history review_history
                  WHERE review_history.candidate_id = candidate.id
                    AND review_history.stage = 'under_review'
                )
              ) AS shortlisted,
              COUNT(*) FILTER (WHERE decision.decision = 'active_teacher') AS hired,
              COUNT(*) FILTER (WHERE decision.decision = 'rejected') AS rejected,
              COUNT(*) FILTER (WHERE decision.decision = 'teacher_academy') AS academy_accepted,
              COUNT(*) FILTER (WHERE decision.decision = 'candidate_withdrew') AS withdrawn,
              COUNT(*) FILTER (WHERE candidate.status = ANY(%s::text[])) AS active_candidates,
              ROUND(AVG(
                EXTRACT(EPOCH FROM (
                  decision.created_at - COALESCE(application_history.entered_at, candidate.created_at)
                )) / 86400.0
              ) FILTER (WHERE decision.decision = 'active_teacher'), 1) AS average_time_to_hire_days,
              ROUND(
                100.0 * COUNT(*) FILTER (WHERE decision.decision = 'active_teacher')
                / NULLIF(COUNT(*), 0),
                1
              ) AS overall_conversion_percentage,
              COALESCE(SUM(stage_sla.breaches), 0) AS sla_breaches
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN LATERAL (
              SELECT final_decision.decision, final_decision.created_at
              FROM msi_v2.teacher_candidate_final_decisions final_decision
              WHERE final_decision.candidate_id = candidate.id
                AND final_decision.voided_at IS NULL
              ORDER BY final_decision.created_at DESC, final_decision.id DESC
              LIMIT 1
            ) decision ON true
            LEFT JOIN LATERAL (
              SELECT history.entered_at
              FROM msi_v2.teacher_candidate_stage_history history
              WHERE history.candidate_id = candidate.id
                AND history.stage = 'new_candidate'
              ORDER BY history.entered_at ASC, history.id ASC
              LIMIT 1
            ) application_history ON true
            LEFT JOIN LATERAL (
              SELECT COUNT(*)::integer AS breaches
              FROM msi_v2.teacher_candidate_stage_history history
              WHERE history.candidate_id = candidate.id
                AND history.sla_due_at IS NOT NULL
                AND COALESCE(history.exited_at, %s::timestamptz) > history.sla_due_at
            ) stage_sla ON true
            WHERE {where_sql}""",
        tuple([list(ACTIVE_STAGES), now, *params]),
    ).fetchone()


def dashboard_rows(
    conn: Any,
    *,
    date_from: str,
    date_to: str,
    comparison_from: str,
    comparison_to: str,
    bucket: str,
    now: str,
    source: str = "",
    subsource: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
) -> dict[str, Any]:
    filter_values = {
        "source": source,
        "subsource": subsource,
        "position": position,
        "subject_id": subject_id,
        "responsible_account_id": responsible_account_id,
    }
    where_sql, params = _candidate_filters(
        date_from=date_from,
        date_to=date_to,
        **filter_values,
    )
    comparison_where, comparison_params = _candidate_filters(
        date_from=comparison_from,
        date_to=comparison_to,
        **filter_values,
    )
    base_where, base_params = _candidate_filters(**filter_values)

    current_summary = _cohort_summary(conn, where_sql=where_sql, params=params, now=now)
    comparison_summary = _cohort_summary(
        conn,
        where_sql=comparison_where,
        params=comparison_params,
        now=now,
    )

    journey = conn.execute(
        f"""WITH cohort AS (
              SELECT candidate.id
              FROM msi_v2.teacher_candidates candidate
              WHERE {where_sql}
            )
            SELECT history.stage, COUNT(DISTINCT history.candidate_id) AS candidates
            FROM msi_v2.teacher_candidate_stage_history history
            JOIN cohort ON cohort.id = history.candidate_id
            WHERE history.stage IN (
              'new_candidate', 'responded', 'job_interview',
              'test_and_demo', 'under_review'
            )
            GROUP BY history.stage""",
        tuple(params),
    ).fetchall()

    outcomes = conn.execute(
        f"""SELECT decision.decision AS outcome, COUNT(*) AS candidates
            FROM msi_v2.teacher_candidates candidate
            JOIN LATERAL (
              SELECT final_decision.decision
              FROM msi_v2.teacher_candidate_final_decisions final_decision
              WHERE final_decision.candidate_id = candidate.id
                AND final_decision.voided_at IS NULL
              ORDER BY final_decision.created_at DESC, final_decision.id DESC
              LIMIT 1
            ) decision ON true
            WHERE {where_sql}
              AND decision.decision IN (
                'teacher_academy', 'active_teacher', 'rejected', 'candidate_withdrew'
              )
            GROUP BY decision.decision""",
        tuple(params),
    ).fetchall()

    trend = conn.execute(
        f"""WITH filtered_candidates AS (
              SELECT candidate.id, candidate.application_date
              FROM msi_v2.teacher_candidates candidate
              WHERE {base_where}
            ), first_review AS (
              SELECT history.candidate_id, MIN(history.entered_at) AS entered_at
              FROM msi_v2.teacher_candidate_stage_history history
              JOIN filtered_candidates candidate ON candidate.id = history.candidate_id
              WHERE history.stage = 'under_review'
              GROUP BY history.candidate_id
            ), latest_decision AS (
              SELECT DISTINCT ON (final_decision.candidate_id)
                     final_decision.candidate_id,
                     final_decision.decision,
                     final_decision.created_at
              FROM msi_v2.teacher_candidate_final_decisions final_decision
              JOIN filtered_candidates candidate ON candidate.id = final_decision.candidate_id
              WHERE final_decision.voided_at IS NULL
              ORDER BY final_decision.candidate_id,
                       final_decision.created_at DESC,
                       final_decision.id DESC
            ), events AS (
              SELECT candidate.application_date AS event_date, 'applications'::text AS event_type
              FROM filtered_candidates candidate
              WHERE candidate.application_date IS NOT NULL
              UNION ALL
              SELECT (review.entered_at AT TIME ZONE 'Asia/Tashkent')::date, 'shortlisted'
              FROM first_review review
              UNION ALL
              SELECT (decision.created_at AT TIME ZONE 'Asia/Tashkent')::date,
                     CASE
                       WHEN decision.decision = 'active_teacher' THEN 'hired'
                       WHEN decision.decision = 'rejected' THEN 'rejected'
                     END
              FROM latest_decision decision
              WHERE decision.decision IN ('active_teacher', 'rejected')
            )
            SELECT date_trunc(%s, event.event_date::timestamp)::date::text AS bucket,
                   event.event_type,
                   COUNT(*) AS candidates
            FROM events event
            WHERE event.event_date BETWEEN %s::date AND %s::date
            GROUP BY date_trunc(%s, event.event_date::timestamp)::date, event.event_type
            ORDER BY date_trunc(%s, event.event_date::timestamp)::date, event.event_type""",
        tuple([*base_params, bucket, date_from, date_to, bucket, bucket]),
    ).fetchall()

    positions = conn.execute(
        f"""SELECT COALESCE(
                     position_setting.label,
                     NULLIF(candidate.applied_position, ''),
                     'Not set'
                   ) AS position,
                   COUNT(*) AS candidates
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN msi_v2.teacher_recruitment_settings position_setting
              ON position_setting.id = candidate.position_option_id
            WHERE {where_sql}
            GROUP BY COALESCE(
              position_setting.label,
              NULLIF(candidate.applied_position, ''),
              'Not set'
            )
            ORDER BY candidates DESC, position
            LIMIT 12""",
        tuple(params),
    ).fetchall()

    sources = conn.execute(
        f"""SELECT
              COALESCE(source_setting.label, NULLIF(candidate.source, ''), 'Not set') AS source,
              COALESCE(subsource_setting.label, 'Not set') AS subsource,
              COUNT(*) AS candidates,
              COUNT(*) FILTER (
                WHERE EXISTS (
                  SELECT 1
                  FROM msi_v2.teacher_candidate_stage_history review_history
                  WHERE review_history.candidate_id = candidate.id
                    AND review_history.stage = 'under_review'
                )
              ) AS shortlisted,
              COUNT(*) FILTER (WHERE decision.decision = 'active_teacher') AS hired,
              ROUND(
                100.0 * COUNT(*) FILTER (WHERE decision.decision = 'active_teacher')
                / NULLIF(COUNT(*), 0),
                1
              ) AS conversion_percentage
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN msi_v2.teacher_recruitment_settings source_setting
              ON source_setting.id = candidate.source_option_id
            LEFT JOIN msi_v2.teacher_recruitment_settings subsource_setting
              ON subsource_setting.id = candidate.subsource_option_id
            LEFT JOIN LATERAL (
              SELECT final_decision.decision
              FROM msi_v2.teacher_candidate_final_decisions final_decision
              WHERE final_decision.candidate_id = candidate.id
                AND final_decision.voided_at IS NULL
              ORDER BY final_decision.created_at DESC, final_decision.id DESC
              LIMIT 1
            ) decision ON true
            WHERE {where_sql}
            GROUP BY
              COALESCE(source_setting.label, NULLIF(candidate.source, ''), 'Not set'),
              COALESCE(subsource_setting.label, 'Not set')
            ORDER BY candidates DESC, source, subsource""",
        tuple(params),
    ).fetchall()

    stage_time = conn.execute(
        f"""SELECT history.stage,
                   ROUND(AVG(
                     EXTRACT(EPOCH FROM (
                       COALESCE(history.exited_at, %s::timestamptz) - history.entered_at
                     )) / 86400.0
                   ), 1) AS average_days,
                   MAX(history.sla_target_days) AS sla_target_days,
                   COUNT(*) FILTER (
                     WHERE history.sla_due_at IS NOT NULL
                       AND COALESCE(history.exited_at, %s::timestamptz) > history.sla_due_at
                   ) AS sla_breaches,
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
            WHERE task.status = 'pending'
              AND task.due_at < %s::timestamptz
              AND {where_sql}
            ORDER BY task.due_at ASC, task.id ASC
            LIMIT 20""",
        tuple([now, *params]),
    ).fetchall()

    appointments = conn.execute(
        f"""SELECT appointment.id, appointment.candidate_id,
                   candidate.full_name AS candidate_name,
                   appointment.appointment_type,
                   appointment.starts_at::text AS starts_at,
                   COALESCE(account.full_name, account.login, '') AS responsible_name
            FROM msi_v2.teacher_candidate_appointments appointment
            JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
            LEFT JOIN msi_v2.accounts account ON account.id = appointment.responsible_account_id
            WHERE appointment.status IN ('scheduled', 'in_progress')
              AND appointment.starts_at >= %s::timestamptz
              AND {where_sql}
            ORDER BY appointment.starts_at ASC, appointment.id ASC
            LIMIT 20""",
        tuple([now, *params]),
    ).fetchall()

    recent_candidates = conn.execute(
        f"""SELECT candidate.id, candidate.full_name,
                   COALESCE(
                     position_setting.label,
                     NULLIF(candidate.applied_position, ''),
                     'Not set'
                   ) AS position,
                   COALESCE(source_setting.label, NULLIF(candidate.source, ''), 'Not set') AS source,
                   COALESCE(subsource_setting.label, '') AS subsource,
                   candidate.application_date::text AS application_date,
                   candidate.status,
                   next_task.title AS next_action
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN msi_v2.teacher_recruitment_settings position_setting
              ON position_setting.id = candidate.position_option_id
            LEFT JOIN msi_v2.teacher_recruitment_settings source_setting
              ON source_setting.id = candidate.source_option_id
            LEFT JOIN msi_v2.teacher_recruitment_settings subsource_setting
              ON subsource_setting.id = candidate.subsource_option_id
            LEFT JOIN LATERAL (
              SELECT task.title
              FROM msi_v2.teacher_candidate_tasks task
              WHERE task.candidate_id = candidate.id
                AND task.status = 'pending'
              ORDER BY task.due_at ASC NULLS LAST, task.id ASC
              LIMIT 1
            ) next_task ON true
            WHERE {where_sql}
            ORDER BY candidate.application_date DESC NULLS LAST, candidate.id DESC
            LIMIT 12""",
        tuple(params),
    ).fetchall()

    recent_activity = conn.execute(
        f"""SELECT audit.id, audit.event_type, audit.detail_json,
                   audit.created_at::text AS created_at,
                   candidate.id AS candidate_id,
                   candidate.full_name AS candidate_name,
                   COALESCE(account.full_name, account.login, staff.login, 'System') AS actor
            FROM msi_v2.audit_events audit
            JOIN msi_v2.teacher_candidates candidate
              ON candidate.id = audit.entity_id
             AND audit.entity_type = 'teacher_candidate'
            LEFT JOIN msi_v2.accounts account ON account.id = audit.actor_account_id
            LEFT JOIN msi_v2.msi_staff staff ON staff.id = audit.actor_staff_id
            WHERE {base_where}
              AND (audit.created_at AT TIME ZONE 'Asia/Tashkent')::date
                    BETWEEN %s::date AND %s::date
            ORDER BY audit.created_at DESC, audit.id DESC
            LIMIT 12""",
        tuple([*base_params, date_from, date_to]),
    ).fetchall()

    return {
        "current_summary": current_summary,
        "comparison_summary": comparison_summary,
        "journey": journey,
        "outcomes": outcomes,
        "activity_trend": trend,
        "position_distribution": positions,
        "source_quality": sources,
        "time_in_stage": stage_time,
        "overdue_actions": overdue,
        "upcoming_appointments": appointments,
        "recent_candidates": recent_candidates,
        "recent_activity": recent_activity,
    }


__all__ = ["dashboard_rows", "options_rows"]
