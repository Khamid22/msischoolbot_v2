import json
import logging
import os
import threading
import time
import uuid

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
_SYNC_STATE_BY_KEY = {}


def _sync_stale_timeout_seconds():
    raw = str(os.environ.get("GOOGLE_SHEETS_SYNC_STALE_SECONDS", "600")).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = 600
    return max(parsed, 60)


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

    try:
        from app.routes.admin.services.page_service import invalidate_admin_page_context_cache

        invalidate_admin_page_context_cache()
    except Exception:
        logging.exception("Failed to invalidate admin cache after Google Sheets sync.")

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


def start_google_sheets_sync_background(target_school_codes, queue_if_running = True):
    normalized_codes = normalize_target_school_codes(target_school_codes)
    if not normalized_codes:
        return {
            "started": False,
            "queued": False,
            "already_running": False,
            "schools": [],
            "message": "No target schools configured.",
        }

    job_key = ",".join(sorted(normalized_codes))
    stale_timeout_seconds = _sync_stale_timeout_seconds()
    worker_token = uuid.uuid4().hex
    now = time.time()
    with _ACTIVE_SYNC_LOCK:
        state = _SYNC_STATE_BY_KEY.setdefault(
            job_key,
            {
                "running": False,
                "rerun_requested": False,
                "started_at": 0.0,
                "worker_token": "",
            },
        )
        if bool(state.get("running", False)):
            started_at = float(state.get("started_at", 0.0) or 0.0)
            if started_at > 0 and (now - started_at) >= stale_timeout_seconds:
                logging.warning(
                    "Google Sheets sync state reset as stale for schools=%s age_s=%s timeout_s=%s",
                    normalized_codes,
                    int(now - started_at),
                    stale_timeout_seconds,
                )
                state["running"] = False
                state["rerun_requested"] = False
                state["started_at"] = 0.0
                state["worker_token"] = ""

        if bool(state.get("running", False)):
            if queue_if_running:
                state["rerun_requested"] = True
                return {
                    "started": True,
                    "queued": True,
                    "already_running": True,
                    "schools": normalized_codes,
                    "message": "Matching sync is already running; rerun queued.",
                }
            return {
                "started": True,
                "queued": False,
                "already_running": True,
                "schools": normalized_codes,
                "message": "Matching sync is already running.",
            }
        state["running"] = True
        state["rerun_requested"] = False
        state["started_at"] = now
        state["worker_token"] = worker_token

    def _run(current_worker_token):
        run_index = 0
        while True:
            run_index += 1
            started_at = time.time()
            logging.info(
                "Google Sheets sync started for schools=%s run=%s",
                normalized_codes,
                run_index,
            )
            try:
                result = run_google_sheets_sync(normalized_codes)
                elapsed_ms = int((time.time() - started_at) * 1000)
                logging.info(
                    "Google Sheets sync finished for schools=%s run=%s ok=%s elapsed_ms=%s errors=%s",
                    normalized_codes,
                    run_index,
                    bool(result.get("ok", False)),
                    elapsed_ms,
                    result.get("errors", []),
                )
            except Exception:
                logging.exception(
                    "Google Sheets sync crashed for schools=%s run=%s",
                    normalized_codes,
                    run_index,
                )

            with _ACTIVE_SYNC_LOCK:
                state = _SYNC_STATE_BY_KEY.get(job_key, {})
                if str(state.get("worker_token", "")) != str(current_worker_token):
                    return
                rerun_requested = bool(state.get("rerun_requested", False))
                if rerun_requested:
                    state["rerun_requested"] = False
                    state["started_at"] = time.time()
                else:
                    state["running"] = False
                    state["started_at"] = 0.0
                    state["worker_token"] = ""
                    _SYNC_STATE_BY_KEY.pop(job_key, None)

            if not rerun_requested:
                break

            logging.info(
                "Google Sheets sync rerun scheduled for schools=%s next_run=%s",
                normalized_codes,
                run_index + 1,
            )

    # Always run in a native daemon thread. Sync work includes Python-heavy
    # parsing and DB writes; running it in gevent greenlets can introduce
    # latency spikes for normal HTTP requests.
    worker = threading.Thread(
        target=_run,
        args=(worker_token,),
        daemon=True,
        name=f"google-sheets-sync-{job_key or 'all'}",
    )
    worker.start()
    return {
        "started": True,
        "queued": True,
        "already_running": False,
        "schools": normalized_codes,
        "runner": "thread",
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
