"""Stable Teacher Academy database and API vocabulary."""

from __future__ import annotations

from enum import StrEnum


class AcademyStatus(StrEnum):
    NEW_ACADEMY_TEACHER = "new_academy_teacher"
    IN_TRAINING = "in_training"
    READY_FOR_EVALUATION = "ready_for_evaluation"
    NEEDS_IMPROVEMENT = "needs_improvement"
    READY_FOR_ACTIVE_TEACHER = "ready_for_active_teacher"
    APPROVED = "approved"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"


class AssignmentStatus(StrEnum):
    ASSIGNED = "assigned"
    READY = "ready"
    ASSESSED = "assessed"
    PASSED = "passed"
    NEEDS_IMPROVEMENT = "needs_improvement"


class AssessmentDecision(StrEnum):
    PASSED = "passed"
    NEEDS_IMPROVEMENT = "needs_improvement"
    REASSIGN_LESSON = "reassign_lesson"
    READY_FOR_FINAL_EVALUATION = "ready_for_final_evaluation"
    APPROVED_FOR_ACTIVE_TEACHER = "approved_for_active_teacher"
    REJECTED = "rejected"


class TeacherAcademyJobTopic(StrEnum):
    SEND_NOTIFICATION = "teacher_academy.send_notification"


VALID_ACADEMY_STATUSES = frozenset(status.value for status in AcademyStatus)
VALID_ASSIGNMENT_STATUSES = frozenset(status.value for status in AssignmentStatus)
VALID_DECISIONS = frozenset(decision.value for decision in AssessmentDecision)


__all__ = [
    "AcademyStatus",
    "AssessmentDecision",
    "AssignmentStatus",
    "TeacherAcademyJobTopic",
    "VALID_ACADEMY_STATUSES",
    "VALID_ASSIGNMENT_STATUSES",
    "VALID_DECISIONS",
]
