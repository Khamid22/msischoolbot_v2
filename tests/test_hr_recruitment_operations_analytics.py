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
from backend.modules.hr.recruitment.constants import DEMO_CRITERIA
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
    demo = DemoLessonWrite.model_validate(
        {
            "result": "passed",
            "criteria_scores": [
                {"criterion": criterion, "score": 8}
                for criterion in DEMO_CRITERIA
            ],
        }
    )
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
        "total_summary": {
            "applications": 20,
            "shortlisted": 8,
            "hired": 3,
            "rejected": 4,
            "withdrawn": 2,
        },
        "event_summary": {
            "applications": 10,
            "final_decision": 6,
            "teacher_academy": 1,
            "active_teachers": 2,
            "rejected": 3,
            "withdrawn": 1,
            "interview_total": 2,
            "interview_unique_candidates": 2,
            "interview_passed": 1,
            "interview_failed": 1,
            "demo_total": 4,
            "demo_unique_candidates": 3,
            "demo_passed": 2,
            "demo_failed": 1,
            "subject_test_total": 6,
            "subject_test_unique_candidates": 5,
            "subject_test_passed": 4,
            "subject_test_failed": 1,
        },
        "comparison_event_summary": {
            "applications": 5,
            "final_decision": 4,
            "teacher_academy": 0,
            "active_teachers": 1,
            "rejected": 1,
            "withdrawn": 0,
        },
        "total_event_summary": {
            "applications": 20,
            "final_decision": 8,
            "teacher_academy": 9,
            "active_teachers": 3,
            "rejected": 4,
            "withdrawn": 2,
        },
        "monthly_stage_totals": {
            "application_received": 10,
            "rejected": 3,
            "in_process": 8,
            "job_interview": 6,
            "test_and_demo": 5,
            "teacher_academy": 1,
        },
        "total_stage_totals": {
            "application_received": 20,
            "rejected": 4,
            "in_process": 15,
            "job_interview": 12,
            "test_and_demo": 8,
            "teacher_academy": 9,
        },
        "cohort_scope": {
            "applications_received": 10,
            "included_candidates": 9,
            "excluded_trash_candidates": 1,
        },
        "pipeline_column_counts": [
            {
                "stage": "new_candidate",
                "stage_label": "Application Received",
                "color_token": "neutral",
                "candidates": 4,
            },
            {
                "stage": "responded",
                "stage_label": "In Process",
                "color_token": "blue",
                "candidates": 3,
            },
            {
                "stage": "job_interview",
                "stage_label": "Job Interview",
                "color_token": "green",
                "candidates": 2,
            },
            {
                "stage": "test_and_demo",
                "stage_label": "Test & Demo",
                "color_token": "orange",
                "candidates": 1,
            },
            {
                "stage": "under_review",
                "stage_label": "Final Decision",
                "color_token": "violet",
                "candidates": 0,
            },
        ],
        "outcome_reasons": [
            {
                "outcome": "rejected",
                "value": "low_english_level",
                "label": "Low English Level",
                "candidates": 2,
            },
            {
                "outcome": "rejected",
                "value": "poor_soft_skills",
                "label": "Poor Soft Skills",
                "candidates": 1,
            },
            {
                "outcome": "candidate_withdrew",
                "value": "personal_reasons",
                "label": "Personal Reasons",
                "candidates": 1,
            },
        ],
        "total_outcome_reasons": [
            {
                "outcome": "rejected",
                "value": "low_english_level",
                "label": "Low English Level",
                "candidates": 3,
            },
            {
                "outcome": "rejected",
                "value": "poor_soft_skills",
                "label": "Poor Soft Skills",
                "candidates": 1,
            },
            {
                "outcome": "candidate_withdrew",
                "value": "personal_reasons",
                "label": "Personal Reasons",
                "candidates": 2,
            },
        ],
        "turnover": [
            {
                "bucket": "2026-07-01",
                "departures": 1,
                "starting_headcount": 9,
                "ending_headcount": 11,
                "average_headcount": 10,
                "turnover_rate": 10,
            }
        ],
        "applications_received_trend": [
            {
                "bucket": "2026-06-01",
                "applications_received": 7,
            },
            {
                "bucket": "2026-07-01",
                "applications_received": 10,
            },
        ],
        "live_summary": {
            "active_candidates": 304,
            "sla_overdue_now": 294,
            "academy_roster_total": 9,
            "active_teacher_roster_total": 3,
        },
        "journey": [
            {"stage": "new_candidate", "candidates": 9},
            {"stage": "responded", "candidates": 8},
            {"stage": "job_interview", "candidates": 6},
            {"stage": "test_and_demo", "candidates": 5},
            {"stage": "under_review", "candidates": 4},
        ],
        "outcomes": [
            {"outcome": "teacher_academy", "candidates": 1},
            {"outcome": "active_teacher", "candidates": 2},
            {"outcome": "rejected", "candidates": 3},
        ],
        "activity_trend": [],
        "position_distribution": [],
        "source_quality": [
            {
                "source": "University",
                "subsource": "Turin University",
                "candidates": 4,
                "shortlisted": 2,
                "hired": 1,
            }
        ],
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
    assert result["summary_cards"]["applications"]["total"] == 20
    assert result["summary_cards"]["final_decision"]["value"] == 6
    assert result["summary_cards"]["teacher_academy"]["value"] == 1
    assert result["summary_cards"]["active_teachers"]["value"] == 2
    assert result["evaluation_kpis"]["interview"] == {
        "total": 2,
        "unique_candidates": 2,
        "passed": 1,
        "failed": 1,
        "pass_rate": 50.0,
    }
    assert result["evaluation_kpis"]["demo"] == {
        "total": 4,
        "unique_candidates": 3,
        "passed": 2,
        "failed": 1,
        "pass_rate": 66.7,
    }
    assert result["secondary_kpis"]["academy_accepted"] == 1
    assert result["secondary_kpis"]["academy_total"] == 9
    assert result["secondary_kpis"]["active_teacher_total"] == 3
    assert result["secondary_kpis"]["withdrawn_total"] == 2
    assert result["secondary_kpis"]["overall_conversion_percentage"] == 20
    assert result["secondary_kpis"]["active_candidates"] == 304
    assert result["secondary_kpis"]["sla_overdue_now"] == 294
    assert result["secondary_kpis"]["cohort_sla_breaches"] == 2
    assert result["monthly_stage_totals"] == {
        "application_received": 10,
        "rejected": 3,
        "in_process": 8,
        "job_interview": 6,
        "test_and_demo": 5,
        "teacher_academy": 1,
    }
    assert result["monthly_activity"] == {
        "applications_received": 10,
        "entered_process": 8,
        "interviews_conducted": 6,
        "tests_and_demos_conducted": 5,
        "academy_admissions": 1,
    }
    assert result["monthly_outcomes"] == {
        "rejected": 3,
        "candidate_withdrew": 1,
    }
    assert result["cohort_scope"] == {
        "applications_received": 10,
        "included_candidates": 9,
        "excluded_trash_candidates": 1,
    }
    assert result["total_overview"] == {
        "applications_received": 20,
        "rejected": 4,
        "processed": 15,
        "job_interviews": 12,
        "tests_and_demos": 8,
        "teacher_academy": 9,
    }
    assert result["total_outcomes"] == {
        "rejected": 4,
        "candidate_withdrew": 2,
    }
    assert result["monthly_pipeline"] == [
        {
            "stage": "new_candidate",
            "stage_label": "Application Received",
            "color_token": "neutral",
            "candidates": 4,
        },
        {
            "stage": "responded",
            "stage_label": "In Process",
            "color_token": "blue",
            "candidates": 3,
        },
        {
            "stage": "job_interview",
            "stage_label": "Job Interview",
            "color_token": "green",
            "candidates": 2,
        },
        {
            "stage": "test_and_demo",
            "stage_label": "Test & Demo",
            "color_token": "orange",
            "candidates": 1,
        },
        {
            "stage": "under_review",
            "stage_label": "Final Decision",
            "color_token": "violet",
            "candidates": 0,
        },
    ]
    assert result["turnover"]["population"] == "recruited_active_teachers"
    assert result["turnover"]["monthly"] == [
        {
            "bucket": "2026-07-01",
            "departures": 1,
            "starting_headcount": 9,
            "ending_headcount": 11,
            "average_headcount": 10.0,
            "turnover_rate": 10.0,
        }
    ]
    assert result["applications_received_trend"] == {
        "from": "2026-06-01",
        "to": "2026-07-01",
        "monthly": [
            {
                "bucket": "2026-06-01",
                "applications_received": 7,
            },
            {
                "bucket": "2026-07-01",
                "applications_received": 10,
            },
        ],
    }
    assert result["outcome_reason_breakdown"]["rejected"] == {
        "total": 3,
        "items": [
            {
                "value": "low_english_level",
                "label": "Low English Level",
                "candidates": 2,
                "percentage": 66.7,
            },
            {
                "value": "poor_soft_skills",
                "label": "Poor Soft Skills",
                "candidates": 1,
                "percentage": 33.3,
            },
        ],
    }
    assert result["total_outcome_reason_breakdown"]["rejected"]["total"] == 4
    assert result["total_outcome_reason_breakdown"]["candidate_withdrew"][
        "total"
    ] == 2
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


def test_analytics_semantics_allow_overlapping_activity_and_outcome_counts():
    analytics_service._ensure_semantic_consistency(
        journey=[
            {"stage": "new_candidate", "candidates": 4},
            {"stage": "responded", "candidates": 4},
            {"stage": "job_interview", "candidates": 3},
            {"stage": "test_and_demo", "candidates": 2},
            {"stage": "under_review", "candidates": 1},
        ],
        monthly_activity={
            "applications_received": 5,
            "entered_process": 5,
            "interviews_conducted": 3,
            "tests_and_demos_conducted": 2,
            "academy_admissions": 1,
        },
        monthly_outcomes={
            "rejected": 2,
            "candidate_withdrew": 1,
        },
        cohort_scope={
            "applications_received": 5,
            "included_candidates": 4,
            "excluded_trash_candidates": 1,
        },
        outcome_reason_breakdown={
            "rejected": {
                "total": 2,
                "items": [
                    {
                        "value": "low_english_level",
                        "candidates": 2,
                    }
                ],
            },
            "candidate_withdrew": {"total": 1, "items": []},
        },
    )


def test_analytics_rejects_non_monotonic_application_cohort():
    with pytest.raises(
        analytics_service.HrAnalyticsError,
        match="funnel counts are not monotonic",
    ) as error:
        analytics_service._ensure_semantic_consistency(
            journey=[
                {"stage": "new_candidate", "candidates": 4},
                {"stage": "responded", "candidates": 3},
                {"stage": "job_interview", "candidates": 4},
                {"stage": "test_and_demo", "candidates": 2},
                {"stage": "under_review", "candidates": 1},
            ],
            monthly_activity={
                "applications_received": 4,
                "entered_process": 3,
                "interviews_conducted": 3,
                "tests_and_demos_conducted": 2,
                "academy_admissions": 1,
            },
            monthly_outcomes={
                "rejected": 1,
                "candidate_withdrew": 0,
            },
            cohort_scope={
                "applications_received": 4,
                "included_candidates": 4,
                "excluded_trash_candidates": 0,
            },
            outcome_reason_breakdown={
                "rejected": {"total": 1, "items": []},
                "candidate_withdrew": {"total": 0, "items": []},
            },
        )
    assert error.value.status_code == 500


def test_analytics_rejects_rejection_reason_total_mismatch():
    with pytest.raises(
        analytics_service.HrAnalyticsError,
        match="Rejected outcome reasons do not match",
    ) as error:
        analytics_service._ensure_semantic_consistency(
            journey=[
                {"stage": "new_candidate", "candidates": 4},
                {"stage": "responded", "candidates": 3},
                {"stage": "job_interview", "candidates": 2},
                {"stage": "test_and_demo", "candidates": 1},
                {"stage": "under_review", "candidates": 1},
            ],
            monthly_activity={
                "applications_received": 4,
                "entered_process": 3,
                "interviews_conducted": 2,
                "tests_and_demos_conducted": 1,
                "academy_admissions": 0,
            },
            monthly_outcomes={
                "rejected": 2,
                "candidate_withdrew": 0,
            },
            cohort_scope={
                "applications_received": 4,
                "included_candidates": 4,
                "excluded_trash_candidates": 0,
            },
            outcome_reason_breakdown={
                "rejected": {"total": 1, "items": []},
                "candidate_withdrew": {"total": 0, "items": []},
            },
        )
    assert error.value.status_code == 500


def test_analytics_repository_queries_bind_every_placeholder():
    executed_queries = []
    executed_calls = []

    class Cursor:
        def fetchone(self):
            return {}

        def fetchall(self):
            return []

    class Connection:
        def execute(self, query, params=()):
            assert query.count("%s") == len(params), query
            executed_queries.append(query)
            executed_calls.append((query, tuple(params)))
            return Cursor()

    result = analytics_repository.dashboard_rows(
        Connection(),
        date_from="2026-07-01",
        date_to="2026-07-31",
        as_of_date="2026-07-17",
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
    trend_query = next(
        query for query in executed_queries if "), first_shortlist AS (" in query
    )
    assert "GROUP BY 1, 2" in trend_query
    assert "GROUP BY date_trunc" not in trend_query
    trend_candidates = trend_query.split("), first_shortlist", 1)[0]
    assert "candidate.application_date BETWEEN" not in trend_candidates
    assert "candidate.status <> 'trash_bin'" not in trend_candidates
    activity_query = next(
        query for query in executed_queries
        if "FROM msi_v2.audit_events audit" in query
    )
    assert "candidate.application_date BETWEEN" not in activity_query
    assert "candidate.status <> 'trash_bin'" not in activity_query
    event_queries = [
        query for query in executed_queries if "ranked_attempts AS" in query
    ]
    assert len(event_queries) == 3
    for query in event_queries:
        base_candidates = query.split("), latest_closure", 1)[0]
        assert "candidate.application_date BETWEEN" not in base_candidates
        assert "candidate.status <> 'trash_bin'" not in base_candidates
    monthly_totals_query = next(
        query for query in executed_queries if "test_demo_participants AS" in query
    )
    monthly_activity_base = monthly_totals_query.split(
        "), latest_decision AS", 1
    )[0]
    assert "candidate.status <>" not in monthly_activity_base
    assert "candidate.status =" not in monthly_activity_base
    assert "COUNT(DISTINCT history.candidate_id)" in monthly_totals_query
    assert "COUNT(DISTINCT interview.candidate_id)" in monthly_totals_query
    assert "COUNT(DISTINCT participant.candidate_id)" in monthly_totals_query
    assert "COUNT(DISTINCT decision.candidate_id)" in monthly_totals_query
    assert "demo.voided_at IS NULL" in monthly_totals_query
    assert "test.voided_at IS NULL" in monthly_totals_query
    assert "interview.voided_at IS NULL" in monthly_totals_query
    assert "decision.voided_at IS NULL" in monthly_totals_query
    assert "history.stage = 'responded'" in monthly_totals_query
    stage_total_calls = [
        params
        for query, params in executed_calls
        if "test_demo_participants AS" in query
    ]
    assert any(params[:2] == ("2026-07-01", "2026-07-31") for params in stage_total_calls)
    assert any(params[:2] == ("1900-01-01", "2999-12-31") for params in stage_total_calls)
    pipeline_columns_query = next(
        query
        for query in executed_queries
        if "COUNT(DISTINCT candidate.id) AS candidates" in query
        and "stage.is_pipeline = true" in query
    )
    assert "candidate.status = stage.stage_key" in pipeline_columns_query
    assert "stage.is_active = true" in pipeline_columns_query
    assert "candidate.application_date BETWEEN" in pipeline_columns_query
    assert "candidate.is_application_received = true" in pipeline_columns_query
    assert "GROUP BY" in pipeline_columns_query
    cohort_scope_query = next(
        query
        for query in executed_queries
        if "AS excluded_trash_candidates" in query
    )
    assert cohort_scope_query.count("COUNT(DISTINCT candidate.id)") == 3
    assert "candidate.status <> 'trash_bin'" in cohort_scope_query
    assert "candidate.status = 'trash_bin'" in cohort_scope_query
    assert "candidate.application_date BETWEEN" in cohort_scope_query
    assert "candidate.is_application_received = true" in cohort_scope_query
    for filter_column in (
        "candidate.source_option_id",
        "candidate.subsource_option_id",
        "candidate.position_option_id",
        "candidate.subject_id",
        "responsible_history.responsible_account_id",
    ):
        assert filter_column in cohort_scope_query
    outcome_reason_query = next(
        query
        for query in executed_queries
        if "COALESCE(classified.reason_value, 'unspecified')" in query
    )
    assert "decision.voided_at IS NULL" in outcome_reason_query
    turnover_query = next(
        query
        for query in executed_queries
        if "FROM msi_v2.teacher_employment_events event" in query
    )
    assert "interval '11 months'" in turnover_query
    assert "average_headcount" in turnover_query
    applications_query = next(
        query
        for query in executed_queries
        if "), monthly_applications AS (" in query
    )
    assert "interval '11 months'" in applications_query
    assert "COUNT(DISTINCT candidate.id) AS applications_received" in applications_query
    assert "candidate.is_application_received = true" in applications_query
    assert "candidate.status <> 'trash_bin'" not in applications_query
    applications_params = next(
        params
        for query, params in executed_calls
        if "), monthly_applications AS (" in query
    )
    assert applications_params[:2] == ("2026-07-17", "2026-07-17")
    for filter_column in (
        "candidate.source_option_id",
        "candidate.subsource_option_id",
        "candidate.position_option_id",
        "candidate.subject_id",
        "responsible_history.responsible_account_id",
    ):
        assert filter_column in applications_query
    all_queries = "\n".join(executed_queries)
    assert "msi_v2.academy_teachers" in all_queries
    assert "msi_v2.teachers" in all_queries
    assert "academy_status NOT IN (" in all_queries
    assert "'rejected', 'removed', 'trash_bin'" in all_queries
    assert "teacher_recruitment_pipeline_stages active_stage" in all_queries
    assert "active_stage.is_pipeline = true" in all_queries


def test_migration_contains_append_only_history_and_snapshotted_sla():
    source = Path("database/alembic/versions/0022_hr_recruitment_operations_analytics.py").read_text()
    assert "teacher_candidate_stage_history" in source
    assert "idx_teacher_candidate_stage_history_open" in source
    assert "sla_target_days" in source and "sla_due_at" in source
    assert "teacher_candidate_subject_test_topics" in source
    assert "teacher_candidate_demo_criteria" in source


def test_teacher_employment_event_migration_backfills_and_tracks_transitions():
    source = Path("database/alembic/versions/0042_teacher_employment_events.py").read_text()
    assert 'revision = "0042_teacher_employment_events"' in source
    assert 'down_revision = "0041_consolidate_reasons"' in source
    assert "teacher_employment_events" in source
    assert "capture_teacher_employment_event" in source
    assert "trg_capture_teacher_employment_event" in source
    assert "'activated'" in source and "'deactivated'" in source
    assert "'historical_backfill'" in source
    assert "teacher.status <> 'active'" in source
    assert "teacher.status <> 'active'\n          AND teacher.activated_at IS NOT NULL" not in source
    upgrade = source.split("def downgrade", 1)[0]
    assert "DELETE FROM msi_v2.teachers" not in upgrade
    assert "DELETE FROM msi_v2.teacher_candidates" not in upgrade


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
