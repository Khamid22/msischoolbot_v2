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
    schema = app.openapi()
    return {
        path: {method.upper() for method in path_spec.keys()}
        for path, path_spec in schema.get("paths", {}).items()
    }


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
        "schools": [{"code": "school5", "name": "School 5"}],
        "subjects": [{"id": 5, "name": "Mathematics", "subject_name": "Mathematics"}],
        "groups": [
            {
                "id": 100,
                "name": "Math 10A",
                "group_name": "Math 10A",
                "subject_name": "Mathematics",
                "school_code": "school5",
                "students_count": 12,
            }
        ],
        "enrollments": [],
        "lessons": [
            {
                "id": 701,
                "group_id": 100,
                "group_name": "Math 10A",
                "subject_name": "Mathematics",
                "lesson_number": "Lesson 3",
                "lesson_topic": "HCF and LCM",
                "lesson_date": "2026-07-08",
            }
        ],
        "schedules": [
            {
                "id": 301,
                "group_id": 100,
                "group_name": "Math 10A",
                "subject_name": "Mathematics",
                "weekday": 3,
                "start_time": "09:30",
                "end_time": "11:00",
            }
        ],
        "sessions": [
            {
                "id": 401,
                "group_id": 100,
                "group_name": "Math 10A",
                "subject_name": "Mathematics",
                "session_date": "2026-07-08",
                "start_time": "09:30",
                "end_time": "11:00",
            }
        ],
        "curriculum_programs": [
            {
                "id": 5,
                "subject_key": "igcse-mathematics",
                "subject_name": "Mathematics",
                "lesson_count": 1,
                "exam_count": 0,
                "total_items": 1,
            }
        ],
        "curriculum_items": [
            {
                "id": 900,
                "program_id": 5,
                "item_type": "lesson",
                "lesson_number": "Lesson 3",
                "title": "HCF and LCM",
            }
        ],
        "enrollment_summary": {},
    }


def _patch_academic_director_cards(monkeypatch):
    import backend.pages.academic_director as academic_director_routes

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
    import backend.pages.academic_director as academic_director_routes
    import backend.pages.head_of_department as head_of_department_routes

    def fake_teacher_academy_page_context():
        admin_context = _minimal_admin_page_context()
        academic_context = _minimal_academic_context()
        return {
            "teachers": admin_context["admin_teachers"],
            "academy_teachers": admin_context["admin_teacher_academy"],
            "group_options": admin_context["admin_group_options"],
            "subjects": academic_context["subjects"],
            "curriculum_programs": academic_context["curriculum_programs"],
            "curriculum_items": academic_context["curriculum_items"],
        }

    monkeypatch.setattr(admin_page, "build_admin_page_context", lambda **kwargs: _minimal_admin_page_context())
    monkeypatch.setattr(admin_page, "list_admin_academic_context", _minimal_academic_context)
    monkeypatch.setattr(academic_director_routes, "list_academic_admin_rows", lambda include_heavy=True: _minimal_academic_context())
    monkeypatch.setattr(admin_page, "list_announcements", lambda: [])
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
    monkeypatch.setattr(head_of_department_routes, "head_of_department_workspace_cards", lambda: [])
    monkeypatch.setattr(academic_director_routes, "list_teacher_academy_page_context", fake_teacher_academy_page_context)
    monkeypatch.setattr(
        academic_director_routes,
        "list_academy_timetable_events",
        lambda subject_ids=None: [
            {
                "id": "academy-100",
                "assignment_id": 100,
                "subject_id": 5,
                "subject_name": "Mathematics",
                "teacher_name": "Academy Math Teacher",
                "group_name": "Teacher Academy",
                "title": "Lesson 3 - HCF and LCM",
                "session_date": "2026-07-08",
                "start_time": "09:30",
                "status": "assigned",
                "evaluator_name": "Ada HOD",
                "event_type": "academy_lesson",
            },
            {
                "id": "academy-101",
                "assignment_id": 101,
                "subject_id": 7,
                "subject_name": "English",
                "teacher_name": "Academy English Teacher",
                "group_name": "Teacher Academy",
                "title": "Lesson 4 - Essay planning",
                "session_date": "2026-07-08",
                "start_time": "11:30",
                "status": "assigned",
                "evaluator_name": "Grace HOD",
                "event_type": "academy_lesson",
            },
        ]
        if subject_ids is None
        else [
            row
            for row in academic_director_routes.list_academy_timetable_events()
            if int(row["subject_id"]) in set(subject_ids)
        ],
    )
    monkeypatch.setattr(
        academic_director_routes,
        "list_announcements",
        lambda include_drafts=True: [
            {
                "id": 30,
                "title": "Term Update",
                "body": "Academic Department update.",
                "audience": "teachers",
                "priority": "info",
                "status": "published",
                "pinned": False,
            }
        ],
    )
    monkeypatch.setattr(head_of_department_routes, "list_teacher_academy_page_context", fake_teacher_academy_page_context)
    monkeypatch.setattr(head_of_department_routes, "current_hod_subject_ids", lambda: {5})
    monkeypatch.setattr(head_of_department_routes, "list_academy_timetable_events", academic_director_routes.list_academy_timetable_events)
    monkeypatch.setattr(head_of_department_routes, "list_announcements", academic_director_routes.list_announcements)
    monkeypatch.setattr(
        academic_director_routes,
        "list_active_subjects",
        lambda: [
            {"id": 5, "name": "Mathematics"},
            {"id": 7, "name": "English"},
        ],
    )
    monkeypatch.setattr(
        academic_director_routes,
        "list_head_of_department_accounts",
        lambda: {
            "items": [
                {
                    "account_id": 80,
                    "login": "HOD0001",
                    "display_name": "Head of Math Department",
                    "role": "head_of_department",
                    "status": "active",
                    "subject_id": 5,
                    "subject_name": "Mathematics",
                    "scope_type": "head_of_department",
                    "created_at": "2026-07-06T10:00:00Z",
                    "updated_at": "2026-07-06T10:00:00Z",
                }
            ],
            "warning": "",
        },
    )


def test_academic_director_home_bootstrap_keeps_cards_and_profile_context(client, monkeypatch):
    _patch_academic_director_cards(monkeypatch)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.get("/academic-director")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
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
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert 'data-react-page="academic-director-academy"' in response.text
    assert "academic_director" in response.text
    assert "Student mode" not in response.text
    assert 'data-react-page="admin-home"' not in response.text


def test_academic_director_head_of_departments_route_loads_safe_page(client, monkeypatch):
    _patch_admin_page_context(monkeypatch)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.get("/academic-director/head-of-departments")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert 'data-react-page="academic-director-head-of-departments"' in response.text
    assert "Head of Departments" in response.text
    assert "Head of Math Department" in response.text
    assert "Mathematics" in response.text
    assert "password_hash" not in response.text
    assert "Student mode" not in response.text
    assert 'data-react-page="admin-home"' not in response.text


def test_academic_department_timetable_announcements_and_profile_routes_load(client, monkeypatch):
    _patch_admin_page_context(monkeypatch)
    ad_workspace_source = Path("frontend/src/roles/academic_director/pages/AcademicWorkspace.tsx").read_text()
    department_workspace_source = Path("frontend/src/roles/common/pages/AcademicDepartmentWorkspace.tsx").read_text()

    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})
    ad_groups = client.get("/academic-director/groups")
    ad_subjects = client.get("/academic-director/subjects")
    ad_timetable = client.get("/academic-director/timetable")
    ad_announcements = client.get("/academic-director/announcements")
    ad_profile = client.get("/academic-director/profile")

    assert ad_groups.status_code == 200
    assert 'data-react-page="academic-director-groups"' in ad_groups.text
    assert "Math 10A" in ad_groups.text
    assert ad_subjects.status_code == 200
    assert 'data-react-page="academic-director-subjects"' in ad_subjects.text
    assert "Mathematics" in ad_subjects.text
    assert ad_timetable.status_code == 200
    assert 'data-react-page="academic-director-timetable"' in ad_timetable.text
    # Academic Director timetable is the group academic timetable; Teacher
    # Academy lesson schedule now lives inside the Teacher Academy page.
    assert "Math 10A" in ad_timetable.text
    assert "adminAcademicSessions" in ad_timetable.text
    assert "adminAcademicSchedules" in ad_timetable.text
    assert "adminAcademyLessonEvents" not in ad_timetable.text
    assert "Academy Math Teacher" not in ad_timetable.text
    assert "AdminSidebar" not in ad_timetable.text
    assert "Student mode" not in ad_timetable.text
    assert ad_announcements.status_code == 200
    assert 'data-react-page="academic-director-announcements"' in ad_announcements.text
    assert "Term Update" in ad_announcements.text
    assert "AcademicPanel" in ad_workspace_source
    assert "academicDirectorAcademicRoutes" in ad_workspace_source
    assert "adminAcademyLessonEvents" not in ad_workspace_source
    assert "adminAcademicSessions" not in department_workspace_source
    assert "adminAcademicSchedules" not in department_workspace_source
    assert 'data-react-page="admin-home"' not in ad_announcements.text
    assert ad_profile.status_code == 200
    assert 'data-react-page="academic-director-home"' in ad_profile.text
    assert "Academic Director Profile" in ad_profile.text

    client.cookies.clear()
    _set_session(client, {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80})
    hod_timetable = client.get("/head-of-department/timetable")
    hod_announcements = client.get("/head-of-department/announcements")
    hod_profile = client.get("/head-of-department/profile")

    assert hod_timetable.status_code == 200
    assert 'data-react-page="head-of-department-timetable"' in hod_timetable.text
    # Subject scope keeps only the Mathematics academy lesson; gradebook
    # sessions are no longer part of the timetable.
    assert "Math 10A" not in hod_timetable.text
    assert "English 9B" not in hod_timetable.text
    assert "Lesson 3 - HCF and LCM" in hod_timetable.text
    assert "Academy Math Teacher" in hod_timetable.text
    assert "Lesson 4 - Essay planning" not in hod_timetable.text
    assert "Academy English Teacher" not in hod_timetable.text
    assert "password_hash" not in hod_timetable.text
    assert "AdminSidebar" not in hod_timetable.text
    assert "Student mode" not in hod_timetable.text
    assert hod_announcements.status_code == 200
    assert 'data-react-page="head-of-department-announcements"' in hod_announcements.text
    assert "Term Update" in hod_announcements.text
    assert hod_profile.status_code == 200
    assert 'data-react-page="head-of-department-home"' in hod_profile.text
    assert "Head of Department Profile" in hod_profile.text


def test_academic_department_overviews_do_not_render_duplicate_profile_logout_blocks():
    source = Path("frontend/src/roles/common/pages/RoleHome.tsx").read_text()
    route_source = Path("backend/pages/academic_director.py").read_text()
    hod_route_source = Path("backend/pages/head_of_department.py").read_text()
    ad_overview_block = source.split("function AcademicDirectorHome", 1)[1].split("function HeadOfDepartmentHome", 1)[0]
    hod_overview_block = source.split("function HeadOfDepartmentHome", 1)[1].split("export function RoleHome", 1)[0]
    ad_overview_return = ad_overview_block.rsplit("return (", 1)[1]
    hod_overview_return = hod_overview_block.rsplit("return (", 1)[1]

    assert 'view?: "overview" | "profile"' in source
    assert 'view="profile"' in route_source
    assert 'view="profile"' in hod_route_source
    assert 'view === "profile"' in ad_overview_block
    assert 'view === "profile"' in hod_overview_block
    assert "AcademicDirectorProfileSection authLogin={authLogin} csrfToken={csrfToken}" in ad_overview_block
    assert "HeadOfDepartmentProfileSection authLogin={authLogin} csrfToken={csrfToken}" in hod_overview_block
    assert "AcademicDirectorProfileSection" not in ad_overview_return
    assert "HeadOfDepartmentProfileSection" not in hod_overview_return
    assert "AcademicDirectorTeacherAcademyCta" in ad_overview_return
    assert "HeadOfDepartmentTeacherAcademyCta" in hod_overview_return


def test_academic_director_shell_source_contains_sidebar_profile_logout_and_mobile_nav():
    source = Path("frontend/src/roles/common/components/AcademicDirectorShell.tsx").read_text()
    nav_source = Path("frontend/src/roles/common/components/academicNav.ts").read_text()
    routes_source = Path("frontend/src/shared/lib/routes.ts").read_text()
    admin_source = Path("frontend/src/roles/admin/pages/Admin.tsx").read_text()
    academy_source = Path("frontend/src/roles/academic_director/pages/TeacherAcademy.tsx").read_text()
    hod_academy_source = Path("frontend/src/roles/head_of_department/pages/TeacherAcademy.tsx").read_text()
    app_source = Path("frontend/src/app/App.tsx").read_text()
    bootstrap_source = Path("frontend/src/shared/lib/bootstrap.ts").read_text()
    stale_state_source = Path("frontend/src/shared/lib/staleUiState.ts").read_text()
    admin_state_source = Path("frontend/src/roles/admin/hooks/useAdminState.ts").read_text()
    admin_page_source = Path("backend/roles/admin/routes/admin_page.py").read_text()
    deployment_doc = Path("docs/ENGINEERING_DEPLOYMENT.md").read_text()

    assert "Academic Director navigation" in source
    assert "Academic Director mobile navigation" in source
    assert "Head of Department navigation" in source
    assert "Head of Department mobile navigation" in source
    # Nav item definitions moved to the pure academicNav.ts config so they can
    # run under node --test; the shell attaches icons and renders them.
    assert 'label: "Overview"' in nav_source
    assert 'label: "Teacher Academy"' in nav_source
    assert 'label: "Timetable"' in nav_source
    assert 'label: "Announcements"' in nav_source
    assert 'label: "Profile"' in nav_source
    assert 'mobileLabel: "Academy"' in nav_source
    assert 'mobileLabel: "Schedule"' in nav_source
    assert 'mobileLabel: "News"' in nav_source
    assert "Head of Departments" in nav_source
    assert "academicDirectorNavConfig" in source
    assert "Open Teacher Academy" in source
    assert 'academicDirectorOverview: "/academic-director"' in routes_source
    assert 'academicDirectorTeacherAcademy: "/academic-director/teacher-academy"' in routes_source
    assert 'academicDirectorHeadOfDepartments: "/academic-director/head-of-departments"' in routes_source
    assert 'academicDirectorGroups: "/academic-director/groups"' in routes_source
    assert 'academicDirectorSubjects: "/academic-director/subjects"' in routes_source
    assert 'academicDirectorTimetable: "/academic-director/timetable"' in routes_source
    assert 'academicDirectorAnnouncements: "/academic-director/announcements"' in routes_source
    assert 'academicDirectorProfile: "/academic-director/profile"' in routes_source
    assert "academicDirectorProfileSection" not in routes_source
    assert 'headOfDepartmentOverview: "/head-of-department"' in routes_source
    assert 'headOfDepartmentTeacherAcademy: "/head-of-department/teacher-academy"' in routes_source
    assert 'headOfDepartmentTimetable: "/head-of-department/timetable"' in routes_source
    assert 'headOfDepartmentAnnouncements: "/head-of-department/announcements"' in routes_source
    assert 'headOfDepartmentProfile: "/head-of-department/profile"' in routes_source
    assert "headOfDepartmentProfileSection" not in routes_source
    assert "href: routes.academicDirectorTeacherAcademy" in nav_source
    assert "href: routes.academicDirectorHeadOfDepartments" in nav_source
    assert "href: routes.academicDirectorGroups" in nav_source
    assert "href: routes.academicDirectorSubjects" in nav_source
    assert "href: routes.academicDirectorTimetable" in nav_source
    assert "href: routes.academicDirectorAnnouncements" in nav_source
    assert "href: routes.academicDirectorProfile" in nav_source
    assert "href: routes.headOfDepartmentTeacherAcademy" in nav_source
    assert "href: routes.headOfDepartmentTimetable" in nav_source
    assert "href: routes.headOfDepartmentAnnouncements" in nav_source
    assert "href: routes.headOfDepartmentProfile" in nav_source
    assert "academic-director-profile" in source
    assert "head-of-department-profile" in source
    assert "academicDirectorActiveNavFromPath" in source
    assert "headOfDepartmentActiveNavFromPath" in source
    assert 'mobileNavItemsFrom(academicDirectorNavConfig, ["departments", "subjects", "announcements"])' in nav_source
    assert "pointer-events-none" not in source
    assert "AdminSidebar" not in source
    assert "action={routes.logout}" in source
    assert 'name="csrf_token"' in source
    assert "AcademicDirectorMobileNav active=\"academy\"" not in admin_source
    assert "AdminSidebar" not in academy_source
    assert "AcademicDirectorPageShell" in academy_source
    assert 'active="academy"' in academy_source
    assert "HeadOfDepartmentPageShell" in hod_academy_source
    assert 'active="academy"' in hod_academy_source
    assert "allowTeacherPreview={false}" in academy_source
    assert "if (!allowTeacherPreview)" in Path(
        "frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx"
    ).read_text()
    assert '"academic-director-academy"' in app_source
    assert '"academic-director-head-of-departments"' in app_source
    assert '"academic-director-groups"' in app_source
    assert '"academic-director-subjects"' in app_source
    assert '"academic-director-timetable"' in app_source
    assert '"academic-director-announcements"' in app_source
    assert '"head-of-department-home"' in app_source
    assert '"head-of-department-academy"' in app_source
    assert '"head-of-department-timetable"' in app_source
    assert '"head-of-department-announcements"' in app_source
    assert '"academic-director-academy"' in bootstrap_source
    assert '"academic-director-head-of-departments"' in bootstrap_source
    assert '"academic-director-groups"' in bootstrap_source
    assert '"academic-director-subjects"' in bootstrap_source
    assert '"academic-director-timetable"' in bootstrap_source
    assert '"academic-director-announcements"' in bootstrap_source
    assert '"head-of-department-home"' in bootstrap_source
    assert '"head-of-department-academy"' in bootstrap_source
    assert '"head-of-department-timetable"' in bootstrap_source
    assert '"head-of-department-announcements"' in bootstrap_source
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
    assert "Boolean(props.devPreviewEnabled) && canUseAdminPreviewForRole(realRole)" in admin_state_source
    assert "clearRolePreviewStorage()" in admin_state_source
    assert "modeParam && allowPreviewMode" in admin_state_source
    assert "urlAdminMode() || storedAdminMode()" in admin_state_source
    assert 'buildAdminTabUrl(nextTab, currentSchool, allowPreviewMode ? adminMode : "")' in admin_state_source
    assert 'buildAdminTabUrl(fallbackTab, currentSchool, allowPreviewMode ? adminMode : "")' in admin_state_source
    assert 'preview_enabled = current_auth_role() == "admin" and _dev_preview_enabled()' in admin_page_source
    # Preview gating lives entirely in useAdminState; Admin.tsx just consumes
    # the resolved state and must not re-derive it.
    assert "canUseAdminPreviewForRole" not in admin_source
    assert "Account/profile auth is always active." in deployment_doc
    assert "ADMIN_PREVIEW_ROLES=0" in deployment_doc


def test_academic_director_academy_uses_single_shell_source():
    server_source = Path("backend/server.py").read_text()
    route_source = Path("backend/pages/academic_director.py").read_text()
    hod_route_source = Path("backend/pages/head_of_department.py").read_text()
    academy_source = Path("frontend/src/roles/academic_director/pages/TeacherAcademy.tsx").read_text()
    hod_academy_source = Path("frontend/src/roles/head_of_department/pages/TeacherAcademy.tsx").read_text()

    assert "register_academic_director_page_routes(app_instance, render_admin_page" not in server_source
    assert "register_head_of_department_page_routes(app_instance, render_admin_page" not in server_source
    assert "register_academic_director_page_routes(app_instance)" in server_source
    assert "register_head_of_department_page_routes(app_instance)" in server_source
    assert "def register_academic_director_page_routes(app):" in route_source
    assert "def register_head_of_department_page_routes(app):" in hod_route_source
    assert "render_admin_page" not in route_source
    assert "render_admin_page" not in hod_route_source
    assert "previewRole" not in route_source
    assert "previewRole" not in hod_route_source
    assert "devPreviewEnabled" not in route_source
    assert "devPreviewEnabled" not in hod_route_source
    assert '"academic-director-academy"' in route_source
    assert '"admin-home"' not in route_source
    assert academy_source.count("AcademicDirectorPageShell") >= 1
    assert "AdminSidebar" not in academy_source
    assert "AcademicDirectorSidebar" not in academy_source
    assert "AcademicDirectorMobileNav" not in academy_source
    assert "TeacherAcademyPanel" in academy_source
    assert "HeadOfDepartmentPageShell" in hod_academy_source
    assert "AdminSidebar" not in hod_academy_source
    assert "HeadOfDepartmentSidebar" not in hod_academy_source
    assert "HeadOfDepartmentMobileNav" not in hod_academy_source
    assert "TeacherAcademyPanel" in hod_academy_source


def test_academic_director_critical_routes_remain_registered(app):
    routes = _route_methods(app)

    for method, path in [
        ("GET", "/"),
        ("POST", "/login"),
        ("POST", "/auth/telegram"),
        ("GET", "/academic-director"),
        ("GET", "/academic-director/teacher-academy"),
        ("GET", "/academic-director/head-of-departments"),
        ("GET", "/academic-director/groups"),
        ("GET", "/academic-director/subjects"),
        ("GET", "/academic-director/timetable"),
        ("GET", "/academic-director/announcements"),
        ("GET", "/academic-director/profile"),
        ("GET", "/api/v1/academic-director/academic/context"),
        ("POST", "/api/v1/academic-director/academic/groups"),
        ("POST", "/api/v1/academic-director/academic/schools"),
        ("POST", "/api/v1/academic-director/academic/schedules"),
        ("GET", "/head-of-department"),
        ("GET", "/head-of-department/teacher-academy"),
        ("GET", "/head-of-department/timetable"),
        ("GET", "/head-of-department/announcements"),
        ("GET", "/head-of-department/profile"),
        ("POST", "/logout"),
        ("GET", "/admin"),
        ("GET", "/teacher"),
        ("GET", "/parent"),
        ("GET", "/api/v1/auth/me"),
    ]:
        assert path in routes
        assert method in routes[path]
