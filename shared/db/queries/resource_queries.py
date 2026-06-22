"""Resource library SQL query helpers."""

from shared.academics import canonical


def list_resource_type_rows(conn, include_inactive=False):
    if include_inactive:
        return conn.execute(
            """
            SELECT
                id,
                name,
                slug,
                is_active,
                is_system,
                display_order,
                created_at,
                updated_at
            FROM resource_types
            ORDER BY is_active DESC, display_order ASC, lower(name) ASC, id ASC
            """
        ).fetchall()

    return conn.execute(
        """
        SELECT
            id,
            name,
            slug,
            is_active,
            is_system,
            display_order,
            created_at,
            updated_at
        FROM resource_types
        WHERE is_active = 1
        ORDER BY display_order ASC, lower(name) ASC, id ASC
        """
    ).fetchall()


def get_resource_type_by_name_row(conn, name):
    return conn.execute(
        """
        SELECT
            id,
            name,
            slug,
            is_active,
            is_system,
            display_order,
            created_at,
            updated_at
        FROM resource_types
        WHERE lower(name) = lower(%s)
        LIMIT 1
        """,
        (name,),
    ).fetchone()


def get_resource_type_by_slug_row(conn, slug):
    return conn.execute(
        """
        SELECT
            id,
            name,
            slug,
            is_active,
            is_system,
            display_order,
            created_at,
            updated_at
        FROM resource_types
        WHERE lower(slug) = lower(%s)
        LIMIT 1
        """,
        (slug,),
    ).fetchone()


def get_resource_type_by_id_row(conn, resource_type_id):
    return conn.execute(
        """
        SELECT
            id,
            name,
            slug,
            is_active,
            is_system,
            display_order,
            created_at,
            updated_at
        FROM resource_types
        WHERE id = %s
        LIMIT 1
        """,
        (resource_type_id,),
    ).fetchone()


def get_next_resource_type_display_order(conn):
    row = conn.execute(
        """
        SELECT COALESCE(MAX(display_order), 0) AS max_display_order
        FROM resource_types
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
        INSERT INTO resource_types (
            name,
            slug,
            is_active,
            is_system,
            display_order,
            created_at,
            updated_at
        )
        VALUES (%s, %s, 1, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            name,
            slug,
            int(bool(is_system)),
            int(display_order),
            created_at,
            updated_at,
        ),
    )
    row = inserted.fetchone()
    return int(row["id"] or 0) if row else 0


def update_resource_type_active(conn, resource_type_id, is_active, updated_at):
    updated = conn.execute(
        """
        UPDATE resource_types
        SET
            is_active = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (int(bool(is_active)), updated_at, int(resource_type_id)),
    )
    return int(updated.rowcount or 0)


def update_resource_type_row(conn, resource_type_id, name, slug, updated_at):
    updated = conn.execute(
        """
        UPDATE resource_types
        SET
            name = %s,
            slug = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            name,
            slug,
            updated_at,
            int(resource_type_id),
        ),
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

    for order_index, (name, slug, is_system) in enumerate(defaults, start=1):
        existing = get_resource_type_by_slug_row(conn, slug)
        if existing:
            continue

        existing = get_resource_type_by_name_row(conn, name)
        if existing:
            conn.execute(
                """
                UPDATE resource_types
                SET
                    slug = %s,
                    is_system = %s,
                    display_order = CASE
                        WHEN display_order <= 0 THEN %s
                        ELSE display_order
                    END
                WHERE id = %s
                """,
                (
                    slug,
                    int(bool(is_system)),
                    int(order_index),
                    int(existing["id"]),
                ),
            )
            continue
        insert_resource_type_row(
            conn,
            name=name,
            slug=slug,
            is_system=is_system,
            display_order=order_index,
            created_at=created_at,
            updated_at=created_at,
        )


def list_resource_subject_names(conn):
    rows = conn.execute(
        """
        SELECT subject_name
        FROM resources
        WHERE trim(coalesce(subject_name, '')) <> ''
        GROUP BY subject_name
        ORDER BY lower(subject_name) ASC
        """
    ).fetchall()
    return [str(row["subject_name"]).strip() for row in rows if str(row["subject_name"]).strip()]


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
    canonical_subject_name = canonical.canonical_subject_name(subject_name) or str(subject_name or "").strip()
    canonical_subject_key = canonical.subject_key(canonical_subject_name)
    inserted = conn.execute(
        """
        INSERT INTO resources (
            subject_name,
            subject_key,
            resource_type_id,
            folder_path,
            title,
            description,
            resource_url,
            resource_file_path,
            thumbnail_file_path,
            is_active,
            created_by_admin_id,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s)
        RETURNING id
        """,
        (
            canonical_subject_name,
            canonical_subject_key,
            int(resource_type_id),
            folder_path,
            title,
            description,
            resource_url,
            resource_file_path,
            thumbnail_file_path,
            created_by_admin_id,
            created_at,
            updated_at,
        ),
    )
    row = inserted.fetchone()
    return int(row["id"] or 0) if row else 0


def update_resource_active(conn, resource_id, is_active, updated_at):
    updated = conn.execute(
        """
        UPDATE resources
        SET
            is_active = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (int(bool(is_active)), updated_at, int(resource_id)),
    )
    return int(updated.rowcount or 0)


def count_resources_by_type(conn, resource_type_id):
    row = conn.execute(
        """
        SELECT COUNT(1) AS row_count
        FROM resources
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
        UPDATE resources
        SET
            title = %s,
            description = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (title, description, updated_at, int(resource_id)),
    )
    return int(updated.rowcount or 0)


def update_resource_full_row(conn, resource_id, title, description, resource_file_path, thumbnail_file_path, updated_at, resource_type_id=None):
    if resource_type_id is not None:
        updated = conn.execute(
            """
            UPDATE resources
            SET
                title = %s,
                description = %s,
                resource_file_path = %s,
                thumbnail_file_path = %s,
                resource_type_id = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (title, description, resource_file_path, thumbnail_file_path, int(resource_type_id), updated_at, int(resource_id)),
        )
    else:
        updated = conn.execute(
            """
            UPDATE resources
            SET
                title = %s,
                description = %s,
                resource_file_path = %s,
                thumbnail_file_path = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (title, description, resource_file_path, thumbnail_file_path, updated_at, int(resource_id)),
        )
    return int(updated.rowcount or 0)


def get_resource_row_by_id(conn, resource_id):
    return conn.execute(
        """
        SELECT
            r.id,
            r.subject_name,
            r.subject_key,
            r.resource_type_id,
            r.folder_path,
            r.title,
            r.description,
            r.resource_url,
            r.resource_file_path,
            r.thumbnail_file_path,
            r.is_active,
            r.created_by_admin_id,
            r.created_at,
            r.updated_at,
            t.name AS resource_type_name,
            t.is_active AS resource_type_active
        FROM resources r
        JOIN resource_types t ON t.id = r.resource_type_id
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
        filters.append("r.subject_key = %s")
        params.append(normalized_subject_key)

    if not include_inactive:
        filters.append("r.is_active = 1")
        filters.append("t.is_active = 1")

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    return conn.execute(
        f"""
        SELECT
            r.id,
            r.subject_name,
            r.subject_key,
            r.resource_type_id,
            r.folder_path,
            r.title,
            r.description,
            r.resource_url,
            r.resource_file_path,
            r.thumbnail_file_path,
            r.is_active,
            r.created_by_admin_id,
            r.created_at,
            r.updated_at,
            t.name AS resource_type_name,
            t.slug AS resource_type_slug,
            t.display_order AS resource_type_display_order,
            t.is_active AS resource_type_active
        FROM resources r
        JOIN resource_types t ON t.id = r.resource_type_id
        {where_sql}
        ORDER BY
            lower(r.subject_name) ASC,
            lower(r.folder_path) ASC,
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
