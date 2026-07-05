"""Academic Director sidebar/profile/logout UI guards."""

import json
import os
from base64 import b64encode
from pathlib import Path

from itsdangerous import TimestampSigner


def _session_secret():
    return (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )


def _signed_session(data):
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    return TimestampSigner(_session_secret()).sign(encoded).decode("utf-8")


def _set_session(client, data):
    client.cookies.set("session", _signed_session(data))


def _route_methods(app):
    routes = {}

    def walk(route_list):
        for route in route_list:
            if type(route).__name__ == "_IncludedRouter":
                walk(route.original_router.routes)
                continue
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is not None and methods:
                routes.setdefault(path, set()).update(methods)
            nested = getattr(route, "routes", None)
            if nested:
                walk(nested)

    walk(app.routes)
    return routes


def _minimal_admin_page_context():
    return {
        "panel": "teachers",
        "school_filter": "all",
        "sync_errors": [],
        "load_error": "",
        "admin_students": [],
        "admin_teachers": [],
        "admin_teacher_candidates": [],
        "admin_teacher_academy": [],
        "admin_complaints": [],
        "admin_parents": [],
        "admin_parent_children": [],
        "admin_teacher_options": [],
        "admin_group_options": [],
        "admin_teacher_edit": None,
        "admin_teacher_edit_school": "",
        "admin_school_options": [{"code": "all", "label": "All Schools"}],
        "admin_quick_stats": {},
        "admin_school_info": [],
        "admin_subject_info": [],
        "admin_group_zones": {"green": [], "yellow": [], "red": []},
        "admin_resource_types": [],
        "admin_resource_active_types": [],
        "admin_resources": [],
        "adminResourceSubjectOptions": [],
        "admin_resource_subject_options": [],
        "admin_resource_upload_enabled": False,
    }


def _minimal_academic_context():
    return {
        "schools": [],
        "subjects": [],
        "groups": [],
        "enrollments": [],
        "lessons": [],
        "schedules": [],
        "sessions": [],
        "curriculum_programs": [],
        "curriculum_items": [],
        "enrollment_summary": {},
    }


def _patch_academic_director_cards(monkeypatch):
    import backend.roles.academic_director.routes as academic_director_routes

    monkeypatch.setattr(
        academic_director_routes,
        "academic_director_workspace_cards",
        lambda: [
            {"label": "Groups", "value": "8"},
            {"label": "Teachers", "value": "3"},
            {"label": "Subjects", "value": "5"},
            {"label": "Students", "value": "177"},
        ],
    )


def _patch_admin_page_context(monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page
    import backend.roles.academic_director.routes as academic_director_routes

    monkeypatch.setattr(admin_page, "build_admin_page_context", lambda **kwargs: _minimal_admin_page_context())
    monkeypatch.setattr(admin_page, "list_admin_academic_context", _minimal_academic_context)
    monkeypatch.setattr(admin_page, "list_announcements", lambda: [])
    monkeypatch.setattr(admin_page, "system_admin_workspace_cards", lambda: [])
    monkeypatch.setattr(academic_director_routes, "build_admin_page_context", lambda **kwargs: _minimal_admin_page_context())
    monkeypatch.setattr(academic_director_routes, "list_admin_academic_context", _minimal_academic_context)


def test_academic_director_home_bootstrap_keeps_cards_and_profile_context(client, monkeypatch):
    _patch_academic_director_cards(monkeypatch)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.get("/academic-director")

    assert response.status_code == 200
    assert 'data-react-page="academic-director-home"' in response.text
    assert 'data-react-page="admin-home"' not in response.text
    assert "Academic Director Dashboard" in response.text
    assert "AD0001" in response.text
    assert "Student mode" not in response.text
    assert "csrfToken" in response.text
    assert "Groups" in response.text
    assert "Teachers" in response.text
    assert "Subjects" in response.text
    assert "Students" in response.text


def test_academic_director_teacher_academy_route_still_loads(client, monkeypatch):
    _patch_admin_page_context(monkeypatch)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.get("/academic-director/teacher-academy")

    assert response.status_code == 200
    assert 'data-react-page="academic-director-academy"' in response.text
    assert "academic_director" in response.text
    assert "Student mode" not in response.text
    assert 'data-react-page="admin-home"' not in response.text


def test_academic_director_shell_source_contains_sidebar_profile_logout_and_mobile_nav():
    source = Path("frontend/src/roles/common/components/AcademicDirectorShell.tsx").read_text()
    admin_source = Path("frontend/src/roles/admin/pages/Admin.tsx").read_text()
    academy_source = Path("frontend/src/roles/academic_director/pages/TeacherAcademy.tsx").read_text()
    app_source = Path("frontend/src/app/App.tsx").read_text()
    bootstrap_source = Path("frontend/src/shared/lib/bootstrap.ts").read_text()
    stale_state_source = Path("frontend/src/shared/lib/staleUiState.ts").read_text()
    admin_state_source = Path("frontend/src/roles/admin/hooks/useAdminState.ts").read_text()
    deployment_doc = Path("docs/ENGINEERING_DEPLOYMENT.md").read_text()

    assert "Academic Director navigation" in source
    assert "Academic Director mobile navigation" in source
    assert 'label: "Dashboard"' in source
    assert 'label: "Teacher Academy"' in source
    assert 'label: "Profile"' in source
    assert 'label: "Home"' in source
    assert 'label: "Academy"' in source
    assert "Head of Departments" in source
    assert "Open Teacher Academy" in source
    assert "/academic-director/teacher-academy" in source
    assert "academic-director-profile" in source
    assert "action={routes.logout}" in source
    assert 'name="csrf_token"' in source
    assert "AcademicDirectorMobileNav active=\"academy\"" not in admin_source
    assert "AdminSidebar" not in academy_source
    assert "AcademicDirectorSidebar" in academy_source
    assert "AcademicDirectorMobileNav active=\"academy\"" in academy_source
    assert "allowTeacherPreview={false}" in academy_source
    assert "if (!allowTeacherPreview)" in Path(
        "frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx"
    ).read_text()
    assert '"academic-director-academy"' in app_source
    assert '"academic-director-academy"' in bootstrap_source
    assert "clearStaleRolePreviewStorage(" in app_source
    assert "bootstrap.props.authRole || bootstrap.props.role || bootstrap.props.adminMode" in app_source
    for key in [
        "devPreviewRole",
        "msi_admin_mode",
        "msi_teacher_preview_key",
        "msi_teacher_preview_id",
    ]:
        assert key in stale_state_source
    assert "canUseAdminPreviewForRole" in admin_state_source
    assert "clearStaleRolePreviewStorage(realRole)" in admin_state_source
    assert "modeParam && allowPreviewMode" in admin_state_source
    assert "urlAdminMode() || storedAdminMode()" in admin_state_source
    assert "ACCOUNT_AUTH_V2_ENABLED=1" in deployment_doc
    assert "ADMIN_PREVIEW_ROLES=0" in deployment_doc


def test_academic_director_academy_uses_single_shell_source():
    route_source = Path("backend/roles/academic_director/routes.py").read_text()
    academy_source = Path("frontend/src/roles/academic_director/pages/TeacherAcademy.tsx").read_text()

    assert '"academic-director-academy"' in route_source
    assert '"admin-home"' not in route_source
    assert "render_admin_page(" not in route_source
    assert academy_source.count("AcademicDirectorSidebar") >= 1
    assert "AdminSidebar" not in academy_source
    assert "TeacherAcademyPanel" in academy_source


def test_academic_director_critical_routes_remain_registered(app):
    routes = _route_methods(app)

    for method, path in [
        ("GET", "/"),
        ("POST", "/login"),
        ("POST", "/auth/telegram"),
        ("GET", "/academic-director"),
        ("GET", "/academic-director/teacher-academy"),
        ("POST", "/logout"),
        ("GET", "/admin"),
        ("GET", "/teacher"),
        ("GET", "/parent"),
        ("GET", "/api/v1/auth/me"),
    ]:
        assert path in routes
        assert method in routes[path]
