"""Public Student orchestration interface used by the Student workspace."""

from backend.modules.domains.academics import contracts as resources_service
from backend.modules.domains.academics.contracts import (
    build_subject_leaderboard,
    collect_subject_dashboards_from_cache,
    collect_subject_dashboards_from_dataset,
    get_group_cache_entry,
    is_full_form,
    list_office_hours_teachers,
    load_dataset,
    seed_group_cache_from_dataset,
)
from backend.modules.domains.communications.contracts import list_announcements
from backend.modules.domains.identity.contracts import (
    build_dashboard_url,
    current_auth_login,
    current_auth_role,
    current_student_db_id,
    current_student_enrollment_id,
    current_student_school_code,
    url_for,
)
from backend.modules.domains.student_records.contracts import (
    get_student_db_id_by_enrollment_id,
    list_enrolled_subject_options,
    record_student_activity,
)
from backend.modules.people.student import dashboard as dashboard_service
from backend.modules.people.student import payload as payload_service
from backend.modules.people.student.activity_api import router as activity_router
from backend.modules.people.student.chat_api import router as chat_router
from backend.modules.people.student.comments_api import router as comments_router
from backend.modules.people.student.module import PERSON_MODULE
from backend.modules.people.student.office_hours_api import router as office_hours_router
from backend.modules.people.student.panel_queries import build_student_panel_context

list_teachers = list_office_hours_teachers

__all__ = [
    "PERSON_MODULE",
    "activity_router",
    "build_dashboard_url",
    "build_student_panel_context",
    "build_subject_leaderboard",
    "chat_router",
    "collect_subject_dashboards_from_cache",
    "collect_subject_dashboards_from_dataset",
    "comments_router",
    "current_auth_login",
    "current_auth_role",
    "current_student_db_id",
    "current_student_enrollment_id",
    "current_student_school_code",
    "dashboard_service",
    "get_group_cache_entry",
    "get_student_db_id_by_enrollment_id",
    "is_full_form",
    "list_announcements",
    "list_enrolled_subject_options",
    "list_teachers",
    "load_dataset",
    "office_hours_router",
    "payload_service",
    "record_student_activity",
    "resources_service",
    "seed_group_cache_from_dataset",
    "url_for",
]
