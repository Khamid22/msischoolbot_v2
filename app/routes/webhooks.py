import hmac
import logging
import os

from flask import Blueprint, jsonify, request

from app.background import start_google_sheets_sync_background
from app.config.schools import get_configured_school_spreadsheets
from app.extensions import csrf
from app.integrations.sheets_data import mark_school_dataset_dirty
from app.routes.students.services import normalization_service


def register_webhook_routes(
    app,
    *,
    clear_group_cache,
):
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

    @webhook_blueprint.post("/webhooks/google-sheets")
    @csrf.exempt
    def google_sheets_webhook():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}

        token_ok, token_error = _validate_webhook_token(payload)
        if not token_ok:
            logging.warning(
                "Google Sheets webhook rejected: %s (remote_addr=%s)",
                token_error,
                request.remote_addr,
            )
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

        logging.info(
            "Google Sheets webhook accepted for schools=%s",
            target_school_codes,
        )
        clear_group_cache()
        mark_school_dataset_dirty(target_school_codes, clear_cached_data=False)

        sync_state = start_google_sheets_sync_background(target_school_codes)
        logging.info("Google Sheets background sync state=%s", sync_state)
        started = bool(sync_state.get("started", False))
        return jsonify({"ok": started, **sync_state}), (202 if started else 503)

    app.register_blueprint(webhook_blueprint)
