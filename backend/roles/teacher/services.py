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
from backend.domains.announcements.service import list_announcements
from backend.roles.admin.services.academic_service import get_group_gradebook
from backend.roles.admin.services.teacher_academy_service import (
    get_academy_teacher_for_teacher_account,
)
from backend.roles.admin.services.teacher_candidate_service import (  # noqa: F401
    create_teacher_candidate,
    get_teacher_candidate,
    list_teacher_candidates,
    update_teacher_candidate_status,
)


def _as_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _as_score(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def _academy_training_end_date(assignments):
    dates = []
    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        for key in ("session_datetime", "deadline_date", "updated_at"):
            raw_value = str(assignment.get(key) or "").strip()
            if raw_value:
                dates.append(raw_value)
                break
    return max(dates) if dates else ""


def _academy_rank(progress):
    if not isinstance(progress, dict):
        return "Not ranked"
    average_score = _as_score(progress.get("average_score"))
    assessed_count = _as_int(progress.get("assessed_count"))
    if not assessed_count:
        return "Not ranked"
    if average_score >= 8.5:
        return "High performer"
    if average_score >= 7:
        return "On track"
    return "Needs support"


def _academy_summary(academy, assignments, assessments):
    progress = academy.get("progress") if isinstance(academy.get("progress"), dict) else {}
    assigned_count = _as_int(progress.get("assigned_count")) or len(assignments)
    assessed_count = _as_int(progress.get("assessed_count"))
    remaining_count = max(assigned_count - assessed_count, 0)
    # Progress target equals the number of assigned lessons — no fixed 12 fallback.
    target_lessons = _as_int(progress.get("target_lessons")) or assigned_count
    progress_percent = round((assessed_count / target_lessons) * 100) if target_lessons else 0
    scores = [_as_score(item.get("weighted_overall_score")) for item in assessments if isinstance(item, dict)]
    scores = [score for score in scores if score > 0]
    average_score = progress.get("average_score")
    latest_score = progress.get("latest_score")
    if average_score is None and scores:
        average_score = round(sum(scores) / len(scores), 2)
    if latest_score is None and scores:
        latest_score = round(scores[-1], 2)
    score_summary = "No assessments yet."
    if scores:
        score_summary = f"{len(scores)} assessed lesson{'s' if len(scores) != 1 else ''}; latest {scores[-1]:.1f}/10."
    return {
        "assigned_count": assigned_count,
        "assessed_count": assessed_count,
        "completed_count": assessed_count,
        "remaining_count": remaining_count,
        "target_lessons": target_lessons,
        "progress_percent": min(100, max(0, progress_percent)),
        "rank": _academy_rank({"average_score": average_score, "assessed_count": assessed_count}),
        "status": str(academy.get("academy_status") or "in_training"),
        "subject": str(academy.get("subject") or ""),
        "training_start_date": str(academy.get("academy_start_date") or ""),
        "training_end_date": _academy_training_end_date(assignments),
        "average_score": average_score,
        "latest_score": latest_score,
        "score_summary": score_summary,
    }


def _academy_related_announcement(item):
    if not isinstance(item, dict):
        return False
    audience = str(item.get("audience") or "").strip().lower()
    if audience == "trainees":
        return True
    text = f"{item.get('title') or ''} {item.get('body') or ''}".lower()
    return "academy" in text or "trainee" in text or "training teacher" in text


def _announcement_updates():
    try:
        announcements = list_announcements(include_drafts=False)
    except Exception:
        announcements = []
    updates = []
    for item in announcements:
        if not _academy_related_announcement(item):
            continue
        updates.append(
            {
                "id": f"announcement-{item.get('id')}",
                "kind": "announcement",
                "title": str(item.get("title") or "Teacher Academy update"),
                "body": str(item.get("body") or ""),
                "source": str(item.get("author") or "Academic Department") or "Academic Department",
                "created_at": str(item.get("publishedAt") or item.get("updatedAt") or item.get("createdAt") or ""),
                "priority": str(item.get("priority") or "info"),
            }
        )
    return updates


def _academy_updates(assignments, assessments):
    updates = _announcement_updates()
    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        updates.append(
            {
                "id": f"assignment-{assignment.get('id')}",
                "kind": "lesson",
                "title": "Academy lesson scheduled" if assignment.get("session_datetime") else "Academy lesson assigned",
                "body": " ".join(
                    part
                    for part in [
                        str(assignment.get("lesson_number") or "").strip(),
                        str(assignment.get("lesson_topic") or "").strip(),
                    ]
                    if part
                )
                or "Training lesson",
                "source": str(assignment.get("evaluator_name") or "Academic Department"),
                "created_at": str(assignment.get("updated_at") or assignment.get("created_at") or ""),
                "priority": "info",
            }
        )
    for report in assessments:
        if not isinstance(report, dict):
            continue
        updates.append(
            {
                "id": f"assessment-{report.get('id')}",
                "kind": "assessment",
                "title": "Assessment report added",
                "body": str(report.get("final_recommendation") or report.get("decision") or "Lesson report is available."),
                "source": str(report.get("created_by") or report.get("evaluator_name") or "Academic Department"),
                "created_at": str(report.get("updated_at") or report.get("created_at") or ""),
                "priority": "important",
            }
        )
    return sorted(updates, key=lambda item: str(item.get("created_at") or ""), reverse=True)[:12]


def _academy_workspace_for(teacher_id, staff_id=None):
    parsed_teacher_id = _as_int(teacher_id)
    parsed_staff_id = _as_int(staff_id)
    academy = get_academy_teacher_for_teacher_account(parsed_teacher_id, parsed_staff_id)
    if not academy:
        return None
    assignments = list(academy.get("assignments") or [])
    assessments = list(academy.get("assessments") or [])
    scheduled = [
        assignment
        for assignment in assignments
        if str(assignment.get("session_datetime") or "").strip()
    ]
    return {
        "academy": academy,
        "academy_summary": _academy_summary(academy, assignments, assessments),
        "academy_updates": _academy_updates(assignments, assessments),
        "journey": assignments,
        "lesson_reports": assessments,
        "training_timetable": scheduled,
    }


def build_teacher_workspace(teacher_id, staff_id=None):
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
    academy_workspace = _academy_workspace_for(teacher_id, staff_id)

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
            "performance_score": float(teacher.get("performance_score") or 0),
        },
        "groups": gradebooks,
        "academy": (academy_workspace or {}).get("academy"),
        "academy_summary": (academy_workspace or {}).get("academy_summary", {}),
        "academy_updates": (academy_workspace or {}).get("academy_updates", []),
        "journey": (academy_workspace or {}).get("journey", []),
        "lesson_reports": (academy_workspace or {}).get("lesson_reports", []),
        "training_timetable": (academy_workspace or {}).get("training_timetable", []),
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
