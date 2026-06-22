import os
import threading
import time

from shared.db import queries
from shared.academics import canonical
from shared.identity.account_service import (
    get_admin_student_profile,
    list_students_for_admin,
    list_teachers,
)
from .teacher_candidate_service import list_teacher_candidates
from web.backend.domains.complaints.service import list_complaints
from web.backend.utils.normalization import normalize_text
from .parent_service import list_parent_accounts, list_parent_children
from shared.academics.performance_summary import (
    list_subject_summaries,
)
from web.backend.domains.academics.internal_dashboard_service import build_internal_overview_dataset

from .insights_service import (
    build_admin_group_zones,
    build_admin_quick_stats,
    build_admin_school_info,
    build_admin_subject_info,
    extract_overview_student_metrics,
)
from web.backend.domains.resources.service import (
    is_resource_upload_enabled,
    list_resource_subject_names,
    list_resource_types,
    list_resources,
    normalize_subject_name,
)


_ADMIN_PAGE_CONTEXT_CACHE_LOCK = threading.Lock()
_ADMIN_PAGE_CONTEXT_CACHE = {}

def _subject_priority_key(subject_name):
    return canonical.subject_sort_key(subject_name)


def invalidate_admin_page_context_cache():
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        _ADMIN_PAGE_CONTEXT_CACHE.clear()


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
            str(admin_teacher_edit.get("category", "")).strip().casefold(),
            str(admin_teacher_edit.get("semester_stage", "")).strip(),
            str(admin_teacher_edit.get("performance_score", "")).strip(),
            str(admin_teacher_edit.get("supervised_lessons", "")).strip(),
        ]
    )


def _build_admin_page_context_cache_key(panel, school_filter, admin_teacher_edit, parent_admin_id):
    return (
        str(panel or "").strip().casefold(),
        str(school_filter or "").strip().casefold(),
        _teacher_edit_cache_key(admin_teacher_edit),
        int(parent_admin_id or 0),
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


def _get_schools_from_db():
    """Return list of (code, name) from academic_schools, ordered by display preference."""
    try:
        with queries.connect_auth_db() as conn:
            rows = conn.execute(
                "SELECT code, name FROM academic_schools ORDER BY name"
            ).fetchall()
        return [(str(r["code"]), str(r["name"])) for r in rows]
    except Exception:
        return []


def _get_groups_from_db(school_filter="all"):
    try:
        with queries.connect_auth_db() as conn:
            if school_filter and school_filter != "all":
                rows = conn.execute(
                    """
                    SELECT DISTINCT g.name AS name FROM academic_groups g
                    JOIN academic_schools s ON s.id = g.school_id
                    WHERE s.code = %s
                      AND lower(g.name) <> 'online'
                    ORDER BY g.name
                    """,
                    (school_filter,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT DISTINCT name AS name FROM academic_groups WHERE lower(name) <> 'online' ORDER BY name"
                ).fetchall()
        return [str(row["name"]) for row in rows]
    except Exception:
        return []


def _get_group_school_sets_from_db():
    """Return {group_name: set(school_codes)} from DB."""
    try:
        with queries.connect_auth_db() as conn:
            rows = conn.execute(
                """
                SELECT g.name AS group_name, s.code AS school_code FROM academic_groups g
                JOIN academic_schools s ON s.id = g.school_id
                WHERE lower(g.name) <> 'online'
                """
            ).fetchall()
        result = {}
        for row in rows:
            result.setdefault(str(row["group_name"]), set()).add(str(row["school_code"]))
        return result
    except Exception:
        return {}


def build_school_configuration():
    db_schools = _get_schools_from_db()
    school_option_catalog = {code: name for code, name in db_schools}
    # Fallback display names if DB is empty
    school_option_catalog.setdefault("school5", "School 5")
    school_option_catalog.setdefault("sehriyo", "Sehriyo")

    preferred_order = ["sehriyo", "school5"]
    db_codes = {code for code, _ in db_schools}
    ordered_school_codes = [c for c in preferred_order if c in db_codes]
    # Append any schools not in the preferred order
    for code, _ in db_schools:
        if code not in ordered_school_codes:
            ordered_school_codes.append(code)
    if not ordered_school_codes:
        ordered_school_codes = ["school5"]

    admin_school_options = [{"code": "all", "label": "All Schools"}] + [
        {"code": code, "label": school_option_catalog.get(code, code.title())}
        for code in ordered_school_codes
    ]
    available_school_codes = list(ordered_school_codes)
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




def build_admin_resource_subject_options(summary_rows, resource_rows):
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
        key=_subject_priority_key,
    )


def build_admin_page_context(
    *,
    admin_panel,
    admin_school,
    admin_teacher_edit,
    parent_admin_id=0,
    force_refresh=False,
):
    school_config = build_school_configuration()
    school_option_catalog = school_config["school_option_catalog"]
    admin_school_options = school_config["admin_school_options"]
    available_school_codes = school_config["available_school_codes"]

    panel = str(admin_panel or "overview").strip().lower()
    if panel not in {
        "overview",
        "students",
        "parents",
        "teachers",
        "resources",
        "payments",
        "complaints",
        "career_growth",
        "contact",
        "chat",
        "subjects",
        "groups",
        "schedule",
        "announcements",
        "student_dashboard",
        "student_profile",
        "student_resources",
        "student_chat",
        "student_rating",
        "student_aap",
        "student_ar",
        "student_office_hours",
        "office_hours",
        "curriculum",
        "gradebook",
    }:
        panel = "overview"

    school_filter = normalize_admin_school_filter(admin_school, admin_school_options)

    cache_key = _build_admin_page_context_cache_key(
        panel,
        school_filter,
        admin_teacher_edit,
        parent_admin_id,
    )
    if not force_refresh:
        cached_context = _get_cached_admin_page_context(cache_key)
        if cached_context is not None:
            return cached_context

    sync_errors = []
    load_error = ""

    # Groups and school mappings come from internal DB — no Sheets call needed.
    groups = _get_groups_from_db(school_filter)
    group_school_sets = _get_group_school_sets_from_db()

    admin_teachers = list_teachers()
    admin_teacher_candidates = list_teacher_candidates()
    admin_complaints = list_complaints()
    admin_parents = list_parent_accounts()
    admin_parent_children = list_parent_children(parent_admin_id)
    admin_students = list_students_for_admin(
        school_filter=school_filter if panel == "students" else "all"
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
        overview_dataset = None
        try:
            overview_dataset = build_internal_overview_dataset()
        except Exception:
            overview_dataset = None
        overview_metrics = extract_overview_student_metrics(
            summary_rows,
            school_option_catalog,
        )
        admin_school_info = build_admin_school_info(overview_metrics)
        admin_subject_info = build_admin_subject_info(
            overview_metrics,
            dataset=overview_dataset,
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
    if panel in {"overview", "resources"}:
        admin_resources = list_resources(include_inactive=False)

    if panel == "resources":
        summary_rows = list_subject_summaries("all")
        admin_resource_types = list_resource_types(include_inactive=False)
        admin_resource_active_types = list(admin_resource_types)
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
        "admin_teacher_candidates": admin_teacher_candidates,
        "admin_complaints": admin_complaints,
        "admin_parents": admin_parents,
        "admin_parent_children": admin_parent_children,
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
    should_cache_context = not force_refresh and not load_error and not sync_errors
    if should_cache_context:
        _set_cached_admin_page_context(cache_key, context)
    return context


def build_edit_student_page_context(student_row_id):
    selected_student = get_admin_student_profile(student_row_id)
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
    "invalidate_admin_page_context_cache",
    "normalize_admin_school_filter",
]
