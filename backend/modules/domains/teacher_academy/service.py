import json

from backend.modules.domains.identity.passwords import generate_password_hash
from backend.core.database import connect_auth_db

from backend.modules.domains.teacher_academy import repository as repository
from backend.modules.domains.teacher_academy import mutations_repository
from backend.modules.domains.teacher_academy.account_provisioning import (
    AcademyAccountProvisioningError,
    provision_recruitment_academy_account,
)
from backend.modules.domains.recruitment import contracts as recruitment_contracts
from backend.modules.domains.teacher_records.service import list_teachers, upsert_teacher
from backend.modules.domains.teacher_academy.commands.create_teacher import (
    CreateAcademyTeacherCommand,
    CreateAcademyTeacherDependencies,
    create_academy_teacher as execute_create_academy_teacher,
)
from backend.modules.domains.teacher_academy.commands.assessments import (
    AddAssessmentCommand,
    AssessmentDependencies,
    DeleteAssessmentCommand,
    add_assessment as execute_add_assessment,
    delete_assessment as execute_delete_assessment,
)
from backend.modules.domains.teacher_academy.commands.lifecycle import (
    LifecycleDependencies,
    delete_academy_teacher as execute_delete_academy_teacher,
    update_academy_status as execute_update_academy_status,
)
from backend.modules.domains.teacher_academy.domain_types import (
    VALID_ASSIGNMENT_STATUSES,
)

from backend.modules.domains.teacher_academy.read_service import (
    _academy_teacher_notification_payload, _as_int, _as_score,
    _assessment_notification_payload, _assignment_notification_payload,
    _create_result, _json_dumps, _normalize_status, _notify_academy_event_safe,
    _phase1_accounts_available, _program_row, _provision_teacher_account_v2,
    _selected_curriculum_lessons, _utc_now_iso, list_academy_teachers,
)

# Temporary monkeypatch-compatible alias for legacy callers and characterization tests.
# Production code crosses the module boundary only through recruitment_contracts.
recruitment_repository = recruitment_contracts.repository


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
    result = execute_create_academy_teacher(
        CreateAcademyTeacherCommand(
            full_name=str(full_name or ""),
            subject_program_id=subject_program_id,
            selected_curriculum_item_ids=selected_curriculum_item_ids,
            position=str(position or ""),
            employment_type=str(employment_type or ""),
            telegram_username=str(telegram_username or ""),
            phone=str(phone or ""),
            email=str(email or ""),
            academy_start_date=str(academy_start_date or ""),
            mentor_id=mentor_id,
            department_head_id=department_head_id,
            notes=str(notes or ""),
            created_by=str(created_by or ""),
        ),
        CreateAcademyTeacherDependencies(
            connect=connect_auth_db,
            generate_password_hash=generate_password_hash,
            provision_account=_provision_teacher_account_v2,
            notify=_notify_academy_event_safe,
            now=_utc_now_iso,
            as_int=_as_int,
            get_program=_program_row,
            get_lessons=_selected_curriculum_lessons,
        ),
    )
    credentials = (
        result.credentials.to_legacy_payload() if result.credentials else None
    )
    return _create_result(
        result.is_created,
        result.message,
        credentials,
        return_credentials=return_credentials,
    )


def onboard_recruitment_academy_teacher(
    *,
    academy_teacher_id,
    subject_program_id,
    selected_curriculum_item_ids,
    actor_account_id=None,
    actor_login="",
):
    """Assign curriculum while reusing or provisioning the Academy account."""
    now = _utc_now_iso()
    with connect_auth_db() as conn:
        intake = mutations_repository.get_pending_recruitment_academy_intake(
            conn, _as_int(academy_teacher_id)
        )
        if not intake:
            return False, "Recruitment Academy intake was not found.", {}
        program = _program_row(conn, subject_program_id)
        if not program:
            return False, "Select a subject curriculum program.", {}
        lessons, lesson_error = _selected_curriculum_lessons(
            conn, program["id"], selected_curriculum_item_ids
        )
        if lesson_error:
            return False, lesson_error, {}

        try:
            provisioned = provision_recruitment_academy_account(
                conn,
                academy_teacher_id=int(intake["id"]),
                actor_account_id=_as_int(actor_account_id) or None,
                actor_login=str(actor_login or ""),
                now=now,
            )
        except AcademyAccountProvisioningError as exc:
            conn.rollback()
            return False, str(exc), {}

        existing_rows = repository.list_assignment_rows(conn, int(intake["id"]))
        assignment_id_by_item = {
            int(row["curriculum_item_id"]): int(row["id"])
            for row in existing_rows
            if int(row["curriculum_item_id"] or 0)
        }
        selected_item_ids = {int(lesson["id"]) for lesson in lessons}
        removed_assignment_ids = [
            int(row["id"])
            for row in existing_rows
            if int(row["curriculum_item_id"] or 0) not in selected_item_ids
        ]
        mutations_repository.delete_assignment_rows_with_assessments(
            conn,
            removed_assignment_ids,
        )
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
                    academy_teacher_id=int(intake["id"]),
                    subject_id=int(program["subject_id"]),
                    subject_program_id=int(program["id"]),
                    curriculum_item_id=int(lesson["id"]),
                    sequence_no=sequence_no,
                    lesson_number=str(lesson["lesson_number"] or ""),
                    lesson_topic=str(lesson["title"] or ""),
                    focus_areas_json=json.dumps([]),
                    created_by=str(actor_login or "Academic Director"),
                    created_at=now,
                )
        if not mutations_repository.complete_recruitment_academy_curriculum(
            conn,
            academy_teacher_id=int(intake["id"]),
            subject_id=int(program["subject_id"]),
            subject_program_id=int(program["id"]),
            updated_at=now,
        ):
            conn.rollback()
            return False, "Unable to assign the Teacher Academy curriculum.", {}
        mutations_repository.insert_recruitment_academy_onboarding_audit(
            conn,
            academy_teacher_id=int(intake["id"]),
            candidate_id=int(intake["recruitment_candidate_id"]),
            actor_account_id=_as_int(actor_account_id) or None,
            actor_login=str(actor_login or ""),
            created_at=now,
        )
        conn.commit()
    return True, "Teacher account is ready and the curriculum was assigned.", {
        "role": "teacher",
        "login": provisioned.login,
        "teacher_code": provisioned.login,
        "temporary_password": provisioned.login if provisioned.created else "",
        "display_name": str(intake["full_name"] or ""),
        "subject_name": str(program["subject_name"] or ""),
    }


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


def _assessment_dependencies():
    return AssessmentDependencies(
        connect=connect_auth_db,
        now=_utc_now_iso,
        as_int=_as_int,
        as_score=_as_score,
        normalize_status=_normalize_status,
        json_dumps=_json_dumps,
        notify=_notify_academy_event_safe,
        teacher_payload=_academy_teacher_notification_payload,
        assignment_payload=_assignment_notification_payload,
        assessment_payload=_assessment_notification_payload,
    )


def _lifecycle_dependencies():
    return LifecycleDependencies(
        connect=connect_auth_db,
        now=_utc_now_iso,
        as_int=_as_int,
        normalize_status=_normalize_status,
        are_canonical_accounts_available=_phase1_accounts_available,
    )


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
    return execute_add_assessment(
        AddAssessmentCommand(
            academy_teacher_id=academy_teacher_id,
            lesson_assignment_id=lesson_assignment_id,
            assessment_type=str(assessment_type or ""),
            evaluator_id=evaluator_id,
            assessment_datetime=str(assessment_datetime or ""),
            session_type=str(session_type or ""),
            class_label=str(class_label or ""),
            section_feedback=section_feedback,
            scores=scores,
            strengths=str(strengths or ""),
            areas_for_improvement=str(areas_for_improvement or ""),
            final_recommendation=str(final_recommendation or ""),
            decision=str(decision or ""),
            created_by=str(created_by or ""),
        ),
        _assessment_dependencies(),
    )


def delete_assessment(*, academy_teacher_id, assessment_id):
    return execute_delete_assessment(
        DeleteAssessmentCommand(
            academy_teacher_id=academy_teacher_id,
            assessment_id=assessment_id,
        ),
        _assessment_dependencies(),
    )


def update_academy_status(*, academy_teacher_id, status):
    return execute_update_academy_status(
        academy_teacher_id=academy_teacher_id,
        status=str(status or ""),
        dependencies=_lifecycle_dependencies(),
    )


def delete_academy_teacher(*, academy_teacher_id):
    return execute_delete_academy_teacher(
        academy_teacher_id=academy_teacher_id,
        dependencies=_lifecycle_dependencies(),
    )


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
