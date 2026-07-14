"""Staff account registration persistence."""

from __future__ import annotations

import json
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _utc_now_iso():
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _insert_password_reset_audit_event(
    conn: Any,
    *,
    actor_account_id: int | None,
    entity_account_id: int,
    actor_login: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_account_id, event_type, entity_type, entity_id, detail_json, created_at
        )
        VALUES (%s, 'account.password_reset', 'account', %s, %s::jsonb, now())
        """,
        (
            actor_account_id,
            entity_account_id,
            json.dumps(
                {
                    "role": "head_of_department",
                    "method": "academic_director",
                    "actor_login": _text(actor_login),
                },
                ensure_ascii=False,
            ),
        ),
    )


def lock_head_of_department_account(conn: Any, account_id: int):
    return conn.execute(
        """
        SELECT id, login, full_name, status, legacy_source_table, legacy_source_id
        FROM msi_v2.accounts
        WHERE id = %s
          AND role = 'head_of_department'
        LIMIT 1
        FOR UPDATE
        """,
        (int(account_id),),
    ).fetchone()


def update_head_of_department_password(
    conn: Any, *, account_id: int, password_hash: str, updated_at: str
):
    return conn.execute(
        """
        UPDATE msi_v2.accounts
        SET password_hash = %s,
            must_change_password = true,
            password_changed_at = NULL,
            session_version = session_version + 1,
            updated_at = %s::timestamptz
        WHERE id = %s
          AND role = 'head_of_department'
        RETURNING session_version
        """,
        (password_hash, updated_at, int(account_id)),
    ).fetchone()


def update_legacy_head_of_department_password(
    conn: Any,
    *,
    legacy_staff_id: int,
    login: str,
    password_hash: str,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.msi_staff
        SET password_hash = %s,
            updated_at = %s::timestamptz
        WHERE lower(role) = 'head_of_department'
          AND (id = %s OR lower(btrim(login)) = lower(btrim(%s)))
        """,
        (password_hash, updated_at, int(legacy_staff_id or -1), login),
    )


def _phase1_accounts_available(conn: Any) -> bool:
    try:
        row = conn.execute("SELECT to_regclass('msi_v2.accounts') AS table_name").fetchone()
    except Exception:
        return False
    return bool(row and row["table_name"])


def _table_available(conn: Any, table_name: str) -> bool:
    safe_name = _text(table_name)
    if not safe_name:
        return False
    try:
        row = conn.execute("SELECT to_regclass(%s) AS table_name", (safe_name,)).fetchone()
    except Exception:
        return False
    return bool(row and row["table_name"])


def _subject_row(conn: Any, subject_id: Any) -> dict[str, Any] | None:
    parsed_subject_id = _to_int(subject_id)
    if not parsed_subject_id:
        return None
    row = conn.execute(
        """
        SELECT id, subject_name, subject_key
        FROM msi_v2.subjects
        WHERE id = %s AND COALESCE(status, 'active') = 'active'
        LIMIT 1
        """,
        (parsed_subject_id,),
    ).fetchone()
    return dict(row) if row else None


def _list_active_subjects(conn: Any) -> list[dict[str, Any]]:
    if not _table_available(conn, "msi_v2.subjects"):
        return []
    try:
        rows = conn.execute(
            """
            SELECT id, subject_name
            FROM msi_v2.subjects
            WHERE COALESCE(status, 'active') = 'active'
            ORDER BY subject_name
            """
        ).fetchall()
    except Exception:
        return []
    return [{"id": _to_int(row["id"]), "name": _text(row["subject_name"])} for row in rows]


def _next_staff_code(conn: Any, prefix: str) -> str:
    normalized_prefix = _text(prefix).upper() or "HOD"
    row = conn.execute(
        """
        SELECT COALESCE(MAX(NULLIF(regexp_replace(upper(login), %s, ''), '')::integer), 0) AS max_num
        FROM msi_v2.msi_staff
        WHERE upper(login) ~ %s
        """,
        (f"^{normalized_prefix}", f"^{normalized_prefix}[0-9]+$"),
    ).fetchone()
    return f"{normalized_prefix}{int(row['max_num'] or 0) + 1:04d}"


def _insert_or_update_hod_staff(
    conn: Any,
    *,
    login: str,
    password_hash: str,
    display_name: str,
    subject_key: str,
    actor_login: str,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.msi_staff (
            login, password_hash, display_name, role, status, subject_scope,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, 'head_of_department', 'active', %s, %s::timestamptz, %s::timestamptz)
        ON CONFLICT ((lower(login))) DO UPDATE SET
            password_hash = excluded.password_hash,
            display_name = excluded.display_name,
            role = 'head_of_department',
            status = 'active',
            subject_scope = excluded.subject_scope,
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (
            login,
            password_hash,
            display_name,
            subject_key,
            now,
            now,
        ),
    ).fetchone()
    return _to_int(row["id"]) if row else 0


def _insert_or_update_staff_role(
    conn: Any,
    *,
    login: str,
    password_hash: str,
    display_name: str,
    role: str,
    subject_scope: str = "",
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.msi_staff (
            login, password_hash, display_name, role, status, subject_scope,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'active', %s, %s::timestamptz, %s::timestamptz)
        ON CONFLICT ((lower(login))) DO UPDATE SET
            password_hash = excluded.password_hash,
            display_name = excluded.display_name,
            role = excluded.role,
            status = 'active',
            subject_scope = excluded.subject_scope,
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (
            login,
            password_hash,
            display_name,
            role,
            subject_scope,
            now,
            now,
        ),
    ).fetchone()
    return _to_int(row["id"]) if row else 0


def _upsert_staff_account(
    conn: Any,
    *,
    staff_id: int,
    login: str,
    password_hash: str,
    display_name: str,
    role: str,
    now: str,
) -> int:
    account = conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE (
                role IN (
                    'system_admin', 'ceo', 'hr_manager', 'customer_support',
                    'academic_director', 'head_of_department'
                )
                AND lower(btrim(login)) = lower(btrim(%s))
              )
           OR (legacy_source_table = 'msi_staff' AND legacy_source_id = %s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (login, staff_id),
    ).fetchone()
    if account:
        account_id = _to_int(account["id"])
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s,
                password_hash = %s,
                role = %s,
                status = 'active',
                full_name = %s,
                legacy_source_table = 'msi_staff',
                legacy_source_id = %s,
                must_change_password = true,
                password_changed_at = NULL,
                session_version = session_version + 1,
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (login, password_hash, role, display_name, staff_id, now, account_id),
        )
        return account_id

    inserted = conn.execute(
        """
        INSERT INTO msi_v2.accounts (
            login, password_hash, role, status, full_name,
            legacy_source_table, legacy_source_id, must_change_password,
            session_version, created_at, updated_at
        )
        VALUES (%s, %s, %s, 'active', %s, 'msi_staff', %s, true, 1, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (login, password_hash, role, display_name, staff_id, now, now),
    ).fetchone()
    return _to_int(inserted["id"]) if inserted else 0


def _upsert_staff_profile_role(
    conn: Any,
    *,
    account_id: int,
    staff_id: int,
    job_title: str,
    department: str,
    now: str,
) -> int:
    profile = conn.execute(
        """
        SELECT id
        FROM msi_v2.staff_profiles
        WHERE account_id = %s OR staff_id = %s
        ORDER BY id ASC
        LIMIT 1
        """,
        (account_id, staff_id),
    ).fetchone()
    if profile:
        profile_id = _to_int(profile["id"])
        conn.execute(
            """
            UPDATE msi_v2.staff_profiles
            SET account_id = %s,
                staff_id = %s,
                job_title = %s,
                department = %s,
                status = 'active',
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (account_id, staff_id, job_title, department, now, profile_id),
        )
        return profile_id

    inserted = conn.execute(
        """
        INSERT INTO msi_v2.staff_profiles (
            account_id, staff_id, job_title, department, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'active', %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (account_id, staff_id, job_title, department, now, now),
    ).fetchone()
    return _to_int(inserted["id"]) if inserted else 0


def _upsert_hod_account(conn: Any, *, staff_id: int, login: str, password_hash: str, display_name: str, now: str) -> int:
    account = conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE (
                role IN (
                    'system_admin', 'ceo', 'hr_manager', 'customer_support',
                    'academic_director', 'head_of_department'
                )
                AND lower(btrim(login)) = lower(btrim(%s))
              )
           OR (legacy_source_table = 'msi_staff' AND legacy_source_id = %s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (login, staff_id),
    ).fetchone()
    if account:
        account_id = _to_int(account["id"])
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s,
                password_hash = %s,
                role = 'head_of_department',
                status = 'active',
                full_name = %s,
                legacy_source_table = 'msi_staff',
                legacy_source_id = %s,
                must_change_password = true,
                password_changed_at = NULL,
                session_version = session_version + 1,
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (login, password_hash, display_name, staff_id, now, account_id),
        )
        return account_id

    inserted = conn.execute(
        """
        INSERT INTO msi_v2.accounts (
            login, password_hash, role, status, full_name,
            legacy_source_table, legacy_source_id, must_change_password,
            session_version, created_at, updated_at
        )
        VALUES (%s, %s, 'head_of_department', 'active', %s, 'msi_staff', %s, true, 1, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (login, password_hash, display_name, staff_id, now, now),
    ).fetchone()
    return _to_int(inserted["id"]) if inserted else 0


def _upsert_hod_profile(
    conn: Any,
    *,
    account_id: int,
    staff_id: int,
    department: str,
    subject_id: int,
    now: str,
) -> int:
    profile = conn.execute(
        """
        SELECT id
        FROM msi_v2.staff_profiles
        WHERE account_id = %s OR staff_id = %s
        ORDER BY id ASC
        LIMIT 1
        """,
        (account_id, staff_id),
    ).fetchone()
    if profile:
        profile_id = _to_int(profile["id"])
        conn.execute(
            """
            UPDATE msi_v2.staff_profiles
            SET account_id = %s,
                staff_id = %s,
                job_title = 'Head of Department',
                department = %s,
                status = 'active',
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (account_id, staff_id, department, now, profile_id),
        )
    else:
        inserted = conn.execute(
            """
            INSERT INTO msi_v2.staff_profiles (
                account_id, staff_id, job_title, department, status, created_at, updated_at
            )
            VALUES (%s, %s, 'Head of Department', %s, 'active', %s::timestamptz, %s::timestamptz)
            RETURNING id
            """,
            (account_id, staff_id, department, now, now),
        ).fetchone()
        profile_id = _to_int(inserted["id"]) if inserted else 0

    if profile_id:
        conn.execute(
            """
            INSERT INTO msi_v2.staff_subject_scopes (
                account_id, staff_profile_id, subject_id, scope_type, status, created_at, updated_at
            )
            VALUES (%s, %s, %s, 'head_of_department', 'active', %s::timestamptz, %s::timestamptz)
            ON CONFLICT (account_id, subject_id, scope_type) WHERE status = 'active'
            DO UPDATE SET
                staff_profile_id = excluded.staff_profile_id,
                updated_at = excluded.updated_at
            """,
            (account_id, profile_id, subject_id, now, now),
        )
    return profile_id


def _hod_account_payload(row: Any) -> dict[str, Any]:
    return {
        "account_id": _to_int(row["account_id"]),
        "login": _text(row["login"]),
        "display_name": _text(row["display_name"]) or _text(row["login"]),
        "role": _text(row["role"]) or "head_of_department",
        "status": _text(row["status"]) or "active",
        "subject_id": _to_int(row["subject_id"]),
        "subject_name": _text(row["subject_name"]) or "Not assigned",
        "scope_type": _text(row["scope_type"]) or "head_of_department",
        "created_at": _text(row["created_at"]),
        "updated_at": _text(row["updated_at"]),
    }


def _list_head_of_department_accounts(conn: Any) -> dict[str, Any]:
    required_tables = (
        "msi_v2.accounts",
        "msi_v2.staff_profiles",
        "msi_v2.staff_subject_scopes",
        "msi_v2.subjects",
    )
    missing = [table_name for table_name in required_tables if not _table_available(conn, table_name)]
    if missing:
        return {
            "items": [],
            "warning": f"Head of Department account tables are not available yet: {', '.join(missing)}.",
        }

    try:
        rows = conn.execute(
            """
            SELECT
                account.id AS account_id,
                account.login,
                COALESCE(NULLIF(account.full_name, ''), NULLIF(profile.department, ''), account.login) AS display_name,
                account.role,
                account.status,
                scope.subject_id,
                subject.subject_name,
                scope.scope_type,
                account.created_at::text AS created_at,
                COALESCE(scope.updated_at, profile.updated_at, account.updated_at)::text AS updated_at
            FROM msi_v2.accounts account
            LEFT JOIN msi_v2.staff_profiles profile
              ON profile.account_id = account.id
            LEFT JOIN msi_v2.staff_subject_scopes scope
              ON scope.account_id = account.id
             AND scope.scope_type = 'head_of_department'
             AND scope.status = 'active'
            LEFT JOIN msi_v2.subjects subject
              ON subject.id = scope.subject_id
            WHERE account.role = 'head_of_department'
            ORDER BY COALESCE(scope.updated_at, profile.updated_at, account.updated_at) DESC,
                     account.id DESC
            """
        ).fetchall()
    except Exception as exc:
        return {
            "items": [],
            "warning": f"Head of Department accounts could not be loaded: {exc}",
        }
    return {"items": [_hod_account_payload(row) for row in rows], "warning": ""}
