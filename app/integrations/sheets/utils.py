from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta

from app.config.schools import DEFAULT_SCHOOL_CODE

from .constants import (
    Columns,
    EXCLUDED_HOMEWORK_LESSON_NUMBERS,
    SCHOOL_CODE_ALIASES,
    SCHOOL_DISPLAY_NAMES,
    SUBJECT_ALIASES,
    SUBJECT_DISPLAY_ORDER,
)


def normalize_school_code(school_code):
    normalized = str(school_code or DEFAULT_SCHOOL_CODE).strip().casefold()
    aliased = SCHOOL_CODE_ALIASES.get(normalized)
    if aliased is not None:
        return aliased
    return normalized or DEFAULT_SCHOOL_CODE


def school_display_name(school_code):
    normalized = normalize_school_code(school_code)
    return SCHOOL_DISPLAY_NAMES.get(normalized, "School")


def subject_sort_key(subject_name):
    normalized = subject_name.strip()
    return (SUBJECT_DISPLAY_ORDER.get(normalized, 999), normalized.casefold())


def group_sort_key(group_name):
    normalized = group_name.strip()
    normalized_lower = normalized.casefold()
    compact = re.sub(r"[^a-z0-9]+", "", normalized_lower)

    if normalized_lower.startswith("morning group") or compact.startswith("mg"):
        part_order = 0
    elif normalized_lower.startswith("afternoon group") or compact.startswith("aft"):
        part_order = 1
    else:
        part_order = 2

    number_match = re.search(r"(\d+)$", normalized)
    group_number = int(number_match.group(1)) if number_match else 999
    return (part_order, group_number, normalized_lower)


def normalize_group_code(raw_code):
    return re.sub(r"[^A-Za-z0-9]", "", raw_code).upper()


def normalize_sehriyo_class_name(raw_class):
    from .constants import SEHRIYO_CLASS_DISPLAY_TRANSLATION

    class_name = str(raw_class or "").strip().upper()
    class_name = class_name.translate(SEHRIYO_CLASS_DISPLAY_TRANSLATION)
    return class_name


def legacy_sehriyo_class_key(class_name):
    match = re.fullmatch(r"([0-9]+)([A-Z]+)", class_name)
    if not match:
        return class_name

    grade, suffix = match.groups()
    return f"{grade}{suffix.replace('B', 'Б')}"


def split_subject_and_suffix(normalized_code):
    from .constants import SUBJECT_NAMES

    subject_candidates = sorted(
        set(list(SUBJECT_NAMES.keys()) + list(SUBJECT_ALIASES.keys())),
        key=len,
        reverse=True,
    )

    for candidate in subject_candidates:
        if normalized_code.startswith(candidate):
            canonical_subject = SUBJECT_ALIASES.get(candidate, candidate)
            suffix = normalized_code[len(candidate):]
            return canonical_subject, suffix

    return None, None


def humanize_group_suffix(suffix):
    normalized_suffix = str(suffix or "").strip().upper()
    if normalized_suffix in {"ONLINE", "ONL"}:
        return "Online"

    morning_match = re.fullmatch(r"MG(\d+)", suffix)
    if morning_match:
        return f"MG{morning_match.group(1)}"

    afternoon_match = re.fullmatch(r"AFTG(\d+)", suffix)
    if afternoon_match:
        return f"AFT{afternoon_match.group(1)}"

    generic_group_match = re.fullmatch(r"GRP(\d+)", suffix)
    if generic_group_match:
        return f"Group {generic_group_match.group(1)}"

    fallback = re.sub(r"(\D)(\d)", r"\1 \2", suffix)
    fallback = fallback.replace("AFTG", "AFT").replace("MG", "MG")
    return fallback.title()


def is_supported_group_suffix(suffix):
    normalized_suffix = str(suffix or "").strip().upper()
    if normalized_suffix in {"ONLINE", "ONL"}:
        return True
    return bool(re.fullmatch(r"[A-Z]*G\d+", normalized_suffix))


def extract_title_from_a1_range(a1_range):
    if "!" not in a1_range:
        return a1_range.strip().strip("'")

    title_part = a1_range.split("!", 1)[0].strip()
    if title_part.startswith("'") and title_part.endswith("'"):
        title_part = title_part[1:-1].replace("''", "'")
    return title_part


def escape_sheet_title(title):
    return title.replace("'", "''")


def cell_value(row, index):
    if index < 0 or index >= len(row):
        return None
    return row[index]


def to_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_whitespace(value):
    return " ".join(value.split())


def parse_numeric_score(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip().replace(",", ".")
    if not raw:
        return None

    raw = raw.replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_attendance_markers(value):
    if value is None:
        return 0, 0, 0

    raw = str(value).strip()
    if not raw:
        return 0, 0, 0

    normalized = str(raw).upper().replace("Aİ", "AI")

    # Canceled/cancelled sessions should not be interpreted as attendance marks.
    if re.search(r"\bCANCEL(?:ED|LED)\b", normalized):
        return 0, 0, 0

    # Normalize justified-absence notations like "A(I)", "A/I", "A I" -> "AI".
    normalized = re.sub(r"A\s*[\(\[/\\-]?\s*I\s*[\)\]]?", "AI", normalized)

    # Split by common separators and only accept explicit attendance tokens.
    tokens = [
        token
        for token in re.split(r"[\s,;|/]+", normalized)
        if token in {"P", "L", "A", "AI"}
    ]

    present = sum(1 for token in tokens if token in {"P", "L"})
    justified_absent = sum(1 for token in tokens if token == "AI")
    absent = sum(1 for token in tokens if token == "A")

    return present, absent, justified_absent


def is_student_data_row(row):
    row_index_marker = parse_numeric_score(cell_value(row, Columns.STUDENT_INDEX_MARKER))
    student_name = normalize_whitespace(to_text(cell_value(row, Columns.STUDENT_NAME)))
    return row_index_marker is not None and bool(student_name)


def is_sehriyo_chemistry_group(group):
    normalized_school_code = normalize_school_code(
        getattr(group, "school_code", DEFAULT_SCHOOL_CODE)
    )
    return normalized_school_code == "sehriyo" and is_chemistry_group(group)


def is_chemistry_group(group):
    subject_code = str(getattr(group, "subject_code", "")).strip().upper()
    return subject_code == "CHM"


def average_grade_column_index(group):
    _ = group
    return Columns.SCHOOL_AVERAGE_GRADE


def format_lesson_date(value):
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        # Convert Google Sheets serial dates when possible.
        numeric = float(value)
        if numeric > 0:
            try:
                return (datetime(1899, 12, 30) + timedelta(days=numeric)).date().isoformat()
            except (OverflowError, ValueError):
                return str(value).strip()
        return ""

    return normalize_whitespace(str(value).replace("\n", " ").strip())


def extract_lesson_number(label):
    # Supports labels like "L21", "L 21", or "Lesson 21".
    match = re.search(r"\bL?\s*(\d{1,3})\b", str(label or "").upper())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def should_skip_homework_lesson(label):
    lesson_number = extract_lesson_number(label)
    return lesson_number in EXCLUDED_HOMEWORK_LESSON_NUMBERS


def is_excluded_homework_session(label, topic):
    normalized = f"{label} {topic}".casefold()
    if "cancelled" in normalized or "canceled" in normalized:
        return True
    return "practice" in normalized or "review" in normalized or "revision" in normalized


def normalize_exam_name(value):
    if not value:
        return ""

    normalized = normalize_whitespace(value.replace("\n", " "))
    normalized = normalized.replace(" - ", "-")
    return normalized


def build_student_row_key(group, full_name):
    if getattr(group, "school_code", DEFAULT_SCHOOL_CODE) == "sehriyo":
        return f"sehriyo|{group.normalized_code}|{full_name}"
    return f"{group.normalized_code}|{full_name}"


def normalize_name_key(name):
    return normalize_whitespace(name).casefold()


def format_assessment_date(raw_value, fallback_label):
    if raw_value is None or raw_value == "":
        return fallback_label

    if isinstance(raw_value, (int, float)):
        numeric = float(raw_value)
        if numeric >= 20000:
            date_value = datetime(1899, 12, 30) + timedelta(days=numeric)
            return date_value.date().isoformat()
        return str(raw_value)

    raw_text = str(raw_value).strip()
    if not raw_text:
        return fallback_label

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw_text, fmt).date().isoformat()
        except ValueError:
            continue

    return raw_text


def split_student_name(full_name):
    parts = full_name.split()
    if not parts:
        return {"name": "", "surname": "", "initials": ""}

    if len(parts) == 1:
        name = parts[0]
        surname = ""
    else:
        name = parts[0]
        surname = " ".join(parts[1:])

    first_initial = name[0].upper() if name else ""
    second_initial = surname[0].upper() if surname else ""
    initials = (first_initial + second_initial) or first_initial

    return {"name": name, "surname": surname, "initials": initials}


def build_stable_student_id(key, used_student_ids):
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    candidate = int(digest[:8], 16)
    while candidate in used_student_ids:
        candidate += 1
    used_student_ids.add(candidate)
    return candidate
