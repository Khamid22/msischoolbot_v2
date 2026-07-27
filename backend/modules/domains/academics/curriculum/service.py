"""Curriculum domain services."""


from backend.modules.domains.academics.curriculum import repository as academic_repository
from backend.modules.domains.academics.foundation import (
    _connect,
)

def list_lesson_catalog_for_subject(subject_name):
    """Public academic read used by student-facing lesson catalog views."""

    with _connect() as conn:
        return list(
            academic_repository.list_lesson_catalog_rows_by_subject(
                conn,
                subject_name,
            )
        )
