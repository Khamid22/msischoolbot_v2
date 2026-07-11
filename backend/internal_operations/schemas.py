"""Admin API v1 schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AdminCreateAvailabilityRequest(BaseModel):
    teacher_id: int
    starts_at: str
    ends_at: str
    slot_minutes: int = 30
    room: str = ""
    capacity: int = 1
    subject_id: int | None = None
    planned_topic: str = ""


class CancelAvailabilityRequest(BaseModel):
    status: str


class UpdateBookingStatusRequest(BaseModel):
    status: str
    teacher_note: str | None = None


class AvailabilityCreated(BaseModel):
    availability_id: int


class AvailabilityList(BaseModel):
    availabilities: list[dict[str, Any]]


class BookingList(BaseModel):
    bookings: list[dict[str, Any]]


class CreateAnnouncementRequest(BaseModel):
    title: str = ""
    body: str = ""
    audience: str = "all"
    priority: str = "info"
    status: str = "draft"
    pinned: bool = False
    scheduled_at: str = ""


class UpdateAnnouncementRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    audience: str | None = None
    priority: str | None = None
    status: str | None = None
    pinned: bool | None = None
    scheduled_at: str | None = None


class BlockStudentRequest(BaseModel):
    studentId: str = ""
    reason: str = ""


class AdminChatMessages(BaseModel):
    messages: list[dict[str, Any]]
    room: str


class BlockedStudents(BaseModel):
    blocked: list[dict[str, Any]]


class ChatRooms(BaseModel):
    rooms: list[dict[str, Any]]


class CreateComplaintRequest(BaseModel):
    parent_admin_id: int | None = None
    student_row_id: int | None = None
    student_id: int | None = None
    category: str = "other"
    topic: str = ""
    message: str = ""


class UpdateComplaintRequest(BaseModel):
    status: str | None = None
    reply: str | None = None
    assigned_to: str | None = None


class ComplaintReplyRequest(BaseModel):
    body: str | None = None
    reply: str | None = None
    status: str | None = None
    assigned_to: str | None = None


class ComplaintPayload(BaseModel):
    complaint: dict[str, Any]


class ComplaintList(BaseModel):
    complaints: list[dict[str, Any]]


class CreateStudentPaymentRequest(BaseModel):
    subject: str = ""
    currency: str = "UZS"
    paid_amount: float | None = None
    next_payment_amount: float | None = None
    remaining_debt: float | None = None
    amount: float | None = None
    month: str | None = None
    month_label: str | None = None
    status: str | None = None
    due_date: str | None = None
    paid_at: str | None = None
    paid_date: str | None = None
    next_payment_date: str | None = None
    notes: str | None = None


class MarkStudentPaymentRequest(BaseModel):
    paid: bool = True
    paid_at: str | None = None


class StudentPaymentPayload(BaseModel):
    student_row_id: int | None = None
    payment: dict[str, Any] | None = None
    payments: list[dict[str, Any]]
    summary: dict[str, Any]


class AdminCreateStudentRequest(BaseModel):
    full_name: str
    group_id: int


class AdminCreateAcademicSchoolRequest(BaseModel):
    school_name: str
    school_code: str = ""


class AdminCreateAcademicGroupRequest(BaseModel):
    school_code: str
    program_subject_key: str = ""
    program_subject_keys: list[str] = Field(default_factory=list)
    group_name: str
    group_code: str = ""
    class_id: int = 0
    set_name: str = "Set 1"


class AdminCreateAcademicClassRequest(BaseModel):
    school_code: str
    class_name: str
    class_code: str = ""


class AdminStudentsList(BaseModel):
    students: list[dict[str, Any]]


class AdminStudentCreated(BaseModel):
    student: dict[str, Any]


class AdminParentInviteCreated(BaseModel):
    invite_code: str
    inviteCode: str
    invite_url: str
    inviteUrl: str
    telegram_invite_url: str
    telegramInviteUrl: str
    web_invite_url: str
    webInviteUrl: str


class AdminCreateScheduleRequest(BaseModel):
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


class AdminUpdateGroupScheduleRequest(BaseModel):
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


class AdminScheduleCreated(BaseModel):
    schedule: dict[str, Any]
    schedules: list[dict[str, Any]]
    sessions: list[dict[str, Any]]
    lessons: list[dict[str, Any]]


class AdminAcademicContextDelta(BaseModel):
    group: dict[str, Any] | None = None
    groups: list[dict[str, Any]] = Field(default_factory=list)
    enrollments: list[dict[str, Any]] = Field(default_factory=list)
    schedules: list[dict[str, Any]] = Field(default_factory=list)
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    lessons: list[dict[str, Any]] = Field(default_factory=list)


class AdminAcademicContextPayload(BaseModel):
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


class AdminEnrollmentStatusRequest(BaseModel):
    status: str
    reason: str = ""


class AdminEnrollmentGroupRequest(BaseModel):
    group_id: int


class AdminEnrollmentUpdated(BaseModel):
    enrollment: dict[str, Any]
    groups: list[dict[str, Any]] | None = None


class AdminRecordAttendanceRequest(BaseModel):
    enrollment_id: int
    status: str = ""
    lesson_session_id: int | None = None
    lesson_id: int | None = None
    lesson_label: str = ""
    topic: str = ""
    lesson_date: str = ""
    attendance_type: str = "regular"


class AdminRecordHomeworkRequest(BaseModel):
    enrollment_id: int
    score: float
    lesson_session_id: int | None = None
    lesson_id: int | None = None
    lesson_label: str = ""
    topic: str = ""
    lesson_date: str = ""
    score_type: str = "Homework"


class AdminRecordExamRequest(BaseModel):
    enrollment_id: int
    exam_name: str = ""
    label: str = ""
    attempt: str = ""
    score: float


class AdminRecordCoinRequest(BaseModel):
    enrollment_id: int
    amount: int
    source: str = "manual"


class AdminRecordCreated(BaseModel):
    id: int


class AdminLessonUpdateRequest(BaseModel):
    lesson_date: str | None = None
    date: str | None = None
    status: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    room: str | None = None


class AdminLessonUpdated(BaseModel):
    lesson: dict[str, Any]


class AdminResourceList(BaseModel):
    resources: list[dict[str, Any]]


class AdminResourceUploadProgress(BaseModel):
    events: list[dict[str, Any]]
    latest_seq: int
    done: bool


class AssignParentChildRequest(BaseModel):
    student_row_id: int | None = None
    student_id: int | None = None
    parent_admin_id: int | None = None


class ParentChildAssigned(BaseModel):
    child: dict[str, Any]
