"""Focused contracts for stage SLA, progress, and the essential analytics surface."""

import json
import os
from base64 import b64encode
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner

from backend.core.access import CurrentUser
from backend.modules.hr.analytics import repository as analytics_repository
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


def test_subject_test_title_is_derived_from_candidate_subject():
    assert service._subject_test_paper_title(
        {"subject": "Math", "applied_position": "Math Teacher"}
    ) == "IGCSE Math Paper Test"
    assert service._subject_test_paper_title(
        {"subject": "", "applied_position": "English Teacher"}
    ) == "IGCSE English Paper Test"


def test_hr_and_ceo_can_read_analytics_but_ad_cannot(client, monkeypatch):
    monkeypatch.setattr(analytics_service, "options", lambda user: {"role": user.role})
    monkeypatch.setattr(analytics_service, "dashboard", lambda user, **filters: {"role": user.role, "filters": filters})
    for role in ("hr_manager", "ceo"):
        client.cookies.set("session", _session(role))
        assert client.get("/api/v1/hr/analytics/options", headers=XHR).status_code == 200
        assert client.get("/api/v1/hr/analytics/dashboard", headers=XHR).json()["data"]["role"] == role
    client.cookies.set("session", _session("academic_director"))
    assert client.get("/api/v1/hr/analytics/dashboard", headers=XHR).status_code == 403


def test_analytics_calendar_periods_use_tashkent_boundaries():
    today = datetime(2026, 7, 17).date()
    assert analytics_service._period_bounds(
        today=today, period="month", date_from="", date_to=""
    ) == (
        datetime(2026, 7, 1).date(),
        datetime(2026, 7, 17).date(),
        datetime(2026, 6, 1).date(),
        datetime(2026, 6, 17).date(),
        "month",
    )
    assert analytics_service._period_bounds(
        today=today, period="custom", date_from="2026-07-10", date_to="2026-07-17"
    ) == (
        datetime(2026, 7, 10).date(),
        datetime(2026, 7, 17).date(),
        datetime(2026, 7, 2).date(),
        datetime(2026, 7, 9).date(),
        "custom",
    )
    with pytest.raises(analytics_service.HrAnalyticsError, match="cannot be in the future"):
        analytics_service._period_bounds(
            today=today,
            period="custom",
            date_from="2026-07-10",
            date_to="2026-07-18",
        )


def test_analytics_contract_keeps_academy_separate_and_deduplicated(monkeypatch):
    @contextmanager
    def fake_connection():
        yield object()

    rows = {
        "current_summary": {
            "applications": 10,
            "shortlisted": 6,
            "hired": 2,
            "rejected": 3,
            "academy_accepted": 1,
            "withdrawn": 1,
            "active_candidates": 4,
            "average_time_to_hire_days": 12.5,
            "overall_conversion_percentage": 20,
            "cohort_sla_breaches": 2,
        },
        "comparison_summary": {
            "applications": 5,
            "shortlisted": 4,
            "hired": 1,
            "rejected": 1,
        },
        "live_summary": {
            "active_candidates": 304,
            "sla_overdue_now": 294,
        },
        "journey": [
            {"stage": "new_candidate", "candidates": 10},
            {"stage": "under_review", "candidates": 6},
        ],
        "outcomes": [
            {"outcome": "teacher_academy", "candidates": 1},
            {"outcome": "active_teacher", "candidates": 2},
            {"outcome": "rejected", "candidates": 3},
        ],
        "activity_trend": [],
        "position_distribution": [],
        "source_quality": [],
        "time_in_stage": [],
        "overdue_actions": [],
        "upcoming_appointments": [],
        "recent_candidates": [],
        "recent_activity": [],
    }
    monkeypatch.setattr(analytics_service, "connect_auth_db", fake_connection)
    monkeypatch.setattr(
        analytics_service.repository,
        "dashboard_rows",
        lambda _conn, **_kwargs: rows,
    )
    result = analytics_service.dashboard(
        CurrentUser(login="HR0001", role="hr_manager"),
        period="custom",
        date_from="2026-07-01",
        date_to="2026-07-20",
    )
    assert result["summary_cards"]["applications"]["delta_percentage"] == 100.0
    assert result["summary_cards"]["hired"]["value"] == 2
    assert result["secondary_kpis"]["academy_accepted"] == 1
    assert result["secondary_kpis"]["overall_conversion_percentage"] == 20
    assert result["secondary_kpis"]["active_candidates"] == 304
    assert result["secondary_kpis"]["sla_overdue_now"] == 294
    assert result["secondary_kpis"]["cohort_sla_breaches"] == 2
    assert result["outcomes"] == [
        {"outcome": "teacher_academy", "candidates": 1},
        {"outcome": "active_teacher", "candidates": 2},
        {"outcome": "rejected", "candidates": 3},
        {"outcome": "candidate_withdrew", "candidates": 0},
    ]


def test_analytics_rejects_invalid_dependent_subsource(monkeypatch):
    @contextmanager
    def fake_connection():
        yield object()

    monkeypatch.setattr(analytics_service, "connect_auth_db", fake_connection)
    monkeypatch.setattr(
        analytics_service.repository,
        "subsource_matches_source",
        lambda _conn, **_kwargs: False,
    )
    with pytest.raises(
        analytics_service.HrAnalyticsError,
        match="does not belong to the selected source",
    ):
        analytics_service.dashboard(
            CurrentUser(login="HR0001", role="hr_manager"),
            period="custom",
            date_from="2026-07-01",
            date_to="2026-07-20",
            source="10",
            subsource="20",
        )


def test_analytics_trend_fills_empty_buckets_and_zero_comparison_is_safe():
    trend = analytics_service._trend(
        [{"bucket": "2026-07-02", "event_type": "applications", "candidates": 3}],
        start=datetime(2026, 7, 1).date(),
        end=datetime(2026, 7, 3).date(),
        bucket="day",
    )
    assert [item["applications"] for item in trend] == [0, 3, 0]
    assert analytics_service._comparison_metric(4, 0) == {
        "value": 4,
        "previous": 0,
        "delta_percentage": None,
    }


def test_analytics_repository_queries_bind_every_placeholder():
    executed_queries = []

    class Cursor:
        def fetchone(self):
            return {}

        def fetchall(self):
            return []

    class Connection:
        def execute(self, query, params=()):
            assert query.count("%s") == len(params), query
            executed_queries.append(query)
            return Cursor()

    result = analytics_repository.dashboard_rows(
        Connection(),
        date_from="2026-07-01",
        date_to="2026-07-31",
        comparison_from="2026-06-01",
        comparison_to="2026-06-30",
        bucket="day",
        now="2026-07-17T10:00:00+00:00",
        source="1",
        subsource="2",
        position="3",
        subject_id=4,
        responsible_account_id=5,
    )
    assert result["journey"] == []
    assert result["recent_activity"] == []
    trend_query = next(query for query in executed_queries if "WITH filtered_candidates AS" in query)
    assert "GROUP BY 1, 2" in trend_query
    assert "GROUP BY date_trunc" not in trend_query
    all_queries = "\n".join(executed_queries)
    assert "msi_v2.academy_teachers" in all_queries
    assert "msi_v2.teachers" in all_queries
    assert "academy_status NOT IN ('rejected', 'removed')" in all_queries
    assert "candidate.status = ANY" in all_queries


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


def test_standardized_option_and_interview_session_migrations_are_chained_and_deduplicated():
    options = Path("database/alembic/versions/0024_recruitment_standardized_options.py").read_text()
    sessions = Path("database/alembic/versions/0025_recruitment_interview_sessions.py").read_text()
    assert 'down_revision = "0023_remove_on_hold"' in options
    assert "source_option_id" in options and "subsource_option_id" in options
    assert "validate_candidate_recruitment_options" in options
    assert "Recruitment option identity is immutable" in options
    assert "backfill_candidate_text_option" in options
    assert 'down_revision = "0024_recruitment_options"' in sessions
    assert "started_at" in sessions and "in_progress" in sessions
    assert "idx_teacher_candidate_appointments_active_type" in sessions
    assert "idx_teacher_candidate_hire_approvals_one_actionable" in sessions


def test_position_migration_seeds_canonical_values_and_rewrites_candidates_safely():
    positions = Path("database/alembic/versions/0026_recruitment_positions.py").read_text()
    assert 'down_revision = "0025_interview_sessions"' in positions
    assert "position_option_id" in positions
    assert "validate_candidate_recruitment_options" in positions
    for label in (
        "IGCSE Math Teacher",
        "IGCSE Chemistry Teacher",
        "IGCSE Physics Teacher",
        "IGCSE Biology Teacher",
        "IGCSE ESL Teacher",
    ):
        assert label in positions
    assert "SET position_option_id = setting.id" in positions
    assert "candidate.position_standardized" in positions
    assert "DELETE FROM msi_v2.teacher_candidates" not in positions
