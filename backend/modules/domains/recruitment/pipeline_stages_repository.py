"""Persistence for configurable Recruitment pipeline stages."""

from __future__ import annotations

import json
from typing import Any, Iterable


_STAGE_COLUMNS = """
    stage.id,
    stage.stage_key,
    stage.label,
    stage.stage_kind,
    stage.color_token,
    stage.sort_order,
    stage.is_pipeline,
    stage.is_active,
    stage.replacement_stage_key,
    stage.sla_target_days,
    stage.version,
    stage.created_at::text AS created_at,
    stage.updated_at::text AS updated_at,
    stage.archived_at::text AS archived_at
"""


def list_pipeline_stage_rows(
    conn: Any,
    *,
    include_inactive: bool = False,
    pipeline_only: bool = True,
) -> list[Any]:
    clauses: list[str] = []
    if pipeline_only:
        clauses.append("stage.is_pipeline = true")
    if not include_inactive:
        clauses.append("stage.is_active = true")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return conn.execute(
        f"""
        SELECT {_STAGE_COLUMNS}
        FROM msi_v2.teacher_recruitment_pipeline_stages stage
        {where_sql}
        ORDER BY stage.sort_order, stage.id
        """
    ).fetchall()


def pipeline_stage_by_key(conn: Any, stage_key: str, *, for_update: bool = False) -> Any:
    return conn.execute(
        f"""
        SELECT {_STAGE_COLUMNS}
        FROM msi_v2.teacher_recruitment_pipeline_stages stage
        WHERE stage.stage_key = %s
        LIMIT 1
        {'FOR UPDATE' if for_update else ''}
        """,
        (stage_key,),
    ).fetchone()


def active_pipeline_stage_by_key(conn: Any, stage_key: str) -> Any:
    return conn.execute(
        f"""
        SELECT {_STAGE_COLUMNS}
        FROM msi_v2.teacher_recruitment_pipeline_stages stage
        WHERE stage.stage_key = %s
          AND stage.is_pipeline = true
          AND stage.is_active = true
        LIMIT 1
        """,
        (stage_key,),
    ).fetchone()


def pipeline_stage_label_exists(
    conn: Any,
    *,
    label: str,
    exclude_stage_key: str = "",
) -> bool:
    return bool(
        conn.execute(
            """
            SELECT 1
            FROM msi_v2.teacher_recruitment_pipeline_stages stage
            WHERE lower(btrim(stage.label)) = lower(btrim(%s))
              AND (%s = '' OR stage.stage_key <> %s)
            LIMIT 1
            """,
            (label, exclude_stage_key, exclude_stage_key),
        ).fetchone()
    )


def insert_pipeline_stage(
    conn: Any,
    *,
    stage_key: str,
    label: str,
    color_token: str,
    sla_target_days: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        f"""
        INSERT INTO msi_v2.teacher_recruitment_pipeline_stages (
            stage_key, label, stage_kind, color_token, sort_order,
            is_pipeline, is_active, sla_target_days,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, 'custom', %s, 2147480000,
            true, true, %s, %s, %s, %s::timestamptz, %s::timestamptz
        )
        RETURNING {_STAGE_COLUMNS.replace('stage.', '')}
        """,
        (
            stage_key,
            label,
            color_token,
            int(sla_target_days),
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()


def insert_pipeline_stage_sla_rule(
    conn: Any,
    *,
    stage_key: str,
    target_days: int,
    actor_account_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_recruitment_sla_rules (
            stage, target_days, is_active, updated_by_account_id, created_at, updated_at
        ) VALUES (%s, %s, true, %s, %s::timestamptz, %s::timestamptz)
        ON CONFLICT (stage) DO UPDATE
        SET target_days = EXCLUDED.target_days,
            is_active = true,
            updated_by_account_id = EXCLUDED.updated_by_account_id,
            updated_at = EXCLUDED.updated_at
        """,
        (stage_key, int(target_days), actor_account_id, now, now),
    )


def update_pipeline_stage(
    conn: Any,
    *,
    stage_key: str,
    label: str,
    color_token: str,
    sla_target_days: int,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        f"""
        UPDATE msi_v2.teacher_recruitment_pipeline_stages stage
        SET label = %s,
            color_token = CASE WHEN stage.stage_kind = 'custom' THEN %s ELSE stage.color_token END,
            sla_target_days = CASE WHEN stage.stage_kind = 'custom' THEN %s ELSE stage.sla_target_days END,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz,
            version = stage.version + 1
        WHERE stage.stage_key = %s
          AND stage.is_pipeline = true
          AND stage.is_active = true
          AND stage.version = %s
        RETURNING {_STAGE_COLUMNS}
        """,
        (
            label,
            color_token,
            int(sla_target_days),
            actor_account_id,
            now,
            stage_key,
            int(expected_version),
        ),
    ).fetchone()


def update_pipeline_stage_sla_rule(
    conn: Any,
    *,
    stage_key: str,
    target_days: int,
    actor_account_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_sla_rules
        SET target_days = %s,
            is_active = true,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE stage = %s
        """,
        (int(target_days), actor_account_id, now, stage_key),
    )


def reorder_pipeline_stages(conn: Any, ordered_stage_keys: Iterable[str]) -> None:
    for index, stage_key in enumerate(ordered_stage_keys, start=1):
        conn.execute(
            """
            UPDATE msi_v2.teacher_recruitment_pipeline_stages
            SET sort_order = %s
            WHERE stage_key = %s AND is_pipeline = true AND is_active = true
            """,
            (index * 10, stage_key),
        )


def list_candidate_stage_rows_for_update(conn: Any, stage_key: str) -> list[Any]:
    return conn.execute(
        """
        SELECT id, status, version
        FROM msi_v2.teacher_candidates
        WHERE status = %s
        ORDER BY id
        FOR UPDATE
        """,
        (stage_key,),
    ).fetchall()


def archive_pipeline_stage(
    conn: Any,
    *,
    stage_key: str,
    replacement_stage_key: str,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    row = conn.execute(
        f"""
        UPDATE msi_v2.teacher_recruitment_pipeline_stages stage
        SET is_active = false,
            replacement_stage_key = %s,
            archived_at = %s::timestamptz,
            archived_by_account_id = %s,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz,
            version = stage.version + 1
        WHERE stage.stage_key = %s
          AND stage.stage_kind = 'custom'
          AND stage.is_active = true
          AND stage.version = %s
        RETURNING {_STAGE_COLUMNS}
        """,
        (
            replacement_stage_key,
            now,
            actor_account_id,
            actor_account_id,
            now,
            stage_key,
            int(expected_version),
        ),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE msi_v2.teacher_recruitment_sla_rules
            SET is_active = false,
                updated_by_account_id = %s,
                updated_at = %s::timestamptz
            WHERE stage = %s
            """,
            (actor_account_id, now, stage_key),
        )
    return row


def resolve_active_pipeline_stage_key(conn: Any, stage_key: str) -> str:
    row = conn.execute(
        """
        WITH RECURSIVE replacement AS (
            SELECT stage_key, replacement_stage_key, is_pipeline, is_active, 1 AS depth
            FROM msi_v2.teacher_recruitment_pipeline_stages
            WHERE stage_key = %s
            UNION ALL
            SELECT next_stage.stage_key, next_stage.replacement_stage_key,
                   next_stage.is_pipeline, next_stage.is_active, replacement.depth + 1
            FROM replacement
            JOIN msi_v2.teacher_recruitment_pipeline_stages next_stage
              ON next_stage.stage_key = replacement.replacement_stage_key
            WHERE replacement.depth < 20
        )
        SELECT stage_key
        FROM replacement
        WHERE is_pipeline = true AND is_active = true
        ORDER BY depth
        LIMIT 1
        """,
        (stage_key,),
    ).fetchone()
    return str(row["stage_key"]) if row else ""


def insert_pipeline_stage_audit(
    conn: Any,
    *,
    stage_id: int,
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
        ) VALUES (
            %s, %s, %s, 'teacher_recruitment_pipeline_stage', %s,
            %s::jsonb, %s::timestamptz
        )
        """,
        (
            actor_staff_id,
            actor_account_id,
            event_type,
            int(stage_id),
            json.dumps(detail, ensure_ascii=False, default=str),
            now,
        ),
    )


__all__ = [name for name in globals() if not name.startswith("_")]
