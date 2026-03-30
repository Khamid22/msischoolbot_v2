"""Backward-compatible facade for Google Sheets integration."""

from app.integrations.sheets import (
    GroupInfo,
    SheetsDataError,
    get_school_dataset,
    mark_school_dataset_dirty,
)

__all__ = [
    "get_school_dataset",
    "mark_school_dataset_dirty",
    "SheetsDataError",
    "GroupInfo",
]
