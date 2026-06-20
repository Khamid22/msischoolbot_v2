"""Canonical date parsing and formatting rules."""

from datetime import date, datetime

from shared.academics.text import normalize_text

PLACEHOLDER_DATE_TOKENS = {
    "",
    "homework",
    "h/w",
    "hw",
    "task",
    "topic",
    "date",
    "lesson",
}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%d/%m/%y",
    "%m/%d/%y",
    "%d.%m.%y",
    "%m.%d.%y",
    "%d-%m-%y",
    "%m-%d-%y",
)


def parse_date(value):
    """Parse a date string into a ``date``; return ``None`` if unrecognized."""
    import re

    text = str(value or "").strip()
    if not text:
        return None
    text = re.sub(r"\s*([./-])\s*", r"\1", text)
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    parts = text.replace(".", "/").replace("-", "/").split("/")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        day = int(parts[0])
        month = int(parts[1])
        if 1 <= day <= 31 and 1 <= month <= 12:
            now = datetime.utcnow()
            year = now.year - 1 if month > now.month + 1 else now.year
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


def format_date(value):
    """Return the database-wide date format: dd/mm/yyyy."""
    if is_placeholder_date(value):
        return ""
    parsed = parse_date(value)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value or "").strip()


def date_sort_key(value, *, on_unparseable=datetime.max):
    """Sortable ``datetime`` for a date string."""
    text = str(value or "").strip()
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue

    parts = text.replace(".", "/").replace("-", "/").split("/")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        day = int(parts[0])
        month = int(parts[1])
        if 1 <= day <= 31 and 1 <= month <= 12:
            now = datetime.utcnow()
            year = now.year - 1 if month > now.month + 1 else now.year
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

    return on_unparseable


def is_placeholder_date(value):
    """True for blank/sentinel date cells."""
    text = str(value or "").strip()
    if not text:
        return True
    return normalize_text(text) in PLACEHOLDER_DATE_TOKENS or not any(
        char.isdigit() for char in text
    )


__all__ = [
    "PLACEHOLDER_DATE_TOKENS",
    "parse_date",
    "format_date",
    "date_sort_key",
    "is_placeholder_date",
]
