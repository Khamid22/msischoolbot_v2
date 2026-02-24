def create_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            is_owner INTEGER NOT NULL DEFAULT 0 CHECK (is_owner IN (0, 1)),
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            student_id TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password TEXT NOT NULL,
            subjects TEXT NOT NULL,
            telegram_user_id INTEGER,
            photo_url TEXT NOT NULL DEFAULT '',
            profile_description TEXT NOT NULL DEFAULT '',
            class_name TEXT NOT NULL DEFAULT '',
            school_name TEXT NOT NULL DEFAULT '',
            teacher_name TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students_sheet_map (
            sheet_student_id INTEGER PRIMARY KEY,
            student_row_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS student_auth (
            student_row_id INTEGER PRIMARY KEY,
            password_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            pay_rate REAL NOT NULL DEFAULT 0,
            assigned_group TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_summaries (
            sheet_student_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            full_name_norm TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            subject_short TEXT NOT NULL,
            aap INTEGER NOT NULL,
            ar INTEGER NOT NULL,
            ep INTEGER NOT NULL,
            total_coins INTEGER NOT NULL,
            rating_rank INTEGER NOT NULL,
            rating_total INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subject_summaries_name_norm
        ON subject_summaries(full_name_norm)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subject_summaries_subject_name
        ON subject_summaries(subject_name)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lesson_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            group_name TEXT NOT NULL DEFAULT '',
            lesson_number TEXT NOT NULL,
            lesson_topic TEXT NOT NULL,
            lesson_date TEXT NOT NULL DEFAULT '',
            lesson_order INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(subject_name, group_name, lesson_number)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_lesson_catalog_subject_order
        ON lesson_catalog(subject_name, group_name, lesson_order)
        """
    )


def ensure_students_schema(conn):
    # Backward-compatible migration for old DBs.
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(students)").fetchall()
    }
    if "telegram_user_id" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN telegram_user_id INTEGER")
    if "photo_url" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN photo_url TEXT NOT NULL DEFAULT ''")
    if "profile_description" not in columns:
        conn.execute(
            "ALTER TABLE students ADD COLUMN profile_description TEXT NOT NULL DEFAULT ''"
        )
    if "class_name" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN class_name TEXT NOT NULL DEFAULT ''")
    if "school_name" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN school_name TEXT NOT NULL DEFAULT ''")
    if "teacher_name" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN teacher_name TEXT NOT NULL DEFAULT ''")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
        ON students(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )


def ensure_lesson_catalog_schema(conn):
    # Backward-compatible migration for lesson catalog fields.
    column_rows = conn.execute("PRAGMA table_info(lesson_catalog)").fetchall()
    columns = {str(row["name"]) for row in column_rows}
    if not columns:
        return

    # Rebuild old table structure that had UNIQUE(subject_name, lesson_number)
    # and no group_name column. Keep existing rows with empty group fallback.
    needs_rebuild = "group_name" not in columns
    if needs_rebuild:
        has_lesson_date = "lesson_date" in columns
        conn.execute("ALTER TABLE lesson_catalog RENAME TO lesson_catalog_legacy")
        conn.execute(
            """
            CREATE TABLE lesson_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_name TEXT NOT NULL,
                group_name TEXT NOT NULL DEFAULT '',
                lesson_number TEXT NOT NULL,
                lesson_topic TEXT NOT NULL,
                lesson_date TEXT NOT NULL DEFAULT '',
                lesson_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(subject_name, group_name, lesson_number)
            )
            """
        )
        if has_lesson_date:
            conn.execute(
                """
                INSERT INTO lesson_catalog (
                    subject_name,
                    group_name,
                    lesson_number,
                    lesson_topic,
                    lesson_date,
                    lesson_order,
                    updated_at
                )
                SELECT
                    subject_name,
                    '',
                    lesson_number,
                    lesson_topic,
                    COALESCE(lesson_date, ''),
                    lesson_order,
                    updated_at
                FROM lesson_catalog_legacy
                """
            )
        else:
            conn.execute(
                """
                INSERT INTO lesson_catalog (
                    subject_name,
                    group_name,
                    lesson_number,
                    lesson_topic,
                    lesson_date,
                    lesson_order,
                    updated_at
                )
                SELECT
                    subject_name,
                    '',
                    lesson_number,
                    lesson_topic,
                    '',
                    lesson_order,
                    updated_at
                FROM lesson_catalog_legacy
                """
            )
        conn.execute("DROP TABLE lesson_catalog_legacy")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lesson_catalog_subject_order
            ON lesson_catalog(subject_name, group_name, lesson_order)
            """
        )
        return

    if "lesson_date" not in columns:
        conn.execute(
            "ALTER TABLE lesson_catalog ADD COLUMN lesson_date TEXT NOT NULL DEFAULT ''"
        )


def get_admin_id_by_login(conn, login):
    return conn.execute(
        "SELECT id FROM admins WHERE lower(login) = lower(?)",
        (login,),
    ).fetchone()


def insert_owner_admin(conn, login, password_hash, created_at):
    conn.execute(
        """
        INSERT INTO admins (login, password_hash, role, is_owner, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (login, password_hash, "owner", created_at),
    )


def get_admin_credentials_row(conn, login):
    return conn.execute(
        """
        SELECT id, login, password_hash, role, is_owner
        FROM admins
        WHERE lower(login) = lower(?)
        """,
        (login,),
    ).fetchone()


def get_student_login_row(conn, student_login):
    return conn.execute(
        """
        SELECT
            s.id,
            s.full_name,
            s.student_id,
            s.password,
            s.subjects,
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


def get_next_student_code(conn):
    row = conn.execute(
        """
        SELECT MAX(CAST(SUBSTR(student_id, 4) AS INTEGER)) AS max_num
        FROM students
        WHERE upper(student_id) LIKE 'MSI%'
        """
    ).fetchone()
    next_num = int(row["max_num"] or 0) + 1
    return f"MSI{next_num:05d}"


def upsert_meta(conn, key, value):
    conn.execute(
        """
        INSERT INTO app_meta (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_meta(conn, key):
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if not row:
        return ""
    return str(row["value"])


def get_students_sheet_map_row(conn, sheet_student_id):
    return conn.execute(
        """
        SELECT student_row_id
        FROM students_sheet_map
        WHERE sheet_student_id = ?
        """,
        (sheet_student_id,),
    ).fetchone()


def update_student_profile(conn, full_name, subject_label, student_row_id):
    conn.execute(
        """
        UPDATE students
        SET full_name = ?, subjects = ?
        WHERE id = ?
        """,
        (full_name, subject_label, student_row_id),
    )


def insert_student(conn, full_name, student_code, default_password, subject_label):
    inserted = conn.execute(
        """
        INSERT INTO students (full_name, student_id, password, subjects)
        VALUES (?, ?, ?, ?)
        """,
        (full_name, student_code, default_password, subject_label),
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


def insert_students_sheet_map(conn, sheet_student_id, student_row_id):
    conn.execute(
        """
        INSERT INTO students_sheet_map (sheet_student_id, student_row_id)
        VALUES (?, ?)
        """,
        (sheet_student_id, student_row_id),
    )


def list_students_for_admin_rows(conn):
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
            school_name
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


def list_teachers_rows(conn):
    return conn.execute(
        """
        SELECT
            id,
            full_name,
            pay_rate,
            assigned_group,
            created_at,
            updated_at
        FROM teachers
        ORDER BY full_name COLLATE NOCASE ASC, id ASC
        """
    ).fetchall()


def get_teacher_by_id_row(conn, teacher_id):
    return conn.execute(
        """
        SELECT
            id,
            full_name,
            pay_rate,
            assigned_group,
            created_at,
            updated_at
        FROM teachers
        WHERE id = ?
        """,
        (teacher_id,),
    ).fetchone()


def insert_teacher_row(conn, full_name, pay_rate, assigned_group, created_at, updated_at):
    conn.execute(
        """
        INSERT INTO teachers (
            full_name,
            pay_rate,
            assigned_group,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(assigned_group) DO UPDATE SET
            full_name = excluded.full_name,
            pay_rate = excluded.pay_rate,
            updated_at = excluded.updated_at
        """,
        (full_name, pay_rate, assigned_group, created_at, updated_at),
    )


def get_teacher_by_group_row(conn, group_name):
    return conn.execute(
        """
        SELECT id, full_name, pay_rate, assigned_group
        FROM teachers
        WHERE lower(assigned_group) = lower(?)
        """,
        (group_name,),
    ).fetchone()


def get_teacher_by_full_name_row(conn, full_name):
    return conn.execute(
        """
        SELECT id, full_name, pay_rate, assigned_group
        FROM teachers
        WHERE lower(full_name) = lower(?)
        ORDER BY id ASC
        LIMIT 1
        """,
        (full_name,),
    ).fetchone()


def delete_teacher_by_group(conn, group_name):
    conn.execute(
        """
        DELETE FROM teachers
        WHERE lower(assigned_group) = lower(?)
        """,
        (group_name,),
    )


def update_teacher_row_by_id(conn, teacher_id, full_name, pay_rate, assigned_group, updated_at):
    conn.execute(
        """
        UPDATE teachers
        SET
            full_name = ?,
            pay_rate = ?,
            assigned_group = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (full_name, pay_rate, assigned_group, updated_at, teacher_id),
    )


def delete_teacher_row_by_id(conn, teacher_id):
    conn.execute(
        """
        DELETE FROM teachers
        WHERE id = ?
        """,
        (teacher_id,),
    )


def get_bot_users_count(conn):
    row = conn.execute("SELECT COUNT(*) AS total FROM bot_users").fetchone()
    return int(row["total"] if row else 0)


def upsert_bot_user(conn, user_id, username, first_name, last_name, now):
    conn.execute(
        """
        INSERT INTO bot_users (
            telegram_user_id,
            username,
            first_name,
            last_name,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(telegram_user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            updated_at = excluded.updated_at
        """,
        (user_id, username, first_name, last_name, now, now),
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
            m.sheet_student_id
        FROM students s
        LEFT JOIN students_sheet_map m ON m.student_row_id = s.id
        WHERE s.telegram_user_id = ?
        """,
        (telegram_user_id,),
    ).fetchone()


def replace_subject_summary_rows(conn, rows):
    conn.execute("DELETE FROM subject_summaries")

    if not rows:
        return

    payload_rows = []
    for row in rows:
        payload_rows.append(
            (
                int(row.get("sheet_student_id", 0)),
                str(row.get("full_name", "")),
                str(row.get("full_name_norm", "")),
                str(row.get("subject_name", "")),
                str(row.get("subject_short", "")),
                int(row.get("aap", 0)),
                int(row.get("ar", 0)),
                int(row.get("ep", 0)),
                int(row.get("total_coins", 0)),
                int(row.get("rating_rank", 0)),
                int(row.get("rating_total", 0)),
                str(row.get("updated_at", "")),
            )
        )

    conn.executemany(
        """
        INSERT INTO subject_summaries (
            sheet_student_id,
            full_name,
            full_name_norm,
            subject_name,
            subject_short,
            aap,
            ar,
            ep,
            total_coins,
            rating_rank,
            rating_total,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload_rows,
    )


def list_subject_summary_rows_by_full_name_norm(conn, full_name_norm):
    return conn.execute(
        """
        SELECT
            sheet_student_id,
            full_name,
            subject_name,
            subject_short,
            aap,
            ar,
            ep,
            total_coins,
            rating_rank,
            rating_total,
            updated_at
        FROM subject_summaries
        WHERE full_name_norm = ?
        ORDER BY lower(subject_name) ASC, sheet_student_id ASC
        """,
        (full_name_norm,),
    ).fetchall()


def replace_lesson_catalog_rows(conn, rows):
    conn.execute("DELETE FROM lesson_catalog")

    if not rows:
        return

    payload_rows = []
    for row in rows:
        payload_rows.append(
            (
                str(row.get("subject_name", "")),
                str(row.get("group_name", "")),
                str(row.get("lesson_number", "")),
                str(row.get("lesson_topic", "")),
                str(row.get("lesson_date", "")),
                int(row.get("lesson_order", 0)),
                str(row.get("updated_at", "")),
            )
        )

    conn.executemany(
        """
        INSERT INTO lesson_catalog (
            subject_name,
            group_name,
            lesson_number,
            lesson_topic,
            lesson_date,
            lesson_order,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        payload_rows,
    )


def list_lesson_catalog_rows_by_subject(conn, subject_name):
    return conn.execute(
        """
        SELECT
            group_name,
            lesson_number,
            lesson_topic,
            lesson_date,
            lesson_order,
            updated_at
        FROM lesson_catalog
        WHERE lower(subject_name) = lower(?)
        ORDER BY lesson_order ASC, lesson_number ASC
        """,
        (subject_name,),
    ).fetchall()


def list_lesson_catalog_rows_by_subject_group(conn, subject_name, group_name):
    return conn.execute(
        """
        SELECT
            group_name,
            lesson_number,
            lesson_topic,
            lesson_date,
            lesson_order,
            updated_at
        FROM lesson_catalog
        WHERE lower(subject_name) = lower(?)
          AND lower(group_name) = lower(?)
        ORDER BY lesson_order ASC, lesson_number ASC
        """,
        (subject_name, group_name),
    ).fetchall()
