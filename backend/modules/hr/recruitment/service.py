"""Recruitment use cases and domain invariants."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from math import ceil
from typing import Any

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.constants import (
    ALL_STAGES,
    ALTERNATIVE_STAGES,
    CANDIDATE_SOURCES,
    DEMO_RESULTS,
    DOCUMENT_TYPES,
    INTERVIEW_RESULTS,
    PRIMARY_STAGES,
    PROTECTED_HIRE_STAGES,
    REJECTION_REASONS,
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


class RecruitmentError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


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
    return payload


def _academic_visible_id(user: CurrentUser) -> int | None:
    value = visible_account_id(user)
    return value if value and value > 0 else None


def _visible_subject_ids(user: CurrentUser, conn: Any | None = None) -> set[int] | None:
    if user.role != "head_of_department":
        return None
    return hod_subject_ids_for_user(user, conn=conn)


def list_pipeline(user: CurrentUser) -> dict[str, Any]:
    restricted = _academic_visible_id(user)
    with connect_auth_db() as conn:
        rows = repository.list_pipeline_rows(
            conn,
            visible_account_id=restricted,
            visible_subject_ids=_visible_subject_ids(user, conn),
            include_decision_queue=user.role == "academic_director",
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
        "can_manage_assignments": role in {"hr_manager", "ceo"},
        "can_move_stage": role in {"hr_manager", "ceo"},
        "can_add_academic_evaluation": academic_evaluation,
        "can_request_approval": role in {"hr_manager", "ceo"},
        "can_review_approval": role == "academic_director",
        "can_finalize": role == "ceo",
        "can_reject": role in {"academic_director", "ceo"},
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
        tasks = [_task_payload(task) for task in repository.list_task_rows(conn, candidate_id=int(candidate_id))]
        notes = [_row_dict(note) for note in repository.list_note_rows(conn, int(candidate_id))]
        assignments = [_row_dict(item) for item in repository.list_assignment_rows(conn, int(candidate_id))]
        approvals = [_row_dict(item) for item in repository.list_approval_rows(conn, int(candidate_id))]
        decisions = [_row_dict(item) for item in repository.list_decision_rows(conn, int(candidate_id))]
        activity = [_row_dict(item) for item in repository.list_activity_rows(conn, int(candidate_id))]

    uploaded_types = {item["document_type"] for item in documents}
    pending_tasks = [item for item in tasks if item["effective_status"] in {"pending", "overdue"}]
    latest_interview = interviews[0] if interviews else None
    latest_test = subject_tests[0] if subject_tests else None
    latest_demo = demos[0] if demos else None
    candidate.update(
        {
            "documents": documents,
            "interviews": interviews,
            "subject_tests": subject_tests,
            "demo_lessons": demos,
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
    normalized = {**values, "full_name": full_name, "application_date": _iso(values.get("application_date"))}
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
    prepared = {key: _iso(value) if key in {"application_date", "available_start_date"} else value for key, value in values.items()}
    if "full_name" in prepared and not _text(prepared["full_name"]):
        raise RecruitmentError("Candidate full name is required.")
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        repository.update_candidate(
            conn,
            candidate_id=int(candidate_id),
            values=prepared,
            actor_account_id=_actor_account(user),
            now=now,
        )
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


def move_candidate(user: CurrentUser, candidate_id: int, *, stage: str, expected_version: int, reason: str = "") -> dict[str, Any]:
    normalized_stage = _text(stage)
    if normalized_stage not in ALL_STAGES:
        raise RecruitmentError("Unknown candidate stage.")
    if normalized_stage in PROTECTED_HIRE_STAGES or normalized_stage in {"rejected", "on_hold", "candidate_withdrew"}:
        raise RecruitmentError("Use the final decision action for this outcome.")
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
        event_type = (
            "candidate.moved_to_trash"
            if normalized_stage == "trash_bin"
            else "candidate.restored_from_trash"
            if _text(existing["status"]) == "trash_bin"
            else "candidate.stage_changed"
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=event_type,
            detail={"from": existing["status"], "to": normalized_stage, "reason": _text(reason)},
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
    return _add_record(user, candidate_id, prepared, "candidate.interview_recorded", repository.insert_interview)


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
    return _add_record(user, candidate_id, prepared, "candidate.demo_lesson_recorded", repository.insert_demo)


def _add_record(user: CurrentUser, candidate_id: int, values: dict[str, Any], event_type: str, inserter: Any) -> dict[str, Any]:
    now = _now()
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        record_id = inserter(
            conn,
            candidate_id=int(candidate_id),
            values=values,
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.touch_candidate(conn, candidate_id=int(candidate_id), actor_account_id=_actor_account(user), now=now)
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type=event_type,
            detail={"record_id": record_id, "result": values.get("result", "")},
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
    if decision == "rejected" and user.role not in {"academic_director", "ceo"}:
        raise RecruitmentError("Only Academic Director or CEO can reject a candidate.", status_code=403)
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
        normalized_values = {
            **values,
            "decision": decision,
            "rejection_reason": rejection_reason,
            "reason_detail": reason_detail,
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
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.final_decision_made",
            detail={
                "decision_id": decision_id,
                "decision": decision,
                "rejection_reason": rejection_reason,
                "reason_detail": reason_detail,
                "approval_id": approval_id or None,
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        conn.commit()
    return get_candidate(user, int(candidate_id))


__all__ = [name for name in globals() if not name.startswith("_")]
