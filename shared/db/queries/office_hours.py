def _slot_status_for_db(status):
    value = str(status or "").strip().lower()
    if value == "active":
        return "open"
    return value or None


def create_availability_row(
    conn,
    teacher_id,
    subject_id,
    starts_at,
    ends_at,
    slot_minutes,
    room,
    capacity,
    status="active",
    planned_topic="",
):
    result = conn.execute(
        """
        INSERT INTO msi_v2.office_hour_slots (
            teacher_id, subject_id, planned_topic, starts_at, ends_at,
            slot_minutes, room, capacity, status
        ) VALUES (
            %s, %s, %s, %s::timestamptz, %s::timestamptz,
            %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            teacher_id,
            subject_id,
            planned_topic,
            starts_at,
            ends_at,
            slot_minutes,
            room,
            capacity,
            _slot_status_for_db(status) or "open",
        ),
    )
    row = result.fetchone()
    return row["id"] if row else None


def _availability_select_sql(*, for_update=False):
    lock = " FOR UPDATE" if for_update else ""
    return f"""
        SELECT
            s.id,
            s.teacher_id,
            s.subject_id,
            s.planned_topic,
            to_char(s.starts_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS starts_at,
            to_char(s.ends_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS ends_at,
            s.slot_minutes,
            s.room,
            s.capacity,
            CASE WHEN s.status = 'open' THEN 'active' ELSE s.status END AS status,
            to_char(s.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at
        FROM msi_v2.office_hour_slots s
        WHERE s.id = %s
        {lock}
    """


def get_availability_row(conn, availability_id):
    return conn.execute(
        _availability_select_sql(for_update=True),
        (availability_id,),
    ).fetchone()


def update_availability_status_row(conn, availability_id, status):
    conn.execute(
        """
        UPDATE msi_v2.office_hour_slots
        SET status = %s
        WHERE id = %s
        """,
        (_slot_status_for_db(status) or status, availability_id),
    )
    return True


def list_availabilities_rows(conn, teacher_id=None, subject_id=None, status=None, starts_at_from=None):
    sql = """
        SELECT
            s.id,
            s.teacher_id,
            t.full_name AS teacher_name,
            s.subject_id,
            subj.subject_name,
            s.planned_topic,
            to_char(s.starts_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS starts_at,
            to_char(s.ends_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS ends_at,
            s.slot_minutes,
            s.room,
            s.capacity,
            CASE WHEN s.status = 'open' THEN 'active' ELSE s.status END AS status,
            to_char(s.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
            (
                SELECT COUNT(*)
                FROM msi_v2.office_hour_bookings b
                WHERE b.slot_id = s.id
                  AND b.status = 'booked'
            ) AS booked_count
        FROM msi_v2.office_hour_slots s
        JOIN msi_v2.teachers t ON t.id = s.teacher_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = s.subject_id
        WHERE 1 = 1
    """
    params = []
    if teacher_id is not None:
        sql += " AND s.teacher_id = %s"
        params.append(teacher_id)
    if subject_id is not None:
        sql += " AND s.subject_id = %s"
        params.append(subject_id)
    if status is not None:
        sql += " AND s.status = %s"
        params.append(_slot_status_for_db(status) or status)
    if starts_at_from is not None:
        sql += " AND s.starts_at >= %s::timestamptz"
        params.append(starts_at_from)
    sql += " ORDER BY s.starts_at ASC"
    return conn.execute(sql, params).fetchall()


def create_booking_row(
    conn,
    availability_id,
    teacher_id,
    student_row_id,
    subject_id,
    starts_at,
    ends_at,
    status="booked",
    student_note="",
    teacher_note="",
    student_topic_request="",
):
    result = conn.execute(
        """
        INSERT INTO msi_v2.office_hour_bookings (
            slot_id, student_id, subject_id, status,
            student_topic_request, student_note, teacher_note
        )
        SELECT
            %s,
            st.id,
            %s,
            %s,
            %s,
            %s,
            %s
        FROM msi_v2.students st
        WHERE st.legacy_student_row_id = %s
        LIMIT 1
        RETURNING id
        """,
        (
            availability_id,
            subject_id,
            status,
            student_topic_request,
            student_note,
            teacher_note,
            student_row_id,
        ),
    )
    row = result.fetchone()
    return row["id"] if row else None


def _booking_select_sql():
    return """
        SELECT
            b.id,
            b.slot_id AS availability_id,
            slot.teacher_id,
            t.full_name AS teacher_name,
            st.legacy_student_row_id AS student_row_id,
            st.full_name AS student_name,
            COALESCE(b.subject_id, slot.subject_id) AS subject_id,
            subj.subject_name,
            to_char(slot.starts_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS starts_at,
            to_char(slot.ends_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS ends_at,
            b.status,
            b.student_topic_request,
            b.student_note,
            b.teacher_note,
            to_char(b.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
            to_char(b.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS updated_at,
            slot.room,
            slot.planned_topic
        FROM msi_v2.office_hour_bookings b
        JOIN msi_v2.office_hour_slots slot ON slot.id = b.slot_id
        JOIN msi_v2.teachers t ON t.id = slot.teacher_id
        JOIN msi_v2.students st ON st.id = b.student_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = COALESCE(b.subject_id, slot.subject_id)
    """


def get_booking_row(conn, booking_id):
    return conn.execute(
        _booking_select_sql() + " WHERE b.id = %s",
        (booking_id,),
    ).fetchone()


def update_booking_status_row(conn, booking_id, status, teacher_note=None):
    if teacher_note is not None:
        conn.execute(
            """
            UPDATE msi_v2.office_hour_bookings
            SET status = %s,
                teacher_note = %s,
                updated_at = now(),
                canceled_at = CASE WHEN %s = 'cancelled' THEN now() ELSE canceled_at END
            WHERE id = %s
            """,
            (status, teacher_note, status, booking_id),
        )
    else:
        conn.execute(
            """
            UPDATE msi_v2.office_hour_bookings
            SET status = %s,
                updated_at = now(),
                canceled_at = CASE WHEN %s = 'cancelled' THEN now() ELSE canceled_at END
            WHERE id = %s
            """,
            (status, status, booking_id),
        )
    return True


def list_bookings_rows(conn, availability_id=None, teacher_id=None, student_row_id=None, subject_id=None, status=None, starts_at_from=None):
    sql = _booking_select_sql() + " WHERE 1 = 1"
    params = []
    if availability_id is not None:
        sql += " AND b.slot_id = %s"
        params.append(availability_id)
    if teacher_id is not None:
        sql += " AND slot.teacher_id = %s"
        params.append(teacher_id)
    if student_row_id is not None:
        sql += " AND st.legacy_student_row_id = %s"
        params.append(student_row_id)
    if subject_id is not None:
        sql += " AND COALESCE(b.subject_id, slot.subject_id) = %s"
        params.append(subject_id)
    if status is not None:
        sql += " AND b.status = %s"
        params.append(status)
    if starts_at_from is not None:
        sql += " AND slot.starts_at >= %s::timestamptz"
        params.append(starts_at_from)
    sql += " ORDER BY slot.starts_at ASC, b.created_at ASC"
    return conn.execute(sql, params).fetchall()
