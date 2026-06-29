"""Parent CLIENT account SQL helpers (separate from `admins`).

These back the parent invite-link flow: a parent fills in their details on the
signed invite page and is linked to a student. Parents here are customers, not
staff — no login, no admin privileges. See tables._create_parent_accounts_tables.
"""

from shared.db.tables import ensure_parent_accounts_schema


def _clean_username(value):
    """Store a Telegram handle without a leading @ and surrounding space."""
    return str(value or "").strip().lstrip("@").strip()


def _clean_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parent_row(conn, parent_id):
    return conn.execute(
        """
        SELECT id, full_name, phone, telegram_username, telegram_user_id,
               source_admin_id, created_at, updated_at
        FROM parents
        WHERE id = %s
        """,
        (int(parent_id),),
    ).fetchone()


def link_parent_from_invite(
    conn,
    *,
    student_row_id,
    full_name,
    phone,
    telegram_username,
    now,
    telegram_user_id=None,
):
    """Create or update a parent from an invite, then link to the student.

    Telegram Mini App claims are anchored by the verified ``telegram_user_id``.
    Manual fallbacks stay idempotent per student by matching username or phone.
    Returns the parent row.
    """
    ensure_parent_accounts_schema(conn)

    student_row_id = int(student_row_id)
    full_name = str(full_name or "").strip()
    phone = str(phone or "").strip()
    username = _clean_username(telegram_username)
    telegram_user_id = _clean_positive_int(telegram_user_id)

    if telegram_user_id is not None:
        existing = conn.execute(
            """
            SELECT id
            FROM parents
            WHERE telegram_user_id = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (telegram_user_id,),
        ).fetchone()
    else:
        existing = conn.execute(
            """
            SELECT p.id
            FROM parents p
            JOIN parent_student_links l ON l.parent_id = p.id
            WHERE l.student_row_id = %s
              AND (
                  (%s <> '' AND lower(p.telegram_username) = lower(%s))
                  OR (%s <> '' AND p.phone = %s)
              )
            ORDER BY p.id ASC
            LIMIT 1
            """,
            (student_row_id, username, username, phone, phone),
        ).fetchone()

    if existing:
        parent_id = int(existing["id"])
        conn.execute(
            """
            UPDATE parents
            SET full_name = CASE WHEN %s <> '' THEN %s ELSE full_name END,
                phone = CASE WHEN %s <> '' THEN %s ELSE phone END,
                telegram_username = CASE WHEN %s <> '' THEN %s ELSE telegram_username END,
                telegram_user_id = COALESCE(%s, telegram_user_id),
                updated_at = %s
            WHERE id = %s
            """,
            (
                full_name,
                full_name,
                phone,
                phone,
                username,
                username,
                telegram_user_id,
                now,
                parent_id,
            ),
        )
    else:
        inserted = conn.execute(
            """
            INSERT INTO parents (
                full_name, phone, telegram_username, telegram_user_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (full_name, phone, username, telegram_user_id, now, now),
        ).fetchone()
        parent_id = int(inserted["id"])

    conn.execute(
        """
        INSERT INTO parent_student_links (parent_id, student_row_id, created_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (parent_id, student_row_id) DO NOTHING
        """,
        (parent_id, student_row_id, now),
    )

    return _parent_row(conn, parent_id)


def get_parents_for_student(conn, student_row_id):
    """All linked parents for a student (for future admin visibility)."""
    ensure_parent_accounts_schema(conn)
    return conn.execute(
        """
        SELECT p.id, p.full_name, p.phone, p.telegram_username,
               p.telegram_user_id, l.created_at AS linked_at
        FROM parent_student_links l
        JOIN parents p ON p.id = l.parent_id
        WHERE l.student_row_id = %s
        ORDER BY l.created_at ASC, p.id ASC
        """,
        (int(student_row_id),),
    ).fetchall()


def get_parent_by_telegram_id(conn, telegram_user_id):
    ensure_parent_accounts_schema(conn)
    parent_id = _clean_positive_int(telegram_user_id)
    if parent_id is None:
        return None
    return conn.execute(
        """
        SELECT id, full_name, phone, telegram_username, telegram_user_id,
               source_admin_id, created_at, updated_at
        FROM parents
        WHERE telegram_user_id = %s
        LIMIT 1
        """,
        (parent_id,),
    ).fetchone()


def clear_parent_telegram_user_conflicts(conn, telegram_user_id, parent_id=None):
    ensure_parent_accounts_schema(conn)
    parsed_telegram_user_id = _clean_positive_int(telegram_user_id)
    if parsed_telegram_user_id is None:
        return

    if parent_id is not None:
        parsed_parent_id = _clean_positive_int(parent_id)
        if parsed_parent_id is None:
            return
        conn.execute(
            """
            UPDATE parents
            SET telegram_user_id = NULL
            WHERE telegram_user_id = %s
              AND id <> %s
            """,
            (parsed_telegram_user_id, parsed_parent_id),
        )
        return

    conn.execute(
        """
        UPDATE parents
        SET telegram_user_id = NULL
        WHERE telegram_user_id = %s
        """,
        (parsed_telegram_user_id,),
    )


def list_parent_client_child_rows(conn, parent_id):
    ensure_parent_accounts_schema(conn)
    return conn.execute(
        """
        SELECT
            p.id AS parent_id,
            p.full_name,
            p.phone,
            p.telegram_username,
            p.telegram_user_id,
            p.source_admin_id,
            p.created_at,
            p.updated_at,
            l.created_at AS linked_at,
            s.id AS student_row_id,
            s.full_name AS student_full_name,
            s.student_id,
            s.password,
            s.subjects,
            s.telegram_user_id AS student_telegram_user_id,
            s.photo_url,
            s.profile_description,
            s.class_name,
            s.school_name,
            s.last_seen_at
        FROM parent_student_links l
        JOIN parents p ON p.id = l.parent_id
        JOIN students s ON s.id = l.student_row_id
        WHERE p.id = %s
        ORDER BY lower(s.full_name) ASC, s.id ASC
        """,
        (int(parent_id),),
    ).fetchall()


def list_invite_parent_rows(conn):
    """All parent CLIENT accounts with their linked students for admin visibility."""
    ensure_parent_accounts_schema(conn)
    return conn.execute(
        """
        SELECT
            p.id AS parent_id,
            p.full_name,
            p.phone,
            p.telegram_username,
            p.telegram_user_id,
            p.source_admin_id,
            p.created_at,
            p.updated_at,
            l.created_at AS linked_at,
            s.id AS student_row_id,
            s.full_name AS student_full_name,
            s.student_id,
            s.password,
            s.subjects,
            s.telegram_user_id AS student_telegram_user_id,
            s.photo_url,
            s.profile_description,
            s.class_name,
            s.school_name,
            s.last_seen_at
        FROM parents p
        LEFT JOIN parent_student_links l ON l.parent_id = p.id
        LEFT JOIN students s ON s.id = l.student_row_id
        ORDER BY lower(p.full_name) ASC, p.id ASC, lower(s.full_name) ASC, s.id ASC
        """
    ).fetchall()


__all__ = [
    "clear_parent_telegram_user_conflicts",
    "get_parent_by_telegram_id",
    "get_parents_for_student",
    "link_parent_from_invite",
    "list_invite_parent_rows",
    "list_parent_client_child_rows",
]
