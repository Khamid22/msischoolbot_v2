import hashlib
import json
import math
import os
import threading
import time
from datetime import timedelta

from flask import Flask, jsonify, redirect, request, session, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from app.auth.policies import is_authenticated_session as is_authenticated_policy_session
from app.auth.session import configure_login_manager
from app.config.schools import get_configured_school_spreadsheets
from app.config.settings import get_web_settings
from app.extensions import init_extensions, login_manager
from app.routes.admin.admin_page import register_admin_page_routes
from app.routes.admin.upload_progress_ws import register_admin_upload_progress_ws
from app.routes.system_routes import register_system_routes
from app.routes.students.student_page import register_student_page_routes
from app.routes.students.services.dataset_service import SheetsDataError, get_school_dataset
from app.routes.webhooks import register_webhook_routes
from app.storage.db_config import get_auth_db_path

_BACKEND_DIR = os.path.dirname(__file__)
_FRONTEND_DIR = os.path.join(_BACKEND_DIR, "web")
_TEMPLATE_DIR = os.path.join(_FRONTEND_DIR, "templates")
_STATIC_DIR = os.path.join(_FRONTEND_DIR, "static")
_CSS_DIR = os.path.join(_STATIC_DIR, "css")
app = Flask(
    __name__,
    template_folder=_TEMPLATE_DIR,
    static_folder=_STATIC_DIR,
    static_url_path="/static",
)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    days=int(os.environ.get("SESSION_LIFETIME_DAYS", "365"))
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.abspath(get_auth_db_path())
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None

init_extensions(app)
configure_login_manager(login_manager)


def _build_default_asset_version():
    # Build a simple asset version from the latest static/template file mtime.
    candidate_paths = [
        os.path.join(_BACKEND_DIR, "server.py"),
        os.path.join(_TEMPLATE_DIR, "student", "dashboard.html"),
        os.path.join(_TEMPLATE_DIR, "home.html"),
        os.path.join(_TEMPLATE_DIR, "auth", "login.html"),
        os.path.join(_TEMPLATE_DIR, "student", "home.html"),
        os.path.join(_TEMPLATE_DIR, "admin", "home.html"),
        os.path.join(_TEMPLATE_DIR, "layouts", "portal.html"),
        os.path.join(_STATIC_DIR, "js", "dashboard.js"),
        os.path.join(_STATIC_DIR, "js", "home.js"),
        os.path.join(_STATIC_DIR, "js", "pwa.js"),
        os.path.join(_STATIC_DIR, "js", "sw.js"),
    ]

    css_root = os.path.join(_STATIC_DIR, "css")
    for root_dir, _dir_names, file_names in os.walk(css_root):
        for file_name in file_names:
            if not file_name.endswith(".css"):
                continue
            candidate_paths.append(os.path.join(root_dir, file_name))

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
_ASSET_VERSION = (
    _asset_version_override
    if _asset_version_override and _asset_version_override != "1"
    else _build_default_asset_version()
)

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
_SEEDED_DATASET_TOKENS = {}
_SEEDING_IN_PROGRESS = set()
_STUDENTS_BY_SUBJECT_GROUP_CACHE = {}


def _clear_group_cache():
    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE.clear()
        _SEEDED_DATASET_TOKENS.clear()
        _SEEDING_IN_PROGRESS.clear()
        _STUDENTS_BY_SUBJECT_GROUP_CACHE.clear()


def _normalize(value):
    return " ".join(value.strip().casefold().split())


_SCHOOL_CODE_ALIASES = {
    "school_5": "school5",
    "school-5": "school5",
    "school 5": "school5",
    "school5": "school5",
    "sehriyo": "sehriyo",
    "sehriyo school": "sehriyo",
}


def _normalize_school_code(value):
    normalized = str(value or "").strip().casefold()
    return _SCHOOL_CODE_ALIASES.get(normalized, normalized)


def _iter_dashboard_school_codes(preferred_school_code = ""):
    configured_codes = list(get_configured_school_spreadsheets().keys())
    if not configured_codes:
        configured_codes = ["school5"]

    normalized_preferred_code = _normalize_school_code(preferred_school_code)
    ordered_codes = []
    if normalized_preferred_code and normalized_preferred_code in configured_codes:
        ordered_codes.append(normalized_preferred_code)

    for school_code in configured_codes:
        if school_code not in ordered_codes:
            ordered_codes.append(school_code)

    return ordered_codes


def _group_cache_key(subject, group):
    return (_normalize(subject), _normalize(group))


def _seed_group_cache_from_dataset(dataset):
    students = dataset.get("students", [])
    dashboards_by_id = dataset.get("dashboards_by_id", {})
    if not isinstance(students, list) or not isinstance(dashboards_by_id, dict):
        return

    now = time.time()
    dataset_token = int(id(dataset))

    with _GROUP_CACHE_LOCK:
        if dataset_token in _SEEDING_IN_PROGRESS:
            return
        token_expires_at = float(_SEEDED_DATASET_TOKENS.get(dataset_token, 0))
        if now < token_expires_at:
            return
        _SEEDING_IN_PROGRESS.add(dataset_token)

    try:
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

        expires_at = now + GROUP_CACHE_TTL_SECONDS
        for entry in grouped_entries.values():
            entry["students"].sort(key=lambda item: _normalize(str(item.get("fullName", ""))))
            entry["expires_at"] = expires_at

        with _GROUP_CACHE_LOCK:
            _GROUP_CACHE.update(grouped_entries)
            _SEEDED_DATASET_TOKENS[dataset_token] = expires_at
            seeded_dataset_tokens = dict(_SEEDED_DATASET_TOKENS)

        # Prune expired/old dataset tokens to keep memory bounded.
        expired_tokens = [
            token
            for token, token_expiry in seeded_dataset_tokens.items()
            if float(token_expiry) <= now
        ]
        tokens_to_prune = []
        if len(seeded_dataset_tokens) > 512:
            ordered_tokens = sorted(
                seeded_dataset_tokens.items(),
                key=lambda item: float(item[1]),
            )
            tokens_to_prune = [
                token
                for token, _expiry in ordered_tokens[: len(seeded_dataset_tokens) - 512]
            ]

        with _GROUP_CACHE_LOCK:
            for token in expired_tokens:
                if float(_SEEDED_DATASET_TOKENS.get(token, 0)) <= now:
                    _SEEDED_DATASET_TOKENS.pop(token, None)
            for token in tokens_to_prune:
                if len(_SEEDED_DATASET_TOKENS) <= 512:
                    break
                _SEEDED_DATASET_TOKENS.pop(token, None)
    finally:
        with _GROUP_CACHE_LOCK:
            _SEEDING_IN_PROGRESS.discard(dataset_token)


def _get_group_cache_entry(subject, group, school_code = "", force_refresh = False):
    # Try cached group first; if expired/missing, refresh from Google Sheets.
    key = _group_cache_key(subject, group)
    now = time.time()

    if not force_refresh:
        with _GROUP_CACHE_LOCK:
            cached_entry = _GROUP_CACHE.get(key)
            if cached_entry and now < float(cached_entry.get("expires_at", 0)):
                return cached_entry, None

    dataset, load_error = _load_dataset(
        school_code=school_code,
        force_refresh=force_refresh,
    )
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
    if not isinstance(students, list):
        return {}

    now = time.time()
    serialized_students = json.dumps(students, sort_keys=True).encode()
    cache_key = hashlib.md5(serialized_students).hexdigest()
    with _GROUP_CACHE_LOCK:
        cached_entry = _STUDENTS_BY_SUBJECT_GROUP_CACHE.get(cache_key)
        if cached_entry and now < float(cached_entry.get("expires_at", 0)):
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
            "value": students_by_subject_group,
            "expires_at": expires_at,
        }
        # Keep cache small and drop expired entries.
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


def _load_dataset(school_code = None, force_refresh = False):
    # Single place that wraps data load errors from Google Sheets.
    try:
        return get_school_dataset(
            force_refresh=force_refresh,
            school_code=school_code,
        ), None
    except SheetsDataError as exc:
        return None, str(exc)


def _load_dashboard_payload(
    student_id,
    requested_subject,
    requested_group,
    requested_school = "",
    force_refresh = False,
):
    dataset = None
    payload = None
    cache_error = None
    first_load_error = ""
    normalized_requested_school = _normalize_school_code(requested_school)

    if requested_subject and requested_group:
        group_cache_entry, cache_error = _get_group_cache_entry(
            requested_subject,
            requested_group,
            school_code=normalized_requested_school,
            force_refresh=force_refresh,
        )
        if group_cache_entry:
            cached_payload = group_cache_entry.get("dashboards_by_id", {}).get(student_id)
            if cached_payload and normalized_requested_school:
                cached_student = (
                    cached_payload.get("student", {})
                    if isinstance(cached_payload, dict)
                    else {}
                )
                cached_school_code = _normalize_school_code(
                    cached_student.get("schoolCode", "")
                )
                if cached_school_code == normalized_requested_school:
                    payload = cached_payload
            else:
                payload = cached_payload

    if payload is not None:
        return payload, dataset, None

    any_dataset_loaded = False
    for school_code in _iter_dashboard_school_codes(normalized_requested_school):
        dataset, load_error = _load_dataset(
            school_code=school_code,
            force_refresh=force_refresh,
        )
        if load_error or not dataset:
            if not first_load_error:
                first_load_error = load_error or ""
            continue

        any_dataset_loaded = True
        _seed_group_cache_from_dataset(dataset)
        payload = dataset.get("dashboards_by_id", {}).get(student_id)
        if payload is not None:
            return payload, dataset, None

    if not any_dataset_loaded:
        return (
            None,
            None,
            first_load_error or cache_error or "Unable to load Google Sheets data.",
        )

    return payload, dataset, None


@app.context_processor
def inject_asset_version():
    return {"asset_version": _ASSET_VERSION}


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
    if bool(getattr(current_user, "is_authenticated", False)):
        return True
    return bool(is_authenticated_policy_session(session))


@app.before_request
def require_authentication_for_protected_routes():
    endpoint = request.endpoint or ""
    endpoint_name = endpoint.split(".")[-1] if endpoint else ""
    public_endpoints = {
        "static",
        "home",
        "login",
        "logout",
        "manifest",
        "service_worker",
        "google_sheets_webhook",
    }
    if endpoint in public_endpoints or endpoint_name in public_endpoints:
        return None

    if _is_authenticated_session():
        session.permanent = True
        return None

    if request.path.startswith("/api/"):
        return jsonify({"message": "Authentication required."}), 401
    return redirect(url_for("student.home"))


@app.errorhandler(CSRFError)
def handle_csrf_error(_error):
    if request.path.startswith("/api/"):
        return jsonify({"message": "Invalid or missing CSRF token."}), 400
    return redirect(url_for("student.home"))


render_admin_page = register_admin_page_routes(
    app,
    load_dataset=_load_dataset,
)
register_student_page_routes(
    app,
    render_admin_page=render_admin_page,
    load_dataset=_load_dataset,
    seed_group_cache_from_dataset=_seed_group_cache_from_dataset,
    build_students_by_subject_group=_build_students_by_subject_group,
    is_full_form=_is_full_form,
    get_group_cache_entry=_get_group_cache_entry,
    search_student=_search_student,
    load_dashboard_payload=_load_dashboard_payload,
    collect_subject_dashboards_from_dataset=_collect_subject_dashboards_from_dataset,
    collect_subject_dashboards_from_cache=_collect_subject_dashboards_from_cache,
    extract_attendance_rate=_extract_attendance_rate,
    extract_exam_average_score=_extract_exam_average_score,
    round_grade_half_up=_round_grade_half_up,
    compute_subject_rating=_compute_subject_rating,
    build_subject_leaderboard=_build_subject_leaderboard,
)
register_webhook_routes(
    app,
    clear_group_cache=_clear_group_cache,
)
register_system_routes(app)
register_admin_upload_progress_ws()
