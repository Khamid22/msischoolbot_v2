from flask import request

from app.routes.admin.services.auth_service import (
    delete_teacher_by_id,
    get_teacher_by_id,
    list_teachers,
    update_teacher_by_id,
    upsert_teacher,
)
from app.routes.admin.services.normalization_service import normalize_school_code
from app.routes.admin.services.route_service import group_belongs_to_school


def register_admin_teacher_routes(
    router,
    *,
    render_admin_page,
    load_dataset,
):
    @router.post("/admin/teachers/add")
    def add_teacher():
        edit_teacher_id_raw = request.form.get("teacher_edit_id", "").strip()
        edit_teacher_id = 0
        if edit_teacher_id_raw:
            try:
                edit_teacher_id = int(edit_teacher_id_raw)
            except ValueError:
                edit_teacher_id = 0

        mode = str(request.form.get("teacher_mode", "select")).strip().lower()
        assigned_group = request.form.get("teacher_assigned_group", "").strip()
        assigned_school = normalize_school_code(
            request.form.get("teacher_assigned_school", "")
        )
        if not assigned_group:
            selected_teacher_edit = (
                get_teacher_by_id(edit_teacher_id) if edit_teacher_id > 0 else None
            )
            return (
                render_admin_page(
                    auth_error="Please select a group for teacher assignment.",
                    admin_panel="teachers",
                    admin_teacher_edit=selected_teacher_edit,
                ),
                400,
            )
        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school, load_dataset):
                selected_teacher_edit = (
                    get_teacher_by_id(edit_teacher_id) if edit_teacher_id > 0 else None
                )
                return (
                    render_admin_page(
                        auth_error="Selected group does not belong to the selected school.",
                        admin_panel="teachers",
                        admin_teacher_edit=selected_teacher_edit,
                    ),
                    400,
                )

        if mode == "add":
            candidate_full_name = request.form.get("teacher_full_name", "").strip()
            candidate_pay_rate = request.form.get("teacher_pay_rate", "").strip()
        else:
            selected_teacher_name = request.form.get("teacher_selected_name", "").strip()
            teacher_rows = list_teachers()
            selected_teacher = next(
                (
                    row
                    for row in teacher_rows
                    if str(row.get("full_name", "")).strip().casefold()
                    == selected_teacher_name.casefold()
                ),
                None,
            )
            if not selected_teacher:
                selected_teacher_edit = (
                    get_teacher_by_id(edit_teacher_id) if edit_teacher_id > 0 else None
                )
                return (
                    render_admin_page(
                        auth_error="Please select an existing teacher.",
                        admin_panel="teachers",
                        admin_teacher_edit=selected_teacher_edit,
                    ),
                    400,
                )
            candidate_full_name = str(selected_teacher.get("full_name", "")).strip()
            candidate_pay_rate = float(selected_teacher.get("pay_rate", 0))

        if edit_teacher_id > 0:
            created, update_error = update_teacher_by_id(
                teacher_id=edit_teacher_id,
                full_name=candidate_full_name,
                pay_rate=candidate_pay_rate,
                assigned_group=assigned_group,
            )
            if not created:
                selected_teacher_edit = get_teacher_by_id(edit_teacher_id)
                return (
                    render_admin_page(
                        auth_error=update_error or "Unable to update teacher.",
                        admin_panel="teachers",
                        admin_teacher_edit=selected_teacher_edit,
                    ),
                    400,
                )
        else:
            created = upsert_teacher(
                full_name=candidate_full_name,
                pay_rate=candidate_pay_rate,
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
            admin_notice="Teacher changes saved.",
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
