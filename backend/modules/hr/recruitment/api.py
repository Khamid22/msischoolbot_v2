"""Role-scoped Teacher Recruitment API v1 routes."""

from __future__ import annotations

from typing import Annotated, Any, Callable

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse

from backend.core.access import CurrentUser, get_current_user, require_role
from backend.core.api import api_success
from backend.modules.hr.recruitment import service
from backend.modules.hr.recruitment import notifications as recruitment_notifications
from backend.modules.hr.recruitment.constants import RECRUITMENT_ROLES
from backend.modules.hr.recruitment.policies import (
    ensure_academic_write,
    ensure_approval_request,
    ensure_approval_review,
    ensure_assignment_management,
    ensure_candidate_view,
    ensure_final_decision,
    ensure_hr_management,
    ensure_pipeline_management,
)
from backend.modules.hr.recruitment.schemas import (
    ApprovalRequestCreate,
    ApprovalReview,
    AppointmentCreate,
    AppointmentStatusChange,
    AppointmentUpdate,
    AssignmentReplace,
    CandidateCreate,
    CandidateHold,
    CandidateUpdate,
    DemoLessonWrite,
    EvaluationVoid,
    FinalDecisionCreate,
    InterviewWrite,
    NoteCreate,
    RecruitmentSettingCreate,
    ScheduledStageMove,
    StageChange,
    SubjectTestWrite,
    TaskWrite,
)
router = APIRouter(
    prefix="/recruitment",
    tags=["teacher-recruitment"],
    dependencies=[Depends(require_role(*RECRUITMENT_ROLES))],
)


def _call(operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return operation(*args, **kwargs)
    except service.RecruitmentError as exc:
        detail: str | dict[str, Any] = str(exc)
        if exc.code or exc.details is not None:
            detail = {"message": str(exc), "code": exc.code, "details": exc.details}
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc


@router.get("/pipeline", operation_id="api_v1_recruitment_pipeline")
def pipeline(
    search: str = "",
    position: str = "",
    source: str = "",
    application_from: str = "",
    application_to: str = "",
    evaluator_account_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return api_success(
        _call(
            service.list_pipeline,
            user,
            search=search,
            position=position,
            source=source,
            application_from=application_from,
            application_to=application_to,
            evaluator_account_id=evaluator_account_id,
        )
    )


@router.get("/candidates", operation_id="api_v1_recruitment_candidates")
def candidates(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    search: str = "",
    position: str = "",
    stage: str = "",
    source: str = "",
    application_from: str = "",
    application_to: str = "",
    final_decision: str = "",
    evaluator_account_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return api_success(
        _call(
            service.list_candidates,
            user,
            page=page,
            per_page=per_page,
            search=search,
            position=position,
            stage=stage,
            source=source,
            application_from=application_from,
            application_to=application_to,
            final_decision=final_decision,
            evaluator_account_id=evaluator_account_id,
        )
    )


@router.get("/decision-queue", operation_id="api_v1_recruitment_decision_queue")
def decision_queue(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    user: CurrentUser = Depends(require_role("academic_director")),
):
    return api_success(
        _call(
            service.list_decision_queue,
            user,
            page=page,
            per_page=per_page,
        )
    )


@router.get("/candidates/{candidate_id}", operation_id="api_v1_recruitment_candidate")
def candidate_detail(candidate_id: int, user: CurrentUser = Depends(get_current_user)):
    ensure_candidate_view(user, candidate_id)
    return api_success(_call(service.get_candidate, user, candidate_id))


@router.get("/tasks", operation_id="api_v1_recruitment_tasks")
def tasks(user: CurrentUser = Depends(get_current_user)):
    return api_success(_call(service.list_tasks, user))


@router.get("/appointments", operation_id="api_v1_recruitment_appointments")
def appointments(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 50,
    starts_from: Annotated[str, Query(alias="from")] = "",
    starts_to: Annotated[str, Query(alias="to")] = "",
    appointment_type: str = "",
    status: str = "scheduled",
    responsible_account_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return api_success(
        _call(
            service.list_appointments,
            user,
            page=page,
            per_page=per_page,
            starts_from=starts_from,
            starts_to=starts_to,
            appointment_type=appointment_type,
            status=status,
            responsible_account_id=responsible_account_id,
        )
    )


@router.get("/notifications", operation_id="api_v1_recruitment_notifications")
def notifications(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    user: CurrentUser = Depends(get_current_user),
):
    if not user.account_id:
        raise HTTPException(status_code=403, detail="An account is required for notifications.")
    return api_success(
        recruitment_notifications.list_notifications(
            int(user.account_id), page=page, per_page=per_page
        )
    )


@router.get("/notifications/unread-count", operation_id="api_v1_recruitment_notification_unread_count")
def notification_unread_count(user: CurrentUser = Depends(get_current_user)):
    if not user.account_id:
        raise HTTPException(status_code=403, detail="An account is required for notifications.")
    return api_success({"unread_count": recruitment_notifications.unread_count(int(user.account_id))})


@router.post("/notifications/{notification_id}/read", operation_id="api_v1_recruitment_notification_read")
def mark_notification_read(notification_id: int, user: CurrentUser = Depends(get_current_user)):
    if not user.account_id:
        raise HTTPException(status_code=403, detail="An account is required for notifications.")
    if not recruitment_notifications.mark_notification_read(int(user.account_id), int(notification_id)):
        raise HTTPException(status_code=404, detail="Notification was not found.")
    return api_success({"message": "Notification marked as read."})


@router.get("/options", operation_id="api_v1_recruitment_options")
def options():
    return api_success(_call(service.options))


@router.get("/settings", operation_id="api_v1_recruitment_settings")
def settings(user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    return api_success(_call(service.list_settings, user))


@router.post("/settings", status_code=201, operation_id="api_v1_recruitment_create_setting")
def create_setting(
    payload: RecruitmentSettingCreate,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_hr_management(user)
    setting = _call(
        service.add_setting,
        user,
        category=payload.category,
        label=payload.label,
    )
    return api_success(
        {"message": "Recruitment setting added.", "setting": setting},
        status_code=201,
    )


@router.delete("/settings/{setting_id}", operation_id="api_v1_recruitment_remove_setting")
def remove_setting(setting_id: int, user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    setting = _call(service.remove_setting, user, setting_id)
    return api_success({"message": "Recruitment setting removed.", "setting": setting})


@router.post("/candidates", status_code=201, operation_id="api_v1_recruitment_create_candidate")
def create_candidate(payload: CandidateCreate, user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    candidate = _call(service.create_candidate, user, payload.model_dump())
    return api_success({"message": "Candidate created.", "candidate": candidate}, status_code=201)


@router.patch("/candidates/{candidate_id}", operation_id="api_v1_recruitment_update_candidate")
def update_candidate(candidate_id: int, payload: CandidateUpdate, user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    candidate = _call(
        service.update_candidate,
        user,
        candidate_id,
        payload.model_dump(exclude_unset=True),
    )
    return api_success({"message": "Candidate profile updated.", "candidate": candidate})


@router.post("/candidates/{candidate_id}/stage", operation_id="api_v1_recruitment_move_candidate")
def move_candidate(candidate_id: int, payload: StageChange, user: CurrentUser = Depends(get_current_user)):
    ensure_pipeline_management(user)
    ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.move_candidate,
        user,
        candidate_id,
        stage=payload.stage,
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    message = "Candidate moved to Trash Bin." if payload.stage == "trash_bin" else "Candidate moved."
    return api_success({"message": message, "candidate": candidate})


@router.post("/candidates/{candidate_id}/hold", operation_id="api_v1_recruitment_hold_candidate")
def hold_candidate(
    candidate_id: int,
    payload: CandidateHold,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_pipeline_management(user)
    ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.hold_candidate,
        user,
        candidate_id,
        expected_version=payload.expected_version,
        reason=payload.reason,
        application_date=payload.application_date,
    )
    return api_success({"message": "Candidate placed On Hold.", "candidate": candidate})


@router.post(
    "/candidates/{candidate_id}/scheduled-stage-moves",
    status_code=201,
    operation_id="api_v1_recruitment_scheduled_stage_move",
)
def scheduled_stage_move(
    candidate_id: int,
    payload: ScheduledStageMove,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_pipeline_management(user)
    result = _call(service.schedule_stage_move, user, candidate_id, payload.model_dump())
    return api_success({"message": "Appointment scheduled and candidate moved.", **result}, status_code=201)


@router.post(
    "/candidates/{candidate_id}/appointments",
    status_code=201,
    operation_id="api_v1_recruitment_create_appointment",
)
def create_appointment(
    candidate_id: int,
    payload: AppointmentCreate,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_pipeline_management(user)
    result = _call(service.create_appointment, user, candidate_id, payload.model_dump())
    return api_success({"message": "Appointment scheduled.", **result}, status_code=201)


@router.patch(
    "/candidates/{candidate_id}/appointments/{appointment_id}",
    operation_id="api_v1_recruitment_update_appointment",
)
def update_appointment(
    candidate_id: int,
    appointment_id: int,
    payload: AppointmentUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_pipeline_management(user)
    result = _call(service.update_appointment, user, candidate_id, appointment_id, payload.model_dump())
    return api_success({"message": "Appointment rescheduled.", **result})


@router.post(
    "/candidates/{candidate_id}/appointments/{appointment_id}/cancel",
    operation_id="api_v1_recruitment_cancel_appointment",
)
def cancel_appointment(
    candidate_id: int,
    appointment_id: int,
    payload: AppointmentStatusChange,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_pipeline_management(user)
    result = _call(
        service.change_appointment_status,
        user,
        candidate_id,
        appointment_id,
        status="cancelled",
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    return api_success({"message": "Appointment cancelled.", **result})


@router.post(
    "/candidates/{candidate_id}/appointments/{appointment_id}/no-show",
    operation_id="api_v1_recruitment_no_show_appointment",
)
def no_show_appointment(
    candidate_id: int,
    appointment_id: int,
    payload: AppointmentStatusChange,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_pipeline_management(user)
    result = _call(
        service.change_appointment_status,
        user,
        candidate_id,
        appointment_id,
        status="no_show",
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    return api_success({"message": "Appointment marked as no-show.", **result})


@router.put("/candidates/{candidate_id}/assignments", operation_id="api_v1_recruitment_assign_candidate")
def replace_assignments(
    candidate_id: int,
    payload: AssignmentReplace,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_assignment_management(user)
    ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.replace_assignments,
        user,
        candidate_id,
        assignee_account_ids=payload.assignee_account_ids,
        subject_id=payload.subject_id,
    )
    return api_success({"message": "Evaluator assignments updated.", "candidate": candidate})


@router.post("/candidates/{candidate_id}/interviews", status_code=201, operation_id="api_v1_recruitment_add_interview")
def add_interview(candidate_id: int, payload: InterviewWrite, user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    candidate = _call(service.add_interview, user, candidate_id, payload.model_dump())
    return api_success({"message": "Interview recorded.", "candidate": candidate}, status_code=201)


@router.post("/candidates/{candidate_id}/subject-tests", status_code=201, operation_id="api_v1_recruitment_add_subject_test")
def add_subject_test(candidate_id: int, payload: SubjectTestWrite, user: CurrentUser = Depends(get_current_user)):
    ensure_academic_write(user, candidate_id)
    candidate = _call(service.add_subject_test, user, candidate_id, payload.model_dump())
    return api_success({"message": "Subject test recorded.", "candidate": candidate}, status_code=201)


@router.post("/candidates/{candidate_id}/demo-lessons", status_code=201, operation_id="api_v1_recruitment_add_demo")
def add_demo(candidate_id: int, payload: DemoLessonWrite, user: CurrentUser = Depends(get_current_user)):
    ensure_academic_write(user, candidate_id)
    candidate = _call(service.add_demo, user, candidate_id, payload.model_dump())
    return api_success({"message": "Demo lesson recorded.", "candidate": candidate}, status_code=201)


@router.post(
    "/candidates/{candidate_id}/interviews/{attempt_id}/void",
    operation_id="api_v1_recruitment_void_interview",
)
def void_interview(
    candidate_id: int,
    attempt_id: int,
    payload: EvaluationVoid,
    user: CurrentUser = Depends(get_current_user),
):
    if user.role in {"academic_director", "head_of_department"}:
        ensure_academic_write(user, candidate_id)
    else:
        ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.void_evaluation,
        user,
        candidate_id,
        evaluation_type="interview",
        attempt_id=attempt_id,
        reason=payload.reason,
    )
    return api_success({"message": "Interview result voided.", "candidate": candidate})


@router.post(
    "/candidates/{candidate_id}/subject-tests/{attempt_id}/void",
    operation_id="api_v1_recruitment_void_subject_test",
)
def void_subject_test(
    candidate_id: int,
    attempt_id: int,
    payload: EvaluationVoid,
    user: CurrentUser = Depends(get_current_user),
):
    if user.role in {"academic_director", "head_of_department"}:
        ensure_academic_write(user, candidate_id)
    else:
        ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.void_evaluation,
        user,
        candidate_id,
        evaluation_type="subject_test",
        attempt_id=attempt_id,
        reason=payload.reason,
    )
    return api_success({"message": "Subject-test result voided.", "candidate": candidate})


@router.post(
    "/candidates/{candidate_id}/demo-lessons/{attempt_id}/void",
    operation_id="api_v1_recruitment_void_demo",
)
def void_demo(
    candidate_id: int,
    attempt_id: int,
    payload: EvaluationVoid,
    user: CurrentUser = Depends(get_current_user),
):
    if user.role in {"academic_director", "head_of_department"}:
        ensure_academic_write(user, candidate_id)
    else:
        ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.void_evaluation,
        user,
        candidate_id,
        evaluation_type="demo",
        attempt_id=attempt_id,
        reason=payload.reason,
    )
    return api_success({"message": "Demo result voided.", "candidate": candidate})


@router.post("/candidates/{candidate_id}/tasks", status_code=201, operation_id="api_v1_recruitment_create_task")
def create_task(candidate_id: int, payload: TaskWrite, user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    candidate = _call(service.save_task, user, candidate_id, payload.model_dump())
    return api_success({"message": "Task created.", "candidate": candidate}, status_code=201)


@router.put("/candidates/{candidate_id}/tasks/{task_id}", operation_id="api_v1_recruitment_update_task")
def update_task(
    candidate_id: int,
    task_id: int,
    payload: TaskWrite,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_hr_management(user)
    candidate = _call(service.save_task, user, candidate_id, payload.model_dump(), task_id=task_id)
    return api_success({"message": "Task updated.", "candidate": candidate})


@router.post("/candidates/{candidate_id}/notes", status_code=201, operation_id="api_v1_recruitment_add_note")
def add_note(candidate_id: int, payload: NoteCreate, user: CurrentUser = Depends(get_current_user)):
    ensure_candidate_view(user, candidate_id)
    candidate = _call(service.add_note, user, candidate_id, payload.body)
    return api_success({"message": "Note added.", "candidate": candidate}, status_code=201)


@router.post("/candidates/{candidate_id}/documents", status_code=201, operation_id="api_v1_recruitment_upload_document")
def upload_document(
    candidate_id: int,
    document_type: Annotated[str, Form()],
    document: Annotated[UploadFile, File()],
    replaces_document_id: Annotated[int | None, Form()] = None,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_hr_management(user)
    candidate = _call(
        service.upload_document,
        user,
        candidate_id,
        document_type=document_type,
        uploaded_file=document,
        replaces_document_id=replaces_document_id,
    )
    return api_success({"message": "Document uploaded.", "candidate": candidate}, status_code=201)


@router.get("/candidates/{candidate_id}/documents/{document_id}/open", operation_id="api_v1_recruitment_open_document")
def open_document(
    candidate_id: int,
    document_id: int,
    download: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_candidate_view(user, candidate_id)
    return RedirectResponse(_call(service.document_url, candidate_id, document_id, download=download), status_code=302)


@router.delete("/candidates/{candidate_id}/documents/{document_id}", operation_id="api_v1_recruitment_remove_document")
def remove_document(candidate_id: int, document_id: int, user: CurrentUser = Depends(get_current_user)):
    ensure_hr_management(user)
    candidate = _call(service.remove_document, user, candidate_id, document_id)
    return api_success({"message": "Document removed.", "candidate": candidate})


@router.post("/candidates/{candidate_id}/approval-requests", status_code=201, operation_id="api_v1_recruitment_request_approval")
def request_approval(
    candidate_id: int,
    payload: ApprovalRequestCreate,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_approval_request(user)
    ensure_candidate_view(user, candidate_id)
    candidate = _call(
        service.request_approval,
        user,
        candidate_id,
        requested_outcome=payload.requested_outcome,
        request_note=payload.request_note,
    )
    return api_success({"message": "Academic approval requested.", "candidate": candidate}, status_code=201)


@router.post("/candidates/{candidate_id}/approval-requests/{approval_id}/review", operation_id="api_v1_recruitment_review_approval")
def review_approval(
    candidate_id: int,
    approval_id: int,
    payload: ApprovalReview,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_approval_review(user, candidate_id)
    candidate = _call(
        service.review_approval,
        user,
        candidate_id,
        approval_id,
        status=payload.status,
        review_comment=payload.review_comment,
    )
    message = (
        "Candidate approved and finalized."
        if payload.status == "approved"
        else "Approval request returned."
    )
    return api_success({"message": message, "candidate": candidate})


@router.post("/candidates/{candidate_id}/final-decisions", status_code=201, operation_id="api_v1_recruitment_final_decision")
def final_decision(
    candidate_id: int,
    payload: FinalDecisionCreate,
    user: CurrentUser = Depends(get_current_user),
):
    ensure_final_decision(user, payload.decision)
    ensure_candidate_view(user, candidate_id)
    candidate = _call(service.make_final_decision, user, candidate_id, payload.model_dump())
    return api_success({"message": "Final decision recorded.", "candidate": candidate}, status_code=201)


__all__ = ["router"]
