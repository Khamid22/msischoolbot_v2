import json

from backend.core.passwords import generate_password_hash
from backend.core.database import connect_auth_db

from backend.modules.teacher_academy import repository as repository
from backend.modules.teacher_academy import mutations_repository
from backend.modules.people.teachers.service import list_teachers, upsert_teacher

VALID_ACADEMY_STATUSES = {
    "new_academy_teacher",
    "in_training",
    "ready_for_evaluation",
    "needs_improvement",
    "ready_for_active_teacher",
    "approved",
    "rejected",
    "on_hold",
}

VALID_ASSIGNMENT_STATUSES = {
    "assigned",
    "ready",
    "assessed",
    "passed",
    "needs_improvement",
}

VALID_DECISIONS = {
    "passed",
    "needs_improvement",
    "reassign_lesson",
    "ready_for_final_evaluation",
    "approved_for_active_teacher",
    "rejected",
}

RUBRIC_WEIGHTS = {
    "teacher_guidance_compliance_score": 0.25,
    "timing_adherence_score": 0.20,
    "resource_familiarity_score": 0.15,
    "english_fluency_score": 0.15,
    "confidence_delivery_score": 0.10,
    "engagement_technique_score": 0.15,
}

from backend.modules.teacher_academy.read_service import (
    _academy_teacher_notification_payload, _as_int, _as_score,
    _assessment_notification_payload, _assignment_notification_payload,
    _create_result, _json_dumps, _normalize_status, _notify_academy_event_safe,
    _phase1_accounts_available, _program_row, _provision_teacher_account_v2,
    _selected_curriculum_lessons, _utc_now_iso, list_academy_teachers,
)

def create_academy_teacher(
    *,
    full_name,
    subject_program_id,
    selected_curriculum_item_ids=None,
    position="Trainee Teacher",
    employment_type="academy",
    telegram_username="",
    phone="",
    email="",
    academy_start_date="",
    mentor_id=0,
    department_head_id=0,
    notes="",
    created_by="",
    return_credentials=False,
):
    normalized_name = str(full_name or "").strip()
    if not normalized_name:
        return _create_result(False, "Trainee name is required.", return_credentials=return_credentials)

    now = _utc_now_iso()
    with connect_auth_db() as conn:
        program = _program_row(conn, subject_program_id)
        if not program:
            return _create_result(False, "Select a subject curriculum program.", return_credentials=return_credentials)
        lessons, lesson_error = _selected_curriculum_lessons(
            conn,
            program["id"],
            selected_curriculum_item_ids,
        )
        if lesson_error:
            return _create_result(False, lesson_error, return_credentials=return_credentials)
        subject_name = str(program["subject_name"] or "")
        profile_teacher_id = repository.insert_teacher_profile_row(
            conn,
            normalized_name,
            notes=str(notes or "").strip(),
            status="academy",
            subject_id=int(program["subject_id"]),
            created_at=now,
            updated_at=now,
        )
        if not profile_teacher_id:
            return _create_result(False, "Unable to create the teacher profile.", return_credentials=return_credentials)
        login = repository.get_next_teacher_code(conn)
        password_hash = generate_password_hash(login)
        staff_id = repository.insert_teacher_auth(
            conn,
            profile_teacher_id,
            login,
            login,
            password_hash,
            now,
        )
        _provision_teacher_account_v2(
            conn,
            teacher_id=profile_teacher_id,
            staff_id=staff_id,
            login=login,
            password_hash=password_hash,
            full_name=normalized_name,
        )

        academy_teacher_id = mutations_repository.insert_academy_teacher(
            conn,
            staff_id=staff_id,
            full_name=normalized_name,
            subject_id=int(program["subject_id"]),
            subject_program_id=int(program["id"]),
            position=str(position or "Trainee Teacher").strip() or "Trainee Teacher",
            employment_type=str(employment_type or "academy").strip() or "academy",
            telegram_username=str(telegram_username or "").strip(),
            phone=str(phone or "").strip(),
            email=str(email or "").strip(),
            academy_start_date=str(academy_start_date or "").strip(),
            mentor_id=_as_int(mentor_id),
            department_head_id=_as_int(department_head_id),
            notes=str(notes or "").strip(),
            created_by=str(created_by or "").strip(),
            created_at=now,
        )
        for sequence_no, lesson in enumerate(lessons, start=1):
            mutations_repository.insert_academy_lesson_assignment(
                conn,
                academy_teacher_id=academy_teacher_id,
                subject_id=int(program["subject_id"]),
                subject_program_id=int(program["id"]),
                curriculum_item_id=int(lesson["id"]),
                sequence_no=sequence_no,
                lesson_number=str(lesson["lesson_number"] or ""),
                lesson_topic=str(lesson["title"] or ""),
                focus_areas_json=json.dumps([]),
                created_by=str(created_by or "").strip(),
                created_at=now,
            )
        conn.commit()
    _notify_academy_event_safe(
        academy_teacher={
            "id": academy_teacher_id,
            "full_name": normalized_name,
            "subject_id": int(program["subject_id"] or 0),
            "subject": subject_name,
            "telegram_username": str(telegram_username or "").strip(),
            "telegram_user_id": 0,
        },
        event_type="teacher_created",
        title="Welcome to MSI School",
        body="Welcome to the MSI School family.",
        source="Academic Department",
    )
    credentials = {
        "role": "teacher",
        "login": login,
        "teacher_code": login,
        "temporary_password": login,
        "display_name": normalized_name,
        "subject_name": subject_name,
    }
    return _create_result(True, "", credentials, return_credentials=return_credentials)


def update_assignment(
    *,
    assignment_id,
    assignment_type="",
    deadline_date="",
    session_datetime="",
    evaluator_id=0,
    focus_areas=None,
    notes_to_trainee="",
    status="assigned",
):
    parsed_assignment_id = _as_int(assignment_id)
    if not parsed_assignment_id:
        return False, "Assignment not found."
    normalized_status = _normalize_status(status, VALID_ASSIGNMENT_STATUSES, "assigned")
    now = _utc_now_iso()
    with connect_auth_db() as conn:
        existing = mutations_repository.get_assignment_schedule_row(conn, parsed_assignment_id)
        if not existing:
            return False, "Assignment not found."
        old_session_datetime = str(existing["session_datetime"] or "").strip()
        mutations_repository.update_assignment_schedule(
            conn,
            assignment_id=parsed_assignment_id,
            assignment_type=str(assignment_type or "").strip(),
            deadline_date=str(deadline_date or "").strip(),
            session_datetime=str(session_datetime or "").strip(),
            evaluator_id=_as_int(evaluator_id),
            focus_areas_json=json.dumps(focus_areas if isinstance(focus_areas, list) else []),
            notes_to_trainee=str(notes_to_trainee or "").strip(),
            status=normalized_status,
            updated_at=now,
        )
        conn.commit()
    next_session_datetime = str(session_datetime or "").strip()
    event_type = (
        "lesson_time_changed"
        if old_session_datetime and next_session_datetime and old_session_datetime != next_session_datetime
        else "lesson_assigned"
    )
    _notify_academy_event_safe(
        academy_teacher=_academy_teacher_notification_payload(existing),
        assignment=_assignment_notification_payload(existing, session_datetime=next_session_datetime),
        event_type=event_type,
        title="Academy lesson schedule updated" if event_type == "lesson_time_changed" else "Academy lesson assigned",
        body="A Teacher Academy lesson has been updated.",
        source="Academic Department",
    )
    return True, ""


def sync_academy_lessons(*, academy_teacher_id, selected_curriculum_item_ids, created_by=""):
    """Replace the teacher's selected academy lessons with the given curriculum items.

    Assignments whose curriculum item is unticked are deleted together with
    their assessment reports; newly ticked items become new assignments.
    """
    parsed_teacher_id = _as_int(academy_teacher_id)
    if not parsed_teacher_id:
        return False, "Academy teacher not found."

    now = _utc_now_iso()
    with connect_auth_db() as conn:
        teacher = mutations_repository.get_academy_teacher_program_row(conn, parsed_teacher_id)
        if not teacher:
            return False, "Academy teacher not found."
        program = _program_row(conn, teacher["subject_program_id"])
        if not program:
            return False, "Academy teacher has no subject curriculum program."
        lessons, lesson_error = _selected_curriculum_lessons(
            conn,
            program["id"],
            selected_curriculum_item_ids,
        )
        if lesson_error:
            return False, lesson_error

        existing_rows = repository.list_assignment_rows(conn, parsed_teacher_id)
        assignment_id_by_item = {}
        for row in existing_rows:
            item_id = int(row["curriculum_item_id"] or 0)
            if item_id and item_id not in assignment_id_by_item:
                assignment_id_by_item[item_id] = int(row["id"])

        selected_item_ids = {int(lesson["id"]) for lesson in lessons}
        removed_assignment_ids = [
            int(row["id"])
            for row in existing_rows
            if int(row["curriculum_item_id"] or 0) not in selected_item_ids
        ]
        mutations_repository.delete_assignment_rows_with_assessments(conn, removed_assignment_ids)

        added_count = 0
        for sequence_no, lesson in enumerate(lessons, start=1):
            assignment_id = assignment_id_by_item.get(int(lesson["id"]))
            if assignment_id:
                mutations_repository.update_assignment_sequence(
                    conn,
                    assignment_id=assignment_id,
                    sequence_no=sequence_no,
                    updated_at=now,
                )
            else:
                mutations_repository.insert_academy_lesson_assignment(
                    conn,
                    academy_teacher_id=parsed_teacher_id,
                    subject_id=int(program["subject_id"]),
                    subject_program_id=int(program["id"]),
                    curriculum_item_id=int(lesson["id"]),
                    sequence_no=sequence_no,
                    lesson_number=str(lesson["lesson_number"] or ""),
                    lesson_topic=str(lesson["title"] or ""),
                    focus_areas_json=json.dumps([]),
                    created_by=str(created_by or "").strip(),
                    created_at=now,
                )
                added_count += 1
        mutations_repository.touch_academy_teacher(
            conn,
            academy_teacher_id=parsed_teacher_id,
            updated_at=now,
        )
        conn.commit()
    if added_count or removed_assignment_ids:
        _notify_academy_event_safe(
            academy_teacher=_academy_teacher_notification_payload(teacher),
            event_type="lesson_assigned",
            title="Teacher Academy lessons updated",
            body=f"{len(lessons)} academy lessons are selected.",
            source="Academic Department",
            lessons_count=len(lessons),
        )
    return True, ""


def _assignment_for_assessment(conn, academy_teacher_id, lesson_assignment_id):
    return mutations_repository.get_assignment_for_assessment(
        conn,
        academy_teacher_id=_as_int(academy_teacher_id),
        lesson_assignment_id=_as_int(lesson_assignment_id),
    )


def _weighted_score(scores):
    total = 0.0
    for key, weight in RUBRIC_WEIGHTS.items():
        total += _as_score(scores.get(key)) * weight
    return round(total, 2)


def add_assessment(
    *,
    academy_teacher_id,
    lesson_assignment_id,
    assessment_type="academy_practice_lesson",
    evaluator_id=0,
    assessment_datetime="",
    session_type="training_simulation",
    class_label="",
    section_feedback=None,
    scores=None,
    strengths="",
    areas_for_improvement="",
    final_recommendation="",
    decision="needs_improvement",
    created_by="",
):
    parsed_teacher_id = _as_int(academy_teacher_id)
    if not parsed_teacher_id:
        return False, "Academy teacher not found."
    parsed_assignment_id = _as_int(lesson_assignment_id)
    normalized_decision = _normalize_status(decision, VALID_DECISIONS, "needs_improvement")
    safe_scores = {key: _as_score((scores or {}).get(key)) for key in RUBRIC_WEIGHTS}
    weighted_score = _weighted_score(safe_scores)
    now = _utc_now_iso()

    with connect_auth_db() as conn:
        assignment = _assignment_for_assessment(conn, parsed_teacher_id, parsed_assignment_id)
        if not assignment:
            return False, "Assignment not found."
        evaluator = _as_int(evaluator_id) or _as_int(assignment["evaluator_id"])

        # One report per lesson: a re-assessment replaces any prior report for this
        # assignment so the average score and progress counts stay correct.
        mutations_repository.delete_assessments_for_assignment(
            conn,
            academy_teacher_id=parsed_teacher_id,
            lesson_assignment_id=parsed_assignment_id,
        )

        mutations_repository.insert_assessment(
            conn,
            academy_teacher_id=parsed_teacher_id,
            lesson_assignment_id=parsed_assignment_id,
            assessment_type=str(assessment_type or "academy_practice_lesson").strip(),
            lesson_number=str(assignment["lesson_number"] or ""),
            lesson_topic=str(assignment["lesson_topic"] or ""),
            evaluator_id=evaluator,
            assessment_datetime=str(assessment_datetime or "").strip(),
            session_type=str(session_type or "training_simulation").strip(),
            class_label=str(class_label or "").strip(),
            section_feedback_json=_json_dumps(section_feedback if isinstance(section_feedback, dict) else {}),
            scores=safe_scores,
            weighted_score=weighted_score,
            strengths=str(strengths or "").strip(),
            areas_for_improvement=str(areas_for_improvement or "").strip(),
            final_recommendation=str(final_recommendation or "").strip(),
            decision=normalized_decision,
            created_by=str(created_by or "").strip(),
            created_at=now,
        )
        assignment_status = (
            "passed"
            if normalized_decision in {"passed", "ready_for_final_evaluation", "approved_for_active_teacher"}
            else "needs_improvement"
        )
        mutations_repository.update_assignment_status(
            conn,
            assignment_id=parsed_assignment_id,
            status=assignment_status,
            updated_at=now,
        )
        next_status = None
        if normalized_decision == "approved_for_active_teacher":
            next_status = "ready_for_active_teacher"
        elif normalized_decision == "rejected":
            next_status = "rejected"
        elif normalized_decision in {"needs_improvement", "reassign_lesson"}:
            next_status = "needs_improvement"
        elif normalized_decision == "ready_for_final_evaluation":
            next_status = "ready_for_evaluation"
        if next_status:
            mutations_repository.update_academy_teacher_status(
                conn,
                academy_teacher_id=parsed_teacher_id,
                status=next_status,
                updated_at=now,
            )
        else:
            mutations_repository.touch_academy_teacher(
                conn,
                academy_teacher_id=parsed_teacher_id,
                updated_at=now,
            )
        conn.commit()
    _notify_academy_event_safe(
        academy_teacher=_academy_teacher_notification_payload(assignment),
        assignment=_assignment_notification_payload(assignment),
        assessment=_assessment_notification_payload(
            decision=normalized_decision,
            weighted_score=weighted_score,
            assessment_datetime=assessment_datetime,
        ),
        event_type="assessment_added",
        title="Assessment report added",
        body="An Academic Department assessment report is available.",
        source="Academic Department",
    )
    return True, ""


def _assignment_status_from_decision(decision):
    normalized = str(decision or "").strip()
    return (
        "passed"
        if normalized in {"passed", "ready_for_final_evaluation", "approved_for_active_teacher"}
        else "needs_improvement"
    )


def _academy_status_from_decision(decision):
    normalized = str(decision or "").strip()
    if normalized == "approved_for_active_teacher":
        return "ready_for_active_teacher"
    if normalized == "rejected":
        return "rejected"
    if normalized in {"needs_improvement", "reassign_lesson"}:
        return "needs_improvement"
    if normalized == "ready_for_final_evaluation":
        return "ready_for_evaluation"
    return None


def delete_assessment(*, academy_teacher_id, assessment_id):
    parsed_teacher_id = _as_int(academy_teacher_id)
    parsed_assessment_id = _as_int(assessment_id)
    if not parsed_teacher_id or not parsed_assessment_id:
        return False, "Assessment report not found."

    now = _utc_now_iso()
    with connect_auth_db() as conn:
        assessment = mutations_repository.get_assessment_delete_row(
            conn,
            academy_teacher_id=parsed_teacher_id,
            assessment_id=parsed_assessment_id,
        )
        if not assessment:
            return False, "Assessment report not found."

        lesson_assignment_id = _as_int(assessment["lesson_assignment_id"])
        mutations_repository.delete_assessment_row(conn, parsed_assessment_id)

        if lesson_assignment_id:
            latest_assignment_assessment = mutations_repository.get_latest_assessment_for_assignment(
                conn,
                academy_teacher_id=parsed_teacher_id,
                lesson_assignment_id=lesson_assignment_id,
            )
            if latest_assignment_assessment:
                assignment_status = _assignment_status_from_decision(latest_assignment_assessment["decision"])
            else:
                assignment = mutations_repository.get_assignment_schedule_row(conn, lesson_assignment_id)
                assignment_status = "ready" if assignment and str(assignment["session_datetime"] or "").strip() else "assigned"
            mutations_repository.update_assignment_status(
                conn,
                assignment_id=lesson_assignment_id,
                status=assignment_status,
                updated_at=now,
            )

        latest_teacher_assessment = mutations_repository.get_latest_assessment_for_teacher(conn, parsed_teacher_id)
        next_status = (
            _academy_status_from_decision(latest_teacher_assessment["decision"])
            if latest_teacher_assessment
            else None
        )
        current_status = str(mutations_repository.get_academy_teacher_status(conn, parsed_teacher_id) or "").strip()
        assessment_driven_statuses = {
            "needs_improvement",
            "ready_for_evaluation",
            "ready_for_active_teacher",
            "rejected",
        }
        if next_status:
            mutations_repository.update_academy_teacher_status(
                conn,
                academy_teacher_id=parsed_teacher_id,
                status=next_status,
                updated_at=now,
            )
        elif current_status in assessment_driven_statuses:
            mutations_repository.update_academy_teacher_status(
                conn,
                academy_teacher_id=parsed_teacher_id,
                status="in_training",
                updated_at=now,
            )
        else:
            mutations_repository.touch_academy_teacher(
                conn,
                academy_teacher_id=parsed_teacher_id,
                updated_at=now,
            )

        conn.commit()
    return True, ""


def update_academy_status(*, academy_teacher_id, status):
    parsed_teacher_id = _as_int(academy_teacher_id)
    if not parsed_teacher_id:
        return False, "Academy teacher not found."
    normalized_status = _normalize_status(status, VALID_ACADEMY_STATUSES, "in_training")
    now = _utc_now_iso()
    with connect_auth_db() as conn:
        existing = mutations_repository.get_academy_teacher_id(conn, parsed_teacher_id)
        if not existing:
            return False, "Academy teacher not found."
        mutations_repository.update_academy_teacher_status(
            conn,
            academy_teacher_id=parsed_teacher_id,
            status=normalized_status,
            updated_at=now,
        )
        conn.commit()
    return True, ""


def delete_academy_teacher(*, academy_teacher_id):
    parsed_teacher_id = _as_int(academy_teacher_id)
    if not parsed_teacher_id:
        return False, "Academy teacher not found."

    with connect_auth_db() as conn:
        row = mutations_repository.get_academy_teacher_delete_row(conn, parsed_teacher_id)
        if not row:
            return False, "Academy teacher not found."

        staff_id = _as_int(row["staff_id"])
        teacher_id = _as_int(row["teacher_id"])
        teacher_status = str(row["teacher_status"] or "").strip().lower()
        promoted_teacher_id = _as_int(row["promoted_teacher_id"])
        delete_generated_identity = bool(staff_id and teacher_id and teacher_status == "academy" and not promoted_teacher_id)
        account_ids: list[int] = []
        if delete_generated_identity and _phase1_accounts_available(conn):
            account_ids = mutations_repository.list_teacher_account_ids_for_staff(conn, staff_id=staff_id)

        mutations_repository.delete_academy_teacher_row(conn, parsed_teacher_id)

        if delete_generated_identity:
            mutations_repository.delete_teacher_profiles_for_delete(
                conn,
                teacher_id=teacher_id,
                account_ids=account_ids,
            )
            mutations_repository.delete_staff_profiles_for_delete(
                conn,
                staff_id=staff_id,
                account_ids=account_ids,
            )
            mutations_repository.delete_teacher_accounts_for_delete(conn, account_ids)
            mutations_repository.delete_academy_teacher_staff_row(conn, staff_id)
            mutations_repository.delete_academy_teacher_profile_row(conn, teacher_id)

        conn.commit()
    return True, ""


def _academy_teacher_for_promotion(academy_teacher_id):
    parsed_teacher_id = _as_int(academy_teacher_id)
    if not parsed_teacher_id:
        return None
    teachers = list_academy_teachers()
    return next((teacher for teacher in teachers if int(teacher["id"]) == parsed_teacher_id), None)


def promote_academy_teacher(
    *,
    academy_teacher_id,
    assigned_group,
    pay_rate=0,
    category="junior",
    semester_stage="1-2",
    promotion_notes="",
):
    teacher = _academy_teacher_for_promotion(academy_teacher_id)
    if not teacher:
        return False, "Academy teacher not found."
    normalized_group = str(assigned_group or "").strip()
    if not normalized_group:
        return False, "Select a real group for the active teacher."

    progress = teacher.get("progress") if isinstance(teacher.get("progress"), dict) else {}
    average_score = progress.get("average_score") or 7
    supervised_lessons = progress.get("assessed_count") or 0
    assigned_lessons = progress.get("target_lessons") or progress.get("assigned_count") or supervised_lessons
    now = _utc_now_iso()
    promoted_teacher_id = _as_int(teacher.get("account_teacher_id"))
    with connect_auth_db() as conn:
        if promoted_teacher_id:
            repository.activate_teacher_profile(
                conn,
                promoted_teacher_id,
                promotion_notes or "Promoted from Teacher Academy.",
                now,
            )
            assigned = repository.set_teacher_group_assignment(conn, promoted_teacher_id, normalized_group)
            if not assigned:
                return False, "Unable to promote teacher. Check the selected group."
        else:
            created = upsert_teacher(
                full_name=teacher["full_name"],
                pay_rate=pay_rate,
                assigned_group=normalized_group,
                category=category,
                semester_stage=semester_stage,
                performance_score=average_score,
                supervised_lessons=supervised_lessons,
                igcse_evidence=f"Teacher Academy: {supervised_lessons}/{assigned_lessons} assessed lessons.",
                promotion_notes=promotion_notes or "Promoted from Teacher Academy.",
            )
            if not created:
                return False, "Unable to promote teacher. Check group and pay rate."
            for row in list_teachers():
                if (
                    str(row.get("full_name", "")).strip().casefold() == str(teacher["full_name"]).strip().casefold()
                    and str(row.get("assigned_group", "")).strip().casefold() == normalized_group.casefold()
                ):
                    promoted_teacher_id = int(row.get("id") or 0)
        mutations_repository.approve_academy_teacher_promotion(
            conn,
            academy_teacher_id=_as_int(academy_teacher_id),
            promoted_teacher_id=promoted_teacher_id,
            updated_at=now,
        )
        conn.commit()
    return True, ""
