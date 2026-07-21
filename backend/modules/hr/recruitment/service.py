"""Recruitment use cases and domain invariants."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Any
from zoneinfo import ZoneInfo

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment import notifications as recruitment_notifications
from backend.modules.hr.recruitment.appointments import service as appointment_service
from backend.modules.hr.recruitment.candidates import service as candidate_service
from backend.modules.hr.recruitment.constants import (
    ALL_STAGES,
    ALTERNATIVE_STAGES,
    APPOINTMENT_STATUSES,
    APPOINTMENT_TYPES,
    DEMO_RESULTS,
    DOCUMENT_TYPES,
    INTERVIEW_RESULTS,
    PRIMARY_STAGES,
    PROTECTED_HIRE_STAGES,
    REQUIRED_DOCUMENT_TYPES,
    RECRUITMENT_ROLES,
    RECRUITMENT_OPTION_CATEGORIES,
    REJECTION_REASONS,
    SCHEDULED_STAGE_TYPES,
    SLA_STAGES,
    TASK_STATUSES,
    OPTIONAL_DOCUMENT_TYPES,
)
from backend.modules.hr.recruitment.decisions import service as decision_service
from backend.modules.hr.recruitment.documents import service as document_service
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.evaluations import service as evaluation_service
from backend.modules.hr.recruitment.handoffs import service as handoff_service
from backend.modules.hr.recruitment.policies import visible_account_id
from backend.modules.hr.recruitment.projections import (
    appointment_payload as _appointment_payload,
    candidate_progress as _candidate_progress,
    candidate_summary as _candidate_summary,
    derived_evaluation_states as _derived_evaluation_states,
    normalize_attempt_rows as _normalize_attempt_rows,
    parse_datetime as _parse_datetime,
    permissions as _permissions,
    row_dict as _row_dict,
    sla_payload as _sla_payload,
    task_payload as _task_payload,
    text as _text,
)
from backend.modules.teacher_academy.account_provisioning import (
    AcademyAccountProvisioningError,
    provision_recruitment_academy_account,
)
from backend.platform.storage.r2 import is_r2_configured


SCHOOL_TIME_ZONE = ZoneInfo("Asia/Tashkent")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _subject_test_paper_title(candidate: Any) -> str:
    subject = _text(candidate.get("subject"))
    if not subject:
        subject = re.sub(
            r"\s+teachers?$",
            "",
            _text(candidate.get("applied_position")),
            flags=re.IGNORECASE,
        ).strip()
    subject = subject or "Subject"
    if not subject.lower().startswith("igcse"):
        subject = f"IGCSE {subject}"
    return f"{subject} Paper Test"


def _iso(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _text(value)


def _school_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        try:
            value = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise RecruitmentError("Enter a valid appointment date and time.") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=SCHOOL_TIME_ZONE)
    return value.astimezone(UTC)


def _actor_account(user: CurrentUser) -> int | None:
    return int(user.account_id) if user.account_id else None


def _actor_staff(user: CurrentUser) -> int | None:
    return int(user.staff_id) if user.staff_id else None


def _database_features_available(conn: Any) -> bool:
    return _text(getattr(conn, "db_backend", "")) == "postgres"


def _sync_system_next_actions(
    conn: Any,
    *,
    candidate_id: int,
    actor_account_id: int | None,
    now: str,
) -> None:
    if not _database_features_available(conn):
        return
    state_row = repository.candidate_automation_state_row(conn, int(candidate_id))
    if not state_row:
        return
    state = _row_dict(state_row)
    stage = _text(state.get("status"))
    stage_history_id = int(state.get("stage_history_id") or 0)
    if not stage_history_id:
        return
    due_at = _text(state.get("sla_due_at"))
    responsible_account_id = (
        int(state.get("stage_responsible_account_id") or actor_account_id or 0) or None
    )
    desired: list[dict[str, Any]] = []

    def add(task_key: str, title: str, *, due: str = due_at) -> None:
        desired.append(
            {
                "task_key": task_key,
                "title": title,
                "due_at": due,
                "responsible_account_id": responsible_account_id,
            }
        )

    if stage == "new_candidate":
        add("contact_candidate", "Contact candidate")
    elif stage == "responded":
        add("schedule_interview", "Schedule job interview")
    elif stage == "job_interview":
        if state.get("interview_appointment_id"):
            add(
                "record_interview_result",
                "Record job interview result",
                due=_text(state.get("interview_appointment_ends_at")) or due_at,
            )
        elif _text(state.get("interview_result")) != "passed":
            add("schedule_interview", "Schedule job interview")
    elif stage == "test_and_demo":
        if state.get("demo_appointment_id"):
            add(
                "record_demo_result",
                "Record demo lesson result",
                due=_text(state.get("demo_appointment_ends_at")) or due_at,
            )
        elif _text(state.get("demo_result")) != "passed":
            add("schedule_demo", "Schedule demo lesson")
        elif _text(state.get("subject_test_result")) != "passed":
            add("record_subject_test", "Record subject test")
    elif stage == "under_review":
        if int(state.get("required_document_count") or 0) < len(
            REQUIRED_DOCUMENT_TYPES
        ):
            add("collect_required_documents", "Collect required documents")
        if not state.get("actionable_approval_id"):
            add(
                "choose_teacher_destination",
                "Choose Teacher Academy or Active Teachers",
            )

    repository.replace_system_tasks(
        conn,
        candidate_id=int(candidate_id),
        stage=stage,
        stage_history_id=stage_history_id,
        desired_tasks=desired,
        actor_account_id=actor_account_id,
        now=now,
    )


def _academic_visible_id(user: CurrentUser) -> int | None:
    value = visible_account_id(user)
    return value if value and value > 0 else None


def _visible_subject_ids(user: CurrentUser, conn: Any | None = None) -> set[int] | None:
    # Recruitment visibility is assignment-scoped for both academic roles.
    # HOD subject scopes continue to apply inside Teacher Academy, not here.
    return None


def _candidate_dependencies() -> candidate_service.CandidateDependencies:
    return candidate_service.CandidateDependencies(
        connect=connect_auth_db,
        get_candidate=get_candidate,
        sync_next_actions=_sync_system_next_actions,
        notify_cancelled_appointments=_notify_cancelled_appointments,
        academic_visible_id=_academic_visible_id,
        visible_subject_ids=_visible_subject_ids,
        setting_value=_setting_value,
    )


def list_pipeline(
    user: CurrentUser,
    *,
    search: str = "",
    position: str = "",
    source: str = "",
    subject_id: int | None = None,
    application_from: str = "",
    application_to: str = "",
    evaluator_account_id: int | None = None,
) -> dict[str, Any]:
    return candidate_service.list_pipeline(
        user,
        search=search,
        position=position,
        source=source,
        subject_id=subject_id,
        application_from=application_from,
        application_to=application_to,
        evaluator_account_id=evaluator_account_id,
        dependencies=_candidate_dependencies(),
    )


def list_candidates(
    user: CurrentUser,
    *,
    page: int = 1,
    per_page: int = 25,
    search: str = "",
    position: str = "",
    stage: str = "",
    source: str = "",
    subject_id: int | None = None,
    application_from: str = "",
    application_to: str = "",
    closed_from: str = "",
    closed_to: str = "",
    origin_stage: str = "",
    final_decision: str = "",
    evaluator_account_id: int | None = None,
) -> dict[str, Any]:
    return candidate_service.list_candidates(
        user,
        page=page,
        per_page=per_page,
        search=search,
        position=position,
        stage=stage,
        source=source,
        subject_id=subject_id,
        application_from=application_from,
        application_to=application_to,
        closed_from=closed_from,
        closed_to=closed_to,
        origin_stage=origin_stage,
        final_decision=final_decision,
        evaluator_account_id=evaluator_account_id,
        dependencies=_candidate_dependencies(),
    )


def restore_closed_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    expected_version: int,
) -> dict[str, Any]:
    return candidate_service.restore_closed_candidate(
        user,
        candidate_id,
        expected_version=expected_version,
        dependencies=_candidate_dependencies(),
    )


def _validate_permanent_delete_row(candidate: Any) -> None:
    candidate_service._validate_permanent_delete_row(candidate)


def permanently_delete_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    expected_version: int,
    confirmation: str,
) -> dict[str, Any]:
    return candidate_service.permanently_delete_candidate(
        user,
        candidate_id,
        expected_version=expected_version,
        confirmation=confirmation,
        dependencies=_candidate_dependencies(),
    )


def empty_trash_bin(
    user: CurrentUser,
    *,
    confirmation: str,
) -> dict[str, Any]:
    return candidate_service.empty_trash_bin(
        user,
        confirmation=confirmation,
        dependencies=_candidate_dependencies(),
    )


def list_teacher_handoffs(
    user: CurrentUser,
    *,
    kind: str,
    page: int = 1,
    per_page: int = 100,
    search: str = "",
    subject_id: int | None = None,
    sort: str = "average_score",
) -> dict[str, Any]:
    return candidate_service.list_teacher_handoffs(
        user,
        kind=kind,
        page=page,
        per_page=per_page,
        search=search,
        subject_id=subject_id,
        sort=sort,
        dependencies=_candidate_dependencies(),
    )


def list_decision_queue(
    user: CurrentUser,
    *,
    page: int = 1,
    per_page: int = 25,
) -> dict[str, Any]:
    return candidate_service.list_decision_queue(
        user,
        page=page,
        per_page=per_page,
        dependencies=_candidate_dependencies(),
    )


def get_candidate(user: CurrentUser, candidate_id: int) -> dict[str, Any]:
    return candidate_service.get_candidate(
        user,
        candidate_id,
        dependencies=_candidate_dependencies(),
    )


def _validate_candidate_options(
    conn: Any,
    values: dict[str, Any],
    *,
    current: Any | None = None,
) -> dict[str, Any]:
    return candidate_service._validate_candidate_options(
        conn,
        values,
        current=current,
        dependencies=_candidate_dependencies(),
    )


def create_candidate(
    user: CurrentUser,
    values: dict[str, Any],
) -> dict[str, Any]:
    return candidate_service.create_candidate(
        user,
        values,
        dependencies=_candidate_dependencies(),
    )


def update_candidate(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return candidate_service.update_candidate(
        user,
        candidate_id,
        values,
        dependencies=_candidate_dependencies(),
    )


def move_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    stage: str,
    expected_version: int,
    reason: str = "",
) -> dict[str, Any]:
    return candidate_service.move_candidate(
        user,
        candidate_id,
        stage=stage,
        expected_version=expected_version,
        reason=reason,
        dependencies=_candidate_dependencies(),
    )


def replace_assignments(
    user: CurrentUser,
    candidate_id: int,
    *,
    assignee_account_ids: list[int],
    subject_id: int | None,
) -> dict[str, Any]:
    return candidate_service.replace_assignments(
        user,
        candidate_id,
        assignee_account_ids=assignee_account_ids,
        subject_id=subject_id,
        dependencies=_candidate_dependencies(),
    )


def list_tasks(user: CurrentUser) -> dict[str, Any]:
    with connect_auth_db() as conn:
        rows = repository.list_task_rows(
            conn,
            visible_account_id=_academic_visible_id(user),
            visible_subject_ids=_visible_subject_ids(user, conn),
            include_decision_queue=user.role == "academic_director",
        )
    items = [_task_payload(row) for row in rows]
    return {
        "items": items,
        "groups": {
            "overdue": [
                item for item in items if item["effective_status"] == "overdue"
            ],
            "pending": [
                item for item in items if item["effective_status"] == "pending"
            ],
            "completed": [
                item for item in items if item["effective_status"] == "completed"
            ],
            "cancelled": [
                item for item in items if item["effective_status"] == "cancelled"
            ],
        },
    }


def options() -> dict[str, Any]:
    with connect_auth_db() as conn:
        values = repository.list_recruitment_options(conn)
    configured_sources = list(values.get("sources") or [])
    configured_reasons = list(
        values.get("rejection_reason_options")
        or [
            {"value": value, "label": value.replace("_", " ").title()}
            for value in REJECTION_REASONS
        ]
    )
    return {
        **values,
        "stages": list(PRIMARY_STAGES) + list(ALTERNATIVE_STAGES),
        "sources": configured_sources,
        "document_types": list(DOCUMENT_TYPES),
        "required_document_types": sorted(REQUIRED_DOCUMENT_TYPES),
        "optional_document_types": sorted(OPTIONAL_DOCUMENT_TYPES),
        "rejection_reasons": [item["value"] for item in configured_reasons],
        "rejection_reason_options": configured_reasons,
        "document_upload_enabled": bool(is_r2_configured()),
    }


_RECRUITMENT_SETTING_CATEGORIES = RECRUITMENT_OPTION_CATEGORIES


def _setting_value(category: str, label: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
    if normalized:
        return normalized[:120]
    digest = hashlib.sha256(label.casefold().encode("utf-8")).hexdigest()[:16]
    return f"custom_{digest}"


def list_settings(user: CurrentUser) -> dict[str, Any]:
    if user.role not in {"hr_manager", "ceo"}:
        raise RecruitmentError(
            "Recruitment settings require HR or CEO access.", status_code=403
        )
    with connect_auth_db() as conn:
        rows = repository.list_recruitment_setting_rows(conn, include_inactive=True)
        sla_rows = repository.list_sla_rule_rows(conn)
        usage_counts = repository.recruitment_setting_usage_counts(conn)
    items = [_row_dict(row) for row in rows]
    for item in items:
        item["usage_count"] = usage_counts.get(int(item["id"]), 0)
    grouped = {
        category: [item for item in items if item["category"] == category]
        for category in sorted(_RECRUITMENT_SETTING_CATEGORIES)
    }
    return {
        "items": items,
        **{f"{category}s": group for category, group in grouped.items()},
        "sources": grouped["source"],
        "subsources": grouped["subsource"],
        "rejection_reasons": grouped["rejection_reason"],
        "sla_rules": [_row_dict(row) for row in sla_rows],
        "read_only": user.role == "ceo",
    }


def update_sla_rule(
    user: CurrentUser,
    *,
    stage: str,
    target_days: int,
) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError(
            "Only HR Manager can change SLA targets.", status_code=403
        )
    normalized_stage = _text(stage)
    if normalized_stage not in SLA_STAGES:
        raise RecruitmentError("This stage does not use an SLA target.")
    if int(target_days) < 1 or int(target_days) > 90:
        raise RecruitmentError("SLA target must be between 1 and 90 calendar days.")
    now = _now()
    with connect_auth_db() as conn:
        saved = repository.update_sla_rule(
            conn,
            stage=normalized_stage,
            target_days=int(target_days),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not saved:
            raise RecruitmentError("SLA rule was not found.", status_code=404)
        repository.insert_recruitment_setting_audit(
            conn,
            setting_id=0,
            event_type="recruitment.sla_rule_updated",
            detail={"stage": normalized_stage, "target_days": int(target_days)},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return _row_dict(saved)


def add_setting(
    user: CurrentUser,
    *,
    category: str,
    label: str,
    parent_id: int | None = None,
) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError(
            "Only HR Manager can manage recruitment settings.", status_code=403
        )
    normalized_category = _text(category).lower()
    normalized_label = " ".join(_text(label).split())
    if normalized_category not in _RECRUITMENT_SETTING_CATEGORIES:
        raise RecruitmentError("Unknown recruitment setting category.")
    if not normalized_label:
        raise RecruitmentError("Setting name is required.")
    if len(normalized_label) > 120:
        raise RecruitmentError("Setting name must be 120 characters or fewer.")
    normalized_parent_id = int(parent_id) if parent_id else None
    if normalized_category == "subsource" and not normalized_parent_id:
        raise RecruitmentError("Select a source for this subsource.")
    if normalized_category != "subsource" and normalized_parent_id:
        raise RecruitmentError("Only a subsource can have a parent.")
    value = _setting_value(normalized_category, normalized_label)
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.recruitment_setting_by_label_or_value(
            conn,
            category=normalized_category,
            value=value,
            label=normalized_label,
            parent_id=normalized_parent_id,
        )
        if normalized_parent_id:
            parent = repository.recruitment_setting_by_id(conn, normalized_parent_id)
            if (
                not parent
                or parent["category"] != "source"
                or not bool(parent["is_active"])
            ):
                raise RecruitmentError("Select an active source for this subsource.")
        if existing and bool(existing["is_active"]):
            raise RecruitmentError(
                "This recruitment setting already exists.", status_code=409
            )
        saved = repository.save_recruitment_setting(
            conn,
            existing_id=int(existing["id"]) if existing else None,
            category=normalized_category,
            value=value,
            label=normalized_label,
            parent_id=normalized_parent_id,
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not saved:
            raise RecruitmentError("Unable to save the recruitment setting.")
        setting = _row_dict(saved)
        repository.insert_recruitment_setting_audit(
            conn,
            setting_id=int(setting["id"]),
            event_type=(
                "recruitment.setting_reactivated"
                if existing
                else "recruitment.setting_created"
            ),
            detail={
                "category": normalized_category,
                "value": value,
                "label": normalized_label,
                **({"parent_id": normalized_parent_id} if normalized_parent_id else {}),
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return setting


def rename_setting(
    user: CurrentUser,
    setting_id: int,
    *,
    label: str,
) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError(
            "Only HR Manager can manage recruitment settings.", status_code=403
        )
    normalized_label = " ".join(_text(label).split())
    if not normalized_label:
        raise RecruitmentError("Setting name is required.")
    if len(normalized_label) > 120:
        raise RecruitmentError("Setting name must be 120 characters or fewer.")
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.recruitment_setting_by_id(conn, int(setting_id))
        if not existing:
            raise RecruitmentError("Recruitment setting was not found.", status_code=404)
        if bool(existing["is_system"]):
            raise RecruitmentError(
                "System rejection reasons cannot be renamed.", status_code=409
            )
        duplicate = repository.recruitment_setting_by_label_or_value(
            conn,
            category=_text(existing["category"]),
            value="__rename_label_check__",
            label=normalized_label,
            parent_id=existing["parent_id"],
        )
        if (
            duplicate
            and int(duplicate["id"]) != int(setting_id)
            and bool(duplicate["is_active"])
        ):
            raise RecruitmentError(
                "This recruitment setting already exists.", status_code=409
            )
        old_label = _text(existing["label"])
        renamed = repository.rename_recruitment_setting(
            conn,
            setting_id=int(setting_id),
            label=normalized_label,
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not renamed:
            raise RecruitmentError("Recruitment setting was not found.", status_code=404)
        setting = _row_dict(renamed)
        repository.insert_recruitment_setting_audit(
            conn,
            setting_id=int(setting["id"]),
            event_type="recruitment.setting_renamed",
            detail={
                "category": setting["category"],
                "value": setting["value"],
                "from_label": old_label,
                "to_label": normalized_label,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return setting


def remove_setting(user: CurrentUser, setting_id: int) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError(
            "Only HR Manager can manage recruitment settings.", status_code=403
        )
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.recruitment_setting_by_id(conn, int(setting_id))
        if existing and bool(existing["is_system"]):
            raise RecruitmentError(
                "System rejection reasons cannot be removed.", status_code=409
            )
        removed = repository.deactivate_recruitment_setting(
            conn,
            setting_id=int(setting_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not removed:
            raise RecruitmentError(
                "Recruitment setting was not found.", status_code=404
            )
        setting = _row_dict(removed)
        repository.insert_recruitment_setting_audit(
            conn,
            setting_id=int(setting["id"]),
            event_type="recruitment.setting_removed",
            detail={
                "category": setting["category"],
                "value": setting["value"],
                "label": setting["label"],
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return setting


def restore_setting(user: CurrentUser, setting_id: int) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError(
            "Only HR Manager can manage recruitment settings.", status_code=403
        )
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.recruitment_setting_by_id(conn, int(setting_id))
        if not existing:
            raise RecruitmentError("Recruitment setting was not found.", status_code=404)
        if bool(existing["is_active"]):
            raise RecruitmentError("This recruitment setting is already active.")
        if existing["category"] == "subsource" and existing["parent_id"]:
            parent = repository.recruitment_setting_by_id(
                conn, int(existing["parent_id"])
            )
            if not parent or not bool(parent["is_active"]):
                raise RecruitmentError(
                    "Restore the source before restoring this subsource."
                )
        restored = repository.save_recruitment_setting(
            conn,
            existing_id=int(setting_id),
            category=existing["category"],
            value=existing["value"],
            label=existing["label"],
            parent_id=existing["parent_id"],
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not restored:
            raise RecruitmentError("Recruitment setting was not found.", status_code=404)
        setting = _row_dict(restored)
        repository.insert_recruitment_setting_audit(
            conn,
            setting_id=int(setting["id"]),
            event_type="recruitment.setting_reactivated",
            detail={
                "category": setting["category"],
                "value": setting["value"],
                "label": setting["label"],
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return setting


def _lock_candidate(conn: Any, candidate_id: int) -> Any:
    """Use a row lock in PostgreSQL while keeping lightweight repository test doubles usable."""
    try:
        return repository.lock_candidate_decision_row(conn, int(candidate_id))
    except AttributeError:
        try:
            return repository.get_candidate_row(conn, int(candidate_id))
        except AttributeError:
            return {"id": int(candidate_id)}


def _appointment_dependencies() -> appointment_service.AppointmentDependencies:
    return appointment_service.AppointmentDependencies(
        connect=connect_auth_db,
        lock_candidate=_lock_candidate,
        get_candidate=get_candidate,
        sync_next_actions=_sync_system_next_actions,
        add_record=_add_record,
        prepare_appointment=_prepare_appointment,
        ensure_demo_assignment=_ensure_demo_assignment,
        audit_appointment=_audit_appointment,
        academic_visible_id=_academic_visible_id,
        visible_subject_ids=_visible_subject_ids,
        school_datetime=_school_datetime,
    )


def start_interview_session(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    expected_version: int,
) -> dict[str, Any]:
    return appointment_service.start_interview_session(
        user,
        candidate_id,
        appointment_id,
        expected_version=expected_version,
        dependencies=_appointment_dependencies(),
    )


def start_appointment_session(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    expected_version: int,
) -> dict[str, Any]:
    return appointment_service.start_appointment_session(
        user,
        candidate_id,
        appointment_id,
        expected_version=expected_version,
        dependencies=_appointment_dependencies(),
    )


def complete_interview_session(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return appointment_service.complete_interview_session(
        user,
        candidate_id,
        appointment_id,
        values,
        dependencies=_appointment_dependencies(),
    )


def create_appointment(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return appointment_service.create_appointment(
        user,
        candidate_id,
        values,
        dependencies=_appointment_dependencies(),
    )


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
) -> dict[str, Any]:
    return appointment_service.list_appointments(
        user,
        page=page,
        per_page=per_page,
        starts_from=starts_from,
        starts_to=starts_to,
        appointment_type=appointment_type,
        status=status,
        responsible_account_id=responsible_account_id,
        dependencies=_appointment_dependencies(),
    )


def update_appointment(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return appointment_service.update_appointment(
        user,
        candidate_id,
        appointment_id,
        values,
        dependencies=_appointment_dependencies(),
    )


def change_appointment_status(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    status: str,
    expected_version: int,
    reason: str,
) -> dict[str, Any]:
    return appointment_service.change_appointment_status(
        user,
        candidate_id,
        appointment_id,
        status=status,
        expected_version=expected_version,
        reason=reason,
        dependencies=_appointment_dependencies(),
    )


def _prepare_appointment(
    conn: Any,
    *,
    user: CurrentUser,
    candidate: Any,
    appointment_type: str,
    values: dict[str, Any],
    exclude_appointment_id: int | None = None,
    existing_note: str = "",
    job_interviewer_account_id: int | None = None,
) -> dict[str, Any]:
    if appointment_type not in APPOINTMENT_TYPES:
        raise RecruitmentError("Unknown appointment type.")
    starts_at = _school_datetime(values.get("starts_at"))
    responsible_account_id = (
        int(job_interviewer_account_id or _actor_account(user) or 0)
        if appointment_type == "job_interview"
        else int(values.get("responsible_account_id") or 0)
    )
    if appointment_type == "job_interview" and not responsible_account_id:
        raise RecruitmentError("The HR account is not available for this interview.")
    responsible = (
        repository.responsible_account_row(conn, responsible_account_id)
        if responsible_account_id
        and appointment_type == "demo_lesson"
        else None
    )
    if (
        appointment_type == "demo_lesson"
        and responsible_account_id
        and not responsible
    ):
        raise RecruitmentError("Select an active responsible staff member.")
    if responsible and _text(responsible["status"]) != "active":
        raise RecruitmentError("Select an active responsible staff member.")
    if responsible and _text(responsible["role"]) not in RECRUITMENT_ROLES:
        raise RecruitmentError(
            "Selected staff member cannot manage recruitment appointments."
        )
    if appointment_type == "demo_lesson":
        if not responsible:
            raise RecruitmentError(
                "Select an Academic Director or HOD for the demo lesson."
            )
        if _text(responsible["role"]) not in {
            "academic_director",
            "head_of_department",
        }:
            raise RecruitmentError(
                "Demo evaluator must be an Academic Director or HOD."
            )
    prepared = {
        **values,
        "appointment_type": appointment_type,
        "starts_at": starts_at.isoformat(),
        "ends_at": None,
        "responsible_account_id": responsible_account_id or None,
        "appointment_format": _text(values.get("appointment_format")),
        "location_or_link": _text(values.get("location_or_link")),
        "topic": _text(values.get("topic")),
        "note": (
            existing_note if values.get("note") is None else _text(values.get("note"))
        ),
    }
    if not prepared["appointment_format"]:
        raise RecruitmentError("Select an appointment format.")
    return prepared


def _ensure_demo_assignment(
    conn: Any,
    *,
    candidate: Any,
    values: dict[str, Any],
    actor_account_id: int | None,
    actor_staff_id: int | None,
    now: str,
) -> None:
    if values["appointment_type"] != "demo_lesson":
        return
    repository.ensure_candidate_assignment(
        conn,
        candidate_id=int(candidate["id"]),
        assignee_account_id=int(values["responsible_account_id"]),
        subject_id=int(candidate["subject_id"]) if candidate["subject_id"] else None,
        actor_account_id=actor_account_id,
        now=now,
    )
    repository.insert_audit(
        conn,
        candidate_id=int(candidate["id"]),
        event_type="candidate.assignment_ensured",
        detail={
            "assignee_account_id": int(values["responsible_account_id"]),
            "subject_id": (
                int(candidate["subject_id"]) if candidate["subject_id"] else None
            ),
            "source": "demo_lesson_appointment",
        },
        actor_account_id=actor_account_id,
        actor_staff_id=actor_staff_id,
        now=now,
    )


def _audit_appointment(
    conn: Any,
    *,
    user: CurrentUser,
    candidate_id: int,
    event_type: str,
    appointment_id: int,
    detail: dict[str, Any],
    now: str,
) -> None:
    repository.insert_audit(
        conn,
        candidate_id=int(candidate_id),
        event_type=event_type,
        detail={"appointment_id": int(appointment_id), **detail},
        actor_account_id=_actor_account(user),
        actor_staff_id=_actor_staff(user),
        now=now,
    )


def _notify_cancelled_appointments(
    conn: Any,
    *,
    candidate_id: int,
    appointment_ids: list[int],
) -> None:
    """Cancel reminders and tell assigned demo evaluators about terminal changes."""

    for appointment_id in appointment_ids:
        recruitment_notifications.cancel_demo_reminders(conn, int(appointment_id))
        if not hasattr(conn, "execute"):
            continue
        appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
        )
        if appointment and _text(appointment["appointment_type"]) == "demo_lesson":
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=appointment,
                event_type="demo_cancelled",
                version_token=int(appointment.get("version") or 1),
            )


def schedule_stage_move(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    stage = _text(values.get("stage"))
    appointment_type = SCHEDULED_STAGE_TYPES.get(stage, "")
    if not appointment_type:
        raise RecruitmentError("This stage does not use appointment scheduling.")
    now = _now()
    appointment_id = 0
    with connect_auth_db() as conn:
        candidate = _lock_candidate(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if _text(candidate["status"]) == stage:
            raise RecruitmentError(
                "Candidate is already in this stage.", status_code=409
            )
        if _text(candidate["status"]) in PROTECTED_HIRE_STAGES:
            raise RecruitmentError(
                "Accepted candidates cannot be reopened from the pipeline.",
                status_code=409,
            )
        prepared = _prepare_appointment(
            conn,
            user=user,
            candidate=candidate,
            appointment_type=appointment_type,
            values=values,
            job_interviewer_account_id=_actor_account(user),
        )
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=stage,
            expected_version=int(values.get("expected_version") or 0),
            actor_account_id=_actor_account(user),
            now=now,
            comment="Appointment scheduled",
            transition_source="manual",
        )
        if not updated:
            raise RecruitmentError(
                "This candidate changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        _ensure_demo_assignment(
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
        _audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type="candidate.appointment_scheduled",
            appointment_id=appointment_id,
            detail={
                "appointment_type": appointment_type,
                "starts_at": prepared["starts_at"],
                "ends_at": prepared["ends_at"],
                "responsible_account_id": prepared.get("responsible_account_id"),
            },
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.stage_changed",
            detail={
                "from": candidate["status"],
                "to": stage,
                "reason": "Appointment scheduled",
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        saved_appointment = (
            repository.get_appointment_row(
                conn,
                candidate_id=int(candidate_id),
                appointment_id=appointment_id,
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
        _sync_system_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    result = get_candidate(user, int(candidate_id))
    appointment = next(
        (
            item
            for item in result.get("appointments", [])
            if int(item.get("id") or 0) == appointment_id
        ),
        None,
    )
    return {"candidate": result, "appointment": appointment}


def _evaluation_dependencies() -> evaluation_service.EvaluationDependencies:
    return evaluation_service.EvaluationDependencies(
        connect=connect_auth_db,
        lock_candidate=_lock_candidate,
        get_candidate=get_candidate,
        sync_next_actions=_sync_system_next_actions,
        audit_appointment=_audit_appointment,
        notify_cancelled_appointments=_notify_cancelled_appointments,
        subject_test_paper_title=_subject_test_paper_title,
    )


def add_interview(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return evaluation_service.add_interview(
        user,
        candidate_id,
        values,
        dependencies=_evaluation_dependencies(),
    )


def add_subject_test(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return evaluation_service.add_subject_test(
        user,
        candidate_id,
        values,
        dependencies=_evaluation_dependencies(),
    )


def add_demo(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return evaluation_service.add_demo(
        user,
        candidate_id,
        values,
        dependencies=_evaluation_dependencies(),
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
) -> dict[str, Any]:
    return evaluation_service._add_record(
        user,
        candidate_id,
        values,
        event_type,
        inserter,
        appointment_type=appointment_type,
        timestamp_key=timestamp_key,
        dependencies=_evaluation_dependencies(),
    )


def delete_evaluation(
    user: CurrentUser,
    candidate_id: int,
    *,
    evaluation_type: str,
    attempt_id: int,
) -> dict[str, Any]:
    return evaluation_service.delete_evaluation(
        user,
        candidate_id,
        evaluation_type=evaluation_type,
        attempt_id=attempt_id,
        dependencies=_evaluation_dependencies(),
    )


def save_task(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
    *,
    task_id: int | None = None,
) -> dict[str, Any]:
    status = _text(values.get("status")) or "pending"
    if status == "overdue":
        status = "pending"
    if status not in TASK_STATUSES:
        raise RecruitmentError("Unknown task status.")
    prepared = {**values, "status": status, "due_at": _iso(values.get("due_at"))}
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if task_id:
            if not repository.update_task(
                conn,
                candidate_id=int(candidate_id),
                task_id=int(task_id),
                values=prepared,
                actor_account_id=_actor_account(user),
                now=now,
            ):
                raise RecruitmentError("Task was not found.", status_code=404)
            saved_id = int(task_id)
            event_type = "candidate.task_updated"
        else:
            saved_id = repository.insert_task(
                conn,
                candidate_id=int(candidate_id),
                values=prepared,
                actor_account_id=_actor_account(user),
                now=now,
            )
            event_type = "candidate.task_created"
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=event_type,
            detail={
                "task_id": saved_id,
                "status": status,
                "title": prepared.get("title", ""),
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def add_note(user: CurrentUser, candidate_id: int, body: str) -> dict[str, Any]:
    normalized = _text(body)
    if not normalized:
        raise RecruitmentError("Note text is required.")
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        note_id = repository.insert_note(
            conn,
            candidate_id=int(candidate_id),
            body=normalized,
            actor_account_id=_actor_account(user),
            actor_login=user.login,
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
            event_type="candidate.note_added",
            detail={"note_id": note_id},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def upload_document(
    user: CurrentUser,
    candidate_id: int,
    *,
    document_type: str,
    uploaded_file: Any,
    replaces_document_id: int | None = None,
) -> dict[str, Any]:
    return document_service.upload_document(
        user,
        candidate_id,
        document_type=document_type,
        uploaded_file=uploaded_file,
        replaces_document_id=replaces_document_id,
        candidate_loader=get_candidate,
        sync_next_actions=_sync_system_next_actions,
    )


def remove_document(
    user: CurrentUser, candidate_id: int, document_id: int
) -> dict[str, Any]:
    return document_service.remove_document(
        user,
        candidate_id,
        document_id,
        candidate_loader=get_candidate,
        sync_next_actions=_sync_system_next_actions,
    )


def document_url(candidate_id: int, document_id: int, *, download: bool = False) -> str:
    return document_service.document_url(
        candidate_id,
        document_id,
        download=download,
    )


def _decision_dependencies() -> decision_service.DecisionDependencies:
    return decision_service.DecisionDependencies(
        connect=connect_auth_db,
        lock_candidate=_lock_candidate,
        get_candidate=get_candidate,
        sync_next_actions=_sync_system_next_actions,
        notify_cancelled_appointments=_notify_cancelled_appointments,
        provision_academy_account=provision_recruitment_academy_account,
    )


def request_approval(
    user: CurrentUser,
    candidate_id: int,
    *,
    requested_outcome: str,
    request_note: str,
) -> dict[str, Any]:
    return decision_service.request_approval(
        user,
        candidate_id,
        requested_outcome=requested_outcome,
        request_note=request_note,
        dependencies=_decision_dependencies(),
    )


def review_approval(
    user: CurrentUser,
    candidate_id: int,
    approval_id: int,
    *,
    status: str,
    review_comment: str,
) -> dict[str, Any]:
    return decision_service.review_approval(
        user,
        candidate_id,
        approval_id,
        status=status,
        review_comment=review_comment,
        dependencies=_decision_dependencies(),
    )


def make_final_decision(
    user: CurrentUser,
    candidate_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return decision_service.make_final_decision(
        user,
        candidate_id,
        values,
        dependencies=_decision_dependencies(),
    )


def _handoff_dependencies() -> handoff_service.HandoffDependencies:
    return handoff_service.HandoffDependencies(
        connect=connect_auth_db,
        lock_candidate=_lock_candidate,
        sync_next_actions=_sync_system_next_actions,
        notify_cancelled_appointments=_notify_cancelled_appointments,
        remove_academy_teacher=remove_academy_teacher,
    )


def remove_academy_teacher(
    user: CurrentUser,
    academy_teacher_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return handoff_service.remove_academy_teacher(
        user,
        academy_teacher_id,
        values,
        dependencies=_handoff_dependencies(),
    )


def close_teacher_handoff(
    user: CurrentUser,
    *,
    kind: str,
    record_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    return handoff_service.close_teacher_handoff(
        user,
        kind=kind,
        record_id=record_id,
        values=values,
        dependencies=_handoff_dependencies(),
    )


__all__ = [name for name in globals() if not name.startswith("_")]
