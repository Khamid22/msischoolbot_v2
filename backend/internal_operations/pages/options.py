"""School and resource selector builders for the system-admin workspace."""

from backend.modules.academics.resources.service import (
    list_resource_subject_names,
    normalize_subject_name,
)
from backend.modules.organization import canonical
from backend.modules.organization.canonical import normalize_text
from backend.modules.reporting.service import list_active_schools


def build_school_configuration():
    try:
        database_schools = list_active_schools()
    except Exception:
        database_schools = []

    school_names = {code: name for code, name in database_schools}
    school_names.setdefault("school5", "School 5")
    school_names.setdefault("sehriyo", "Sehriyo")

    preferred_order = ["sehriyo", "school5"]
    database_codes = {code for code, _name in database_schools}
    ordered_codes = [code for code in preferred_order if code in database_codes]
    ordered_codes.extend(
        code for code, _name in database_schools if code not in ordered_codes
    )
    if not ordered_codes:
        ordered_codes = ["school5"]

    return {
        "school_option_catalog": school_names,
        "admin_school_options": [{"code": "all", "label": "All Schools"}]
        + [
            {"code": code, "label": school_names.get(code, code.title())}
            for code in ordered_codes
        ],
        "available_school_codes": list(ordered_codes),
    }


def normalize_admin_school_filter(value, admin_school_options):
    normalized = str(value or "all").strip().casefold()
    allowed_codes = {option["code"] for option in admin_school_options}
    return normalized if normalized in allowed_codes else "all"


def build_resource_subject_options(summary_rows, resource_rows):
    subject_map = {}
    for rows in (summary_rows, resource_rows):
        if not isinstance(rows, list):
            continue
        for row in rows:
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

    return sorted(subject_map.values(), key=canonical.subject_sort_key)


__all__ = [
    "build_resource_subject_options",
    "build_school_configuration",
    "normalize_admin_school_filter",
]
