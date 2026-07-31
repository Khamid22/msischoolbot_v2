"""PostgreSQL persistence for private presentation conversion and renditions."""

from __future__ import annotations


def get_asset_row(conn, asset_id: int, *, for_update: bool = False):
    lock_sql = "FOR UPDATE OF asset" if for_update else ""
    return conn.execute(
        f"""
        SELECT asset.*,
               item.curriculum_id,
               item.status AS item_status,
               item.published_revision_id,
               curriculum.subject_id,
               curriculum.curriculum_key,
               curriculum.status AS curriculum_status,
               EXISTS (
                   SELECT 1
                   FROM msi_v2.supplemental_curriculum_revision_assets placement
                   WHERE placement.revision_id = item.published_revision_id
                     AND placement.asset_id = asset.id
                     AND placement.status = 'active'
               ) AS is_published
        FROM msi_v2.supplemental_curriculum_assets asset
        JOIN msi_v2.supplemental_curriculum_items item ON item.id = asset.item_id
        JOIN msi_v2.supplemental_curricula curriculum
          ON curriculum.id = item.curriculum_id
        WHERE asset.id = %s
        {lock_sql}
        """,
        (asset_id,),
    ).fetchone()


def mark_conversion_processing(conn, asset_id: int):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_assets
        SET conversion_status = 'processing',
            conversion_error = '',
            conversion_attempts = conversion_attempts + 1,
            updated_at = now()
        WHERE id = %s
          AND render_kind = 'presentation'
          AND conversion_status IN ('pending', 'failed', 'processing')
        RETURNING *
        """,
        (asset_id,),
    ).fetchone()


def mark_conversion_failed(conn, asset_id: int, error: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_assets
        SET conversion_status = 'failed',
            conversion_error = %s,
            updated_at = now()
        WHERE id = %s
        """,
        (error[:500], asset_id),
    )


def mark_conversion_pending(conn, asset_id: int):
    return conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_assets
        SET conversion_status = 'pending',
            conversion_error = '',
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND render_kind = 'presentation'
          AND conversion_status = 'failed'
        RETURNING id, conversion_attempts, version
        """,
        (asset_id,),
    ).fetchone()


def insert_rendition(
    conn,
    *,
    asset_id: int,
    slide_number: int,
    object_key: str,
    mime_type: str,
    size_bytes: int,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.supplemental_curriculum_asset_renditions (
            asset_id, rendition_kind, slide_number, object_key,
            mime_type, size_bytes, created_at
        )
        VALUES (%s, 'slide_image', %s, %s, %s, %s, now())
        ON CONFLICT (asset_id, rendition_kind, slide_number)
        DO NOTHING
        """,
        (asset_id, slide_number, object_key, mime_type, size_bytes),
    )


def mark_conversion_ready(conn, asset_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.supplemental_curriculum_assets
        SET conversion_status = 'ready',
            conversion_error = '',
            converted_at = now(),
            version = version + 1,
            updated_at = now()
        WHERE id = %s
        """,
        (asset_id,),
    )


def get_rendition_row(conn, asset_id: int, slide_number: int):
    return conn.execute(
        """
        SELECT rendition.*, asset.item_id
        FROM msi_v2.supplemental_curriculum_asset_renditions rendition
        JOIN msi_v2.supplemental_curriculum_assets asset
          ON asset.id = rendition.asset_id
        WHERE rendition.asset_id = %s
          AND rendition.slide_number = %s
        """,
        (asset_id, slide_number),
    ).fetchone()


__all__ = [
    "get_asset_row",
    "get_rendition_row",
    "insert_rendition",
    "mark_conversion_failed",
    "mark_conversion_pending",
    "mark_conversion_processing",
    "mark_conversion_ready",
]
