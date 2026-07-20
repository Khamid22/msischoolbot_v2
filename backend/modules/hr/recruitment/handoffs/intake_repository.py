"""Intake persistence for Recruitment handoffs."""

from __future__ import annotations

from typing import Any

from backend.modules.hr.recruitment.handoffs.lifecycle_repository import (
    set_teacher_identity_enabled,
)


def list_teacher_handoff_rows(
    conn: Any,
    *,
    kind: str,
    search: str = "",
    subject_id: int | None = None,
    sort: str = "average_score",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Any], int]:
    """List canonical Academy/active teacher business records."""

    if kind == "teacher_academy":
        records_sql = """
            SELECT
                'teacher_academy'::text AS kind,
                academy.id AS record_id,
                academy.recruitment_candidate_id,
                academy.full_name,
                COALESCE(
                    NULLIF(academy.position, ''),
                    NULLIF(program.program_name, ''),
                    NULLIF(subject.subject_name, ''),
                    'Position not set'
                ) AS position,
                COALESCE(subject.subject_name, '') AS subject,
                CASE
                    WHEN academy.subject_id IS NULL THEN ARRAY[]::bigint[]
                    ELSE ARRAY[academy.subject_id]::bigint[]
                END AS subject_ids,
                COALESCE(academy.academy_status, 'in_training') AS status,
                COALESCE(academy.account_onboarding_status, 'complete') AS onboarding_status,
                academy.academy_start_date::timestamptz AS joined_at,
                COALESCE(
                    academy.academy_start_date::text,
                    (academy.created_at AT TIME ZONE 'Asia/Tashkent')::date::text
                ) AS added_on,
                COALESCE(academy.academy_start_date::timestamptz, academy.created_at)
                    AS sort_at,
                COALESCE(academy_progress.assigned_count, 0)::integer AS assigned_count,
                COALESCE(academy_progress.evaluated_count, 0)::integer AS evaluated_count,
                COALESCE(academy_progress.passed_count, 0)::integer AS passed_count,
                COALESCE(academy_progress.failed_count, 0)::integer AS failed_count,
                academy_progress.average_score,
                (
                    academy.user_id IS NOT NULL
                    AND academy.promoted_teacher_id IS NULL
                    AND COALESCE(identity_staff.role, '') = 'teacher'
                    AND COALESCE(identity_teacher.status, '') = 'academy'
                ) AS generated_login_will_be_deleted
            FROM msi_v2.academy_teachers academy
            LEFT JOIN msi_v2.subjects subject ON subject.id = academy.subject_id
            LEFT JOIN msi_v2.subject_programs program
              ON program.id = academy.subject_program_id
            LEFT JOIN msi_v2.msi_staff identity_staff
              ON identity_staff.id = academy.user_id
            LEFT JOIN msi_v2.teachers identity_teacher
              ON identity_teacher.id = identity_staff.teacher_id
            LEFT JOIN LATERAL (
                SELECT
                    (
                        SELECT COUNT(*)::integer
                        FROM msi_v2.academy_lesson_assignments assignment
                        WHERE assignment.academy_teacher_id = academy.id
                    ) AS assigned_count,
                    COUNT(latest_assessment.id)::integer AS evaluated_count,
                    COUNT(latest_assessment.id) FILTER (
                        WHERE latest_assessment.decision IN (
                            'passed',
                            'ready_for_final_evaluation',
                            'approved_for_active_teacher'
                        )
                    )::integer AS passed_count,
                    COUNT(latest_assessment.id) FILTER (
                        WHERE latest_assessment.decision NOT IN (
                            'passed',
                            'ready_for_final_evaluation',
                            'approved_for_active_teacher'
                        )
                    )::integer AS failed_count,
                    AVG(latest_assessment.weighted_overall_score) FILTER (
                        WHERE latest_assessment.weighted_overall_score > 0
                    ) AS average_score
                FROM (
                    SELECT DISTINCT ON (assessment.lesson_assignment_id)
                        assessment.id,
                        assessment.lesson_assignment_id,
                        assessment.decision,
                        assessment.weighted_overall_score
                    FROM msi_v2.academy_assessments assessment
                    WHERE assessment.academy_teacher_id = academy.id
                      AND assessment.lesson_assignment_id IS NOT NULL
                    ORDER BY
                        assessment.lesson_assignment_id,
                        assessment.assessment_datetime DESC NULLS LAST,
                        assessment.id DESC
                ) latest_assessment
            ) academy_progress ON true
            LEFT JOIN msi_v2.teacher_candidates candidate
              ON candidate.id = academy.recruitment_candidate_id
            WHERE academy.promoted_teacher_id IS NULL
              AND COALESCE(academy.academy_status, '') NOT IN (
                  'rejected', 'removed', 'trash_bin'
              )
              AND COALESCE(candidate.status, 'teacher_academy') NOT IN (
                  'rejected', 'candidate_withdrew', 'trash_bin'
              )
        """
    elif kind == "active_teacher":
        records_sql = """
            SELECT
                'active_teacher'::text AS kind,
                teacher.id AS record_id,
                teacher.recruitment_candidate_id,
                teacher.full_name,
                COALESCE(
                    NULLIF(candidate.applied_position, ''),
                    NULLIF(teacher_subject.subject_name, ''),
                    'Position not set'
                ) AS position,
                COALESCE(teacher_subject.subject_name, '') AS subject,
                COALESCE(teacher_subject.subject_ids, ARRAY[]::bigint[]) AS subject_ids,
                teacher.status,
                COALESCE(teacher.account_onboarding_status, 'complete') AS onboarding_status,
                teacher.created_at AS joined_at,
                (teacher.created_at AT TIME ZONE 'Asia/Tashkent')::date::text AS added_on,
                teacher.created_at AS sort_at,
                0::integer AS assigned_count,
                0::integer AS evaluated_count,
                0::integer AS passed_count,
                0::integer AS failed_count,
                NULL::numeric AS average_score,
                false AS generated_login_will_be_deleted
            FROM msi_v2.teachers teacher
            LEFT JOIN msi_v2.teacher_candidates candidate
              ON candidate.id = teacher.recruitment_candidate_id
            LEFT JOIN LATERAL (
                SELECT string_agg(
                    DISTINCT available_subject.subject_name,
                    ', ' ORDER BY available_subject.subject_name
                ) AS subject_name,
                array_agg(
                    DISTINCT available_subject.subject_id
                    ORDER BY available_subject.subject_id
                ) FILTER (WHERE available_subject.subject_id IS NOT NULL) AS subject_ids
                FROM (
                    SELECT direct_subject.id AS subject_id, direct_subject.subject_name
                    FROM msi_v2.teacher_subjects teacher_subject_link
                    JOIN msi_v2.subjects direct_subject
                      ON direct_subject.id = teacher_subject_link.subject_id
                    WHERE teacher_subject_link.teacher_id = teacher.id
                      AND teacher_subject_link.status = 'active'

                    UNION ALL

                    SELECT group_subject.id AS subject_id, group_subject.subject_name
                    FROM msi_v2.group_teachers group_teacher
                    JOIN msi_v2.groups teacher_group ON teacher_group.id = group_teacher.group_id
                    JOIN msi_v2.subject_programs group_program
                      ON group_program.id = teacher_group.program_id
                    JOIN msi_v2.subjects group_subject
                      ON group_subject.id = group_program.subject_id
                    WHERE group_teacher.teacher_id = teacher.id
                      AND group_teacher.status = 'active'
                ) available_subject
            ) teacher_subject ON true
            WHERE teacher.status = 'active'
              AND COALESCE(candidate.status, 'active_teacher') NOT IN (
                  'rejected', 'candidate_withdrew', 'trash_bin'
              )
        """
    else:
        raise ValueError("Unknown teacher handoff kind.")

    filters: list[str] = []
    params: list[Any] = []
    normalized_search = str(search or "").strip()
    if normalized_search:
        filters.append(
            "(record.full_name ILIKE %s OR record.position ILIKE %s OR record.subject ILIKE %s)"
        )
        search_term = f"%{normalized_search}%"
        params.extend((search_term, search_term, search_term))
    if subject_id is not None:
        filters.append("%s = ANY(record.subject_ids)")
        params.append(int(subject_id))
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    normalized_sort = str(sort or "").strip().lower()
    if kind == "active_teacher":
        normalized_sort = "date"
    order_sql = {
        "average_score": (
            "record.average_score DESC NULLS LAST, record.passed_count DESC, "
            "record.sort_at DESC NULLS LAST, lower(record.full_name), record.record_id"
        ),
        "lessons": (
            "record.passed_count DESC, record.average_score DESC NULLS LAST, "
            "record.sort_at DESC NULLS LAST, lower(record.full_name), record.record_id"
        ),
        "date": (
            "record.sort_at DESC NULLS LAST, lower(record.full_name), record.record_id"
        ),
    }.get(normalized_sort)
    if order_sql is None:
        raise ValueError("Unknown teacher handoff sort.")
    total_row = conn.execute(
        f"""
        WITH record AS ({records_sql})
        SELECT count(*) AS total
        FROM record
        {where_sql}
        """,
        tuple(params) if params else None,
    ).fetchone()
    rows = conn.execute(
        f"""
        WITH record AS ({records_sql})
        SELECT record.kind, record.record_id, record.recruitment_candidate_id,
               record.full_name, record.position, record.subject, record.status,
               record.onboarding_status, record.joined_at::text AS joined_at,
               record.added_on, record.assigned_count, record.evaluated_count,
               record.passed_count, record.failed_count,
               record.average_score,
               record.generated_login_will_be_deleted
        FROM record
        {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
        """,
        tuple([*params, int(limit), int(offset)]),
    ).fetchall()
    return rows, int(total_row["total"] or 0) if total_row else 0


def exact_academy_identity_match(
    conn: Any,
    *,
    phone: str = "",
    email: str = "",
    telegram_username: str = "",
    linked_account_id: int | None = None,
) -> Any:
    """Return an existing Academy lifecycle profile matched by exact identity.

    Names are intentionally excluded. A person may share a name with another
    applicant and name similarity must never block a real application.
    """

    normalized_phone = "".join(
        character for character in str(phone or "") if character.isdigit()
    )
    normalized_email = str(email or "").strip().lower()
    normalized_telegram = str(telegram_username or "").strip().lstrip("@").lower()
    if not any(
        (normalized_phone, normalized_email, normalized_telegram, linked_account_id)
    ):
        return None
    return conn.execute(
        """
        SELECT candidate.id AS profile_id, academy.id AS academy_teacher_id,
               candidate.full_name, candidate.profile_origin,
               candidate.is_application_received
        FROM msi_v2.academy_teachers academy
        JOIN msi_v2.teacher_candidates candidate
          ON candidate.id = academy.recruitment_candidate_id
        WHERE
            (
                %s <> ''
                AND (
                    regexp_replace(COALESCE(candidate.phone, ''), '[^0-9]+', '', 'g') = %s
                    OR regexp_replace(COALESCE(academy.phone, ''), '[^0-9]+', '', 'g') = %s
                )
            )
            OR (
                %s <> ''
                AND (
                    lower(COALESCE(candidate.email, '')) = %s
                    OR lower(COALESCE(academy.email, '')) = %s
                )
            )
            OR (
                %s <> ''
                AND (
                    lower(ltrim(COALESCE(candidate.telegram_username, ''), '@')) = %s
                    OR lower(ltrim(COALESCE(academy.telegram_username, ''), '@')) = %s
                )
            )
            OR (
                %s IS NOT NULL
                AND (
                    candidate.linked_account_id = %s
                    OR EXISTS (
                        SELECT 1
                        FROM msi_v2.accounts account
                        WHERE account.id = %s
                          AND account.legacy_source_table = 'msi_staff'
                          AND account.legacy_source_id = academy.user_id
                    )
                )
            )
        ORDER BY candidate.id
        LIMIT 1
        """,
        (
            normalized_phone,
            normalized_phone,
            normalized_phone,
            normalized_email,
            normalized_email,
            normalized_email,
            normalized_telegram,
            normalized_telegram,
            normalized_telegram,
            linked_account_id,
            linked_account_id,
            linked_account_id,
        ),
    ).fetchone()


def insert_academy_direct_profile(
    conn: Any,
    *,
    full_name: str,
    subject_id: int | None,
    applied_position: str,
    phone: str,
    email: str,
    telegram_username: str,
    linked_account_id: int | None,
    now: str,
    actor_account_id: int | None,
    transition_source: str = "migration",
    history_comment: str = "Lifecycle profile created from an existing Teacher Academy record.",
) -> int:
    """Create a lifecycle profile without fabricating a recruitment application."""

    row = conn.execute(
        """
        WITH inserted_profile AS (
            INSERT INTO msi_v2.teacher_candidates (
                full_name, phone, email, telegram_username, subject_id,
                applied_position, application_date, source, source_detail,
                status, stage_changed_at, linked_account_id,
                is_application_received, profile_origin, version,
                updated_by_account_id, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, NULLIF(%s::bigint, 0), %s,
                NULL, '', '', 'teacher_academy', %s::timestamptz, %s,
                false, 'academy_direct', 1, %s, %s::timestamptz, %s::timestamptz
            )
            RETURNING id
        ), inserted_history AS (
            INSERT INTO msi_v2.teacher_candidate_stage_history (
                candidate_id, stage, entered_at, responsible_account_id,
                comment, transition_source, sla_target_days, sla_due_at
            )
            SELECT id, 'teacher_academy', %s::timestamptz, %s,
                   %s, %s, NULL, NULL
            FROM inserted_profile
            RETURNING candidate_id
        )
        SELECT candidate_id AS id FROM inserted_history
        """,
        (
            full_name,
            phone,
            email,
            telegram_username,
            int(subject_id or 0),
            applied_position,
            now,
            linked_account_id,
            actor_account_id,
            now,
            now,
            now,
            actor_account_id,
            history_comment,
            transition_source,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def link_academy_profile(
    conn: Any,
    *,
    academy_teacher_id: int,
    candidate_id: int,
    full_name: str,
    linked_account_id: int | None,
    now: str,
) -> bool:
    """Attach one Academy block to one lifecycle profile, failing on conflicts."""

    row = conn.execute(
        """
        UPDATE msi_v2.academy_teachers academy
        SET recruitment_candidate_id = %s,
            full_name = %s,
            updated_at = %s::timestamptz
        WHERE academy.id = %s
          AND (academy.recruitment_candidate_id IS NULL OR academy.recruitment_candidate_id = %s)
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.academy_teachers other
              WHERE other.recruitment_candidate_id = %s
                AND other.id <> academy.id
          )
        RETURNING academy.id
        """,
        (
            int(candidate_id),
            full_name,
            now,
            int(academy_teacher_id),
            int(candidate_id),
            int(candidate_id),
        ),
    ).fetchone()
    if not row:
        return False
    if linked_account_id:
        linked = conn.execute(
            """
            UPDATE msi_v2.teacher_candidates
            SET linked_account_id = %s, updated_at = %s::timestamptz
            WHERE id = %s
              AND (linked_account_id IS NULL OR linked_account_id = %s)
            """,
            (int(linked_account_id), now, int(candidate_id), int(linked_account_id)),
        )
        if int(getattr(linked, "rowcount", 0) or 0) < 1:
            return False
    return True


def ensure_academy_intake(
    conn: Any, *, candidate: Any, actor_login: str, now: str
) -> int:
    existing = conn.execute(
        """
        SELECT id, academy_status, user_id
        FROM msi_v2.academy_teachers
        WHERE recruitment_candidate_id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (candidate["id"],),
    ).fetchone()
    if existing:
        if str(existing["academy_status"] or "") == "rejected":
            conn.execute(
                """
                UPDATE msi_v2.academy_teachers
                SET academy_status = 'new_academy_teacher',
                    account_onboarding_status = CASE
                        WHEN user_id IS NULL THEN 'pending'
                        ELSE 'complete'
                    END,
                    updated_at = %s::timestamptz
                WHERE id = %s
                """,
                (now, int(existing["id"])),
            )
        return int(existing["id"])
    row = conn.execute(
        """
        INSERT INTO msi_v2.academy_teachers (
            user_id, full_name, subject_id, subject_program_id, position,
            employment_type, telegram_username, phone, email, academy_status,
            notes, created_by, recruitment_candidate_id,
            account_onboarding_status, created_at, updated_at
        ) VALUES (
            NULL, %s, NULLIF(%s::bigint, 0), NULL, %s,
            'academy', %s, %s, %s, 'new_academy_teacher',
            %s, %s, %s, 'pending', %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate["full_name"],
            int(candidate["subject_id"] or 0),
            candidate["applied_position"] or "Trainee Teacher",
            candidate["telegram_username"],
            candidate["phone"],
            candidate.get("email", ""),
            (
                f"Linked to Academy-direct lifecycle profile #{candidate['id']}."
                if candidate.get("profile_origin") == "academy_direct"
                else f"Accepted from recruitment candidate #{candidate['id']}."
            ),
            actor_login,
            candidate["id"],
            now,
            now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def ensure_active_teacher_intake(conn: Any, *, candidate: Any, now: str) -> int:
    existing = conn.execute(
        """
        SELECT id, status
        FROM msi_v2.teachers
        WHERE recruitment_candidate_id = %s
        LIMIT 1
        """,
        (candidate["id"],),
    ).fetchone()
    if existing:
        teacher_id = int(existing["id"])
        if str(existing["status"] or "").strip().lower() == "rejected":
            conn.execute(
                """
                UPDATE msi_v2.teachers
                SET status = 'active', updated_at = %s::timestamptz
                WHERE id = %s AND status = 'rejected'
                """,
                (now, teacher_id),
            )
            staff = conn.execute(
                """
                SELECT id
                FROM msi_v2.msi_staff
                WHERE teacher_id = %s AND lower(role) = 'teacher'
                ORDER BY id
                LIMIT 1
                """,
                (teacher_id,),
            ).fetchone()
            set_teacher_identity_enabled(
                conn,
                staff_id=int(staff["id"] or 0) if staff else 0,
                teacher_id=teacher_id,
                enabled=True,
                now=now,
            )
        return teacher_id
    row = conn.execute(
        """
        INSERT INTO msi_v2.teachers (
            full_name, phone, telegram_username, status, notes,
            recruitment_candidate_id, account_onboarding_status,
            created_at, updated_at
        ) VALUES (%s, %s, %s, 'active', %s, %s, 'pending', %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (
            candidate["full_name"],
            candidate["phone"],
            candidate["telegram_username"],
            f"Accepted directly from recruitment candidate #{candidate['id']}.",
            candidate["id"],
            now,
            now,
        ),
    ).fetchone()
    teacher_id = int(row["id"]) if row else 0
    if teacher_id and int(candidate["subject_id"] or 0):
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_subjects (teacher_id, subject_id, status, created_at)
            VALUES (%s, %s, 'active', %s::timestamptz)
            ON CONFLICT (teacher_id, subject_id) DO UPDATE SET status = 'active'
            """,
            (teacher_id, int(candidate["subject_id"]), now),
        )
    return teacher_id


__all__ = [
    "ensure_academy_intake",
    "ensure_active_teacher_intake",
    "exact_academy_identity_match",
    "insert_academy_direct_profile",
    "link_academy_profile",
    "list_teacher_handoff_rows",
]
