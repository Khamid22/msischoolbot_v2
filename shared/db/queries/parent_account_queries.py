"""Parent CLIENT account SQL helpers (separate from `admins`).

These back the parent invite-link flow: a parent fills in their details on the
signed invite page and is linked to a student. Parents here are customers, not
staff — no login, no admin privileges. See tables._create_parent_accounts_tables.
"""

from shared.db.tables import ensure_parent_accounts_schema


def _clean_username(value):
    """Store a Telegram handle without a leading @ and surrounding space."""
    return str(value or "").strip().lstrip("@").strip()


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


def link_parent_from_invite(conn, *, student_row_id, full_name, phone, telegram_username, now):
    """Create or update a parent from the invite form, then link to the student.

    Idempotent per student: if a parent already linked to this student matches
    the submitted Telegram username (case-insensitive) or phone, that record is
    updated in place instead of creating a duplicate — so refreshing/re-submitting
    the page does not spawn extra parent rows. Returns the parent row.
    """
    ensure_parent_accounts_schema(conn)

    student_row_id = int(student_row_id)
    full_name = str(full_name or "").strip()
    phone = str(phone or "").strip()
    username = _clean_username(telegram_username)

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
            SET full_name = %s, phone = %s, telegram_username = %s, updated_at = %s
            WHERE id = %s
            """,
            (full_name, phone, username, now, parent_id),
        )
    else:
        inserted = conn.execute(
            """
            INSERT INTO parents (full_name, phone, telegram_username, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (full_name, phone, username, now, now),
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


__all__ = ["link_parent_from_invite", "get_parents_for_student"]
