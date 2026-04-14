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
        """Resolve target school codes from the webhook request.

        Priority: JSON body → query string → form data.
        Accepts both school codes ("school5", "sehriyo") and spreadsheet IDs.
        Falls back to all configured schools when none are specified.
        """
        configured_map = get_configured_school_spreadsheets()
        spreadsheet_to_school = {
            str(sid).strip(): code
            for code, sid in configured_map.items()
            if str(sid).strip()
        }

        resolved: list[str] = []

        def _add(raw_value):
            code = normalization_service.normalize_school_code(raw_value)
            if code and code in configured_map and code not in resolved:
                resolved.append(code)

        def _add_spreadsheet_id(raw_id):
            school = spreadsheet_to_school.get(str(raw_id).strip())
            if school and school not in resolved:
                resolved.append(school)

        # 1. JSON body (most explicit — checked first)
        if isinstance(payload, dict):
            for raw in _split_csv(payload.get("school")) + _split_csv(payload.get("schools")):
                _add(raw)
            for raw in _split_csv(payload.get("spreadsheet_id")) + _split_csv(payload.get("spreadsheet_ids")):
                _add_spreadsheet_id(raw)
            if isinstance(payload.get("schools"), list):
                for raw in payload["schools"]:
                    _add(raw)

        # 2. Query string
        for raw in _split_csv(request.args.get("school", "")):
            _add(raw)

        # 3. Form data
        for raw in _split_csv(request.form.get("school", "")):
            _add(raw)

        return resolved or list(configured_map.keys())

    def _validate_webhook_token(payload):
        """Validate the bearer token in the request.

        Returns (ok: bool, error_message: str, status_code: int).
        """
        expected_token = str(os.environ.get("GOOGLE_SHEETS_WEBHOOK_TOKEN", "")).strip()
        if not expected_token:
            return False, "GOOGLE_SHEETS_WEBHOOK_TOKEN is not configured.", 503

        provided_token = (
            str(request.headers.get("X-Webhook-Token", "")).strip()
            or str(request.args.get("token", "")).strip()
            or str(request.form.get("token", "")).strip()
            or (str(payload.get("token", "")).strip() if isinstance(payload, dict) else "")
        )

        if not provided_token:
            return False, "Webhook token is missing.", 401
        if not hmac.compare_digest(provided_token, expected_token):
            return False, "Webhook token is invalid.", 401
        return True, "", 200

    @webhook_blueprint.post("/webhooks/google-sheets")
    @csrf.exempt
    def google_sheets_webhook():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}

        token_ok, token_error, token_status = _validate_webhook_token(payload)
        if not token_ok:
            logging.warning(
                "Google Sheets webhook rejected: %s (remote_addr=%s)",
                token_error,
                request.remote_addr,
            )
            return jsonify({"ok": False, "message": token_error}), token_status

        target_school_codes = _extract_school_codes(payload)
        if not target_school_codes:
            return (
                jsonify({"ok": False, "message": "Unable to resolve target schools for this webhook event."}),
                400,
            )

        logging.info("Google Sheets webhook accepted for schools=%s", target_school_codes)
        clear_group_cache()
        mark_school_dataset_dirty(target_school_codes, clear_cached_data=False)

        sync_state = start_google_sheets_sync_background(target_school_codes)
        logging.info("Google Sheets background sync state=%s", sync_state)
        started = bool(sync_state.get("started", False))
        return jsonify({"ok": started, **sync_state}), (202 if started else 503)

    app.register_blueprint(webhook_blueprint)
