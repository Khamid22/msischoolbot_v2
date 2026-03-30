import json
import logging
import threading
import time

from app.config.schools import get_configured_school_spreadsheets
from app.integrations.sheets_data import SheetsDataError, get_school_dataset, mark_school_dataset_dirty
from app.routes.students.services import (
    auth_service,
    dataset_service,
    lesson_catalog_service,
    normalization_service,
    subject_summary_service,
)

JOB_TYPE_GOOGLE_SHEETS_SYNC = "google_sheets_sync"
_ACTIVE_SYNC_LOCK = threading.Lock()
_ACTIVE_SYNC_KEYS = set()


def normalize_target_school_codes(target_school_codes):
    configured_map = get_configured_school_spreadsheets()
    configured_codes = list(configured_map.keys())
    if not configured_codes:
        return []

    if target_school_codes is None:
        return configured_codes

    if isinstance(target_school_codes, (list, tuple, set)):
        candidates = list(target_school_codes)
    else:
        candidates = [target_school_codes]

    resolved_codes = []
    for candidate in candidates:
        normalized = normalization_service.normalize_school_code(candidate)
        if not normalized or normalized not in configured_map:
            continue
        if normalized in resolved_codes:
            continue
        resolved_codes.append(normalized)

    if not resolved_codes:
        return configured_codes
    return resolved_codes


def _load_school_dataset(school_code = None, force_refresh = False):
    try:
        dataset = get_school_dataset(
            force_refresh=force_refresh,
            school_code=school_code,
        )
        return dataset, ""
    except SheetsDataError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def _load_all_schools_from_cache(force_refresh=False):
    _ = force_refresh
    try:
        return dataset_service.load_all_schools_dataset(force_refresh=False), ""
    except SheetsDataError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def build_google_sheets_sync_payload(target_school_codes):
    normalized_codes = normalize_target_school_codes(target_school_codes)
    return {"schools": normalized_codes}


def parse_google_sheets_sync_payload(payload_json):
    try:
        payload = json.loads(str(payload_json or "{}"))
    except (TypeError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return build_google_sheets_sync_payload(payload.get("schools"))


def run_google_sheets_sync(target_school_codes):
    normalized_codes = normalize_target_school_codes(target_school_codes)
    if not normalized_codes:
        return {
            "ok": False,
            "schools": [],
            "students_sync": {},
            "subject_summaries_sync": {"synced": False, "count": 0, "error": "No target schools configured."},
            "lesson_catalog_sync": {"synced": False, "count": 0, "error": "No target schools configured."},
            "errors": ["No target schools configured."],
        }

    mark_school_dataset_dirty(normalized_codes, clear_cached_data=False)

    students_sync_results = {}
    webhook_errors = []
    for school_code in normalized_codes:
        sync_result = auth_service.sync_students_if_needed(
            _load_school_dataset,
            school_code=school_code,
        )
        students_sync_results[school_code] = {
            "synced": bool(sync_result.get("synced", False)),
            "added": int(sync_result.get("added", 0)),
            "updated": int(sync_result.get("updated", 0)),
            "error": str(sync_result.get("error", "")).strip(),
        }
        sync_error = str(sync_result.get("error", "")).strip()
        if sync_error:
            webhook_errors.append(f"{school_code}: {sync_error}")

    summary_sync_result = subject_summary_service.sync_subject_summaries_if_needed(
        _load_all_schools_from_cache,
    )
    summary_sync_error = str(summary_sync_result.get("error", "")).strip()
    if summary_sync_error:
        webhook_errors.append(f"subject_summaries: {summary_sync_error}")

    lesson_sync_result = lesson_catalog_service.sync_lesson_catalog_if_needed(
        _load_all_schools_from_cache,
    )
    lesson_sync_error = str(lesson_sync_result.get("error", "")).strip()
    if lesson_sync_error:
        webhook_errors.append(f"lesson_catalog: {lesson_sync_error}")

    return {
        "ok": not webhook_errors,
        "schools": normalized_codes,
        "students_sync": students_sync_results,
        "subject_summaries_sync": {
            "synced": bool(summary_sync_result.get("synced", False)),
            "count": int(summary_sync_result.get("count", 0)),
            "error": summary_sync_error,
        },
        "lesson_catalog_sync": {
            "synced": bool(lesson_sync_result.get("synced", False)),
            "count": int(lesson_sync_result.get("count", 0)),
            "error": lesson_sync_error,
        },
        "errors": webhook_errors,
    }


def start_google_sheets_sync_background(target_school_codes):
    normalized_codes = normalize_target_school_codes(target_school_codes)
    if not normalized_codes:
        return {
            "started": False,
            "queued": False,
            "schools": [],
            "message": "No target schools configured.",
        }

    job_key = ",".join(sorted(normalized_codes))
    with _ACTIVE_SYNC_LOCK:
        if job_key in _ACTIVE_SYNC_KEYS:
            return {
                "started": True,
                "queued": False,
                "schools": normalized_codes,
                "message": "Matching sync is already running.",
            }
        _ACTIVE_SYNC_KEYS.add(job_key)

    # Native thread is intentional: request returns immediately while sync runs.
    # gevent monkey patch (applied in main.py) still patches socket/ssl I/O.
    def _run():
        started_at = time.time()
        logging.info("Google Sheets sync started for schools=%s", normalized_codes)
        try:
            result = run_google_sheets_sync(normalized_codes)
            elapsed_ms = int((time.time() - started_at) * 1000)
            logging.info(
                "Google Sheets sync finished for schools=%s ok=%s elapsed_ms=%s",
                normalized_codes,
                bool(result.get("ok", False)),
                elapsed_ms,
            )
        except Exception:
            logging.exception(
                "Google Sheets sync crashed for schools=%s", normalized_codes
            )
        finally:
            with _ACTIVE_SYNC_LOCK:
                _ACTIVE_SYNC_KEYS.discard(job_key)

    worker = threading.Thread(
        target=_run,
        daemon=True,
        name=f"google-sheets-sync-{job_key or 'all'}",
    )
    worker.start()
    return {
        "started": True,
        "queued": True,
        "schools": normalized_codes,
        "message": "Sync started in background.",
    }


__all__ = [
    "JOB_TYPE_GOOGLE_SHEETS_SYNC",
    "normalize_target_school_codes",
    "build_google_sheets_sync_payload",
    "parse_google_sheets_sync_payload",
    "run_google_sheets_sync",
    "start_google_sheets_sync_background",
]
