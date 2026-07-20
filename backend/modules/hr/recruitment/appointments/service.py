"""Recruitment appointment use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment import notifications as recruitment_notifications
from backend.modules.hr.recruitment.constants import (
    ALTERNATIVE_STAGES,
    APPOINTMENT_STATUSES,
    APPOINTMENT_TYPES,
    PROTECTED_HIRE_STAGES,
)
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import (
    appointment_payload as _appointment_payload,
    parse_datetime as _parse_datetime,
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
    record_historical_result: Callable[..., dict[str, Any]]
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


def start_interview_session(
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
        if not appointment or _text(appointment["appointment_type"]) != "job_interview":
            raise RecruitmentError(
                "Job interview appointment was not found.", status_code=404
            )
        if _text(appointment["status"]) == "in_progress":
            conn.commit()
            return {
                "candidate": dependencies.get_candidate(user, int(candidate_id)),
                "appointment": _appointment_payload(appointment),
            }
        if _text(appointment["status"]) != "scheduled":
            raise RecruitmentError(
                "This interview can no longer be started.", status_code=409
            )
        starts_at = _parse_datetime(appointment["starts_at"])
        if starts_at and datetime.now(UTC) < starts_at - timedelta(minutes=30):
            raise RecruitmentError(
                "This interview can be started 30 minutes before its scheduled time.",
                status_code=409,
                code="interview_too_early",
                details={
                    "start_available_at": (
                        starts_at - timedelta(minutes=30)
                    ).isoformat()
                },
            )
        started = repository.start_interview_session(
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
            event_type="candidate.interview_started",
            appointment_id=int(appointment_id),
            detail={"started_at": now},
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
        "appointment": _appointment_payload(saved) if saved else None,
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
            "notes": _text(values.get("notes")),
            "result": _text(values.get("result")),
            "interviewer_account_id": _actor_account(user),
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
        if _text(candidate["status"]) in {*PROTECTED_HIRE_STAGES, *ALTERNATIVE_STAGES}:
            raise RecruitmentError(
                "Reopen this candidate before adding an appointment.", status_code=409
            )
        # Interviews can be scheduled from the Interview Schedule stage onward;
        # demo lessons anywhere in the interview/demo phase. This lets HR, e.g.,
        # book the interview straight from the Interview Schedule column or
        # record a missed interview for a candidate already in Test & Demo.
        allowed_stages = (
            {"responded", "job_interview", "test_and_demo"}
            if appointment_type == "job_interview"
            else {"job_interview", "test_and_demo"}
        )
        if _text(candidate["status"]) not in allowed_stages:
            raise RecruitmentError(
                "Move the candidate to the Interview Schedule, Job Interview, or Test & Demo stage before scheduling this appointment."
                if appointment_type == "job_interview"
                else "Move the candidate to the Job Interview or Test & Demo stage before scheduling this appointment.",
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
        if not prepared["is_historical"]:
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
        if prepared["is_historical"]:
            dependencies.record_historical_result(
                conn,
                user=user,
                candidate=candidate,
                appointment_id=appointment_id,
                prepared=prepared,
                now=now,
            )
        else:
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
    status: str = "scheduled,in_progress,completed",
    responsible_account_id: int | None = None,
    dependencies: AppointmentDependencies,
) -> dict[str, Any]:
    if appointment_type and appointment_type not in APPOINTMENT_TYPES:
        raise RecruitmentError("Unknown appointment type.")
    appointment_statuses = [
        _text(item) for item in _text(status).split(",") if _text(item)
    ]
    if any((item not in APPOINTMENT_STATUSES for item in appointment_statuses)):
        raise RecruitmentError("Unknown appointment status.")
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 50), 100))
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
            appointment_type=appointment_type,
            status=",".join(appointment_statuses),
            responsible_account_id=responsible_account_id,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    return {
        "items": [_appointment_payload(item) for item in rows],
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
        if not prepared["is_historical"]:
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
            not prepared["is_historical"]
            and _text(appointment["appointment_type"]) == "demo_lesson"
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
        if prepared["is_historical"]:
            recruitment_notifications.cancel_demo_reminders(conn, int(appointment_id))
            dependencies.record_historical_result(
                conn,
                user=user,
                candidate=candidate,
                appointment_id=int(appointment_id),
                prepared=prepared,
                now=now,
            )
        else:
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
    "start_interview_session",
    "update_appointment",
]
