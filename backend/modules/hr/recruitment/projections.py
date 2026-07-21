"""Pure response projections for the Recruitment domain.

This module contains no database access or mutations. Keeping payload shaping
separate lets the transactional services focus on workflow invariants.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment.constants import (
    OPTIONAL_DOCUMENT_TYPES,
    REQUIRED_DOCUMENT_TYPES,
    RECRUITMENT_ROLES,
    SLA_STAGES,
)


def text(value: Any) -> str:
    return str(value or "").strip()


def row_dict(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    result = dict(row)
    for key, value in list(result.items()):
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
    return result


def task_payload(row: Any) -> dict[str, Any]:
    payload = row_dict(row)
    status = text(payload.get("status")) or "pending"
    due_at = text(payload.get("due_at"))
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


def appointment_payload(row: Any) -> dict[str, Any]:
    payload = row_dict(row)
    payload["is_overdue"] = False
    payload["can_start"] = text(payload.get("status")) == "scheduled"
    payload["start_available_at"] = payload.get("starts_at")
    payload["overdue_at"] = None
    status = text(payload.get("status"))
    outcome = text(payload.get("evaluation_outcome")).lower()
    display_status = {
        "cancelled": "not_conducted",
        "no_show": "not_conducted",
        "in_progress": "in_progress",
    }.get(status, "")
    if outcome in {"passed", "failed"}:
        display_status = outcome
    if payload.get("starts_at"):
        try:
            starts_at = datetime.fromisoformat(
                text(payload["starts_at"]).replace("Z", "+00:00")
            )
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=UTC)
            now = datetime.now(UTC)
            payload["overdue_at"] = starts_at.isoformat()
            payload["is_overdue"] = (
                status == "scheduled" and now > starts_at
            )
            if payload["is_overdue"]:
                display_status = "overdue"
        except ValueError:
            pass
    if not display_status:
        display_status = "scheduled" if status == "scheduled" else "not_conducted"
    payload["display_status"] = display_status
    return payload


def parse_datetime(value: Any) -> datetime | None:
    raw = text(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    )


def sla_payload(
    candidate: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    stage = text(candidate.get("status"))
    if stage not in SLA_STAGES and text(candidate.get("status_kind")) != "custom":
        return None
    entered_at = parse_datetime(
        candidate.get("current_sla_anchor_at")
        or candidate.get("current_stage_entered_at")
    )
    due_at = parse_datetime(candidate.get("current_sla_due_at"))
    target_days = int(candidate.get("current_sla_target_days") or 0)
    if not entered_at or not due_at or target_days <= 0:
        return None
    current = (now or datetime.now(UTC)).astimezone(UTC)
    total_seconds = max((due_at - entered_at).total_seconds(), 1.0)
    elapsed_seconds = max((current - entered_at).total_seconds(), 0.0)
    elapsed_percentage = round((elapsed_seconds / total_seconds) * 100, 1)
    if elapsed_percentage < 75:
        status = "green"
    elif current <= due_at:
        status = "yellow"
    else:
        status = "red"
    return {
        "stage": stage,
        "status": status,
        "target_days": target_days,
        "entered_at": entered_at.isoformat(),
        "due_at": due_at.isoformat(),
        "elapsed_percentage": elapsed_percentage,
        "remaining_seconds": round((due_at - current).total_seconds()),
        "responsible_account_id": candidate.get("current_stage_responsible_account_id"),
        "responsible_name": candidate.get("current_stage_responsible_name") or "",
    }


_ORDERED_STAGE_RANK = {
    "new_candidate": 0,
    "responded": 1,
    "job_interview": 2,
    "test_and_demo": 3,
    "under_review": 4,
    "teacher_academy": 5,
    "active_teacher": 5,
}


def derived_evaluation_states(
    candidate: dict[str, Any],
    *,
    reached_stages: set[str] | None = None,
) -> dict[str, str]:
    """Return truthful workflow state without fabricating evaluation records."""

    reached = set(reached_stages or ())
    reached.add(text(candidate.get("status")))
    furthest_rank = max(
        (_ORDERED_STAGE_RANK.get(stage, -1) for stage in reached),
        default=-1,
    )
    actual_interview = text(candidate.get("latest_interview_result"))
    actual_demo = text(candidate.get("latest_demo_result"))
    actual_subject = text(candidate.get("latest_subject_test_result"))

    def _record_state(actual: str, missing_from_rank: int) -> str:
        """Reflect the real evaluation record only.

        Never fabricate a "passed" from stage progression: when a candidate has
        advanced past the stage where the evaluation was expected but no record
        exists, report "missing" so the card and profile agree. Before that
        stage the evaluation is simply "pending".
        """

        if actual == "passed":
            return "passed"
        if actual:
            return actual
        return "missing" if furthest_rank >= missing_from_rank else "pending"

    return {
        "interview": _record_state(actual_interview, 3),
        "demo": _record_state(actual_demo, 4),
        "subject_test": (
            "passed"
            if actual_subject == "passed"
            else ("not_passed" if actual_subject else "missing")
        ),
    }


def candidate_summary(row: Any) -> dict[str, Any]:
    payload = row_dict(row)
    academy_fields = {
        "academy_teacher_id": "id",
        "academy_status": "status",
        "academy_start_date": "start_date",
        "academy_onboarding_status": "onboarding_status",
        "academy_subject_id": "subject_id",
        "academy_subject": "subject",
        "academy_subject_program_id": "subject_program_id",
        "academy_curriculum": "curriculum",
        "academy_staff_id": "staff_id",
        "academy_login": "login",
        "academy_lesson_count": "lesson_count",
        "academy_assessment_count": "assessment_count",
    }
    payload["academy"] = (
        {
            **{
                target: payload.get(source) for source, target in academy_fields.items()
            },
            "account_state": (
                "connected"
                if payload.get("academy_staff_id") and payload.get("academy_login")
                else "onboarding_pending"
            ),
        }
        if payload.get("academy_teacher_id")
        else None
    )
    payload["exact_identity"] = {
        "has_phone": bool(text(payload.get("phone"))),
        "has_email": bool(text(payload.get("email"))),
        "has_telegram": bool(text(payload.get("telegram_username"))),
        "has_linked_account": bool(payload.get("linked_account_id")),
    }
    for source in academy_fields:
        if source != "academy_teacher_id":
            payload.pop(source, None)
    payload["current_sla"] = sla_payload(payload)
    if payload.get("next_task_id"):
        payload["next_task"] = task_payload(
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
        "next_appointment_started_at": "started_at",
    }
    if payload.get("next_appointment_id"):
        payload["next_appointment"] = appointment_payload(
            {
                target: payload.get(source)
                for source, target in appointment_fields.items()
            }
        )
    else:
        payload["next_appointment"] = None
    for source in appointment_fields:
        payload.pop(source, None)
    payload["evaluation_states"] = derived_evaluation_states(payload)
    return payload


def candidate_progress(
    *,
    candidate: dict[str, Any],
    stage_history: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    interviews: list[dict[str, Any]],
    subject_tests: list[dict[str, Any]],
    demos: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reached_stages = {str(item.get("stage") or "") for item in stage_history}
    uploaded_types = {str(item.get("document_type") or "") for item in documents}
    active_interviews = [item for item in interviews if not item.get("voided_at")]
    active_tests = [item for item in subject_tests if not item.get("voided_at")]
    active_demos = [item for item in demos if not item.get("voided_at")]
    stage = text(candidate.get("status"))
    evaluation_states = derived_evaluation_states(
        {
            **candidate,
            "latest_interview_result": next(
                (text(item.get("result")) for item in active_interviews),
                "",
            ),
            "latest_subject_test_result": next(
                (text(item.get("result")) for item in active_tests),
                "",
            ),
            "latest_demo_result": next(
                (text(item.get("result")) for item in active_demos),
                "",
            ),
        },
        reached_stages=reached_stages,
    )
    completed = {
        "contacted": "responded" in reached_stages
        or stage not in {"", "new_candidate"},
        "interview": evaluation_states["interview"] == "passed",
        "subject_test": evaluation_states["subject_test"] == "passed",
        "demo": evaluation_states["demo"] == "passed",
        "documents": REQUIRED_DOCUMENT_TYPES.issubset(uploaded_types),
        "review": bool(
            {"under_review", "teacher_academy", "active_teacher"} & reached_stages
        )
        or stage in {"under_review", "teacher_academy", "active_teacher"},
        "decision": bool(candidate.get("final_decision")),
    }
    labels = (
        ("contacted", "Contacted"),
        ("interview", "Interview"),
        ("subject_test", "Subject Test"),
        ("demo", "Demo"),
        ("documents", "Documents"),
        ("review", "Review"),
        ("decision", "Decision"),
    )
    first_incomplete = next((key for key, _label in labels if not completed[key]), "")
    progress = [
        {
            "key": key,
            "label": label,
            "status": (
                "completed"
                if completed[key]
                else "current" if key == first_incomplete else "pending"
            ),
        }
        for key, label in labels
    ]
    required_uploaded = len(REQUIRED_DOCUMENT_TYPES & uploaded_types)
    optional_uploaded = len(OPTIONAL_DOCUMENT_TYPES & uploaded_types)
    document_progress = {
        "required_uploaded": required_uploaded,
        "required_total": len(REQUIRED_DOCUMENT_TYPES),
        "optional_uploaded": optional_uploaded,
        "optional_total": len(OPTIONAL_DOCUMENT_TYPES),
        "completion_percentage": round(
            required_uploaded / len(REQUIRED_DOCUMENT_TYPES) * 100
        ),
        "missing_required_types": sorted(REQUIRED_DOCUMENT_TYPES - uploaded_types),
    }
    return progress, document_progress


def normalize_attempt_rows(
    rows: list[Any],
    timestamp_key: str,
) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = row_dict(row)
        alias = f"{timestamp_key}_text"
        if alias in item:
            item[timestamp_key] = item.pop(alias)
        if "created_at_text" in item:
            item["created_at"] = item.pop("created_at_text")
        if "updated_at_text" in item:
            item["updated_at"] = item.pop("updated_at_text")
        normalized.append(item)
    return normalized


def permissions(
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
        "can_add_subject_test": role == "hr_manager" or academic_evaluation,
        "can_add_academic_evaluation": academic_evaluation,
        "can_request_approval": role in {"hr_manager", "ceo"},
        "can_review_approval": role == "academic_director",
        "can_finalize": role == "ceo",
        "can_reject": role in {"hr_manager", "academic_director", "ceo"},
        "can_delete_evaluations": (role in {"hr_manager", "ceo"} or academic_evaluation),
        "can_add_note": role
        in {"hr_manager", "academic_director", "head_of_department", "ceo"},
    }


__all__ = [
    "appointment_payload",
    "candidate_progress",
    "candidate_summary",
    "derived_evaluation_states",
    "normalize_attempt_rows",
    "parse_datetime",
    "permissions",
    "row_dict",
    "sla_payload",
    "task_payload",
    "text",
]
