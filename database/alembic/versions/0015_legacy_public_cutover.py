"""import the legacy public database into the canonical msi_v2 schema

Revision ID: 0015_legacy_public_cutover
Revises: 0014_hr_decision_queue
Create Date: 2026-07-15

The Railway database originally used the legacy ``public`` tables.  The clean
FastAPI application reads only ``msi_v2``.  This migration performs the missing
cutover without dropping or altering any legacy table, so the pre-cutover dump
and the original rows remain available for rollback and reconciliation.
"""

from __future__ import annotations

import re
from typing import Any

from alembic import op
from sqlalchemy import text
from werkzeug.security import generate_password_hash


revision = "0015_legacy_public_cutover"
down_revision = "0014_hr_decision_queue"
branch_labels = None
depends_on = None


_TEACHER_CODE_RE = re.compile(r"^TCH[0-9]{4}$", re.IGNORECASE)


def _one(bind, sql: str, **params: Any) -> dict[str, Any] | None:
    row = bind.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _all(bind, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in bind.execute(text(sql), params).mappings().all()]


def _legacy_table_exists(bind, table_name: str) -> bool:
    row = _one(
        bind,
        """
        SELECT to_regclass(:qualified_name) IS NOT NULL AS exists
        """,
        qualified_name=f"public.{table_name}",
    )
    return bool(row and row["exists"])


def _import_schools_and_subjects(bind) -> None:
    bind.execute(
        text(
            """
            INSERT INTO msi_v2.schools (
                school_key, school_name, status, created_at, updated_at
            )
            SELECT
                lower(btrim(school_key)),
                max(COALESCE(NULLIF(btrim(school_name), ''), btrim(school_key))),
                'active', now(), now()
            FROM public.students
            WHERE COALESCE(btrim(school_key), '') <> ''
            GROUP BY lower(btrim(school_key))
            ON CONFLICT ((lower(school_key))) DO UPDATE SET
                school_name = excluded.school_name,
                status = 'active',
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            WITH legacy_subjects AS (
                SELECT subjects AS subject_name, ''::text AS subject_short
                FROM public.students
                UNION ALL
                SELECT subject_name, COALESCE(subject_short, '')
                FROM public.subject_summaries
                UNION ALL
                SELECT subject_name, ''::text
                FROM public.lesson_catalog
                UNION ALL
                SELECT subject_name, ''::text
                FROM public.resources
            ), normalized AS (
                SELECT
                    trim(both '-' FROM lower(regexp_replace(
                        btrim(subject_name), '[^a-zA-Z0-9]+', '-', 'g'
                    ))) AS subject_key,
                    max(btrim(subject_name)) AS subject_name,
                    max(COALESCE(NULLIF(btrim(subject_short), ''), '')) AS subject_short
                FROM legacy_subjects
                WHERE COALESCE(btrim(subject_name), '') <> ''
                GROUP BY trim(both '-' FROM lower(regexp_replace(
                    btrim(subject_name), '[^a-zA-Z0-9]+', '-', 'g'
                )))
            )
            INSERT INTO msi_v2.subjects (
                subject_key, subject_name, subject_short, status, created_at, updated_at
            )
            SELECT subject_key, subject_name, subject_short, 'active', now(), now()
            FROM normalized
            WHERE subject_key <> ''
            ON CONFLICT ((lower(subject_key))) DO UPDATE SET
                subject_name = excluded.subject_name,
                subject_short = CASE
                    WHEN excluded.subject_short <> '' THEN excluded.subject_short
                    ELSE msi_v2.subjects.subject_short
                END,
                status = 'active',
                updated_at = now()
            """
        )
    )


def _import_students(bind) -> None:
    bind.execute(
        text(
            """
            INSERT INTO msi_v2.students (
                student_code, full_name, school_id, telegram_user_id,
                photo_url, profile_description, status,
                legacy_public_dashboard_id, legacy_student_row_id,
                class_name, teacher_name, created_at, updated_at
            )
            SELECT
                upper(btrim(legacy.student_id)),
                COALESCE(NULLIF(btrim(legacy.full_name), ''), upper(btrim(legacy.student_id))),
                school.id,
                CASE WHEN legacy.telegram_user_id > 0 THEN legacy.telegram_user_id END,
                COALESCE(legacy.photo_url, ''),
                COALESCE(legacy.profile_description, ''),
                'active', legacy.id, legacy.id,
                COALESCE(legacy.class_name, ''),
                COALESCE(legacy.teacher_name, ''),
                now(), now()
            FROM public.students legacy
            LEFT JOIN msi_v2.schools school
              ON lower(school.school_key) = lower(btrim(legacy.school_key))
            WHERE COALESCE(btrim(legacy.student_id), '') <> ''
            ON CONFLICT ((upper(student_code))) DO UPDATE SET
                full_name = excluded.full_name,
                school_id = excluded.school_id,
                telegram_user_id = COALESCE(
                    msi_v2.students.telegram_user_id,
                    excluded.telegram_user_id
                ),
                photo_url = excluded.photo_url,
                profile_description = excluded.profile_description,
                status = 'active',
                legacy_public_dashboard_id = excluded.legacy_public_dashboard_id,
                legacy_student_row_id = excluded.legacy_student_row_id,
                class_name = excluded.class_name,
                teacher_name = excluded.teacher_name,
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name,
                legacy_source_table, legacy_source_id,
                must_change_password, password_changed_at, session_version,
                created_at, updated_at
            )
            SELECT
                student.student_code,
                auth.password_hash,
                'student', 'active', student.full_name,
                'students', student.id,
                false, now(), 1, now(), now()
            FROM public.students legacy
            JOIN msi_v2.students student
              ON student.legacy_student_row_id = legacy.id
            JOIN public.student_auth auth
              ON auth.student_row_id = legacy.id
            WHERE COALESCE(btrim(auth.password_hash), '') <> ''
            ON CONFLICT ((lower(btrim(login)))) WHERE login IS NOT NULL DO UPDATE SET
                password_hash = CASE
                    WHEN COALESCE(btrim(msi_v2.accounts.password_hash), '') <> ''
                    THEN msi_v2.accounts.password_hash
                    ELSE excluded.password_hash
                END,
                role = 'student',
                status = 'active',
                full_name = excluded.full_name,
                legacy_source_table = excluded.legacy_source_table,
                legacy_source_id = excluded.legacy_source_id,
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.student_profiles (
                account_id, student_id, school_id, student_code, status,
                created_at, updated_at
            )
            SELECT
                account.id, student.id, student.school_id,
                student.student_code, 'active', now(), now()
            FROM msi_v2.students student
            JOIN msi_v2.accounts account
              ON account.role = 'student'
             AND lower(btrim(account.login)) = lower(btrim(student.student_code))
            WHERE student.legacy_student_row_id IS NOT NULL
            ON CONFLICT (student_id) WHERE student_id IS NOT NULL DO UPDATE SET
                account_id = excluded.account_id,
                school_id = excluded.school_id,
                student_code = excluded.student_code,
                status = 'active',
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.account_telegram_links (
                account_id, telegram_user_id, linked_at, status
            )
            SELECT account.id, legacy.telegram_user_id, now(), 'active'
            FROM public.students legacy
            JOIN msi_v2.students student
              ON student.legacy_student_row_id = legacy.id
            JOIN msi_v2.student_profiles profile ON profile.student_id = student.id
            JOIN msi_v2.accounts account ON account.id = profile.account_id
            WHERE legacy.telegram_user_id > 0
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                account_id = excluded.account_id,
                status = 'active'
            """
        )
    )


def _import_admins(bind) -> None:
    if not _legacy_table_exists(bind, "admins"):
        return

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.msi_staff (
                login, password_hash, display_name, role, status,
                telegram_user_id, legacy_admin_id, created_at, updated_at
            )
            SELECT
                btrim(login), password_hash, btrim(login),
                CASE WHEN COALESCE(is_owner, 0) = 1 THEN 'owner' ELSE 'admin' END,
                'active',
                CASE WHEN telegram_user_id > 0 THEN telegram_user_id END,
                id, now(), now()
            FROM public.admins
            WHERE COALESCE(btrim(login), '') <> ''
              AND COALESCE(btrim(password_hash), '') <> ''
            ON CONFLICT ((lower(login))) DO UPDATE SET
                password_hash = CASE
                    WHEN COALESCE(btrim(msi_v2.msi_staff.password_hash), '') <> ''
                    THEN msi_v2.msi_staff.password_hash
                    ELSE excluded.password_hash
                END,
                display_name = excluded.display_name,
                role = excluded.role,
                status = 'active',
                telegram_user_id = COALESCE(
                    msi_v2.msi_staff.telegram_user_id,
                    excluded.telegram_user_id
                ),
                legacy_admin_id = excluded.legacy_admin_id,
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name,
                legacy_source_table, legacy_source_id,
                must_change_password, password_changed_at, session_version,
                created_at, updated_at
            )
            SELECT
                staff.login, staff.password_hash, 'system_admin', 'active',
                staff.display_name, 'msi_staff', staff.id,
                false, now(), 1, now(), now()
            FROM msi_v2.msi_staff staff
            WHERE staff.legacy_admin_id IS NOT NULL
            ON CONFLICT ((lower(btrim(login)))) WHERE login IS NOT NULL DO UPDATE SET
                password_hash = CASE
                    WHEN COALESCE(btrim(msi_v2.accounts.password_hash), '') <> ''
                    THEN msi_v2.accounts.password_hash
                    ELSE excluded.password_hash
                END,
                role = 'system_admin',
                status = 'active',
                full_name = excluded.full_name,
                legacy_source_table = excluded.legacy_source_table,
                legacy_source_id = excluded.legacy_source_id,
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.staff_profiles (
                account_id, staff_id, job_title, department, status,
                created_at, updated_at
            )
            SELECT
                account.id, staff.id,
                CASE WHEN lower(staff.role) = 'owner' THEN 'Owner' ELSE 'Admin' END,
                'System', 'active', now(), now()
            FROM msi_v2.msi_staff staff
            JOIN msi_v2.accounts account
              ON account.legacy_source_table = 'msi_staff'
             AND account.legacy_source_id = staff.id
            WHERE staff.legacy_admin_id IS NOT NULL
            ON CONFLICT (staff_id) WHERE staff_id IS NOT NULL DO UPDATE SET
                account_id = excluded.account_id,
                job_title = excluded.job_title,
                department = excluded.department,
                status = 'active',
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.account_telegram_links (
                account_id, telegram_user_id, linked_at, status
            )
            SELECT account.id, staff.telegram_user_id, now(), 'active'
            FROM msi_v2.msi_staff staff
            JOIN msi_v2.accounts account
              ON account.legacy_source_table = 'msi_staff'
             AND account.legacy_source_id = staff.id
            WHERE staff.legacy_admin_id IS NOT NULL
              AND staff.telegram_user_id > 0
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                account_id = excluded.account_id,
                status = 'active'
            """
        )
    )


def _import_academic_structure(bind) -> None:
    bind.execute(
        text(
            """
            INSERT INTO msi_v2.subject_programs (
                subject_id, academic_year, program_name, source_file,
                total_items, lesson_count, exam_count, status,
                created_at, updated_at
            )
            SELECT
                subject.id, '2025-26', subject.subject_name || ' Legacy Program',
                'public.lesson_catalog',
                count(catalog.id), count(catalog.id), 0, 'active', now(), now()
            FROM msi_v2.subjects subject
            LEFT JOIN public.lesson_catalog catalog
              ON lower(btrim(catalog.subject_name)) = lower(btrim(subject.subject_name))
            GROUP BY subject.id, subject.subject_name
            ON CONFLICT (subject_id, academic_year) DO UPDATE SET
                total_items = GREATEST(
                    msi_v2.subject_programs.total_items,
                    excluded.total_items
                ),
                lesson_count = GREATEST(
                    msi_v2.subject_programs.lesson_count,
                    excluded.lesson_count
                ),
                status = 'active',
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            WITH lessons AS (
                SELECT DISTINCT ON (lower(btrim(subject_name)), lesson_order)
                    lower(btrim(subject_name)) AS subject_name,
                    lesson_order,
                    COALESCE(NULLIF(btrim(lesson_number), ''), lesson_order::text) AS lesson_number,
                    COALESCE(
                        NULLIF(btrim(lesson_topic), ''),
                        'Lesson ' || lesson_order::text
                    ) AS title
                FROM public.lesson_catalog
                WHERE lesson_order > 0
                  AND COALESCE(btrim(subject_name), '') <> ''
                ORDER BY lower(btrim(subject_name)), lesson_order, id
            )
            INSERT INTO msi_v2.subject_program_items (
                program_id, item_order, lesson_number, item_type, title,
                source_file, sheet_name, raw_json, created_at, updated_at
            )
            SELECT
                program.id, lessons.lesson_order, lessons.lesson_number,
                'lesson', lessons.title, 'public.lesson_catalog',
                'legacy-cutover',
                jsonb_build_object('legacy_public', true), now(), now()
            FROM lessons
            JOIN msi_v2.subjects subject
              ON lower(btrim(subject.subject_name)) = lessons.subject_name
            JOIN msi_v2.subject_programs program
              ON program.subject_id = subject.id
             AND program.academic_year = '2025-26'
            ON CONFLICT (program_id, item_order) DO NOTHING
            """
        )
    )

    bind.execute(
        text(
            """
            WITH legacy_groups AS (
                SELECT DISTINCT
                    lower(btrim(summary.school_key)) AS school_key,
                    btrim(summary.group_name) AS group_name,
                    lower(btrim(summary.subject_name)) AS subject_name
                FROM public.subject_summaries summary
                WHERE COALESCE(btrim(summary.school_key), '') <> ''
                  AND COALESCE(btrim(summary.group_name), '') <> ''
                  AND COALESCE(btrim(summary.subject_name), '') <> ''
            )
            INSERT INTO msi_v2.classes (
                school_id, class_name, class_code, status, created_at, updated_at
            )
            SELECT DISTINCT
                school.id, legacy.group_name,
                upper(regexp_replace(legacy.group_name, '[^a-zA-Z0-9]+', '-', 'g')),
                'active', now(), now()
            FROM legacy_groups legacy
            JOIN msi_v2.schools school
              ON lower(school.school_key) = legacy.school_key
            ON CONFLICT (school_id, lower(btrim(class_name))) DO UPDATE SET
                status = 'active',
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            WITH legacy_groups AS (
                SELECT DISTINCT
                    lower(btrim(summary.school_key)) AS school_key,
                    btrim(summary.group_name) AS group_name,
                    lower(btrim(summary.subject_name)) AS subject_name
                FROM public.subject_summaries summary
                WHERE COALESCE(btrim(summary.school_key), '') <> ''
                  AND COALESCE(btrim(summary.group_name), '') <> ''
                  AND COALESCE(btrim(summary.subject_name), '') <> ''
            )
            INSERT INTO msi_v2.groups (
                school_id, program_id, group_name, group_code,
                class_id, set_name, status, created_at, updated_at
            )
            SELECT
                school.id, program.id, legacy.group_name,
                upper(school.school_key || '-' || subject.subject_key || '-' ||
                    regexp_replace(legacy.group_name, '[^a-zA-Z0-9]+', '-', 'g')),
                class.id, 'Set 1', 'active', now(), now()
            FROM legacy_groups legacy
            JOIN msi_v2.schools school
              ON lower(school.school_key) = legacy.school_key
            JOIN msi_v2.subjects subject
              ON lower(btrim(subject.subject_name)) = legacy.subject_name
            JOIN msi_v2.subject_programs program
              ON program.subject_id = subject.id
             AND program.academic_year = '2025-26'
            JOIN msi_v2.classes class
              ON class.school_id = school.id
             AND lower(btrim(class.class_name)) = lower(btrim(legacy.group_name))
            WHERE NOT EXISTS (
                SELECT 1
                FROM msi_v2.groups existing
                WHERE existing.school_id = school.id
                  AND existing.program_id = program.id
                  AND lower(btrim(existing.group_name)) = lower(btrim(legacy.group_name))
            )
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.group_students (
                group_id, student_id, enrollment_status, joined_at,
                legacy_public_dashboard_id
            )
            SELECT DISTINCT
                group_row.id, student.id, 'active', now(), legacy.id
            FROM public.students legacy
            JOIN public.students_sheet_map mapping
              ON mapping.student_row_id = legacy.id
            JOIN public.subject_summaries summary
              ON summary.school_key = mapping.school_key
             AND summary.sheet_student_id = mapping.sheet_student_id
            JOIN msi_v2.students student
              ON student.legacy_student_row_id = legacy.id
            JOIN msi_v2.schools school
              ON lower(school.school_key) = lower(btrim(summary.school_key))
            JOIN msi_v2.subjects subject
              ON lower(btrim(subject.subject_name)) = lower(btrim(summary.subject_name))
            JOIN msi_v2.subject_programs program
              ON program.subject_id = subject.id
             AND program.academic_year = '2025-26'
            JOIN msi_v2.groups group_row
              ON group_row.school_id = school.id
             AND group_row.program_id = program.id
             AND lower(btrim(group_row.group_name)) = lower(btrim(summary.group_name))
            ON CONFLICT (group_id, student_id) DO UPDATE SET
                enrollment_status = 'active',
                left_at = NULL,
                legacy_public_dashboard_id = excluded.legacy_public_dashboard_id
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.class_students (
                class_id, student_id, enrollment_status, joined_at
            )
            SELECT DISTINCT group_row.class_id, enrollment.student_id, 'active', now()
            FROM msi_v2.group_students enrollment
            JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
            JOIN msi_v2.students student ON student.id = enrollment.student_id
            WHERE group_row.class_id IS NOT NULL
              AND student.legacy_student_row_id IS NOT NULL
            ON CONFLICT (class_id, student_id) DO UPDATE SET
                enrollment_status = 'active',
                left_at = NULL
            """
        )
    )

    bind.execute(
        text(
            """
            UPDATE msi_v2.student_profiles profile
            SET class_id = selected.class_id,
                updated_at = now()
            FROM (
                SELECT enrollment.student_id, min(group_row.class_id) AS class_id
                FROM msi_v2.group_students enrollment
                JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
                JOIN msi_v2.students student ON student.id = enrollment.student_id
                WHERE group_row.class_id IS NOT NULL
                  AND student.legacy_student_row_id IS NOT NULL
                GROUP BY enrollment.student_id
            ) selected
            WHERE profile.student_id = selected.student_id
            """
        )
    )


def _used_teacher_codes(bind) -> set[str]:
    rows = _all(
        bind,
        """
        SELECT teacher_code AS code FROM msi_v2.teacher_profiles
        UNION ALL
        SELECT login AS code FROM msi_v2.accounts WHERE login IS NOT NULL
        UNION ALL
        SELECT login AS code FROM msi_v2.msi_staff
        """,
    )
    return {
        str(row.get("code") or "").strip().upper()
        for row in rows
        if _TEACHER_CODE_RE.fullmatch(str(row.get("code") or "").strip())
    }


def _next_teacher_code(used_codes: set[str]) -> str:
    number = 1
    while f"TCH{number:04d}" in used_codes:
        number += 1
    code = f"TCH{number:04d}"
    used_codes.add(code)
    return code


def _import_teachers(bind) -> None:
    if not _legacy_table_exists(bind, "teachers"):
        return

    bind.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_legacy_teacher_id
            ON msi_v2.teachers (legacy_teacher_id)
            WHERE legacy_teacher_id IS NOT NULL
            """
        )
    )

    used_codes = _used_teacher_codes(bind)
    for legacy in _all(bind, "SELECT * FROM public.teachers ORDER BY id"):
        teacher = _one(
            bind,
            """
            SELECT * FROM msi_v2.teachers
            WHERE legacy_teacher_id = :legacy_id
            LIMIT 1
            """,
            legacy_id=int(legacy["id"]),
        )
        if teacher:
            teacher_id = int(teacher["id"])
            bind.execute(
                text(
                    """
                    UPDATE msi_v2.teachers
                    SET full_name = :full_name,
                        status = 'active',
                        updated_at = now()
                    WHERE id = :teacher_id
                    """
                ),
                {
                    "teacher_id": teacher_id,
                    "full_name": str(legacy.get("full_name") or "").strip()
                    or f"Teacher {legacy['id']}",
                },
            )
        else:
            inserted = _one(
                bind,
                """
                INSERT INTO msi_v2.teachers (
                    full_name, status, notes, legacy_teacher_id,
                    created_at, updated_at
                )
                VALUES (
                    :full_name, 'active', :notes, :legacy_id, now(), now()
                )
                RETURNING id
                """,
                full_name=str(legacy.get("full_name") or "").strip()
                or f"Teacher {legacy['id']}",
                notes="Imported from the legacy public.teachers table.",
                legacy_id=int(legacy["id"]),
            )
            if not inserted:
                raise RuntimeError("Unable to import a legacy teacher.")
            teacher_id = int(inserted["id"])

        existing_profile = _one(
            bind,
            """
            SELECT profile.teacher_code, profile.account_id
            FROM msi_v2.teacher_profiles profile
            WHERE profile.teacher_id = :teacher_id
            LIMIT 1
            """,
            teacher_id=teacher_id,
        )
        existing_code = str(
            (existing_profile or {}).get("teacher_code") or ""
        ).strip().upper()
        code = (
            existing_code
            if _TEACHER_CODE_RE.fullmatch(existing_code)
            else _next_teacher_code(used_codes)
        )
        used_codes.add(code)
        password_hash = generate_password_hash(code)

        staff = _one(
            bind,
            """
            INSERT INTO msi_v2.msi_staff (
                login, password_hash, display_name, role, status,
                teacher_id, created_at, updated_at
            )
            VALUES (
                :login, :password_hash, :display_name, 'teacher', 'active',
                :teacher_id, now(), now()
            )
            ON CONFLICT ((lower(login))) DO UPDATE SET
                password_hash = CASE
                    WHEN COALESCE(btrim(msi_v2.msi_staff.password_hash), '') <> ''
                    THEN msi_v2.msi_staff.password_hash
                    ELSE excluded.password_hash
                END,
                display_name = excluded.display_name,
                role = 'teacher',
                status = 'active',
                teacher_id = excluded.teacher_id,
                updated_at = now()
            RETURNING id, password_hash
            """,
            login=code,
            password_hash=password_hash,
            display_name=str(legacy.get("full_name") or "").strip() or code,
            teacher_id=teacher_id,
        )
        if not staff:
            raise RuntimeError("Unable to import a legacy teacher login.")
        staff_id = int(staff["id"])

        account = _one(
            bind,
            """
            SELECT * FROM msi_v2.accounts
            WHERE lower(btrim(login)) = lower(btrim(:login))
               OR (legacy_source_table = 'msi_staff' AND legacy_source_id = :staff_id)
            ORDER BY id
            LIMIT 1
            """,
            login=code,
            staff_id=staff_id,
        )
        if account:
            account_id = int(account["id"])
            bind.execute(
                text(
                    """
                    UPDATE msi_v2.accounts
                    SET login = :login,
                        password_hash = CASE
                            WHEN COALESCE(btrim(password_hash), '') <> ''
                            THEN password_hash
                            ELSE :password_hash
                        END,
                        role = 'teacher',
                        status = 'active',
                        full_name = :full_name,
                        legacy_source_table = 'msi_staff',
                        legacy_source_id = :staff_id,
                        must_change_password = false,
                        password_changed_at = COALESCE(password_changed_at, now()),
                        updated_at = now()
                    WHERE id = :account_id
                    """
                ),
                {
                    "login": code,
                    "password_hash": str(staff["password_hash"]),
                    "full_name": str(legacy.get("full_name") or "").strip() or code,
                    "staff_id": staff_id,
                    "account_id": account_id,
                },
            )
        else:
            inserted_account = _one(
                bind,
                """
                INSERT INTO msi_v2.accounts (
                    login, password_hash, role, status, full_name,
                    legacy_source_table, legacy_source_id,
                    must_change_password, password_changed_at, session_version,
                    created_at, updated_at
                )
                VALUES (
                    :login, :password_hash, 'teacher', 'active', :full_name,
                    'msi_staff', :staff_id,
                    false, now(), 1, now(), now()
                )
                RETURNING id
                """,
                login=code,
                password_hash=str(staff["password_hash"]),
                full_name=str(legacy.get("full_name") or "").strip() or code,
                staff_id=staff_id,
            )
            if not inserted_account:
                raise RuntimeError("Unable to create a canonical teacher account.")
            account_id = int(inserted_account["id"])

        bind.execute(
            text(
                """
                INSERT INTO msi_v2.teacher_profiles (
                    account_id, teacher_id, teacher_code, legacy_login,
                    status, created_at, updated_at
                )
                VALUES (
                    :account_id, :teacher_id, :teacher_code, '',
                    'active', now(), now()
                )
                ON CONFLICT (teacher_id) WHERE teacher_id IS NOT NULL DO UPDATE SET
                    account_id = excluded.account_id,
                    teacher_code = excluded.teacher_code,
                    status = 'active',
                    updated_at = now()
                """
            ),
            {
                "account_id": account_id,
                "teacher_id": teacher_id,
                "teacher_code": code,
            },
        )

        assigned_group = str(legacy.get("assigned_group") or "").strip()
        if assigned_group:
            bind.execute(
                text(
                    """
                    INSERT INTO msi_v2.group_teachers (
                        group_id, teacher_id, role, status, assigned_at
                    )
                    SELECT group_row.id, :teacher_id, 'main', 'active', now()
                    FROM msi_v2.groups group_row
                    WHERE lower(btrim(group_row.group_name)) = lower(btrim(:group_name))
                    ON CONFLICT (group_id, teacher_id, role) DO UPDATE SET
                        status = 'active'
                    """
                ),
                {"teacher_id": teacher_id, "group_name": assigned_group},
            )
            bind.execute(
                text(
                    """
                    INSERT INTO msi_v2.teacher_subjects (
                        teacher_id, subject_id, status, created_at
                    )
                    SELECT DISTINCT :teacher_id, program.subject_id, 'active', now()
                    FROM msi_v2.groups group_row
                    JOIN msi_v2.subject_programs program
                      ON program.id = group_row.program_id
                    WHERE lower(btrim(group_row.group_name)) = lower(btrim(:group_name))
                    ON CONFLICT (teacher_id, subject_id) DO UPDATE SET
                        status = 'active'
                    """
                ),
                {"teacher_id": teacher_id, "group_name": assigned_group},
            )


def _import_resources_and_communications(bind) -> None:
    bind.execute(
        text(
            """
            INSERT INTO msi_v2.resource_types (
                name, slug, is_active, display_order, legacy_resource_type_id,
                created_at, updated_at
            )
            SELECT
                name, lower(btrim(slug)), COALESCE(is_active, 1) <> 0,
                COALESCE(display_order, 0), id, now(), now()
            FROM public.resource_types
            WHERE COALESCE(btrim(slug), '') <> ''
            ON CONFLICT ((lower(slug))) DO UPDATE SET
                name = excluded.name,
                is_active = excluded.is_active,
                display_order = excluded.display_order,
                legacy_resource_type_id = excluded.legacy_resource_type_id,
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.resources (
                subject_id, resource_type_id, title, description,
                resource_url, resource_file_path, thumbnail_file_path,
                is_active, created_by_staff_id, legacy_resource_id,
                created_at, updated_at
            )
            SELECT
                subject.id, resource_type.id,
                COALESCE(NULLIF(btrim(legacy.title), ''), 'Legacy resource'),
                COALESCE(legacy.description, ''),
                COALESCE(legacy.resource_url, ''),
                COALESCE(legacy.resource_file_path, ''),
                COALESCE(legacy.thumbnail_file_path, ''),
                COALESCE(legacy.is_active, 1) <> 0,
                staff.id, legacy.id, now(), now()
            FROM public.resources legacy
            LEFT JOIN msi_v2.subjects subject
              ON lower(btrim(subject.subject_key)) = lower(btrim(legacy.subject_key))
              OR lower(btrim(subject.subject_name)) = lower(btrim(legacy.subject_name))
            LEFT JOIN msi_v2.resource_types resource_type
              ON resource_type.legacy_resource_type_id = legacy.resource_type_id
            LEFT JOIN msi_v2.msi_staff staff
              ON staff.legacy_admin_id = legacy.created_by_admin_id
            ON CONFLICT (legacy_resource_id) WHERE legacy_resource_id IS NOT NULL DO UPDATE SET
                subject_id = excluded.subject_id,
                resource_type_id = excluded.resource_type_id,
                title = excluded.title,
                description = excluded.description,
                resource_url = excluded.resource_url,
                resource_file_path = excluded.resource_file_path,
                thumbnail_file_path = excluded.thumbnail_file_path,
                is_active = excluded.is_active,
                created_by_staff_id = excluded.created_by_staff_id,
                updated_at = now()
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.resource_comments (
                id, resource_id, author_name, body, created_at
            )
            SELECT
                legacy.id, resource.id, legacy.author_name, legacy.body, now()
            FROM public.resource_comments legacy
            JOIN msi_v2.resources resource
              ON resource.legacy_resource_id = legacy.resource_id
            ON CONFLICT (id) DO UPDATE SET
                resource_id = excluded.resource_id,
                author_name = excluded.author_name,
                body = excluded.body
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.chat_messages (
                id, room, author_name, author_student_id, body,
                is_deleted, created_at
            )
            SELECT
                id, room, author_name, author_student_id, body,
                COALESCE(is_deleted, 0) <> 0, now()
            FROM public.chat_messages
            ON CONFLICT (id) DO UPDATE SET
                room = excluded.room,
                author_name = excluded.author_name,
                author_student_id = excluded.author_student_id,
                body = excluded.body,
                is_deleted = excluded.is_deleted
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.chat_blocked_users (
                student_id, blocked_by_staff_login, blocked_at, reason
            )
            SELECT
                student_id, COALESCE(blocked_by_admin, ''), now(), COALESCE(reason, '')
            FROM public.chat_blocked_users
            ON CONFLICT (student_id) DO UPDATE SET
                blocked_by_staff_login = excluded.blocked_by_staff_login,
                reason = excluded.reason
            """
        )
    )

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.app_settings (key, value, updated_at)
            SELECT key, value, now()
            FROM public.app_meta
            ON CONFLICT (key) DO UPDATE SET
                value = excluded.value,
                updated_at = now()
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    required_tables = {
        "students",
        "student_auth",
        "students_sheet_map",
        "subject_summaries",
        "teachers",
        "lesson_catalog",
        "resource_types",
        "resources",
        "resource_comments",
        "chat_messages",
        "chat_blocked_users",
        "app_meta",
    }
    if not all(_legacy_table_exists(bind, table_name) for table_name in required_tables):
        return

    _import_schools_and_subjects(bind)
    _import_students(bind)
    _import_admins(bind)
    _import_academic_structure(bind)
    _import_teachers(bind)
    _import_resources_and_communications(bind)

    bind.execute(
        text(
            """
            INSERT INTO msi_v2.audit_events (
                event_type, entity_type, detail_json, created_at
            )
            SELECT
                'legacy_public.cutover', 'database',
                jsonb_build_object(
                    'students', (SELECT count(*) FROM public.students),
                    'teachers', (SELECT count(*) FROM public.teachers),
                    'resources', (SELECT count(*) FROM public.resources),
                    'legacy_tables_preserved', true
                ),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM msi_v2.audit_events
                WHERE event_type = 'legacy_public.cutover'
            )
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "The legacy public cutover is intentionally irreversible. Restore the "
        "pre-cutover database backup instead of deleting imported identities."
    )
