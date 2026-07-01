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
            student_row_id BIGINT NOT NULL,
            PRIMARY KEY (school_key, sheet_student_id),
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_students_sheet_map_student_row_id
        ON students_sheet_map(student_row_id)
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

    _create_parent_accounts_tables(conn)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS student_payments (
            id BIGSERIAL PRIMARY KEY,
            student_row_id BIGINT,
            subject TEXT NOT NULL DEFAULT '',
            month_label TEXT NOT NULL DEFAULT '',
            amount DOUBLE PRECISION NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'UZS',
            status TEXT NOT NULL DEFAULT 'due',
            due_date TEXT NOT NULL DEFAULT '',
            paid_at TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_by_admin_id BIGINT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by_admin_id) REFERENCES admins(id) ON DELETE SET NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_student_payments_student_due
        ON student_payments(student_row_id, due_date, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_student_payments_status_due
        ON student_payments(status, due_date)
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
            category TEXT NOT NULL DEFAULT 'junior',
            semester_stage TEXT NOT NULL DEFAULT '1-2',
            performance_score DOUBLE PRECISION NOT NULL DEFAULT 7,
            supervised_lessons INTEGER NOT NULL DEFAULT 0,
            igcse_evidence TEXT NOT NULL DEFAULT '',
            promotion_notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'junior'")
    conn.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS semester_stage TEXT NOT NULL DEFAULT '1-2'")
    conn.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS performance_score DOUBLE PRECISION NOT NULL DEFAULT 7")
    conn.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS supervised_lessons INTEGER NOT NULL DEFAULT 0")
    conn.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS igcse_evidence TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS promotion_notes TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_assigned_group_ci
        ON teachers ((lower(assigned_group)))
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_candidates (
            id BIGSERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL DEFAULT '',
            telegram_username TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            subject TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_status_updated
        ON teacher_candidates(status, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_name_ci
        ON teacher_candidates ((lower(full_name)))
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_candidate_events (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL,
            event_type TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT '',
            score DOUBLE PRECISION,
            notes TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES teacher_candidates(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_events_candidate_created
        ON teacher_candidate_events(candidate_id, created_at)
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
    """Compatibility hook retained for old callers.

    The live application now bootstraps the canonical msi_v2 schema from
    scripts/rebuild_database_v2.sql. Do not recreate legacy public tables here.
    """
    conn.execute("CREATE SCHEMA IF NOT EXISTS msi_v2")


def ensure_students_schema(conn):
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
        ON students(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )
    # A student can legitimately map to several sheet ids (the old Sheets import
    # gave each subject its own public_dashboard_id). Drop the historical
    # one-map-per-student UNIQUE so a single login can own multiple subject ids.
    conn.execute(
        "ALTER TABLE students_sheet_map DROP CONSTRAINT IF EXISTS students_sheet_map_student_row_id_key"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_students_sheet_map_student_row_id ON students_sheet_map(student_row_id)"
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
    # Editable parent/guardian profile fields (parents are stored as admins with
    # role='parent'). Additive only — never removes or renames existing columns.
    conn.execute("ALTER TABLE admins ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE admins ADD COLUMN IF NOT EXISTS phone TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE admins ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE admins ADD COLUMN IF NOT EXISTS telegram_username TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE admins ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT ''")
    # Account lifecycle: a disabled parent account keeps its data but cannot log in.
    conn.execute("ALTER TABLE admins ADD COLUMN IF NOT EXISTS disabled SMALLINT NOT NULL DEFAULT 0")


def _create_parent_accounts_tables(conn):
    """Parent CLIENT accounts — deliberately separate from `admins`.

    A parent is a customer responsible for their children, NOT a staff member:
    these rows carry no login/password and grant no admin privileges. Populated
    by the parent invite-link flow (web/backend/roles/parent). `source_admin_id`
    records provenance when a legacy role='parent' admin is migrated in, so the
    migration stays idempotent and the old row can be matched back.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parents (
            id BIGSERIAL PRIMARY KEY,
            full_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            telegram_username TEXT NOT NULL DEFAULT '',
            telegram_user_id BIGINT,
            source_admin_id BIGINT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(source_admin_id) REFERENCES admins(id) ON DELETE SET NULL
        )
        """
    )
    # Idempotent migration anchor: at most one parent per migrated admin row.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_parents_source_admin
        ON parents(source_admin_id)
        WHERE source_admin_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_parents_telegram_username
        ON parents ((lower(telegram_username)))
        WHERE telegram_username <> ''
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_parents_telegram_user_id
        ON parents(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parent_student_links (
            parent_id BIGINT NOT NULL,
            student_row_id BIGINT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (parent_id, student_row_id),
            FOREIGN KEY(parent_id) REFERENCES parents(id) ON DELETE CASCADE,
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_parent_student_links_student
        ON parent_student_links(student_row_id)
        """
    )


def ensure_parent_accounts_schema(conn):
    """Lazy guard so query code can create the parent tables on demand."""
    _create_parent_accounts_tables(conn)


def ensure_parent_invites_schema(conn):
    """Short bot deep-link codes for parent invite tokens.

    Telegram `/start` payloads are intentionally short, so the full signed web
    invite token is stored server-side and referenced by a compact code.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parent_invites (
            code TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            student_row_id BIGINT NOT NULL,
            issued_by BIGINT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT '',
            used_at TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(issued_by) REFERENCES admins(id) ON DELETE SET NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_parent_invites_student
        ON parent_invites(student_row_id, created_at)
        """
    )


def ensure_student_payments_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS student_payments (
            id BIGSERIAL PRIMARY KEY,
            student_row_id BIGINT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            month_label TEXT NOT NULL DEFAULT '',
            amount DOUBLE PRECISION NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'UZS',
            status TEXT NOT NULL DEFAULT 'due',
            due_date TEXT NOT NULL DEFAULT '',
            paid_at TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_by_admin_id BIGINT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by_admin_id) REFERENCES admins(id) ON DELETE SET NULL
        )
        """
    )
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS subject TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS month_label TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS amount DOUBLE PRECISION NOT NULL DEFAULT 0")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'UZS'")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'due'")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS due_date TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS paid_at TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS created_by_admin_id BIGINT")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS created_at TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE student_payments ADD COLUMN IF NOT EXISTS updated_at TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_student_payments_student_due
        ON student_payments(student_row_id, due_date, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_student_payments_status_due
        ON student_payments(status, due_date)
        """
    )


def ensure_parent_complaints_schema(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS msi_v2")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.support_tickets (
            id BIGSERIAL PRIMARY KEY,
            parent_id BIGINT REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
            student_id BIGINT REFERENCES msi_v2.students(id) ON DELETE SET NULL,
            category TEXT NOT NULL DEFAULT 'other',
            topic TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            assigned_to_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            escalated_to_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            legacy_complaint_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at TIMESTAMPTZ
        )
        """
    )
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS parent_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS student_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'other'")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'new'")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS assigned_to_staff_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS escalated_to_staff_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS legacy_complaint_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    conn.execute("ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_support_tickets_parent_id
        ON msi_v2.support_tickets(parent_id)
        WHERE parent_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_support_tickets_status_updated
        ON msi_v2.support_tickets(status, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_support_tickets_student_id
        ON msi_v2.support_tickets(student_id)
        WHERE student_id IS NOT NULL
        """
    )


def ensure_complaint_messages_schema(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS msi_v2")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.ticket_messages (
            id BIGSERIAL PRIMARY KEY,
            ticket_id BIGINT NOT NULL REFERENCES msi_v2.support_tickets(id) ON DELETE CASCADE,
            author_type TEXT NOT NULL,
            author_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            author_parent_id BIGINT REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute("ALTER TABLE msi_v2.ticket_messages ADD COLUMN IF NOT EXISTS ticket_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.ticket_messages ADD COLUMN IF NOT EXISTS author_type TEXT NOT NULL DEFAULT 'system'")
    conn.execute("ALTER TABLE msi_v2.ticket_messages ADD COLUMN IF NOT EXISTS author_staff_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.ticket_messages ADD COLUMN IF NOT EXISTS author_parent_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.ticket_messages ADD COLUMN IF NOT EXISTS body TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE msi_v2.ticket_messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket
        ON msi_v2.ticket_messages(ticket_id, created_at, id)
        """
    )


def ensure_lesson_catalog_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_lesson_catalog_subject_order
        ON lesson_catalog(subject_name, group_name, lesson_order)
        """
    )


def ensure_teacher_auth_schema(conn):
    # Login credentials for the teacher role. Mirrors student_auth, but keeps a
    # viewable login/password so admins can hand credentials to teachers (the
    # students list shows passwords the same way).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_auth (
            teacher_id BIGINT PRIMARY KEY,
            login TEXT NOT NULL,
            password TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_auth_login_ci
        ON teacher_auth ((lower(login)))
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


def ensure_teacher_candidates_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidates (
            id BIGSERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL DEFAULT '',
            telegram_username TEXT NOT NULL DEFAULT '',
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            source TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            notes TEXT NOT NULL DEFAULT '',
            legacy_candidate_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_status_updated
        ON msi_v2.teacher_candidates(status, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_name_ci
        ON msi_v2.teacher_candidates ((lower(full_name)))
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_events (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT '',
            score NUMERIC(4, 1),
            notes TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_events_candidate_created
        ON msi_v2.teacher_candidate_events(candidate_id, created_at)
        """
    )


def ensure_academic_reference_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_schools (
            id BIGSERIAL PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_subjects (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL REFERENCES academic_schools(id),
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            code TEXT NOT NULL DEFAULT '',
            short_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, key)
        )
        """
    )


def ensure_office_hours_schema(conn):
    conn.execute(
        """
        CREATE SCHEMA IF NOT EXISTS msi_v2
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.office_hour_slots (
            id BIGSERIAL PRIMARY KEY,
            teacher_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE CASCADE,
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ NOT NULL,
            slot_minutes INTEGER NOT NULL DEFAULT 30,
            capacity INTEGER NOT NULL DEFAULT 1,
            room TEXT NOT NULL DEFAULT '',
            planned_topic TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            legacy_slot_id BIGINT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_office_hour_slots_starts
        ON msi_v2.office_hour_slots(starts_at, status)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_office_hour_slots_legacy_id
        ON msi_v2.office_hour_slots(legacy_slot_id)
        WHERE legacy_slot_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.office_hour_bookings (
            id BIGSERIAL PRIMARY KEY,
            slot_id BIGINT NOT NULL REFERENCES msi_v2.office_hour_slots(id) ON DELETE CASCADE,
            student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'booked',
            student_note TEXT NOT NULL DEFAULT '',
            student_topic_request TEXT NOT NULL DEFAULT '',
            teacher_note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            canceled_at TIMESTAMPTZ,
            legacy_booking_id BIGINT
        )
        """
    )
    conn.execute("ALTER TABLE msi_v2.office_hour_slots ADD COLUMN IF NOT EXISTS planned_topic TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE msi_v2.office_hour_slots ADD COLUMN IF NOT EXISTS legacy_slot_id BIGINT")
    conn.execute("ALTER TABLE msi_v2.office_hour_bookings ADD COLUMN IF NOT EXISTS student_topic_request TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE msi_v2.office_hour_bookings ADD COLUMN IF NOT EXISTS legacy_booking_id BIGINT")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_office_hour_bookings_student
        ON msi_v2.office_hour_bookings(student_id, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_office_hour_bookings_teacher
        ON msi_v2.office_hour_slots(teacher_id, starts_at)
        """
    )


__all__ = [
    "create_tables",
    "ensure_admins_schema",
    "ensure_parent_accounts_schema",
    "ensure_parent_invites_schema",
    "ensure_parent_complaints_schema",
    "ensure_complaint_messages_schema",
    "ensure_student_payments_schema",
    "ensure_students_schema",
    "ensure_lesson_catalog_schema",
    "ensure_resources_schema",
    "ensure_resource_comments_schema",
    "ensure_chat_schema",
    "ensure_teacher_candidates_schema",
    "ensure_teacher_auth_schema",
    "ensure_office_hours_schema",
]
