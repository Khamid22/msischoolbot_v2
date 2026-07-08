"""API v1 architecture migration guards."""

from pathlib import Path


def test_api_v1_router_registry_includes_role_routers():
    source = Path("backend/api/v1/router.py").read_text()

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


def test_api_v1_is_not_a_page_rendering_layer():
    for path in Path("backend/api/v1").rglob("*.py"):
        source = path.read_text()
        assert "render_admin_page" not in source
        assert "render_react_page" not in source
        assert "HTMLResponse" not in source


def test_server_registers_api_v1_before_role_pages():
    source = Path("backend/server.py").read_text()

    assert "from backend.api.v1.router import router as api_v1_router" in source
    assert "from backend.pages.academic_director import register_academic_director_page_routes" in source
    assert "from backend.pages.head_of_department import register_head_of_department_page_routes" in source
    assert "from backend.pages.teacher import register_teacher_page_routes" in source
    assert "from backend.pages.student import register_student_page_routes" in source
    assert "from backend.pages.parent import register_parent_page_routes" in source
    assert "from backend.pages.parent import register_parent_invite_routes" in source
    assert "from backend.roles.academic_director.routes" not in source
    assert "from backend.roles.head_of_department.routes" not in source
    assert "from backend.roles.teacher.routes" not in source
    assert "from backend.roles.student.routes" not in source
    assert "from backend.roles.parent.routes" not in source
    assert "app_instance.include_router(api_v1_router)" in source
    assert source.index("app_instance.include_router(api_v1_router)") < source.index(
        "register_academic_director_page_routes(app_instance)"
    )


def test_student_and_parent_page_routes_live_in_pages_layer():
    for path in [
        Path("backend/pages/student.py"),
        Path("backend/pages/student_dashboard.py"),
        Path("backend/pages/student_forms.py"),
        Path("backend/pages/student_resources.py"),
        Path("backend/pages/student_chat.py"),
        Path("backend/pages/student_office_hours.py"),
        Path("backend/pages/student_rating_board.py"),
        Path("backend/pages/parent.py"),
    ]:
        assert path.exists(), f"Expected page route module to exist: {path}"
        source = path.read_text()
        assert "response_model=ApiSuccess" not in source
        assert "from database import queries" not in source


def test_student_and_parent_role_route_files_are_compatibility_only():
    wrapper_paths = [
        Path("backend/roles/student/routes/__init__.py"),
        Path("backend/roles/student/routes/student_page.py"),
        Path("backend/roles/student/routes/dashboard.py"),
        Path("backend/roles/student/routes/students.py"),
        Path("backend/roles/student/routes/resources.py"),
        Path("backend/roles/student/routes/chat_page.py"),
        Path("backend/roles/student/routes/office_hours_routes.py"),
        Path("backend/roles/student/routes/rating_board.py"),
        Path("backend/roles/parent/routes.py"),
    ]
    for path in wrapper_paths:
        source = path.read_text()
        assert "backend.pages." in source
        assert "render_react_page" not in source
        assert "HTMLResponse" not in source
        assert "@router." not in source
        assert "@app." not in source
        assert "FROM msi_v2" not in source


def test_ad_hod_and_teacher_role_route_files_are_deleted_after_page_move():
    for path in [
        Path("backend/roles/academic_director/routes.py"),
        Path("backend/roles/head_of_department/routes.py"),
        Path("backend/roles/teacher/routes.py"),
    ]:
        assert not path.exists()

    assert "backend.pages.academic_director" in Path("backend/roles/academic_director/__init__.py").read_text()
    assert "backend.pages.head_of_department" in Path("backend/roles/head_of_department/__init__.py").read_text()
    assert "backend.pages.teacher" in Path("backend/roles/teacher/__init__.py").read_text()


def test_academic_director_and_hod_role_routes_are_page_only_for_migrated_actions():
    for path in [
        Path("backend/pages/academic_director.py"),
        Path("backend/pages/head_of_department.py"),
    ]:
        source = path.read_text()
        assert "@router.post" not in source
        assert "/academic-director/api/" not in source
        assert "/head-of-department/api/" not in source
        assert "teacher_academy_actions" not in source


def test_teacher_academy_v1_routes_use_native_fastapi_contracts():
    schemas_source = Path("backend/api/v1/teacher_academy/schemas.py").read_text()
    responses_source = Path("backend/api/v1/teacher_academy/responses.py").read_text()

    for path in [
        Path("backend/api/v1/academic_director/teacher_academy.py"),
        Path("backend/api/v1/head_of_department/teacher_academy.py"),
    ]:
        source = path.read_text()
        assert "response_model=ApiSuccess[" in source
        assert "backend.utils.context" not in source
        assert "jsonify" not in source
        assert "from backend.utils.guards" not in source

    assert "BaseModel" in schemas_source
    assert "api_success" in responses_source
    for source in (schemas_source, responses_source):
        assert "backend.utils.context" not in source
        assert "jsonify" not in source


def test_teacher_academy_domain_permissions_do_not_import_legacy_session_context():
    source = Path("backend/domains/teacher_academy/permissions.py").read_text()

    assert "backend.utils.context" not in source
    assert "backend.utils.session" not in source
    assert "from backend.utils" not in source


def test_teacher_academy_responses_do_not_export_raw_domain_services():
    import backend.api.v1.teacher_academy.responses as responses

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
    source = Path("backend/api/v1/head_of_department/teacher_academy.py").read_text()

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
    academic_director_router = Path("backend/api/v1/academic_director/router.py").read_text()
    hod_router = Path("backend/api/v1/head_of_department/router.py").read_text()
    academic_director_academy = Path("backend/api/v1/academic_director/teacher_academy.py").read_text()
    hod_academy = Path("backend/api/v1/head_of_department/teacher_academy.py").read_text()

    assert "from backend.api.v1.academic_director.teacher_academy import register_teacher_academy_routes" in academic_director_router
    assert "from backend.api.v1.head_of_department.teacher_academy import register_teacher_academy_routes" in hod_router
    assert "register_teacher_academy_routes(router)" in academic_director_router
    assert "register_teacher_academy_routes(router)" in hod_router
    assert "api_v1_academic_director_create_academy_teacher" in academic_director_academy
    assert "api_v1_head_of_department_update_academy_assignment" in hod_academy


def test_no_ad_or_hod_frontend_posts_to_legacy_admin_teacher_academy():
    for path in Path("frontend/src").rglob("*.ts*"):
        source = path.read_text()
        assert "/admin/teacher-academy" not in source
        assert "admin/teacher-academy" not in source
