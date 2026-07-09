"""Tomorrow-ready Teacher Academy safety coverage."""

import json
import os
from base64 import b64encode
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner

from backend.domains.teacher_academy.notifications import notify_academy_teacher_event
from backend.roles.teacher.workspace_cards import build_teacher_workspace_cards


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


def _teacher_home_source():
    return Path("frontend/src/roles/teacher/pages/TeacherHome.tsx").read_text()


def _academy_workspace():
    return {
        "teacher": {
            "id": 42,
            "full_name": "Example Teacher",
            "login": "TCH0004",
            "assigned_group": "",
            "category": "academy",
            "semester_stage": "",
            "performance_score": 7.0,
        },
        "groups": [],
        "academy": {
            "id": 7,
            "full_name": "Example Teacher",
            "subject": "Mathematics",
            "subject_program_name": "IGCSE Mathematics",
            "academy_status": "in_training",
            "academy_start_date": "2026-07-06",
            "progress": {
                "assigned_count": 12,
                "assessed_count": 3,
                "passed_count": 2,
                "average_score": 8.2,
                "latest_score": 8.7,
                "target_lessons": 12,
            },
        },
        "academy_summary": {
            "assigned_count": 12,
            "assessed_count": 3,
            "completed_count": 3,
            "remaining_count": 9,
            "target_lessons": 12,
            "progress_percent": 25,
            "rank": "On track",
            "status": "in_training",
            "subject": "IGCSE Mathematics",
            "training_start_date": "2026-07-06",
            "training_end_date": "2026-08-01T09:00:00Z",
            "average_score": 8.2,
            "latest_score": 8.7,
            "score_summary": "3 assessed lessons; latest 8.7/10.",
        },
        "academy_updates": [
            {
                "id": "assessment-1",
                "kind": "assessment",
                "title": "Assessment report added",
                "body": "Ready for the next lesson.",
                "source": "Academic Department",
                "created_at": "2026-07-06T09:00:00Z",
                "priority": "important",
            }
        ],
        "journey": [
            {
                "id": 21,
                "sequence_no": 1,
                "lesson_number": "L1",
                "lesson_topic": "Number",
                "status": "assessed",
                "session_datetime": "2026-07-07T09:00:00Z",
                "deadline_date": "2026-07-07",
                "evaluator_name": "Academic Director",
                "specification_points": "1.1",
                "book_pages": "12-14",
            }
        ],
        "lesson_reports": [
            {
                "id": 31,
                "lesson_assignment_id": 21,
                "lesson_number": "L1",
                "lesson_topic": "Number",
                "evaluator_name": "Academic Director",
                "assessment_datetime": "2026-07-07T10:00:00Z",
                "session_type": "training_simulation",
                "weighted_overall_score": 8.7,
                "decision": "passed",
                "strengths": "Clear instructions.",
                "areas_for_improvement": "Tighter timing.",
                "final_recommendation": "Proceed to the next academy lesson.",
                "scores": {
                    "teacher_guidance_compliance_score": 9,
                    "timing_adherence_score": 8,
                },
            }
        ],
        "training_timetable": [
            {
                "id": 21,
                "sequence_no": 1,
                "lesson_number": "L1",
                "lesson_topic": "Number",
                "status": "assigned",
                "session_datetime": "2026-07-07T09:00:00Z",
                "deadline_date": "2026-07-07",
                "evaluator_name": "Academic Director",
                "specification_points": "1.1",
                "book_pages": "12-14",
            }
        ],
    }


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _SubjectConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        return _Rows([{"id": 1, "name": "Mathematics"}])


def _minimal_admin_page_context():
    return {
        "panel": "teachers",
        "school_filter": "all",
        "sync_errors": [],
        "load_error": "",
        "admin_students": [],
        "admin_teachers": [],
        "admin_teacher_candidates": [],
        "admin_teacher_academy": [_academy_workspace()["academy"]],
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


def _patch_admin_page_context(monkeypatch):
    import backend.roles.admin.routes.admin_page as admin_page
    import backend.pages.academic_director as academic_director_routes

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
    monkeypatch.setattr(admin_page, "list_announcements", lambda: [])
    monkeypatch.setattr(academic_director_routes, "list_teacher_academy_page_context", fake_teacher_academy_page_context)


def test_academy_teacher_source_limits_tabs_to_required_set():
    source = _teacher_home_source()

    academy_tabs_block = source.split("const academyTabs", 1)[1].split("];", 1)[0]
    assert 'label: "Overview"' in academy_tabs_block
    assert 'label: "Lessons"' in academy_tabs_block
    assert 'label: "Timetable"' in academy_tabs_block
    assert 'label: "Updates"' in academy_tabs_block
    assert "Career Growth" not in academy_tabs_block


def test_active_teacher_source_keeps_normal_workspace_tabs():
    source = _teacher_home_source()

    active_tabs_block = source.split("const activeTeacherTabs", 1)[1].split("];", 1)[0]
    assert 'label: "Home"' in active_tabs_block
    assert 'label: "Lesson Reports"' in active_tabs_block
    assert 'label: "Timetable"' in active_tabs_block
    assert 'label: "Career Growth"' in active_tabs_block
    assert 'label: "Updates"' in active_tabs_block


def test_academy_workspace_cards_show_required_counts():
    cards = build_teacher_workspace_cards(
        teacher_id=42,
        teacher_staff_id=9,
        workspace=_academy_workspace(),
    )

    assert [card["label"] for card in cards] == [
        "Assigned Lessons",
        "Completed/Assessed",
        "Remaining Lessons",
        "Average Score",
    ]
    assert cards[0]["value"] == "12"
    assert cards[1]["value"] == "3"
    assert cards[2]["value"] == "9"
    assert cards[3]["value"] == "8.2"


def test_teacher_route_exposes_academy_overview_lessons_timetable_and_updates(client, monkeypatch):
    import backend.domains.teachers.service as teacher_service
    import backend.pages.teacher as teacher_routes
    import database

    monkeypatch.setattr(teacher_routes, "build_teacher_workspace", lambda teacher_id, staff_id=None: _academy_workspace())
    monkeypatch.setattr(teacher_service, "get_teacher_by_id", lambda teacher_id: {"assigned_group": ""})
    monkeypatch.setattr(database, "connect_auth_db", lambda: _SubjectConnection())
    _set_session(
        client,
        {
            "auth_role": "teacher",
            "auth_login": "TCH0004",
            "teacher_id": 42,
            "teacher_staff_id": 9,
        },
    )

    response = client.get("/teacher")

    assert response.status_code == 200
    assert 'data-react-page="teacher-home"' in response.text
    assert "Assigned Lessons" in response.text
    assert "Completed/Assessed" in response.text
    assert "Remaining Lessons" in response.text
    assert "Average Score" in response.text
    assert "3 assessed lessons; latest 8.7/10." in response.text
    assert "Proceed to the next academy lesson." in response.text
    assert "Academic Department" in response.text
    assert "2026-07-07T09:00:00Z" in response.text


def test_academy_teacher_page_source_shows_report_timetable_and_update_fallbacks():
    source = _teacher_home_source()

    assert "Written report from Academic Department" in source
    assert "Strengths" in source
    assert "Areas for improvement" in source
    assert "Final recommendation" in source
    assert "Start time" in source
    assert "End time" in source
    assert "Evaluator / Academic Director" in source
    assert "No academy updates yet" in source


def test_academic_director_can_access_academy_management_route(client, monkeypatch):
    _patch_admin_page_context(monkeypatch)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "ad@test"})

    response = client.get("/academic-director/teacher-academy")

    assert response.status_code == 200
    assert 'data-react-page="academic-director-academy"' in response.text
    assert "academic_director" in response.text
    assert "adminTeacherAcademy" in response.text
    assert 'data-react-page="admin-home"' not in response.text


def test_academic_director_can_create_academy_teacher_through_api_v1(client, monkeypatch):
    import backend.api.v1.teacher_academy.responses as academy_api

    calls = []
    monkeypatch.setattr(
        academy_api,
        "create_academy_teacher",
        lambda **kwargs: calls.append(kwargs) or (True, "", {"login": "TCH0004"}),
    )
    monkeypatch.setattr(academy_api, "list_academy_teachers", lambda: [_academy_workspace()["academy"]])
    monkeypatch.setattr(academy_api, "list_teachers", lambda: [])
    monkeypatch.setattr(academy_api, "filter_academy_teachers_for_user", lambda rows, user: list(rows))
    monkeypatch.setattr(academy_api, "invalidate_admin_page_context_cache", lambda: None)
    _set_session(client, {"auth_role": "academic_director", "auth_login": "ad@test"})

    response = client.post(
        "/api/v1/academic-director/teacher-academy",
        data={
            "academy_full_name": "Example Teacher",
            "academy_subject_program_id": "5",
            "academy_curriculum_item_ids": "101,102",
            "academy_start_date": "2026-07-06",
        },
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert calls
    assert calls[0]["full_name"] == "Example Teacher"
    assert calls[0]["selected_curriculum_item_ids"] == ["101", "102"]


def test_next_teacher_code_uses_four_digit_tch_format():
    from database.queries.teacher_queries import get_next_teacher_code

    class _OneRow:
        def fetchone(self):
            return {"max_num": 3}

    class _Conn:
        def execute(self, sql, params=None):
            return _OneRow()

    assert get_next_teacher_code(_Conn()) == "TCH0004"


def test_notification_does_not_crash_without_telegram_link(monkeypatch):
    monkeypatch.delenv("TEACHER_ACADEMY_CHANNEL_CHAT_ID", raising=False)

    result = notify_academy_teacher_event(
        academy_teacher={"full_name": "Example Teacher"},
        event_type="assessment_added",
        title="Assessment report added",
        body="Report is ready.",
    )

    assert result["ok"] is True
    assert result["in_app_available"] is True
    assert result["telegram_sent"] is False
    assert result["reason"] == "telegram_link_missing"


def test_notification_posts_new_teacher_to_subject_channel(monkeypatch):
    from backend.domains.teacher_academy import notifications

    sent_messages = []
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("TEACHER_ACADEMY_CHANNEL_CHAT_ID", "-100-general")
    monkeypatch.setenv("TEACHER_ACADEMY_MATHEMATICS_CHAT_ID", "-100-math")
    monkeypatch.setattr(
        notifications,
        "_send_telegram_message",
        lambda chat_id, text: sent_messages.append((str(chat_id), text)) or (True, ""),
    )

    result = notifications.notify_academy_teacher_event(
        academy_teacher={"full_name": "Example Teacher", "subject": "Mathematics"},
        event_type="teacher_created",
        title="Welcome to MSI School",
        body="Welcome to the MSI School family.",
        lessons_count=2,
    )

    assert result["ok"] is True
    assert result["telegram_sent"] is True
    assert result["channel_sent"] is True
    assert result["teacher_sent"] is False
    assert sent_messages[0][0] == "-100-math"
    assert "Example Teacher" in sent_messages[0][1]
    assert "welcome to the MSI School family" in sent_messages[0][1]
    assert "Assigned lessons" not in sent_messages[0][1]
    assert "academy lessons" not in sent_messages[0][1]


def test_notification_sends_direct_message_to_linked_teacher(monkeypatch):
    from backend.domains.teacher_academy import notifications

    sent_messages = []
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.delenv("TEACHER_ACADEMY_CHANNEL_CHAT_ID", raising=False)
    monkeypatch.setattr(
        notifications,
        "_send_telegram_message",
        lambda chat_id, text: sent_messages.append((str(chat_id), text)) or (True, ""),
    )

    result = notifications.notify_academy_teacher_event(
        academy_teacher={
            "full_name": "Example Teacher",
            "telegram_user_id": 901234,
        },
        assignment={"lesson_number": "L1", "lesson_topic": "Numbers"},
        event_type="lesson_assigned",
        title="Academy lesson assigned",
        body="A Teacher Academy lesson has been updated.",
    )

    assert result["telegram_sent"] is True
    assert result["teacher_sent"] is True
    assert sent_messages[0][0] == "901234"
    assert "L1: Numbers" in sent_messages[0][1]


def test_new_teacher_direct_message_is_greeting_only(monkeypatch):
    from backend.domains.teacher_academy import notifications

    sent_messages = []
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.delenv("TEACHER_ACADEMY_CHANNEL_CHAT_ID", raising=False)
    monkeypatch.setattr(
        notifications,
        "_send_telegram_message",
        lambda chat_id, text: sent_messages.append((str(chat_id), text)) or (True, ""),
    )

    result = notifications.notify_academy_teacher_event(
        academy_teacher={
            "full_name": "Example Teacher",
            "subject": "Mathematics",
            "telegram_user_id": 901234,
        },
        event_type="teacher_created",
        title="Welcome to MSI School",
        body="Welcome to the MSI School family.",
        lessons_count=12,
    )

    assert result["teacher_sent"] is True
    assert sent_messages[0][0] == "901234"
    assert "welcome to the MSI School family" in sent_messages[0][1]
    assert "Assigned lessons" not in sent_messages[0][1]
    assert "assigned lesson" not in sent_messages[0][1]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/teacher"),
        ("GET", "/admin"),
        ("GET", "/parent"),
        ("GET", "/student"),
        ("GET", "/dashboard/{student_id}"),
        ("POST", "/api/v1/academic-director/teacher-academy"),
        ("POST", "/api/v1/academic-director/teacher-academy/assignments/{assignment_id}"),
        ("POST", "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments"),
        ("POST", "/api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments/{assessment_id}/delete"),
        ("POST", "/api/v1/head-of-department/teacher-academy/assignments/{assignment_id}"),
        ("POST", "/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments"),
        ("POST", "/api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments/{assessment_id}/delete"),
        ("GET", "/academic-director/teacher-academy"),
    ],
)
def test_academy_critical_routes_remain_registered(app, method, path):
    routes = _route_methods(app)

    assert path in routes
    assert method in routes[path]


def test_old_admin_teacher_academy_action_routes_are_removed(app):
    routes = _route_methods(app)

    for path in [
        "/admin/teacher-academy",
        "/admin/teacher-academy/assignments/{assignment_id}",
        "/admin/teacher-academy/{academy_teacher_id}/assessments",
        "/admin/teacher-academy/{academy_teacher_id}/status",
        "/admin/teacher-academy/{academy_teacher_id}/promote",
        "/admin/teacher-academy/{academy_teacher_id}/delete",
        "/academic-director/api/teacher-academy",
        "/academic-director/api/teacher-academy/assignments/{assignment_id}",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/assessments",
        "/academic-director/api/teacher-academy/{academy_teacher_id}/status",
        "/head-of-department/api/teacher-academy/assignments/{assignment_id}",
        "/head-of-department/api/teacher-academy/{academy_teacher_id}/assessments",
        "/head-of-department/api/teacher-academy/{academy_teacher_id}/status",
    ]:
        assert path not in routes
