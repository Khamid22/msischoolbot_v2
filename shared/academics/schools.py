"""Canonical school code and school display rules."""

from shared.academics.text import normalize_text

DEFAULT_SCHOOL_CODE = "school5"
DEFAULT_SCHOOL_NAME = "School 5"
ADMIN_SCHOOL_FILTER_ALL = "all"

SCHOOL_CODE_ALIASES = {
    "school_5": "school5",
    "school-5": "school5",
    "school 5": "school5",
    "school5": "school5",
    "sehriyo": "sehriyo",
    "sehriyo school": "sehriyo",
}

SCHOOL_DISPLAY_NAMES = {
    "school5": "School 5",
    "sehriyo": "Sehriyo",
}

SCHOOL_STUDENT_PREFIX = {
    "school5": "MSI",
    "sehriyo": "MSIS",
}


def normalize_school_code(value, default=DEFAULT_SCHOOL_CODE):
    """Map any spelling of a school to its canonical code."""
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return str(default or "").strip().casefold()
    return SCHOOL_CODE_ALIASES.get(normalized, normalized)


def school_display_name(school_code):
    return SCHOOL_DISPLAY_NAMES.get(normalize_school_code(school_code), DEFAULT_SCHOOL_NAME)


def student_code_prefix(school_code):
    return SCHOOL_STUDENT_PREFIX.get(normalize_school_code(school_code), "MSI")


def normalize_admin_school_filter(value):
    normalized = normalize_text(value) or ADMIN_SCHOOL_FILTER_ALL
    if normalized in SCHOOL_DISPLAY_NAMES:
        return normalized
    return ADMIN_SCHOOL_FILTER_ALL


__all__ = [
    "DEFAULT_SCHOOL_CODE",
    "DEFAULT_SCHOOL_NAME",
    "ADMIN_SCHOOL_FILTER_ALL",
    "SCHOOL_CODE_ALIASES",
    "SCHOOL_DISPLAY_NAMES",
    "SCHOOL_STUDENT_PREFIX",
    "normalize_school_code",
    "school_display_name",
    "student_code_prefix",
    "normalize_admin_school_filter",
]
