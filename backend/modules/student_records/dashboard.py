import math
import re
import threading
import time

from backend.core.request_context import session
from backend.core.session import url_for

from backend.modules.academics import canonical
from backend.modules.student_records.service import (
    get_dashboard_student_profile,
    get_student_db_id_by_enrollment_id,
)
from .lesson_catalog import get_lessons_for_subject
from backend.modules.academics.rating import (
    compute_subject_rating,
    extract_attendance_rate,
    extract_exam_average_score,
    load_dataset,
    round_grade_half_up,
)
from backend.modules.academics.canonical import normalize_text
from backend.core.session import current_auth_role, current_student_db_id


_SUBJECT_SWITCH_CACHE_LOCK = threading.Lock()
_SUBJECT_SWITCH_CACHE = {}
_SUBJECT_SWITCH_CACHE_TTL_SECONDS = 60


def subject_short_name(subject_name):
    return canonical.subject_short_name(subject_name)


def extract_aap_remark(score):
    if score is None:
        return "Not Graded", "remark-muted"
    if score <= 4:
        return "Fail", "remark-fail"
    if score <= 7:
        return "Satisfactory", "remark-satisfactory"
    return "Excellent", "remark-excellent"


def extract_attendance_remark(status):
    normalized = str(status or "").strip().casefold()
    if normalized == "present":
        return "Present", "remark-excellent"
    if normalized == "absent":
        return "Absent", "remark-fail"
    if normalized == "justified":
        return "Justified", "remark-satisfactory"
    return "N/A", "remark-muted"


def extract_program_total_lessons(payload, dataset, subject_name, group_name):
    """Read the real program length; never invent a school-wide constant."""
    payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
    if isinstance(payload_student, dict):
        try:
            payload_total = int(payload_student.get("programLessonCount") or 0)
        except (TypeError, ValueError):
            payload_total = 0
        if payload_total > 0:
            return payload_total

    if not isinstance(dataset, dict):
        return 0
    grouped = dataset.get("lesson_catalog_by_subject_group", {})
    subject_groups = grouped.get(subject_name, {}) if isinstance(grouped, dict) else {}
    lessons = subject_groups.get(group_name, []) if isinstance(subject_groups, dict) else []
    if not lessons:
        by_subject = dataset.get("lesson_catalog_by_subject", {})
        lessons = by_subject.get(subject_name, []) if isinstance(by_subject, dict) else []
    if not isinstance(lessons, list):
        return 0
    lesson_numbers = {
        str(row.get("lesson_number") or "").strip().casefold()
        for row in lessons
        if isinstance(row, dict) and str(row.get("lesson_number") or "").strip()
    }
    return len(lesson_numbers)


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


def _build_lesson_catalog_rows(
    *,
    lesson_catalog,
    lesson_data_by_lesson,
    topic_key,
    date_key,
):
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

    for lesson_number, lesson_item in lesson_data_by_lesson.items():
        dedupe_key = lesson_number.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        max_lesson_order += 1
        lesson_catalog.append(
            {
                "lesson_number": lesson_number,
                "lesson_topic": str(lesson_item.get(topic_key, "")).strip(),
                "lesson_date": str(lesson_item.get(date_key, "")).strip(),
                "lesson_order": max_lesson_order,
            }
        )

    return lesson_catalog


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

    # Primary source: the student's own enrollments straight from the DB. This is
    # reliable for multi-subject students and does not depend on loading and
    # name-matching the whole school dataset (which can silently yield nothing at
    # runtime, collapsing the switcher to a single subject). Dataset matching
    # below remains a fallback when the DB source is unavailable.
    try:
        from backend.modules.student_records.service import (
            get_student_subject_enrollments,
        )

        db_options = get_student_subject_enrollments(current_student_id)
    except Exception:
        db_options = []
    if db_options:
        seen_db = set()
        for entry in db_options:
            key = (entry["student_id"], entry["subject"], entry["group"])
            if key in seen_db:
                continue
            seen_db.add(key)
            options.append(
                {
                    "student_id": entry["student_id"],
                    "subject": entry["subject"],
                    "subject_short": subject_short_name(entry["subject"]),
                    "group": entry["group"],
                }
            )
        options.sort(
            key=lambda item: (
                normalize_text(item.get("subject", "")),
                normalize_text(item.get("group", "")),
                int(item.get("student_id", 0)),
            )
        )

    cache_key = (int(id(dataset)), current_name_norm)
    if not options and isinstance(dataset, dict) and current_name_norm:
        now = time.time()
        with _SUBJECT_SWITCH_CACHE_LOCK:
            cached_entry = _SUBJECT_SWITCH_CACHE.get(cache_key)
            if (
                cached_entry
                and cached_entry.get("dataset_obj") is dataset
                and now < float(cached_entry.get("expires_at", 0))
            ):
                options = [dict(item) for item in cached_entry.get("options", [])]

    if not options and current_name_norm:
        seen = set()
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

        if isinstance(dataset, dict):
            now = time.time()
            with _SUBJECT_SWITCH_CACHE_LOCK:
                _SUBJECT_SWITCH_CACHE[cache_key] = {
                    "dataset_obj": dataset,
                    "options": [dict(item) for item in options],
                    "expires_at": now + _SUBJECT_SWITCH_CACHE_TTL_SECONDS,
                }
                expired_keys = [
                    key
                    for key, entry in _SUBJECT_SWITCH_CACHE.items()
                    if float(entry.get("expires_at", 0)) <= now
                ]
                for key in expired_keys:
                    _SUBJECT_SWITCH_CACHE.pop(key, None)
                if len(_SUBJECT_SWITCH_CACHE) > 256:
                    ordered_entries = sorted(
                        _SUBJECT_SWITCH_CACHE.items(),
                        key=lambda item: float(item[1].get("expires_at", 0)),
                    )
                    for key, _entry in ordered_entries[: len(_SUBJECT_SWITCH_CACHE) - 256]:
                        _SUBJECT_SWITCH_CACHE.pop(key, None)

    if not options:
        options = [
            {
                "student_id": int(current_student_id),
                "subject": current_subject_name,
                "subject_short": subject_short_name(current_subject_name),
                "group": current_group_name,
            }
        ]

    current_subject_norm = normalize_text(current_subject_name)
    current_group_norm = normalize_text(current_group_name)

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

        option["is_current"] = (
            option_student_id == int(current_student_id)
            and (
                not current_subject_norm
                or normalize_text(option_subject) == current_subject_norm
            )
            and (
                not current_group_norm
                or normalize_text(option_group) == current_group_norm
            )
        )
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

    auth_role = current_auth_role()
    resolved_student_db_id = current_student_db_id() if auth_role == "student" else None
    if not resolved_student_db_id:
        resolved_student_db_id = get_student_db_id_by_enrollment_id(
            student_id,
            school_code=current_school_code,
        )
        if resolved_student_db_id and auth_role == "student":
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
    program_total_lessons = extract_program_total_lessons(
        payload,
        dataset_for_subject_switch or dataset,
        current_subject_name,
        current_group_name,
    )
    raw_completed_lessons = max(0, extract_last_completed_lesson(payload))
    completed_lessons = (
        min(raw_completed_lessons, program_total_lessons)
        if program_total_lessons > 0
        else raw_completed_lessons
    )
    program_completed_rate = (
        round((completed_lessons / program_total_lessons) * 100)
        if program_total_lessons > 0
        else 0
    )
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
    ar_lessons_url = url_for(
        "student.ar_lessons",
        student_id=student_id,
        subject=requested_subject or current_subject_name,
        group=requested_group or current_group_name,
        school=current_school_code,
    )

    dashboard_back_url = url_for("student.home")
    if auth_role == "admin":
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
    elif auth_role == "parent":
        dashboard_back_url = url_for("student.home")

    return {
        "payload": payload,
        "attendance_rate": attendance_rate,
        "exam_performance": exam_performance,
        "program_completed_lessons": completed_lessons,
        "program_total_lessons": program_total_lessons,
        "program_completed_rate": program_completed_rate,
        "subject_rating": subject_rating,
        "rating_board_url": rating_board_url,
        "resources_url": resources_url,
        "aap_lessons_url": aap_lessons_url,
        "ar_lessons_url": ar_lessons_url,
        "current_subject_name": current_subject_name,
        "current_subject_short_name": current_subject_short_name,
        "subject_switch_options": subject_switch_options,
        "student_profile": student_profile,
        "profile_notice": profile_notice,
        "profile_error": profile_error,
        "dashboard_back_url": dashboard_back_url,
        "show_dashboard_back": auth_role in {"admin", "parent"},
    }


def build_aap_lessons_page_context(
    *,
    student_id,
    payload,
    requested_subject,
    requested_group,
    requested_school,
    force_refresh=False,
):
    payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
    subject_name = str(payload_student.get("subject", "")).strip() or "Unknown"
    group_name = str(payload_student.get("group", "")).strip()
    full_name = str(payload_student.get("fullName", "")).strip()
    current_school_code = (
        str(payload_student.get("schoolCode", "")).strip() or requested_school
    )

    homework_grades = payload.get("homeworkGrades", [])
    if not isinstance(homework_grades, list):
        homework_grades = []

    lesson_rows = []
    is_chemistry = normalize_text(subject_name) == "chemistry"
    if is_chemistry:
        for item in homework_grades:
            if not isinstance(item, dict):
                continue

            lesson_number = str(item.get("lesson", "")).strip()
            lesson_topic = str(item.get("topic", "")).strip()
            task_name = lesson_number or "Homework"

            if not lesson_number and not lesson_topic:
                continue

            raw_score = item.get("score")
            lesson_score = None
            try:
                score = float(raw_score)
                if math.isfinite(score):
                    lesson_score = max(0, min(9, round_grade_half_up(score)))
            except (TypeError, ValueError):
                lesson_score = None

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
                    "lesson_date_display": task_name,
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
    else:
        lesson_catalog, lesson_error = get_lessons_for_subject(
            subject_name,
            group_name,
        )
        if lesson_error:
            return None, lesson_error, 503

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

        lesson_catalog = _build_lesson_catalog_rows(
            lesson_catalog=lesson_catalog,
            lesson_data_by_lesson={
                lesson_number: {
                    "topic": topic_by_lesson.get(lesson_number, ""),
                    "date": date_by_lesson.get(lesson_number, ""),
                }
                for lesson_number in grade_by_lesson.keys()
            },
            topic_key="topic",
            date_key="date",
        )

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


def build_ar_lessons_page_context(
    *,
    student_id,
    payload,
    requested_subject,
    requested_group,
    requested_school,
    force_refresh=False,
):
    payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
    subject_name = str(payload_student.get("subject", "")).strip() or "Unknown"
    group_name = str(payload_student.get("group", "")).strip()
    full_name = str(payload_student.get("fullName", "")).strip()
    current_school_code = (
        str(payload_student.get("schoolCode", "")).strip() or requested_school
    )

    attendance_lessons = payload.get("attendanceLessons", [])
    if not isinstance(attendance_lessons, list):
        attendance_lessons = []

    lesson_rows = []
    is_chemistry = normalize_text(subject_name) == "chemistry"
    is_amir_online = (
        normalize_text(full_name) in {"amir", "амир"}
        and "online" in normalize_text(group_name)
    )
    if is_chemistry or is_amir_online:
        for item in attendance_lessons:
            if not isinstance(item, dict):
                continue

            lesson_number = str(item.get("lesson", "")).strip()
            lesson_topic = str(item.get("topic", "")).strip()
            lesson_date = str(item.get("date", "")).strip()

            if not lesson_number and not lesson_topic:
                continue

            status = str(item.get("status", "")).strip().casefold()
            if status not in {"present", "absent", "justified"}:
                continue

            raw_type = str(
                item.get("attendanceType")
                or item.get("type")
                or ""
            ).strip().casefold()
            if raw_type in {"lesson", "lecture"}:
                attendance_type = "Lecture"
            elif raw_type == "lab":
                attendance_type = "Lab"
            else:
                attendance_type = ""

            # Backward-compatible inference for old payloads that encoded type
            # in the topic text instead of a dedicated field.
            if not attendance_type:
                normalized_topic = lesson_topic.casefold()
                if normalized_topic.endswith("(lesson)"):
                    attendance_type = "Lecture"
                elif normalized_topic.endswith("(lab)"):
                    attendance_type = "Lab"
            lesson_topic = re.sub(
                r"\s*\((?:lesson|lab)\)\s*$",
                "",
                lesson_topic,
                flags=re.IGNORECASE,
            ).strip()

            remark, remark_class = extract_attendance_remark(status)
            lesson_rows.append(
                {
                    "lesson_number": lesson_number,
                    "lesson_topic": lesson_topic or "Topic unavailable",
                    "lesson_date_display": lesson_date or "Not conducted",
                    "attendance_type": attendance_type,
                    "attendance_status": status,
                    "attendance_display": remark,
                    "remark_class": remark_class,
                }
            )
    else:
        lesson_catalog, lesson_error = get_lessons_for_subject(
            subject_name,
            group_name,
        )
        if lesson_error:
            return None, lesson_error, 503

        parsed_attendance_rows = []
        deduped_lesson_data = {}
        for item in attendance_lessons:
            if not isinstance(item, dict):
                continue

            lesson_number = str(item.get("lesson", "")).strip()
            status = str(item.get("status", "")).strip().casefold()
            if status not in {"present", "absent", "justified"}:
                continue

            lesson_topic = str(item.get("topic", "")).strip()
            lesson_date = str(item.get("date", "")).strip()
            if not lesson_number and not lesson_topic:
                continue

            parsed_attendance_rows.append(
                {
                    "lesson_number": lesson_number,
                    "status": status,
                    "topic": lesson_topic,
                    "date": lesson_date,
                }
            )

            # Keep catalog enrichment backward-compatible while preserving all
            # raw attendance rows (including repeated "Cancelled" sessions).
            if lesson_number and lesson_number not in deduped_lesson_data:
                deduped_lesson_data[lesson_number] = {
                    "topic": lesson_topic,
                    "date": lesson_date,
                }

        lesson_catalog = _build_lesson_catalog_rows(
            lesson_catalog=lesson_catalog,
            lesson_data_by_lesson=deduped_lesson_data,
            topic_key="topic",
            date_key="date",
        )

        used_attendance_indexes = set()
        for lesson in lesson_catalog:
            lesson_number = str(lesson.get("lesson_number", "")).strip()
            lesson_topic = str(lesson.get("lesson_topic", "")).strip()
            lesson_date = str(lesson.get("lesson_date", "")).strip()
            if not lesson_number:
                continue

            lesson_status = ""
            matched_topic = ""
            matched_date = ""
            for idx, attendance_row in enumerate(parsed_attendance_rows):
                if idx in used_attendance_indexes:
                    continue
                if str(attendance_row.get("lesson_number", "")).strip() != lesson_number:
                    continue
                used_attendance_indexes.add(idx)
                lesson_status = str(attendance_row.get("status", "")).strip().casefold()
                matched_topic = str(attendance_row.get("topic", "")).strip()
                matched_date = str(attendance_row.get("date", "")).strip()
                break

            if matched_topic:
                lesson_topic = matched_topic
            if not lesson_date:
                lesson_date = matched_date

            remark, remark_class = extract_attendance_remark(lesson_status)
            lesson_rows.append(
                {
                    "lesson_number": lesson_number,
                    "lesson_topic": lesson_topic or "Topic unavailable",
                    "lesson_date_display": lesson_date or "Not conducted",
                    "attendance_type": "",
                    "attendance_status": lesson_status,
                    "attendance_display": remark,
                    "remark_class": remark_class,
                }
            )

        # Include attendance rows that are not represented in lesson catalog,
        # such as repeated "Cancelled" sessions with different dates/reasons.
        for idx, attendance_row in enumerate(parsed_attendance_rows):
            if idx in used_attendance_indexes:
                continue

            lesson_status = str(attendance_row.get("status", "")).strip().casefold()
            if lesson_status not in {"present", "absent", "justified"}:
                continue

            remark, remark_class = extract_attendance_remark(lesson_status)
            lesson_rows.append(
                {
                    "lesson_number": str(
                        attendance_row.get("lesson_number", "")
                    ).strip(),
                    "lesson_topic": (
                        str(attendance_row.get("topic", "")).strip()
                        or "Topic unavailable"
                    ),
                    "lesson_date_display": (
                        str(attendance_row.get("date", "")).strip()
                        or "Not conducted"
                    ),
                    "attendance_type": "",
                    "attendance_status": lesson_status,
                    "attendance_display": remark,
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
    "build_ar_lessons_page_context",
    "build_subject_switch_options",
    "extract_aap_remark",
    "extract_attendance_remark",
    "subject_short_name",
]
