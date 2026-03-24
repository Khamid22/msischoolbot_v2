"""Data synchronization helpers."""

try:
    from ..services.auth_service import sync_students_from_dataset, sync_students_if_needed
    from ..services.lesson_catalog_service import (
        get_lessons_for_subject,
        sync_lesson_catalog_if_needed,
    )
    from ..services.subject_summary_service import (
        get_subject_summaries_for_student,
        sync_subject_summaries_if_needed,
    )
except ImportError:
    from app.services.auth_service import sync_students_from_dataset, sync_students_if_needed
    from app.services.lesson_catalog_service import (
        get_lessons_for_subject,
        sync_lesson_catalog_if_needed,
    )
    from app.services.subject_summary_service import (
        get_subject_summaries_for_student,
        sync_subject_summaries_if_needed,
    )

__all__ = [
    "sync_students_from_dataset",
    "sync_students_if_needed",
    "sync_lesson_catalog_if_needed",
    "get_lessons_for_subject",
    "sync_subject_summaries_if_needed",
    "get_subject_summaries_for_student",
]
