"""Recruitment appointment use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment import notifications as recruitment_notifications
from backend.modules.hr.recruitment.constants import (
    ALTERNATIVE_STAGES,
    APPOINTMENT_DISPLAY_STATUSES,
    APPOINTMENT_STATUSES,
    APPOINTMENT_TYPES,
)
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import (
    appointment_payload as _appointment_payload,
    text as _text,
)


@dataclass(frozen=True)
class AppointmentDependencies:
    connect: Callable[..., Any]
    lock_candidate: Callable[..., Any]
    get_candidate: Callable[..., dict[str, Any]]
    sync_next_actions: Callable[..., None]
    add_record: Callable[..., dict[str, Any]]
    prepare_appointment: Callable[..., dict[str, Any]]
    ensure_demo_assignment: Callable[..., None]
    audit_appointment: Callable[..., None]
    academic_visible_id: Callable[..., int | None]
    visible_subject_ids: Callable[..., set[int] | None]
    school_datetime: Callable[..., datetime]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actor_account(user: CurrentUser) -> int | None:
    return int(user.account_id) if user.account_id else None


def _actor_staff(user: CurrentUser) -> int | None:
    return int(user.staff_id) if user.staff_id else None


def _appointment_payload_for_user(
    user: CurrentUser, row: Any
) -> dict[str, Any]:
    payload = _appointment_payload(row)
    appointment_type = _text(payload.get("appointment_type"))
    actor_account_id = _actor_account(user)
    responsible_account_id = payload.get("responsible_account_id")
    is_authorized = (
        user.role == "hr_manager"
        if appointment_type == "job_interview"
        else actor_account_id is not None
        and responsible_account_id is not None
        and int(responsible_account_id) == int(actor_account_id)
    )
    status = _text(payload.get("status"))
    payload["can_start"] = is_authorized and status == "scheduled"
    payload["can_resume"] = is_authorized and status == "in_progress"
    payload["can_undo_start"] = (
        is_authorized
        and status == "in_progress"
        and bool(_text(payload.get("pre_start_starts_at")))
    )
    return payload


def start_appointment_session(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    expected_version: int,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    now = _now()
    with dependencies.connect() as conn:
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
            for_update=True,
        )
        if not appointment:
            raise RecruitmentError("Appointment was not found.", status_code=404)
        appointment_type = _text(appointment["appointment_type"])
        if appointment_type == "job_interview" and user.role != "hr_manager":
            raise RecruitmentError(
                "Only HR can start a job interview.", status_code=403
            )
        if appointment_type == "demo_lesson" and int(
            appointment["responsible_account_id"] or 0
        ) != int(_actor_account(user) or 0):
            raise RecruitmentError(
                "Only the assigned evaluator can start this demo lesson.",
                status_code=403,
            )
        if _text(appointment["status"]) == "in_progress":
            conn.commit()
            return {
                "candidate": dependencies.get_candidate(user, int(candidate_id)),
                "appointment": _appointment_payload_for_user(user, appointment),
            }
        if _text(appointment["status"]) != "scheduled":
            raise RecruitmentError(
                "This appointment can no longer be started.", status_code=409
            )
        original_starts_at = _text(appointment["starts_at"])
        started = repository.start_appointment_session(
            conn,
            appointment_id=int(appointment_id),
            candidate_id=int(candidate_id),
            expected_version=int(expected_version),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not started:
            raise RecruitmentError(
                "This interview changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        recruitment_notifications.cancel_appointment_reminders(
            conn, int(appointment_id)
        )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type=(
                "candidate.interview_started"
                if appointment_type == "job_interview"
                else "candidate.demo_lesson_started"
            ),
            appointment_id=int(appointment_id),
            detail={
                "scheduled_starts_at": original_starts_at,
                "started_at": now,
                "scheduled_time_overwritten": True,
            },
            now=now,
        )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        saved = repository.get_appointment_row(
            conn, candidate_id=int(candidate_id), appointment_id=int(appointment_id)
        )
        conn.commit()
    return {
        "candidate": dependencies.get_candidate(user, int(candidate_id)),
        "appointment": _appointment_payload_for_user(user, saved) if saved else None,
    }


def start_interview_session(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    expected_version: int,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    """Compatibility wrapper for clients using the original interview route."""

    return start_appointment_session(
        user,
        candidate_id,
        appointment_id,
        expected_version=expected_version,
        dependencies=dependencies,
    )


def undo_appointment_start(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    expected_version: int,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    """Undo an accidental start and restore the appointment's saved schedule."""

    now = _now()
    with dependencies.connect() as conn:
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
            for_update=True,
        )
        if not appointment:
            raise RecruitmentError("Appointment was not found.", status_code=404)
        appointment_type = _text(appointment["appointment_type"])
        if appointment_type == "job_interview" and user.role != "hr_manager":
            raise RecruitmentError(
                "Only HR can cancel a started job interview.", status_code=403
            )
        if appointment_type == "demo_lesson" and int(
            appointment["responsible_account_id"] or 0
        ) != int(_actor_account(user) or 0):
            raise RecruitmentError(
                "Only the assigned evaluator can cancel this demo lesson start.",
                status_code=403,
            )
        if _text(appointment["status"]) != "in_progress":
            raise RecruitmentError(
                "Only an in-progress appointment can have its start cancelled.",
                status_code=409,
            )
        original_starts_at = _text(
            appointment["pre_start_starts_at"]
            if "pre_start_starts_at" in appointment
            else ""
        )
        if not original_starts_at:
            raise RecruitmentError(
                "The original scheduled time is unavailable. Refresh and try again after the latest update is deployed.",
                status_code=409,
            )
        cancelled_started_at = _text(appointment["started_at"])
        restored = repository.undo_appointment_start(
            conn,
            appointment_id=int(appointment_id),
            candidate_id=int(candidate_id),
            expected_version=int(expected_version),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not restored:
            raise RecruitmentError(
                "This appointment changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type=(
                "candidate.interview_start_cancelled"
                if appointment_type == "job_interview"
                else "candidate.demo_lesson_start_cancelled"
            ),
            appointment_id=int(appointment_id),
            detail={
                "cancelled_started_at": cancelled_started_at,
                "restored_starts_at": original_starts_at,
                "restored_schedule": True,
            },
            now=now,
        )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        saved = repository.get_appointment_row(
            conn, candidate_id=int(candidate_id), appointment_id=int(appointment_id)
        )
        if saved:
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=saved,
                event_type="demo_rescheduled",
                version_token=int(saved["version"] or 1),
                include_reminders=True,
            )
        conn.commit()
    return {
        "candidate": dependencies.get_candidate(user, int(candidate_id)),
        "appointment": (
            _appointment_payload_for_user(user, saved) if saved else None
        ),
    }


def complete_interview_session(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    values: dict[str, Any],
    *,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    if _text(values.get("result")) not in {"passed", "failed"}:
        raise RecruitmentError("Choose Pass or Fail.")
    return dependencies.add_record(
        user,
        candidate_id,
        {
            "appointment_id": int(appointment_id),
            "expected_version": int(values.get("expected_version") or 0),
            "notes": "",
            "result": _text(values.get("result")),
            "reason_detail": _text(values.get("reason_detail")),
            "interviewer_account_id": _actor_account(user),
            "english_level_option_id": values.get("english_level_option_id"),
            "education_background": _text(values.get("education_background")),
            "teaching_experience_option_id": values.get(
                "teaching_experience_option_id"
            ),
            "interests_hobbies": _text(values.get("interests_hobbies")),
            "motivation_expectations": _text(values.get("motivation_expectations")),
        },
        "candidate.interview_recorded",
        repository.insert_interview,
        appointment_type="job_interview",
        timestamp_key="interview_at",
    )


def create_appointment(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    appointment_type = _text(values.get("appointment_type"))
    now = _now()
    appointment_id = 0
    with dependencies.connect() as conn:
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if _text(candidate["status"]) in {
            "active_teacher",
            *ALTERNATIVE_STAGES,
        }:
            raise RecruitmentError(
                "Reopen this candidate before adding an appointment.", status_code=409
            )
        # Interviews can be scheduled from the Interview Schedule stage onward;
        # demo lessons anywhere in the interview/demo phase. This lets HR, e.g.,
        # book the interview straight from the Interview Schedule column or
        # record a missed interview for a candidate already in Test & Demo.
        allowed_stages = (
            {"responded", "job_interview", "test_and_demo", "teacher_academy"}
            if appointment_type == "job_interview"
            else {"job_interview", "test_and_demo", "teacher_academy"}
        )
        if _text(candidate["status"]) not in allowed_stages:
            raise RecruitmentError(
                "Move the candidate to Interview Schedule, Job Interview, Test & Demo, or Teacher Academy before scheduling this appointment."
                if appointment_type == "job_interview"
                else "Move the candidate to Job Interview, Test & Demo, or Teacher Academy before scheduling this appointment.",
                status_code=409,
            )
        existing_appointment = repository.active_appointment_for_type(
            conn, candidate_id=int(candidate_id), appointment_type=appointment_type
        )
        if existing_appointment:
            raise RecruitmentError(
                "This candidate already has an active appointment of this type. Reschedule it instead.",
                status_code=409,
                code="appointment_already_scheduled",
                details={"appointment_id": int(existing_appointment["id"])},
            )
        prepared = dependencies.prepare_appointment(
            conn,
            user=user,
            candidate=candidate,
            appointment_type=appointment_type,
            values=values,
            job_interviewer_account_id=_actor_account(user),
        )
        dependencies.ensure_demo_assignment(
            conn,
            candidate=candidate,
            values=prepared,
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        appointment_id = repository.insert_appointment(
            conn,
            candidate_id=int(candidate_id),
            values=prepared,
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type="candidate.appointment_scheduled",
            appointment_id=appointment_id,
            detail={
                "appointment_type": appointment_type,
                "starts_at": prepared["starts_at"],
                "ends_at": prepared["ends_at"],
            },
            now=now,
        )
        saved_appointment = (
            repository.get_appointment_row(
                conn, candidate_id=int(candidate_id), appointment_id=appointment_id
            )
            if hasattr(conn, "execute")
            else None
        )
        if saved_appointment:
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=saved_appointment,
                event_type="demo_assigned",
                version_token=int(saved_appointment["version"] or 1),
                include_reminders=True,
            )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    result = dependencies.get_candidate(user, int(candidate_id))
    appointment = next(
        (
            item
            for item in result.get("appointments", [])
            if int(item.get("id") or 0) == appointment_id
        ),
        None,
    )
    return {"candidate": result, "appointment": appointment}


def list_appointments(
    user: CurrentUser,
    *,
    page: int = 1,
    per_page: int = 50,
    starts_from: str = "",
    starts_to: str = "",
    appointment_type: str = "",
    status: str = "",
    responsible_account_id: int | None = None,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    if appointment_type and appointment_type not in APPOINTMENT_TYPES:
        raise RecruitmentError("Unknown appointment type.")
    effective_appointment_type = (
        "demo_lesson"
        if user.role in {"academic_director", "head_of_department"}
        else appointment_type
    )
    appointment_statuses = [
        _text(item) for item in _text(status).split(",") if _text(item)
    ]
    raw_statuses = [
        item
        for item in appointment_statuses
        if item in APPOINTMENT_STATUSES
        and item not in APPOINTMENT_DISPLAY_STATUSES
    ]
    display_statuses = [
        item
        for item in appointment_statuses
        if item in APPOINTMENT_DISPLAY_STATUSES
    ]
    if any(
        item not in APPOINTMENT_STATUSES
        and item not in APPOINTMENT_DISPLAY_STATUSES
        for item in appointment_statuses
    ):
        raise RecruitmentError("Unknown appointment status.")
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 50), 500))
    normalized_from = (
        dependencies.school_datetime(starts_from).isoformat() if starts_from else ""
    )
    normalized_to = (
        dependencies.school_datetime(starts_to).isoformat() if starts_to else ""
    )
    with dependencies.connect() as conn:
        rows, total = repository.list_appointment_rows(
            conn,
            visible_account_id=dependencies.academic_visible_id(user),
            visible_subject_ids=dependencies.visible_subject_ids(user, conn),
            starts_from=normalized_from,
            starts_to=normalized_to,
            appointment_type=effective_appointment_type,
            status=",".join(raw_statuses),
            display_status=",".join(display_statuses),
            responsible_account_id=responsible_account_id,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    return {
        "items": [_appointment_payload_for_user(user, item) for item in rows],
        "page": safe_page,
        "per_page": safe_per_page,
        "total": total,
        "total_pages": max(1, ceil(total / safe_per_page)) if total else 1,
    }


def update_appointment(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    values: dict[str, Any],
    *,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    now = _now()
    with dependencies.connect() as conn:
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
            for_update=True,
        )
        if not candidate or not appointment:
            raise RecruitmentError("Appointment was not found.", status_code=404)
        if _text(appointment["status"]) != "scheduled":
            raise RecruitmentError(
                "Only scheduled appointments can be changed.", status_code=409
            )
        prepared = dependencies.prepare_appointment(
            conn,
            user=user,
            candidate=candidate,
            appointment_type=_text(appointment["appointment_type"]),
            values=values,
            exclude_appointment_id=int(appointment_id),
            existing_note=_text(appointment["note"]),
            job_interviewer_account_id=int(appointment["responsible_account_id"] or 0)
            or _actor_account(user),
        )
        dependencies.ensure_demo_assignment(
            conn,
            candidate=candidate,
            values=prepared,
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        old_demo_evaluator = int(appointment["responsible_account_id"] or 0)
        new_demo_evaluator = int(prepared.get("responsible_account_id") or 0)
        if (
            _text(appointment["appointment_type"]) == "demo_lesson"
            and old_demo_evaluator
            and (old_demo_evaluator != new_demo_evaluator)
        ):
            recruitment_notifications.cancel_demo_reminders(conn, int(appointment_id))
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=appointment,
                event_type="demo_cancelled",
                version_token=f"reassigned:{int(appointment['version'] or 1)}",
            )
        updated = repository.update_appointment(
            conn,
            appointment_id=int(appointment_id),
            candidate_id=int(candidate_id),
            expected_version=int(values.get("expected_version") or 0),
            values=prepared,
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not updated:
            raise RecruitmentError(
                "This appointment changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type="candidate.appointment_rescheduled",
            appointment_id=int(appointment_id),
            detail={
                "starts_at": prepared["starts_at"],
                "ends_at": prepared["ends_at"],
            },
            now=now,
        )
        saved_appointment = repository.get_appointment_row(
            conn, candidate_id=int(candidate_id), appointment_id=int(appointment_id)
        )
        if saved_appointment:
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=saved_appointment,
                event_type="demo_rescheduled",
                version_token=int(saved_appointment["version"] or 1),
                include_reminders=True,
            )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    return {"candidate": dependencies.get_candidate(user, int(candidate_id))}


def change_appointment_status(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    status: str,
    expected_version: int,
    reason: str,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    if status not in {"cancelled", "no_show"}:
        raise RecruitmentError("Unknown appointment status action.")
    if status == "cancelled" and (not _text(reason)):
        raise RecruitmentError("Add a cancellation reason.")
    now = _now()
    with dependencies.connect() as conn:
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
            for_update=True,
        )
        if not appointment:
            raise RecruitmentError("Appointment was not found.", status_code=404)
        updated = repository.set_appointment_status(
            conn,
            appointment_id=int(appointment_id),
            candidate_id=int(candidate_id),
            expected_version=int(expected_version),
            status=status,
            reason=_text(reason),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not updated:
            raise RecruitmentError(
                "This appointment changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type=f"candidate.appointment_{status}",
            appointment_id=int(appointment_id),
            detail={"reason": _text(reason)},
            now=now,
        )
        changed_appointment = repository.get_appointment_row(
            conn, candidate_id=int(candidate_id), appointment_id=int(appointment_id)
        )
        recruitment_notifications.cancel_appointment_reminders(
            conn, int(appointment_id)
        )
        if (
            changed_appointment
            and _text(
                changed_appointment["appointment_type"]
                if "appointment_type" in changed_appointment
                else ""
            )
            == "demo_lesson"
        ):
            recruitment_notifications.cancel_demo_reminders(conn, int(appointment_id))
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=changed_appointment,
                event_type=(
                    "demo_cancelled" if status == "cancelled" else "demo_no_show"
                ),
                version_token=int(changed_appointment["version"] or 1),
            )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    return {"candidate": dependencies.get_candidate(user, int(candidate_id))}


__all__ = [
    "AppointmentDependencies",
    "change_appointment_status",
    "complete_interview_session",
    "create_appointment",
    "list_appointments",
    "start_appointment_session",
    "start_interview_session",
    "undo_appointment_start",
    "update_appointment",
]
