def create_availability_row(conn, teacher_id, subject_id, starts_at, ends_at, slot_minutes, room, capacity, status='active', planned_topic=''):
    result = conn.execute(
        """
        INSERT INTO office_hour_availability (
            teacher_id, subject_id, planned_topic, starts_at, ends_at, slot_minutes, room, capacity, status, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP::text
        ) RETURNING id
        """,
        (teacher_id, subject_id, planned_topic, starts_at, ends_at, slot_minutes, room, capacity, status)
    )
    row = result.fetchone()
    return row["id"] if row else None


def get_availability_row(conn, availability_id):
    return conn.execute(
        """
        SELECT id, teacher_id, subject_id, planned_topic, starts_at, ends_at, slot_minutes, room, capacity, status, created_at
        FROM office_hour_availability
        WHERE id = %s
        FOR UPDATE
        """,
        (availability_id,)
    ).fetchone()


def update_availability_status_row(conn, availability_id, status):
    conn.execute(
        """
        UPDATE office_hour_availability
        SET status = %s
        WHERE id = %s
        """,
        (status, availability_id)
    )
    return True


def list_availabilities_rows(conn, teacher_id=None, subject_id=None, status=None, starts_at_from=None):
    sql = """
        SELECT a.id, a.teacher_id, t.full_name AS teacher_name,
               a.subject_id, s.name AS subject_name,
               a.planned_topic, a.starts_at, a.ends_at, a.slot_minutes, a.room, a.capacity, a.status, a.created_at,
               (SELECT COUNT(*) FROM office_hour_bookings b WHERE b.availability_id = a.id AND b.status = 'booked') AS booked_count
        FROM office_hour_availability a
        JOIN teachers t ON t.id = a.teacher_id
        LEFT JOIN academic_subjects s ON s.id = a.subject_id
        WHERE 1 = 1
    """
    params = []
    if teacher_id is not None:
        sql += " AND a.teacher_id = %s"
        params.append(teacher_id)
    if subject_id is not None:
        sql += " AND a.subject_id = %s"
        params.append(subject_id)
    if status is not None:
        sql += " AND a.status = %s"
        params.append(status)
    if starts_at_from is not None:
        sql += " AND a.starts_at >= %s"
        params.append(starts_at_from)
    sql += " ORDER BY a.starts_at ASC"
    return conn.execute(sql, params).fetchall()


def create_booking_row(conn, availability_id, teacher_id, student_row_id, subject_id, starts_at, ends_at, status='booked', student_note='', teacher_note='', student_topic_request=''):
    result = conn.execute(
        """
        INSERT INTO office_hour_bookings (
            availability_id, teacher_id, student_row_id, subject_id, starts_at, ends_at, status, student_topic_request, student_note, teacher_note, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP::text, CURRENT_TIMESTAMP::text
        ) RETURNING id
        """,
        (availability_id, teacher_id, student_row_id, subject_id, starts_at, ends_at, status, student_topic_request, student_note, teacher_note)
    )
    row = result.fetchone()
    return row["id"] if row else None


def get_booking_row(conn, booking_id):
    return conn.execute(
        """
        SELECT b.id, b.availability_id, b.teacher_id, t.full_name AS teacher_name,
               b.student_row_id, st.full_name AS student_name, b.subject_id, s.name AS subject_name,
               b.starts_at, b.ends_at, b.status, b.student_topic_request, b.student_note, b.teacher_note, b.created_at, b.updated_at,
               a.room, a.planned_topic
        FROM office_hour_bookings b
        JOIN office_hour_availability a ON a.id = b.availability_id
        JOIN teachers t ON t.id = b.teacher_id
        JOIN students st ON st.id = b.student_row_id
        LEFT JOIN academic_subjects s ON s.id = b.subject_id
        WHERE b.id = %s
        """,
        (booking_id,)
    ).fetchone()


def update_booking_status_row(conn, booking_id, status, teacher_note=None):
    if teacher_note is not None:
        conn.execute(
            """
            UPDATE office_hour_bookings
            SET status = %s, teacher_note = %s, updated_at = CURRENT_TIMESTAMP::text
            WHERE id = %s
            """,
            (status, teacher_note, booking_id)
        )
    else:
        conn.execute(
            """
            UPDATE office_hour_bookings
            SET status = %s, updated_at = CURRENT_TIMESTAMP::text
            WHERE id = %s
            """,
            (status, booking_id)
        )
    return True


def list_bookings_rows(conn, availability_id=None, teacher_id=None, student_row_id=None, subject_id=None, status=None, starts_at_from=None):
    sql = """
        SELECT b.id, b.availability_id, b.teacher_id, t.full_name AS teacher_name,
               b.student_row_id, st.full_name AS student_name, b.subject_id, s.name AS subject_name,
               b.starts_at, b.ends_at, b.status, b.student_topic_request, b.student_note, b.teacher_note, b.created_at, b.updated_at,
               a.room, a.planned_topic
        FROM office_hour_bookings b
        JOIN office_hour_availability a ON a.id = b.availability_id
        JOIN teachers t ON t.id = b.teacher_id
        JOIN students st ON st.id = b.student_row_id
        LEFT JOIN academic_subjects s ON s.id = b.subject_id
        WHERE 1 = 1
    """
    params = []
    if availability_id is not None:
        sql += " AND b.availability_id = %s"
        params.append(availability_id)
    if teacher_id is not None:
        sql += " AND b.teacher_id = %s"
        params.append(teacher_id)
    if student_row_id is not None:
        sql += " AND b.student_row_id = %s"
        params.append(student_row_id)
    if subject_id is not None:
        sql += " AND b.subject_id = %s"
        params.append(subject_id)
    if status is not None:
        sql += " AND b.status = %s"
        params.append(status)
    if starts_at_from is not None:
        sql += " AND b.starts_at >= %s"
        params.append(starts_at_from)
    sql += " ORDER BY b.starts_at ASC"
    return conn.execute(sql, params).fetchall()
