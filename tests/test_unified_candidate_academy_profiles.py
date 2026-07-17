"""Contracts for one lifecycle profile across Recruitment and Teacher Academy."""

from pathlib import Path

from backend.modules.hr.recruitment import repository, service


class _Rows:
    def __init__(self, *, one=None, many=None):
        self._one = one
        self._many = many or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class _CaptureConnection:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return _Rows(one={"total": 0}, many=[])


def test_pipeline_and_candidate_lists_exclude_academy_direct_profiles():
    conn = _CaptureConnection()
    repository.list_pipeline_rows(conn)
    pipeline_sql = conn.calls[-1][0]
    assert "candidate.is_application_received = true" in pipeline_sql
    assert "candidate.status IN ('new_candidate', 'responded', 'job_interview', 'test_and_demo', 'under_review')" in pipeline_sql

    conn = _CaptureConnection()
    repository.list_candidate_rows(conn)
    combined_sql = "\n".join(call[0] for call in conn.calls)
    assert "candidate.is_application_received = true" in combined_sql


def test_candidate_summary_exposes_one_academy_block_and_exact_identity_state():
    payload = service._candidate_summary(
        {
            "id": 42,
            "status": "teacher_academy",
            "phone": "+998 90 000 00 00",
            "email": "teacher@example.com",
            "telegram_username": "",
            "linked_account_id": 9,
            "academy_teacher_id": 14,
            "academy_status": "in_training",
            "academy_start_date": "2026-07-01",
            "academy_onboarding_status": "complete",
            "academy_subject_id": 2,
            "academy_subject": "Mathematics",
            "academy_subject_program_id": 3,
            "academy_curriculum": "IGCSE Mathematics A",
            "academy_staff_id": 25,
            "academy_login": "TCH0015",
            "academy_lesson_count": 12,
            "academy_assessment_count": 8,
        }
    )
    assert payload["academy"] == {
        "id": 14,
        "status": "in_training",
        "start_date": "2026-07-01",
        "onboarding_status": "complete",
        "subject_id": 2,
        "subject": "Mathematics",
        "subject_program_id": 3,
        "curriculum": "IGCSE Mathematics A",
        "staff_id": 25,
        "login": "TCH0015",
        "lesson_count": 12,
        "assessment_count": 8,
        "account_state": "connected",
    }
    assert payload["exact_identity"] == {
        "has_phone": True,
        "has_email": True,
        "has_telegram": False,
        "has_linked_account": True,
    }
    assert "academy_status" not in payload


def test_exact_duplicate_match_never_uses_a_name():
    conn = _CaptureConnection()
    assert repository.exact_academy_identity_match(conn) is None
    assert conn.calls == []

    repository.exact_academy_identity_match(conn, email="Teacher@Example.com")
    sql, params = conn.calls[-1]
    assert "full_name" not in sql.split("WHERE", 1)[1]
    assert "teacher@example.com" in params


def test_unified_profile_migration_and_reconciliation_are_history_safe():
    migration = Path("database/alembic/versions/0027_unified_teacher_profiles.py").read_text()
    command = Path("scripts/reconcile_teacher_academy_profiles.py").read_text()
    persistence = Path("backend/modules/hr/recruitment/repository.py").read_text()
    assert "profile_origin" in migration
    assert "is_application_received" in migration
    assert "academy_direct" in migration
    assert "NULL, '', '', 'teacher_academy'" in persistence
    assert "insert_final_decision" not in command
    assert "--apply" in command
    for name in (
        "Qodirov Ibrohim",
        "Niaz Ahmed",
        "Ziyodullayeva Nigora",
        "Bunyodjon Xaydaraliyev",
        "Shakhzod",
        "Azizbek Quldashev",
        "Zikriyoev Javokhir",
        "Mamadiyev Asilbek",
        "Murotboyeva Sabrina",
    ):
        assert name in command


def test_frontend_uses_the_shared_profile_and_academy_block():
    model = Path("frontend/src/features/recruitment/model.ts").read_text()
    profile = Path("frontend/src/features/recruitment/CandidateProfile.tsx").read_text()
    teachers = Path("frontend/src/features/recruitment/TeachersView.tsx").read_text()
    assert 'profile_origin?: "application" | "academy_direct"' in model
    assert "candidate.academy" in profile
    assert "No application history has been generated." in profile
    assert "origin=teachers" in teachers
