"""PostgreSQL persistence for teacher recruitment."""

from __future__ import annotations

import json
from typing import Any, Iterable


_CANDIDATE_COLUMNS = """
    candidate.id,
    candidate.full_name,
    candidate.phone,
    candidate.telegram_username,
    candidate.subject_id,
    COALESCE(subject.subject_name, '') AS subject,
    candidate.applied_position,
    candidate.application_date::text AS application_date,
    candidate.age,
    candidate.address,
    candidate.source,
    candidate.source_detail,
    candidate.status,
    candidate.english_level,
    candidate.motivation_expectations,
    candidate.interests_hobbies,
    candidate.preferred_schedule,
    candidate.employment_availability,
    candidate.education_background,
    candidate.work_experience,
    candidate.teaching_experience,
    candidate.previous_workplace,
    candidate.expected_salary_uzs,
    candidate.available_start_date::text AS available_start_date,
    candidate.stage_changed_at::text AS stage_changed_at,
    candidate.version,
    candidate.created_at::text AS created_at,
    candidate.updated_at::text AS updated_at,
    stage_history.id AS current_stage_history_id,
    stage_history.entered_at::text AS current_stage_entered_at,
    stage_history.responsible_account_id AS current_stage_responsible_account_id,
    COALESCE(stage_responsible.full_name, stage_responsible.login, '')
        AS current_stage_responsible_name,
    stage_history.comment AS current_stage_comment,
    stage_history.transition_source AS current_stage_transition_source,
    stage_history.sla_target_days AS current_sla_target_days,
    stage_history.sla_due_at::text AS current_sla_due_at,
    COALESCE(decision.decision, '') AS final_decision,
    COALESCE(decision.rejection_reason, '') AS rejection_reason,
    COALESCE(decision.reason_detail, '') AS decision_reason_detail,
    COALESCE(decision.origin_stage, '') AS decision_origin_stage,
    COALESCE(decision.source_evaluation_type, '') AS decision_source_evaluation_type,
    decision.source_evaluation_id AS decision_source_evaluation_id,
    COALESCE(decision_actor.full_name, decision_actor.login, decision.decided_by_login, '')
        AS final_decision_actor,
    decision.follow_up_at::text AS decision_follow_up_at,
    decision.created_at::text AS final_decision_at,
    COALESCE(latest_interview.result, '') AS latest_interview_result,
    latest_interview.interview_at::text AS latest_interview_at,
    task.id AS next_task_id,
    COALESCE(task.title, '') AS next_action,
    task.due_at::text AS next_action_at,
    appointment.id AS next_appointment_id,
    appointment.appointment_type AS next_appointment_type,
    appointment.starts_at::text AS next_appointment_starts_at,
    appointment.ends_at::text AS next_appointment_ends_at,
    appointment.responsible_account_id AS next_appointment_responsible_account_id,
    COALESCE(appointment_responsible.full_name, appointment_responsible.login, '')
        AS next_appointment_responsible_name,
    appointment.appointment_format AS next_appointment_format,
    appointment.location_or_link AS next_appointment_location_or_link,
    appointment.topic AS next_appointment_topic,
    appointment.status AS next_appointment_status,
    appointment.version AS next_appointment_version,
    academy.id AS academy_teacher_id,
    teacher.id AS active_teacher_id
"""


def _candidate_joins() -> str:
    return """
        LEFT JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
        LEFT JOIN LATERAL (
            SELECT history.id, history.entered_at, history.responsible_account_id,
                   history.comment, history.transition_source,
                   history.sla_target_days, history.sla_due_at
            FROM msi_v2.teacher_candidate_stage_history history
            WHERE history.candidate_id = candidate.id AND history.exited_at IS NULL
            ORDER BY history.entered_at DESC, history.id DESC
            LIMIT 1
        ) stage_history ON true
        LEFT JOIN msi_v2.accounts stage_responsible
          ON stage_responsible.id = stage_history.responsible_account_id
        LEFT JOIN LATERAL (
            SELECT d.decision, d.rejection_reason, d.reason_detail,
                   d.origin_stage, d.follow_up_at, d.created_at,
                   d.decided_by_account_id, d.decided_by_login,
                   d.source_evaluation_type, d.source_evaluation_id
            FROM msi_v2.teacher_candidate_final_decisions d
            WHERE d.candidate_id = candidate.id AND d.voided_at IS NULL
            ORDER BY d.created_at DESC, d.id DESC
            LIMIT 1
        ) decision ON true
        LEFT JOIN msi_v2.accounts decision_actor ON decision_actor.id = decision.decided_by_account_id
        LEFT JOIN LATERAL (
            SELECT interview.result, interview.interview_at
            FROM msi_v2.teacher_candidate_interviews interview
            WHERE interview.candidate_id = candidate.id
              AND interview.voided_at IS NULL
            ORDER BY interview.interview_at DESC NULLS LAST, interview.id DESC
            LIMIT 1
        ) latest_interview ON true
        LEFT JOIN LATERAL (
            SELECT t.id, t.title, t.due_at
            FROM msi_v2.teacher_candidate_tasks t
            WHERE t.candidate_id = candidate.id AND t.status = 'pending'
            ORDER BY t.due_at ASC NULLS LAST, t.id ASC
            LIMIT 1
        ) task ON true
        LEFT JOIN LATERAL (
            SELECT a.id, a.appointment_type, a.starts_at, a.ends_at,
                   a.responsible_account_id, a.appointment_format,
                   a.location_or_link, a.topic, a.status, a.version
            FROM msi_v2.teacher_candidate_appointments a
            WHERE a.candidate_id = candidate.id
              AND a.status = 'scheduled'
              AND (
                  (candidate.status = 'job_interview' AND a.appointment_type = 'job_interview')
                  OR (candidate.status = 'test_and_demo' AND a.appointment_type = 'demo_lesson')
                  OR candidate.status NOT IN ('job_interview', 'test_and_demo')
              )
            ORDER BY a.starts_at ASC, a.id ASC
            LIMIT 1
        ) appointment ON true
        LEFT JOIN msi_v2.accounts appointment_responsible
          ON appointment_responsible.id = appointment.responsible_account_id
        LEFT JOIN msi_v2.academy_teachers academy
          ON academy.recruitment_candidate_id = candidate.id
        LEFT JOIN msi_v2.teachers teacher
          ON teacher.recruitment_candidate_id = candidate.id
    """


def _visibility_clause(
    visible_account_id: int | None,
    visible_subject_ids: set[int] | None = None,
    include_decision_queue: bool = False,
) -> tuple[str, list[Any]]:
    if not visible_account_id:
        return "", []
    if visible_subject_ids is not None and not visible_subject_ids:
        return "FALSE", []
    subject_clause = ""
    params: list[Any] = [visible_account_id]
    if visible_subject_ids is not None:
        subject_clause = "AND visibility.subject_id = ANY(%s::bigint[])"
        params.append(sorted(visible_subject_ids))
    assignment_clause = f"""EXISTS (
            SELECT 1
            FROM msi_v2.teacher_candidate_assignments visibility
            WHERE visibility.candidate_id = candidate.id
              AND visibility.assignee_account_id = %s
              AND visibility.status = 'active'
              {subject_clause}
        )"""
    if include_decision_queue:
        return (
            f"""({assignment_clause} OR EXISTS (
                SELECT 1
                FROM msi_v2.teacher_candidate_hire_approvals queue_approval
                WHERE queue_approval.candidate_id = candidate.id
                  AND queue_approval.status IN ('requested', 'approved')
            ))""",
            params,
        )
    return assignment_clause, params


def list_pipeline_rows(
    conn: Any,
    *,
    visible_account_id: int | None = None,
    visible_subject_ids: set[int] | None = None,
    include_decision_queue: bool = False,
    search: str = "",
    position: str = "",
    source: str = "",
    subject_id: int | None = None,
    application_from: str = "",
    application_to: str = "",
    evaluator_account_id: int | None = None,
) -> list[Any]:
    visibility, visibility_params = _visibility_clause(
        visible_account_id,
        visible_subject_ids,
        include_decision_queue,
    )
    clauses: list[str] = []
    params: list[Any] = []
    if visibility:
        clauses.append(visibility)
        params.extend(visibility_params)
    if search:
        clauses.append("candidate.full_name ILIKE %s")
        params.append(f"%{search}%")
    if position:
        clauses.append("candidate.applied_position ILIKE %s")
        params.append(f"%{position}%")
    if source:
        clauses.append("candidate.source = %s")
        params.append(source)
    if subject_id:
        clauses.append("candidate.subject_id = %s")
        params.append(int(subject_id))
    if application_from:
        clauses.append("candidate.application_date >= %s::date")
        params.append(application_from)
    if application_to:
        clauses.append("candidate.application_date <= %s::date")
        params.append(application_to)
    if evaluator_account_id:
        clauses.append(
            """EXISTS (
                SELECT 1 FROM msi_v2.teacher_candidate_assignments evaluator_filter
                WHERE evaluator_filter.candidate_id = candidate.id
                  AND evaluator_filter.assignee_account_id = %s
                  AND evaluator_filter.status = 'active'
            )"""
        )
        params.append(int(evaluator_account_id))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS}
        FROM msi_v2.teacher_candidates candidate
        {_candidate_joins()}
        {where_sql}
        ORDER BY candidate.updated_at DESC, candidate.id DESC
        """,
        tuple(params) if params else None,
    ).fetchall()


def list_candidate_rows(
    conn: Any,
    *,
    visible_account_id: int | None = None,
    visible_subject_ids: set[int] | None = None,
    include_decision_queue: bool = False,
    search: str = "",
    position: str = "",
    stage: str = "",
    source: str = "",
    subject_id: int | None = None,
    application_from: str = "",
    application_to: str = "",
    final_decision: str = "",
    evaluator_account_id: int | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[Any], int]:
    clauses: list[str] = []
    params: list[Any] = []
    visibility, visibility_params = _visibility_clause(
        visible_account_id,
        visible_subject_ids,
        include_decision_queue,
    )
    if visibility:
        clauses.append(visibility)
        params.extend(visibility_params)
    if search:
        clauses.append("candidate.full_name ILIKE %s")
        params.append(f"%{search}%")
    if position:
        clauses.append("candidate.applied_position ILIKE %s")
        params.append(f"%{position}%")
    if stage:
        clauses.append("candidate.status = %s")
        params.append(stage)
    else:
        clauses.append("candidate.status <> 'trash_bin'")
    if source:
        clauses.append("candidate.source = %s")
        params.append(source)
    if subject_id:
        clauses.append("candidate.subject_id = %s")
        params.append(int(subject_id))
    if application_from:
        clauses.append("candidate.application_date >= %s::date")
        params.append(application_from)
    if application_to:
        clauses.append("candidate.application_date <= %s::date")
        params.append(application_to)
    if final_decision:
        clauses.append("COALESCE(decision.decision, '') = %s")
        params.append(final_decision)
    if evaluator_account_id:
        clauses.append(
            """EXISTS (
                SELECT 1 FROM msi_v2.teacher_candidate_assignments evaluator_filter
                WHERE evaluator_filter.candidate_id = candidate.id
                  AND evaluator_filter.assignee_account_id = %s
                  AND evaluator_filter.status = 'active'
            )"""
        )
        params.append(evaluator_account_id)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    base_from = f"""
        FROM msi_v2.teacher_candidates candidate
        {_candidate_joins()}
        {where_sql}
    """
    total_row = conn.execute(
        f"SELECT count(DISTINCT candidate.id) AS total {base_from}",
        tuple(params) if params else None,
    ).fetchone()
    rows = conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS}
        {base_from}
        ORDER BY candidate.updated_at DESC, candidate.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple([*params, limit, offset]),
    ).fetchall()
    return rows, int(total_row["total"] or 0) if total_row else 0


def list_decision_queue_rows(
    conn: Any,
    *,
    account_id: int,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[Any], int]:
    visibility = """
        EXISTS (
            SELECT 1
            FROM msi_v2.teacher_candidate_assignments queue_assignment
            WHERE queue_assignment.candidate_id = candidate.id
              AND queue_assignment.assignee_account_id = %s
              AND queue_assignment.status = 'active'
        )
        OR EXISTS (
            SELECT 1
            FROM msi_v2.teacher_candidate_hire_approvals queue_visibility
            WHERE queue_visibility.candidate_id = candidate.id
              AND queue_visibility.status IN ('requested', 'approved')
        )
    """
    total_row = conn.execute(
        f"""
        SELECT count(*) AS total
        FROM msi_v2.teacher_candidates candidate
        WHERE candidate.status <> 'trash_bin' AND ({visibility})
        """,
        (int(account_id),),
    ).fetchone()
    rows = conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS},
               actionable.id AS actionable_approval_id,
               actionable.requested_outcome AS actionable_requested_outcome,
               actionable.status AS actionable_approval_status,
               actionable.request_note AS actionable_request_note,
               actionable.created_at::text AS actionable_requested_at,
               CASE WHEN actionable.id IS NULL THEN 'assignment' ELSE 'approval_request' END
                   AS access_reason
        FROM msi_v2.teacher_candidates candidate
        {_candidate_joins()}
        LEFT JOIN LATERAL (
            SELECT approval.id, approval.requested_outcome, approval.status,
                   approval.request_note, approval.created_at
            FROM msi_v2.teacher_candidate_hire_approvals approval
            WHERE approval.candidate_id = candidate.id
              AND approval.status IN ('requested', 'approved')
            ORDER BY CASE WHEN approval.status = 'requested' THEN 0 ELSE 1 END,
                     approval.created_at DESC, approval.id DESC
            LIMIT 1
        ) actionable ON true
        WHERE candidate.status <> 'trash_bin' AND ({visibility})
        ORDER BY CASE WHEN actionable.id IS NULL THEN 1 ELSE 0 END,
                 actionable.created_at DESC NULLS LAST,
                 candidate.updated_at DESC,
                 candidate.id DESC
        LIMIT %s OFFSET %s
        """,
        (int(account_id), int(limit), int(offset)),
    ).fetchall()
    return rows, int(total_row["total"] or 0) if total_row else 0


def get_candidate_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS}
        FROM msi_v2.teacher_candidates candidate
        {_candidate_joins()}
        WHERE candidate.id = %s
        LIMIT 1
        """,
        (candidate_id,),
    ).fetchone()


def lock_candidate_decision_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        """
        SELECT candidate.id, candidate.full_name, candidate.phone,
               candidate.telegram_username, candidate.subject_id,
               candidate.applied_position, candidate.status, candidate.version,
               academy.id AS academy_teacher_id,
               teacher.id AS active_teacher_id
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN msi_v2.academy_teachers academy
          ON academy.recruitment_candidate_id = candidate.id
        LEFT JOIN msi_v2.teachers teacher
          ON teacher.recruitment_candidate_id = candidate.id
        WHERE candidate.id = %s
        LIMIT 1
        FOR UPDATE OF candidate
        """,
        (int(candidate_id),),
    ).fetchone()


def candidate_assignment_row(conn: Any, *, candidate_id: int, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT assignment.id, assignment.subject_id
        FROM msi_v2.teacher_candidate_assignments assignment
        WHERE assignment.candidate_id = %s
          AND assignment.assignee_account_id = %s
          AND assignment.status = 'active'
        LIMIT 1
        """,
        (candidate_id, account_id),
    ).fetchone()


def candidate_actionable_approval_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, requested_outcome, status, created_at
        FROM msi_v2.teacher_candidate_hire_approvals
        WHERE candidate_id = %s AND status IN ('requested', 'approved')
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (int(candidate_id),),
    ).fetchone()


def list_document_rows(conn: Any, candidate_id: int, *, include_removed: bool = False) -> list[Any]:
    removed_clause = "" if include_removed else "AND document.removed_at IS NULL"
    return conn.execute(
        f"""
        SELECT document.id, document.candidate_id, document.document_type,
               document.original_file_name, document.object_key, document.mime_type,
               document.size_bytes, document.version, document.replaces_document_id,
               document.removed_at::text AS removed_at,
               document.created_at::text AS created_at,
               COALESCE(account.login, '') AS uploaded_by
        FROM msi_v2.teacher_candidate_documents document
        LEFT JOIN msi_v2.accounts account ON account.id = document.uploaded_by_account_id
        WHERE document.candidate_id = %s {removed_clause}
        ORDER BY document.created_at DESC, document.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def get_document_row(conn: Any, *, candidate_id: int, document_id: int, active_only: bool = True) -> Any:
    active_clause = "AND removed_at IS NULL" if active_only else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, document_type, original_file_name, object_key,
               mime_type, size_bytes, version, replaces_document_id,
               removed_at::text AS removed_at, created_at::text AS created_at
        FROM msi_v2.teacher_candidate_documents
        WHERE id = %s AND candidate_id = %s {active_clause}
        LIMIT 1
        """,
        (document_id, candidate_id),
    ).fetchone()


def list_interview_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT interview.*, interview.interview_at::text AS interview_at_text,
               interview.created_at::text AS created_at_text,
               interview.updated_at::text AS updated_at_text,
               COALESCE(interviewer.login, '') AS interviewer_login
        FROM msi_v2.teacher_candidate_interviews interview
        LEFT JOIN msi_v2.accounts interviewer ON interviewer.id = interview.interviewer_account_id
        WHERE interview.candidate_id = %s
        ORDER BY interview.created_at DESC, interview.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_subject_test_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT test.*, test.test_at::text AS test_at_text,
               test.created_at::text AS created_at_text,
               test.updated_at::text AS updated_at_text,
               COALESCE(subject.subject_name, test.subject_label, '') AS subject,
               COALESCE(evaluator.login, '') AS evaluator_login,
               COALESCE(topics.items, '[]'::jsonb) AS topic_scores
        FROM msi_v2.teacher_candidate_subject_tests test
        LEFT JOIN msi_v2.subjects subject ON subject.id = test.subject_id
        LEFT JOIN msi_v2.accounts evaluator ON evaluator.id = test.evaluator_account_id
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'id', topic.id,
                    'topic', topic.topic,
                    'score', topic.score,
                    'maximum_score', topic.maximum_score,
                    'percentage', round((topic.score / topic.maximum_score) * 100, 1)
                ) ORDER BY topic.id
            ) AS items
            FROM msi_v2.teacher_candidate_subject_test_topics topic
            WHERE topic.subject_test_id = test.id
        ) topics ON true
        WHERE test.candidate_id = %s
        ORDER BY test.created_at DESC, test.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_demo_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT demo.*, demo.demo_at::text AS demo_at_text,
               demo.created_at::text AS created_at_text,
               demo.updated_at::text AS updated_at_text,
               COALESCE(subject.subject_name, demo.subject_label, '') AS subject,
               COALESCE(evaluator.login, '') AS evaluator_login,
               COALESCE(criteria.items, '[]'::jsonb) AS criteria_scores
        FROM msi_v2.teacher_candidate_demo_lessons demo
        LEFT JOIN msi_v2.subjects subject ON subject.id = demo.subject_id
        LEFT JOIN msi_v2.accounts evaluator ON evaluator.id = demo.evaluator_account_id
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'id', criterion.id,
                    'criterion', criterion.criterion,
                    'score', criterion.score,
                    'maximum_score', criterion.maximum_score
                ) ORDER BY criterion.id
            ) AS items
            FROM msi_v2.teacher_candidate_demo_criteria criterion
            WHERE criterion.demo_lesson_id = demo.id
        ) criteria ON true
        WHERE demo.candidate_id = %s
        ORDER BY demo.created_at DESC, demo.id DESC
        """,
        (candidate_id,),
    ).fetchall()


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
        appointment.created_at::text AS created_at,
        appointment.updated_at::text AS updated_at,
        candidate.full_name AS candidate_name,
        candidate.status AS candidate_status,
        candidate.subject_id,
        COALESCE(subject.subject_name, '') AS subject,
        COALESCE(responsible.full_name, responsible.login, '') AS responsible_name,
        responsible.role AS responsible_role
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
        clauses.append("appointment.status = %s")
        params.append(status)
    if responsible_account_id:
        clauses.append("appointment.responsible_account_id = %s")
        params.append(int(responsible_account_id))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    base_sql = f"""
        FROM msi_v2.teacher_candidate_appointments appointment
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
        LEFT JOIN msi_v2.accounts responsible ON responsible.id = appointment.responsible_account_id
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
          AND appointment.status = 'scheduled'
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
            int(candidate_id), values["appointment_type"], values["starts_at"], values["ends_at"],
            values.get("responsible_account_id"), values.get("appointment_format", ""),
            values.get("location_or_link", ""), values.get("topic", ""), values.get("note", ""),
            actor_account_id, actor_account_id, now, now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def scheduled_appointment_for_type(
    conn: Any,
    *,
    candidate_id: int,
    appointment_type: str,
) -> Any:
    return conn.execute(
        """
        SELECT id, version, starts_at::text AS starts_at
        FROM msi_v2.teacher_candidate_appointments
        WHERE candidate_id = %s AND appointment_type = %s AND status = 'scheduled'
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
            values["starts_at"], values["ends_at"], values.get("responsible_account_id"),
            values.get("appointment_format", ""), values.get("location_or_link", ""),
            values.get("topic", ""), values.get("note", ""), actor_account_id, now,
            int(appointment_id), int(candidate_id), int(expected_version),
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
        WHERE id = %s AND candidate_id = %s AND status = 'scheduled' AND version = %s
        RETURNING id, version
        """,
        (
            status, status, reason, status, now, status, now, status, now,
            actor_account_id, now, int(appointment_id), int(candidate_id), int(expected_version),
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
        WHERE id = %s AND candidate_id = %s AND status = 'scheduled'
        RETURNING id, version
        """,
        (now, actor_account_id, now, int(appointment_id), int(candidate_id)),
    ).fetchone()


def cancel_scheduled_appointments(
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
        WHERE candidate_id = %s AND status = 'scheduled'
        RETURNING id
        """,
        (reason, now, actor_account_id, now, int(candidate_id)),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def void_evaluation(
    conn: Any,
    *,
    table: str,
    candidate_id: int,
    attempt_id: int,
    actor_account_id: int | None,
    reason: str,
    now: str,
) -> Any:
    allowed_tables = {
        "teacher_candidate_interviews",
        "teacher_candidate_subject_tests",
        "teacher_candidate_demo_lessons",
    }
    if table not in allowed_tables:
        return None
    return conn.execute(
        f"""
        UPDATE msi_v2.{table}
        SET voided_at = %s::timestamptz,
            voided_by_account_id = %s,
            void_reason = %s,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s AND candidate_id = %s AND voided_at IS NULL
        RETURNING id
        """,
        (now, actor_account_id, reason, actor_account_id, now, attempt_id, candidate_id),
    ).fetchone()


def get_evaluation_row(
    conn: Any,
    *,
    table: str,
    candidate_id: int,
    attempt_id: int,
    for_update: bool = False,
) -> Any:
    allowed_tables = {
        "teacher_candidate_interviews",
        "teacher_candidate_subject_tests",
        "teacher_candidate_demo_lessons",
    }
    if table not in allowed_tables:
        return None
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, result, voided_at
        FROM msi_v2.{table}
        WHERE id = %s AND candidate_id = %s
        LIMIT 1 {lock}
        """,
        (int(attempt_id), int(candidate_id)),
    ).fetchone()


def get_system_decision_for_evaluation(
    conn: Any,
    *,
    candidate_id: int,
    evaluation_type: str,
    attempt_id: int,
    for_update: bool = False,
) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, decision, origin_stage, created_at, voided_at
        FROM msi_v2.teacher_candidate_final_decisions
        WHERE candidate_id = %s
          AND is_system_generated = true
          AND source_evaluation_type = %s
          AND source_evaluation_id = %s
          AND voided_at IS NULL
        LIMIT 1 {lock}
        """,
        (int(candidate_id), evaluation_type, int(attempt_id)),
    ).fetchone()


def latest_active_final_decision(conn: Any, candidate_id: int, *, for_update: bool = False) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, decision, created_at
        FROM msi_v2.teacher_candidate_final_decisions
        WHERE candidate_id = %s AND voided_at IS NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1 {lock}
        """,
        (int(candidate_id),),
    ).fetchone()


def void_system_final_decision(
    conn: Any,
    *,
    decision_id: int,
    actor_account_id: int | None,
    reason: str,
    now: str,
) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_final_decisions
        SET voided_at = %s::timestamptz, voided_by_account_id = %s,
            void_reason = %s
        WHERE id = %s AND is_system_generated = true AND voided_at IS NULL
        """,
        (now, actor_account_id, reason, int(decision_id)),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def responsible_account_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, role, status, COALESCE(NULLIF(full_name, ''), login) AS name
        FROM msi_v2.accounts WHERE id = %s LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def hod_account_has_subject_scope(conn: Any, *, account_id: int, subject_id: int) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM msi_v2.staff_subject_scopes
        WHERE account_id = %s AND subject_id = %s
          AND scope_type = 'head_of_department' AND status = 'active'
        LIMIT 1
        """,
        (int(account_id), int(subject_id)),
    ).fetchone()
    return bool(row)


def ensure_candidate_assignment(
    conn: Any,
    *,
    candidate_id: int,
    assignee_account_id: int,
    subject_id: int | None,
    actor_account_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_assignments (
            candidate_id, assignee_account_id, assignment_type, subject_id,
            status, assigned_by_account_id, created_at, updated_at
        ) VALUES (%s, %s, 'academic_evaluator', %s, 'active', %s, %s::timestamptz, %s::timestamptz)
        ON CONFLICT (candidate_id, assignee_account_id, assignment_type)
            WHERE status = 'active'
        DO UPDATE SET subject_id = COALESCE(excluded.subject_id, teacher_candidate_assignments.subject_id),
                      assigned_by_account_id = excluded.assigned_by_account_id,
                      updated_at = excluded.updated_at
        """,
        (int(candidate_id), int(assignee_account_id), subject_id, actor_account_id, now, now),
    )


def list_task_rows(
    conn: Any,
    *,
    candidate_id: int | None = None,
    visible_account_id: int | None = None,
    visible_subject_ids: set[int] | None = None,
    include_decision_queue: bool = False,
) -> list[Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if candidate_id:
        clauses.append("task.candidate_id = %s")
        params.append(candidate_id)
    else:
        clauses.append("candidate.status <> 'trash_bin'")
    if visible_account_id:
        if visible_subject_ids is not None and not visible_subject_ids:
            clauses.append("FALSE")
        else:
            subject_clause = ""
            if visible_subject_ids is not None:
                subject_clause = "AND visibility.subject_id = ANY(%s::bigint[])"
            queue_clause = ""
            if include_decision_queue:
                queue_clause = """
                    OR EXISTS (
                        SELECT 1
                        FROM msi_v2.teacher_candidate_hire_approvals queue_approval
                        WHERE queue_approval.candidate_id = task.candidate_id
                          AND queue_approval.status IN ('requested', 'approved')
                    )
                """
            clauses.append(
                f"""(EXISTS (
                    SELECT 1 FROM msi_v2.teacher_candidate_assignments visibility
                    WHERE visibility.candidate_id = task.candidate_id
                      AND visibility.assignee_account_id = %s
                      AND visibility.status = 'active'
                      {subject_clause}
                ){queue_clause})"""
            )
            params.append(visible_account_id)
            if visible_subject_ids is not None:
                params.append(sorted(visible_subject_ids))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return conn.execute(
        f"""
        SELECT task.id, task.candidate_id, task.title, task.due_at::text AS due_at,
               task.responsible_account_id, task.status, task.note,
               task.task_key, task.task_origin, task.stage_history_id,
               task.completed_at::text AS completed_at,
               task.cancelled_at::text AS cancelled_at,
               task.created_at::text AS created_at,
               task.updated_at::text AS updated_at,
               candidate.full_name AS candidate_name,
               COALESCE(account.login, account.full_name, '') AS responsible_name
        FROM msi_v2.teacher_candidate_tasks task
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = task.candidate_id
        LEFT JOIN msi_v2.accounts account ON account.id = task.responsible_account_id
        {where_sql}
        ORDER BY
            CASE task.status WHEN 'pending' THEN 0 WHEN 'completed' THEN 1 ELSE 2 END,
            task.due_at ASC NULLS LAST, task.id DESC
        """,
        tuple(params) if params else None,
    ).fetchall()


def list_note_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT note.id, note.candidate_id, note.body, note.author_account_id,
               COALESCE(account.login, note.author_login, '') AS author,
               note.created_at::text AS created_at
        FROM msi_v2.teacher_candidate_notes note
        LEFT JOIN msi_v2.accounts account ON account.id = note.author_account_id
        WHERE note.candidate_id = %s
        ORDER BY note.created_at DESC, note.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_assignment_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT assignment.id, assignment.assignee_account_id, assignment.subject_id,
               assignment.status, assignment.created_at::text AS created_at,
               COALESCE(account.full_name, account.login, '') AS assignee_name,
               account.role AS assignee_role,
               COALESCE(subject.subject_name, '') AS subject
        FROM msi_v2.teacher_candidate_assignments assignment
        JOIN msi_v2.accounts account ON account.id = assignment.assignee_account_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = assignment.subject_id
        WHERE assignment.candidate_id = %s AND assignment.status = 'active'
        ORDER BY lower(COALESCE(account.full_name, account.login)), assignment.id
        """,
        (candidate_id,),
    ).fetchall()


def list_approval_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT approval.id, approval.candidate_id, approval.requested_outcome,
               approval.status, approval.request_note, approval.review_comment,
               approval.requested_by_account_id, approval.reviewed_by_account_id,
               approval.reviewed_at::text AS reviewed_at,
               approval.consumed_at::text AS consumed_at,
               approval.created_at::text AS created_at,
               approval.updated_at::text AS updated_at,
               COALESCE(requester.login, '') AS requested_by,
               COALESCE(reviewer.login, '') AS reviewed_by
        FROM msi_v2.teacher_candidate_hire_approvals approval
        LEFT JOIN msi_v2.accounts requester ON requester.id = approval.requested_by_account_id
        LEFT JOIN msi_v2.accounts reviewer ON reviewer.id = approval.reviewed_by_account_id
        WHERE approval.candidate_id = %s
        ORDER BY approval.created_at DESC, approval.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_decision_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT decision.id, decision.candidate_id, decision.decision,
               decision.rejection_reason, decision.reason_detail,
               decision.origin_stage,
               decision.is_system_generated, decision.source_evaluation_type,
               decision.source_evaluation_id,
               decision.voided_at::text AS voided_at,
               decision.follow_up_at::text AS follow_up_at,
               decision.approval_id, decision.decided_by_account_id,
               COALESCE(account.full_name, account.login, decision.decided_by_login, '') AS decided_by,
               decision.created_at::text AS created_at
        FROM msi_v2.teacher_candidate_final_decisions decision
        LEFT JOIN msi_v2.accounts account ON account.id = decision.decided_by_account_id
        WHERE decision.candidate_id = %s
        ORDER BY decision.created_at DESC, decision.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_activity_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT audit.id, audit.event_type, audit.detail_json,
               audit.created_at::text AS created_at,
               COALESCE(account.login, staff.login, '') AS actor
        FROM msi_v2.audit_events audit
        LEFT JOIN msi_v2.accounts account ON account.id = audit.actor_account_id
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = audit.actor_staff_id
        WHERE audit.entity_type = 'teacher_candidate' AND audit.entity_id = %s
        ORDER BY audit.created_at DESC, audit.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_stage_history_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT history.id, history.candidate_id, history.stage,
               history.entered_at::text AS entered_at,
               history.exited_at::text AS exited_at,
               history.responsible_account_id,
               COALESCE(account.full_name, account.login, '') AS responsible_name,
               history.comment, history.transition_source,
               history.sla_target_days,
               history.sla_due_at::text AS sla_due_at
        FROM msi_v2.teacher_candidate_stage_history history
        LEFT JOIN msi_v2.accounts account ON account.id = history.responsible_account_id
        WHERE history.candidate_id = %s
        ORDER BY history.entered_at DESC, history.id DESC
        """,
        (int(candidate_id),),
    ).fetchall()


def insert_candidate(conn: Any, *, values: dict[str, Any], now: str, actor_account_id: int | None) -> int:
    row = conn.execute(
        """
        WITH inserted_candidate AS (
            INSERT INTO msi_v2.teacher_candidates (
                full_name, phone, telegram_username, applied_position, subject_id,
                application_date, source, source_detail, status, stage_changed_at,
                version, updated_by_account_id, created_at, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, NULLIF(%s, '')::date, %s, %s,
                'new_candidate', %s::timestamptz, 1, %s,
                %s::timestamptz, %s::timestamptz
            )
            RETURNING id
        ), inserted_history AS (
            INSERT INTO msi_v2.teacher_candidate_stage_history (
                candidate_id, stage, entered_at, responsible_account_id,
                comment, transition_source, sla_target_days, sla_due_at
            )
            SELECT candidate.id, 'new_candidate', %s::timestamptz, %s,
                   'Candidate created.', 'manual', rule.target_days,
                   CASE WHEN rule.target_days IS NULL THEN NULL
                        ELSE %s::timestamptz + make_interval(days => rule.target_days)
                   END
            FROM inserted_candidate candidate
            LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
              ON rule.stage = 'new_candidate' AND rule.is_active = true
            RETURNING id
        )
        SELECT candidate.id
        FROM inserted_candidate candidate
        JOIN inserted_history history ON true
        """,
        (
            values["full_name"], values.get("phone", ""), values.get("telegram_username", ""),
            values.get("applied_position", ""), values.get("subject_id"), values.get("application_date", ""),
            values.get("source", ""), values.get("source_detail", ""), now,
            actor_account_id, now, now, now, actor_account_id, now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_candidate(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
    expected_version: int | None = None,
) -> bool:
    allowed = {
        "full_name", "phone", "telegram_username", "applied_position", "subject_id", "application_date",
        "age", "address", "source", "source_detail", "english_level", "motivation_expectations",
        "interests_hobbies", "preferred_schedule", "employment_availability",
        "education_background",
        "work_experience", "teaching_experience", "previous_workplace",
        "expected_salary_uzs", "available_start_date",
    }
    assignments: list[str] = []
    params: list[Any] = []
    for key, value in values.items():
        if key not in allowed:
            continue
        if key in {"application_date", "available_start_date"}:
            assignments.append(f"{key} = NULLIF(%s, '')::date")
        else:
            assignments.append(f"{key} = %s")
        params.append(value)
    if not assignments:
        return True
    assignments.extend(
        ["updated_by_account_id = %s", "updated_at = %s::timestamptz", "version = version + 1"]
    )
    version_clause = " AND version = %s" if expected_version else ""
    params.extend([actor_account_id, now, candidate_id])
    if expected_version:
        params.append(int(expected_version))
    cursor = conn.execute(
        f"UPDATE msi_v2.teacher_candidates SET {', '.join(assignments)} WHERE id = %s{version_clause}",
        tuple(params),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def update_candidate_stage(
    conn: Any,
    *,
    candidate_id: int,
    stage: str,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
    comment: str = "",
    transition_source: str = "manual",
) -> Any:
    return conn.execute(
        """
        WITH current_candidate AS (
            SELECT id, status, version
            FROM msi_v2.teacher_candidates
            WHERE id = %s
            FOR UPDATE
        ), updated_candidate AS (
            UPDATE msi_v2.teacher_candidates candidate
            SET status = %s, stage_changed_at = %s::timestamptz,
                updated_at = %s::timestamptz, updated_by_account_id = %s,
                version = candidate.version + 1
            FROM current_candidate current
            WHERE candidate.id = current.id AND current.version = %s
            RETURNING candidate.id, candidate.status, candidate.version
        ), closed_history AS (
            UPDATE msi_v2.teacher_candidate_stage_history history
            SET exited_at = %s::timestamptz
            FROM updated_candidate updated
            WHERE history.candidate_id = updated.id AND history.exited_at IS NULL
            RETURNING history.id
        ), new_history AS (
            INSERT INTO msi_v2.teacher_candidate_stage_history (
                candidate_id, stage, entered_at, responsible_account_id,
                comment, transition_source, sla_target_days, sla_due_at
            )
            SELECT updated.id, %s, %s::timestamptz, %s, %s, %s,
                   rule.target_days,
                   CASE WHEN rule.target_days IS NULL THEN NULL
                        ELSE %s::timestamptz + make_interval(days => rule.target_days)
                   END
            FROM updated_candidate updated
            CROSS JOIN (SELECT count(*) FROM closed_history) closed
            LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
              ON rule.stage = %s AND rule.is_active = true
            RETURNING id
        )
        SELECT updated.id, updated.status, updated.version,
               history.id AS current_stage_history_id
        FROM updated_candidate updated
        JOIN new_history history ON true
        """,
        (
            int(candidate_id), stage, now, now, actor_account_id,
            int(expected_version), now, stage, now, actor_account_id,
            comment, transition_source, now, stage,
        ),
    ).fetchone()


def touch_candidate(conn: Any, *, candidate_id: int, actor_account_id: int | None, now: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidates
        SET updated_at = %s::timestamptz, updated_by_account_id = %s, version = version + 1
        WHERE id = %s
        """,
        (now, actor_account_id, candidate_id),
    )


def insert_note(conn: Any, *, candidate_id: int, body: str, actor_account_id: int | None, actor_login: str, now: str) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_notes (
            candidate_id, body, author_account_id, author_login, created_at
        ) VALUES (%s, %s, %s, %s, %s::timestamptz)
        RETURNING id
        """,
        (candidate_id, body, actor_account_id, actor_login, now),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_document(conn: Any, *, values: dict[str, Any], actor_account_id: int | None, now: str) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_documents (
            candidate_id, document_type, original_file_name, object_key,
            mime_type, size_bytes, version, replaces_document_id,
            uploaded_by_account_id, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz)
        RETURNING id
        """,
        (
            values["candidate_id"], values["document_type"], values["original_file_name"],
            values["object_key"], values["mime_type"], values["size_bytes"],
            values.get("version", 1), values.get("replaces_document_id"), actor_account_id, now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def remove_document(conn: Any, *, document_id: int, actor_account_id: int | None, now: str) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_documents
        SET removed_at = %s::timestamptz, removed_by_account_id = %s
        WHERE id = %s AND removed_at IS NULL
        """,
        (now, actor_account_id, document_id),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def insert_interview(conn: Any, *, candidate_id: int, values: dict[str, Any], actor_account_id: int | None, now: str) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_interviews (
            candidate_id, appointment_id, interview_at, interviewer_account_id, interview_format,
            notes, english_level, strengths, concerns, hr_recommendation, result,
            cefr_level, overall_score, communication_score, recommendation_code,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id, values.get("appointment_id"), values.get("interview_at", ""), values.get("interviewer_account_id"),
            values.get("interview_format", ""), values.get("notes", ""),
            values.get("english_level", ""), values.get("strengths", ""), values.get("concerns", ""),
            values.get("hr_recommendation", ""), values["result"],
            values.get("cefr_level", ""), values.get("overall_score"),
            values.get("communication_score"), values.get("recommendation_code", ""),
            actor_account_id,
            actor_account_id, now, now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_subject_test(conn: Any, *, candidate_id: int, values: dict[str, Any], actor_account_id: int | None, now: str) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_subject_tests (
            candidate_id, test_at, subject_id, subject_label, evaluator_account_id,
            score, maximum_score, paper, notes, result, created_by_account_id,
            updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id, values.get("test_at", ""), values.get("subject_id"),
            values.get("subject_label", ""), values.get("evaluator_account_id"),
            values.get("score"), values.get("maximum_score"), values.get("paper", ""),
            values.get("notes", ""),
            values["result"], actor_account_id, actor_account_id, now, now,
        ),
    ).fetchone()
    attempt_id = int(row["id"]) if row else 0
    topic_scores = list(values.get("topic_scores") or [])
    if attempt_id and topic_scores:
        conn.executemany(
            """
            INSERT INTO msi_v2.teacher_candidate_subject_test_topics (
                subject_test_id, topic, score, maximum_score
            ) VALUES (%s, %s, %s, %s)
            """,
            [
                (
                    attempt_id,
                    item.get("topic", ""),
                    item.get("score"),
                    item.get("maximum_score"),
                )
                for item in topic_scores
            ],
        )
    return attempt_id


def insert_demo(conn: Any, *, candidate_id: int, values: dict[str, Any], actor_account_id: int | None, now: str) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_demo_lessons (
            candidate_id, appointment_id, demo_at, subject_id, subject_label, topic,
            evaluator_account_id, overview, strengths, areas_for_improvement,
            score, result, recommendation, created_by_account_id,
            updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id, values.get("appointment_id"), values.get("demo_at", ""), values.get("subject_id"),
            values.get("subject_label", ""), values.get("topic", ""),
            values.get("evaluator_account_id"), values.get("overview", ""),
            values.get("strengths", ""), values.get("areas_for_improvement", ""),
            values.get("score"), values["result"], values.get("recommendation", ""),
            actor_account_id, actor_account_id, now, now,
        ),
    ).fetchone()
    attempt_id = int(row["id"]) if row else 0
    criteria_scores = list(values.get("criteria_scores") or [])
    if attempt_id and criteria_scores:
        conn.executemany(
            """
            INSERT INTO msi_v2.teacher_candidate_demo_criteria (
                demo_lesson_id, criterion, score, maximum_score
            ) VALUES (%s, %s, %s, %s)
            """,
            [
                (
                    attempt_id,
                    item.get("criterion", ""),
                    item.get("score"),
                    item.get("maximum_score", 10),
                )
                for item in criteria_scores
            ],
        )
    return attempt_id


def insert_task(conn: Any, *, candidate_id: int, values: dict[str, Any], actor_account_id: int | None, now: str) -> int:
    status = values.get("status", "pending")
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_tasks (
            candidate_id, title, due_at, responsible_account_id, status, note,
            completed_at, cancelled_at, created_by_account_id,
            updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            CASE WHEN %s = 'completed' THEN %s::timestamptz END,
            CASE WHEN %s = 'cancelled' THEN %s::timestamptz END,
            %s, %s, %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id, values["title"], values.get("due_at", ""),
            values.get("responsible_account_id"), status, values.get("note", ""),
            status, now, status, now, actor_account_id, actor_account_id, now, now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_task(conn: Any, *, candidate_id: int, task_id: int, values: dict[str, Any], actor_account_id: int | None, now: str) -> bool:
    status = values.get("status", "pending")
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_tasks
        SET title = %s, due_at = NULLIF(%s, '')::timestamptz,
            responsible_account_id = %s, status = %s, note = %s,
            completed_at = CASE WHEN %s = 'completed' THEN COALESCE(completed_at, %s::timestamptz) ELSE NULL END,
            cancelled_at = CASE WHEN %s = 'cancelled' THEN COALESCE(cancelled_at, %s::timestamptz) ELSE NULL END,
            updated_by_account_id = %s, updated_at = %s::timestamptz
        WHERE id = %s AND candidate_id = %s
        """,
        (
            values["title"], values.get("due_at", ""), values.get("responsible_account_id"),
            status, values.get("note", ""), status, now, status, now,
            actor_account_id, now, task_id, candidate_id,
        ),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def candidate_automation_state_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        """
        SELECT candidate.id, candidate.status, candidate.updated_by_account_id,
               history.id AS stage_history_id,
               history.sla_due_at::text AS sla_due_at,
               history.responsible_account_id AS stage_responsible_account_id,
               interview.result AS interview_result,
               subject_test.result AS subject_test_result,
               demo.result AS demo_result,
               interview_appointment.id AS interview_appointment_id,
               interview_appointment.ends_at::text AS interview_appointment_ends_at,
               demo_appointment.id AS demo_appointment_id,
               demo_appointment.ends_at::text AS demo_appointment_ends_at,
               COALESCE(documents.required_count, 0) AS required_document_count,
               approval.id AS actionable_approval_id
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN LATERAL (
            SELECT item.id, item.sla_due_at, item.responsible_account_id
            FROM msi_v2.teacher_candidate_stage_history item
            WHERE item.candidate_id = candidate.id AND item.exited_at IS NULL
            ORDER BY item.entered_at DESC, item.id DESC
            LIMIT 1
        ) history ON true
        LEFT JOIN LATERAL (
            SELECT item.result
            FROM msi_v2.teacher_candidate_interviews item
            WHERE item.candidate_id = candidate.id AND item.voided_at IS NULL
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) interview ON true
        LEFT JOIN LATERAL (
            SELECT item.result
            FROM msi_v2.teacher_candidate_subject_tests item
            WHERE item.candidate_id = candidate.id AND item.voided_at IS NULL
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) subject_test ON true
        LEFT JOIN LATERAL (
            SELECT item.result
            FROM msi_v2.teacher_candidate_demo_lessons item
            WHERE item.candidate_id = candidate.id AND item.voided_at IS NULL
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) demo ON true
        LEFT JOIN LATERAL (
            SELECT item.id, item.ends_at
            FROM msi_v2.teacher_candidate_appointments item
            WHERE item.candidate_id = candidate.id
              AND item.appointment_type = 'job_interview'
              AND item.status = 'scheduled'
            ORDER BY item.starts_at, item.id
            LIMIT 1
        ) interview_appointment ON true
        LEFT JOIN LATERAL (
            SELECT item.id, item.ends_at
            FROM msi_v2.teacher_candidate_appointments item
            WHERE item.candidate_id = candidate.id
              AND item.appointment_type = 'demo_lesson'
              AND item.status = 'scheduled'
            ORDER BY item.starts_at, item.id
            LIMIT 1
        ) demo_appointment ON true
        LEFT JOIN LATERAL (
            SELECT count(DISTINCT item.document_type) AS required_count
            FROM msi_v2.teacher_candidate_documents item
            WHERE item.candidate_id = candidate.id
              AND item.removed_at IS NULL
              AND item.document_type IN ('cv', 'id_passport', 'diploma')
        ) documents ON true
        LEFT JOIN LATERAL (
            SELECT item.id
            FROM msi_v2.teacher_candidate_hire_approvals item
            WHERE item.candidate_id = candidate.id
              AND item.status IN ('requested', 'approved')
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) approval ON true
        WHERE candidate.id = %s
        LIMIT 1
        """,
        (int(candidate_id),),
    ).fetchone()


def replace_system_tasks(
    conn: Any,
    *,
    candidate_id: int,
    stage: str,
    stage_history_id: int,
    desired_tasks: list[dict[str, Any]],
    actor_account_id: int | None,
    now: str,
) -> None:
    desired_keys = [str(item["task_key"]) for item in desired_tasks]
    terminal = stage in {
        "teacher_academy", "active_teacher",
        "rejected", "candidate_withdrew", "trash_bin",
    }
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_tasks
        SET status = CASE WHEN %s THEN 'cancelled' ELSE 'completed' END,
            completed_at = CASE WHEN %s THEN NULL ELSE %s::timestamptz END,
            cancelled_at = CASE WHEN %s THEN %s::timestamptz ELSE NULL END,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE candidate_id = %s
          AND task_origin = 'system'
          AND status = 'pending'
          AND NOT (task_key = ANY(%s::text[]) AND stage_history_id = %s)
        """,
        (
            terminal, terminal, now, terminal, now,
            actor_account_id, now, int(candidate_id), desired_keys,
            int(stage_history_id),
        ),
    )
    if not desired_tasks:
        return
    conn.executemany(
        """
        INSERT INTO msi_v2.teacher_candidate_tasks (
            candidate_id, title, due_at, responsible_account_id,
            status, note, task_key, task_origin, stage_history_id,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s,
            'pending', '', %s, 'system', %s,
            %s, %s, %s::timestamptz, %s::timestamptz
        )
        ON CONFLICT (candidate_id, task_key, stage_history_id)
            WHERE task_origin = 'system' AND status = 'pending'
        DO UPDATE SET
            title = excluded.title,
            due_at = excluded.due_at,
            responsible_account_id = excluded.responsible_account_id,
            updated_by_account_id = excluded.updated_by_account_id,
            updated_at = excluded.updated_at
        """,
        [
            (
                int(candidate_id), item["title"], item.get("due_at", ""),
                item.get("responsible_account_id"), item["task_key"],
                int(stage_history_id), actor_account_id, actor_account_id,
                now, now,
            )
            for item in desired_tasks
        ],
    )


def replace_assignments(
    conn: Any,
    *,
    candidate_id: int,
    assignee_account_ids: Iterable[int],
    subject_id: int | None,
    actor_account_id: int | None,
    now: str,
) -> None:
    wanted = {int(value) for value in assignee_account_ids if int(value) > 0}
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_assignments
        SET status = 'removed', updated_at = %s::timestamptz
        WHERE candidate_id = %s AND assignment_type = 'academic_evaluator'
          AND status = 'active' AND NOT (assignee_account_id = ANY(%s::bigint[]))
        """,
        (now, candidate_id, list(wanted) or [0]),
    )
    for assignee_id in sorted(wanted):
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_candidate_assignments (
                candidate_id, assignee_account_id, assignment_type, subject_id,
                status, assigned_by_account_id, created_at, updated_at
            ) VALUES (%s, %s, 'academic_evaluator', %s, 'active', %s, %s::timestamptz, %s::timestamptz)
            ON CONFLICT (candidate_id, assignee_account_id, assignment_type)
                WHERE status = 'active'
            DO UPDATE SET subject_id = excluded.subject_id,
                          assigned_by_account_id = excluded.assigned_by_account_id,
                          updated_at = excluded.updated_at
            """,
            (candidate_id, assignee_id, subject_id, actor_account_id, now, now),
        )


def list_valid_evaluator_accounts(conn: Any, account_ids: Iterable[int]) -> set[int]:
    values = sorted({int(value) for value in account_ids if int(value) > 0})
    if not values:
        return set()
    rows = conn.execute(
        """
        SELECT id FROM msi_v2.accounts
        WHERE id = ANY(%s::bigint[]) AND role IN ('academic_director', 'head_of_department')
          AND status = 'active'
        """,
        (values,),
    ).fetchall()
    return {int(row["id"]) for row in rows}


def insert_approval_request(conn: Any, *, candidate_id: int, outcome: str, note: str, actor_account_id: int | None, now: str) -> int:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = 'revoked', updated_at = %s::timestamptz
        WHERE candidate_id = %s AND requested_outcome = %s
          AND status IN ('requested', 'approved')
        """,
        (now, candidate_id, outcome),
    )
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_hire_approvals (
            candidate_id, requested_outcome, status, request_note,
            requested_by_account_id, created_at, updated_at
        ) VALUES (%s, %s, 'requested', %s, %s, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (candidate_id, outcome, note, actor_account_id, now, now),
    ).fetchone()
    return int(row["id"]) if row else 0


def get_approval_row(conn: Any, *, candidate_id: int, approval_id: int, for_update: bool = False) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, requested_outcome, status,
               requested_by_account_id, reviewed_by_account_id
        FROM msi_v2.teacher_candidate_hire_approvals
        WHERE id = %s AND candidate_id = %s
        LIMIT 1 {lock}
        """,
        (approval_id, candidate_id),
    ).fetchone()


def get_approval_by_id(conn: Any, *, approval_id: int, for_update: bool = False) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, requested_outcome, status,
               requested_by_account_id, reviewed_by_account_id
        FROM msi_v2.teacher_candidate_hire_approvals
        WHERE id = %s
        LIMIT 1 {lock}
        """,
        (int(approval_id),),
    ).fetchone()


def review_approval(conn: Any, *, candidate_id: int, approval_id: int, status: str, comment: str, actor_account_id: int | None, now: str) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = %s, review_comment = %s, reviewed_by_account_id = %s,
            reviewed_at = %s::timestamptz, updated_at = %s::timestamptz
        WHERE id = %s AND candidate_id = %s AND status = 'requested'
        """,
        (status, comment, actor_account_id, now, now, approval_id, candidate_id),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def final_decision_for_approval(conn: Any, *, candidate_id: int, approval_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, decision
        FROM msi_v2.teacher_candidate_final_decisions
        WHERE candidate_id = %s AND approval_id = %s AND voided_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(candidate_id), int(approval_id)),
    ).fetchone()


def revoke_open_approvals(
    conn: Any,
    *,
    candidate_id: int,
    comment: str,
    actor_account_id: int | None,
    now: str,
) -> list[int]:
    rows = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = 'revoked',
            review_comment = %s,
            reviewed_by_account_id = %s,
            reviewed_at = %s::timestamptz,
            updated_at = %s::timestamptz
        WHERE candidate_id = %s AND status IN ('requested', 'approved')
        RETURNING id
        """,
        (comment, actor_account_id, now, now, int(candidate_id)),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def consume_approval(conn: Any, *, approval_id: int, now: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = 'consumed', consumed_at = %s::timestamptz, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (now, now, approval_id),
    )


def insert_final_decision(conn: Any, *, candidate_id: int, values: dict[str, Any], actor_account_id: int | None, actor_login: str, now: str) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_final_decisions (
            candidate_id, decision, rejection_reason, reason_detail,
            origin_stage, follow_up_at, approval_id, decided_by_account_id,
            decided_by_login, created_at, is_system_generated,
            source_evaluation_type, source_evaluation_id
        ) VALUES (
            %s, %s, %s, %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            %s::timestamptz, %s, %s, %s
        )
        RETURNING id
        """,
        (
            candidate_id, values["decision"], values.get("rejection_reason", ""),
            values.get("reason_detail", ""), values.get("origin_stage", ""),
            values.get("follow_up_at", ""),
            values.get("approval_id"), actor_account_id, actor_login, now,
            bool(values.get("is_system_generated")),
            values.get("source_evaluation_type", ""),
            values.get("source_evaluation_id"),
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def ensure_academy_intake(conn: Any, *, candidate: Any, actor_login: str, now: str) -> int:
    existing = conn.execute(
        "SELECT id FROM msi_v2.academy_teachers WHERE recruitment_candidate_id = %s LIMIT 1",
        (candidate["id"],),
    ).fetchone()
    if existing:
        return int(existing["id"])
    row = conn.execute(
        """
        INSERT INTO msi_v2.academy_teachers (
            user_id, full_name, subject_id, subject_program_id, position,
            employment_type, telegram_username, phone, academy_status,
            notes, created_by, recruitment_candidate_id,
            account_onboarding_status, created_at, updated_at
        ) VALUES (
            NULL, %s, NULLIF(%s::bigint, 0), NULL, %s,
            'academy', %s, %s, 'new_academy_teacher',
            %s, %s, %s, 'pending', %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate["full_name"], int(candidate["subject_id"] or 0),
            candidate["applied_position"] or "Trainee Teacher",
            candidate["telegram_username"], candidate["phone"],
            f"Accepted from recruitment candidate #{candidate['id']}.", actor_login,
            candidate["id"], now, now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def ensure_active_teacher_intake(conn: Any, *, candidate: Any, now: str) -> int:
    existing = conn.execute(
        "SELECT id FROM msi_v2.teachers WHERE recruitment_candidate_id = %s LIMIT 1",
        (candidate["id"],),
    ).fetchone()
    if existing:
        return int(existing["id"])
    row = conn.execute(
        """
        INSERT INTO msi_v2.teachers (
            full_name, phone, telegram_username, status, notes,
            recruitment_candidate_id, account_onboarding_status,
            created_at, updated_at
        ) VALUES (%s, %s, %s, 'active', %s, %s, 'pending', %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (
            candidate["full_name"], candidate["phone"], candidate["telegram_username"],
            f"Accepted directly from recruitment candidate #{candidate['id']}.",
            candidate["id"], now, now,
        ),
    ).fetchone()
    teacher_id = int(row["id"]) if row else 0
    if teacher_id and int(candidate["subject_id"] or 0):
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_subjects (teacher_id, subject_id, status, created_at)
            VALUES (%s, %s, 'active', %s::timestamptz)
            ON CONFLICT (teacher_id, subject_id) DO UPDATE SET status = 'active'
            """,
            (teacher_id, int(candidate["subject_id"]), now),
        )
    return teacher_id


def insert_audit(
    conn: Any,
    *,
    candidate_id: int,
    event_type: str,
    detail: dict[str, Any],
    actor_account_id: int | None,
    actor_staff_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, actor_account_id, event_type,
            entity_type, entity_id, detail_json, created_at
        ) VALUES (%s, %s, %s, 'teacher_candidate', %s, %s::jsonb, %s::timestamptz)
        """,
        (
            actor_staff_id, actor_account_id, event_type, candidate_id,
            json.dumps(detail, ensure_ascii=False, default=str), now,
        ),
    )


def list_recruitment_setting_rows(
    conn: Any,
    *,
    include_inactive: bool = False,
) -> list[Any]:
    active_clause = "" if include_inactive else "WHERE is_active = true"
    return conn.execute(
        f"""
        SELECT id, category, value, label, is_active, sort_order, is_system,
               created_at::text AS created_at, updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_settings
        {active_clause}
        ORDER BY category, sort_order, lower(label), id
        """
    ).fetchall()


def list_sla_rule_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT rule.stage, rule.target_days, rule.is_active,
               rule.updated_by_account_id,
               COALESCE(account.full_name, account.login, '') AS updated_by,
               rule.updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_sla_rules rule
        LEFT JOIN msi_v2.accounts account ON account.id = rule.updated_by_account_id
        ORDER BY CASE rule.stage
            WHEN 'new_candidate' THEN 1
            WHEN 'responded' THEN 2
            WHEN 'job_interview' THEN 3
            WHEN 'test_and_demo' THEN 4
            WHEN 'under_review' THEN 5
            ELSE 99 END
        """
    ).fetchall()


def update_sla_rule(
    conn: Any,
    *,
    stage: str,
    target_days: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_sla_rules
        SET target_days = %s,
            is_active = true,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE stage = %s
        RETURNING stage, target_days, is_active, updated_by_account_id,
                  updated_at::text AS updated_at
        """,
        (int(target_days), actor_account_id, now, stage),
    ).fetchone()


def recruitment_setting_by_label_or_value(
    conn: Any,
    *,
    category: str,
    value: str,
    label: str,
) -> Any:
    return conn.execute(
        """
        SELECT id, category, value, label, is_active, sort_order, is_system,
               created_at::text AS created_at, updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_settings
        WHERE category = %s
          AND (value = %s OR lower(label) = lower(%s))
        ORDER BY id
        LIMIT 1
        FOR UPDATE
        """,
        (category, value, label),
    ).fetchone()


def recruitment_setting_by_id(conn: Any, setting_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, category, value, label, is_active, sort_order, is_system
        FROM msi_v2.teacher_recruitment_settings
        WHERE id = %s
        LIMIT 1
        """,
        (int(setting_id),),
    ).fetchone()


def save_recruitment_setting(
    conn: Any,
    *,
    existing_id: int | None,
    category: str,
    value: str,
    label: str,
    actor_account_id: int | None,
    now: str,
) -> Any:
    if existing_id:
        return conn.execute(
            """
            UPDATE msi_v2.teacher_recruitment_settings
            SET value = %s,
                label = %s,
                is_active = true,
                updated_by_account_id = %s,
                updated_at = %s::timestamptz
            WHERE id = %s
            RETURNING id, category, value, label, is_active, sort_order, is_system,
                      created_at::text AS created_at, updated_at::text AS updated_at
            """,
            (value, label, actor_account_id, now, int(existing_id)),
        ).fetchone()
    return conn.execute(
        """
        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, sort_order,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, %s,
            COALESCE((
                SELECT max(sort_order) + 10
                FROM msi_v2.teacher_recruitment_settings
                WHERE category = %s
            ), 10),
            %s, %s, %s::timestamptz, %s::timestamptz
        )
        RETURNING id, category, value, label, is_active, sort_order, is_system,
                  created_at::text AS created_at, updated_at::text AS updated_at
        """,
        (
            category, value, label, category,
            actor_account_id, actor_account_id, now, now,
        ),
    ).fetchone()


def deactivate_recruitment_setting(
    conn: Any,
    *,
    setting_id: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_settings
        SET is_active = false,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s AND is_active = true AND is_system = false
        RETURNING id, category, value, label, is_active, sort_order, is_system,
                  created_at::text AS created_at, updated_at::text AS updated_at
        """,
        (actor_account_id, now, int(setting_id)),
    ).fetchone()


def recruitment_setting_value_exists(conn: Any, *, category: str, value: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM msi_v2.teacher_recruitment_settings
        WHERE category = %s AND value = %s AND is_active = true
        LIMIT 1
        """,
        (category, value),
    ).fetchone()
    return bool(row)


def insert_recruitment_setting_audit(
    conn: Any,
    *,
    setting_id: int,
    event_type: str,
    detail: dict[str, Any],
    actor_account_id: int | None,
    actor_staff_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, actor_account_id, event_type,
            entity_type, entity_id, detail_json, created_at
        ) VALUES (%s, %s, %s, 'teacher_recruitment_setting', %s, %s::jsonb, %s::timestamptz)
        """,
        (
            actor_staff_id, actor_account_id, event_type, setting_id,
            json.dumps(detail, ensure_ascii=False, default=str), now,
        ),
    )


def insert_recruitment_notification(conn: Any, *, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_recruitment_notifications (
            recipient_account_id, candidate_id, appointment_id,
            notification_type, title, body, action_url, deliver_at,
            telegram_status, telegram_next_attempt_at, dedupe_key,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s::timestamptz,
            'pending', %s::timestamptz, %s, now(), now()
        )
        ON CONFLICT (dedupe_key) DO NOTHING
        """,
        (
            int(values["recipient_account_id"]), int(values["candidate_id"]),
            int(values["appointment_id"]), values["notification_type"],
            values["title"], values["body"], values["action_url"],
            values["deliver_at"], values["deliver_at"], values["dedupe_key"],
        ),
    )


def cancel_recruitment_notification_reminders(conn: Any, appointment_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'cancelled', updated_at = now()
        WHERE appointment_id = %s
          AND notification_type IN ('demo_reminder_24h', 'demo_reminder_1h')
          AND telegram_status IN ('pending', 'waiting_link', 'failed')
        """,
        (int(appointment_id),),
    )


def list_future_demo_appointments_for_recipient(conn: Any, account_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT appointment.id, appointment.candidate_id, appointment.appointment_type,
               appointment.starts_at, appointment.topic,
               appointment.responsible_account_id, candidate.full_name AS candidate_name,
               account.role AS responsible_role
        FROM msi_v2.teacher_candidate_appointments appointment
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        JOIN msi_v2.accounts account ON account.id = appointment.responsible_account_id
        WHERE appointment.responsible_account_id = %s
          AND appointment.appointment_type = 'demo_lesson'
          AND appointment.status = 'scheduled'
          AND appointment.starts_at > now()
        ORDER BY appointment.starts_at ASC
        """,
        (int(account_id),),
    ).fetchall()


def list_recruitment_notification_rows(
    conn: Any,
    *,
    account_id: int,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    total_row = conn.execute(
        """
        SELECT count(*) AS total
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND deliver_at <= now()
        """,
        (int(account_id),),
    ).fetchone()
    rows = conn.execute(
        """
        SELECT id, candidate_id, appointment_id, notification_type, title,
               body, action_url, deliver_at, read_at, created_at
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND deliver_at <= now()
        ORDER BY created_at DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        (int(account_id), int(limit), int(offset)),
    ).fetchall()
    return rows, int(total_row["total"] or 0) if total_row else 0


def recruitment_notification_unread_count(conn: Any, account_id: int) -> int:
    row = conn.execute(
        """
        SELECT count(*) AS total
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND read_at IS NULL AND deliver_at <= now()
        """,
        (int(account_id),),
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def mark_recruitment_notification_read(conn: Any, *, account_id: int, notification_id: int) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET read_at = COALESCE(read_at, now()), updated_at = now()
        WHERE id = %s AND recipient_account_id = %s
        """,
        (int(notification_id), int(account_id)),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def recover_stale_recruitment_notification_deliveries(conn: Any) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'failed', telegram_locked_at = NULL,
            telegram_next_attempt_at = now(),
            telegram_last_error = 'delivery_worker_recovered_after_restart',
            updated_at = now()
        WHERE telegram_status = 'sending'
          AND telegram_locked_at < now() - interval '10 minutes'
        """
    )


def claimable_recruitment_notification_rows(conn: Any, limit: int) -> list[Any]:
    return conn.execute(
        """
        SELECT notification.id, notification.title, notification.body,
               notification.action_url, notification.telegram_attempts,
               link.telegram_user_id
        FROM msi_v2.teacher_recruitment_notifications notification
        LEFT JOIN msi_v2.account_telegram_links link
          ON link.account_id = notification.recipient_account_id
         AND link.status = 'active'
        WHERE notification.telegram_status IN ('pending', 'failed', 'waiting_link')
          AND COALESCE(notification.telegram_next_attempt_at, notification.deliver_at) <= now()
          AND notification.deliver_at <= now()
        ORDER BY COALESCE(notification.telegram_next_attempt_at, notification.deliver_at), notification.id
        LIMIT %s
        FOR UPDATE OF notification SKIP LOCKED
        """,
        (int(limit),),
    ).fetchall()


def mark_recruitment_notification_waiting_link(conn: Any, notification_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'waiting_link',
            telegram_next_attempt_at = now() + interval '6 hours',
            telegram_last_error = 'telegram_account_not_linked', updated_at = now()
        WHERE id = %s
        """,
        (int(notification_id),),
    )


def mark_recruitment_notification_sending(conn: Any, notification_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'sending', telegram_locked_at = now(), updated_at = now()
        WHERE id = %s
        """,
        (int(notification_id),),
    )


def mark_recruitment_notification_sent(conn: Any, *, notification_id: int, attempts: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'sent', telegram_attempts = %s,
            telegram_sent_at = now(), telegram_next_attempt_at = NULL,
            telegram_last_error = '', telegram_locked_at = NULL, updated_at = now()
        WHERE id = %s AND telegram_status = 'sending'
        """,
        (int(attempts), int(notification_id)),
    )


def mark_recruitment_notification_failed(
    conn: Any,
    *,
    notification_id: int,
    attempts: int,
    retry_delay_minutes: int,
    error: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'failed', telegram_attempts = %s,
            telegram_next_attempt_at = now() + (%s || ' minutes')::interval,
            telegram_last_error = %s, telegram_locked_at = NULL, updated_at = now()
        WHERE id = %s AND telegram_status = 'sending'
        """,
        (int(attempts), str(retry_delay_minutes), error[:500], int(notification_id)),
    )


def list_recruitment_options(conn: Any) -> dict[str, Any]:
    subject_rows = conn.execute(
        """
        SELECT id, subject_name AS name
        FROM msi_v2.subjects WHERE status = 'active'
        ORDER BY subject_name
        """
    ).fetchall()
    staff_rows = conn.execute(
        """
        SELECT id, role, COALESCE(NULLIF(full_name, ''), login) AS name, login
        FROM msi_v2.accounts
        WHERE status = 'active'
          AND role IN ('ceo', 'hr_manager', 'academic_director', 'head_of_department')
        ORDER BY role, lower(COALESCE(NULLIF(full_name, ''), login))
        """
    ).fetchall()
    setting_rows = list_recruitment_setting_rows(conn)
    sources = [str(row["label"]) for row in setting_rows if row["category"] == "source"]
    rejection_reason_options = [
        {"value": str(row["value"]), "label": str(row["label"])}
        for row in setting_rows
        if row["category"] == "rejection_reason"
    ]
    return {
        "subjects": [dict(row) for row in subject_rows],
        "staff": [dict(row) for row in staff_rows],
        "sources": sources,
        "rejection_reason_options": rejection_reason_options,
    }


__all__ = [name for name in globals() if not name.startswith("_")]
