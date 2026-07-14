"""Contracts for the clean Teacher Recruitment MVP (not the deleted legacy pipeline)."""

import json
import os
from base64 import b64encode
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner
from pydantic import ValidationError

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository, service
from backend.modules.hr.recruitment.constants import ALL_STAGES, PRIMARY_STAGES, REJECTION_REASONS
from backend.modules.hr.recruitment.schemas import CandidateCreate, DemoLessonWrite, SubjectTestWrite


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _signed_session(data):
    secret = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip() or "dev-only-insecure-key-do-not-use-in-prod"
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    return TimestampSigner(secret).sign(encoded).decode("utf-8")


def _set_session(client, role, **extra):
    client.cookies.set(
        "session",
        _signed_session({"auth_role": role, "auth_login": f"{role}@test", **extra}),
    )


def _user(role="hr_manager"):
    return CurrentUser(login=f"{role}@test", role=role, account_id=10, staff_id=20)


def test_stage_and_rejection_taxonomies_are_stable():
    assert PRIMARY_STAGES == (
        "new_candidate",
        "job_interview",
        "test_and_demo",
        "under_review",
        "teacher_academy",
        "active_teacher",
    )
    assert ALL_STAGES == {*PRIMARY_STAGES, "rejected", "on_hold", "candidate_withdrew"}
    assert "other" in REJECTION_REASONS
    assert "missing_or_invalid_documents" in REJECTION_REASONS


def test_minimal_candidate_and_blank_optional_values_validate():
    candidate = CandidateCreate.model_validate({"full_name": "  Ada Teacher  ", "application_date": ""})
    assert candidate.full_name == "Ada Teacher"
    assert candidate.application_date is None

    test = SubjectTestWrite.model_validate(
        {"result": "not_completed", "score": "", "maximum_score": ""}
    )
    assert test.score is None
    assert test.maximum_score is None


def test_demo_score_is_restricted_to_zero_through_ten():
    assert DemoLessonWrite.model_validate({"result": "passed", "score": 10}).score == 10
    with pytest.raises(ValidationError):
        DemoLessonWrite.model_validate({"result": "passed", "score": 10.01})


def test_overdue_task_status_is_derived_and_not_stored():
    payload = service._task_payload(
        {
            "id": 1,
            "status": "pending",
            "due_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        }
    )
    assert payload["status"] == "pending"
    assert payload["effective_status"] == "overdue"


def test_hod_summary_visibility_fails_closed_without_subject_scope():
    assert repository._visibility_clause(10, set()) == ("FALSE", [])
    sql, params = repository._visibility_clause(10, {7, 3})
    assert "visibility.subject_id = ANY" in sql
    assert params == [10, [3, 7]]


def test_protected_stage_and_decision_rules_fail_before_persistence():
    with pytest.raises(service.RecruitmentError, match="final decision"):
        service.move_candidate(
            _user(), 1, stage="active_teacher", expected_version=1
        )
    with pytest.raises(service.RecruitmentError, match="Only Admin or CEO"):
        service.make_final_decision(
            _user(), 1, {"decision": "active_teacher", "approval_id": 1}
        )
    with pytest.raises(service.RecruitmentError, match="Explain"):
        service.make_final_decision(
            _user("admin"),
            1,
            {"decision": "rejected", "rejection_reason": "other", "reason_detail": ""},
        )
    with pytest.raises(service.RecruitmentError, match="comment is required"):
        service.review_approval(
            _user("academic_director"),
            1,
            1,
            status="returned",
            review_comment="",
        )


def test_recruitment_api_is_role_scoped_and_hr_pipeline_is_available(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "list_pipeline",
        lambda user: {"stages": {}, "counts": {}, "total": 0, "role": user.role},
    )
    _set_session(client, "hr_manager", account_id=10, staff_id=20)
    allowed = client.get("/api/v1/recruitment/pipeline", headers=XHR)
    assert allowed.status_code == 200
    assert allowed.json()["data"]["role"] == "hr_manager"

    _set_session(client, "student", account_id=11)
    denied = client.get("/api/v1/recruitment/pipeline", headers=XHR)
    assert denied.status_code == 403


def test_hr_page_renders_new_shared_workspace_without_legacy_pipeline(client):
    _set_session(client, "hr_manager", account_id=10, staff_id=20)
    response = client.get("/hr-manager")
    assert response.status_code == 200
    assert '"page":"recruitment-workspace"' in response.text
    assert "Lesson Practice" not in response.text


def test_migration_preserves_candidates_and_normalizes_history():
    source = Path("database/alembic/versions/0013_teacher_recruitment_mvp.py").read_text()
    for mapping in (
        "WHEN 'new' THEN 'new_candidate'",
        "WHEN 'interview' THEN 'job_interview'",
        "WHEN 'math_test' THEN 'test_and_demo'",
        "WHEN 'training_passed' THEN 'under_review'",
        "WHEN 'hired' THEN 'active_teacher'",
    ):
        assert mapping in source
    for table in (
        "teacher_candidate_documents",
        "teacher_candidate_interviews",
        "teacher_candidate_subject_tests",
        "teacher_candidate_demo_lessons",
        "teacher_candidate_assignments",
        "teacher_candidate_tasks",
        "teacher_candidate_notes",
        "teacher_candidate_hire_approvals",
        "teacher_candidate_final_decisions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS msi_v2.{table}" in source
    upgrade_source = source.split("def downgrade", 1)[0]
    assert "DROP TABLE IF EXISTS msi_v2.teacher_candidates" not in upgrade_source
    assert "candidate.legacy_event" in upgrade_source


def test_recruitment_document_urls_never_use_public_resource_url():
    source = Path("backend/platform/storage/r2.py").read_text()
    private_function = source.split("def build_private_candidate_document_url", 1)[1]
    private_function = private_function.split("\ndef ", 1)[0]
    assert "generate_presigned_url" in private_function
    assert "public_base_url" not in private_function


def test_deleted_legacy_candidate_endpoints_and_lesson_practice_stay_absent(app):
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/admin/teacher-candidates" not in paths
    assert not Path("frontend/src/features/teacher-academy/TrainingEvaluationModal.tsx").exists()
    assert not Path("frontend/src/features/hr/recruitment/PromoteModal.tsx").exists()
