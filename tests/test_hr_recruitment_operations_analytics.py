"""Focused contracts for stage SLA, progress, and the essential analytics surface."""

import json
import os
from base64 import b64encode
from datetime import UTC, datetime, timedelta
from pathlib import Path

from itsdangerous import TimestampSigner

from backend.modules.hr.analytics import service as analytics_service
from backend.modules.hr.recruitment import service
from backend.modules.hr.recruitment.schemas import DemoLessonWrite, InterviewWrite, SubjectTestWrite


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _session(role: str) -> str:
    secret = os.environ.get("APP_SECRET_KEY", "").strip() or "dev-only-insecure-key-do-not-use-in-prod"
    encoded = b64encode(json.dumps({"auth_role": role, "auth_login": f"{role}@test", "account_id": 9}).encode())
    return TimestampSigner(secret).sign(encoded).decode()


def test_sla_boundaries_and_inactive_stages():
    entered = datetime(2026, 7, 1, tzinfo=UTC)
    candidate = {
        "status": "new_candidate",
        "current_stage_entered_at": entered.isoformat(),
        "current_sla_due_at": (entered + timedelta(days=1)).isoformat(),
        "current_sla_target_days": 1,
    }
    assert service._sla_payload(candidate, now=entered + timedelta(hours=17))["status"] == "green"
    assert service._sla_payload(candidate, now=entered + timedelta(hours=18))["status"] == "yellow"
    assert service._sla_payload(candidate, now=entered + timedelta(days=1, seconds=1))["status"] == "red"
    assert service._sla_payload({**candidate, "status": "candidate_withdrew"}, now=entered) is None


def test_progress_and_required_documents_are_derived_without_blocking():
    progress, documents = service._candidate_progress(
        candidate={"status": "under_review", "final_decision": ""},
        stage_history=[{"stage": "responded"}, {"stage": "under_review"}],
        documents=[{"document_type": "cv"}, {"document_type": "id_passport"}],
        interviews=[{"result": "passed"}],
        subject_tests=[{"result": "passed"}],
        demos=[{"result": "passed"}],
    )
    assert [item["key"] for item in progress] == ["contacted", "interview", "subject_test", "demo", "documents", "review", "decision"]
    assert documents["required_uploaded"] == 2
    assert documents["missing_required_types"] == ["diploma"]
    assert next(item for item in progress if item["key"] == "documents")["status"] == "current"


def test_structured_evaluation_contracts_validate_scores():
    interview = InterviewWrite.model_validate({"result": "passed", "cefr_level": "C1", "overall_score": 8.5, "communication_score": 9})
    assert interview.cefr_level == "C1"
    subject_test = SubjectTestWrite.model_validate({"result": "passed", "paper": "Math 2", "topic_scores": [{"topic": "Algebra", "score": 18, "maximum_score": 20}]})
    assert subject_test.topic_scores[0].topic == "Algebra"
    demo = DemoLessonWrite.model_validate({"result": "passed", "criteria_scores": [{"criterion": "Clarity", "score": 8}]})
    assert demo.criteria_scores[0].maximum_score == 10


def test_hr_and_ceo_can_read_analytics_but_ad_cannot(client, monkeypatch):
    monkeypatch.setattr(analytics_service, "options", lambda user: {"role": user.role})
    monkeypatch.setattr(analytics_service, "dashboard", lambda user, **filters: {"role": user.role, "filters": filters})
    for role in ("hr_manager", "ceo"):
        client.cookies.set("session", _session(role))
        assert client.get("/api/v1/hr/analytics/options", headers=XHR).status_code == 200
        assert client.get("/api/v1/hr/analytics/dashboard", headers=XHR).json()["data"]["role"] == role
    client.cookies.set("session", _session("academic_director"))
    assert client.get("/api/v1/hr/analytics/dashboard", headers=XHR).status_code == 403


def test_migration_contains_append_only_history_and_snapshotted_sla():
    source = Path("database/alembic/versions/0022_hr_recruitment_operations_analytics.py").read_text()
    assert "teacher_candidate_stage_history" in source
    assert "idx_teacher_candidate_stage_history_open" in source
    assert "sla_target_days" in source and "sla_due_at" in source
    assert "teacher_candidate_subject_test_topics" in source
    assert "teacher_candidate_demo_criteria" in source


def test_on_hold_removal_migration_restores_candidates_and_tightens_stage_constraint():
    source = Path("database/alembic/versions/0023_remove_recruitment_on_hold.py").read_text()
    assert "recruitment_on_hold_restore" in source
    assert "hold.origin_stage" in source
    assert "ELSE 'responded'" in source
    assert "candidate.stage_restored_after_on_hold_removal" in source
    active_constraint = source.split("def downgrade", 1)[0].split("teacher_candidates_stage_check", 1)[1]
    assert "'on_hold'" not in active_constraint
