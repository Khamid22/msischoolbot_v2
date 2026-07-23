"""Contracts for Academic Director and HOD evaluation candidate groups."""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import service as recruitment_service
from backend.modules.hr.recruitment.candidates import read_repository, read_service


class _Result:
    def __init__(self, *, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class _CandidateQueryConnection:
    def __init__(self):
        self.calls: list[tuple[str, tuple | None]] = []

    def execute(self, sql, params=None):
        statement = str(sql)
        self.calls.append((statement, params))
        if "count(DISTINCT candidate.id)" in statement:
            return _Result(row={"total": 2})
        return _Result(rows=[])


@pytest.mark.parametrize(
    ("group", "condition", "date_expression", "evaluator_expression"),
    [
        (
            "new",
            "academic_demo_appointment.id IS NOT NULL",
            "academic_demo_appointment.starts_at",
            "academic_demo_appointment.responsible_account_id",
        ),
        (
            "subject_test",
            "COALESCE(latest_demo.result, '') = 'passed'",
            "latest_demo.demo_at",
            "latest_demo.evaluator_account_id",
        ),
        (
            "successful",
            "COALESCE(latest_subject_test.result, '') = 'passed'",
            "latest_subject_test.test_at",
            "latest_subject_test.evaluator_account_id",
        ),
        (
            "rejected",
            "decision.source_evaluation_type, '') IN ('demo', 'subject_test')",
            "decision.created_at",
            "decision.source_evaluation_type = 'demo'",
        ),
    ],
)
def test_candidate_group_sql_classifies_filters_and_sorts_by_relevant_event(
    group,
    condition,
    date_expression,
    evaluator_expression,
):
    conn = _CandidateQueryConnection()

    rows, total = read_repository.list_candidate_rows(
        conn,
        candidate_group=group,
        evaluator_account_id=41,
        relevant_from="2026-07-01",
        relevant_to="2026-07-23",
        limit=25,
        offset=0,
    )

    assert rows == []
    assert total == 2
    assert len(conn.calls) == 2
    count_sql, count_params = conn.calls[0]
    list_sql, list_params = conn.calls[1]
    for sql in (count_sql, list_sql):
        assert condition in sql
        assert evaluator_expression in sql
        assert f"({date_expression})::date >= %s::date" in sql
        assert f"({date_expression})::date <= %s::date" in sql
    if group == "new":
        assert f"CASE WHEN ({date_expression}) >= now() THEN 0 ELSE 1 END" in list_sql
        assert f"THEN ({date_expression})" in list_sql
        assert "END ASC NULLS LAST" in list_sql
        assert f"({date_expression}) DESC NULLS LAST" in list_sql
    else:
        assert f"ORDER BY ({date_expression}) DESC NULLS LAST, candidate.id DESC" in list_sql
    assert count_params == (41, "2026-07-01", "2026-07-23")
    assert list_params == (41, "2026-07-01", "2026-07-23", 25, 0)


def test_rejected_group_only_contains_evaluation_rejections():
    rejected = read_repository._academic_candidate_group_condition("rejected")

    assert "candidate.status = 'rejected'" in rejected
    assert "decision.decision, '') = 'rejected'" in rejected
    assert "source_evaluation_type, '') IN ('demo', 'subject_test')" in rejected
    assert "candidate_withdrew" not in rejected


def test_new_group_contains_only_candidates_with_an_active_demo():
    new = read_repository._academic_candidate_group_condition("new")

    assert "candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')" in new
    assert "academic_demo_appointment.id IS NOT NULL" in new
    assert "latest_demo.result, '') <> 'passed'" in new


def test_subject_test_group_contains_demo_passes_without_a_test_result():
    subject_test = read_repository._academic_candidate_group_condition("subject_test")

    assert "candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')" in subject_test
    assert "latest_demo.result, '') = 'passed'" in subject_test
    assert "latest_subject_test.result, '') = ''" in subject_test


def test_unreviewed_badge_count_uses_the_visible_new_candidate_query():
    conn = _CandidateQueryConnection()

    rows, total = read_repository.list_candidate_rows(
        conn,
        visible_account_id=41,
        include_decision_queue=True,
        candidate_group="new",
        unreviewed_account_id=41,
        limit=0,
    )

    assert rows == []
    assert total == 2
    assert len(conn.calls) == 1
    count_sql, count_params = conn.calls[0]
    assert "teacher_candidate_assignments visibility" in count_sql
    assert "teacher_candidate_hire_approvals queue_approval" in count_sql
    assert "teacher_recruitment_notifications review_notification" in count_sql
    assert "review_notification.read_at IS NULL" in count_sql
    assert "academic_demo_appointment.id IS NOT NULL" in count_sql
    assert count_params == (41, 41)


def test_academic_unreviewed_badge_service_counts_only_new_candidates(monkeypatch):
    captured = {}

    @contextmanager
    def connect():
        yield object()

    def list_rows(_conn, **values):
        captured.update(values)
        return [], 2

    monkeypatch.setattr(recruitment_service, "connect_auth_db", connect)
    monkeypatch.setattr(
        recruitment_service.repository,
        "list_candidate_rows",
        list_rows,
    )

    total = recruitment_service.academic_unreviewed_candidate_count(
        CurrentUser(
            login="director@test",
            role="academic_director",
            account_id=41,
            staff_id=51,
        )
    )

    assert total == 2
    assert captured["candidate_group"] == "new"
    assert captured["unreviewed_account_id"] == 41
    assert captured["visible_account_id"] == 41
    assert captured["include_decision_queue"] is True
    assert captured["limit"] == 0


def test_successful_group_excludes_closed_non_evaluation_outcomes():
    successful = read_repository._academic_candidate_group_condition("successful")

    assert "candidate.status NOT IN ('rejected', 'candidate_withdrew', 'trash_bin')" in successful
    assert "latest_demo.result, '') = 'passed'" in successful
    assert "latest_subject_test.result, '') = 'passed'" in successful


def test_candidate_group_service_returns_counts_and_evaluation_metadata(monkeypatch):
    calls: list[dict] = []
    totals = {"new": 3, "subject_test": 4, "successful": 2, "rejected": 1}
    selected_row = {
        "id": 17,
        "full_name": "Newest Candidate",
        "status": "test_and_demo",
        "academic_demo_starts_at": "2026-07-23T10:00:00+05:00",
        "academic_demo_responsible_name": "Head of Mathematics",
        "actionable_approval_id": None,
    }

    def list_rows(_conn, **values):
        calls.append(values)
        group = values["candidate_group"]
        rows = [selected_row] if group == "new" and values["limit"] else []
        return rows, totals[group]

    monkeypatch.setattr(
        read_service.repository,
        "list_candidate_rows",
        list_rows,
    )
    monkeypatch.setattr(
        read_service.repository,
        "unreviewed_recruitment_candidate_ids",
        lambda *_args, **_kwargs: {17},
    )

    @contextmanager
    def connect():
        yield object()

    dependencies = read_service.CandidateReadDependencies(
        connect=connect,
        academic_visible_id=lambda user: user.account_id,
        visible_subject_ids=lambda _user, _conn: {8},
        appointment_payload_for_user=lambda _user, row: dict(row),
    )
    result = read_service.list_candidates(
        CurrentUser(
            login="hod@test",
            role="head_of_department",
            account_id=41,
            staff_id=51,
        ),
        candidate_group="new",
        page=1,
        per_page=25,
        dependencies=dependencies,
    )

    assert result["group_counts"] == totals
    assert result["total"] == 3
    assert result["items"][0]["candidate_group"] == "new"
    assert result["items"][0]["relevant_at"] == selected_row["academic_demo_starts_at"]
    assert (
        result["items"][0]["evaluation_evaluator_name"]
        == "Head of Mathematics"
    )
    assert result["items"][0]["is_unreviewed"] is True
    assert calls[0]["visible_account_id"] == 41
    assert calls[0]["visible_subject_ids"] == {8}
    assert calls[0]["limit"] == 25
    assert [call["candidate_group"] for call in calls[1:]] == [
        "new",
        "subject_test",
        "successful",
        "rejected",
    ]
    assert all(call["limit"] == 0 for call in calls[1:])


def test_candidate_groups_are_not_available_to_hr_manager():
    @contextmanager
    def connect():
        yield object()

    dependencies = read_service.CandidateReadDependencies(
        connect=connect,
        academic_visible_id=lambda _user: None,
        visible_subject_ids=lambda _user, _conn: None,
        appointment_payload_for_user=lambda _user, row: dict(row),
    )

    with pytest.raises(
        read_service.RecruitmentError,
        match="require academic recruitment access",
    ):
        read_service.list_candidates(
            CurrentUser(
                login="hr@test",
                role="hr_manager",
                account_id=41,
                staff_id=51,
            ),
            candidate_group="new",
            dependencies=dependencies,
        )
