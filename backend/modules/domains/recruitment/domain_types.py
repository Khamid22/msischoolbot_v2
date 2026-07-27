"""Stable Recruitment database and API vocabulary for new code."""

from __future__ import annotations

from enum import StrEnum


class CandidateStage(StrEnum):
    NEW_CANDIDATE = "new_candidate"
    RESPONDED = "responded"
    JOB_INTERVIEW = "job_interview"
    TEST_AND_DEMO = "test_and_demo"
    UNDER_REVIEW = "under_review"
    TEACHER_ACADEMY = "teacher_academy"
    ACTIVE_TEACHER = "active_teacher"
    REJECTED = "rejected"
    CANDIDATE_WITHDREW = "candidate_withdrew"
    TRASH_BIN = "trash_bin"


class AppointmentType(StrEnum):
    JOB_INTERVIEW = "job_interview"
    DEMO_LESSON = "demo_lesson"


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecruitmentEventType(StrEnum):
    ACADEMY_PROFILE_CREATED = "candidate.academy_profile_created"


__all__ = [
    "AppointmentStatus",
    "AppointmentType",
    "CandidateStage",
    "RecruitmentEventType",
    "TaskStatus",
]
