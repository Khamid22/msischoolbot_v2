from web.backend.routes.admin.resource_routes import register_admin_resource_routes
from web.backend.routes.admin.student_routes import register_admin_student_routes
from web.backend.routes.admin.teacher_routes import register_admin_teacher_routes


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
    register_admin_resource_routes(
        router,
        render_admin_page=render_admin_page,
    )
