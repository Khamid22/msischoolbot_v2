"""Teacher Academy queries for the Alembic-managed ``msi_v2`` schema."""

from __future__ import annotations

from typing import Any

from backend.modules.domains.teacher_records import contracts as teacher_contract
from backend.modules.domains.teacher_academy.lifecycle_repository import (
    approve_academy_teacher_promotion,
    delete_academy_teacher_profile_row,
    delete_academy_teacher_row,
    delete_academy_teacher_staff_row,
    delete_by_ids as _delete_by_ids,
    delete_staff_profiles_for_delete,
    delete_teacher_accounts_for_delete,
    delete_teacher_profiles_for_delete,
    get_academy_teacher_delete_row,
    list_teacher_account_ids_for_staff,
    touch_academy_teacher,
    update_academy_teacher_status,
)
# Teacher identity helpers remain owned by the canonical teacher domain.
get_teacher_by_full_name_row = teacher_contract.get_teacher_by_full_name_row
insert_teacher_profile_row = teacher_contract.insert_teacher_profile_row
upsert_teacher_subject = teacher_contract.upsert_teacher_subject
get_teacher_auth_row_by_id = teacher_contract.get_teacher_auth_row_by_id
get_next_teacher_code = teacher_contract.get_next_teacher_code
insert_teacher_auth = teacher_contract.insert_teacher_auth
activate_teacher_profile = teacher_contract.activate_teacher_profile
set_teacher_group_assignment = teacher_contract.set_teacher_group_assignment
acquire_teacher_login_advisory_lock = (
    teacher_contract.acquire_teacher_login_advisory_lock
)


def insert_academy_teacher(
    conn: Any,
    *,
    staff_id: int,
    full_name: str,
    subject_id: int,
    subject_program_id: int,
    position: str,
    employment_type: str,
    telegram_username: str,
    phone: str,
    email: str,
    academy_start_date: str,
    mentor_id: int,
    department_head_id: int,
    notes: str,
    created_by: str,
    created_at: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.academy_teachers (
            user_id, full_name, subject_id, subject_program_id, position, employment_type,
            telegram_username, phone, email, academy_status, academy_start_date,
            mentor_id, department_head_id, notes, created_by, created_at, updated_at
        )
        VALUES (
            NULLIF(%s::bigint, 0), %s, %s, %s, %s, %s,
            %s, %s, %s, 'in_training', NULLIF(%s, '')::date,
            NULLIF(%s::bigint, 0), NULLIF(%s::bigint, 0), %s, %s, %s::timestamptz, %s::timestamptz
        )
        RETURNING id
        """,
        (
            staff_id,
            full_name,
            subject_id,
            subject_program_id,
            position,
            employment_type,
            telegram_username,
            phone,
            email,
            academy_start_date,
            mentor_id,
            department_head_id,
            notes,
            created_by,
            created_at,
            created_at,
        ),
    ).fetchone()
    return int(row["id"] or 0) if row else 0


def link_teacher_identity_to_candidate(
    conn: Any,
    *,
    teacher_id: int,
    candidate_id: int,
    updated_at: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.teachers
        SET recruitment_candidate_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s
          AND (
              recruitment_candidate_id IS NULL
              OR recruitment_candidate_id = %s
          )
        RETURNING id
        """,
        (candidate_id, updated_at, teacher_id, candidate_id),
    ).fetchone()
    return bool(row)


def get_pending_recruitment_academy_intake(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, full_name, phone, telegram_username, notes,
               recruitment_candidate_id, account_onboarding_status,
               user_id, subject_id, subject_program_id, academy_status
        FROM msi_v2.academy_teachers
        WHERE id = %s
          AND recruitment_candidate_id IS NOT NULL
          AND COALESCE(academy_status, '') NOT IN ('rejected', 'removed', 'trash_bin')
        FOR UPDATE
        """,
        (academy_teacher_id,),
    ).fetchone()


def get_recruitment_academy_account_context(conn: Any, academy_teacher_id: int) -> Any:
    """Lock an Academy intake and expose every canonical identity link."""
    return conn.execute(
        """
        SELECT
            academy.id,
            academy.full_name,
            academy.phone,
            academy.email,
            academy.telegram_username,
            academy.notes,
            academy.subject_id,
            academy.subject_program_id,
            academy.academy_status,
            academy.account_onboarding_status,
            academy.user_id AS academy_staff_id,
            academy.recruitment_candidate_id AS candidate_id,
            candidate.linked_account_id AS candidate_account_id,
            candidate.status AS candidate_status,
            COALESCE(academy_staff.id, linked_staff.id, candidate_account_staff.id) AS staff_id,
            COALESCE(
                academy_staff.login,
                linked_staff.login,
                candidate_account_staff.login,
                ''
            ) AS staff_login,
            COALESCE(
                academy_staff.password_hash,
                linked_staff.password_hash,
                candidate_account_staff.password_hash,
                ''
            ) AS staff_password_hash,
            COALESCE(
                academy_staff.role,
                linked_staff.role,
                candidate_account_staff.role,
                ''
            ) AS staff_role,
            COALESCE(
                academy_staff.teacher_id,
                linked_teacher.id,
                candidate_account_teacher.id
            ) AS teacher_id,
            COALESCE(
                linked_teacher.recruitment_candidate_id,
                candidate_account_teacher.recruitment_candidate_id
            ) AS teacher_candidate_id,
            staff_account.id AS staff_account_id,
            candidate_account.id AS linked_candidate_account_id,
            COALESCE(staff_account.id, candidate_account.id) AS account_id,
            COALESCE(staff_account.role, candidate_account.role, '') AS account_role,
            COALESCE(staff_account.legacy_source_id, candidate_account.legacy_source_id) AS account_staff_id
        FROM msi_v2.academy_teachers academy
        JOIN msi_v2.teacher_candidates candidate
          ON candidate.id = academy.recruitment_candidate_id
        LEFT JOIN msi_v2.accounts candidate_account
          ON candidate_account.id = candidate.linked_account_id
        LEFT JOIN msi_v2.msi_staff candidate_account_staff
          ON candidate_account.legacy_source_table = 'msi_staff'
         AND candidate_account_staff.id = candidate_account.legacy_source_id
        LEFT JOIN msi_v2.teachers candidate_account_teacher
          ON candidate_account_teacher.id = candidate_account_staff.teacher_id
        LEFT JOIN msi_v2.teachers linked_teacher
          ON linked_teacher.recruitment_candidate_id = candidate.id
        LEFT JOIN msi_v2.msi_staff academy_staff
          ON academy_staff.id = academy.user_id
        LEFT JOIN msi_v2.msi_staff linked_staff
          ON linked_staff.teacher_id = linked_teacher.id
        LEFT JOIN msi_v2.accounts staff_account
          ON staff_account.role = 'teacher'
         AND staff_account.legacy_source_table = 'msi_staff'
         AND staff_account.legacy_source_id = COALESCE(
             academy_staff.id,
             linked_staff.id,
             candidate_account_staff.id
         )
        WHERE academy.id = %s
        FOR UPDATE OF academy, candidate
        """,
        (int(academy_teacher_id),),
    ).fetchone()


def mark_recruitment_academy_account_ready(
    conn: Any,
    *,
    academy_teacher_id: int,
    staff_id: int,
    updated_at: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET user_id = %s,
            account_onboarding_status = 'complete',
            updated_at = %s::timestamptz
        WHERE id = %s
          AND (user_id IS NULL OR user_id = %s)
          AND COALESCE(academy_status, '') NOT IN ('rejected', 'removed', 'trash_bin')
        RETURNING id
        """,
        (int(staff_id), updated_at, int(academy_teacher_id), int(staff_id)),
    ).fetchone()
    return bool(row)


def complete_recruitment_academy_curriculum(
    conn: Any,
    *,
    academy_teacher_id: int,
    subject_id: int,
    subject_program_id: int,
    updated_at: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET subject_id = %s,
            subject_program_id = %s,
            academy_status = 'in_training',
            updated_at = %s::timestamptz
        WHERE id = %s
          AND user_id IS NOT NULL
          AND account_onboarding_status = 'complete'
          AND COALESCE(academy_status, '') NOT IN ('rejected', 'removed', 'trash_bin')
        RETURNING id
        """,
        (subject_id, subject_program_id, updated_at, academy_teacher_id),
    ).fetchone()
    return bool(row)


def attach_lifecycle_profile_account(
    conn: Any,
    *,
    candidate_id: int,
    account_id: int,
    updated_at: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.teacher_candidates
        SET linked_account_id = %s, updated_at = %s::timestamptz
        WHERE id = %s
          AND (linked_account_id IS NULL OR linked_account_id = %s)
        RETURNING id
        """,
        (int(account_id), updated_at, int(candidate_id), int(account_id)),
    ).fetchone()
    return bool(row)


def insert_recruitment_academy_account_audit(
    conn: Any,
    *,
    academy_teacher_id: int,
    candidate_id: int,
    teacher_id: int,
    staff_id: int,
    account_id: int,
    login: str,
    actor_account_id: int | None,
    actor_login: str,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_account_id, event_type, entity_type, entity_id, detail_json, created_at
        ) VALUES (
            %s, 'candidate.academy_account_provisioned', 'teacher_candidate', %s,
            jsonb_build_object(
                'academy_teacher_id', %s,
                'teacher_id', %s,
                'staff_id', %s,
                'account_id', %s,
                'login', %s::text,
                'actor_login', %s::text
            ),
            %s::timestamptz
        )
        """,
        (
            actor_account_id,
            candidate_id,
            academy_teacher_id,
            teacher_id,
            staff_id,
            account_id,
            login,
            actor_login,
            created_at,
        ),
    )


def insert_recruitment_academy_onboarding_audit(
    conn: Any,
    *,
    academy_teacher_id: int,
    candidate_id: int,
    actor_account_id: int | None,
    actor_login: str,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_account_id, event_type, entity_type, entity_id, detail_json, created_at
        ) VALUES (
            %s, 'candidate.academy_onboarding_completed', 'teacher_candidate', %s,
            jsonb_build_object('academy_teacher_id', %s, 'actor_login', %s::text),
            %s::timestamptz
        )
        """,
        (actor_account_id, candidate_id, academy_teacher_id, actor_login, created_at),
    )


def insert_academy_lesson_assignment(
    conn: Any,
    *,
    academy_teacher_id: int,
    subject_id: int,
    subject_program_id: int,
    curriculum_item_id: int,
    sequence_no: int,
    lesson_number: str,
    lesson_topic: str,
    focus_areas_json: str,
    created_by: str,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.academy_lesson_assignments (
            academy_teacher_id, subject_id, subject_program_id, curriculum_item_id,
            sequence_no, lesson_number, lesson_topic, assignment_type,
            focus_areas, created_by, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, 'full_practice_lesson',
            %s::jsonb, %s, %s::timestamptz, %s::timestamptz
        )
        """,
        (
            academy_teacher_id,
            subject_id,
            subject_program_id,
            curriculum_item_id,
            sequence_no,
            lesson_number,
            lesson_topic,
            focus_areas_json,
            created_by,
            created_at,
            created_at,
        ),
    )


def get_assignment_schedule_row(conn: Any, assignment_id: int) -> Any:
    return conn.execute(
        """
        SELECT
            ala.id,
            ala.academy_teacher_id,
            ala.lesson_number,
            ala.lesson_topic,
            ala.assignment_type,
            ala.deadline_date::text AS deadline_date,
            ala.session_datetime::text AS session_datetime,
            ala.evaluator_id,
            COALESCE(eval.full_name, '') AS evaluator_name,
            at.full_name AS academy_teacher_name,
            at.subject_id,
            COALESCE(subj.subject_name, '') AS subject,
            at.telegram_username,
            COALESCE(
                NULLIF(staff.telegram_user_id, 0),
                (
                    SELECT link.telegram_user_id
                    FROM msi_v2.account_telegram_links link
                    JOIN msi_v2.accounts account ON account.id = link.account_id
                    WHERE link.status = 'active'
                      AND account.legacy_source_table = 'msi_staff'
                      AND account.legacy_source_id = staff.id
                    ORDER BY link.id DESC
                    LIMIT 1
                ),
                0
            ) AS telegram_user_id
        FROM msi_v2.academy_lesson_assignments ala
        LEFT JOIN msi_v2.academy_teachers at ON at.id = ala.academy_teacher_id
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = COALESCE(ala.subject_id, at.subject_id)
        LEFT JOIN msi_v2.teachers eval ON eval.id = ala.evaluator_id
        WHERE ala.id = %s
        """,
        (assignment_id,),
    ).fetchone()


def update_assignment_schedule(
    conn: Any,
    *,
    assignment_id: int,
    assignment_type: str,
    deadline_date: str,
    session_datetime: str,
    evaluator_id: int,
    focus_areas_json: str,
    notes_to_trainee: str,
    status: str,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_lesson_assignments
        SET assignment_type = COALESCE(NULLIF(%s, ''), assignment_type),
            deadline_date = NULLIF(%s, '')::date,
            session_datetime = NULLIF(%s, '')::timestamptz,
            evaluator_id = NULLIF(%s::bigint, 0),
            focus_areas = %s::jsonb,
            notes_to_trainee = %s,
            status = %s,
            updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (
            assignment_type,
            deadline_date,
            session_datetime,
            evaluator_id,
            focus_areas_json,
            notes_to_trainee,
            status,
            updated_at,
            assignment_id,
        ),
    )


def get_assignment_for_assessment(conn: Any, *, academy_teacher_id: int, lesson_assignment_id: int) -> Any:
    return conn.execute(
        """
        SELECT
            ala.id,
            ala.academy_teacher_id,
            ala.lesson_number,
            ala.lesson_topic,
            ala.assignment_type,
            ala.deadline_date::text AS deadline_date,
            ala.session_datetime::text AS session_datetime,
            ala.evaluator_id,
            COALESCE(eval.full_name, '') AS evaluator_name,
            at.full_name AS academy_teacher_name,
            at.subject_id,
            COALESCE(subj.subject_name, '') AS subject,
            at.telegram_username,
            COALESCE(
                NULLIF(staff.telegram_user_id, 0),
                (
                    SELECT link.telegram_user_id
                    FROM msi_v2.account_telegram_links link
                    JOIN msi_v2.accounts account ON account.id = link.account_id
                    WHERE link.status = 'active'
                      AND account.legacy_source_table = 'msi_staff'
                      AND account.legacy_source_id = staff.id
                    ORDER BY link.id DESC
                    LIMIT 1
                ),
                0
            ) AS telegram_user_id
        FROM msi_v2.academy_lesson_assignments ala
        LEFT JOIN msi_v2.academy_teachers at ON at.id = ala.academy_teacher_id
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = COALESCE(ala.subject_id, at.subject_id)
        LEFT JOIN msi_v2.teachers eval ON eval.id = ala.evaluator_id
        WHERE ala.id = %s AND ala.academy_teacher_id = %s
        LIMIT 1
        """,
        (lesson_assignment_id, academy_teacher_id),
    ).fetchone()


def insert_assessment(
    conn: Any,
    *,
    academy_teacher_id: int,
    lesson_assignment_id: int,
    assessment_type: str,
    lesson_number: str,
    lesson_topic: str,
    evaluator_id: int,
    assessment_datetime: str,
    session_type: str,
    class_label: str,
    section_feedback_json: str,
    scores: dict[str, float],
    weighted_score: float,
    strengths: str,
    areas_for_improvement: str,
    final_recommendation: str,
    decision: str,
    created_by: str,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.academy_assessments (
            academy_teacher_id, lesson_assignment_id, assessment_type,
            lesson_number, lesson_topic, evaluator_id, assessment_datetime,
            session_type, class_label, section_feedback,
            teacher_guidance_compliance_score, timing_adherence_score,
            resource_familiarity_score, english_fluency_score,
            confidence_delivery_score, engagement_technique_score,
            weighted_overall_score, strengths, areas_for_improvement,
            final_recommendation, decision, created_by, created_at, updated_at
        )
        VALUES (
            %s, %s, %s,
            %s, %s, NULLIF(%s::bigint, 0), NULLIF(%s, '')::timestamptz,
            %s, %s, %s::jsonb,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s::timestamptz, %s::timestamptz
        )
        """,
        (
            academy_teacher_id,
            lesson_assignment_id,
            assessment_type,
            lesson_number,
            lesson_topic,
            evaluator_id,
            assessment_datetime,
            session_type,
            class_label,
            section_feedback_json,
            scores["teacher_guidance_compliance_score"],
            scores["timing_adherence_score"],
            scores["resource_familiarity_score"],
            scores["english_fluency_score"],
            scores["confidence_delivery_score"],
            scores["engagement_technique_score"],
            weighted_score,
            strengths,
            areas_for_improvement,
            final_recommendation,
            decision,
            created_by,
            created_at,
            created_at,
        ),
    )


def get_assessment_delete_row(conn: Any, *, academy_teacher_id: int, assessment_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, academy_teacher_id, lesson_assignment_id
        FROM msi_v2.academy_assessments
        WHERE id = %s AND academy_teacher_id = %s
        LIMIT 1
        """,
        (assessment_id, academy_teacher_id),
    ).fetchone()


def delete_assessment_row(conn: Any, assessment_id: int) -> None:
    conn.execute(
        "DELETE FROM msi_v2.academy_assessments WHERE id = %s",
        (assessment_id,),
    )


def delete_assessments_for_assignment(conn: Any, *, academy_teacher_id: int, lesson_assignment_id: int) -> None:
    """Remove every existing report for one assignment so a re-assessment replaces it."""
    conn.execute(
        """
        DELETE FROM msi_v2.academy_assessments
        WHERE academy_teacher_id = %s AND lesson_assignment_id = %s
        """,
        (academy_teacher_id, lesson_assignment_id),
    )


def get_latest_assessment_for_assignment(conn: Any, *, academy_teacher_id: int, lesson_assignment_id: int) -> Any:
    return conn.execute(
        """
        SELECT decision
        FROM msi_v2.academy_assessments
        WHERE academy_teacher_id = %s AND lesson_assignment_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (academy_teacher_id, lesson_assignment_id),
    ).fetchone()


def get_latest_assessment_for_teacher(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        """
        SELECT decision
        FROM msi_v2.academy_assessments
        WHERE academy_teacher_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (academy_teacher_id,),
    ).fetchone()


def get_academy_teacher_status(conn: Any, academy_teacher_id: int) -> str:
    row = conn.execute(
        """
        SELECT academy_status
        FROM msi_v2.academy_teachers
        WHERE id = %s
        LIMIT 1
        """,
        (academy_teacher_id,),
    ).fetchone()
    return str(row["academy_status"] or "") if row else ""


def update_assignment_status(conn: Any, *, assignment_id: int, status: str, updated_at: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_lesson_assignments
        SET status = %s, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (status, updated_at, assignment_id),
    )


def get_academy_teacher_id(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        "SELECT id FROM msi_v2.academy_teachers WHERE id = %s",
        (academy_teacher_id,),
    ).fetchone()


def get_academy_teacher_program_row(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        """
        SELECT
            at.id,
            at.subject_id,
            at.subject_program_id,
            at.full_name,
            at.telegram_username,
            COALESCE(
                NULLIF(staff.telegram_user_id, 0),
                (
                    SELECT link.telegram_user_id
                    FROM msi_v2.account_telegram_links link
                    JOIN msi_v2.accounts account ON account.id = link.account_id
                    WHERE link.status = 'active'
                      AND account.legacy_source_table = 'msi_staff'
                      AND account.legacy_source_id = staff.id
                    ORDER BY link.id DESC
                    LIMIT 1
                ),
                0
            ) AS telegram_user_id,
            COALESCE(subj.subject_name, '') AS subject
        FROM msi_v2.academy_teachers at
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = at.subject_id
        WHERE at.id = %s
        LIMIT 1
        """,
        (academy_teacher_id,),
    ).fetchone()


def update_assignment_sequence(conn: Any, *, assignment_id: int, sequence_no: int, updated_at: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_lesson_assignments
        SET sequence_no = %s, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (sequence_no, updated_at, assignment_id),
    )


def delete_assignment_rows_with_assessments(conn: Any, assignment_ids: list[int]) -> None:
    _delete_by_ids(conn, "msi_v2.academy_assessments", "lesson_assignment_id", assignment_ids)
    _delete_by_ids(conn, "msi_v2.academy_lesson_assignments", "id", assignment_ids)
