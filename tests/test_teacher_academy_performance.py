"""Teacher Academy performance-oriented service coverage."""

import backend.roles.admin.services.teacher_academy_service as academy_service


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _EmptyAcademyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        return _Rows([])


class _SingleAcademyTeacherConnection:
    def __init__(self):
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if "FROM msi_v2.academy_teachers at" in sql:
            return _Rows(
                [
                    {
                        "id": 3,
                        "user_id": 44,
                        "full_name": "Training Teacher",
                        "subject_id": 2,
                        "subject_program_id": 7,
                        "subject": "Mathematics",
                        "subject_program_name": "IGCSE Mathematics",
                        "position": "Trainee Teacher",
                        "employment_type": "academy",
                        "telegram_username": "",
                        "phone": "",
                        "email": "",
                        "academy_status": "in_training",
                        "academy_start_date": "2026-07-01",
                        "mentor_id": 0,
                        "mentor_name": "",
                        "department_head_id": 0,
                        "department_head_name": "",
                        "notes": "",
                        "login": "TCH0004",
                        "account_teacher_id": 12,
                        "promoted_teacher_id": 0,
                        "created_at": "2026-07-01T00:00:00Z",
                        "updated_at": "2026-07-02T00:00:00Z",
                    }
                ]
            )
        if "FROM msi_v2.academy_lesson_assignments ala" in sql:
            return _Rows(
                [
                    {
                        "id": 8,
                        "academy_teacher_id": 3,
                        "sequence_no": 1,
                        "subject_program_id": 7,
                        "curriculum_item_id": 101,
                        "lesson_number": "L1",
                        "lesson_topic": "Numbers",
                        "assignment_type": "full_practice_lesson",
                        "deadline_date": "",
                        "session_datetime": "2026-07-07T09:00:00Z",
                        "evaluator_id": 0,
                        "evaluator_name": "Academic Director",
                        "focus_areas_json": "[]",
                        "notes_to_trainee": "",
                        "status": "assigned",
                        "specification_points": "1.1",
                        "book_pages": "10-11",
                        "created_at": "2026-07-01T00:00:00Z",
                        "updated_at": "2026-07-02T00:00:00Z",
                    }
                ]
            )
        if "FROM msi_v2.academy_assessments aa" in sql:
            return _Rows(
                [
                    {
                        "id": 11,
                        "academy_teacher_id": 3,
                        "lesson_assignment_id": 8,
                        "assessment_type": "academy_practice_lesson",
                        "lesson_number": "L1",
                        "lesson_topic": "Numbers",
                        "evaluator_id": 0,
                        "evaluator_name": "Academic Director",
                        "assessment_datetime": "2026-07-08T09:00:00Z",
                        "session_type": "training_simulation",
                        "class_label": "",
                        "section_feedback_json": "{}",
                        "teacher_guidance_compliance_score": 8,
                        "timing_adherence_score": 8,
                        "resource_familiarity_score": 8,
                        "english_fluency_score": 8,
                        "confidence_delivery_score": 8,
                        "engagement_technique_score": 8,
                        "weighted_overall_score": 8,
                        "strengths": "",
                        "areas_for_improvement": "",
                        "final_recommendation": "",
                        "decision": "passed",
                        "created_by": "Academic Director",
                        "created_at": "2026-07-08T00:00:00Z",
                        "updated_at": "2026-07-08T00:00:00Z",
                    }
                ]
            )
        return _Rows([])


def test_list_academy_teachers_does_not_backfill_on_read(monkeypatch):
    monkeypatch.setattr(academy_service.queries, "connect_auth_db", lambda: _EmptyAcademyConnection())
    monkeypatch.setattr(academy_service.queries, "ensure_teacher_academy_schema", lambda conn: None)
    monkeypatch.setattr(
        academy_service,
        "_backfill_academy_teacher_accounts",
        lambda conn: (_ for _ in ()).throw(AssertionError("backfill should not run on read")),
    )

    assert academy_service.list_academy_teachers() == []


def test_lightweight_teacher_academy_lookup_returns_matching_teacher(monkeypatch):
    conn = _SingleAcademyTeacherConnection()
    monkeypatch.setattr(academy_service.queries, "connect_auth_db", lambda: conn)
    monkeypatch.setattr(academy_service.queries, "ensure_teacher_academy_schema", lambda conn: None)

    teacher = academy_service.get_academy_teacher_for_teacher_account(12, staff_id=44)

    assert teacher["id"] == 3
    assert teacher["account_teacher_id"] == 12
    assert [assignment["id"] for assignment in teacher["assignments"]] == [8]
    assert [assessment["id"] for assessment in teacher["assessments"]] == [11]
    assert teacher["progress"]["assigned_count"] == 1
    assert teacher["progress"]["assessed_count"] == 1
    assert any("LIMIT 1" in sql for sql, _params in conn.queries)


def test_progress_target_matches_selected_assignment_count():
    six_assignments = [{"id": index + 1, "status": "assigned"} for index in range(6)]
    ten_assignments = [{"id": index + 1, "status": "assigned"} for index in range(10)]

    six_progress = academy_service._progress_for(six_assignments, [])
    ten_progress = academy_service._progress_for(ten_assignments, [])

    assert six_progress["assigned_count"] == 6
    assert six_progress["target_lessons"] == 6
    assert ten_progress["assigned_count"] == 10
    assert ten_progress["target_lessons"] == 10
