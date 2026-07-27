"""Teacher Academy lifecycle, deletion, and promotion persistence."""

from __future__ import annotations

from typing import Any


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


def delete_by_ids(conn: Any, table_name: str, id_column: str, ids: list[int]) -> None:
    safe_ids = [int(item) for item in ids if int(item or 0) > 0]
    if not safe_ids:
        return
    placeholders = ", ".join(["%s"] * len(safe_ids))
    conn.execute(
        f"DELETE FROM {table_name} WHERE {id_column} IN ({placeholders})",
        tuple(safe_ids),
    )


def delete_teacher_profiles_for_delete(
    conn: Any,
    *,
    teacher_id: int,
    account_ids: list[int],
) -> None:
    if account_ids:
        delete_by_ids(conn, "msi_v2.teacher_profiles", "account_id", account_ids)
    if teacher_id:
        conn.execute(
            "DELETE FROM msi_v2.teacher_profiles WHERE teacher_id = %s",
            (teacher_id,),
        )


def delete_staff_profiles_for_delete(
    conn: Any,
    *,
    staff_id: int,
    account_ids: list[int],
) -> None:
    if account_ids:
        delete_by_ids(conn, "msi_v2.staff_profiles", "account_id", account_ids)
    if staff_id:
        conn.execute(
            "DELETE FROM msi_v2.staff_profiles WHERE staff_id = %s",
            (staff_id,),
        )


def delete_teacher_accounts_for_delete(conn: Any, account_ids: list[int]) -> None:
    delete_by_ids(conn, "msi_v2.accounts", "id", account_ids)


def delete_academy_teacher_row(conn: Any, academy_teacher_id: int) -> None:
    conn.execute(
        "DELETE FROM msi_v2.academy_teachers WHERE id = %s",
        (academy_teacher_id,),
    )


def delete_academy_teacher_staff_row(conn: Any, staff_id: int) -> None:
    if staff_id:
        conn.execute("DELETE FROM msi_v2.msi_staff WHERE id = %s", (staff_id,))


def delete_academy_teacher_profile_row(conn: Any, teacher_id: int) -> None:
    if teacher_id:
        conn.execute(
            "DELETE FROM msi_v2.teachers WHERE id = %s AND status = 'academy'",
            (teacher_id,),
        )


def update_academy_teacher_status(
    conn: Any,
    *,
    academy_teacher_id: int,
    status: str,
    updated_at: str,
) -> None:
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
    conn: Any,
    *,
    academy_teacher_id: int,
    promoted_teacher_id: int,
    updated_at: str,
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
    "approve_academy_teacher_promotion",
    "delete_academy_teacher_profile_row",
    "delete_academy_teacher_row",
    "delete_academy_teacher_staff_row",
    "delete_by_ids",
    "delete_staff_profiles_for_delete",
    "delete_teacher_accounts_for_delete",
    "delete_teacher_profiles_for_delete",
    "get_academy_teacher_delete_row",
    "list_teacher_account_ids_for_staff",
    "touch_academy_teacher",
    "update_academy_teacher_status",
]
