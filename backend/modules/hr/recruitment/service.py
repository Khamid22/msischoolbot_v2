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
from backend.modules.hr.recruitment.constants import (
    ALL_STAGES,
    ALTERNATIVE_STAGES,
    APPOINTMENT_STATUSES,
    APPOINTMENT_TYPES,
    CANDIDATE_SOURCES,
    DEMO_RESULTS,
    DOCUMENT_TYPES,
    INTERVIEW_RESULTS,
    PRIMARY_STAGES,
    PROTECTED_HIRE_STAGES,
    RECRUITMENT_ROLES,
    REJECTION_REASONS,
    SCHEDULED_STAGE_TYPES,
    SUBJECT_TEST_RESULTS,
    TASK_STATUSES,
)
from backend.modules.hr.recruitment.policies import visible_account_id
from backend.modules.teacher_academy.policies import hod_subject_ids_for_user
from backend.platform.storage.r2 import (
    build_private_candidate_document_url,
    delete_private_candidate_document,
    is_r2_configured,
    upload_private_candidate_document,
)


SCHOOL_TIME_ZONE = ZoneInfo("Asia/Tashkent")


class RecruitmentError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "",
        details: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(value: Any) -> str:
    return str(value or "").strip()


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


def _row_dict(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    result = dict(row)
    for key, value in list(result.items()):
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
    return result


def _task_payload(row: Any) -> dict[str, Any]:
    payload = _row_dict(row)
    status = _text(payload.get("status")) or "pending"
    due_at = _text(payload.get("due_at"))
    if status == "pending" and due_at:
        try:
            due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if due.tzinfo is None:
                due = due.replace(tzinfo=UTC)
            if due < datetime.now(UTC):
                status = "overdue"
        except ValueError:
            pass
    payload["effective_status"] = status
    return payload


def _candidate_summary(row: Any) -> dict[str, Any]:
    payload = _row_dict(row)
    if payload.get("next_task_id"):
        payload["next_task"] = _task_payload(
            {
                "id": payload.get("next_task_id"),
                "title": payload.get("next_action"),
                "due_at": payload.get("next_action_at"),
                "status": "pending",
            }
        )
    else:
        payload["next_task"] = None
    appointment_fields = {
        "next_appointment_id": "id",
        "next_appointment_type": "appointment_type",
        "next_appointment_starts_at": "starts_at",
        "next_appointment_ends_at": "ends_at",
        "next_appointment_responsible_account_id": "responsible_account_id",
        "next_appointment_responsible_name": "responsible_name",
        "next_appointment_format": "appointment_format",
        "next_appointment_location_or_link": "location_or_link",
        "next_appointment_topic": "topic",
        "next_appointment_status": "status",
        "next_appointment_version": "version",
    }
    if payload.get("next_appointment_id"):
        payload["next_appointment"] = _appointment_payload(
            {
                target: payload.get(source)
                for source, target in appointment_fields.items()
            }
        )
    else:
        payload["next_appointment"] = None
    for source in appointment_fields:
        payload.pop(source, None)
    return payload


def _academic_visible_id(user: CurrentUser) -> int | None:
    value = visible_account_id(user)
    return value if value and value > 0 else None


def _visible_subject_ids(user: CurrentUser, conn: Any | None = None) -> set[int] | None:
    if user.role != "head_of_department":
        return None
    return hod_subject_ids_for_user(user, conn=conn)


def list_pipeline(
    user: CurrentUser,
    *,
    search: str = "",
    position: str = "",
    source: str = "",
    application_from: str = "",
    application_to: str = "",
    evaluator_account_id: int | None = None,
) -> dict[str, Any]:
    restricted = _academic_visible_id(user)
    with connect_auth_db() as conn:
        rows = repository.list_pipeline_rows(
            conn,
            visible_account_id=restricted,
            visible_subject_ids=_visible_subject_ids(user, conn),
            include_decision_queue=user.role == "academic_director",
            search=_text(search),
            position=_text(position),
            source=_text(source),
            application_from=_text(application_from),
            application_to=_text(application_to),
            evaluator_account_id=evaluator_account_id,
        )
    candidates = [{**_candidate_summary(row), "permissions": _permissions(user)} for row in rows]
    grouped = {stage: [] for stage in (*PRIMARY_STAGES, *ALTERNATIVE_STAGES)}
    for candidate in candidates:
        grouped.setdefault(_text(candidate.get("status")) or "new_candidate", []).append(candidate)
    return {
        "stages": grouped,
        "counts": {stage: len(items) for stage, items in grouped.items()},
        "total": len(candidates),
    }


def list_candidates(
    user: CurrentUser,
    *,
    page: int = 1,
    per_page: int = 25,
    search: str = "",
    position: str = "",
    stage: str = "",
    source: str = "",
    application_from: str = "",
    application_to: str = "",
    final_decision: str = "",
    evaluator_account_id: int | None = None,
) -> dict[str, Any]:
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 25), 100))
    normalized_stage = _text(stage)
    if normalized_stage and normalized_stage not in ALL_STAGES:
        raise RecruitmentError("Unknown candidate stage.")
    with connect_auth_db() as conn:
        rows, total = repository.list_candidate_rows(
            conn,
            visible_account_id=_academic_visible_id(user),
            visible_subject_ids=_visible_subject_ids(user, conn),
            include_decision_queue=user.role == "academic_director",
            search=_text(search),
            position=_text(position),
            stage=normalized_stage,
            source=_text(source),
            application_from=_text(application_from),
            application_to=_text(application_to),
            final_decision=_text(final_decision),
            evaluator_account_id=evaluator_account_id,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    return {
        "items": [{**_candidate_summary(row), "permissions": _permissions(user)} for row in rows],
        "page": safe_page,
        "per_page": safe_per_page,
        "total": total,
        "total_pages": max(1, ceil(total / safe_per_page)) if total else 1,
    }


def list_decision_queue(
    user: CurrentUser,
    *,
    page: int = 1,
    per_page: int = 25,
) -> dict[str, Any]:
    if user.role != "academic_director" or not user.account_id:
        raise RecruitmentError(
            "The recruitment decision queue requires Academic Director access.",
            status_code=403,
        )
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 25), 100))
    with connect_auth_db() as conn:
        rows, total = repository.list_decision_queue_rows(
            conn,
            account_id=int(user.account_id),
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    items = []
    for row in rows:
        candidate = _candidate_summary(row)
        approval_id = candidate.pop("actionable_approval_id", None)
        requested_outcome = candidate.pop("actionable_requested_outcome", None)
        approval_status = candidate.pop("actionable_approval_status", None)
        request_note = candidate.pop("actionable_request_note", None)
        requested_at = candidate.pop("actionable_requested_at", None)
        candidate["actionable_approval"] = (
            {
                "id": approval_id,
                "requested_outcome": requested_outcome,
                "status": approval_status,
                "request_note": request_note,
                "created_at": requested_at,
            }
            if approval_id
            else None
        )
        candidate["permissions"] = _permissions(user)
        items.append(candidate)
    return {
        "items": items,
        "page": safe_page,
        "per_page": safe_per_page,
        "total": total,
        "total_pages": max(1, ceil(total / safe_per_page)) if total else 1,
    }


def _normalize_attempt_rows(rows: list[Any], timestamp_key: str) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = _row_dict(row)
        alias = f"{timestamp_key}_text"
        if alias in item:
            item[timestamp_key] = item.pop(alias)
        if "created_at_text" in item:
            item["created_at"] = item.pop("created_at_text")
        if "updated_at_text" in item:
            item["updated_at"] = item.pop("updated_at_text")
        normalized.append(item)
    return normalized


def _permissions(
    user: CurrentUser,
    *,
    can_add_academic_evaluation: bool | None = None,
) -> dict[str, bool]:
    role = user.role
    academic_evaluation = (
        role in {"academic_director", "head_of_department"}
        if can_add_academic_evaluation is None
        else bool(can_add_academic_evaluation)
    )
    return {
        "can_edit_profile": role == "hr_manager",
        "can_manage_documents": role == "hr_manager",
        "can_manage_interviews": role == "hr_manager",
        "can_manage_tasks": role == "hr_manager",
        "can_manage_appointments": role in {"hr_manager", "ceo"},
        "can_view_schedule": role in RECRUITMENT_ROLES,
        "can_manage_assignments": role in {"hr_manager", "ceo"},
        "can_move_stage": role in {"hr_manager", "ceo"},
        "can_add_academic_evaluation": academic_evaluation,
        "can_request_approval": role in {"hr_manager", "ceo"},
        "can_review_approval": role == "academic_director",
        "can_finalize": role == "ceo",
        "can_reject": role in {"hr_manager", "academic_director", "ceo"},
        "can_void_evaluations": role in {"hr_manager", "ceo"} or academic_evaluation,
        "can_add_note": role in {"hr_manager", "academic_director", "head_of_department", "ceo"},
    }


def get_candidate(user: CurrentUser, candidate_id: int) -> dict[str, Any]:
    with connect_auth_db() as conn:
        row = repository.get_candidate_row(conn, int(candidate_id))
        if not row:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        candidate = _candidate_summary(row)
        documents_raw = repository.list_document_rows(conn, int(candidate_id))
        documents = []
        for document in documents_raw:
            payload = _row_dict(document)
            payload.pop("object_key", None)
            documents.append(payload)
        interviews = _normalize_attempt_rows(repository.list_interview_rows(conn, int(candidate_id)), "interview_at")
        subject_tests = _normalize_attempt_rows(repository.list_subject_test_rows(conn, int(candidate_id)), "test_at")
        for test in subject_tests:
            score = test.get("score")
            maximum = test.get("maximum_score")
            test["percentage"] = round(float(score) / float(maximum) * 100, 1) if score is not None and maximum else None
        demos = _normalize_attempt_rows(repository.list_demo_rows(conn, int(candidate_id)), "demo_at")
        appointment_rows, _ = repository.list_appointment_rows(
            conn,
            candidate_id=int(candidate_id),
            limit=100,
        )
        appointments = [_appointment_payload(item) for item in appointment_rows]
        tasks = [_task_payload(task) for task in repository.list_task_rows(conn, candidate_id=int(candidate_id))]
        notes = [_row_dict(note) for note in repository.list_note_rows(conn, int(candidate_id))]
        assignments = [_row_dict(item) for item in repository.list_assignment_rows(conn, int(candidate_id))]
        approvals = [_row_dict(item) for item in repository.list_approval_rows(conn, int(candidate_id))]
        decisions = [_row_dict(item) for item in repository.list_decision_rows(conn, int(candidate_id))]
        activity = [_row_dict(item) for item in repository.list_activity_rows(conn, int(candidate_id))]

    uploaded_types = {item["document_type"] for item in documents}
    pending_tasks = [item for item in tasks if item["effective_status"] in {"pending", "overdue"}]
    latest_interview = next((item for item in interviews if not item.get("voided_at")), None)
    latest_test = next((item for item in subject_tests if not item.get("voided_at")), None)
    latest_demo = next((item for item in demos if not item.get("voided_at")), None)
    candidate.update(
        {
            "documents": documents,
            "interviews": interviews,
            "subject_tests": subject_tests,
            "demo_lessons": demos,
            "appointments": appointments,
            "tasks": tasks,
            "notes": notes,
            "assignments": assignments,
            "approvals": approvals,
            "decisions": decisions,
            "activity": activity,
            "missing_document_types": [item for item in DOCUMENT_TYPES if item not in uploaded_types],
            "under_review": {
                "interview_result": latest_interview.get("result") if latest_interview else "",
                "subject_test_result": latest_test.get("result") if latest_test else "",
                "demo_result": latest_demo.get("result") if latest_demo else "",
                "hr_recommendation": latest_interview.get("hr_recommendation") if latest_interview else "",
                "academic_recommendation": latest_demo.get("recommendation") if latest_demo else "",
                "unfinished_actions": len(pending_tasks),
                "final_decision": candidate.get("final_decision") or "pending",
            },
            "permissions": _permissions(
                user,
                can_add_academic_evaluation=(
                    any(
                        int(item.get("assignee_account_id") or 0) == int(user.account_id or 0)
                        for item in assignments
                    )
                    if user.role in {"academic_director", "head_of_department"}
                    else None
                ),
            ),
        }
    )
    return candidate


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
            "overdue": [item for item in items if item["effective_status"] == "overdue"],
            "pending": [item for item in items if item["effective_status"] == "pending"],
            "completed": [item for item in items if item["effective_status"] == "completed"],
            "cancelled": [item for item in items if item["effective_status"] == "cancelled"],
        },
    }


def options() -> dict[str, Any]:
    with connect_auth_db() as conn:
        values = repository.list_recruitment_options(conn)
    configured_sources = list(values.get("sources") or CANDIDATE_SOURCES)
    configured_reasons = list(values.get("rejection_reason_options") or [
        {"value": value, "label": value.replace("_", " ").title()}
        for value in REJECTION_REASONS
    ])
    return {
        **values,
        "stages": list(PRIMARY_STAGES) + list(ALTERNATIVE_STAGES),
        "sources": configured_sources,
        "document_types": list(DOCUMENT_TYPES),
        "rejection_reasons": [item["value"] for item in configured_reasons],
        "rejection_reason_options": configured_reasons,
        "document_upload_enabled": bool(is_r2_configured()),
    }


_RECRUITMENT_SETTING_CATEGORIES = frozenset({"source", "rejection_reason"})


def _setting_value(category: str, label: str) -> str:
    if category == "source":
        return label
    normalized = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
    if normalized:
        return normalized[:120]
    digest = hashlib.sha256(label.casefold().encode("utf-8")).hexdigest()[:16]
    return f"custom_{digest}"


def list_settings(user: CurrentUser) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError("Only HR Manager can manage recruitment settings.", status_code=403)
    with connect_auth_db() as conn:
        rows = repository.list_recruitment_setting_rows(conn)
    items = [_row_dict(row) for row in rows]
    return {
        "items": items,
        "sources": [item for item in items if item["category"] == "source"],
        "rejection_reasons": [item for item in items if item["category"] == "rejection_reason"],
    }


def add_setting(user: CurrentUser, *, category: str, label: str) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError("Only HR Manager can manage recruitment settings.", status_code=403)
    normalized_category = _text(category).lower()
    normalized_label = " ".join(_text(label).split())
    if normalized_category not in _RECRUITMENT_SETTING_CATEGORIES:
        raise RecruitmentError("Unknown recruitment setting category.")
    if not normalized_label:
        raise RecruitmentError("Setting name is required.")
    if len(normalized_label) > 120:
        raise RecruitmentError("Setting name must be 120 characters or fewer.")
    value = _setting_value(normalized_category, normalized_label)
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.recruitment_setting_by_label_or_value(
            conn,
            category=normalized_category,
            value=value,
            label=normalized_label,
        )
        if existing and bool(existing["is_active"]):
            raise RecruitmentError("This recruitment setting already exists.", status_code=409)
        saved = repository.save_recruitment_setting(
            conn,
            existing_id=int(existing["id"]) if existing else None,
            category=normalized_category,
            value=value,
            label=normalized_label,
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not saved:
            raise RecruitmentError("Unable to save the recruitment setting.")
        setting = _row_dict(saved)
        repository.insert_recruitment_setting_audit(
            conn,
            setting_id=int(setting["id"]),
            event_type="recruitment.setting_reactivated" if existing else "recruitment.setting_created",
            detail={"category": normalized_category, "value": value, "label": normalized_label},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return setting


def remove_setting(user: CurrentUser, setting_id: int) -> dict[str, Any]:
    if user.role != "hr_manager":
        raise RecruitmentError("Only HR Manager can manage recruitment settings.", status_code=403)
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.recruitment_setting_by_id(conn, int(setting_id))
        if existing and bool(existing["is_system"]):
            raise RecruitmentError("System rejection reasons cannot be removed.", status_code=409)
        removed = repository.deactivate_recruitment_setting(
            conn,
            setting_id=int(setting_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not removed:
            raise RecruitmentError("Recruitment setting was not found.", status_code=404)
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


def create_candidate(user: CurrentUser, values: dict[str, Any]) -> dict[str, Any]:
    full_name = _text(values.get("full_name"))
    if not full_name:
        raise RecruitmentError("Candidate full name is required.")
    normalized = {
        **values,
        "full_name": full_name,
        "application_date": _iso(values.get("application_date")) or datetime.now(SCHOOL_TIME_ZONE).date().isoformat(),
    }
    now = _now()
    with connect_auth_db() as conn:
        candidate_id = repository.insert_candidate(
            conn,
            values=normalized,
            now=now,
            actor_account_id=_actor_account(user),
        )
        if not candidate_id:
            raise RecruitmentError("Unable to create the candidate.")
        comment = _text(values.get("comment"))
        if comment:
            repository.insert_note(
                conn,
                candidate_id=candidate_id,
                body=comment,
                actor_account_id=_actor_account(user),
                actor_login=user.login,
                now=now,
            )
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.created",
            detail={"stage": "new_candidate", "comment_added": bool(comment)},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, candidate_id)


def update_candidate(user: CurrentUser, candidate_id: int, values: dict[str, Any]) -> dict[str, Any]:
    expected_raw = values.pop("expected_version", None)
    expected_version = int(expected_raw) if expected_raw else None
    prepared = {key: _iso(value) if key in {"application_date", "available_start_date"} else value for key, value in values.items()}
    if "full_name" in prepared and not _text(prepared["full_name"]):
        raise RecruitmentError("Candidate full name is required.")
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        updated = repository.update_candidate(
            conn,
            candidate_id=int(candidate_id),
            values=prepared,
            actor_account_id=_actor_account(user),
            now=now,
            expected_version=expected_version,
        )
        if not updated:
            raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.profile_updated",
            detail={"fields": sorted(prepared)},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def _appointment_payload(row: Any) -> dict[str, Any]:
    payload = _row_dict(row)
    payload["is_overdue"] = False
    if _text(payload.get("status")) == "scheduled" and payload.get("ends_at"):
        try:
            ends_at = datetime.fromisoformat(_text(payload["ends_at"]).replace("Z", "+00:00"))
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=UTC)
            payload["is_overdue"] = ends_at < datetime.now(UTC)
        except ValueError:
            pass
    return payload


def _prepare_appointment(
    conn: Any,
    *,
    candidate: Any,
    appointment_type: str,
    values: dict[str, Any],
    exclude_appointment_id: int | None = None,
    existing_note: str = "",
) -> dict[str, Any]:
    if appointment_type not in APPOINTMENT_TYPES:
        raise RecruitmentError("Unknown appointment type.")
    starts_at = _school_datetime(values.get("starts_at"))
    if starts_at <= datetime.now(UTC):
        raise RecruitmentError("Appointment date and time must be in the future.")
    duration = int(values.get("duration_minutes") or (30 if appointment_type == "job_interview" else 45))
    if duration < 15 or duration > 240:
        raise RecruitmentError("Appointment duration must be between 15 and 240 minutes.")
    ends_at = starts_at + timedelta(minutes=duration)
    responsible_account_id = int(values.get("responsible_account_id") or 0)
    responsible = repository.responsible_account_row(conn, responsible_account_id) if responsible_account_id else None
    if responsible_account_id and not responsible:
        raise RecruitmentError("Select an active responsible staff member.")
    if responsible and _text(responsible["status"]) != "active":
        raise RecruitmentError("Select an active responsible staff member.")
    if responsible and _text(responsible["role"]) not in RECRUITMENT_ROLES:
        raise RecruitmentError("Selected staff member cannot manage recruitment appointments.")
    if appointment_type == "demo_lesson":
        if not responsible:
            raise RecruitmentError("Select an Academic Director or HOD for the demo lesson.")
        if _text(responsible["role"]) not in {"academic_director", "head_of_department"}:
            raise RecruitmentError("Demo evaluator must be an Academic Director or HOD.")
        if _text(responsible["role"]) == "head_of_department":
            subject_id = int(candidate["subject_id"] or 0)
            if not subject_id or not repository.hod_account_has_subject_scope(
                conn,
                account_id=responsible_account_id,
                subject_id=subject_id,
            ):
                raise RecruitmentError("Selected HOD is outside this candidate's subject scope.", status_code=403)
    prepared = {
        **values,
        "appointment_type": appointment_type,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "duration_minutes": duration,
        "responsible_account_id": responsible_account_id or None,
        "appointment_format": _text(values.get("appointment_format")),
        "location_or_link": _text(values.get("location_or_link")),
        "topic": _text(values.get("topic")),
        "note": existing_note if values.get("note") is None else _text(values.get("note")),
    }
    if not prepared["appointment_format"]:
        raise RecruitmentError("Select an appointment format.")
    conflicts = (
        repository.list_appointment_conflicts(
            conn,
            responsible_account_id=responsible_account_id,
            starts_at=prepared["starts_at"],
            ends_at=prepared["ends_at"],
            exclude_appointment_id=exclude_appointment_id,
        )
        if responsible_account_id
        else []
    )
    if conflicts and not bool(values.get("allow_conflict")):
        raise RecruitmentError(
            "This staff member already has an overlapping recruitment appointment.",
            status_code=409,
            code="appointment_conflict",
            details=[_appointment_payload(item) for item in conflicts],
        )
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
            "subject_id": int(candidate["subject_id"]) if candidate["subject_id"] else None,
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
        candidate = repository.get_candidate_row(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if _text(candidate["status"]) == stage:
            raise RecruitmentError("Candidate is already in this stage.", status_code=409)
        if _text(candidate["status"]) in PROTECTED_HIRE_STAGES:
            raise RecruitmentError("Accepted candidates cannot be reopened from the pipeline.", status_code=409)
        prepared = _prepare_appointment(
            conn,
            candidate=candidate,
            appointment_type=appointment_type,
            values=values,
        )
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=stage,
            expected_version=int(values.get("expected_version") or 0),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not updated:
            raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
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
        saved_appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=appointment_id,
        ) if hasattr(conn, "execute") else None
        if saved_appointment:
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=saved_appointment,
                event_type="demo_assigned",
                version_token=int(saved_appointment["version"] or 1),
                include_reminders=True,
            )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.stage_changed",
            detail={"from": candidate["status"], "to": stage, "reason": "Appointment scheduled"},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    result = get_candidate(user, int(candidate_id))
    appointment = next((item for item in result.get("appointments", []) if int(item.get("id") or 0) == appointment_id), None)
    return {"candidate": result, "appointment": appointment}


def create_appointment(user: CurrentUser, candidate_id: int, values: dict[str, Any]) -> dict[str, Any]:
    appointment_type = _text(values.get("appointment_type"))
    now = _now()
    appointment_id = 0
    with connect_auth_db() as conn:
        candidate = repository.get_candidate_row(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if _text(candidate["status"]) in {*PROTECTED_HIRE_STAGES, *ALTERNATIVE_STAGES}:
            raise RecruitmentError("Reopen this candidate before adding an appointment.", status_code=409)
        expected_stage = "job_interview" if appointment_type == "job_interview" else "test_and_demo"
        if _text(candidate["status"]) != expected_stage:
            raise RecruitmentError(
                f"Move the candidate to {expected_stage.replace('_', ' ').title()} before scheduling this appointment.",
                status_code=409,
            )
        existing_appointment = repository.scheduled_appointment_for_type(
            conn,
            candidate_id=int(candidate_id),
            appointment_type=appointment_type,
        )
        if existing_appointment:
            raise RecruitmentError(
                "This candidate already has an active appointment of this type. Reschedule it instead.",
                status_code=409,
                code="appointment_already_scheduled",
                details={"appointment_id": int(existing_appointment["id"])},
            )
        prepared = _prepare_appointment(
            conn,
            candidate=candidate,
            appointment_type=appointment_type,
            values=values,
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
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        _audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type="candidate.appointment_scheduled",
            appointment_id=appointment_id,
            detail={"appointment_type": appointment_type, "starts_at": prepared["starts_at"], "ends_at": prepared["ends_at"]},
            now=now,
        )
        saved_appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=appointment_id,
        ) if hasattr(conn, "execute") else None
        if saved_appointment:
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=saved_appointment,
                event_type="demo_assigned",
                version_token=int(saved_appointment["version"] or 1),
                include_reminders=True,
            )
        conn.commit()
    result = get_candidate(user, int(candidate_id))
    appointment = next((item for item in result.get("appointments", []) if int(item.get("id") or 0) == appointment_id), None)
    return {"candidate": result, "appointment": appointment}


def list_appointments(
    user: CurrentUser,
    *,
    page: int = 1,
    per_page: int = 50,
    starts_from: str = "",
    starts_to: str = "",
    appointment_type: str = "",
    status: str = "scheduled",
    responsible_account_id: int | None = None,
) -> dict[str, Any]:
    if appointment_type and appointment_type not in APPOINTMENT_TYPES:
        raise RecruitmentError("Unknown appointment type.")
    if status and status not in APPOINTMENT_STATUSES:
        raise RecruitmentError("Unknown appointment status.")
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 50), 100))
    normalized_from = _school_datetime(starts_from).isoformat() if starts_from else ""
    normalized_to = _school_datetime(starts_to).isoformat() if starts_to else ""
    with connect_auth_db() as conn:
        rows, total = repository.list_appointment_rows(
            conn,
            visible_account_id=_academic_visible_id(user),
            visible_subject_ids=_visible_subject_ids(user, conn),
            starts_from=normalized_from,
            starts_to=normalized_to,
            appointment_type=appointment_type,
            status=status,
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
) -> dict[str, Any]:
    now = _now()
    with connect_auth_db() as conn:
        candidate = repository.get_candidate_row(conn, int(candidate_id))
        appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
            for_update=True,
        )
        if not candidate or not appointment:
            raise RecruitmentError("Appointment was not found.", status_code=404)
        if _text(appointment["status"]) != "scheduled":
            raise RecruitmentError("Only scheduled appointments can be changed.", status_code=409)
        prepared = _prepare_appointment(
            conn,
            candidate=candidate,
            appointment_type=_text(appointment["appointment_type"]),
            values=values,
            exclude_appointment_id=int(appointment_id),
            existing_note=_text(appointment["note"]),
        )
        _ensure_demo_assignment(
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
            and old_demo_evaluator != new_demo_evaluator
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
            raise RecruitmentError("This appointment changed elsewhere. Refresh and try again.", status_code=409)
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        _audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type="candidate.appointment_rescheduled",
            appointment_id=int(appointment_id),
            detail={"starts_at": prepared["starts_at"], "ends_at": prepared["ends_at"]},
            now=now,
        )
        saved_appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
        )
        if saved_appointment:
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=saved_appointment,
                event_type="demo_rescheduled",
                version_token=int(saved_appointment["version"] or 1),
                include_reminders=True,
            )
        conn.commit()
    return {"candidate": get_candidate(user, int(candidate_id))}


def change_appointment_status(
    user: CurrentUser,
    candidate_id: int,
    appointment_id: int,
    *,
    status: str,
    expected_version: int,
    reason: str,
) -> dict[str, Any]:
    if status not in {"cancelled", "no_show"}:
        raise RecruitmentError("Unknown appointment status action.")
    if status == "cancelled" and not _text(reason):
        raise RecruitmentError("Add a cancellation reason.")
    now = _now()
    with connect_auth_db() as conn:
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
            raise RecruitmentError("This appointment changed elsewhere. Refresh and try again.", status_code=409)
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        _audit_appointment(
            conn,
            user=user,
            candidate_id=int(candidate_id),
            event_type=f"candidate.appointment_{status}",
            appointment_id=int(appointment_id),
            detail={"reason": _text(reason)},
            now=now,
        )
        changed_appointment = repository.get_appointment_row(
            conn,
            candidate_id=int(candidate_id),
            appointment_id=int(appointment_id),
        )
        if changed_appointment and _text(changed_appointment["appointment_type"] if "appointment_type" in changed_appointment else "") == "demo_lesson":
            recruitment_notifications.cancel_demo_reminders(conn, int(appointment_id))
            recruitment_notifications.enqueue_demo_event(
                conn,
                appointment=changed_appointment,
                event_type="demo_cancelled" if status == "cancelled" else "demo_no_show",
                version_token=int(changed_appointment["version"] or 1),
            )
        conn.commit()
    return {"candidate": get_candidate(user, int(candidate_id))}


def hold_candidate(
    user: CurrentUser,
    candidate_id: int,
    *,
    expected_version: int,
    reason: str,
    application_date: Any = None,
) -> dict[str, Any]:
    normalized_reason = _text(reason)
    if not normalized_reason:
        raise RecruitmentError("Add an On Hold reason.")
    now = _now()
    with connect_auth_db() as conn:
        candidate = repository.get_candidate_row(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        origin_stage = _text(candidate["status"])
        if origin_stage == "on_hold":
            raise RecruitmentError("Candidate is already On Hold.", status_code=409)
        if origin_stage in PROTECTED_HIRE_STAGES:
            raise RecruitmentError("Accepted candidates cannot be placed On Hold.", status_code=409)
        normalized_application_date = _iso(application_date) or _text(candidate.get("application_date") if hasattr(candidate, "get") else candidate["application_date"])
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage="on_hold",
            expected_version=int(expected_version),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not updated:
            raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
        repository.release_open_hold(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        hold_id = repository.insert_candidate_hold(
            conn,
            candidate_id=int(candidate_id),
            origin_stage=origin_stage,
            reason=normalized_reason,
            application_date=normalized_application_date,
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.set_candidate_application_date(
            conn,
            candidate_id=int(candidate_id),
            application_date=normalized_application_date,
            actor_account_id=_actor_account(user),
            now=now,
        )
        cancelled = repository.cancel_scheduled_appointments(
            conn,
            candidate_id=int(candidate_id),
            reason="Candidate placed On Hold.",
            actor_account_id=_actor_account(user),
            now=now,
        )
        _notify_cancelled_appointments(
            conn,
            candidate_id=int(candidate_id),
            appointment_ids=cancelled,
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.placed_on_hold",
            detail={
                "hold_id": hold_id,
                "from": origin_stage,
                "to": "on_hold",
                "reason": normalized_reason,
                "application_date": normalized_application_date,
                "cancelled_appointment_ids": cancelled,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def move_candidate(user: CurrentUser, candidate_id: int, *, stage: str, expected_version: int, reason: str = "") -> dict[str, Any]:
    normalized_stage = _text(stage)
    if normalized_stage not in ALL_STAGES:
        raise RecruitmentError("Unknown candidate stage.")
    if normalized_stage in PROTECTED_HIRE_STAGES or normalized_stage in {"rejected", "on_hold", "candidate_withdrew"}:
        raise RecruitmentError("Use the protected outcome action for this stage.")
    now = _now()
    with connect_auth_db() as conn:
        existing = repository.get_candidate_row(conn, int(candidate_id))
        if not existing:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if _text(existing["status"]) in PROTECTED_HIRE_STAGES:
            raise RecruitmentError("Accepted candidates cannot be reopened from the pipeline.", status_code=409)
        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=normalized_stage,
            expected_version=int(expected_version),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not updated:
            raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
        released_hold_ids: list[int] = []
        if _text(existing["status"]) == "on_hold" and normalized_stage != "on_hold":
            released_hold_ids = repository.release_open_hold(
                conn,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                now=now,
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
                detail={"approval_ids": revoked_approval_ids, "reason": "Candidate moved to Trash Bin."},
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        cancelled_appointment_ids: list[int] = []
        cancellation_reason = ""
        if normalized_stage == "trash_bin" or (
            _text(existing["status"]) in SCHEDULED_STAGE_TYPES
            and normalized_stage != _text(existing["status"])
        ):
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
            _notify_cancelled_appointments(
                conn,
                candidate_id=int(candidate_id),
                appointment_ids=cancelled_appointment_ids,
            )
        if cancelled_appointment_ids:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.appointments_cancelled",
                detail={"appointment_ids": cancelled_appointment_ids, "reason": cancellation_reason},
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
        event_type = (
            "candidate.moved_to_trash"
            if normalized_stage == "trash_bin"
            else "candidate.restored_from_trash"
            if _text(existing["status"]) == "trash_bin"
            else "candidate.stage_changed"
        )
        move_detail: dict[str, Any] = {
            "from": existing["status"],
            "to": normalized_stage,
            "reason": _text(reason),
        }
        if normalized_stage == "responded":
            move_detail["responded_at"] = now
        if released_hold_ids:
            move_detail["released_hold_ids"] = released_hold_ids
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=event_type,
            detail=move_detail,
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def replace_assignments(user: CurrentUser, candidate_id: int, *, assignee_account_ids: list[int], subject_id: int | None) -> dict[str, Any]:
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        valid_ids = repository.list_valid_evaluator_accounts(conn, assignee_account_ids)
        requested_ids = {int(item) for item in assignee_account_ids}
        if valid_ids != requested_ids:
            raise RecruitmentError("Assignments may only use active Academic Director or HOD accounts.")
        repository.replace_assignments(
            conn,
            candidate_id=int(candidate_id),
            assignee_account_ids=valid_ids,
            subject_id=subject_id,
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.assignments_changed",
            detail={"assignee_account_ids": sorted(valid_ids), "subject_id": subject_id},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def add_interview(user: CurrentUser, candidate_id: int, values: dict[str, Any]) -> dict[str, Any]:
    if _text(values.get("result")) not in INTERVIEW_RESULTS:
        raise RecruitmentError("Unknown interview result.")
    prepared = {**values, "interview_at": _iso(values.get("interview_at"))}
    prepared["interviewer_account_id"] = prepared.get("interviewer_account_id") or _actor_account(user)
    return _add_record(
        user,
        candidate_id,
        prepared,
        "candidate.interview_recorded",
        repository.insert_interview,
        appointment_type="job_interview",
        timestamp_key="interview_at",
    )


def add_subject_test(user: CurrentUser, candidate_id: int, values: dict[str, Any]) -> dict[str, Any]:
    if _text(values.get("result")) not in SUBJECT_TEST_RESULTS:
        raise RecruitmentError("Unknown subject test result.")
    score, maximum = values.get("score"), values.get("maximum_score")
    if score is not None and maximum is not None and Decimal(score) > Decimal(maximum):
        raise RecruitmentError("Test score cannot exceed the maximum score.")
    prepared = {**values, "test_at": _iso(values.get("test_at"))}
    prepared["evaluator_account_id"] = _actor_account(user)
    return _add_record(user, candidate_id, prepared, "candidate.subject_test_recorded", repository.insert_subject_test)


def add_demo(user: CurrentUser, candidate_id: int, values: dict[str, Any]) -> dict[str, Any]:
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
    now = _now()
    evaluation_type = (
        "interview"
        if event_type == "candidate.interview_recorded"
        else "subject_test"
        if event_type == "candidate.subject_test_recorded"
        else "demo"
    )
    with connect_auth_db() as conn:
        database_backed = hasattr(conn, "execute")
        candidate = (
            repository.lock_candidate_decision_row(conn, int(candidate_id))
            if database_backed
            else repository.get_candidate_row(conn, int(candidate_id))
        )
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
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
                raise RecruitmentError("Appointment type does not match this evaluation.", status_code=409)
            if _text(appointment["status"]) != "scheduled":
                raise RecruitmentError("This appointment is no longer scheduled.", status_code=409)
            if timestamp_key and not _text(values.get(timestamp_key)):
                values[timestamp_key] = _text(appointment["starts_at"])
            if appointment_type == "job_interview" and appointment["responsible_account_id"]:
                values["interviewer_account_id"] = int(appointment["responsible_account_id"])
            if appointment_type == "demo_lesson" and _text(values.get("result")) == "passed":
                if int(appointment["responsible_account_id"] or 0) != int(_actor_account(user) or 0):
                    raise RecruitmentError(
                        "Only the assigned demo evaluator can submit the passing result.",
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
            if not repository.complete_appointment(
                conn,
                appointment_id=appointment_id,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                now=now,
            ):
                raise RecruitmentError("This appointment changed elsewhere. Refresh and try again.", status_code=409)
            if appointment_type == "demo_lesson":
                recruitment_notifications.cancel_demo_reminders(conn, appointment_id)
                completed_appointment = repository.get_appointment_row(
                    conn,
                    candidate_id=int(candidate_id),
                    appointment_id=appointment_id,
                )
                if completed_appointment:
                    recruitment_notifications.enqueue_demo_event(
                        conn,
                        appointment=completed_appointment,
                        event_type="demo_completed",
                        version_token=int(completed_appointment.get("version") or 1),
                    )
            _audit_appointment(
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
        if result == "failed" and candidate.get("status") is not None and candidate.get("version") is not None:
            if _text(candidate["status"]) in {*PROTECTED_HIRE_STAGES, "rejected", "candidate_withdrew", "trash_bin"}:
                raise RecruitmentError("A finalized candidate cannot receive another rejecting evaluation.", status_code=409)
            rejection_reason, rejection_label = {
                "interview": ("failed_job_interview", "Failed job interview"),
                "subject_test": ("failed_subject_test", "Failed subject test"),
                "demo": ("failed_demo_lesson", "Failed demo lesson"),
            }[evaluation_type]
            evaluator_account_id = int(
                values.get("interviewer_account_id")
                or values.get("evaluator_account_id")
                or _actor_account(user)
                or 0
            ) or None
            cancelled_after_failure = repository.cancel_scheduled_appointments(
                conn,
                candidate_id=int(candidate_id),
                reason=rejection_label,
                actor_account_id=evaluator_account_id,
                now=now,
            )
            _notify_cancelled_appointments(
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
                    actor_staff_id=_actor_staff(user) if evaluator_account_id == _actor_account(user) else None,
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
            ):
                raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
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
                actor_staff_id=_actor_staff(user) if evaluator_account_id == _actor_account(user) else None,
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.stage_changed",
                detail={"from": _text(candidate["status"]), "to": "rejected", "reason": rejection_label},
                actor_account_id=evaluator_account_id,
                actor_staff_id=_actor_staff(user) if evaluator_account_id == _actor_account(user) else None,
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
                detail={"appointment_ids": cancelled_after_failure, "evaluation_type": evaluation_type, "record_id": record_id},
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
            evaluation_type == "demo"
            and result == "passed"
            and appointment_id
            and _text(candidate.get("status")) == "test_and_demo"
        ):
            if not repository.update_candidate_stage(
                conn,
                candidate_id=int(candidate_id),
                stage="under_review",
                expected_version=int(candidate["version"]),
                actor_account_id=_actor_account(user),
                now=now,
            ):
                raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
            stage_changed = True
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.stage_changed",
                detail={"from": "test_and_demo", "to": "under_review", "reason": "Passed assigned demo lesson"},
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
                conn,
                candidate_id=int(candidate_id),
                appointment_id=appointment_id,
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
        conn.commit()
    return get_candidate(user, int(candidate_id))


def void_evaluation(
    user: CurrentUser,
    candidate_id: int,
    *,
    evaluation_type: str,
    attempt_id: int,
    reason: str,
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
    if user.role in {"academic_director", "head_of_department"} and evaluation_type == "interview":
        raise RecruitmentError("Academic evaluators cannot void HR interview results.", status_code=403)
    if user.role not in {"hr_manager", "ceo", "academic_director", "head_of_department"}:
        raise RecruitmentError("You cannot void recruitment evaluations.", status_code=403)
    now = _now()
    with connect_auth_db() as conn:
        database_backed = hasattr(conn, "execute")
        candidate = (
            repository.lock_candidate_decision_row(conn, int(candidate_id))
            if database_backed
            else repository.get_candidate_row(conn, int(candidate_id))
        )
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        evaluation = repository.get_evaluation_row(
            conn,
            table=table,
            candidate_id=int(candidate_id),
            attempt_id=int(attempt_id),
            for_update=True,
        ) if database_backed else {"id": attempt_id, "result": "", "voided_at": None}
        if not evaluation or evaluation["voided_at"]:
            raise RecruitmentError("Evaluation was not found or was already voided.", status_code=409)
        system_decision = repository.get_system_decision_for_evaluation(
            conn,
            candidate_id=int(candidate_id),
            evaluation_type=evaluation_type,
            attempt_id=int(attempt_id),
            for_update=True,
        ) if database_backed else None
        if system_decision:
            latest_decision = repository.latest_active_final_decision(
                conn,
                int(candidate_id),
                for_update=True,
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
            raise RecruitmentError("Evaluation was not found or was already voided.", status_code=409)
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
                raise RecruitmentError("The automatic rejection changed elsewhere.", status_code=409)
            if not repository.update_candidate_stage(
                conn,
                candidate_id=int(candidate_id),
                stage=restored_stage,
                expected_version=int(candidate["version"]),
                actor_account_id=_actor_account(user),
                now=now,
            ):
                raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
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
                detail={"from": "rejected", "to": restored_stage, "reason": "Failed evaluation voided"},
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
        conn.commit()
    return get_candidate(user, int(candidate_id))


def save_task(user: CurrentUser, candidate_id: int, values: dict[str, Any], *, task_id: int | None = None) -> dict[str, Any]:
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
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=event_type,
            detail={"task_id": saved_id, "status": status, "title": prepared.get("title", "")},
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
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
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


def upload_document(user: CurrentUser, candidate_id: int, *, document_type: str, uploaded_file: Any, replaces_document_id: int | None = None) -> dict[str, Any]:
    normalized_type = _text(document_type).lower()
    if normalized_type not in DOCUMENT_TYPES:
        raise RecruitmentError("Unknown candidate document type.")
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        replaced = (
            repository.get_document_row(conn, candidate_id=int(candidate_id), document_id=int(replaces_document_id))
            if replaces_document_id
            else None
        )
        if replaces_document_id and not replaced:
            raise RecruitmentError("Document to replace was not found.", status_code=404)

    uploaded, error = upload_private_candidate_document(
        uploaded_file,
        candidate_id=int(candidate_id),
        document_type=normalized_type,
    )
    if error:
        raise RecruitmentError(error)
    now = _now()
    try:
        with connect_auth_db() as conn:
            document_id = repository.insert_document(
                conn,
                values={
                    **uploaded,
                    "candidate_id": int(candidate_id),
                    "document_type": normalized_type,
                    "version": int(replaced["version"] or 1) + 1 if replaced else 1,
                    "replaces_document_id": int(replaces_document_id) if replaces_document_id else None,
                },
                actor_account_id=_actor_account(user),
                now=now,
            )
            if replaced:
                repository.remove_document(conn, document_id=int(replaces_document_id), actor_account_id=_actor_account(user), now=now)
            repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.document_replaced" if replaced else "candidate.document_uploaded",
                detail={
                    "document_id": document_id,
                    "document_type": normalized_type,
                    "file_name": uploaded["original_file_name"],
                    "replaces_document_id": replaces_document_id,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
            conn.commit()
    except Exception:
        delete_private_candidate_document(uploaded.get("object_key"))
        raise
    if replaced:
        delete_private_candidate_document(replaced["object_key"])
    return get_candidate(user, int(candidate_id))


def remove_document(user: CurrentUser, candidate_id: int, document_id: int) -> dict[str, Any]:
    now = _now()
    with connect_auth_db() as conn:
        document = repository.get_document_row(conn, candidate_id=int(candidate_id), document_id=int(document_id))
        if not document:
            raise RecruitmentError("Document was not found.", status_code=404)
        repository.remove_document(conn, document_id=int(document_id), actor_account_id=_actor_account(user), now=now)
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.document_removed",
            detail={"document_id": int(document_id), "document_type": document["document_type"], "file_name": document["original_file_name"]},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    delete_private_candidate_document(document["object_key"])
    return get_candidate(user, int(candidate_id))


def document_url(candidate_id: int, document_id: int, *, download: bool = False) -> str:
    with connect_auth_db() as conn:
        document = repository.get_document_row(conn, candidate_id=int(candidate_id), document_id=int(document_id))
    if not document:
        raise RecruitmentError("Document was not found.", status_code=404)
    url = build_private_candidate_document_url(
        document["object_key"],
        original_file_name=document["original_file_name"],
        download=download,
    )
    if not url:
        raise RecruitmentError("Private document storage is unavailable.", status_code=503)
    return url


def request_approval(user: CurrentUser, candidate_id: int, *, requested_outcome: str, request_note: str) -> dict[str, Any]:
    outcome = _text(requested_outcome)
    if outcome not in PROTECTED_HIRE_STAGES:
        raise RecruitmentError("Hiring approval is only available for Academy or Active Teacher outcomes.")
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        approval_id = repository.insert_approval_request(
            conn,
            candidate_id=int(candidate_id),
            outcome=outcome,
            note=_text(request_note),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.hire_approval_requested",
            detail={"approval_id": approval_id, "requested_outcome": outcome},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def _approve_and_finalize_request(
    user: CurrentUser,
    candidate_id: int,
    approval_id: int,
    *,
    review_comment: str,
) -> dict[str, Any]:
    now = _now()
    with connect_auth_db() as conn:
        candidate = repository.lock_candidate_decision_row(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        approval = repository.get_approval_row(
            conn,
            candidate_id=int(candidate_id),
            approval_id=int(approval_id),
            for_update=True,
        )
        if not approval:
            mismatched = repository.get_approval_by_id(
                conn,
                approval_id=int(approval_id),
                for_update=True,
            )
            if mismatched:
                raise RecruitmentError(
                    "Approval request does not belong to this candidate.",
                    status_code=409,
                )
            raise RecruitmentError("Approval request was not found.", status_code=404)

        outcome = _text(approval["requested_outcome"])
        approval_status = _text(approval["status"])
        linked_id = (
            int(candidate["academy_teacher_id"] or 0)
            if outcome == "teacher_academy"
            else int(candidate["active_teacher_id"] or 0)
        )
        if approval_status == "consumed":
            final_decision = repository.final_decision_for_approval(
                conn,
                candidate_id=int(candidate_id),
                approval_id=int(approval_id),
            )
            if (
                outcome in PROTECTED_HIRE_STAGES
                and _text(candidate["status"]) == outcome
                and linked_id
                and final_decision
                and _text(final_decision["decision"]) == outcome
            ):
                conn.rollback()
                return get_candidate(user, int(candidate_id))
            raise RecruitmentError("This approval was already consumed by another decision.", status_code=409)
        if approval_status not in {"requested", "approved"}:
            raise RecruitmentError("Approval request is no longer actionable.", status_code=409)
        if outcome not in PROTECTED_HIRE_STAGES:
            raise RecruitmentError("Approval request has an invalid hiring outcome.", status_code=409)
        if _text(candidate["status"]) in PROTECTED_HIRE_STAGES or linked_id:
            raise RecruitmentError("The candidate already has a finalized hiring outcome.", status_code=409)

        if approval_status == "requested":
            if not repository.review_approval(
                conn,
                candidate_id=int(candidate_id),
                approval_id=int(approval_id),
                status="approved",
                comment=review_comment,
                actor_account_id=_actor_account(user),
                now=now,
            ):
                raise RecruitmentError("Approval request changed elsewhere. Refresh and try again.", status_code=409)
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.hire_approval_approved",
                detail={"approval_id": int(approval_id), "comment": review_comment},
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )

        if outcome == "teacher_academy":
            repository.ensure_academy_intake(conn, candidate=candidate, actor_login=user.login, now=now)
        else:
            repository.ensure_active_teacher_intake(conn, candidate=candidate, now=now)

        updated = repository.update_candidate_stage(
            conn,
            candidate_id=int(candidate_id),
            stage=outcome,
            expected_version=int(candidate["version"]),
            actor_account_id=_actor_account(user),
            now=now,
        )
        if not updated:
            raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
        decision_id = repository.insert_final_decision(
            conn,
            candidate_id=int(candidate_id),
            values={
                "decision": outcome,
                "rejection_reason": "",
                "reason_detail": review_comment,
                "origin_stage": _text(candidate["status"]),
                "follow_up_at": "",
                "approval_id": int(approval_id),
            },
            actor_account_id=_actor_account(user),
            actor_login=user.login,
            now=now,
        )
        repository.consume_approval(conn, approval_id=int(approval_id), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.final_decision_made",
            detail={
                "decision_id": decision_id,
                "decision": outcome,
                "rejection_reason": "",
                "reason_detail": review_comment,
                "approval_id": int(approval_id),
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def review_approval(user: CurrentUser, candidate_id: int, approval_id: int, *, status: str, review_comment: str) -> dict[str, Any]:
    normalized_status = _text(status)
    normalized_comment = _text(review_comment)
    if normalized_status not in {"approved", "returned"}:
        raise RecruitmentError("Unknown approval review status.")
    if normalized_status == "returned" and not normalized_comment:
        raise RecruitmentError("A comment is required when returning an approval request.")
    if normalized_status == "approved":
        return _approve_and_finalize_request(
            user,
            candidate_id,
            approval_id,
            review_comment=normalized_comment or "Approved and finalized by Academic Director.",
        )
    now = _now()
    with connect_auth_db() as conn:
        if not repository.review_approval(
            conn,
            candidate_id=int(candidate_id),
            approval_id=int(approval_id),
            status=normalized_status,
            comment=normalized_comment,
            actor_account_id=_actor_account(user),
            now=now,
        ):
            raise RecruitmentError("Approval request was not found or is no longer pending.", status_code=409)
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=f"candidate.hire_approval_{normalized_status}",
            detail={"approval_id": int(approval_id), "comment": normalized_comment},
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


def make_final_decision(user: CurrentUser, candidate_id: int, values: dict[str, Any]) -> dict[str, Any]:
    decision = _text(values.get("decision"))
    allowed = {*PROTECTED_HIRE_STAGES, "rejected", "on_hold", "candidate_withdrew"}
    if decision not in allowed:
        raise RecruitmentError("Unknown final decision.")
    if decision in PROTECTED_HIRE_STAGES and user.role != "ceo":
        raise RecruitmentError("Only CEO can directly finalize this hiring outcome.", status_code=403)
    if decision == "rejected" and user.role not in {"hr_manager", "academic_director", "ceo"}:
        raise RecruitmentError("You cannot reject this candidate.", status_code=403)
    if decision in {"on_hold", "candidate_withdrew"} and user.role not in {"hr_manager", "ceo"}:
        raise RecruitmentError("You cannot record this outcome.", status_code=403)

    rejection_reason = _text(values.get("rejection_reason"))
    reason_detail = _text(values.get("reason_detail"))
    if decision == "rejected":
        if not rejection_reason:
            raise RecruitmentError("Select a rejection reason.")
        if rejection_reason == "other" and not reason_detail:
            raise RecruitmentError("Explain the other rejection reason.")
    if decision == "on_hold" and not reason_detail:
        raise RecruitmentError("Add an On Hold reason.")

    now = _now()
    approval_id = int(values.get("approval_id") or 0)
    with connect_auth_db() as conn:
        if decision == "rejected" and not repository.recruitment_setting_value_exists(
            conn,
            category="rejection_reason",
            value=rejection_reason,
        ):
            raise RecruitmentError("Select an active rejection reason.")
        candidate = repository.lock_candidate_decision_row(conn, int(candidate_id))
        if not candidate:
            raise RecruitmentError("Candidate was not found.", status_code=404)
        if decision == "rejected" and (
            _text(candidate["status"]) in PROTECTED_HIRE_STAGES
            or int(candidate["academy_teacher_id"] or 0)
            or int(candidate["active_teacher_id"] or 0)
        ):
            raise RecruitmentError("A finalized teacher intake cannot be rejected.", status_code=409)
        if decision in PROTECTED_HIRE_STAGES:
            linked_id = int(candidate["academy_teacher_id"] or 0) if decision == "teacher_academy" else int(candidate["active_teacher_id"] or 0)
            if _text(candidate["status"]) == decision and linked_id:
                conn.rollback()
                return get_candidate(user, int(candidate_id))
            if not approval_id:
                raise RecruitmentError("Academic Director approval is required.")
            approval = repository.get_approval_row(
                conn,
                candidate_id=int(candidate_id),
                approval_id=approval_id,
                for_update=True,
            )
            if not approval or approval["status"] != "approved" or approval["requested_outcome"] != decision:
                raise RecruitmentError("Use an approved Academic Director request for this outcome.", status_code=409)

        if decision == "teacher_academy":
            repository.ensure_academy_intake(conn, candidate=candidate, actor_login=user.login, now=now)
        elif decision == "active_teacher":
            repository.ensure_active_teacher_intake(conn, candidate=candidate, now=now)

        revoked_approval_ids: list[int] = []
        if decision == "rejected":
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
        )
        if not updated:
            raise RecruitmentError("This candidate changed elsewhere. Refresh and try again.", status_code=409)
        cancelled_appointment_ids: list[int] = []
        if decision in {"rejected", "on_hold", "candidate_withdrew"}:
            cancelled_appointment_ids = repository.cancel_scheduled_appointments(
                conn,
                candidate_id=int(candidate_id),
                reason=f"Candidate moved to {decision.replace('_', ' ')}.",
                actor_account_id=_actor_account(user),
                now=now,
            )
            _notify_cancelled_appointments(
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
        if decision in PROTECTED_HIRE_STAGES:
            repository.consume_approval(conn, approval_id=approval_id, now=now)
        if revoked_approval_ids:
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type="candidate.hire_approvals_revoked",
                detail={"approval_ids": revoked_approval_ids, "reason": reason_detail or rejection_reason},
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
        conn.commit()
    return get_candidate(user, int(candidate_id))


__all__ = [name for name in globals() if not name.startswith("_")]
