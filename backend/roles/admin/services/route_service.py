"""Business helpers used by admin route handlers."""

from database import queries

from backend.utils.normalization import (
    normalize_school_code,
    normalize_text,
)


def school_code_from_name(school_name):
    normalized = normalize_text(school_name)
    if normalized == "sehriyo":
        return "sehriyo"
    if normalized in {"school 5", "school5"}:
        return "school5"
    return ""


def group_belongs_to_school(group_name, school_code, load_dataset=None):
    normalized_group = str(group_name or "").strip()
    normalized_school = normalize_school_code(school_code)
    if not normalized_group or not normalized_school or normalized_school == "all":
        return True

    try:
        with queries.connect_auth_db() as conn:
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


def resolve_sheet_student_for_admin(student_row_id, get_admin_student_profile, load_dataset=None):
    student_profile = get_admin_student_profile(student_row_id)
    if not student_profile:
        return None, "Selected student was not found.", 404

    full_name = str(student_profile.get("full_name", "")).strip()
    preferred_group = str(student_profile.get("group", "")).strip()
    school_name = str(student_profile.get("school_name", "")).strip()
    school_code = school_code_from_name(school_name)

    try:
        with queries.connect_auth_db() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                    sub.subject_name,
                    g.group_name,
                    s.school_key
                FROM msi_v2.students st
                JOIN msi_v2.group_students gs ON gs.student_id = st.id
                JOIN msi_v2.groups g ON g.id = gs.group_id
                JOIN msi_v2.schools s ON s.id = g.school_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
                WHERE st.legacy_student_row_id = %s
                  AND gs.enrollment_status = 'active'
                  AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
                ORDER BY g.group_name, sub.subject_name
                """,
                (student_row_id,),
            ).fetchall()
    except Exception:
        rows = []

    if not rows:
        return None, "No dashboard data found for this student.", 404

    candidates = []
    for row in rows:
        group_name_row = str(row["group_name"] or "").strip()
        candidates.append(
            {
                "student_id": int(row["public_dashboard_id"]),
                "subject": str(row["subject_name"] or "").strip(),
                "group": group_name_row,
                "school": str(row.get("school_key") or school_code).strip() or school_code,
                "group_match": bool(preferred_group and group_name_row == preferred_group),
            }
        )

    candidates.sort(
        key=lambda item: (
            0 if item.get("group_match") else 1,
            str(item.get("subject", "")).casefold(),
            str(item.get("group", "")).casefold(),
            int(item.get("student_id", 0)),
        )
    )

    return candidates[0], "", 200


__all__ = [
    "group_belongs_to_school",
    "school_code_from_name",
    "resolve_sheet_student_for_admin",
]
