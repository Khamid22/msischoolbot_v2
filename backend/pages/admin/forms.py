from backend.pages.resources.admin_forms import register_admin_resource_routes
from backend.pages.students.admin_forms import register_admin_student_routes
from backend.pages.teachers.admin_forms import register_admin_teacher_routes


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
