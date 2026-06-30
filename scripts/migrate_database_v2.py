#!/usr/bin/env python3
"""Preview or migrate current public tables into the clean msi_v2 schema.

This script is additive. It creates/fills msi_v2 tables and does not drop old
public tables. Use scripts/drop_old_database_tables_v2.sql only after the app
has been switched and verified.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_subject_programs_v2 import _apply as import_subject_programs
from shared.academics.curriculum import load_default_curricula
from shared.db import queries


SCHEMA_SQL = PROJECT_ROOT / "scripts" / "rebuild_database_v2.sql"


COUNT_SQL = {
    "staff": "SELECT count(*) AS n FROM admins WHERE lower(role) <> 'parent'",
    "schools": "SELECT count(*) AS n FROM academic_schools",
    "students": "SELECT count(*) AS n FROM students WHERE full_name NOT ILIKE '[DEMO]%'",
    "students_from_orphan_enrollments": """
        SELECT count(*) AS n
        FROM (
            SELECT DISTINCT e.student_row_id
            FROM academic_enrollments e
            LEFT JOIN students s ON s.id = e.student_row_id
            WHERE e.student_row_id IS NOT NULL AND s.id IS NULL
        ) x
    """,
    "parents": """
        SELECT (
            (SELECT count(*) FROM parents WHERE full_name NOT ILIKE '[DEMO]%') +
            (SELECT count(*) FROM admins WHERE lower(role) = 'parent' AND login NOT ILIKE 'demo_%')
        ) AS n
    """,
    "parent_links": """
        SELECT (
            (SELECT count(*) FROM parent_student_links) +
            (SELECT count(*) FROM parent_children)
        ) AS n
    """,
    "groups": "SELECT count(*) AS n FROM academic_groups",
    "group_students": "SELECT count(*) AS n FROM academic_enrollments WHERE student_row_id IS NOT NULL",
    "teachers": "SELECT count(*) AS n FROM teachers WHERE full_name NOT ILIKE '[DEMO]%'",
    "lessons": "SELECT count(*) AS n FROM academic_lessons",
    "attendance": "SELECT count(*) AS n FROM academic_attendance_records",
    "homework": "SELECT count(*) AS n FROM academic_homework_scores",
    "exams": "SELECT count(*) AS n FROM academic_exam_results",
    "resources": "SELECT count(*) AS n FROM resources WHERE title NOT ILIKE '[DEMO]%'",
    "announcements": "SELECT count(*) AS n FROM announcements WHERE title NOT ILIKE '[DEMO]%'",
    "tickets": "SELECT count(*) AS n FROM parent_complaints WHERE topic NOT ILIKE '[DEMO]%' AND message NOT ILIKE '[DEMO]%'",
    "payments": "SELECT count(*) AS n FROM student_payments",
    "office_slots": "SELECT count(*) AS n FROM office_hour_availability",
    "office_bookings": "SELECT count(*) AS n FROM office_hour_bookings",
    "candidates": "SELECT count(*) AS n FROM teacher_candidates WHERE full_name NOT ILIKE '[DEMO]%'",
}


MIGRATION_STEPS: tuple[tuple[str, str], ...] = (
    (
        "telegram_accounts",
        """
        INSERT INTO msi_v2.telegram_accounts (
            telegram_user_id, username, first_name, last_name, linked_entity_type,
            linked_entity_id, created_at, updated_at
        )
        SELECT telegram_user_id, COALESCE(username, ''), COALESCE(first_name, ''),
               COALESCE(last_name, ''), '', NULL, now(), now()
        FROM bot_users
        WHERE telegram_user_id IS NOT NULL
        ON CONFLICT (telegram_user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            updated_at = excluded.updated_at
        """,
    ),
    (
        "schools",
        """
        INSERT INTO msi_v2.schools (school_key, school_name, created_at, updated_at)
        SELECT code, name, now(), now()
        FROM academic_schools old
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.schools s WHERE lower(s.school_key) = lower(old.code)
        )
        """,
    ),
    (
        "schools_from_students",
        """
        INSERT INTO msi_v2.schools (school_key, school_name, created_at, updated_at)
        SELECT DISTINCT school_key, COALESCE(NULLIF(school_name, ''), school_key), now(), now()
        FROM students old
        WHERE COALESCE(school_key, '') <> ''
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.schools s WHERE lower(s.school_key) = lower(old.school_key)
          )
        """,
    ),
    (
        "staff",
        """
        INSERT INTO msi_v2.msi_staff (
            login, password_hash, display_name, phone, telegram_user_id,
            telegram_username, role, status, legacy_admin_id, created_at, updated_at
        )
        SELECT login, password_hash,
               COALESCE(NULLIF(display_name, ''), login),
               COALESCE(phone, ''),
               telegram_user_id,
               COALESCE(telegram_username, ''),
               role,
               CASE WHEN COALESCE(disabled, 0) = 1 THEN 'disabled' ELSE 'active' END,
               id,
               COALESCE(NULLIF(created_at, '')::timestamptz, now()),
               now()
        FROM admins old
        WHERE lower(role) <> 'parent'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.msi_staff s WHERE s.legacy_admin_id = old.id
          )
        """,
    ),
    (
        "students",
        """
        INSERT INTO msi_v2.students (
            student_code, full_name, school_id, telegram_user_id, photo_url,
            profile_description, status, legacy_student_row_id,
            password_plain, class_name, teacher_name, last_seen_at, created_at, updated_at
        )
        SELECT old.student_id,
               old.full_name,
               school.id,
               old.telegram_user_id,
               COALESCE(old.photo_url, ''),
               COALESCE(old.profile_description, ''),
               'active',
               old.id,
               COALESCE(old.password, ''),
               COALESCE(old.class_name, ''),
               COALESCE(old.teacher_name, ''),
               CASE WHEN COALESCE(old.last_seen_at, '') <> '' THEN old.last_seen_at::timestamptz ELSE NULL END,
               now(),
               now()
        FROM students old
        LEFT JOIN msi_v2.schools school ON lower(school.school_key) = lower(old.school_key)
        WHERE old.full_name NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.students s WHERE s.legacy_student_row_id = old.id
          )
        """,
    ),
    (
        "students_from_orphan_enrollments",
        """
        INSERT INTO msi_v2.students (
            student_code, full_name, school_id, telegram_user_id, photo_url,
            profile_description, status, legacy_public_dashboard_id,
            legacy_student_row_id, created_at, updated_at
        )
        SELECT DISTINCT ON (old.student_row_id)
               'MIG' || old.student_row_id::text,
               old.full_name,
               school.id,
               NULL,
               '',
               'Recovered from academic enrollment during v2 migration.',
               COALESCE(NULLIF(old.enrollment_status, ''), CASE WHEN old.active = 1 THEN 'active' ELSE 'inactive' END),
               old.public_dashboard_id,
               old.student_row_id,
               now(),
               now()
        FROM academic_enrollments old
        JOIN academic_schools os ON os.id = old.school_id
        LEFT JOIN students existing ON existing.id = old.student_row_id
        LEFT JOIN msi_v2.schools school ON lower(school.school_key) = lower(os.code)
        WHERE old.student_row_id IS NOT NULL
          AND existing.id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.students s WHERE s.legacy_student_row_id = old.student_row_id
          )
        ORDER BY old.student_row_id, old.id
        """,
    ),
    (
        "student_auth",
        """
        INSERT INTO msi_v2.student_auth (student_id, password_hash, must_change_password, updated_at)
        SELECT ns.id, old.password_hash, false, now()
        FROM student_auth old
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        ON CONFLICT (student_id) DO UPDATE SET
            password_hash = excluded.password_hash,
            updated_at = excluded.updated_at
        """,
    ),
    (
        "student_telegram_accounts",
        """
        INSERT INTO msi_v2.telegram_accounts (
            telegram_user_id, username, first_name, last_name, linked_entity_type,
            linked_entity_id, created_at, updated_at
        )
        SELECT old.telegram_user_id, '', '', '', 'student', ns.id, now(), now()
        FROM students old
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.id
        WHERE old.telegram_user_id IS NOT NULL
        ON CONFLICT (telegram_user_id) DO UPDATE SET
            linked_entity_type = 'student',
            linked_entity_id = excluded.linked_entity_id,
            updated_at = excluded.updated_at
        """,
    ),
    (
        "student_telegram_links",
        """
        INSERT INTO msi_v2.student_telegram_links (student_id, telegram_user_id, status, linked_at)
        SELECT ns.id, old.telegram_user_id, 'active', now()
        FROM students old
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.id
        WHERE old.telegram_user_id IS NOT NULL
        ON CONFLICT (student_id, telegram_user_id) DO UPDATE SET status = 'active'
        """,
    ),
    (
        "parents_table",
        """
        INSERT INTO msi_v2.parents (
            display_name, phone, telegram_user_id, telegram_username,
            preferred_language, status, legacy_parent_id, created_at, updated_at
        )
        SELECT COALESCE(NULLIF(full_name, ''), telegram_username, phone, 'Parent'),
               COALESCE(phone, ''),
               telegram_user_id,
               COALESCE(telegram_username, ''),
               'ru',
               'active',
               id,
               now(),
               now()
        FROM parents old
        WHERE full_name NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.parents p WHERE p.legacy_parent_id = old.id
          )
        """,
    ),
    (
        "parents_from_legacy_admins",
        """
        INSERT INTO msi_v2.parents (
            display_name, phone, telegram_user_id, telegram_username,
            preferred_language, status, legacy_admin_id, created_at, updated_at
        )
        SELECT COALESCE(NULLIF(display_name, ''), login),
               COALESCE(phone, ''),
               telegram_user_id,
               COALESCE(telegram_username, ''),
               'ru',
               CASE WHEN COALESCE(disabled, 0) = 1 THEN 'disabled' ELSE 'active' END,
               id,
               now(),
               now()
        FROM admins old
        WHERE lower(role) = 'parent'
          AND login NOT ILIKE 'demo_%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.parents p WHERE p.legacy_admin_id = old.id
          )
        """,
    ),
    (
        "parent_links_table",
        """
        INSERT INTO msi_v2.parent_student_links (parent_id, student_id, relationship, status, created_at)
        SELECT np.id, ns.id, 'parent', 'active', now()
        FROM parent_student_links old
        JOIN msi_v2.parents np ON np.legacy_parent_id = old.parent_id
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        ON CONFLICT (parent_id, student_id) DO UPDATE SET status = 'active'
        """,
    ),
    (
        "parent_links_legacy_admins",
        """
        INSERT INTO msi_v2.parent_student_links (parent_id, student_id, relationship, status, created_at)
        SELECT np.id, ns.id, 'parent', 'active', now()
        FROM parent_children old
        JOIN msi_v2.parents np ON np.legacy_admin_id = old.parent_admin_id
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        ON CONFLICT (parent_id, student_id) DO UPDATE SET status = 'active'
        """,
    ),
    (
        "groups",
        """
        INSERT INTO msi_v2.groups (
            school_id, program_id, group_name, group_code, status,
            legacy_group_id, created_at, updated_at
        )
        SELECT ns.id,
               sp.id,
               old.name,
               COALESCE(old.code, ''),
               'active',
               old.id,
               now(),
               now()
        FROM academic_groups old
        JOIN academic_schools os ON os.id = old.school_id
        JOIN msi_v2.schools ns ON lower(ns.school_key) = lower(os.code)
        JOIN academic_subjects osub ON osub.id = old.subject_id
        JOIN msi_v2.subjects sub ON lower(sub.subject_key) = lower(osub.key)
        JOIN msi_v2.subject_programs sp ON sp.subject_id = sub.id AND sp.status = 'active'
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.groups g WHERE g.legacy_group_id = old.id
        )
        """,
    ),
    (
        "group_students",
        """
        INSERT INTO msi_v2.group_students (
            group_id, student_id, enrollment_status, joined_at,
            legacy_enrollment_id, legacy_public_dashboard_id
        )
        SELECT ng.id,
               ns.id,
               COALESCE(NULLIF(old.enrollment_status, ''), CASE WHEN old.active = 1 THEN 'active' ELSE 'inactive' END),
               now(),
               old.id,
               old.public_dashboard_id
        FROM academic_enrollments old
        JOIN msi_v2.groups ng ON ng.legacy_group_id = old.group_id
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        WHERE old.student_row_id IS NOT NULL
        ON CONFLICT (group_id, student_id) DO UPDATE SET
            enrollment_status = excluded.enrollment_status,
            legacy_enrollment_id = excluded.legacy_enrollment_id,
            legacy_public_dashboard_id = excluded.legacy_public_dashboard_id
        """,
    ),
    (
        "teachers",
        """
        INSERT INTO msi_v2.teachers (
            full_name, status, notes, legacy_teacher_id, created_at, updated_at
        )
        SELECT full_name,
               'active',
               COALESCE(promotion_notes, ''),
               id,
               now(),
               now()
        FROM teachers old
        WHERE full_name NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.teachers t WHERE t.legacy_teacher_id = old.id
          )
        """,
    ),
    (
        "group_teachers",
        """
        INSERT INTO msi_v2.group_teachers (group_id, teacher_id, role, status, assigned_at)
        SELECT DISTINCT ng.id, nt.id, 'main', 'active', now()
        FROM teachers old
        JOIN msi_v2.teachers nt ON nt.legacy_teacher_id = old.id
        JOIN msi_v2.groups ng ON lower(ng.group_name) = lower(old.assigned_group)
        ON CONFLICT (group_id, teacher_id, role) DO UPDATE SET status = 'active'
        """,
    ),
    (
        "teacher_subjects",
        """
        INSERT INTO msi_v2.teacher_subjects (teacher_id, subject_id, status, created_at)
        SELECT DISTINCT gt.teacher_id, sp.subject_id, 'active', now()
        FROM msi_v2.group_teachers gt
        JOIN msi_v2.groups g ON g.id = gt.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        ON CONFLICT (teacher_id, subject_id) DO UPDATE SET status = 'active'
        """,
    ),
    (
        "lesson_sessions",
        """
        INSERT INTO msi_v2.lesson_sessions (
            group_id, program_item_id, session_date, status, legacy_lesson_id,
            created_at, updated_at
        )
        SELECT ng.id,
               spi.id,
               CASE
                   WHEN old.lesson_date ~ '^\\d{1,2}/\\d{1,2}/\\d{4}$'
                   THEN to_date(old.lesson_date, 'DD/MM/YYYY')
                   ELSE NULL
               END,
               'completed',
               old.id,
               now(),
               now()
        FROM academic_lessons old
        JOIN msi_v2.groups ng ON ng.legacy_group_id = old.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = ng.program_id
        LEFT JOIN msi_v2.subject_program_items spi
               ON spi.program_id = sp.id AND spi.item_order = old.lesson_order
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.lesson_sessions ls WHERE ls.legacy_lesson_id = old.id
        )
        """,
    ),
    (
        "attendance_records",
        """
        INSERT INTO msi_v2.attendance_records (
            lesson_session_id, group_id, student_id, attendance_status,
            created_at, updated_at
        )
        SELECT ls.id,
               gs.group_id,
               gs.student_id,
               COALESCE(NULLIF(old.status, ''), NULLIF(old.attendance_type, ''), 'unknown'),
               now(),
               now()
        FROM academic_attendance_records old
        JOIN msi_v2.group_students gs ON gs.legacy_enrollment_id = old.enrollment_id
        JOIN msi_v2.lesson_sessions ls ON ls.group_id = gs.group_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE spi.item_order = old.lesson_order
        ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
            attendance_status = excluded.attendance_status,
            updated_at = excluded.updated_at
        """,
    ),
    (
        "homework_scores",
        """
        INSERT INTO msi_v2.homework_scores (
            lesson_session_id, group_id, student_id, score, score_scale,
            created_at, updated_at
        )
        SELECT ls.id,
               gs.group_id,
               gs.student_id,
               old.score,
               9,
               now(),
               now()
        FROM academic_homework_scores old
        JOIN msi_v2.group_students gs ON gs.legacy_enrollment_id = old.enrollment_id
        JOIN msi_v2.lesson_sessions ls ON ls.group_id = gs.group_id
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE spi.item_order = old.lesson_order
        ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
            score = excluded.score,
            updated_at = excluded.updated_at
        """,
    ),
    (
        "exam_results",
        """
        INSERT INTO msi_v2.exam_results (
            group_id, program_item_id, student_id, exam_name, attempt, score,
            score_scale, created_at, updated_at
        )
        SELECT gs.group_id,
               spi.id,
               gs.student_id,
               COALESCE(NULLIF(old.exam_name, ''), old.label),
               COALESCE(old.attempt, ''),
               old.score,
               9,
               now(),
               now()
        FROM academic_exam_results old
        JOIN msi_v2.group_students gs ON gs.legacy_enrollment_id = old.enrollment_id
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        LEFT JOIN msi_v2.subject_program_items spi
               ON spi.program_id = sp.id
              AND spi.item_type = 'exam'
              AND lower(spi.title) = lower(old.exam_name)
        WHERE NOT EXISTS (
            SELECT 1
            FROM msi_v2.exam_results er
            WHERE er.group_id = gs.group_id
              AND er.student_id = gs.student_id
              AND lower(er.exam_name) = lower(COALESCE(NULLIF(old.exam_name, ''), old.label))
              AND lower(er.attempt) = lower(COALESCE(old.attempt, ''))
              AND COALESCE(er.score, -1) = COALESCE(old.score, -1)
        )
        """,
    ),
    (
        "coin_events",
        """
        INSERT INTO msi_v2.coin_events (student_id, group_id, amount, source, note, occurred_at, created_at)
        SELECT gs.student_id, gs.group_id, old.amount, COALESCE(old.source, ''), '', now(), now()
        FROM academic_coin_events old
        JOIN msi_v2.group_students gs ON gs.legacy_enrollment_id = old.enrollment_id
        """,
    ),
    (
        "resource_types",
        """
        INSERT INTO msi_v2.resource_types (
            name, slug, is_active, display_order, legacy_resource_type_id, created_at, updated_at
        )
        SELECT name, slug, (is_active = 1), display_order, id, now(), now()
        FROM resource_types old
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.resource_types rt WHERE rt.legacy_resource_type_id = old.id
        )
        """,
    ),
    (
        "resources",
        """
        INSERT INTO msi_v2.resources (
            subject_id, resource_type_id, title, description, resource_url,
            resource_file_path, thumbnail_file_path, is_active, legacy_resource_id,
            created_at, updated_at
        )
        SELECT sub.id,
               rt.id,
               old.title,
               COALESCE(old.description, ''),
               COALESCE(old.resource_url, ''),
               COALESCE(old.resource_file_path, ''),
               COALESCE(old.thumbnail_file_path, ''),
               old.is_active = 1,
               old.id,
               now(),
               now()
        FROM resources old
        LEFT JOIN msi_v2.subjects sub ON lower(sub.subject_key) = lower(old.subject_key)
        LEFT JOIN msi_v2.resource_types rt ON rt.legacy_resource_type_id = old.resource_type_id
        WHERE old.title NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.resources r WHERE r.legacy_resource_id = old.id
          )
        """,
    ),
    (
        "announcements",
        """
        INSERT INTO msi_v2.announcements (
            title, body, audience, priority, status, pinned, legacy_announcement_id,
            published_at, created_at, updated_at
        )
        SELECT title, body, audience, priority, status, pinned = 1, id,
               CASE WHEN COALESCE(published_at, '') <> '' THEN published_at::timestamptz ELSE NULL END,
               now(),
               now()
        FROM announcements old
        WHERE title NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.announcements a WHERE a.legacy_announcement_id = old.id
          )
        """,
    ),
    (
        "support_tickets",
        """
        INSERT INTO msi_v2.support_tickets (
            parent_id, student_id, category, topic, status, legacy_complaint_id,
            created_at, updated_at, resolved_at
        )
        SELECT np.id,
               ns.id,
               COALESCE(old.category, 'other'),
               COALESCE(NULLIF(old.topic, ''), old.category, 'Support request'),
               COALESCE(old.status, 'new'),
               old.id,
               now(),
               now(),
               CASE WHEN COALESCE(old.resolved_at, '') <> '' THEN old.resolved_at::timestamptz ELSE NULL END
        FROM parent_complaints old
        LEFT JOIN msi_v2.parents np
               ON np.legacy_admin_id = old.parent_admin_id OR np.legacy_parent_id = old.parent_id
        LEFT JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        WHERE old.topic NOT ILIKE '[DEMO]%'
          AND old.message NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.support_tickets t WHERE t.legacy_complaint_id = old.id
          )
        """,
    ),
    (
        "ticket_initial_messages",
        """
        INSERT INTO msi_v2.ticket_messages (ticket_id, author_type, author_parent_id, body, created_at)
        SELECT nt.id, 'parent', nt.parent_id, old.message, nt.created_at
        FROM parent_complaints old
        JOIN msi_v2.support_tickets nt ON nt.legacy_complaint_id = old.id
        WHERE COALESCE(old.message, '') <> ''
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.ticket_messages tm
              WHERE tm.ticket_id = nt.id AND tm.author_type = 'parent' AND tm.body = old.message
          )
        """,
    ),
    (
        "ticket_messages",
        """
        INSERT INTO msi_v2.ticket_messages (ticket_id, author_type, body, created_at)
        SELECT nt.id, old.author_role, old.body,
               CASE WHEN COALESCE(old.created_at, '') <> '' THEN old.created_at::timestamptz ELSE now() END
        FROM parent_complaint_messages old
        JOIN msi_v2.support_tickets nt ON nt.legacy_complaint_id = old.complaint_id
        WHERE COALESCE(old.body, '') <> ''
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.ticket_messages tm
              WHERE tm.ticket_id = nt.id AND tm.author_type = old.author_role AND tm.body = old.body
          )
        """,
    ),
    (
        "payments",
        """
        INSERT INTO msi_v2.payments (
            student_id, group_id, month_label, amount, currency, status,
            due_date, paid_at, notes, legacy_payment_id, created_at, updated_at
        )
        SELECT ns.id,
               gs.group_id,
               COALESCE(old.month_label, ''),
               old.amount,
               COALESCE(old.currency, 'UZS'),
               COALESCE(old.status, 'due'),
               CASE WHEN old.due_date ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN old.due_date::date ELSE NULL END,
               CASE WHEN COALESCE(old.paid_at, '') <> '' THEN old.paid_at::timestamptz ELSE NULL END,
               COALESCE(old.notes, ''),
               old.id,
               now(),
               now()
        FROM student_payments old
        LEFT JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        LEFT JOIN msi_v2.group_students gs ON gs.student_id = ns.id
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.payments p WHERE p.legacy_payment_id = old.id
        )
        """,
    ),
    (
        "office_hour_slots",
        """
        INSERT INTO msi_v2.office_hour_slots (
            teacher_id, subject_id, starts_at, ends_at, slot_minutes, capacity,
            room, planned_topic, status, created_at, legacy_slot_id
        )
        SELECT nt.id,
               sub.id,
               old.starts_at::timestamptz,
               old.ends_at::timestamptz,
               old.slot_minutes,
               old.capacity,
               COALESCE(old.room, ''),
               COALESCE(old.planned_topic, ''),
               COALESCE(old.status, 'open'),
               now(),
               old.id
        FROM office_hour_availability old
        LEFT JOIN msi_v2.teachers nt ON nt.legacy_teacher_id = old.teacher_id
        LEFT JOIN msi_v2.subjects sub ON sub.id = old.subject_id
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.office_hour_slots s WHERE s.legacy_slot_id = old.id
        )
        """,
    ),
    (
        "office_hour_bookings",
        """
        INSERT INTO msi_v2.office_hour_bookings (
            slot_id, student_id, subject_id, status, student_note, student_topic_request, teacher_note,
            created_at, updated_at, canceled_at, legacy_booking_id
        )
        SELECT slot.id,
               ns.id,
               sub.id,
               COALESCE(old.status, 'booked'),
               COALESCE(old.student_note, ''),
               COALESCE(old.student_topic_request, ''),
               COALESCE(old.teacher_note, ''),
               now(),
               now(),
               NULL,
               old.id
        FROM office_hour_bookings old
        JOIN msi_v2.office_hour_slots slot ON slot.legacy_slot_id = old.availability_id
        JOIN msi_v2.students ns ON ns.legacy_student_row_id = old.student_row_id
        LEFT JOIN msi_v2.subjects sub ON sub.id = old.subject_id
        WHERE NOT EXISTS (
            SELECT 1 FROM msi_v2.office_hour_bookings b WHERE b.legacy_booking_id = old.id
        )
        """,
    ),
    (
        "teacher_candidates",
        """
        INSERT INTO msi_v2.teacher_candidates (
            full_name, phone, telegram_username, subject_id, source, status,
            notes, legacy_candidate_id, created_at, updated_at
        )
        SELECT old.full_name,
               COALESCE(old.phone, ''),
               COALESCE(old.telegram_username, ''),
               sub.id,
               COALESCE(old.source, ''),
               COALESCE(old.status, 'new'),
               COALESCE(old.notes, ''),
               old.id,
               now(),
               now()
        FROM teacher_candidates old
        LEFT JOIN msi_v2.subjects sub
               ON lower(sub.subject_name) = lower(old.subject)
               OR lower(sub.subject_short) = lower(old.subject)
        WHERE old.full_name NOT ILIKE '[DEMO]%'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.teacher_candidates c WHERE c.legacy_candidate_id = old.id
          )
        """,
    ),
)


def _ensure_schema(conn) -> None:
    conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))


def _count(conn, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row["n"] or 0)


def _preview(conn) -> None:
    print("Current public schema rows that can feed msi_v2")
    for name, sql in COUNT_SQL.items():
        print(f"- {name}: {_count(conn, sql)}")

    exists = conn.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.schemata WHERE schema_name = 'msi_v2'
        ) AS ok
        """
    ).fetchone()["ok"]
    if not exists:
        print()
        print("msi_v2 does not exist yet. Run with --apply to create and migrate.")
        return

    print()
    print("Current msi_v2 row counts")
    rows = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'msi_v2' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    ).fetchall()
    for row in rows:
        table = row["table_name"]
        print(f"- {table}: {_count(conn, f'SELECT count(*) AS n FROM msi_v2.{table}')}")

    health_rows = conn.execute(
        """
        WITH exam_dupes AS (
            SELECT group_id, student_id, lower(exam_name) AS exam_name,
                   lower(attempt) AS attempt, score, count(*) AS copies
            FROM msi_v2.exam_results
            GROUP BY group_id, student_id, lower(exam_name), lower(attempt), score
            HAVING count(*) > 1
        )
        SELECT
            (
                SELECT count(*)
                FROM (
                    SELECT DISTINCT ls.id, gs.student_id
                    FROM academic_attendance_records old
                    JOIN msi_v2.group_students gs
                         ON gs.legacy_enrollment_id = old.enrollment_id
                    JOIN msi_v2.lesson_sessions ls ON ls.group_id = gs.group_id
                    JOIN msi_v2.subject_program_items spi
                         ON spi.id = ls.program_item_id
                        AND spi.item_order = old.lesson_order
                ) clean_keys
            ) AS attendance_clean_keys,
            (SELECT count(*) FROM msi_v2.attendance_records) AS attendance_rows,
            (
                SELECT count(*)
                FROM (
                    SELECT DISTINCT ls.id, gs.student_id
                    FROM academic_homework_scores old
                    JOIN msi_v2.group_students gs
                         ON gs.legacy_enrollment_id = old.enrollment_id
                    JOIN msi_v2.lesson_sessions ls ON ls.group_id = gs.group_id
                    JOIN msi_v2.subject_program_items spi
                         ON spi.id = ls.program_item_id
                        AND spi.item_order = old.lesson_order
                ) clean_keys
            ) AS homework_clean_keys,
            (SELECT count(*) FROM msi_v2.homework_scores) AS homework_rows,
            (
                SELECT count(*)
                FROM (
                    SELECT DISTINCT gs.group_id, gs.student_id,
                           lower(COALESCE(NULLIF(old.exam_name, ''), old.label)) AS exam_name,
                           lower(COALESCE(old.attempt, '')) AS attempt,
                           old.score
                    FROM academic_exam_results old
                    JOIN msi_v2.group_students gs
                         ON gs.legacy_enrollment_id = old.enrollment_id
                ) clean_keys
            ) AS exam_clean_keys,
            (
                SELECT count(*)
                FROM (
                    SELECT DISTINCT group_id, student_id, lower(exam_name),
                           lower(attempt), score
                    FROM msi_v2.exam_results
                ) clean_keys
            ) AS exam_distinct_rows,
            COALESCE((SELECT sum(copies - 1)::int FROM exam_dupes), 0) AS exam_duplicate_rows
        """
    ).fetchone()

    print()
    print("Migration health")
    print(
        "- attendance clean keys / rows: "
        f"{health_rows['attendance_clean_keys']} / {health_rows['attendance_rows']}"
    )
    print(
        "- homework clean keys / rows: "
        f"{health_rows['homework_clean_keys']} / {health_rows['homework_rows']}"
    )
    print(
        "- exam distinct source keys / distinct rows: "
        f"{health_rows['exam_clean_keys']} / {health_rows['exam_distinct_rows']}"
    )
    print(f"- exam duplicate rows in msi_v2: {health_rows['exam_duplicate_rows']}")


def _apply(conn) -> None:
    _ensure_schema(conn)
    for name, sql in MIGRATION_STEPS:
        print(f"Applying {name}...")
        conn.execute(sql)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--academic-year", default="2025-26")
    args = parser.parse_args()

    with queries.connect_auth_db() as conn:
        _preview(conn)
        if not args.apply:
            conn.rollback()
            print()
            print("READ-ONLY PREVIEW COMPLETE. No database values were changed.")
            return 0

        print()
        print("Creating schema and importing official subject programs...")
        conn.rollback()

    # Importer owns its own transaction and commits the official programs.
    import_subject_programs(load_default_curricula(), academic_year=args.academic_year)

    with queries.connect_auth_db() as conn:
        _apply(conn)
        conn.commit()
        print()
        print("APPLIED: migrated current public tables into msi_v2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
