"""School-specific configuration for external data sources."""

import os

DEFAULT_SCHOOL_CODE = "school5"

SCHOOL_SPREADSHEET_ENV_KEYS = {
    "school5": "SCHOOL5_SPREAD_SHEETS",
    "sehriyo": "SEHRIYO_SPREAD_SHEETS",
}


def _normalize_school_code(school_code):
    normalized = str(school_code or DEFAULT_SCHOOL_CODE).strip().casefold()
    if normalized in {"school_5", "school-5", "school 5", "school5"}:
        return "school5"
    if normalized in {"sehriyo", "sehriyo school"}:
        return "sehriyo"
    return normalized or DEFAULT_SCHOOL_CODE


def get_school_spreadsheet_id(school_code = DEFAULT_SCHOOL_CODE):
    normalized = _normalize_school_code(school_code)
    env_key = SCHOOL_SPREADSHEET_ENV_KEYS.get(normalized)
    spreadsheet_id = os.environ.get(str(env_key or ""), "").strip() if env_key else ""

    if not spreadsheet_id and normalized == "school5":
        spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()

    return spreadsheet_id


def get_configured_school_spreadsheets():
    configured = {}
    for school_code in SCHOOL_SPREADSHEET_ENV_KEYS:
        spreadsheet_id = get_school_spreadsheet_id(school_code)
        if spreadsheet_id:
            configured[school_code] = spreadsheet_id
    return configured


__all__ = [
    "DEFAULT_SCHOOL_CODE",
    "SCHOOL_SPREADSHEET_ENV_KEYS",
    "get_school_spreadsheet_id",
    "get_configured_school_spreadsheets",
]
