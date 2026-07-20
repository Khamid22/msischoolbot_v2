"""Recruitment candidate read/query use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import ceil
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.constants import (
    ALL_STAGES,
    ALTERNATIVE_STAGES,
    DOCUMENT_TYPES,
    PRIMARY_STAGES,
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


@dataclass(frozen=True)
class CandidateReadDependencies:
    connect: Callable[..., Any]
    academic_visible_id: Callable[..., int | None]
    visible_subject_ids: Callable[..., set[int] | None]


def _iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _text(value)


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
    dependencies: CandidateReadDependencies,
) -> dict[str, Any]:
    restricted = dependencies.academic_visible_id(user)
    with dependencies.connect() as conn:
        rows = repository.list_pipeline_rows(
            conn,
            visible_account_id=restricted,
            visible_subject_ids=dependencies.visible_subject_ids(user, conn),
            include_decision_queue=user.role == "academic_director",
            search=_text(search),
            position=_text(position),
            source=_text(source),
            subject_id=subject_id,
            application_from=_text(application_from),
            application_to=_text(application_to),
            evaluator_account_id=evaluator_account_id,
        )
    candidates = [
        {**_candidate_summary(row), "permissions": _permissions(user)} for row in rows
    ]
    grouped = {stage: [] for stage in (*PRIMARY_STAGES, *ALTERNATIVE_STAGES)}
    for candidate in candidates:
        grouped.setdefault(
            _text(candidate.get("status")) or "new_candidate", []
        ).append(candidate)
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
    subject_id: int | None = None,
    application_from: str = "",
    application_to: str = "",
    closed_from: str = "",
    closed_to: str = "",
    origin_stage: str = "",
    final_decision: str = "",
    evaluator_account_id: int | None = None,
    dependencies: CandidateReadDependencies,
) -> dict[str, Any]:
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 25), 100))
    normalized_stage = _text(stage)
    if normalized_stage and normalized_stage not in ALL_STAGES:
        raise RecruitmentError("Unknown candidate stage.")
    normalized_origin_stage = _text(origin_stage)
    if normalized_origin_stage and normalized_origin_stage not in ALL_STAGES:
        raise RecruitmentError("Unknown origin stage.")
    normalized_closed_from = _text(closed_from)
    normalized_closed_to = _text(closed_to)
    try:
        parsed_closed_from = (
            date.fromisoformat(normalized_closed_from)
            if normalized_closed_from
            else None
        )
        parsed_closed_to = (
            date.fromisoformat(normalized_closed_to) if normalized_closed_to else None
        )
    except ValueError as exc:
        raise RecruitmentError("Enter a valid closed-date range.") from exc
    if (
        parsed_closed_from
        and parsed_closed_to
        and (parsed_closed_from > parsed_closed_to)
    ):
        raise RecruitmentError("Closed from date cannot be after closed to date.")
    with dependencies.connect() as conn:
        rows, total = repository.list_candidate_rows(
            conn,
            visible_account_id=dependencies.academic_visible_id(user),
            visible_subject_ids=dependencies.visible_subject_ids(user, conn),
            include_decision_queue=user.role == "academic_director",
            search=_text(search),
            position=_text(position),
            stage=normalized_stage,
            source=_text(source),
            subject_id=subject_id,
            application_from=_text(application_from),
            application_to=_text(application_to),
            closed_from=normalized_closed_from,
            closed_to=normalized_closed_to,
            origin_stage=normalized_origin_stage,
            final_decision=_text(final_decision),
            evaluator_account_id=evaluator_account_id,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    return {
        "items": [
            {**_candidate_summary(row), "permissions": _permissions(user)}
            for row in rows
        ],
        "page": safe_page,
        "per_page": safe_per_page,
        "total": total,
        "total_pages": max(1, ceil(total / safe_per_page)) if total else 1,
    }


def list_teacher_handoffs(
    user: CurrentUser,
    *,
    kind: str,
    page: int = 1,
    per_page: int = 100,
    search: str = "",
    subject_id: int | None = None,
    sort: str = "average_score",
    dependencies: CandidateReadDependencies,
) -> dict[str, Any]:
    if user.role not in {"hr_manager", "academic_director", "ceo"}:
        raise RecruitmentError(
            "Teacher handoff records require HR Manager, Academic Director, or CEO access.",
            status_code=403,
        )
    normalized_kind = _text(kind)
    if normalized_kind not in {"teacher_academy", "active_teacher"}:
        raise RecruitmentError("Unknown teacher handoff type.")
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 100), 100))
    normalized_sort = _text(sort).lower() or "average_score"
    if normalized_sort not in {"average_score", "lessons", "date"}:
        raise RecruitmentError("Unknown teacher roster sort.")
    if normalized_kind == "active_teacher":
        normalized_sort = "date"
    with dependencies.connect() as conn:
        rows, total = repository.list_teacher_handoff_rows(
            conn,
            kind=normalized_kind,
            search=_text(search),
            subject_id=subject_id,
            sort=normalized_sort,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    normalized_rows = [_row_dict(row) for row in rows]
    return {
        "items": [
            {
                "kind": _text(row["kind"]),
                "record_id": int(row["record_id"]),
                "recruitment_candidate_id": int(row["recruitment_candidate_id"] or 0),
                "full_name": _text(row["full_name"]),
                "position": _text(row["position"]),
                "subject": _text(row["subject"]),
                "status": _text(row["status"]),
                "onboarding_status": _text(row["onboarding_status"]),
                "joined_at": _iso(row["joined_at"]),
                "added_on": _text(row.get("added_on")),
                "assigned_count": int(row.get("assigned_count") or 0),
                "evaluated_count": int(row.get("evaluated_count") or 0),
                "passed_count": int(row.get("passed_count") or 0),
                "failed_count": int(row.get("failed_count") or 0),
                "average_score": (
                    round(float(row["average_score"]), 1)
                    if row.get("average_score") is not None
                    else None
                ),
                "academy_completed": bool(
                    normalized_kind == "teacher_academy"
                    and int(row.get("assigned_count") or 0) > 0
                    and (
                        int(row.get("evaluated_count") or 0)
                        == int(row.get("assigned_count") or 0)
                    )
                    and (
                        int(row.get("passed_count") or 0)
                        == int(row.get("assigned_count") or 0)
                    )
                    and (int(row.get("failed_count") or 0) == 0)
                    and (row.get("average_score") is not None)
                    and (float(row["average_score"]) > 7)
                ),
                "can_remove": user.role in {"hr_manager", "academic_director"}
                and normalized_kind == "teacher_academy",
                "can_delete": bool(
                    row["recruitment_candidate_id"]
                    and (
                        user.role == "hr_manager"
                        or (
                            user.role == "academic_director"
                            and normalized_kind == "teacher_academy"
                        )
                    )
                ),
                "can_reject": bool(
                    row["recruitment_candidate_id"]
                    and (
                        user.role == "hr_manager"
                        or (
                            user.role == "academic_director"
                            and normalized_kind == "teacher_academy"
                        )
                    )
                ),
                "generated_login_will_be_deleted": bool(
                    row.get("generated_login_will_be_deleted")
                ),
            }
            for row in normalized_rows
        ],
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
    dependencies: CandidateReadDependencies,
) -> dict[str, Any]:
    if user.role != "academic_director" or not user.account_id:
        raise RecruitmentError(
            "The recruitment decision queue requires Academic Director access.",
            status_code=403,
        )
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 25), 100))
    with dependencies.connect() as conn:
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


def get_candidate(
    user: CurrentUser, candidate_id: int, *, dependencies: CandidateReadDependencies
) -> dict[str, Any]:
    with dependencies.connect() as conn:
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
        interviews = _normalize_attempt_rows(
            repository.list_interview_rows(conn, int(candidate_id)), "interview_at"
        )
        subject_tests = _normalize_attempt_rows(
            repository.list_subject_test_rows(conn, int(candidate_id)), "test_at"
        )
        for test in subject_tests:
            score = test.get("score")
            maximum = test.get("maximum_score")
            test["percentage"] = (
                round(float(score) / float(maximum) * 100, 1)
                if score is not None and maximum
                else None
            )
        demos = _normalize_attempt_rows(
            repository.list_demo_rows(conn, int(candidate_id)), "demo_at"
        )
        appointment_rows, _ = repository.list_appointment_rows(
            conn, candidate_id=int(candidate_id), limit=100
        )
        appointments = [_appointment_payload(item) for item in appointment_rows]
        tasks = [
            _task_payload(task)
            for task in repository.list_task_rows(conn, candidate_id=int(candidate_id))
        ]
        notes = [
            _row_dict(note)
            for note in repository.list_note_rows(conn, int(candidate_id))
        ]
        assignments = [
            _row_dict(item)
            for item in repository.list_assignment_rows(conn, int(candidate_id))
        ]
        approvals = [
            _row_dict(item)
            for item in repository.list_approval_rows(conn, int(candidate_id))
        ]
        decisions = [
            _row_dict(item)
            for item in repository.list_decision_rows(conn, int(candidate_id))
        ]
        activity = [
            _row_dict(item)
            for item in repository.list_activity_rows(conn, int(candidate_id))
        ]
        stage_history = [
            _row_dict(item)
            for item in repository.list_stage_history_rows(conn, int(candidate_id))
        ]
        academy_lessons: list[dict[str, Any]] = []
        academy_assessments: list[dict[str, Any]] = []
        if candidate.get("academy_teacher_id"):
            academy_id = int(candidate["academy_teacher_id"])
            academy_lessons = [
                _row_dict(item)
                for item in repository.list_academy_lifecycle_lesson_rows(
                    conn, academy_id
                )
            ]
            academy_assessments = [
                _row_dict(item)
                for item in repository.list_academy_lifecycle_assessment_rows(
                    conn, academy_id
                )
            ]
    uploaded_types = {item["document_type"] for item in documents}
    pending_tasks = [
        item for item in tasks if item["effective_status"] in {"pending", "overdue"}
    ]
    latest_interview = next(
        (item for item in interviews if not item.get("voided_at")), None
    )
    latest_test = next(
        (item for item in subject_tests if not item.get("voided_at")), None
    )
    latest_demo = next((item for item in demos if not item.get("voided_at")), None)
    evaluation_states = _derived_evaluation_states(
        {
            **candidate,
            "latest_interview_result": (
                latest_interview.get("result") if latest_interview else ""
            ),
            "latest_subject_test_result": (
                latest_test.get("result") if latest_test else ""
            ),
            "latest_demo_result": latest_demo.get("result") if latest_demo else "",
        },
        reached_stages={_text(item.get("stage")) for item in stage_history},
    )
    progress, document_progress = _candidate_progress(
        candidate=candidate,
        stage_history=stage_history,
        documents=documents,
        interviews=interviews,
        subject_tests=subject_tests,
        demos=demos,
    )
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
            "stage_history": stage_history,
            "progress": progress,
            "evaluation_states": evaluation_states,
            "document_progress": document_progress,
            "missing_document_types": [
                item for item in DOCUMENT_TYPES if item not in uploaded_types
            ],
            "missing_required_document_types": document_progress[
                "missing_required_types"
            ],
            "under_review": {
                "interview_result": (
                    latest_interview.get("result") if latest_interview else ""
                ),
                "subject_test_result": latest_test.get("result") if latest_test else "",
                "demo_result": latest_demo.get("result") if latest_demo else "",
                "hr_recommendation": (
                    latest_interview.get("hr_recommendation")
                    if latest_interview
                    else ""
                ),
                "academic_recommendation": (
                    latest_demo.get("recommendation") if latest_demo else ""
                ),
                "unfinished_actions": len(pending_tasks),
                "final_decision": candidate.get("final_decision") or "pending",
            },
            "permissions": _permissions(
                user,
                can_add_academic_evaluation=(
                    any(
                        (
                            int(item.get("assignee_account_id") or 0)
                            == int(user.account_id or 0)
                            for item in assignments
                        )
                    )
                    if user.role in {"academic_director", "head_of_department"}
                    else None
                ),
            ),
        }
    )
    if candidate.get("academy"):
        candidate["academy"]["lessons"] = academy_lessons
        candidate["academy"]["assessments"] = academy_assessments
    return candidate


__all__ = [
    "CandidateReadDependencies",
    "get_candidate",
    "list_candidates",
    "list_decision_queue",
    "list_pipeline",
    "list_teacher_handoffs",
]
