from __future__ import annotations

import os
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


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _empty_form_data() -> dict[str, str]:
    return {
        "surname": "",
        "name": "",
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

    return render_template(
        "home.html",
        groups=groups,
        groups_by_subject=groups_by_subject,
        subjects=subjects,
        error=load_error,
        form_data=_empty_form_data(),
    )


@app.post("/search")
def search_student_form():
    form_data = {
        "surname": request.form.get("surname", "").strip(),
        "name": request.form.get("name", "").strip(),
        "group": request.form.get("group", "").strip(),
        "subject": request.form.get("subject", "").strip(),
    }

    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return (
            render_template(
                "home.html",
                groups=[],
                groups_by_subject={},
                subjects=[],
                error=load_error or "Unable to load Google Sheets data.",
                form_data=form_data,
            ),
            503,
        )

    if not _is_full_form(form_data):
        return (
            render_template(
                "home.html",
                groups=dataset["groups"],
                groups_by_subject=dataset["groups_by_subject"],
                subjects=dataset["subjects"],
                error="Please fill all fields.",
                form_data=form_data,
            ),
            400,
        )

    student = _search_student(
        dataset["students"],
        surname=form_data["surname"],
        name=form_data["name"],
        group=form_data["group"],
        subject=form_data["subject"],
    )

    if not student:
        return (
            render_template(
                "home.html",
                groups=dataset["groups"],
                groups_by_subject=dataset["groups_by_subject"],
                subjects=dataset["subjects"],
                error="Student not found. Please check your details.",
                form_data=form_data,
            ),
            404,
        )

    return redirect(url_for("dashboard", student_id=student["id"]))


@app.get("/dashboard/<int:student_id>")
def dashboard(student_id: int):
    dataset, load_error = _load_dataset()
    if load_error or not dataset:
        return (
            render_template(
                "not_found.html",
                message=load_error or "Unable to load Google Sheets data.",
            ),
            503,
        )

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

    return render_template(
        "dashboard.html",
        payload=payload,
        attendance_rate=attendance_rate,
        program_completed_lessons=completed_lessons,
        program_completed_rate=program_completed_rate,
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
