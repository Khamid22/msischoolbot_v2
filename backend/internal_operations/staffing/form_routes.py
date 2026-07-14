from fastapi.responses import JSONResponse
from backend.core.web.responses import with_status
from backend.core.web.request_context import request

from backend.modules.people.teachers.service import (
    delete_teacher_by_id,
    get_teacher_by_id,
    list_teachers,
    update_teacher_by_id,
    upsert_teacher,
)
from backend.modules.organization.canonical import normalize_school_code
from backend.modules.academics.groups.service import group_belongs_to_school
from backend.internal_operations.pages.context import invalidate_admin_page_context_cache


def _wants_json():
    requested_with = str(request.headers.get("X-Requested-With", "")).strip()
    return requested_with == "XMLHttpRequest"


def _resolve_teacher_fields(mode):
    """Parse and validate the common teacher form fields.

    Returns (full_name, pay_rate, assigned_group, assigned_school, progression, error_message).
    error_message is a non-empty string when validation fails.
    """
    assigned_group = request.form.get("teacher_assigned_group", "").strip()
    assigned_school = normalize_school_code(
        request.form.get("teacher_assigned_school", ""),
        default="",
    )

    if not assigned_group:
        return None, None, None, None, None, "Please select a group for teacher assignment."

    progression = {
        "category": request.form.get("teacher_category", "junior"),
        "semester_stage": request.form.get("teacher_semester_stage", "1-2"),
        "performance_score": request.form.get("teacher_performance_score", "7"),
        "supervised_lessons": request.form.get("teacher_supervised_lessons", "0"),
        "igcse_evidence": request.form.get("teacher_igcse_evidence", ""),
        "promotion_notes": request.form.get("teacher_promotion_notes", ""),
    }

    if mode == "add":
        full_name = request.form.get("teacher_full_name", "").strip()
        pay_rate = request.form.get("teacher_pay_rate", "").strip()
    else:
        selected_name = request.form.get("teacher_selected_name", "").strip()
        teacher_rows = list_teachers()
        matched = next(
            (
                row
                for row in teacher_rows
                if str(row.get("full_name", "")).strip().casefold()
                == selected_name.casefold()
            ),
            None,
        )
        if not matched:
            return None, None, None, None, None, "Please select an existing teacher."
        full_name = str(matched.get("full_name", "")).strip()
        pay_rate = float(matched.get("pay_rate", 0))
        progression = {
            "category": matched.get("category", "junior"),
            "semester_stage": matched.get("semester_stage", "1-2"),
            "performance_score": matched.get("performance_score", 7),
            "supervised_lessons": matched.get("supervised_lessons", 0),
            "igcse_evidence": matched.get("igcse_evidence", ""),
            "promotion_notes": matched.get("promotion_notes", ""),
        }

    return full_name, pay_rate, assigned_group, assigned_school, progression, ""


def register_admin_teacher_routes(
    router,
    *,
    render_admin_page,
):
    def _teacher_error(message, *, teacher_edit=None, status=400):
        if _wants_json():
            return JSONResponse({"ok": False, "message": message}, status_code=status)
        return with_status(render_admin_page(
                auth_error=message,
                admin_panel="teachers",
                admin_teacher_edit=teacher_edit,
            ), status)

    def _teacher_success(message):
        invalidate_admin_page_context_cache()
        if _wants_json():
            return JSONResponse(
                {"ok": True, "message": message, "teachers": list_teachers()}
            )
        return render_admin_page(admin_notice=message, admin_panel="teachers")

    @router.post("/admin/teachers")
    def create_teacher():
        mode = str(request.form.get("teacher_mode", "select")).strip().lower()

        full_name, pay_rate, assigned_group, assigned_school, progression, err = _resolve_teacher_fields(
            mode
        )
        if err:
            return _teacher_error(err)

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                return _teacher_error(
                    "Selected group does not belong to the selected school."
                )

        created = upsert_teacher(
            full_name=full_name,
            pay_rate=pay_rate,
            assigned_group=assigned_group,
            **progression,
        )
        if not created:
            return _teacher_error(
                "Unable to save teacher. Check full name, pay rate, and group."
            )

        return _teacher_success("Teacher saved.")

    @router.post("/admin/teachers/{teacher_id}")
    def update_teacher(teacher_id: int):
        mode = str(request.form.get("teacher_mode", "select")).strip().lower()
        teacher_edit = get_teacher_by_id(teacher_id)

        full_name, pay_rate, assigned_group, assigned_school, progression, err = _resolve_teacher_fields(
            mode
        )
        if err:
            return _teacher_error(err, teacher_edit=teacher_edit)

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                return _teacher_error(
                    "Selected group does not belong to the selected school.",
                    teacher_edit=teacher_edit,
                )

        updated, update_error = update_teacher_by_id(
            teacher_id=teacher_id,
            full_name=full_name,
            pay_rate=pay_rate,
            assigned_group=assigned_group,
            **progression,
        )
        if not updated:
            return _teacher_error(
                update_error or "Unable to update teacher.",
                teacher_edit=get_teacher_by_id(teacher_id),
            )

        return _teacher_success("Teacher updated.")

    @router.post("/admin/teachers/{teacher_id}/delete")
    def delete_teacher(teacher_id: int):
        deleted = delete_teacher_by_id(teacher_id)
        if not deleted:
            return _teacher_error("Unable to delete teacher.")

        return _teacher_success("Teacher deleted.")
