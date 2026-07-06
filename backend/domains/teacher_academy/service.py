import json
from datetime import datetime

from werkzeug.security import generate_password_hash

from backend.domains.teacher_academy import queries
from backend.identity.teachers import list_teachers, upsert_teacher
from backend.roles.admin.services.teacher_academy_notifications import notify_academy_teacher_event

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


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_schema(conn):
    queries.ensure_teacher_academy_schema(conn)


def _as_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _as_score(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    return min(10.0, max(0.0, parsed))


def _json_loads(value, fallback):
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _json_dumps(value):
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return "{}"


def _normalize_status(value, allowed, fallback):
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback


def _create_result(ok, message="", credentials=None, *, return_credentials=False):
    if return_credentials:
        return ok, message, credentials or {}
    return ok, message


def _program_row(conn, program_id):
    parsed_program_id = _as_int(program_id)
    if not parsed_program_id:
        return None
    return queries.get_subject_program(conn, parsed_program_id)


def _curriculum_lessons(conn, program_id):
    return queries.list_curriculum_lessons(conn, int(program_id))


def _normalize_selected_curriculum_item_ids(value):
    if value in (None, ""):
        return [], []
    if isinstance(value, str):
        raw_values = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [value]

    selected_ids = []
    invalid_values = []
    seen = set()
    for raw_value in raw_values:
        if isinstance(raw_value, (list, tuple, set)):
            tokens = raw_value
        else:
            raw_text = str(raw_value or "").strip()
            if not raw_text:
                continue
            if raw_text.startswith("["):
                try:
                    parsed = json.loads(raw_text)
                except (TypeError, ValueError):
                    parsed = None
                tokens = parsed if isinstance(parsed, list) else [raw_text]
            else:
                tokens = raw_text.split(",")
        for token in tokens:
            raw_token = str(token or "").strip()
            if not raw_token:
                continue
            parsed_id = _as_int(raw_token)
            if not parsed_id:
                invalid_values.append(raw_token)
                continue
            if parsed_id in seen:
                continue
            seen.add(parsed_id)
            selected_ids.append(parsed_id)
    return selected_ids, invalid_values


def _selected_curriculum_lessons(conn, program_id, selected_curriculum_item_ids):
    selected_ids, invalid_values = _normalize_selected_curriculum_item_ids(selected_curriculum_item_ids)
    if invalid_values:
        return [], "Select valid Teacher Academy lessons."
    if not selected_ids:
        return [], "Select at least 1 Teacher Academy lesson."

    lessons_by_id = {
        int(row["id"]): row
        for row in _curriculum_lessons(conn, program_id)
    }
    missing_ids = [item_id for item_id in selected_ids if item_id not in lessons_by_id]
    if missing_ids:
        return [], "Selected Teacher Academy lessons must be lesson items from the selected subject curriculum."
    return [lessons_by_id[item_id] for item_id in selected_ids], ""


def _backfill_academy_teacher_accounts(conn):
    """Ensure older academy teacher rows have a linked teacher login."""
    now = _utc_now_iso()
    rows = queries.list_academy_teacher_account_backfill_rows(conn)
    for row in rows:
        full_name = str(row["full_name"] or "").strip()
        if not full_name:
            continue
        existing_teacher = queries.get_teacher_by_full_name_row(conn, full_name)
        teacher_id = int(existing_teacher["id"] or 0) if existing_teacher else 0
        subject_id = _as_int(row["subject_id"])
        if not teacher_id:
            teacher_id = queries.insert_teacher_profile_row(
                conn,
                full_name,
                notes=str(row["notes"] or "").strip(),
                status="academy",
                subject_id=subject_id,
                created_at=now,
                updated_at=now,
            )
        elif subject_id:
            queries.upsert_teacher_subject(conn, teacher_id, subject_id)
        if not teacher_id:
            continue

        existing_login = str(row["staff_login"] or "").strip()
        auth = queries.get_teacher_auth_row_by_id(conn, teacher_id)
        auth_login = str(auth["login"] or "").strip() if auth else ""
        login = existing_login or auth_login or queries.get_next_teacher_code(conn)
        password_hash = generate_password_hash(login)
        staff_id = queries.insert_teacher_auth(
            conn,
            teacher_id,
            login,
            login,
            password_hash,
            now,
        )
        if staff_id:
            _provision_teacher_account_v2(
                conn,
                teacher_id=teacher_id,
                staff_id=staff_id,
                login=login,
                password_hash=password_hash,
                full_name=full_name,
                legacy_login=existing_login or auth_login,
            )
            queries.update_academy_teacher_user_id(
                conn,
                academy_teacher_id=int(row["id"]),
                staff_id=staff_id,
                updated_at=now,
            )


def backfill_academy_teacher_accounts():
    """Explicit maintenance action for older academy rows missing teacher logins."""
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        _backfill_academy_teacher_accounts(conn)
        conn.commit()


def _teacher_name(conn, teacher_id):
    parsed_teacher_id = _as_int(teacher_id)
    if not parsed_teacher_id:
        return ""
    return queries.get_teacher_name(conn, parsed_teacher_id)


def _phase1_accounts_available(conn):
    return queries.phase1_accounts_available(conn)


def _provision_teacher_account_v2(conn, *, teacher_id, staff_id, login, password_hash, full_name, legacy_login=""):
    """Best-effort shared account provisioning for new academy teachers."""
    if not _phase1_accounts_available(conn):
        return 0

    normalized_login = str(login or "").strip()
    if not normalized_login:
        return 0

    now = _utc_now_iso()
    account = queries.get_teacher_account_for_provisioning(
        conn,
        login=normalized_login,
        staff_id=_as_int(staff_id),
    )
    if account:
        account_id = int(account["id"] or 0)
        queries.update_teacher_account_for_provisioning(
            conn,
            account_id=account_id,
            login=normalized_login,
            password_hash=password_hash,
            full_name=str(full_name or "").strip(),
            staff_id=_as_int(staff_id),
            updated_at=now,
        )
    else:
        account_id = queries.insert_teacher_account_for_provisioning(
            conn,
            login=normalized_login,
            password_hash=password_hash,
            full_name=str(full_name or "").strip(),
            staff_id=_as_int(staff_id),
            created_at=now,
        )

    if account_id:
        profile = queries.get_teacher_profile_for_provisioning(
            conn,
            account_id=account_id,
            teacher_id=_as_int(teacher_id),
            teacher_code=normalized_login,
        )
        if profile:
            queries.update_teacher_profile_for_provisioning(
                conn,
                profile_id=int(profile["id"]),
                account_id=account_id,
                teacher_id=_as_int(teacher_id),
                teacher_code=normalized_login,
                legacy_login=str(legacy_login or "").strip(),
                updated_at=now,
            )
        else:
            queries.insert_teacher_profile_for_provisioning(
                conn,
                account_id=account_id,
                teacher_id=_as_int(teacher_id),
                teacher_code=normalized_login,
                legacy_login=str(legacy_login or "").strip(),
                created_at=now,
            )
    return account_id


def _notify_academy_event_safe(**kwargs):
    try:
        return notify_academy_teacher_event(**kwargs)
    except Exception:
        return {"ok": False, "telegram_sent": False, "in_app_available": True}


def _row_to_assignment(row):
    return {
        "id": int(row["id"]),
        "academy_teacher_id": int(row["academy_teacher_id"]),
        "sequence_no": int(row["sequence_no"] or 0),
        "subject_program_id": int(row["subject_program_id"] or 0),
        "curriculum_item_id": int(row["curriculum_item_id"] or 0),
        "lesson_number": str(row["lesson_number"] or ""),
        "lesson_topic": str(row["lesson_topic"] or ""),
        "assignment_type": str(row["assignment_type"] or ""),
        "deadline_date": str(row["deadline_date"] or ""),
        "session_datetime": str(row["session_datetime"] or ""),
        "evaluator_id": int(row["evaluator_id"] or 0),
        "evaluator_name": str(row["evaluator_name"] or ""),
        "focus_areas": _json_loads(row["focus_areas_json"], []),
        "notes_to_trainee": str(row["notes_to_trainee"] or ""),
        "status": str(row["status"] or "assigned"),
        "specification_points": str(row["specification_points"] or ""),
        "book_pages": str(row["book_pages"] or ""),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
    }


def _row_to_assessment(row):
    return {
        "id": int(row["id"]),
        "academy_teacher_id": int(row["academy_teacher_id"]),
        "lesson_assignment_id": int(row["lesson_assignment_id"] or 0),
        "assessment_type": str(row["assessment_type"] or ""),
        "lesson_number": str(row["lesson_number"] or ""),
        "lesson_topic": str(row["lesson_topic"] or ""),
        "evaluator_id": int(row["evaluator_id"] or 0),
        "evaluator_name": str(row["evaluator_name"] or ""),
        "assessment_datetime": str(row["assessment_datetime"] or ""),
        "session_type": str(row["session_type"] or ""),
        "class_label": str(row["class_label"] or ""),
        "section_feedback": _json_loads(row["section_feedback_json"], {}),
        "scores": {
            key: float(row[key] or 0)
            for key in RUBRIC_WEIGHTS
        },
        "weighted_overall_score": float(row["weighted_overall_score"] or 0),
        "strengths": str(row["strengths"] or ""),
        "areas_for_improvement": str(row["areas_for_improvement"] or ""),
        "final_recommendation": str(row["final_recommendation"] or ""),
        "decision": str(row["decision"] or ""),
        "created_by": str(row["created_by"] or ""),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
    }


def _progress_for(assignments, assessments):
    assessed_assignment_ids = {
        int(item["lesson_assignment_id"])
        for item in assessments
        if int(item.get("lesson_assignment_id") or 0) > 0
    }
    passed_decisions = {"passed", "ready_for_final_evaluation", "approved_for_active_teacher"}
    passed_assignment_ids = {
        int(item["lesson_assignment_id"])
        for item in assessments
        if int(item.get("lesson_assignment_id") or 0) > 0 and str(item.get("decision")) in passed_decisions
    }
    scores = [
        float(item["weighted_overall_score"])
        for item in assessments
        if float(item.get("weighted_overall_score") or 0) > 0
    ]
    next_assignment = next(
        (
            assignment
            for assignment in assignments
            if assignment["id"] not in assessed_assignment_ids
            and assignment["status"] not in {"cancelled", "passed"}
        ),
        None,
    )
    return {
        "assigned_count": len(assignments),
        "assessed_count": len(assessed_assignment_ids),
        "passed_count": len(passed_assignment_ids),
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "latest_score": round(scores[-1], 2) if scores else None,
        # The progress target always equals the number of lessons the Academic
        # Director actually assigned — never a fixed 12-lesson pack.
        "target_lessons": len(assignments),
        "next_assignment": next_assignment,
    }


def _academy_teacher_payload(row, assignments, assessments):
    teacher_id = int(row["id"])
    return {
        "id": teacher_id,
        "user_id": int(row["user_id"] or 0),
        "full_name": str(row["full_name"] or ""),
        "subject_id": int(row["subject_id"] or 0),
        "subject_program_id": int(row["subject_program_id"] or 0),
        "subject": str(row["subject"] or ""),
        "subject_program_name": str(row["subject_program_name"] or ""),
        "position": str(row["position"] or ""),
        "employment_type": str(row["employment_type"] or ""),
        "telegram_username": str(row["telegram_username"] or ""),
        "phone": str(row["phone"] or ""),
        "email": str(row["email"] or ""),
        "academy_status": str(row["academy_status"] or ""),
        "academy_start_date": str(row["academy_start_date"] or ""),
        "mentor_id": int(row["mentor_id"] or 0),
        "mentor_name": str(row["mentor_name"] or ""),
        "department_head_id": int(row["department_head_id"] or 0),
        "department_head_name": str(row["department_head_name"] or ""),
        "notes": str(row["notes"] or ""),
        "login": str(row["login"] or ""),
        "account_teacher_id": int(row["account_teacher_id"] or 0),
        "promoted_teacher_id": int(row["promoted_teacher_id"] or 0),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
        "assignments": assignments,
        "assessments": assessments,
        "progress": _progress_for(assignments, assessments),
    }


def list_academy_teachers():
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        teacher_rows = queries.list_academy_teacher_rows(conn)
        assignment_rows = queries.list_assignment_rows(conn)
        assessment_rows = queries.list_assessment_rows(conn)

    teachers = []
    assignments_by_teacher = {}
    assessments_by_teacher = {}
    for row in assignment_rows:
        assignment = _row_to_assignment(row)
        assignments_by_teacher.setdefault(assignment["academy_teacher_id"], []).append(assignment)
    for row in assessment_rows:
        assessment = _row_to_assessment(row)
        assessments_by_teacher.setdefault(assessment["academy_teacher_id"], []).append(assessment)
    for row in teacher_rows:
        teacher_id = int(row["id"])
        assignments = assignments_by_teacher.get(teacher_id, [])
        assessments = assessments_by_teacher.get(teacher_id, [])
        teachers.append(_academy_teacher_payload(row, assignments, assessments))
    return teachers


def get_academy_teacher_for_teacher_account(teacher_id, staff_id=None):
    parsed_teacher_id = _as_int(teacher_id)
    parsed_staff_id = _as_int(staff_id)
    if not parsed_teacher_id and not parsed_staff_id:
        return None

    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        teacher_row = queries.get_academy_teacher_row_for_account(
            conn,
            teacher_id=parsed_teacher_id,
            staff_id=parsed_staff_id,
        )
        if not teacher_row:
            return None
        academy_teacher_id = int(teacher_row["id"])
        assignment_rows = queries.list_assignment_rows(conn, academy_teacher_id)
        assessment_rows = queries.list_assessment_rows(conn, academy_teacher_id)
    return _academy_teacher_payload(
        teacher_row,
        [_row_to_assignment(row) for row in assignment_rows],
        [_row_to_assessment(row) for row in assessment_rows],
    )


def list_teacher_academy_page_context():
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        subjects = queries.list_active_subjects(conn)
        group_options = queries.list_active_group_options(conn)
        curriculum_programs = queries.list_curriculum_programs(conn)
        curriculum_items = queries.list_curriculum_items(conn)
    return {
        "teachers": list_teachers(),
        "academy_teachers": list_academy_teachers(),
        "group_options": group_options,
        "subjects": subjects,
        "curriculum_programs": curriculum_programs,
        "curriculum_items": curriculum_items,
    }


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
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
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
        profile_teacher_id = queries.insert_teacher_profile_row(
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
        login = queries.get_next_teacher_code(conn)
        password_hash = generate_password_hash(login)
        staff_id = queries.insert_teacher_auth(
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

        academy_teacher_id = queries.insert_academy_teacher(
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
            queries.insert_academy_lesson_assignment(
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
        academy_teacher={"telegram_username": str(telegram_username or "").strip()},
        event_type="lesson_assigned",
        title="Teacher Academy lessons assigned",
        body=f"{len(lessons)} academy lessons are ready.",
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
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        existing = queries.get_assignment_schedule_row(conn, parsed_assignment_id)
        if not existing:
            return False, "Assignment not found."
        old_session_datetime = str(existing["session_datetime"] or "").strip()
        queries.update_assignment_schedule(
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
        event_type=event_type,
        title="Academy lesson schedule updated" if event_type == "lesson_time_changed" else "Academy lesson assigned",
        body="A Teacher Academy lesson has been updated.",
        source="Academic Department",
    )
    return True, ""


def _assignment_for_assessment(conn, academy_teacher_id, lesson_assignment_id):
    return queries.get_assignment_for_assessment(
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

    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        assignment = _assignment_for_assessment(conn, parsed_teacher_id, parsed_assignment_id)
        if not assignment:
            return False, "Assignment not found."
        evaluator = _as_int(evaluator_id) or _as_int(assignment["evaluator_id"])

        queries.insert_assessment(
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
        queries.update_assignment_status(
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
            queries.update_academy_teacher_status(
                conn,
                academy_teacher_id=parsed_teacher_id,
                status=next_status,
                updated_at=now,
            )
        else:
            queries.touch_academy_teacher(
                conn,
                academy_teacher_id=parsed_teacher_id,
                updated_at=now,
            )
        conn.commit()
    _notify_academy_event_safe(
        event_type="assessment_added",
        title="Assessment report added",
        body="An Academic Department assessment report is available.",
        source="Academic Department",
    )
    return True, ""


def update_academy_status(*, academy_teacher_id, status):
    parsed_teacher_id = _as_int(academy_teacher_id)
    if not parsed_teacher_id:
        return False, "Academy teacher not found."
    normalized_status = _normalize_status(status, VALID_ACADEMY_STATUSES, "in_training")
    now = _utc_now_iso()
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        existing = queries.get_academy_teacher_id(conn, parsed_teacher_id)
        if not existing:
            return False, "Academy teacher not found."
        queries.update_academy_teacher_status(
            conn,
            academy_teacher_id=parsed_teacher_id,
            status=normalized_status,
            updated_at=now,
        )
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
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        if promoted_teacher_id:
            queries.activate_teacher_profile(
                conn,
                promoted_teacher_id,
                promotion_notes or "Promoted from Teacher Academy.",
                now,
            )
            assigned = queries.set_teacher_group_assignment(conn, promoted_teacher_id, normalized_group)
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
        queries.approve_academy_teacher_promotion(
            conn,
            academy_teacher_id=_as_int(academy_teacher_id),
            promoted_teacher_id=promoted_teacher_id,
            updated_at=now,
        )
        conn.commit()
    return True, ""


__all__ = [
    "RUBRIC_WEIGHTS",
    "backfill_academy_teacher_accounts",
    "get_academy_teacher_for_teacher_account",
    "list_academy_teachers",
    "list_teacher_academy_page_context",
    "create_academy_teacher",
    "update_assignment",
    "add_assessment",
    "update_academy_status",
    "promote_academy_teacher",
]
