"""View-model builders for admin pages."""

import os
import threading
import time

from app.config.schools import get_configured_school_spreadsheets
from .auth_service import (
    get_admin_student_profile,
    list_students_for_admin,
    list_teachers,
)
from .normalization_service import normalize_text
from .subject_summary_service import (
    list_subject_summaries,
)

from .insights_service import (
    build_admin_group_zones,
    build_admin_quick_stats,
    build_admin_school_info,
    build_admin_subject_info,
    extract_overview_student_metrics,
)
from .resources_service import (
    is_resource_upload_enabled,
    list_resource_subject_names,
    list_resource_types,
    list_resources,
    normalize_subject_name,
)


_ADMIN_PAGE_CONTEXT_CACHE_LOCK = threading.Lock()
_ADMIN_PAGE_CONTEXT_CACHE = {}


def _admin_page_context_cache_ttl_seconds():
    raw_value = str(os.environ.get("ADMIN_PAGE_CONTEXT_CACHE_SECONDS", "15") or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 15
    return max(parsed, 0)


def _teacher_edit_cache_key(admin_teacher_edit):
    if not isinstance(admin_teacher_edit, dict):
        return ""

    return "|".join(
        [
            str(admin_teacher_edit.get("id", "")).strip(),
            str(admin_teacher_edit.get("full_name", "")).strip().casefold(),
            str(admin_teacher_edit.get("assigned_group", "")).strip().casefold(),
            str(admin_teacher_edit.get("pay_rate", "")).strip(),
        ]
    )


def _build_admin_page_context_cache_key(panel, school_filter, admin_teacher_edit):
    return (
        str(panel or "").strip().casefold(),
        str(school_filter or "").strip().casefold(),
        _teacher_edit_cache_key(admin_teacher_edit),
    )


def _get_cached_admin_page_context(cache_key):
    now = time.time()
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        cached_entry = _ADMIN_PAGE_CONTEXT_CACHE.get(cache_key)
        if cached_entry and now < float(cached_entry.get("expires_at", 0)):
            return cached_entry.get("context")
    return None


def _set_cached_admin_page_context(cache_key, context):
    ttl_seconds = _admin_page_context_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return

    now = time.time()
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        _ADMIN_PAGE_CONTEXT_CACHE[cache_key] = {
            "context": context,
            "expires_at": now + ttl_seconds,
        }
        expired_keys = [
            key
            for key, entry in _ADMIN_PAGE_CONTEXT_CACHE.items()
            if float(entry.get("expires_at", 0)) <= now
        ]
        for key in expired_keys:
            _ADMIN_PAGE_CONTEXT_CACHE.pop(key, None)
        if len(_ADMIN_PAGE_CONTEXT_CACHE) > 128:
            ordered_entries = sorted(
                _ADMIN_PAGE_CONTEXT_CACHE.items(),
                key=lambda item: float(item[1].get("expires_at", 0)),
            )
            for key, _entry in ordered_entries[: len(_ADMIN_PAGE_CONTEXT_CACHE) - 128]:
                _ADMIN_PAGE_CONTEXT_CACHE.pop(key, None)


def build_school_configuration():
    configured_school_codes = set(get_configured_school_spreadsheets().keys())
    school_option_catalog = {
        "school5": "School 5",
        "sehriyo": "Sehriyo",
    }
    ordered_school_codes = [
        code
        for code in ("school5", "sehriyo")
        if code in configured_school_codes
    ]
    if not ordered_school_codes:
        ordered_school_codes = ["school5"]

    admin_school_options = [{"code": "all", "label": "All Schools"}] + [
        {"code": code, "label": school_option_catalog.get(code, code.title())}
        for code in ordered_school_codes
    ]
    available_school_codes = [
        option["code"]
        for option in admin_school_options
        if option["code"] != "all"
    ]
    return {
        "school_option_catalog": school_option_catalog,
        "admin_school_options": admin_school_options,
        "available_school_codes": available_school_codes,
    }


def normalize_admin_school_filter(value, admin_school_options):
    normalized = str(value or "all").strip().casefold()
    allowed_codes = {option["code"] for option in admin_school_options}
    if normalized in allowed_codes:
        return normalized
    return "all"


def _merge_admin_datasets(datasets):
    merged_students = []
    merged_dashboards_by_id = {}
    groups_set = set()
    subjects_set = set()
    groups_by_subject_sets = {}

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
                target_groups = groups_by_subject_sets.setdefault(
                    normalized_subject,
                    set(),
                )
                if isinstance(groups, list):
                    for group_name in groups:
                        normalized_group = str(group_name or "").strip()
                        if normalized_group:
                            target_groups.add(normalized_group)

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
    }


def _load_admin_dataset_for_filter(
    school_filter,
    *,
    available_school_codes,
    load_dataset,
    force_refresh=False,
):
    selected_school_codes = (
        available_school_codes
        if school_filter == "all"
        else [school_filter]
    )
    loaded_datasets = []
    first_load_error = ""

    for school_code in selected_school_codes:
        try:
            dataset, load_error = load_dataset(
                school_code=school_code,
                force_refresh=force_refresh,
            )
        except TypeError:
            dataset, load_error = load_dataset()

        normalized_load_error = str(load_error or "").strip()
        if normalized_load_error and not first_load_error:
            first_load_error = normalized_load_error

        if dataset:
            loaded_datasets.append(dataset)

    if not loaded_datasets:
        return None, first_load_error or "Unable to load Google Sheets data."

    if len(loaded_datasets) == 1:
        return loaded_datasets[0], first_load_error

    return _merge_admin_datasets(loaded_datasets), first_load_error


def build_admin_resource_subject_options(summary_rows, resource_rows):
    subject_priority = {
        "math": 0,
        "english": 1,
        "chemistry": 2,
        "biology": 3,
        "physics": 4,
    }

    subject_map = {}
    if isinstance(summary_rows, list):
        for row in summary_rows:
            if not isinstance(row, dict):
                continue
            subject_name = normalize_subject_name(row.get("subject_name", ""))
            subject_key = normalize_text(subject_name)
            if subject_name and subject_key and subject_key not in subject_map:
                subject_map[subject_key] = subject_name

    if isinstance(resource_rows, list):
        for row in resource_rows:
            if not isinstance(row, dict):
                continue
            subject_name = normalize_subject_name(row.get("subject_name", ""))
            subject_key = normalize_text(subject_name)
            if subject_name and subject_key and subject_key not in subject_map:
                subject_map[subject_key] = subject_name

    for subject_name in list_resource_subject_names():
        normalized_name = normalize_subject_name(subject_name)
        subject_key = normalize_text(normalized_name)
        if normalized_name and subject_key and subject_key not in subject_map:
            subject_map[subject_key] = normalized_name

    return sorted(
        subject_map.values(),
        key=lambda value: (
            subject_priority.get(normalize_text(value), 999),
            normalize_text(value),
        ),
    )


def build_admin_page_context(
    *,
    admin_panel,
    admin_school,
    admin_teacher_edit,
    load_dataset,
    force_refresh=False,
):
    school_config = build_school_configuration()
    school_option_catalog = school_config["school_option_catalog"]
    admin_school_options = school_config["admin_school_options"]
    available_school_codes = school_config["available_school_codes"]

    panel = str(admin_panel or "overview").strip().lower()
    if panel not in {"overview", "students", "teachers", "resources"}:
        panel = "overview"

    school_filter = normalize_admin_school_filter(admin_school, admin_school_options)
    dataset_scope = "all" if panel in {"overview", "teachers"} else school_filter

    cache_key = _build_admin_page_context_cache_key(
        panel,
        school_filter,
        admin_teacher_edit,
    )
    if not force_refresh:
        cached_context = _get_cached_admin_page_context(cache_key)
        if cached_context is not None:
            return cached_context

    sync_errors = []
    dataset = None
    load_error = ""
    groups = []
    if panel in {"overview", "teachers"}:
        dataset, load_error = _load_admin_dataset_for_filter(
            dataset_scope,
            available_school_codes=available_school_codes,
            load_dataset=load_dataset,
            force_refresh=force_refresh,
        )
        groups = dataset["groups"] if dataset else []

    admin_teachers = list_teachers()
    admin_students = list_students_for_admin(
        school_filter=school_filter if panel == "students" else "all"
    )

    group_school_sets = {}
    dataset_students = dataset.get("students", []) if isinstance(dataset, dict) else []
    if isinstance(dataset_students, list):
        for student_row in dataset_students:
            if not isinstance(student_row, dict):
                continue
            group_name = str(student_row.get("group", "")).strip()
            if not group_name:
                continue
            school_code = str(
                student_row.get("schoolCode")
                or student_row.get("school_code")
                or student_row.get("schoolKey")
                or student_row.get("school_key")
                or ""
            ).strip().casefold()
            if school_code not in available_school_codes:
                continue
            group_school_sets.setdefault(group_name, set()).add(school_code)

    if not group_school_sets:
        fallback_school_code = (
            school_filter
            if school_filter in available_school_codes
            else (available_school_codes[0] if len(available_school_codes) == 1 else "")
        )
        if fallback_school_code:
            for group_name in groups:
                normalized_group = str(group_name or "").strip()
                if normalized_group:
                    group_school_sets.setdefault(normalized_group, set()).add(
                        fallback_school_code
                    )

    admin_group_options = []
    for group_name in groups:
        normalized_group = str(group_name or "").strip()
        if not normalized_group:
            continue
        school_codes = sorted(
            group_school_sets.get(normalized_group, set()),
            key=lambda value: value.casefold(),
        )
        if not school_codes and school_filter in available_school_codes:
            school_codes = [school_filter]
        elif not school_codes and len(available_school_codes) == 1:
            school_codes = [available_school_codes[0]]
        admin_group_options.append(
            {
                "name": normalized_group,
                "school_codes": school_codes,
            }
        )

    teacher_name_to_schools = {}
    for teacher_row in admin_teachers:
        teacher_name = str(teacher_row.get("full_name", "")).strip()
        if not teacher_name:
            continue
        teacher_group = str(teacher_row.get("assigned_group", "")).strip()
        teacher_school_codes = group_school_sets.get(teacher_group, set())
        school_set = teacher_name_to_schools.setdefault(teacher_name, set())
        school_set.update(teacher_school_codes)

    admin_teacher_options = []
    for teacher_name in sorted(teacher_name_to_schools, key=lambda value: value.casefold()):
        school_codes = sorted(
            teacher_name_to_schools.get(teacher_name, set()),
            key=lambda value: value.casefold(),
        )
        if not school_codes and school_filter in available_school_codes:
            school_codes = [school_filter]
        elif not school_codes and len(available_school_codes) == 1:
            school_codes = [available_school_codes[0]]
        admin_teacher_options.append(
            {
                "name": teacher_name,
                "school_codes": school_codes,
            }
        )

    admin_teacher_edit_school = ""
    if isinstance(admin_teacher_edit, dict):
        edit_group_name = str(admin_teacher_edit.get("assigned_group", "")).strip()
        edit_group_schools = sorted(
            group_school_sets.get(edit_group_name, set()),
            key=lambda value: value.casefold(),
        )
        if edit_group_schools:
            admin_teacher_edit_school = edit_group_schools[0]
        elif school_filter in available_school_codes:
            admin_teacher_edit_school = school_filter
        elif available_school_codes:
            admin_teacher_edit_school = available_school_codes[0]

    admin_quick_stats = {
        "total_students": 0,
        "total_schools": 0,
        "total_teachers": 0,
        "total_subjects": 0,
        "school_counts": [],
    }
    admin_school_info = []
    admin_subject_info = []
    admin_group_zones = {
        "green": [],
        "yellow": [],
        "red": [],
    }
    admin_resource_types = []
    admin_resource_active_types = []
    admin_resources = []
    admin_resource_subject_options = []
    admin_resource_upload_enabled = False

    if panel == "overview":
        summary_rows = list_subject_summaries("all")
        overview_metrics = extract_overview_student_metrics(
            summary_rows,
            school_option_catalog,
        )
        admin_school_info = build_admin_school_info(overview_metrics)
        admin_subject_info = build_admin_subject_info(
            overview_metrics,
            dataset=dataset,
            school_option_catalog=school_option_catalog,
        )
        admin_group_zones = build_admin_group_zones(overview_metrics)
        total_subjects = len(
            {
                str(item.get("subject", "")).strip().casefold()
                for item in overview_metrics
                if str(item.get("subject", "")).strip()
            }
        )
        admin_quick_stats = build_admin_quick_stats(
            admin_school_info,
            admin_teachers,
            total_subjects,
        )
    elif panel == "resources":
        summary_rows = list_subject_summaries("all")
        admin_resource_types = list_resource_types(include_inactive=True)
        admin_resource_active_types = [
            row for row in admin_resource_types if bool(row.get("is_active"))
        ]
        admin_resources = list_resources(include_inactive=True)
        admin_resource_subject_options = build_admin_resource_subject_options(
            summary_rows,
            admin_resources,
        )
        admin_resource_upload_enabled = is_resource_upload_enabled()

    context = {
        "panel": panel,
        "school_filter": school_filter,
        "sync_errors": sync_errors,
        "load_error": load_error,
        "admin_students": admin_students,
        "admin_teachers": admin_teachers,
        "admin_teacher_options": admin_teacher_options,
        "admin_group_options": admin_group_options,
        "admin_teacher_edit": admin_teacher_edit,
        "admin_teacher_edit_school": admin_teacher_edit_school,
        "admin_school_options": admin_school_options,
        "admin_quick_stats": admin_quick_stats,
        "admin_school_info": admin_school_info,
        "admin_subject_info": admin_subject_info,
        "admin_group_zones": admin_group_zones,
        "admin_resource_types": admin_resource_types,
        "admin_resource_active_types": admin_resource_active_types,
        "admin_resources": admin_resources,
        "admin_resource_subject_options": admin_resource_subject_options,
        "admin_resource_upload_enabled": admin_resource_upload_enabled,
    }
    if not force_refresh:
        _set_cached_admin_page_context(cache_key, context)
    return context


def build_edit_student_page_context(student_row_id, load_dataset):
    selected_student = get_admin_student_profile(student_row_id, load_dataset)
    if not selected_student:
        return None

    teacher_rows = list_teachers()
    teacher_name_options = sorted(
        {
            str(row.get("full_name", "")).strip()
            for row in teacher_rows
            if str(row.get("full_name", "")).strip()
        },
        key=lambda value: value.casefold(),
    )

    return {
        "student": selected_student,
        "teacher_name_options": teacher_name_options,
    }


__all__ = [
    "build_admin_page_context",
    "build_edit_student_page_context",
    "build_school_configuration",
    "normalize_admin_school_filter",
]
