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
               at.recruitment_candidate_id, at.account_onboarding_status,
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
          AND COALESCE(at.account_onboarding_status, 'complete') <> 'pending'
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
        SELECT id, password_hash, must_change_password
        FROM msi_v2.accounts
        WHERE (role = 'teacher' AND lower(btrim(login)) = lower(btrim(%s)))
           OR (role = 'teacher' AND legacy_source_table = 'msi_staff' AND legacy_source_id = %s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (login, staff_id),
    ).fetchone()


def update_teacher_account_for_provisioning(
    conn: Any, *, account_id: int, login: str, full_name: str, staff_id: int, updated_at: str
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.accounts
        SET login = %s,
            role = 'teacher',
            status = 'active',
            full_name = %s,
            legacy_source_table = 'msi_staff',
            legacy_source_id = %s,
            session_version = session_version + 1,
            updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (login, full_name, staff_id, updated_at, account_id),
    )


def insert_teacher_account_for_provisioning(
    conn: Any, *, login: str, password_hash: str, full_name: str, staff_id: int, created_at: str
) -> int:
    inserted = conn.execute(
        """
        INSERT INTO msi_v2.accounts (
            login, password_hash, role, status, full_name,
            legacy_source_table, legacy_source_id, must_change_password,
            session_version, created_at, updated_at
        )
        VALUES (%s, %s, 'teacher', 'active', %s, 'msi_staff', %s, false, 1, %s::timestamptz, %s::timestamptz)
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
