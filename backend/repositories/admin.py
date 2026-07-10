"""Persistence for system-administrator workspace composition."""


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
