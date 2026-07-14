"""Groups domain services."""


from backend.modules.organization import canonical
from backend.modules.academics.groups import repository as group_repository
from backend.modules.organization import contracts as organization_contract
from backend.modules.academics.curriculum import repository as curriculum_repository
from backend.modules.academics.timetable import repository as timetable_repository
from backend.modules.academics.foundation import (
    _connect, _normalize, _canonical_subject_name, _mint_legacy_id,
    _resolve_group, _next_student_code,
)

def group_belongs_to_school(group_name, school_code):
    normalized_group = str(group_name or "").strip()
    normalized_school = canonical.normalize_school_code(school_code, default="")
    if not normalized_group or not normalized_school or normalized_school == "all":
        return True
    try:
        with _connect() as conn:
            return group_repository.group_belongs_to_school(
                conn,
                normalized_group,
                normalized_school,
            )
    except Exception:
        return True


def list_academic_admin_rows(*, include_heavy=True, include_groups=True):
    with _connect() as conn:
        schools = [dict(row) for row in organization_contract.list_school_rows(conn)]
        classes = [dict(row) for row in organization_contract.list_class_rows(conn)]
        subjects = [dict(row) for row in organization_contract.list_subject_rows(conn)]
        groups = (
            [dict(row) for row in group_repository.list_group_rows(conn)]
            if include_groups
            else []
        )
        enrollment_summary = dict(group_repository.get_enrollment_summary_row(conn) or {})
        duplicate_names = int(enrollment_summary.get("active_enrollments") or 0) - int(
            enrollment_summary.get("active_unique_students") or 0
        )
        enrollment_summary["active_duplicate_enrollments"] = max(0, duplicate_names)
        enrollments = []
        lessons = []
        schedules = []
        sessions = []
        curriculum_programs = []
        curriculum_items = []
        if include_heavy:
            enrollments = [dict(row) for row in group_repository.list_enrollment_rows(conn)]
            lessons = [dict(row) for row in curriculum_repository.list_lesson_rows(conn)]
            schedules = [dict(row) for row in timetable_repository.list_schedule_rows(conn)]
            sessions = [dict(row) for row in timetable_repository.list_session_rows(conn)]
            curriculum_programs = [dict(row) for row in curriculum_repository.list_curriculum_program_rows(conn)]
            curriculum_items = [dict(row) for row in curriculum_repository.list_curriculum_item_rows(conn)]
        return {
            "schools": schools,
            "classes": classes,
            "subjects": subjects,
            "groups": groups,
            "enrollments": enrollments,
            "lessons": lessons,
            "schedules": schedules,
            "sessions": sessions,
            "curriculum_programs": curriculum_programs,
            "curriculum_items": curriculum_items,
            "enrollment_summary": enrollment_summary,
        }


def create_group_from_program(
    school_code, program_subject_key, group_name, group_code="", *, class_id=0, set_name="Set 1"
):
    group_name = str(group_name or "Group").strip() or "Group"
    with _connect() as conn:
        school = organization_contract.get_school_by_key(conn, school_code)
        if not school:
            raise ValueError("Client school was not found.")
        program = curriculum_repository.get_subject_program_by_subject_key(conn, program_subject_key)
        if not program:
            raise ValueError("Subject program was not found.")
        selected_class = None
        if int(class_id or 0) > 0:
            selected_class = organization_contract.get_class(conn, int(class_id))
            if not selected_class or int(selected_class["school_id"]) != int(school["id"]):
                raise ValueError("Class was not found in the selected school.")
            group_name = str(selected_class["class_name"])
        else:
            selected_class = organization_contract.get_class_by_school_and_name(
                conn, int(school["id"]), group_name
            )
            if not selected_class:
                selected_class = organization_contract.insert_class(
                    conn, int(school["id"]), group_name, group_code
                )
        existing = group_repository.get_existing_group(conn, int(school["id"]), int(program["id"]), group_name)
        if existing:
            group_repository.update_group_code(conn, int(existing["id"]), group_code)
            group_repository.update_group_class(
                conn, int(existing["id"]), int(selected_class["id"]), set_name
            )
            group_v2_id = int(existing["id"])
        else:
            legacy_group_id = _mint_legacy_id(conn, "groups", "legacy_group_id")
            inserted_group = group_repository.insert_group(
                conn,
                int(school["id"]),
                int(program["id"]),
                group_name,
                group_code,
                legacy_group_id,
                class_id=int(selected_class["id"]),
                set_name=set_name,
            )
            group_v2_id = int(inserted_group["id"])
        timetable_repository.ensure_curriculum_lesson_sessions(conn, group_v2_id)
        conn.commit()


def create_student_with_enrollment(full_name, group_id):
    """Create a student login identity and enroll them into a group.

    Reuses an existing student (same normalized name + school) instead of minting
    a duplicate code, then writes a ``group_students`` row with freshly minted
    legacy ids so the student immediately shows in the group's gradebook.
    """
    from backend.modules.identity.service import provision_student_account

    full_name = str(full_name or "").strip()
    group_id = int(group_id or 0)
    if not full_name:
        raise ValueError("Student full name is required.")
    if group_id <= 0:
        raise ValueError("A group is required.")

    with _connect() as conn:
        group = _resolve_group(conn, group_id)
        if not group:
            raise ValueError("Group was not found.")

        v2_group_id = int(group["id"])
        school_id = int(group["school_id"])
        school_code = canonical.normalize_school_code(group["school_key"])
        school_name = str(group["school_name"] or canonical.school_display_name(school_code))
        subject_name = _canonical_subject_name(group["subject_name"])

        # Reuse an existing login for the same person (same normalized name +
        # school) so a person keeps one login across subjects/groups.
        target_norm = _normalize(full_name)
        existing_student = None
        for candidate in group_repository.list_students_by_school_id(conn, school_id):
            if _normalize(candidate["full_name"]) == target_norm:
                existing_student = candidate
                break

        if existing_student:
            reused = True
            student_id = int(existing_student["id"])
            student_code = str(existing_student["student_code"] or "")
            default_password = ""  # unknown for an existing login
        else:
            reused = False
            student_code = _next_student_code(conn, canonical.student_code_prefix(school_code))
            default_password = student_code
            legacy_student_row_id = _mint_legacy_id(conn, "students", "legacy_student_row_id")
            inserted = group_repository.insert_student(
                conn,
                student_code=student_code,
                full_name=full_name,
                school_id=school_id,
                legacy_student_row_id=legacy_student_row_id,
            )
            student_id = int(inserted["id"])
            account_id = provision_student_account(
                conn,
                student_id=student_id,
                login=student_code,
                initial_password=default_password,
                full_name=full_name,
                school_id=school_id,
            )
            if account_id <= 0:
                raise RuntimeError("Unable to provision the student account.")

        next_enrollment_id = _mint_legacy_id(conn, "group_students", "legacy_enrollment_id")
        next_dashboard_id = _mint_legacy_id(conn, "group_students", "legacy_public_dashboard_id")
        enrollment = group_repository.upsert_group_student_enrollment(
            conn,
            group_id=v2_group_id,
            student_id=student_id,
            legacy_enrollment_id=next_enrollment_id,
            legacy_public_dashboard_id=next_dashboard_id,
        )
        if group.get("class_id"):
            organization_contract.upsert_class_student(conn, int(group["class_id"]), student_id)
        enrollment_id = int(enrollment["legacy_enrollment_id"] or next_enrollment_id) if enrollment else next_enrollment_id
        conn.commit()

    return {
        "studentRowId": int(student_id),
        "enrollmentId": int(enrollment_id),
        "studentCode": student_code,
        "password": default_password,
        "reused": reused,
        "fullName": full_name,
        "schoolName": school_name,
        "subjectName": subject_name,
        "groupName": str(group["group_name"]),
    }
