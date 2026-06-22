"""Student profile lookup helpers."""

from shared.academics import canonical
from shared.db import queries
from shared.identity.common import connect
from shared.identity.storage import init_storage
from shared.identity.teachers import get_teacher_name_by_group


def split_name(full_name):
    parts = [part for part in str(full_name or "").strip().split() if part]
    if not parts:
        return {"surname": "", "name": ""}
    if len(parts) == 1:
        return {"surname": parts[0], "name": ""}
    return {"surname": parts[0], "name": " ".join(parts[1:])}


def extract_auto_student_context(full_name):
    context = {"groups": [], "group": "", "classmates": []}
    normalized_full_name = canonical.normalize_text(full_name)
    if not normalized_full_name:
        return context

    try:
        with connect() as conn:
            enrollment = conn.execute(
                """
                SELECT e.full_name, g.name AS group_name, sub.name AS subject_name
                FROM academic_enrollments e
                JOIN academic_groups   g   ON g.id   = e.group_id
                JOIN academic_subjects sub ON sub.id = e.subject_id
                WHERE e.full_name_norm = %s AND e.active = 1
                LIMIT 1
                """,
                (normalized_full_name,),
            ).fetchone()

            if not enrollment:
                return context

            group_name = str(enrollment["group_name"] or "").strip()
            subject_name = str(enrollment["subject_name"] or "").strip()

            classmate_rows = conn.execute(
                """
                SELECT e.full_name FROM academic_enrollments e
                JOIN academic_groups   g   ON g.id   = e.group_id
                JOIN academic_subjects sub ON sub.id = e.subject_id
                WHERE g.name = %s AND sub.name = %s AND e.active = 1
                  AND e.full_name_norm != %s
                ORDER BY e.full_name
                """,
                (group_name, subject_name, normalized_full_name),
            ).fetchall()

        classmates = [str(r["full_name"]).strip() for r in classmate_rows if r["full_name"]]
        context["groups"] = [group_name] if group_name else []
        context["group"] = group_name
        context["classmates"] = classmates
    except Exception:
        pass

    return context


def get_admin_student_profile(student_row_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        row = queries.get_student_admin_row(conn, student_row_id)
    if not row:
        return None

    full_name = str(row["full_name"]).strip()
    auto_context = extract_auto_student_context(full_name)
    teacher_name = get_teacher_name_by_group(auto_context.get("group", ""))
    split = split_name(full_name)

    student_row_id = int(row["id"])
    student_code = str(row["student_id"]).strip()

    return {
        "id": student_row_id,
        "student_row_id": student_row_id,
        "studentRowId": student_row_id,
        "full_name": full_name,
        "surname": split["surname"],
        "name": split["name"],
        "student_id": student_code,
        "student_code": student_code,
        "studentCode": student_code,
        "password": str(row["password"]).strip(),
        "subjects": str(row["subjects"]).strip(),
        "photo_url": str(row["photo_url"] or "").strip(),
        "profile_description": str(row["profile_description"] or "").strip(),
        "class_name": str(row["class_name"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip() or canonical.DEFAULT_SCHOOL_NAME,
        "group": str(auto_context.get("group", "")).strip(),
        "groups": list(auto_context.get("groups", [])),
        "classmates": list(auto_context.get("classmates", [])),
        "teacher_name": teacher_name,
    }


def get_dashboard_student_profile(
    student_db_id,
    full_name,
    group_name,
    subject_name,
    load_dataset=None,
):
    _ = subject_name, load_dataset
    profile = {
        "full_name": str(full_name or "").strip(),
        "photo_url": "",
        "profile_description": "",
        "class_name": "",
        "school_name": canonical.DEFAULT_SCHOOL_NAME,
        "group_name": str(group_name or "").strip(),
        "teacher_name": "",
        "classmates": [],
    }

    if isinstance(student_db_id, int) and student_db_id > 0:
        init_storage()
        with connect() as conn:
            row = queries.get_student_admin_row(conn, student_db_id)
        if row:
            profile["photo_url"] = str(row["photo_url"] or "").strip()
            profile["profile_description"] = str(row["profile_description"] or "").strip()
            profile["class_name"] = str(row["class_name"] or "").strip()
            profile["school_name"] = (
                str(row["school_name"] or "").strip() or canonical.DEFAULT_SCHOOL_NAME
            )

    profile["teacher_name"] = get_teacher_name_by_group(group_name)

    auto_context = extract_auto_student_context(full_name)
    if auto_context.get("classmates"):
        profile["classmates"] = auto_context["classmates"]
    return profile


def get_student_db_id_by_enrollment_id(enrollment_id, school_code=None):
    try:
        normalized_enrollment_id = int(enrollment_id)
    except (TypeError, ValueError):
        return None
    if normalized_enrollment_id <= 0:
        return None

    init_storage()
    with connect() as conn:
        mapping = queries.get_students_sheet_map_row(
            conn,
            normalized_enrollment_id,
            school_key=canonical.normalize_school_code(school_code),
        )
    if not mapping:
        return None
    try:
        return int(mapping["student_row_id"])
    except (TypeError, ValueError, KeyError):
        return None


__all__ = [
    "extract_auto_student_context",
    "get_admin_student_profile",
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "split_name",
]
