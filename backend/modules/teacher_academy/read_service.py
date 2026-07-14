import json
from datetime import datetime, timezone

from backend.modules.identity.passwords import generate_password_hash
from backend.core.database import connect_auth_db

from backend.modules.teacher_academy import repository as repository
from backend.modules.people.teachers.service import list_teachers
from backend.modules.teacher_academy.notifications import notify_academy_teacher_event

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
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    return repository.get_subject_program(conn, parsed_program_id)


def _curriculum_lessons(conn, program_id):
    return repository.list_curriculum_lessons(conn, int(program_id))


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
    rows = repository.list_academy_teacher_account_backfill_rows(conn)
    for row in rows:
        full_name = str(row["full_name"] or "").strip()
        if not full_name:
            continue
        existing_teacher = repository.get_teacher_by_full_name_row(conn, full_name)
        teacher_id = int(existing_teacher["id"] or 0) if existing_teacher else 0
        subject_id = _as_int(row["subject_id"])
        if not teacher_id:
            teacher_id = repository.insert_teacher_profile_row(
                conn,
                full_name,
                notes=str(row["notes"] or "").strip(),
                status="academy",
                subject_id=subject_id,
                created_at=now,
                updated_at=now,
            )
        elif subject_id:
            repository.upsert_teacher_subject(conn, teacher_id, subject_id)
        if not teacher_id:
            continue

        existing_login = str(row["staff_login"] or "").strip()
        auth = repository.get_teacher_auth_row_by_id(conn, teacher_id)
        auth_login = str(auth["login"] or "").strip() if auth else ""
        login = existing_login or auth_login or repository.get_next_teacher_code(conn)
        password_hash = generate_password_hash(login)
        staff_id = repository.insert_teacher_auth(
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
            repository.update_academy_teacher_user_id(
                conn,
                academy_teacher_id=int(row["id"]),
                staff_id=staff_id,
                updated_at=now,
            )


def backfill_academy_teacher_accounts():
    """Explicit maintenance action for older academy rows missing teacher logins."""
    with connect_auth_db() as conn:
        _backfill_academy_teacher_accounts(conn)
        conn.commit()


def _teacher_name(conn, teacher_id):
    parsed_teacher_id = _as_int(teacher_id)
    if not parsed_teacher_id:
        return ""
    return repository.get_teacher_name(conn, parsed_teacher_id)


def _phase1_accounts_available(conn):
    return repository.phase1_accounts_available(conn)


def _provision_teacher_account_v2(conn, *, teacher_id, staff_id, login, password_hash, full_name, legacy_login=""):
    """Best-effort shared account provisioning for new academy teachers."""
    if not _phase1_accounts_available(conn):
        return 0

    normalized_login = str(login or "").strip()
    if not normalized_login:
        return 0

    now = _utc_now_iso()
    account = repository.get_teacher_account_for_provisioning(
        conn,
        login=normalized_login,
        staff_id=_as_int(staff_id),
    )
    if account:
        account_id = int(account["id"] or 0)
        repository.update_teacher_account_for_provisioning(
            conn,
            account_id=account_id,
            login=normalized_login,
            full_name=str(full_name or "").strip(),
            staff_id=_as_int(staff_id),
            updated_at=now,
        )
    else:
        account_id = repository.insert_teacher_account_for_provisioning(
            conn,
            login=normalized_login,
            password_hash=password_hash,
            full_name=str(full_name or "").strip(),
            staff_id=_as_int(staff_id),
            created_at=now,
        )

    if account_id:
        profile = repository.get_teacher_profile_for_provisioning(
            conn,
            account_id=account_id,
            teacher_id=_as_int(teacher_id),
            teacher_code=normalized_login,
        )
        if profile:
            repository.update_teacher_profile_for_provisioning(
                conn,
                profile_id=int(profile["id"]),
                account_id=account_id,
                teacher_id=_as_int(teacher_id),
                teacher_code=normalized_login,
                legacy_login=str(legacy_login or "").strip(),
                updated_at=now,
            )
        else:
            repository.insert_teacher_profile_for_provisioning(
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


def _row_value(row, key, default=""):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return default


def _academy_teacher_notification_payload(row):
    if not row:
        return {}
    return {
        "id": _as_int(_row_value(row, "academy_teacher_id") or _row_value(row, "id")),
        "full_name": str(_row_value(row, "academy_teacher_name") or _row_value(row, "full_name") or ""),
        "subject_id": _as_int(_row_value(row, "subject_id")),
        "subject": str(_row_value(row, "subject") or _row_value(row, "subject_name") or ""),
        "telegram_username": str(_row_value(row, "telegram_username") or ""),
        "telegram_user_id": _as_int(_row_value(row, "telegram_user_id")),
    }


def _assignment_notification_payload(row, *, session_datetime=None):
    if not row:
        return {}
    return {
        "id": _as_int(_row_value(row, "id")),
        "lesson_number": str(_row_value(row, "lesson_number") or ""),
        "lesson_topic": str(_row_value(row, "lesson_topic") or ""),
        "assignment_type": str(_row_value(row, "assignment_type") or ""),
        "deadline_date": str(_row_value(row, "deadline_date") or ""),
        "session_datetime": str(
            session_datetime
            if session_datetime is not None
            else (_row_value(row, "session_datetime") or "")
        ),
        "evaluator_id": _as_int(_row_value(row, "evaluator_id")),
        "evaluator_name": str(_row_value(row, "evaluator_name") or ""),
    }


def _assessment_notification_payload(*, decision, weighted_score=None, assessment_datetime=""):
    return {
        "decision": str(decision or ""),
        "weighted_score": weighted_score,
        "assessment_datetime": str(assessment_datetime or ""),
    }


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
    # Only passed lessons are "done" — a failed lesson stays next until it passes.
    next_assignment = next(
        (
            assignment
            for assignment in assignments
            if assignment["id"] not in passed_assignment_ids
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
        "telegram_user_id": _as_int(_row_value(row, "telegram_user_id")),
        "promoted_teacher_id": int(row["promoted_teacher_id"] or 0),
        "recruitment_candidate_id": int(_row_value(row, "recruitment_candidate_id") or 0),
        "account_onboarding_status": str(_row_value(row, "account_onboarding_status") or "complete"),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
        "assignments": assignments,
        "assessments": assessments,
        "progress": _progress_for(assignments, assessments),
    }


def list_academy_teachers():
    with connect_auth_db() as conn:
        teacher_rows = repository.list_academy_teacher_rows(conn)
        assignment_rows = repository.list_assignment_rows(conn)
        assessment_rows = repository.list_assessment_rows(conn)

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


def _academy_event_date_parts(session_datetime):
    raw = str(session_datetime or "").strip()
    if not raw:
        return "", ""
    normalized = raw.replace(" ", "T")
    date_part = normalized[:10] if len(normalized) >= 10 else ""
    time_part = ""
    if "T" in normalized:
        time_part = normalized.split("T", 1)[1][:5]
    return date_part, time_part


def list_academy_timetable_events(subject_ids=None):
    scoped_subject_ids = {
        _as_int(subject_id)
        for subject_id in (subject_ids or [])
        if _as_int(subject_id)
    }
    events = []
    for teacher in list_academy_teachers():
        subject_id = _as_int(teacher.get("subject_id"))
        if scoped_subject_ids and subject_id not in scoped_subject_ids:
            continue
        for assignment in teacher.get("assignments") or []:
            session_datetime = str(assignment.get("session_datetime") or "").strip()
            if not session_datetime:
                continue
            session_date, start_time = _academy_event_date_parts(session_datetime)
            lesson_number = str(assignment.get("lesson_number") or "").strip()
            lesson_topic = str(assignment.get("lesson_topic") or "").strip()
            title = " - ".join(part for part in (lesson_number, lesson_topic) if part) or "Academy lesson"
            events.append(
                {
                    "id": f"academy-{_as_int(assignment.get('id'))}",
                    "assignment_id": _as_int(assignment.get("id")),
                    "academy_teacher_id": _as_int(teacher.get("id")),
                    "subject_id": subject_id,
                    "subject_name": str(teacher.get("subject") or teacher.get("subject_program_name") or ""),
                    "teacher_name": str(teacher.get("full_name") or ""),
                    "group_name": "Teacher Academy",
                    "title": title,
                    "lesson_number": lesson_number,
                    "lesson_topic": lesson_topic,
                    "session_datetime": session_datetime,
                    "session_date": session_date,
                    "start_time": start_time,
                    "end_time": "",
                    "room": "Teacher Academy",
                    "online_url": "",
                    "status": str(assignment.get("status") or "scheduled"),
                    "evaluator_id": _as_int(assignment.get("evaluator_id")),
                    "evaluator_name": str(assignment.get("evaluator_name") or ""),
                    "event_type": "academy_lesson",
                }
            )
    return sorted(
        events,
        key=lambda row: (
            str(row.get("session_date") or "9999-99-99"),
            str(row.get("start_time") or ""),
            str(row.get("teacher_name") or ""),
        ),
    )


def get_academy_teacher_for_teacher_account(teacher_id, staff_id=None):
    parsed_teacher_id = _as_int(teacher_id)
    parsed_staff_id = _as_int(staff_id)
    if not parsed_teacher_id and not parsed_staff_id:
        return None

    with connect_auth_db() as conn:
        teacher_row = repository.get_academy_teacher_row_for_account(
            conn,
            teacher_id=parsed_teacher_id,
            staff_id=parsed_staff_id,
        )
        if not teacher_row:
            return None
        academy_teacher_id = int(teacher_row["id"])
        assignment_rows = repository.list_assignment_rows(conn, academy_teacher_id)
        assessment_rows = repository.list_assessment_rows(conn, academy_teacher_id)
    return _academy_teacher_payload(
        teacher_row,
        [_row_to_assignment(row) for row in assignment_rows],
        [_row_to_assessment(row) for row in assessment_rows],
    )


def list_teacher_academy_page_context():
    with connect_auth_db() as conn:
        subjects = repository.list_active_subjects(conn)
        group_options = repository.list_active_group_options(conn)
        curriculum_programs = repository.list_curriculum_programs(conn)
        curriculum_items = repository.list_curriculum_items(conn)
    return {
        "teachers": list_teachers(),
        "academy_teachers": list_academy_teachers(),
        "group_options": group_options,
        "subjects": subjects,
        "curriculum_programs": curriculum_programs,
        "curriculum_items": curriculum_items,
    }
