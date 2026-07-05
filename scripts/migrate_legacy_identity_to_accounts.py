#!/usr/bin/env python3
"""Plan or apply the legacy identity -> shared accounts migration.

This script is intentionally additive:
- it never drops, truncates, or deletes existing tables;
- dry-run mode does not write to PostgreSQL;
- apply mode only writes to the new Phase 1 account/profile tables.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database.database import connect_auth_db  # noqa: E402


ALLOWED_ACCOUNT_ROLES = {
    "system_admin",
    "ceo",
    "hr_manager",
    "customer_support",
    "student",
    "teacher",
    "parent",
    "academic_director",
}
ACCOUNT_STATUSES = {"active", "pending", "disabled", "archived"}
TEACHER_CODE_RE = re.compile(r"^TCH[0-9]{4}$")
LEGACY_SOURCE_TABLES = {
    "staff": "msi_staff",
    "student": "students",
    "teacher": "teachers",
    "parent": "parents",
}

ROLE_MAP = {
    "owner": "system_admin",
    "admin": "system_admin",
    "system_admin": "system_admin",
    "system-admin": "system_admin",
    "system admin": "system_admin",
    "ceo": "ceo",
    "hr": "hr_manager",
    "hr_manager": "hr_manager",
    "hr-manager": "hr_manager",
    "hr manager": "hr_manager",
    "customer_support": "customer_support",
    "customer-support": "customer_support",
    "customer support": "customer_support",
    "support": "customer_support",
    "sales": "customer_support",
    "academic_director": "academic_director",
    "academic-director": "academic_director",
    "academic director": "academic_director",
    "teacher": "teacher",
    "student": "student",
    "parent": "parent",
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_login(value: Any) -> str:
    return normalize_text(value).casefold()


def normalize_role(value: Any) -> str:
    raw = normalize_text(value).casefold().replace("_", " ").replace("-", " ")
    compact = " ".join(raw.split())
    return ROLE_MAP.get(compact) or ROLE_MAP.get(compact.replace(" ", "_")) or ""


def normalize_status(value: Any, *, default: str = "active") -> str:
    raw = normalize_text(value).casefold()
    if raw in {"active", "pending", "disabled", "archived"}:
        return raw
    if raw in {"inactive", "blocked", "banned"}:
        return "disabled"
    return default


def active_source_status(value: Any) -> bool:
    return normalize_text(value).casefold() == "active"


def is_valid_teacher_code(value: Any) -> bool:
    return bool(TEACHER_CODE_RE.fullmatch(normalize_text(value).upper()))


def next_teacher_code(used_codes: set[str], start_at: int = 1) -> str:
    number = max(1, int(start_at or 1))
    while True:
        candidate = f"TCH{number:04d}"
        if candidate.casefold() not in used_codes:
            return candidate
        number += 1


def duplicate_values(values: list[str]) -> dict[str, int]:
    counts = Counter(value for value in values if value)
    return {value: count for value, count in counts.items() if count > 1}


def generate_teacher_code_map(
    teacher_sources: list[dict[str, Any]],
    *,
    reserved_logins: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic teacher code assignments.

    Existing valid TCH0001-style logins are kept when they do not conflict with
    already reserved account logins. Other teacher logins receive the next
    available TCH code in teacher_id/staff_id order.
    """

    reserved = set(reserved_logins or set())
    used_codes = {value for value in reserved if TEACHER_CODE_RE.fullmatch(value.upper())}
    mappings: list[dict[str, Any]] = []
    sorted_sources = sorted(
        teacher_sources,
        key=lambda row: (
            int(row.get("teacher_id") or 0),
            int(row.get("staff_id") or 0),
            normalize_login(row.get("old_login")),
        ),
    )
    for row in sorted_sources:
        old_login = normalize_text(row.get("old_login"))
        old_code = old_login.upper()
        old_normalized = old_code.casefold()
        if is_valid_teacher_code(old_code) and old_normalized not in used_codes:
            new_code = old_code
            conflict_status = "kept"
        else:
            new_code = next_teacher_code(used_codes)
            conflict_status = (
                "generated_due_to_conflict"
                if is_valid_teacher_code(old_code)
                else "generated"
            )
        used_codes.add(new_code.casefold())
        mappings.append(
            {
                "staff_id": int(row.get("staff_id") or 0),
                "teacher_id": int(row.get("teacher_id") or 0),
                "teacher_name": normalize_text(row.get("teacher_name")),
                "old_teacher_login": old_login,
                "new_teacher_code": new_code,
                "conflict_status": conflict_status,
            }
        )
    return mappings


def load_legacy_rows(conn) -> dict[str, list[dict[str, Any]]]:
    staff_rows = conn.execute(
        """
        SELECT id AS staff_id, login, password_hash, display_name, phone,
               telegram_user_id, telegram_username, role, status, teacher_id
        FROM msi_v2.msi_staff
        ORDER BY id
        """
    ).fetchall()
    student_rows = conn.execute(
        """
        SELECT st.id AS student_db_id, st.student_code, st.full_name, st.school_id,
               st.telegram_user_id, st.status, st.legacy_student_row_id,
               a.password_hash, a.must_change_password, a.last_login_at
        FROM msi_v2.students st
        LEFT JOIN msi_v2.student_auth a ON a.student_id = st.id
        ORDER BY st.id
        """
    ).fetchall()
    teacher_rows = conn.execute(
        """
        SELECT t.id AS teacher_id, t.full_name AS teacher_name, t.status,
               t.telegram_user_id, t.telegram_username
        FROM msi_v2.teachers t
        ORDER BY t.id
        """
    ).fetchall()
    teacher_staff_rows = conn.execute(
        """
        SELECT sf.id AS staff_id, sf.login AS old_login, sf.password_hash,
               sf.display_name, sf.phone, sf.telegram_user_id, sf.telegram_username,
               sf.status AS staff_status, sf.teacher_id,
               COALESCE(NULLIF(t.full_name, ''), NULLIF(sf.display_name, ''), sf.login) AS teacher_name,
               t.status AS teacher_status
        FROM msi_v2.msi_staff sf
        LEFT JOIN msi_v2.teachers t ON t.id = sf.teacher_id
        WHERE lower(sf.role) = 'teacher'
        ORDER BY COALESCE(sf.teacher_id, 0), sf.id
        """
    ).fetchall()
    parent_rows = conn.execute(
        """
        SELECT id AS parent_id, display_name, phone, telegram_user_id,
               telegram_username, status
        FROM msi_v2.parents
        ORDER BY id
        """
    ).fetchall()
    return {
        "staff_rows": [dict(row) for row in staff_rows],
        "student_rows": [dict(row) for row in student_rows],
        "teacher_rows": [dict(row) for row in teacher_rows],
        "teacher_staff_rows": [dict(row) for row in teacher_staff_rows],
        "parent_rows": [dict(row) for row in parent_rows],
    }


def planned_account(
    *,
    source_type: str,
    source_id: int,
    login: str,
    role: str,
    status: str,
    full_name: str,
    phone: str | None = None,
    password_hash: str | None = None,
    profile: dict[str, Any] | None = None,
    telegram_user_id: int | None = None,
    telegram_username: str | None = None,
) -> dict[str, Any]:
    legacy_source_table = LEGACY_SOURCE_TABLES.get(source_type, source_type)
    return {
        "source_type": source_type,
        "source_id": int(source_id or 0),
        "legacy_source_table": legacy_source_table,
        "legacy_source_id": int(source_id or 0) or None,
        "login": normalize_text(login) or None,
        "role": role,
        "status": status if status in ACCOUNT_STATUSES else "disabled",
        "full_name": normalize_text(full_name),
        "phone": normalize_text(phone) or None,
        "password_hash": normalize_text(password_hash) or None,
        "profile": profile or {},
        "telegram_user_id": int(telegram_user_id) if telegram_user_id else None,
        "telegram_username": normalize_text(telegram_username) or None,
    }


def build_plan(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    validations: dict[str, Any] = {
        "duplicate_logins": {},
        "missing_password_hash": [],
        "students_without_auth": [],
        "teachers_without_staff_rows": [],
        "parents_without_telegram": [],
        "duplicate_telegram_ids": {},
        "invalid_roles": [],
        "disabled_or_inactive_users": [],
        "teacher_code_conflicts": [],
        "student_code_conflicts": {},
    }
    accounts: list[dict[str, Any]] = []
    teacher_sources: list[dict[str, Any]] = []

    staff_rows = rows.get("staff_rows", [])
    student_rows = rows.get("student_rows", [])
    teacher_rows = rows.get("teacher_rows", [])
    teacher_staff_rows = rows.get("teacher_staff_rows", [])
    parent_rows = rows.get("parent_rows", [])

    teacher_staff_by_teacher = {
        int(row.get("teacher_id") or 0)
        for row in teacher_staff_rows
        if int(row.get("teacher_id") or 0) > 0
    }
    for teacher in teacher_rows:
        teacher_id = int(teacher.get("teacher_id") or 0)
        if active_source_status(teacher.get("status")) and teacher_id not in teacher_staff_by_teacher:
            validations["teachers_without_staff_rows"].append(teacher_id)

    for staff in staff_rows:
        raw_role = normalize_text(staff.get("role"))
        role = normalize_role(raw_role)
        staff_id = int(staff.get("staff_id") or 0)
        if raw_role.casefold() == "teacher":
            if int(staff.get("teacher_id") or 0) <= 0:
                validations["teachers_without_staff_rows"].append(f"staff:{staff_id}")
            continue
        if not role:
            validations["invalid_roles"].append({"source": "msi_staff", "id": staff_id, "role": raw_role})
            continue
        if role not in ALLOWED_ACCOUNT_ROLES:
            validations["invalid_roles"].append({"source": "msi_staff", "id": staff_id, "role": raw_role})
            continue
        source_active = active_source_status(staff.get("status"))
        status = "active" if source_active else "disabled"
        if not source_active:
            validations["disabled_or_inactive_users"].append({"source": "msi_staff", "id": staff_id})
        if not normalize_text(staff.get("password_hash")):
            validations["missing_password_hash"].append({"source": "msi_staff", "id": staff_id})
            status = "disabled"
        accounts.append(
            planned_account(
                source_type="staff",
                source_id=staff_id,
                login=staff.get("login"),
                role=role,
                status=status,
                full_name=staff.get("display_name") or staff.get("login"),
                phone=staff.get("phone"),
                password_hash=staff.get("password_hash"),
                profile={
                    "table": "staff_profiles",
                    "staff_id": staff_id,
                    "job_title": role,
                    "department": role,
                },
                telegram_user_id=staff.get("telegram_user_id"),
                telegram_username=staff.get("telegram_username"),
            )
        )

    student_codes = [normalize_text(row.get("student_code")).upper() for row in student_rows]
    validations["student_code_conflicts"] = duplicate_values(student_codes)
    for student in student_rows:
        student_id = int(student.get("student_db_id") or 0)
        has_password = bool(normalize_text(student.get("password_hash")))
        source_active = active_source_status(student.get("status"))
        if not has_password:
            validations["students_without_auth"].append(student_id)
            validations["missing_password_hash"].append({"source": "students", "id": student_id})
        if not source_active:
            validations["disabled_or_inactive_users"].append({"source": "students", "id": student_id})
        status = "active" if source_active and has_password else "disabled"
        accounts.append(
            planned_account(
                source_type="student",
                source_id=student_id,
                login=student.get("student_code"),
                role="student",
                status=status,
                full_name=student.get("full_name"),
                password_hash=student.get("password_hash"),
                profile={
                    "table": "student_profiles",
                    "student_id": student_id,
                    "school_id": student.get("school_id"),
                    "student_code": normalize_text(student.get("student_code")).upper(),
                    "class_id": None,
                },
                telegram_user_id=student.get("telegram_user_id"),
            )
        )

    reserved_logins = {
        normalize_login(account.get("login"))
        for account in accounts
        if normalize_login(account.get("login"))
    }
    for parent in parent_rows:
        parent_id = int(parent.get("parent_id") or 0)
        has_telegram = bool(parent.get("telegram_user_id"))
        source_active = active_source_status(parent.get("status"))
        if not has_telegram:
            validations["parents_without_telegram"].append(parent_id)
        if not source_active:
            validations["disabled_or_inactive_users"].append({"source": "parents", "id": parent_id})
        status = "active" if source_active and has_telegram else "pending" if source_active else "disabled"
        accounts.append(
            planned_account(
                source_type="parent",
                source_id=parent_id,
                login="",
                role="parent",
                status=status,
                full_name=parent.get("display_name") or "Parent",
                phone=parent.get("phone"),
                profile={
                    "table": "parent_profiles",
                    "parent_id": parent_id,
                    "telegram_username": normalize_text(parent.get("telegram_username")) or None,
                },
                telegram_user_id=parent.get("telegram_user_id"),
                telegram_username=parent.get("telegram_username"),
            )
        )

    for row in teacher_staff_rows:
        teacher_id = int(row.get("teacher_id") or 0)
        staff_id = int(row.get("staff_id") or 0)
        if teacher_id <= 0:
            continue
        teacher_sources.append(
            {
                "staff_id": staff_id,
                "teacher_id": teacher_id,
                "teacher_name": row.get("teacher_name"),
                "old_login": row.get("old_login"),
            }
        )

    teacher_code_map = generate_teacher_code_map(
        teacher_sources,
        reserved_logins=reserved_logins,
    )
    teacher_staff_by_id = {
        int(row.get("staff_id") or 0): row for row in teacher_staff_rows
    }
    for mapping in teacher_code_map:
        staff = teacher_staff_by_id.get(int(mapping["staff_id"]), {})
        source_active = active_source_status(staff.get("staff_status")) and active_source_status(staff.get("teacher_status") or "active")
        if not source_active:
            validations["disabled_or_inactive_users"].append({"source": "teachers", "id": mapping["teacher_id"]})
        has_password = bool(normalize_text(staff.get("password_hash")))
        if not has_password:
            validations["missing_password_hash"].append({"source": "teachers", "id": mapping["teacher_id"]})
        status = "active" if source_active and has_password else "disabled"
        accounts.append(
            planned_account(
                source_type="teacher",
                source_id=int(mapping["teacher_id"]),
                login=mapping["new_teacher_code"],
                role="teacher",
                status=status,
                full_name=mapping.get("teacher_name"),
                phone=staff.get("phone"),
                password_hash=staff.get("password_hash"),
                profile={
                    "table": "teacher_profiles",
                    "teacher_id": int(mapping["teacher_id"]),
                    "school_id": None,
                    "teacher_code": mapping["new_teacher_code"],
                    "legacy_login": mapping["old_teacher_login"],
                },
                telegram_user_id=staff.get("telegram_user_id"),
                telegram_username=staff.get("telegram_username"),
            )
        )

    login_values = [normalize_login(account.get("login")) for account in accounts]
    validations["duplicate_logins"] = duplicate_values(login_values)

    telegram_values = [
        str(account["telegram_user_id"])
        for account in accounts
        if account.get("telegram_user_id")
    ]
    validations["duplicate_telegram_ids"] = duplicate_values(telegram_values)

    for mapping in teacher_code_map:
        if mapping["conflict_status"] == "generated_due_to_conflict":
            validations["teacher_code_conflicts"].append(mapping)

    blocking = bool(
        validations["duplicate_logins"]
        or validations["duplicate_telegram_ids"]
        or validations["invalid_roles"]
        or validations["student_code_conflicts"]
    )

    return {
        "accounts": accounts,
        "teacher_code_map": teacher_code_map,
        "validations": validations,
        "blocking": blocking,
        "counts": {
            "planned_accounts": len(accounts),
            "by_role": dict(Counter(account["role"] for account in accounts)),
            "telegram_links": sum(1 for account in accounts if account.get("telegram_user_id")),
        },
    }


def account_tables_exist(conn) -> bool:
    row = conn.execute("SELECT to_regclass('msi_v2.accounts') AS table_name").fetchone()
    return bool(row and row.get("table_name"))


def find_account_id(conn, account: dict[str, Any]) -> int | None:
    legacy_source_table = account.get("legacy_source_table")
    legacy_source_id = account.get("legacy_source_id")
    if legacy_source_table and legacy_source_id:
        row = conn.execute(
            """
            SELECT id
            FROM msi_v2.accounts
            WHERE legacy_source_table = %s
              AND legacy_source_id = %s
            LIMIT 1
            """,
            (legacy_source_table, legacy_source_id),
        ).fetchone()
        if row:
            return int(row["id"])

    profile = account.get("profile") or {}
    profile_table = profile.get("table")
    source_lookup = {
        "staff_profiles": ("staff_id", profile.get("staff_id")),
        "student_profiles": ("student_id", profile.get("student_id")),
        "teacher_profiles": ("teacher_id", profile.get("teacher_id")),
        "parent_profiles": ("parent_id", profile.get("parent_id")),
    }
    if profile_table in source_lookup:
        column, value = source_lookup[profile_table]
        if value:
            row = conn.execute(
                f"""
                SELECT account_id
                FROM msi_v2.{profile_table}
                WHERE {column} = %s
                LIMIT 1
                """,
                (value,),
            ).fetchone()
            if row:
                return int(row["account_id"])
    if account.get("login"):
        row = conn.execute(
            """
            SELECT id
            FROM msi_v2.accounts
            WHERE lower(btrim(login)) = lower(btrim(%s))
            LIMIT 1
            """,
            (account["login"],),
        ).fetchone()
        if row:
            return int(row["id"])
    return None


def upsert_account(conn, account: dict[str, Any]) -> tuple[int, str]:
    account_id = find_account_id(conn, account)
    params = (
        account.get("login"),
        account.get("password_hash"),
        account["role"],
        account["status"],
        account.get("full_name") or "",
        account.get("phone"),
        account.get("legacy_source_table") or "",
        account.get("legacy_source_id"),
    )
    if account_id:
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s,
                password_hash = %s,
                role = %s,
                status = %s,
                full_name = %s,
                phone = %s,
                legacy_source_table = %s,
                legacy_source_id = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (*params, account_id),
        )
        return account_id, "updated"
    row = conn.execute(
        """
        INSERT INTO msi_v2.accounts (
            login, password_hash, role, status, full_name, phone,
            legacy_source_table, legacy_source_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        params,
    ).fetchone()
    return int(row["id"]), "created"


def upsert_profile(conn, account_id: int, account: dict[str, Any]) -> str:
    profile = account.get("profile") or {}
    table = profile.get("table")
    status = account["status"]
    if table == "staff_profiles":
        staff_id = int(profile.get("staff_id") or 0)
        existing = conn.execute(
            "SELECT id FROM msi_v2.staff_profiles WHERE staff_id = %s",
            (staff_id,),
        ).fetchone()
        values = (
            account_id,
            staff_id,
            profile.get("job_title"),
            profile.get("department"),
            status,
        )
        if existing:
            conn.execute(
                """
                UPDATE msi_v2.staff_profiles
                SET account_id = %s, job_title = %s, department = %s,
                    status = %s, updated_at = now()
                WHERE staff_id = %s
                """,
                (account_id, profile.get("job_title"), profile.get("department"), status, staff_id),
            )
            return "updated"
        conn.execute(
            """
            INSERT INTO msi_v2.staff_profiles (
                account_id, staff_id, job_title, department, status
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            values,
        )
        return "created"
    if table == "student_profiles":
        student_id = int(profile.get("student_id") or 0)
        existing = conn.execute(
            "SELECT id FROM msi_v2.student_profiles WHERE student_id = %s",
            (student_id,),
        ).fetchone()
        values = (
            account_id,
            student_id,
            profile.get("school_id"),
            profile.get("student_code"),
            profile.get("class_id"),
            status,
        )
        if existing:
            conn.execute(
                """
                UPDATE msi_v2.student_profiles
                SET account_id = %s, school_id = %s, student_code = %s,
                    class_id = %s, status = %s, updated_at = now()
                WHERE student_id = %s
                """,
                (
                    account_id,
                    profile.get("school_id"),
                    profile.get("student_code"),
                    profile.get("class_id"),
                    status,
                    student_id,
                ),
            )
            return "updated"
        conn.execute(
            """
            INSERT INTO msi_v2.student_profiles (
                account_id, student_id, school_id, student_code, class_id, status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            values,
        )
        return "created"
    if table == "teacher_profiles":
        teacher_id = int(profile.get("teacher_id") or 0)
        existing = conn.execute(
            "SELECT id FROM msi_v2.teacher_profiles WHERE teacher_id = %s",
            (teacher_id,),
        ).fetchone()
        values = (
            account_id,
            teacher_id,
            profile.get("school_id"),
            profile.get("teacher_code"),
            profile.get("legacy_login") or "",
            status,
        )
        if existing:
            conn.execute(
                """
                UPDATE msi_v2.teacher_profiles
                SET account_id = %s, school_id = %s, teacher_code = %s,
                    legacy_login = %s, status = %s, updated_at = now()
                WHERE teacher_id = %s
                """,
                (
                    account_id,
                    profile.get("school_id"),
                    profile.get("teacher_code"),
                    profile.get("legacy_login") or "",
                    status,
                    teacher_id,
                ),
            )
            return "updated"
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_profiles (
                account_id, teacher_id, school_id, teacher_code, legacy_login, status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            values,
        )
        return "created"
    if table == "parent_profiles":
        parent_id = int(profile.get("parent_id") or 0)
        existing = conn.execute(
            "SELECT id FROM msi_v2.parent_profiles WHERE parent_id = %s",
            (parent_id,),
        ).fetchone()
        values = (
            account_id,
            parent_id,
            profile.get("telegram_username"),
            status,
        )
        if existing:
            conn.execute(
                """
                UPDATE msi_v2.parent_profiles
                SET account_id = %s, telegram_username = %s,
                    status = %s, updated_at = now()
                WHERE parent_id = %s
                """,
                (account_id, profile.get("telegram_username"), status, parent_id),
            )
            return "updated"
        conn.execute(
            """
            INSERT INTO msi_v2.parent_profiles (
                account_id, parent_id, telegram_username, status
            )
            VALUES (%s, %s, %s, %s)
            """,
            values,
        )
        return "created"
    return "skipped"


def upsert_telegram_link(conn, account_id: int, account: dict[str, Any]) -> str:
    telegram_user_id = account.get("telegram_user_id")
    if not telegram_user_id:
        return "skipped"
    row = conn.execute(
        """
        SELECT id, account_id
        FROM msi_v2.account_telegram_links
        WHERE telegram_user_id = %s
        LIMIT 1
        """,
        (telegram_user_id,),
    ).fetchone()
    if row:
        existing_account_id = int(row["account_id"])
        if existing_account_id != int(account_id):
            return "conflict"
        conn.execute(
            """
            UPDATE msi_v2.account_telegram_links
            SET telegram_username = %s, status = 'active'
            WHERE id = %s
            """,
            (account.get("telegram_username"), int(row["id"])),
        )
        return "updated"
    conn.execute(
        """
        INSERT INTO msi_v2.account_telegram_links (
            account_id, telegram_user_id, telegram_username, status
        )
        VALUES (%s, %s, %s, 'active')
        """,
        (account_id, telegram_user_id, account.get("telegram_username")),
    )
    return "created"


def apply_plan(conn, plan: dict[str, Any]) -> dict[str, int]:
    if plan.get("blocking"):
        raise RuntimeError("Blocking validation errors exist; refusing to apply.")
    if not account_tables_exist(conn):
        raise RuntimeError("msi_v2.accounts does not exist. Run Alembic migration first.")

    stats = Counter()
    for account in plan["accounts"]:
        account_id, account_action = upsert_account(conn, account)
        stats[f"accounts_{account_action}"] += 1
        profile_action = upsert_profile(conn, account_id, account)
        stats[f"profiles_{profile_action}"] += 1
        telegram_action = upsert_telegram_link(conn, account_id, account)
        stats[f"telegram_{telegram_action}"] += 1
    return dict(stats)


def compact_validations(validations: dict[str, Any]) -> dict[str, Any]:
    compact = {}
    for key, value in validations.items():
        if isinstance(value, dict):
            compact[key] = {"count": len(value), "items": value}
        elif isinstance(value, list):
            compact[key] = {"count": len(value), "items": value}
        else:
            compact[key] = value
    return compact


def markdown_report(plan: dict[str, Any], *, mode: str, apply_stats: dict[str, int] | None) -> str:
    validations = plan["validations"]
    lines = [
        "# Phase 1 Legacy Identity To Accounts Report",
        "",
        f"- Mode: `{mode}`",
        f"- Generated at UTC: `{datetime.now(timezone.utc).isoformat()}`",
        "- Behavior: non-destructive; legacy auth tables are not deleted or changed.",
        "",
        "## Backup Plan",
        "",
        "- Full database backup should be taken before `--apply`.",
        "- Current local `pg_dump` is known to be version 16.13 while the PostgreSQL server is 18.3.",
        "- If that version mismatch remains, do not run destructive commands; use a matching PostgreSQL 18 client or provider-level backup before apply.",
        "",
        "## Planned Accounts",
        "",
        f"- Total planned accounts: {plan['counts']['planned_accounts']}",
        f"- Planned Telegram links: {plan['counts']['telegram_links']}",
        "",
        "| Role | Count |",
        "|---|---:|",
    ]
    for role, count in sorted(plan["counts"]["by_role"].items()):
        lines.append(f"| `{role}` | {count} |")

    lines.extend(
        [
            "",
            "## Validation Summary",
            "",
            "| Validation | Count |",
            "|---|---:|",
        ]
    )
    for key, value in compact_validations(validations).items():
        count = value.get("count") if isinstance(value, dict) else value
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            f"- Blocking validation errors: {'yes' if plan.get('blocking') else 'no'}",
            "",
            "## Teacher Code Mapping",
            "",
            "| Teacher ID | Teacher Name | Old Login | New Code | Conflict Status |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in plan["teacher_code_map"]:
        lines.append(
            "| {teacher_id} | {teacher_name} | `{old_teacher_login}` | `{new_teacher_code}` | `{conflict_status}` |".format(
                teacher_id=row["teacher_id"],
                teacher_name=normalize_text(row["teacher_name"]) or "-",
                old_teacher_login=normalize_text(row["old_teacher_login"]) or "-",
                new_teacher_code=row["new_teacher_code"],
                conflict_status=row["conflict_status"],
            )
        )

    if apply_stats is not None:
        lines.extend(
            [
                "",
                "## Apply Summary",
                "",
                "| Action | Count |",
                "|---|---:|",
            ]
        )
        for key, value in sorted(apply_stats.items()):
            lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Dry-run mode does not write to PostgreSQL.",
            "- Apply mode refuses to run when blocking validation errors exist.",
            "- Parent accounts are Telegram-first and do not receive Phase 1 login values.",
            "- Parent accounts without Telegram are planned as `pending` and receive no Telegram link.",
            "- Accounts store legacy source table/id values for idempotency and debugging.",
            "- Students without auth are planned as `disabled`; no passwords are invented.",
            "- Existing teacher logins are reported and mapped to `TCH0001` format.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_reports(
    plan: dict[str, Any],
    *,
    report_dir: Path,
    mode: str,
    apply_stats: dict[str, int] | None = None,
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_timestamp()
    stem = f"phase1_accounts_{mode}_{stamp}"
    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"
    payload = {
        "mode": mode,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": plan["counts"],
        "validations": plan["validations"],
        "blocking": plan["blocking"],
        "teacher_code_map": plan["teacher_code_map"],
        "apply_stats": apply_stats,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(
        markdown_report(plan, mode=mode, apply_stats=apply_stats),
        encoding="utf-8",
    )
    return md_path, json_path


def run_migration(
    *,
    apply: bool,
    report_dir: Path,
    rows: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[dict[str, Any], dict[str, int] | None, tuple[Path, Path]]:
    mode = "apply" if apply else "dry_run"
    apply_stats = None
    if rows is not None:
        plan = build_plan(rows)
        if apply:
            raise RuntimeError("Cannot apply with injected rows; provide a database connection.")
        report_paths = write_reports(plan, report_dir=report_dir, mode=mode, apply_stats=None)
        return plan, None, report_paths

    with connect_auth_db() as conn:
        plan = build_plan(load_legacy_rows(conn))
        if apply:
            apply_stats = apply_plan(conn, plan)
            conn.commit()
        report_paths = write_reports(plan, report_dir=report_dir, mode=mode, apply_stats=apply_stats)
    return plan, apply_stats, report_paths


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or apply the MSI LMS Phase 1 shared accounts migration."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Build reports only; do not write.")
    mode.add_argument("--apply", action="store_true", help="Write to new account tables.")
    parser.add_argument(
        "--report-dir",
        default=str(REPO_ROOT / "migration_reports"),
        help="Directory for Markdown and JSON reports.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    report_dir = Path(args.report_dir).expanduser().resolve()
    try:
        plan, apply_stats, (md_path, json_path) = run_migration(
            apply=bool(args.apply),
            report_dir=report_dir,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mode = "apply" if args.apply else "dry-run"
    print(f"Mode: {mode}")
    print(f"Planned accounts: {plan['counts']['planned_accounts']}")
    print(f"Blocking validation errors: {'yes' if plan['blocking'] else 'no'}")
    if apply_stats is not None:
        print(f"Apply stats: {json.dumps(apply_stats, sort_keys=True)}")
    print(f"Markdown report: {md_path}")
    print(f"JSON report: {json_path}")
    return 0 if not (args.apply and plan["blocking"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
