"""Parent complaint SQL helpers."""


def list_parent_complaint_rows(conn, parent_admin_id=0):
    filters = []
    params = []
    if int(parent_admin_id or 0) > 0:
        filters.append("pc.parent_admin_id = %s")
        params.append(int(parent_admin_id))
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    return conn.execute(
        f"""
        SELECT
            pc.id,
            pc.parent_admin_id,
            pc.student_row_id,
            pc.category,
            pc.topic,
            pc.message,
            pc.status,
            pc.reply,
            pc.created_at,
            pc.updated_at,
            pc.resolved_at,
            a.login AS parent_login,
            s.full_name AS student_name,
            s.student_id AS student_code,
            s.school_name AS school_name
        FROM parent_complaints pc
        JOIN admins a ON a.id = pc.parent_admin_id
        LEFT JOIN students s ON s.id = pc.student_row_id
        {where_clause}
        ORDER BY
            CASE pc.status
                WHEN 'new' THEN 0
                WHEN 'escalated' THEN 1
                WHEN 'in_progress' THEN 2
                WHEN 'resolved' THEN 3
                ELSE 4
            END,
            pc.updated_at DESC,
            pc.id DESC
        """,
        tuple(params),
    ).fetchall()


def get_parent_complaint_row(conn, complaint_id):
    return conn.execute(
        """
        SELECT
            pc.id,
            pc.parent_admin_id,
            pc.student_row_id,
            pc.category,
            pc.topic,
            pc.message,
            pc.status,
            pc.reply,
            pc.created_at,
            pc.updated_at,
            pc.resolved_at,
            a.login AS parent_login,
            s.full_name AS student_name,
            s.student_id AS student_code,
            s.school_name AS school_name
        FROM parent_complaints pc
        JOIN admins a ON a.id = pc.parent_admin_id
        LEFT JOIN students s ON s.id = pc.student_row_id
        WHERE pc.id = %s
        """,
        (int(complaint_id),),
    ).fetchone()


def insert_parent_complaint_row(
    conn,
    *,
    parent_admin_id,
    student_row_id,
    category,
    topic,
    message,
    status,
    created_at,
    updated_at,
):
    normalized_student_id = int(student_row_id) if int(student_row_id or 0) > 0 else None
    return conn.execute(
        """
        INSERT INTO parent_complaints (
            parent_admin_id,
            student_row_id,
            category,
            topic,
            message,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            int(parent_admin_id),
            normalized_student_id,
            str(category or "other").strip(),
            str(topic or "").strip(),
            str(message or "").strip(),
            str(status or "new").strip().casefold(),
            str(created_at or "").strip(),
            str(updated_at or "").strip(),
        ),
    ).fetchone()


def update_parent_complaint_row(
    conn,
    complaint_id,
    *,
    status,
    reply,
    updated_at,
    resolved_at,
):
    conn.execute(
        """
        UPDATE parent_complaints
        SET status = %s,
            reply = %s,
            updated_at = %s,
            resolved_at = %s
        WHERE id = %s
        """,
        (
            str(status or "new").strip().casefold(),
            str(reply or "").strip(),
            str(updated_at or "").strip(),
            str(resolved_at or "").strip(),
            int(complaint_id),
        ),
    )


__all__ = [
    "get_parent_complaint_row",
    "insert_parent_complaint_row",
    "list_parent_complaint_rows",
    "update_parent_complaint_row",
]
