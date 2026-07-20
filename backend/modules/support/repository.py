def _ticket_row_select():
    return """
        SELECT
            t.id,
            t.parent_id AS parent_admin_id,
            COALESCE(st.legacy_student_row_id, 0) AS student_row_id,
            t.category,
            t.topic,
            COALESCE(opening.body, '') AS message,
            t.status,
            COALESCE(latest_staff.body, '') AS reply,
            to_char(t.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
            to_char(t.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at,
            COALESCE(to_char(t.resolved_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS resolved_at,
            COALESCE(assigned.login, assigned.display_name, '') AS assigned_to,
            COALESCE(p.display_name, '') AS parent_login,
            COALESCE(p.display_name, '') AS parent_display_name,
            COALESCE(p.phone, '') AS parent_phone,
            '' AS parent_email,
            COALESCE(p.telegram_username, '') AS parent_telegram_username,
            COALESCE(st.full_name, '') AS student_name,
            COALESCE(st.student_code, '') AS student_code,
            COALESCE(sch.school_name, '') AS school_name
        FROM msi_v2.support_tickets t
        LEFT JOIN msi_v2.parents p ON p.id = t.parent_id
        LEFT JOIN msi_v2.students st ON st.id = t.student_id
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        LEFT JOIN msi_v2.msi_staff assigned ON assigned.id = t.assigned_to_staff_id
        LEFT JOIN LATERAL (
            SELECT body
            FROM msi_v2.ticket_messages msg
            WHERE msg.ticket_id = t.id
              AND msg.author_type = 'parent'
            ORDER BY msg.created_at ASC, msg.id ASC
            LIMIT 1
        ) opening ON true
        LEFT JOIN LATERAL (
            SELECT body
            FROM msi_v2.ticket_messages msg
            WHERE msg.ticket_id = t.id
              AND msg.author_type <> 'parent'
            ORDER BY msg.created_at DESC, msg.id DESC
            LIMIT 1
        ) latest_staff ON true
    """


def list_parent_complaint_rows(conn, parent_admin_id=0):
    filters = []
    params = []
    if int(parent_admin_id or 0) > 0:
        filters.append("t.parent_id = %s")
        params.append(int(parent_admin_id))
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    return conn.execute(
        f"""
        {_ticket_row_select()}
        {where_clause}
        ORDER BY
            CASE t.status
                WHEN 'new' THEN 0
                WHEN 'escalated' THEN 1
                WHEN 'in_progress' THEN 2
                WHEN 'resolved' THEN 3
                ELSE 4
            END,
            t.updated_at DESC,
            t.id DESC
        """,
        tuple(params),
    ).fetchall()


def get_parent_complaint_row(conn, complaint_id):
    return conn.execute(
        f"""
        {_ticket_row_select()}
        WHERE t.id = %s
        """,
        (int(complaint_id),),
    ).fetchone()


def _resolve_student_v2_id(conn, student_row_id):
    if not int(student_row_id or 0):
        return None
    row = conn.execute(
        "SELECT id FROM msi_v2.students WHERE legacy_student_row_id = %s LIMIT 1",
        (int(student_row_id),),
    ).fetchone()
    return int(row["id"]) if row else None


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
    student_id = _resolve_student_v2_id(conn, student_row_id)
    inserted = conn.execute(
        """
        INSERT INTO msi_v2.support_tickets (
            parent_id,
            student_id,
            category,
            topic,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (
            int(parent_admin_id),
            student_id,
            str(category or "other").strip(),
            str(topic or "").strip(),
            str(status or "new").strip().casefold(),
            str(created_at or "").strip(),
            str(updated_at or "").strip(),
        ),
    ).fetchone()
    if inserted:
        insert_complaint_message_row(
            conn,
            complaint_id=int(inserted["id"]),
            author_role="parent",
            author_login="",
            body=message,
            created_at=created_at,
        )
    return inserted


def update_parent_complaint_row(
    conn,
    complaint_id,
    *,
    status,
    reply,
    updated_at,
    resolved_at,
    assigned_to="",
):
    conn.execute(
        """
        UPDATE msi_v2.support_tickets
        SET status = %s,
            assigned_to_staff_id = COALESCE(
                (
                    SELECT id
                    FROM msi_v2.msi_staff
                    WHERE lower(login) = lower(%s)
                       OR lower(display_name) = lower(%s)
                    ORDER BY id ASC
                    LIMIT 1
                ),
                assigned_to_staff_id
            ),
            updated_at = %s::timestamptz,
            resolved_at = CASE WHEN %s = '' THEN NULL ELSE %s::timestamptz END
        WHERE id = %s
        """,
        (
            str(status or "new").strip().casefold(),
            str(assigned_to or "").strip(),
            str(assigned_to or "").strip(),
            str(updated_at or "").strip(),
            str(resolved_at or "").strip(),
            str(resolved_at or "").strip(),
            int(complaint_id),
        ),
    )


def _author_type(author_role):
    role = str(author_role or "system").strip().casefold()
    if role == "parent":
        return "parent"
    if role in {
        "ceo",
        "customer_support",
        "academic_director",
        "head_of_department",
        "hr_manager",
        "teacher",
    }:
        return role
    return "system"


def list_complaint_message_rows(conn, complaint_id):
    return conn.execute(
        """
        SELECT
            msg.id,
            ticket_id AS complaint_id,
            author_type AS author_role,
            COALESCE(staff.login, parent.display_name, '') AS author_login,
            body,
            to_char(msg.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at
        FROM msi_v2.ticket_messages msg
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = msg.author_staff_id
        LEFT JOIN msi_v2.parents parent ON parent.id = msg.author_parent_id
        WHERE msg.ticket_id = %s
        ORDER BY msg.created_at ASC, msg.id ASC
        """,
        (int(complaint_id),),
    ).fetchall()


def insert_complaint_message_row(
    conn,
    *,
    complaint_id,
    author_role,
    author_login,
    body,
    created_at,
):
    author_type = _author_type(author_role)
    return conn.execute(
        """
        INSERT INTO msi_v2.ticket_messages (
            ticket_id,
            author_type,
            author_staff_id,
            author_parent_id,
            body,
            created_at
        )
        SELECT
            %s,
            %s,
            CASE WHEN %s <> 'parent' THEN (
                SELECT id
                FROM msi_v2.msi_staff
                WHERE lower(login) = lower(%s)
                   OR lower(display_name) = lower(%s)
                ORDER BY id ASC
                LIMIT 1
            ) ELSE NULL END,
            CASE WHEN %s = 'parent' THEN (
                SELECT parent_id
                FROM msi_v2.support_tickets
                WHERE id = %s
                LIMIT 1
            ) ELSE NULL END,
            %s,
            %s::timestamptz
        RETURNING id
        """,
        (
            int(complaint_id),
            author_type,
            author_type,
            str(author_login or "").strip(),
            str(author_login or "").strip(),
            author_type,
            int(complaint_id),
            str(body or "").strip(),
            str(created_at or "").strip(),
        ),
    ).fetchone()


def count_complaints_by_parent(conn):
    """Map of parent_id -> {total, open} ticket counts (open = not resolved)."""
    return conn.execute(
        """
        SELECT
            parent_id AS parent_admin_id,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE lower(status) <> 'resolved') AS open_count
        FROM msi_v2.support_tickets
        WHERE parent_id IS NOT NULL
        GROUP BY parent_id
        """
    ).fetchall()


__all__ = [
    "count_complaints_by_parent",
    "get_parent_complaint_row",
    "insert_complaint_message_row",
    "insert_parent_complaint_row",
    "list_complaint_message_rows",
    "list_parent_complaint_rows",
    "update_parent_complaint_row",
]
