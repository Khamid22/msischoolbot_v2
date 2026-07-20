"""Recruitment evaluation use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment import notifications as recruitment_notifications
from backend.modules.hr.recruitment.constants import (
    DEMO_RESULTS,
    INTERVIEW_RESULTS,
    PROTECTED_HIRE_STAGES,
)
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import text as _text


@dataclass(frozen=True)
class EvaluationDependencies:
    connect: Callable[..., Any]
    lock_candidate: Callable[..., Any]
    get_candidate: Callable[..., dict[str, Any]]
    sync_next_actions: Callable[..., None]
    audit_appointment: Callable[..., None]
    notify_cancelled_appointments: Callable[..., None]
    subject_test_paper_title: Callable[..., str]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _text(value)


def _actor_account(user: CurrentUser) -> int | None:
    return int(user.account_id) if user.account_id else None


def _actor_staff(user: CurrentUser) -> int | None:
    return int(user.staff_id) if user.staff_id else None


def add_interview(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    dependencies: EvaluationDependencies,
) -> dict[str, Any]:
    if values.get("appointment_id"):
        raise RecruitmentError(
            "Scheduled interviews must be started before recording a result.",
            status_code=409,
            code="interview_start_required",
        )
    if _text(values.get("result")) not in INTERVIEW_RESULTS:
        raise RecruitmentError("Unknown interview result.")
    prepared = {**values, "interview_at": _iso(values.get("interview_at"))}
    prepared["interviewer_account_id"] = prepared.get(
        "interviewer_account_id"
    ) or _actor_account(user)
    return _add_record(
        user,
        candidate_id,
        prepared,
        "candidate.interview_recorded",
        repository.insert_interview,
        appointment_type="job_interview",
        timestamp_key="interview_at",
        dependencies=dependencies,
    )


def add_subject_test(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    dependencies: EvaluationDependencies,
) -> dict[str, Any]:
    if _text(values.get("result")) not in {"passed", "failed"}:
        raise RecruitmentError("Subject test status must be Passed or Failed.")
    prepared = {
        **values,
        "maximum_score": Decimal("100"),
        "test_at": _iso(values.get("test_at")),
    }
    score, maximum = (prepared.get("score"), prepared["maximum_score"])
    if (
        score is not None
        and maximum is not None
        and (Decimal(score) > Decimal(maximum))
    ):
        raise RecruitmentError("Subject test percentage cannot exceed 100.")
    prepared["evaluator_account_id"] = _actor_account(user)
    return _add_record(
        user,
        candidate_id,
        prepared,
        "candidate.subject_test_recorded",
        repository.insert_subject_test,
        dependencies=dependencies,
    )


def add_demo(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    dependencies: EvaluationDependencies,
) -> dict[str, Any]:
    if _text(values.get("result")) not in DEMO_RESULTS:
        raise RecruitmentError("Unknown demo lesson result.")
    prepared = {**values, "demo_at": _iso(values.get("demo_at"))}
    prepared["evaluator_account_id"] = _actor_account(user)
    return _add_record(
        user,
        candidate_id,
        prepared,
        "candidate.demo_lesson_recorded",
        repository.insert_demo,
        appointment_type="demo_lesson",
        timestamp_key="demo_at",
        dependencies=dependencies,
    )


def _add_record(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    event_type: str,
    inserter: Any,
    *,
    appointment_type: str = "",
    timestamp_key: str = "",
    dependencies: EvaluationDependencies,
) -> dict[str, Any]:
    now = _now()
    evaluation_type = (
        "interview"
        if event_type == "candidate.interview_recorded"
        else (
            "subject_test"
            if event_type == "candidate.subject_test_recorded"
            else "demo"
        )
    )
    with dependencies.connect() as conn:
        database_backed = hasattr(conn, "execute")
        candidate = (
            dependencies.lock_candidate(conn, int(candidate_id))
            if database_backed
            else repository.get_candidate_row(conn, int(candidate_id))
        )
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if evaluation_type == "subject_test":
            subject = _text(candidate.get("subject"))
            values.update(
                {
                    "subject_id": candidate.get("subject_id"),
                    "subject_label": subject,
                    "paper": dependencies.subject_test_paper_title(candidate),
                    "maximum_score": Decimal("100"),
                    "topic_scores": [],
                    "notes": "",
                }
            )
        appointment_id = int(values.get("appointment_id") or 0)
        appointment = None
        if appointment_id:
            appointment = repository.get_appointment_row(
                conn,
                candidate_id=int(candidate_id),
                appointment_id=appointment_id,
                for_update=True,
            )
            if not appointment:
                raise RecruitmentError("Appointment was not found.", status_code=404)
            if _text(appointment["appointment_type"]) != appointment_type:
                raise RecruitmentError(
                    "Appointment type does not match this evaluation.", status_code=409
                )
            required_status = (
                "in_progress" if appointment_type == "job_interview" else "scheduled"
            )
            if _text(appointment["status"]) != required_status:
                message = (
                    "Start this interview before recording its result."
                    if appointment_type == "job_interview"
                    else "This appointment is no longer scheduled."
                )
                raise RecruitmentError(message, status_code=409)
            if timestamp_key and (not _text(values.get(timestamp_key))):
                values[timestamp_key] = _text(
                    appointment.get("started_at") or appointment["starts_at"]
                )
            if (
                appointment_type == "job_interview"
                and appointment["responsible_account_id"]
            ):
                values["interviewer_account_id"] = int(
                    appointment["responsible_account_id"]
                )
            if appointment_type == "demo_lesson":
                if int(appointment["responsible_account_id"] or 0) != int(
                    _actor_account(user) or 0
                ):
                    raise RecruitmentError(
                        "Only the assigned demo evaluator can submit this result.",
                        status_code=403,
                    )
        record_id = inserter(
            conn,
            candidate_id=int(candidate_id),
            values=values,
            actor_account_id=_actor_account(user),
            now=now,
        )
        if appointment_id:
            completed = (
                repository.complete_interview_session(
                    conn,
                    appointment_id=appointment_id,
                    candidate_id=int(candidate_id),
                    expected_version=int(values.get("expected_version") or 0),
                    actor_account_id=_actor_account(user),
                    now=now,
                )
                if appointment_type == "job_interview"
                else repository.complete_appointment(
                    conn,
                    appointment_id=appointment_id,
                    candidate_id=int(candidate_id),
                    actor_account_id=_actor_account(user),
                    now=now,
                )
            )
            if not completed:
                raise RecruitmentError(
                    "This appointment changed elsewhere. Refresh and try again.",
                    status_code=409,
                )
            if appointment_type == "demo_lesson":
                recruitment_notifications.cancel_demo_reminders(conn, appointment_id)
                completed_appointment = repository.get_appointment_row(
                    conn, candidate_id=int(candidate_id), appointment_id=appointment_id
                )
                if completed_appointment:
                    recruitment_notifications.enqueue_demo_event(
                        conn,
                        appointment=completed_appointment,
                        event_type="demo_completed",
                        version_token=int(completed_appointment.get("version") or 1),
                    )
            dependencies.audit_appointment(
                conn,
                user=user,
                candidate_id=int(candidate_id),
                event_type="candidate.appointment_completed",
                appointment_id=appointment_id,
                detail={"record_id": record_id, "evaluation_type": appointment_type},
                now=now,
            )
        result = _text(values.get("result"))
        if database_backed:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type=event_type,
                detail={"record_id": record_id, "result": result},
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        stage_changed = False
        if (
            result == "failed"
            and candidate.get("status") is not None
            and (candidate.get("version") is not None)
        ):
            if _text(candidate["status"]) in {
                *PROTECTED_HIRE_STAGES,
                "rejected",
                "candidate_withdrew",
                "trash_bin",
            }:
                raise RecruitmentError(
                    "A finalized candidate cannot receive another rejecting evaluation.",
                    status_code=409,
                )
            rejection_reason, rejection_label = {
                "interview": ("failed_job_interview", "Failed job interview"),
                "subject_test": ("failed_subject_test", "Failed subject test"),
                "demo": ("failed_demo_lesson", "Failed demo lesson"),
            }[evaluation_type]
            evaluator_account_id = (
                int(
                    values.get("interviewer_account_id")
                    or values.get("evaluator_account_id")
                    or _actor_account(user)
                    or 0
                )
                or None
            )
            cancelled_after_failure = repository.cancel_scheduled_appointments(
                conn,
                candidate_id=int(candidate_id),
                reason=rejection_label,
                actor_account_id=evaluator_account_id,
                now=now,
            )
            dependencies.notify_cancelled_appointments(
                conn,
                candidate_id=int(candidate_id),
                appointment_ids=cancelled_after_failure,
            )
            if cancelled_after_failure:
                repository.insert_audit(
                    conn,
                    candidate_id=int(candidate_id),
                    event_type="candidate.appointments_cancelled_after_failed_evaluation",
                    detail={
                        "appointment_ids": cancelled_after_failure,
                        "evaluation_type": evaluation_type,
                        "record_id": record_id,
                    },
                    actor_account_id=evaluator_account_id,
                    actor_staff_id=(
                        _actor_staff(user)
                        if evaluator_account_id == _actor_account(user)
                        else None
                    ),
                    now=now,
                )
            revoked_approval_ids = repository.revoke_open_approvals(
                conn,
                candidate_id=int(candidate_id),
                comment=rejection_label,
                actor_account_id=evaluator_account_id,
                now=now,
            )
            if not repository.update_candidate_stage(
                conn,
                candidate_id=int(candidate_id),
                stage="rejected",
                expected_version=int(candidate["version"]),
                actor_account_id=evaluator_account_id,
                now=now,
                comment=rejection_label,
                transition_source="automatic",
            ):
                raise RecruitmentError(
                    "This candidate changed elsewhere. Refresh and try again.",
                    status_code=409,
                )
            stage_changed = True
            decision_id = repository.insert_final_decision(
                conn,
                candidate_id=int(candidate_id),
                values={
                    "decision": "rejected",
                    "rejection_reason": rejection_reason,
                    "reason_detail": f"{rejection_label}; evaluation #{record_id}.",
                    "origin_stage": _text(candidate["status"]),
                    "follow_up_at": "",
                    "approval_id": None,
                    "is_system_generated": True,
                    "source_evaluation_type": evaluation_type,
                    "source_evaluation_id": record_id,
                },
                actor_account_id=evaluator_account_id,
                actor_login=user.login,
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.final_decision_made",
                detail={
                    "decision_id": decision_id,
                    "decision": "rejected",
                    "rejection_reason": rejection_reason,
                    "origin_stage": _text(candidate["status"]),
                    "evaluation_type": evaluation_type,
                    "record_id": record_id,
                    "revoked_approval_ids": revoked_approval_ids,
                },
                actor_account_id=evaluator_account_id,
                actor_staff_id=(
                    _actor_staff(user)
                    if evaluator_account_id == _actor_account(user)
                    else None
                ),
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.stage_changed",
                detail={
                    "from": _text(candidate["status"]),
                    "to": "rejected",
                    "reason": rejection_label,
                },
                actor_account_id=evaluator_account_id,
                actor_staff_id=(
                    _actor_staff(user)
                    if evaluator_account_id == _actor_account(user)
                    else None
                ),
                now=now,
            )
        elif result == "failed":
            cancelled_after_failure = repository.cancel_scheduled_appointments(
                conn,
                candidate_id=int(candidate_id),
                reason="Candidate failed a recruitment evaluation.",
                actor_account_id=_actor_account(user),
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.appointments_cancelled_after_failed_evaluation",
                detail={
                    "appointment_ids": cancelled_after_failure,
                    "evaluation_type": evaluation_type,
                    "record_id": record_id,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type=event_type,
                detail={"record_id": record_id, "result": result},
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        elif (
            evaluation_type == "interview"
            and result == "passed"
            and (_text(candidate.get("status")) == "job_interview")
        ):
            if not repository.update_candidate_stage(
                conn,
                candidate_id=int(candidate_id),
                stage="test_and_demo",
                expected_version=int(candidate["version"]),
                actor_account_id=_actor_account(user),
                now=now,
                comment="Passed job interview",
                transition_source="automatic",
            ):
                raise RecruitmentError(
                    "This candidate changed elsewhere. Refresh and try again.",
                    status_code=409,
                )
            stage_changed = True
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.stage_changed",
                detail={
                    "from": "job_interview",
                    "to": "test_and_demo",
                    "reason": "Passed job interview",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        elif (
            evaluation_type == "demo"
            and result == "passed"
            and appointment_id
            and (_text(candidate.get("status")) == "test_and_demo")
        ):
            if not repository.update_candidate_stage(
                conn,
                candidate_id=int(candidate_id),
                stage="under_review",
                expected_version=int(candidate["version"]),
                actor_account_id=_actor_account(user),
                now=now,
                comment="Passed assigned demo lesson",
                transition_source="automatic",
            ):
                raise RecruitmentError(
                    "This candidate changed elsewhere. Refresh and try again.",
                    status_code=409,
                )
            stage_changed = True
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.stage_changed",
                detail={
                    "from": "test_and_demo",
                    "to": "under_review",
                    "reason": "Passed assigned demo lesson",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        if not database_backed and result != "failed":
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type=event_type,
                detail={"record_id": record_id, "result": result},
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        if evaluation_type == "demo" and appointment:
            evaluated_appointment = repository.get_appointment_row(
                conn, candidate_id=int(candidate_id), appointment_id=appointment_id
            )
            if evaluated_appointment:
                recruitment_notifications.enqueue_demo_event(
                    conn,
                    appointment=evaluated_appointment,
                    event_type="demo_evaluated",
                    version_token=f"{int(evaluated_appointment.get('version') or 1)}:{record_id}",
                )
        if not stage_changed:
            repository.touch_candidate(
                conn,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                now=now,
            )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    return dependencies.get_candidate(user, int(candidate_id))


def void_evaluation(
    user: CurrentUser,
    candidate_id: int,
    *,
    evaluation_type: str,
    attempt_id: int,
    reason: str,
    dependencies: EvaluationDependencies,
) -> dict[str, Any]:
    normalized_reason = _text(reason)
    if not normalized_reason:
        raise RecruitmentError("Explain why this evaluation is being voided.")
    table_by_type = {
        "interview": "teacher_candidate_interviews",
        "subject_test": "teacher_candidate_subject_tests",
        "demo": "teacher_candidate_demo_lessons",
    }
    table = table_by_type.get(_text(evaluation_type))
    if not table:
        raise RecruitmentError("Unknown evaluation type.")
    if (
        user.role in {"academic_director", "head_of_department"}
        and evaluation_type == "interview"
    ):
        raise RecruitmentError(
            "Academic evaluators cannot void HR interview results.", status_code=403
        )
    if user.role not in {
        "hr_manager",
        "ceo",
        "academic_director",
        "head_of_department",
    }:
        raise RecruitmentError(
            "You cannot void recruitment evaluations.", status_code=403
        )
    now = _now()
    with dependencies.connect() as conn:
        database_backed = hasattr(conn, "execute")
        candidate = (
            dependencies.lock_candidate(conn, int(candidate_id))
            if database_backed
            else repository.get_candidate_row(conn, int(candidate_id))
        )
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        evaluation = (
            repository.get_evaluation_row(
                conn,
                table=table,
                candidate_id=int(candidate_id),
                attempt_id=int(attempt_id),
                for_update=True,
            )
            if database_backed
            else {"id": attempt_id, "result": "", "voided_at": None}
        )
        if not evaluation or evaluation["voided_at"]:
            raise RecruitmentError(
                "Evaluation was not found or was already voided.", status_code=409
            )
        system_decision = (
            repository.get_system_decision_for_evaluation(
                conn,
                candidate_id=int(candidate_id),
                evaluation_type=evaluation_type,
                attempt_id=int(attempt_id),
                for_update=True,
            )
            if database_backed
            else None
        )
        if system_decision:
            latest_decision = repository.latest_active_final_decision(
                conn, int(candidate_id), for_update=True
            )
            if (
                _text(candidate["status"]) != "rejected"
                or not latest_decision
                or int(latest_decision["id"]) != int(system_decision["id"])
            ):
                raise RecruitmentError(
                    "This rejection has later workflow changes and requires manual review.",
                    status_code=409,
                )
        voided = repository.void_evaluation(
            conn,
            table=table,
            candidate_id=int(candidate_id),
            attempt_id=int(attempt_id),
            actor_account_id=_actor_account(user),
            reason=normalized_reason,
            now=now,
        )
        if not voided:
            raise RecruitmentError(
                "Evaluation was not found or was already voided.", status_code=409
            )
        restored_stage = ""
        if system_decision:
            restored_stage = _text(system_decision["origin_stage"]) or "new_candidate"
            if not repository.void_system_final_decision(
                conn,
                decision_id=int(system_decision["id"]),
                actor_account_id=_actor_account(user),
                reason=normalized_reason,
                now=now,
            ):
                raise RecruitmentError(
                    "The automatic rejection changed elsewhere.", status_code=409
                )
            if not repository.update_candidate_stage(
                conn,
                candidate_id=int(candidate_id),
                stage=restored_stage,
                expected_version=int(candidate["version"]),
                actor_account_id=_actor_account(user),
                now=now,
                comment="Failed evaluation voided",
                transition_source="restored",
            ):
                raise RecruitmentError(
                    "This candidate changed elsewhere. Refresh and try again.",
                    status_code=409,
                )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.system_rejection_voided",
                detail={
                    "decision_id": int(system_decision["id"]),
                    "evaluation_type": evaluation_type,
                    "attempt_id": int(attempt_id),
                    "restored_stage": restored_stage,
                    "reason": normalized_reason,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.stage_changed",
                detail={
                    "from": "rejected",
                    "to": restored_stage,
                    "reason": "Failed evaluation voided",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        else:
            repository.touch_candidate(
                conn,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                now=now,
            )
        void_detail = {
            "evaluation_type": evaluation_type,
            "attempt_id": int(attempt_id),
            "reason": normalized_reason,
        }
        if restored_stage:
            void_detail["restored_stage"] = restored_stage
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.evaluation_voided",
            detail=void_detail,
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        dependencies.sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    return dependencies.get_candidate(user, int(candidate_id))


__all__ = [
    "EvaluationDependencies",
    "_add_record",
    "add_demo",
    "add_interview",
    "add_subject_test",
    "void_evaluation",
]
