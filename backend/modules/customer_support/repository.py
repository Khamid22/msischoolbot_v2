"""SQL boundary for the Customer Support records desk."""

from __future__ import annotations

import json
from typing import Any


def get_staff_scope_row(conn, *, staff_id: int | None, account_id: int | None):
    return conn.execute(
        """
        SELECT staff.id, staff.school_scope
        FROM msi_v2.msi_staff staff
        LEFT JOIN msi_v2.staff_profiles profile ON profile.staff_id = staff.id
        WHERE (%s::bigint IS NOT NULL AND staff.id = %s)
           OR (%s::bigint IS NOT NULL AND profile.account_id = %s)
        ORDER BY CASE WHEN staff.id = %s THEN 0 ELSE 1 END, staff.id
        LIMIT 1
        """,
        (staff_id, staff_id, account_id, account_id, staff_id),
    ).fetchone()


def list_school_rows(conn):
    return conn.execute(
        """
        SELECT id, school_key, school_name, status
        FROM msi_v2.schools
        WHERE status = 'active'
        ORDER BY lower(school_name), id
        """
    ).fetchall()


def get_school_row(conn, school_id: int):
    return conn.execute(
        """
        SELECT id, school_key, school_name, status
        FROM msi_v2.schools
        WHERE id = %s
        """,
        (int(school_id),),
    ).fetchone()


def search_record_rows(
    conn,
    *,
    query: str,
    kind: str,
    status: str,
    school_id: int | None,
    exclude_parent_id: int | None,
    allowed_school_ids: list[int],
    all_schools: bool,
    cursor_name: str,
    cursor_kind: str,
    cursor_id: int,
    limit: int,
):
    pattern = f"%{str(query or '').strip()}%"
    return conn.execute(
        """
        WITH student_records AS (
            SELECT
                'student'::text AS kind,
                st.id,
                st.full_name AS display_name,
                st.student_code AS secondary,
                COALESCE(account.phone, '') AS phone,
                COALESCE(link.telegram_username, '') AS telegram_username,
                st.status,
                st.school_id,
                COALESCE(school.school_name, 'School not set') AS school_name,
                st.version,
                COALESCE(balance.outstanding, 0)::float AS outstanding,
                COALESCE(parent_count.linked_count, 0)::int AS linked_count,
                st.updated_at
            FROM msi_v2.students st
            LEFT JOIN msi_v2.schools school ON school.id = st.school_id
            LEFT JOIN msi_v2.student_profiles profile ON profile.student_id = st.id
            LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
            LEFT JOIN LATERAL (
                SELECT telegram.telegram_username
                FROM msi_v2.account_telegram_links telegram
                WHERE telegram.account_id = account.id AND telegram.status = 'active'
                ORDER BY telegram.linked_at DESC
                LIMIT 1
            ) link ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(payment.amount) FILTER (
                    WHERE payment.voided_at IS NULL
                      AND payment.paid_at IS NULL
                      AND payment.status <> 'paid'
                ), 0) AS outstanding
                FROM msi_v2.payments payment
                WHERE payment.student_id = st.id
            ) balance ON true
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS linked_count
                FROM msi_v2.parent_student_links family
                WHERE family.student_id = st.id AND family.status = 'active'
            ) parent_count ON true
            WHERE (%s OR st.school_id = ANY(%s::bigint[]))
              AND (%s::bigint IS NULL OR st.school_id = %s)
              AND (%s = 'all' OR st.status = %s)
              AND (
                    %s::bigint IS NULL
                    OR NOT EXISTS (
                        SELECT 1
                        FROM msi_v2.parent_student_links existing_family
                        WHERE existing_family.parent_id = %s
                          AND existing_family.student_id = st.id
                          AND existing_family.status = 'active'
                    )
              )
              AND (
                    %s = ''
                    OR st.full_name ILIKE %s
                    OR st.student_code ILIKE %s
                    OR COALESCE(account.phone, '') ILIKE %s
                    OR COALESCE(link.telegram_username, '') ILIKE %s
                    OR COALESCE(school.school_name, '') ILIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM msi_v2.parent_student_links family
                        JOIN msi_v2.parents parent ON parent.id = family.parent_id
                        WHERE family.student_id = st.id
                          AND family.status = 'active'
                          AND (
                              parent.display_name ILIKE %s
                              OR parent.phone ILIKE %s
                              OR parent.telegram_username ILIKE %s
                          )
                    )
              )
        ),
        parent_records AS (
            SELECT
                'parent'::text AS kind,
                parent.id,
                COALESCE(NULLIF(parent.display_name, ''), 'Unnamed parent') AS display_name,
                COALESCE(NULLIF(parent.phone, ''), NULLIF(parent.telegram_username, ''), 'No contact') AS secondary,
                parent.phone,
                parent.telegram_username,
                parent.status,
                MIN(st.school_id) AS school_id,
                COALESCE(string_agg(DISTINCT school.school_name, ', ' ORDER BY school.school_name), 'School not set') AS school_name,
                parent.version,
                COALESCE(SUM(payment_balance.outstanding), 0)::float AS outstanding,
                COUNT(DISTINCT st.id)::int AS linked_count,
                parent.updated_at
            FROM msi_v2.parents parent
            JOIN msi_v2.parent_student_links family
              ON family.parent_id = parent.id AND family.status = 'active'
            JOIN msi_v2.students st ON st.id = family.student_id
            LEFT JOIN msi_v2.schools school ON school.id = st.school_id
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(payment.amount) FILTER (
                    WHERE payment.voided_at IS NULL
                      AND payment.paid_at IS NULL
                      AND payment.status <> 'paid'
                ), 0) AS outstanding
                FROM msi_v2.payments payment
                WHERE payment.student_id = st.id
            ) payment_balance ON true
            WHERE (%s OR st.school_id = ANY(%s::bigint[]))
              AND (%s::bigint IS NULL OR st.school_id = %s)
              AND (%s = 'all' OR parent.status = %s)
            GROUP BY parent.id
            HAVING (
                %s = ''
                OR parent.display_name ILIKE %s
                OR parent.phone ILIKE %s
                OR parent.telegram_username ILIKE %s
                OR string_agg(st.full_name, ' ') ILIKE %s
                OR string_agg(st.student_code, ' ') ILIKE %s
                OR string_agg(COALESCE(school.school_name, ''), ' ') ILIKE %s
            )
        ),
        combined AS (
            SELECT * FROM student_records WHERE %s IN ('all', 'student')
            UNION ALL
            SELECT * FROM parent_records WHERE %s IN ('all', 'parent')
        )
        SELECT *
        FROM combined
        WHERE (%s = '' OR (lower(display_name), kind, id) > (%s, %s, %s))
        ORDER BY lower(display_name), kind, id
        LIMIT %s
        """,
        (
            all_schools,
            allowed_school_ids,
            school_id,
            school_id,
            status,
            status,
            exclude_parent_id,
            exclude_parent_id,
            query,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            all_schools,
            allowed_school_ids,
            school_id,
            school_id,
            status,
            status,
            query,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            kind,
            kind,
            cursor_name,
            cursor_name,
            cursor_kind,
            int(cursor_id),
            int(limit),
        ),
    ).fetchall()


def get_student_row(conn, student_id: int):
    return conn.execute(
        """
        SELECT st.id, st.legacy_student_row_id, st.student_code, st.full_name,
               st.school_id, COALESCE(school.school_name, '') AS school_name,
               COALESCE(school.school_key, '') AS school_key,
               st.photo_url, st.profile_description, st.status, st.version,
               st.created_at, st.updated_at,
               profile.account_id, COALESCE(account.phone, '') AS phone,
               COALESCE(account.login, st.student_code) AS login,
               COALESCE(account.status, st.status) AS account_status,
               COALESCE(account.must_change_password, false) AS must_change_password,
               account.last_login_at,
               COALESCE(telegram.telegram_username, '') AS telegram_username
        FROM msi_v2.students st
        LEFT JOIN msi_v2.schools school ON school.id = st.school_id
        LEFT JOIN msi_v2.student_profiles profile ON profile.student_id = st.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
        LEFT JOIN LATERAL (
            SELECT link.telegram_username
            FROM msi_v2.account_telegram_links link
            WHERE link.account_id = account.id AND link.status = 'active'
            ORDER BY link.linked_at DESC
            LIMIT 1
        ) telegram ON true
        WHERE st.id = %s
        """,
        (int(student_id),),
    ).fetchone()


def list_student_enrollment_rows(conn, student_id: int):
    return conn.execute(
        """
        SELECT gs.legacy_enrollment_id AS id, gs.enrollment_status AS status,
               gs.joined_at, gs.left_at, g.id AS group_id, g.group_name,
               subj.id AS subject_id, subj.subject_name,
               COALESCE(hw.homework_average, 0)::float AS homework_average,
               COALESCE(ex.exam_average, 0)::float AS exam_average,
               COALESCE(att.present_count, 0)::int AS present_count,
               COALESCE(att.absent_count, 0)::int AS absent_count,
               COALESCE(att.justified_count, 0)::int AS justified_count
        FROM msi_v2.group_students gs
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs program ON program.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = program.subject_id
        LEFT JOIN LATERAL (
            SELECT AVG(score) AS homework_average
            FROM msi_v2.homework_scores score
            WHERE score.group_id = gs.group_id AND score.student_id = gs.student_id
        ) hw ON true
        LEFT JOIN LATERAL (
            SELECT AVG(score) AS exam_average
            FROM msi_v2.exam_results result
            WHERE result.group_id = gs.group_id AND result.student_id = gs.student_id
        ) ex ON true
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) FILTER (WHERE lower(record.attendance_status) = 'present') AS present_count,
                COUNT(*) FILTER (WHERE lower(record.attendance_status) = 'absent') AS absent_count,
                COUNT(*) FILTER (WHERE lower(record.attendance_status) IN ('justified', 'justified absent')) AS justified_count
            FROM msi_v2.attendance_records record
            WHERE record.group_id = gs.group_id AND record.student_id = gs.student_id
        ) att ON true
        WHERE gs.student_id = %s
        ORDER BY CASE WHEN gs.enrollment_status = 'active' THEN 0 ELSE 1 END,
                 lower(subj.subject_name), lower(g.group_name)
        """,
        (int(student_id),),
    ).fetchall()


def list_student_parent_rows(conn, student_id: int):
    return conn.execute(
        """
        SELECT parent.id, parent.display_name, parent.phone, parent.telegram_username,
               parent.preferred_language, parent.status, parent.version,
               family.relationship, family.created_at AS linked_at
        FROM msi_v2.parent_student_links family
        JOIN msi_v2.parents parent ON parent.id = family.parent_id
        WHERE family.student_id = %s AND family.status = 'active'
        ORDER BY lower(parent.display_name), parent.id
        """,
        (int(student_id),),
    ).fetchall()


def get_parent_row(conn, parent_id: int):
    return conn.execute(
        """
        SELECT parent.id, parent.display_name, parent.phone, parent.telegram_user_id,
               parent.telegram_username, parent.preferred_language, parent.status,
               parent.version, parent.created_at, parent.updated_at,
               profile.account_id, COALESCE(account.status, parent.status) AS account_status,
               account.last_login_at
        FROM msi_v2.parents parent
        LEFT JOIN msi_v2.parent_profiles profile ON profile.parent_id = parent.id
        LEFT JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE parent.id = %s
        """,
        (int(parent_id),),
    ).fetchone()


def list_parent_student_rows(
    conn, *, parent_id: int, allowed_school_ids: list[int], all_schools: bool
):
    return conn.execute(
        """
        SELECT st.id, st.legacy_student_row_id, st.student_code, st.full_name,
               st.status, st.school_id, COALESCE(school.school_name, '') AS school_name,
               family.relationship, family.created_at AS linked_at,
               COALESCE(balance.outstanding, 0)::float AS outstanding
        FROM msi_v2.parent_student_links family
        JOIN msi_v2.students st ON st.id = family.student_id
        LEFT JOIN msi_v2.schools school ON school.id = st.school_id
        LEFT JOIN LATERAL (
            SELECT COALESCE(SUM(payment.amount) FILTER (
                WHERE payment.voided_at IS NULL
                  AND payment.paid_at IS NULL
                  AND payment.status <> 'paid'
            ), 0) AS outstanding
            FROM msi_v2.payments payment
            WHERE payment.student_id = st.id
        ) balance ON true
        WHERE family.parent_id = %s
          AND family.status = 'active'
          AND (%s OR st.school_id = ANY(%s::bigint[]))
        ORDER BY lower(st.full_name), st.id
        """,
        (int(parent_id), all_schools, allowed_school_ids),
    ).fetchall()


def count_parent_hidden_links(
    conn, *, parent_id: int, allowed_school_ids: list[int], all_schools: bool
):
    if all_schools:
        return 0
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM msi_v2.parent_student_links family
        JOIN msi_v2.students st ON st.id = family.student_id
        WHERE family.parent_id = %s
          AND family.status = 'active'
          AND NOT (st.school_id = ANY(%s::bigint[]))
        """,
        (int(parent_id), allowed_school_ids),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def list_payment_rows(conn, *, student_id: int):
    return conn.execute(
        """
        SELECT payment.id, payment.student_id, payment.group_id,
               subject.id AS subject_id, COALESCE(subject.subject_name, '') AS subject,
               payment.month_label, payment.amount::float AS amount, payment.currency,
               payment.status, payment.due_date, payment.paid_at, payment.notes,
               payment.version, payment.voided_at, payment.void_reason,
               payment.created_at, payment.updated_at
        FROM msi_v2.payments payment
        LEFT JOIN msi_v2.groups g ON g.id = payment.group_id
        LEFT JOIN msi_v2.subject_programs program ON program.id = g.program_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE payment.student_id = %s
        ORDER BY payment.voided_at NULLS FIRST,
                 COALESCE(payment.due_date, DATE '9999-12-31'), payment.id
        """,
        (int(student_id),),
    ).fetchall()


def get_payment_row(conn, payment_id: int):
    return conn.execute(
        """
        SELECT payment.*, student.school_id,
               subject.id AS subject_id, COALESCE(subject.subject_name, '') AS subject
        FROM msi_v2.payments payment
        JOIN msi_v2.students student ON student.id = payment.student_id
        LEFT JOIN msi_v2.groups g ON g.id = payment.group_id
        LEFT JOIN msi_v2.subject_programs program ON program.id = g.program_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE payment.id = %s
        """,
        (int(payment_id),),
    ).fetchone()


def list_audit_rows(conn, *, entity_types: list[str], entity_id: int, limit: int = 50):
    return conn.execute(
        """
        SELECT audit.id, audit.event_type, audit.entity_type, audit.entity_id,
               audit.detail_json, audit.created_at,
               COALESCE(account.full_name, staff.display_name, staff.login, 'System') AS actor
        FROM msi_v2.audit_events audit
        LEFT JOIN msi_v2.accounts account ON account.id = audit.actor_account_id
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = audit.actor_staff_id
        WHERE audit.entity_type = ANY(%s::text[])
          AND audit.entity_id = %s
        ORDER BY audit.created_at DESC, audit.id DESC
        LIMIT %s
        """,
        (entity_types, int(entity_id), max(1, min(int(limit), 100))),
    ).fetchall()


def list_student_codes(conn, prefix: str):
    return conn.execute(
        """
        SELECT student_code
        FROM msi_v2.students
        WHERE upper(student_code) LIKE upper(%s)
        """,
        (f"{prefix}%",),
    ).fetchall()


def next_legacy_student_id(conn):
    row = conn.execute(
        """
        SELECT GREATEST(
            COALESCE(MAX(legacy_student_row_id), 0) + 1,
            9000000000
        ) AS next_id
        FROM msi_v2.students
        """
    ).fetchone()
    return int(row["next_id"])


def insert_student(
    conn,
    *,
    student_code: str,
    full_name: str,
    school_id: int,
    phone: str,
    photo_url: str,
    profile_description: str,
    legacy_student_row_id: int,
):
    row = conn.execute(
        """
        INSERT INTO msi_v2.students (
            student_code, full_name, school_id, photo_url, profile_description,
            status, legacy_student_row_id, version, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, 'active', %s, 1, now(), now())
        RETURNING id
        """,
        (
            student_code,
            full_name,
            int(school_id),
            photo_url,
            profile_description,
            int(legacy_student_row_id),
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_student_account_phone(conn, *, student_id: int, phone: str):
    conn.execute(
        """
        UPDATE msi_v2.accounts account
        SET phone = %s, updated_at = now()
        FROM msi_v2.student_profiles profile
        WHERE profile.student_id = %s AND account.id = profile.account_id
        """,
        (phone, int(student_id)),
    )


def update_student_record(
    conn,
    *,
    student_id: int,
    expected_version: int,
    full_name: str,
    school_id: int,
    phone: str,
    photo_url: str,
    profile_description: str,
    status: str,
):
    row = conn.execute(
        """
        UPDATE msi_v2.students
        SET full_name = %s, school_id = %s, photo_url = %s,
            profile_description = %s, status = %s,
            version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id, version
        """,
        (
            full_name,
            int(school_id),
            photo_url,
            profile_description,
            status,
            int(student_id),
            int(expected_version),
        ),
    ).fetchone()
    if not row:
        return None
    conn.execute(
        """
        UPDATE msi_v2.accounts account
        SET full_name = %s, phone = %s,
            status = CASE WHEN %s = 'active' THEN 'active' ELSE 'disabled' END,
            session_version = CASE
                WHEN account.status = CASE WHEN %s = 'active' THEN 'active' ELSE 'disabled' END
                    THEN session_version
                ELSE session_version + 1
            END,
            updated_at = now()
        FROM msi_v2.student_profiles profile
        WHERE profile.student_id = %s AND account.id = profile.account_id
        """,
        (full_name, phone, status, status, int(student_id)),
    )
    conn.execute(
        """
        UPDATE msi_v2.student_profiles
        SET school_id = %s,
            status = CASE WHEN %s = 'active' THEN 'active' ELSE 'disabled' END,
            updated_at = now()
        WHERE student_id = %s
        """,
        (int(school_id), status, int(student_id)),
    )
    return dict(row)


def list_active_enrollment_blockers(conn, student_id: int):
    return conn.execute(
        """
        SELECT g.id AS group_id, g.group_name, subject.subject_name
        FROM msi_v2.group_students enrollment
        JOIN msi_v2.groups g ON g.id = enrollment.group_id
        JOIN msi_v2.subject_programs program ON program.id = g.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE enrollment.student_id = %s AND enrollment.enrollment_status = 'active'
        ORDER BY lower(subject.subject_name), lower(g.group_name)
        """,
        (int(student_id),),
    ).fetchall()


def set_student_lifecycle(
    conn, *, student_id: int, expected_version: int, status: str
):
    row = conn.execute(
        """
        UPDATE msi_v2.students
        SET status = %s, version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id, version
        """,
        (status, int(student_id), int(expected_version)),
    ).fetchone()
    if not row:
        return None
    account_status = "active" if status == "active" else "archived"
    conn.execute(
        """
        UPDATE msi_v2.accounts account
        SET status = %s, session_version = session_version + 1, updated_at = now()
        FROM msi_v2.student_profiles profile
        WHERE profile.student_id = %s AND account.id = profile.account_id
        """,
        (account_status, int(student_id)),
    )
    conn.execute(
        """
        UPDATE msi_v2.student_profiles
        SET status = %s, updated_at = now()
        WHERE student_id = %s
        """,
        (account_status, int(student_id)),
    )
    return dict(row)


def bump_student_version(conn, *, student_id: int, expected_version: int):
    row = conn.execute(
        """
        UPDATE msi_v2.students
        SET version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id, version
        """,
        (int(student_id), int(expected_version)),
    ).fetchone()
    return dict(row) if row else None


def update_parent_record(
    conn,
    *,
    parent_id: int,
    expected_version: int,
    display_name: str,
    phone: str,
    telegram_username: str,
    preferred_language: str,
    status: str,
):
    row = conn.execute(
        """
        UPDATE msi_v2.parents
        SET display_name = %s, phone = %s, telegram_username = %s,
            preferred_language = %s, status = %s,
            version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id, version
        """,
        (
            display_name,
            phone,
            telegram_username,
            preferred_language,
            status,
            int(parent_id),
            int(expected_version),
        ),
    ).fetchone()
    if not row:
        return None
    conn.execute(
        """
        UPDATE msi_v2.accounts account
        SET full_name = %s, phone = %s,
            status = CASE WHEN %s = 'active' THEN 'active' ELSE 'disabled' END,
            session_version = CASE
                WHEN %s = 'active' THEN session_version
                ELSE session_version + 1
            END,
            updated_at = now()
        FROM msi_v2.parent_profiles profile
        WHERE profile.parent_id = %s AND account.id = profile.account_id
        """,
        (display_name, phone, status, status, int(parent_id)),
    )
    conn.execute(
        """
        UPDATE msi_v2.parent_profiles
        SET status = CASE WHEN %s = 'active' THEN 'active' ELSE 'disabled' END,
            updated_at = now()
        WHERE parent_id = %s
        """,
        (status, int(parent_id)),
    )
    conn.execute(
        """
        UPDATE msi_v2.account_telegram_links link
        SET telegram_username = NULLIF(%s, ''), linked_at = now()
        FROM msi_v2.parent_profiles profile
        WHERE profile.parent_id = %s
          AND link.account_id = profile.account_id
          AND link.status = 'active'
        """,
        (telegram_username, int(parent_id)),
    )
    return dict(row)


def bump_parent_version(conn, *, parent_id: int, expected_version: int):
    row = conn.execute(
        """
        UPDATE msi_v2.parents
        SET version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id, version
        """,
        (int(parent_id), int(expected_version)),
    ).fetchone()
    return dict(row) if row else None


def insert_parent_student_link(conn, *, parent_id: int, student_id: int):
    row = conn.execute(
        """
        INSERT INTO msi_v2.parent_student_links AS existing_family (
            parent_id, student_id, relationship, status, created_at
        ) VALUES (%s, %s, 'parent', 'active', now())
        ON CONFLICT (parent_id, student_id)
        DO UPDATE SET status = 'active', created_at = now()
        WHERE existing_family.status <> 'active'
        RETURNING parent_id
        """,
        (int(parent_id), int(student_id)),
    ).fetchone()
    return bool(row)


def remove_parent_student_link(conn, *, parent_id: int, student_id: int):
    result = conn.execute(
        """
        UPDATE msi_v2.parent_student_links
        SET status = 'inactive'
        WHERE parent_id = %s AND student_id = %s AND status = 'active'
        """,
        (int(parent_id), int(student_id)),
    )
    return int(result.rowcount or 0)


def find_active_group_for_subject(conn, *, student_id: int, subject_id: int):
    return conn.execute(
        """
        SELECT enrollment.group_id
        FROM msi_v2.group_students enrollment
        JOIN msi_v2.groups g ON g.id = enrollment.group_id
        JOIN msi_v2.subject_programs program ON program.id = g.program_id
        WHERE enrollment.student_id = %s
          AND enrollment.enrollment_status = 'active'
          AND program.subject_id = %s
        ORDER BY enrollment.joined_at DESC, enrollment.group_id
        LIMIT 1
        """,
        (int(student_id), int(subject_id)),
    ).fetchone()


def insert_payment(
    conn,
    *,
    student_id: int,
    group_id: int,
    month_label: str,
    amount: float,
    currency: str,
    due_date: str,
    paid_at: str,
    notes: str,
    actor_staff_id: int | None,
):
    row = conn.execute(
        """
        INSERT INTO msi_v2.payments (
            student_id, group_id, month_label, amount, currency, status,
            due_date, paid_at, notes, created_by_staff_id, version,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            CASE WHEN NULLIF(%s, '') IS NULL THEN 'due' ELSE 'paid' END,
            NULLIF(%s, '')::date, NULLIF(%s, '')::timestamptz,
            %s, %s, 1, now(), now()
        ) RETURNING id
        """,
        (
            int(student_id),
            int(group_id),
            month_label,
            float(amount),
            currency,
            paid_at,
            due_date,
            paid_at,
            notes,
            actor_staff_id,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_payment_record(
    conn,
    *,
    payment_id: int,
    expected_version: int,
    month_label: str,
    amount: float,
    currency: str,
    due_date: str,
    notes: str,
):
    return conn.execute(
        """
        UPDATE msi_v2.payments
        SET month_label = %s, amount = %s, currency = %s,
            due_date = NULLIF(%s, '')::date, notes = %s,
            version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s AND voided_at IS NULL
        RETURNING id, version
        """,
        (
            month_label,
            float(amount),
            currency,
            due_date,
            notes,
            int(payment_id),
            int(expected_version),
        ),
    ).fetchone()


def settle_payment(
    conn,
    *,
    payment_id: int,
    expected_version: int,
    paid: bool,
    paid_at: str,
):
    return conn.execute(
        """
        UPDATE msi_v2.payments
        SET status = CASE WHEN %s THEN 'paid' ELSE 'due' END,
            paid_at = CASE WHEN %s THEN COALESCE(NULLIF(%s, '')::timestamptz, now()) ELSE NULL END,
            version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s AND voided_at IS NULL
        RETURNING id, version
        """,
        (bool(paid), bool(paid), paid_at, int(payment_id), int(expected_version)),
    ).fetchone()


def void_payment(
    conn,
    *,
    payment_id: int,
    expected_version: int,
    reason: str,
    actor_account_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.payments
        SET status = 'voided', voided_at = now(), voided_by_account_id = %s,
            void_reason = %s, version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s AND voided_at IS NULL
        RETURNING id, version
        """,
        (actor_account_id, reason, int(payment_id), int(expected_version)),
    ).fetchone()


def insert_audit_event(
    conn,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int,
    detail: dict[str, Any],
    actor_staff_id: int | None,
    actor_account_id: int | None,
):
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, actor_account_id, event_type,
            entity_type, entity_id, detail_json, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, now())
        """,
        (
            actor_staff_id,
            actor_account_id,
            event_type,
            entity_type,
            int(entity_id),
            json.dumps(detail, ensure_ascii=False, default=str),
        ),
    )


__all__ = [name for name in globals() if not name.startswith("_")]
