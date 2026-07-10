"""API v1 architecture migration guards."""

from pathlib import Path


def test_api_v1_router_registry_includes_role_routers():
    source = Path("backend/modules/router.py").read_text()

    assert 'APIRouter(prefix="/api/v1")' in source
    for router_name in [
        "academic_director_router",
        "head_of_department_router",
        "teacher_router",
        "student_router",
        "parent_router",
        "admin_router",
        "ceo_router",
        "hr_manager_router",
        "customer_support_router",
    ]:
        assert f"router.include_router({router_name})" in source


def test_module_api_adapters_are_not_page_rendering_layers():
    api_paths = list(Path("backend/modules").rglob("api.py")) + list(
        Path("backend/modules").rglob("*_api.py")
    )
    assert api_paths
    for path in api_paths:
        source = path.read_text()
        assert "render_admin_page" not in source
        assert "render_react_page" not in source
        assert "HTMLResponse" not in source


def test_server_registers_api_v1_before_role_pages():
    source = Path("backend/server.py").read_text()
    registry = Path("backend/modules/registry.py").read_text()

    assert "from backend.modules.router import router as api_v1_router" in source
    assert "from backend.modules.registry import register_module_pages" in source
    assert "from backend.modules.academics.director_page import register_academic_director_page_routes" in registry
    assert "from backend.modules.academics.hod_page import register_head_of_department_page_routes" in registry
    assert "from backend.modules.teachers.page import register_teacher_page_routes" in registry
    assert "from backend.modules.students.page import register_student_page_routes" in registry
    assert "from backend.modules.parents.page import register_parent_invite_routes, register_parent_page_routes" in registry
    assert "from backend.roles.academic_director.routes" not in source
    assert "from backend.roles.head_of_department.routes" not in source
    assert "from backend.roles.teacher.routes" not in source
    assert "from backend.roles.student.routes" not in source
    assert "from backend.roles.parent.routes" not in source
    assert "app_instance.include_router(api_v1_router)" in source
    assert source.index("app_instance.include_router(api_v1_router)") < source.index(
        "register_module_pages(app_instance)"
    )


def test_student_and_parent_page_routes_live_in_their_modules():
    for path in [
        Path("backend/modules/students/page.py"),
        Path("backend/modules/students/dashboard_page.py"),
        Path("backend/modules/students/forms.py"),
        Path("backend/modules/students/resources_page.py"),
        Path("backend/modules/students/chat_page.py"),
        Path("backend/modules/students/office_hours_page.py"),
        Path("backend/modules/students/rating_page.py"),
        Path("backend/modules/parents/page.py"),
    ]:
        assert path.exists(), f"Expected page route module to exist: {path}"
        source = path.read_text()
        assert "response_model=ApiSuccess" not in source
        assert "from database import queries" not in source


def test_scattered_technical_and_role_layers_are_removed():
    for path in [
        Path("backend/api"),
        Path("backend/pages"),
        Path("backend/roles"),
        Path("backend/domains"),
        Path("backend/identity"),
        Path("backend/routes"),
        Path("backend/utils"),
        Path("backend/security"),
    ]:
        assert not path.exists(), f"Ownership must live under backend/modules or backend/core: {path}"


def test_http_pages_and_workspaces_do_not_own_sql():
    candidates = []
    for path in Path("backend/modules").rglob("*.py"):
        name = path.name
        if name in {"api.py", "page.py", "workspace.py", "cards.py"} or any(
            marker in name for marker in ("_api.py", "_page.py", "_forms.py")
        ):
            candidates.append(path)

    assert candidates
    for path in candidates:
        source = path.read_text()
        assert "conn.execute" not in source, f"HTTP/workspace SQL belongs in a repository: {path}"
        assert "FROM msi_v2" not in source, f"HTTP/workspace SQL belongs in a repository: {path}"
        assert "INSERT INTO msi_v2" not in source, f"HTTP/workspace SQL belongs in a repository: {path}"


def test_services_do_not_call_other_role_http_adapters():
    for path in Path("backend/modules").rglob("*service.py"):
        source = path.read_text()
        assert "_api import" not in source
        assert ".page import" not in source
        assert ".workspace import" not in source


def test_academic_role_adapters_are_owned_by_academic_modules():
    for path in [
        Path("backend/modules/academics/director_page.py"),
        Path("backend/modules/academics/director_router.py"),
        Path("backend/modules/academics/hod_page.py"),
        Path("backend/modules/academics/hod_router.py"),
    ]:
        assert path.is_file()


def test_teacher_http_and_domain_ownership_is_one_module():
    teacher_module = Path("backend/modules/teachers")
    assert teacher_module.is_dir()
    for file_name in ["api.py", "page.py", "schemas.py", "service.py", "repository.py", "workspace.py", "cards.py"]:
        assert (teacher_module / file_name).is_file()
    assert not Path("backend/api/v1/teacher").exists()
    assert not Path("backend/pages/teacher.py").exists()
    assert not Path("backend/roles/teacher").exists()
    assert not Path("backend/domains/teachers").exists()


def test_academic_director_and_hod_role_routes_are_page_only_for_migrated_actions():
    for path in [
        Path("backend/modules/academics/director_page.py"),
        Path("backend/modules/academics/hod_page.py"),
    ]:
        source = path.read_text()
        assert "@router.post" not in source
        assert "/academic-director/api/" not in source
        assert "/head-of-department/api/" not in source
        assert "teacher_academy_actions" not in source


def test_teacher_academy_v1_routes_use_native_fastapi_contracts():
    schemas_source = Path("backend/modules/teacher_academy/schemas.py").read_text()
    responses_source = Path("backend/modules/teacher_academy/http_responses.py").read_text()

    for path in [
        Path("backend/modules/teacher_academy/director_api.py"),
        Path("backend/modules/teacher_academy/hod_api.py"),
    ]:
        source = path.read_text()
        assert "response_model=ApiSuccess[" in source
        assert "backend.core.request_context" not in source
        assert "jsonify" not in source
        assert "from backend.core.guards" not in source

    assert "BaseModel" in schemas_source
    assert "api_success" in responses_source
    for source in (schemas_source, responses_source):
        assert "backend.core.request_context" not in source
        assert "jsonify" not in source


def test_teacher_academy_domain_permissions_do_not_import_legacy_session_context():
    source = Path("backend/modules/teacher_academy/permissions.py").read_text()

    assert "backend.core.request_context" not in source
    assert "backend.core.session" not in source
    assert "from backend.utils" not in source


def test_teacher_academy_responses_do_not_export_raw_domain_services():
    import backend.modules.teacher_academy.http_responses as responses

    raw_service_exports = {
        "add_assessment",
        "create_academy_teacher",
        "delete_academy_teacher",
        "delete_assessment",
        "list_academy_teachers",
        "list_teachers",
        "promote_academy_teacher",
        "sync_academy_lessons",
        "update_academy_status",
        "update_assignment",
    }

    assert raw_service_exports.isdisjoint(set(responses.__all__))


def test_hod_teacher_academy_api_passes_current_user_to_scope_checks():
    source = Path("backend/modules/teacher_academy/hod_api.py").read_text()

    assert "user: CurrentUser = Depends(get_current_user)" in source
    assert "can_user_manage_academy_assignment(user, assignment_id)" in source
    assert "can_user_manage_academy_teacher(user, academy_teacher_id)" in source
    assert "scope_user=user" in source


def test_frontend_teacher_academy_api_helpers_use_api_v1_namespace():
    source = Path("frontend/src/shared/api/routes.ts").read_text()

    assert "/api/v1/academic-director/teacher-academy" in source
    assert "/api/v1/head-of-department/teacher-academy" in source
    assert "academicDirectorTeacherAcademyAssessmentDelete" in source
    assert "headOfDepartmentTeacherAcademyAssessmentDelete" in source
    assert "/academic-director/api" not in source
    assert "/head-of-department/api" not in source


def test_teacher_academy_routes_live_in_role_specific_modules():
    academic_director_router = Path("backend/modules/academics/director_router.py").read_text()
    hod_router = Path("backend/modules/academics/hod_router.py").read_text()
    academic_director_academy = Path("backend/modules/teacher_academy/director_api.py").read_text()
    hod_academy = Path("backend/modules/teacher_academy/hod_api.py").read_text()

    assert "from backend.modules.teacher_academy.director_api import register_teacher_academy_routes" in academic_director_router
    assert "from backend.modules.teacher_academy.hod_api import register_teacher_academy_routes" in hod_router
    assert "register_teacher_academy_routes(router)" in academic_director_router
    assert "register_teacher_academy_routes(router)" in hod_router
    assert "api_v1_academic_director_create_academy_teacher" in academic_director_academy
    assert "api_v1_head_of_department_update_academy_assignment" in hod_academy


def test_no_ad_or_hod_frontend_posts_to_legacy_admin_teacher_academy():
    for path in Path("frontend/src").rglob("*.ts*"):
        source = path.read_text()
        assert "/admin/teacher-academy" not in source
        assert "admin/teacher-academy" not in source
