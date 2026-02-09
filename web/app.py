from __future__ import annotations

import os
import threading
import time
import math
from types import SimpleNamespace
from typing import Any

from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for

try:
    # Package import path (used by `from web.app import ...`).
    from .sheets_data import SheetsDataError, get_school_dataset
except ImportError:
    # If imported as a package (`python -m web.app`), propagate the original
    # error (e.g. missing dependency) instead of masking it.
    if __package__:
        raise
    # Script import path (used by `python web/app.py`).
    from sheets_data import SheetsDataError, get_school_dataset

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30


def _build_default_asset_version() -> str:
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
settings = SimpleNamespace(
    flask_host=os.environ.get("FLASK_HOST", "0.0.0.0"),
    flask_port=int(os.environ.get("PORT", os.environ.get("FLASK_PORT", "5000"))),
)
GROUP_CACHE_TTL_SECONDS = int(
    os.environ.get(
        "GROUP_CACHE_TTL_SECONDS",
        os.environ.get("SHEETS_CACHE_TTL_SECONDS", "600"),
    )
)

_GROUP_CACHE_LOCK = threading.Lock()
_GROUP_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _group_cache_key(subject: str, group: str) -> tuple[str, str]:
    return (_normalize(subject), _normalize(group))


def _seed_group_cache_from_dataset(dataset: dict[str, Any]) -> None:
    students = dataset.get("students", [])
    dashboards_by_id = dataset.get("dashboards_by_id", {})
    if not isinstance(students, list) or not isinstance(dashboards_by_id, dict):
        return

    grouped_entries: dict[tuple[str, str], dict[str, Any]] = {}
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


def _get_group_cache_entry(subject: str, group: str) -> tuple[dict[str, Any] | None, str | None]:
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


def _extract_numeric_average_grade(dashboard_payload: dict[str, Any]) -> float | None:
    raw_value = dashboard_payload.get("averageGrade")
    try:
        average_grade = float(raw_value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(average_grade):
        return None
    return average_grade


def _collect_subject_dashboards_from_dataset(
    dataset: dict[str, Any],
    subject: str,
) -> list[dict[str, Any]]:
    dashboards_by_id = dataset.get("dashboards_by_id", {})
    if not isinstance(dashboards_by_id, dict):
        return []

    subject_norm = _normalize(subject)
    dashboards: list[dict[str, Any]] = []
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


def _collect_subject_dashboards_from_cache(subject: str) -> list[dict[str, Any]]:
    subject_norm = _normalize(subject)
    now = time.time()
    dashboards: list[dict[str, Any]] = []

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
    student_id: int,
    dashboards: list[dict[str, Any]],
) -> dict[str, int] | None:
    ranking_rows: list[tuple[int, float, str]] = []

    for dashboard_payload in dashboards:
        student = dashboard_payload.get("student", {})
        if not isinstance(student, dict):
            continue

        current_student_id = student.get("id")
        if not isinstance(current_student_id, int):
            continue

        average_grade = _extract_numeric_average_grade(dashboard_payload)
        if average_grade is None:
            continue

        full_name = _normalize(str(student.get("fullName", "")))
        ranking_rows.append((current_student_id, average_grade, full_name))

    if not ranking_rows:
        return None

    ranking_rows.sort(key=lambda row: (-row[1], row[2], row[0]))

    total = len(ranking_rows)
    position = 0
    current_rank = 0
    previous_average: float | None = None

    for current_student_id, average_grade, _full_name in ranking_rows:
        position += 1
        if previous_average is None or not math.isclose(
            average_grade,
            previous_average,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            current_rank = position
            previous_average = average_grade

        if current_student_id == student_id:
            return {"rank": current_rank, "total": total}

    return None


def _compute_subject_rating(
    student_id: int,
    payload: dict[str, Any],
    dataset: dict[str, Any] | None = None,
) -> dict[str, int] | None:
    student = payload.get("student", {})
    if not isinstance(student, dict):
        return None

    subject = str(student.get("subject", "")).strip()
    if not subject:
        return None

    dashboards: list[dict[str, Any]] = []
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


def _empty_form_data() -> dict[str, str]:
    return {
        "student_id": "",
        "group": "",
        "subject": "",
    }


def _is_full_form(form_data: dict[str, str]) -> bool:
    return all(form_data.values())


def _search_student(
    students: list[dict[str, Any]],
    surname: str,
    name: str,
    group: str,
    subject: str,
) -> dict[str, Any] | None:
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
    students: list[dict[str, Any]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    students_by_subject_group: dict[str, dict[str, list[dict[str, Any]]]] = {}

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


def _load_dataset() -> tuple[dict[str, Any] | None, str | None]:
    try:
        return get_school_dataset(), None
    except SheetsDataError as exc:
        return None, str(exc)


@app.context_processor
def inject_asset_version() -> dict[str, str]:
    return {"asset_version": ASSET_VERSION}


@app.after_request
def add_common_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    if request.path == "/" or request.path.startswith("/dashboard/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"

    if request.path.startswith("/static/") and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "public, max-age=2592000, immutable"

    return response


@app.get("/")
def home() -> str:
    dataset, load_error = _load_dataset()
    groups = dataset["groups"] if dataset else []
    groups_by_subject = dataset["groups_by_subject"] if dataset else {}
    subjects = dataset["subjects"] if dataset else []
    if dataset:
        _seed_group_cache_from_dataset(dataset)
    students_by_subject_group = (
        _build_students_by_subject_group(dataset["students"]) if dataset else {}
    )

    return render_template(
        "home.html",
        groups=groups,
        groups_by_subject=groups_by_subject,
        subjects=subjects,
        students_by_subject_group=students_by_subject_group,
        error=load_error,
        form_data=_empty_form_data(),
    )


@app.post("/search")
def search_student_form():
    form_data = {
        "student_id": request.form.get("student_id", "").strip(),
        "group": request.form.get("group", "").strip(),
        "subject": request.form.get("subject", "").strip(),
    }

    if not _is_full_form(form_data):
        dataset, load_error = _load_dataset()
        if load_error or not dataset:
            return (
                render_template(
                    "home.html",
                    groups=[],
                    groups_by_subject={},
                    subjects=[],
                    students_by_subject_group={},
                    error=load_error or "Unable to load Google Sheets data.",
                    form_data=form_data,
                ),
                503,
            )

        return (
            render_template(
                "home.html",
                groups=dataset["groups"],
                groups_by_subject=dataset["groups_by_subject"],
                subjects=dataset["subjects"],
                students_by_subject_group=_build_students_by_subject_group(
                    dataset["students"]
                ),
                error="Please fill all fields.",
                form_data=form_data,
            ),
            400,
        )

    try:
        requested_student_id = int(form_data["student_id"])
    except ValueError:
        dataset, load_error = _load_dataset()
        if load_error or not dataset:
            return (
                render_template(
                    "home.html",
                    groups=[],
                    groups_by_subject={},
                    subjects=[],
                    students_by_subject_group={},
                    error=load_error or "Unable to load Google Sheets data.",
                    form_data=form_data,
                ),
                503,
            )

        return (
            render_template(
                "home.html",
                groups=dataset["groups"],
                groups_by_subject=dataset["groups_by_subject"],
                subjects=dataset["subjects"],
                students_by_subject_group=_build_students_by_subject_group(
                    dataset["students"]
                ),
                error="Please choose a valid student from the list.",
                form_data=form_data,
            ),
            400,
        )

    group_cache_entry, cache_error = _get_group_cache_entry(
        form_data["subject"],
        form_data["group"],
    )
    if group_cache_entry and requested_student_id in group_cache_entry.get("dashboards_by_id", {}):
        return redirect(
            url_for(
                "dashboard",
                student_id=requested_student_id,
                subject=form_data["subject"],
                group=form_data["group"],
            )
        )

    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return (
            render_template(
                "home.html",
                groups=[],
                groups_by_subject={},
                subjects=[],
                students_by_subject_group={},
                error=load_error or cache_error or "Unable to load Google Sheets data.",
                form_data=form_data,
            ),
            503,
        )

    return (
        render_template(
            "home.html",
            groups=dataset["groups"],
            groups_by_subject=dataset["groups_by_subject"],
            subjects=dataset["subjects"],
            students_by_subject_group=_build_students_by_subject_group(
                dataset["students"]
            ),
            error="Student not found. Please check your details.",
            form_data=form_data,
        ),
        404,
    )


@app.get("/dashboard/<int:student_id>")
def dashboard(student_id: int):
    requested_subject = request.args.get("subject", "").strip()
    requested_group = request.args.get("group", "").strip()

    dataset: dict[str, Any] | None = None
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
            return (
                render_template(
                    "not_found.html",
                    message=load_error or cache_error or "Unable to load Google Sheets data.",
                ),
                503,
            )
        _seed_group_cache_from_dataset(dataset)
        payload = dataset["dashboards_by_id"].get(student_id)

    if not payload:
        return (
            render_template(
                "not_found.html",
                message="We could not retrieve data for this student. Please search again.",
            ),
            404,
        )

    attendance_record = payload["attendanceRecord"]
    present = attendance_record.get("presentCount", 0)
    absent = attendance_record.get("absentCount", 0)
    justified_absent = attendance_record.get("justifiedAbsentCount", 0)
    total = present + absent + justified_absent
    attendance_rate = round(((present + justified_absent) / total) * 100) if total else 0
    program_total_lessons = 180
    completed_lessons = min(
        len(payload.get("homeworkGrades", [])),
        program_total_lessons,
    )
    program_completed_rate = round((completed_lessons / program_total_lessons) * 100)
    subject_rating = _compute_subject_rating(
        student_id=student_id,
        payload=payload,
        dataset=dataset,
    )

    return render_template(
        "dashboard.html",
        payload=payload,
        attendance_rate=attendance_rate,
        program_completed_lessons=completed_lessons,
        program_completed_rate=program_completed_rate,
        subject_rating=subject_rating,
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


@app.get("/api/metadata")
def api_metadata():
    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return jsonify({"message": load_error or "Unable to load Google Sheets data."}), 503

    return jsonify(
        {
            "groups": dataset["groups"],
            "groupsBySubject": dataset["groups_by_subject"],
            "studentsBySubjectGroup": _build_students_by_subject_group(
                dataset["students"]
            ),
            "subjects": dataset["subjects"],
        }
    )


@app.get("/api/students/search")
def api_search_student():
    surname = request.args.get("surname", "").strip()
    name = request.args.get("name", "").strip()
    group = request.args.get("group", "").strip()
    subject = request.args.get("subject", "").strip()

    if not all([surname, name, group, subject]):
        return jsonify({"message": "All fields are required."}), 400

    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return jsonify({"message": load_error or "Unable to load Google Sheets data."}), 503

    student = _search_student(
        dataset["students"],
        surname=surname,
        name=name,
        group=group,
        subject=subject,
    )
    if not student:
        return jsonify({"message": "Student not found"}), 404

    return jsonify(student)


@app.get("/api/students/<int:student_id>/dashboard")
def api_student_dashboard(student_id: int):
    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return jsonify({"message": load_error or "Unable to load Google Sheets data."}), 503

    payload = dataset["dashboards_by_id"].get(student_id)
    if not payload:
        return jsonify({"message": "Student not found"}), 404

    return jsonify(payload)


if __name__ == "__main__":
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
