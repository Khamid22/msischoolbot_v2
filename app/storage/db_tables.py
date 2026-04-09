def create_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            is_owner INTEGER NOT NULL DEFAULT 0 CHECK (is_owner IN (0, 1)),
            telegram_user_id INTEGER,
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
            school_key TEXT NOT NULL DEFAULT '',
            teacher_name TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students_sheet_map (
            school_key TEXT NOT NULL,
            sheet_student_id INTEGER NOT NULL,
            student_row_id INTEGER NOT NULL UNIQUE,
            PRIMARY KEY (school_key, sheet_student_id),
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
        CREATE TABLE IF NOT EXISTS resource_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            slug TEXT NOT NULL UNIQUE COLLATE NOCASE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            subject_key TEXT NOT NULL DEFAULT '',
            resource_type_id INTEGER NOT NULL,
            folder_path TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            resource_url TEXT NOT NULL DEFAULT '',
            resource_file_path TEXT NOT NULL DEFAULT '',
            thumbnail_file_path TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_by_admin_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(resource_type_id) REFERENCES resource_types(id),
            FOREIGN KEY(created_by_admin_id) REFERENCES admins(id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resource_types_display_order
        ON resource_types(is_active, display_order, name)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resources_subject_key
        ON resources(subject_key, is_active, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resources_type
        ON resources(resource_type_id, is_active, updated_at)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_summaries (
            sheet_student_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            full_name_norm TEXT NOT NULL,
            school_key TEXT NOT NULL DEFAULT '',
            school_name TEXT NOT NULL DEFAULT '',
            group_name TEXT NOT NULL DEFAULT '',
            subject_name TEXT NOT NULL,
            subject_short TEXT NOT NULL,
            aap REAL NOT NULL,
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
    if "school_key" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN school_key TEXT NOT NULL DEFAULT ''")
    if "teacher_name" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN teacher_name TEXT NOT NULL DEFAULT ''")

    # Backfill school_key from school_name for already existing rows.
    conn.execute(
        """
        UPDATE students
        SET school_key = 'school5'
        WHERE lower(trim(coalesce(school_key, ''))) IN ('school_5', 'school-5', 'school 5')
        """
    )
    conn.execute(
        """
        UPDATE students
        SET school_key = 'sehriyo'
        WHERE lower(trim(coalesce(school_key, ''))) IN ('sehriyo school')
        """
    )
    conn.execute(
        """
        UPDATE students
        SET school_key = CASE
            WHEN lower(trim(school_name)) = 'sehriyo' THEN 'sehriyo'
            ELSE 'school5'
        END
        WHERE trim(coalesce(school_key, '')) = ''
        """
    )

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
        ON students(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )


def ensure_admins_schema(conn):
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(admins)").fetchall()
    }
    if "telegram_user_id" not in columns:
        conn.execute("ALTER TABLE admins ADD COLUMN telegram_user_id INTEGER")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_telegram_user_id
        ON admins(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )


def ensure_students_sheet_map_schema(conn):
    column_rows = conn.execute("PRAGMA table_info(students_sheet_map)").fetchall()
    columns = {str(row["name"]) for row in column_rows}
    if not columns:
        return

    pk_rows = sorted(
        (
            (int(row["pk"]), str(row["name"]))
            for row in column_rows
            if int(row["pk"]) > 0
        ),
        key=lambda item: item[0],
    )
    pk_columns = [name for _order, name in pk_rows]
    has_expected_schema = (
        "school_key" in columns
        and "sheet_student_id" in columns
        and pk_columns == ["school_key", "sheet_student_id"]
    )
    if has_expected_schema:
        conn.execute(
            """
            UPDATE students_sheet_map
            SET school_key = 'school5'
            WHERE lower(trim(coalesce(school_key, ''))) IN ('school_5', 'school-5', 'school 5')
            """
        )
        conn.execute(
            """
            UPDATE students_sheet_map
            SET school_key = 'sehriyo'
            WHERE lower(trim(coalesce(school_key, ''))) IN ('sehriyo school')
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_students_sheet_map_sheet_student_id
            ON students_sheet_map(sheet_student_id)
            """
        )
        return

    conn.execute("ALTER TABLE students_sheet_map RENAME TO students_sheet_map_legacy")
    conn.execute(
        """
        CREATE TABLE students_sheet_map (
            school_key TEXT NOT NULL,
            sheet_student_id INTEGER NOT NULL,
            student_row_id INTEGER NOT NULL UNIQUE,
            PRIMARY KEY (school_key, sheet_student_id),
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )

    legacy_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(students_sheet_map_legacy)").fetchall()
    }
    if "school_key" in legacy_columns:
        conn.execute(
            """
            INSERT INTO students_sheet_map (
                school_key,
                sheet_student_id,
                student_row_id
            )
            SELECT
                CASE
                    WHEN lower(trim(coalesce(m.school_key, ''))) IN ('school_5', 'school-5', 'school 5', 'school5') THEN 'school5'
                    WHEN lower(trim(coalesce(m.school_key, ''))) IN ('sehriyo', 'sehriyo school') THEN 'sehriyo'
                    WHEN lower(trim(coalesce(s.school_key, ''))) IN ('sehriyo', 'sehriyo school') THEN 'sehriyo'
                    ELSE 'school5'
                END,
                m.sheet_student_id,
                m.student_row_id
            FROM students_sheet_map_legacy m
            LEFT JOIN students s ON s.id = m.student_row_id
            """
        )
    else:
        conn.execute(
            """
            INSERT INTO students_sheet_map (
                school_key,
                sheet_student_id,
                student_row_id
            )
            SELECT
                CASE
                    WHEN lower(trim(coalesce(s.school_key, ''))) IN ('sehriyo', 'sehriyo school') THEN 'sehriyo'
                    ELSE 'school5'
                END,
                m.sheet_student_id,
                m.student_row_id
            FROM students_sheet_map_legacy m
            LEFT JOIN students s ON s.id = m.student_row_id
            """
        )

    conn.execute("DROP TABLE students_sheet_map_legacy")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_students_sheet_map_sheet_student_id
        ON students_sheet_map(sheet_student_id)
        """
    )


def ensure_lesson_catalog_schema(conn):
    column_rows = conn.execute("PRAGMA table_info(lesson_catalog)").fetchall()
    columns = {str(row["name"]) for row in column_rows}
    if not columns:
        return
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


def ensure_subject_summaries_schema(conn):
    column_rows = conn.execute("PRAGMA table_info(subject_summaries)").fetchall()
    columns = {str(row["name"]) for row in column_rows}
    if not columns:
        return

    aap_column = next(
        (row for row in column_rows if str(row["name"]) == "aap"),
        None,
    )
    if aap_column is None:
        return

    declared_type = str(aap_column["type"] or "").strip().upper()
    requires_rebuild = not (
        "REAL" in declared_type or "FLOA" in declared_type or "DOUB" in declared_type
    )
    if requires_rebuild:
        conn.execute("ALTER TABLE subject_summaries RENAME TO subject_summaries_legacy")
        conn.execute(
            """
            CREATE TABLE subject_summaries (
                sheet_student_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                full_name_norm TEXT NOT NULL,
                school_key TEXT NOT NULL DEFAULT '',
                school_name TEXT NOT NULL DEFAULT '',
                group_name TEXT NOT NULL DEFAULT '',
                subject_name TEXT NOT NULL,
                subject_short TEXT NOT NULL,
                aap REAL NOT NULL,
                ar INTEGER NOT NULL,
                ep INTEGER NOT NULL,
                total_coins INTEGER NOT NULL,
                rating_rank INTEGER NOT NULL,
                rating_total INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        legacy_columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(subject_summaries_legacy)").fetchall()
        }
        has_school_key = "school_key" in legacy_columns
        has_school_name = "school_name" in legacy_columns
        has_group_name = "group_name" in legacy_columns
        conn.execute(
            f"""
            INSERT INTO subject_summaries (
                sheet_student_id,
                full_name,
                full_name_norm,
                school_key,
                school_name,
                group_name,
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
            SELECT
                sheet_student_id,
                full_name,
                full_name_norm,
                {"school_key" if has_school_key else "''"},
                {"school_name" if has_school_name else "''"},
                {"group_name" if has_group_name else "''"},
                subject_name,
                subject_short,
                CAST(aap AS REAL),
                ar,
                ep,
                total_coins,
                rating_rank,
                rating_total,
                updated_at
            FROM subject_summaries_legacy
            """
        )
        conn.execute("DROP TABLE subject_summaries_legacy")
    else:
        if "school_key" not in columns:
            conn.execute(
                "ALTER TABLE subject_summaries ADD COLUMN school_key TEXT NOT NULL DEFAULT ''"
            )
        if "school_name" not in columns:
            conn.execute(
                "ALTER TABLE subject_summaries ADD COLUMN school_name TEXT NOT NULL DEFAULT ''"
            )
        if "group_name" not in columns:
            conn.execute(
                "ALTER TABLE subject_summaries ADD COLUMN group_name TEXT NOT NULL DEFAULT ''"
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
        CREATE INDEX IF NOT EXISTS idx_subject_summaries_school_key
        ON subject_summaries(school_key)
        """
    )


def ensure_resources_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            slug TEXT NOT NULL UNIQUE COLLATE NOCASE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            subject_key TEXT NOT NULL DEFAULT '',
            resource_type_id INTEGER NOT NULL,
            folder_path TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            resource_url TEXT NOT NULL DEFAULT '',
            resource_file_path TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_by_admin_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(resource_type_id) REFERENCES resource_types(id),
            FOREIGN KEY(created_by_admin_id) REFERENCES admins(id)
        )
        """
    )

    resource_type_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(resource_types)").fetchall()
    }
    if resource_type_columns:
        if "is_active" not in resource_type_columns:
            conn.execute(
                "ALTER TABLE resource_types ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )
        if "is_system" not in resource_type_columns:
            conn.execute(
                "ALTER TABLE resource_types ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0"
            )
        if "display_order" not in resource_type_columns:
            conn.execute(
                "ALTER TABLE resource_types ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0"
            )
        if "slug" not in resource_type_columns:
            conn.execute(
                "ALTER TABLE resource_types ADD COLUMN slug TEXT NOT NULL DEFAULT ''"
            )
        if "created_at" not in resource_type_columns:
            conn.execute(
                "ALTER TABLE resource_types ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        if "updated_at" not in resource_type_columns:
            conn.execute(
                "ALTER TABLE resource_types ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
            )
        conn.execute(
            """
            UPDATE resource_types
            SET slug = lower(replace(trim(name), ' ', '-'))
            WHERE trim(coalesce(slug, '')) = ''
            """
        )
        conn.execute(
            """
            UPDATE resource_types
            SET created_at = updated_at
            WHERE trim(coalesce(created_at, '')) = ''
            """
        )
        conn.execute(
            """
            UPDATE resource_types
            SET updated_at = created_at
            WHERE trim(coalesce(updated_at, '')) = ''
            """
        )

    resource_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(resources)").fetchall()
    }
    if resource_columns:
        if "subject_key" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN subject_key TEXT NOT NULL DEFAULT ''"
            )
        if "folder_path" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN folder_path TEXT NOT NULL DEFAULT ''"
            )
        if "description" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN description TEXT NOT NULL DEFAULT ''"
            )
        if "resource_url" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN resource_url TEXT NOT NULL DEFAULT ''"
            )
        if "resource_file_path" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN resource_file_path TEXT NOT NULL DEFAULT ''"
            )
        if "is_active" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )
        if "created_by_admin_id" not in resource_columns:
            conn.execute("ALTER TABLE resources ADD COLUMN created_by_admin_id INTEGER")
        if "thumbnail_file_path" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN thumbnail_file_path TEXT NOT NULL DEFAULT ''"
            )
        if "created_at" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        if "updated_at" not in resource_columns:
            conn.execute(
                "ALTER TABLE resources ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
            )
        conn.execute(
            """
            UPDATE resources
            SET subject_key = lower(trim(subject_name))
            WHERE trim(coalesce(subject_key, '')) = ''
            """
        )
        conn.execute(
            """
            UPDATE resources
            SET folder_path = (
                SELECT coalesce(trim(t.name), '')
                FROM resource_types t
                WHERE t.id = resources.resource_type_id
            )
            WHERE trim(coalesce(folder_path, '')) = ''
            """
        )
        conn.execute(
            """
            UPDATE resources
            SET created_at = updated_at
            WHERE trim(coalesce(created_at, '')) = ''
            """
        )
        conn.execute(
            """
            UPDATE resources
            SET updated_at = created_at
            WHERE trim(coalesce(updated_at, '')) = ''
            """
        )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resource_types_display_order
        ON resource_types(is_active, display_order, name)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resources_subject_key
        ON resources(subject_key, is_active, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resources_type
        ON resources(resource_type_id, is_active, updated_at)
        """
    )


__all__ = [
    "create_tables",
    "ensure_admins_schema",
    "ensure_students_schema",
    "ensure_students_sheet_map_schema",
    "ensure_lesson_catalog_schema",
    "ensure_subject_summaries_schema",
    "ensure_resources_schema",
]
