"""canonical account identity

Revision ID: 0005_canonical_identity
Revises: 0004_hod_subject_scopes
Create Date: 2026-07-10

``msi_v2.accounts`` becomes the only password authority in this revision.  The
backfill deliberately preserves independently changed hashes.  The one repair
exception is a teacher account whose canonical TCH login still has the exact
hash copied from its legacy ``msi_staff`` row: that credential is reset to the
canonical login so the teacher can sign in and immediately choose a password.
"""

from __future__ import annotations

import re
from typing import Any

from alembic import op
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash


revision = "0005_canonical_identity"
down_revision = "0004_hod_subject_scopes"
branch_labels = None
depends_on = None


_TEACHER_CODE_RE = re.compile(r"^TCH[0-9]{4}$", re.IGNORECASE)
_STAFF_ROLE_MAP = {
    "owner": "system_admin",
    "admin": "system_admin",
    "system_admin": "system_admin",
    "ceo": "ceo",
    "hr": "hr_manager",
    "hr_manager": "hr_manager",
    "support": "customer_support",
    "customer_support": "customer_support",
    "academic_director": "academic_director",
    "head_of_department": "head_of_department",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _status(value: Any, *, has_password: bool = True) -> str:
    normalized = _text(value).casefold()
    if normalized in {"disabled", "inactive", "archived"}:
        return "disabled" if normalized != "archived" else "archived"
    if normalized == "pending":
        return "pending"
    return "active" if has_password else "disabled"


def _hash_verifies(password_hash: Any, password: Any) -> bool:
    normalized_hash = _text(password_hash)
    if not normalized_hash:
        return False
    try:
        return bool(check_password_hash(normalized_hash, _text(password)))
    except (TypeError, ValueError):
        return False


def _one(bind, sql: str, **params: Any) -> dict[str, Any] | None:
    row = bind.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _all(bind, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in bind.execute(text(sql), params).mappings().all()]


def _account_for_entity(
    bind,
    *,
    profile_table: str,
    entity_column: str,
    entity_id: int,
    source_table: str,
    source_id: int,
    login: str = "",
    role: str = "",
) -> dict[str, Any] | None:
    profile = _one(
        bind,
        f"""
        SELECT account.*
        FROM msi_v2.{profile_table} profile
        JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE profile.{entity_column} = :entity_id
        ORDER BY account.id
        LIMIT 1
        """,
        entity_id=entity_id,
    )
    if profile:
        return profile

    sourced = _one(
        bind,
        """
        SELECT *
        FROM msi_v2.accounts
        WHERE legacy_source_table = :source_table
          AND legacy_source_id = :source_id
        ORDER BY id
        LIMIT 1
        """,
        source_table=source_table,
        source_id=source_id,
    )
    if sourced:
        return sourced

    if not login:
        return None
    return _one(
        bind,
        """
        SELECT *
        FROM msi_v2.accounts
        WHERE lower(btrim(login)) = lower(btrim(:login))
          AND (:role = '' OR role = :role)
        ORDER BY id
        LIMIT 1
        """,
        login=login,
        role=role,
    )


def _save_account(
    bind,
    *,
    account: dict[str, Any] | None,
    login: str | None,
    password_hash: str | None,
    role: str,
    status: str,
    full_name: str,
    phone: str | None,
    source_table: str,
    source_id: int,
    must_change_password: bool,
) -> int:
    if account:
        account_id = int(account["id"])
        bind.execute(
            text(
                """
                UPDATE msi_v2.accounts
                SET login = :login,
                    password_hash = :password_hash,
                    role = :role,
                    status = :status,
                    full_name = :full_name,
                    phone = :phone,
                    legacy_source_table = :source_table,
                    legacy_source_id = :source_id,
                    must_change_password = :must_change_password,
                    session_version = GREATEST(COALESCE(session_version, 1), 1),
                    updated_at = now()
                WHERE id = :account_id
                """
            ),
            {
                "account_id": account_id,
                "login": login,
                "password_hash": password_hash,
                "role": role,
                "status": status,
                "full_name": full_name,
                "phone": phone,
                "source_table": source_table,
                "source_id": source_id,
                "must_change_password": must_change_password,
            },
        )
        return account_id

    inserted = _one(
        bind,
        """
        INSERT INTO msi_v2.accounts (
            login, password_hash, role, status, full_name, phone,
            legacy_source_table, legacy_source_id, must_change_password,
            session_version, created_at, updated_at
        )
        VALUES (
            :login, :password_hash, :role, :status, :full_name, :phone,
            :source_table, :source_id, :must_change_password, 1, now(), now()
        )
        RETURNING id
        """,
        login=login,
        password_hash=password_hash,
        role=role,
        status=status,
        full_name=full_name,
        phone=phone,
        source_table=source_table,
        source_id=source_id,
        must_change_password=must_change_password,
    )
    if not inserted:
        raise RuntimeError(f"Unable to create {role} account for {source_table}:{source_id}")
    return int(inserted["id"])


def _link_telegram(bind, *, account_id: int, telegram_user_id: Any, username: Any = "") -> None:
    try:
        user_id = int(telegram_user_id or 0)
    except (TypeError, ValueError):
        return
    if user_id <= 0:
        return
    bind.execute(
        text(
            """
            INSERT INTO msi_v2.account_telegram_links (
                account_id, telegram_user_id, telegram_username, linked_at, status
            )
            VALUES (:account_id, :telegram_user_id, :username, now(), 'active')
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                account_id = excluded.account_id,
                telegram_username = excluded.telegram_username,
                status = 'active'
            """
        ),
        {
            "account_id": account_id,
            "telegram_user_id": user_id,
            "username": _text(username) or None,
        },
    )


def _backfill_students(bind) -> None:
    students = _all(
        bind,
        """
        SELECT st.*, auth.password_hash AS legacy_password_hash
        FROM msi_v2.students st
        LEFT JOIN msi_v2.student_auth auth ON auth.student_id = st.id
        ORDER BY st.id
        """,
    )
    for student in students:
        student_id = int(student["id"])
        login = _text(student.get("student_code")).upper()
        account = _account_for_entity(
            bind,
            profile_table="student_profiles",
            entity_column="student_id",
            entity_id=student_id,
            source_table="students",
            source_id=student_id,
            login=login,
            role="student",
        )
        password_hash = _text(account.get("password_hash") if account else "") or _text(
            student.get("legacy_password_hash")
        )
        must_change = bool(password_hash and _hash_verifies(password_hash, login))
        account_id = _save_account(
            bind,
            account=account,
            login=login or None,
            password_hash=password_hash or None,
            role="student",
            status=_status(student.get("status"), has_password=bool(password_hash)),
            full_name=_text(student.get("full_name")),
            phone=None,
            source_table="students",
            source_id=student_id,
            must_change_password=must_change,
        )
        bind.execute(
            text(
                """
                INSERT INTO msi_v2.student_profiles (
                    account_id, student_id, school_id, student_code, status,
                    created_at, updated_at
                )
                VALUES (
                    :account_id, :student_id, :school_id, :student_code, :status,
                    now(), now()
                )
                ON CONFLICT (student_id) WHERE student_id IS NOT NULL DO UPDATE SET
                    account_id = excluded.account_id,
                    school_id = excluded.school_id,
                    student_code = excluded.student_code,
                    status = excluded.status,
                    updated_at = now()
                """
            ),
            {
                "account_id": account_id,
                "student_id": student_id,
                "school_id": student.get("school_id"),
                "student_code": login,
                "status": _status(student.get("status"), has_password=bool(password_hash)),
            },
        )
        _link_telegram(
            bind,
            account_id=account_id,
            telegram_user_id=student.get("telegram_user_id"),
        )


def _used_teacher_codes(bind) -> set[str]:
    rows = _all(
        bind,
        """
        SELECT teacher_code AS code FROM msi_v2.teacher_profiles
        UNION ALL
        SELECT login AS code FROM msi_v2.accounts WHERE login IS NOT NULL
        UNION ALL
        SELECT login AS code FROM msi_v2.msi_staff
        """,
    )
    return {
        _text(row.get("code")).upper()
        for row in rows
        if _TEACHER_CODE_RE.fullmatch(_text(row.get("code")))
    }


def _next_teacher_code(used: set[str]) -> str:
    number = 1
    while f"TCH{number:04d}" in used:
        number += 1
    code = f"TCH{number:04d}"
    used.add(code)
    return code


def _backfill_teachers(bind) -> None:
    used_codes = _used_teacher_codes(bind)
    teachers = _all(
        bind,
        """
        SELECT
            teacher.*,
            staff.id AS staff_id,
            staff.login AS legacy_login,
            staff.password_hash AS legacy_password_hash,
            staff.status AS staff_status,
            staff.telegram_user_id AS staff_telegram_user_id,
            staff.telegram_username AS staff_telegram_username,
            existing_profile.teacher_code AS existing_teacher_code,
            existing_account.id AS existing_account_id,
            existing_account.login AS existing_account_login
        FROM msi_v2.teachers teacher
        LEFT JOIN LATERAL (
            SELECT candidate.*
            FROM msi_v2.msi_staff candidate
            WHERE candidate.teacher_id = teacher.id
              AND lower(candidate.role) = 'teacher'
            ORDER BY CASE WHEN lower(candidate.status) = 'active' THEN 0 ELSE 1 END,
                     candidate.id
            LIMIT 1
        ) staff ON true
        LEFT JOIN msi_v2.teacher_profiles existing_profile
          ON existing_profile.teacher_id = teacher.id
        LEFT JOIN msi_v2.accounts existing_account
          ON existing_account.id = existing_profile.account_id
        ORDER BY teacher.id
        """,
    )
    for teacher in teachers:
        teacher_id = int(teacher["id"])
        existing_code = _text(teacher.get("existing_teacher_code")).upper()
        existing_login = _text(teacher.get("existing_account_login")).upper()
        legacy_login = _text(teacher.get("legacy_login"))
        if _TEACHER_CODE_RE.fullmatch(existing_code):
            login = existing_code
            used_codes.add(login)
        elif _TEACHER_CODE_RE.fullmatch(existing_login):
            login = existing_login
            used_codes.add(login)
        elif _TEACHER_CODE_RE.fullmatch(legacy_login):
            login = legacy_login.upper()
            used_codes.add(login)
        else:
            login = _next_teacher_code(used_codes)

        staff_id = int(teacher.get("staff_id") or 0)
        source_table = "msi_staff" if staff_id else "teachers"
        source_id = staff_id or teacher_id
        account = _account_for_entity(
            bind,
            profile_table="teacher_profiles",
            entity_column="teacher_id",
            entity_id=teacher_id,
            source_table=source_table,
            source_id=source_id,
            login=login,
            role="teacher",
        )
        account_hash = _text(account.get("password_hash") if account else "")
        staff_hash = _text(teacher.get("legacy_password_hash"))
        password_hash = account_hash or staff_hash

        # A copied legacy hash belongs to the old staff login, not to the new
        # canonical TCH login.  Only repair exact copies; an independently
        # changed account hash is preserved byte-for-byte.
        copied_legacy_hash = bool(staff_hash and password_hash == staff_hash)
        if copied_legacy_hash and not _hash_verifies(password_hash, login):
            password_hash = generate_password_hash(login)

        has_password = bool(password_hash)
        account_id = _save_account(
            bind,
            account=account,
            login=login,
            password_hash=password_hash or None,
            role="teacher",
            status=_status(teacher.get("staff_status") or teacher.get("status"), has_password=has_password),
            full_name=_text(teacher.get("full_name")),
            phone=_text(teacher.get("phone")) or None,
            source_table=source_table,
            source_id=source_id,
            must_change_password=bool(password_hash and _hash_verifies(password_hash, login)),
        )
        bind.execute(
            text(
                """
                INSERT INTO msi_v2.teacher_profiles (
                    account_id, teacher_id, school_id, teacher_code, legacy_login,
                    status, created_at, updated_at
                )
                VALUES (
                    :account_id, :teacher_id, NULL, :teacher_code, :legacy_login,
                    :status, now(), now()
                )
                ON CONFLICT (teacher_id) WHERE teacher_id IS NOT NULL DO UPDATE SET
                    account_id = excluded.account_id,
                    teacher_code = excluded.teacher_code,
                    legacy_login = excluded.legacy_login,
                    status = excluded.status,
                    updated_at = now()
                """
            ),
            {
                "account_id": account_id,
                "teacher_id": teacher_id,
                "teacher_code": login,
                "legacy_login": legacy_login,
                "status": _status(
                    teacher.get("staff_status") or teacher.get("status"),
                    has_password=has_password,
                ),
            },
        )
        _link_telegram(
            bind,
            account_id=account_id,
            telegram_user_id=teacher.get("staff_telegram_user_id") or teacher.get("telegram_user_id"),
            username=teacher.get("staff_telegram_username") or teacher.get("telegram_username"),
        )


def _backfill_staff(bind) -> None:
    staff_rows = _all(
        bind,
        """
        SELECT *
        FROM msi_v2.msi_staff
        WHERE lower(role) <> 'teacher'
        ORDER BY id
        """,
    )
    for staff in staff_rows:
        raw_role = _text(staff.get("role")).casefold()
        role = _STAFF_ROLE_MAP.get(raw_role)
        if not role:
            continue
        staff_id = int(staff["id"])
        login = _text(staff.get("login"))
        account = _account_for_entity(
            bind,
            profile_table="staff_profiles",
            entity_column="staff_id",
            entity_id=staff_id,
            source_table="msi_staff",
            source_id=staff_id,
            login=login,
            role=role,
        )
        password_hash = _text(account.get("password_hash") if account else "") or _text(
            staff.get("password_hash")
        )
        has_password = bool(password_hash)
        account_id = _save_account(
            bind,
            account=account,
            login=login or None,
            password_hash=password_hash or None,
            role=role,
            status=_status(staff.get("status"), has_password=has_password),
            full_name=_text(staff.get("display_name")) or login,
            phone=_text(staff.get("phone")) or None,
            source_table="msi_staff",
            source_id=staff_id,
            must_change_password=bool(password_hash and _hash_verifies(password_hash, login)),
        )
        bind.execute(
            text(
                """
                INSERT INTO msi_v2.staff_profiles (
                    account_id, staff_id, job_title, department, status,
                    created_at, updated_at
                )
                VALUES (
                    :account_id, :staff_id, :job_title, :department, :status,
                    now(), now()
                )
                ON CONFLICT (staff_id) WHERE staff_id IS NOT NULL DO UPDATE SET
                    account_id = excluded.account_id,
                    job_title = excluded.job_title,
                    department = excluded.department,
                    status = excluded.status,
                    updated_at = now()
                """
            ),
            {
                "account_id": account_id,
                "staff_id": staff_id,
                "job_title": "Owner" if raw_role == "owner" else role.replace("_", " ").title(),
                "department": "System" if role == "system_admin" else role.replace("_", " ").title(),
                "status": _status(staff.get("status"), has_password=has_password),
            },
        )
        _link_telegram(
            bind,
            account_id=account_id,
            telegram_user_id=staff.get("telegram_user_id"),
            username=staff.get("telegram_username"),
        )


def _backfill_parents(bind) -> None:
    parents = _all(bind, "SELECT * FROM msi_v2.parents ORDER BY id")
    for parent in parents:
        parent_id = int(parent["id"])
        account = _account_for_entity(
            bind,
            profile_table="parent_profiles",
            entity_column="parent_id",
            entity_id=parent_id,
            source_table="parents",
            source_id=parent_id,
            role="parent",
        )
        password_hash = _text(account.get("password_hash") if account else "")
        login = _text(account.get("login") if account else "") or None
        parent_status = _text(parent.get("status")).casefold()
        has_verified_telegram_identity = bool(int(parent.get("telegram_user_id") or 0) > 0)
        account_status = (
            "active"
            if parent_status == "active" and has_verified_telegram_identity
            else _text(account.get("status")).casefold()
            if account and _text(account.get("status")).casefold() in {"active", "pending", "disabled", "archived"}
            else ("active" if parent_status == "active" else _status(parent_status, has_password=False))
        )
        account_id = _save_account(
            bind,
            account=account,
            login=login,
            password_hash=password_hash or None,
            role="parent",
            status=account_status,
            full_name=_text(parent.get("display_name")),
            phone=_text(parent.get("phone")) or None,
            source_table="parents",
            source_id=parent_id,
            must_change_password=bool(password_hash and login and _hash_verifies(password_hash, login)),
        )
        profile_status = "active" if parent_status == "active" else account_status
        bind.execute(
            text(
                """
                INSERT INTO msi_v2.parent_profiles (
                    account_id, parent_id, telegram_username, status,
                    created_at, updated_at
                )
                VALUES (
                    :account_id, :parent_id, :telegram_username, :status,
                    now(), now()
                )
                ON CONFLICT (parent_id) WHERE parent_id IS NOT NULL DO UPDATE SET
                    account_id = excluded.account_id,
                    telegram_username = excluded.telegram_username,
                    status = excluded.status,
                    updated_at = now()
                """
            ),
            {
                "account_id": account_id,
                "parent_id": parent_id,
                "telegram_username": _text(parent.get("telegram_username")) or None,
                "status": profile_status,
            },
        )
        _link_telegram(
            bind,
            account_id=account_id,
            telegram_user_id=parent.get("telegram_user_id"),
            username=parent.get("telegram_username"),
        )


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.accounts
            ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT true,
            ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS session_version BIGINT NOT NULL DEFAULT 1;

        UPDATE msi_v2.accounts
        SET session_version = 1
        WHERE session_version IS NULL OR session_version < 1;

        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_session_version_positive_check;

        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_session_version_positive_check
        CHECK (session_version > 0);

        ALTER TABLE msi_v2.audit_events
        ADD COLUMN IF NOT EXISTS actor_account_id BIGINT
            REFERENCES msi_v2.accounts(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_audit_events_actor_account_created
        ON msi_v2.audit_events (actor_account_id, created_at DESC)
        WHERE actor_account_id IS NOT NULL;
        """
    )

    bind = op.get_bind()
    _backfill_students(bind)
    _backfill_teachers(bind)
    _backfill_staff(bind)
    _backfill_parents(bind)

    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.student_auth;
        ALTER TABLE msi_v2.students DROP COLUMN IF EXISTS password_plain;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.students
        ADD COLUMN IF NOT EXISTS password_plain TEXT NOT NULL DEFAULT '';

        CREATE TABLE IF NOT EXISTS msi_v2.student_auth (
            student_id BIGINT PRIMARY KEY REFERENCES msi_v2.students(id) ON DELETE CASCADE,
            password_hash TEXT NOT NULL,
            must_change_password BOOLEAN NOT NULL DEFAULT true,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_login_at TIMESTAMPTZ
        );

        INSERT INTO msi_v2.student_auth (
            student_id, password_hash, must_change_password, updated_at, last_login_at
        )
        SELECT
            profile.student_id,
            account.password_hash,
            account.must_change_password,
            account.updated_at,
            account.last_login_at
        FROM msi_v2.student_profiles profile
        JOIN msi_v2.accounts account ON account.id = profile.account_id
        WHERE profile.student_id IS NOT NULL
          AND account.password_hash IS NOT NULL
        ON CONFLICT (student_id) DO UPDATE SET
            password_hash = excluded.password_hash,
            must_change_password = excluded.must_change_password,
            updated_at = excluded.updated_at,
            last_login_at = excluded.last_login_at;

        DROP INDEX IF EXISTS msi_v2.idx_audit_events_actor_account_created;
        ALTER TABLE msi_v2.audit_events DROP COLUMN IF EXISTS actor_account_id;

        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_session_version_positive_check;
        ALTER TABLE msi_v2.accounts
            DROP COLUMN IF EXISTS session_version,
            DROP COLUMN IF EXISTS last_login_at,
            DROP COLUMN IF EXISTS password_changed_at,
            DROP COLUMN IF EXISTS must_change_password;
        """
    )
