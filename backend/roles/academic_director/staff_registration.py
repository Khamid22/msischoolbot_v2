"""Academic Director staff registration helpers."""

from __future__ import annotations

from typing import Any

from backend.core.database import connect_auth_db
from backend.core.security import generate_password_hash


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


def list_active_subjects() -> list[dict[str, Any]]:
    """Subject options for the Head of Departments page (New HOD form + coverage).

    Best-effort: the page must still render when the subjects table (or the
    database itself) is unavailable, so failures collapse to an empty list.
    """
    try:
        with connect_auth_db() as conn:
            return _list_active_subjects(conn)
    except Exception:
        return []


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
        WHERE lower(btrim(login)) = lower(btrim(%s))
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
            legacy_source_table, legacy_source_id, created_at, updated_at
        )
        VALUES (%s, %s, %s, 'active', %s, 'msi_staff', %s, %s::timestamptz, %s::timestamptz)
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
        WHERE lower(btrim(login)) = lower(btrim(%s))
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
            legacy_source_table, legacy_source_id, created_at, updated_at
        )
        VALUES (%s, %s, 'head_of_department', 'active', %s, 'msi_staff', %s, %s::timestamptz, %s::timestamptz)
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


def create_head_of_department_account(
    *,
    display_name: str,
    subject_id: Any,
    created_by: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    with connect_auth_db() as conn:
        return _create_head_of_department_account(
            conn,
            display_name=display_name,
            subject_id=subject_id,
            created_by=created_by,
            commit=True,
        )


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


def list_head_of_department_accounts() -> dict[str, Any]:
    with connect_auth_db() as conn:
        return _list_head_of_department_accounts(conn)


def create_academic_director_account(
    *,
    login: str = "AD0001",
    display_name: str = "Academic Director",
    temporary_password: str = "",
    commit: bool = True,
) -> tuple[bool, str, dict[str, Any]]:
    with connect_auth_db() as conn:
        return _create_academic_director_account(
            conn,
            login=login,
            display_name=display_name,
            temporary_password=temporary_password,
            commit=commit,
        )


def _create_academic_director_account(
    conn: Any,
    *,
    login: str = "AD0001",
    display_name: str = "Academic Director",
    temporary_password: str = "",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    if not _phase1_accounts_available(conn):
        return False, "Shared accounts are not available. Apply Phase 1 account schema first.", {}

    normalized_login = _text(login).upper() or "AD0001"
    if not normalized_login.startswith("AD"):
        return False, "Academic Director login must use AD0001 format.", {}
    password = _text(temporary_password) or normalized_login
    normalized_display_name = _text(display_name) or "Academic Director"
    now = _utc_now_iso()
    password_hash = generate_password_hash(password)

    staff_id = _insert_or_update_staff_role(
        conn,
        login=normalized_login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="academic_director",
        subject_scope="",
        now=now,
    )
    if not staff_id:
        return False, "Unable to create Academic Director staff row.", {}

    account_id = _upsert_staff_account(
        conn,
        staff_id=staff_id,
        login=normalized_login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        role="academic_director",
        now=now,
    )
    if not account_id:
        return False, "Unable to create Academic Director account.", {}

    profile_id = _upsert_staff_profile_role(
        conn,
        account_id=account_id,
        staff_id=staff_id,
        job_title="Academic Director",
        department="Academic Department",
        now=now,
    )
    if not profile_id:
        return False, "Unable to create Academic Director profile.", {}

    if commit:
        conn.commit()

    return True, "", {
        "role": "academic_director",
        "login": normalized_login,
        "temporary_password": password,
        "display_name": normalized_display_name,
        "account_id": account_id,
        "staff_id": staff_id,
    }


def _create_head_of_department_account(
    conn: Any,
    *,
    display_name: str,
    subject_id: Any,
    created_by: str = "",
    commit: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    if not _phase1_accounts_available(conn):
        return False, "Shared accounts are not available. Apply Phase 1 account schema first.", {}

    subject = _subject_row(conn, subject_id)
    if not subject:
        return False, "Select a valid subject scope.", {}

    subject_name = _text(subject.get("subject_name")) or "Department"
    subject_key = _text(subject.get("subject_key"))
    normalized_display_name = _text(display_name) or f"Head of {subject_name} Department"
    now = _utc_now_iso()
    login = _next_staff_code(conn, "HOD")
    password_hash = generate_password_hash(login)

    staff_id = _insert_or_update_hod_staff(
        conn,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        subject_key=subject_key or str(subject["id"]),
        actor_login=_text(created_by),
        now=now,
    )
    if not staff_id:
        return False, "Unable to create HOD staff row.", {}

    account_id = _upsert_hod_account(
        conn,
        staff_id=staff_id,
        login=login,
        password_hash=password_hash,
        display_name=normalized_display_name,
        now=now,
    )
    if not account_id:
        return False, "Unable to create HOD account.", {}

    profile_id = _upsert_hod_profile(
        conn,
        account_id=account_id,
        staff_id=staff_id,
        department=f"{subject_name} Department",
        subject_id=int(subject["id"]),
        now=now,
    )
    if not profile_id:
        return False, "Unable to create HOD profile.", {}

    if commit:
        conn.commit()

    credentials = {
        "role": "head_of_department",
        "login": login,
        "temporary_password": login,
        "display_name": normalized_display_name,
        "subject_id": int(subject["id"]),
        "subject_name": subject_name,
        "account_id": account_id,
        "staff_id": staff_id,
    }
    return True, "", credentials


__all__ = [
    "create_academic_director_account",
    "create_head_of_department_account",
    "list_head_of_department_accounts",
    "_create_academic_director_account",
    "_create_head_of_department_account",
    "_list_head_of_department_accounts",
]
