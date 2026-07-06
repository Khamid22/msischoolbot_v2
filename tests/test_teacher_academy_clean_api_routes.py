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
    import backend.roles.common.teacher_academy_api as academy_api

    monkeypatch.setattr(academy_api, "invalidate_admin_page_context_cache", lambda: None)
    monkeypatch.setattr(academy_api, "list_academy_teachers", lambda: [{"id": 91, "subject_id": 2}])
    monkeypatch.setattr(academy_api, "filter_academy_teachers_for_current_scope", lambda rows: list(rows))
    monkeypatch.setattr(academy_api, "list_teachers", lambda: [{"id": 44, "full_name": "Example Teacher"}])
    return academy_api


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


def test_clean_teacher_academy_api_routes_are_registered(app):
    routes = _route_methods(app)

    for path in [
        "/academic-director/api/teacher-academy",
        "/academic-director/api/teacher-academy/assignments/{assignment_id}",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/assessments",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/status",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/promote",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/delete",
        "/head-of-department/api/teacher-academy/assignments/{assignment_id}",
        "/head-of-department/api/teacher-academy/{academy_teacher_id}/assessments",
        "/head-of-department/api/teacher-academy/{academy_teacher_id}/status",
    ]:
        assert "POST" in routes[path]


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
        "/academic-director/api/teacher-academy",
        data={
            "academy_full_name": "Example Teacher",
            "academy_subject_program_id": "7",
            "academy_curriculum_item_ids": "103,101",
        },
        headers=XHR,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["credentials"]["login"] == "TCH0004"
    assert "password_hash" not in payload["credentials"]
    assert captured["selected_curriculum_item_ids"] == ["103", "101"]
    assert captured["created_by"] == "AD0001"
    assert captured["return_credentials"] is True


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

    def fake_delete(**kwargs):
        calls["delete"] = kwargs
        return True, ""

    monkeypatch.setattr(academy_api, "update_assignment", fake_update_assignment)
    monkeypatch.setattr(academy_api, "add_assessment", fake_add_assessment)
    monkeypatch.setattr(academy_api, "update_academy_status", fake_update_status)
    monkeypatch.setattr(academy_api, "promote_academy_teacher", fake_promote)
    monkeypatch.setattr(academy_api, "delete_academy_teacher", fake_delete)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "AD0001"})

    schedule_response = client.post(
        "/academic-director/api/teacher-academy/assignments/8",
        data={"assignment_id": "8", "session_datetime": "2026-07-08T09:00", "assignment_status": "ready"},
        headers=XHR,
    )
    assessment_response = client.post(
        "/academic-director/api/teacher-academy/91/assessments",
        data={"lesson_assignment_id": "8", "decision": "passed"},
        headers=XHR,
    )
    status_response = client.post(
        "/academic-director/api/teacher-academy/91/status",
        data={"academy_status": "ready_for_active_teacher"},
        headers=XHR,
    )
    promote_response = client.post(
        "/academic-director/api/teacher-academy/91/promote",
        data={"teacher_assigned_group": "Grade 8A", "teacher_pay_rate": "100000"},
        headers=XHR,
    )
    delete_response = client.post(
        "/academic-director/api/teacher-academy/91/delete",
        headers=XHR,
    )

    assert schedule_response.status_code == 200
    assert assessment_response.status_code == 200
    assert status_response.status_code == 200
    assert promote_response.status_code == 200
    assert delete_response.status_code == 200
    assert calls["assignment"]["assignment_id"] == 8
    assert calls["assignment"]["status"] == "ready"
    assert calls["assessment"]["academy_teacher_id"] == 91
    assert calls["assessment"]["lesson_assignment_id"] == "8"
    assert calls["assessment"]["created_by"] == "AD0001"
    assert calls["status"] == {"academy_teacher_id": 91, "status": "ready_for_active_teacher"}
    assert calls["promote"]["academy_teacher_id"] == 91
    assert calls["promote"]["assigned_group"] == "Grade 8A"
    assert calls["delete"]["academy_teacher_id"] == 91


def test_hod_schedule_own_scope_succeeds_and_out_of_scope_is_denied(client, monkeypatch):
    import backend.roles.head_of_department.routes as hod_routes

    academy_api = _patch_api_payload(monkeypatch)
    calls = {"update": 0}

    def fake_update_assignment(**kwargs):
        calls["update"] += 1
        return True, ""

    monkeypatch.setattr(academy_api, "update_assignment", fake_update_assignment)
    monkeypatch.setattr(hod_routes, "can_current_user_manage_academy_assignment", lambda assignment_id: True)
    _set_session(client, {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80, "staff_id": 40})

    response = client.post(
        "/head-of-department/api/teacher-academy/assignments/8",
        data={"assignment_id": "8", "assignment_status": "ready"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert calls["update"] == 1

    monkeypatch.setattr(hod_routes, "can_current_user_manage_academy_assignment", lambda assignment_id: False)
    denied = client.post(
        "/head-of-department/api/teacher-academy/assignments/9",
        data={"assignment_id": "9", "assignment_status": "ready"},
        headers=XHR,
    )

    assert denied.status_code == 403
    assert denied.json()["message"] == "This Teacher Academy lesson is outside your subject scope."
    assert calls["update"] == 1


@pytest.mark.parametrize(
    ("path", "service_name", "expected_key"),
    [
        ("/head-of-department/api/teacher-academy/91/assessments", "add_assessment", "assessment"),
        ("/head-of-department/api/teacher-academy/91/status", "update_academy_status", "status"),
    ],
)
def test_hod_teacher_routes_enforce_subject_scope(client, monkeypatch, path, service_name, expected_key):
    import backend.roles.head_of_department.routes as hod_routes

    academy_api = _patch_api_payload(monkeypatch)
    calls = {}

    def fake_service(**kwargs):
        calls[expected_key] = kwargs
        return True, ""

    monkeypatch.setattr(academy_api, service_name, fake_service)
    monkeypatch.setattr(hod_routes, "can_current_user_manage_academy_teacher", lambda teacher_id: True)
    _set_session(client, {"auth_role": "head_of_department", "auth_login": "HOD0001", "account_id": 80, "staff_id": 40})

    response = client.post(
        path,
        data={"lesson_assignment_id": "8", "academy_status": "ready_for_evaluation"},
        headers=XHR,
    )

    assert response.status_code == 200
    assert expected_key in calls

    monkeypatch.setattr(hod_routes, "can_current_user_manage_academy_teacher", lambda teacher_id: False)
    denied = client.post(
        path,
        data={"lesson_assignment_id": "8", "academy_status": "ready_for_evaluation"},
        headers=XHR,
    )

    assert denied.status_code == 403
    assert denied.json()["message"] == "This Teacher Academy teacher is outside your subject scope."


def test_frontend_teacher_academy_uses_clean_role_routes_without_admin_action_fallback():
    panel_source = Path("frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx").read_text()
    routes_source = Path("frontend/src/shared/lib/routes.ts").read_text()
    ad_page = Path("frontend/src/roles/academic_director/pages/TeacherAcademy.tsx").read_text()
    hod_page = Path("frontend/src/roles/head_of_department/pages/TeacherAcademy.tsx").read_text()

    assert "routes.academicDirectorTeacherAcademyCreate" in panel_source
    assert "routes.academicDirectorTeacherAcademyAssignmentUpdate" in panel_source
    assert "routes.academicDirectorTeacherAcademyAssessmentCreate" in panel_source
    assert "routes.academicDirectorTeacherAcademyDelete" in panel_source
    assert "routes.headOfDepartmentTeacherAcademyAssignmentUpdate" in panel_source
    assert "routes.headOfDepartmentTeacherAcademyAssessmentCreate" in panel_source
    assert "submit(routes.adminTeacherAcademy" not in panel_source
    assert "routes.adminTeacherAcademy" not in panel_source
    assert "academicDirectorTeacherAcademyCreate: \"/academic-director/api/teacher-academy\"" in routes_source
    assert "academicDirectorTeacherAcademyDelete" in routes_source
    assert "headOfDepartmentTeacherAcademyAssignmentUpdate" in routes_source
    assert "adminTeacherAcademy" not in routes_source
    assert "/admin/teacher-academy" not in routes_source
    assert "adminMode: props.adminMode || \"academic_director\"" in ad_page
    assert "adminMode: \"head_of_department\"" in hod_page


def test_teacher_academy_legacy_deletion_plan_documents_completed_admin_cleanup():
    plan_source = Path("TEACHER_ACADEMY_LEGACY_DELETION_PLAN.md").read_text()

    for required in [
        "Status: completed",
        "Removed old admin Teacher Academy action routes",
        "Removed `backend/roles/admin/services/teacher_academy_service.py`",
        "Removed `adminTeacherAcademy...` frontend action helpers",
        "Academic Director mode uses `/academic-director/api/teacher-academy...`",
        "Head of Department mode uses `/head-of-department/api/teacher-academy...`",
        "Admin/system admin no longer posts Teacher Academy actions through `/admin`.",
    ]:
        assert required in plan_source
