"""Persistence for account-owned student support tickets."""

from backend.modules.domains.support_cases.tickets.read_sql import ticket_row_select


def list_account_ticket_rows(conn, *, requester_account_id):
    return conn.execute(
        f"""
        {ticket_row_select()}
        WHERE t.requester_account_id = %s
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
        (int(requester_account_id),),
    ).fetchall()


def get_account_ticket_row(
    conn,
    *,
    requester_account_id,
    ticket_id,
    for_update=False,
):
    lock_clause = " FOR UPDATE OF t" if for_update else ""
    return conn.execute(
        f"""
        {ticket_row_select()}
        WHERE t.id = %s
          AND t.requester_account_id = %s
        {lock_clause}
        """,
        (int(ticket_id), int(requester_account_id)),
    ).fetchone()


def insert_account_ticket_row(
    conn,
    *,
    requester_account_id,
    student_id,
    category,
    topic,
    message,
    created_at,
):
    inserted = conn.execute(
        """
        WITH selected_policy AS (
            SELECT policy.first_response_minutes, policy.resolution_minutes
            FROM msi_v2.students student
            JOIN msi_v2.support_ticket_sla_policies policy
              ON policy.is_active
             AND policy.priority = 'normal'
             AND (policy.school_id = student.school_id OR policy.school_id IS NULL)
            WHERE student.id = %s
            ORDER BY policy.school_id NULLS LAST
            LIMIT 1
        )
        INSERT INTO msi_v2.support_tickets (
            requester_account_id, student_id, category, topic, status, priority,
            first_response_target_minutes, resolution_target_minutes,
            first_response_due_at, resolution_due_at, created_at, updated_at
        )
        SELECT
            %s, %s, %s, %s, 'new', 'normal',
            COALESCE(policy.first_response_minutes, 240),
            COALESCE(policy.resolution_minutes, 1440),
            %s + make_interval(
                mins => COALESCE(policy.first_response_minutes, 240)
            ),
            %s + make_interval(
                mins => COALESCE(policy.resolution_minutes, 1440)
            ),
            %s,
            %s
        FROM (SELECT 1) seed
        LEFT JOIN selected_policy policy ON true
        RETURNING id
        """,
        (
            int(student_id),
            int(requester_account_id),
            int(student_id),
            str(category),
            str(topic),
            created_at,
            created_at,
            created_at,
            created_at,
        ),
    ).fetchone()
    if not inserted:
        return None
    insert_account_ticket_message_row(
        conn,
        ticket_id=int(inserted["id"]),
        author_account_id=int(requester_account_id),
        author_type="student",
        body=message,
        created_at=created_at,
    )
    return inserted


def insert_account_ticket_message_row(
    conn,
    *,
    ticket_id,
    author_account_id,
    author_type,
    body,
    created_at,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.ticket_messages (
            ticket_id, author_type, author_account_id, body, created_at
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            int(ticket_id),
            str(author_type),
            int(author_account_id),
            str(body).strip(),
            created_at,
        ),
    ).fetchone()


__all__ = [
    "get_account_ticket_row",
    "insert_account_ticket_message_row",
    "insert_account_ticket_row",
    "list_account_ticket_rows",
]
