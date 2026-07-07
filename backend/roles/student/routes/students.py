import os
import threading
import time

from backend.utils.response_helpers import redirect, with_status
from backend.utils.context import request, session
from backend.utils.session import url_for
from backend.domains.students.service import change_student_password
from backend.domains.academics.rating_service import (
    get_group_cache_entry,
    is_full_form,
)
from backend.utils.session import (
    build_dashboard_url,
    current_auth_role,
    current_student_db_id,
    current_student_enrollment_id,
    current_student_school_code,
)


def register_student_routes(students, *, render_student_panel):
    metadata_cache_lock = threading.Lock()
    metadata_cache = {}

    raw_metadata_ttl = str(os.environ.get("STUDENT_METADATA_CACHE_SECONDS", "30") or "").strip()
    try:
        metadata_cache_ttl_seconds = max(int(raw_metadata_ttl), 0)
    except ValueError:
        metadata_cache_ttl_seconds = 30

    def _require_student_role():
        """These actions are student-only; other roles bounce to the portal home."""
        if current_auth_role() == "student":
            return None
        return redirect(url_for("student.home"))

    @students.get("/student")
    def student_home_entry():
        denied = _require_student_role()
        if denied is not None:
            return denied

        enrollment_id = current_student_enrollment_id()
        if enrollment_id is not None:
            return redirect(build_dashboard_url(enrollment_id))
        return render_student_panel(form_data={})

    @students.post("/profile/password")
    def profile_change_password():
        denied = _require_student_role()
        if denied is not None:
            return denied

        student_db_id = current_student_db_id()
        enrollment_id = current_student_enrollment_id()
        if student_db_id is None:
            session.clear()
            return redirect(url_for("student.home"))

        subject = request.form.get("subject", "").strip()
        group = request.form.get("group", "").strip()

        current_password_value = str(request.form.get("current_password", ""))
        new_password_value = str(request.form.get("new_password", ""))
        confirm_password_value = str(request.form.get("confirm_password", ""))
        csrf_token_value = str(request.form.get("csrf_token", ""))

        # Validate CSRF manually
        expected_csrf = session.get("csrf_token", "")
        if not expected_csrf or csrf_token_value != expected_csrf:
            profile_error = "Form security token is missing or invalid. Please refresh and try again."
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

        if not current_password_value or not new_password_value or not confirm_password_value:
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
        denied = _require_student_role()
        if denied is not None:
            return denied

        form_data = {
            "student_id": request.form.get("student_id", "").strip(),
            "group": request.form.get("group", "").strip(),
            "subject": request.form.get("subject", "").strip(),
        }

        if not is_full_form(form_data):
            return with_status(render_student_panel(
                form_data=form_data,
                panel_error="Please fill all fields.",
            ), 400)

        try:
            requested_student_id = int(form_data["student_id"])
        except ValueError:
            return with_status(render_student_panel(
                form_data=form_data,
                panel_error="Please choose a valid student from the list.",
            ), 400)

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
            return with_status(render_student_panel(
                form_data=form_data,
                panel_error=cache_error or "Unable to load internal academic data.",
            ), 503)

        return with_status(render_student_panel(
            form_data=form_data,
            panel_error="Student not found. Please check your details.",
        ), 404)
