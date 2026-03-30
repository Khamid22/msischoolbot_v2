"""View-model builders for student landing/search pages."""

from .normalization_service import normalize_school_code


def _normalize_student_school_code(value):
    normalized = normalize_school_code(value)
    if normalized in {"school5", "sehriyo"}:
        return normalized
    return ""


def build_student_panel_context(
    *,
    form_data,
    student_school_code,
    load_dataset,
    seed_group_cache_from_dataset,
    build_students_by_subject_group,
    force_refresh=False,
):
    normalized_school_code = _normalize_student_school_code(student_school_code)
    try:
        if normalized_school_code:
            dataset, load_error = load_dataset(
                school_code=normalized_school_code,
                force_refresh=force_refresh,
            )
        else:
            dataset, load_error = load_dataset(force_refresh=force_refresh)
    except TypeError:
        if normalized_school_code:
            dataset, load_error = load_dataset(school_code=normalized_school_code)
        else:
            dataset, load_error = load_dataset()

    groups = dataset["groups"] if dataset else []
    groups_by_subject = dataset["groups_by_subject"] if dataset else {}
    subjects = dataset["subjects"] if dataset else []

    if dataset:
        seed_group_cache_from_dataset(dataset)

    students_by_subject_group = (
        build_students_by_subject_group(dataset["students"]) if dataset else {}
    )

    return {
        "groups": groups,
        "groups_by_subject": groups_by_subject,
        "subjects": subjects,
        "students_by_subject_group": students_by_subject_group,
        "load_error": load_error,
        "form_data": form_data,
    }


__all__ = ["build_student_panel_context"]
