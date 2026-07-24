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
    DOCUMENT_TYPES,
)
from backend.modules.hr.recruitment.errors import RecruitmentError
from backend.modules.hr.recruitment.projections import (
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
    appointment_payload_for_user: Callable[..., dict[str, Any]]


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
        stage_rows = repository.list_pipeline_stage_rows(conn)
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
    columns = [_row_dict(row) for row in stage_rows]
    grouped = {_text(stage.get("stage_key")): [] for stage in columns}
    for candidate in candidates:
        grouped.setdefault(
            _text(candidate.get("status")) or "new_candidate", []
        ).append(candidate)
    return {
        "columns": columns,
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
    candidate_group: str = "",
    relevant_from: str = "",
    relevant_to: str = "",
    dependencies: CandidateReadDependencies,
) -> dict[str, Any]:
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(int(per_page or 25), 100))
    normalized_stage = _text(stage)
    normalized_origin_stage = _text(origin_stage)
    normalized_closed_from = _text(closed_from)
    normalized_closed_to = _text(closed_to)
    normalized_candidate_group = _text(candidate_group).lower()
    normalized_relevant_from = _text(relevant_from)
    normalized_relevant_to = _text(relevant_to)
    if normalized_candidate_group and user.role not in {
        "academic_director",
        "head_of_department",
    }:
        raise RecruitmentError(
            "Evaluation candidate groups require academic recruitment access.",
            status_code=403,
        )
    if normalized_candidate_group not in {
        "",
        "new",
        "subject_test",
        "successful",
        "rejected",
    }:
        raise RecruitmentError("Unknown candidate group.")
    try:
        parsed_closed_from = (
            date.fromisoformat(normalized_closed_from)
            if normalized_closed_from
            else None
        )
        parsed_closed_to = (
            date.fromisoformat(normalized_closed_to) if normalized_closed_to else None
        )
        parsed_relevant_from = (
            date.fromisoformat(normalized_relevant_from)
            if normalized_relevant_from
            else None
        )
        parsed_relevant_to = (
            date.fromisoformat(normalized_relevant_to)
            if normalized_relevant_to
            else None
        )
    except ValueError as exc:
        raise RecruitmentError("Enter valid date filters.") from exc
    if (
        parsed_closed_from
        and parsed_closed_to
        and (parsed_closed_from > parsed_closed_to)
    ):
        raise RecruitmentError("Closed from date cannot be after closed to date.")
    if (
        parsed_relevant_from
        and parsed_relevant_to
        and parsed_relevant_from > parsed_relevant_to
    ):
        raise RecruitmentError("Relevant from date cannot be after relevant to date.")
    common_query = {
        "visible_account_id": dependencies.academic_visible_id(user),
        "visible_subject_ids": None,
        "include_decision_queue": user.role == "academic_director",
        "search": _text(search),
        "position": _text(position),
        "stage": normalized_stage,
        "source": _text(source),
        "subject_id": subject_id,
        "application_from": _text(application_from),
        "application_to": _text(application_to),
        "closed_from": normalized_closed_from,
        "closed_to": normalized_closed_to,
        "origin_stage": normalized_origin_stage,
        "final_decision": _text(final_decision),
        "evaluator_account_id": evaluator_account_id,
        "relevant_from": normalized_relevant_from,
        "relevant_to": normalized_relevant_to,
    }
    with dependencies.connect() as conn:
        if normalized_stage and normalized_stage not in ALL_STAGES and not repository.pipeline_stage_by_key(conn, normalized_stage):
            raise RecruitmentError("Unknown candidate stage.")
        if normalized_origin_stage and normalized_origin_stage not in ALL_STAGES and not repository.pipeline_stage_by_key(conn, normalized_origin_stage):
            raise RecruitmentError("Unknown origin stage.")
        common_query["visible_subject_ids"] = dependencies.visible_subject_ids(
            user, conn
        )
        rows, total = repository.list_candidate_rows(
            conn,
            **common_query,
            candidate_group=normalized_candidate_group,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
        group_counts = (
            {
                group: repository.list_candidate_rows(
                    conn,
                    **common_query,
                    candidate_group=group,
                    limit=0,
                )[1]
                for group in ("new", "subject_test", "successful", "rejected")
            }
            if normalized_candidate_group
            else {}
        )
        candidate_ids = []
        for row in rows:
            candidate_id = int(_row_dict(row).get("id") or 0)
            if candidate_id > 0:
                candidate_ids.append(candidate_id)
        unreviewed_candidate_ids = (
            repository.unreviewed_recruitment_candidate_ids(
                conn,
                account_id=int(user.account_id),
                candidate_ids=candidate_ids,
            )
            if normalized_candidate_group == "new" and user.account_id and rows
            else set()
        )
    items = []
    for row in rows:
        candidate = {**_candidate_summary(row), "permissions": _permissions(user)}
        if normalized_candidate_group:
            candidate["candidate_group"] = normalized_candidate_group
            candidate["relevant_at"] = {
                "new": candidate.get("academic_demo_starts_at"),
                "subject_test": candidate.get("latest_demo_at"),
                "successful": candidate.get("latest_subject_test_at"),
                "rejected": candidate.get("final_decision_at"),
            }[normalized_candidate_group]
            candidate["evaluation_evaluator_name"] = {
                "new": candidate.get("academic_demo_responsible_name")
                or candidate.get("latest_demo_evaluator_name"),
                "subject_test": candidate.get("latest_demo_evaluator_name"),
                "successful": candidate.get("latest_subject_test_evaluator_name")
                or candidate.get("latest_demo_evaluator_name"),
                "rejected": (
                    candidate.get("latest_demo_evaluator_name")
                    if candidate.get("decision_source_evaluation_type") == "demo"
                    else candidate.get("latest_subject_test_evaluator_name")
                ),
            }[normalized_candidate_group]
            candidate["is_unreviewed"] = candidate["id"] in unreviewed_candidate_ids
        items.append(candidate)
    return {
        "items": items,
        "page": safe_page,
        "per_page": safe_per_page,
        "total": total,
        "total_pages": max(1, ceil(total / safe_per_page)) if total else 1,
        "group_counts": group_counts,
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
    promotion_only: bool = False,
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
            promotion_only=promotion_only,
            limit=safe_per_page,
            offset=(safe_page - 1) * safe_per_page,
        )
    items = []
    for row in rows:
        candidate = _candidate_summary(row)
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
        appointments = [
            dependencies.appointment_payload_for_user(user, item)
            for item in appointment_rows
        ]
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
                    if user.role in {"hr_manager", "academic_director", "head_of_department"}
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
