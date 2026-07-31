"""PostgreSQL persistence for private curriculum drafts and media renditions."""

from __future__ import annotations

import json


def insert_draft_item(
    conn,
    *,
    curriculum_id: int,
    item_order: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_items (
            curriculum_id, item_order, lesson_number, item_type, title,
            term_label, week_label, specification_points, book_pages,
            lesson_count, duration_hours, content_json, guidance_json,
            status, version, created_by_staff_id, updated_by_staff_id,
            created_at, updated_at
        )
        VALUES (
            %s, %s, %s, 'lesson', 'Untitled Fundamentals lesson',
            '', '', '', '', '', '', '[]'::jsonb,
            '{"overview":"","tags":[],"duration_minutes":0,"before_teaching":[],"sections":[]}'::jsonb,
            'draft', 1, %s, %s, now(), now()
        )
        RETURNING id, version
        """,
        (
            curriculum_id,
            item_order,
            f"DRAFT-{item_order:02d}",
            actor_staff_id,
            actor_staff_id,
        ),
    ).fetchone()


def get_item_draft_row(conn, item_id: int, *, for_update: bool = False):
    lock_sql = "FOR UPDATE OF revision" if for_update else ""
    return conn.execute(
        f"""
        SELECT revision.*,
               item.curriculum_id,
               item.status AS item_status,
               item.published_revision_id,
               curriculum.subject_id,
               curriculum.curriculum_key
        FROM msi_v2.supplemental_curriculum_item_revisions revision
        JOIN msi_v2.supplemental_curriculum_items item ON item.id = revision.item_id
        JOIN msi_v2.supplemental_curricula curriculum
          ON curriculum.id = item.curriculum_id
        WHERE revision.item_id = %s
          AND revision.state = 'draft'
        {lock_sql}
        """,
        (item_id,),
    ).fetchone()


def get_draft_row(conn, draft_id: int, *, for_update: bool = False):
    lock_sql = "FOR UPDATE OF revision, item" if for_update else ""
    return conn.execute(
        f"""
        SELECT revision.*,
               item.curriculum_id,
               item.status AS item_status,
               item.published_revision_id,
               item.item_order,
               item.lesson_number,
               item.version AS item_version,
               curriculum.subject_id,
               curriculum.curriculum_key,
               curriculum.status AS curriculum_status
        FROM msi_v2.supplemental_curriculum_item_revisions revision
        JOIN msi_v2.supplemental_curriculum_items item ON item.id = revision.item_id
        JOIN msi_v2.supplemental_curricula curriculum
          ON curriculum.id = item.curriculum_id
        WHERE revision.id = %s
        {lock_sql}
        """,
        (draft_id,),
    ).fetchone()


def insert_draft_revision(
    conn,
    *,
    item_id: int,
    title: str,
    guidance: dict[str, object],
    base_item_version: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_item_revisions (
            item_id, revision_number, state, title, guidance_json,
            base_item_version, version, created_by_staff_id,
            updated_by_staff_id, created_at, updated_at
        )
        SELECT %s, coalesce(max(revision_number), 0) + 1, 'draft', %s, %s::jsonb,
               %s, 1, %s, %s, now(), now()
        FROM msi_v2.supplemental_curriculum_item_revisions
        WHERE item_id = %s
        RETURNING *
        """,
        (
            item_id,
            title,
            json.dumps(guidance, ensure_ascii=False),
            base_item_version,
            actor_staff_id,
            actor_staff_id,
            item_id,
        ),
    ).fetchone()


def copy_published_asset_placements(
    conn,
    *,
    published_revision_id: int,
    draft_revision_id: int,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_revision_assets (
            revision_id, asset_id, block_key, section_key, content_area,
            display_order, status, version, created_at, updated_at
        )
        SELECT %s, asset_id, block_key, section_key, content_area,
               display_order, status, 1, now(), now()
        FROM msi_v2.supplemental_curriculum_revision_assets
        WHERE revision_id = %s
          AND status = 'active'
        ON CONFLICT (revision_id, asset_id, block_key) DO NOTHING
        """,
        (draft_revision_id, published_revision_id),
    )


def list_revision_asset_rows(
    conn,
    revision_id: int,
    *,
    include_archived: bool = False,
):
    status_sql = "" if include_archived else "AND placement.status = 'active'"
    return conn.execute(
        f"""
        SELECT asset.id AS asset_id,
               asset.item_id,
               asset.asset_kind,
               asset.render_kind,
               asset.title,
               asset.external_url,
               asset.object_key,
               asset.original_file_name,
               asset.mime_type,
               asset.size_bytes,
               placement.display_order,
               placement.block_key,
               placement.section_key,
               placement.content_area,
               placement.status,
               placement.version AS placement_version,
               asset.version,
               asset.conversion_status,
               asset.conversion_error,
               asset.conversion_attempts
        FROM msi_v2.supplemental_curriculum_revision_assets placement
        JOIN msi_v2.supplemental_curriculum_assets asset
          ON asset.id = placement.asset_id
        WHERE placement.revision_id = %s
          AND asset.status = 'active'
          {status_sql}
        ORDER BY placement.display_order, placement.id
        """,
        (revision_id,),
    ).fetchall()


def list_published_asset_rows(
    conn,
    item_ids: list[int],
    *,
    include_archived: bool = False,
):
    if not item_ids:
        return []
    status_sql = "" if include_archived else "AND placement.status = 'active'"
    return conn.execute(
        f"""
        SELECT asset.id AS asset_id,
               asset.item_id,
               asset.asset_kind,
               asset.render_kind,
               asset.title,
               asset.external_url,
               asset.object_key,
               asset.original_file_name,
               asset.mime_type,
               asset.size_bytes,
               placement.display_order,
               placement.block_key,
               placement.section_key,
               placement.content_area,
               placement.status,
               placement.version AS placement_version,
               asset.version,
               asset.conversion_status,
               asset.conversion_error,
               asset.conversion_attempts
        FROM msi_v2.supplemental_curriculum_items item
        JOIN msi_v2.supplemental_curriculum_revision_assets placement
          ON placement.revision_id = item.published_revision_id
        JOIN msi_v2.supplemental_curriculum_assets asset
          ON asset.id = placement.asset_id
        WHERE item.id = ANY(%s)
          AND asset.status = 'active'
          {status_sql}
        ORDER BY asset.item_id, placement.display_order, placement.id
        """,
        (item_ids,),
    ).fetchall()


def list_rendition_rows(conn, asset_ids: list[int]):
    if not asset_ids:
        return []
    return conn.execute(
        """
        SELECT id AS rendition_id, asset_id, slide_number, object_key,
               mime_type, size_bytes, width, height
        FROM msi_v2.supplemental_curriculum_asset_renditions
        WHERE asset_id = ANY(%s)
        ORDER BY asset_id, slide_number
        """,
        (asset_ids,),
    ).fetchall()


def insert_external_asset(
    conn,
    *,
    item_id: int,
    revision_id: int,
    title: str,
    external_url: str,
    render_kind: str,
    actor_staff_id: int | None,
):
    asset = conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_assets (
            item_id, asset_kind, render_kind, title, external_url,
            display_order, status, version, conversion_status,
            created_by_staff_id, created_at, updated_at
        )
        SELECT %s, 'link', %s, %s, %s, coalesce(max(display_order), 0) + 1,
               'active', 1, 'not_required', %s, now(), now()
        FROM msi_v2.supplemental_curriculum_assets
        WHERE item_id = %s
        RETURNING id, display_order
        """,
        (
            item_id,
            render_kind,
            title,
            external_url,
            actor_staff_id,
            item_id,
        ),
    ).fetchone()
    if asset:
        attach_asset(
            conn,
            revision_id=revision_id,
            asset_id=int(asset["id"]),
            display_order=int(asset["display_order"]),
        )
    return asset


def insert_file_asset(
    conn,
    *,
    item_id: int,
    revision_id: int,
    title: str,
    object_key: str,
    original_file_name: str,
    mime_type: str,
    size_bytes: int,
    render_kind: str,
    conversion_status: str,
    actor_staff_id: int | None,
):
    asset = conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_assets (
            item_id, asset_kind, render_kind, title, object_key,
            original_file_name, mime_type, size_bytes, display_order,
            status, version, conversion_status, created_by_staff_id,
            created_at, updated_at
        )
        SELECT %s, 'file', %s, %s, %s, %s, %s, %s,
               coalesce(max(display_order), 0) + 1,
               'active', 1, %s, %s, now(), now()
        FROM msi_v2.supplemental_curriculum_assets
        WHERE item_id = %s
        RETURNING id, display_order, conversion_attempts
        """,
        (
            item_id,
            render_kind,
            title,
            object_key,
            original_file_name,
            mime_type,
            size_bytes,
            conversion_status,
            actor_staff_id,
            item_id,
        ),
    ).fetchone()
    if asset:
        attach_asset(
            conn,
            revision_id=revision_id,
            asset_id=int(asset["id"]),
            display_order=int(asset["display_order"]),
        )
    return asset


def attach_asset(
    conn,
    *,
    revision_id: int,
    asset_id: int,
    display_order: int,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_revision_assets (
            revision_id, asset_id, block_key, section_key, content_area,
            display_order, status, version, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, '', 'materials', %s, 'active', 1, now(), now()
        )
        ON CONFLICT (revision_id, asset_id, block_key)
        DO UPDATE SET status = 'active', archived_at = NULL, updated_at = now()
        """,
        (revision_id, asset_id, f"staged-asset-{asset_id}", display_order),
    )


def detach_asset(
    conn,
    *,
    revision_id: int,
    asset_id: int,
    expected_version: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_revision_assets
        SET status = 'archived',
            archived_at = now(),
            archived_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE revision_id = %s
          AND asset_id = %s
          AND status = 'active'
          AND version = %s
        RETURNING id
        """,
        (actor_staff_id, revision_id, asset_id, expected_version),
    ).fetchone()


def sync_asset_placements(
    conn,
    *,
    revision_id: int,
    placements: list[dict[str, object]],
    actor_staff_id: int | None,
) -> None:
    referenced_ids = [int(str(placement["asset_id"])) for placement in placements]
    conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_revision_assets
        SET status = 'archived',
            archived_at = now(),
            archived_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE revision_id = %s
          AND status = 'active'
          AND NOT (asset_id = ANY(%s))
        """,
        (actor_staff_id, revision_id, referenced_ids or [0]),
    )
    for display_order, placement in enumerate(placements, start=1):
        conn.execute(
            """
            UPDATE msi_v2.supplemental_curriculum_revision_assets
            SET block_key = %s,
                section_key = %s,
                content_area = %s,
                display_order = %s,
                updated_at = now()
            WHERE revision_id = %s
              AND asset_id = %s
              AND status = 'active'
            """,
            (
                placement["block_key"],
                placement["section_key"],
                placement["content_area"],
                display_order,
                revision_id,
                placement["asset_id"],
            ),
        )


def update_draft(
    conn,
    *,
    draft_id: int,
    title: str,
    guidance: dict[str, object],
    expected_version: int,
    actor_staff_id: int | None,
):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_item_revisions
        SET title = %s,
            guidance_json = %s::jsonb,
            updated_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND state = 'draft'
          AND version = %s
        RETURNING *
        """,
        (
            title,
            json.dumps(guidance, ensure_ascii=False),
            actor_staff_id,
            draft_id,
            expected_version,
        ),
    ).fetchone()


def prepare_new_item_for_publish(conn, *, item_id: int, curriculum_id: int):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_items item
        SET item_order = active.next_order,
            lesson_number = 'F-' || lpad(active.next_order::text, 2, '0'),
            updated_at = now()
        FROM (
            SELECT coalesce(max(item_order), 0) + 1 AS next_order
            FROM msi_v2.supplemental_curriculum_items
            WHERE curriculum_id = %s AND status = 'active'
        ) active
        WHERE item.id = %s
          AND item.curriculum_id = %s
          AND item.status = 'draft'
        RETURNING item.id, item.item_order
        """,
        (curriculum_id, item_id, curriculum_id),
    ).fetchone()


def abandon_draft(
    conn,
    *,
    draft_id: int,
    actor_staff_id: int | None,
):
    revision = conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_item_revisions
        SET state = 'abandoned',
            abandoned_at = now(),
            updated_by_staff_id = %s,
            updated_at = now()
        WHERE id = %s AND state = 'draft'
        RETURNING item_id
        """,
        (actor_staff_id, draft_id),
    ).fetchone()
    if revision:
        conn.execute(
            """
            UPDATE msi_v2.supplemental_curriculum_items
            SET status = 'archived',
                archived_at = now(),
                archived_by_staff_id = %s,
                archive_reason = 'Unpublished draft abandoned',
                updated_at = now()
            WHERE id = %s
              AND status = 'draft'
              AND published_revision_id IS NULL
            """,
            (actor_staff_id, int(revision["item_id"])),
        )
    return revision


def list_blocking_conversion_rows(conn, revision_id: int):
    return conn.execute(
        """
        SELECT asset.id, asset.title, asset.conversion_status
        FROM msi_v2.supplemental_curriculum_revision_assets placement
        JOIN msi_v2.supplemental_curriculum_assets asset
          ON asset.id = placement.asset_id
        WHERE placement.revision_id = %s
          AND placement.status = 'active'
          AND asset.status = 'active'
          AND asset.render_kind = 'presentation'
          AND asset.conversion_status <> 'ready'
        ORDER BY asset.id
        """,
        (revision_id,),
    ).fetchall()


def list_attached_asset_ids(conn, revision_id: int) -> list[int]:
    rows = conn.execute(
        """
        SELECT asset_id
        FROM msi_v2.supplemental_curriculum_revision_assets
        WHERE revision_id = %s AND status = 'active'
        ORDER BY display_order, id
        """,
        (revision_id,),
    ).fetchall()
    return [int(row["asset_id"]) for row in rows]


def publish_draft(
    conn,
    *,
    draft_id: int,
    item_id: int,
    curriculum_id: int,
    title: str,
    guidance: dict[str, object],
    base_item_version: int,
    actor_staff_id: int | None,
):
    conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_item_revisions
        SET state = 'superseded', updated_at = now()
        WHERE item_id = %s AND state = 'published'
        """,
        (item_id,),
    )
    revision = conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_item_revisions
        SET state = 'published',
            title = %s,
            guidance_json = %s::jsonb,
            published_by_staff_id = %s,
            published_at = now(),
            updated_at = now()
        WHERE id = %s AND state = 'draft'
        RETURNING id
        """,
        (
            title,
            json.dumps(guidance, ensure_ascii=False),
            actor_staff_id,
            draft_id,
        ),
    ).fetchone()
    if not revision:
        return None
    item = conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_items
        SET title = %s,
            guidance_json = %s::jsonb,
            status = 'active',
            published_revision_id = %s,
            lesson_number = CASE
                WHEN status = 'draft' THEN 'F-' || lpad(item_order::text, 2, '0')
                ELSE lesson_number
            END,
            updated_by_staff_id = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND version = %s
          AND status IN ('draft', 'active')
        RETURNING id, version
        """,
        (
            title,
            json.dumps(guidance, ensure_ascii=False),
            draft_id,
            actor_staff_id,
            item_id,
            base_item_version,
        ),
    ).fetchone()
    if not item:
        return None
    return item


__all__ = [
    "abandon_draft",
    "attach_asset",
    "copy_published_asset_placements",
    "detach_asset",
    "get_draft_row",
    "get_item_draft_row",
    "insert_draft_item",
    "insert_draft_revision",
    "insert_external_asset",
    "insert_file_asset",
    "list_attached_asset_ids",
    "list_blocking_conversion_rows",
    "list_published_asset_rows",
    "list_rendition_rows",
    "list_revision_asset_rows",
    "prepare_new_item_for_publish",
    "publish_draft",
    "sync_asset_placements",
    "update_draft",
]
