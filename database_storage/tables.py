from .database import get_db_backend_for_connection


def _is_postgres_conn(conn):
    return str(get_db_backend_for_connection(conn)).strip().casefold() == "postgres"


def _create_tables_postgres(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id BIGSERIAL PRIMARY KEY,
            login TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            is_owner SMALLINT NOT NULL DEFAULT 0 CHECK (is_owner IN (0, 1)),
            telegram_user_id BIGINT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_login_ci
        ON admins ((lower(login)))
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_telegram_user_id
        ON admins(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id BIGSERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            password TEXT NOT NULL,
            subjects TEXT NOT NULL,
            telegram_user_id BIGINT,
            photo_url TEXT NOT NULL DEFAULT '',
            profile_description TEXT NOT NULL DEFAULT '',
            class_name TEXT NOT NULL DEFAULT '',
            school_name TEXT NOT NULL DEFAULT '',
            school_key TEXT NOT NULL DEFAULT '',
            teacher_name TEXT NOT NULL DEFAULT '',
            last_seen_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_id_ci
        ON students ((upper(student_id)))
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
        ON students(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students_sheet_map (
            school_key TEXT NOT NULL,
            sheet_student_id BIGINT NOT NULL,
            student_row_id BIGINT NOT NULL UNIQUE,
            PRIMARY KEY (school_key, sheet_student_id),
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_students_sheet_map_sheet_student_id
        ON students_sheet_map(sheet_student_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS student_auth (
            student_row_id BIGINT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_users (
            id BIGSERIAL PRIMARY KEY,
            telegram_user_id BIGINT NOT NULL UNIQUE,
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
            id BIGSERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            pay_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            assigned_group TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_assigned_group_ci
        ON teachers ((lower(assigned_group)))
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
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            is_active SMALLINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            is_system SMALLINT NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_types_name_ci
        ON resource_types ((lower(name)))
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_types_slug_ci
        ON resource_types ((lower(slug)))
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
        CREATE TABLE IF NOT EXISTS resources (
            id BIGSERIAL PRIMARY KEY,
            subject_name TEXT NOT NULL,
            subject_key TEXT NOT NULL DEFAULT '',
            resource_type_id BIGINT NOT NULL,
            folder_path TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            resource_url TEXT NOT NULL DEFAULT '',
            resource_file_path TEXT NOT NULL DEFAULT '',
            thumbnail_file_path TEXT NOT NULL DEFAULT '',
            is_active SMALLINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_by_admin_id BIGINT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(resource_type_id) REFERENCES resource_types(id),
            FOREIGN KEY(created_by_admin_id) REFERENCES admins(id)
        )
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
            sheet_student_id BIGINT PRIMARY KEY,
            full_name TEXT NOT NULL,
            full_name_norm TEXT NOT NULL,
            school_key TEXT NOT NULL DEFAULT '',
            school_name TEXT NOT NULL DEFAULT '',
            group_name TEXT NOT NULL DEFAULT '',
            subject_name TEXT NOT NULL,
            subject_short TEXT NOT NULL,
            aap DOUBLE PRECISION NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_subject_summaries_school_key
        ON subject_summaries(school_key)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lesson_catalog (
            id BIGSERIAL PRIMARY KEY,
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

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id BIGSERIAL PRIMARY KEY,
            room TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_student_id TEXT NOT NULL,
            body TEXT NOT NULL,
            is_deleted SMALLINT NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
            edited_at TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_room_created
        ON chat_messages(room, created_at)
        WHERE is_deleted = 0
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_room_id
        ON chat_messages(room, id)
        WHERE is_deleted = 0
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_blocked_users (
            student_id TEXT PRIMARY KEY,
            blocked_by_admin TEXT NOT NULL DEFAULT '',
            blocked_at TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT ''
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_comments (
            id BIGSERIAL PRIMARY KEY,
            resource_id BIGINT NOT NULL,
            author_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resource_comments_resource_id
        ON resource_comments(resource_id, created_at)
        """
    )



def create_tables(conn):
    _create_tables_postgres(conn)


def ensure_students_schema(conn):
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
        ON students(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )
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
    conn.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS last_seen_at TEXT")


def ensure_admins_schema(conn):
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_telegram_user_id
        ON admins(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )


def ensure_students_sheet_map_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_students_sheet_map_sheet_student_id
        ON students_sheet_map(sheet_student_id)
        """
    )
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


def ensure_lesson_catalog_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_lesson_catalog_subject_order
        ON lesson_catalog(subject_name, group_name, lesson_order)
        """
    )


def ensure_subject_summaries_schema(conn):
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


def ensure_chat_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_room_created
        ON chat_messages(room, created_at)
        WHERE is_deleted = 0
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_room_id
        ON chat_messages(room, id)
        WHERE is_deleted = 0
        """
    )


def ensure_resource_comments_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resource_comments_resource_id
        ON resource_comments(resource_id, created_at)
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
    "ensure_resource_comments_schema",
    "ensure_chat_schema",
]
