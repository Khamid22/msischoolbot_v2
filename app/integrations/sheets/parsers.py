from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.config.schools import DEFAULT_SCHOOL_CODE

from .constants import (
    Columns,
    EXACT_GROUP_DISPLAY_NAMES,
    SEHRIYO_SUBJECT_ALIASES,
    SUBJECT_NAMES,
)
from .utils import (
    average_grade_column_index,
    build_stable_student_id,
    build_student_row_key,
    cell_value,
    format_lesson_date,
    humanize_group_suffix,
    is_excluded_homework_session,
    is_chemistry_group,
    is_sehriyo_chemistry_group,
    is_student_data_row,
    is_supported_group_suffix,
    legacy_sehriyo_class_key,
    normalize_exam_name,
    normalize_group_code,
    normalize_name_key,
    normalize_school_code,
    normalize_sehriyo_class_name,
    normalize_whitespace,
    parse_attendance_markers,
    parse_numeric_score,
    school_display_name,
    should_skip_homework_lesson,
    split_student_name,
    split_subject_and_suffix,
    to_text,
)


@dataclass(frozen=True)
class GroupInfo:
    title: str
    normalized_code: str
    subject_code: str
    subject_name: str
    group_display_name: str
    school_code: str


@dataclass(frozen=True)
class LessonMeta:
    attendance_column_index: int
    score_column_index: int
    label: str
    topic: str
    date: str
    session_type: str = ""
    include_homework: bool = True
    include_attendance: bool = True
    include_in_lesson_catalog: bool = True


@dataclass(frozen=True)
class ExamMeta:
    column_index: int
    exam_name: str
    attempt_name: str
    label: str


@dataclass(frozen=True)
class HeaderRows:
    lesson_date_row: list[Any]
    lesson_number_row: list[Any]
    lesson_name_row: list[Any]


def parse_group_info(sheet_title, school_code):
    normalized_school_code = normalize_school_code(school_code)
    if normalized_school_code == "sehriyo":
        return parse_sehriyo_group_info(sheet_title)

    normalized_code = normalize_group_code(sheet_title)
    if not normalized_code:
        return None

    subject_code, suffix = split_subject_and_suffix(normalized_code)
    if not subject_code or not suffix:
        return None

    if not is_supported_group_suffix(suffix):
        return None

    subject_name = SUBJECT_NAMES.get(subject_code)
    if not subject_name:
        return None

    if normalized_code in EXACT_GROUP_DISPLAY_NAMES:
        group_display_name = EXACT_GROUP_DISPLAY_NAMES[normalized_code]
    else:
        group_display_name = humanize_group_suffix(suffix)

    return GroupInfo(
        title=sheet_title,
        normalized_code=normalized_code,
        subject_code=subject_code,
        subject_name=subject_name,
        group_display_name=group_display_name,
        school_code=normalized_school_code,
    )


def parse_sehriyo_group_info(sheet_title):
    # Expected format: Class-Subject, for example 7D-Math or 8A-CH.
    title = str(sheet_title or "").strip()
    if not title:
        return None

    parts = re.split(r"\s*[-_–—]\s*", title, maxsplit=1)
    if len(parts) != 2:
        return None

    class_name = normalize_sehriyo_class_name(parts[0])
    subject_token = str(parts[1] or "").strip().upper()
    if not class_name or not subject_token:
        return None

    if not re.fullmatch(r"[0-9]+[A-Z]+", class_name):
        return None

    subject_token = subject_token.translate(
        str.maketrans(
            {
                "А": "A",
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
    )

    subject_code = SEHRIYO_SUBJECT_ALIASES.get(subject_token)
    if not subject_code:
        return None

    subject_name = SUBJECT_NAMES.get(subject_code)
    if not subject_name:
        return None

    # Keep stable student IDs after class-name normalization changes.
    normalized_code = f"{legacy_sehriyo_class_key(class_name)}{subject_code}"
    return GroupInfo(
        title=title,
        normalized_code=normalized_code,
        subject_code=subject_code,
        subject_name=subject_name,
        group_display_name=class_name,
        school_code="sehriyo",
    )


def _scan_rows(rows, group):
    """Single pass over all data rows.

    Returns:
        max_columns   – width of the widest row (needed for homework column ranges)
        coins_by_name – normalised-name → coin total
        student_row_data – list of (row_number, row, full_name) for student rows
    """
    normalized_school_code = normalize_school_code(
        getattr(group, "school_code", DEFAULT_SCHOOL_CODE)
    )
    is_sehriyo = normalized_school_code == "sehriyo"
    is_chemistry = is_chemistry_group(group)
    skip_coins = is_sehriyo and getattr(group, "subject_code", "") == "CHM"
    coins_start_row = 31 if is_sehriyo else 19

    max_columns = 0
    coins_by_name: dict[str, int] = {}
    student_row_data: list = []

    for row_number, row in enumerate(rows, start=1):
        row_len = len(row)
        if row_len > max_columns:
            max_columns = row_len

        # ── Coins ──────────────────────────────────────────────────────────
        if not skip_coins and row_number >= coins_start_row:
            name = normalize_whitespace(to_text(cell_value(row, Columns.STUDENT_INDEX_MARKER)))
            if not name:
                name = normalize_whitespace(to_text(cell_value(row, Columns.STUDENT_NAME)))
            if name and "TOTAL COINS" not in name.upper():
                coins_value = parse_numeric_score(cell_value(row, Columns.COINS))
                if coins_value is not None:
                    coins_by_name[normalize_name_key(name)] = int(round(coins_value))

        # ── Student rows ────────────────────────────────────────────────────
        full_name = normalize_whitespace(to_text(cell_value(row, Columns.STUDENT_NAME)))
        if not full_name:
            continue
        if full_name.casefold() in {"student name", "lesson aap", "submission rate"}:
            continue

        if is_chemistry:
            if row_number < 4 or row_number > 19:
                continue
        elif is_sehriyo:
            if row_number < 4 or row_number > 19:
                continue
        else:
            if not is_student_data_row(row):
                continue

        student_row_data.append((row_number, row, full_name))

    return max_columns, coins_by_name, student_row_data


def parse_group_rows(
    group,
    rows,
    used_student_ids,
):
    if not rows:
        return [], []

    header_rows = HeaderRows(
        lesson_date_row=rows[0] if len(rows) > 0 else [],
        lesson_number_row=rows[1] if len(rows) > 1 else [],
        lesson_name_row=rows[2] if len(rows) > 2 else [],
    )

    exam_columns = list(range(Columns.EXAM_START, Columns.EXAM_END_EXCLUSIVE))  # C..T

    exam_column_meta = build_exam_column_meta(header_rows.lesson_name_row, exam_columns)

    # Single combined pass: max column width, coins, and student rows.
    max_columns, coins_by_name, student_row_data = _scan_rows(rows, group)

    homework_columns_meta = build_homework_column_meta(
        group,
        header_rows.lesson_number_row,
        header_rows.lesson_name_row,
        header_rows.lesson_date_row,
        max_columns,
    )
    lesson_catalog = build_lesson_catalog(homework_columns_meta)

    parsed_rows = []
    for row_number, row, full_name in student_row_data:
        parsed_row = parse_student_row(
            group=group,
            row_number=row_number,
            row=row,
            full_name=full_name,
            exam_column_meta=exam_column_meta,
            homework_columns_meta=homework_columns_meta,
            coins_by_name=coins_by_name,
            used_student_ids=used_student_ids,
        )
        if parsed_row is not None:
            parsed_rows.append(parsed_row)

    return parsed_rows, lesson_catalog


def build_exam_column_meta(
    lesson_name_row,
    exam_columns,
):
    meta: list[ExamMeta] = []
    current_exam_name = ""

    for index, column_index in enumerate(exam_columns, start=1):
        header_name = normalize_exam_name(to_text(cell_value(lesson_name_row, column_index)))
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
            ExamMeta(
                column_index=column_index,
                exam_name=current_exam_name or "Exam",
                attempt_name=attempt_name,
                label=label,
            )
        )

    return meta


def build_homework_column_meta(
    group,
    lesson_number_row,
    lesson_topic_row,
    lesson_date_row,
    max_columns,
):
    # max_columns is pre-computed by _scan_rows so trailing score columns are not
    # dropped when header rows are shorter than student rows.
    if is_chemistry_group(group):
        return build_chemistry_homework_column_meta(
            lesson_number_row,
            lesson_topic_row,
            lesson_date_row,
            max_columns,
        )

    metadata: list[LessonMeta] = []
    for column_index in range(Columns.HOMEWORK_START, max_columns):
        raw_label = to_text(cell_value(lesson_number_row, column_index))
        if not raw_label:
            continue

        label = normalize_whitespace(raw_label.replace("\n", " "))
        if should_skip_homework_lesson(label):
            continue

        next_label = to_text(cell_value(lesson_number_row, column_index + 1))
        if next_label:
            score_column_index = column_index
        else:
            score_column_index = min(column_index + 1, max_columns - 1)
        attendance_column_index = column_index

        raw_topic = to_text(cell_value(lesson_topic_row, column_index))
        if not raw_topic and score_column_index != column_index:
            raw_topic = to_text(cell_value(lesson_topic_row, score_column_index))

        raw_date = cell_value(lesson_date_row, column_index)
        if (
            (raw_date is None or to_text(raw_date) == "")
            and score_column_index != column_index
        ):
            raw_date = cell_value(lesson_date_row, score_column_index)
        lesson_date = format_lesson_date(raw_date)

        topic = normalize_whitespace(raw_topic.replace("\n", " "))
        if not topic:
            topic = "Topic"
        if is_excluded_homework_session(label, topic):
            continue

        metadata.append(
            LessonMeta(
                attendance_column_index=attendance_column_index,
                score_column_index=score_column_index,
                label=label,
                topic=topic,
                date=lesson_date,
            )
        )

    return metadata


def build_chemistry_homework_column_meta(
    lesson_number_row,
    lesson_topic_row,
    lesson_date_row,
    max_columns,
):
    def _is_cancelled_marker(value):
        normalized = str(value or "").strip().casefold()
        return "cancelled" in normalized or "canceled" in normalized

    def _is_homework_marker(value):
        normalized = re.sub(r"\s+", "", str(value or "").strip().casefold())
        if not normalized:
            return False
        if "homework" in normalized:
            return True
        return normalized in {"hw", "h/w", "h.w"}

    def _is_date_like(value):
        text = str(value or "").strip()
        if not text or _is_homework_marker(text):
            return False
        return bool(re.search(r"\d", text) and any(sep in text for sep in ("/", "-", ".")))

    def _normalized_cell_text(row, column_index):
        return normalize_whitespace(to_text(cell_value(row, column_index)).replace("\n", " "))

    def _strip_topic_suffix(value):
        return re.sub(
            r"\s*\((?:lesson|lab)\)\s*$",
            "",
            str(value or ""),
            flags=re.IGNORECASE,
        ).strip()

    def _topic_session_type(topic_value):
        topic_text = str(topic_value or "").strip()
        if re.search(r"\(\s*lab\s*\)\s*$", topic_text, flags=re.IGNORECASE):
            return "Lab"
        if re.search(r"\(\s*(?:lesson|lecture)\s*\)\s*$", topic_text, flags=re.IGNORECASE):
            return "Lecture"
        return ""

    def _extract_lesson_label(label_value):
        raw_text = normalize_whitespace(str(label_value or "").strip())
        if not raw_text:
            return ""
        match = re.search(r"\b(?:lesson|l)\s*(\d{1,3})\b", raw_text, flags=re.IGNORECASE)
        if not match:
            return ""
        lesson_number = str(int(match.group(1)))
        if re.fullmatch(r"l\s*\d{1,3}", raw_text, flags=re.IGNORECASE):
            return f"L{lesson_number}"
        return f"Lesson {lesson_number}"

    def _is_lesson_label(label_value):
        return bool(_extract_lesson_label(label_value))

    def _has_neighbor_session_context(column_index):
        for neighbor_index in (column_index - 2, column_index - 1, column_index + 1):
            if neighbor_index < Columns.HOMEWORK_START or neighbor_index >= max_columns:
                continue

            neighbor_label = _normalized_cell_text(lesson_number_row, neighbor_index)
            if _is_lesson_label(neighbor_label):
                return True

            neighbor_topic_raw = _normalized_cell_text(lesson_topic_row, neighbor_index)
            if _topic_session_type(neighbor_topic_raw):
                return True

        return False

    metadata: list[LessonMeta] = []
    # Chemistry can include cancellation/month separator columns that break fixed
    # V/W/X triplet alignment. Scan each column by content instead.
    active_lesson_label = ""
    latest_lesson_label = ""
    latest_topic = ""
    topic_by_lesson: dict[str, str] = {}
    for column_index in range(Columns.HOMEWORK_START, max_columns):
        label = _normalized_cell_text(lesson_number_row, column_index)
        topic_raw = _normalized_cell_text(lesson_topic_row, column_index)
        topic = _strip_topic_suffix(topic_raw)
        lesson_date = format_lesson_date(cell_value(lesson_date_row, column_index))

        is_cancelled = _is_cancelled_marker(label) or _is_cancelled_marker(topic_raw)
        is_homework = _is_homework_marker(label) or _is_homework_marker(lesson_date)

        inferred_label = _extract_lesson_label(label)
        if inferred_label:
            active_lesson_label = inferred_label
            latest_lesson_label = inferred_label

        session_type = ""
        topic_type = _topic_session_type(topic_raw)
        if topic_type:
            session_type = topic_type
        elif is_homework:
            session_type = "Homework"
        elif _is_lesson_label(label):
            session_type = "Lecture"
        elif (
            not topic
            and not inferred_label
            and (column_index - Columns.HOMEWORK_START) % 3 == 2
            and _is_date_like(lesson_date)
            and _has_neighbor_session_context(column_index)
        ):
            # Backward compatibility for legacy chemistry sheets where H/W
            # columns were plain date cells in fixed triplets.
            session_type = "Homework"

        if topic:
            if topic_type or (is_cancelled and _topic_session_type(topic_raw)):
                latest_topic = topic
                if active_lesson_label:
                    topic_by_lesson[active_lesson_label] = topic

        if session_type in {"Lecture", "Lab"}:
            if is_cancelled:
                continue

            resolved_label = inferred_label or active_lesson_label or latest_lesson_label or label
            resolved_topic = (
                topic
                or topic_by_lesson.get(resolved_label, "")
                or latest_topic
                or "Topic"
            )
            if resolved_label and resolved_topic:
                topic_by_lesson[resolved_label] = resolved_topic
                latest_lesson_label = resolved_label

            metadata.append(
                LessonMeta(
                    attendance_column_index=column_index,
                    score_column_index=column_index,
                    label=resolved_label,
                    topic=resolved_topic,
                    date=lesson_date,
                    session_type=session_type,
                    include_homework=False,
                    include_attendance=True,
                    include_in_lesson_catalog=False,
                )
            )
            continue

        if session_type == "Homework":
            if is_cancelled:
                continue

            resolved_label = inferred_label or active_lesson_label or latest_lesson_label
            if not resolved_label:
                resolved_label = label or "H/W"

            resolved_topic = (
                topic
                or topic_by_lesson.get(resolved_label, "")
                or latest_topic
                or "Topic"
            )
            if resolved_label and resolved_topic:
                topic_by_lesson[resolved_label] = resolved_topic
                latest_lesson_label = resolved_label

            metadata.append(
                LessonMeta(
                    attendance_column_index=column_index,
                    score_column_index=column_index,
                    label=resolved_label,
                    topic=resolved_topic,
                    # Chemistry homework uses a static marker instead of date.
                    date="HOMEWORK",
                    session_type="Homework",
                    include_homework=True,
                    include_attendance=False,
                    include_in_lesson_catalog=True,
                )
            )

    return metadata


def build_lesson_catalog(homework_columns_meta):
    lesson_catalog = []
    lesson_order = 0
    for lesson_meta in homework_columns_meta:
        if not lesson_meta.include_in_lesson_catalog:
            continue
        lesson_order += 1
        lesson_catalog.append(
            {
                "lesson_number": str(lesson_meta.label).strip(),
                "lesson_topic": str(lesson_meta.topic).strip(),
                "lesson_date": str(lesson_meta.date).strip(),
                "lesson_order": lesson_order,
            }
        )
    return lesson_catalog


def parse_student_row(
    group,
    row_number,
    row,
    full_name,
    exam_column_meta,
    homework_columns_meta,
    coins_by_name,
    used_student_ids,
):
    del row_number

    split_name = split_student_name(full_name)

    exam_results = []
    for exam_meta in exam_column_meta:
        score = parse_numeric_score(cell_value(row, exam_meta.column_index))
        if score is None:
            continue

        exam_results.append(
            {
                "label": exam_meta.label,
                "examName": exam_meta.exam_name,
                "attempt": exam_meta.attempt_name,
                "score": score,
            }
        )

    homework_grades = []
    attendance_lessons = []
    present_count = 0
    absent_count = 0
    justified_absent_count = 0
    for lesson_meta in homework_columns_meta:
        attendance_cell = cell_value(row, lesson_meta.attendance_column_index)
        score_cell = cell_value(row, lesson_meta.score_column_index)

        if lesson_meta.include_homework:
            score = parse_numeric_score(score_cell)
            if (
                score is None
                and lesson_meta.score_column_index != lesson_meta.attendance_column_index
            ):
                score = parse_numeric_score(attendance_cell)
            if score is not None:
                homework_grades.append(
                    {
                        "lesson": lesson_meta.label,
                        "topic": lesson_meta.topic,
                        "date": lesson_meta.date,
                        "type": lesson_meta.session_type or "Homework",
                        "score": score,
                    }
                )

        if lesson_meta.include_attendance:
            p, a, ai = parse_attendance_markers(attendance_cell)
            if lesson_meta.score_column_index != lesson_meta.attendance_column_index:
                p2, a2, ai2 = parse_attendance_markers(score_cell)
                p += p2
                a += a2
                ai += ai2

            if ai > 0:
                attendance_status = "justified"
            elif a > 0:
                attendance_status = "absent"
            elif p > 0:
                attendance_status = "present"
            else:
                attendance_status = ""

            if attendance_status:
                attendance_lessons.append(
                    {
                        "lesson": lesson_meta.label,
                        "topic": lesson_meta.topic,
                        "date": lesson_meta.date,
                        "attendanceType": lesson_meta.session_type,
                        "status": attendance_status,
                    }
                )

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

    average_grade_cell = parse_numeric_score(
        cell_value(row, average_grade_column_index(group))
    )
    if average_grade_cell is None and is_sehriyo_chemistry_group(group):
        average_grade_cell = parse_numeric_score(
            cell_value(row, Columns.SEHRIYO_CHEMISTRY_AVERAGE_GRADE)
        )
    if average_grade_cell is not None:
        average_grade = float(average_grade_cell)
    else:
        graded_count = len(exam_results)
        average_grade = (
            (sum(result["score"] for result in exam_results) / graded_count)
            if graded_count
            else 0.0
        )

    total_count = present_count + absent_count + justified_absent_count

    student_id = build_stable_student_id(
        key=build_student_row_key(group, full_name),
        used_student_ids=used_student_ids,
    )

    coins = coins_by_name.get(normalize_name_key(full_name), 0)

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
        "schoolCode": group.school_code,
        "schoolName": school_display_name(group.school_code),
        "coins": coins,
    }

    dashboard = {
        "student": student,
        "academicRecords": academic_records,
        "examResults": exam_results,
        "homeworkGrades": homework_grades,
        "attendanceLessons": attendance_lessons,
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

    return {"student": student, "dashboard": dashboard}
