"""PostgreSQL persistence for primary and supplemental subject curricula."""

from __future__ import annotations

import json


def list_teacher_curriculum_variant_rows(conn, teacher_id: int):
    return conn.execute(
        """
        WITH assigned_subjects AS (
            SELECT DISTINCT subject.id, subject.subject_key, subject.subject_name,
                   subject.subject_short
            FROM msi_v2.teachers teacher
            JOIN msi_v2.teacher_subjects teacher_subject
              ON teacher_subject.teacher_id = teacher.id
             AND teacher_subject.status = 'active'
            JOIN msi_v2.subjects subject
              ON subject.id = teacher_subject.subject_id
             AND subject.status = 'active'
            WHERE teacher.id = %s
              AND teacher.status = 'active'
        ),
        primary_variants AS (
            SELECT assigned.id AS subject_id,
                   assigned.subject_key,
                   assigned.subject_name,
                   assigned.subject_short,
                   'primary'::text AS curriculum_key,
                   program.id AS program_id,
                   NULL::bigint AS curriculum_id,
                   'Primary Curriculum'::text AS title,
                   coalesce(program.total_items, 0)::bigint AS item_count,
                   coalesce(program.lesson_count, 0)::bigint AS lesson_count,
                   coalesce(program.exam_count, 0)::bigint AS exam_count,
                   1::bigint AS version,
                   program.updated_at,
                   curriculum_view.last_viewed_at
            FROM assigned_subjects assigned
            LEFT JOIN LATERAL (
                SELECT candidate.*
                FROM msi_v2.subject_programs candidate
                WHERE candidate.subject_id = assigned.id
                  AND candidate.status = 'active'
                ORDER BY candidate.updated_at DESC, candidate.id DESC
                LIMIT 1
            ) program ON true
            LEFT JOIN msi_v2.teacher_curriculum_views curriculum_view
              ON curriculum_view.teacher_id = %s
             AND curriculum_view.subject_id = assigned.id
             AND curriculum_view.curriculum_key = 'primary'
        ),
        supplemental_variants AS (
            SELECT assigned.id AS subject_id,
                   assigned.subject_key,
                   assigned.subject_name,
                   assigned.subject_short,
                   curriculum.curriculum_key,
                   NULL::bigint AS program_id,
                   curriculum.id AS curriculum_id,
                   curriculum.title,
                   count(item.id) FILTER (WHERE item.status = 'active')::bigint AS item_count,
                   count(item.id) FILTER (
                       WHERE item.status = 'active' AND item.item_type = 'lesson'
                   )::bigint AS lesson_count,
                   count(item.id) FILTER (
                       WHERE item.status = 'active' AND item.item_type = 'exam'
                   )::bigint AS exam_count,
                   curriculum.version,
                   greatest(
                       curriculum.updated_at,
                       coalesce(max(item.updated_at), curriculum.updated_at)
                   ) AS updated_at,
                   curriculum_view.last_viewed_at
            FROM assigned_subjects assigned
            JOIN msi_v2.supplemental_curricula curriculum
              ON curriculum.subject_id = assigned.id
             AND curriculum.status = 'active'
            LEFT JOIN msi_v2.supplemental_curriculum_items item
              ON item.curriculum_id = curriculum.id
            LEFT JOIN msi_v2.teacher_curriculum_views curriculum_view
              ON curriculum_view.teacher_id = %s
             AND curriculum_view.subject_id = assigned.id
             AND curriculum_view.curriculum_key = curriculum.curriculum_key
            GROUP BY assigned.id, assigned.subject_key, assigned.subject_name,
                     assigned.subject_short, curriculum.id,
                     curriculum.curriculum_key, curriculum.title,
                     curriculum.version, curriculum.updated_at,
                     curriculum_view.last_viewed_at
        )
        SELECT *
        FROM (
            SELECT * FROM supplemental_variants
            UNION ALL
            SELECT * FROM primary_variants
        ) curriculum_variants
        ORDER BY subject_name,
                 CASE curriculum_key WHEN 'fundamentals' THEN 0 ELSE 1 END,
                 curriculum_key
        """,
        (teacher_id, teacher_id, teacher_id),
    ).fetchall()


def list_director_curriculum_variant_rows(conn):
    return conn.execute(
        """
        WITH primary_variants AS (
            SELECT subject.id AS subject_id,
                   subject.subject_key,
                   subject.subject_name,
                   subject.subject_short,
                   'primary'::text AS curriculum_key,
                   program.id AS program_id,
                   NULL::bigint AS curriculum_id,
                   'Primary Curriculum'::text AS title,
                   coalesce(program.total_items, 0)::bigint AS item_count,
                   coalesce(program.lesson_count, 0)::bigint AS lesson_count,
                   coalesce(program.exam_count, 0)::bigint AS exam_count,
                   1::bigint AS version,
                   program.updated_at,
                   NULL::timestamptz AS last_viewed_at
            FROM msi_v2.subjects subject
            LEFT JOIN LATERAL (
                SELECT candidate.*
                FROM msi_v2.subject_programs candidate
                WHERE candidate.subject_id = subject.id
                  AND candidate.status = 'active'
                ORDER BY candidate.updated_at DESC, candidate.id DESC
                LIMIT 1
            ) program ON true
            WHERE subject.status = 'active'
        ),
        supplemental_variants AS (
            SELECT subject.id AS subject_id,
                   subject.subject_key,
                   subject.subject_name,
                   subject.subject_short,
                   curriculum.curriculum_key,
                   NULL::bigint AS program_id,
                   curriculum.id AS curriculum_id,
                   curriculum.title,
                   count(item.id) FILTER (WHERE item.status = 'active')::bigint AS item_count,
                   count(item.id) FILTER (
                       WHERE item.status = 'active' AND item.item_type = 'lesson'
                   )::bigint AS lesson_count,
                   count(item.id) FILTER (
                       WHERE item.status = 'active' AND item.item_type = 'exam'
                   )::bigint AS exam_count,
                   curriculum.version,
                   greatest(
                       curriculum.updated_at,
                       coalesce(max(item.updated_at), curriculum.updated_at)
                   ) AS updated_at,
                   NULL::timestamptz AS last_viewed_at
            FROM msi_v2.subjects subject
            JOIN msi_v2.supplemental_curricula curriculum
              ON curriculum.subject_id = subject.id
             AND curriculum.status = 'active'
            LEFT JOIN msi_v2.supplemental_curriculum_items item
              ON item.curriculum_id = curriculum.id
            WHERE subject.status = 'active'
            GROUP BY subject.id, subject.subject_key, subject.subject_name,
                     subject.subject_short, curriculum.id,
                     curriculum.curriculum_key, curriculum.title,
                     curriculum.version, curriculum.updated_at
        )
        SELECT *
        FROM (
            SELECT * FROM supplemental_variants
            UNION ALL
            SELECT * FROM primary_variants
        ) curriculum_variants
        ORDER BY subject_name,
                 CASE curriculum_key WHEN 'fundamentals' THEN 0 ELSE 1 END,
                 curriculum_key
        """
    ).fetchall()


def teacher_has_subject(conn, teacher_id: int, subject_id: int) -> bool:
    return bool(
        conn.execute(
            """
            SELECT 1
            FROM msi_v2.teachers teacher
            JOIN msi_v2.teacher_subjects teacher_subject
              ON teacher_subject.teacher_id = teacher.id
             AND teacher_subject.status = 'active'
            JOIN msi_v2.subjects subject
              ON subject.id = teacher_subject.subject_id
             AND subject.status = 'active'
            WHERE teacher.id = %s
              AND teacher.status = 'active'
              AND subject.id = %s
            """,
            (teacher_id, subject_id),
        ).fetchone()
    )


def get_subject_row(conn, subject_id: int):
    return conn.execute(
        """
        SELECT id, subject_key, subject_name, subject_short
        FROM msi_v2.subjects
        WHERE id = %s AND status = 'active'
        """,
        (subject_id,),
    ).fetchone()


def get_primary_variant_row(conn, subject_id: int):
    return conn.execute(
        """
        SELECT program.id AS program_id,
               program.subject_id,
               'primary'::text AS curriculum_key,
               'Primary Curriculum'::text AS title,
               program.total_items::bigint AS item_count,
               program.lesson_count::bigint AS lesson_count,
               program.exam_count::bigint AS exam_count,
               program.updated_at,
               1::bigint AS version
        FROM msi_v2.subject_programs program
        WHERE program.subject_id = %s
          AND program.status = 'active'
        ORDER BY program.updated_at DESC, program.id DESC
        LIMIT 1
        """,
        (subject_id,),
    ).fetchone()


def get_supplemental_variant_row(
    conn,
    subject_id: int,
    curriculum_key: str,
):
    return conn.execute(
        """
        SELECT curriculum.id AS curriculum_id,
               curriculum.subject_id,
               curriculum.curriculum_key,
               curriculum.title,
               curriculum.status,
               curriculum.version,
               curriculum.updated_at,
               count(item.id) FILTER (WHERE item.status = 'active')::bigint AS item_count,
               count(item.id) FILTER (
                   WHERE item.status = 'active' AND item.item_type = 'lesson'
               )::bigint AS lesson_count,
               count(item.id) FILTER (
                   WHERE item.status = 'active' AND item.item_type = 'exam'
               )::bigint AS exam_count
        FROM msi_v2.supplemental_curricula curriculum
        LEFT JOIN msi_v2.supplemental_curriculum_items item
          ON item.curriculum_id = curriculum.id
        WHERE curriculum.subject_id = %s
          AND curriculum.curriculum_key = %s
          AND curriculum.status = 'active'
        GROUP BY curriculum.id
        """,
        (subject_id, curriculum_key),
    ).fetchone()


def lock_supplemental_curriculum(conn, curriculum_id: int):
    return conn.execute(
        """
        SELECT id, subject_id, curriculum_key, title, status, version, updated_at
        FROM msi_v2.supplemental_curricula
        WHERE id = %s AND status = 'active'
        FOR UPDATE
        """,
        (curriculum_id,),
    ).fetchone()


def list_primary_item_rows(conn, program_id: int):
    return conn.execute(
        """
        SELECT item.id AS item_id,
               item.item_order,
               item.lesson_number,
               item.item_type,
               item.title,
               item.term_label,
               item.week_label,
               item.specification_points,
               item.book_pages,
               item.lesson_count,
               item.duration_hours,
               '[]'::jsonb AS content_json,
               '{}'::jsonb AS guidance_json,
               'active'::text AS status,
               1::bigint AS version,
               item.updated_at
        FROM msi_v2.subject_program_items item
        WHERE item.program_id = %s
        ORDER BY item.item_order, item.id
        """,
        (program_id,),
    ).fetchall()


def list_supplemental_item_rows(
    conn,
    curriculum_id: int,
    *,
    include_archived: bool,
):
    status_sql = "" if include_archived else "AND item.status = 'active'"
    return conn.execute(
        f"""
        SELECT item.id AS item_id,
               item.item_order,
               item.lesson_number,
               item.item_type,
               item.title,
               item.term_label,
               item.week_label,
               item.specification_points,
               item.book_pages,
               item.lesson_count,
               item.duration_hours,
               item.content_json,
               item.guidance_json,
               item.status,
               item.version,
               item.updated_at
        FROM msi_v2.supplemental_curriculum_items item
        WHERE item.curriculum_id = %s
          {status_sql}
        ORDER BY
          CASE item.status WHEN 'active' THEN 0 ELSE 1 END,
          item.item_order,
          item.id
        """,
        (curriculum_id,),
    ).fetchall()


def list_asset_rows(conn, item_ids: list[int], *, include_archived: bool = False):
    if not item_ids:
        return []
    status_sql = "" if include_archived else "AND asset.status = 'active'"
    return conn.execute(
        f"""
        SELECT asset.id AS asset_id,
               asset.item_id,
               asset.asset_kind,
               asset.title,
               asset.external_url,
               asset.object_key,
               asset.original_file_name,
               asset.mime_type,
               asset.size_bytes,
               asset.display_order,
               asset.status,
               asset.version
        FROM msi_v2.supplemental_curriculum_assets asset
        WHERE asset.item_id = ANY(%s)
          {status_sql}
        ORDER BY asset.item_id, asset.display_order, asset.id
        """,
        (item_ids,),
    ).fetchall()


def get_supplemental_item_row(conn, item_id: int, *, for_update: bool = False):
    lock_sql = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT item.*, curriculum.subject_id, curriculum.curriculum_key
        FROM msi_v2.supplemental_curriculum_items item
        JOIN msi_v2.supplemental_curricula curriculum
          ON curriculum.id = item.curriculum_id
        WHERE item.id = %s
        {lock_sql}
        """,
        (item_id,),
    ).fetchone()


def insert_supplemental_item(
    conn,
    *,
    curriculum_id: int,
    item_order: int,
    payload: dict[str, object],
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_items (
            curriculum_id, item_order, lesson_number, item_type, title,
            term_label, week_label, specification_points, book_pages,
            lesson_count, duration_hours, content_json, guidance_json, status, version,
            created_by_staff_id, updated_by_staff_id, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, 'lesson', %s, '', '', '', '', '', '', '[]'::jsonb, %s::jsonb,
            'active', 1, %s, %s, now(), now()
        )
        RETURNING id
        """,
        (
            curriculum_id,
            item_order,
            payload["lesson_number"],
            payload["title"],
            json.dumps(payload["guidance"], ensure_ascii=False),
            actor_staff_id,
            actor_staff_id,
        ),
    ).fetchone()


def update_supplemental_item(
    conn,
    *,
    item_id: int,
    expected_version: int,
    payload: dict[str, object],
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_items
        SET title = %s,
            guidance_json = %s::jsonb,
            updated_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND status = 'active'
          AND version = %s
        RETURNING id, version
        """,
        (
            payload["title"],
            json.dumps(payload["guidance"], ensure_ascii=False),
            actor_staff_id,
            item_id,
            expected_version,
        ),
    ).fetchone()


def next_active_item_order(conn, curriculum_id: int) -> int:
    row = conn.execute(
        """
        SELECT coalesce(max(item_order), 0) + 1 AS next_order
        FROM msi_v2.supplemental_curriculum_items
        WHERE curriculum_id = %s AND status = 'active'
        """,
        (curriculum_id,),
    ).fetchone()
    return int(row["next_order"] or 1)


def list_active_item_ids_for_update(conn, curriculum_id: int) -> list[int]:
    rows = conn.execute(
        """
        SELECT id
        FROM msi_v2.supplemental_curriculum_items
        WHERE curriculum_id = %s AND status = 'active'
        ORDER BY item_order, id
        FOR UPDATE
        """,
        (curriculum_id,),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def reorder_active_items(conn, curriculum_id: int, item_ids: list[int]) -> None:
    conn.execute(
        """
        WITH boundary AS (
            SELECT coalesce(max(item_order), 0) + count(*) + 1 AS offset
            FROM msi_v2.supplemental_curriculum_items
            WHERE curriculum_id = %s AND status = 'active'
        )
        UPDATE msi_v2.supplemental_curriculum_items
        SET item_order = item_order + boundary.offset,
            updated_at = now()
        FROM boundary
        WHERE curriculum_id = %s AND status = 'active'
        """,
        (curriculum_id, curriculum_id),
    )
    for item_order, item_id in enumerate(item_ids, start=1):
        conn.execute(
            """
            UPDATE msi_v2.supplemental_curriculum_items
            SET item_order = %s, version = version + 1, updated_at = now()
            WHERE curriculum_id = %s AND id = %s AND status = 'active'
            """,
            (item_order, curriculum_id, item_id),
        )


def archive_item(
    conn,
    *,
    item_id: int,
    expected_version: int,
    reason: str,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_items
        SET status = 'archived',
            archived_at = now(),
            archived_by_staff_id = %s,
            archive_reason = %s,
            updated_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND status = 'active'
          AND version = %s
        RETURNING id, curriculum_id
        """,
        (actor_staff_id, reason, actor_staff_id, item_id, expected_version),
    ).fetchone()


def restore_item(
    conn,
    *,
    item_id: int,
    expected_version: int,
    item_order: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_items
        SET status = 'active',
            item_order = %s,
            archived_at = NULL,
            archived_by_staff_id = NULL,
            archive_reason = '',
            updated_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND status = 'archived'
          AND version = %s
        RETURNING id, curriculum_id
        """,
        (item_order, actor_staff_id, item_id, expected_version),
    ).fetchone()


def touch_curriculum(
    conn,
    curriculum_id: int,
    *,
    actor_staff_id: int | None,
    expected_version: int | None = None,
):
    version_sql = "AND version = %s" if expected_version is not None else ""
    params: tuple[object, ...] = (
        actor_staff_id,
        curriculum_id,
        *((expected_version,) if expected_version is not None else ()),
    )
    return conn.execute(
        f"""
        UPDATE msi_v2.supplemental_curricula
        SET version = version + 1,
            updated_by_staff_id = %s,
            updated_at = now()
        WHERE id = %s
          AND status = 'active'
          {version_sql}
        RETURNING id, version
        """,
        params,
    ).fetchone()


def insert_external_asset(
    conn,
    *,
    item_id: int,
    asset_kind: str,
    title: str,
    external_url: str,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_assets (
            item_id, asset_kind, title, external_url, display_order,
            status, version, created_by_staff_id, created_at, updated_at
        )
        SELECT %s, %s, %s, %s, coalesce(max(display_order), 0) + 1,
               'active', 1, %s, now(), now()
        FROM msi_v2.supplemental_curriculum_assets
        WHERE item_id = %s
        RETURNING id
        """,
        (item_id, asset_kind, title, external_url, actor_staff_id, item_id),
    ).fetchone()


def insert_file_asset(
    conn,
    *,
    item_id: int,
    title: str,
    object_key: str,
    original_file_name: str,
    mime_type: str,
    size_bytes: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_assets (
            item_id, asset_kind, title, object_key, original_file_name,
            mime_type, size_bytes, display_order, status, version,
            created_by_staff_id, created_at, updated_at
        )
        SELECT %s, 'file', %s, %s, %s, %s, %s,
               coalesce(max(display_order), 0) + 1,
               'active', 1, %s, now(), now()
        FROM msi_v2.supplemental_curriculum_assets
        WHERE item_id = %s
        RETURNING id
        """,
        (
            item_id,
            title,
            object_key,
            original_file_name,
            mime_type,
            size_bytes,
            actor_staff_id,
            item_id,
        ),
    ).fetchone()


def get_asset_row(conn, asset_id: int):
    return conn.execute(
        """
        SELECT asset.*,
               item.curriculum_id,
               item.status AS item_status,
               curriculum.subject_id,
               curriculum.curriculum_key,
               curriculum.status AS curriculum_status
        FROM msi_v2.supplemental_curriculum_assets asset
        JOIN msi_v2.supplemental_curriculum_items item ON item.id = asset.item_id
        JOIN msi_v2.supplemental_curricula curriculum
          ON curriculum.id = item.curriculum_id
        WHERE asset.id = %s
        """,
        (asset_id,),
    ).fetchone()


def archive_asset(
    conn,
    *,
    asset_id: int,
    expected_version: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_assets
        SET status = 'archived',
            archived_at = now(),
            archived_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND status = 'active'
          AND version = %s
        RETURNING id, item_id
        """,
        (actor_staff_id, asset_id, expected_version),
    ).fetchone()


def upsert_teacher_curriculum_view(
    conn,
    *,
    teacher_id: int,
    subject_id: int,
    curriculum_key: str,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.teacher_curriculum_views (
            teacher_id, subject_id, curriculum_key, last_viewed_at, updated_at
        )
        VALUES (%s, %s, %s, now(), now())
        ON CONFLICT (teacher_id, subject_id, curriculum_key)
        DO UPDATE SET last_viewed_at = excluded.last_viewed_at, updated_at = now()
        RETURNING last_viewed_at
        """,
        (teacher_id, subject_id, curriculum_key),
    ).fetchone()


def insert_audit_event(
    conn,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int,
    detail: dict[str, object],
    actor_staff_id: int | None,
):
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, event_type, entity_type, entity_id,
            detail_json, created_at
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, now())
        """,
        (
            actor_staff_id,
            event_type,
            entity_type,
            entity_id,
            json.dumps(detail, ensure_ascii=False),
        ),
    )


__all__ = [
    "archive_asset",
    "archive_item",
    "get_asset_row",
    "get_primary_variant_row",
    "get_subject_row",
    "get_supplemental_item_row",
    "get_supplemental_variant_row",
    "insert_audit_event",
    "insert_external_asset",
    "insert_file_asset",
    "insert_supplemental_item",
    "list_active_item_ids_for_update",
    "list_asset_rows",
    "list_director_curriculum_variant_rows",
    "list_primary_item_rows",
    "list_supplemental_item_rows",
    "list_teacher_curriculum_variant_rows",
    "lock_supplemental_curriculum",
    "next_active_item_order",
    "reorder_active_items",
    "restore_item",
    "teacher_has_subject",
    "touch_curriculum",
    "update_supplemental_item",
    "upsert_teacher_curriculum_view",
]
