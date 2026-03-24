import math
import threading
from datetime import datetime

try:
    from ..storage import queries
except ImportError:
    from app.storage import queries

_DB_LOCK = threading.Lock()
_SYNC_LOCK = threading.Lock()

_SUBJECT_SHORT_NAMES = {
    "igcse mathematics a": "Math",
    "mathematics": "Math",
    "math": "Math",
    "general english": "English",
    "english": "English",
    "chemistry": "Chemistry",
    "biology": "Biology",
    "physics": "Physics",
}

_SUBJECT_SORT_ORDER = {
    "math": 0,
    "english": 1,
}


def _normalize_school_code(value):
    normalized = _normalize(value)
    if normalized in {"school_5", "school-5", "school 5", "school5"}:
        return "school5"
    if normalized in {"sehriyo", "sehriyo school"}:
        return "sehriyo"
    return normalized


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_today_iso():
    return datetime.utcnow().date().isoformat()


def _normalize(value):
    return " ".join(str(value or "").strip().casefold().split())


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


def _subject_short_name(subject_name):
    normalized = _normalize(subject_name)
    if normalized in _SUBJECT_SHORT_NAMES:
        return _SUBJECT_SHORT_NAMES[normalized]
    words = [part for part in str(subject_name or "").split() if part]
    if not words:
        return "Subject"
    return words[0]


def _subject_sort_key(subject_name):
    short_name = _subject_short_name(subject_name)
    normalized_short_name = _normalize(short_name)
    return (
        _SUBJECT_SORT_ORDER.get(normalized_short_name, 999),
        normalized_short_name,
    )


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
    queries.ensure_students_sheet_map_schema(conn)
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

    for sheet_student_id, payload in dashboards_by_id.items():
        if not isinstance(sheet_student_id, int):
            continue
        if not isinstance(payload, dict):
            continue

        student = payload.get("student", {})
        if not isinstance(student, dict):
            continue

        full_name = str(student.get("fullName", "")).strip()
        if not full_name:
            continue

        school_key = _normalize_school_code(student.get("schoolCode", ""))
        school_name = str(student.get("schoolName", "")).strip()
        group_name = str(student.get("group", "")).strip()
        subject_name = str(student.get("subject", "")).strip() or "Unknown"
        subject_short = _subject_short_name(subject_name)

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
            "sheet_student_id": int(sheet_student_id),
            "full_name": full_name,
            "full_name_norm": _normalize(full_name),
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

    rating_by_sheet_id = {}
    for subject_name, rows in subject_rows.items():
        ordered_rows = sorted(
            rows,
            key=lambda row: (
                -float(row["average_composite"]),
                -int(row["ep"]),
                -float(row["aap"]),
                -int(row["ar"]),
                str(row["full_name_norm"]),
                int(row["sheet_student_id"]),
            ),
        )
        total = len(ordered_rows)
        for position, row in enumerate(ordered_rows, start=1):
            rating_by_sheet_id[int(row["sheet_student_id"])] = {
                "rating_rank": position,
                "rating_total": total,
            }

    updated_at = _utc_now_iso()
    payload_rows = []
    for row in summary_rows:
        rating = rating_by_sheet_id.get(int(row["sheet_student_id"]), {})
        payload_rows.append(
            {
                "sheet_student_id": int(row["sheet_student_id"]),
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
    with _SYNC_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)

            today = _utc_today_iso()
            last_sync_date = queries.get_meta(conn, "subject_summary_sync_date")
            if not force_refresh and last_sync_date == today:
                return {"synced": False, "error": "", "count": 0}

        dataset, load_error = _load_dataset(
            load_dataset,
            force_refresh=force_refresh,
        )
        if load_error or not dataset:
            return {
                "synced": False,
                "error": load_error or "Unable to load Google Sheets data.",
                "count": 0,
            }

        summary_rows = _build_subject_summary_rows(dataset)

        with _DB_LOCK:
            with _connect() as conn:
                _ensure_storage(conn)
                queries.replace_subject_summary_rows(conn, summary_rows)
                queries.upsert_meta(conn, "subject_summary_sync_date", _utc_today_iso())
                conn.commit()

        return {"synced": True, "error": "", "count": len(summary_rows)}


def list_subject_summaries_by_full_name(full_name):
    normalized_name = _normalize(full_name)
    if not normalized_name:
        return []

    with _connect() as conn:
        _ensure_storage(conn)
        rows = queries.list_subject_summary_rows_by_full_name_norm(conn, normalized_name)

    results = []
    for row in rows:
        results.append(
            {
                "sheet_student_id": int(row["sheet_student_id"]),
                "full_name": str(row["full_name"]),
                "school_key": str(row["school_key"] or "").strip(),
                "school_name": str(row["school_name"] or "").strip(),
                "group_name": str(row["group_name"] or "").strip(),
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
            _subject_sort_key(row.get("subject_name", "")),
            int(row.get("sheet_student_id", 0)),
        )
    )
    return results


def list_subject_summaries(school_key = ""):
    normalized_school_key = _normalize_school_code(school_key)
    with _connect() as conn:
        _ensure_storage(conn)
        rows = queries.list_subject_summary_rows(
            conn,
            school_key=normalized_school_key if normalized_school_key else "all",
        )

    results = []
    for row in rows:
        results.append(
            {
                "sheet_student_id": int(row["sheet_student_id"]),
                "full_name": str(row["full_name"]),
                "school_key": str(row["school_key"] or "").strip(),
                "school_name": str(row["school_name"] or "").strip(),
                "group_name": str(row["group_name"] or "").strip(),
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


def get_subject_summaries_for_student(full_name, load_dataset):
    sync_result = sync_subject_summaries_if_needed(load_dataset)
    sync_error = str(sync_result.get("error", "")).strip()
    if sync_error:
        return [], sync_error

    rows = list_subject_summaries_by_full_name(full_name)
    if rows:
        return rows, ""

    # If cache says up-to-date but rows are empty, refresh once as fallback.
    if not bool(sync_result.get("synced", False)):
        fallback_sync = sync_subject_summaries_if_needed(
            load_dataset,
            force_refresh=True,
        )
        fallback_error = str(fallback_sync.get("error", "")).strip()
        if fallback_error:
            return [], fallback_error
        rows = list_subject_summaries_by_full_name(full_name)

    return rows, ""


__all__ = [
    "sync_subject_summaries_if_needed",
    "get_subject_summaries_for_student",
    "list_subject_summaries_by_full_name",
    "list_subject_summaries",
]
