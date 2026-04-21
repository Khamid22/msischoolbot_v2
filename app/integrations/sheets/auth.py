from __future__ import annotations

import json
import os
import threading
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .constants import SCOPES


class SheetsDataError(RuntimeError):
    """Raised when Google Sheets data cannot be loaded or parsed."""


_SERVICE_LOCAL = threading.local()


def is_retryable_google_error(exc):
    if isinstance(exc, HttpError):
        status_code = int(getattr(getattr(exc, "resp", None), "status", 0) or 0)
        return status_code in {429, 500, 502, 503, 504}
    return False


def extract_google_error_details(exc):
    if isinstance(exc, HttpError):
        status_code = int(getattr(getattr(exc, "resp", None), "status", 0) or 0)
        message = ""
        content = getattr(exc, "content", b"")
        if content:
            try:
                payload = json.loads(content.decode("utf-8", errors="ignore"))
                message = str(payload.get("error", {}).get("message", "")).strip()
            except Exception:
                message = ""
        if not message:
            message = str(exc).strip()
        if status_code:
            return f"HTTP {status_code}: {message}"
        return message
    return str(exc).strip() or exc.__class__.__name__


def execute_google_request_with_retries(request_factory):
    last_exc = None
    for attempt in range(1, 4):
        try:
            return request_factory().execute()
        except Exception as exc:
            last_exc = exc
            if attempt >= 3 or not is_retryable_google_error(exc):
                break
            time.sleep(0.6 * attempt)
    raise last_exc


def get_sheets_service():
    service = getattr(_SERVICE_LOCAL, "service", None)
    if service is not None:
        return service

    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_source = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    credentials = None
    if raw_json:
        try:
            service_account_info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise SheetsDataError("GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON.") from exc
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )
    elif credentials_source:
        if credentials_source.startswith("{"):
            try:
                service_account_info = json.loads(credentials_source)
            except json.JSONDecodeError as exc:
                raise SheetsDataError(
                    "GOOGLE_APPLICATION_CREDENTIALS looks like JSON but is invalid."
                ) from exc
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES,
            )
        else:
            try:
                credentials = Credentials.from_service_account_file(
                    credentials_source,
                    scopes=SCOPES,
                )
            except Exception as exc:
                raise SheetsDataError(
                    "Failed to load GOOGLE_APPLICATION_CREDENTIALS file. "
                    "Use a valid in-container path, or set GOOGLE_SERVICE_ACCOUNT_JSON."
                ) from exc
    else:
        raise SheetsDataError(
            "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS."
        )

    try:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        raise SheetsDataError("Failed to initialize Google Sheets API client.") from exc
    _SERVICE_LOCAL.service = service
    return service
