from backend.modules.people.academic_director.workspace.page import (
    register_academic_director_page_routes,
    register_academic_director_recruitment_page_routes,
)
from backend.modules.people.head_of_department.workspace.page import (
    register_head_of_department_page_routes,
    register_head_of_department_recruitment_page_routes,
)
from backend.modules.people.hr_manager.workspace.page import register_hr_manager_page_routes
from backend.modules.people.parent.workspace.page import (
    register_parent_invite_routes,
    register_parent_page_routes,
)
from backend.modules.domains.identity.page import register_portal_routes
from backend.modules.people.ceo.workspace.page import (
    register_ceo_page_routes,
    register_ceo_recruitment_page_routes,
)
from backend.modules.people.customer_support.workspace.page import register_customer_support_page_routes
from backend.modules.people.student.workspace.page import register_student_page_routes
from backend.modules.people.teacher.workspace.page import register_teacher_page_routes
from backend.application.module_spec import WorkspaceSpec


WORKSPACES = (
    WorkspaceSpec("identity", register_portal_routes),
    WorkspaceSpec("student", register_student_page_routes),
    WorkspaceSpec("parent", register_parent_page_routes),
    WorkspaceSpec("ceo", register_ceo_page_routes),
    WorkspaceSpec("customer_support", register_customer_support_page_routes),
    WorkspaceSpec("teacher", register_teacher_page_routes),
    WorkspaceSpec("academic_director", register_academic_director_page_routes),
    WorkspaceSpec("head_of_department", register_head_of_department_page_routes),
    WorkspaceSpec("hr_manager_recruitment", register_hr_manager_page_routes),
    WorkspaceSpec("ceo_recruitment", register_ceo_recruitment_page_routes),
    WorkspaceSpec(
        "academic_director_recruitment",
        register_academic_director_recruitment_page_routes,
    ),
    WorkspaceSpec(
        "head_of_department_recruitment",
        register_head_of_department_recruitment_page_routes,
    ),
    WorkspaceSpec("parent_invite", register_parent_invite_routes),
)


def register_application_pages(app) -> None:
    """Register page adapters without introducing role-to-role dependencies."""

    for workspace in WORKSPACES:
        workspace.register_pages(app)


__all__ = ["WORKSPACES", "register_application_pages"]
