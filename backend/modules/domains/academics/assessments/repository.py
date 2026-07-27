"""Assessment result persistence operations."""


def find_exam_program_item(conn, *, group_id, exam_name):
    return conn.execute(
        """
        SELECT spi.id
        FROM msi_v2.groups g
        JOIN msi_v2.subject_program_items spi ON spi.program_id = g.program_id
        WHERE g.id = %s AND spi.item_type = 'exam' AND lower(spi.title) = lower(%s)
        LIMIT 1
        """,
        (int(group_id), exam_name),
    ).fetchone()


def insert_exam_result_if_missing(
    conn,
    *,
    group_id,
    program_item_id,
    student_id,
    exam_name,
    attempt,
    score,
    actor_staff_id,
    recorded_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.exam_results (
            group_id, program_item_id, student_id, exam_name, attempt, score,
            score_scale, recorded_by_staff_id, created_at, updated_at
        )
        SELECT %s, %s, %s, %s, %s, %s, 9, %s, %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.exam_results er
            WHERE er.group_id = %s AND er.student_id = %s
              AND lower(er.exam_name) = lower(%s) AND lower(er.attempt) = lower(%s)
        )
        RETURNING id
        """,
        (
            int(group_id), program_item_id, int(student_id), exam_name, attempt, score,
            int(actor_staff_id) if actor_staff_id else None, recorded_at, recorded_at,
            int(group_id), int(student_id), exam_name, attempt,
        ),
    ).fetchone()


def update_exam_result(
    conn,
    *,
    group_id,
    program_item_id,
    student_id,
    exam_name,
    attempt,
    score,
    actor_staff_id,
    recorded_at,
):
    return conn.execute(
        """
        UPDATE msi_v2.exam_results
        SET score = %s, program_item_id = COALESCE(%s, program_item_id),
            recorded_by_staff_id = %s, updated_at = %s
        WHERE group_id = %s AND student_id = %s
          AND lower(exam_name) = lower(%s) AND lower(attempt) = lower(%s)
        RETURNING id
        """,
        (
            score, program_item_id, int(actor_staff_id) if actor_staff_id else None,
            recorded_at, int(group_id), int(student_id), exam_name, attempt,
        ),
    ).fetchone()


__all__ = ["find_exam_program_item", "insert_exam_result_if_missing", "update_exam_result"]
