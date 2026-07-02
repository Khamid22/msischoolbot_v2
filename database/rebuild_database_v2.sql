-- MSI School clean database schema v2.
--
-- This creates clean tables in a separate PostgreSQL schema: msi_v2.
-- It does not drop or alter the old public tables.
--
-- Apply locally with:
--   psql "$DATABASE_URL" -f scripts/rebuild_database_v2.sql
--
-- Or through the app wrapper/import scripts before cutover.

BEGIN;

CREATE SCHEMA IF NOT EXISTS msi_v2;

CREATE TABLE IF NOT EXISTS msi_v2.msi_staff (
    id BIGSERIAL PRIMARY KEY,
    login TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    telegram_user_id BIGINT,
    telegram_username TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    subject_scope TEXT NOT NULL DEFAULT '',
    school_scope TEXT NOT NULL DEFAULT '',
    legacy_admin_id BIGINT,
    created_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_msi_staff_login_ci
ON msi_v2.msi_staff ((lower(login)));

CREATE UNIQUE INDEX IF NOT EXISTS idx_msi_staff_telegram_user_id
ON msi_v2.msi_staff (telegram_user_id)
WHERE telegram_user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_msi_staff_legacy_admin_id
ON msi_v2.msi_staff (legacy_admin_id)
WHERE legacy_admin_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.telegram_accounts (
    telegram_user_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    linked_entity_type TEXT NOT NULL DEFAULT '',
    linked_entity_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msi_v2.audit_events (
    id BIGSERIAL PRIMARY KEY,
    actor_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    actor_telegram_user_id BIGINT,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id BIGINT,
    detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_entity_created
ON msi_v2.audit_events (entity_type, entity_id, created_at DESC);

CREATE TABLE IF NOT EXISTS msi_v2.schools (
    id BIGSERIAL PRIMARY KEY,
    school_key TEXT NOT NULL,
    school_name TEXT NOT NULL,
    contact_name TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_key_ci
ON msi_v2.schools ((lower(school_key)));

CREATE TABLE IF NOT EXISTS msi_v2.students (
    id BIGSERIAL PRIMARY KEY,
    student_code TEXT NOT NULL,
    full_name TEXT NOT NULL,
    school_id BIGINT REFERENCES msi_v2.schools(id) ON DELETE SET NULL,
    telegram_user_id BIGINT,
    photo_url TEXT NOT NULL DEFAULT '',
    profile_description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    legacy_public_dashboard_id BIGINT,
    legacy_student_row_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_students_code_ci
ON msi_v2.students ((upper(student_code)));

CREATE UNIQUE INDEX IF NOT EXISTS idx_students_telegram_user_id
ON msi_v2.students (telegram_user_id)
WHERE telegram_user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_students_legacy_student_row_id
ON msi_v2.students (legacy_student_row_id)
WHERE legacy_student_row_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.student_auth (
    student_id BIGINT PRIMARY KEY REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    must_change_password BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS msi_v2.student_telegram_links (
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL REFERENCES msi_v2.telegram_accounts(telegram_user_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    linked_by_invite_id BIGINT,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    unlinked_at TIMESTAMPTZ,
    PRIMARY KEY (student_id, telegram_user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_student_telegram_links_one_active
ON msi_v2.student_telegram_links (student_id)
WHERE status = 'active';

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
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_parents_telegram_user_id
ON msi_v2.parents (telegram_user_id)
WHERE telegram_user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_parents_legacy_parent_id
ON msi_v2.parents (legacy_parent_id)
WHERE legacy_parent_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_parents_legacy_admin_id
ON msi_v2.parents (legacy_admin_id)
WHERE legacy_admin_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.parent_student_links (
    parent_id BIGINT NOT NULL REFERENCES msi_v2.parents(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL DEFAULT 'parent',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (parent_id, student_id)
);

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
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_account_invites_token_hash
ON msi_v2.account_invites (token_hash);

CREATE TABLE IF NOT EXISTS msi_v2.subjects (
    id BIGSERIAL PRIMARY KEY,
    subject_key TEXT NOT NULL,
    subject_name TEXT NOT NULL,
    subject_short TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_key_ci
ON msi_v2.subjects ((lower(subject_key)));

CREATE TABLE IF NOT EXISTS msi_v2.subject_programs (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL REFERENCES msi_v2.subjects(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL DEFAULT '2025-26',
    program_name TEXT NOT NULL,
    source_file TEXT NOT NULL DEFAULT '',
    total_items INTEGER NOT NULL DEFAULT 0,
    lesson_count INTEGER NOT NULL DEFAULT 0,
    exam_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subject_id, academic_year)
);

CREATE TABLE IF NOT EXISTS msi_v2.subject_program_items (
    id BIGSERIAL PRIMARY KEY,
    program_id BIGINT NOT NULL REFERENCES msi_v2.subject_programs(id) ON DELETE CASCADE,
    item_order INTEGER NOT NULL,
    lesson_number TEXT NOT NULL,
    item_type TEXT NOT NULL DEFAULT 'lesson',
    title TEXT NOT NULL,
    term_label TEXT NOT NULL DEFAULT '',
    week_label TEXT NOT NULL DEFAULT '',
    specification_points TEXT NOT NULL DEFAULT '',
    book_pages TEXT NOT NULL DEFAULT '',
    lesson_count TEXT NOT NULL DEFAULT '',
    duration_hours TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL DEFAULT '',
    sheet_name TEXT NOT NULL DEFAULT '',
    source_row INTEGER NOT NULL DEFAULT 0,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (program_id, item_order)
);

CREATE INDEX IF NOT EXISTS idx_subject_program_items_program_type_order
ON msi_v2.subject_program_items (program_id, item_type, item_order);

CREATE TABLE IF NOT EXISTS msi_v2.groups (
    id BIGSERIAL PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES msi_v2.schools(id) ON DELETE CASCADE,
    program_id BIGINT NOT NULL REFERENCES msi_v2.subject_programs(id) ON DELETE RESTRICT,
    group_name TEXT NOT NULL,
    group_code TEXT NOT NULL DEFAULT '',
    start_date DATE,
    end_date DATE,
    status TEXT NOT NULL DEFAULT 'active',
    legacy_group_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_groups_school_program
ON msi_v2.groups (school_id, program_id, group_name);

CREATE UNIQUE INDEX IF NOT EXISTS idx_groups_legacy_group_id
ON msi_v2.groups (legacy_group_id)
WHERE legacy_group_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.group_students (
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    enrollment_status TEXT NOT NULL DEFAULT 'active',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    left_at TIMESTAMPTZ,
    legacy_enrollment_id BIGINT,
    legacy_public_dashboard_id BIGINT,
    PRIMARY KEY (group_id, student_id)
);

ALTER TABLE msi_v2.group_students
ADD COLUMN IF NOT EXISTS legacy_public_dashboard_id BIGINT;

CREATE TABLE IF NOT EXISTS msi_v2.teachers (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    telegram_user_id BIGINT,
    telegram_username TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT NOT NULL DEFAULT '',
    legacy_teacher_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msi_v2.teacher_subjects (
    teacher_id BIGINT NOT NULL REFERENCES msi_v2.teachers(id) ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES msi_v2.subjects(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (teacher_id, subject_id)
);

CREATE TABLE IF NOT EXISTS msi_v2.group_teachers (
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    teacher_id BIGINT NOT NULL REFERENCES msi_v2.teachers(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'main',
    status TEXT NOT NULL DEFAULT 'active',
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, teacher_id, role)
);

CREATE TABLE IF NOT EXISTS msi_v2.group_schedule_rules (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    weekdays TEXT NOT NULL DEFAULT '',
    start_time TIME,
    end_time TIME,
    start_date DATE,
    end_date DATE,
    room TEXT NOT NULL DEFAULT '',
    online_url TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msi_v2.lesson_sessions (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    program_item_id BIGINT REFERENCES msi_v2.subject_program_items(id) ON DELETE SET NULL,
    teacher_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL,
    session_date DATE,
    start_time TIME,
    end_time TIME,
    room TEXT NOT NULL DEFAULT '',
    online_url TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'scheduled',
    source_key TEXT NOT NULL DEFAULT '',
    source_kind TEXT NOT NULL DEFAULT '',
    source_label TEXT NOT NULL DEFAULT '',
    source_topic TEXT NOT NULL DEFAULT '',
    source_order INTEGER NOT NULL DEFAULT 0,
    source_file TEXT NOT NULL DEFAULT '',
    source_sheet TEXT NOT NULL DEFAULT '',
    legacy_lesson_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lesson_sessions_group_date
ON msi_v2.lesson_sessions (group_id, session_date);

CREATE UNIQUE INDEX IF NOT EXISTS idx_lesson_sessions_legacy_lesson_id
ON msi_v2.lesson_sessions (legacy_lesson_id)
WHERE legacy_lesson_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_lesson_sessions_source_key
ON msi_v2.lesson_sessions (source_key)
WHERE source_key <> '';

CREATE INDEX IF NOT EXISTS idx_lesson_sessions_group_source_order
ON msi_v2.lesson_sessions (group_id, source_order)
WHERE source_order > 0;

CREATE TABLE IF NOT EXISTS msi_v2.attendance_records (
    id BIGSERIAL PRIMARY KEY,
    lesson_session_id BIGINT REFERENCES msi_v2.lesson_sessions(id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    attendance_status TEXT NOT NULL DEFAULT '',
    recorded_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (lesson_session_id, student_id)
);

CREATE TABLE IF NOT EXISTS msi_v2.homework_scores (
    id BIGSERIAL PRIMARY KEY,
    lesson_session_id BIGINT REFERENCES msi_v2.lesson_sessions(id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    score NUMERIC(4, 1),
    score_scale INTEGER NOT NULL DEFAULT 9,
    recorded_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (lesson_session_id, student_id)
);

CREATE TABLE IF NOT EXISTS msi_v2.exam_results (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
    program_item_id BIGINT REFERENCES msi_v2.subject_program_items(id) ON DELETE SET NULL,
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    exam_name TEXT NOT NULL DEFAULT '',
    attempt TEXT NOT NULL DEFAULT '',
    score NUMERIC(4, 1),
    score_scale INTEGER NOT NULL DEFAULT 9,
    recorded_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msi_v2.coin_events (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
    group_id BIGINT REFERENCES msi_v2.groups(id) ON DELETE SET NULL,
    amount INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msi_v2.resource_types (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER NOT NULL DEFAULT 0,
    legacy_resource_type_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_types_slug_ci
ON msi_v2.resource_types ((lower(slug)));

CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_types_legacy_id
ON msi_v2.resource_types (legacy_resource_type_id)
WHERE legacy_resource_type_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.resources (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
    resource_type_id BIGINT REFERENCES msi_v2.resource_types(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    resource_url TEXT NOT NULL DEFAULT '',
    resource_file_path TEXT NOT NULL DEFAULT '',
    thumbnail_file_path TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    legacy_resource_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_resources_legacy_id
ON msi_v2.resources (legacy_resource_id)
WHERE legacy_resource_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.resource_comments (
    id BIGSERIAL PRIMARY KEY,
    resource_id BIGINT NOT NULL REFERENCES msi_v2.resources(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_resource_comments_resource_id
ON msi_v2.resource_comments (resource_id, created_at);

CREATE TABLE IF NOT EXISTS msi_v2.announcements (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    audience TEXT NOT NULL DEFAULT 'all',
    priority TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'published',
    pinned BOOLEAN NOT NULL DEFAULT false,
    author_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    legacy_announcement_id BIGINT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_announcements_legacy_id
ON msi_v2.announcements (legacy_announcement_id)
WHERE legacy_announcement_id IS NOT NULL;

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
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_status_updated
ON msi_v2.support_tickets (status, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_support_tickets_legacy_complaint_id
ON msi_v2.support_tickets (legacy_complaint_id)
WHERE legacy_complaint_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.ticket_messages (
    id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES msi_v2.support_tickets(id) ON DELETE CASCADE,
    author_type TEXT NOT NULL,
    author_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    author_parent_id BIGINT REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msi_v2.payments (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT REFERENCES msi_v2.students(id) ON DELETE SET NULL,
    parent_id BIGINT REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
    group_id BIGINT REFERENCES msi_v2.groups(id) ON DELETE SET NULL,
    month_label TEXT NOT NULL DEFAULT '',
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'UZS',
    status TEXT NOT NULL DEFAULT 'due',
    due_date DATE,
    paid_at TIMESTAMPTZ,
    notes TEXT NOT NULL DEFAULT '',
    created_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    legacy_payment_id BIGINT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_legacy_id
ON msi_v2.payments (legacy_payment_id)
WHERE legacy_payment_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS msi_v2.chat_messages (
    id BIGSERIAL PRIMARY KEY,
    room TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_student_id TEXT NOT NULL,
    body TEXT NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    edited_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_room_id
ON msi_v2.chat_messages (room, id)
WHERE is_deleted IS FALSE;

CREATE TABLE IF NOT EXISTS msi_v2.chat_blocked_users (
    student_id TEXT PRIMARY KEY,
    blocked_by_staff_login TEXT NOT NULL DEFAULT '',
    blocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason TEXT NOT NULL DEFAULT ''
);

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
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_office_hour_slots_legacy_id
ON msi_v2.office_hour_slots (legacy_slot_id)
WHERE legacy_slot_id IS NOT NULL;

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
);

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
);

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
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidates_legacy_id
ON msi_v2.teacher_candidates (legacy_candidate_id)
WHERE legacy_candidate_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_teacher_candidate_events_candidate_created
ON msi_v2.teacher_candidate_events (candidate_id, created_at DESC);

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
);

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
);

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
);

CREATE INDEX IF NOT EXISTS idx_academy_teachers_status_updated
ON msi_v2.academy_teachers (academy_status, updated_at);

CREATE INDEX IF NOT EXISTS idx_academy_assignments_teacher_sequence
ON msi_v2.academy_lesson_assignments (academy_teacher_id, sequence_no);

CREATE INDEX IF NOT EXISTS idx_academy_assessments_teacher_created
ON msi_v2.academy_assessments (academy_teacher_id, created_at);

CREATE TABLE IF NOT EXISTS msi_v2.app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE msi_v2.msi_staff ADD COLUMN IF NOT EXISTS legacy_admin_id BIGINT;
-- Teacher login rows (role='teacher') point back to their teacher profile so the
-- teachers<->staff join is by id, not display_name (names are not unique).
ALTER TABLE msi_v2.msi_staff ADD COLUMN IF NOT EXISTS teacher_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL;
ALTER TABLE msi_v2.students ADD COLUMN IF NOT EXISTS legacy_student_row_id BIGINT;
ALTER TABLE msi_v2.parents ADD COLUMN IF NOT EXISTS legacy_parent_id BIGINT;
ALTER TABLE msi_v2.parents ADD COLUMN IF NOT EXISTS legacy_admin_id BIGINT;
ALTER TABLE msi_v2.groups ADD COLUMN IF NOT EXISTS legacy_group_id BIGINT;
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS legacy_lesson_id BIGINT;
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_key TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_kind TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_label TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_topic TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_file TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS source_sheet TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.resource_types ADD COLUMN IF NOT EXISTS legacy_resource_type_id BIGINT;
ALTER TABLE msi_v2.resources ADD COLUMN IF NOT EXISTS legacy_resource_id BIGINT;
ALTER TABLE msi_v2.announcements ADD COLUMN IF NOT EXISTS legacy_announcement_id BIGINT;
ALTER TABLE msi_v2.support_tickets ADD COLUMN IF NOT EXISTS legacy_complaint_id BIGINT;
ALTER TABLE msi_v2.payments ADD COLUMN IF NOT EXISTS legacy_payment_id BIGINT;
ALTER TABLE msi_v2.office_hour_slots ADD COLUMN IF NOT EXISTS legacy_slot_id BIGINT;
ALTER TABLE msi_v2.office_hour_bookings ADD COLUMN IF NOT EXISTS legacy_booking_id BIGINT;
ALTER TABLE msi_v2.office_hour_bookings ADD COLUMN IF NOT EXISTS student_topic_request TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.teacher_candidates ADD COLUMN IF NOT EXISTS legacy_candidate_id BIGINT;
ALTER TABLE msi_v2.account_invites ADD COLUMN IF NOT EXISTS token TEXT NOT NULL DEFAULT '';

-- Enrollment lifecycle metadata (disqualification reason/timestamp) so the admin
-- gradebook keeps the same behaviour it had on the old academic_enrollments table.
ALTER TABLE msi_v2.group_students ADD COLUMN IF NOT EXISTS disqualification_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.group_students ADD COLUMN IF NOT EXISTS disqualified_at TIMESTAMPTZ;

-- Schedule rules carry the assigned teacher and a display title, matching the old
-- academic_schedules shape used by the admin scheduling UI and conflict checks.
ALTER TABLE msi_v2.group_schedule_rules ADD COLUMN IF NOT EXISTS teacher_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE SET NULL;
ALTER TABLE msi_v2.group_schedule_rules ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '';

-- Student profile fields kept on the row so the admin Students panel and login
-- behave exactly as they did on the old denormalized students table:
--   password_plain  -> admin "view login" credential (kept in sync on change)
--   class_name / teacher_name / last_seen_at -> admin profile + activity display
ALTER TABLE msi_v2.students ADD COLUMN IF NOT EXISTS password_plain TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.students ADD COLUMN IF NOT EXISTS class_name TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.students ADD COLUMN IF NOT EXISTS teacher_name TEXT NOT NULL DEFAULT '';
ALTER TABLE msi_v2.students ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Schedule-generated calendar sessions are stored in lesson_sessions and tagged
-- with their originating schedule rule, so the admin "sessions" list can show only
-- generated calendar entries (program_item_id NULL) and keep them separate from the
-- curriculum gradebook lessons (program_item_id set).
ALTER TABLE msi_v2.lesson_sessions ADD COLUMN IF NOT EXISTS schedule_rule_id BIGINT REFERENCES msi_v2.group_schedule_rules(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_lesson_sessions_schedule_rule
ON msi_v2.lesson_sessions (schedule_rule_id) WHERE schedule_rule_id IS NOT NULL;

COMMIT;
