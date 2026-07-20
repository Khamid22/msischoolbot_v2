"""Clean Teacher Academy role API route coverage."""

import json
import os
from base64 import b64encode
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner


XHR = {"X-Requested-With": "XMLHttpRequest"}


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


def _patch_api_payload(monkeypatch):
    import backend.modules.teacher_academy.responses as academy_api

    monkeypatch.setattr(academy_api, "list_academy_teachers", lambda: [{"id": 91, "subject_id": 2}])
    monkeypatch.setattr(academy_api, "filter_academy_teachers_for_user", lambda rows, user: list(rows))
    monkeypatch.setattr(academy_api, "list_teachers", lambda: [{"id": 44, "full_name": "Example Teacher"}])
    return academy_api


def _route_methods(app):
    routes = {}

    def join_paths(prefix, path):
        if not prefix:
            return path
        if not path or path == "/":
            return prefix
        return f"{prefix.rstrip('/')}/{path.lstrip('/')}"

    def routes_already_include_prefix(route_list, prefix):
        if not prefix:
            return True
        for route in route_list:
            path = getattr(route, "path", None)
            if path is not None:
                return path == prefix or path.startswith(f"{prefix.rstrip('/')}/")
        return False

    def walk(route_list, prefix=""):
        for route in route_list:
            if type(route).__name__ == "_IncludedRouter":
                router_prefix = getattr(route.original_router, "prefix", "")
                next_prefix = (
                    prefix
                    if routes_already_include_prefix(route.original_router.routes, router_prefix)
                    else join_paths(prefix, router_prefix)
                )
                walk(
                    route.original_router.routes,
                    next_prefix,
                )
                continue
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is not None and methods:
                routes.setdefault(join_paths(prefix, path), set()).update(methods)
            nested = getattr(route, "routes", None)
            if nested:
                walk(nested, prefix)

    walk(app.routes)
    return routes


def test_clean_teacher_academy_api_routes_are_registered(app):
    routes = _route_methods(app)

    for path in [
        "/api/v1/academic-director/head-of-departments",
        "/api/v1/academic-director/head-of-departments/{account_id}/reset-password",
        "/api/v1/academic-director/teachers/{teacher_id}/reset-password",
        "/api/v1/academic-director/teacher-academy",
        "/api/v1/academic-director/teacher-academy/assignments/{assignment_id}",
        "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments",
        "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments/{assessment_id}/delete",
        "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/status",
        "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/lessons",
        "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/promote",
        "/api/v1/head-of-department/teacher-academy/assignments/{assignment_id}",
        "/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments",
        "/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments/{assessment_id}/delete",
        "/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/status",
        "/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/lessons",
    ]:
        assert "POST" in routes[path]
    assert "POST" not in routes.get(
        "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/delete",
        set(),
    )
    assert "POST" in routes[
        "/api/v1/recruitment/teachers/{academy_teacher_id}/remove"
    ]


def test_old_role_teacher_academy_api_routes_are_absent(app):
    routes = _route_methods(app)

    for path in [
        "/academic-director/api/head-of-departments",
        "/academic-director/api/teacher-academy",
        "/academic-director/api/teacher-academy/assignments/{assignment_id}",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/assessments",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/status",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/promote",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/delete",
        "/head-of-departments/api/teacher-academy/assignments/{assignment_id}",
        "/head-of-departments/api/teacher-academy/{academy_teacher_id}/assessments",
        "/head-of-departments/api/teacher-academy/{academy_teacher_id}/status",
    ]:
        assert "POST" not in routes.get(path, set())


def test_academic_director_create_academy_teacher_uses_selected_lessons_and_safe_credentials(client, monkeypatch):
    academy_api = _patch_api_payload(monkeypatch)
    captured = {}

    def fake_create_academy_teacher(**kwargs):
        captured.update(kwargs)
        return True, "", {
            "login": "TCH0004",
            "teacher_code": "TCH0004",
            "temporary_password": "TCH0004",
            "display_name": "Example Teacher",
            "subject_name": "Mathematics",
            "password_hash": "must-not-leak",
        }

    monkeypatch.setattr(academy_api, "create_academy_teacher", fake_create_academy_teacher)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.post(
        "/api/v1/academic-director/teacher-academy",
        data={
            "academy_full_name": "Example Teacher",
            "academy_subject_program_id": "7",
            "academy_curriculum_item_ids": "103,101",
        },
        headers=XHR,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["credentials"]["login"] == "TCH0004"
    assert "password_hash" not in payload["data"]["credentials"]
    assert captured["selected_curriculum_item_ids"] == ["103", "101"]
    assert captured["created_by"] == "AD0001"
    assert captured["return_credentials"] is True


def test_academic_director_can_reset_teacher_password_and_receives_it_once(client, monkeypatch):
    import backend.workspaces.academic_director.staff_records_api as staff_records_api

    captured = {}

    def fake_reset(teacher_id, **kwargs):
        captured["teacher_id"] = teacher_id
        captured.update(kwargs)
        return True, "", {
            "login": "TCH0042",
            "temporary_password": "SafePass4826",
            "display_name": "Example Teacher",
            "must_change_password": True,
            "updated_at": "2026-07-13T10:00:00Z",
        }

    monkeypatch.setattr(staff_records_api, "reset_teacher_password", fake_reset)
    _set_session(
        client,
        {"auth_role": "academic_director", "auth_login": "AD0001", "account_id": 12},
    )

    response = client.post(
        "/api/v1/academic-director/teachers/42/reset-password",
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "message": "Temporary password generated.",
        "login": "TCH0042",
        "temporary_password": "SafePass4826",
        "display_name": "Example Teacher",
        "must_change_password": True,
        "updated_at": "2026-07-13T10:00:00Z",
    }
    assert captured == {
        "teacher_id": 42,
        "actor_account_id": 12,
        "actor_login": "AD0001",
    }


def test_head_of_department_cannot_reset_teacher_password(client, monkeypatch):
    import backend.workspaces.academic_director.staff_records_api as staff_records_api

    def should_not_reset(*args, **kwargs):
        raise AssertionError("role dependency must reject this request before password reset")

    monkeypatch.setattr(staff_records_api, "reset_teacher_password", should_not_reset)
    _set_session(
        client,
        {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80},
    )

    response = client.post(
        "/api/v1/academic-director/teachers/42/reset-password",
        headers=XHR,
    )

    assert response.status_code == 403


def test_hr_and_academic_director_can_safely_remove_a_teacher_from_academy(client, monkeypatch):
    import backend.modules.hr.recruitment.api as recruitment_api

    calls = []

    def fake_remove(user, academy_teacher_id, values):
        calls.append((user.role, academy_teacher_id, values))
        return {
            "identity_deleted": False,
            "already_removed": False,
            "candidate": {"id": 164},
        }

    monkeypatch.setattr(recruitment_api.service, "remove_academy_teacher", fake_remove)
    payload = {"rejection_reason": "failed_academy", "reason_detail": "Did not pass Academy."}

    _set_session(
        client,
        {
            "auth_role": "hr_manager",
            "auth_login": "HR0001",
            "account_id": 41,
            "staff_id": 21,
        },
    )
    allowed = client.post(
        "/api/v1/recruitment/teachers/8/remove",
        json=payload,
        headers=XHR,
    )
    assert allowed.status_code == 200
    assert calls == [("hr_manager", 8, payload)]

    _set_session(
        client,
        {
            "auth_role": "academic_director",
            "auth_login": "AD0001",
            "account_id": 43,
            "staff_id": 23,
        },
    )
    academic_allowed = client.post(
        "/api/v1/recruitment/teachers/8/remove",
        json=payload,
        headers=XHR,
    )
    assert academic_allowed.status_code == 200
    assert calls[-1] == ("academic_director", 8, payload)

    for role in ("ceo", "head_of_department"):
        _set_session(
            client,
            {
                "auth_role": role,
                "auth_login": role.upper(),
                "account_id": 42,
                "staff_id": 22,
            },
        )
        denied = client.post(
            "/api/v1/recruitment/teachers/8/remove",
            json=payload,
            headers=XHR,
        )
        assert denied.status_code == 403

    assert calls == [
        ("hr_manager", 8, payload),
        ("academic_director", 8, payload),
    ]


def test_academic_director_schedule_assess_status_and_promote_routes_call_domain_service(client, monkeypatch):
    academy_api = _patch_api_payload(monkeypatch)
    calls = {}

    def fake_update_assignment(**kwargs):
        calls["assignment"] = kwargs
        return True, ""

    def fake_add_assessment(**kwargs):
        calls["assessment"] = kwargs
        return True, ""

    def fake_update_status(**kwargs):
        calls["status"] = kwargs
        return True, ""

    def fake_promote(**kwargs):
        calls["promote"] = kwargs
        return True, ""

    def fake_delete_assessment(**kwargs):
        calls["delete_assessment"] = kwargs
        return True, ""

    monkeypatch.setattr(academy_api, "update_assignment", fake_update_assignment)
    monkeypatch.setattr(academy_api, "add_assessment", fake_add_assessment)
    monkeypatch.setattr(academy_api, "update_academy_status", fake_update_status)
    monkeypatch.setattr(academy_api, "promote_academy_teacher", fake_promote)
    monkeypatch.setattr(academy_api, "delete_assessment", fake_delete_assessment)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    schedule_response = client.post(
        "/api/v1/academic-director/teacher-academy/assignments/8",
        data={"assignment_id": "8", "session_datetime": "2026-07-08T09:00", "assignment_status": "ready"},
        headers=XHR,
    )
    assessment_response = client.post(
        "/api/v1/academic-director/teacher-academy/91/assessments",
        data={"lesson_assignment_id": "8", "decision": "passed"},
        headers=XHR,
    )
    status_response = client.post(
        "/api/v1/academic-director/teacher-academy/91/status",
        data={"academy_status": "ready_for_active_teacher"},
        headers=XHR,
    )
    assessment_delete_response = client.post(
        "/api/v1/academic-director/teacher-academy/91/assessments/17/delete",
        headers=XHR,
    )
    promote_response = client.post(
        "/api/v1/academic-director/teacher-academy/91/promote",
        data={"teacher_assigned_group": "Grade 8A", "teacher_pay_rate": "100000"},
        headers=XHR,
    )
    assert schedule_response.status_code == 200
    assert assessment_response.status_code == 200
    assert status_response.status_code == 200
    assert assessment_delete_response.status_code == 200
    assert promote_response.status_code == 200
    assert calls["assignment"]["assignment_id"] == 8
    assert calls["assignment"]["status"] == "ready"
    assert calls["assessment"]["academy_teacher_id"] == 91
    assert calls["assessment"]["lesson_assignment_id"] == "8"
    assert calls["assessment"]["created_by"] == "AD0001"
    assert calls["status"] == {"academy_teacher_id": 91, "status": "ready_for_active_teacher"}
    assert calls["delete_assessment"] == {"academy_teacher_id": 91, "assessment_id": 17}
    assert calls["promote"]["academy_teacher_id"] == 91
    assert calls["promote"]["assigned_group"] == "Grade 8A"
    removed_route = client.post(
        "/api/v1/academic-director/teacher-academy/91/delete",
        headers=XHR,
    )
    assert removed_route.status_code == 404


def test_academic_director_lessons_sync_route_calls_domain_service(client, monkeypatch):
    academy_api = _patch_api_payload(monkeypatch)
    captured = {}

    def fake_sync_academy_lessons(**kwargs):
        captured.update(kwargs)
        return True, ""

    monkeypatch.setattr(academy_api, "sync_academy_lessons", fake_sync_academy_lessons)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    response = client.post(
        "/api/v1/academic-director/teacher-academy/91/lessons",
        data={"academy_curriculum_item_ids": "103,101,120"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert captured["academy_teacher_id"] == 91
    assert captured["selected_curriculum_item_ids"] == ["103", "101", "120"]
    assert captured["created_by"] == "AD0001"


def test_hod_schedule_own_scope_succeeds_and_out_of_scope_is_denied(client, monkeypatch):
    import backend.workspaces.head_of_departments.staff_records_api as hod_api_routes

    academy_api = _patch_api_payload(monkeypatch)
    calls = {"update": 0}

    def fake_update_assignment(**kwargs):
        calls["update"] += 1
        return True, ""

    monkeypatch.setattr(academy_api, "update_assignment", fake_update_assignment)
    monkeypatch.setattr(hod_api_routes, "can_user_manage_academy_assignment", lambda user, assignment_id: True)
    _set_session(client, {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80, "staff_id": 40})

    response = client.post(
        "/api/v1/head-of-department/teacher-academy/assignments/8",
        data={"assignment_id": "8", "assignment_status": "ready"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert calls["update"] == 1

    monkeypatch.setattr(hod_api_routes, "can_user_manage_academy_assignment", lambda user, assignment_id: False)
    denied = client.post(
        "/api/v1/head-of-department/teacher-academy/assignments/9",
        data={"assignment_id": "9", "assignment_status": "ready"},
        headers=XHR,
    )

    assert denied.status_code == 403
    assert denied.json()["message"] == "This Teacher Academy lesson is outside your subject scope."
    assert calls["update"] == 1


@pytest.mark.parametrize(
    ("path", "service_name", "expected_key"),
    [
        ("/api/v1/head-of-department/teacher-academy/91/assessments", "add_assessment", "assessment"),
        ("/api/v1/head-of-department/teacher-academy/91/assessments/17/delete", "delete_assessment", "delete_assessment"),
        ("/api/v1/head-of-department/teacher-academy/91/status", "update_academy_status", "status"),
        ("/api/v1/head-of-department/teacher-academy/91/lessons", "sync_academy_lessons", "lessons"),
    ],
)
def test_hod_teacher_routes_enforce_subject_scope(client, monkeypatch, path, service_name, expected_key):
    import backend.workspaces.head_of_departments.staff_records_api as hod_api_routes

    academy_api = _patch_api_payload(monkeypatch)
    calls = {}

    def fake_service(**kwargs):
        calls[expected_key] = kwargs
        return True, ""

    monkeypatch.setattr(academy_api, service_name, fake_service)
    monkeypatch.setattr(hod_api_routes, "can_user_manage_academy_teacher", lambda user, teacher_id: True)
    _set_session(client, {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80, "staff_id": 40})

    response = client.post(
        path,
        data={"lesson_assignment_id": "8", "academy_status": "ready_for_evaluation"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert expected_key in calls

    monkeypatch.setattr(hod_api_routes, "can_user_manage_academy_teacher", lambda user, teacher_id: False)
    denied = client.post(
        path,
        data={"lesson_assignment_id": "8", "academy_status": "ready_for_evaluation"},
        headers=XHR,
    )

    assert denied.status_code == 403
    assert denied.json()["message"] == "This Teacher Academy teacher is outside your subject scope."


def test_frontend_teacher_academy_uses_clean_role_routes_without_admin_action_fallback():
    panel_source = Path("frontend/src/features/teacher-academy/TeacherAcademyPanel.tsx").read_text()
    routes_source = Path("frontend/src/shared/lib/routes.ts").read_text()
    api_routes_source = Path("frontend/src/shared/api/routes.ts").read_text()
    ad_page = Path("frontend/src/workspaces/academic_director/pages/TeacherAcademy.tsx").read_text()
    hod_page = Path("frontend/src/workspaces/head_of_departments/pages/TeacherAcademy.tsx").read_text()

    assert "routes.academicDirectorTeacherAcademyCreate" in panel_source
    assert "routes.academicDirectorTeacherAcademyAssignmentUpdate" in panel_source
    assert "routes.academicDirectorTeacherAcademyAssessmentCreate" in panel_source
    assert "routes.academicDirectorTeacherAcademyAssessmentDelete" in panel_source
    assert "routes.academicDirectorTeacherAcademyDelete" not in panel_source
    assert "routes.academicDirectorTeacherPasswordReset" in panel_source
    assert "Password reset — same as the login" in panel_source
    assert "Delete assessment report" in panel_source
    assert "assessmentDelete" in panel_source
    assert "routes.headOfDepartmentTeacherAcademyAssignmentUpdate" in panel_source
    assert "routes.headOfDepartmentTeacherAcademyAssessmentCreate" in panel_source
    assert "routes.headOfDepartmentTeacherAcademyAssessmentDelete" in panel_source
    assert "submit(routes.adminTeacherAcademy" not in panel_source
    assert "routes.adminTeacherAcademy" not in panel_source
    assert "apiRoutes.academicDirectorTeacherAcademyCreate" in routes_source
    assert 'academicDirectorTeacherAcademyCreate: "/api/v1/academic-director/teacher-academy"' in api_routes_source
    assert "academicDirectorTeacherAcademyDelete" not in routes_source
    assert "academicDirectorTeacherAcademyDelete" not in api_routes_source
    assert "academicDirectorTeacherPasswordReset" in routes_source
    assert "/api/v1/academic-director/teachers/${teacherId}/reset-password" in api_routes_source
    assert "academicDirectorTeacherAcademyAssessmentDelete" in routes_source
    assert "headOfDepartmentTeacherAcademyAssignmentUpdate" in routes_source
    assert "headOfDepartmentTeacherAcademyAssessmentDelete" in routes_source
    assert "adminTeacherAcademy" not in routes_source
    assert "/admin/teacher-academy" not in routes_source
    assert "/academic-director/api" not in routes_source
    assert "/head-of-departments/api" not in routes_source
    assert "/academic-director/api" not in api_routes_source
    assert "/head-of-departments/api" not in api_routes_source
    assert 'managementMode: props.managementMode || "academic_director"' in ad_page
    assert 'managementMode: "head_of_department"' in hod_page


def test_teacher_academy_legacy_deletion_plan_documents_completed_admin_cleanup():
    plan_source = Path("docs/TEACHER_ACADEMY_LEGACY_DELETION_PLAN.md").read_text()

    for required in [
        "Status: completed",
        "Removed old admin Teacher Academy action routes",
        "Removed `backend/roles/admin/services/teacher_academy_service.py`",
        "Removed `adminTeacherAcademy...` frontend action helpers",
        "Academic Director mode uses `/api/v1/academic-director/teacher-academy...`",
        "Head of Department mode uses `/api/v1/head-of-department/teacher-academy...`",
        "Admin/system admin no longer posts Teacher Academy actions through `/admin`.",
    ]:
        assert required in plan_source
