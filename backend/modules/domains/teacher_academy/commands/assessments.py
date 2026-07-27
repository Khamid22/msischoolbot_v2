"""Teacher Academy assessment write use cases."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import JsonValue

from backend.modules.domains.teacher_academy import mutations_repository
from backend.modules.domains.teacher_academy.catalog import RUBRIC_WEIGHTS
from backend.modules.domains.teacher_academy.commands.create_teacher import ConnectionContext
from backend.modules.domains.teacher_academy.domain_types import VALID_DECISIONS

DEFAULT_ASSESSMENT_TYPE = "academy_practice_lesson"
DEFAULT_ASSESSMENT_DECISION = "needs_improvement"
DEFAULT_SESSION_TYPE = "training_simulation"
ASSESSMENT_DRIVEN_ACADEMY_STATUSES = frozenset(
    {
        "needs_improvement",
        "ready_for_evaluation",
        "ready_for_active_teacher",
        "rejected",
    }
)


@dataclass(frozen=True)
class AddAssessmentCommand:
    academy_teacher_id: int | str
    lesson_assignment_id: int | str
    assessment_type: str = DEFAULT_ASSESSMENT_TYPE
    evaluator_id: int | str = 0
    assessment_datetime: str = ""
    session_type: str = DEFAULT_SESSION_TYPE
    class_label: str = ""
    section_feedback: Mapping[str, JsonValue] | None = None
    scores: Mapping[str, float | int | str | None] | None = None
    strengths: str = ""
    areas_for_improvement: str = ""
    final_recommendation: str = ""
    decision: str = DEFAULT_ASSESSMENT_DECISION
    created_by: str = ""


@dataclass(frozen=True)
class DeleteAssessmentCommand:
    academy_teacher_id: int | str
    assessment_id: int | str


@dataclass(frozen=True)
class AssessmentDependencies:
    connect: Callable[[], ConnectionContext]
    now: Callable[[], str]
    as_int: Callable[[Any], int]
    as_score: Callable[[Any], float]
    normalize_status: Callable[[Any, Any, str], str]
    json_dumps: Callable[[Any], str]
    notify: Callable[..., dict[str, Any]]
    teacher_payload: Callable[[Any], dict[str, Any]]
    assignment_payload: Callable[[Any], dict[str, Any]]
    assessment_payload: Callable[..., dict[str, Any]]


def weighted_score(scores: Mapping[str, float]) -> float:
    total = sum(scores.get(key, 0.0) * weight for key, weight in RUBRIC_WEIGHTS.items())
    return round(total, 2)


def assignment_status_from_decision(decision: Any) -> str:
    normalized = str(decision or "").strip()
    passing_decisions = {
        "passed",
        "ready_for_final_evaluation",
        "approved_for_active_teacher",
    }
    return "passed" if normalized in passing_decisions else "needs_improvement"


def academy_status_from_decision(decision: Any) -> str | None:
    normalized = str(decision or "").strip()
    statuses = {
        "approved_for_active_teacher": "ready_for_active_teacher",
        "rejected": "rejected",
        "needs_improvement": "needs_improvement",
        "reassign_lesson": "needs_improvement",
        "ready_for_final_evaluation": "ready_for_evaluation",
    }
    return statuses.get(normalized)


def _insert_assessment(
    conn: ConnectionContext,
    *,
    command: AddAssessmentCommand,
    assignment: Any,
    teacher_id: int,
    assignment_id: int,
    decision: str,
    scores: Mapping[str, float],
    score: float,
    dependencies: AssessmentDependencies,
) -> None:
    mutations_repository.delete_assessments_for_assignment(
        conn,
        academy_teacher_id=teacher_id,
        lesson_assignment_id=assignment_id,
    )
    mutations_repository.insert_assessment(
        conn,
        academy_teacher_id=teacher_id,
        lesson_assignment_id=assignment_id,
        assessment_type=command.assessment_type.strip() or DEFAULT_ASSESSMENT_TYPE,
        lesson_number=str(assignment["lesson_number"] or ""),
        lesson_topic=str(assignment["lesson_topic"] or ""),
        evaluator_id=dependencies.as_int(command.evaluator_id)
        or dependencies.as_int(assignment["evaluator_id"]),
        assessment_datetime=command.assessment_datetime.strip(),
        session_type=command.session_type.strip() or DEFAULT_SESSION_TYPE,
        class_label=command.class_label.strip(),
        section_feedback_json=dependencies.json_dumps(dict(command.section_feedback or {})),
        scores=dict(scores),
        weighted_score=score,
        strengths=command.strengths.strip(),
        areas_for_improvement=command.areas_for_improvement.strip(),
        final_recommendation=command.final_recommendation.strip(),
        decision=decision,
        created_by=command.created_by.strip(),
        created_at=dependencies.now(),
    )


def _update_assessment_statuses(
    conn: ConnectionContext,
    *,
    teacher_id: int,
    assignment_id: int,
    decision: str,
    occurred_at: str,
) -> None:
    mutations_repository.update_assignment_status(
        conn,
        assignment_id=assignment_id,
        status=assignment_status_from_decision(decision),
        updated_at=occurred_at,
    )
    academy_status = academy_status_from_decision(decision)
    if academy_status:
        mutations_repository.update_academy_teacher_status(
            conn,
            academy_teacher_id=teacher_id,
            status=academy_status,
            updated_at=occurred_at,
        )
    else:
        mutations_repository.touch_academy_teacher(
            conn,
            academy_teacher_id=teacher_id,
            updated_at=occurred_at,
        )


def _notify_assessment_added(
    *,
    command: AddAssessmentCommand,
    dependencies: AssessmentDependencies,
    assignment: Any,
    decision: str,
    score: float,
) -> None:
    dependencies.notify(
        academy_teacher=dependencies.teacher_payload(assignment),
        assignment=dependencies.assignment_payload(assignment),
        assessment=dependencies.assessment_payload(
            decision=decision,
            weighted_score=score,
            assessment_datetime=command.assessment_datetime,
        ),
        event_type="assessment_added",
        title="Assessment report added",
        body="An Academic Department assessment report is available.",
        source="Academic Department",
    )


def add_assessment(
    command: AddAssessmentCommand,
    dependencies: AssessmentDependencies,
) -> tuple[bool, str]:
    teacher_id = dependencies.as_int(command.academy_teacher_id)
    if not teacher_id:
        return False, "Academy teacher not found."
    assignment_id = dependencies.as_int(command.lesson_assignment_id)
    decision = dependencies.normalize_status(
        command.decision,
        VALID_DECISIONS,
        DEFAULT_ASSESSMENT_DECISION,
    )
    scores = {key: dependencies.as_score((command.scores or {}).get(key)) for key in RUBRIC_WEIGHTS}
    score = weighted_score(scores)
    occurred_at = dependencies.now()
    with dependencies.connect() as conn:
        assignment = mutations_repository.get_assignment_for_assessment(
            conn,
            academy_teacher_id=teacher_id,
            lesson_assignment_id=assignment_id,
        )
        if not assignment:
            return False, "Assignment not found."
        _insert_assessment(
            conn,
            command=command,
            assignment=assignment,
            teacher_id=teacher_id,
            assignment_id=assignment_id,
            decision=decision,
            scores=scores,
            score=score,
            dependencies=dependencies,
        )
        _update_assessment_statuses(
            conn,
            teacher_id=teacher_id,
            assignment_id=assignment_id,
            decision=decision,
            occurred_at=occurred_at,
        )
        conn.commit()
    _notify_assessment_added(
        command=command,
        dependencies=dependencies,
        assignment=assignment,
        decision=decision,
        score=score,
    )
    return True, ""


def _update_assignment_after_delete(
    conn: ConnectionContext,
    *,
    teacher_id: int,
    assignment_id: int,
    occurred_at: str,
) -> None:
    if not assignment_id:
        return
    latest = mutations_repository.get_latest_assessment_for_assignment(
        conn,
        academy_teacher_id=teacher_id,
        lesson_assignment_id=assignment_id,
    )
    if latest:
        status = assignment_status_from_decision(latest["decision"])
    else:
        assignment = mutations_repository.get_assignment_schedule_row(conn, assignment_id)
        status = (
            "ready"
            if assignment and str(assignment["session_datetime"] or "").strip()
            else "assigned"
        )
    mutations_repository.update_assignment_status(
        conn,
        assignment_id=assignment_id,
        status=status,
        updated_at=occurred_at,
    )


def _update_teacher_after_delete(
    conn: ConnectionContext,
    *,
    teacher_id: int,
    occurred_at: str,
) -> None:
    latest = mutations_repository.get_latest_assessment_for_teacher(conn, teacher_id)
    next_status = academy_status_from_decision(latest["decision"]) if latest else None
    current_status = str(
        mutations_repository.get_academy_teacher_status(conn, teacher_id) or ""
    ).strip()
    if next_status:
        mutations_repository.update_academy_teacher_status(
            conn,
            academy_teacher_id=teacher_id,
            status=next_status,
            updated_at=occurred_at,
        )
    elif current_status in ASSESSMENT_DRIVEN_ACADEMY_STATUSES:
        mutations_repository.update_academy_teacher_status(
            conn,
            academy_teacher_id=teacher_id,
            status="in_training",
            updated_at=occurred_at,
        )
    else:
        mutations_repository.touch_academy_teacher(
            conn,
            academy_teacher_id=teacher_id,
            updated_at=occurred_at,
        )


def delete_assessment(
    command: DeleteAssessmentCommand,
    dependencies: AssessmentDependencies,
) -> tuple[bool, str]:
    teacher_id = dependencies.as_int(command.academy_teacher_id)
    assessment_id = dependencies.as_int(command.assessment_id)
    if not teacher_id or not assessment_id:
        return False, "Assessment report not found."
    occurred_at = dependencies.now()
    with dependencies.connect() as conn:
        assessment = mutations_repository.get_assessment_delete_row(
            conn,
            academy_teacher_id=teacher_id,
            assessment_id=assessment_id,
        )
        if not assessment:
            return False, "Assessment report not found."
        assignment_id = dependencies.as_int(assessment["lesson_assignment_id"])
        mutations_repository.delete_assessment_row(conn, assessment_id)
        _update_assignment_after_delete(
            conn,
            teacher_id=teacher_id,
            assignment_id=assignment_id,
            occurred_at=occurred_at,
        )
        _update_teacher_after_delete(
            conn,
            teacher_id=teacher_id,
            occurred_at=occurred_at,
        )
        conn.commit()
    return True, ""


__all__ = [
    "AddAssessmentCommand",
    "AssessmentDependencies",
    "DeleteAssessmentCommand",
    "academy_status_from_decision",
    "add_assessment",
    "assignment_status_from_decision",
    "delete_assessment",
    "weighted_score",
]
