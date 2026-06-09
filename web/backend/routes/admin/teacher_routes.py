from flask import request

from web.backend.routes.admin.services.auth_service import (
    delete_teacher_by_id,
    get_teacher_by_id,
    list_teachers,
    update_teacher_by_id,
    upsert_teacher,
)
from web.backend.routes.admin.services.normalization_service import normalize_school_code
from web.backend.routes.admin.services.route_service import group_belongs_to_school


def _resolve_teacher_fields(mode, render_admin_page, teacher_edit=None):
    """Parse and validate the common teacher form fields.

    Returns (full_name, pay_rate, assigned_group, assigned_school, error_response).
    error_response is non-None when validation fails.
    """
    assigned_group = request.form.get("teacher_assigned_group", "").strip()
    assigned_school = normalize_school_code(
        request.form.get("teacher_assigned_school", "")
    )

    if not assigned_group:
        return None, None, None, None, (
            render_admin_page(
                auth_error="Please select a group for teacher assignment.",
                admin_panel="teachers",
                admin_teacher_edit=teacher_edit,
            ),
            400,
        )

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
            return None, None, None, None, (
                render_admin_page(
                    auth_error="Please select an existing teacher.",
                    admin_panel="teachers",
                    admin_teacher_edit=teacher_edit,
                ),
                400,
            )
        full_name = str(matched.get("full_name", "")).strip()
        pay_rate = float(matched.get("pay_rate", 0))

    return full_name, pay_rate, assigned_group, assigned_school, None


def register_admin_teacher_routes(
    router,
    *,
    render_admin_page,
):
    @router.post("/admin/teachers")
    def create_teacher():
        mode = str(request.form.get("teacher_mode", "select")).strip().lower()

        full_name, pay_rate, assigned_group, assigned_school, err = _resolve_teacher_fields(
            mode, render_admin_page
        )
        if err:
            return err

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                return (
                    render_admin_page(
                        auth_error="Selected group does not belong to the selected school.",
                        admin_panel="teachers",
                    ),
                    400,
                )

        created = upsert_teacher(
            full_name=full_name,
            pay_rate=pay_rate,
            assigned_group=assigned_group,
        )
        if not created:
            return (
                render_admin_page(
                    auth_error="Unable to save teacher. Check full name, pay rate, and group.",
                    admin_panel="teachers",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Teacher saved.",
            admin_panel="teachers",
        )

    @router.post("/admin/teachers/<int:teacher_id>")
    def update_teacher(teacher_id):
        mode = str(request.form.get("teacher_mode", "select")).strip().lower()
        teacher_edit = get_teacher_by_id(teacher_id)

        full_name, pay_rate, assigned_group, assigned_school, err = _resolve_teacher_fields(
            mode, render_admin_page, teacher_edit=teacher_edit
        )
        if err:
            return err

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                return (
                    render_admin_page(
                        auth_error="Selected group does not belong to the selected school.",
                        admin_panel="teachers",
                        admin_teacher_edit=teacher_edit,
                    ),
                    400,
                )

        updated, update_error = update_teacher_by_id(
            teacher_id=teacher_id,
            full_name=full_name,
            pay_rate=pay_rate,
            assigned_group=assigned_group,
        )
        if not updated:
            return (
                render_admin_page(
                    auth_error=update_error or "Unable to update teacher.",
                    admin_panel="teachers",
                    admin_teacher_edit=get_teacher_by_id(teacher_id),
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Teacher updated.",
            admin_panel="teachers",
        )

    @router.post("/admin/teachers/<int:teacher_id>/delete")
    def delete_teacher(teacher_id):
        deleted = delete_teacher_by_id(teacher_id)
        if not deleted:
            return (
                render_admin_page(
                    auth_error="Unable to delete teacher.",
                    admin_panel="teachers",
                ),
                400,
            )

        return render_admin_page(
            admin_notice="Teacher deleted.",
            admin_panel="teachers",
        )
