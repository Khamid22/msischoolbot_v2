import os
import threading
import time
import math
import sys

from flask import Flask, jsonify, make_response, redirect, request, session, url_for

try:
    from config import get_web_settings
except ImportError:
    if __package__:
        raise
    # Allow running `python web/app.py` by adding project root to import path.
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config import get_web_settings

try:
    from .sheets_data import SheetsDataError, get_school_dataset
except ImportError:
    if __package__:
        raise
    from sheets_data import SheetsDataError, get_school_dataset

try:
    from .auth_store import init_storage
except ImportError:
    if __package__:
        raise
    from auth_store import init_storage

# Main Flask application object.
app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")

# Initialize auth-related SQLite tables on startup.
init_storage()


def _build_default_asset_version():
    # Build a simple asset version from the latest static/template file mtime.
    base_dir = os.path.dirname(__file__)
    candidate_paths = [
        os.path.join(base_dir, "app.py"),
        os.path.join(base_dir, "templates", "dashboard.html"),
        os.path.join(base_dir, "templates", "home.html"),
        os.path.join(base_dir, "static", "js", "dashboard.js"),
        os.path.join(base_dir, "static", "js", "home.js"),
        os.path.join(base_dir, "static", "js", "pwa.js"),
        os.path.join(base_dir, "static", "js", "sw.js"),
        os.path.join(base_dir, "static", "css", "style.css"),
    ]
    mtimes = []
    for path in candidate_paths:
        try:
            mtimes.append(int(os.path.getmtime(path)))
        except OSError:
            continue

    if not mtimes:
        return "1"
    return str(max(mtimes))


_asset_version_override = os.environ.get("ASSET_VERSION", "").strip()
if _asset_version_override and _asset_version_override != "1":
    ASSET_VERSION = _asset_version_override
else:
    ASSET_VERSION = _build_default_asset_version()

# Reuse shared root config so web uses the same source as main.py.
settings = get_web_settings()
GROUP_CACHE_TTL_SECONDS = int(
    os.environ.get(
        "GROUP_CACHE_TTL_SECONDS",
        os.environ.get("SHEETS_CACHE_TTL_SECONDS", "600"),
    )
)

_GROUP_CACHE_LOCK = threading.Lock()
# In-memory cache keyed by (subject, group) to avoid repeated sheet calls.
_GROUP_CACHE = {}


def _normalize(value):
    return " ".join(value.strip().casefold().split())


def _group_cache_key(subject, group):
    return (_normalize(subject), _normalize(group))


def _seed_group_cache_from_dataset(dataset):
    students = dataset.get("students", [])
    dashboards_by_id = dataset.get("dashboards_by_id", {})
    if not isinstance(students, list) or not isinstance(dashboards_by_id, dict):
        return

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

        entry = grouped_entries.setdefault(
            key,
            {
                "students": [],
                "dashboards_by_id": {},
            },
        )
        entry["students"].append(
            {
                "id": student_id,
                "fullName": str(student.get("fullName", "")).strip(),
            }
        )

        dashboard_payload = dashboards_by_id.get(student_id)
        if dashboard_payload:
            entry["dashboards_by_id"][student_id] = dashboard_payload

    expires_at = time.time() + GROUP_CACHE_TTL_SECONDS
    for entry in grouped_entries.values():
        entry["students"].sort(key=lambda item: _normalize(str(item.get("fullName", ""))))
        entry["expires_at"] = expires_at

    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE.update(grouped_entries)


def _get_group_cache_entry(subject, group):
    # Try cached group first; if expired/missing, refresh from Google Sheets.
    key = _group_cache_key(subject, group)
    now = time.time()

    with _GROUP_CACHE_LOCK:
        cached_entry = _GROUP_CACHE.get(key)
        if cached_entry and now < float(cached_entry.get("expires_at", 0)):
            return cached_entry, None

    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return None, load_error or "Unable to load Google Sheets data."

    _seed_group_cache_from_dataset(dataset)

    with _GROUP_CACHE_LOCK:
        cached_entry = _GROUP_CACHE.get(key)
        if cached_entry and time.time() < float(cached_entry.get("expires_at", 0)):
            return cached_entry, None

    return None, "Selected group data was not found."


def _extract_numeric_average_grade(dashboard_payload):
    raw_value = dashboard_payload.get("averageGrade")
    try:
        average_grade = float(raw_value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(average_grade):
        return None
    return average_grade


def _extract_exam_average_score(dashboard_payload):
    exam_scores = []
    for exam_result in dashboard_payload.get("examResults", []):
        if not isinstance(exam_result, dict):
            continue

        raw_score = exam_result.get("score")
        try:
            numeric_score = float(raw_score)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric_score):
            continue

        exam_scores.append(numeric_score)

    if not exam_scores:
        return None
    return round(sum(exam_scores) / len(exam_scores), 1)


def _safe_nonnegative_int(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(numeric):
        return 0
    return max(int(round(numeric)), 0)


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


def _attendance_rate_to_score(attendance_rate):
    bounded_rate = max(0, min(int(attendance_rate), 100))
    if bounded_rate == 0:
        return 0
    return max(1, min(9, _round_grade_half_up((bounded_rate / 100) * 9)))


def _collect_subject_dashboards_from_dataset(
    dataset,
    subject,
):
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


def _collect_subject_dashboards_from_cache(subject):
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


def _build_subject_rating(
    student_id,
    dashboards,
):
    leaderboard = _build_subject_leaderboard(dashboards)
    total = len(leaderboard)
    for row in leaderboard:
        if int(row.get("studentId", -1)) == student_id:
            return {"rank": int(row.get("rank", 0)), "total": total}
    return None


def _round_grade_half_up(value):
    return int(math.floor(value + 0.5))


def _build_subject_leaderboard(
    dashboards,
):
    # Each row stores raw values we need for sorting and final display.
    ranking_rows = []

    for dashboard_payload in dashboards:
        student = dashboard_payload.get("student", {})
        if not isinstance(student, dict):
            continue

        student_id = student.get("id")
        if not isinstance(student_id, int):
            continue

        average_grade = _extract_numeric_average_grade(dashboard_payload)
        if average_grade is None:
            average_grade = 0.0

        full_name = str(student.get("fullName", "")).strip()
        surname = str(student.get("surname", "")).strip()
        name = str(student.get("name", "")).strip()
        display_name = f"{surname} {name}".strip() if surname and name else full_name
        group_name = str(student.get("group", "")).strip()

        avg_exam_score = _extract_exam_average_score(dashboard_payload) or 0.0
        exam_performance = (
            _round_grade_half_up(avg_exam_score) if avg_exam_score > 0 else 0
        )
        aap = _round_grade_half_up(average_grade)
        attendance_rate = _extract_attendance_rate(dashboard_payload)
        attendance_score = _attendance_rate_to_score(attendance_rate)
        average_composite = round((exam_performance + aap + attendance_score) / 3, 1)

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
                "aap": aap,
                "attendanceRate": attendance_rate,
                "attendanceScore": attendance_score,
                "averageComposite": average_composite,
                "averageCompositeDisplay": f"{average_composite:.1f}",
            }
        )

    ranking_rows.sort(
        # Sort by the same priority users see in the rating board.
        key=lambda row: (
            -float(row["averageComposite"]),
            -int(row["examPerformance"]),
            -int(row["aap"]),
            -int(row["attendanceRate"]),
            str(row["sortName"]),
            int(row["studentId"]),
        )
    )

    leaderboard = []
    for position, row in enumerate(ranking_rows, start=1):
        average_grade = float(row["averageGrade"])

        leaderboard.append(
            {
                "rank": position,
                "position": position,
                "studentId": row["studentId"],
                "displayName": row["displayName"],
                "group": row["group"],
                "avgExamScoreDisplay": row["avgExamScoreDisplay"],
                "examPerformance": row["examPerformance"],
                "aap": row["aap"],
                "attendanceRate": row["attendanceRate"],
                "attendanceScore": row["attendanceScore"],
                "averageComposite": row["averageComposite"],
                "averageCompositeDisplay": row["averageCompositeDisplay"],
                "averageGrade": average_grade,
            }
        )

    return leaderboard


def _compute_subject_rating(
    student_id,
    payload,
    dataset = None,
):
    student = payload.get("student", {})
    if not isinstance(student, dict):
        return None

    subject = str(student.get("subject", "")).strip()
    if not subject:
        return None

    dashboards = []
    if dataset:
        dashboards = _collect_subject_dashboards_from_dataset(dataset, subject)

    if not dashboards:
        dashboards = _collect_subject_dashboards_from_cache(subject)

    if not dashboards:
        refreshed_dataset, load_error = _load_dataset()
        if load_error or not refreshed_dataset:
            return None
        _seed_group_cache_from_dataset(refreshed_dataset)
        dashboards = _collect_subject_dashboards_from_dataset(refreshed_dataset, subject)

    return _build_subject_rating(student_id=student_id, dashboards=dashboards)


def _empty_form_data():
    return {
        "student_id": "",
        "group": "",
        "subject": "",
    }


def _is_full_form(form_data):
    return all(form_data.values())


def _search_student(
    students,
    surname,
    name,
    group,
    subject,
):
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


def _build_students_by_subject_group(
    students,
):
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

    return students_by_subject_group


def _load_dataset():
    # Single place that wraps data load errors from Google Sheets.
    try:
        return get_school_dataset(), None
    except SheetsDataError as exc:
        return None, str(exc)


def _load_dashboard_payload(
    student_id,
    requested_subject,
    requested_group,
):
    dataset = None
    payload = None
    cache_error = None

    if requested_subject and requested_group:
        group_cache_entry, cache_error = _get_group_cache_entry(
            requested_subject,
            requested_group,
        )
        if group_cache_entry:
            payload = group_cache_entry.get("dashboards_by_id", {}).get(student_id)

    if payload is None:
        dataset, load_error = _load_dataset()
        if load_error or not dataset:
            return None, None, load_error or cache_error or "Unable to load Google Sheets data."
        _seed_group_cache_from_dataset(dataset)
        payload = dataset["dashboards_by_id"].get(student_id)

    return payload, dataset, None


@app.context_processor
def inject_asset_version():
    return {"asset_version": ASSET_VERSION}


@app.after_request
def add_common_headers(response):
    # Apply shared security/cache headers for every response.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    if request.path == "/" or request.path.startswith("/dashboard/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"

    if request.path.startswith("/static/") and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "public, max-age=2592000, immutable"

    return response


def _is_authenticated_session():
    auth_role = str(session.get("auth_role", "")).strip().lower()
    if auth_role == "admin":
        return bool(session.get("admin_id"))
    if auth_role == "student":
        return bool(session.get("student_db_id")) and bool(session.get("student_sheet_id"))
    return False


@app.before_request
def require_authentication_for_protected_routes():
    endpoint = request.endpoint or ""
    public_endpoints = {
        "static",
        "home",
        "login",
        "logout",
        "manifest",
        "service_worker",
    }
    if endpoint in public_endpoints:
        return None

    if _is_authenticated_session():
        return None

    if request.path.startswith("/api/"):
        return jsonify({"message": "Authentication required."}), 401
    return redirect(url_for("home"))


try:
    from .routes.dashboard import register_dashboard_routes
    from .routes.home import register_home_routes
    from .routes.rating_board import register_rating_board_routes
except ImportError:
    if __package__:
        raise
    from routes.dashboard import register_dashboard_routes
    from routes.home import register_home_routes
    from routes.rating_board import register_rating_board_routes


# Route modules register endpoint handlers on the shared app object.
register_home_routes(
    app,
    load_dataset=_load_dataset,
    seed_group_cache_from_dataset=_seed_group_cache_from_dataset,
    build_students_by_subject_group=_build_students_by_subject_group,
    empty_form_data=_empty_form_data,
    is_full_form=_is_full_form,
    get_group_cache_entry=_get_group_cache_entry,
    search_student=_search_student,
)
register_dashboard_routes(
    app,
    load_dashboard_payload=_load_dashboard_payload,
    load_dataset=_load_dataset,
    extract_attendance_rate=_extract_attendance_rate,
    extract_exam_average_score=_extract_exam_average_score,
    round_grade_half_up=_round_grade_half_up,
    compute_subject_rating=_compute_subject_rating,
)
register_rating_board_routes(
    app,
    load_dashboard_payload=_load_dashboard_payload,
    collect_subject_dashboards_from_dataset=_collect_subject_dashboards_from_dataset,
    collect_subject_dashboards_from_cache=_collect_subject_dashboards_from_cache,
    load_dataset=_load_dataset,
    seed_group_cache_from_dataset=_seed_group_cache_from_dataset,
    build_subject_leaderboard=_build_subject_leaderboard,
)


@app.get("/manifest.webmanifest")
def manifest():
    response = make_response(app.send_static_file("manifest.webmanifest"))
    response.headers["Content-Type"] = "application/manifest+json"
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.get("/sw.js")
def service_worker():
    response = make_response(app.send_static_file("js/sw.js"))
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Cache-Control"] = "no-cache"
    return response


if __name__ == "__main__":
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
