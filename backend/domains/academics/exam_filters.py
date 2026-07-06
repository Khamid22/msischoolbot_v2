"""Conservative filters for rows that should count as exam performance."""

from __future__ import annotations

import re
from typing import Any

_EXAM_KEYWORD_RE = re.compile(
    r"(?:"
    r"\bexam\b|"
    r"\btest\b|"
    r"\bmock\b|"
    r"\bdiagnostic\b|"
    r"\bfinal\b|"
    r"\bhalf[\s-]*term\b|"
    r"\bend[\s-]*of[\s-]*term\b|"
    r"\bassessment\b|"
    r"\b(?:hft|ht|et)\s*\d+\b"
    r")",
    re.IGNORECASE,
)
_CANCELLED_RE = re.compile(r"\b(?:cancelled|canceled)\b", re.IGNORECASE)
_EXPLICIT_EXAM_TYPES = {"exam", "test", "assessment"}


def _joined_text(*values: Any) -> str:
    return " ".join(str(value or "").strip() for value in values if str(value or "").strip())


def text_indicates_exam_performance(*values: Any) -> bool:
    text = _joined_text(*values)
    if not text or _CANCELLED_RE.search(text):
        return False
    return bool(_EXAM_KEYWORD_RE.search(text))


def is_exam_performance_row(
    *,
    item_type: Any = "",
    exam_name: Any = "",
    label: Any = "",
    title: Any = "",
    attempt: Any = "",
) -> bool:
    text = _joined_text(exam_name, label, title, attempt)
    if not text or _CANCELLED_RE.search(text):
        return False

    normalized_type = str(item_type or "").strip().casefold()
    if normalized_type in _EXPLICIT_EXAM_TYPES:
        return True

    return text_indicates_exam_performance(text)


__all__ = ["is_exam_performance_row", "text_indicates_exam_performance"]
