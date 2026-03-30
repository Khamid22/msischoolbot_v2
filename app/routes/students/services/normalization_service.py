"""Shared normalization helpers used across routes/services."""

SCHOOL_CODE_ALIASES = {
    "school_5": "school5",
    "school-5": "school5",
    "school 5": "school5",
    "school5": "school5",
    "sehriyo": "sehriyo",
    "sehriyo school": "sehriyo",
}


def normalize_text(value):
    return " ".join(str(value or "").strip().casefold().split())


def normalize_school_code(value, default=""):
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return str(default or "").strip().casefold()
    return SCHOOL_CODE_ALIASES.get(normalized, normalized)


__all__ = [
    "SCHOOL_CODE_ALIASES",
    "normalize_text",
    "normalize_school_code",
]
