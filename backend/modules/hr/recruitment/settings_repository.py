"""PostgreSQL persistence for Recruitment settings."""

from __future__ import annotations

import json
from typing import Any


def list_recruitment_setting_rows(
    conn: Any,
    *,
    include_inactive: bool = False,
) -> list[Any]:
    active_clause = "" if include_inactive else "WHERE is_active = true"
    return conn.execute(
        f"""
        SELECT id, category, value, label, parent_id, is_active, sort_order,
               is_system, is_legacy,
               created_at::text AS created_at, updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_settings
        {active_clause}
        ORDER BY category, parent_id NULLS FIRST, sort_order, lower(label), id
        """
    ).fetchall()


def list_sla_rule_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT rule.stage, rule.target_days, rule.is_active,
               stage.label AS stage_label,
               stage.stage_kind, stage.color_token, stage.sort_order,
               rule.updated_by_account_id,
               COALESCE(account.full_name, account.login, '') AS updated_by,
               rule.updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_sla_rules rule
        JOIN msi_v2.teacher_recruitment_pipeline_stages stage
          ON stage.stage_key = rule.stage
        LEFT JOIN msi_v2.accounts account ON account.id = rule.updated_by_account_id
        WHERE stage.is_pipeline = true AND stage.is_active = true
          AND stage.stage_kind = 'system'
        ORDER BY stage.sort_order, stage.id
        """
    ).fetchall()


def update_sla_rule(
    conn: Any,
    *,
    stage: str,
    target_days: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    row = conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_sla_rules
        SET target_days = %s,
            is_active = true,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE stage = %s
        RETURNING stage, target_days, is_active, updated_by_account_id,
                  updated_at::text AS updated_at
        """,
        (int(target_days), actor_account_id, now, stage),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE msi_v2.teacher_recruitment_pipeline_stages
            SET sla_target_days = %s,
                updated_by_account_id = %s,
                updated_at = %s::timestamptz,
                version = version + 1
            WHERE stage_key = %s
            """,
            (int(target_days), actor_account_id, now, stage),
        )
    return row


def recruitment_setting_by_label_or_value(
    conn: Any,
    *,
    category: str,
    value: str,
    label: str,
    parent_id: int | None = None,
) -> Any:
    return conn.execute(
        """
        SELECT id, category, value, label, parent_id, is_active, sort_order,
               is_system, is_legacy,
               created_at::text AS created_at, updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_settings
        WHERE category = %s
          AND (value = %s OR lower(btrim(label)) = lower(btrim(%s)))
          AND parent_id IS NOT DISTINCT FROM %s
        ORDER BY id
        LIMIT 1
        FOR UPDATE
        """,
        (category, value, label, parent_id),
    ).fetchone()


def active_subsource_exists(conn: Any, source_option_id: int) -> bool:
    return bool(
        conn.execute(
            """
            SELECT 1 FROM msi_v2.teacher_recruitment_settings
            WHERE category = 'subsource' AND parent_id = %s AND is_active = true
            LIMIT 1
            """,
            (int(source_option_id),),
        ).fetchone()
    )


def recruitment_setting_by_id(conn: Any, setting_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, category, value, label, parent_id, is_active, sort_order,
               is_system, is_legacy
        FROM msi_v2.teacher_recruitment_settings
        WHERE id = %s
        LIMIT 1
        """,
        (int(setting_id),),
    ).fetchone()


def save_recruitment_setting(
    conn: Any,
    *,
    existing_id: int | None,
    category: str,
    value: str,
    label: str,
    parent_id: int | None,
    actor_account_id: int | None,
    now: str,
) -> Any:
    if existing_id:
        return conn.execute(
            """
            UPDATE msi_v2.teacher_recruitment_settings
            SET is_active = true,
                updated_by_account_id = %s,
                updated_at = %s::timestamptz
            WHERE id = %s
            RETURNING id, category, value, label, parent_id, is_active,
                      sort_order, is_system, is_legacy,
                      created_at::text AS created_at, updated_at::text AS updated_at
            """,
            (actor_account_id, now, int(existing_id)),
        ).fetchone()
    return conn.execute(
        """
        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, parent_id, sort_order,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s,
            COALESCE((
                SELECT max(sort_order) + 10
                FROM msi_v2.teacher_recruitment_settings
                WHERE category = %s AND parent_id IS NOT DISTINCT FROM %s
            ), 10),
            %s, %s, %s::timestamptz, %s::timestamptz
        )
        RETURNING id, category, value, label, parent_id, is_active,
                  sort_order, is_system, is_legacy,
                  created_at::text AS created_at, updated_at::text AS updated_at
        """,
        (
            category,
            value,
            label,
            parent_id,
            category,
            parent_id,
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()


def rename_recruitment_setting(
    conn: Any,
    *,
    setting_id: int,
    label: str,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_settings
        SET label = %s,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s AND is_system = false
        RETURNING id, category, value, label, parent_id, is_active,
                  sort_order, is_system, is_legacy,
                  created_at::text AS created_at, updated_at::text AS updated_at
        """,
        (label, actor_account_id, now, int(setting_id)),
    ).fetchone()


def recruitment_setting_usage_counts(conn: Any) -> dict[int, int]:
    """Map setting id -> number of candidates/decisions referencing it."""

    option_rows = conn.execute(
        """
        SELECT setting_id, count(*) AS usage_count
        FROM (
            SELECT source_option_id AS setting_id FROM msi_v2.teacher_candidates
            WHERE source_option_id IS NOT NULL
            UNION ALL
            SELECT subsource_option_id FROM msi_v2.teacher_candidates
            WHERE subsource_option_id IS NOT NULL
            UNION ALL
            SELECT position_option_id FROM msi_v2.teacher_candidates
            WHERE position_option_id IS NOT NULL
            UNION ALL
            SELECT english_level_option_id FROM msi_v2.teacher_candidates
            WHERE english_level_option_id IS NOT NULL
            UNION ALL
            SELECT schedule_option_id FROM msi_v2.teacher_candidates
            WHERE schedule_option_id IS NOT NULL
            UNION ALL
            SELECT availability_option_id FROM msi_v2.teacher_candidates
            WHERE availability_option_id IS NOT NULL
            UNION ALL
            SELECT teaching_experience_option_id FROM msi_v2.teacher_candidates
            WHERE teaching_experience_option_id IS NOT NULL
            UNION ALL
            SELECT expected_salary_option_id FROM msi_v2.teacher_candidates
            WHERE expected_salary_option_id IS NOT NULL
        ) usage
        GROUP BY setting_id
        """
    ).fetchall()
    reason_rows = conn.execute(
        """
        SELECT s.id AS setting_id, count(d.id) AS usage_count
        FROM msi_v2.teacher_recruitment_settings s
        JOIN msi_v2.teacher_candidate_final_decisions d ON d.rejection_reason = s.value
        WHERE s.category = 'rejection_reason'
        GROUP BY s.id
        """
    ).fetchall()
    counts: dict[int, int] = {}
    for row in (*option_rows, *reason_rows):
        row = dict(row)
        counts[int(row["setting_id"])] = counts.get(int(row["setting_id"]), 0) + int(
            row["usage_count"]
        )
    return counts


def deactivate_recruitment_setting(
    conn: Any,
    *,
    setting_id: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_settings
        SET is_active = false,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s AND is_active = true AND is_system = false
        RETURNING id, category, value, label, parent_id, is_active,
                  sort_order, is_system, is_legacy,
                  created_at::text AS created_at, updated_at::text AS updated_at
        """,
        (actor_account_id, now, int(setting_id)),
    ).fetchone()


def recruitment_setting_value_exists(conn: Any, *, category: str, value: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM msi_v2.teacher_recruitment_settings
        WHERE category = %s AND value = %s AND is_active = true
        LIMIT 1
        """,
        (category, value),
    ).fetchone()
    return bool(row)


def insert_recruitment_setting_audit(
    conn: Any,
    *,
    setting_id: int,
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
        ) VALUES (%s, %s, %s, 'teacher_recruitment_setting', %s, %s::jsonb, %s::timestamptz)
        """,
        (
            actor_staff_id,
            actor_account_id,
            event_type,
            setting_id,
            json.dumps(detail, ensure_ascii=False, default=str),
            now,
        ),
    )


def list_recruitment_options(conn: Any) -> dict[str, Any]:
    subject_rows = conn.execute(
        """
        SELECT id, subject_name AS name
        FROM msi_v2.subjects WHERE status = 'active'
        ORDER BY subject_name
        """
    ).fetchall()
    staff_rows = conn.execute(
        """
        SELECT id, role, COALESCE(NULLIF(full_name, ''), login) AS name, login
        FROM msi_v2.accounts
        WHERE status = 'active'
          AND role IN ('ceo', 'hr_manager', 'academic_director', 'head_of_department')
        ORDER BY role, lower(COALESCE(NULLIF(full_name, ''), login))
        """
    ).fetchall()
    setting_rows = list_recruitment_setting_rows(conn)
    option_items = [dict(row) for row in setting_rows]
    option_categories = {
        category: [item for item in option_items if item["category"] == category]
        for category in (
            "source",
            "subsource",
            "position",
            "english_level",
            "schedule",
            "availability",
            "expected_salary",
            "teaching_experience",
        )
    }
    rejection_reason_options = [
        {"value": str(row["value"]), "label": str(row["label"])}
        for row in setting_rows
        if row["category"] == "rejection_reason"
    ]
    return {
        "subjects": [dict(row) for row in subject_rows],
        "staff": [dict(row) for row in staff_rows],
        "sources": option_categories["source"],
        "subsources": option_categories["subsource"],
        "option_categories": option_categories,
        "rejection_reason_options": rejection_reason_options,
    }


__all__ = [
    "active_subsource_exists",
    "deactivate_recruitment_setting",
    "insert_recruitment_setting_audit",
    "list_recruitment_options",
    "list_recruitment_setting_rows",
    "list_sla_rule_rows",
    "recruitment_setting_by_id",
    "recruitment_setting_by_label_or_value",
    "recruitment_setting_usage_counts",
    "recruitment_setting_value_exists",
    "rename_recruitment_setting",
    "save_recruitment_setting",
    "update_sla_rule",
]
