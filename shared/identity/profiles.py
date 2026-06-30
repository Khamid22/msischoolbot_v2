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


def extract_auto_student_context(full_name, student_row_id=None):
    # Resolve the student's active group + classmates. Prefer the student's
    # legacy id (reliable); fall back to a name match for name-only callers.
    # The DB collation does not lowercase Cyrillic via lower(), so name matching
    # is normalized in Python instead.
    context = {"groups": [], "group": "", "classmates": []}
    normalized_full_name = canonical.normalize_text(full_name)
    has_id = isinstance(student_row_id, int) and student_row_id > 0
    if not has_id and not normalized_full_name:
        return context

    try:
        with connect() as conn:
            enrollment = None
            if has_id:
                enrollment = conn.execute(
                    """
                    SELECT gs.group_id, gs.student_id, g.group_name
                    FROM msi_v2.group_students gs
                    JOIN msi_v2.students st ON st.id = gs.student_id
                    JOIN msi_v2.groups g ON g.id = gs.group_id
                    WHERE st.legacy_student_row_id = %s AND gs.enrollment_status = 'active'
                    LIMIT 1
                    """,
                    (student_row_id,),
                ).fetchone()
            if not enrollment and normalized_full_name:
                for row in conn.execute(
                    """
                    SELECT gs.group_id, gs.student_id, g.group_name, st.full_name
                    FROM msi_v2.group_students gs
                    JOIN msi_v2.students st ON st.id = gs.student_id
                    JOIN msi_v2.groups g ON g.id = gs.group_id
                    WHERE gs.enrollment_status = 'active'
                    """
                ).fetchall():
                    if canonical.normalize_text(row["full_name"]) == normalized_full_name:
                        enrollment = row
                        break

            if not enrollment:
                return context

            group_name = str(enrollment["group_name"] or "").strip()
            self_student_id = int(enrollment["student_id"])

            classmate_rows = conn.execute(
                """
                SELECT st.full_name
                FROM msi_v2.group_students gs
                JOIN msi_v2.students st ON st.id = gs.student_id
                WHERE gs.group_id = %s AND gs.enrollment_status = 'active'
                  AND gs.student_id != %s
                ORDER BY st.full_name
                """,
                (int(enrollment["group_id"]), self_student_id),
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
    student_row_id = int(row["id"])
    auto_context = extract_auto_student_context(full_name, student_row_id=student_row_id)
    teacher_name = get_teacher_name_by_group(auto_context.get("group", ""))
    split = split_name(full_name)
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

    auto_context = extract_auto_student_context(
        full_name,
        student_row_id=student_db_id if isinstance(student_db_id, int) and student_db_id > 0 else None,
    )
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
