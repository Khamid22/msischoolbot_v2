"""SQL owned by the canonical account identity domain."""

from __future__ import annotations

import json
from typing import Any


ACCOUNT_COLUMNS = """
    id, login, password_hash, role, status, full_name, phone,
    legacy_source_table, legacy_source_id, must_change_password,
    password_changed_at, last_login_at, session_version
"""


def get_account_by_login_row(conn: Any, login: str) -> Any:
    return conn.execute(
        f"""
        SELECT {ACCOUNT_COLUMNS}
        FROM msi_v2.accounts
        WHERE lower(btrim(login)) = lower(btrim(%s))
        LIMIT 1
        """,
        (login,),
    ).fetchone()


def get_account_by_id_row(conn: Any, account_id: int, *, for_update: bool = False) -> Any:
    lock_clause = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT {ACCOUNT_COLUMNS}
        FROM msi_v2.accounts
        WHERE id = %s
        LIMIT 1{lock_clause}
        """,
        (int(account_id),),
    ).fetchone()


def get_student_profile_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT sp.id AS profile_id, sp.account_id, sp.student_id, sp.school_id,
               sp.student_code, sp.class_id, sp.status AS profile_status,
               st.id AS canonical_student_id,
               st.legacy_student_row_id,
               st.full_name,
               COALESCE(NULLIF(st.student_code, ''), sp.student_code) AS current_student_code,
               COALESCE(sch.school_key, '') AS school_code,
               COALESCE(
                   (
                       SELECT min(gs.legacy_public_dashboard_id)
                       FROM msi_v2.group_students gs
                       WHERE gs.student_id = st.id
                         AND gs.enrollment_status = 'active'
                         AND gs.legacy_public_dashboard_id IS NOT NULL
                   ),
                   st.legacy_public_dashboard_id
               ) AS enrollment_id
        FROM msi_v2.student_profiles sp
        JOIN msi_v2.students st ON st.id = sp.student_id
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        WHERE sp.account_id = %s
        LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def get_parent_profile_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT pp.id AS profile_id, pp.account_id, pp.parent_id,
               pp.telegram_username, pp.status AS profile_status,
               p.display_name AS full_name, p.telegram_user_id
        FROM msi_v2.parent_profiles pp
        JOIN msi_v2.parents p ON p.id = pp.parent_id
        WHERE pp.account_id = %s
        LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def get_staff_profile_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT sp.id AS profile_id, sp.account_id, sp.staff_id, sp.job_title,
               sp.department, sp.status AS profile_status,
               staff.login AS staff_login,
               staff.role AS legacy_staff_role,
               CASE WHEN lower(COALESCE(staff.role, '')) = 'owner' THEN 1 ELSE 0 END AS is_owner
        FROM msi_v2.staff_profiles sp
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = sp.staff_id
        WHERE sp.account_id = %s
        LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def get_teacher_profile_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT tp.id AS profile_id, tp.account_id, tp.teacher_id, tp.teacher_code,
               tp.status AS profile_status,
               account.full_name AS full_name,
               account.legacy_source_id AS staff_id
        FROM msi_v2.teacher_profiles tp
        LEFT JOIN msi_v2.accounts account ON account.id = tp.account_id
        WHERE tp.account_id = %s
        LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def get_account_telegram_link_row(conn: Any, telegram_user_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, account_id, telegram_user_id, telegram_username, status
        FROM msi_v2.account_telegram_links
        WHERE telegram_user_id = %s
        LIMIT 1
        """,
        (int(telegram_user_id),),
    ).fetchone()


def mark_account_login(conn: Any, account_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.accounts
        SET last_login_at = now(), updated_at = now()
        WHERE id = %s
        """,
        (int(account_id),),
    )


def change_account_password(
    conn: Any,
    *,
    account_id: int,
    password_hash: str,
    must_change_password: bool,
) -> int:
    row = conn.execute(
        """
        UPDATE msi_v2.accounts
        SET password_hash = %s,
            must_change_password = %s,
            password_changed_at = now(),
            session_version = session_version + 1,
            updated_at = now()
        WHERE id = %s
        RETURNING session_version
        """,
        (password_hash, bool(must_change_password), int(account_id)),
    ).fetchone()
    return int(row["session_version"] or 0) if row else 0


def reset_account_password(
    conn: Any,
    *,
    account_id: int,
    password_hash: str,
) -> int:
    """Replace a forgotten password and revoke existing account sessions."""

    row = conn.execute(
        """
        UPDATE msi_v2.accounts
        SET password_hash = %s,
            must_change_password = true,
            password_changed_at = NULL,
            session_version = session_version + 1,
            updated_at = now()
        WHERE id = %s
        RETURNING session_version
        """,
        (password_hash, int(account_id)),
    ).fetchone()
    return int(row["session_version"] or 0) if row else 0


def insert_account_audit_event(
    conn: Any,
    *,
    actor_account_id: int | None,
    event_type: str,
    entity_account_id: int,
    detail: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_account_id, event_type, entity_type, entity_id, detail_json, created_at
        )
        VALUES (%s, %s, 'account', %s, %s::jsonb, now())
        """,
        (
            int(actor_account_id) if actor_account_id else None,
            str(event_type),
            int(entity_account_id),
            json.dumps(detail or {}, ensure_ascii=False),
        ),
    )


def get_student_account_by_legacy_id_row(
    conn: Any,
    student_row_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock_clause = " FOR UPDATE OF account" if for_update else ""
    return conn.execute(
        f"""
        SELECT account.*, st.legacy_student_row_id
        FROM msi_v2.students st
        JOIN msi_v2.student_profiles profile ON profile.student_id = st.id
        JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE st.legacy_student_row_id = %s
        LIMIT 1{lock_clause}
        """,
        (int(student_row_id),),
    ).fetchone()


def find_student_account_row(conn: Any, *, student_id: int, login: str) -> Any:
    return conn.execute(
        f"""
        SELECT DISTINCT {', '.join(f'account.{column.strip()}' for column in ACCOUNT_COLUMNS.split(','))}
        FROM msi_v2.accounts account
        LEFT JOIN msi_v2.student_profiles profile ON profile.account_id = account.id
        WHERE profile.student_id = %s
           OR (account.legacy_source_table = 'students' AND account.legacy_source_id = %s)
           OR (account.role = 'student' AND lower(btrim(account.login)) = lower(btrim(%s)))
        ORDER BY account.id
        LIMIT 1
        """,
        (int(student_id), int(student_id), login),
    ).fetchone()


def save_student_account(
    conn: Any,
    *,
    account_id: int,
    student_id: int,
    login: str,
    password_hash: str,
    full_name: str,
    school_id: int | None,
    status: str,
) -> int:
    if account_id > 0:
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s,
                password_hash = %s,
                role = 'student',
                status = 'disabled',
                full_name = %s,
                legacy_source_table = 'students',
                legacy_source_id = %s,
                must_change_password = true,
                password_changed_at = NULL,
                session_version = session_version + 1,
                updated_at = now()
            WHERE id = %s
            """,
            (login, password_hash, status, full_name, int(student_id), int(account_id)),
        )
    else:
        row = conn.execute(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name,
                legacy_source_table, legacy_source_id, must_change_password,
                session_version, created_at, updated_at
            )
            VALUES (%s, %s, 'student', %s, %s, 'students', %s, true, 1, now(), now())
            RETURNING id
            """,
            (login, password_hash, status, full_name, int(student_id)),
        ).fetchone()
        account_id = int(row["id"] or 0) if row else 0
    if account_id <= 0:
        return 0
    conn.execute(
        """
        INSERT INTO msi_v2.student_profiles (
            account_id, student_id, school_id, student_code, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, now(), now())
        ON CONFLICT (student_id) WHERE student_id IS NOT NULL DO UPDATE SET
            account_id = excluded.account_id,
            school_id = excluded.school_id,
            student_code = excluded.student_code,
            status = excluded.status,
            updated_at = now()
        """,
        (account_id, int(student_id), school_id, login, status),
    )
    return account_id


def get_next_teacher_code(conn: Any) -> str:
    row = conn.execute(
        """
        SELECT COALESCE(MAX(number_value), 0) AS max_num
        FROM (
            SELECT NULLIF(regexp_replace(upper(teacher_code), '^TCH', ''), '')::integer AS number_value
            FROM msi_v2.teacher_profiles
            WHERE upper(teacher_code) ~ '^TCH[0-9]{4}$'
            UNION ALL
            SELECT NULLIF(regexp_replace(upper(login), '^TCH', ''), '')::integer AS number_value
            FROM msi_v2.accounts
            WHERE upper(login) ~ '^TCH[0-9]{4}$'
        ) codes
        """
    ).fetchone()
    return f"TCH{int(row['max_num'] or 0) + 1:04d}"


def find_teacher_account_row(conn: Any, *, teacher_id: int, staff_id: int, login: str) -> Any:
    return conn.execute(
        f"""
        SELECT DISTINCT {', '.join(f'account.{column.strip()}' for column in ACCOUNT_COLUMNS.split(','))}
        FROM msi_v2.accounts account
        LEFT JOIN msi_v2.teacher_profiles profile ON profile.account_id = account.id
        WHERE profile.teacher_id = %s
           OR (account.legacy_source_table = 'msi_staff' AND account.legacy_source_id = %s)
           OR (account.role = 'teacher' AND lower(btrim(account.login)) = lower(btrim(%s)))
        ORDER BY account.id
        LIMIT 1
        """,
        (int(teacher_id), int(staff_id), login),
    ).fetchone()


def save_teacher_account(
    conn: Any,
    *,
    account_id: int,
    teacher_id: int,
    staff_id: int,
    login: str,
    legacy_login: str,
    password_hash: str,
    full_name: str,
    status: str = "active",
) -> int:
    if account_id > 0:
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s,
                password_hash = %s,
                role = 'teacher',
                status = %s,
                full_name = %s,
                legacy_source_table = 'msi_staff',
                legacy_source_id = %s,
                must_change_password = false,
                password_changed_at = NULL,
                session_version = session_version + 1,
                updated_at = now()
            WHERE id = %s
            """,
            (login, password_hash, status, full_name, int(staff_id), int(account_id)),
        )
    else:
        row = conn.execute(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name,
                legacy_source_table, legacy_source_id, must_change_password,
                session_version, created_at, updated_at
            )
            VALUES (%s, %s, 'teacher', %s, %s, 'msi_staff', %s, false, 1, now(), now())
            RETURNING id
            """,
            (login, password_hash, status, full_name, int(staff_id)),
        ).fetchone()
        account_id = int(row["id"] or 0) if row else 0
    if account_id <= 0:
        return 0
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_profiles (
            account_id, teacher_id, teacher_code, legacy_login, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, now(), now())
        ON CONFLICT (teacher_id) WHERE teacher_id IS NOT NULL DO UPDATE SET
            account_id = excluded.account_id,
            teacher_code = excluded.teacher_code,
            legacy_login = excluded.legacy_login,
            status = excluded.status,
            updated_at = now()
        """,
        (account_id, int(teacher_id), login, legacy_login, status),
    )
    return account_id


def find_staff_account_row(conn: Any, *, staff_id: int, login: str) -> Any:
    return conn.execute(
        f"""
        SELECT DISTINCT {', '.join(f'account.{column.strip()}' for column in ACCOUNT_COLUMNS.split(','))}
        FROM msi_v2.accounts account
        LEFT JOIN msi_v2.staff_profiles profile ON profile.account_id = account.id
        WHERE profile.staff_id = %s
           OR (account.legacy_source_table = 'msi_staff' AND account.legacy_source_id = %s)
           OR (
                account.role IN (
                    'system_admin', 'ceo', 'customer_support', 'hr_manager',
                    'academic_director', 'head_of_department'
                )
                AND lower(btrim(account.login)) = lower(btrim(%s))
           )
        ORDER BY account.id
        LIMIT 1
        """,
        (int(staff_id), int(staff_id), login),
    ).fetchone()


def find_parent_account_row(conn: Any, *, parent_id: int) -> Any:
    return conn.execute(
        f"""
        SELECT DISTINCT {', '.join(f'account.{column.strip()}' for column in ACCOUNT_COLUMNS.split(','))}
        FROM msi_v2.accounts account
        LEFT JOIN msi_v2.parent_profiles profile ON profile.account_id = account.id
        WHERE profile.parent_id = %s
           OR (account.legacy_source_table = 'parents' AND account.legacy_source_id = %s)
        ORDER BY account.id
        LIMIT 1
        """,
        (int(parent_id), int(parent_id)),
    ).fetchone()


def save_parent_account(
    conn: Any,
    *,
    account_id: int,
    parent_id: int,
    full_name: str,
    phone: str,
    telegram_user_id: int | None,
    telegram_username: str,
) -> int:
    if account_id > 0:
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET role = 'parent', status = 'active', full_name = %s,
                phone = NULLIF(%s, ''), legacy_source_table = 'parents',
                legacy_source_id = %s,
                must_change_password = CASE
                    WHEN password_hash IS NULL OR btrim(password_hash) = '' THEN false
                    ELSE must_change_password
                END,
                updated_at = now()
            WHERE id = %s
            """,
            (full_name, phone, int(parent_id), int(account_id)),
        )
    else:
        row = conn.execute(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name, phone,
                legacy_source_table, legacy_source_id, must_change_password,
                session_version, created_at, updated_at
            )
            VALUES (NULL, NULL, 'parent', 'active', %s, NULLIF(%s, ''),
                    'parents', %s, false, 1, now(), now())
            RETURNING id
            """,
            (full_name, phone, int(parent_id)),
        ).fetchone()
        account_id = int(row["id"] or 0) if row else 0
    if account_id <= 0:
        return 0
    conn.execute(
        """
        INSERT INTO msi_v2.parent_profiles (
            account_id, parent_id, telegram_username, status, created_at, updated_at
        )
        VALUES (%s, %s, NULLIF(%s, ''), 'active', now(), now())
        ON CONFLICT (parent_id) WHERE parent_id IS NOT NULL DO UPDATE SET
            account_id = excluded.account_id,
            telegram_username = excluded.telegram_username,
            status = 'active',
            updated_at = now()
        """,
        (account_id, int(parent_id), telegram_username),
    )
    if telegram_user_id and int(telegram_user_id) > 0:
        conn.execute(
            """
            INSERT INTO msi_v2.account_telegram_links (
                account_id, telegram_user_id, telegram_username, status, linked_at
            )
            VALUES (%s, %s, NULLIF(%s, ''), 'active', now())
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                account_id = excluded.account_id,
                telegram_username = excluded.telegram_username,
                status = 'active',
                linked_at = now()
            """,
            (account_id, int(telegram_user_id), telegram_username),
        )
    return account_id


def transfer_parent_telegram_identity(
    conn: Any,
    *,
    parent_id: int,
    telegram_user_id: int,
    telegram_username: str,
) -> None:
    """Move one verified Telegram identity to a parent without unique conflicts."""

    conn.execute(
        "UPDATE msi_v2.students SET telegram_user_id = NULL WHERE telegram_user_id = %s",
        (int(telegram_user_id),),
    )
    conn.execute(
        "UPDATE msi_v2.msi_staff SET telegram_user_id = NULL WHERE telegram_user_id = %s",
        (int(telegram_user_id),),
    )
    conn.execute(
        """
        UPDATE msi_v2.parents
        SET telegram_user_id = NULL, updated_at = now()
        WHERE telegram_user_id = %s AND id <> %s
        """,
        (int(telegram_user_id), int(parent_id)),
    )
    conn.execute(
        """
        UPDATE msi_v2.parents
        SET telegram_user_id = %s,
            telegram_username = %s,
            status = 'active',
            updated_at = now()
        WHERE id = %s
        """,
        (int(telegram_user_id), telegram_username, int(parent_id)),
    )


def save_staff_account(
    conn: Any,
    *,
    account_id: int,
    staff_id: int,
    login: str,
    password_hash: str,
    role: str,
    full_name: str,
    phone: str = "",
    job_title: str = "",
    department: str = "",
    must_change_password: bool,
) -> int:
    if account_id > 0:
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s, password_hash = %s, role = %s, status = 'active',
                full_name = %s, phone = NULLIF(%s, ''),
                legacy_source_table = 'msi_staff', legacy_source_id = %s,
                must_change_password = %s, updated_at = now()
            WHERE id = %s
            """,
            (
                login,
                password_hash,
                role,
                full_name,
                phone,
                int(staff_id),
                bool(must_change_password),
                int(account_id),
            ),
        )
    else:
        row = conn.execute(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name, phone,
                legacy_source_table, legacy_source_id, must_change_password,
                session_version, created_at, updated_at
            )
            VALUES (%s, %s, %s, 'active', %s, NULLIF(%s, ''),
                    'msi_staff', %s, %s, 1, now(), now())
            RETURNING id
            """,
            (login, password_hash, role, full_name, phone, int(staff_id), bool(must_change_password)),
        ).fetchone()
        account_id = int(row["id"] or 0) if row else 0
    if account_id <= 0:
        return 0
    conn.execute(
        """
        INSERT INTO msi_v2.staff_profiles (
            account_id, staff_id, job_title, department, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'active', now(), now())
        ON CONFLICT (staff_id) WHERE staff_id IS NOT NULL DO UPDATE SET
            account_id = excluded.account_id,
            job_title = excluded.job_title,
            department = excluded.department,
            status = 'active',
            updated_at = now()
        """,
        (account_id, int(staff_id), job_title, department),
    )
    return account_id


def get_staff_by_login(conn: Any, login: str):
    return conn.execute(
        "SELECT id, password_hash FROM msi_v2.msi_staff WHERE lower(login) = lower(%s)",
        (login,),
    ).fetchone()


def promote_staff_owner(conn: Any, staff_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET role = 'owner', status = 'active', updated_at = now()
        WHERE id = %s
        """,
        (int(staff_id),),
    )


def demote_other_staff_owners(conn: Any, owner_staff_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET role = 'admin', updated_at = now()
        WHERE lower(role) = 'owner' AND id != %s
        """,
        (int(owner_staff_id),),
    )


def get_first_owner_staff(conn: Any):
    return conn.execute(
        """
        SELECT id, password_hash
        FROM msi_v2.msi_staff
        WHERE lower(role) = 'owner'
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()


def rename_owner_staff(conn: Any, *, staff_id: int, login: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET login = %s, role = 'owner', status = 'active', updated_at = now()
        WHERE id = %s
        """,
        (login, int(staff_id)),
    )


def insert_owner_staff(conn: Any, *, login: str, password_hash: str):
    return conn.execute(
        """
        INSERT INTO msi_v2.msi_staff (login, password_hash, role, status)
        VALUES (%s, %s, 'owner', 'active')
        RETURNING id
        """,
        (login, password_hash),
    ).fetchone()


__all__ = [
    "change_account_password",
    "find_staff_account_row",
    "find_parent_account_row",
    "find_student_account_row",
    "find_teacher_account_row",
    "get_account_by_id_row",
    "get_account_by_login_row",
    "get_account_telegram_link_row",
    "get_next_teacher_code",
    "get_parent_profile_row",
    "get_staff_profile_row",
    "get_student_account_by_legacy_id_row",
    "get_student_profile_row",
    "get_first_owner_staff",
    "get_staff_by_login",
    "insert_account_audit_event",
    "mark_account_login",
    "demote_other_staff_owners",
    "insert_owner_staff",
    "promote_staff_owner",
    "rename_owner_staff",
    "save_staff_account",
    "save_parent_account",
    "save_student_account",
    "save_teacher_account",
    "transfer_parent_telegram_identity",
]
