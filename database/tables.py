def create_tables(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS msi_v2")


def ensure_students_schema(conn):
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
        ON msi_v2.students(telegram_user_id)
        WHERE telegram_user_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_code_ci
        ON msi_v2.students ((upper(student_code)))
        """
    )


def ensure_parents_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.parents (
            id BIGSERIAL PRIMARY KEY,
            display_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            telegram_user_id BIGINT,
            telegram_username TEXT NOT NULL DEFAULT '',
            preferred_language TEXT NOT NULL DEFAULT 'ru',
            status TEXT NOT NULL DEFAULT 'active',
            legacy_parent_id BIGINT,
            legacy_admin_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.parent_student_links (
            parent_id BIGINT NOT NULL REFERENCES msi_v2.parents(id) ON DELETE CASCADE,
            student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
            relationship TEXT NOT NULL DEFAULT 'parent',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (parent_id, student_id)
        )
        """
    )


def ensure_account_invites_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.account_invites (
            id BIGSERIAL PRIMARY KEY,
            invite_type TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            token TEXT NOT NULL DEFAULT '',
            student_id BIGINT REFERENCES msi_v2.students(id) ON DELETE CASCADE,
            issued_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            expires_at TIMESTAMPTZ,
            max_uses INTEGER NOT NULL DEFAULT 1,
            used_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            used_by_telegram_user_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            used_at TIMESTAMPTZ
        )
        """
    )
    conn.execute("ALTER TABLE msi_v2.account_invites ADD COLUMN IF NOT EXISTS token TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_account_invites_token_hash
        ON msi_v2.account_invites(token_hash)
        """
    )


def ensure_support_tickets_schema(conn):
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
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_support_tickets_status_updated
        ON msi_v2.support_tickets(status, updated_at)
        """
    )


def ensure_ticket_messages_schema(conn):
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
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket
        ON msi_v2.ticket_messages(ticket_id, created_at, id)
        """
    )


def ensure_payments_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payments_student_due
        ON msi_v2.payments(student_id, due_date, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payments_status_due
        ON msi_v2.payments(status, due_date)
        """
    )


def ensure_curriculum_items_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subject_program_items_program_type_order
        ON msi_v2.subject_program_items(program_id, item_type, item_order)
        """
    )


def ensure_resources_schema(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resources_subject_active
        ON msi_v2.resources(subject_id, is_active, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resources_type_active
        ON msi_v2.resources(resource_type_id, is_active, updated_at)
        """
    )


def ensure_chat_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.chat_messages (
            id BIGSERIAL PRIMARY KEY,
            room TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_student_id TEXT NOT NULL,
            body TEXT NOT NULL,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            edited_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_room_id
        ON msi_v2.chat_messages(room, id)
        WHERE is_deleted IS FALSE
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.chat_blocked_users (
            student_id TEXT PRIMARY KEY,
            blocked_by_staff_login TEXT NOT NULL DEFAULT '',
            blocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            reason TEXT NOT NULL DEFAULT ''
        )
        """
    )


def ensure_resource_comments_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.resource_comments (
            id BIGSERIAL PRIMARY KEY,
            resource_id BIGINT NOT NULL REFERENCES msi_v2.resources(id) ON DELETE CASCADE,
            author_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resource_comments_resource_id
        ON msi_v2.resource_comments(resource_id, created_at)
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


def ensure_teacher_academy_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.academy_teachers (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            full_name TEXT NOT NULL,
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            subject_program_id BIGINT REFERENCES msi_v2.subject_programs(id) ON DELETE SET NULL,
            position TEXT NOT NULL DEFAULT 'Trainee Teacher',
            employment_type TEXT NOT NULL DEFAULT 'academy',
            telegram_username TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            academy_status TEXT NOT NULL DEFAULT 'in_training',
            academy_start_date DATE,
            mentor_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL,
            department_head_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            promoted_teacher_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.academy_lesson_assignments (
            id BIGSERIAL PRIMARY KEY,
            academy_teacher_id BIGINT NOT NULL REFERENCES msi_v2.academy_teachers(id) ON DELETE CASCADE,
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            subject_program_id BIGINT REFERENCES msi_v2.subject_programs(id) ON DELETE SET NULL,
            curriculum_item_id BIGINT REFERENCES msi_v2.subject_program_items(id) ON DELETE SET NULL,
            sequence_no INTEGER NOT NULL DEFAULT 0,
            lesson_number TEXT NOT NULL DEFAULT '',
            lesson_topic TEXT NOT NULL DEFAULT '',
            assignment_type TEXT NOT NULL DEFAULT 'full_practice_lesson',
            deadline_date DATE,
            session_datetime TIMESTAMPTZ,
            evaluator_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL,
            focus_areas JSONB NOT NULL DEFAULT '[]'::jsonb,
            notes_to_trainee TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'assigned',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.academy_assessments (
            id BIGSERIAL PRIMARY KEY,
            academy_teacher_id BIGINT NOT NULL REFERENCES msi_v2.academy_teachers(id) ON DELETE CASCADE,
            lesson_assignment_id BIGINT REFERENCES msi_v2.academy_lesson_assignments(id) ON DELETE SET NULL,
            assessment_type TEXT NOT NULL DEFAULT 'academy_practice_lesson',
            lesson_number TEXT NOT NULL DEFAULT '',
            lesson_topic TEXT NOT NULL DEFAULT '',
            evaluator_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL,
            assessment_datetime TIMESTAMPTZ,
            session_type TEXT NOT NULL DEFAULT 'training_simulation',
            class_label TEXT NOT NULL DEFAULT '',
            section_feedback JSONB NOT NULL DEFAULT '{}'::jsonb,
            teacher_guidance_compliance_score NUMERIC(4, 2) NOT NULL DEFAULT 0,
            timing_adherence_score NUMERIC(4, 2) NOT NULL DEFAULT 0,
            resource_familiarity_score NUMERIC(4, 2) NOT NULL DEFAULT 0,
            english_fluency_score NUMERIC(4, 2) NOT NULL DEFAULT 0,
            confidence_delivery_score NUMERIC(4, 2) NOT NULL DEFAULT 0,
            engagement_technique_score NUMERIC(4, 2) NOT NULL DEFAULT 0,
            weighted_overall_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
            strengths TEXT NOT NULL DEFAULT '',
            areas_for_improvement TEXT NOT NULL DEFAULT '',
            final_recommendation TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT 'needs_improvement',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_academy_teachers_status_updated
        ON msi_v2.academy_teachers(academy_status, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_academy_assignments_teacher_sequence
        ON msi_v2.academy_lesson_assignments(academy_teacher_id, sequence_no)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_academy_assessments_teacher_created
        ON msi_v2.academy_assessments(academy_teacher_id, created_at)
        """
    )


def ensure_office_hours_schema(conn):
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


__all__ = [
    "create_tables",
    "ensure_parents_schema",
    "ensure_account_invites_schema",
    "ensure_support_tickets_schema",
    "ensure_ticket_messages_schema",
    "ensure_payments_schema",
    "ensure_students_schema",
    "ensure_curriculum_items_schema",
    "ensure_resources_schema",
    "ensure_resource_comments_schema",
    "ensure_chat_schema",
    "ensure_teacher_candidates_schema",
    "ensure_teacher_academy_schema",
    "ensure_office_hours_schema",
]
