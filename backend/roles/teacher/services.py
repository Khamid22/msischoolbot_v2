"""Teacher role service facade."""

from database import queries
from backend.identity.account_service import (  # noqa: F401
    assign_teacher_to_group,
    get_teacher_by_id,
    get_teacher_name_by_group,
    list_teachers,
    update_teacher_by_id,
    upsert_teacher,
)
from backend.domains.academics.postgres_service import ensure_academic_schema
from backend.roles.admin.services.academic_service import get_group_gradebook
from backend.roles.admin.services.teacher_candidate_service import (  # noqa: F401
    create_teacher_candidate,
    get_teacher_candidate,
    list_teacher_candidates,
    update_teacher_candidate_status,
)


def build_teacher_workspace(teacher_id):
    """Read-only data for a logged-in teacher, scoped to THEIR assigned group(s).

    Security: a teacher only ever receives the gradebook(s) for the academic
    group(s) whose name matches their own ``assigned_group``. No other teacher's
    or school-wide data is included.
    """
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return None

    teacher = get_teacher_by_id(teacher_id)
    if not teacher:
        return None

    group_name = str(teacher.get("assigned_group") or "").strip()
    gradebooks = []
    if group_name:
        with queries.connect_auth_db() as conn:
            ensure_academic_schema(conn)
            group_rows = conn.execute(
                """
                SELECT id
                FROM msi_v2.groups
                WHERE lower(group_name) = lower(%s)
                  AND status = 'active'
                ORDER BY id
                """,
                (group_name,),
            ).fetchall()
        for row in group_rows:
            gradebook = get_group_gradebook(int(row["id"]))
            if gradebook:
                gradebooks.append(gradebook)

    return {
        "teacher": {
            "id": int(teacher["id"]),
            "full_name": str(teacher.get("full_name", "")),
            "login": str(teacher.get("login", "")),
            "assigned_group": group_name,
            "category": str(teacher.get("category", "")),
            "semester_stage": str(teacher.get("semester_stage", "")),
        },
        "groups": gradebooks,
    }


__all__ = [
    "assign_teacher_to_group",
    "build_teacher_workspace",
    "create_teacher_candidate",
    "get_teacher_by_id",
    "get_teacher_candidate",
    "get_teacher_name_by_group",
    "list_teacher_candidates",
    "list_teachers",
    "update_teacher_by_id",
    "update_teacher_candidate_status",
    "upsert_teacher",
]
