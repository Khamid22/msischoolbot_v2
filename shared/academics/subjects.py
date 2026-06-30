"""Canonical subject names, short labels, and matching keys."""

import re

from shared.academics.text import normalize_text

SUBJECT_CANONICAL_NAMES = {
    "igcse mathematics a": "IGCSE Mathematics A",
    "igcse math a": "IGCSE Mathematics A",
    "mathematics": "IGCSE Mathematics A",
    "math": "IGCSE Mathematics A",
    "m": "IGCSE Mathematics A",
    "igcse chemistry": "IGCSE Chemistry",
    "chemistry": "IGCSE Chemistry",
    "chem": "IGCSE Chemistry",
    "chm": "IGCSE Chemistry",
    "english as a second language": "English as a Second Language",
    "esl": "English as a Second Language",
    "general english": "English as a Second Language",
    "english": "English as a Second Language",
    "eng": "English as a Second Language",
    "igcse biology": "IGCSE Biology",
    "biology": "IGCSE Biology",
    "bio": "IGCSE Biology",
    "igcse physics": "IGCSE Physics",
    "physics": "IGCSE Physics",
    "phy": "IGCSE Physics",
}

SUBJECT_SHORT_NAMES = {
    "igcse mathematics a": "Math",
    "igcse chemistry": "Chem",
    "english as a second language": "Eng",
    "igcse biology": "Bio",
    "igcse physics": "Phy",
}

SUBJECT_SORT_ORDER = {
    "math": 0,
    "eng": 1,
    "chem": 2,
    "bio": 3,
    "phy": 4,
}


def subject_short_name(subject_name):
    """Short display label for a subject."""
    normalized = normalize_text(canonical_subject_name(subject_name))
    if normalized in SUBJECT_SHORT_NAMES:
        return SUBJECT_SHORT_NAMES[normalized]
    words = [part for part in str(subject_name or "").split() if part]
    if not words:
        return "Subject"
    return words[0]


def subject_sort_key(subject_name):
    """Sort key placing Math, English, Chemistry, Biology, Physics first."""
    short_name = subject_short_name(subject_name)
    normalized_short_name = normalize_text(short_name)
    return (
        SUBJECT_SORT_ORDER.get(normalized_short_name, 999),
        normalized_short_name,
    )


def normalize_subject_label(subject_name):
    """Backward-compatible alias for canonical subject display names."""
    return canonical_subject_name(subject_name)


def canonical_subject_name(subject_name):
    """Return the universal subject name stored in PostgreSQL."""
    normalized = normalize_text(subject_name)
    if not normalized:
        return ""
    return SUBJECT_CANONICAL_NAMES.get(normalized, str(subject_name or "").strip())


def subject_key(subject_name):
    """Stable key for uniqueness and lookups."""
    canonical_name = canonical_subject_name(subject_name)
    key = re.sub(r"[^a-z0-9]+", "-", normalize_text(canonical_name)).strip("-")
    return key or "subject"


def split_subjects(subjects_value):
    """Split a comma/semicolon-separated subject string into cleaned parts."""
    normalized = str(subjects_value or "").replace(";", ",")
    parts = [part.strip() for part in normalized.split(",")]
    return [part for part in parts if part]


__all__ = [
    "SUBJECT_SHORT_NAMES",
    "SUBJECT_CANONICAL_NAMES",
    "SUBJECT_SORT_ORDER",
    "subject_short_name",
    "subject_sort_key",
    "normalize_subject_label",
    "canonical_subject_name",
    "subject_key",
    "split_subjects",
]
