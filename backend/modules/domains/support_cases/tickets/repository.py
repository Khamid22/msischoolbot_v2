import json


def _ticket_row_select():
    return """
        SELECT
            t.id,
            t.parent_id AS parent_admin_id,
            COALESCE(st.id, 0) AS student_id,
            COALESCE(st.legacy_student_row_id, 0) AS student_row_id,
            COALESCE(sch.id, 0) AS school_id,
            t.category,
            t.topic,
            COALESCE(opening.body, '') AS message,
            t.status,
            t.priority,
            t.first_response_target_minutes,
            t.resolution_target_minutes,
            to_char(
                t.first_response_due_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
            ) AS first_response_due_at,
            to_char(
                t.resolution_due_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
            ) AS resolution_due_at,
            to_char(
                t.first_responded_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
            ) AS first_responded_at,
            to_char(
                t.waiting_on_requester_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
            ) AS waiting_on_requester_at,
            t.requester_wait_seconds,
            COALESCE(latest_staff.body, '') AS reply,
            to_char(t.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
            to_char(t.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at,
            to_char(
                t.updated_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
            ) AS cursor_updated_at,
            COALESCE(to_char(t.resolved_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS resolved_at,
            t.assigned_to_staff_id,
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


def get_parent_ticket_row(
    conn,
    *,
    ticket_id,
    parent_id,
    for_update=False,
):
    lock_clause = " FOR UPDATE OF t" if for_update else ""
    return conn.execute(
        f"""
        {_ticket_row_select()}
        WHERE t.id = %s
          AND t.parent_id = %s
        {lock_clause}
        """,
        (int(ticket_id), int(parent_id)),
    ).fetchone()


def get_ticket_row(conn, *, ticket_id, for_update=False):
    lock_clause = " FOR UPDATE OF t" if for_update else ""
    return conn.execute(
        f"""
        {_ticket_row_select()}
        WHERE t.id = %s
        {lock_clause}
        """,
        (int(ticket_id),),
    ).fetchone()


def list_support_ticket_rows(
    conn,
    *,
    search_text,
    selected_school_id,
    allowed_school_ids,
    all_schools,
    status,
    category,
    priority,
    sla_state,
    assigned_staff_id,
    is_unassigned,
    cursor_status_rank,
    cursor_updated_at,
    cursor_id,
    limit,
):
    status_rank = """
        CASE t.status
            WHEN 'new' THEN 0
            WHEN 'escalated' THEN 1
            WHEN 'in_progress' THEN 2
            WHEN 'resolved' THEN 3
            ELSE 4
        END
    """
    sla_expression = """
        CASE
            WHEN t.status = 'resolved' THEN
                CASE
                    WHEN t.resolved_at IS NOT NULL
                     AND t.resolution_due_at IS NOT NULL
                     AND t.resolved_at <= t.resolution_due_at
                    THEN 'met'
                    ELSE 'breached'
                END
            WHEN t.waiting_on_requester_at IS NOT NULL
             AND t.first_responded_at IS NOT NULL THEN 'paused'
            WHEN (
                (t.first_responded_at IS NULL AND now() >= t.first_response_due_at)
                OR now() >= t.resolution_due_at
            ) THEN 'breached'
            WHEN (
                t.first_responded_at IS NULL
                AND t.first_response_due_at - now()
                    <= make_interval(mins => t.first_response_target_minutes / 4)
            ) OR (
                t.first_responded_at IS NOT NULL
                AND t.resolution_due_at - now()
                    <= make_interval(mins => t.resolution_target_minutes / 4)
            ) THEN 'due_soon'
            ELSE 'on_track'
        END
    """
    search_pattern = f"%{str(search_text or '').strip()}%"
    cursor_timestamp = str(cursor_updated_at or "").strip() or None
    return conn.execute(
        f"""
        {_ticket_row_select()}
        WHERE (%s OR sch.id = ANY(%s::bigint[]))
          AND (%s::bigint IS NULL OR sch.id = %s)
          AND (%s = '' OR t.status = %s)
          AND (%s = '' OR t.category = %s)
          AND (%s = '' OR t.priority = %s)
          AND (%s = '' OR ({sla_expression}) = %s)
          AND (%s::bigint IS NULL OR t.assigned_to_staff_id = %s)
          AND (NOT %s OR t.assigned_to_staff_id IS NULL)
          AND (
                %s = ''
                OR t.topic ILIKE %s
                OR p.display_name ILIKE %s
                OR st.full_name ILIKE %s
                OR st.student_code ILIKE %s
          )
          AND (
                %s::timestamptz IS NULL
                OR {status_rank} > %s
                OR (
                    {status_rank} = %s
                    AND (
                        t.updated_at < %s::timestamptz
                        OR (t.updated_at = %s::timestamptz AND t.id < %s)
                    )
                )
          )
        ORDER BY {status_rank}, t.updated_at DESC, t.id DESC
        LIMIT %s
        """,
        (
            bool(all_schools),
            list(allowed_school_ids),
            selected_school_id,
            selected_school_id,
            str(status or ""),
            str(status or ""),
            str(category or ""),
            str(category or ""),
            str(priority or ""),
            str(priority or ""),
            str(sla_state or ""),
            str(sla_state or ""),
            assigned_staff_id,
            assigned_staff_id,
            bool(is_unassigned),
            str(search_text or "").strip(),
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            cursor_timestamp,
            int(cursor_status_rank),
            int(cursor_status_rank),
            cursor_timestamp,
            cursor_timestamp,
            int(cursor_id),
            int(limit),
        ),
    ).fetchall()


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
        WITH selected_student AS (
            SELECT id, school_id
            FROM msi_v2.students
            WHERE id = %s
        ),
        selected_policy AS (
            SELECT
                policy.first_response_minutes,
                policy.resolution_minutes
            FROM msi_v2.support_ticket_sla_policies policy
            LEFT JOIN selected_student student ON true
            WHERE policy.is_active
              AND policy.priority = 'normal'
              AND (
                    policy.school_id = student.school_id
                    OR policy.school_id IS NULL
              )
            ORDER BY policy.school_id NULLS LAST
            LIMIT 1
        )
        INSERT INTO msi_v2.support_tickets (
            parent_id,
            student_id,
            category,
            topic,
            status,
            priority,
            first_response_target_minutes,
            resolution_target_minutes,
            first_response_due_at,
            resolution_due_at,
            created_at,
            updated_at
        )
        SELECT
            %s,
            %s,
            %s,
            %s,
            %s,
            'normal',
            COALESCE(policy.first_response_minutes, 240),
            COALESCE(policy.resolution_minutes, 1440),
            %s::timestamptz
                + make_interval(mins => COALESCE(policy.first_response_minutes, 240)),
            %s::timestamptz
                + make_interval(mins => COALESCE(policy.resolution_minutes, 1440)),
            %s::timestamptz,
            %s::timestamptz
        FROM (SELECT 1) seed
        LEFT JOIN selected_policy policy ON true
        RETURNING id
        """,
        (
            student_id,
            int(parent_admin_id),
            student_id,
            str(category or "other").strip(),
            str(topic or "").strip(),
            str(status or "new").strip().casefold(),
            str(created_at or "").strip(),
            str(created_at or "").strip(),
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


def insert_staff_ticket_message_row(
    conn,
    *,
    ticket_id,
    author_type,
    staff_id,
    body,
    created_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.ticket_messages (
            ticket_id,
            author_type,
            author_staff_id,
            body,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            int(ticket_id),
            _author_type(author_type),
            int(staff_id),
            str(body or "").strip(),
            created_at,
        ),
    ).fetchone()


def update_ticket_state_row(
    conn,
    *,
    ticket_id,
    status,
    assigned_staff_id,
    resolved_at,
    updated_at,
):
    return conn.execute(
        """
        UPDATE msi_v2.support_tickets
        SET status = %s,
            assigned_to_staff_id = %s,
            resolved_at = %s,
            updated_at = %s
        WHERE id = %s
        RETURNING id
        """,
        (
            str(status),
            int(assigned_staff_id) if assigned_staff_id else None,
            resolved_at,
            updated_at,
            int(ticket_id),
        ),
    ).fetchone()


def mark_first_staff_response_row(conn, *, ticket_id, responded_at):
    return conn.execute(
        """
        UPDATE msi_v2.support_tickets
        SET first_responded_at = COALESCE(first_responded_at, %s),
            updated_at = %s
        WHERE id = %s
        RETURNING id
        """,
        (responded_at, responded_at, int(ticket_id)),
    ).fetchone()


def set_ticket_waiting_on_requester_row(
    conn,
    *,
    ticket_id,
    is_waiting,
    changed_at,
):
    if is_waiting:
        return conn.execute(
            """
            UPDATE msi_v2.support_tickets
            SET waiting_on_requester_at = COALESCE(waiting_on_requester_at, %s),
                updated_at = %s
            WHERE id = %s
            RETURNING id
            """,
            (changed_at, changed_at, int(ticket_id)),
        ).fetchone()
    return conn.execute(
        """
        UPDATE msi_v2.support_tickets
        SET resolution_due_at = CASE
                WHEN waiting_on_requester_at IS NULL THEN resolution_due_at
                ELSE resolution_due_at + (%s - waiting_on_requester_at)
            END,
            requester_wait_seconds = requester_wait_seconds + CASE
                WHEN waiting_on_requester_at IS NULL THEN 0
                ELSE GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (%s - waiting_on_requester_at))::bigint
                )
            END,
            waiting_on_requester_at = NULL,
            updated_at = %s
        WHERE id = %s
        RETURNING id
        """,
        (changed_at, changed_at, changed_at, int(ticket_id)),
    ).fetchone()


def update_ticket_priority_row(
    conn,
    *,
    ticket_id,
    priority,
    updated_at,
):
    return conn.execute(
        """
        WITH selected_policy AS (
            SELECT
                policy.first_response_minutes,
                policy.resolution_minutes
            FROM msi_v2.support_tickets ticket
            LEFT JOIN msi_v2.students student ON student.id = ticket.student_id
            JOIN msi_v2.support_ticket_sla_policies policy
              ON policy.is_active
             AND policy.priority = %s
             AND (
                    policy.school_id = student.school_id
                    OR policy.school_id IS NULL
             )
            WHERE ticket.id = %s
            ORDER BY policy.school_id NULLS LAST
            LIMIT 1
        )
        UPDATE msi_v2.support_tickets ticket
        SET priority = %s,
            first_response_target_minutes = policy.first_response_minutes,
            resolution_target_minutes = policy.resolution_minutes,
            first_response_due_at = ticket.created_at
                + make_interval(mins => policy.first_response_minutes),
            resolution_due_at = ticket.created_at
                + make_interval(mins => policy.resolution_minutes)
                + make_interval(secs => ticket.requester_wait_seconds::integer),
            updated_at = %s
        FROM selected_policy policy
        WHERE ticket.id = %s
        RETURNING ticket.id
        """,
        (
            str(priority),
            int(ticket_id),
            str(priority),
            updated_at,
            int(ticket_id),
        ),
    ).fetchone()


def insert_ticket_audit_event(
    conn,
    *,
    ticket_id,
    event_type,
    actor_staff_id,
    actor_account_id,
    detail,
    created_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id,
            actor_account_id,
            event_type,
            entity_type,
            entity_id,
            detail_json,
            created_at
        )
        VALUES (%s, %s, %s, 'support_ticket', %s, %s::jsonb, %s)
        RETURNING id
        """,
        (
            int(actor_staff_id) if actor_staff_id else None,
            int(actor_account_id) if actor_account_id else None,
            str(event_type),
            int(ticket_id),
            json.dumps(detail, separators=(",", ":")),
            created_at,
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
    "get_parent_ticket_row",
    "get_ticket_row",
    "insert_complaint_message_row",
    "insert_parent_complaint_row",
    "insert_staff_ticket_message_row",
    "insert_ticket_audit_event",
    "list_complaint_message_rows",
    "list_parent_complaint_rows",
    "list_support_ticket_rows",
    "mark_first_staff_response_row",
    "set_ticket_waiting_on_requester_row",
    "update_parent_complaint_row",
    "update_ticket_priority_row",
    "update_ticket_state_row",
]
