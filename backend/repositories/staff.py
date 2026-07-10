"""Aggregate count persistence for staff workspaces."""

from backend.core.database import connect


COUNT_SQL = {
    "schools": "SELECT count(*) AS total FROM msi_v2.schools WHERE status = 'active'",
    "students": "SELECT count(*) AS total FROM msi_v2.students WHERE status = 'active'",
    "teachers": "SELECT count(*) AS total FROM msi_v2.teachers WHERE status = 'active'",
    "subjects": "SELECT count(*) AS total FROM msi_v2.subjects WHERE status = 'active'",
    "groups": "SELECT count(*) AS total FROM msi_v2.groups WHERE status = 'active'",
    "parents": "SELECT count(*) AS total FROM msi_v2.parents WHERE status = 'active'",
    "candidates": "SELECT count(*) AS total FROM msi_v2.teacher_candidates",
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
