from backend.utils.response_helpers import jsonify, redirect
from backend.utils.context import request
from backend.utils.session import url_for

from backend.roles.admin.routes.request_payload import request_payload
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.roles.admin.services.academic_service import (
    create_group_from_payload,
    create_schedule_from_payload,
    create_school_from_payload,
    get_group_gradebook,
    list_admin_academic_context,
    record_attendance_from_payload,
    record_coin_from_payload,
    record_exam_from_payload,
    record_homework_from_payload,
    move_enrollment_group_from_payload,
    update_enrollment_status_from_payload,
)


def register_academic_admin_routes(
    admin_blueprint,
    *,
    render_admin_page,
):
    @admin_blueprint.post("/admin/academic/subjects")
    def admin_create_academic_subject():
        return render_admin_page(
            admin_notice="Subjects can only be added through a full scheme of work program import.",
            admin_panel="subjects",
        )

    @admin_blueprint.post("/admin/academic/schools")
    def admin_create_academic_school():
        try:
            create_school_from_payload(request.form)
        except (TypeError, ValueError) as exc:
            return render_admin_page(admin_notice=str(exc), admin_panel="groups")
        invalidate_admin_page_context_cache()
        return redirect(url_for("student.home", panel="groups"))

    @admin_blueprint.post("/admin/academic/groups")
    def admin_create_academic_group():
        try:
            result = create_group_from_payload(request.form)
        except (TypeError, ValueError) as exc:
            return render_admin_page(admin_notice=str(exc), admin_panel="groups")
        invalidate_admin_page_context_cache()
        return redirect(url_for("student.home", panel="groups", school=result["school_code"]))

    @admin_blueprint.post("/admin/api/academic/schedules")
    def admin_create_academic_schedule():
        try:
            result = create_schedule_from_payload(request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        invalidate_admin_page_context_cache()
        academic_context = list_admin_academic_context()
        return jsonify(
            {
                "ok": True,
                "schedule": result,
                "schedules": academic_context.get("schedules", []),
                "sessions": academic_context.get("sessions", []),
                "lessons": academic_context.get("lessons", []),
            }
        )

    @admin_blueprint.get("/admin/api/academic/gradebook")
    def admin_academic_gradebook():
        try:
            gradebook = get_group_gradebook(request.args.get("group_id", 0))
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        if not gradebook:
            return jsonify({"ok": False, "message": "Group not found"}, status_code=404)
        return jsonify(gradebook)

    @admin_blueprint.patch("/admin/api/academic/enrollments/{enrollment_id}/status")
    def admin_update_academic_enrollment_status(enrollment_id: int):
        try:
            result = update_enrollment_status_from_payload(enrollment_id, request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "enrollment": result})

    @admin_blueprint.patch("/admin/api/academic/enrollments/{enrollment_id}/group")
    def admin_move_academic_enrollment_group(enrollment_id: int):
        try:
            result = move_enrollment_group_from_payload(enrollment_id, request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        invalidate_admin_page_context_cache()
        academic_context = list_admin_academic_context()
        return jsonify(
            {
                "ok": True,
                "enrollment": result,
                "groups": academic_context.get("groups", []),
            }
        )

    @admin_blueprint.post("/admin/api/academic/attendance")
    def admin_record_academic_attendance():
        try:
            record_id = record_attendance_from_payload(request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        return jsonify({"ok": True, "id": record_id})

    @admin_blueprint.post("/admin/api/academic/homework")
    def admin_record_academic_homework():
        try:
            record_id = record_homework_from_payload(request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        return jsonify({"ok": True, "id": record_id})

    @admin_blueprint.post("/admin/api/academic/exams")
    def admin_record_academic_exam():
        try:
            record_id = record_exam_from_payload(request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        return jsonify({"ok": True, "id": record_id})

    @admin_blueprint.post("/admin/api/academic/coins")
    def admin_record_academic_coins():
        try:
            record_id = record_coin_from_payload(request_payload())
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        return jsonify({"ok": True, "id": record_id})
