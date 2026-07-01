"""Parent role service facade."""

from database import queries
from backend.identity.parent_accounts import (
    link_parent_via_invite,
    parent_children,
    parent_from_telegram_user_id,
)
from backend.roles.admin.services.parent_service import (  # noqa: F401
    _to_invite_child,
    assign_parent_child,
    list_parent_accounts,
    list_parent_children,
    remove_parent_child,
)
from backend.domains.payments.service import (  # noqa: F401
    list_student_payments,
    payment_summary_for_student,
)


def list_parent_client_children(parent_id):
    """Children for a parent CLIENT account, shaped for the parent portal."""
    raw_rows = parent_children(parent_id)
    if not raw_rows:
        return []
    with queries.connect_auth_db() as conn:
        return [
            child
            for child in (_to_invite_child(row, conn=conn) for row in raw_rows)
            if child
        ]


def parent_can_access_student(parent_id, student_row_id):
    """True when this parent client is linked to the requested student row."""
    try:
        parsed_parent_id = int(parent_id)
        parsed_student_row_id = int(student_row_id)
    except (TypeError, ValueError):
        return False
    if parsed_parent_id <= 0 or parsed_student_row_id <= 0:
        return False
    with queries.connect_auth_db() as conn:
        row = queries.get_parent_child_link(conn, parsed_parent_id, parsed_student_row_id)
    return bool(row)


def parent_can_access_dashboard(parent_id, dashboard_student_id):
    """True when this parent client is linked to a dashboard enrollment id."""
    try:
        parsed_parent_id = int(parent_id)
        parsed_dashboard_student_id = int(dashboard_student_id)
    except (TypeError, ValueError):
        return False
    if parsed_parent_id <= 0 or parsed_dashboard_student_id <= 0:
        return False
    with queries.connect_auth_db() as conn:
        row = queries.get_parent_child_link_by_dashboard_id(
            conn,
            parsed_parent_id,
            parsed_dashboard_student_id,
        )
    return bool(row)


def resolve_parent_child_dashboard(student_row_id):
    """Resolve a linked child row to the default student dashboard route params."""
    try:
        parsed_student_row_id = int(student_row_id)
    except (TypeError, ValueError):
        return None
    if parsed_student_row_id <= 0:
        return None
    with queries.connect_auth_db() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                subj.subject_name AS subject_name,
                g.group_name AS group_name,
                COALESCE(s.school_key, '') AS school_code
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            LEFT JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE st.legacy_student_row_id = %s
              AND gs.enrollment_status = 'active'
              AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
            ORDER BY
                lower(subj.subject_name) ASC,
                lower(g.group_name) ASC,
                gs.legacy_enrollment_id ASC
            LIMIT 1
            """,
            (parsed_student_row_id,),
        ).fetchone()
    if not row:
        return None
    try:
        dashboard_id = int(row["public_dashboard_id"])
    except (TypeError, ValueError):
        return None
    if dashboard_id <= 0:
        return None
    return {
        "student_id": dashboard_id,
        "subject": str(row["subject_name"] or "").strip(),
        "group": str(row["group_name"] or "").strip(),
        "school": str(row["school_code"] or "").strip(),
    }


__all__ = [
    "assign_parent_child",
    "link_parent_via_invite",
    "list_parent_accounts",
    "list_parent_client_children",
    "list_parent_children",
    "list_student_payments",
    "payment_summary_for_student",
    "parent_can_access_dashboard",
    "parent_can_access_student",
    "parent_from_telegram_user_id",
    "remove_parent_child",
    "resolve_parent_child_dashboard",
]
