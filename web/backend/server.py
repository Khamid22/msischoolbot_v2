import math
import os
import re
import hashlib
import threading
import time
from datetime import timedelta

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from web.backend.utils.limiter import limiter

from web.backend.utils.context import RequestContextMiddleware, session, request
from web.backend.utils.demo_auth import is_demo_auth_enabled, maybe_apply_demo_auth
from web.backend.utils.normalization import normalize_text as _normalize, normalize_school_code as _normalize_school_code
from config import get_web_settings
from web.backend.roles.admin.routes import register_admin_page_routes
from web.backend.roles.parent.routes import register_parent_invite_routes
from web.backend.roles.student.routes import register_student_page_routes
from web.backend.roles.teacher.routes import register_teacher_page_routes

_BACKEND_DIR = os.path.dirname(__file__)
_STATIC_DIR = os.path.join(_BACKEND_DIR, "static")
_REACT_DIR = os.path.join(_STATIC_DIR, "react")

_CACHE_NO_STORE = "no-store, max-age=0"
_CACHE_NO_CACHE_REVALIDATE = "no-cache, no-store, must-revalidate"
_CACHE_LONG_IMMUTABLE = "public, max-age=31536000, immutable"
_CACHE_STATIC_DEFAULT = "public, max-age=2592000, immutable"

_HASHED_REACT_ASSET_FILE_RE = re.compile(r"-[A-Za-z0-9_-]{8,}\.(js|css)$")
_VERSIONED_REACT_ENTRY_RE = re.compile(r"^/static/react/app\.(js|css)$")
_VERSIONED_BUNDLE_RE = re.compile(r"^/static/js/bundles/[^/]+\.js$")

def _resolve_cache_control_header(request_path: str, query_version: str = ""):
    if request_path == "/" or request_path.startswith("/dashboard/"):
        return _CACHE_NO_STORE

    if request_path.startswith("/api/") or request_path.startswith("/admin/api/"):
        return _CACHE_NO_STORE

    if request_path.startswith("/static/react/"):
        file_name = os.path.basename(request_path)
        if file_name in {"manifest.json", "index.html"}:
            return _CACHE_NO_CACHE_REVALIDATE
        if _HASHED_REACT_ASSET_FILE_RE.search(file_name):
            return _CACHE_LONG_IMMUTABLE
        if query_version and _VERSIONED_REACT_ENTRY_RE.match(request_path):
            return _CACHE_LONG_IMMUTABLE
        return _CACHE_NO_STORE

    if request_path.startswith("/static/js/bundles/"):
        if query_version and _VERSIONED_BUNDLE_RE.match(request_path):
            return _CACHE_LONG_IMMUTABLE
        return _CACHE_NO_STORE

    if request_path.startswith("/static/"):
        return _CACHE_STATIC_DEFAULT

    return None

PUBLIC_PATHS = {
    "/",
    "/login",
    "/auth/telegram",
    "/admin",
    "/admin/continue",
    # /teacher self-gates to the teacher role (see roles/teacher/routes.py). Listing
    # it public keeps the teacher role OUT of the {admin, student} auth gate above,
    # so a teacher session can reach ONLY /teacher + login/logout/static.
    "/teacher",
    "/manifest.webmanifest",
    "/sw.js",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/system/status",
}
_STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Endpoints authenticated by a signed payload rather than the ambient session
# cookie are exempt from the same-origin/CSRF check: a cross-site forgery gains
# nothing because the request must itself carry a server-verified signature.
# /auth/telegram only trusts HMAC-validated Telegram initData.
_SAME_ORIGIN_EXEMPT_PATHS = {"/auth/telegram"}

class AuthAndSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_obj = Request(scope, receive=receive)
        path = request_obj.url.path
        maybe_apply_demo_auth(request_obj)

        # 1. Reject cross-origin state changes (Same-Origin check). Applies to
        # every mutating method on every path (not just /api/), so plain admin
        # form posts like /admin/teachers are covered too.
        if request_obj.method in _STATE_CHANGING_METHODS and path not in _SAME_ORIGIN_EXEMPT_PATHS:
            origin = request_obj.headers.get("Origin") or request_obj.headers.get("Referer") or ""
            is_api = path.startswith("/api/") or path.startswith("/admin/api/")
            if origin:
                from urllib.parse import urlparse
                host = request_obj.headers.get("host") or ""
                host_name = host.split(":")[0] if ":" in host else host
                origin_netloc = urlparse(origin).netloc
                origin_name = origin_netloc.split(":")[0] if ":" in origin_netloc else origin_netloc
                if origin_name != host_name:
                    response = JSONResponse({"message": "Cross-origin request rejected."}, status_code=403)
                    await response(scope, receive, send)
                    return
            elif is_api:
                # No Origin/Referer on an XHR/JSON API call: require the
                # XMLHttpRequest marker, which a cross-site page cannot set
                # without a CORS preflight. Same-origin HTML form posts that omit
                # both headers are allowed here because the SameSite=Lax session
                # cookie already prevents a cross-site POST from carrying auth.
                if request_obj.headers.get("X-Requested-With") != "XMLHttpRequest":
                    response = JSONResponse({"message": "Cross-origin request rejected."}, status_code=403)
                    await response(scope, receive, send)
                    return

        # 2. Authentication check
        is_public = (
            path in PUBLIC_PATHS
            or path.startswith("/static/")
            or path.startswith("/teacher/")
            # Parent invite links are reached by a logged-out parent. Auth is the
            # signed, server-verified token in the URL itself (same trust model as
            # /auth/telegram), so the path must bypass the session-cookie gate.
            or path.startswith("/parent/link/")
            or path.startswith("/parent/invite/")
        )

        if not is_public:
            auth_role = request_obj.session.get("auth_role")
            if not auth_role or auth_role not in {"admin", "student", "parent"}:
                requested_with = request_obj.headers.get("X-Requested-With") or ""
                is_xhr = requested_with == "XMLHttpRequest"
                if path.startswith("/api/") or is_xhr:
                    response = JSONResponse({"message": "Authentication required."}, status_code=401)
                    await response(scope, receive, send)
                    return
                response = RedirectResponse(url="/", status_code=302)
                await response(scope, receive, send)
                return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                header_names = {h[0].lower() for h in headers}

                if b"x-content-type-options" not in header_names:
                    headers.append((b"x-content-type-options", b"nosniff"))
                if b"referrer-policy" not in header_names:
                    headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))

                cache_control = _resolve_cache_control_header(
                    request_path=path,
                    query_version=request_obj.query_params.get("v", ""),
                )
                if cache_control and b"cache-control" not in header_names:
                    headers.append((b"cache-control", cache_control.encode("utf-8")))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

# Limiter imported from utils.limiter

# Instantiate FastAPI application
app = FastAPI(
    title="MSI School API",
    description="Backend API for MSI School Bot and Web portal management, serving multiple role-based dashboards.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "identity", "description": "Authentication and user session management."},
        {"name": "student", "description": "Student-specific views and dashboard APIs."},
        {"name": "admin", "description": "System administration, settings, and general management."},
        {"name": "parent", "description": "Parent dashboard, student linked data access."},
        {"name": "resources", "description": "Study materials, resources, and file management."},
        {"name": "payments", "description": "Payment history, details, and billing APIs."},
        {"name": "communication", "description": "Chats, system complaints, and messaging routes."},
        {"name": "system", "description": "System diagnostics, health checks, and metadata utilities."},
    ],
)
app.state.limiter = limiter

app.name = "web.backend.server"
app.static_folder = _STATIC_DIR
app.backend_root_path = _BACKEND_DIR

# Fail closed: a known/default signing key lets anyone forge a session cookie
_secret_key = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
if not _secret_key:
    if os.environ.get("APP_ENV", "").strip().lower() in {"dev", "development", "local"}:
        _secret_key = "dev-only-insecure-key-do-not-use-in-prod"
    else:
        raise RuntimeError(
            "APP_SECRET_KEY must be set. Generate one with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )

# Register Starlette and Custom middlewares
app.add_middleware(AuthAndSecurityMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=512)
app.add_middleware(
    SessionMiddleware,
    secret_key=_secret_key,
    session_cookie="session",
    max_age=30 * 24 * 3600,  # 30 days
    same_site=os.environ.get("SESSION_COOKIE_SAMESITE", "lax").lower(),
    https_only=os.environ.get("SESSION_COOKIE_SECURE", "0").strip().lower() not in {"0", "false", "no", "off"},
)

# Mount static files correctly
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")




# Expose settings
settings = get_web_settings()
GROUP_CACHE_TTL_SECONDS = int(os.environ.get("GROUP_CACHE_TTL_SECONDS", "600"))
RATING_CACHE_TTL_SECONDS = int(os.environ.get("RATING_CACHE_TTL_SECONDS", "60"))
RATING_CACHE_MAX_ENTRIES = int(os.environ.get("RATING_CACHE_MAX_ENTRIES", "128"))

_GROUP_CACHE_LOCK = threading.Lock()
# In-memory cache keyed by (subject, group) to avoid repeated dataset rebuilds
_GROUP_CACHE = {}
_STUDENTS_BY_SUBJECT_GROUP_CACHE = {}
_RATING_CACHE_LOCK = threading.Lock()
_RATING_LEADERBOARD_CACHE = {}
_APP_BOOTSTRAPPED = False




# Rate limiter exception handler
@app.exception_handler(RateLimitExceeded)
def handle_rate_limited(request_obj: Request, exc: RateLimitExceeded):
    message = "Too many attempts. Please wait a moment and try again."
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith(("/api/", "/admin/api/")) or is_xhr:
        return JSONResponse({"message": message}, status_code=429)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(message, status_code=429)


# HTTP exception handler
@app.exception_handler(HTTPException)
def handle_http_exception(request_obj: Request, exc: HTTPException):
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith(("/api/", "/admin/api/")) or is_xhr:
        return JSONResponse({"message": exc.detail}, status_code=exc.status_code)
    if exc.status_code in {401, 403}:
        return RedirectResponse(url="/", status_code=302)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(exc.detail, status_code=exc.status_code)


# Global unexpected error handler
@app.exception_handler(Exception)
def handle_unexpected_error(request_obj: Request, exc: Exception):
    import logging
    logging.exception("Unhandled error on %s %s", request_obj.method, request_obj.url.path)
    requested_with = request_obj.headers.get("X-Requested-With", "")
    is_xhr = requested_with == "XMLHttpRequest"
    if request_obj.url.path.startswith(("/api/", "/admin/api/")) or is_xhr:
        return JSONResponse({"message": "Something went wrong. Please try again."}, status_code=500)
    return RedirectResponse(url="/", status_code=302)


def _clear_group_cache():
    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE.clear()
        _STUDENTS_BY_SUBJECT_GROUP_CACHE.clear()
    with _RATING_CACHE_LOCK:
        _RATING_LEADERBOARD_CACHE.clear()


def _iter_dashboard_school_codes(preferred_school_code = ""):
    configured_codes = ["school5", "sehriyo"]
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


def _seed_group_cache_from_dataset(dataset, force=False):
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


def _get_group_cache_entry(subject, group, school_code = "", force_refresh = False):
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
        return None, load_error or "Unable to load internal academic data."

    _seed_group_cache_from_dataset(dataset, force=force_refresh)

    with _GROUP_CACHE_LOCK:
        cached_entry = _GROUP_CACHE.get(key)
        if cached_entry and time.time() < float(cached_entry.get("expires_at", 0)):
            return cached_entry, None

    return None, "Selected group data was not found."


def _extract_numeric_average_grade(dashboard_payload):
    scores = _extract_homework_scores(dashboard_payload)
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


def _extract_homework_scores(dashboard_payload):
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


def _extract_exam_average_score(dashboard_payload):
    best_scores = _extract_best_exam_scores(dashboard_payload)
    if not best_scores:
        return None
    return round(sum(best_scores.values()) / len(best_scores), 1)


def _normalize_exam_rating_key(value):
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return " ".join(normalized.casefold().split())


def _extract_best_exam_scores(dashboard_payload):
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


def _extract_attendance_total(dashboard_payload):
    attendance_record = dashboard_payload.get("attendanceRecord", {})
    if not isinstance(attendance_record, dict):
        attendance_record = {}

    present = _safe_nonnegative_int(attendance_record.get("presentCount", 0))
    absent = _safe_nonnegative_int(attendance_record.get("absentCount", 0))
    justified_absent = _safe_nonnegative_int(
        attendance_record.get("justifiedAbsentCount", 0)
    )
    return present + absent + justified_absent


def _attendance_rate_to_score(attendance_rate):
    bounded_rate = max(0, min(int(attendance_rate), 100))
    if bounded_rate == 0:
        return 0
    return round((bounded_rate / 100) * 9, 1)


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

        average_grade = _extract_numeric_average_grade(dashboard_payload)
        if average_grade is None:
            average_grade = 0.0

        full_name = str(student.get("fullName", "")).strip()
        surname = str(student.get("surname", "")).strip()
        name = str(student.get("name", "")).strip()
        display_name = f"{surname} {name}".strip() if surname and name else full_name
        group_name = str(student.get("group", "")).strip()

        best_exam_scores = _extract_best_exam_scores(dashboard_payload)
        exam_count = len(best_exam_scores)
        avg_exam_score = (
            round(sum(best_exam_scores.values()) / exam_count, 1)
            if exam_count
            else 0.0
        )
        exam_performance = (
            _round_grade_half_up(avg_exam_score) if avg_exam_score > 0 else 0
        )
        homework_count = len(_extract_homework_scores(dashboard_payload))
        aap = _round_grade_half_up(average_grade)
        attendance_rate = _extract_attendance_rate(dashboard_payload)
        attendance_score = _attendance_rate_to_score(attendance_rate)
        attendance_total = _extract_attendance_total(dashboard_payload)
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
        from web.backend.domains.academics.internal_dashboard_service import get_subject_dashboards_from_db
        dashboards = get_subject_dashboards_from_db(subject)

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


def _load_dataset(school_code = None, force_refresh = False):
    from web.backend.domains.academics.internal_dashboard_service import build_internal_dataset
    dataset = build_internal_dataset(school_code or "")
    if dataset:
        _seed_group_cache_from_dataset(dataset, force=bool(force_refresh))
        return dataset, None
    return None, "Internal academic data is not available."


def _load_dashboard_payload(
    student_id,
    requested_subject,
    requested_group,
    requested_school = "",
    force_refresh = False,
):
    normalized_requested_school = _normalize_school_code(requested_school)
    from web.backend.domains.academics.internal_dashboard_service import get_enrollment_dashboard
    db_payload = get_enrollment_dashboard(student_id, normalized_requested_school)
    if db_payload is not None:
        return db_payload, None, None

    if requested_subject and requested_group:
        group_cache_entry, _cache_error = _get_group_cache_entry(
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


def _build_default_asset_version():
    candidate_paths = [
        os.path.join(_BACKEND_DIR, "js_bundles.py"),
        os.path.join(_BACKEND_DIR, "server.py"),
        os.path.join(_BACKEND_DIR, "render.py"),
        os.path.join(_REACT_DIR, "manifest.json"),
        os.path.join(_REACT_DIR, "app.css"),
        os.path.join(_REACT_DIR, "app.js"),
    ]

    js_roots = [
        os.path.join(_STATIC_DIR, "js"),
    ]
    for js_root in js_roots:
        for root_dir, _dir_names, file_names in os.walk(js_root):
            for file_name in file_names:
                if not file_name.endswith(".js"):
                    continue
                candidate_paths.append(os.path.join(root_dir, file_name))

    if os.path.isdir(_REACT_DIR):
        for root_dir, _dir_names, file_names in os.walk(_REACT_DIR):
            for file_name in file_names:
                if not (file_name.endswith(".js") or file_name.endswith(".css")):
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


def _bootstrap_app(app_instance):
    global _APP_BOOTSTRAPPED
    if _APP_BOOTSTRAPPED:
        return app_instance

    # Loudly flag demo auth at startup. When DEMO_AUTH_ENABLED is on, anyone who
    # reaches the app is auto-logged-in (owner-level for /admin) with no
    # credentials. That is intentional for team testing, but must never be left
    # on for real users — this banner makes it impossible to forget.
    import logging as _logging

    if is_demo_auth_enabled():
        _is_prod = os.environ.get("APP_ENV", "").strip().lower() in {
            "prod",
            "production",
        }
        _logging.getLogger("uvicorn.error").warning(
            "DEMO_AUTH_ENABLED is ON — all visitors are auto-authenticated WITHOUT "
            "a password%s. Set DEMO_AUTH_ENABLED=0 before exposing this to real "
            "users.",
            " (APP_ENV=production!)" if _is_prod else "",
        )

    # Set static files dependencies in render.py
    import web.backend.render as render
    render.ASSET_VERSION = _ASSET_VERSION
    render.STATIC_FOLDER = _STATIC_DIR

    # Set static files dependencies in system.py
    import web.backend.routes.system as system_routes
    system_routes.STATIC_FOLDER = _STATIC_DIR

    # Include system router
    from web.backend.routes.system import router as system_router
    app_instance.include_router(system_router)

    # Register admin and student page routes
    render_admin_page = register_admin_page_routes(
        app_instance,
        clear_group_cache=_clear_group_cache,
    )
    register_student_page_routes(
        app_instance,
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
    register_teacher_page_routes(app_instance)
    register_parent_invite_routes(app_instance)

    _APP_BOOTSTRAPPED = True
    return app_instance


def create_app():
    return _bootstrap_app(app)


app = create_app()
