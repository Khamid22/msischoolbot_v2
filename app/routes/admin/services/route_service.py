"""Business helpers used by admin route handlers."""

from .normalization_service import (
    normalize_school_code,
    normalize_text,
)


def school_code_from_name(school_name):
    normalized = normalize_text(school_name)
    if normalized == "sehriyo":
        return "sehriyo"
    if normalized in {"school 5", "school5"}:
        return "school5"
    return ""


def group_belongs_to_school(group_name, school_code, load_dataset):
    normalized_group = str(group_name or "").strip()
    normalized_school = normalize_school_code(school_code)
    if not normalized_group or not normalized_school or normalized_school == "all":
        return True

    dataset, _load_error = load_dataset(school_code=normalized_school)

    if not isinstance(dataset, dict):
        return True

    dataset_groups = dataset.get("groups", [])
    if not isinstance(dataset_groups, list):
        return True

    normalized_dataset_groups = {
        normalize_text(row)
        for row in dataset_groups
        if str(row or "").strip()
    }
    return normalize_text(normalized_group) in normalized_dataset_groups


def resolve_sheet_student_for_admin(student_row_id, get_admin_student_profile, load_dataset):
    student_profile = get_admin_student_profile(student_row_id, load_dataset)
    if not student_profile:
        return None, "Selected student was not found.", 404

    school_code = school_code_from_name(student_profile.get("school_name", ""))
    dataset, load_error = load_dataset(school_code=school_code or None)

    if load_error or not dataset:
        return None, load_error or "Unable to load Google Sheets data.", 503

    students = dataset.get("students", [])
    if not isinstance(students, list):
        return None, "Students dataset is invalid.", 503

    target_name_norm = normalize_text(student_profile.get("full_name", ""))
    preferred_group = str(student_profile.get("group", "")).strip()
    candidates = []

    for student in students:
        if not isinstance(student, dict):
            continue

        if normalize_text(student.get("fullName", "")) != target_name_norm:
            continue

        sheet_student_id = student.get("id")
        if not isinstance(sheet_student_id, int) or sheet_student_id <= 0:
            continue

        subject_name = str(student.get("subject", "")).strip()
        group_name = str(student.get("group", "")).strip()
        candidates.append(
            {
                "student_id": int(sheet_student_id),
                "subject": subject_name,
                "group": group_name,
                "school": school_code,
                "group_match": bool(preferred_group and group_name == preferred_group),
            }
        )

    if not candidates:
        return None, "No dashboard data found for this student.", 404

    candidates.sort(
        key=lambda item: (
            0 if item.get("group_match") else 1,
            str(item.get("subject", "")).casefold(),
            str(item.get("group", "")).casefold(),
            int(item.get("student_id", 0)),
        )
    )

    return candidates[0], "", 200


__all__ = [
    "group_belongs_to_school",
    "school_code_from_name",
    "resolve_sheet_student_for_admin",
]
