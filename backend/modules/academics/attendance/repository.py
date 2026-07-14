"""Attendance persistence operations."""


def delete_attendance_record(conn, *, lesson_session_id, student_id):
    return conn.execute(
        """
        DELETE FROM msi_v2.attendance_records
        WHERE lesson_session_id = %s AND student_id = %s
        RETURNING id
        """,
        (int(lesson_session_id), int(student_id)),
    ).fetchone()


def upsert_attendance_record(
    conn,
    *,
    lesson_session_id,
    group_id,
    student_id,
    status,
    actor_staff_id,
    recorded_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.attendance_records (
            lesson_session_id, group_id, student_id, attendance_status,
            recorded_by_staff_id, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
            attendance_status = excluded.attendance_status,
            recorded_by_staff_id = excluded.recorded_by_staff_id,
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (
            int(lesson_session_id), int(group_id), int(student_id), status,
            int(actor_staff_id) if actor_staff_id else None, recorded_at, recorded_at,
        ),
    ).fetchone()


__all__ = ["delete_attendance_record", "upsert_attendance_record"]
