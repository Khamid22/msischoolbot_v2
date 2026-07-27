"""Chat persistence for the communication module."""

from backend.core.database import connect_auth_db


def connect():
    return connect_auth_db()


def student_has_subject_room(conn, student_id: int, subject_name: str):
    return conn.execute(
        """
        SELECT 1
        FROM msi_v2.students st
        JOIN msi_v2.group_students gs ON gs.student_id = st.id AND gs.enrollment_status = 'active'
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        WHERE st.id = %s AND lower(btrim(sub.subject_name)) = lower(btrim(%s))
        LIMIT 1
        """,
        (student_id, subject_name),
    ).fetchone()


def student_has_group_room(conn, student_id: int, group_name: str):
    return conn.execute(
        """
        SELECT 1
        FROM msi_v2.students st
        JOIN msi_v2.group_students gs ON gs.student_id = st.id AND gs.enrollment_status = 'active'
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE st.id = %s AND lower(btrim(g.group_name)) = lower(btrim(%s))
        LIMIT 1
        """,
        (student_id, group_name),
    ).fetchone()


def is_blocked(conn, student_login: str):
    return conn.execute(
        "SELECT 1 FROM msi_v2.chat_blocked_users WHERE student_id = %s",
        (student_login.strip().lower(),),
    ).fetchone()


def list_message_rows(conn, room: str, *, before_id=0, after_id=0, limit=40, include_deleted=False):
    deleted_filter = "" if include_deleted else "AND is_deleted IS FALSE"
    if after_id > 0:
        comparator, cursor, direction = ">", after_id, "ASC"
    elif before_id > 0:
        comparator, cursor, direction = "<", before_id, "DESC"
    else:
        comparator, cursor, direction = "", 0, "DESC"
    cursor_filter = f"AND id {comparator} %s" if comparator else ""
    params = (room, cursor, limit) if comparator else (room, limit)
    return conn.execute(
        f"""
        SELECT id, room, author_name, author_student_id, body, is_deleted, edited_at, created_at
        FROM msi_v2.chat_messages
        WHERE room = %s {deleted_filter} {cursor_filter}
        ORDER BY id {direction}
        LIMIT %s
        """,
        params,
    ).fetchall()


def insert_message(conn, *, room, author_name, student_login, body, created_at):
    return conn.execute(
        """
        INSERT INTO msi_v2.chat_messages (room, author_name, author_student_id, body, created_at)
        VALUES (%s, %s, %s, %s, %s::timestamptz)
        RETURNING id
        """,
        (room, author_name, student_login, body, created_at),
    ).fetchone()


def get_message_author(conn, message_id: int):
    return conn.execute(
        "SELECT author_student_id FROM msi_v2.chat_messages WHERE id = %s AND is_deleted IS FALSE",
        (message_id,),
    ).fetchone()


def update_message(conn, message_id: int, body: str, edited_at: str):
    conn.execute(
        "UPDATE msi_v2.chat_messages SET body = %s, edited_at = %s::timestamptz WHERE id = %s",
        (body, edited_at, message_id),
    )


def soft_delete_message(conn, message_id: int):
    conn.execute("UPDATE msi_v2.chat_messages SET is_deleted = TRUE WHERE id = %s", (message_id,))
