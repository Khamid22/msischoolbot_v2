"""Resource library queries for the Alembic-managed ``msi_v2`` schema."""

from backend.modules.academics import canonical


_RESOURCE_TYPE_COLUMNS = """
    id,
    name,
    slug,
    is_active,
    true AS is_system,
    display_order,
    created_at::text AS created_at,
    updated_at::text AS updated_at
"""


def list_resource_type_rows(conn, include_inactive=False):
    where_sql = "" if include_inactive else "WHERE is_active IS TRUE"
    return conn.execute(
        f"""
        SELECT {_RESOURCE_TYPE_COLUMNS}
        FROM msi_v2.resource_types
        {where_sql}
        ORDER BY is_active DESC, display_order ASC, lower(name) ASC, id ASC
        """
    ).fetchall()


def get_resource_type_by_name_row(conn, name):
    return conn.execute(
        f"""
        SELECT {_RESOURCE_TYPE_COLUMNS}
        FROM msi_v2.resource_types
        WHERE lower(name) = lower(%s)
        LIMIT 1
        """,
        (name,),
    ).fetchone()


def get_resource_type_by_slug_row(conn, slug):
    return conn.execute(
        f"""
        SELECT {_RESOURCE_TYPE_COLUMNS}
        FROM msi_v2.resource_types
        WHERE lower(slug) = lower(%s)
        LIMIT 1
        """,
        (slug,),
    ).fetchone()


def get_resource_type_by_id_row(conn, resource_type_id):
    return conn.execute(
        f"""
        SELECT {_RESOURCE_TYPE_COLUMNS}
        FROM msi_v2.resource_types
        WHERE id = %s
        LIMIT 1
        """,
        (resource_type_id,),
    ).fetchone()


def get_next_resource_type_display_order(conn):
    row = conn.execute(
        """
        SELECT COALESCE(MAX(display_order), 0) AS max_display_order
        FROM msi_v2.resource_types
        """
    ).fetchone()
    if not row:
        return 1
    try:
        max_value = int(row["max_display_order"] or 0)
    except (TypeError, ValueError, KeyError):
        max_value = 0
    return max_value + 1


def insert_resource_type_row(
    conn,
    name,
    slug,
    is_system,
    display_order,
    created_at,
    updated_at,
):
    inserted = conn.execute(
        """
        INSERT INTO msi_v2.resource_types (
            name,
            slug,
            is_active,
            display_order,
            created_at,
            updated_at
        )
        VALUES (%s, %s, true, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()))
        RETURNING id
        """,
        (
            name,
            slug,
            int(display_order),
            created_at or None,
            updated_at or None,
        ),
    )
    row = inserted.fetchone()
    return int(row["id"] or 0) if row else 0


def update_resource_type_active(conn, resource_type_id, is_active, updated_at):
    updated = conn.execute(
        """
        UPDATE msi_v2.resource_types
        SET
            is_active = %s,
            updated_at = COALESCE(%s::timestamptz, now())
        WHERE id = %s
        """,
        (bool(is_active), updated_at or None, int(resource_type_id)),
    )
    return int(updated.rowcount or 0)


def update_resource_type_row(conn, resource_type_id, name, slug, updated_at):
    updated = conn.execute(
        """
        UPDATE msi_v2.resource_types
        SET
            name = %s,
            slug = %s,
            updated_at = COALESCE(%s::timestamptz, now())
        WHERE id = %s
        """,
        (name, slug, updated_at or None, int(resource_type_id)),
    )
    return int(updated.rowcount or 0)


def ensure_default_resource_types(conn, created_at):
    defaults = [
        ("Definition", "definition", 1),
        ("Video", "video", 1),
        ("Practice Sheet", "practice-sheet", 1),
        ("Worksheet", "worksheet", 1),
        ("Past Paper", "past-paper", 1),
    ]

    for order_index, (name, slug, _is_system) in enumerate(defaults, start=1):
        existing = get_resource_type_by_slug_row(conn, slug)
        if existing:
            continue

        existing = get_resource_type_by_name_row(conn, name)
        if existing:
            conn.execute(
                """
                UPDATE msi_v2.resource_types
                SET
                    slug = %s,
                    display_order = CASE
                        WHEN display_order <= 0 THEN %s
                        ELSE display_order
                    END,
                    updated_at = COALESCE(%s::timestamptz, now())
                WHERE id = %s
                """,
                (slug, int(order_index), created_at or None, int(existing["id"])),
            )
            continue

        insert_resource_type_row(
            conn,
            name=name,
            slug=slug,
            is_system=True,
            display_order=order_index,
            created_at=created_at,
            updated_at=created_at,
        )


def list_resource_subject_names(conn):
    rows = conn.execute(
        """
        SELECT s.subject_name
        FROM msi_v2.resources r
        JOIN msi_v2.subjects s ON s.id = r.subject_id
        WHERE trim(coalesce(s.subject_name, '')) <> ''
        GROUP BY s.subject_name
        ORDER BY lower(s.subject_name) ASC
        """
    ).fetchall()
    return [str(row["subject_name"]).strip() for row in rows if str(row["subject_name"]).strip()]


def _get_subject_id(conn, subject_name, subject_key):
    canonical_subject_name = canonical.canonical_subject_name(subject_name) or str(subject_name or "").strip()
    canonical_subject_key = canonical.subject_key(canonical_subject_name) or str(subject_key or "").strip()
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.subjects
        WHERE lower(subject_key) = lower(%s)
           OR lower(subject_name) = lower(%s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (canonical_subject_key, canonical_subject_name),
    ).fetchone()
    return int(row["id"]) if row else None


def insert_resource_row(
    conn,
    subject_name,
    subject_key,
    resource_type_id,
    folder_path,
    title,
    description,
    resource_url,
    resource_file_path,
    thumbnail_file_path,
    created_by_admin_id,
    created_at,
    updated_at,
):
    subject_id = _get_subject_id(conn, subject_name, subject_key)
    inserted = conn.execute(
        """
        INSERT INTO msi_v2.resources (
            subject_id,
            resource_type_id,
            title,
            description,
            resource_url,
            resource_file_path,
            thumbnail_file_path,
            is_active,
            created_by_staff_id,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()))
        RETURNING id
        """,
        (
            subject_id,
            int(resource_type_id),
            title,
            description,
            resource_url,
            resource_file_path,
            thumbnail_file_path,
            created_by_admin_id,
            created_at or None,
            updated_at or None,
        ),
    )


def list_resource_comment_rows(conn, resource_id: int, limit: int):
    return conn.execute(
        """
        SELECT id, author_name, body, created_at
        FROM msi_v2.resource_comments
        WHERE resource_id = %s
        ORDER BY created_at ASC
        LIMIT %s
        """,
        (resource_id, limit),
    ).fetchall()


def active_resource_exists(conn, resource_id: int):
    return conn.execute(
        "SELECT 1 FROM msi_v2.resources WHERE id = %s AND is_active IS TRUE",
        (resource_id,),
    ).fetchone()


def insert_resource_comment(conn, *, resource_id: int, author_name: str, body: str, created_at: str):
    return conn.execute(
        """
        INSERT INTO msi_v2.resource_comments (resource_id, author_name, body, created_at)
        VALUES (%s, %s, %s, %s::timestamptz)
        RETURNING id
        """,
        (resource_id, author_name, body, created_at),
    ).fetchone()
    row = inserted.fetchone()
    return int(row["id"] or 0) if row else 0


def update_resource_active(conn, resource_id, is_active, updated_at):
    updated = conn.execute(
        """
        UPDATE msi_v2.resources
        SET
            is_active = %s,
            updated_at = COALESCE(%s::timestamptz, now())
        WHERE id = %s
        """,
        (bool(is_active), updated_at or None, int(resource_id)),
    )
    return int(updated.rowcount or 0)


def count_resources_by_type(conn, resource_type_id):
    row = conn.execute(
        """
        SELECT COUNT(1) AS row_count
        FROM msi_v2.resources
        WHERE resource_type_id = %s
        """,
        (int(resource_type_id),),
    ).fetchone()
    if not row:
        return 0
    try:
        return int(row["row_count"] or 0)
    except (TypeError, ValueError, KeyError):
        return 0


def update_resource_row(conn, resource_id, title, description, updated_at):
    updated = conn.execute(
        """
        UPDATE msi_v2.resources
        SET
            title = %s,
            description = %s,
            updated_at = COALESCE(%s::timestamptz, now())
        WHERE id = %s
        """,
        (title, description, updated_at or None, int(resource_id)),
    )
    return int(updated.rowcount or 0)


def update_resource_full_row(conn, resource_id, title, description, resource_file_path, thumbnail_file_path, updated_at, resource_type_id=None):
    if resource_type_id is not None:
        updated = conn.execute(
            """
            UPDATE msi_v2.resources
            SET
                title = %s,
                description = %s,
                resource_file_path = %s,
                thumbnail_file_path = %s,
                resource_type_id = %s,
                updated_at = COALESCE(%s::timestamptz, now())
            WHERE id = %s
            """,
            (title, description, resource_file_path, thumbnail_file_path, int(resource_type_id), updated_at or None, int(resource_id)),
        )
    else:
        updated = conn.execute(
            """
            UPDATE msi_v2.resources
            SET
                title = %s,
                description = %s,
                resource_file_path = %s,
                thumbnail_file_path = %s,
                updated_at = COALESCE(%s::timestamptz, now())
            WHERE id = %s
            """,
            (title, description, resource_file_path, thumbnail_file_path, updated_at or None, int(resource_id)),
        )
    return int(updated.rowcount or 0)


def _resource_select_sql():
    return """
        r.id,
        s.subject_name,
        s.subject_key,
        r.resource_type_id,
        '' AS folder_path,
        r.title,
        r.description,
        r.resource_url,
        r.resource_file_path,
        r.thumbnail_file_path,
        r.is_active,
        r.created_by_staff_id AS created_by_admin_id,
        r.created_at::text AS created_at,
        r.updated_at::text AS updated_at,
        t.name AS resource_type_name,
        t.slug AS resource_type_slug,
        t.display_order AS resource_type_display_order,
        t.is_active AS resource_type_active
    """


def get_resource_row_by_id(conn, resource_id):
    return conn.execute(
        f"""
        SELECT {_resource_select_sql()}
        FROM msi_v2.resources r
        JOIN msi_v2.resource_types t ON t.id = r.resource_type_id
        LEFT JOIN msi_v2.subjects s ON s.id = r.subject_id
        WHERE r.id = %s
        LIMIT 1
        """,
        (int(resource_id),),
    ).fetchone()


def list_resource_rows(conn, include_inactive=False, subject_key=""):
    filters = []
    params = []

    normalized_subject_key = str(subject_key or "").strip()
    if normalized_subject_key:
        filters.append("s.subject_key = %s")
        params.append(normalized_subject_key)

    if not include_inactive:
        filters.append("r.is_active IS TRUE")
        filters.append("t.is_active IS TRUE")

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    return conn.execute(
        f"""
        SELECT {_resource_select_sql()}
        FROM msi_v2.resources r
        JOIN msi_v2.resource_types t ON t.id = r.resource_type_id
        LEFT JOIN msi_v2.subjects s ON s.id = r.subject_id
        {where_sql}
        ORDER BY
            lower(coalesce(s.subject_name, '')) ASC,
            t.display_order ASC,
            lower(t.name) ASC,
            lower(r.title) ASC,
            r.id DESC
        """,
        tuple(params),
    ).fetchall()


__all__ = [
    "list_resource_type_rows",
    "get_resource_type_by_name_row",
    "get_resource_type_by_slug_row",
    "get_resource_type_by_id_row",
    "get_next_resource_type_display_order",
    "insert_resource_type_row",
    "update_resource_type_active",
    "update_resource_type_row",
    "ensure_default_resource_types",
    "list_resource_subject_names",
    "insert_resource_row",
    "update_resource_active",
    "update_resource_row",
    "update_resource_full_row",
    "count_resources_by_type",
    "get_resource_row_by_id",
    "list_resource_rows",
]
