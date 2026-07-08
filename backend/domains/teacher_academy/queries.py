"""Teacher Academy SQL helpers.

This DB-1 module owns Teacher Academy data access while intentionally keeping
the physical ``msi_v2`` schema and old database modules intact.
"""

from __future__ import annotations

from typing import Any

from backend.core.database import connect_auth_db
from backend.domains.teachers import queries as teacher_queries
from database import queries as legacy_queries


# Compatibility exports used by the Teacher Academy service and existing tests.
ensure_teacher_academy_schema = legacy_queries.ensure_teacher_academy_schema
get_teacher_by_full_name_row = teacher_queries.get_teacher_by_full_name_row
insert_teacher_profile_row = teacher_queries.insert_teacher_profile_row
upsert_teacher_subject = teacher_queries.upsert_teacher_subject
get_teacher_auth_row_by_id = teacher_queries.get_teacher_auth_row_by_id
get_next_teacher_code = teacher_queries.get_next_teacher_code
insert_teacher_auth = teacher_queries.insert_teacher_auth
activate_teacher_profile = teacher_queries.activate_teacher_profile
set_teacher_group_assignment = teacher_queries.set_teacher_group_assignment


def list_hod_subject_scope_rows(conn: Any, *, account_id: int, staff_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT DISTINCT scope.subject_id
        FROM msi_v2.staff_subject_scopes scope
        LEFT JOIN msi_v2.staff_profiles profile ON profile.id = scope.staff_profile_id
        WHERE scope.status = 'active'
          AND scope.scope_type = 'head_of_department'
          AND (
            scope.account_id = NULLIF(%s::bigint, 0)
            OR profile.staff_id = NULLIF(%s::bigint, 0)
          )
        """,
        (int(account_id or 0), int(staff_id or 0)),
    ).fetchall()


def get_academy_teacher_subject_id(conn: Any, academy_teacher_id: int) -> int:
    row = conn.execute(
        """
        SELECT subject_id
        FROM msi_v2.academy_teachers
        WHERE id = %s
        LIMIT 1
        """,
        (int(academy_teacher_id or 0),),
    ).fetchone()
    return int(row["subject_id"] or 0) if row else 0


def get_assignment_subject_id(conn: Any, assignment_id: int) -> int:
    row = conn.execute(
        """
        SELECT subject_id
        FROM msi_v2.academy_lesson_assignments
        WHERE id = %s
        LIMIT 1
        """,
        (int(assignment_id or 0),),
    ).fetchone()
    return int(row["subject_id"] or 0) if row else 0


def get_subject_program(conn: Any, program_id: int) -> Any:
    return conn.execute(
        """
        SELECT sp.id, sp.subject_id, sp.program_name, subj.subject_name, subj.subject_key
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE sp.id = %s AND sp.status = 'active'
        LIMIT 1
        """,
        (program_id,),
    ).fetchone()


def list_curriculum_lessons(conn: Any, program_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT id, program_id, item_order, lesson_number, title, specification_points, book_pages
        FROM msi_v2.subject_program_items
        WHERE program_id = %s AND item_type = 'lesson'
        ORDER BY item_order ASC
        """,
        (int(program_id),),
    ).fetchall()


def list_active_subjects(conn: Any) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, subject_name AS name, subject_key AS key,
                   subject_short AS code, subject_short AS short_name
            FROM msi_v2.subjects
            WHERE status = 'active'
            ORDER BY subject_name
            """
        ).fetchall()
    ]


def list_active_group_options(conn: Any) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT DISTINCT g.group_name AS name
            FROM msi_v2.groups g
            WHERE lower(g.group_name) <> 'online'
              AND COALESCE(g.status, 'active') = 'active'
            ORDER BY g.group_name
            """
        ).fetchall()
    ]


def list_curriculum_programs(conn: Any) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT sp.id, sp.subject_id, subj.subject_key, subj.subject_name,
                   subj.subject_short, sp.program_name, sp.lesson_count,
                   sp.exam_count, sp.updated_at::text AS updated_at
            FROM msi_v2.subject_programs sp
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            WHERE sp.status = 'active'
            ORDER BY subj.subject_name
            """
        ).fetchall()
    ]


def list_curriculum_items(conn: Any) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT spi.id, spi.program_id, subj.subject_key, subj.subject_name,
                   spi.item_order, spi.lesson_number, spi.item_type, spi.title,
                   spi.term_label, spi.week_label, spi.specification_points,
                   spi.book_pages, spi.lesson_count, spi.duration_hours
            FROM msi_v2.subject_program_items spi
            JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            WHERE sp.status = 'active'
              AND spi.item_type = 'lesson'
            ORDER BY subj.subject_name, spi.item_order
            """
        ).fetchall()
    ]


def list_academy_teacher_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT at.id, at.user_id, at.full_name, at.subject_id, at.subject_program_id,
               COALESCE(subj.subject_name, '') AS subject,
               COALESCE(sp.program_name, subj.subject_name, '') AS subject_program_name,
               at.position, at.employment_type, at.telegram_username, at.phone, at.email,
               at.academy_status, at.academy_start_date::text AS academy_start_date,
               at.mentor_id, COALESCE(mentor.full_name, '') AS mentor_name,
               at.department_head_id, COALESCE(head.full_name, '') AS department_head_name,
               at.notes, at.promoted_teacher_id,
               COALESCE(staff.login, '') AS login,
               COALESCE(staff.teacher_id, 0) AS account_teacher_id,
               at.created_at::text AS created_at, at.updated_at::text AS updated_at
        FROM msi_v2.academy_teachers at
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = at.subject_id
        LEFT JOIN msi_v2.subject_programs sp ON sp.id = at.subject_program_id
        LEFT JOIN msi_v2.teachers mentor ON mentor.id = at.mentor_id
        LEFT JOIN msi_v2.teachers head ON head.id = at.department_head_id
        ORDER BY at.updated_at DESC, at.id DESC
        """
    ).fetchall()


def get_academy_teacher_row_for_account(conn: Any, *, teacher_id: int, staff_id: int) -> Any:
    return conn.execute(
        """
        SELECT at.id, at.user_id, at.full_name, at.subject_id, at.subject_program_id,
               COALESCE(subj.subject_name, '') AS subject,
               COALESCE(sp.program_name, subj.subject_name, '') AS subject_program_name,
               at.position, at.employment_type, at.telegram_username, at.phone, at.email,
               at.academy_status, at.academy_start_date::text AS academy_start_date,
               at.mentor_id, COALESCE(mentor.full_name, '') AS mentor_name,
               at.department_head_id, COALESCE(head.full_name, '') AS department_head_name,
               at.notes, at.promoted_teacher_id,
               COALESCE(staff.login, '') AS login,
               COALESCE(staff.teacher_id, 0) AS account_teacher_id,
               at.created_at::text AS created_at, at.updated_at::text AS updated_at
        FROM msi_v2.academy_teachers at
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = at.subject_id
        LEFT JOIN msi_v2.subject_programs sp ON sp.id = at.subject_program_id
        LEFT JOIN msi_v2.teachers mentor ON mentor.id = at.mentor_id
        LEFT JOIN msi_v2.teachers head ON head.id = at.department_head_id
        WHERE (%s > 0 AND at.user_id = %s)
           OR (%s > 0 AND staff.teacher_id = %s)
           OR (%s > 0 AND at.promoted_teacher_id = %s)
        ORDER BY
            CASE
                WHEN %s > 0 AND at.user_id = %s THEN 0
                WHEN %s > 0 AND staff.teacher_id = %s THEN 1
                ELSE 2
            END,
            at.updated_at DESC,
            at.id DESC
        LIMIT 1
        """,
        (
            staff_id,
            staff_id,
            teacher_id,
            teacher_id,
            teacher_id,
            teacher_id,
            staff_id,
            staff_id,
            teacher_id,
            teacher_id,
        ),
    ).fetchone()


def list_assignment_rows(conn: Any, academy_teacher_id: int | None = None) -> list[Any]:
    where_clause = "WHERE ala.academy_teacher_id = %s" if academy_teacher_id else ""
    order_clause = (
        "ORDER BY ala.sequence_no ASC, ala.id ASC"
        if academy_teacher_id
        else "ORDER BY ala.academy_teacher_id, ala.sequence_no ASC, ala.id ASC"
    )
    params = (academy_teacher_id,) if academy_teacher_id else None
    return conn.execute(
        f"""
        SELECT ala.id, ala.academy_teacher_id, ala.sequence_no, ala.subject_program_id,
               ala.curriculum_item_id, ala.lesson_number, ala.lesson_topic,
               ala.assignment_type, ala.deadline_date::text AS deadline_date,
               ala.session_datetime::text AS session_datetime,
               ala.evaluator_id, COALESCE(eval.full_name, '') AS evaluator_name,
               ala.focus_areas::text AS focus_areas_json,
               ala.notes_to_trainee, ala.status,
               COALESCE(spi.specification_points, '') AS specification_points,
               COALESCE(spi.book_pages, '') AS book_pages,
               ala.created_at::text AS created_at, ala.updated_at::text AS updated_at
        FROM msi_v2.academy_lesson_assignments ala
        LEFT JOIN msi_v2.teachers eval ON eval.id = ala.evaluator_id
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ala.curriculum_item_id
        {where_clause}
        {order_clause}
        """,
        params,
    ).fetchall()


def list_assessment_rows(conn: Any, academy_teacher_id: int | None = None) -> list[Any]:
    where_clause = "WHERE aa.academy_teacher_id = %s" if academy_teacher_id else ""
    order_clause = (
        "ORDER BY aa.created_at ASC, aa.id ASC"
        if academy_teacher_id
        else "ORDER BY aa.academy_teacher_id, aa.created_at ASC, aa.id ASC"
    )
    params = (academy_teacher_id,) if academy_teacher_id else None
    return conn.execute(
        f"""
        SELECT aa.id, aa.academy_teacher_id, aa.lesson_assignment_id,
               aa.assessment_type, aa.lesson_number, aa.lesson_topic,
               aa.evaluator_id, COALESCE(eval.full_name, '') AS evaluator_name,
               aa.assessment_datetime::text AS assessment_datetime,
               aa.session_type, aa.class_label,
               aa.section_feedback::text AS section_feedback_json,
               aa.teacher_guidance_compliance_score,
               aa.timing_adherence_score,
               aa.resource_familiarity_score,
               aa.english_fluency_score,
               aa.confidence_delivery_score,
               aa.engagement_technique_score,
               aa.weighted_overall_score,
               aa.strengths, aa.areas_for_improvement,
               aa.final_recommendation, aa.decision,
               aa.created_by,
               aa.created_at::text AS created_at, aa.updated_at::text AS updated_at
        FROM msi_v2.academy_assessments aa
        LEFT JOIN msi_v2.teachers eval ON eval.id = aa.evaluator_id
        {where_clause}
        {order_clause}
        """,
        params,
    ).fetchall()


def list_academy_teacher_account_backfill_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT
            at.id,
            at.user_id,
            at.full_name,
            at.subject_id,
            at.notes,
            COALESCE(staff.login, '') AS staff_login,
            COALESCE(subj.subject_name, '') AS subject_name,
            COALESCE(subj.subject_key, '') AS subject_key
        FROM msi_v2.academy_teachers at
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = at.subject_id
        WHERE COALESCE(at.full_name, '') <> ''
          AND COALESCE(at.academy_status, '') NOT IN ('rejected')
          AND (
            at.user_id IS NULL
            OR staff.id IS NULL
            OR COALESCE(staff.login, '') = ''
            OR staff.teacher_id IS NULL
          )
        ORDER BY at.id ASC
        """
    ).fetchall()


def update_academy_teacher_user_id(conn: Any, *, academy_teacher_id: int, staff_id: int, updated_at: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET user_id = %s, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (staff_id, updated_at, academy_teacher_id),
    )


def get_teacher_name(conn: Any, teacher_id: int) -> str:
    row = conn.execute(
        "SELECT full_name FROM msi_v2.teachers WHERE id = %s LIMIT 1",
        (teacher_id,),
    ).fetchone()
    return str(row["full_name"] or "") if row else ""


def phase1_accounts_available(conn: Any) -> bool:
    try:
        row = conn.execute("SELECT to_regclass('msi_v2.accounts') AS table_name").fetchone()
    except Exception:
        return False
    return bool(row and row["table_name"])


def get_teacher_account_for_provisioning(conn: Any, *, login: str, staff_id: int) -> Any:
    return conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE lower(btrim(login)) = lower(btrim(%s))
           OR (legacy_source_table = 'msi_staff' AND legacy_source_id = %s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (login, staff_id),
    ).fetchone()


def update_teacher_account_for_provisioning(
    conn: Any, *, account_id: int, login: str, password_hash: str, full_name: str, staff_id: int, updated_at: str
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.accounts
        SET login = %s,
            password_hash = %s,
            role = 'teacher',
            status = 'active',
            full_name = %s,
            legacy_source_table = 'msi_staff',
            legacy_source_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (login, password_hash, full_name, staff_id, updated_at, account_id),
    )


def insert_teacher_account_for_provisioning(
    conn: Any, *, login: str, password_hash: str, full_name: str, staff_id: int, created_at: str
) -> int:
    inserted = conn.execute(
        """
        INSERT INTO msi_v2.accounts (
            login, password_hash, role, status, full_name,
            legacy_source_table, legacy_source_id, created_at, updated_at
        )
        VALUES (%s, %s, 'teacher', 'active', %s, 'msi_staff', %s, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (login, password_hash, full_name, staff_id, created_at, created_at),
    ).fetchone()
    return int(inserted["id"] or 0) if inserted else 0


def get_teacher_profile_for_provisioning(conn: Any, *, account_id: int, teacher_id: int, teacher_code: str) -> Any:
    return conn.execute(
        """
        SELECT id
        FROM msi_v2.teacher_profiles
        WHERE account_id = %s OR teacher_id = %s OR upper(btrim(teacher_code)) = upper(btrim(%s))
        ORDER BY id ASC
        LIMIT 1
        """,
        (account_id, teacher_id, teacher_code),
    ).fetchone()


def update_teacher_profile_for_provisioning(
    conn: Any, *, profile_id: int, account_id: int, teacher_id: int, teacher_code: str, legacy_login: str, updated_at: str
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_profiles
        SET account_id = %s,
            teacher_id = %s,
            teacher_code = %s,
            legacy_login = %s,
            status = 'active',
            updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (account_id, teacher_id, teacher_code, legacy_login, updated_at, profile_id),
    )


def insert_teacher_profile_for_provisioning(
    conn: Any, *, account_id: int, teacher_id: int, teacher_code: str, legacy_login: str, created_at: str
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_profiles (
            account_id, teacher_id, teacher_code, legacy_login, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'active', %s::timestamptz, %s::timestamptz)
        """,
        (account_id, teacher_id, teacher_code, legacy_login, created_at, created_at),
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
        SELECT id, academy_teacher_id, session_datetime::text AS session_datetime
        FROM msi_v2.academy_lesson_assignments
        WHERE id = %s
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
        SELECT id, academy_teacher_id, lesson_number, lesson_topic, evaluator_id
        FROM msi_v2.academy_lesson_assignments
        WHERE id = %s AND academy_teacher_id = %s
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
        SELECT id, subject_id, subject_program_id
        FROM msi_v2.academy_teachers
        WHERE id = %s
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


__all__ = [
    "activate_teacher_profile",
    "approve_academy_teacher_promotion",
    "connect_auth_db",
    "delete_assessment_row",
    "delete_academy_teacher_profile_row",
    "delete_academy_teacher_row",
    "delete_academy_teacher_staff_row",
    "delete_staff_profiles_for_delete",
    "delete_teacher_accounts_for_delete",
    "delete_teacher_profiles_for_delete",
    "ensure_teacher_academy_schema",
    "get_academy_teacher_delete_row",
    "get_academy_teacher_id",
    "get_academy_teacher_row_for_account",
    "get_academy_teacher_status",
    "get_academy_teacher_subject_id",
    "get_assessment_delete_row",
    "get_assignment_for_assessment",
    "get_assignment_schedule_row",
    "get_assignment_subject_id",
    "get_latest_assessment_for_assignment",
    "get_latest_assessment_for_teacher",
    "get_next_teacher_code",
    "get_subject_program",
    "get_teacher_account_for_provisioning",
    "get_teacher_auth_row_by_id",
    "get_teacher_by_full_name_row",
    "get_teacher_name",
    "get_teacher_profile_for_provisioning",
    "insert_academy_lesson_assignment",
    "insert_academy_teacher",
    "insert_assessment",
    "insert_teacher_account_for_provisioning",
    "insert_teacher_auth",
    "insert_teacher_profile_for_provisioning",
    "insert_teacher_profile_row",
    "list_academy_teacher_account_backfill_rows",
    "list_academy_teacher_rows",
    "list_teacher_account_ids_for_staff",
    "list_active_group_options",
    "list_active_subjects",
    "list_assessment_rows",
    "list_assignment_rows",
    "list_curriculum_items",
    "list_curriculum_lessons",
    "list_curriculum_programs",
    "list_hod_subject_scope_rows",
    "phase1_accounts_available",
    "set_teacher_group_assignment",
    "touch_academy_teacher",
    "update_academy_teacher_status",
    "update_academy_teacher_user_id",
    "update_assignment_schedule",
    "update_assignment_status",
    "update_teacher_account_for_provisioning",
    "update_teacher_profile_for_provisioning",
    "upsert_teacher_subject",
]
