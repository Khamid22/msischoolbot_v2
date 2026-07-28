"""Enrollment persistence used by the admissions contract."""

from __future__ import annotations

from collections.abc import Iterable

from backend.core.unit_of_work import Connection


def activate_group_enrollments(
    conn: Connection,
    *,
    student_id: int,
    group_ids: Iterable[int],
) -> tuple[int, ...]:
    public_dashboard_row = conn.execute(
        "SELECT nextval('msi_v2.legacy_dashboard_id_seq') AS dashboard_id"
    ).fetchone()
    public_dashboard_id = int(public_dashboard_row["dashboard_id"])
    enrollment_ids: list[int] = []
    for group_id in group_ids:
        enrollment_row = conn.execute(
            "SELECT nextval('msi_v2.legacy_enrollment_id_seq') AS enrollment_id"
        ).fetchone()
        enrollment_id = int(enrollment_row["enrollment_id"])
        row = conn.execute(
            """
            INSERT INTO msi_v2.group_students (
                group_id, student_id, enrollment_status, joined_at,
                legacy_enrollment_id, legacy_public_dashboard_id
            )
            VALUES (%s, %s, 'active', now(), %s, %s)
            ON CONFLICT (group_id, student_id) DO UPDATE SET
                enrollment_status = 'active',
                left_at = NULL
            RETURNING legacy_enrollment_id
            """,
            (
                int(group_id),
                int(student_id),
                enrollment_id,
                public_dashboard_id,
            ),
        ).fetchone()
        if not row:
            raise RuntimeError("A selected group enrollment could not be activated.")
        enrollment_ids.append(int(row["legacy_enrollment_id"]))
    return tuple(enrollment_ids)


__all__ = ["activate_group_enrollments"]
