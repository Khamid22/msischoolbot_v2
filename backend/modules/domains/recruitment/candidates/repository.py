"""Mutation persistence for Recruitment candidates."""

from __future__ import annotations

import json
from typing import Any

from backend.modules.domains.recruitment.handoffs.lifecycle_repository import (
    delete_generated_academy_identity,
    list_teacher_account_ids_for_staff,
)


_STAGE_HISTORY_TRANSITION_SOURCES = frozenset(
    {"manual", "automatic", "migration", "restored"}
)
_STAGE_HISTORY_TRANSITION_SOURCE_ALIASES = {
    "historical_restoration": "restored",
}


def delete_closed_candidate(
    conn: Any,
    *,
    candidate_id: int,
    expected_version: int,
) -> bool:
    row = conn.execute(
        """
        WITH locked AS (
            SELECT id
            FROM msi_v2.teacher_candidates
            WHERE id = %s
              AND version = %s
              AND status IN ('trash_bin', 'rejected', 'candidate_withdrew')
            FOR UPDATE
        ), deleted_audit AS (
            DELETE FROM msi_v2.audit_events audit
            USING locked
            WHERE audit.entity_type = 'teacher_candidate'
              AND audit.entity_id = locked.id
        )
        DELETE FROM msi_v2.teacher_candidates candidate
        USING locked
        WHERE candidate.id = locked.id
        RETURNING candidate.id
        """,
        (int(candidate_id), int(expected_version)),
    ).fetchone()
    return bool(row)


def list_trash_candidates_for_purge(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT candidate.id, candidate.full_name, candidate.status, candidate.version,
               academy.id AS academy_teacher_id,
               academy.academy_status,
               academy.promoted_teacher_id AS academy_promoted_teacher_id,
               teacher.id AS active_teacher_id,
               teacher.status AS active_teacher_status
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN msi_v2.academy_teachers academy
          ON academy.recruitment_candidate_id = candidate.id
        LEFT JOIN msi_v2.teachers teacher
          ON teacher.recruitment_candidate_id = candidate.id
        WHERE candidate.status = 'trash_bin'
        ORDER BY candidate.id
        FOR UPDATE OF candidate
        """
    ).fetchall()


def purge_closed_academy_handoff(conn: Any, *, candidate_id: int) -> bool:
    """Delete one terminal Academy handoff and its generated-only identity."""
    academy = conn.execute(
        """
        SELECT academy.id, academy.user_id AS staff_id,
               academy.academy_status, academy.promoted_teacher_id,
               COALESCE(staff.teacher_id, 0) AS teacher_id,
               COALESCE(identity_teacher.status, '') AS teacher_status
        FROM msi_v2.academy_teachers academy
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = academy.user_id
        LEFT JOIN msi_v2.teachers identity_teacher
          ON identity_teacher.id = staff.teacher_id
        WHERE academy.recruitment_candidate_id = %s
        FOR UPDATE OF academy
        """,
        (int(candidate_id),),
    ).fetchone()
    if not academy:
        return True
    if (
        str(academy["academy_status"] or "").strip()
        not in {"rejected", "removed", "trash_bin"}
        or int(academy["promoted_teacher_id"] or 0)
    ):
        return False

    academy_teacher_id = int(academy["id"])
    staff_id = int(academy["staff_id"] or 0)
    teacher_id = int(academy["teacher_id"] or 0)
    generated_identity = bool(
        staff_id
        and teacher_id
        and str(academy["teacher_status"] or "").strip() == "academy"
    )
    account_ids = (
        list_teacher_account_ids_for_staff(conn, staff_id)
        if generated_identity
        else []
    )
    deleted = conn.execute(
        """
        DELETE FROM msi_v2.academy_teachers
        WHERE id = %s
          AND promoted_teacher_id IS NULL
          AND academy_status IN ('rejected', 'removed', 'trash_bin')
        RETURNING id
        """,
        (academy_teacher_id,),
    ).fetchone()
    if not deleted:
        return False
    if generated_identity:
        delete_generated_academy_identity(
            conn,
            staff_id=staff_id,
            teacher_id=teacher_id,
            account_ids=account_ids,
        )
    return True


def insert_candidate(
    conn: Any, *, values: dict[str, Any], now: str, actor_account_id: int | None
) -> int:
    row = conn.execute(
        """
        WITH inserted_candidate AS (
            INSERT INTO msi_v2.teacher_candidates (
                full_name, phone, email, telegram_username, applied_position,
                position_option_id, subject_id,
                application_date, source_option_id, subsource_option_id,
                age, address,
                source, source_detail, status, stage_changed_at,
                is_application_received, profile_origin,
                version, updated_by_account_id, created_at, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, NULLIF(%s, '')::date, %s, %s, %s, %s, '', '',
                'new_candidate', %s::timestamptz, true, 'application', 1, %s,
                %s::timestamptz, %s::timestamptz
            )
            RETURNING id, application_date, stage_changed_at
        ), inserted_history AS (
            -- The SLA clock starts from the candidate's application date (when they
            -- actually applied), not from the moment HR entered the record, so a
            -- historical application_date immediately reflects elapsed/overdue SLA.
            INSERT INTO msi_v2.teacher_candidate_stage_history (
                candidate_id, stage, entered_at, responsible_account_id,
                comment, transition_source, sla_target_days, sla_due_at
            )
            SELECT candidate.id, 'new_candidate',
                   LEAST(
                       COALESCE(
                           candidate.application_date::timestamp AT TIME ZONE 'Asia/Tashkent',
                           %s::timestamptz
                       ),
                       candidate.stage_changed_at
                   ),
                   %s,
                   'Candidate created.', 'manual', rule.target_days,
                   CASE WHEN rule.target_days IS NULL THEN NULL
                        ELSE COALESCE(candidate.application_date::timestamp AT TIME ZONE 'Asia/Tashkent', %s::timestamptz)
                             + make_interval(days => rule.target_days)
                   END
            FROM inserted_candidate candidate
            LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
              ON rule.stage = 'new_candidate' AND rule.is_active = true
            RETURNING id
        )
        SELECT candidate.id
        FROM inserted_candidate candidate
        JOIN inserted_history history ON true
        """,
        (
            values["full_name"],
            values.get("phone", ""),
            values.get("email", ""),
            values.get("telegram_username", ""),
            values.get("applied_position", ""),
            values.get("position_option_id"),
            values.get("subject_id"),
            values.get("application_date", ""),
            values.get("source_option_id"),
            values.get("subsource_option_id"),
            values.get("age"),
            values.get("address", ""),
            now,
            actor_account_id,
            now,
            now,
            now,
            actor_account_id,
            now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_candidate(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
    expected_version: int | None = None,
) -> bool:
    allowed = {
        "full_name",
        "phone",
        "email",
        "telegram_username",
        "applied_position",
        "position_option_id",
        "subject_id",
        "application_date",
        "age",
        "address",
        "source_option_id",
        "subsource_option_id",
        "english_level_option_id",
        "motivation_expectations",
        "interests_hobbies",
        "schedule_option_id",
        "availability_option_id",
        "education_background",
        "work_experience",
        "teaching_experience_option_id",
        "previous_workplace",
        "expected_salary_option_id",
        "available_start_date",
    }
    assignments: list[str] = []
    params: list[Any] = []
    for key, value in values.items():
        if key not in allowed:
            continue
        if key in {"application_date", "available_start_date"}:
            assignments.append(f"{key} = NULLIF(%s, '')::date")
        else:
            assignments.append(f"{key} = %s")
        params.append(value)
    if not assignments:
        return True
    assignments.extend(
        [
            "updated_by_account_id = %s",
            "updated_at = %s::timestamptz",
            "version = version + 1",
        ]
    )
    version_clause = " AND version = %s" if expected_version else ""
    params.extend([actor_account_id, now, candidate_id])
    if expected_version:
        params.append(int(expected_version))
    cursor = conn.execute(
        f"UPDATE msi_v2.teacher_candidates SET {', '.join(assignments)} WHERE id = %s{version_clause}",
        tuple(params),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def _stage_history_transition_source(value: str) -> str:
    source = str(value or "manual").strip().lower()
    source = _STAGE_HISTORY_TRANSITION_SOURCE_ALIASES.get(source, source)
    if source not in _STAGE_HISTORY_TRANSITION_SOURCES:
        raise ValueError(f"Unsupported stage-history transition source: {value!r}")
    return source


def update_candidate_stage(
    conn: Any,
    *,
    candidate_id: int,
    stage: str,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
    comment: str = "",
    transition_source: str = "manual",
) -> Any:
    transition_source = _stage_history_transition_source(transition_source)
    return conn.execute(
        """
        WITH current_candidate AS (
            SELECT id, status, version
            FROM msi_v2.teacher_candidates
            WHERE id = %s
            FOR UPDATE
        ), updated_candidate AS (
            UPDATE msi_v2.teacher_candidates candidate
            SET status = %s, stage_changed_at = %s::timestamptz,
                updated_at = %s::timestamptz, updated_by_account_id = %s,
                version = candidate.version + 1
            FROM current_candidate current
            WHERE candidate.id = current.id AND current.version = %s
            RETURNING candidate.id, candidate.status, candidate.version,
                      candidate.application_date, candidate.created_at,
                      candidate.stage_changed_at
        ), closed_history AS (
            UPDATE msi_v2.teacher_candidate_stage_history history
            SET entered_at = LEAST(
                    history.entered_at,
                    updated.stage_changed_at,
                    %s::timestamptz
                ),
                exited_at = updated.stage_changed_at
            FROM updated_candidate updated
            WHERE history.candidate_id = updated.id AND history.exited_at IS NULL
            RETURNING history.id
        ), new_history AS (
            -- Landing back on new_candidate (drag out and back in, or a
            -- restore) anchors the SLA to the candidate's actual
            -- application_date, not this transition's timestamp, so it
            -- never resets an already-elapsed/overdue SLA to fresh/green.
            INSERT INTO msi_v2.teacher_candidate_stage_history (
                candidate_id, stage, entered_at, responsible_account_id,
                comment, transition_source, sla_target_days, sla_due_at
            )
            SELECT updated.id, updated.status,
                   LEAST(
                       COALESCE(
                           CASE WHEN updated.status = 'new_candidate'
                                THEN updated.application_date::timestamp AT TIME ZONE 'Asia/Tashkent'
                           END,
                           %s::timestamptz
                       ),
                       updated.stage_changed_at
                   ),
                   %s, %s, %s,
                   definition.sla_target_days,
                   CASE WHEN definition.sla_target_days IS NULL THEN NULL
                        ELSE COALESCE(
                            CASE
                                WHEN definition.stage_kind = 'custom'
                                    THEN COALESCE(
                                        updated.application_date::timestamp AT TIME ZONE 'Asia/Tashkent',
                                        updated.created_at
                                    )
                                WHEN updated.status = 'new_candidate'
                                    THEN updated.application_date::timestamp AT TIME ZONE 'Asia/Tashkent'
                            END,
                            %s::timestamptz
                        ) + make_interval(days => definition.sla_target_days)
                   END
            FROM updated_candidate updated
            CROSS JOIN (SELECT count(*) FROM closed_history) closed
            JOIN msi_v2.teacher_recruitment_pipeline_stages definition
              ON definition.stage_key = updated.status
            RETURNING id
        )
        SELECT updated.id, updated.status, updated.version,
               history.id AS current_stage_history_id
        FROM updated_candidate updated
        JOIN new_history history ON true
        """,
        (
            int(candidate_id),
            stage,
            now,
            now,
            actor_account_id,
            int(expected_version),
            now,
            now,
            actor_account_id,
            comment,
            transition_source,
            now,
        ),
    ).fetchone()


def touch_candidate(
    conn: Any, *, candidate_id: int, actor_account_id: int | None, now: str
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidates
        SET updated_at = %s::timestamptz, updated_by_account_id = %s, version = version + 1
        WHERE id = %s
        """,
        (now, actor_account_id, candidate_id),
    )


def insert_note(
    conn: Any,
    *,
    candidate_id: int,
    body: str,
    actor_account_id: int | None,
    actor_login: str,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_notes (
            candidate_id, body, author_account_id, author_login, created_at
        ) VALUES (%s, %s, %s, %s, %s::timestamptz)
        RETURNING id
        """,
        (candidate_id, body, actor_account_id, actor_login, now),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_audit(
    conn: Any,
    *,
    candidate_id: int,
    event_type: str,
    detail: dict[str, Any],
    actor_account_id: int | None,
    actor_staff_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, actor_account_id, event_type,
            entity_type, entity_id, detail_json, created_at
        ) VALUES (%s, %s, %s, 'teacher_candidate', %s, %s::jsonb, %s::timestamptz)
        """,
        (
            actor_staff_id,
            actor_account_id,
            event_type,
            candidate_id,
            json.dumps(detail, ensure_ascii=False, default=str),
            now,
        ),
    )


__all__ = [
    "_stage_history_transition_source",
    "delete_closed_candidate",
    "insert_audit",
    "insert_candidate",
    "insert_note",
    "list_trash_candidates_for_purge",
    "touch_candidate",
    "update_candidate",
    "update_candidate_stage",
]
