"""Google Sheets integration API."""

from app.config.schools import (
    DEFAULT_SCHOOL_CODE,
    SCHOOL_SPREADSHEET_ENV_KEYS,
    get_configured_school_spreadsheets,
    get_school_spreadsheet_id,
)

from .auth import SheetsDataError
from .cache import (
    get_school_dataset,
    get_school_dataset_last_updated,
    mark_school_dataset_dirty,
)
from .parsers import GroupInfo

__all__ = [
    "get_school_dataset",
    "get_school_dataset_last_updated",
    "mark_school_dataset_dirty",
    "SheetsDataError",
    "GroupInfo",
    "DEFAULT_SCHOOL_CODE",
    "SCHOOL_SPREADSHEET_ENV_KEYS",
    "get_school_spreadsheet_id",
    "get_configured_school_spreadsheets",
]
