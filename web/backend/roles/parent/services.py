"""Parent role service facade."""

from shared.db import queries
from shared.identity.parent_accounts import (
    link_parent_via_invite,
    parent_children,
    parent_from_telegram_user_id,
)
from web.backend.roles.admin.services.parent_service import (  # noqa: F401
    _to_invite_child,
    assign_parent_child,
    create_parent_account,
    list_parent_accounts,
    list_parent_children,
    remove_parent_child,
)
from web.backend.domains.payments.service import (  # noqa: F401
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
                e.public_dashboard_id,
                sub.name AS subject_name,
                g.name AS group_name,
                COALESCE(s.code, '') AS school_code
            FROM academic_enrollments e
            JOIN academic_subjects sub ON sub.id = e.subject_id
            JOIN academic_groups g ON g.id = e.group_id
            LEFT JOIN academic_schools s ON s.id = g.school_id
            WHERE e.student_row_id = %s
              AND e.active = 1
              AND e.public_dashboard_id IS NOT NULL
            ORDER BY
                CASE WHEN e.enrollment_status = 'active' THEN 0 ELSE 1 END,
                lower(sub.name) ASC,
                lower(g.name) ASC,
                e.id ASC
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
    "create_parent_account",
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
