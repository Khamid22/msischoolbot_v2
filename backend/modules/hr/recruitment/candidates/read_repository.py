"""Read persistence and SQL projections for Recruitment candidates."""

from __future__ import annotations

from typing import Any

_CANDIDATE_COLUMNS = """
    candidate.id,
    candidate.full_name,
    candidate.phone,
    candidate.email,
    candidate.telegram_username,
    candidate.linked_account_id,
    candidate.is_application_received,
    candidate.profile_origin,
    candidate.subject_id,
    COALESCE(subject.subject_name, '') AS subject,
    candidate.position_option_id,
    COALESCE(position_option.label, candidate.applied_position, '') AS applied_position,
    candidate.application_date::text AS application_date,
    candidate.age,
    candidate.address,
    candidate.source_option_id,
    candidate.subsource_option_id,
    COALESCE(source_option.label, candidate.source, '') AS source,
    COALESCE(subsource_option.label, '') AS subsource,
    candidate.source_detail,
    candidate.status,
    COALESCE(current_stage_definition.label, '') AS status_label,
    current_stage_definition.stage_kind AS status_kind,
    current_stage_definition.color_token AS status_color_token,
    candidate.english_level_option_id,
    COALESCE(english_option.label, candidate.english_level, '') AS english_level,
    candidate.motivation_expectations,
    candidate.interests_hobbies,
    candidate.schedule_option_id,
    COALESCE(schedule_option.label, candidate.preferred_schedule, '') AS preferred_schedule,
    candidate.availability_option_id,
    COALESCE(availability_option.label, candidate.employment_availability, '') AS employment_availability,
    candidate.education_background,
    candidate.work_experience,
    candidate.teaching_experience_option_id,
    COALESCE(teaching_experience_option.label, candidate.teaching_experience, '') AS teaching_experience,
    candidate.previous_workplace,
    candidate.expected_salary_option_id,
    candidate.expected_salary_uzs,
    COALESCE(expected_salary_option.label, '') AS expected_salary,
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
    CASE
        WHEN current_stage_definition.stage_kind = 'custom'
            THEN COALESCE(
                candidate.application_date::timestamp AT TIME ZONE 'Asia/Tashkent',
                candidate.created_at
            )
        ELSE stage_history.entered_at
    END::text AS current_sla_anchor_at,
    COALESCE(decision.decision, '') AS final_decision,
    COALESCE(decision.rejection_reason, '') AS rejection_reason,
    COALESCE(decision.reason_detail, '') AS decision_reason_detail,
    COALESCE(decision.origin_stage, '') AS decision_origin_stage,
    COALESCE(decision_origin_definition.label, '') AS decision_origin_stage_label,
    CASE
        WHEN candidate.status = 'trash_bin'
            THEN COALESCE(previous_stage.stage, NULLIF(decision.origin_stage, ''), '')
        ELSE COALESCE(NULLIF(decision.origin_stage, ''), previous_stage.stage, '')
    END AS restore_stage,
    COALESCE(decision.source_evaluation_type, '') AS decision_source_evaluation_type,
    decision.source_evaluation_id AS decision_source_evaluation_id,
    COALESCE(decision_actor.full_name, decision_actor.login, decision.decided_by_login, '')
        AS final_decision_actor,
    decision.follow_up_at::text AS decision_follow_up_at,
    decision.created_at::text AS final_decision_at,
    COALESCE(latest_interview.result, '') AS latest_interview_result,
    latest_interview.interview_at::text AS latest_interview_at,
    COALESCE(latest_subject_test.result, '') AS latest_subject_test_result,
    latest_subject_test.test_at::text AS latest_subject_test_at,
    latest_subject_test.evaluator_account_id AS latest_subject_test_evaluator_account_id,
    COALESCE(
        latest_subject_test_evaluator.full_name,
        latest_subject_test_evaluator.login,
        ''
    ) AS latest_subject_test_evaluator_name,
    COALESCE(latest_demo.result, '') AS latest_demo_result,
    latest_demo.demo_at::text AS latest_demo_at,
    latest_demo.evaluator_account_id AS latest_demo_evaluator_account_id,
    COALESCE(latest_demo_evaluator.full_name, latest_demo_evaluator.login, '')
        AS latest_demo_evaluator_name,
    COALESCE(
        NULLIF(latest_demo.recommendation, ''),
        NULLIF(latest_demo.overview, ''),
        NULLIF(latest_demo.strengths, ''),
        ''
    ) AS latest_demo_note,
    academic_demo_appointment.id AS academic_demo_appointment_id,
    academic_demo_appointment.starts_at::text AS academic_demo_starts_at,
    academic_demo_appointment.status AS academic_demo_status,
    academic_demo_appointment.responsible_account_id AS academic_demo_responsible_account_id,
    COALESCE(
        academic_demo_responsible.full_name,
        academic_demo_responsible.login,
        ''
    ) AS academic_demo_responsible_name,
    actionable_approval.id AS actionable_approval_id,
    actionable_approval.requested_outcome AS actionable_requested_outcome,
    actionable_approval.status AS actionable_approval_status,
    actionable_approval.request_note AS actionable_request_note,
    actionable_approval.created_at::text AS actionable_requested_at,
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
    appointment.started_at::text AS next_appointment_started_at,
    appointment.pre_start_starts_at::text AS next_appointment_pre_start_starts_at,
    appointment.pre_start_ends_at::text AS next_appointment_pre_start_ends_at,
    academy.id AS academy_teacher_id,
    academy.academy_status AS academy_status,
    COALESCE(
        academy.academy_start_date::text,
        (academy.created_at AT TIME ZONE 'Asia/Tashkent')::date::text
    ) AS academy_start_date,
    academy.account_onboarding_status AS academy_onboarding_status,
    academy.subject_id AS academy_subject_id,
    COALESCE(academy_subject.subject_name, '') AS academy_subject,
    academy.subject_program_id AS academy_subject_program_id,
    COALESCE(academy_program.program_name, '') AS academy_curriculum,
    academy.user_id AS academy_staff_id,
    COALESCE(academy_staff.login, '') AS academy_login,
    academy_counts.lesson_count AS academy_lesson_count,
    academy_counts.assessment_count AS academy_assessment_count,
    teacher.id AS active_teacher_id
"""


def _candidate_joins() -> str:
    return """
        LEFT JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
        LEFT JOIN msi_v2.teacher_recruitment_settings source_option
          ON source_option.id = candidate.source_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings subsource_option
          ON subsource_option.id = candidate.subsource_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings position_option
          ON position_option.id = candidate.position_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings english_option
          ON english_option.id = candidate.english_level_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings schedule_option
          ON schedule_option.id = candidate.schedule_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings availability_option
          ON availability_option.id = candidate.availability_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings expected_salary_option
          ON expected_salary_option.id = candidate.expected_salary_option_id
        LEFT JOIN msi_v2.teacher_recruitment_settings teaching_experience_option
          ON teaching_experience_option.id = candidate.teaching_experience_option_id
        LEFT JOIN msi_v2.teacher_recruitment_pipeline_stages current_stage_definition
          ON current_stage_definition.stage_key = candidate.status
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
        LEFT JOIN msi_v2.teacher_recruitment_pipeline_stages decision_origin_definition
          ON decision_origin_definition.stage_key = decision.origin_stage
        LEFT JOIN LATERAL (
            SELECT history.stage
            FROM msi_v2.teacher_candidate_stage_history history
            WHERE history.candidate_id = candidate.id
              AND history.id <> COALESCE(stage_history.id, 0)
            ORDER BY history.entered_at DESC, history.id DESC
            LIMIT 1
        ) previous_stage ON true
        LEFT JOIN LATERAL (
            SELECT interview.result, interview.interview_at
            FROM msi_v2.teacher_candidate_interviews interview
            WHERE interview.candidate_id = candidate.id
              AND interview.voided_at IS NULL
            ORDER BY interview.interview_at DESC NULLS LAST, interview.id DESC
            LIMIT 1
        ) latest_interview ON true
        LEFT JOIN LATERAL (
            SELECT subject_test.id, subject_test.result, subject_test.test_at,
                   subject_test.evaluator_account_id
            FROM msi_v2.teacher_candidate_subject_tests subject_test
            WHERE subject_test.candidate_id = candidate.id
              AND subject_test.voided_at IS NULL
            ORDER BY subject_test.test_at DESC NULLS LAST, subject_test.id DESC
            LIMIT 1
        ) latest_subject_test ON true
        LEFT JOIN msi_v2.accounts latest_subject_test_evaluator
          ON latest_subject_test_evaluator.id = latest_subject_test.evaluator_account_id
        LEFT JOIN LATERAL (
            SELECT demo.id, demo.result, demo.demo_at, demo.evaluator_account_id,
                   demo.recommendation, demo.overview, demo.strengths
            FROM msi_v2.teacher_candidate_demo_lessons demo
            WHERE demo.candidate_id = candidate.id
              AND demo.voided_at IS NULL
            ORDER BY demo.demo_at DESC NULLS LAST, demo.id DESC
            LIMIT 1
        ) latest_demo ON true
        LEFT JOIN msi_v2.accounts latest_demo_evaluator
          ON latest_demo_evaluator.id = latest_demo.evaluator_account_id
        LEFT JOIN LATERAL (
            SELECT demo_appointment.id, demo_appointment.starts_at,
                   demo_appointment.status, demo_appointment.responsible_account_id
            FROM msi_v2.teacher_candidate_appointments demo_appointment
            WHERE demo_appointment.candidate_id = candidate.id
              AND demo_appointment.appointment_type = 'demo_lesson'
              AND demo_appointment.status IN ('scheduled', 'in_progress')
            ORDER BY
                CASE WHEN demo_appointment.status = 'in_progress' THEN 0 ELSE 1 END,
                demo_appointment.starts_at DESC,
                demo_appointment.id DESC
            LIMIT 1
        ) academic_demo_appointment ON true
        LEFT JOIN msi_v2.accounts academic_demo_responsible
          ON academic_demo_responsible.id = academic_demo_appointment.responsible_account_id
        LEFT JOIN LATERAL (
            SELECT approval.id, approval.requested_outcome, approval.status,
                   approval.request_note, approval.created_at
            FROM msi_v2.teacher_candidate_hire_approvals approval
            WHERE approval.candidate_id = candidate.id
              AND approval.status IN ('requested', 'approved')
            ORDER BY
                CASE WHEN approval.status = 'requested' THEN 0 ELSE 1 END,
                approval.created_at DESC,
                approval.id DESC
            LIMIT 1
        ) actionable_approval ON true
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
                   a.location_or_link, a.topic, a.status, a.version, a.started_at,
                   a.pre_start_starts_at, a.pre_start_ends_at
            FROM msi_v2.teacher_candidate_appointments a
            WHERE a.candidate_id = candidate.id
              AND a.status IN ('scheduled', 'in_progress')
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
        LEFT JOIN msi_v2.subjects academy_subject
          ON academy_subject.id = academy.subject_id
        LEFT JOIN msi_v2.subject_programs academy_program
          ON academy_program.id = academy.subject_program_id
        LEFT JOIN msi_v2.msi_staff academy_staff
          ON academy_staff.id = academy.user_id
        LEFT JOIN LATERAL (
            SELECT
                (
                    SELECT COUNT(*)::integer
                    FROM msi_v2.academy_lesson_assignments lesson
                    WHERE lesson.academy_teacher_id = academy.id
                ) AS lesson_count,
                (
                    SELECT COUNT(*)::integer
                    FROM msi_v2.academy_assessments assessment
                    WHERE assessment.academy_teacher_id = academy.id
                ) AS assessment_count
        ) academy_counts ON academy.id IS NOT NULL
        LEFT JOIN msi_v2.teachers teacher
          ON teacher.recruitment_candidate_id = candidate.id
    """


_ACADEMIC_CANDIDATE_GROUPS = {
    "new",
    "subject_test",
    "successful",
    "rejected",
}
_ACADEMIC_SUCCESSFUL_CONDITION = """
    candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')
    AND COALESCE(latest_demo.result, '') = 'passed'
    AND COALESCE(latest_subject_test.result, '') = 'passed'
"""
_ACADEMIC_REJECTED_CONDITION = """
    candidate.status = 'rejected'
    AND COALESCE(decision.decision, '') = 'rejected'
    AND COALESCE(decision.source_evaluation_type, '') IN ('demo', 'subject_test')
"""
_ACADEMIC_SUBJECT_TEST_CONDITION = """
    candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')
    AND COALESCE(latest_demo.result, '') = 'passed'
    AND COALESCE(latest_subject_test.result, '') = ''
"""
_ACADEMIC_NEW_CONDITION = """
    candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')
    AND academic_demo_appointment.id IS NOT NULL
    AND COALESCE(latest_demo.result, '') <> 'passed'
"""


def _academic_candidate_group_condition(candidate_group: str) -> str:
    return {
        "new": _ACADEMIC_NEW_CONDITION,
        "subject_test": _ACADEMIC_SUBJECT_TEST_CONDITION,
        "successful": _ACADEMIC_SUCCESSFUL_CONDITION,
        "rejected": _ACADEMIC_REJECTED_CONDITION,
    }[candidate_group]


def _academic_candidate_relevant_expression(candidate_group: str) -> str:
    return {
        "new": "academic_demo_appointment.starts_at",
        "subject_test": "latest_demo.demo_at",
        "successful": "latest_subject_test.test_at",
        "rejected": "decision.created_at",
    }[candidate_group]


def _academic_candidate_evaluator_expression(candidate_group: str) -> str:
    return {
        "new": (
            "COALESCE(academic_demo_appointment.responsible_account_id, "
            "latest_demo.evaluator_account_id)"
        ),
        "subject_test": "latest_demo.evaluator_account_id",
        "successful": (
            "COALESCE(latest_subject_test.evaluator_account_id, "
            "latest_demo.evaluator_account_id)"
        ),
        "rejected": (
            "CASE "
            "WHEN decision.source_evaluation_type = 'demo' "
            "THEN latest_demo.evaluator_account_id "
            "WHEN decision.source_evaluation_type = 'subject_test' "
            "THEN latest_subject_test.evaluator_account_id "
            "END"
        ),
    }[candidate_group]


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
    clauses: list[str] = [
        "candidate.is_application_received = true",
        "EXISTS (SELECT 1 FROM msi_v2.teacher_recruitment_pipeline_stages pipeline_stage WHERE pipeline_stage.stage_key = candidate.status AND pipeline_stage.is_pipeline = true AND pipeline_stage.is_active = true)",
    ]
    params: list[Any] = []
    if visibility:
        clauses.append(visibility)
        params.extend(visibility_params)
    if search:
        clauses.append("candidate.full_name ILIKE %s")
        params.append(f"%{search}%")
    if position:
        if str(position).isdigit():
            clauses.append("candidate.position_option_id = %s")
            params.append(int(position))
        else:
            clauses.append(
                "lower(COALESCE(position_option.label, candidate.applied_position)) = lower(%s)"
            )
            params.append(position)
    if source:
        if str(source).isdigit():
            clauses.append("candidate.source_option_id = %s")
            params.append(int(source))
        else:
            clauses.append("COALESCE(source_option.label, candidate.source) = %s")
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
        ORDER BY
            CASE
                WHEN candidate.status IN ('job_interview', 'test_and_demo')
                     AND appointment.id IS NOT NULL
                    THEN 0
                WHEN candidate.status IN ('job_interview', 'test_and_demo')
                    THEN 1
                ELSE 2
            END,
            CASE
                WHEN candidate.status IN ('job_interview', 'test_and_demo')
                    THEN appointment.starts_at
            END ASC NULLS LAST,
            CASE
                WHEN candidate.status = 'new_candidate'
                     OR current_stage_definition.stage_kind = 'custom'
                    THEN COALESCE(
                        candidate.application_date::timestamp AT TIME ZONE 'Asia/Tashkent',
                        candidate.created_at
                    )
                ELSE COALESCE(candidate.stage_changed_at, candidate.created_at)
            END DESC,
            candidate.id DESC
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
    closed_from: str = "",
    closed_to: str = "",
    origin_stage: str = "",
    final_decision: str = "",
    evaluator_account_id: int | None = None,
    candidate_group: str = "",
    relevant_from: str = "",
    relevant_to: str = "",
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[Any], int]:
    if candidate_group and candidate_group not in _ACADEMIC_CANDIDATE_GROUPS:
        raise ValueError("Unknown academic candidate group.")
    clauses: list[str] = []
    if stage in {"rejected", "candidate_withdrew", "trash_bin"}:
        clauses.append(
            "(candidate.is_application_received = true OR candidate.profile_origin = 'academy_direct')"
        )
    else:
        clauses.append("candidate.is_application_received = true")
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
        if str(position).isdigit():
            clauses.append("candidate.position_option_id = %s")
            params.append(int(position))
        else:
            clauses.append(
                "lower(COALESCE(position_option.label, candidate.applied_position)) = lower(%s)"
            )
            params.append(position)
    if stage:
        clauses.append("candidate.status = %s")
        params.append(stage)
    else:
        clauses.append("candidate.status <> 'trash_bin'")
    if source:
        if str(source).isdigit():
            clauses.append("candidate.source_option_id = %s")
            params.append(int(source))
        else:
            clauses.append("COALESCE(source_option.label, candidate.source) = %s")
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
    closed_at_sql = (
        "COALESCE(decision.created_at, candidate.stage_changed_at)"
        if stage in {"rejected", "candidate_withdrew"}
        else "candidate.stage_changed_at"
    )
    if closed_from:
        clauses.append(f"{closed_at_sql}::date >= %s::date")
        params.append(closed_from)
    if closed_to:
        clauses.append(f"{closed_at_sql}::date <= %s::date")
        params.append(closed_to)
    if origin_stage:
        clauses.append(
            "COALESCE(NULLIF(decision.origin_stage, ''), previous_stage.stage, '') = %s"
        )
        params.append(origin_stage)
    if final_decision:
        clauses.append("COALESCE(decision.decision, '') = %s")
        params.append(final_decision)
    if evaluator_account_id:
        if candidate_group:
            clauses.append(
                f"({_academic_candidate_evaluator_expression(candidate_group)}) = %s"
            )
        else:
            clauses.append(
                """EXISTS (
                    SELECT 1 FROM msi_v2.teacher_candidate_assignments evaluator_filter
                    WHERE evaluator_filter.candidate_id = candidate.id
                      AND evaluator_filter.assignee_account_id = %s
                      AND evaluator_filter.status = 'active'
                )"""
            )
        params.append(evaluator_account_id)
    if candidate_group:
        clauses.append(f"({_academic_candidate_group_condition(candidate_group)})")
        relevant_expression = _academic_candidate_relevant_expression(candidate_group)
        if relevant_from:
            clauses.append(f"({relevant_expression})::date >= %s::date")
            params.append(relevant_from)
        if relevant_to:
            clauses.append(f"({relevant_expression})::date <= %s::date")
            params.append(relevant_to)

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
    if limit <= 0:
        return [], int(total_row["total"] or 0) if total_row else 0
    if candidate_group == "new":
        relevant_expression = _academic_candidate_relevant_expression(candidate_group)
        order_sql = f"""
            CASE WHEN ({relevant_expression}) >= now() THEN 0 ELSE 1 END,
            CASE WHEN ({relevant_expression}) >= now()
                THEN ({relevant_expression})
            END ASC NULLS LAST,
            ({relevant_expression}) DESC NULLS LAST,
            candidate.id DESC
        """
    elif candidate_group:
        order_sql = (
            f"({_academic_candidate_relevant_expression(candidate_group)}) "
            "DESC NULLS LAST, candidate.id DESC"
        )
    else:
        order_sql = "candidate.updated_at DESC, candidate.id DESC"
    rows = conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS}
        {base_from}
        ORDER BY {order_sql}
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
               CASE WHEN actionable_approval.id IS NULL THEN 'assignment' ELSE 'approval_request' END
                   AS access_reason
        FROM msi_v2.teacher_candidates candidate
        {_candidate_joins()}
        WHERE candidate.status <> 'trash_bin' AND ({visibility})
        ORDER BY CASE WHEN actionable_approval.id IS NULL THEN 1 ELSE 0 END,
                 actionable_approval.created_at DESC NULLS LAST,
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


def list_academy_lifecycle_lesson_rows(conn: Any, academy_teacher_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT assignment.id, assignment.sequence_no, assignment.lesson_number,
               assignment.lesson_topic, assignment.assignment_type,
               assignment.created_at::text AS assigned_at,
               assignment.deadline_date::text AS deadline_date,
               assignment.session_datetime::text AS session_datetime,
               assignment.status,
               COALESCE(evaluator.full_name, '') AS evaluator_name
        FROM msi_v2.academy_lesson_assignments assignment
        LEFT JOIN msi_v2.teachers evaluator ON evaluator.id = assignment.evaluator_id
        WHERE assignment.academy_teacher_id = %s
        ORDER BY assignment.sequence_no, assignment.id
        """,
        (int(academy_teacher_id),),
    ).fetchall()


def list_academy_lifecycle_assessment_rows(
    conn: Any, academy_teacher_id: int
) -> list[Any]:
    return conn.execute(
        """
        SELECT assessment.id, assessment.lesson_assignment_id,
               assessment.assessment_type, assessment.lesson_number,
               assessment.lesson_topic,
               assessment.assessment_datetime::text AS assessment_datetime,
               assessment.session_type, assessment.class_label,
               assessment.section_feedback,
               assessment.teacher_guidance_compliance_score,
               assessment.timing_adherence_score,
               assessment.resource_familiarity_score,
               assessment.english_fluency_score,
               assessment.confidence_delivery_score,
               assessment.engagement_technique_score,
               assessment.weighted_overall_score,
               assessment.strengths, assessment.areas_for_improvement,
               assessment.final_recommendation, assessment.decision,
               assessment.created_by,
               COALESCE(evaluator.full_name, '') AS evaluator_name
        FROM msi_v2.academy_assessments assessment
        LEFT JOIN msi_v2.teachers evaluator ON evaluator.id = assessment.evaluator_id
        WHERE assessment.academy_teacher_id = %s
        ORDER BY assessment.created_at, assessment.id
        """,
        (int(academy_teacher_id),),
    ).fetchall()


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
               stage_definition.label AS stage_label,
               history.entered_at::text AS entered_at,
               history.exited_at::text AS exited_at,
               history.responsible_account_id,
               COALESCE(account.full_name, account.login, '') AS responsible_name,
               history.comment, history.transition_source,
               history.sla_target_days,
               history.sla_due_at::text AS sla_due_at
        FROM msi_v2.teacher_candidate_stage_history history
        JOIN msi_v2.teacher_recruitment_pipeline_stages stage_definition
          ON stage_definition.stage_key = history.stage
        LEFT JOIN msi_v2.accounts account ON account.id = history.responsible_account_id
        WHERE history.candidate_id = %s
        ORDER BY history.entered_at DESC, history.id DESC
        """,
        (int(candidate_id),),
    ).fetchall()


__all__ = [
    "_CANDIDATE_COLUMNS",
    "_candidate_joins",
    "_visibility_clause",
    "candidate_assignment_row",
    "get_candidate_row",
    "list_academy_lifecycle_assessment_rows",
    "list_academy_lifecycle_lesson_rows",
    "list_activity_rows",
    "list_assignment_rows",
    "list_candidate_rows",
    "list_decision_queue_rows",
    "list_note_rows",
    "list_pipeline_rows",
    "list_stage_history_rows",
]
