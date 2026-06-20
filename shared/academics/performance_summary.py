import math
import threading
from datetime import datetime

from shared.academics import canonical
from shared.db import queries

_DB_LOCK = threading.Lock()
_SYNC_LOCK = threading.Lock()


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _round_grade_half_up(value):
    return int(math.floor(float(value) + 0.5))


def _safe_nonnegative_int(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(numeric):
        return 0
    return max(int(round(numeric)), 0)


def _extract_exam_average_score(dashboard_payload):
    exam_scores = []
    for exam_result in dashboard_payload.get("examResults", []):
        if not isinstance(exam_result, dict):
            continue
        try:
            score = float(exam_result.get("score"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score):
            continue
        exam_scores.append(score)

    if not exam_scores:
        return None
    return round(sum(exam_scores) / len(exam_scores), 1)


def _extract_attendance_rate(dashboard_payload):
    attendance_record = dashboard_payload.get("attendanceRecord", {})
    if not isinstance(attendance_record, dict):
        attendance_record = {}

    present = _safe_nonnegative_int(attendance_record.get("presentCount", 0))
    absent = _safe_nonnegative_int(attendance_record.get("absentCount", 0))
    justified_absent = _safe_nonnegative_int(
        attendance_record.get("justifiedAbsentCount", 0)
    )
    total = present + absent + justified_absent
    if total <= 0:
        return 0
    return round(((present + justified_absent) / total) * 100)


def _extract_aap_score(dashboard_payload):
    homework_grades = dashboard_payload.get("homeworkGrades", [])
    if not isinstance(homework_grades, list):
        homework_grades = []

    scores = []
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

    if scores:
        return math.floor((sum(scores) / len(scores)) * 10 + 0.5) / 10

    raw_average_grade = dashboard_payload.get("averageGrade")
    try:
        average_grade = float(raw_average_grade)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(average_grade):
        return 0.0
    return max(average_grade, 0.0)


def _attendance_rate_to_score(attendance_rate):
    bounded_rate = max(0, min(int(attendance_rate), 100))
    if bounded_rate == 0:
        return 0
    return max(1, min(9, _round_grade_half_up((bounded_rate / 100) * 9)))


def _ensure_storage(conn):
    queries.create_tables(conn)
    queries.ensure_students_schema(conn)
    queries.ensure_subject_summaries_schema(conn)


def _load_dataset(load_dataset, force_refresh = False):
    try:
        loaded = load_dataset(force_refresh=force_refresh)
    except Exception as exc:
        try:
            loaded = load_dataset()
        except Exception:
            return None, str(exc)

    if isinstance(loaded, tuple) and len(loaded) == 2:
        dataset, load_error = loaded
        return dataset, str(load_error or "")

    return loaded, ""


def _build_subject_summary_rows(dataset):
    dashboards_by_id = dataset.get("dashboards_by_id", {}) if isinstance(dataset, dict) else {}
    if not isinstance(dashboards_by_id, dict):
        return []

    summary_rows = []
    subject_rows = {}

    for enrollment_id, payload in dashboards_by_id.items():
        if not isinstance(enrollment_id, int):
            continue
        if not isinstance(payload, dict):
            continue

        student = payload.get("student", {})
        if not isinstance(student, dict):
            continue

        full_name = str(student.get("fullName", "")).strip()
        if not full_name:
            continue

        school_key = canonical.normalize_school_code(student.get("schoolCode", ""), default="")
        school_name = str(student.get("schoolName", "")).strip()
        group_name = str(student.get("group", "")).strip()
        subject_name = str(student.get("subject", "")).strip() or "Unknown"
        subject_short = canonical.subject_short_name(subject_name)

        aap_score = _extract_aap_score(payload)
        attendance_rate = _extract_attendance_rate(payload)
        exam_average = _extract_exam_average_score(payload)
        exam_performance = (
            _round_grade_half_up(exam_average)
            if exam_average is not None and exam_average > 0
            else 0
        )
        total_coins = _safe_nonnegative_int(
            payload.get("coins", student.get("coins", 0))
        )
        attendance_score = _attendance_rate_to_score(attendance_rate)
        average_composite = round((exam_performance + aap_score + attendance_score) / 3, 1)

        row = {
            "enrollment_id": int(enrollment_id),
            "full_name": full_name,
            "full_name_norm": canonical.normalize_text(full_name),
            "school_key": school_key,
            "school_name": school_name,
            "group_name": group_name,
            "subject_name": subject_name,
            "subject_short": subject_short,
            "aap": float(aap_score),
            "ar": int(attendance_rate),
            "ep": int(exam_performance),
            "total_coins": int(total_coins),
            "average_composite": float(average_composite),
        }

        summary_rows.append(row)
        subject_rows.setdefault(subject_name, []).append(row)

    rating_by_enrollment_id = {}
    for subject_name, rows in subject_rows.items():
        ordered_rows = sorted(
            rows,
            key=lambda row: (
                -float(row["average_composite"]),
                -int(row["ep"]),
                -float(row["aap"]),
                -int(row["ar"]),
                str(row["full_name_norm"]),
                int(row["enrollment_id"]),
            ),
        )
        total = len(ordered_rows)
        for position, row in enumerate(ordered_rows, start=1):
            rating_by_enrollment_id[int(row["enrollment_id"])] = {
                "rating_rank": position,
                "rating_total": total,
            }

    updated_at = _utc_now_iso()
    payload_rows = []
    for row in summary_rows:
        rating = rating_by_enrollment_id.get(int(row["enrollment_id"]), {})
        payload_rows.append(
            {
                "enrollment_id": int(row["enrollment_id"]),
                "full_name": str(row["full_name"]),
                "full_name_norm": str(row["full_name_norm"]),
                "school_key": str(row["school_key"]),
                "school_name": str(row["school_name"]),
                "group_name": str(row["group_name"]),
                "subject_name": str(row["subject_name"]),
                "subject_short": str(row["subject_short"]),
                "aap": float(row["aap"]),
                "ar": int(row["ar"]),
                "ep": int(row["ep"]),
                "total_coins": int(row["total_coins"]),
                "rating_rank": int(rating.get("rating_rank", 0)),
                "rating_total": int(rating.get("rating_total", 0)),
                "updated_at": updated_at,
            }
        )

    return payload_rows


def sync_subject_summaries_if_needed(load_dataset, force_refresh=False):
    _ = force_refresh
    with _SYNC_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)

        dataset, load_error = _load_dataset(
            load_dataset,
            force_refresh=True,
        )
        if load_error or not dataset:
            return {
                "synced": False,
                "error": load_error or "Unable to load internal academic data.",
                "count": 0,
            }

        summary_rows = _build_subject_summary_rows(dataset)

        with _DB_LOCK:
            with _connect() as conn:
                _ensure_storage(conn)
                queries.replace_subject_summary_rows(conn, summary_rows)
                conn.commit()

        return {"synced": True, "error": "", "count": len(summary_rows)}


def list_subject_summaries_by_full_name(full_name):
    normalized_name = canonical.normalize_text(full_name)
    if not normalized_name:
        return []

    with _connect() as conn:
        _ensure_storage(conn)
        rows = queries.list_subject_summary_rows_by_full_name_norm(conn, normalized_name)

    results = []
    for row in rows:
        group_name = str(row["group_name"] or "").strip()
        if group_name.casefold() == "online":
            continue
        results.append(
            {
                "enrollment_id": int(row["enrollment_id"]),
                "full_name": str(row["full_name"]),
                "school_key": str(row["school_key"] or "").strip(),
                "school_name": str(row["school_name"] or "").strip(),
                "group_name": group_name,
                "subject_name": str(row["subject_name"]),
                "subject_short": str(row["subject_short"]),
                "aap": float(row["aap"]),
                "ar": int(row["ar"]),
                "ep": int(row["ep"]),
                "total_coins": int(row["total_coins"]),
                "rating_rank": int(row["rating_rank"]),
                "rating_total": int(row["rating_total"]),
                "updated_at": str(row["updated_at"]),
            }
        )

    results.sort(
        key=lambda row: (
            canonical.subject_sort_key(row.get("subject_name", "")),
            int(row.get("enrollment_id", 0)),
        )
    )
    return results


def list_subject_summaries(school_key = ""):
    normalized_school_key = canonical.normalize_school_code(school_key, default="")
    with _connect() as conn:
        _ensure_storage(conn)
        rows = queries.list_subject_summary_rows(
            conn,
            school_key=normalized_school_key if normalized_school_key else "all",
        )

    results = []
    for row in rows:
        group_name = str(row["group_name"] or "").strip()
        if group_name.casefold() == "online":
            continue
        results.append(
            {
                "enrollment_id": int(row["enrollment_id"]),
                "full_name": str(row["full_name"]),
                "school_key": str(row["school_key"] or "").strip(),
                "school_name": str(row["school_name"] or "").strip(),
                "group_name": group_name,
                "subject_name": str(row["subject_name"]),
                "subject_short": str(row["subject_short"]),
                "aap": float(row["aap"]),
                "ar": int(row["ar"]),
                "ep": int(row["ep"]),
                "total_coins": int(row["total_coins"]),
                "rating_rank": int(row["rating_rank"]),
                "rating_total": int(row["rating_total"]),
                "updated_at": str(row["updated_at"]),
            }
        )
    return results


def get_subject_summaries_for_student(full_name, load_dataset=None):
    _ = load_dataset
    rows = list_subject_summaries_by_full_name(full_name)
    return rows, ""


__all__ = [
    "sync_subject_summaries_if_needed",
    "get_subject_summaries_for_student",
    "list_subject_summaries_by_full_name",
    "list_subject_summaries",
]
