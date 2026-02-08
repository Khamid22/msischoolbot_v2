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
CACHE_TTL_SECONDS = int(os.environ.get("SHEETS_CACHE_TTL_SECONDS", "120"))

SUBJECT_NAMES = {
    "M": "IGCSE Mathematics A",
    "ENG": "English",
    "CHM": "Chemistry",
    "BIO": "Biology",
    "PHY": "Physics",
}

SUBJECT_ALIASES = {
    "E": "ENG",
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


def get_school_dataset(force_refresh: bool = False) -> dict[str, Any]:
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


def _load_from_google_sheets() -> dict[str, Any]:
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
    subjects_set: set[str] = set()
    used_student_ids: set[int] = set()

    for group in group_infos:
        rows = values_by_title.get(group.title, [])
        groups_set.add(group.group_display_name)
        groups_by_subject.setdefault(group.subject_name, set()).add(group.group_display_name)
        subjects_set.add(group.subject_name)

        parsed_students = _parse_group_rows(
            group=group,
            rows=rows,
            used_student_ids=used_student_ids,
        )
        for parsed in parsed_students:
            students.append(parsed["student"])
            dashboards_by_id[parsed["student"]["id"]] = parsed["dashboard"]

    students.sort(
        key=lambda student: (
            student["subject"],
            student["group"],
            student["fullName"],
        )
    )

    return {
        "students": students,
        "dashboards_by_id": dashboards_by_id,
        "groups": sorted(groups_set),
        "groups_by_subject": {
            subject: sorted(group_names)
            for subject, group_names in sorted(groups_by_subject.items())
        },
        "subjects": sorted(subjects_set),
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


def _parse_group_info(sheet_title: str) -> GroupInfo | None:
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


def _normalize_group_code(raw_code: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw_code).upper()


def _split_subject_and_suffix(normalized_code: str) -> tuple[str | None, str | None]:
    subject_candidates = sorted(
        set(list(SUBJECT_NAMES.keys()) + list(SUBJECT_ALIASES.keys())),
        key=len,
        reverse=True,
    )

    for candidate in subject_candidates:
        if normalized_code.startswith(candidate):
            canonical_subject = SUBJECT_ALIASES.get(candidate, candidate)
            suffix = normalized_code[len(candidate) :]
            return canonical_subject, suffix

    return None, None


def _humanize_group_suffix(suffix: str) -> str:
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


def _is_supported_group_suffix(suffix: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]*G\d+", suffix))


def _extract_title_from_a1_range(a1_range: str) -> str:
    if "!" not in a1_range:
        return a1_range.strip().strip("'")

    title_part = a1_range.split("!", 1)[0].strip()
    if title_part.startswith("'") and title_part.endswith("'"):
        title_part = title_part[1:-1].replace("''", "'")
    return title_part


def _escape_sheet_title(title: str) -> str:
    return title.replace("'", "''")


def _parse_group_rows(
    group: GroupInfo,
    rows: list[list[Any]],
    used_student_ids: set[int],
) -> list[dict[str, Any]]:
    if not rows:
        return []

    lesson_number_row = rows[1] if len(rows) > 1 else []
    lesson_name_row = rows[2] if len(rows) > 2 else []
    exam_columns = list(range(2, 20))  # C..T
    exam_column_meta = _build_exam_columns_metadata(lesson_name_row, exam_columns)
    homework_columns_meta = _build_homework_columns_metadata(rows, lesson_number_row)
    coins_by_name = _extract_coins_by_name(rows)

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

    return parsed_rows


def _cell_value(row: list[Any], index: int) -> Any:
    if index < 0 or index >= len(row):
        return None
    return row[index]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _parse_numeric_score(value: Any) -> float | None:
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


def _parse_attendance_markers(value: Any) -> tuple[int, int, int]:
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


def _is_student_data_row(row: list[Any]) -> bool:
    row_index_marker = _parse_numeric_score(_cell_value(row, 0))
    student_name = _normalize_whitespace(_to_text(_cell_value(row, 1)))
    return row_index_marker is not None and bool(student_name)


def _build_homework_columns_metadata(
    rows: list[list[Any]],
    lesson_number_row: list[Any],
) -> list[dict[str, Any]]:
    max_columns = max((len(row) for row in rows), default=0)
    start_column = 21  # V

    metadata: list[dict[str, Any]] = []
    for column_index in range(start_column, max_columns):
        raw_label = _to_text(_cell_value(lesson_number_row, column_index))
        if not raw_label:
            continue

        label = _normalize_whitespace(raw_label.replace("\n", " "))
        next_label = _to_text(_cell_value(lesson_number_row, column_index + 1))
        if next_label:
            score_column_index = column_index
        else:
            score_column_index = min(column_index + 1, max_columns - 1)

        metadata.append(
            {
                "attendance_column_index": column_index,
                "score_column_index": score_column_index,
                "label": label,
            }
        )

    return metadata


def _build_exam_columns_metadata(
    lesson_name_row: list[Any],
    exam_columns: list[int],
) -> list[dict[str, Any]]:
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


def _normalize_exam_name(value: str) -> str:
    if not value:
        return ""

    normalized = _normalize_whitespace(value.replace("\n", " "))
    normalized = normalized.replace(" - ", "-")
    return normalized


def _extract_coins_by_name(rows: list[list[Any]]) -> dict[str, int]:
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


def _normalize_name_key(name: str) -> str:
    return _normalize_whitespace(name).casefold()


def _format_assessment_date(raw_value: Any, fallback_label: str) -> str:
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


def _split_student_name(full_name: str) -> dict[str, str]:
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


def _build_stable_student_id(key: str, used_student_ids: set[int]) -> int:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    candidate = int(digest[:8], 16)
    while candidate in used_student_ids:
        candidate += 1
    used_student_ids.add(candidate)
    return candidate
