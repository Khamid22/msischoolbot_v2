"""Recruitment candidate lifecycle and read use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import ceil
from typing import Any, Callable
from zoneinfo import ZoneInfo

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.candidates.read_service import (
    get_candidate,
    list_candidates,
    list_decision_queue,
    list_pipeline,
    list_teacher_handoffs,
)
from backend.modules.hr.recruitment.candidates.repository import (
    purge_closed_academy_handoff,
)
from backend.modules.hr.recruitment.constants import (
    ALL_STAGES,
    ALTERNATIVE_STAGES,
    DOCUMENT_TYPES,
    PRIMARY_STAGES,
    PROTECTED_HIRE_STAGES,
)
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import (
    appointment_payload as _appointment_payload,
    candidate_progress as _candidate_progress,
    candidate_summary as _candidate_summary,
    derived_evaluation_states as _derived_evaluation_states,
    normalize_attempt_rows as _normalize_attempt_rows,
    permissions as _permissions,
    row_dict as _row_dict,
    task_payload as _task_payload,
    text as _text,
)
from backend.platform.storage.r2 import delete_private_candidate_document


SCHOOL_TIME_ZONE = ZoneInfo("Asia/Tashkent")


@dataclass(frozen=True)
class CandidateDependencies:
    connect: Callable[..., Any]
    get_candidate: Callable[..., dict[str, Any]]
    sync_next_actions: Callable[..., None]
    notify_cancelled_appointments: Callable[..., None]
    academic_visible_id: Callable[..., int | None]
    visible_subject_ids: Callable[..., set[int] | None]
    setting_value: Callable[..., str]


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


_RESTORABLE_PIPELINE_STAGES = {
    "new_candidate",
    "responded",
    "job_interview",
    "test_and_demo",
    "under_review",
}


_CLOSED_CANDIDATE_STAGES = {"trash_bin", "rejected", "candidate_withdrew"}
_CLOSED_ACADEMY_STATUSES = {"rejected", "removed", "trash_bin"}
_CLOSED_ACTIVE_TEACHER_STATUSES = {"rejected", "removed", "trash_bin"}


_CANDIDATE_OPTION_FIELDS = {
    "source_option_id": "source",
    "subsource_option_id": "subsource",
    "position_option_id": "position",
    "english_level_option_id": "english_level",
    "schedule_option_id": "schedule",
    "availability_option_id": "availability",
    "expected_salary_option_id": "expected_salary",
    "teaching_experience_option_id": "teaching_experience",
}


def restore_closed_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    expected_version: int,
    dependencies: CandidateDependencies,
) -> dict[str, Any]:
    now = _now()
    with dependencies.connect() as conn:
        candidate = repository.get_candidate_row(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        from_stage = _text(candidate["status"])
        if from_stage not in _CLOSED_CANDIDATE_STAGES:
            raise RecruitmentError(
                "Only closed candidates can be recovered.", status_code=409
            )
        restore_stage = _text(candidate["restore_stage"])
        restoring_teacher_handoff = (
            from_stage == "trash_bin" and restore_stage in PROTECTED_HIRE_STAGES
        )
        if restore_stage not in _RESTORABLE_PIPELINE_STAGES and (
            not restoring_teacher_handoff
        ):
            restore_stage = (
                "under_review"
                if restore_stage in PROTECTED_HIRE_STAGES
                else "new_candidate"
            )
        if restoring_teacher_handoff and (
            not repository.restore_teacher_handoff(
                conn, candidate_id=int(candidate_id), kind=restore_stage, now=now
            )
        ):
            raise RecruitmentError(
                "The linked teacher record changed or is no longer recoverable.",
                status_code=409,
            )
        voided_decision_id = None
        if from_stage in {"rejected", "candidate_withdrew"}:
            voided_decision_id = repository.void_latest_closed_decision(
                conn,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                reason="Candidate recovered by HR Manager.",
                now=now,
            )
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=restore_stage,
            expected_version=int(expected_version),
            actor_account_id=_actor_account(user),
            now=now,
            comment=f"Recovered from {from_stage.replace('_', ' ')}.",
            transition_source="restored",
        )
        if not updated:
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.recovered",
            detail={
                "from": from_stage,
                "to": restore_stage,
                "voided_decision_id": voided_decision_id,
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


def _validate_permanent_delete_row(candidate: Any) -> None:
    if not candidate:
        raise RecruitmentError("Candidate was not found.", status_code=404)
    row = _row_dict(candidate)
    if _text(row.get("status")) not in _CLOSED_CANDIDATE_STAGES:
        raise RecruitmentError(
            "Only Trash Bin, Rejected, or Withdrawn candidates can be permanently deleted.",
            status_code=409,
        )
    academy_teacher_id = int(row.get("academy_teacher_id") or 0)
    academy_status = _text(row.get("academy_status"))
    academy_promoted_teacher_id = int(row.get("academy_promoted_teacher_id") or 0)
    if academy_teacher_id and (
        academy_status not in _CLOSED_ACADEMY_STATUSES
        or academy_promoted_teacher_id
    ):
        raise RecruitmentError(
            "This profile is linked to an open Teacher Academy record and cannot be permanently deleted.",
            status_code=409,
        )
    active_teacher_id = int(row.get("active_teacher_id") or 0)
    active_teacher_status = _text(row.get("active_teacher_status"))
    is_closed_academy_identity = bool(
        active_teacher_id
        and active_teacher_status == "academy"
        and academy_teacher_id
        and academy_status in _CLOSED_ACADEMY_STATUSES
        and not academy_promoted_teacher_id
    )
    if active_teacher_id and (
        active_teacher_status not in _CLOSED_ACTIVE_TEACHER_STATUSES
        and not is_closed_academy_identity
    ):
        raise RecruitmentError(
            "This profile is linked to an open Active Teacher record and cannot be permanently deleted.",
            status_code=409,
        )


def permanently_delete_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    expected_version: int,
    confirmation: str,
    dependencies: CandidateDependencies,
) -> dict[str, Any]:
    if _text(confirmation) != "PERMANENTLY DELETE":
        raise RecruitmentError("Permanent deletion was not confirmed.")
    object_keys: list[str] = []
    deleted_name = ""
    with dependencies.connect() as conn:
        candidate = repository.lock_candidate_decision_row(conn, int(candidate_id))
        _validate_permanent_delete_row(candidate)
        if int(candidate["version"] or 0) != int(expected_version):
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        deleted_name = _text(candidate["full_name"])
        object_keys = [
            _text(document["object_key"])
            for document in repository.list_document_rows(conn, int(candidate_id))
            if _text(document["object_key"])
        ]
        if int(candidate["academy_teacher_id"] or 0) and (
            not purge_closed_academy_handoff(
                conn, candidate_id=int(candidate_id)
            )
        ):
            raise RecruitmentError(
                "The linked Teacher Academy record changed. Refresh and try again.",
                status_code=409,
            )
        if not repository.delete_closed_candidate(
            conn, candidate_id=int(candidate_id), expected_version=int(expected_version)
        ):
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        conn.commit()
    for object_key in dict.fromkeys(object_keys):
        delete_private_candidate_document(object_key)
    return {"deleted_candidate_id": int(candidate_id), "deleted_name": deleted_name}


def empty_trash_bin(
    user: CurrentUser, *, confirmation: str, dependencies: CandidateDependencies
) -> dict[str, Any]:
    if _text(confirmation) != "EMPTY TRASH BIN":
        raise RecruitmentError("Empty Trash Bin was not confirmed.")
    object_keys: list[str] = []
    with dependencies.connect() as conn:
        candidates = repository.list_trash_candidates_for_purge(conn)
        for candidate in candidates:
            _validate_permanent_delete_row(candidate)
            object_keys.extend(
                (
                    _text(document["object_key"])
                    for document in repository.list_document_rows(
                        conn, int(candidate["id"])
                    )
                    if _text(document["object_key"])
                )
            )
        for candidate in candidates:
            if int(candidate["academy_teacher_id"] or 0) and (
                not purge_closed_academy_handoff(
                    conn, candidate_id=int(candidate["id"])
                )
            ):
                raise RecruitmentError(
                    "A linked Teacher Academy record changed. Refresh and try again.",
                    status_code=409,
                )
            if not repository.delete_closed_candidate(
                conn,
                candidate_id=int(candidate["id"]),
                expected_version=int(candidate["version"]),
            ):
                raise RecruitmentError(
                    "Trash Bin changed elsewhere. Refresh and try again.",
                    status_code=409,
                )
        conn.commit()
    for object_key in dict.fromkeys((key for key in object_keys if key)):
        delete_private_candidate_document(object_key)
    return {"deleted_count": len(candidates)}


def _validate_candidate_options(
    conn: Any,
    values: dict[str, Any],
    *,
    current: Any | None = None,
    dependencies: CandidateDependencies,
) -> dict[str, Any]:
    prepared = dict(values)
    if "source_option_id" in prepared and "subsource_option_id" not in prepared:
        prepared["subsource_option_id"] = None
    resolved: dict[str, Any] = {}
    current_values = _row_dict(current) if current is not None else {}
    for field, category in _CANDIDATE_OPTION_FIELDS.items():
        raw = prepared.get(field) if field in prepared else current_values.get(field)
        if not raw:
            resolved[field] = None
            continue
        option = repository.recruitment_setting_by_id(conn, int(raw))
        if not option or option["category"] != category:
            raise RecruitmentError(f"Invalid {category.replace('_', ' ')} option.")
        if field in prepared and (not bool(option["is_active"])):
            raise RecruitmentError(
                f"Select an active {category.replace('_', ' ')} option."
            )
        resolved[field] = option
    source = resolved.get("source_option_id")
    subsource = resolved.get("subsource_option_id")
    if subsource and (
        not source or int(subsource["parent_id"] or 0) != int(source["id"])
    ):
        raise RecruitmentError("The selected subsource does not belong to this source.")
    if (
        source
        and repository.active_subsource_exists(conn, int(source["id"]))
        and (not subsource)
    ):
        raise RecruitmentError("Select a subsource for this source.")
    if "position_option_id" in prepared:
        position = resolved.get("position_option_id")
        prepared["applied_position"] = _text(position.get("label")) if position else ""
    elif "applied_position" in prepared:
        legacy_label = " ".join(_text(prepared.get("applied_position")).split())
        if legacy_label:
            option = repository.recruitment_setting_by_label_or_value(
                conn,
                category="position",
                value=dependencies.setting_value("position", legacy_label),
                label=legacy_label,
            )
            if not option or not bool(option["is_active"]):
                raise RecruitmentError("Select a standardized teacher position.")
            prepared["position_option_id"] = int(option["id"])
            prepared["applied_position"] = _text(option["label"])
        else:
            prepared["position_option_id"] = None
    return prepared


def create_candidate(
    user: CurrentUser, values: dict[str, Any], *, dependencies: CandidateDependencies
) -> dict[str, Any]:
    full_name = _text(values.get("full_name"))
    if not full_name:
        raise RecruitmentError("Candidate full name is required.")
    normalized = {
        **values,
        "full_name": full_name,
        "application_date": _iso(values.get("application_date"))
        or datetime.now(SCHOOL_TIME_ZONE).date().isoformat(),
    }
    now = _now()
    with dependencies.connect() as conn:
        normalized = _validate_candidate_options(
            conn, normalized, dependencies=dependencies
        )
        identity_match = repository.exact_academy_identity_match(
            conn,
            phone=_text(normalized.get("phone")),
            email=_text(normalized.get("email")),
            telegram_username=_text(normalized.get("telegram_username")),
            linked_account_id=normalized.get("linked_account_id"),
        )
        if identity_match:
            existing = _row_dict(identity_match)
            raise RecruitmentError(
                "This identity is already linked to a Teacher Academy profile.",
                status_code=409,
                code="existing_academy_profile",
                details={
                    "profile_id": int(existing["profile_id"]),
                    "academy_teacher_id": int(existing["academy_teacher_id"]),
                    "full_name": existing.get("full_name") or "",
                    "profile_url": f"/hr-manager/candidates/{int(existing['profile_id'])}?origin=teachers",
                },
            )
        candidate_id = repository.insert_candidate(
            conn, values=normalized, now=now, actor_account_id=_actor_account(user)
        )
        if not candidate_id:
            raise RecruitmentError("Unable to create the candidate.")
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.created",
            detail={"stage": "new_candidate"},
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
    return dependencies.get_candidate(user, candidate_id)


def update_candidate(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    dependencies: CandidateDependencies,
) -> dict[str, Any]:
    expected_raw = values.pop("expected_version", None)
    expected_version = int(expected_raw) if expected_raw else None
    prepared = {
        key: (
            _iso(value)
            if key in {"application_date", "available_start_date"}
            else value
        )
        for key, value in values.items()
    }
    if "full_name" in prepared and (not _text(prepared["full_name"])):
        raise RecruitmentError("Candidate full name is required.")
    now = _now()
    with dependencies.connect() as conn:
        current = repository.get_candidate_row(conn, int(candidate_id))
        if not current:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        prepared = _validate_candidate_options(
            conn, prepared, current=current, dependencies=dependencies
        )
        updated = repository.update_candidate(
            conn,
            candidate_id=int(candidate_id),
            values=prepared,
            actor_account_id=_actor_account(user),
            now=now,
            expected_version=expected_version,
        )
        if not updated:
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        synchronized_academy_subject_id = None
        if "subject_id" in prepared and prepared.get("subject_id"):
            synchronized_academy_subject_id = (
                repository.sync_academy_subject_from_candidate(
                    conn,
                    candidate_id=int(candidate_id),
                    now=now,
                )
            )
        audit_detail: dict[str, Any] = {"fields": sorted(prepared)}
        if synchronized_academy_subject_id:
            audit_detail["academy_subject_synchronized"] = (
                synchronized_academy_subject_id
            )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.profile_updated",
            detail=audit_detail,
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return dependencies.get_candidate(user, int(candidate_id))


def move_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    stage: str,
    expected_version: int,
    reason: str = "",
    dependencies: CandidateDependencies,
) -> dict[str, Any]:
    normalized_stage = _text(stage)
    if normalized_stage not in ALL_STAGES:
        raise RecruitmentError("Unknown candidate stage.")
    if normalized_stage in PROTECTED_HIRE_STAGES or normalized_stage in {
        "rejected",
        "candidate_withdrew",
    }:
        raise RecruitmentError("Use the protected outcome action for this stage.")
    now = _now()
    with dependencies.connect() as conn:
        existing = repository.get_candidate_row(conn, int(candidate_id))
        if not existing:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if _text(existing["status"]) in PROTECTED_HIRE_STAGES:
            raise RecruitmentError(
                "Accepted candidates cannot be reopened from the pipeline.",
                status_code=409,
            )
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=normalized_stage,
            expected_version=int(expected_version),
            actor_account_id=_actor_account(user),
            now=now,
            comment=_text(reason) or f"Moved to {normalized_stage.replace('_', ' ')}.",
            transition_source=(
                "restored"
                if _text(existing["status"])
                in {"trash_bin", "rejected", "candidate_withdrew"}
                else "manual"
            ),
        )
        if not updated:
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        revoked_approval_ids: list[int] = []
        if normalized_stage == "trash_bin":
            revoked_approval_ids = repository.revoke_open_approvals(
                conn,
                candidate_id=int(candidate_id),
                comment="Candidate moved to Trash Bin.",
                actor_account_id=_actor_account(user),
                now=now,
            )
        if revoked_approval_ids:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.hire_approvals_revoked",
                detail={
                    "approval_ids": revoked_approval_ids,
                    "reason": "Candidate moved to Trash Bin.",
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        cancelled_appointment_ids: list[int] = []
        cancellation_reason = ""
        # Only terminal outcomes cancel a scheduled interview/demo. Ordinary
        # board moves keep the booking so dragging a card never destroys a
        # scheduled appointment (HR should not have to re-schedule).
        if normalized_stage in ALTERNATIVE_STAGES:
            cancellation_reason = (
                "Candidate moved to Trash Bin."
                if normalized_stage == "trash_bin"
                else f"Candidate moved from {_text(existing['status']).replace('_', ' ')} to {normalized_stage.replace('_', ' ')}."
            )
            cancelled_appointment_ids = repository.cancel_scheduled_appointments(
                conn,
                candidate_id=int(candidate_id),
                reason=cancellation_reason,
                actor_account_id=_actor_account(user),
                now=now,
            )
            dependencies.notify_cancelled_appointments(
                conn,
                candidate_id=int(candidate_id),
                appointment_ids=cancelled_appointment_ids,
            )
        if cancelled_appointment_ids:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.appointments_cancelled",
                detail={
                    "appointment_ids": cancelled_appointment_ids,
                    "reason": cancellation_reason,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        event_type = (
            "candidate.moved_to_trash"
            if normalized_stage == "trash_bin"
            else (
                "candidate.restored_from_trash"
                if _text(existing["status"]) == "trash_bin"
                else "candidate.stage_changed"
            )
        )
        move_detail: dict[str, Any] = {
            "from": existing["status"],
            "to": normalized_stage,
            "reason": _text(reason),
        }
        if normalized_stage == "responded":
            move_detail["responded_at"] = now
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=event_type,
            detail=move_detail,
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


def replace_assignments(
    user: CurrentUser,
    candidate_id: int,
    *,
    assignee_account_ids: list[int],
    subject_id: int | None,
    dependencies: CandidateDependencies,
) -> dict[str, Any]:
    now = _now()
    with dependencies.connect() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        valid_ids = repository.list_valid_evaluator_accounts(conn, assignee_account_ids)
        requested_ids = {int(item) for item in assignee_account_ids}
        if valid_ids != requested_ids:
            raise RecruitmentError(
                "Assignments may only use active Academic Director or HOD accounts."
            )
        repository.replace_assignments(
            conn,
            candidate_id=int(candidate_id),
            assignee_account_ids=valid_ids,
            subject_id=subject_id,
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
            event_type="candidate.assignments_changed",
            detail={
                "assignee_account_ids": sorted(valid_ids),
                "subject_id": subject_id,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return dependencies.get_candidate(user, int(candidate_id))


__all__ = [
    "CandidateDependencies",
    "_validate_candidate_options",
    "_validate_permanent_delete_row",
    "create_candidate",
    "empty_trash_bin",
    "get_candidate",
    "list_candidates",
    "list_decision_queue",
    "list_pipeline",
    "list_teacher_handoffs",
    "move_candidate",
    "permanently_delete_candidate",
    "replace_assignments",
    "restore_closed_candidate",
    "update_candidate",
]
