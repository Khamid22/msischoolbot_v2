"""Student/account SQL query helpers."""

_DEFAULT_SCHOOL_KEY = "school5"


def _normalize_school_key(school_key):
    normalized = str(school_key or "").strip().casefold()
    if normalized in {"school_5", "school-5", "school 5", "school5"}:
        return "school5"
    if normalized in {"sehriyo", "sehriyo school"}:
        return "sehriyo"
    return normalized or _DEFAULT_SCHOOL_KEY


def get_student_login_row(conn, student_login):
    return conn.execute(
        """
        SELECT
            s.id,
            s.full_name,
            s.student_id,
            s.password,
            s.subjects,
            s.school_key,
            s.telegram_user_id,
            a.password_hash,
            m.sheet_student_id
        FROM students s
        JOIN student_auth a ON a.student_row_id = s.id
        LEFT JOIN students_sheet_map m ON m.student_row_id = s.id
        WHERE upper(s.student_id) = upper(?)
        """,
        (student_login,),
    ).fetchone()


def get_next_student_code(conn, prefix="MSI"):
    normalized_prefix = str(prefix or "MSI").strip().upper()
    if not normalized_prefix:
        normalized_prefix = "MSI"

    rows = conn.execute(
        """
        SELECT student_id
        FROM students
        WHERE upper(student_id) LIKE ?
        """,
        (f"{normalized_prefix}%",),
    ).fetchall()

    max_num = 0
    prefix_length = len(normalized_prefix)
    for row in rows:
        raw_student_id = str(row["student_id"] or "").strip().upper()
        if not raw_student_id.startswith(normalized_prefix):
            continue
        numeric_part = raw_student_id[prefix_length:]
        if not numeric_part.isdigit():
            continue
        max_num = max(max_num, int(numeric_part))

    next_num = max_num + 1
    return f"{normalized_prefix}{next_num:05d}"


def get_students_sheet_map_row(conn, sheet_student_id, school_key=_DEFAULT_SCHOOL_KEY):
    return conn.execute(
        """
        SELECT student_row_id
        FROM students_sheet_map
        WHERE school_key = ?
          AND sheet_student_id = ?
        """,
        (_normalize_school_key(school_key), sheet_student_id),
    ).fetchone()


def update_student_profile(
    conn,
    full_name,
    subject_label,
    school_name,
    student_row_id,
    school_key=_DEFAULT_SCHOOL_KEY,
):
    conn.execute(
        """
        UPDATE students
        SET
            full_name = ?,
            subjects = ?,
            school_name = ?,
            school_key = ?
        WHERE id = ?
        """,
        (
            full_name,
            subject_label,
            school_name,
            _normalize_school_key(school_key),
            student_row_id,
        ),
    )


def insert_student(
    conn,
    full_name,
    student_code,
    default_password,
    subject_label,
    school_name,
    school_key=_DEFAULT_SCHOOL_KEY,
):
    inserted = conn.execute(
        """
        INSERT INTO students (
            full_name,
            student_id,
            password,
            subjects,
            school_name,
            school_key
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            full_name,
            student_code,
            default_password,
            subject_label,
            school_name,
            _normalize_school_key(school_key),
        ),
    )
    return int(inserted.lastrowid)


def insert_student_auth(conn, student_row_id, password_hash, updated_at):
    conn.execute(
        """
        INSERT INTO student_auth (student_row_id, password_hash, updated_at)
        VALUES (?, ?, ?)
        """,
        (student_row_id, password_hash, updated_at),
    )


def insert_students_sheet_map(
    conn,
    sheet_student_id,
    student_row_id,
    school_key=_DEFAULT_SCHOOL_KEY,
):
    conn.execute(
        """
        INSERT INTO students_sheet_map (school_key, sheet_student_id, student_row_id)
        VALUES (?, ?, ?)
        """,
        (_normalize_school_key(school_key), sheet_student_id, student_row_id),
    )


def list_students_sheet_map_rows_by_school(conn, school_key=_DEFAULT_SCHOOL_KEY):
    return conn.execute(
        """
        SELECT
            sheet_student_id,
            student_row_id
        FROM students_sheet_map
        WHERE school_key = ?
        """,
        (_normalize_school_key(school_key),),
    ).fetchall()


def delete_students_by_ids(conn, student_row_ids):
    normalized_ids = []
    for student_row_id in student_row_ids:
        try:
            parsed = int(student_row_id)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            normalized_ids.append(parsed)

    if not normalized_ids:
        return 0

    placeholders = ",".join(["?"] * len(normalized_ids))
    deleted = conn.execute(
        f"""
        DELETE FROM students
        WHERE id IN ({placeholders})
        """,
        tuple(normalized_ids),
    )
    return int(deleted.rowcount or 0)


def update_student_last_seen(conn, student_row_id, now):
    conn.execute(
        """
        UPDATE students
        SET last_seen_at = ?
        WHERE id = ?
        """,
        (now, student_row_id),
    )


def list_students_for_admin_rows(conn, school_key="", school_name=""):
    normalized_school_key = str(school_key or "").strip().casefold()
    if normalized_school_key:
        return conn.execute(
            """
            SELECT
                id,
                full_name,
                student_id,
                password,
                subjects,
                telegram_user_id,
                photo_url,
                profile_description,
                class_name,
                school_name,
                last_seen_at
            FROM students
            WHERE school_key = ?
            ORDER BY id ASC
            """,
            (_normalize_school_key(normalized_school_key),),
        ).fetchall()

    normalized_school_name = str(school_name or "").strip()
    if normalized_school_name:
        return conn.execute(
            """
            SELECT
                id,
                full_name,
                student_id,
                password,
                subjects,
                telegram_user_id,
                photo_url,
                profile_description,
                class_name,
                school_name,
                last_seen_at
            FROM students
            WHERE lower(school_name) = lower(?)
            ORDER BY id ASC
            """,
            (normalized_school_name,),
        ).fetchall()

    return conn.execute(
        """
        SELECT
            id,
            full_name,
            student_id,
            password,
            subjects,
            telegram_user_id,
            photo_url,
            profile_description,
            class_name,
            school_name,
            last_seen_at
        FROM students
        ORDER BY id ASC
        """
    ).fetchall()


def get_student_admin_row(conn, student_row_id):
    return conn.execute(
        """
        SELECT
            id,
            full_name,
            student_id,
            password,
            subjects,
            photo_url,
            profile_description,
            class_name,
            school_name,
            teacher_name
        FROM students
        WHERE id = ?
        """,
        (student_row_id,),
    ).fetchone()


def get_student_auth_row_by_id(conn, student_row_id):
    return conn.execute(
        """
        SELECT
            s.id,
            s.student_id,
            a.password_hash
        FROM students s
        JOIN student_auth a ON a.student_row_id = s.id
        WHERE s.id = ?
        """,
        (student_row_id,),
    ).fetchone()


def update_student_password(conn, student_row_id, plain_password, password_hash, updated_at):
    conn.execute(
        """
        UPDATE students
        SET password = ?
        WHERE id = ?
        """,
        (plain_password, student_row_id),
    )
    conn.execute(
        """
        UPDATE student_auth
        SET
            password_hash = ?,
            updated_at = ?
        WHERE student_row_id = ?
        """,
        (password_hash, updated_at, student_row_id),
    )


def update_student_admin_profile(
    conn,
    student_row_id,
    photo_url,
    profile_description,
    class_name,
    school_name,
    teacher_name,
):
    conn.execute(
        """
        UPDATE students
        SET
            photo_url = ?,
            profile_description = ?,
            class_name = ?,
            school_name = ?,
            teacher_name = ?
        WHERE id = ?
        """,
        (
            photo_url,
            profile_description,
            class_name,
            school_name,
            teacher_name,
            student_row_id,
        ),
    )


def get_student_conflict_by_telegram_id(conn, telegram_user_id, student_row_id):
    return conn.execute(
        """
        SELECT id
        FROM students
        WHERE telegram_user_id = ?
          AND id != ?
        """,
        (telegram_user_id, student_row_id),
    ).fetchone()


def clear_student_telegram_user_conflicts(conn, telegram_user_id, student_row_id):
    conn.execute(
        """
        UPDATE students
        SET telegram_user_id = NULL
        WHERE telegram_user_id = ?
          AND id != ?
        """,
        (telegram_user_id, student_row_id),
    )


def update_student_telegram_user(conn, telegram_user_id, student_row_id):
    conn.execute(
        """
        UPDATE students
        SET telegram_user_id = ?
        WHERE id = ?
        """,
        (telegram_user_id, student_row_id),
    )


def get_student_by_telegram_id(conn, telegram_user_id):
    return conn.execute(
        """
        SELECT
            s.id,
            s.full_name,
            s.student_id,
            s.subjects,
            s.school_key,
            m.sheet_student_id
        FROM students s
        LEFT JOIN students_sheet_map m ON m.student_row_id = s.id
        WHERE s.telegram_user_id = ?
        """,
        (telegram_user_id,),
    ).fetchone()


__all__ = [
    "get_student_login_row",
    "get_next_student_code",
    "get_students_sheet_map_row",
    "update_student_profile",
    "insert_student",
    "insert_student_auth",
    "insert_students_sheet_map",
    "list_students_sheet_map_rows_by_school",
    "delete_students_by_ids",
    "update_student_last_seen",
    "list_students_for_admin_rows",
    "get_student_admin_row",
    "get_student_auth_row_by_id",
    "update_student_password",
    "update_student_admin_profile",
    "get_student_conflict_by_telegram_id",
    "clear_student_telegram_user_conflicts",
    "update_student_telegram_user",
    "get_student_by_telegram_id",
]
