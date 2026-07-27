"""Academic dataset caching, subject ratings, and leaderboard building.

This module owns the in-memory caches over the internal academic dataset
(group cache, rating leaderboard cache, students-by-subject-group cache) and
every computation derived from a dashboard payload (attendance rate, exam
averages, subject rating, leaderboard rows).

Route modules import these functions directly — nothing here depends on the
FastAPI app, so there is no registration-time wiring.
"""

import hashlib
import math
import os
import threading
import time

from backend.modules.domains.organization.canonical import (
    normalize_text as _normalize,
    normalize_school_code as _normalize_school_code,
)

GROUP_CACHE_TTL_SECONDS = int(os.environ.get("GROUP_CACHE_TTL_SECONDS", "600"))
RATING_CACHE_TTL_SECONDS = int(os.environ.get("RATING_CACHE_TTL_SECONDS", "60"))
RATING_CACHE_MAX_ENTRIES = int(os.environ.get("RATING_CACHE_MAX_ENTRIES", "128"))

_GROUP_CACHE_LOCK = threading.Lock()
# In-memory cache keyed by (subject, group) to avoid repeated dataset rebuilds
_GROUP_CACHE = {}
_STUDENTS_BY_SUBJECT_GROUP_CACHE = {}
_RATING_CACHE_LOCK = threading.Lock()
_RATING_LEADERBOARD_CACHE = {}


def clear_group_cache():
    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE.clear()
        _STUDENTS_BY_SUBJECT_GROUP_CACHE.clear()
    with _RATING_CACHE_LOCK:
        _RATING_LEADERBOARD_CACHE.clear()


def _group_cache_key(subject, group):
    return (_normalize(subject), _normalize(group))


def seed_group_cache_from_dataset(dataset, force=False):
    students = dataset.get("students", [])
    dashboards_by_id = dataset.get("dashboards_by_id", {})
    if not isinstance(students, list) or not isinstance(dashboards_by_id, dict):
        return

    now = time.time()
    candidate_keys = set()
    for student in students:
        if not isinstance(student, dict):
            continue
        subject = str(student.get("subject", "")).strip()
        group = str(student.get("group", "")).strip()
        candidate_keys.add(_group_cache_key(subject, group))

    if not force:
        with _GROUP_CACHE_LOCK:
            needed_keys = {
                key for key in candidate_keys
                if not _GROUP_CACHE.get(key) or now >= float(_GROUP_CACHE[key].get("expires_at", 0))
            }
        if not needed_keys:
            return
    else:
        needed_keys = candidate_keys

    grouped_entries = {}
    for student in students:
        if not isinstance(student, dict):
            continue
        student_id = student.get("id")
        if not isinstance(student_id, int):
            continue

        subject = str(student.get("subject", "")).strip()
        group = str(student.get("group", "")).strip()
        key = _group_cache_key(subject, group)
        if key not in needed_keys:
            continue

        entry = grouped_entries.setdefault(key, {"students": [], "dashboards_by_id": {}})
        entry["students"].append({"id": student_id, "fullName": str(student.get("fullName", "")).strip()})
        dashboard_payload = dashboards_by_id.get(student_id)
        if dashboard_payload:
            entry["dashboards_by_id"][student_id] = dashboard_payload

    if not grouped_entries:
        return

    expires_at = now + GROUP_CACHE_TTL_SECONDS
    for entry in grouped_entries.values():
        entry["students"].sort(key=lambda item: _normalize(str(item.get("fullName", ""))))
        entry["expires_at"] = expires_at

    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE.update(grouped_entries)


def get_group_cache_entry(subject, group, school_code="", force_refresh=False):
    key = _group_cache_key(subject, group)
    now = time.time()

    if not force_refresh:
        with _GROUP_CACHE_LOCK:
            cached_entry = _GROUP_CACHE.get(key)
            if cached_entry and now < float(cached_entry.get("expires_at", 0)):
                return cached_entry, None

    dataset, load_error = load_dataset(
        school_code=school_code,
        force_refresh=force_refresh,
    )
    if load_error or not dataset:
        return None, load_error or "Unable to load internal academic data."

    seed_group_cache_from_dataset(dataset, force=force_refresh)

    with _GROUP_CACHE_LOCK:
        cached_entry = _GROUP_CACHE.get(key)
        if cached_entry and time.time() < float(cached_entry.get("expires_at", 0)):
            return cached_entry, None

    return None, "Selected group data was not found."


def extract_numeric_average_grade(dashboard_payload):
    scores = extract_homework_scores(dashboard_payload)
    if scores:
        return math.floor((sum(scores) / len(scores)) * 10 + 0.5) / 10

    raw_value = dashboard_payload.get("averageGrade")
    try:
        average_grade = float(raw_value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(average_grade):
        return None
    return average_grade


def extract_homework_scores(dashboard_payload):
    homework_grades = dashboard_payload.get("homeworkGrades", [])
    scores = []
    if not isinstance(homework_grades, list):
        return scores
    for item in homework_grades:
        if not isinstance(item, dict):
            continue
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score):
            continue
        scores.append(max(0.0, min(9.0, score)))
    return scores


def extract_exam_average_score(dashboard_payload):
    best_scores = extract_best_exam_scores(dashboard_payload)
    if not best_scores:
        return None
    return round(sum(best_scores.values()) / len(best_scores), 1)


def _normalize_exam_rating_key(value):
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return " ".join(normalized.casefold().split())


def extract_best_exam_scores(dashboard_payload):
    best_scores = {}
    for exam_result in dashboard_payload.get("examResults", []):
        if not isinstance(exam_result, dict):
            continue

        exam_key = _normalize_exam_rating_key(
            exam_result.get("examName") or exam_result.get("label")
        )
        if not exam_key:
            continue

        raw_score = exam_result.get("score")
        try:
            numeric_score = float(raw_score)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric_score):
            continue

        bounded_score = max(0.0, min(9.0, numeric_score))
        best_scores[exam_key] = max(best_scores.get(exam_key, 0.0), bounded_score)

    return best_scores


def _safe_nonnegative_int(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(numeric):
        return 0
    return max(int(round(numeric)), 0)


def _attendance_counts(dashboard_payload):
    attendance_record = dashboard_payload.get("attendanceRecord", {})
    if not isinstance(attendance_record, dict):
        attendance_record = {}

    present = _safe_nonnegative_int(attendance_record.get("presentCount", 0))
    absent = _safe_nonnegative_int(attendance_record.get("absentCount", 0))
    justified_absent = _safe_nonnegative_int(
        attendance_record.get("justifiedAbsentCount", 0)
    )
    return present, absent, justified_absent


def extract_attendance_rate(dashboard_payload):
    present, absent, justified_absent = _attendance_counts(dashboard_payload)
    total = present + absent + justified_absent
    if total <= 0:
        return 0

    return round(((present + justified_absent) / total) * 100)


def extract_attendance_total(dashboard_payload):
    present, absent, justified_absent = _attendance_counts(dashboard_payload)
    return present + absent + justified_absent


def attendance_rate_to_score(attendance_rate):
    bounded_rate = max(0, min(int(attendance_rate), 100))
    if bounded_rate == 0:
        return 0
    return round((bounded_rate / 100) * 9, 1)


def collect_subject_dashboards_from_dataset(dataset, subject):
    dashboards_by_id = dataset.get("dashboards_by_id", {})
    if not isinstance(dashboards_by_id, dict):
        return []

    subject_norm = _normalize(subject)
    dashboards = []
    for dashboard_payload in dashboards_by_id.values():
        if not isinstance(dashboard_payload, dict):
            continue

        student = dashboard_payload.get("student", {})
        if not isinstance(student, dict):
            continue

        dashboard_subject = str(student.get("subject", "")).strip()
        if _normalize(dashboard_subject) != subject_norm:
            continue

        dashboards.append(dashboard_payload)

    return dashboards


def collect_subject_dashboards_from_cache(subject):
    subject_norm = _normalize(subject)
    now = time.time()
    dashboards = []

    with _GROUP_CACHE_LOCK:
        for (cached_subject, _cached_group), cache_entry in _GROUP_CACHE.items():
            if cached_subject != subject_norm:
                continue
            if now >= float(cache_entry.get("expires_at", 0)):
                continue

            dashboards_by_id = cache_entry.get("dashboards_by_id", {})
            if not isinstance(dashboards_by_id, dict):
                continue

            for dashboard_payload in dashboards_by_id.values():
                if isinstance(dashboard_payload, dict):
                    dashboards.append(dashboard_payload)

    return dashboards


def build_subject_rating(student_id, dashboards):
    leaderboard = build_subject_leaderboard(dashboards)
    total = len(leaderboard)
    for row in leaderboard:
        if int(row.get("studentId", -1)) == student_id:
            return {"rank": int(row.get("rank", 0)), "total": total}
    return None


def round_grade_half_up(value):
    return int(math.floor(value + 0.5))


def build_subject_leaderboard(dashboards):
    cache_key = _subject_leaderboard_cache_key(dashboards)
    now = time.time()
    if cache_key and RATING_CACHE_TTL_SECONDS > 0:
        with _RATING_CACHE_LOCK:
            cached_entry = _RATING_LEADERBOARD_CACHE.get(cache_key)
            if cached_entry and now < float(cached_entry.get("expires_at", 0)):
                return cached_entry.get("value", [])

    ranking_rows = []

    for dashboard_payload in dashboards:
        student = dashboard_payload.get("student", {})
        if not isinstance(student, dict):
            continue

        student_id = student.get("id")
        if not isinstance(student_id, int):
            continue

        average_grade = extract_numeric_average_grade(dashboard_payload)
        if average_grade is None:
            average_grade = 0.0

        full_name = str(student.get("fullName", "")).strip()
        surname = str(student.get("surname", "")).strip()
        name = str(student.get("name", "")).strip()
        display_name = f"{surname} {name}".strip() if surname and name else full_name
        group_name = str(student.get("group", "")).strip()

        best_exam_scores = extract_best_exam_scores(dashboard_payload)
        exam_count = len(best_exam_scores)
        avg_exam_score = (
            round(sum(best_exam_scores.values()) / exam_count, 1)
            if exam_count
            else 0.0
        )
        exam_performance = (
            round_grade_half_up(avg_exam_score) if avg_exam_score > 0 else 0
        )
        homework_count = len(extract_homework_scores(dashboard_payload))
        aap = round_grade_half_up(average_grade)
        attendance_rate = extract_attendance_rate(dashboard_payload)
        attendance_score = attendance_rate_to_score(attendance_rate)
        attendance_total = extract_attendance_total(dashboard_payload)
        average_composite = round(
            (avg_exam_score * 0.70) + (average_grade * 0.15) + (attendance_score * 0.15),
            1,
        )
        is_provisional = exam_count < 2 or homework_count < 10 or attendance_total < 10

        ranking_rows.append(
            {
                "studentId": student_id,
                "averageGrade": average_grade,
                "sortName": _normalize(display_name or full_name),
                "displayName": display_name or full_name,
                "group": group_name,
                "avgExamScore": avg_exam_score,
                "avgExamScoreDisplay": f"{avg_exam_score:.1f}",
                "examPerformance": exam_performance,
                "examPerformanceDisplay": f"{avg_exam_score:.1f}",
                "examCount": exam_count,
                "aap": aap,
                "aapDisplay": f"{average_grade:.1f}",
                "homeworkCount": homework_count,
                "attendanceRate": attendance_rate,
                "attendanceScore": attendance_score,
                "attendanceScoreDisplay": f"{attendance_score:.1f}",
                "attendanceTotal": attendance_total,
                "averageComposite": average_composite,
                "averageCompositeDisplay": f"{average_composite:.1f}",
                "isProvisional": is_provisional,
                "ratingStatus": "Provisional" if is_provisional else "Official",
            }
        )

    ranking_rows.sort(
        key=lambda row: (
            bool(row["isProvisional"]),
            -float(row["averageComposite"]),
            -float(row["avgExamScore"]),
            -float(row["averageGrade"]),
            -int(row["attendanceRate"]),
            str(row["sortName"]),
            int(row["studentId"]),
        )
    )

    leaderboard = []
    official_position = 0
    for position, row in enumerate(ranking_rows, start=1):
        average_grade = float(row["averageGrade"])
        if not row["isProvisional"]:
            official_position += 1

        leaderboard.append(
            {
                "rank": official_position if not row["isProvisional"] else 0,
                "position": position,
                "studentId": row["studentId"],
                "displayName": row["displayName"],
                "group": row["group"],
                "avgExamScoreDisplay": row["avgExamScoreDisplay"],
                "examPerformance": row["examPerformance"],
                "examPerformanceDisplay": row["examPerformanceDisplay"],
                "examCount": row["examCount"],
                "aap": row["aap"],
                "aapDisplay": row["aapDisplay"],
                "homeworkCount": row["homeworkCount"],
                "attendanceRate": row["attendanceRate"],
                "attendanceScore": row["attendanceScore"],
                "attendanceScoreDisplay": row["attendanceScoreDisplay"],
                "attendanceTotal": row["attendanceTotal"],
                "averageComposite": row["averageComposite"],
                "averageCompositeDisplay": row["averageCompositeDisplay"],
                "averageGrade": average_grade,
                "isProvisional": row["isProvisional"],
                "ratingStatus": row["ratingStatus"],
            }
        )

    if cache_key and RATING_CACHE_TTL_SECONDS > 0:
        with _RATING_CACHE_LOCK:
            _RATING_LEADERBOARD_CACHE[cache_key] = {
                "value": leaderboard,
                "expires_at": now + RATING_CACHE_TTL_SECONDS,
            }
            expired_keys = [
                key
                for key, entry in _RATING_LEADERBOARD_CACHE.items()
                if float(entry.get("expires_at", 0)) <= now
            ]
            for key in expired_keys:
                _RATING_LEADERBOARD_CACHE.pop(key, None)
            if len(_RATING_LEADERBOARD_CACHE) > RATING_CACHE_MAX_ENTRIES:
                ordered_entries = sorted(
                    _RATING_LEADERBOARD_CACHE.items(),
                    key=lambda item: float(item[1].get("expires_at", 0)),
                )
                overflow = len(_RATING_LEADERBOARD_CACHE) - RATING_CACHE_MAX_ENTRIES
                for key, _entry in ordered_entries[:overflow]:
                    _RATING_LEADERBOARD_CACHE.pop(key, None)

    return leaderboard


def _subject_leaderboard_cache_key(dashboards):
    if not isinstance(dashboards, list) or not dashboards:
        return ""

    parts = []
    for dashboard_payload in dashboards:
        if not isinstance(dashboard_payload, dict):
            continue
        student = dashboard_payload.get("student", {})
        if not isinstance(student, dict):
            continue
        student_id = student.get("id")
        subject = _normalize(student.get("subject", ""))
        school = _normalize(student.get("schoolCode", "") or student.get("schoolName", ""))
        group = _normalize(student.get("group", ""))
        average = str(dashboard_payload.get("averageGrade", ""))
        homework_count = len(dashboard_payload.get("homeworkGrades", []) or [])
        exam_count = len(dashboard_payload.get("examResults", []) or [])
        attendance = dashboard_payload.get("attendanceRecord", {})
        if not isinstance(attendance, dict):
            attendance = {}
        attendance_token = ":".join(
            str(attendance.get(key, ""))
            for key in ("presentCount", "absentCount", "justifiedAbsentCount")
        )
        parts.append(
            "|".join(
                [
                    str(student_id),
                    subject,
                    school,
                    group,
                    average,
                    str(homework_count),
                    str(exam_count),
                    attendance_token,
                ]
            )
        )

    if not parts:
        return ""
    digest = hashlib.sha1("\n".join(sorted(parts)).encode("utf-8")).hexdigest()
    return f"subject-leaderboard:{digest}"


def compute_subject_rating(student_id, payload, dataset=None):
    student = payload.get("student", {})
    if not isinstance(student, dict):
        return None

    subject = str(student.get("subject", "")).strip()
    if not subject:
        return None

    dashboards = []
    if dataset:
        dashboards = collect_subject_dashboards_from_dataset(dataset, subject)

    if not dashboards:
        dashboards = collect_subject_dashboards_from_cache(subject)

    if not dashboards:
        from backend.modules.domains.reporting.academic_dashboard import get_subject_dashboards_from_db
        dashboards = get_subject_dashboards_from_db(subject)

    if not dashboards:
        refreshed_dataset, load_error = load_dataset()
        if load_error or not refreshed_dataset:
            return None
        seed_group_cache_from_dataset(refreshed_dataset)
        dashboards = collect_subject_dashboards_from_dataset(refreshed_dataset, subject)

    return build_subject_rating(student_id=student_id, dashboards=dashboards)


def is_full_form(form_data):
    return all(form_data.values())


def search_student(students, surname, name, group, subject):
    surname_norm = _normalize(surname)
    name_norm = _normalize(name)
    group_norm = _normalize(group)
    subject_norm = _normalize(subject)

    for student in students:
        student_group = _normalize(student.get("group", ""))
        student_subject = _normalize(student.get("subject", ""))
        if student_group != group_norm or student_subject != subject_norm:
            continue

        full_name = _normalize(student.get("fullName", ""))
        if surname_norm not in full_name or name_norm not in full_name:
            continue

        return student

    return None


def build_students_by_subject_group(students):
    if not isinstance(students, list):
        return {}

    now = time.time()
    cache_key = int(id(students))
    with _GROUP_CACHE_LOCK:
        cached_entry = _STUDENTS_BY_SUBJECT_GROUP_CACHE.get(cache_key)
        if (
            cached_entry
            and cached_entry.get("students_obj") is students
            and now < float(cached_entry.get("expires_at", 0))
        ):
            return cached_entry.get("value", {})

    students_by_subject_group = {}

    sorted_students = sorted(
        students,
        key=lambda student: (
            _normalize(str(student.get("subject", ""))),
            _normalize(str(student.get("group", ""))),
            _normalize(str(student.get("fullName", ""))),
        ),
    )

    for student in sorted_students:
        subject = str(student.get("subject", "")).strip()
        group = str(student.get("group", "")).strip()
        student_id = student.get("id")
        if not subject or not group or not isinstance(student_id, int):
            continue

        students_by_subject_group.setdefault(subject, {}).setdefault(group, []).append(
            {
                "id": student_id,
                "fullName": str(student.get("fullName", "")).strip(),
            }
        )

    expires_at = now + GROUP_CACHE_TTL_SECONDS
    with _GROUP_CACHE_LOCK:
        _STUDENTS_BY_SUBJECT_GROUP_CACHE[cache_key] = {
            "students_obj": students,
            "value": students_by_subject_group,
            "expires_at": expires_at,
        }
        expired_keys = [
            key
            for key, entry in _STUDENTS_BY_SUBJECT_GROUP_CACHE.items()
            if float(entry.get("expires_at", 0)) <= now
        ]
        for key in expired_keys:
            _STUDENTS_BY_SUBJECT_GROUP_CACHE.pop(key, None)
        if len(_STUDENTS_BY_SUBJECT_GROUP_CACHE) > 64:
            ordered_entries = sorted(
                _STUDENTS_BY_SUBJECT_GROUP_CACHE.items(),
                key=lambda item: float(item[1].get("expires_at", 0)),
            )
            for key, _entry in ordered_entries[: len(_STUDENTS_BY_SUBJECT_GROUP_CACHE) - 64]:
                _STUDENTS_BY_SUBJECT_GROUP_CACHE.pop(key, None)

    return students_by_subject_group


def load_dataset(school_code=None, force_refresh=False):
    from backend.modules.domains.reporting.academic_dashboard import build_internal_dataset
    dataset = build_internal_dataset(school_code or "")
    if dataset:
        seed_group_cache_from_dataset(dataset, force=bool(force_refresh))
        return dataset, None
    return None, "Internal academic data is not available."


def load_dashboard_payload(
    student_id,
    requested_subject,
    requested_group,
    requested_school="",
    force_refresh=False,
):
    normalized_requested_school = _normalize_school_code(requested_school, default="")
    from backend.modules.domains.reporting.academic_dashboard import get_enrollment_dashboard
    db_payload = get_enrollment_dashboard(
        student_id,
        normalized_requested_school,
        subject_name=requested_subject,
        group_name=requested_group,
    )
    if db_payload is None and (requested_subject or requested_group):
        db_payload = get_enrollment_dashboard(student_id, normalized_requested_school)
    if db_payload is not None:
        return db_payload, None, None

    if requested_subject and requested_group:
        group_cache_entry, _cache_error = get_group_cache_entry(
            requested_subject,
            requested_group,
            school_code=normalized_requested_school,
            force_refresh=force_refresh,
        )
        if group_cache_entry:
            cached_payload = group_cache_entry.get("dashboards_by_id", {}).get(student_id)
            if cached_payload:
                return cached_payload, None, None

    return None, None, "Student dashboard was not found in internal academic data."
