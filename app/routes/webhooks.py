import hmac
import os

from flask import Blueprint, jsonify, request

from app.background import (
    enqueue_google_sheets_sync_job,
    get_background_job_status,
    is_async_webhook_sync_enabled,
    run_google_sheets_sync,
)
from app.config.schools import get_configured_school_spreadsheets
from app.extensions import csrf
from app.integrations.sheets_data import mark_school_dataset_dirty
from app.routes.students.services import normalization_service


def register_webhook_routes(
    app,
    *,
    load_dataset,
    clear_group_cache,
):
    _ = load_dataset
    webhook_blueprint = Blueprint("webhooks", __name__)

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
            code = normalization_service.normalize_school_code(raw_value)
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

    @webhook_blueprint.get("/webhooks/google-sheets/jobs/<int:job_id>")
    @csrf.exempt
    def google_sheets_webhook_job_status(job_id):
        token_ok, token_error = _validate_webhook_token({})
        if not token_ok:
            status_code = 503 if "not configured" in token_error else 401
            return jsonify({"ok": False, "message": token_error}), status_code

        status = get_background_job_status(job_id)
        if not status:
            return jsonify({"ok": False, "message": "Job not found."}), 404

        return jsonify({"ok": True, "job": status}), 200

    @webhook_blueprint.post("/webhooks/google-sheets")
    @csrf.exempt
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

        if is_async_webhook_sync_enabled():
            job_id, queued = enqueue_google_sheets_sync_job(target_school_codes)
            if not job_id:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "message": "Failed to enqueue Google Sheets sync job.",
                        }
                    ),
                    500,
                )

            return (
                jsonify(
                    {
                        "ok": True,
                        "queued": True,
                        "job_id": int(job_id),
                        "schools": target_school_codes,
                        "status_url": f"/webhooks/google-sheets/jobs/{int(job_id)}",
                        "message": (
                            "Sync job queued."
                            if queued
                            else "Matching sync job is already pending."
                        ),
                    }
                ),
                202,
            )

        sync_result = run_google_sheets_sync(target_school_codes)
        return jsonify(sync_result), (200 if sync_result.get("ok", False) else 207)

    app.register_blueprint(webhook_blueprint)
