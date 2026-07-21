"""Contracts for one lifecycle profile across Recruitment and Teacher Academy."""

from contextlib import contextmanager
from pathlib import Path

import pytest

from backend.core.access import CurrentUser
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
    assert (
        "candidate.status IN ('new_candidate', 'responded', 'job_interview', 'test_and_demo', 'under_review')"
        in pipeline_sql
    )

    conn = _CaptureConnection()
    repository.list_candidate_rows(conn)
    combined_sql = "\n".join(call[0] for call in conn.calls)
    assert "candidate.is_application_received = true" in combined_sql

    conn = _CaptureConnection()
    repository.list_candidate_rows(conn, stage="rejected")
    rejected_sql = "\n".join(call[0] for call in conn.calls)
    assert "candidate.profile_origin = 'academy_direct'" in rejected_sql


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
    assert "CAST(%s AS BIGINT) IS NOT NULL" in sql
    assert "candidate.linked_account_id = CAST(%s AS BIGINT)" in sql
    assert "account.id = CAST(%s AS BIGINT)" in sql


def test_unified_profile_migration_and_reconciliation_are_history_safe():
    migration = Path(
        "database/alembic/versions/0027_unified_teacher_profiles.py"
    ).read_text()
    command = Path("scripts/reconcile_teacher_academy_profiles.py").read_text()
    persistence = Path(
        "backend/modules/hr/recruitment/handoffs/intake_repository.py"
    ).read_text()
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
    roster = Path(
        "frontend/src/features/teacher-academy/TeacherAcademyRoster.tsx"
    ).read_text()
    academic_panel = Path(
        "frontend/src/features/teacher-academy/TeacherAcademyPanel.tsx"
    ).read_text()
    assert 'profile_origin?: "application" | "academy_direct"' in model
    assert "candidate.academy" in profile
    assert "No application history has been generated." in profile
    assert "TeacherAcademyRoster" in teachers
    assert "TeacherAcademyRoster" in academic_panel
    assert "origin=teachers" in roster
    assert "Delete to Trash Bin" in roster
    assert "Reject teacher" in roster
    assert "generated_login_will_be_deleted" in roster


def test_academy_removal_is_audited_and_history_preserving():
    service_source = "\n".join(
        [
            Path("backend/modules/hr/recruitment/service.py").read_text(),
            Path("backend/modules/hr/recruitment/handoffs/service.py").read_text(),
        ]
    )
    repository_source = "\n".join(
        [
            Path(
                "backend/modules/hr/recruitment/handoffs/lifecycle_repository.py"
            ).read_text(),
            Path(
                "backend/modules/hr/recruitment/handoffs/intake_repository.py"
            ).read_text(),
        ]
    )
    ad_routes = Path(
        "backend/workspaces/academic_director/staff_records_api.py"
    ).read_text()

    assert "def remove_academy_teacher(" in service_source
    assert "candidate.academy_removed" in service_source
    assert "origin_stage" in service_source
    assert "teacher_academy" in service_source
    assert "lessons_and_assessments_preserved" in service_source
    assert "DELETE FROM msi_v2.academy_teachers" not in repository_source
    assert "'rejected', 'removed', 'trash_bin'" in repository_source
    assert "def ensure_academy_intake" in repository_source
    assert "def sync_academy_subject_from_candidate" in repository_source
    assert "subject_id = COALESCE(subject_id, NULLIF(%s::bigint, 0))" in repository_source
    assert "subject_program_id = COALESCE" in repository_source
    assert "WHEN academy_status = 'rejected' THEN 'new_academy_teacher'" in repository_source
    assert "account_onboarding_status = 'removed'" not in repository_source
    assert (
        '@router.post("/teacher-academy/{academy_teacher_id}/delete")' not in ad_routes
    )


def test_academy_roster_excludes_closed_and_promoted_lifecycle_profiles():
    repository_source = Path(
        "backend/modules/teacher_academy/repository.py"
    ).read_text()
    mutations_source = Path(
        "backend/modules/teacher_academy/mutations_repository.py"
    ).read_text()
    migration_source = Path(
        "database/alembic/versions/0031_academy_roster_lifecycle.py"
    ).read_text()

    assert "WHERE at.promoted_teacher_id IS NULL" in repository_source
    assert "'rejected', 'removed', 'trash_bin'" in repository_source
    assert "'rejected', 'candidate_withdrew', 'trash_bin'" in repository_source
    assert "'rejected', 'removed', 'trash_bin'" in mutations_source
    assert "candidate.academy_lifecycle_synchronized" in migration_source


def test_permanent_candidate_purge_deletes_only_closed_academy_handoffs():
    repository_source = Path(
        "backend/modules/hr/recruitment/candidates/repository.py"
    ).read_text()

    assert "def purge_closed_academy_handoff" in repository_source
    assert "DELETE FROM msi_v2.academy_teachers" in repository_source
    assert "promoted_teacher_id IS NULL" in repository_source
    assert "academy_status IN ('rejected', 'removed', 'trash_bin')" in repository_source
    assert "delete_generated_academy_identity" in repository_source


def test_academy_removal_rejects_transactionally_without_deleting_history(monkeypatch):
    class Connection:
        committed = False

        def commit(self):
            self.committed = True

    conn = Connection()

    @contextmanager
    def connect():
        yield conn

    audits = []
    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository, "recruitment_setting_value_exists", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        repository,
        "lock_academy_removal_row",
        lambda *_args, **_kwargs: {
            "id": 14,
            "recruitment_candidate_id": 330,
            "academy_status": "in_training",
            "staff_id": 0,
            "teacher_id": 0,
            "staff_role": "",
            "teacher_status": "",
            "promoted_teacher_id": 0,
        },
    )
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 330,
            "status": "teacher_academy",
            "version": 4,
            "active_teacher_id": 0,
        },
    )
    monkeypatch.setattr(
        repository,
        "latest_active_final_decision",
        lambda *_args, **_kwargs: {"decision": "teacher_academy"},
    )
    monkeypatch.setattr(
        repository, "revoke_open_approvals", lambda *_args, **_kwargs: [7]
    )
    monkeypatch.setattr(
        repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [8]
    )
    monkeypatch.setattr(
        repository, "cancel_pending_candidate_tasks", lambda *_args, **_kwargs: [9]
    )
    monkeypatch.setattr(
        repository, "update_candidate_stage", lambda *_args, **_kwargs: {"id": 330}
    )
    monkeypatch.setattr(
        repository, "mark_academy_removed", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        repository, "insert_final_decision", lambda *_args, **_kwargs: 91
    )
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: audits.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )
    monkeypatch.setattr(
        service, "_notify_cancelled_appointments", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        service, "_sync_system_next_actions", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 330, "status": "rejected"},
    )

    result = service.remove_academy_teacher(
        CurrentUser(login="HR0001", role="hr_manager", account_id=41, staff_id=21),
        14,
        {"rejection_reason": "failed_academy", "reason_detail": "Did not pass."},
    )

    assert result == {
        "candidate": {"id": 330, "status": "rejected"},
        "identity_deleted": False,
        "already_removed": False,
    }
    assert conn.committed is True
    assert {event for event, _detail in audits} >= {
        "candidate.stage_changed",
        "candidate.academy_removed",
        "candidate.final_decision_made",
        "candidate.tasks_cancelled",
    }
    academy_audit = next(
        detail for event, detail in audits if event == "candidate.academy_removed"
    )
    assert academy_audit["lessons_and_assessments_preserved"] is True


@pytest.mark.parametrize("role", ["ceo", "head_of_department"])
def test_academy_removal_fails_closed_for_unauthorized_roles(role):
    with pytest.raises(service.RecruitmentError) as exc:
        service.remove_academy_teacher(
            CurrentUser(login=role.upper(), role=role),
            14,
            {"rejection_reason": "failed_academy"},
        )
    assert exc.value.status_code == 403


def test_roster_reject_reuses_safe_academy_removal(monkeypatch):
    captured = {}

    def remove(user, academy_teacher_id, values):
        captured.update(
            user=user,
            academy_teacher_id=academy_teacher_id,
            values=values,
        )
        return {
            "candidate": {"id": 330, "status": "rejected"},
            "identity_deleted": False,
            "already_removed": False,
        }

    monkeypatch.setattr(service, "remove_academy_teacher", remove)
    result = service.close_teacher_handoff(
        CurrentUser(login="HR0001", role="hr_manager", account_id=41, staff_id=21),
        kind="teacher_academy",
        record_id=14,
        values={
            "action": "rejected",
            "rejection_reason": "failed_academy",
            "reason_detail": "Did not pass.",
        },
    )
    assert result["action"] == "rejected"
    assert captured["academy_teacher_id"] == 14
    assert captured["values"]["rejection_reason"] == "failed_academy"


@pytest.mark.parametrize("role", ["ceo", "head_of_department"])
def test_roster_delete_and_reject_fail_closed_for_unauthorized_roles(role):
    with pytest.raises(service.RecruitmentError) as exc:
        service.close_teacher_handoff(
            CurrentUser(login=role.upper(), role=role),
            kind="active_teacher",
            record_id=12,
            values={"action": "trash_bin"},
        )
    assert exc.value.status_code == 403
