from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ("https://www.googleapis.com/auth/spreadsheets.readonly",)
CACHE_TTL_SECONDS = int(os.environ.get("SHEETS_CACHE_TTL_SECONDS", "600"))

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
    "MMG1": "Morning Group 1",
    "MMG2": "Morning Group 2",
    "MAFTG1": "Afternoon Group 1",
    "MAFTG2": "Afternoon Group 2",
}

_CACHE_LOCK = threading.Lock()
_CACHE_DATA: dict[str, Any] | None = None
_CACHE_EXPIRES_AT = 0.0
_SERVICE = None


class SheetsDataError(RuntimeError):
    """Raised when Google Sheets data cannot be loaded or parsed."""


@dataclass(frozen=True)
class GroupInfo:
    title: str
    normalized_code: str
    subject_code: str
    subject_name: str
    group_display_name: str


def _subject_sort_key(subject_name):
    normalized = subject_name.strip()
    return (SUBJECT_DISPLAY_ORDER.get(normalized, 999), normalized.casefold())


def _group_sort_key(group_name):
    normalized = group_name.strip()
    normalized_lower = normalized.casefold()

    if normalized_lower.startswith("morning group"):
        part_order = 0
    elif normalized_lower.startswith("afternoon group"):
        part_order = 1
    else:
        part_order = 2

    number_match = re.search(r"(\d+)$", normalized)
    group_number = int(number_match.group(1)) if number_match else 999
    return (part_order, group_number, normalized_lower)


def get_school_dataset(force_refresh = False):
    global _CACHE_DATA, _CACHE_EXPIRES_AT

    now = time.time()
    if not force_refresh and _CACHE_DATA and now < _CACHE_EXPIRES_AT:
        return _CACHE_DATA

    with _CACHE_LOCK:
        now = time.time()
        if not force_refresh and _CACHE_DATA and now < _CACHE_EXPIRES_AT:
            return _CACHE_DATA

        dataset = _load_from_google_sheets()
        _CACHE_DATA = dataset
        _CACHE_EXPIRES_AT = now + CACHE_TTL_SECONDS
        return dataset


def _load_from_google_sheets():
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        raise SheetsDataError("GOOGLE_SHEETS_SPREADSHEET_ID is not set.")

    service = _get_sheets_service()

    try:
        metadata = (
            service.spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id,
                fields="sheets(properties(title))",
            )
            .execute()
        )
    except Exception as exc:
        raise SheetsDataError(
            "Failed to read spreadsheet metadata from Google Sheets API."
        ) from exc

    sheet_titles = [
        sheet.get("properties", {}).get("title", "")
        for sheet in metadata.get("sheets", [])
        if sheet.get("properties", {}).get("title")
    ]

    group_infos = []
    for sheet_title in sheet_titles:
        group_info = _parse_group_info(sheet_title)
        if group_info:
            group_infos.append(group_info)

    if not group_infos:
        raise SheetsDataError(
            "No valid subject group tabs found. Use names like MMG1, MAFTG2, ENGMG1."
        )

    ranges = [f"'{_escape_sheet_title(group.title)}'!A1:ZZ" for group in group_infos]
    try:
        values_response = (
            service.spreadsheets()
            .values()
            .batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges,
                majorDimension="ROWS",
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
        )
    except Exception as exc:
        raise SheetsDataError(
            "Failed to read worksheet values from Google Sheets API."
        ) from exc

    values_by_title: dict[str, list[list[Any]]] = {}
    for value_range in values_response.get("valueRanges", []):
        title = _extract_title_from_a1_range(value_range.get("range", ""))
        values_by_title[title] = value_range.get("values", [])

    students: list[dict[str, Any]] = []
    dashboards_by_id: dict[int, dict[str, Any]] = {}
    groups_set: set[str] = set()
    groups_by_subject: dict[str, set[str]] = {}
    lesson_catalog_by_subject: dict[str, list[dict[str, Any]]] = {}
    lesson_catalog_by_subject_group: dict[str, dict[str, list[dict[str, Any]]]] = {}
    subjects_set: set[str] = set()
    used_student_ids: set[int] = set()

    for group in group_infos:
        rows = values_by_title.get(group.title, [])
        groups_set.add(group.group_display_name)
        groups_by_subject.setdefault(group.subject_name, set()).add(group.group_display_name)
        subjects_set.add(group.subject_name)

        parsed_students, group_lesson_catalog = _parse_group_rows(
            group=group,
            rows=rows,
            used_student_ids=used_student_ids,
        )
        for parsed in parsed_students:
            students.append(parsed["student"])
            dashboards_by_id[parsed["student"]["id"]] = parsed["dashboard"]

        subject_group_lessons = lesson_catalog_by_subject_group.setdefault(
            group.subject_name, {}
        )
        group_lessons = subject_group_lessons.setdefault(group.group_display_name, [])
        group_seen_numbers = {
            str(lesson.get("lesson_number", "")).strip().casefold()
            for lesson in group_lessons
            if isinstance(lesson, dict)
        }
        group_existing_by_number = {
            str(lesson.get("lesson_number", "")).strip().casefold(): lesson
            for lesson in group_lessons
            if isinstance(lesson, dict)
        }

        subject_lessons = lesson_catalog_by_subject.setdefault(group.subject_name, [])
        seen_numbers = {
            str(lesson.get("lesson_number", "")).strip().casefold()
            for lesson in subject_lessons
            if isinstance(lesson, dict)
        }
        existing_by_number = {
            str(lesson.get("lesson_number", "")).strip().casefold(): lesson
            for lesson in subject_lessons
            if isinstance(lesson, dict)
        }
        for lesson in group_lesson_catalog:
            if not isinstance(lesson, dict):
                continue
            lesson_number = str(lesson.get("lesson_number", "")).strip()
            lesson_topic = str(lesson.get("lesson_topic", "")).strip()
            lesson_date = str(lesson.get("lesson_date", "")).strip()
            if not lesson_number or not lesson_topic:
                continue
            dedupe_key = lesson_number.casefold()

            if dedupe_key in group_seen_numbers:
                existing_group_lesson = group_existing_by_number.get(dedupe_key)
                if (
                    existing_group_lesson is not None
                    and lesson_date
                    and not str(existing_group_lesson.get("lesson_date", "")).strip()
                ):
                    existing_group_lesson["lesson_date"] = lesson_date
            else:
                group_seen_numbers.add(dedupe_key)
                grouped_lesson = {
                    "lesson_number": lesson_number,
                    "lesson_topic": lesson_topic,
                    "lesson_date": lesson_date,
                    "lesson_order": int(lesson.get("lesson_order", len(group_lessons) + 1)),
                }
                group_lessons.append(grouped_lesson)
                group_existing_by_number[dedupe_key] = grouped_lesson

            if dedupe_key in seen_numbers:
                existing_lesson = existing_by_number.get(dedupe_key)
                if (
                    existing_lesson is not None
                    and lesson_date
                    and not str(existing_lesson.get("lesson_date", "")).strip()
                ):
                    existing_lesson["lesson_date"] = lesson_date
                continue
            seen_numbers.add(dedupe_key)
            merged_lesson = {
                "lesson_number": lesson_number,
                "lesson_topic": lesson_topic,
                "lesson_date": lesson_date,
                "lesson_order": int(lesson.get("lesson_order", len(subject_lessons) + 1)),
            }
            subject_lessons.append(merged_lesson)
            existing_by_number[dedupe_key] = merged_lesson

    # Make coins global per student (sum from all enrolled subjects).
    _merge_total_coins_across_subjects(students, dashboards_by_id)

    students.sort(
        key=lambda student: (
            _subject_sort_key(str(student.get("subject", ""))),
            _group_sort_key(str(student.get("group", ""))),
            str(student.get("fullName", "")).casefold(),
        )
    )

    ordered_subjects = sorted(subjects_set, key=_subject_sort_key)
    ordered_groups_by_subject = {
        subject: sorted(groups_by_subject.get(subject, set()), key=_group_sort_key)
        for subject in ordered_subjects
    }
    ordered_lesson_catalog_by_subject: dict[str, list[dict[str, Any]]] = {}
    ordered_lesson_catalog_by_subject_group: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for subject in ordered_subjects:
        lessons = lesson_catalog_by_subject.get(subject, [])
        ordered_lessons = sorted(
            lessons,
            key=lambda lesson: (
                int(lesson.get("lesson_order", 0)),
                str(lesson.get("lesson_number", "")).casefold(),
            ),
        )
        ordered_lesson_catalog_by_subject[subject] = ordered_lessons

        subject_group_map = lesson_catalog_by_subject_group.get(subject, {})
        ordered_group_map: dict[str, list[dict[str, Any]]] = {}
        for group_name in sorted(subject_group_map.keys(), key=_group_sort_key):
            group_lessons = subject_group_map.get(group_name, [])
            ordered_group_map[group_name] = sorted(
                group_lessons,
                key=lambda lesson: (
                    int(lesson.get("lesson_order", 0)),
                    str(lesson.get("lesson_number", "")).casefold(),
                ),
            )
        ordered_lesson_catalog_by_subject_group[subject] = ordered_group_map

    return {
        "students": students,
        "dashboards_by_id": dashboards_by_id,
        "groups": sorted(groups_set, key=_group_sort_key),
        "groups_by_subject": ordered_groups_by_subject,
        "lesson_catalog_by_subject": ordered_lesson_catalog_by_subject,
        "lesson_catalog_by_subject_group": ordered_lesson_catalog_by_subject_group,
        "subjects": ordered_subjects,
    }


def _get_sheets_service():
    global _SERVICE
    if _SERVICE is not None:
        return _SERVICE

    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_source = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    credentials = None
    if raw_json:
        try:
            service_account_info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise SheetsDataError("GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON.") from exc
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )
    elif credentials_source:
        # Backward-compatible behavior:
        # - If GOOGLE_APPLICATION_CREDENTIALS contains JSON text, parse it.
        # - Otherwise treat it as a filesystem path.
        if credentials_source.startswith("{"):
            try:
                service_account_info = json.loads(credentials_source)
            except json.JSONDecodeError as exc:
                raise SheetsDataError(
                    "GOOGLE_APPLICATION_CREDENTIALS looks like JSON but is invalid."
                ) from exc
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES,
            )
        else:
            try:
                credentials = Credentials.from_service_account_file(
                    credentials_source,
                    scopes=SCOPES,
                )
            except Exception as exc:
                raise SheetsDataError(
                    "Failed to load GOOGLE_APPLICATION_CREDENTIALS file. "
                    "Use a valid in-container path, or set GOOGLE_SERVICE_ACCOUNT_JSON."
                ) from exc
    else:
        raise SheetsDataError(
            "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS."
        )

    try:
        _SERVICE = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        raise SheetsDataError("Failed to initialize Google Sheets API client.") from exc
    return _SERVICE


def _parse_group_info(sheet_title):
    normalized_code = _normalize_group_code(sheet_title)
    if not normalized_code:
        return None

    subject_code, suffix = _split_subject_and_suffix(normalized_code)
    if not subject_code or not suffix:
        return None

    if not _is_supported_group_suffix(suffix):
        return None

    subject_name = SUBJECT_NAMES.get(subject_code)
    if not subject_name:
        return None

    if normalized_code in EXACT_GROUP_DISPLAY_NAMES:
        group_display_name = EXACT_GROUP_DISPLAY_NAMES[normalized_code]
    else:
        group_display_name = _humanize_group_suffix(suffix)

    return GroupInfo(
        title=sheet_title,
        normalized_code=normalized_code,
        subject_code=subject_code,
        subject_name=subject_name,
        group_display_name=group_display_name,
    )


def _normalize_group_code(raw_code):
    return re.sub(r"[^A-Za-z0-9]", "", raw_code).upper()


def _split_subject_and_suffix(normalized_code):
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


def _humanize_group_suffix(suffix):
    morning_match = re.fullmatch(r"MG(\d+)", suffix)
    if morning_match:
        return f"Morning Group {morning_match.group(1)}"

    afternoon_match = re.fullmatch(r"AFTG(\d+)", suffix)
    if afternoon_match:
        return f"Afternoon Group {afternoon_match.group(1)}"

    generic_group_match = re.fullmatch(r"GRP(\d+)", suffix)
    if generic_group_match:
        return f"Group {generic_group_match.group(1)}"

    fallback = re.sub(r"(\D)(\d)", r"\1 \2", suffix)
    fallback = fallback.replace("AFTG", "Afternoon Group").replace("MG", "Morning Group")
    return fallback.title()


def _is_supported_group_suffix(suffix):
    return bool(re.fullmatch(r"[A-Z]*G\d+", suffix))


def _extract_title_from_a1_range(a1_range):
    if "!" not in a1_range:
        return a1_range.strip().strip("'")

    title_part = a1_range.split("!", 1)[0].strip()
    if title_part.startswith("'") and title_part.endswith("'"):
        title_part = title_part[1:-1].replace("''", "'")
    return title_part


def _escape_sheet_title(title):
    return title.replace("'", "''")


def _parse_group_rows(
    group,
    rows,
    used_student_ids,
):
    if not rows:
        return [], []

    lesson_date_row = rows[0] if len(rows) > 0 else []
    lesson_number_row = rows[1] if len(rows) > 1 else []
    lesson_name_row = rows[2] if len(rows) > 2 else []
    exam_columns = list(range(2, 20))  # C..T
    exam_column_meta = _build_exam_columns_metadata(lesson_name_row, exam_columns)
    homework_columns_meta = _build_homework_columns_metadata(
        rows,
        lesson_number_row,
        lesson_name_row,
        lesson_date_row,
    )
    coins_by_name = _extract_coins_by_name(rows)

    lesson_catalog = []
    for lesson_order, lesson_meta in enumerate(homework_columns_meta, start=1):
        lesson_catalog.append(
            {
                "lesson_number": str(lesson_meta.get("label", "")).strip(),
                "lesson_topic": str(lesson_meta.get("topic", "")).strip(),
                "lesson_date": str(lesson_meta.get("date", "")).strip(),
                "lesson_order": lesson_order,
            }
        )

    parsed_rows = []
    for row_number, row in enumerate(rows, start=1):
        if not _is_student_data_row(row):
            continue

        full_name = _normalize_whitespace(_to_text(_cell_value(row, 1)))
        if not full_name:
            continue

        normalized_name = full_name.casefold()
        if normalized_name in {"student name", "lesson aap", "submission rate"}:
            continue

        split_name = _split_student_name(full_name)

        exam_results = []
        for exam_meta in exam_column_meta:
            score = _parse_numeric_score(_cell_value(row, exam_meta["column_index"]))
            if score is None:
                continue

            exam_results.append(
                {
                    "label": exam_meta["label"],
                    "examName": exam_meta["exam_name"],
                    "attempt": exam_meta["attempt_name"],
                    "score": score,
                }
            )

        homework_grades = []
        present_count = 0
        absent_count = 0
        justified_absent_count = 0
        for lesson_meta in homework_columns_meta:
            attendance_cell = _cell_value(row, lesson_meta["attendance_column_index"])
            score_cell = _cell_value(row, lesson_meta["score_column_index"])

            score = _parse_numeric_score(score_cell)
            if score is None:
                score = _parse_numeric_score(attendance_cell)
            if score is not None:
                homework_grades.append(
                    {
                        "lesson": lesson_meta["label"],
                        "topic": lesson_meta.get("topic", ""),
                        "date": lesson_meta.get("date", ""),
                        "score": score,
                    }
                )

            p, a, ai = _parse_attendance_markers(attendance_cell)
            if lesson_meta["score_column_index"] != lesson_meta["attendance_column_index"]:
                p2, a2, ai2 = _parse_attendance_markers(score_cell)
                p += p2
                a += a2
                ai += ai2

            present_count += p
            absent_count += a
            justified_absent_count += ai

        # Keep backward-compatible structure for existing frontend integrations.
        academic_records = [
            {
                "date": result["label"],
                "grade": result["score"],
                "subject": group.subject_name,
                "assessment": result["label"],
            }
            for result in exam_results
        ]

        average_grade_cell = _parse_numeric_score(_cell_value(row, 20))  # U
        if average_grade_cell is not None:
            average_grade = round(average_grade_cell, 1)
        else:
            graded_count = len(exam_results)
            average_grade = (
                round(sum(result["score"] for result in exam_results) / graded_count, 1)
                if graded_count
                else 0.0
            )

        total_count = present_count + absent_count + justified_absent_count

        student_id = _build_stable_student_id(
            key=f"{group.normalized_code}|{full_name}",
            used_student_ids=used_student_ids,
        )

        coins = coins_by_name.get(_normalize_name_key(full_name), 0)

        student = {
            "id": student_id,
            "surname": split_name["surname"],
            "name": split_name["name"],
            "fullName": full_name,
            "initials": split_name["initials"],
            "group": group.group_display_name,
            "groupCode": group.normalized_code,
            "subject": group.subject_name,
            "subjectCode": group.subject_code,
            "coins": coins,
        }

        dashboard = {
            "student": student,
            "academicRecords": academic_records,
            "examResults": exam_results,
            "homeworkGrades": homework_grades,
            "attendanceRecord": {
                "presentCount": present_count,
                "absentCount": absent_count,
                "justifiedAbsentCount": justified_absent_count,
                "totalCount": total_count,
                "subject": group.subject_name,
            },
            "averageGrade": average_grade,
            "coins": coins,
        }

        parsed_rows.append({"student": student, "dashboard": dashboard})

    return parsed_rows, lesson_catalog


def _cell_value(row, index):
    if index < 0 or index >= len(row):
        return None
    return row[index]


def _to_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_whitespace(value):
    return " ".join(value.split())


def _parse_numeric_score(value):
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


def _parse_attendance_markers(value):
    if value is None:
        return 0, 0, 0

    raw = str(value).strip()
    if not raw:
        return 0, 0, 0

    normalized = re.sub(r"\s+", "", raw).upper().replace("Aİ", "AI")
    tokens = re.findall(r"A\(\s*I\s*\)|AI|P|A", normalized)

    present = sum(1 for token in tokens if token == "P")
    justified_absent = sum(1 for token in tokens if token in {"AI", "A(I)"})
    absent = sum(1 for token in tokens if token == "A")

    return present, absent, justified_absent


def _is_student_data_row(row):
    row_index_marker = _parse_numeric_score(_cell_value(row, 0))
    student_name = _normalize_whitespace(_to_text(_cell_value(row, 1)))
    return row_index_marker is not None and bool(student_name)


def _build_homework_columns_metadata(
    rows,
    lesson_number_row,
    lesson_topic_row,
    lesson_date_row,
):
    max_columns = max((len(row) for row in rows), default=0)
    start_column = 21  # V

    metadata: list[dict[str, Any]] = []
    for column_index in range(start_column, max_columns):
        raw_label = _to_text(_cell_value(lesson_number_row, column_index))
        if not raw_label:
            continue

        label = _normalize_whitespace(raw_label.replace("\n", " "))
        if _should_skip_homework_lesson(label):
            continue

        next_label = _to_text(_cell_value(lesson_number_row, column_index + 1))
        if next_label:
            score_column_index = column_index
        else:
            score_column_index = min(column_index + 1, max_columns - 1)

        raw_topic = _to_text(_cell_value(lesson_topic_row, column_index))
        if not raw_topic and score_column_index != column_index:
            raw_topic = _to_text(_cell_value(lesson_topic_row, score_column_index))

        raw_date = _cell_value(lesson_date_row, column_index)
        if (
            (raw_date is None or _to_text(raw_date) == "")
            and score_column_index != column_index
        ):
            raw_date = _cell_value(lesson_date_row, score_column_index)
        lesson_date = _format_lesson_date(raw_date)

        topic = _normalize_whitespace(raw_topic.replace("\n", " "))
        if not topic:
            topic = "Topic"
        if _is_cancelled_homework_lesson(label, topic):
            continue

        metadata.append(
            {
                "attendance_column_index": column_index,
                "score_column_index": score_column_index,
                "label": label,
                "topic": topic,
                "date": lesson_date,
            }
        )

    return metadata


def _format_lesson_date(value):
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

    return _normalize_whitespace(str(value).replace("\n", " ").strip())


def _extract_lesson_number(label):
    # Supports labels like "L21", "L 21", or "Lesson 21".
    match = re.search(r"\bL?\s*(\d{1,3})\b", str(label or "").upper())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _should_skip_homework_lesson(label):
    lesson_number = _extract_lesson_number(label)
    return lesson_number in EXCLUDED_HOMEWORK_LESSON_NUMBERS


def _is_cancelled_homework_lesson(label, topic):
    normalized = f"{label} {topic}".casefold()
    return "cancelled" in normalized or "canceled" in normalized


def _build_exam_columns_metadata(
    lesson_name_row,
    exam_columns,
):
    meta = []
    current_exam_name = ""

    for index, column_index in enumerate(exam_columns, start=1):
        header_name = _normalize_exam_name(_to_text(_cell_value(lesson_name_row, column_index)))
        if header_name:
            current_exam_name = header_name
            attempt_name = "First Attempt"
        else:
            attempt_name = "Second Attempt" if current_exam_name else "Attempt"

        if current_exam_name:
            if attempt_name == "Attempt":
                label = f"{current_exam_name} - Attempt {index}"
            else:
                label = f"{current_exam_name} - {attempt_name}"
        else:
            label = f"Attempt {index}"

        meta.append(
            {
                "column_index": column_index,
                "exam_name": current_exam_name or "Exam",
                "attempt_name": attempt_name,
                "label": label,
            }
        )

    return meta


def _normalize_exam_name(value):
    if not value:
        return ""

    normalized = _normalize_whitespace(value.replace("\n", " "))
    normalized = normalized.replace(" - ", "-")
    return normalized


def _extract_coins_by_name(rows):
    coins_by_name: dict[str, int] = {}

    for row_number, row in enumerate(rows, start=1):
        if row_number < 19:
            continue

        name = _normalize_whitespace(_to_text(_cell_value(row, 0)))
        if not name:
            name = _normalize_whitespace(_to_text(_cell_value(row, 1)))
        if not name:
            continue

        upper_name = name.upper()
        if "TOTAL COINS" in upper_name:
            continue

        coins_value = _parse_numeric_score(_cell_value(row, 20))  # U
        if coins_value is None:
            continue

        coins_by_name[_normalize_name_key(name)] = int(round(coins_value))

    return coins_by_name


def _normalize_name_key(name):
    return _normalize_whitespace(name).casefold()


def _merge_total_coins_across_subjects(students, dashboards_by_id):
    total_coins_by_name: dict[str, int] = {}

    for student in students:
        if not isinstance(student, dict):
            continue
        student_name_key = _normalize_name_key(student.get("fullName", ""))
        if not student_name_key:
            continue

        raw_coins = student.get("coins", 0)
        try:
            numeric_coins = int(round(float(raw_coins)))
        except (TypeError, ValueError):
            numeric_coins = 0

        total_coins_by_name[student_name_key] = (
            total_coins_by_name.get(student_name_key, 0) + numeric_coins
        )

    for student in students:
        if not isinstance(student, dict):
            continue
        student_name_key = _normalize_name_key(student.get("fullName", ""))
        if not student_name_key:
            continue
        student["coins"] = int(total_coins_by_name.get(student_name_key, 0))

    if not isinstance(dashboards_by_id, dict):
        return

    for dashboard_payload in dashboards_by_id.values():
        if not isinstance(dashboard_payload, dict):
            continue

        payload_student = dashboard_payload.get("student", {})
        if not isinstance(payload_student, dict):
            continue

        student_name_key = _normalize_name_key(payload_student.get("fullName", ""))
        if not student_name_key:
            continue

        merged_coins = int(total_coins_by_name.get(student_name_key, 0))
        payload_student["coins"] = merged_coins
        dashboard_payload["coins"] = merged_coins


def _format_assessment_date(raw_value, fallback_label):
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


def _split_student_name(full_name):
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


def _build_stable_student_id(key, used_student_ids):
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    candidate = int(digest[:8], 16)
    while candidate in used_student_ids:
        candidate += 1
    used_student_ids.add(candidate)
    return candidate
