"""Google Sheets school configuration helpers."""

try:
    from ...config.schools import (
        DEFAULT_SCHOOL_CODE,
        SCHOOL_SPREADSHEET_ENV_KEYS,
        get_configured_school_spreadsheets,
        get_school_spreadsheet_id,
    )
except ImportError:
    from app.config.schools import (
        DEFAULT_SCHOOL_CODE,
        SCHOOL_SPREADSHEET_ENV_KEYS,
        get_configured_school_spreadsheets,
        get_school_spreadsheet_id,
    )

__all__ = [
    "DEFAULT_SCHOOL_CODE",
    "SCHOOL_SPREADSHEET_ENV_KEYS",
    "get_school_spreadsheet_id",
    "get_configured_school_spreadsheets",
]
