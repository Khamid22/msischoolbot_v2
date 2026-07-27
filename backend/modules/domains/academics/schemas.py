"""Shared academic API schemas used by every authorized workspace adapter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AcademicManagementCreateGroupStudentRequest(BaseModel):
    full_name: str


class AcademicManagementPurgeGroupRequest(BaseModel):
    confirmation: str


class AcademicManagementStudentCreated(BaseModel):
    student: dict[str, Any]


class AcademicManagementCreateAcademicSchoolRequest(BaseModel):
    school_name: str
    school_code: str = ""


class AcademicManagementCreateAcademicGroupRequest(BaseModel):
    school_code: str
    program_subject_key: str = ""
    program_subject_keys: list[str] = Field(default_factory=list)
    group_name: str
    group_code: str = ""
    class_id: int = 0
    set_name: str = "Set 1"


class AcademicManagementCreateAcademicClassRequest(BaseModel):
    school_code: str
    class_name: str
    class_code: str = ""


class AcademicManagementCreateScheduleRequest(BaseModel):
    group_id: int
    teacher_id: int = 0
    weekdays: list[int] = Field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    lesson_duration_minutes: int = 0
    start_date: str = ""
    end_date: str = ""
    room: str = ""
    online_url: str = ""
    title: str = ""


class AcademicManagementUpdateGroupScheduleRequest(BaseModel):
    teacher_id: int = 0
    weekdays: list[int] = Field(default_factory=list)
    start_time: str = ""
    lesson_duration_minutes: int = 0
    start_date: str = ""
    predicted_end_date: str = ""
    room: str = ""
    online_url: str = ""
    title: str = "Regular class"
    course_launch_date: str = ""
    lesson_time: str = ""
    change_scope: str = ""
    effective_date: str = ""
    change_course_launch_date: bool = False
    allow_recorded_lesson_changes: bool = False


class AcademicManagementScheduleCreated(BaseModel):
    schedule: dict[str, Any]
    schedules: list[dict[str, Any]] = Field(default_factory=list)
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    lessons: list[dict[str, Any]] = Field(default_factory=list)
    entity: dict[str, Any] | None = None
    affected_ids: list[int] = Field(default_factory=list)
    revision: str = ""


class AcademicManagementAcademicContextDelta(BaseModel):
    group: dict[str, Any] | None = None
    groups: list[dict[str, Any]] = Field(default_factory=list)
    enrollments: list[dict[str, Any]] = Field(default_factory=list)
    schedules: list[dict[str, Any]] = Field(default_factory=list)
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    lessons: list[dict[str, Any]] = Field(default_factory=list)
    entity: dict[str, Any] | None = None
    affected_ids: list[int] = Field(default_factory=list)
    revision: str = ""


class AcademicManagementAcademicContextPayload(BaseModel):
    schools: list[dict[str, Any]] = Field(default_factory=list)
    classes: list[dict[str, Any]] = Field(default_factory=list)
    subjects: list[dict[str, Any]] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    enrollments: list[dict[str, Any]] = Field(default_factory=list)
    lessons: list[dict[str, Any]] = Field(default_factory=list)
    schedules: list[dict[str, Any]] = Field(default_factory=list)
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    curriculum_programs: list[dict[str, Any]] = Field(default_factory=list)
    curriculum_items: list[dict[str, Any]] = Field(default_factory=list)
    enrollment_summary: dict[str, Any] = Field(default_factory=dict)


class AcademicManagementEnrollmentStatusRequest(BaseModel):
    status: str
    reason: str = ""


class AcademicManagementEnrollmentGroupRequest(BaseModel):
    group_id: int


class AcademicManagementEnrollmentUpdated(BaseModel):
    enrollment: dict[str, Any]
    groups: list[dict[str, Any]] | None = None


class AcademicManagementRecordAttendanceRequest(BaseModel):
    enrollment_id: int
    status: str = ""
    lesson_session_id: int | None = None
    lesson_id: int | None = None
    lesson_label: str = ""
    topic: str = ""
    lesson_date: str = ""
    attendance_type: str = "regular"


class AcademicManagementRecordHomeworkRequest(BaseModel):
    enrollment_id: int
    score: float
    lesson_session_id: int | None = None
    lesson_id: int | None = None
    lesson_label: str = ""
    topic: str = ""
    lesson_date: str = ""
    score_type: str = "Homework"


class AcademicManagementRecordExamRequest(BaseModel):
    enrollment_id: int
    exam_name: str = ""
    label: str = ""
    attempt: str = ""
    score: float


class AcademicManagementRecordCoinRequest(BaseModel):
    enrollment_id: int
    amount: int
    source: str = "manual"


class AcademicManagementRecordCreated(BaseModel):
    id: int


class AcademicManagementLessonUpdateRequest(BaseModel):
    lesson_date: str | None = None
    date: str | None = None
    status: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    room: str | None = None
    lesson_name: str | None = None
    topic: str | None = None
    allow_recorded_lesson_changes: bool = False


class AcademicManagementLessonCancelRequest(BaseModel):
    reason: str
    allow_recorded_lesson_changes: bool = False


class AcademicManagementLessonRecoverRequest(BaseModel):
    allow_recorded_lesson_changes: bool = False


class AcademicManagementLessonUpdated(BaseModel):
    lesson: dict[str, Any]


class AcademicManagementCalendarClosureRequest(BaseModel):
    school_id: int
    group_id: int = 0
    title: str = "Summer holiday"
    start_date: str
    end_date: str


class AcademicManagementCalendarClosureUnlockRequest(BaseModel):
    rebuild_future: bool = False


class CreateHeadOfDepartmentForm(BaseModel):
    hod_display_name: str = ""
    hod_subject_id: str = ""


class HeadOfDepartmentCredentials(BaseModel):
    role: str = "head_of_department"
    login: str = ""
    temporary_password: str = ""
    display_name: str = ""
    subject_name: str = ""


class HeadOfDepartmentAccount(BaseModel):
    login: str = ""
    display_name: str = ""
    role: str = "head_of_department"
    status: str = "active"
    subject_name: str = ""


class HeadOfDepartmentCreated(BaseModel):
    message: str
    credentials: HeadOfDepartmentCredentials
    headOfDepartment: HeadOfDepartmentAccount


class HeadOfDepartmentPasswordReset(BaseModel):
    message: str
    login: str
    temporary_password: str
    display_name: str = ""
    must_change_password: bool = True
    updated_at: str = ""
