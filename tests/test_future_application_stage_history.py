"""Regression coverage for future-dated candidate stage history."""

from pathlib import Path

from backend.modules.hr.recruitment.candidates import repository


ROOT = Path(__file__).resolve().parents[1]


class _Result:
    def fetchone(self):
        return {"id": 42, "status": "rejected", "version": 2}


class _Connection:
    def __init__(self) -> None:
        self.sql = ""
        self.params: tuple[object, ...] = ()

    def execute(self, sql, params):
        self.sql = str(sql)
        self.params = tuple(params)
        return _Result()


def test_candidate_creation_caps_history_entry_without_changing_sla_anchor():
    conn = _Connection()

    repository.insert_candidate(
        conn,
        values={"full_name": "Future Candidate", "application_date": "2026-07-25"},
        now="2026-07-22T10:00:00Z",
        actor_account_id=7,
    )

    assert "LEAST(" in conn.sql
    assert "candidate.stage_changed_at" in conn.sql
    assert "application_date::timestamp AT TIME ZONE 'Asia/Tashkent'" in conn.sql
    assert "+ make_interval(days => rule.target_days)" in conn.sql


def test_stage_transition_repairs_legacy_future_entry_before_closing_it():
    conn = _Connection()

    repository.update_candidate_stage(
        conn,
        candidate_id=42,
        stage="rejected",
        expected_version=1,
        actor_account_id=7,
        now="2026-07-22T10:00:00Z",
        comment="Rejected by HR.",
        transition_source="manual",
    )

    assert "entered_at = LEAST(history.entered_at, updated.stage_changed_at)" in conn.sql
    assert "exited_at = updated.stage_changed_at" in conn.sql
    assert "LEAST(" in conn.sql


def test_migration_repairs_open_future_history_and_preserves_sla_due_date():
    migration = (
        ROOT
        / "database/alembic/versions/0036_future_application_stage_history.py"
    ).read_text()

    assert 'revision = "0036_future_stage_anchor"' in migration
    assert 'down_revision = "0035_pipeline_stages"' in migration
    assert "history.exited_at IS NULL" in migration
    assert "history.entered_at > now()" in migration
    assert "candidate.stage_history_future_anchor_repaired" in migration
    assert "sla_due_at =" not in migration
