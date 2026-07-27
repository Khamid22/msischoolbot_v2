"""SQL for the school-scoped Teacher Support directory."""

from __future__ import annotations

from backend.core.unit_of_work import Connection

_TEACHER_SUPPORT_CTE = """
    WITH teacher_support AS (
        SELECT
            teacher.id AS teacher_id,
            COALESCE(
                NULLIF(account.full_name, ''),
                NULLIF(teacher.full_name, ''),
                'Unnamed teacher'
            ) AS full_name,
            COALESCE(
                NULLIF(account.login, ''),
                NULLIF(staff.login, ''),
                NULLIF(profile.teacher_code, ''),
                ''
            ) AS login,
            COALESCE(
                NULLIF(account.phone, ''),
                NULLIF(teacher.phone, ''),
                NULLIF(staff.phone, ''),
                ''
            ) AS phone,
            COALESCE(
                NULLIF(telegram.telegram_username, ''),
                NULLIF(teacher.telegram_username, ''),
                NULLIF(staff.telegram_username, ''),
                ''
            ) AS telegram_username,
            COALESCE(
                NULLIF(profile.status, ''),
                NULLIF(account.status, ''),
                NULLIF(staff.status, ''),
                NULLIF(teacher.status, ''),
                'disabled'
            ) AS account_status,
            COALESCE(schools.school_ids, ARRAY[]::bigint[]) AS school_ids,
            COALESCE(schools.school_names, ARRAY[]::text[]) AS school_names,
            COALESCE(subjects.subject_names, ARRAY[]::text[]) AS subject_names,
            COALESCE(groups.group_ids, ARRAY[]::bigint[]) AS assigned_group_ids,
            COALESCE(groups.group_names, ARRAY[]::text[]) AS assigned_group_names
        FROM msi_v2.teachers teacher
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.teacher_id = teacher.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
        LEFT JOIN LATERAL (
            SELECT candidate.login, candidate.phone, candidate.telegram_username, candidate.status
            FROM msi_v2.msi_staff candidate
            WHERE candidate.teacher_id = teacher.id
              AND lower(candidate.role) = 'teacher'
            ORDER BY
                CASE WHEN lower(candidate.status) = 'active' THEN 0 ELSE 1 END,
                candidate.id
            LIMIT 1
        ) staff ON true
        LEFT JOIN LATERAL (
            SELECT link.telegram_username
            FROM msi_v2.account_telegram_links link
            WHERE link.account_id = account.id
              AND link.status = 'active'
            ORDER BY link.linked_at DESC, link.id DESC
            LIMIT 1
        ) telegram ON true
        LEFT JOIN LATERAL (
            SELECT
                array_agg(DISTINCT school.id ORDER BY school.id) AS school_ids,
                array_agg(DISTINCT school.school_name ORDER BY school.school_name) AS school_names
            FROM (
                SELECT profile.school_id
                WHERE profile.school_id IS NOT NULL
                UNION
                SELECT assigned_group.school_id
                FROM msi_v2.group_teachers assignment
                JOIN msi_v2.groups assigned_group ON assigned_group.id = assignment.group_id
                WHERE assignment.teacher_id = teacher.id
                  AND assignment.status = 'active'
                  AND assigned_group.status = 'active'
            ) school_assignment
            JOIN msi_v2.schools school ON school.id = school_assignment.school_id
        ) schools ON true
        LEFT JOIN LATERAL (
            SELECT
                array_agg(DISTINCT assigned_group.id ORDER BY assigned_group.id) AS group_ids,
                array_agg(
                    DISTINCT assigned_group.group_name
                    ORDER BY assigned_group.group_name
                ) AS group_names
            FROM msi_v2.group_teachers assignment
            JOIN msi_v2.groups assigned_group ON assigned_group.id = assignment.group_id
            WHERE assignment.teacher_id = teacher.id
              AND assignment.status = 'active'
              AND assigned_group.status = 'active'
        ) groups ON true
        LEFT JOIN LATERAL (
            SELECT array_agg(
                DISTINCT subject.subject_name
                ORDER BY subject.subject_name
            ) AS subject_names
            FROM msi_v2.teacher_subjects teacher_subject
            JOIN msi_v2.subjects subject ON subject.id = teacher_subject.subject_id
            WHERE teacher_subject.teacher_id = teacher.id
              AND teacher_subject.status = 'active'
              AND subject.status = 'active'
        ) subjects ON true
    )
"""


def search_teacher_support_rows(
    conn: Connection,
    *,
    search_text: str,
    status: str,
    selected_school_id: int | None,
    allowed_school_ids: tuple[int, ...],
    all_schools: bool,
    cursor_name: str,
    cursor_id: int,
    limit: int,
):
    pattern = f"%{search_text.strip()}%"
    return conn.execute(
        f"""
        {_TEACHER_SUPPORT_CTE}
        SELECT *
        FROM teacher_support
        WHERE (%s OR school_ids && %s::bigint[])
          AND (%s::bigint IS NULL OR %s = ANY(school_ids))
          AND (%s = 'all' OR lower(account_status) = %s)
          AND (
                %s = ''
                OR full_name ILIKE %s
                OR login ILIKE %s
                OR phone ILIKE %s
                OR telegram_username ILIKE %s
                OR EXISTS (
                    SELECT 1
                    FROM unnest(school_names || subject_names || assigned_group_names) searchable
                    WHERE searchable ILIKE %s
                )
          )
          AND (
                %s = ''
                OR lower(full_name) > %s
                OR (lower(full_name) = %s AND teacher_id > %s)
          )
        ORDER BY lower(full_name), teacher_id
        LIMIT %s
        """,
        (
            all_schools,
            list(allowed_school_ids),
            selected_school_id,
            selected_school_id,
            status,
            status,
            search_text.strip(),
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            cursor_name,
            cursor_name,
            cursor_name,
            cursor_id,
            limit,
        ),
    ).fetchall()


def get_teacher_support_row(
    conn: Connection,
    *,
    teacher_id: int,
    allowed_school_ids: tuple[int, ...],
    all_schools: bool,
):
    return conn.execute(
        f"""
        {_TEACHER_SUPPORT_CTE}
        SELECT *
        FROM teacher_support
        WHERE teacher_id = %s
          AND (%s OR school_ids && %s::bigint[])
        LIMIT 1
        """,
        (teacher_id, all_schools, list(allowed_school_ids)),
    ).fetchone()


__all__ = ["get_teacher_support_row", "search_teacher_support_rows"]
