"""Public academic use cases used by person orchestration modules."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.unit_of_work import Connection
from backend.modules.domains.academics import admission_repository
from backend.modules.domains.academics.assessments.service import record_exam_from_payload
from backend.modules.domains.academics.attendance.service import record_attendance_from_payload
from backend.modules.domains.academics.calendar.service import (
    CalendarClosureConflictError,
    create_calendar_closure,
    list_calendar_closures,
    preview_calendar_closure,
    unlock_calendar_closure,
)
from backend.modules.domains.academics.curriculum.service import (
    list_lesson_catalog_for_subject,
)
from backend.modules.domains.academics.exceptions import AcademicConflictError
from backend.modules.domains.academics.gradebook.homework import record_homework_from_payload
from backend.modules.domains.academics.gradebook.rating import (
    build_students_by_subject_group,
    build_subject_leaderboard,
    collect_subject_dashboards_from_cache,
    collect_subject_dashboards_from_dataset,
    compute_subject_rating,
    extract_attendance_rate,
    extract_exam_average_score,
    get_group_cache_entry,
    is_full_form,
    load_dashboard_payload,
    load_dataset,
    round_grade_half_up,
    seed_group_cache_from_dataset,
)
from backend.modules.domains.academics.gradebook.rewards import record_coin_from_payload
from backend.modules.domains.academics.gradebook.service import (
    get_enrollment_gradebook_summary,
    get_group_gradebook,
)
from backend.modules.domains.academics.gradebook.trends import get_group_gradebook_trends
from backend.modules.domains.academics.groups.operations import (
    create_group_from_payload,
    create_student_with_enrollment_from_payload,
    delete_group,
    list_academic_management_context,
    move_enrollment_group_from_payload,
    update_enrollment_status_from_payload,
)
from backend.modules.domains.academics.groups.read_service import (
    get_group_summary,
    list_group_page,
    list_group_schedule_rows,
    list_program_item_page,
    list_program_page,
    list_timetable_range,
)
from backend.modules.domains.academics.groups.service import list_academic_management_rows
from backend.modules.domains.academics.head_of_departments_cards import (
    head_of_department_workspace_cards,
)
from backend.modules.domains.academics.lessons.service import (
    update_lesson_session_from_payload,
)
from backend.modules.domains.academics.resources.comments_service import (
    COMMENT_MAX_LENGTH,
    add_resource_comment,
    list_resource_comments,
)
from backend.modules.domains.academics.resources.service import (
    list_resources,
    list_resources_grouped_by_type_old_to_new,
)
from backend.modules.domains.academics.schemas import (
    AcademicManagementAcademicContextDelta,
    AcademicManagementAcademicContextPayload,
    AcademicManagementCalendarClosureRequest,
    AcademicManagementCalendarClosureUnlockRequest,
    AcademicManagementCreateAcademicClassRequest,
    AcademicManagementCreateAcademicGroupRequest,
    AcademicManagementCreateAcademicSchoolRequest,
    AcademicManagementCreateGroupStudentRequest,
    AcademicManagementCreateScheduleRequest,
    AcademicManagementEnrollmentGroupRequest,
    AcademicManagementEnrollmentStatusRequest,
    AcademicManagementEnrollmentUpdated,
    AcademicManagementLessonCancelRequest,
    AcademicManagementLessonRecoverRequest,
    AcademicManagementLessonUpdated,
    AcademicManagementLessonUpdateRequest,
    AcademicManagementRecordAttendanceRequest,
    AcademicManagementRecordCoinRequest,
    AcademicManagementRecordCreated,
    AcademicManagementRecordExamRequest,
    AcademicManagementRecordHomeworkRequest,
    AcademicManagementScheduleCreated,
    AcademicManagementStudentCreated,
    AcademicManagementUpdateGroupScheduleRequest,
    CreateHeadOfDepartmentForm,
    HeadOfDepartmentCreated,
    HeadOfDepartmentPasswordReset,
)
from backend.modules.domains.academics.timetable.office_hours_service import (
    create_booking,
    list_availabilities,
    list_bookings,
    update_booking_status,
)
from backend.modules.domains.academics.timetable.operations import (
    cancel_lesson_session,
    create_schedule_from_payload,
    recover_lesson_session,
    upsert_group_schedule_from_payload,
)


@dataclass(frozen=True)
class ActivateAdmissionEnrollmentsCommand:
    student_id: int
    group_ids: tuple[int, ...]


@dataclass(frozen=True)
class ActivateAdmissionEnrollmentsResult:
    legacy_enrollment_ids: tuple[int, ...]


def activate_admission_enrollments(
    conn: Connection,
    command: ActivateAdmissionEnrollmentsCommand,
) -> ActivateAdmissionEnrollmentsResult:
    if command.student_id <= 0 or not command.group_ids:
        raise ValueError("A student and at least one group are required.")
    enrollment_ids = admission_repository.activate_group_enrollments(
        conn,
        student_id=command.student_id,
        group_ids=command.group_ids,
    )
    return ActivateAdmissionEnrollmentsResult(
        legacy_enrollment_ids=enrollment_ids,
    )


def list_office_hours_teachers():
    from backend.modules.domains.teacher_records.contracts import list_teachers

    return list_teachers()


__all__ = [
    "ActivateAdmissionEnrollmentsCommand",
    "ActivateAdmissionEnrollmentsResult",
    "AcademicConflictError",
    "AcademicManagementAcademicContextDelta",
    "AcademicManagementAcademicContextPayload",
    "AcademicManagementCalendarClosureRequest",
    "AcademicManagementCalendarClosureUnlockRequest",
    "AcademicManagementCreateAcademicClassRequest",
    "AcademicManagementCreateAcademicGroupRequest",
    "AcademicManagementCreateAcademicSchoolRequest",
    "AcademicManagementCreateGroupStudentRequest",
    "AcademicManagementCreateScheduleRequest",
    "AcademicManagementEnrollmentGroupRequest",
    "AcademicManagementEnrollmentStatusRequest",
    "AcademicManagementEnrollmentUpdated",
    "AcademicManagementLessonCancelRequest",
    "AcademicManagementLessonRecoverRequest",
    "AcademicManagementLessonUpdateRequest",
    "AcademicManagementLessonUpdated",
    "AcademicManagementRecordAttendanceRequest",
    "AcademicManagementRecordCoinRequest",
    "AcademicManagementRecordCreated",
    "AcademicManagementRecordExamRequest",
    "AcademicManagementRecordHomeworkRequest",
    "AcademicManagementScheduleCreated",
    "AcademicManagementStudentCreated",
    "AcademicManagementUpdateGroupScheduleRequest",
    "CalendarClosureConflictError",
    "COMMENT_MAX_LENGTH",
    "CreateHeadOfDepartmentForm",
    "HeadOfDepartmentCreated",
    "HeadOfDepartmentPasswordReset",
    "add_resource_comment",
    "activate_admission_enrollments",
    "build_subject_leaderboard",
    "build_students_by_subject_group",
    "collect_subject_dashboards_from_cache",
    "collect_subject_dashboards_from_dataset",
    "create_calendar_closure",
    "create_group_from_payload",
    "create_schedule_from_payload",
    "create_student_with_enrollment_from_payload",
    "create_booking",
    "compute_subject_rating",
    "extract_attendance_rate",
    "extract_exam_average_score",
    "get_enrollment_gradebook_summary",
    "get_group_cache_entry",
    "get_group_gradebook",
    "get_group_gradebook_trends",
    "get_group_summary",
    "head_of_department_workspace_cards",
    "is_full_form",
    "list_availabilities",
    "list_academic_management_context",
    "list_academic_management_rows",
    "list_bookings",
    "list_calendar_closures",
    "list_group_page",
    "list_group_schedule_rows",
    "list_lesson_catalog_for_subject",
    "list_office_hours_teachers",
    "list_program_item_page",
    "list_program_page",
    "list_resource_comments",
    "list_resources",
    "list_resources_grouped_by_type_old_to_new",
    "list_timetable_range",
    "load_dashboard_payload",
    "load_dataset",
    "move_enrollment_group_from_payload",
    "preview_calendar_closure",
    "record_attendance_from_payload",
    "record_coin_from_payload",
    "record_exam_from_payload",
    "record_homework_from_payload",
    "recover_lesson_session",
    "round_grade_half_up",
    "seed_group_cache_from_dataset",
    "cancel_lesson_session",
    "delete_group",
    "unlock_calendar_closure",
    "update_enrollment_status_from_payload",
    "update_lesson_session_from_payload",
    "update_booking_status",
    "upsert_group_schedule_from_payload",
]
