import math
import re

from flask import session, url_for

from .auth_service import (
    get_dashboard_student_profile,
    get_student_db_id_by_sheet_student_id,
)
from .lesson_catalog_service import get_lessons_for_subject
from .normalization_service import normalize_text
from .session_state_service import current_auth_role, current_student_db_id


SUBJECT_SHORT_NAMES = {
    "igcse mathematics a": "Math",
    "mathematics": "Math",
    "math": "Math",
    "general english": "Eng",
    "english": "Eng",
    "chemistry": "Chem",
    "biology": "Bio",
    "physics": "Phys",
}

PROGRAM_TOTAL_LESSONS = 180


def subject_short_name(subject_name):
    normalized = normalize_text(subject_name)
    if normalized in SUBJECT_SHORT_NAMES:
        return SUBJECT_SHORT_NAMES[normalized]

    words = [part for part in str(subject_name or "").strip().split() if part]
    if not words:
        return "Subject"
    if len(words) == 1:
        return words[0][:4]
    return words[0][:4]


def extract_aap_remark(score):
    if score is None:
        return "Not Graded", "remark-muted"
    if score <= 4:
        return "Fail", "remark-fail"
    if score <= 7:
        return "Satisfactory", "remark-satisfactory"
    return "Excellent", "remark-excellent"


def _parse_lesson_number(raw_value):
    text = str(raw_value or "").strip()
    if not text:
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    try:
        lesson_number = int(match.group(0))
    except (TypeError, ValueError):
        return None
    if lesson_number <= 0:
        return None
    return lesson_number


def extract_last_completed_lesson(payload):
    homework_grades = payload.get("homeworkGrades", []) if isinstance(payload, dict) else []
    if not isinstance(homework_grades, list):
        homework_grades = []

    max_lesson_number = 0
    for item in homework_grades:
        if not isinstance(item, dict):
            continue
        for candidate in (
            item.get("lesson"),
            item.get("lessonNumber"),
            item.get("lessonLabel"),
            item.get("label"),
        ):
            lesson_number = _parse_lesson_number(candidate)
            if lesson_number is None:
                continue
            if lesson_number > max_lesson_number:
                max_lesson_number = lesson_number
            break

    if max_lesson_number > 0:
        return max_lesson_number

    return len(homework_grades)


def build_subject_switch_options(
    *,
    dataset,
    current_full_name,
    current_student_id,
    current_subject_name,
    current_group_name,
    current_school_code,
):
    students = dataset.get("students", []) if isinstance(dataset, dict) else []
    if not isinstance(students, list):
        students = []

    current_name_norm = normalize_text(current_full_name)
    options = []
    seen = set()

    if current_name_norm:
        for student in students:
            if not isinstance(student, dict):
                continue
            if normalize_text(student.get("fullName", "")) != current_name_norm:
                continue

            option_student_id = student.get("id")
            if not isinstance(option_student_id, int):
                continue

            subject_name = str(student.get("subject", "")).strip()
            group_name = str(student.get("group", "")).strip()
            unique_key = (option_student_id, subject_name, group_name)
            if unique_key in seen:
                continue
            seen.add(unique_key)

            options.append(
                {
                    "student_id": option_student_id,
                    "subject": subject_name,
                    "subject_short": subject_short_name(subject_name),
                    "group": group_name,
                }
            )

    options.sort(
        key=lambda item: (
            normalize_text(item.get("subject", "")),
            normalize_text(item.get("group", "")),
            int(item.get("student_id", 0)),
        )
    )

    if not options:
        options = [
            {
                "student_id": int(current_student_id),
                "subject": current_subject_name,
                "subject_short": subject_short_name(current_subject_name),
                "group": current_group_name,
            }
        ]

    for option in options:
        option_student_id = int(option.get("student_id", current_student_id))
        option_subject = str(option.get("subject", "")).strip()
        option_group = str(option.get("group", "")).strip()

        route_params = {"student_id": option_student_id}
        if option_subject:
            route_params["subject"] = option_subject
        if option_group:
            route_params["group"] = option_group
        if current_school_code:
            route_params["school"] = current_school_code

        option["is_current"] = option_student_id == int(current_student_id)
        option["url"] = url_for("student.dashboard", **route_params)

    return options


def build_dashboard_page_context(
    *,
    student_id,
    payload,
    dataset,
    requested_subject,
    requested_group,
    requested_school,
    admin_return_panel,
    admin_return_school,
    profile_notice,
    profile_error,
    load_dataset,
    extract_attendance_rate,
    extract_exam_average_score,
    round_grade_half_up,
    compute_subject_rating,
    force_refresh=False,
):
    payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
    current_subject_name = str(payload_student.get("subject", "")).strip() or "Unknown"
    current_group_name = str(payload_student.get("group", "")).strip()
    current_full_name = str(payload_student.get("fullName", "")).strip()
    current_school_code = (
        str(payload_student.get("schoolCode", "")).strip() or requested_school
    )

    def load_current_school_dataset(school_code=None, force_refresh_dataset=False):
        normalized_school = str(school_code or current_school_code).strip()
        if normalized_school:
            return load_dataset(
                school_code=normalized_school,
                force_refresh=force_refresh_dataset,
            )
        return load_dataset(force_refresh=force_refresh_dataset)

    resolved_student_db_id = current_student_db_id()
    if not resolved_student_db_id:
        resolved_student_db_id = get_student_db_id_by_sheet_student_id(
            student_id,
            school_code=current_school_code,
        )
        if resolved_student_db_id:
            session["student_db_id"] = resolved_student_db_id

    student_profile = get_dashboard_student_profile(
        student_db_id=resolved_student_db_id,
        full_name=current_full_name,
        group_name=current_group_name,
        subject_name=current_subject_name,
        load_dataset=load_current_school_dataset,
    )

    dataset_for_subject_switch = dataset
    if not dataset_for_subject_switch:
        refreshed_dataset, load_error = load_current_school_dataset(
            force_refresh_dataset=force_refresh,
        )
        if not load_error and refreshed_dataset:
            dataset_for_subject_switch = refreshed_dataset

    subject_switch_options = build_subject_switch_options(
        dataset=dataset_for_subject_switch,
        current_full_name=current_full_name,
        current_student_id=student_id,
        current_subject_name=current_subject_name,
        current_group_name=current_group_name,
        current_school_code=current_school_code,
    )

    current_subject_short_name = subject_short_name(current_subject_name)

    attendance_rate = extract_attendance_rate(payload)
    exam_average_score = extract_exam_average_score(payload)
    exam_performance = (
        round_grade_half_up(exam_average_score)
        if exam_average_score is not None and exam_average_score > 0
        else 0
    )
    completed_lessons = min(
        extract_last_completed_lesson(payload),
        PROGRAM_TOTAL_LESSONS,
    )
    program_completed_rate = round((completed_lessons / PROGRAM_TOTAL_LESSONS) * 100)
    subject_rating = compute_subject_rating(
        student_id=student_id,
        payload=payload,
        dataset=dataset,
    )

    rating_board_url = url_for(
        "student.rating_board",
        student_id=student_id,
        subject=requested_subject or current_subject_name,
        group=requested_group or current_group_name,
        school=current_school_code,
    )
    resources_url = url_for(
        "student.student_resources",
        student_id=student_id,
        subject=requested_subject or current_subject_name,
        group=requested_group or current_group_name,
        school=current_school_code,
    )
    aap_lessons_url = url_for(
        "student.aap_lessons",
        student_id=student_id,
        subject=requested_subject or current_subject_name,
        group=requested_group or current_group_name,
        school=current_school_code,
    )

    dashboard_back_url = url_for("student.home")
    if current_auth_role() == "admin":
        return_panel = admin_return_panel or "students"
        return_school = admin_return_school or str(
            session.get("admin_last_school", "all")
        ).strip().casefold() or "all"
        session["admin_last_panel"] = return_panel
        session["admin_last_school"] = return_school
        dashboard_back_url = url_for(
            "student.home",
            panel=return_panel,
            school=return_school,
        )

    return {
        "payload": payload,
        "attendance_rate": attendance_rate,
        "exam_performance": exam_performance,
        "program_completed_lessons": completed_lessons,
        "program_completed_rate": program_completed_rate,
        "subject_rating": subject_rating,
        "rating_board_url": rating_board_url,
        "resources_url": resources_url,
        "aap_lessons_url": aap_lessons_url,
        "current_subject_name": current_subject_name,
        "current_subject_short_name": current_subject_short_name,
        "subject_switch_options": subject_switch_options,
        "student_profile": student_profile,
        "profile_notice": profile_notice,
        "profile_error": profile_error,
        "dashboard_back_url": dashboard_back_url,
    }


def build_aap_lessons_page_context(
    *,
    student_id,
    payload,
    requested_subject,
    requested_group,
    requested_school,
    load_dataset,
    round_grade_half_up,
    force_refresh=False,
):
    payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
    subject_name = str(payload_student.get("subject", "")).strip() or "Unknown"
    group_name = str(payload_student.get("group", "")).strip()
    full_name = str(payload_student.get("fullName", "")).strip()
    current_school_code = (
        str(payload_student.get("schoolCode", "")).strip() or requested_school
    )

    def load_current_school_dataset(school_code=None, force_refresh_dataset=False):
        normalized_school = str(school_code or current_school_code).strip()
        if normalized_school:
            return load_dataset(
                school_code=normalized_school,
                force_refresh=force_refresh_dataset,
            )
        return load_dataset(force_refresh=force_refresh_dataset)

    lesson_catalog, lesson_error = get_lessons_for_subject(
        subject_name,
        group_name,
        load_current_school_dataset,
    )
    if lesson_error:
        return None, lesson_error, 503

    homework_grades = payload.get("homeworkGrades", [])
    if not isinstance(homework_grades, list):
        homework_grades = []

    grade_by_lesson = {}
    topic_by_lesson = {}
    date_by_lesson = {}
    for item in homework_grades:
        if not isinstance(item, dict):
            continue

        lesson_number = str(item.get("lesson", "")).strip()
        if not lesson_number:
            continue

        raw_score = item.get("score")
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score):
            continue

        grade_by_lesson[lesson_number] = max(0, min(9, round_grade_half_up(score)))

        lesson_topic = str(item.get("topic", "")).strip()
        if lesson_topic:
            topic_by_lesson[lesson_number] = lesson_topic

        lesson_date = str(item.get("date", "")).strip()
        if lesson_date:
            date_by_lesson[lesson_number] = lesson_date

    if not lesson_catalog:
        lesson_catalog = []

    seen = set()
    max_lesson_order = 0
    for lesson in lesson_catalog:
        if not isinstance(lesson, dict):
            continue
        lesson_number = str(lesson.get("lesson_number", "")).strip()
        if not lesson_number:
            continue
        seen.add(lesson_number.casefold())
        try:
            max_lesson_order = max(max_lesson_order, int(lesson.get("lesson_order", 0)))
        except (TypeError, ValueError):
            continue

    for lesson_number in grade_by_lesson.keys():
        dedupe_key = lesson_number.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        max_lesson_order += 1
        lesson_catalog.append(
            {
                "lesson_number": lesson_number,
                "lesson_topic": topic_by_lesson.get(lesson_number, ""),
                "lesson_date": date_by_lesson.get(lesson_number, ""),
                "lesson_order": max_lesson_order,
            }
        )

    lesson_rows = []
    for lesson in lesson_catalog:
        lesson_number = str(lesson.get("lesson_number", "")).strip()
        lesson_topic = str(lesson.get("lesson_topic", "")).strip()
        lesson_date = str(lesson.get("lesson_date", "")).strip()
        if not lesson_number:
            continue
        if not lesson_date:
            lesson_date = str(date_by_lesson.get(lesson_number, "")).strip()

        lesson_score = grade_by_lesson.get(lesson_number)
        remark, remark_class = extract_aap_remark(lesson_score)
        progress_width = (
            int(round((int(lesson_score) / 9) * 100))
            if lesson_score is not None
            else 0
        )
        lesson_rows.append(
            {
                "lesson_number": lesson_number,
                "lesson_topic": lesson_topic or "Topic unavailable",
                "lesson_date_display": lesson_date or "Not conducted",
                "aap_score": lesson_score,
                "aap_display": (
                    f"{int(lesson_score)}/9"
                    if lesson_score is not None
                    else "N/A"
                ),
                "progress_width": max(0, min(progress_width, 100)),
                "remark": remark,
                "remark_class": remark_class,
            }
        )

    back_url = url_for(
        "student.dashboard",
        student_id=student_id,
        subject=requested_subject or subject_name,
        group=requested_group or group_name,
        school=current_school_code,
    )

    return (
        {
            "student_id": student_id,
            "student_full_name": full_name,
            "subject_name": subject_name,
            "lesson_rows": lesson_rows,
            "back_url": back_url,
        },
        "",
        200,
    )


__all__ = [
    "build_dashboard_page_context",
    "build_aap_lessons_page_context",
    "build_subject_switch_options",
    "extract_aap_remark",
    "subject_short_name",
]
