"""Recruitment hiring-decision use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.constants import PROTECTED_HIRE_STAGES
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import text as _text
from backend.modules.teacher_academy.account_provisioning import (
    AcademyAccountProvisioningError,
)


@dataclass(frozen=True)
class DecisionDependencies:
    connect: Callable[..., Any]
    lock_candidate: Callable[..., Any]
    get_candidate: Callable[..., dict[str, Any]]
    sync_next_actions: Callable[..., None]
    notify_cancelled_appointments: Callable[..., None]
    provision_academy_account: Callable[..., Any]


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


def request_approval(
    user: CurrentUser,
    candidate_id: int,
    *,
    requested_outcome: str,
    request_note: str,
    dependencies: DecisionDependencies,
) -> dict[str, Any]:
    if user.role not in {"hr_manager", "ceo"}:
        raise RecruitmentError(
            "Only HR can request Active Teacher approval.", status_code=403
        )
    outcome = _text(requested_outcome)
    if outcome != "active_teacher":
        raise RecruitmentError(
            "Academic Director approval is only used for Active Teachers."
        )
    now = _now()
    with dependencies.connect() as conn:
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        academy_promotion = (
            _text(candidate["status"]) == "teacher_academy"
            and int(candidate.get("academy_teacher_id") or 0) > 0
        )
        if not academy_promotion:
            evaluation_state = repository.candidate_evaluation_state(
                conn, candidate_id=int(candidate_id)
            )
            if _text(candidate["status"]) != "under_review" or not all(
                bool(evaluation_state[key])
                for key in (
                    "interview_passed",
                    "demo_passed",
                    "subject_test_passed",
                )
            ):
                raise RecruitmentError(
                    "All recruitment evaluations must pass before requesting Active Teacher approval.",
                    status_code=409,
                )
        approval_id = repository.insert_approval_request(
            conn,
            candidate_id=int(candidate_id),
            outcome=outcome,
            note=_text(request_note),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.hire_approval_requested",
            detail={"approval_id": approval_id, "requested_outcome": outcome},
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


def review_approval(
    user: CurrentUser,
    candidate_id: int,
    approval_id: int,
    *,
    status: str,
    review_comment: str,
    dependencies: DecisionDependencies,
) -> dict[str, Any]:
    if user.role != "academic_director":
        raise RecruitmentError(
            "Only the Academic Director can review hiring approval requests.",
            status_code=403,
        )
    normalized_status = _text(status)
    normalized_comment = _text(review_comment)
    if normalized_status not in {"approved", "returned"}:
        raise RecruitmentError("Unknown approval review status.")
    if normalized_status == "returned" and (not normalized_comment):
        raise RecruitmentError(
            "A comment is required when returning an approval request."
        )
    now = _now()
    with dependencies.connect() as conn:
        approval = repository.get_approval_row(
            conn,
            candidate_id=int(candidate_id),
            approval_id=int(approval_id),
            for_update=True,
        )
        if not approval:
            raise RecruitmentError(
                "Approval request was not found or does not belong to this candidate.",
                status_code=409,
            )
        if _text(approval["requested_outcome"]) != "active_teacher":
            raise RecruitmentError(
                "Teacher Academy placement is finalized directly by HR.",
                status_code=409,
            )
        if _text(approval["status"]) != "requested":
            raise RecruitmentError(
                "Approval request is no longer pending.",
                status_code=409,
            )
        if not repository.review_approval(
            conn,
            candidate_id=int(candidate_id),
            approval_id=int(approval_id),
            status=normalized_status,
            comment=normalized_comment,
            actor_account_id=_actor_account(user),
            now=now,
        ):
            raise RecruitmentError(
                "Approval request was not found or is no longer pending.",
                status_code=409,
            )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=f"candidate.hire_approval_{normalized_status}",
            detail={"approval_id": int(approval_id), "comment": normalized_comment},
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


def make_final_decision(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    dependencies: DecisionDependencies,
) -> dict[str, Any]:
    decision = _text(values.get("decision"))
    allowed = {*PROTECTED_HIRE_STAGES, "rejected", "candidate_withdrew"}
    if decision not in allowed:
        raise RecruitmentError("Unknown final decision.")
    if decision == "active_teacher" and user.role != "ceo":
        raise RecruitmentError(
            "Only CEO can directly finalize this hiring outcome.", status_code=403
        )
    if decision == "teacher_academy" and user.role != "hr_manager":
        raise RecruitmentError(
            "Only HR can add a candidate to Teacher Academy.", status_code=403
        )
    if decision == "rejected" and user.role not in {
        "hr_manager",
        "academic_director",
        "ceo",
    }:
        raise RecruitmentError("You cannot reject this candidate.", status_code=403)
    if decision == "candidate_withdrew" and user.role not in {"hr_manager", "ceo"}:
        raise RecruitmentError("You cannot record this outcome.", status_code=403)
    rejection_reason = _text(values.get("rejection_reason"))
    reason_detail = _text(values.get("reason_detail"))
    if decision == "rejected":
        if not rejection_reason:
            raise RecruitmentError("Select a rejection reason.")
        if rejection_reason == "other" and (not reason_detail):
            raise RecruitmentError("Explain the other rejection reason.")
    if decision == "candidate_withdrew" and (not reason_detail):
        raise RecruitmentError("Add the candidate withdrawal reason.")
    now = _now()
    approval_id = int(values.get("approval_id") or 0)
    with dependencies.connect() as conn:
        if decision == "rejected" and (
            not repository.recruitment_setting_value_exists(
                conn, category="rejection_reason", value=rejection_reason
            )
        ):
            raise RecruitmentError("Select an active rejection reason.")
        candidate = dependencies.lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if decision in {"rejected", "candidate_withdrew"} and (
            _text(candidate["status"]) in PROTECTED_HIRE_STAGES
            or int(candidate["academy_teacher_id"] or 0)
            or int(candidate["active_teacher_id"] or 0)
        ):
            raise RecruitmentError(
                "A finalized teacher intake cannot receive this outcome.",
                status_code=409,
            )
        if _text(candidate["status"]) == decision:
            conn.rollback()
            return dependencies.get_candidate(user, int(candidate_id))
        if decision in PROTECTED_HIRE_STAGES:
            academy_promotion = (
                decision == "active_teacher"
                and _text(candidate["status"]) == "teacher_academy"
                and int(candidate.get("academy_teacher_id") or 0) > 0
            )
            if not academy_promotion:
                evaluation_state = repository.candidate_evaluation_state(
                    conn, candidate_id=int(candidate_id)
                )
                if _text(candidate["status"]) != "under_review" or not all(
                    bool(evaluation_state[key])
                    for key in (
                        "interview_passed",
                        "demo_passed",
                        "subject_test_passed",
                    )
                ):
                    raise RecruitmentError(
                        "All recruitment evaluations must pass before final placement.",
                        status_code=409,
                    )
            linked_id = (
                int(candidate["academy_teacher_id"] or 0)
                if decision == "teacher_academy"
                else int(candidate["active_teacher_id"] or 0)
            )
            if _text(candidate["status"]) == decision and linked_id:
                conn.rollback()
                return dependencies.get_candidate(user, int(candidate_id))
            if decision == "active_teacher" and not approval_id:
                raise RecruitmentError("Academic Director approval is required.")
            if decision == "active_teacher":
                approval = repository.get_approval_row(
                    conn,
                    candidate_id=int(candidate_id),
                    approval_id=approval_id,
                    for_update=True,
                )
                if (
                    not approval
                    or approval["status"] != "approved"
                    or approval["requested_outcome"] != decision
                ):
                    raise RecruitmentError(
                        "Use an approved Academic Director request for this outcome.",
                        status_code=409,
                    )
        if decision == "teacher_academy":
            academy_teacher_id = repository.ensure_academy_intake(
                conn, candidate=candidate, actor_login=user.login, now=now
            )
            try:
                dependencies.provision_academy_account(
                    conn,
                    academy_teacher_id=academy_teacher_id,
                    actor_account_id=_actor_account(user),
                    actor_login=user.login,
                    now=now,
                )
            except AcademyAccountProvisioningError as exc:
                raise RecruitmentError(
                    str(exc),
                    status_code=409,
                    code="academy_account_provisioning_failed",
                ) from exc
        elif decision == "active_teacher":
            repository.ensure_active_teacher_intake(conn, candidate=candidate, now=now)
        revoked_approval_ids: list[int] = []
        if decision in {"rejected", "candidate_withdrew"}:
            revoked_approval_ids = repository.revoke_open_approvals(
                conn,
                candidate_id=int(candidate_id),
                comment=reason_detail or rejection_reason,
                actor_account_id=_actor_account(user),
                now=now,
            )
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=decision,
            expected_version=int(candidate["version"]),
            actor_account_id=_actor_account(user),
            now=now,
            comment=reason_detail
            or rejection_reason
            or f"Finalized as {decision.replace('_', ' ')}.",
            transition_source="manual",
        )
        if not updated:
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        cancelled_appointment_ids: list[int] = []
        if decision in {"rejected", "candidate_withdrew"}:
            cancelled_appointment_ids = repository.cancel_scheduled_appointments(
                conn,
                candidate_id=int(candidate_id),
                reason=f"Candidate moved to {decision.replace('_', ' ')}.",
                actor_account_id=_actor_account(user),
                now=now,
            )
            dependencies.notify_cancelled_appointments(
                conn,
                candidate_id=int(candidate_id),
                appointment_ids=cancelled_appointment_ids,
            )
        normalized_values = {
            **values,
            "decision": decision,
            "rejection_reason": rejection_reason,
            "reason_detail": reason_detail,
            "origin_stage": _text(candidate["status"]),
            "follow_up_at": _iso(values.get("follow_up_at")),
            "approval_id": approval_id or None,
        }
        decision_id = repository.insert_final_decision(
            conn,
            candidate_id=int(candidate_id),
            values=normalized_values,
            actor_account_id=_actor_account(user),
            actor_login=user.login,
            now=now,
        )
        if approval_id:
            repository.consume_approval(conn, approval_id=approval_id, now=now)
        if revoked_approval_ids:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.hire_approvals_revoked",
                detail={
                    "approval_ids": revoked_approval_ids,
                    "reason": reason_detail or rejection_reason,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        if cancelled_appointment_ids:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.appointments_cancelled",
                detail={
                    "appointment_ids": cancelled_appointment_ids,
                    "reason": f"Candidate moved to {decision.replace('_', ' ')}.",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.final_decision_made",
            detail={
                "decision_id": decision_id,
                "decision": decision,
                "rejection_reason": rejection_reason,
                "reason_detail": reason_detail,
                "origin_stage": _text(candidate["status"]),
                "approval_id": approval_id or None,
            },
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
    "DecisionDependencies",
    "make_final_decision",
    "request_approval",
    "review_approval",
]
