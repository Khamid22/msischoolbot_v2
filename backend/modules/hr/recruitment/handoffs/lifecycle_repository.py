"""Identity cleanup and restoration persistence for Recruitment handoffs."""

from __future__ import annotations

from typing import Any


def lock_academy_removal_row(conn: Any, academy_teacher_id: int) -> Any:
    return conn.execute(
        """
        SELECT academy.id, academy.recruitment_candidate_id,
               academy.academy_status, academy.account_onboarding_status,
               academy.user_id AS staff_id, academy.promoted_teacher_id,
               COALESCE(staff.teacher_id, 0) AS teacher_id,
               COALESCE(staff.login, '') AS login,
               COALESCE(staff.role, '') AS staff_role,
               COALESCE(identity_teacher.status, '') AS teacher_status
        FROM msi_v2.academy_teachers academy
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = academy.user_id
        LEFT JOIN msi_v2.teachers identity_teacher ON identity_teacher.id = staff.teacher_id
        WHERE academy.id = %s
        FOR UPDATE OF academy
        """,
        (int(academy_teacher_id),),
    ).fetchone()


def lock_academy_identity_rows(
    conn: Any,
    *,
    staff_id: int,
    teacher_id: int,
) -> tuple[Any, Any]:
    staff = conn.execute(
        """
        SELECT id, teacher_id, role, status
        FROM msi_v2.msi_staff
        WHERE id = %s
        FOR UPDATE
        """,
        (int(staff_id),),
    ).fetchone()
    teacher = conn.execute(
        """
        SELECT id, status, recruitment_candidate_id
        FROM msi_v2.teachers
        WHERE id = %s
        FOR UPDATE
        """,
        (int(teacher_id),),
    ).fetchone()
    return staff, teacher


def mark_academy_removed(
    conn: Any,
    *,
    academy_teacher_id: int,
    now: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.academy_teachers
        SET academy_status = 'rejected',
            updated_at = %s::timestamptz
        WHERE id = %s
          AND promoted_teacher_id IS NULL
        RETURNING id
        """,
        (now, int(academy_teacher_id)),
    ).fetchone()
    return bool(row)


def lock_teacher_handoff_row(conn: Any, *, kind: str, record_id: int) -> Any:
    if kind == "teacher_academy":
        return conn.execute(
            """
            SELECT academy.id AS record_id, academy.recruitment_candidate_id,
                   academy.academy_status AS roster_status,
                   academy.user_id AS staff_id, academy.promoted_teacher_id,
                   COALESCE(staff.teacher_id, 0) AS teacher_id
            FROM msi_v2.academy_teachers academy
            LEFT JOIN msi_v2.msi_staff staff ON staff.id = academy.user_id
            WHERE academy.id = %s
            FOR UPDATE OF academy
            """,
            (int(record_id),),
        ).fetchone()
    if kind == "active_teacher":
        return conn.execute(
            """
            SELECT teacher.id AS record_id, teacher.recruitment_candidate_id,
                   teacher.status AS roster_status,
                   COALESCE(staff.id, 0) AS staff_id,
                   teacher.id AS teacher_id,
                   NULL::bigint AS promoted_teacher_id
            FROM msi_v2.teachers teacher
            LEFT JOIN LATERAL (
                SELECT candidate.id
                FROM msi_v2.msi_staff candidate
                WHERE candidate.teacher_id = teacher.id
                  AND lower(candidate.role) = 'teacher'
                ORDER BY
                    CASE WHEN lower(candidate.status) = 'active' THEN 0 ELSE 1 END,
                    candidate.id
                LIMIT 1
            ) staff ON true
            WHERE teacher.id = %s
            FOR UPDATE OF teacher
            """,
            (int(record_id),),
        ).fetchone()
    raise ValueError("Unknown teacher handoff kind.")


def mark_teacher_handoff_closed(
    conn: Any,
    *,
    kind: str,
    record_id: int,
    action: str,
    now: str,
) -> bool:
    if action not in {"trash_bin", "rejected"}:
        raise ValueError("Unknown teacher handoff close action.")
    if kind == "teacher_academy":
        cursor = conn.execute(
            """
            UPDATE msi_v2.academy_teachers
            SET academy_status = %s,
                updated_at = %s::timestamptz
            WHERE id = %s
              AND promoted_teacher_id IS NULL
              AND COALESCE(academy_status, '') NOT IN ('rejected', 'trash_bin')
            """,
            (action, now, int(record_id)),
        )
        return int(getattr(cursor, "rowcount", 0) or 0) == 1
    if kind == "active_teacher":
        cursor = conn.execute(
            """
            UPDATE msi_v2.teachers
            SET status = %s, updated_at = %s::timestamptz
            WHERE id = %s
              AND status = 'active'
            """,
            (action, now, int(record_id)),
        )
        return int(getattr(cursor, "rowcount", 0) or 0) == 1
    raise ValueError("Unknown teacher handoff kind.")


def set_teacher_identity_enabled(
    conn: Any,
    *,
    staff_id: int,
    teacher_id: int,
    enabled: bool,
    now: str,
) -> None:
    staff_status = "active" if enabled else "disabled"
    account_status = "active" if enabled else "disabled"
    if int(staff_id or 0):
        conn.execute(
            """
            UPDATE msi_v2.msi_staff
            SET status = %s, updated_at = %s::timestamptz
            WHERE id = %s AND lower(role) = 'teacher'
            """,
            (staff_status, now, int(staff_id)),
        )
    conn.execute(
        """
        UPDATE msi_v2.accounts account
        SET status = %s, session_version = account.session_version + 1,
            updated_at = %s::timestamptz
        WHERE lower(account.role) = 'teacher'
          AND (
              (
                  %s > 0
                  AND account.legacy_source_table = 'msi_staff'
                  AND account.legacy_source_id = %s
              )
              OR (
                  %s > 0
                  AND EXISTS (
                      SELECT 1
                      FROM msi_v2.teacher_profiles profile
                      WHERE profile.account_id = account.id
                        AND profile.teacher_id = %s
                  )
              )
          )
        """,
        (
            account_status,
            now,
            int(staff_id or 0),
            int(staff_id or 0),
            int(teacher_id or 0),
            int(teacher_id or 0),
        ),
    )


def restore_teacher_handoff(
    conn: Any,
    *,
    candidate_id: int,
    kind: str,
    now: str,
) -> bool:
    if kind == "teacher_academy":
        row = conn.execute(
            """
            UPDATE msi_v2.academy_teachers academy
            SET academy_status = 'in_training',
                updated_at = %s::timestamptz
            WHERE academy.recruitment_candidate_id = %s
              AND academy.academy_status = 'trash_bin'
              AND academy.promoted_teacher_id IS NULL
            RETURNING academy.user_id AS staff_id
            """,
            (now, int(candidate_id)),
        ).fetchone()
        if not row:
            return False
        staff_id = int(row["staff_id"] or 0)
        teacher_row = (
            conn.execute(
                "SELECT COALESCE(teacher_id, 0) AS teacher_id FROM msi_v2.msi_staff WHERE id = %s",
                (staff_id,),
            ).fetchone()
            if staff_id
            else None
        )
        set_teacher_identity_enabled(
            conn,
            staff_id=staff_id,
            teacher_id=int(teacher_row["teacher_id"] or 0) if teacher_row else 0,
            enabled=True,
            now=now,
        )
        return True
    if kind == "active_teacher":
        row = conn.execute(
            """
            UPDATE msi_v2.teachers teacher
            SET status = 'active', updated_at = %s::timestamptz
            WHERE teacher.recruitment_candidate_id = %s
              AND teacher.status = 'trash_bin'
            RETURNING teacher.id
            """,
            (now, int(candidate_id)),
        ).fetchone()
        if not row:
            return False
        teacher_id = int(row["id"])
        staff = conn.execute(
            """
            SELECT id
            FROM msi_v2.msi_staff
            WHERE teacher_id = %s AND lower(role) = 'teacher'
            ORDER BY id
            LIMIT 1
            """,
            (teacher_id,),
        ).fetchone()
        set_teacher_identity_enabled(
            conn,
            staff_id=int(staff["id"] or 0) if staff else 0,
            teacher_id=teacher_id,
            enabled=True,
            now=now,
        )
        return True
    return False


def list_teacher_account_ids_for_staff(conn: Any, staff_id: int) -> list[int]:
    if not int(staff_id or 0):
        return []
    rows = conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE legacy_source_table = 'msi_staff'
          AND legacy_source_id = %s
          AND role = 'teacher'
        ORDER BY id
        FOR UPDATE
        """,
        (int(staff_id),),
    ).fetchall()
    return [int(row["id"]) for row in rows if int(row["id"] or 0) > 0]


def cancel_pending_candidate_tasks(
    conn: Any,
    *,
    candidate_id: int,
    actor_account_id: int | None,
    now: str,
) -> list[int]:
    rows = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_tasks
        SET status = 'cancelled', cancelled_at = %s::timestamptz,
            completed_at = NULL, updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE candidate_id = %s AND status = 'pending'
        RETURNING id
        """,
        (now, actor_account_id, now, int(candidate_id)),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def delete_generated_academy_identity(
    conn: Any,
    *,
    staff_id: int,
    teacher_id: int,
    account_ids: list[int],
) -> None:
    safe_account_ids = [int(item) for item in account_ids if int(item or 0) > 0]
    if safe_account_ids:
        conn.execute(
            "DELETE FROM msi_v2.teacher_profiles WHERE account_id = ANY(%s::bigint[])",
            (safe_account_ids,),
        )
        conn.execute(
            "DELETE FROM msi_v2.staff_profiles WHERE account_id = ANY(%s::bigint[])",
            (safe_account_ids,),
        )
    if int(teacher_id or 0):
        conn.execute(
            "DELETE FROM msi_v2.teacher_profiles WHERE teacher_id = %s",
            (int(teacher_id),),
        )
    if int(staff_id or 0):
        conn.execute(
            "DELETE FROM msi_v2.staff_profiles WHERE staff_id = %s",
            (int(staff_id),),
        )
    if safe_account_ids:
        conn.execute(
            "DELETE FROM msi_v2.accounts WHERE id = ANY(%s::bigint[])",
            (safe_account_ids,),
        )
    if int(staff_id or 0):
        conn.execute(
            "DELETE FROM msi_v2.msi_staff WHERE id = %s",
            (int(staff_id),),
        )
    if int(teacher_id or 0):
        conn.execute(
            "DELETE FROM msi_v2.teachers WHERE id = %s AND status = 'academy'",
            (int(teacher_id),),
        )


__all__ = [
    "cancel_pending_candidate_tasks",
    "delete_generated_academy_identity",
    "list_teacher_account_ids_for_staff",
    "lock_academy_identity_rows",
    "lock_academy_removal_row",
    "lock_teacher_handoff_row",
    "mark_academy_removed",
    "mark_teacher_handoff_closed",
    "restore_teacher_handoff",
    "set_teacher_identity_enabled",
]
