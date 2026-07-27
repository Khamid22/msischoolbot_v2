import os
import threading
import time

from backend.core.web.responses import redirect, with_status
from backend.core.web.request_context import request, session
from backend.modules.people.student.contracts import (
    build_dashboard_url,
    current_auth_role,
    current_student_enrollment_id,
    current_student_school_code,
    get_group_cache_entry,
    is_full_form,
    url_for,
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
