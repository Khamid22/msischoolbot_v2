import json
import random
from datetime import datetime

from werkzeug.security import generate_password_hash

from database import queries
from backend.identity.teachers import list_teachers, upsert_teacher
from backend.roles.admin.services.teacher_academy_notifications import notify_academy_teacher_event


ACADEMY_TARGET_LESSONS = 12

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
    return conn.execute(
        """
        SELECT sp.id, sp.subject_id, sp.program_name, subj.subject_name, subj.subject_key
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE sp.id = %s AND sp.status = 'active'
        LIMIT 1
        """,
        (parsed_program_id,),
    ).fetchone()


def _curriculum_lessons(conn, program_id):
    return conn.execute(
        """
        SELECT id, program_id, item_order, lesson_number, title, specification_points, book_pages
        FROM msi_v2.subject_program_items
        WHERE program_id = %s AND item_type = 'lesson'
        ORDER BY item_order ASC
        """,
        (int(program_id),),
    ).fetchall()


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
    rows = conn.execute(
        """
        SELECT
            at.id,
            at.user_id,
            at.full_name,
            at.subject_id,
            at.notes,
            COALESCE(staff.login, '') AS staff_login,
            COALESCE(subj.subject_name, '') AS subject_name,
            COALESCE(subj.subject_key, '') AS subject_key
        FROM msi_v2.academy_teachers at
        LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
        LEFT JOIN msi_v2.subjects subj ON subj.id = at.subject_id
        WHERE COALESCE(at.full_name, '') <> ''
          AND COALESCE(at.academy_status, '') NOT IN ('rejected')
          AND (
            at.user_id IS NULL
            OR staff.id IS NULL
            OR COALESCE(staff.login, '') = ''
            OR staff.teacher_id IS NULL
          )
        ORDER BY at.id ASC
        """
    ).fetchall()
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
            conn.execute(
                """
                UPDATE msi_v2.academy_teachers
                SET user_id = %s, updated_at = %s::timestamptz
                WHERE id = %s
                """,
                (staff_id, now, int(row["id"])),
            )


def _balanced_random_lessons(rows, count=ACADEMY_TARGET_LESSONS):
    rows = list(rows)
    if len(rows) <= count:
        return rows
    selected = []
    for index in range(count):
        start = round(index * len(rows) / count)
        end = round((index + 1) * len(rows) / count)
        bucket = rows[start:end] or rows
        selected.append(random.choice(bucket))
    by_id = {}
    for row in selected:
        by_id[int(row["id"])] = row
    return sorted(by_id.values(), key=lambda row: int(row["item_order"] or 0))[:count]


def _teacher_name(conn, teacher_id):
    parsed_teacher_id = _as_int(teacher_id)
    if not parsed_teacher_id:
        return ""
    row = conn.execute(
        "SELECT full_name FROM msi_v2.teachers WHERE id = %s LIMIT 1",
        (parsed_teacher_id,),
    ).fetchone()
    return str(row["full_name"] or "") if row else ""


def _phase1_accounts_available(conn):
    try:
        row = conn.execute("SELECT to_regclass('msi_v2.accounts') AS table_name").fetchone()
    except Exception:
        return False
    return bool(row and row["table_name"])


def _provision_teacher_account_v2(conn, *, teacher_id, staff_id, login, password_hash, full_name, legacy_login=""):
    """Best-effort shared account provisioning for new academy teachers."""
    if not _phase1_accounts_available(conn):
        return 0

    normalized_login = str(login or "").strip()
    if not normalized_login:
        return 0

    now = _utc_now_iso()
    account = conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE lower(btrim(login)) = lower(btrim(%s))
           OR (legacy_source_table = 'msi_staff' AND legacy_source_id = %s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (normalized_login, _as_int(staff_id)),
    ).fetchone()
    if account:
        account_id = int(account["id"] or 0)
        conn.execute(
            """
            UPDATE msi_v2.accounts
            SET login = %s,
                password_hash = %s,
                role = 'teacher',
                status = 'active',
                full_name = %s,
                legacy_source_table = 'msi_staff',
                legacy_source_id = %s,
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (normalized_login, password_hash, str(full_name or "").strip(), _as_int(staff_id), now, account_id),
        )
    else:
        inserted = conn.execute(
            """
            INSERT INTO msi_v2.accounts (
                login, password_hash, role, status, full_name,
                legacy_source_table, legacy_source_id, created_at, updated_at
            )
            VALUES (%s, %s, 'teacher', 'active', %s, 'msi_staff', %s, %s::timestamptz, %s::timestamptz)
            RETURNING id
            """,
            (normalized_login, password_hash, str(full_name or "").strip(), _as_int(staff_id), now, now),
        ).fetchone()
        account_id = int(inserted["id"] or 0) if inserted else 0

    if account_id:
        profile = conn.execute(
            """
            SELECT id
            FROM msi_v2.teacher_profiles
            WHERE account_id = %s OR teacher_id = %s OR upper(btrim(teacher_code)) = upper(btrim(%s))
            ORDER BY id ASC
            LIMIT 1
            """,
            (account_id, _as_int(teacher_id), normalized_login),
        ).fetchone()
        if profile:
            conn.execute(
                """
                UPDATE msi_v2.teacher_profiles
                SET account_id = %s,
                    teacher_id = %s,
                    teacher_code = %s,
                    legacy_login = %s,
                    status = 'active',
                    updated_at = %s::timestamptz
                WHERE id = %s
                """,
                (
                    account_id,
                    _as_int(teacher_id),
                    normalized_login,
                    str(legacy_login or "").strip(),
                    now,
                    int(profile["id"]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO msi_v2.teacher_profiles (
                    account_id, teacher_id, teacher_code, legacy_login, status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 'active', %s::timestamptz, %s::timestamptz)
                """,
                (
                    account_id,
                    _as_int(teacher_id),
                    normalized_login,
                    str(legacy_login or "").strip(),
                    now,
                    now,
                ),
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
        "target_lessons": ACADEMY_TARGET_LESSONS,
        "next_assignment": next_assignment,
    }


def list_academy_teachers():
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        _backfill_academy_teacher_accounts(conn)
        conn.commit()
        teacher_rows = conn.execute(
            """
            SELECT at.id, at.user_id, at.full_name, at.subject_id, at.subject_program_id,
                   COALESCE(subj.subject_name, '') AS subject,
                   COALESCE(sp.program_name, subj.subject_name, '') AS subject_program_name,
                   at.position, at.employment_type, at.telegram_username, at.phone, at.email,
                   at.academy_status, at.academy_start_date::text AS academy_start_date,
                   at.mentor_id, COALESCE(mentor.full_name, '') AS mentor_name,
                   at.department_head_id, COALESCE(head.full_name, '') AS department_head_name,
                   at.notes, at.promoted_teacher_id,
                   COALESCE(staff.login, '') AS login,
                   COALESCE(staff.teacher_id, 0) AS account_teacher_id,
                   at.created_at::text AS created_at, at.updated_at::text AS updated_at
            FROM msi_v2.academy_teachers at
            LEFT JOIN msi_v2.msi_staff staff ON staff.id = at.user_id
            LEFT JOIN msi_v2.subjects subj ON subj.id = at.subject_id
            LEFT JOIN msi_v2.subject_programs sp ON sp.id = at.subject_program_id
            LEFT JOIN msi_v2.teachers mentor ON mentor.id = at.mentor_id
            LEFT JOIN msi_v2.teachers head ON head.id = at.department_head_id
            ORDER BY at.updated_at DESC, at.id DESC
            """
        ).fetchall()
        assignment_rows = conn.execute(
            """
            SELECT ala.id, ala.academy_teacher_id, ala.sequence_no, ala.subject_program_id,
                   ala.curriculum_item_id, ala.lesson_number, ala.lesson_topic,
                   ala.assignment_type, ala.deadline_date::text AS deadline_date,
                   ala.session_datetime::text AS session_datetime,
                   ala.evaluator_id, COALESCE(eval.full_name, '') AS evaluator_name,
                   ala.focus_areas::text AS focus_areas_json,
                   ala.notes_to_trainee, ala.status,
                   COALESCE(spi.specification_points, '') AS specification_points,
                   COALESCE(spi.book_pages, '') AS book_pages,
                   ala.created_at::text AS created_at, ala.updated_at::text AS updated_at
            FROM msi_v2.academy_lesson_assignments ala
            LEFT JOIN msi_v2.teachers eval ON eval.id = ala.evaluator_id
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ala.curriculum_item_id
            ORDER BY ala.academy_teacher_id, ala.sequence_no ASC, ala.id ASC
            """
        ).fetchall()
        assessment_rows = conn.execute(
            """
            SELECT aa.id, aa.academy_teacher_id, aa.lesson_assignment_id,
                   aa.assessment_type, aa.lesson_number, aa.lesson_topic,
                   aa.evaluator_id, COALESCE(eval.full_name, '') AS evaluator_name,
                   aa.assessment_datetime::text AS assessment_datetime,
                   aa.session_type, aa.class_label,
                   aa.section_feedback::text AS section_feedback_json,
                   aa.teacher_guidance_compliance_score,
                   aa.timing_adherence_score,
                   aa.resource_familiarity_score,
                   aa.english_fluency_score,
                   aa.confidence_delivery_score,
                   aa.engagement_technique_score,
                   aa.weighted_overall_score,
                   aa.strengths, aa.areas_for_improvement,
                   aa.final_recommendation, aa.decision,
                   aa.created_by,
                   aa.created_at::text AS created_at, aa.updated_at::text AS updated_at
            FROM msi_v2.academy_assessments aa
            LEFT JOIN msi_v2.teachers eval ON eval.id = aa.evaluator_id
            ORDER BY aa.academy_teacher_id, aa.created_at ASC, aa.id ASC
            """
        ).fetchall()

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
        teachers.append(
            {
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
        )
    return teachers


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

        row = conn.execute(
            """
            INSERT INTO msi_v2.academy_teachers (
                user_id, full_name, subject_id, subject_program_id, position, employment_type,
                telegram_username, phone, email, academy_status, academy_start_date,
                mentor_id, department_head_id, notes, created_by, created_at, updated_at
            )
            VALUES (
                NULLIF(%s::bigint, 0), %s, %s, %s, %s, %s,
                %s, %s, %s, 'in_training', NULLIF(%s, '')::date,
                NULLIF(%s::bigint, 0), NULLIF(%s::bigint, 0), %s, %s, %s::timestamptz, %s::timestamptz
            )
            RETURNING id
            """,
            (
                staff_id,
                normalized_name,
                int(program["subject_id"]),
                int(program["id"]),
                str(position or "Trainee Teacher").strip() or "Trainee Teacher",
                str(employment_type or "academy").strip() or "academy",
                str(telegram_username or "").strip(),
                str(phone or "").strip(),
                str(email or "").strip(),
                str(academy_start_date or "").strip(),
                _as_int(mentor_id),
                _as_int(department_head_id),
                str(notes or "").strip(),
                str(created_by or "").strip(),
                now,
                now,
            ),
        ).fetchone()
        academy_teacher_id = int(row["id"])
        for sequence_no, lesson in enumerate(lessons, start=1):
            conn.execute(
                """
                INSERT INTO msi_v2.academy_lesson_assignments (
                    academy_teacher_id, subject_id, subject_program_id, curriculum_item_id,
                    sequence_no, lesson_number, lesson_topic, assignment_type,
                    focus_areas, created_by, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, 'full_practice_lesson',
                    %s::jsonb, %s, %s::timestamptz, %s::timestamptz
                )
                """,
                (
                    academy_teacher_id,
                    int(program["subject_id"]),
                    int(program["id"]),
                    int(lesson["id"]),
                    sequence_no,
                    str(lesson["lesson_number"] or ""),
                    str(lesson["title"] or ""),
                    json.dumps([]),
                    str(created_by or "").strip(),
                    now,
                    now,
                ),
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
        existing = conn.execute(
            """
            SELECT id, academy_teacher_id, session_datetime::text AS session_datetime
            FROM msi_v2.academy_lesson_assignments
            WHERE id = %s
            """,
            (parsed_assignment_id,),
        ).fetchone()
        if not existing:
            return False, "Assignment not found."
        old_session_datetime = str(existing["session_datetime"] or "").strip()
        conn.execute(
            """
            UPDATE msi_v2.academy_lesson_assignments
            SET assignment_type = COALESCE(NULLIF(%s, ''), assignment_type),
                deadline_date = NULLIF(%s, '')::date,
                session_datetime = NULLIF(%s, '')::timestamptz,
                evaluator_id = NULLIF(%s::bigint, 0),
                focus_areas = %s::jsonb,
                notes_to_trainee = %s,
                status = %s,
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (
                str(assignment_type or "").strip(),
                str(deadline_date or "").strip(),
                str(session_datetime or "").strip(),
                _as_int(evaluator_id),
                json.dumps(focus_areas if isinstance(focus_areas, list) else []),
                str(notes_to_trainee or "").strip(),
                normalized_status,
                now,
                parsed_assignment_id,
            ),
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
    return conn.execute(
        """
        SELECT id, academy_teacher_id, lesson_number, lesson_topic, evaluator_id
        FROM msi_v2.academy_lesson_assignments
        WHERE id = %s AND academy_teacher_id = %s
        LIMIT 1
        """,
        (_as_int(lesson_assignment_id), _as_int(academy_teacher_id)),
    ).fetchone()


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

        conn.execute(
            """
            INSERT INTO msi_v2.academy_assessments (
                academy_teacher_id, lesson_assignment_id, assessment_type,
                lesson_number, lesson_topic, evaluator_id, assessment_datetime,
                session_type, class_label, section_feedback,
                teacher_guidance_compliance_score, timing_adherence_score,
                resource_familiarity_score, english_fluency_score,
                confidence_delivery_score, engagement_technique_score,
                weighted_overall_score, strengths, areas_for_improvement,
                final_recommendation, decision, created_by, created_at, updated_at
            )
            VALUES (
                %s, %s, %s,
                %s, %s, NULLIF(%s::bigint, 0), NULLIF(%s, '')::timestamptz,
                %s, %s, %s::jsonb,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s::timestamptz, %s::timestamptz
            )
            """,
            (
                parsed_teacher_id,
                parsed_assignment_id,
                str(assessment_type or "academy_practice_lesson").strip(),
                str(assignment["lesson_number"] or ""),
                str(assignment["lesson_topic"] or ""),
                evaluator,
                str(assessment_datetime or "").strip(),
                str(session_type or "training_simulation").strip(),
                str(class_label or "").strip(),
                _json_dumps(section_feedback if isinstance(section_feedback, dict) else {}),
                safe_scores["teacher_guidance_compliance_score"],
                safe_scores["timing_adherence_score"],
                safe_scores["resource_familiarity_score"],
                safe_scores["english_fluency_score"],
                safe_scores["confidence_delivery_score"],
                safe_scores["engagement_technique_score"],
                weighted_score,
                str(strengths or "").strip(),
                str(areas_for_improvement or "").strip(),
                str(final_recommendation or "").strip(),
                normalized_decision,
                str(created_by or "").strip(),
                now,
                now,
            ),
        )
        assignment_status = (
            "passed"
            if normalized_decision in {"passed", "ready_for_final_evaluation", "approved_for_active_teacher"}
            else "needs_improvement"
        )
        conn.execute(
            """
            UPDATE msi_v2.academy_lesson_assignments
            SET status = %s, updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (assignment_status, now, parsed_assignment_id),
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
            conn.execute(
                """
                UPDATE msi_v2.academy_teachers
                SET academy_status = %s, updated_at = %s::timestamptz
                WHERE id = %s
                """,
                (next_status, now, parsed_teacher_id),
            )
        else:
            conn.execute(
                "UPDATE msi_v2.academy_teachers SET updated_at = %s::timestamptz WHERE id = %s",
                (now, parsed_teacher_id),
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
        existing = conn.execute(
            "SELECT id FROM msi_v2.academy_teachers WHERE id = %s",
            (parsed_teacher_id,),
        ).fetchone()
        if not existing:
            return False, "Academy teacher not found."
        conn.execute(
            """
            UPDATE msi_v2.academy_teachers
            SET academy_status = %s, updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (normalized_status, now, parsed_teacher_id),
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
                igcse_evidence=f"Teacher Academy: {supervised_lessons}/{ACADEMY_TARGET_LESSONS} assessed lessons.",
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
        conn.execute(
            """
            UPDATE msi_v2.academy_teachers
            SET academy_status = 'approved',
                promoted_teacher_id = NULLIF(%s::bigint, 0),
                updated_at = %s::timestamptz
            WHERE id = %s
            """,
            (promoted_teacher_id, now, _as_int(academy_teacher_id)),
        )
        conn.commit()
    return True, ""


__all__ = [
    "ACADEMY_TARGET_LESSONS",
    "RUBRIC_WEIGHTS",
    "list_academy_teachers",
    "create_academy_teacher",
    "update_assignment",
    "add_assessment",
    "update_academy_status",
    "promote_academy_teacher",
]
