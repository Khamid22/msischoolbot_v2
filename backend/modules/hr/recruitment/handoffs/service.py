"""Recruitment handoff and lifecycle-removal use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.constants import PROTECTED_HIRE_STAGES
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import text as _text


@dataclass(frozen=True)
class HandoffDependencies:
    connect: Callable[..., Any]
    lock_candidate: Callable[..., Any]
    sync_next_actions: Callable[..., None]
    notify_cancelled_appointments: Callable[..., None]
    remove_academy_teacher: Callable[..., dict[str, Any]]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actor_account(user: CurrentUser) -> int | None:
    return int(user.account_id) if user.account_id else None


def _actor_staff(user: CurrentUser) -> int | None:
    return int(user.staff_id) if user.staff_id else None


def remove_academy_teacher(
    user: CurrentUser,
    academy_teacher_id: int,
    values: dict[str, Any],
    *,
    dependencies: HandoffDependencies,
) -> dict[str, Any]:
    if user.role not in {"hr_manager", "academic_director"}:
        raise RecruitmentError(
            "Only the HR Manager or Academic Director can remove a Teacher Academy teacher.",
            status_code=403,
        )
    rejection_reason = _text(values.get("rejection_reason"))
    reason_detail = _text(values.get("reason_detail"))
    if not rejection_reason:
        raise RecruitmentError("Select a rejection reason.")
    if rejection_reason == "other" and (not reason_detail):
        raise RecruitmentError("Explain the other rejection reason.")
    now = _now()
    identity_deleted = False
    candidate_id = 0
    with dependencies.connect() as conn:
        if not repository.recruitment_setting_value_exists(
            conn, category="rejection_reason", value=rejection_reason
        ):
            raise RecruitmentError("Select an active rejection reason.")
        academy = repository.lock_academy_removal_row(conn, int(academy_teacher_id))
        if not academy:
            raise RecruitmentError(
                "Teacher Academy record was not found.", status_code=404
            )
        candidate_id = int(academy["recruitment_candidate_id"] or 0)
        if not candidate_id:
            raise RecruitmentError(
                "Link this Academy record to a lifecycle profile before removing it.",
                status_code=409,
            )
        candidate = dependencies.lock_candidate(conn, candidate_id)
        if not candidate:
            raise RecruitmentError(
                "Linked lifecycle profile was not found.", status_code=409
            )
        latest_decision = repository.latest_active_final_decision(
            conn, candidate_id, for_update=True
        )
        if (
            _text(candidate["status"]) == "rejected"
            and _text(academy["academy_status"]) == "rejected"
            and latest_decision
            and (_text(latest_decision["decision"]) == "rejected")
        ):
            conn.rollback()
            return {
                "candidate": {"id": candidate_id, "status": "rejected"},
                "identity_deleted": False,
                "already_removed": True,
            }
        if int(academy["promoted_teacher_id"] or 0) or int(
            candidate["active_teacher_id"] or 0
        ):
            raise RecruitmentError(
                "Active or promoted teachers cannot be removed through Teacher Academy.",
                status_code=409,
            )
        if _text(candidate["status"]) != "teacher_academy":
            raise RecruitmentError(
                "Only a current Teacher Academy profile can be removed.",
                status_code=409,
            )
        if _text(academy["academy_status"]) == "rejected":
            raise RecruitmentError(
                "The Academy record is already removed but its profile is inconsistent.",
                status_code=409,
            )
        staff_id = int(academy["staff_id"] or 0)
        teacher_id = int(academy["teacher_id"] or 0)
        generated_identity = bool(
            staff_id
            and teacher_id
            and (_text(academy["staff_role"]) == "teacher")
            and (_text(academy["teacher_status"]) == "academy")
            and (not int(academy["promoted_teacher_id"] or 0))
        )
        if staff_id and (not generated_identity):
            raise RecruitmentError(
                "This Academy record uses a shared identity and requires manual review.",
                status_code=409,
            )
        if generated_identity:
            locked_staff, locked_teacher = repository.lock_academy_identity_rows(
                conn, staff_id=staff_id, teacher_id=teacher_id
            )
            if (
                not locked_staff
                or int(locked_staff["teacher_id"] or 0) != teacher_id
                or _text(locked_staff["role"]) != "teacher"
                or (not locked_teacher)
                or (_text(locked_teacher["status"]) != "academy")
                or (
                    int(locked_teacher["recruitment_candidate_id"] or 0)
                    and int(locked_teacher["recruitment_candidate_id"]) != candidate_id
                )
            ):
                raise RecruitmentError(
                    "The Academy identity changed or is shared. Refresh and request manual review.",
                    status_code=409,
                )
        account_ids = (
            repository.list_teacher_account_ids_for_staff(conn, staff_id)
            if generated_identity
            else []
        )
        revoked_approval_ids = repository.revoke_open_approvals(
            conn,
            candidate_id=candidate_id,
            comment=reason_detail or rejection_reason,
            actor_account_id=_actor_account(user),
            now=now,
        )
        cancelled_appointment_ids = repository.cancel_scheduled_appointments(
            conn,
            candidate_id=candidate_id,
            reason="Teacher removed from Teacher Academy.",
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.notify_cancelled_appointments(
            conn, candidate_id=candidate_id, appointment_ids=cancelled_appointment_ids
        )
        cancelled_task_ids = repository.cancel_pending_candidate_tasks(
            conn,
            candidate_id=candidate_id,
            actor_account_id=_actor_account(user),
            now=now,
        )
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=candidate_id,
            stage="rejected",
            expected_version=int(candidate["version"]),
            actor_account_id=_actor_account(user),
            now=now,
            comment=reason_detail or rejection_reason,
            transition_source="manual",
        )
        if not updated:
            raise RecruitmentError(
                "This teacher changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        if not repository.mark_academy_removed(
            conn, academy_teacher_id=int(academy_teacher_id), now=now
        ):
            raise RecruitmentError(
                "The Academy record changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        decision_id = repository.insert_final_decision(
            conn,
            candidate_id=candidate_id,
            values={
                "decision": "rejected",
                "rejection_reason": rejection_reason,
                "reason_detail": reason_detail,
                "origin_stage": "teacher_academy",
                "follow_up_at": "",
                "approval_id": None,
            },
            actor_account_id=_actor_account(user),
            actor_login=user.login,
            now=now,
        )
        if generated_identity:
            repository.delete_generated_academy_identity(
                conn, staff_id=staff_id, teacher_id=teacher_id, account_ids=account_ids
            )
            identity_deleted = True
        if revoked_approval_ids:
            repository.insert_audit(
                conn,
                candidate_id=candidate_id,
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
                candidate_id=candidate_id,
                event_type="candidate.appointments_cancelled",
                detail={
                    "appointment_ids": cancelled_appointment_ids,
                    "reason": "Teacher removed from Teacher Academy.",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        if cancelled_task_ids:
            repository.insert_audit(
                conn,
                candidate_id=candidate_id,
                event_type="candidate.tasks_cancelled",
                detail={
                    "task_ids": cancelled_task_ids,
                    "reason": "Teacher removed from Teacher Academy.",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.stage_changed",
            detail={
                "from": "teacher_academy",
                "to": "rejected",
                "reason": reason_detail or rejection_reason,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.academy_removed",
            detail={
                "academy_teacher_id": int(academy_teacher_id),
                "decision_id": decision_id,
                "rejection_reason": rejection_reason,
                "reason_detail": reason_detail,
                "generated_identity_deleted": identity_deleted,
                "deleted_account_ids": account_ids,
                "lessons_and_assessments_preserved": True,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.final_decision_made",
            detail={
                "decision_id": decision_id,
                "decision": "rejected",
                "rejection_reason": rejection_reason,
                "reason_detail": reason_detail,
                "origin_stage": "teacher_academy",
                "approval_id": None,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        dependencies.sync_next_actions(
            conn,
            candidate_id=candidate_id,
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    return {
        "candidate": {"id": candidate_id, "status": "rejected"},
        "identity_deleted": identity_deleted,
        "already_removed": False,
    }


def close_teacher_handoff(
    user: CurrentUser,
    *,
    kind: str,
    record_id: int,
    values: dict[str, Any],
    dependencies: HandoffDependencies,
) -> dict[str, Any]:
    normalized_kind = _text(kind)
    action = _text(values.get("action"))
    if normalized_kind not in PROTECTED_HIRE_STAGES:
        raise RecruitmentError("Unknown teacher roster type.")
    if action not in {"trash_bin", "rejected"}:
        raise RecruitmentError("Unknown teacher roster action.")
    allowed = user.role == "hr_manager" or (
        user.role == "academic_director" and normalized_kind == "teacher_academy"
    )
    if not allowed:
        raise RecruitmentError(
            "You cannot delete or reject this teacher.", status_code=403
        )
    rejection_reason = _text(values.get("rejection_reason"))
    reason_detail = _text(values.get("reason_detail"))
    if action == "rejected":
        if not rejection_reason:
            raise RecruitmentError("Select a rejection reason.")
        if rejection_reason == "other" and (not reason_detail):
            raise RecruitmentError("Explain the other rejection reason.")
        if normalized_kind == "teacher_academy":
            result = dependencies.remove_academy_teacher(
                user,
                int(record_id),
                {"rejection_reason": rejection_reason, "reason_detail": reason_detail},
            )
            return {
                **result,
                "action": action,
                "kind": normalized_kind,
                "record_id": int(record_id),
            }
    now = _now()
    candidate_id = 0
    with dependencies.connect() as conn:
        if action == "rejected" and (
            not repository.recruitment_setting_value_exists(
                conn, category="rejection_reason", value=rejection_reason
            )
        ):
            raise RecruitmentError("Select an active rejection reason.")
        handoff = repository.lock_teacher_handoff_row(
            conn, kind=normalized_kind, record_id=int(record_id)
        )
        if not handoff:
            raise RecruitmentError("Teacher record was not found.", status_code=404)
        candidate_id = int(handoff["recruitment_candidate_id"] or 0)
        if not candidate_id:
            raise RecruitmentError(
                "Link this teacher record to a lifecycle profile first.",
                status_code=409,
            )
        candidate = dependencies.lock_candidate(conn, candidate_id)
        if not candidate:
            raise RecruitmentError(
                "Linked lifecycle profile was not found.", status_code=409
            )
        candidate_stage = _text(candidate["status"])
        roster_status = _text(handoff["roster_status"])
        if candidate_stage == action and roster_status == action:
            conn.rollback()
            return {
                "candidate": {"id": candidate_id, "status": action},
                "action": action,
                "kind": normalized_kind,
                "record_id": int(record_id),
                "already_closed": True,
            }
        if candidate_stage != normalized_kind:
            raise RecruitmentError(
                "The linked profile changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        if normalized_kind == "teacher_academy" and int(
            handoff["promoted_teacher_id"] or 0
        ):
            raise RecruitmentError(
                "A promoted Academy teacher cannot be changed here.", status_code=409
            )
        reason = (
            reason_detail or rejection_reason
            if action == "rejected"
            else "Moved to Trash Bin from the teacher roster."
        )
        revoked_approval_ids = repository.revoke_open_approvals(
            conn,
            candidate_id=candidate_id,
            comment=reason,
            actor_account_id=_actor_account(user),
            now=now,
        )
        cancelled_appointment_ids = repository.cancel_scheduled_appointments(
            conn,
            candidate_id=candidate_id,
            reason=reason,
            actor_account_id=_actor_account(user),
            now=now,
        )
        dependencies.notify_cancelled_appointments(
            conn, candidate_id=candidate_id, appointment_ids=cancelled_appointment_ids
        )
        cancelled_task_ids = repository.cancel_pending_candidate_tasks(
            conn,
            candidate_id=candidate_id,
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not repository.update_candidate_stage(
            conn,
            candidate_id=candidate_id,
            stage=action,
            expected_version=int(candidate["version"]),
            actor_account_id=_actor_account(user),
            now=now,
            comment=reason,
            transition_source="manual",
        ):
            raise RecruitmentError(
                "This teacher changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        if not repository.mark_teacher_handoff_closed(
            conn, kind=normalized_kind, record_id=int(record_id), action=action, now=now
        ):
            raise RecruitmentError(
                "The teacher roster changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        repository.set_teacher_identity_enabled(
            conn,
            staff_id=int(handoff["staff_id"] or 0),
            teacher_id=int(handoff["teacher_id"] or 0),
            enabled=False,
            now=now,
        )
        decision_id = None
        if action == "rejected":
            decision_id = repository.insert_final_decision(
                conn,
                candidate_id=candidate_id,
                values={
                    "decision": "rejected",
                    "rejection_reason": rejection_reason,
                    "reason_detail": reason_detail,
                    "origin_stage": normalized_kind,
                    "follow_up_at": "",
                    "approval_id": None,
                },
                actor_account_id=_actor_account(user),
                actor_login=user.login,
                now=now,
            )
        for event_type, identifiers in (
            ("candidate.hire_approvals_revoked", revoked_approval_ids),
            ("candidate.appointments_cancelled", cancelled_appointment_ids),
            ("candidate.tasks_cancelled", cancelled_task_ids),
        ):
            if identifiers:
                repository.insert_audit(
                    conn,
                    candidate_id=candidate_id,
                    event_type=event_type,
                    detail={"ids": identifiers, "reason": reason},
                    actor_account_id=_actor_account(user),
                    actor_staff_id=_actor_staff(user),
                    now=now,
                )
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.stage_changed",
            detail={"from": normalized_kind, "to": action, "reason": reason},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.teacher_roster_closed",
            detail={
                "kind": normalized_kind,
                "record_id": int(record_id),
                "action": action,
                "rejection_reason": rejection_reason,
                "reason_detail": reason_detail,
                "identity_disabled": bool(
                    int(handoff["staff_id"] or 0) or int(handoff["teacher_id"] or 0)
                ),
                "history_preserved": True,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        if decision_id:
            repository.insert_audit(
                conn,
                candidate_id=candidate_id,
                event_type="candidate.final_decision_made",
                detail={
                    "decision_id": decision_id,
                    "decision": "rejected",
                    "rejection_reason": rejection_reason,
                    "reason_detail": reason_detail,
                    "origin_stage": normalized_kind,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        dependencies.sync_next_actions(
            conn,
            candidate_id=candidate_id,
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    return {
        "candidate": {"id": candidate_id, "status": action},
        "action": action,
        "kind": normalized_kind,
        "record_id": int(record_id),
        "already_closed": False,
    }


__all__ = [
    "HandoffDependencies",
    "close_teacher_handoff",
    "remove_academy_teacher",
]
