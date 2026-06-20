import os
import threading
import time

from flask import jsonify, redirect, request, session, url_for

from web.backend.auth.forms import StudentPasswordChangeForm
from shared.identity.account_service import change_student_password
from web.backend.utils.session import (
    build_dashboard_url,
    current_auth_role,
    current_student_db_id,
    current_student_enrollment_id,
    current_student_school_code,
)


def register_student_routes(
    students,
    *,
    load_dataset,
    is_full_form,
    render_student_panel,
    get_group_cache_entry,
    build_students_by_subject_group,
    search_student,
):
    metadata_cache_lock = threading.Lock()
    metadata_cache = {}

    raw_metadata_ttl = str(os.environ.get("STUDENT_METADATA_CACHE_SECONDS", "30") or "").strip()
    try:
        metadata_cache_ttl_seconds = max(int(raw_metadata_ttl), 0)
    except ValueError:
        metadata_cache_ttl_seconds = 30

    def _metadata_cache_key(dataset, school_code):
        return (int(id(dataset)), str(school_code or "").strip().casefold())

    def _get_cached_metadata(cache_key):
        now = time.time()
        with metadata_cache_lock:
            cached_entry = metadata_cache.get(cache_key)
            if cached_entry and now < float(cached_entry.get("expires_at", 0)):
                return cached_entry.get("payload")
        return None

    def _set_cached_metadata(cache_key, payload):
        if metadata_cache_ttl_seconds <= 0:
            return

        now = time.time()
        with metadata_cache_lock:
            metadata_cache[cache_key] = {
                "payload": payload,
                "expires_at": now + metadata_cache_ttl_seconds,
            }
            expired_keys = [
                key
                for key, entry in metadata_cache.items()
                if float(entry.get("expires_at", 0)) <= now
            ]
            for key in expired_keys:
                metadata_cache.pop(key, None)
            if len(metadata_cache) > 64:
                ordered_entries = sorted(
                    metadata_cache.items(),
                    key=lambda item: float(item[1].get("expires_at", 0)),
                )
                for key, _entry in ordered_entries[: len(metadata_cache) - 64]:
                    metadata_cache.pop(key, None)

    student_only_endpoints = {
        "student.profile_change_password",
        "student.search_student_form",
    }

    @students.before_request
    def ensure_student_role_for_student_actions():
        endpoint = str(request.endpoint or "").strip()
        if endpoint not in student_only_endpoints:
            return None
        if current_auth_role() == "student":
            return None
        return redirect(url_for("student.home"))

    @students.post("/profile/password")
    def profile_change_password():
        password_form = StudentPasswordChangeForm()
        student_db_id = current_student_db_id()
        enrollment_id = current_student_enrollment_id()
        if student_db_id is None:
            session.clear()
            return redirect(url_for("student.home"))

        subject = request.form.get("subject", "").strip()
        group = request.form.get("group", "").strip()

        if not password_form.validate_on_submit():
            if password_form.csrf_token.errors:
                profile_error = (
                    "Form security token is missing or invalid. Please refresh and try again."
                )
            else:
                profile_error = "Please fill all password fields."
            if enrollment_id:
                return redirect(
                    build_dashboard_url(
                        enrollment_id,
                        subject=subject,
                        group=group,
                        profile_error=profile_error,
                    )
                )
            return redirect(url_for("student.home"))

        current_password_value = str(password_form.current_password.data or "")
        new_password_value = str(password_form.new_password.data or "")
        confirm_password_value = str(password_form.confirm_password.data or "")

        if new_password_value != confirm_password_value:
            if enrollment_id:
                return redirect(
                    build_dashboard_url(
                        enrollment_id,
                        subject=subject,
                        group=group,
                        profile_error="New password and confirmation do not match.",
                    )
                )
            return redirect(url_for("student.home"))

        updated, update_error = change_student_password(
            student_db_id,
            current_password=current_password_value,
            new_password=new_password_value,
        )
        if not updated:
            if enrollment_id:
                return redirect(
                    build_dashboard_url(
                        enrollment_id,
                        subject=subject,
                        group=group,
                        profile_error=update_error or "Unable to change password.",
                    )
                )
            return redirect(url_for("student.home"))

        if enrollment_id:
            return redirect(
                build_dashboard_url(
                    enrollment_id,
                    subject=subject,
                    group=group,
                    profile_notice="Password changed successfully.",
                )
            )
        return redirect(url_for("student.home"))

    @students.post("/search")
    def search_student_form():
        form_data = {
            "student_id": request.form.get("student_id", "").strip(),
            "group": request.form.get("group", "").strip(),
            "subject": request.form.get("subject", "").strip(),
        }

        if not is_full_form(form_data):
            return render_student_panel(
                form_data=form_data,
                panel_error="Please fill all fields.",
            ), 400

        try:
            requested_student_id = int(form_data["student_id"])
        except ValueError:
            return render_student_panel(
                form_data=form_data,
                panel_error="Please choose a valid student from the list.",
            ), 400

        school_code = current_student_school_code()
        group_cache_entry, cache_error = get_group_cache_entry(
            form_data["subject"],
            form_data["group"],
            school_code=school_code,
        )
        if group_cache_entry and requested_student_id in group_cache_entry.get(
            "dashboards_by_id", {}
        ):
            route_params = {
                "student_id": requested_student_id,
                "subject": form_data["subject"],
                "group": form_data["group"],
            }
            if school_code:
                route_params["school"] = school_code
            return redirect(url_for("student.dashboard", **route_params))

        if cache_error:
            return render_student_panel(
                form_data=form_data,
                panel_error=cache_error or "Unable to load internal academic data.",
            ), 503

        return render_student_panel(
            form_data=form_data,
            panel_error="Student not found. Please check your details.",
        ), 404

    @students.get("/api/metadata")
    def api_metadata():
        school_code = current_student_school_code()
        if school_code:
            dataset, load_error = load_dataset(school_code=school_code)
        else:
            dataset, load_error = load_dataset()
        if load_error or not dataset:
            return jsonify(
                {"message": load_error or "Unable to load internal academic data."}
            ), 503

        cache_key = _metadata_cache_key(dataset, school_code)
        payload = _get_cached_metadata(cache_key)
        if payload is None:
            payload = {
                "groups": dataset.get("groups", []),
                "groupsBySubject": dataset.get("groups_by_subject", {}),
                "studentsBySubjectGroup": build_students_by_subject_group(
                    dataset.get("students", [])
                ),
                "subjects": dataset.get("subjects", []),
            }
            _set_cached_metadata(cache_key, payload)

        return jsonify(payload)

    @students.get("/api/students/search")
    def api_search_student():
        surname = request.args.get("surname", "").strip()
        name = request.args.get("name", "").strip()
        group = request.args.get("group", "").strip()
        subject = request.args.get("subject", "").strip()

        if not all([surname, name, group, subject]):
            return jsonify({"message": "All fields are required."}), 400

        school_code = current_student_school_code()
        if school_code:
            dataset, load_error = load_dataset(school_code=school_code)
        else:
            dataset, load_error = load_dataset()
        if load_error or not dataset:
            return jsonify(
                {"message": load_error or "Unable to load internal academic data."}
            ), 503

        student = search_student(
            dataset["students"],
            surname=surname,
            name=name,
            group=group,
            subject=subject,
        )
        if not student:
            return jsonify({"message": "Student not found"}), 404

        return jsonify(student)
