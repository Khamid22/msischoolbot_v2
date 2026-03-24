import hmac
import os

from flask import jsonify, request

try:
    from ..config.schools import get_configured_school_spreadsheets
except ImportError:
    from app.config.schools import get_configured_school_spreadsheets

try:
    from ..integrations.sheets_data import mark_school_dataset_dirty
except ImportError:
    from app.integrations.sheets_data import mark_school_dataset_dirty

try:
    from ..services.auth_service import sync_students_if_needed
except ImportError:
    from app.services.auth_service import sync_students_if_needed

try:
    from ..services.dataset_service import SheetsDataError, load_all_schools_dataset
except ImportError:
    from app.services.dataset_service import SheetsDataError, load_all_schools_dataset

try:
    from ..services.lesson_catalog_service import sync_lesson_catalog_if_needed
except ImportError:
    from app.services.lesson_catalog_service import sync_lesson_catalog_if_needed

try:
    from ..services.subject_summary_service import sync_subject_summaries_if_needed
except ImportError:
    from app.services.subject_summary_service import sync_subject_summaries_if_needed


def register_webhook_routes(
    app,
    *,
    load_dataset,
    clear_group_cache,
):
    def _normalize_school_code(value):
        normalized = str(value or "").strip().casefold()
        if normalized in {"school_5", "school-5", "school 5", "school5"}:
            return "school5"
        if normalized in {"sehriyo", "sehriyo school"}:
            return "sehriyo"
        return normalized

    def _split_csv(value):
        text = str(value or "").strip()
        if not text:
            return []
        return [part.strip() for part in text.split(",") if part.strip()]

    def _extract_school_codes(payload):
        configured_map = get_configured_school_spreadsheets()
        spreadsheet_to_school = {
            str(spreadsheet_id).strip(): school_code
            for school_code, spreadsheet_id in configured_map.items()
            if str(spreadsheet_id).strip()
        }

        resolved_codes = []

        def _add_school_code(raw_value):
            code = _normalize_school_code(raw_value)
            if code and code in configured_map and code not in resolved_codes:
                resolved_codes.append(code)

        school_candidates = []
        school_candidates.extend(_split_csv(request.args.get("school", "")))
        school_candidates.extend(_split_csv(request.args.get("schools", "")))
        school_candidates.extend(_split_csv(request.form.get("school", "")))
        school_candidates.extend(_split_csv(request.form.get("schools", "")))

        if isinstance(payload, dict):
            school_candidates.extend(_split_csv(payload.get("school")))
            school_candidates.extend(_split_csv(payload.get("school_code")))
            school_candidates.extend(_split_csv(payload.get("schoolKey")))
            school_candidates.extend(_split_csv(payload.get("schools")))

            raw_schools = payload.get("schools")
            if isinstance(raw_schools, list):
                school_candidates.extend(raw_schools)

            spreadsheet_id_candidates = []
            spreadsheet_id_candidates.extend(_split_csv(payload.get("spreadsheet_id")))
            spreadsheet_id_candidates.extend(_split_csv(payload.get("spreadsheetId")))
            spreadsheet_id_candidates.extend(_split_csv(payload.get("spreadsheet_ids")))
            raw_spreadsheet_ids = payload.get("spreadsheet_ids")
            if isinstance(raw_spreadsheet_ids, list):
                spreadsheet_id_candidates.extend(raw_spreadsheet_ids)

            for spreadsheet_id in spreadsheet_id_candidates:
                resolved_school = spreadsheet_to_school.get(str(spreadsheet_id).strip())
                if resolved_school and resolved_school not in resolved_codes:
                    resolved_codes.append(resolved_school)

        for candidate in school_candidates:
            _add_school_code(candidate)

        if not resolved_codes:
            resolved_codes = list(configured_map.keys())

        return resolved_codes

    def _validate_webhook_token(payload):
        expected_token = str(
            os.environ.get("GOOGLE_SHEETS_WEBHOOK_TOKEN", "")
        ).strip()
        if not expected_token:
            return False, "GOOGLE_SHEETS_WEBHOOK_TOKEN is not configured."

        provided_token = str(request.headers.get("X-Webhook-Token", "")).strip()
        if not provided_token:
            provided_token = str(request.args.get("token", "")).strip()
        if not provided_token:
            provided_token = str(request.form.get("token", "")).strip()
        if not provided_token and isinstance(payload, dict):
            provided_token = str(payload.get("token", "")).strip()

        if not provided_token:
            return False, "Webhook token is missing."
        if not hmac.compare_digest(provided_token, expected_token):
            return False, "Webhook token is invalid."
        return True, ""

    def _load_all_schools_from_cache(force_refresh = False):
        # Keep existing in-memory data for schools that were not changed by this webhook.
        try:
            return load_all_schools_dataset(force_refresh=False), ""
        except SheetsDataError as exc:
            return None, str(exc)
        except Exception as exc:
            return None, str(exc)

    @app.post("/webhooks/google-sheets")
    def google_sheets_webhook():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}

        token_ok, token_error = _validate_webhook_token(payload)
        if not token_ok:
            status_code = 503 if "not configured" in token_error else 401
            return jsonify({"ok": False, "message": token_error}), status_code

        target_school_codes = _extract_school_codes(payload)
        if not target_school_codes:
            return (
                jsonify(
                    {
                        "ok": False,
                        "message": "Unable to resolve target schools for this webhook event.",
                    }
                ),
                400,
            )

        clear_group_cache()
        mark_school_dataset_dirty(target_school_codes, clear_cached_data=False)

        students_sync_results = {}
        webhook_errors = []
        for school_code in target_school_codes:
            sync_result = sync_students_if_needed(
                load_dataset,
                school_code=school_code,
                force_refresh=True,
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

        summary_sync_result = sync_subject_summaries_if_needed(
            _load_all_schools_from_cache,
            force_refresh=True,
        )
        summary_sync_error = str(summary_sync_result.get("error", "")).strip()
        if summary_sync_error:
            webhook_errors.append(f"subject_summaries: {summary_sync_error}")

        lesson_sync_result = sync_lesson_catalog_if_needed(
            _load_all_schools_from_cache,
            force_refresh=True,
        )
        lesson_sync_error = str(lesson_sync_result.get("error", "")).strip()
        if lesson_sync_error:
            webhook_errors.append(f"lesson_catalog: {lesson_sync_error}")

        return (
            jsonify(
                {
                    "ok": not webhook_errors,
                    "schools": target_school_codes,
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
            ),
            200 if not webhook_errors else 207,
        )
