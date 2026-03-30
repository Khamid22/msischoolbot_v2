from __future__ import annotations

from typing import Any

from app.config.schools import get_school_spreadsheet_id

from .auth import (
    SheetsDataError,
    execute_google_request_with_retries,
    extract_google_error_details,
    get_sheets_service,
)
from .parsers import parse_group_info, parse_group_rows
from .utils import (
    escape_sheet_title,
    extract_title_from_a1_range,
    group_sort_key,
    normalize_name_key,
    normalize_school_code,
    subject_sort_key,
)


def load_from_google_sheets(school_code):
    school_code = normalize_school_code(school_code)
    spreadsheet_id = get_school_spreadsheet_id(school_code)
    if not spreadsheet_id:
        raise SheetsDataError(
            "Spreadsheet ID is not set for active school. "
            "Set SCHOOL5_SPREAD_SHEETS (or SEHRIYO_SPREAD_SHEETS for sehriyo)."
        )

    service = get_sheets_service()

    try:
        metadata = execute_google_request_with_retries(
            lambda: service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields="sheets(properties(title))",
            )
        )
    except Exception as exc:
        details = extract_google_error_details(exc)
        raise SheetsDataError(
            f"Failed to read spreadsheet metadata from Google Sheets API. {details}"
        ) from exc

    sheet_titles = [
        sheet.get("properties", {}).get("title", "")
        for sheet in metadata.get("sheets", [])
        if sheet.get("properties", {}).get("title")
    ]

    group_infos = []
    for sheet_title in sheet_titles:
        group_info = parse_group_info(sheet_title, school_code)
        if group_info:
            group_infos.append(group_info)

    if not group_infos:
        expected_pattern = (
            "Use names like 7D-Math or 8A-CH."
            if school_code == "sehriyo"
            else "Use names like MMG1, MAFTG2, ENGMG1."
        )
        raise SheetsDataError(
            f"No valid subject group tabs found. {expected_pattern}"
        )

    ranges = [f"'{escape_sheet_title(group.title)}'!A1:ZZ" for group in group_infos]
    try:
        values_response = execute_google_request_with_retries(
            lambda: service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges,
                majorDimension="ROWS",
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
        )
    except Exception as exc:
        details = extract_google_error_details(exc)
        raise SheetsDataError(
            f"Failed to read worksheet values from Google Sheets API. {details}"
        ) from exc

    values_by_title: dict[str, list[list[Any]]] = {}
    for value_range in values_response.get("valueRanges", []):
        title = extract_title_from_a1_range(value_range.get("range", ""))
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

        parsed_students, group_lesson_catalog = parse_group_rows(
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

    merge_total_coins_across_subjects(students, dashboards_by_id)

    students.sort(
        key=lambda student: (
            subject_sort_key(str(student.get("subject", ""))),
            group_sort_key(str(student.get("group", ""))),
            str(student.get("fullName", "")).casefold(),
        )
    )

    ordered_subjects = sorted(subjects_set, key=subject_sort_key)
    ordered_groups_by_subject = {
        subject: sorted(groups_by_subject.get(subject, set()), key=group_sort_key)
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
        for group_name in sorted(subject_group_map.keys(), key=group_sort_key):
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
        "groups": sorted(groups_set, key=group_sort_key),
        "groups_by_subject": ordered_groups_by_subject,
        "lesson_catalog_by_subject": ordered_lesson_catalog_by_subject,
        "lesson_catalog_by_subject_group": ordered_lesson_catalog_by_subject_group,
        "subjects": ordered_subjects,
    }


def merge_total_coins_across_subjects(students, dashboards_by_id):
    total_coins_by_name: dict[str, int] = {}

    for student in students:
        if not isinstance(student, dict):
            continue
        student_name_key = normalize_name_key(student.get("fullName", ""))
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
        student_name_key = normalize_name_key(student.get("fullName", ""))
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

        student_name_key = normalize_name_key(payload_student.get("fullName", ""))
        if not student_name_key:
            continue

        merged_coins = int(total_coins_by_name.get(student_name_key, 0))
        payload_student["coins"] = merged_coins
        dashboard_payload["coins"] = merged_coins
