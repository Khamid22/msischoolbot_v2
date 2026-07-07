"""Business helpers used by admin route handlers."""

from backend.core.database import connect_auth_db
from backend.domains.students.service import (
    resolve_sheet_student_for_admin,
    school_code_from_name,
)

from database.academics.canonical import (
    normalize_school_code,
    normalize_text,
)


def group_belongs_to_school(group_name, school_code, load_dataset=None):
    normalized_group = str(group_name or "").strip()
    normalized_school = normalize_school_code(school_code, default="")
    if not normalized_group or not normalized_school or normalized_school == "all":
        return True

    try:
        with connect_auth_db() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM msi_v2.groups g
                JOIN msi_v2.schools s ON s.id = g.school_id
                WHERE g.group_name = %s
                  AND lower(s.school_key) = lower(%s)
                LIMIT 1
                """,
                (normalized_group, normalized_school),
            ).fetchone()
        return row is not None
    except Exception:
        return True
__all__ = [
    "group_belongs_to_school",
    "school_code_from_name",
    "resolve_sheet_student_for_admin",
]
