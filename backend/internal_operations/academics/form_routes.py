from backend.core.web.responses import redirect
from backend.core.web.request_context import request
from backend.modules.identity.session import url_for

from backend.internal_operations.pages.context import invalidate_admin_page_context_cache
from backend.modules.academics.groups.operations import create_group_from_payload
from backend.modules.organization.operations import create_school_from_payload


def register_academic_admin_routes(
    admin_blueprint,
    *,
    render_admin_page,
    clear_group_cache=lambda: None,
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
