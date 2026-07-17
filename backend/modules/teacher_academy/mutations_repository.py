"""Teacher Academy queries for the Alembic-managed ``msi_v2`` schema."""

from __future__ import annotations

from typing import Any

from backend.modules.people.teachers import contracts as teacher_contract
# Teacher identity helpers remain owned by the canonical teacher domain.
get_teacher_by_full_name_row = teacher_contract.get_teacher_by_full_name_row
insert_teacher_profile_row = teacher_contract.insert_teacher_profile_row
upsert_teacher_subject = teacher_contract.upsert_teacher_subject
get_teacher_auth_row_by_id = teacher_contract.get_teacher_auth_row_by_id
get_next_teacher_code = teacher_contract.get_next_teacher_code
insert_teacher_auth = teacher_contract.insert_teacher_auth
activate_teacher_profile = teacher_contract.activate_teacher_profile
set_teacher_group_assignment = teacher_contract.set_teacher_group_assignment


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


def get_pending_recruitment_academy_intake(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, full_name, phone, telegram_username, notes,
               recruitment_candidate_id, account_onboarding_status
        FROM msi_v2.academy_teachers
        WHERE id = %s
          AND recruitment_candidate_id IS NOT NULL
          AND account_onboarding_status = 'pending'
        FOR UPDATE
        """,
        (academy_teacher_id,),
    ).fetchone()


def complete_recruitment_academy_intake(
    conn: Any,
    *,
    academy_teacher_id: int,
    staff_id: int,
    subject_id: int,
    subject_program_id: int,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET user_id = %s, subject_id = %s, subject_program_id = %s,
            academy_status = 'in_training', account_onboarding_status = 'complete',
            updated_at = %s::timestamptz
        WHERE id = %s AND account_onboarding_status = 'pending'
        """,
        (staff_id, subject_id, subject_program_id, updated_at, academy_teacher_id),
    )


def attach_lifecycle_profile_account(
    conn: Any,
    *,
    candidate_id: int,
    account_id: int,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidates
        SET linked_account_id = %s, updated_at = %s::timestamptz
        WHERE id = %s
          AND (linked_account_id IS NULL OR linked_account_id = %s)
        """,
        (int(account_id), updated_at, int(candidate_id), int(account_id)),
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


def get_academy_teacher_delete_row(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        """
        SELECT
            at.id,
            at.user_id AS staff_id,
            at.promoted_teacher_id,
            COALESCE(staff.teacher_id, 0) AS teacher_id,
            COALESCE(staff.login, '') AS login,
            COALESCE(teacher.status, '') AS teacher_status
        FROM msi_v2.academy_teachers at
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.teachers teacher ON teacher.id = staff.teacher_id
        WHERE at.id = %s
        LIMIT 1
        """,
        (academy_teacher_id,),
    ).fetchone()


def list_teacher_account_ids_for_staff(conn: Any, *, staff_id: int) -> list[int]:
    if not staff_id:
        return []
    rows = conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE legacy_source_table = 'msi_staff'
          AND legacy_source_id = %s
          AND role = 'teacher'
        ORDER BY id ASC
        """,
        (staff_id,),
    ).fetchall()
    return [int(row["id"]) for row in rows if int(row["id"] or 0) > 0]


def _delete_by_ids(conn: Any, table_name: str, id_column: str, ids: list[int]) -> None:
    safe_ids = [int(item) for item in ids if int(item or 0) > 0]
    if not safe_ids:
        return
    placeholders = ", ".join(["%s"] * len(safe_ids))
    conn.execute(
        f"DELETE FROM {table_name} WHERE {id_column} IN ({placeholders})",
        tuple(safe_ids),
    )


def delete_teacher_profiles_for_delete(conn: Any, *, teacher_id: int, account_ids: list[int]) -> None:
    if account_ids:
        _delete_by_ids(conn, "msi_v2.teacher_profiles", "account_id", account_ids)
    if teacher_id:
        conn.execute(
            "DELETE FROM msi_v2.teacher_profiles WHERE teacher_id = %s",
            (teacher_id,),
        )


def delete_staff_profiles_for_delete(conn: Any, *, staff_id: int, account_ids: list[int]) -> None:
    if account_ids:
        _delete_by_ids(conn, "msi_v2.staff_profiles", "account_id", account_ids)
    if staff_id:
        conn.execute(
            "DELETE FROM msi_v2.staff_profiles WHERE staff_id = %s",
            (staff_id,),
        )


def delete_teacher_accounts_for_delete(conn: Any, account_ids: list[int]) -> None:
    _delete_by_ids(conn, "msi_v2.accounts", "id", account_ids)


def delete_academy_teacher_row(conn: Any, academy_teacher_id: int) -> None:
    conn.execute(
        "DELETE FROM msi_v2.academy_teachers WHERE id = %s",
        (academy_teacher_id,),
    )


def delete_academy_teacher_staff_row(conn: Any, staff_id: int) -> None:
    if not staff_id:
        return
    conn.execute(
        "DELETE FROM msi_v2.msi_staff WHERE id = %s",
        (staff_id,),
    )


def delete_academy_teacher_profile_row(conn: Any, teacher_id: int) -> None:
    if not teacher_id:
        return
    conn.execute(
        "DELETE FROM msi_v2.teachers WHERE id = %s AND status = 'academy'",
        (teacher_id,),
    )


def update_academy_teacher_status(conn: Any, *, academy_teacher_id: int, status: str, updated_at: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET academy_status = %s, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (status, updated_at, academy_teacher_id),
    )


def touch_academy_teacher(conn: Any, *, academy_teacher_id: int, updated_at: str) -> None:
    conn.execute(
        "UPDATE msi_v2.academy_teachers SET updated_at = %s::timestamptz WHERE id = %s",
        (updated_at, academy_teacher_id),
    )


def approve_academy_teacher_promotion(
    conn: Any, *, academy_teacher_id: int, promoted_teacher_id: int, updated_at: str
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET academy_status = 'approved',
            promoted_teacher_id = NULLIF(%s::bigint, 0),
            updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (promoted_teacher_id, updated_at, academy_teacher_id),
    )
