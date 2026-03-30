"""Dataset loading service facade."""

from typing import Any

from app.config.schools import DEFAULT_SCHOOL_CODE, get_configured_school_spreadsheets
from app.integrations.sheets_data import SheetsDataError, get_school_dataset


def _merge_datasets(datasets):
    merged_students = []
    merged_dashboards_by_id: dict[int, dict[str, Any]] = {}
    groups_set = set()
    subjects_set = set()
    groups_by_subject_sets: dict[str, set[str]] = {}
    lesson_catalog_by_subject: dict[str, list[dict[str, Any]]] = {}
    lesson_catalog_by_subject_group: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue

        dataset_students = dataset.get("students", [])
        if isinstance(dataset_students, list):
            merged_students.extend(
                student for student in dataset_students if isinstance(student, dict)
            )

        dataset_dashboards = dataset.get("dashboards_by_id", {})
        if isinstance(dataset_dashboards, dict):
            merged_dashboards_by_id.update(dataset_dashboards)

        dataset_groups = dataset.get("groups", [])
        if isinstance(dataset_groups, list):
            for group_name in dataset_groups:
                normalized_group = str(group_name or "").strip()
                if normalized_group:
                    groups_set.add(normalized_group)

        dataset_subjects = dataset.get("subjects", [])
        if isinstance(dataset_subjects, list):
            for subject_name in dataset_subjects:
                normalized_subject = str(subject_name or "").strip()
                if normalized_subject:
                    subjects_set.add(normalized_subject)

        dataset_groups_by_subject = dataset.get("groups_by_subject", {})
        if isinstance(dataset_groups_by_subject, dict):
            for subject_name, groups in dataset_groups_by_subject.items():
                normalized_subject = str(subject_name or "").strip()
                if not normalized_subject:
                    continue
                target_groups = groups_by_subject_sets.setdefault(normalized_subject, set())
                if isinstance(groups, list):
                    for group_name in groups:
                        normalized_group = str(group_name or "").strip()
                        if normalized_group:
                            target_groups.add(normalized_group)

        dataset_lesson_catalog_by_subject = dataset.get("lesson_catalog_by_subject", {})
        if isinstance(dataset_lesson_catalog_by_subject, dict):
            for subject_name, lessons in dataset_lesson_catalog_by_subject.items():
                normalized_subject = str(subject_name or "").strip()
                if not normalized_subject or not isinstance(lessons, list):
                    continue
                target_lessons = lesson_catalog_by_subject.setdefault(normalized_subject, [])
                target_lessons.extend(
                    lesson for lesson in lessons if isinstance(lesson, dict)
                )

        dataset_lesson_catalog_by_subject_group = dataset.get(
            "lesson_catalog_by_subject_group",
            {},
        )
        if isinstance(dataset_lesson_catalog_by_subject_group, dict):
            for subject_name, group_map in dataset_lesson_catalog_by_subject_group.items():
                normalized_subject = str(subject_name or "").strip()
                if not normalized_subject or not isinstance(group_map, dict):
                    continue
                subject_groups = lesson_catalog_by_subject_group.setdefault(
                    normalized_subject,
                    {},
                )
                for group_name, lessons in group_map.items():
                    normalized_group = str(group_name or "").strip()
                    if not normalized_group or not isinstance(lessons, list):
                        continue
                    target_lessons = subject_groups.setdefault(normalized_group, [])
                    target_lessons.extend(
                        lesson for lesson in lessons if isinstance(lesson, dict)
                    )

    def _dedupe_lessons(lessons):
        deduped = []
        seen = set()
        for lesson in lessons:
            lesson_number = str(lesson.get("lesson_number", "")).strip()
            lesson_topic = str(lesson.get("lesson_topic", "")).strip()
            if not lesson_number or not lesson_topic:
                continue
            dedupe_key = (lesson_number.casefold(), lesson_topic.casefold())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            deduped.append(lesson)
        return deduped

    for subject_name, lessons in list(lesson_catalog_by_subject.items()):
        lesson_catalog_by_subject[subject_name] = _dedupe_lessons(lessons)

    for subject_name, group_map in list(lesson_catalog_by_subject_group.items()):
        normalized_group_map = {}
        for group_name, lessons in group_map.items():
            normalized_group_map[group_name] = _dedupe_lessons(lessons)
        lesson_catalog_by_subject_group[subject_name] = normalized_group_map

    return {
        "students": merged_students,
        "dashboards_by_id": merged_dashboards_by_id,
        "groups": sorted(groups_set, key=lambda value: value.casefold()),
        "subjects": sorted(subjects_set, key=lambda value: value.casefold()),
        "groups_by_subject": {
            subject_name: sorted(group_set, key=lambda value: value.casefold())
            for subject_name, group_set in sorted(
                groups_by_subject_sets.items(),
                key=lambda item: str(item[0]).casefold(),
            )
        },
        "lesson_catalog_by_subject": lesson_catalog_by_subject,
        "lesson_catalog_by_subject_group": lesson_catalog_by_subject_group,
    }


def load_all_schools_dataset(force_refresh = False, school_codes = None):
    configured_codes = list(get_configured_school_spreadsheets().keys())
    if school_codes:
        requested_codes = [str(code or "").strip().casefold() for code in school_codes]
        target_codes = [
            code
            for code in requested_codes
            if code and (not configured_codes or code in configured_codes)
        ]
    else:
        target_codes = configured_codes

    if not target_codes:
        target_codes = [DEFAULT_SCHOOL_CODE]

    datasets = []
    load_errors = []
    for school_code in target_codes:
        try:
            dataset = get_school_dataset(
                force_refresh=force_refresh,
                school_code=school_code,
            )
        except SheetsDataError as exc:
            load_errors.append(str(exc))
            continue
        if isinstance(dataset, dict):
            datasets.append(dataset)

    if not datasets:
        error_message = (
            load_errors[0]
            if load_errors
            else "Unable to load Google Sheets data from configured schools."
        )
        raise SheetsDataError(error_message)

    if len(datasets) == 1:
        return datasets[0]
    return _merge_datasets(datasets)


__all__ = [
    "SheetsDataError",
    "get_school_dataset",
    "load_all_schools_dataset",
]
