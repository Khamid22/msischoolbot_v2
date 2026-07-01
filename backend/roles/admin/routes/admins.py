from backend.roles.admin.routes.complaint_routes import register_admin_complaint_routes
from backend.roles.admin.routes.resource_routes import register_admin_resource_routes
from backend.roles.admin.routes.parent_routes import register_admin_parent_routes
from backend.roles.admin.routes.payment_routes import register_admin_payment_routes
from backend.roles.admin.routes.student_routes import register_admin_student_routes
from backend.roles.admin.routes.teacher_routes import register_admin_teacher_routes


def register_admin_routes(
    router,
    *,
    render_admin_page,
    render_edit_student_page,
    delete_uploaded_student_photo,
):
    register_admin_student_routes(
        router,
        render_admin_page=render_admin_page,
        render_edit_student_page=render_edit_student_page,
        delete_uploaded_student_photo=delete_uploaded_student_photo,
    )
    register_admin_teacher_routes(
        router,
        render_admin_page=render_admin_page,
    )
    register_admin_parent_routes(router)
    register_admin_payment_routes(router)
    register_admin_complaint_routes(router)
    register_admin_resource_routes(
        router,
        render_admin_page=render_admin_page,
    )
