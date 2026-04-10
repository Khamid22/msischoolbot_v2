from __future__ import annotations

import os

SCOPES = ("https://www.googleapis.com/auth/spreadsheets.readonly",)
CACHE_TTL_SECONDS = int(os.environ.get("SHEETS_CACHE_TTL_SECONDS", "1800"))
WEBHOOK_MAX_STALE_SECONDS = int(
    os.environ.get("SHEETS_WEBHOOK_MAX_STALE_SECONDS", "21600")
)


class Columns:
    STUDENT_INDEX_MARKER = 0  # A
    STUDENT_NAME = 1  # B

    EXAM_START = 2  # C
    EXAM_END_EXCLUSIVE = 20  # T (exclusive)
    SEHRIYO_CHEMISTRY_EXAM_END_EXCLUSIVE = 19  # S (exclusive)

    SEHRIYO_CHEMISTRY_LESSON_START = 1  # B
    SEHRIYO_CHEMISTRY_SCORE_START = 20  # U

    SCHOOL_AVERAGE_GRADE = 20  # U
    SEHRIYO_CHEMISTRY_AVERAGE_GRADE = 19  # T

    HOMEWORK_START = 21  # V
    COINS = 20  # U


SUBJECT_NAMES = {
    "M": "IGCSE Mathematics A",
    "ENG": "General English",
    "CHM": "Chemistry",
    "BIO": "Biology",
    "PHY": "Physics",
}

SUBJECT_ALIASES = {
    "E": "ENG",
}

SEHRIYO_SUBJECT_ALIASES = {
    "MATH": "M",
    "MATHEMATICS": "M",
    "ENG": "ENG",
    "ENGLISH": "ENG",
    "GENERALENGLISH": "ENG",
    "CH": "CHM",
    "CHEM": "CHM",
    "CHEMISTRY": "CHM",
}

SEHRIYO_CLASS_DISPLAY_TRANSLATION = str.maketrans(
    {
        "А": "A",
        "Б": "B",
        "В": "B",
        "С": "C",
        "Е": "E",
        "Н": "H",
        "К": "K",
        "М": "M",
        "О": "O",
        "Р": "P",
        "Т": "T",
        "Х": "X",
        "У": "Y",
    }
)

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

SUBJECT_DISPLAY_ORDER = {
    "IGCSE Mathematics A": 0,
    "General English": 1,
}

EXCLUDED_HOMEWORK_LESSON_NUMBERS = {
    21,
    39,
    54,
    72,
    87,
    120,
    153,
    171,
}

EXACT_GROUP_DISPLAY_NAMES = {
    "MMG1": "MG1",
    "MMG2": "MG2",
    "MAFTG1": "AFT1",
    "MAFTG2": "AFT2",
}


def is_webhook_cache_enabled() -> bool:
    raw_value = os.environ.get("SHEETS_WEBHOOK_CACHE_ENABLED")
    if raw_value is None:
        return bool(str(os.environ.get("GOOGLE_SHEETS_WEBHOOK_TOKEN", "")).strip())
    return str(raw_value).strip().casefold() in {"1", "true", "yes", "on"}


WEBHOOK_CACHE_ENABLED = is_webhook_cache_enabled()
