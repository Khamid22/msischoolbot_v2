"""PostgreSQL queries for the recruitment analytics dashboard."""

from __future__ import annotations

from typing import Any


def _stage_rank_sql(expression: str) -> str:
    return f"""CASE {expression}
        WHEN 'new_candidate' THEN 0
        WHEN 'responded' THEN 1
        WHEN 'job_interview' THEN 2
        WHEN 'test_and_demo' THEN 3
        WHEN 'under_review' THEN 4
        WHEN 'teacher_academy' THEN 5
        WHEN 'active_teacher' THEN 6
        ELSE -1
    END"""


def _candidate_facts_cte(*, where_sql: str, alias: str = "candidate") -> str:
    """Return one canonical analytics row per application-origin profile."""

    return f"""candidate_facts AS (
        SELECT
            {alias}.id,
            {alias}.application_date,
            {alias}.created_at AS profile_created_at,
            {alias}.status,
            GREATEST(
                {_stage_rank_sql(f"{alias}.status")},
                COALESCE(stage_progress.furthest_rank, -1),
                CASE WHEN academy.id IS NOT NULL THEN 5 ELSE -1 END,
                CASE WHEN active_teacher.id IS NOT NULL THEN 6 ELSE -1 END
            ) AS furthest_rank,
            decision.decision AS latest_decision,
            decision.created_at AS latest_decision_at,
            academy.id AS academy_teacher_id,
            academy.created_at AS academy_created_at,
            active_teacher.id AS active_teacher_id,
            active_teacher.activated_at AS active_teacher_created_at,
            COALESCE(stage_sla.breaches, 0) AS cohort_sla_breaches
        FROM msi_v2.teacher_candidates {alias}
        LEFT JOIN LATERAL (
            SELECT MAX({_stage_rank_sql("history.stage")}) AS furthest_rank
            FROM msi_v2.teacher_candidate_stage_history history
            WHERE history.candidate_id = {alias}.id
        ) stage_progress ON true
        LEFT JOIN LATERAL (
            SELECT final_decision.decision, final_decision.created_at
            FROM msi_v2.teacher_candidate_final_decisions final_decision
            WHERE final_decision.candidate_id = {alias}.id
              AND final_decision.voided_at IS NULL
            ORDER BY final_decision.created_at DESC, final_decision.id DESC
            LIMIT 1
        ) decision ON true
        LEFT JOIN LATERAL (
            SELECT academy_teacher.id, academy_teacher.created_at
            FROM msi_v2.academy_teachers academy_teacher
            WHERE academy_teacher.recruitment_candidate_id = {alias}.id
              AND academy_teacher.promoted_teacher_id IS NULL
              AND academy_teacher.academy_status NOT IN (
                'rejected', 'removed', 'trash_bin'
              )
            ORDER BY academy_teacher.id DESC
            LIMIT 1
        ) academy ON true
        LEFT JOIN LATERAL (
            SELECT teacher.id, COALESCE(teacher.activated_at, teacher.created_at)
                   AS activated_at
            FROM msi_v2.teachers teacher
            WHERE teacher.recruitment_candidate_id = {alias}.id
              AND teacher.status = 'active'
            ORDER BY teacher.id DESC
            LIMIT 1
        ) active_teacher ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*)::integer AS breaches
            FROM msi_v2.teacher_candidate_stage_history history
            WHERE history.candidate_id = {alias}.id
              AND history.sla_due_at IS NOT NULL
              AND COALESCE(history.exited_at, %s::timestamptz) > history.sla_due_at
        ) stage_sla ON true
        WHERE {where_sql}
    )"""


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
    application_profiles_only: bool = True,
    include_trash: bool = False,
) -> tuple[str, list[Any]]:
    clauses = [] if include_trash else [f"{alias}.status <> 'trash_bin'"]
    if application_profiles_only:
        clauses.append(f"{alias}.is_application_received = true")
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
    return " AND ".join(clauses) or "TRUE", params


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
               WHERE candidate.is_application_received = true
                 AND candidate.status <> 'trash_bin'
               ORDER BY subject.subject_name"""
        ).fetchall(),
        "responsible_people": conn.execute(
            """SELECT DISTINCT account.id,
                      COALESCE(account.full_name, account.login) AS name
               FROM msi_v2.teacher_candidate_stage_history history
               JOIN msi_v2.teacher_candidates candidate ON candidate.id = history.candidate_id
               JOIN msi_v2.accounts account ON account.id = history.responsible_account_id
               WHERE candidate.is_application_received = true
                 AND candidate.status <> 'trash_bin'
               ORDER BY name"""
        ).fetchall(),
    }


def subsource_matches_source(
    conn: Any,
    *,
    source_id: int,
    subsource_id: int,
) -> bool:
    row = conn.execute(
        """SELECT EXISTS (
             SELECT 1
             FROM msi_v2.teacher_recruitment_settings subsource
             JOIN msi_v2.teacher_recruitment_settings source
               ON source.id = subsource.parent_id
             WHERE subsource.id = %s
               AND subsource.category = 'subsource'
               AND subsource.is_active
               AND source.id = %s
               AND source.category = 'source'
               AND source.is_active
           ) AS matches""",
        (subsource_id, source_id),
    ).fetchone()
    return bool(row and row["matches"])


def _cohort_summary(
    conn: Any,
    *,
    where_sql: str,
    params: list[Any],
    now: str,
) -> Any:
    facts_cte = _candidate_facts_cte(where_sql=where_sql)
    return conn.execute(
        f"""WITH {facts_cte}
            SELECT
              COUNT(*) AS applications,
              COUNT(*) FILTER (WHERE furthest_rank >= 4) AS shortlisted,
              COUNT(*) FILTER (WHERE active_teacher_id IS NOT NULL) AS hired,
              COUNT(*) FILTER (
                WHERE active_teacher_id IS NULL
                  AND academy_teacher_id IS NULL
                  AND latest_decision = 'rejected'
              ) AS rejected,
              COUNT(*) FILTER (
                WHERE academy_teacher_id IS NOT NULL
                  AND active_teacher_id IS NULL
              ) AS academy_accepted,
              COUNT(*) FILTER (
                WHERE active_teacher_id IS NULL
                  AND academy_teacher_id IS NULL
                  AND latest_decision = 'candidate_withdrew'
              ) AS withdrawn,
              COUNT(*) FILTER (WHERE EXISTS (
                SELECT 1
                FROM msi_v2.teacher_recruitment_pipeline_stages active_stage
                WHERE active_stage.stage_key = candidate_facts.status
                  AND active_stage.is_pipeline = true
                  AND active_stage.is_active = true
              )) AS active_candidates,
              ROUND(AVG(
                EXTRACT(EPOCH FROM (
                  active_teacher_created_at
                    - (application_date::timestamp AT TIME ZONE 'Asia/Tashkent')
                )) / 86400.0
              ) FILTER (
                WHERE active_teacher_id IS NOT NULL
                  AND application_date IS NOT NULL
              ), 1) AS average_time_to_hire_days,
              ROUND(
                100.0 * COUNT(*) FILTER (WHERE active_teacher_id IS NOT NULL)
                / NULLIF(COUNT(*), 0),
                1
              ) AS overall_conversion_percentage,
              COALESCE(SUM(cohort_sla_breaches), 0) AS cohort_sla_breaches
            FROM candidate_facts""",
        tuple([now, *params]),
    ).fetchone()


def _live_summary(
    conn: Any,
    *,
    where_sql: str,
    params: list[Any],
    now: str,
) -> Any:
    return conn.execute(
        f"""SELECT
              COUNT(*) FILTER (
                WHERE EXISTS (
                  SELECT 1
                  FROM msi_v2.teacher_recruitment_pipeline_stages active_stage
                  WHERE active_stage.stage_key = candidate.status
                    AND active_stage.is_pipeline = true
                    AND active_stage.is_active = true
                )
              ) AS active_candidates,
              COUNT(*) FILTER (
                WHERE EXISTS (
                  SELECT 1
                  FROM msi_v2.teacher_candidate_stage_history open_history
                  WHERE open_history.candidate_id = candidate.id
                    AND open_history.exited_at IS NULL
                    AND open_history.sla_due_at IS NOT NULL
                    AND open_history.sla_due_at < %s::timestamptz
                )
              ) AS sla_overdue_now,
              (
                SELECT COUNT(*)
                FROM msi_v2.academy_teachers academy_teacher
                LEFT JOIN msi_v2.teacher_candidates academy_candidate
                  ON academy_candidate.id = academy_teacher.recruitment_candidate_id
                WHERE academy_teacher.promoted_teacher_id IS NULL
                  AND academy_teacher.academy_status NOT IN (
                    'rejected', 'removed', 'trash_bin'
                  )
                  AND COALESCE(academy_candidate.status, 'teacher_academy') NOT IN (
                    'rejected', 'candidate_withdrew', 'trash_bin'
                  )
              ) AS academy_roster_total,
              (
                SELECT COUNT(*)
                FROM msi_v2.teachers teacher
                LEFT JOIN msi_v2.teacher_candidates active_candidate
                  ON active_candidate.id = teacher.recruitment_candidate_id
                WHERE teacher.status = 'active'
                  AND COALESCE(active_candidate.status, 'active_teacher') NOT IN (
                    'rejected', 'candidate_withdrew', 'trash_bin'
                  )
              ) AS active_teacher_roster_total
            FROM msi_v2.teacher_candidates candidate
            WHERE {where_sql}""",
        tuple([now, *params]),
    ).fetchone()


def _event_summary(
    conn: Any,
    *,
    base_where: str,
    base_params: list[Any],
    date_from: str,
    date_to: str,
) -> Any:
    """Count canonical business events rather than application-cohort outcomes."""

    return conn.execute(
        f"""
        WITH bounds AS (
          SELECT %s::date AS date_from, %s::date AS date_to
        ), base_candidates AS (
          SELECT candidate.id, candidate.application_date, candidate.status,
                 candidate.is_application_received
          FROM msi_v2.teacher_candidates candidate
          WHERE {base_where}
        ), latest_closure AS (
          SELECT DISTINCT ON (decision.candidate_id)
                 decision.candidate_id, decision.decision, decision.created_at
          FROM msi_v2.teacher_candidate_final_decisions decision
          JOIN base_candidates candidate ON candidate.id = decision.candidate_id
          WHERE decision.voided_at IS NULL
            AND decision.decision IN ('rejected', 'candidate_withdrew')
          ORDER BY decision.candidate_id, decision.created_at DESC, decision.id DESC
        ), evaluation_attempts AS (
          SELECT interview.id, interview.candidate_id, 'interview'::text AS kind,
                 interview.result,
                 interview.overall_score::numeric AS score,
                 COALESCE(interview.interview_at, interview.created_at) AS occurred_at
          FROM msi_v2.teacher_candidate_interviews interview
          JOIN base_candidates candidate ON candidate.id = interview.candidate_id
          WHERE interview.voided_at IS NULL
            AND interview.result IN ('passed', 'failed')
          UNION ALL
          SELECT demo.id, demo.candidate_id, 'demo'::text,
                 demo.result, demo.score::numeric,
                 COALESCE(demo.demo_at, demo.created_at)
          FROM msi_v2.teacher_candidate_demo_lessons demo
          JOIN base_candidates candidate ON candidate.id = demo.candidate_id
          WHERE demo.voided_at IS NULL
            AND demo.result IN ('passed', 'failed')
          UNION ALL
          SELECT test.id, test.candidate_id, 'subject_test'::text,
                 test.result,
                 CASE
                   WHEN test.maximum_score > 0
                   THEN (test.score / test.maximum_score) * 100
                   ELSE test.score
                 END,
                 COALESCE(test.test_at, test.created_at)
          FROM msi_v2.teacher_candidate_subject_tests test
          JOIN base_candidates candidate ON candidate.id = test.candidate_id
          WHERE test.voided_at IS NULL
            AND test.result IN ('passed', 'failed')
        ), ranked_attempts AS (
          SELECT attempt.*,
                 row_number() OVER (
                   PARTITION BY attempt.kind, attempt.candidate_id
                   ORDER BY
                     CASE attempt.result WHEN 'passed' THEN 2 ELSE 1 END DESC,
                     attempt.score DESC NULLS LAST,
                     attempt.occurred_at DESC,
                     attempt.id DESC
                 ) AS attempt_rank
          FROM evaluation_attempts attempt
          CROSS JOIN bounds
          WHERE (attempt.occurred_at AT TIME ZONE 'Asia/Tashkent')::date
                BETWEEN bounds.date_from AND bounds.date_to
        ), selected_attempts AS (
          SELECT * FROM ranked_attempts WHERE attempt_rank = 1
        )
        SELECT
          (
            SELECT COUNT(*) FROM base_candidates candidate
            CROSS JOIN bounds
            WHERE candidate.is_application_received = true
              AND candidate.application_date BETWEEN bounds.date_from AND bounds.date_to
          ) AS applications,
          (
            SELECT COUNT(DISTINCT history.candidate_id)
            FROM msi_v2.teacher_candidate_stage_history history
            JOIN base_candidates candidate ON candidate.id = history.candidate_id
            CROSS JOIN bounds
            WHERE history.stage = 'under_review'
              AND (history.entered_at AT TIME ZONE 'Asia/Tashkent')::date
                  BETWEEN bounds.date_from AND bounds.date_to
          ) AS final_decision,
          (
            SELECT COUNT(DISTINCT academy.recruitment_candidate_id)
            FROM msi_v2.academy_teachers academy
            JOIN base_candidates candidate
              ON candidate.id = academy.recruitment_candidate_id
            CROSS JOIN bounds
            WHERE academy.promoted_teacher_id IS NULL
              AND academy.academy_status NOT IN ('rejected', 'removed', 'trash_bin')
              AND candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')
              AND (
                COALESCE(
                  academy.academy_start_date::timestamp AT TIME ZONE 'Asia/Tashkent',
                  academy.created_at
                ) AT TIME ZONE 'Asia/Tashkent'
              )::date BETWEEN bounds.date_from AND bounds.date_to
          ) AS teacher_academy,
          (
            SELECT COUNT(DISTINCT teacher.recruitment_candidate_id)
            FROM msi_v2.teachers teacher
            JOIN base_candidates candidate
              ON candidate.id = teacher.recruitment_candidate_id
            CROSS JOIN bounds
            WHERE teacher.status = 'active'
              AND candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')
              AND (
                COALESCE(teacher.activated_at, teacher.created_at)
                AT TIME ZONE 'Asia/Tashkent'
              )::date BETWEEN bounds.date_from AND bounds.date_to
          ) AS active_teachers,
          (
            SELECT COUNT(*) FROM latest_closure closure
            JOIN base_candidates candidate ON candidate.id = closure.candidate_id
            CROSS JOIN bounds
            WHERE candidate.status = 'rejected'
              AND closure.decision = 'rejected'
              AND (closure.created_at AT TIME ZONE 'Asia/Tashkent')::date
                  BETWEEN bounds.date_from AND bounds.date_to
          ) AS rejected,
          (
            SELECT COUNT(*) FROM latest_closure closure
            JOIN base_candidates candidate ON candidate.id = closure.candidate_id
            CROSS JOIN bounds
            WHERE candidate.status = 'candidate_withdrew'
              AND closure.decision = 'candidate_withdrew'
              AND (closure.created_at AT TIME ZONE 'Asia/Tashkent')::date
                  BETWEEN bounds.date_from AND bounds.date_to
          ) AS withdrawn,
          (
            SELECT COUNT(*) FROM ranked_attempts attempt
            WHERE attempt.kind = 'interview'
          ) AS interview_total,
          COUNT(*) FILTER (
            WHERE selected.kind = 'interview'
          ) AS interview_unique_candidates,
          COUNT(*) FILTER (
            WHERE selected.kind = 'interview' AND selected.result = 'passed'
          ) AS interview_passed,
          COUNT(*) FILTER (
            WHERE selected.kind = 'interview' AND selected.result = 'failed'
          ) AS interview_failed,
          (
            SELECT COUNT(*) FROM ranked_attempts attempt
            WHERE attempt.kind = 'demo'
          ) AS demo_total,
          COUNT(*) FILTER (
            WHERE selected.kind = 'demo'
          ) AS demo_unique_candidates,
          COUNT(*) FILTER (
            WHERE selected.kind = 'demo' AND selected.result = 'passed'
          ) AS demo_passed,
          COUNT(*) FILTER (
            WHERE selected.kind = 'demo' AND selected.result = 'failed'
          ) AS demo_failed,
          (
            SELECT COUNT(*) FROM ranked_attempts attempt
            WHERE attempt.kind = 'subject_test'
          ) AS subject_test_total,
          COUNT(*) FILTER (
            WHERE selected.kind = 'subject_test'
          ) AS subject_test_unique_candidates,
          COUNT(*) FILTER (
            WHERE selected.kind = 'subject_test' AND selected.result = 'passed'
          ) AS subject_test_passed,
          COUNT(*) FILTER (
            WHERE selected.kind = 'subject_test' AND selected.result = 'failed'
          ) AS subject_test_failed
        FROM selected_attempts selected
        """,
        tuple([date_from, date_to, *base_params]),
    ).fetchone()


def _monthly_stage_totals(
    conn: Any,
    *,
    base_where: str,
    base_params: list[Any],
    date_from: str,
    date_to: str,
) -> Any:
    """Count distinct monthly activity, independently of application cohort."""

    return conn.execute(
        f"""
        WITH bounds AS (
          SELECT %s::date AS date_from, %s::date AS date_to
        ), base_candidates AS (
          SELECT candidate.id, candidate.application_date, candidate.status
          FROM msi_v2.teacher_candidates candidate
          WHERE candidate.is_application_received = true
            AND {base_where}
        ), latest_decision AS (
          SELECT DISTINCT ON (decision.candidate_id)
                 decision.candidate_id, decision.decision, decision.created_at
          FROM msi_v2.teacher_candidate_final_decisions decision
          JOIN base_candidates candidate ON candidate.id = decision.candidate_id
          WHERE decision.voided_at IS NULL
          ORDER BY decision.candidate_id, decision.created_at DESC, decision.id DESC
        ), test_demo_participants AS (
          SELECT demo.candidate_id,
                 COALESCE(demo.demo_at, demo.created_at) AS occurred_at
          FROM msi_v2.teacher_candidate_demo_lessons demo
          JOIN base_candidates candidate ON candidate.id = demo.candidate_id
          WHERE demo.voided_at IS NULL
            AND length(btrim(demo.result)) > 0
          UNION ALL
          SELECT test.candidate_id,
                 COALESCE(test.test_at, test.created_at)
          FROM msi_v2.teacher_candidate_subject_tests test
          JOIN base_candidates candidate ON candidate.id = test.candidate_id
          WHERE test.voided_at IS NULL
            AND test.result <> 'not_completed'
            AND length(btrim(test.result)) > 0
        )
        SELECT
          (
            SELECT COUNT(DISTINCT candidate.id)
            FROM base_candidates candidate
            CROSS JOIN bounds
            WHERE candidate.application_date
                  BETWEEN bounds.date_from AND bounds.date_to
          ) AS application_received,
          (
            SELECT COUNT(DISTINCT decision.candidate_id)
            FROM latest_decision decision
            JOIN base_candidates candidate ON candidate.id = decision.candidate_id
            CROSS JOIN bounds
            WHERE candidate.status = 'rejected'
              AND decision.decision = 'rejected'
              AND (decision.created_at AT TIME ZONE 'Asia/Tashkent')::date
                  BETWEEN bounds.date_from AND bounds.date_to
          ) AS rejected,
          (
            SELECT COUNT(DISTINCT history.candidate_id)
            FROM msi_v2.teacher_candidate_stage_history history
            JOIN base_candidates candidate ON candidate.id = history.candidate_id
            CROSS JOIN bounds
            WHERE history.stage = 'responded'
              AND (history.entered_at AT TIME ZONE 'Asia/Tashkent')::date
                  BETWEEN bounds.date_from AND bounds.date_to
          ) AS in_process,
          (
            SELECT COUNT(DISTINCT interview.candidate_id)
            FROM msi_v2.teacher_candidate_interviews interview
            JOIN base_candidates candidate ON candidate.id = interview.candidate_id
            CROSS JOIN bounds
            WHERE interview.voided_at IS NULL
              AND interview.result IN ('passed', 'failed')
              AND (
                COALESCE(interview.interview_at, interview.created_at)
                AT TIME ZONE 'Asia/Tashkent'
              )::date BETWEEN bounds.date_from AND bounds.date_to
          ) AS job_interview,
          (
            SELECT COUNT(DISTINCT participant.candidate_id)
            FROM test_demo_participants participant
            CROSS JOIN bounds
            WHERE (
                participant.occurred_at AT TIME ZONE 'Asia/Tashkent'
              )::date BETWEEN bounds.date_from AND bounds.date_to
          ) AS test_and_demo,
          (
            SELECT COUNT(DISTINCT academy.recruitment_candidate_id)
            FROM msi_v2.academy_teachers academy
            JOIN base_candidates candidate
              ON candidate.id = academy.recruitment_candidate_id
            CROSS JOIN bounds
            WHERE (
                COALESCE(
                  academy.academy_start_date::timestamp
                    AT TIME ZONE 'Asia/Tashkent',
                  academy.created_at
                ) AT TIME ZONE 'Asia/Tashkent'
              )::date BETWEEN bounds.date_from AND bounds.date_to
          ) AS teacher_academy
        """,
        tuple([date_from, date_to, *base_params]),
    ).fetchone()


def _cohort_scope(
    conn: Any,
    *,
    where_sql: str,
    params: list[Any],
) -> Any:
    """Reconcile period applications with the non-trash funnel cohort."""

    return conn.execute(
        f"""
        SELECT
          COUNT(DISTINCT candidate.id) AS applications_received,
          COUNT(DISTINCT candidate.id) FILTER (
            WHERE candidate.status <> 'trash_bin'
          ) AS included_candidates,
          COUNT(DISTINCT candidate.id) FILTER (
            WHERE candidate.status = 'trash_bin'
          ) AS excluded_trash_candidates
        FROM msi_v2.teacher_candidates candidate
        WHERE {where_sql}
        """,
        tuple(params),
    ).fetchone()


def _outcome_reason_rows(
    conn: Any,
    *,
    base_where: str,
    base_params: list[Any],
    date_from: str,
    date_to: str,
) -> list[Any]:
    return conn.execute(
        f"""
        WITH bounds AS (
          SELECT %s::date AS date_from, %s::date AS date_to
        ), base_candidates AS (
          SELECT candidate.id, candidate.status
          FROM msi_v2.teacher_candidates candidate
          WHERE candidate.is_application_received = true
            AND {base_where}
        ), latest_decision AS (
          SELECT DISTINCT ON (decision.candidate_id)
                 decision.candidate_id, decision.decision,
                 decision.rejection_reason, decision.withdrawal_reason,
                 decision.created_at
          FROM msi_v2.teacher_candidate_final_decisions decision
          JOIN base_candidates candidate ON candidate.id = decision.candidate_id
          WHERE decision.voided_at IS NULL
          ORDER BY decision.candidate_id, decision.created_at DESC, decision.id DESC
        ), classified AS (
          SELECT
            decision.candidate_id,
            decision.decision AS outcome,
            CASE decision.decision
              WHEN 'rejected' THEN NULLIF(btrim(decision.rejection_reason), '')
              WHEN 'candidate_withdrew'
                THEN NULLIF(btrim(decision.withdrawal_reason), '')
            END AS reason_value
          FROM latest_decision decision
          JOIN base_candidates candidate ON candidate.id = decision.candidate_id
          CROSS JOIN bounds
          WHERE decision.decision IN ('rejected', 'candidate_withdrew')
            AND candidate.status = decision.decision
            AND (decision.created_at AT TIME ZONE 'Asia/Tashkent')::date
                BETWEEN bounds.date_from AND bounds.date_to
        )
        SELECT
          classified.outcome,
          COALESCE(classified.reason_value, 'unspecified') AS value,
          COALESCE(
            setting.label,
            CASE
              WHEN classified.reason_value IS NULL THEN 'Unspecified'
              ELSE initcap(replace(classified.reason_value, '_', ' '))
            END
          ) AS label,
          COUNT(DISTINCT classified.candidate_id) AS candidates,
          COALESCE(setting.sort_order, 2147483647) AS sort_order
        FROM classified
        LEFT JOIN msi_v2.teacher_recruitment_settings setting
          ON setting.category = CASE classified.outcome
               WHEN 'rejected' THEN 'rejection_reason'
               ELSE 'withdrawal_reason'
             END
         AND setting.value = classified.reason_value
        GROUP BY
          classified.outcome,
          classified.reason_value,
          setting.label,
          setting.sort_order
        ORDER BY classified.outcome, candidates DESC, sort_order, label
        """,
        tuple([date_from, date_to, *base_params]),
    ).fetchall()


def _turnover_rows(
    conn: Any,
    *,
    base_where: str,
    base_params: list[Any],
    date_to: str,
) -> list[Any]:
    return conn.execute(
        f"""
        WITH bounds AS (
          SELECT
            (
              date_trunc('month', %s::date)
              - interval '11 months'
            )::date AS date_from,
            %s::date AS date_to
        ), months AS (
          SELECT bucket::date AS month_start
          FROM bounds,
               generate_series(
                 bounds.date_from,
                 date_trunc('month', bounds.date_to)::date,
                 interval '1 month'
               ) bucket
        ), eligible_teachers AS (
          SELECT teacher.id
          FROM msi_v2.teachers teacher
          JOIN msi_v2.teacher_candidates candidate
            ON candidate.id = teacher.recruitment_candidate_id
          WHERE teacher.recruitment_candidate_id IS NOT NULL
            AND {base_where}
        ), employment_events AS (
          SELECT event.teacher_id, event.event_type,
                 (event.occurred_at AT TIME ZONE 'Asia/Tashkent')::date
                   AS occurred_date
          FROM msi_v2.teacher_employment_events event
          JOIN eligible_teachers teacher ON teacher.id = event.teacher_id
        ), monthly_counts AS (
          SELECT
            months.month_start,
            LEAST(
              (months.month_start + interval '1 month - 1 day')::date,
              bounds.date_to
            ) AS effective_month_end,
            GREATEST(
              COUNT(*) FILTER (
                WHERE event.event_type = 'activated'
                  AND event.occurred_date < months.month_start
              )
              - COUNT(*) FILTER (
                WHERE event.event_type = 'deactivated'
                  AND event.occurred_date < months.month_start
              ),
              0
            ) AS starting_headcount,
            GREATEST(
              COUNT(*) FILTER (
                WHERE event.event_type = 'activated'
                  AND event.occurred_date <= LEAST(
                    (months.month_start + interval '1 month - 1 day')::date,
                    bounds.date_to
                  )
              )
              - COUNT(*) FILTER (
                WHERE event.event_type = 'deactivated'
                  AND event.occurred_date <= LEAST(
                    (months.month_start + interval '1 month - 1 day')::date,
                    bounds.date_to
                  )
              ),
              0
            ) AS ending_headcount,
            COUNT(*) FILTER (
              WHERE event.event_type = 'deactivated'
                AND event.occurred_date BETWEEN months.month_start AND LEAST(
                  (months.month_start + interval '1 month - 1 day')::date,
                  bounds.date_to
                )
            ) AS departures
          FROM months
          CROSS JOIN bounds
          LEFT JOIN employment_events event ON true
          GROUP BY months.month_start, bounds.date_to
        )
        SELECT
          month_start::text AS bucket,
          departures,
          starting_headcount,
          ending_headcount,
          ROUND(
            (starting_headcount + ending_headcount)::numeric / 2.0,
            1
          ) AS average_headcount,
          CASE
            WHEN (starting_headcount + ending_headcount) > 0 THEN ROUND(
              100.0 * departures
              / ((starting_headcount + ending_headcount)::numeric / 2.0),
              1
            )
            ELSE 0
          END AS turnover_rate
        FROM monthly_counts
        ORDER BY month_start
        """,
        tuple([date_to, date_to, *base_params]),
    ).fetchall()


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
    cohort_scope_where, cohort_scope_params = _candidate_filters(
        date_from=date_from,
        date_to=date_to,
        include_trash=True,
        **filter_values,
    )
    base_where, base_params = _candidate_filters(**filter_values)
    event_filter_values = {
        **filter_values,
        "date_from": "",
        "date_to": "",
    }
    event_base_where, event_base_params = _candidate_filters(
        **event_filter_values,
        application_profiles_only=False,
        include_trash=True,
    )

    current_summary = _cohort_summary(conn, where_sql=where_sql, params=params, now=now)
    comparison_summary = _cohort_summary(
        conn,
        where_sql=comparison_where,
        params=comparison_params,
        now=now,
    )
    total_summary = _cohort_summary(
        conn,
        where_sql=base_where,
        params=base_params,
        now=now,
    )
    live_summary = _live_summary(
        conn,
        where_sql=base_where,
        params=base_params,
        now=now,
    )
    event_summary = _event_summary(
        conn,
        base_where=event_base_where,
        base_params=event_base_params,
        date_from=date_from,
        date_to=date_to,
    )
    comparison_event_summary = _event_summary(
        conn,
        base_where=event_base_where,
        base_params=event_base_params,
        date_from=comparison_from,
        date_to=comparison_to,
    )
    total_event_summary = _event_summary(
        conn,
        base_where=event_base_where,
        base_params=event_base_params,
        date_from="1900-01-01",
        date_to="2999-12-31",
    )
    monthly_stage_totals = _monthly_stage_totals(
        conn,
        base_where=event_base_where,
        base_params=event_base_params,
        date_from=date_from,
        date_to=date_to,
    )
    cohort_scope = _cohort_scope(
        conn,
        where_sql=cohort_scope_where,
        params=cohort_scope_params,
    )
    outcome_reasons = _outcome_reason_rows(
        conn,
        base_where=event_base_where,
        base_params=event_base_params,
        date_from=date_from,
        date_to=date_to,
    )
    turnover = _turnover_rows(
        conn,
        base_where=event_base_where,
        base_params=event_base_params,
        date_to=date_to,
    )

    facts_cte = _candidate_facts_cte(where_sql=where_sql)
    journey = conn.execute(
        f"""WITH {facts_cte},
            stages AS (
              SELECT stage.stage_key AS stage,
                     stage.label AS stage_label,
                     stage.color_token,
                     stage.stage_kind,
                     stage.sort_order,
                     {_stage_rank_sql('stage.stage_key')} AS stage_rank
              FROM msi_v2.teacher_recruitment_pipeline_stages stage
              WHERE stage.is_pipeline = true AND stage.is_active = true
            )
            SELECT stages.stage, stages.stage_label, stages.color_token,
                   COUNT(*) FILTER (
                     WHERE (
                       stages.stage_kind = 'system'
                       AND (
                         stages.stage = 'new_candidate'
                         OR candidate_facts.furthest_rank >= stages.stage_rank
                       )
                     ) OR (
                       stages.stage_kind = 'custom'
                       AND EXISTS (
                         SELECT 1
                         FROM msi_v2.teacher_candidate_stage_history custom_history
                         WHERE custom_history.candidate_id = candidate_facts.id
                           AND custom_history.stage = stages.stage
                       )
                     )
                   ) AS candidates
            FROM stages
            CROSS JOIN candidate_facts
            GROUP BY stages.stage, stages.stage_label, stages.color_token,
                     stages.stage_kind, stages.stage_rank, stages.sort_order
            ORDER BY stages.sort_order""",
        tuple([now, *params]),
    ).fetchall()

    outcomes = conn.execute(
        f"""WITH {facts_cte},
            classified AS (
              SELECT CASE
                WHEN active_teacher_id IS NOT NULL THEN 'active_teacher'
                WHEN academy_teacher_id IS NOT NULL THEN 'teacher_academy'
                WHEN latest_decision = 'rejected' THEN 'rejected'
                WHEN latest_decision = 'candidate_withdrew' THEN 'candidate_withdrew'
              END AS outcome
              FROM candidate_facts
            )
            SELECT outcome, COUNT(*) AS candidates
            FROM classified
            WHERE outcome IS NOT NULL
            GROUP BY outcome""",
        tuple([now, *params]),
    ).fetchall()

    trend = conn.execute(
        f"""WITH filtered_candidates AS (
              SELECT candidate.id, candidate.application_date
              FROM msi_v2.teacher_candidates candidate
              WHERE {event_base_where}
            ), first_shortlist AS (
              SELECT candidate.id AS candidate_id, shortlist.entered_at
              FROM filtered_candidates candidate
              JOIN LATERAL (
                SELECT MIN(event.entered_at) AS entered_at
                FROM (
                  SELECT history.entered_at
                  FROM msi_v2.teacher_candidate_stage_history history
                  WHERE history.candidate_id = candidate.id
                    AND history.stage IN (
                      'under_review', 'teacher_academy', 'active_teacher'
                    )
                  UNION ALL
	                  SELECT COALESCE(
	                           academy.academy_start_date::timestamp
	                             AT TIME ZONE 'Asia/Tashkent',
	                           academy.created_at
	                         )
	                  FROM msi_v2.academy_teachers academy
	                  WHERE academy.recruitment_candidate_id = candidate.id
	                    AND academy.promoted_teacher_id IS NULL
	                    AND academy.academy_status NOT IN (
	                      'rejected', 'removed', 'trash_bin'
	                    )
	                  UNION ALL
	                  SELECT COALESCE(teacher.activated_at, teacher.created_at)
	                  FROM msi_v2.teachers teacher
	                  WHERE teacher.recruitment_candidate_id = candidate.id
	                    AND teacher.status = 'active'
                ) event
              ) shortlist ON shortlist.entered_at IS NOT NULL
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
            ), canonical_hires AS (
              SELECT teacher.recruitment_candidate_id AS candidate_id,
	                     COALESCE(teacher.activated_at, teacher.created_at) AS created_at
              FROM msi_v2.teachers teacher
	              JOIN filtered_candidates candidate
	                ON candidate.id = teacher.recruitment_candidate_id
	              WHERE teacher.status = 'active'
            ), events AS (
              SELECT candidate.application_date AS event_date, 'applications'::text AS event_type
              FROM filtered_candidates candidate
              WHERE candidate.application_date IS NOT NULL
              UNION ALL
              SELECT (shortlist.entered_at AT TIME ZONE 'Asia/Tashkent')::date, 'shortlisted'
              FROM first_shortlist shortlist
              UNION ALL
              SELECT (hire.created_at AT TIME ZONE 'Asia/Tashkent')::date, 'hired'
              FROM canonical_hires hire
              UNION ALL
              SELECT (decision.created_at AT TIME ZONE 'Asia/Tashkent')::date, 'rejected'
              FROM latest_decision decision
              WHERE decision.decision = 'rejected'
                AND NOT EXISTS (
                  SELECT 1
                  FROM msi_v2.academy_teachers academy
                  WHERE academy.recruitment_candidate_id = decision.candidate_id
	                    AND academy.promoted_teacher_id IS NULL
	                    AND academy.academy_status NOT IN (
	                      'rejected', 'removed', 'trash_bin'
	                    )
                )
                AND NOT EXISTS (
                  SELECT 1
	                  FROM msi_v2.teachers teacher
	                  WHERE teacher.recruitment_candidate_id = decision.candidate_id
	                    AND teacher.status = 'active'
                )
            )
            SELECT date_trunc(%s, event.event_date::timestamp)::date::text AS bucket,
                   event.event_type,
                   COUNT(*) AS candidates
            FROM events event
            WHERE event.event_date BETWEEN %s::date AND %s::date
            GROUP BY 1, 2
            ORDER BY 1, 2""",
        tuple([*event_base_params, bucket, date_from, date_to]),
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
        f"""WITH {facts_cte}
            SELECT
              COALESCE(source_setting.label, NULLIF(candidate.source, ''), 'Not set') AS source,
              COALESCE(subsource_setting.label, 'Not set') AS subsource,
              COUNT(*) AS candidates,
              COUNT(*) FILTER (WHERE facts.furthest_rank >= 4) AS shortlisted,
              COUNT(*) FILTER (WHERE facts.active_teacher_id IS NOT NULL) AS hired,
              ROUND(
                100.0 * COUNT(*) FILTER (WHERE facts.active_teacher_id IS NOT NULL)
                / NULLIF(COUNT(*), 0),
                1
              ) AS conversion_percentage
            FROM candidate_facts facts
            JOIN msi_v2.teacher_candidates candidate ON candidate.id = facts.id
            LEFT JOIN msi_v2.teacher_recruitment_settings source_setting
              ON source_setting.id = candidate.source_option_id
            LEFT JOIN msi_v2.teacher_recruitment_settings subsource_setting
              ON subsource_setting.id = candidate.subsource_option_id
            GROUP BY
              COALESCE(source_setting.label, NULLIF(candidate.source, ''), 'Not set'),
              COALESCE(subsource_setting.label, 'Not set')
            ORDER BY candidates DESC, source, subsource""",
        tuple([now, *params]),
    ).fetchall()

    stage_time = conn.execute(
        f"""SELECT history.stage, stage_definition.label AS stage_label,
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
            JOIN msi_v2.teacher_recruitment_pipeline_stages stage_definition
              ON stage_definition.stage_key = history.stage
            WHERE {where_sql}
            GROUP BY history.stage, stage_definition.label
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
              AND {base_where}
            ORDER BY task.due_at ASC, task.id ASC
            LIMIT 20""",
        tuple([now, *base_params]),
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
              AND {base_where}
            ORDER BY appointment.starts_at ASC, appointment.id ASC
            LIMIT 20""",
        tuple([now, *base_params]),
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
                   stage_definition.label AS status_label,
                   next_task.title AS next_action
            FROM msi_v2.teacher_candidates candidate
            JOIN msi_v2.teacher_recruitment_pipeline_stages stage_definition
              ON stage_definition.stage_key = candidate.status
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
            WHERE {event_base_where}
              AND (audit.created_at AT TIME ZONE 'Asia/Tashkent')::date
                    BETWEEN %s::date AND %s::date
            ORDER BY audit.created_at DESC, audit.id DESC
            LIMIT 12""",
        tuple([*event_base_params, date_from, date_to]),
    ).fetchall()

    return {
        "current_summary": current_summary,
        "comparison_summary": comparison_summary,
        "total_summary": total_summary,
        "live_summary": live_summary,
        "event_summary": event_summary,
        "comparison_event_summary": comparison_event_summary,
        "total_event_summary": total_event_summary,
        "monthly_stage_totals": monthly_stage_totals,
        "cohort_scope": cohort_scope,
        "outcome_reasons": outcome_reasons,
        "turnover": turnover,
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


__all__ = ["dashboard_rows", "options_rows", "subsource_matches_source"]
