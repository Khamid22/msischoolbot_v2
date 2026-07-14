"""Student-facing lesson catalog backed by canonical subject programs."""

from backend.modules.organization import canonical
from backend.modules.academics.curriculum.service import list_lesson_catalog_for_subject


def list_lessons_by_subject(subject_name, group_name=""):
    """Return the canonical subject program used by the student's group.

    Programs are currently unique per subject and academic year, so
    ``group_name`` remains part of the public contract but does not select a
    separate copy of the curriculum.
    """
    del group_name
    normalized_subject = canonical.canonical_subject_name(subject_name)
    if not normalized_subject:
        return []

    rows = list_lesson_catalog_for_subject(normalized_subject)

    return [
        {
            "group_name": "",
            "lesson_number": str(row["lesson_number"]),
            "lesson_topic": str(row["lesson_topic"]),
            "lesson_date": str(row["lesson_date"] or "").strip(),
            "lesson_order": int(row["lesson_order"]),
            "updated_at": str(row["updated_at"]),
        }
        for row in rows
    ]


def get_lessons_for_subject(subject_name, group_name):
    return list_lessons_by_subject(subject_name, group_name), ""


__all__ = ["get_lessons_for_subject", "list_lessons_by_subject"]
