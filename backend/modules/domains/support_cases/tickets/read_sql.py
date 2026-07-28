"""Shared ticket read projection used by parent, student, and staff queries."""


def ticket_row_select() -> str:
    return """
        SELECT
            t.id,
            t.parent_id AS parent_admin_id,
            t.requester_account_id,
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
            to_char(
                t.created_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS"Z"'
            ) AS created_at,
            to_char(
                t.updated_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS"Z"'
            ) AS updated_at,
            to_char(
                t.updated_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
            ) AS cursor_updated_at,
            COALESCE(
                to_char(
                    t.resolved_at AT TIME ZONE 'UTC',
                    'YYYY-MM-DD"T"HH24:MI:SS"Z"'
                ),
                ''
            ) AS resolved_at,
            t.assigned_to_staff_id,
            COALESCE(assigned.login, assigned.display_name, '') AS assigned_to,
            COALESCE(p.display_name, requester_student.full_name, '') AS parent_login,
            COALESCE(
                p.display_name,
                requester_student.full_name,
                ''
            ) AS parent_display_name,
            COALESCE(p.phone, '') AS parent_phone,
            '' AS parent_email,
            COALESCE(p.telegram_username, '') AS parent_telegram_username,
            COALESCE(st.full_name, '') AS student_name,
            COALESCE(st.student_code, '') AS student_code,
            COALESCE(sch.school_name, '') AS school_name
        FROM msi_v2.support_tickets t
        LEFT JOIN msi_v2.parents p ON p.id = t.parent_id
        LEFT JOIN msi_v2.student_profiles requester_profile
          ON requester_profile.account_id = t.requester_account_id
        LEFT JOIN msi_v2.students requester_student
          ON requester_student.id = requester_profile.student_id
        LEFT JOIN msi_v2.students st ON st.id = t.student_id
        LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
        LEFT JOIN msi_v2.msi_staff assigned ON assigned.id = t.assigned_to_staff_id
        LEFT JOIN LATERAL (
            SELECT body
            FROM msi_v2.ticket_messages msg
            WHERE msg.ticket_id = t.id
              AND msg.author_type IN ('parent', 'student')
            ORDER BY msg.created_at ASC, msg.id ASC
            LIMIT 1
        ) opening ON true
        LEFT JOIN LATERAL (
            SELECT body
            FROM msi_v2.ticket_messages msg
            WHERE msg.ticket_id = t.id
              AND msg.author_type NOT IN ('parent', 'student')
            ORDER BY msg.created_at DESC, msg.id DESC
            LIMIT 1
        ) latest_staff ON true
    """


__all__ = ["ticket_row_select"]
