"""View-model builders for student landing/search pages."""

import os
import threading
import time

from web.backend.utils.normalization import normalize_school_code

_STUDENT_PANEL_CACHE_LOCK = threading.Lock()
_STUDENT_PANEL_CACHE = {}


def _student_panel_cache_ttl_seconds():
    raw_value = str(os.environ.get("STUDENT_PANEL_CONTEXT_CACHE_SECONDS", "30") or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 30
    return max(parsed, 0)


def _student_panel_cache_key(dataset, normalized_school_code):
    return (int(id(dataset)), str(normalized_school_code or "").strip().casefold())


def _get_cached_student_panel_payload(cache_key):
    now = time.time()
    with _STUDENT_PANEL_CACHE_LOCK:
        cached_entry = _STUDENT_PANEL_CACHE.get(cache_key)
        if cached_entry and now < float(cached_entry.get("expires_at", 0)):
            return cached_entry.get("payload")
    return None


def _set_cached_student_panel_payload(cache_key, payload):
    ttl_seconds = _student_panel_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return

    now = time.time()
    with _STUDENT_PANEL_CACHE_LOCK:
        _STUDENT_PANEL_CACHE[cache_key] = {
            "payload": payload,
            "expires_at": now + ttl_seconds,
        }
        expired_keys = [
            key
            for key, entry in _STUDENT_PANEL_CACHE.items()
            if float(entry.get("expires_at", 0)) <= now
        ]
        for key in expired_keys:
            _STUDENT_PANEL_CACHE.pop(key, None)
        if len(_STUDENT_PANEL_CACHE) > 64:
            ordered_entries = sorted(
                _STUDENT_PANEL_CACHE.items(),
                key=lambda item: float(item[1].get("expires_at", 0)),
            )
            for key, _entry in ordered_entries[: len(_STUDENT_PANEL_CACHE) - 64]:
                _STUDENT_PANEL_CACHE.pop(key, None)


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

    groups = []
    groups_by_subject = {}
    subjects = []
    students_by_subject_group = {}

    if dataset:
        seed_group_cache_from_dataset(dataset)
        cache_key = _student_panel_cache_key(dataset, normalized_school_code)
        cached_payload = _get_cached_student_panel_payload(cache_key)
        if cached_payload is None:
            cached_payload = {
                "groups": dataset.get("groups", []),
                "groups_by_subject": dataset.get("groups_by_subject", {}),
                "subjects": dataset.get("subjects", []),
                "students_by_subject_group": build_students_by_subject_group(
                    dataset.get("students", [])
                ),
            }
            _set_cached_student_panel_payload(cache_key, cached_payload)

        groups = cached_payload["groups"]
        groups_by_subject = cached_payload["groups_by_subject"]
        subjects = cached_payload["subjects"]
        students_by_subject_group = cached_payload["students_by_subject_group"]

    return {
        "groups": groups,
        "groups_by_subject": groups_by_subject,
        "subjects": subjects,
        "students_by_subject_group": students_by_subject_group,
        "load_error": load_error,
        "form_data": form_data,
    }


__all__ = ["build_student_panel_context"]
