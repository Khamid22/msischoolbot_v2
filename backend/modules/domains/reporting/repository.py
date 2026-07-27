"""Aggregate count persistence for staff workspaces."""

from backend.core.database import connect


COUNT_SQL = {
    "schools": "SELECT count(*) AS total FROM msi_v2.schools WHERE status = 'active'",
    "students": "SELECT count(*) AS total FROM msi_v2.students WHERE status = 'active'",
    "teachers": "SELECT count(*) AS total FROM msi_v2.teachers WHERE status = 'active'",
    "subjects": "SELECT count(*) AS total FROM msi_v2.subjects WHERE status = 'active'",
    "groups": "SELECT count(*) AS total FROM msi_v2.groups WHERE status = 'active'",
    "parents": "SELECT count(*) AS total FROM msi_v2.parents WHERE status = 'active'",
    "pending_parent_accounts": "SELECT count(*) AS total FROM msi_v2.accounts WHERE role = 'parent' AND status = 'pending'",
    "pending_parent_invites": "SELECT count(*) AS total FROM msi_v2.account_invites WHERE invite_type = 'parent' AND status = 'pending' AND (expires_at IS NULL OR expires_at > now())",
}


def load_counts(keys):
    counts = {key: None for key in keys}
    try:
        with connect() as conn:
            for key in keys:
                try:
                    row = conn.execute(COUNT_SQL[key]).fetchone()
                    counts[key] = row["total"] if row else None
                except Exception:
                    conn.rollback()
    except Exception:
        pass
    return counts


def list_active_school_rows(conn):
    return conn.execute(
        """
        SELECT school_key AS code, school_name AS name
        FROM msi_v2.schools WHERE status = 'active' ORDER BY school_name
        """
    ).fetchall()


def list_active_group_name_rows(conn, school_filter="all"):
    if school_filter and school_filter != "all":
        return conn.execute(
            """
            SELECT DISTINCT g.group_name AS name
            FROM msi_v2.groups g JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE lower(s.school_key) = lower(%s)
              AND lower(g.group_name) <> 'online' AND g.status = 'active'
            ORDER BY g.group_name
            """,
            (school_filter,),
        ).fetchall()
    return conn.execute(
        """
        SELECT DISTINCT group_name AS name FROM msi_v2.groups
        WHERE lower(group_name) <> 'online' AND status = 'active' ORDER BY group_name
        """
    ).fetchall()


def list_active_group_school_rows(conn):
    return conn.execute(
        """
        SELECT g.group_name, s.school_key AS school_code
        FROM msi_v2.groups g JOIN msi_v2.schools s ON s.id = g.school_id
        WHERE lower(g.group_name) <> 'online' AND g.status = 'active'
        """
    ).fetchall()
