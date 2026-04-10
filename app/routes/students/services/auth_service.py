import os
import threading
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.storage import queries

_OWNER_LOGIN = (os.environ.get("OWNER_ADMIN_LOGIN", "admin") or "admin").strip()
_OWNER_PASSWORD = (os.environ.get("OWNER_ADMIN_PASSWORD", "Msischool2026") or "Msischool2026").strip()
_DEFAULT_SCHOOL_NAME = "School 5"
_DEFAULT_SCHOOL_CODE = "school5"
_SCHOOL_DISPLAY_NAMES = {
    "school5": "School 5",
    "sehriyo": "Sehriyo",
}
_SCHOOL_STUDENT_PREFIX = {
    "school5": "MSI",
    "sehriyo": "MSIS",
}
_ADMIN_SCHOOL_FILTER_ALL = "all"

_DB_LOCK = threading.Lock()
_SYNC_LOCK = threading.Lock()
_STORAGE_READY = False


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return queries.connect_auth_db()


def init_storage():
    global _STORAGE_READY
    if _STORAGE_READY:
        return

    with _DB_LOCK:
        if _STORAGE_READY:
            return
        with _connect() as conn:
            queries.create_tables(conn)
            queries.ensure_admins_schema(conn)
            _ensure_students_schema(conn)
            queries.ensure_lesson_catalog_schema(conn)
            queries.ensure_subject_summaries_schema(conn)
            queries.ensure_resources_schema(conn)
            queries.ensure_resource_comments_schema(conn)
            queries.ensure_chat_schema(conn)
            queries.ensure_default_resource_types(conn, _utc_now_iso())
            _ensure_owner_admin(conn)
            conn.commit()
        _STORAGE_READY = True


def _ensure_students_schema(conn):
    queries.ensure_students_schema(conn)
    queries.ensure_students_sheet_map_schema(conn)


def _ensure_owner_admin(conn):
    desired_login = _OWNER_LOGIN
    desired_password_hash = generate_password_hash(_OWNER_PASSWORD)

    # If the desired login already exists, enforce it as the single owner account.
    existing_desired_login = queries.get_admin_id_by_login(conn, desired_login)
    if existing_desired_login:
        target_id = int(existing_desired_login["id"])
        conn.execute(
            """
            UPDATE admins
            SET password_hash = ?, role = 'owner', is_owner = 1
            WHERE id = ?
            """,
            (desired_password_hash, target_id),
        )
        conn.execute(
            """
            UPDATE admins
            SET role = 'admin', is_owner = 0
            WHERE is_owner = 1 AND id != ?
            """,
            (target_id,),
        )
        return

    # Otherwise migrate an existing owner account (if any) to the desired login.
    owner_row = conn.execute(
        """
        SELECT id
        FROM admins
        WHERE is_owner = 1
        ORDER BY id ASC
        LIMIT 1
        """
    ).fetchone()
    if owner_row:
        owner_id = int(owner_row["id"])
        conn.execute(
            """
            UPDATE admins
            SET login = ?, password_hash = ?, role = 'owner', is_owner = 1
            WHERE id = ?
            """,
            (desired_login, desired_password_hash, owner_id),
        )
        conn.execute(
            """
            UPDATE admins
            SET role = 'admin', is_owner = 0
            WHERE is_owner = 1 AND id != ?
            """,
            (owner_id,),
        )
        return

    queries.insert_owner_admin(
        conn,
        desired_login,
        desired_password_hash,
        _utc_now_iso(),
    )


def detect_login_role(login):
    normalized = (login or "").strip().casefold()
    if normalized == "admin" or normalized.startswith("staff"):
        return "admin"
    if normalized.startswith("msi"):
        return "student"
    return ""


def verify_admin_credentials(login, password):
    init_storage()
    with _connect() as conn:
        row = queries.get_admin_credentials_row(
            conn,
            (login or "").strip(),
        )

    if not row:
        return None
    if not check_password_hash(row["password_hash"], password or ""):
        return None

    return {
        "id": int(row["id"]),
        "login": str(row["login"]),
        "role": str(row["role"]),
        "is_owner": bool(row["is_owner"]),
    }


def verify_student_credentials(login, password):
    init_storage()
    student_login = (login or "").strip().upper()

    with _connect() as conn:
        row = queries.get_student_login_row(conn, student_login)

    if not row:
        return None
    if not check_password_hash(row["password_hash"], password or ""):
        return None
    if row["sheet_student_id"] is None:
        return None

    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "student_id": str(row["student_id"]),
        "subjects": str(row["subjects"]),
        "school_code": _normalize_school_code(row["school_key"]),
        "telegram_user_id": (
            int(row["telegram_user_id"])
            if row["telegram_user_id"] is not None
            else None
        ),
        "sheet_student_id": int(row["sheet_student_id"]),
    }


def _normalize_school_code(value):
    normalized = str(value or _DEFAULT_SCHOOL_CODE).strip().casefold()
    if normalized in {"school_5", "school-5", "school 5", "school5"}:
        return "school5"
    if normalized in {"sehriyo", "sehriyo school"}:
        return "sehriyo"
    return normalized or _DEFAULT_SCHOOL_CODE


def _school_display_name(school_code):
    normalized_code = _normalize_school_code(school_code)
    return _SCHOOL_DISPLAY_NAMES.get(normalized_code, _DEFAULT_SCHOOL_NAME)


def _student_code_prefix_for_school(school_code):
    normalized_code = _normalize_school_code(school_code)
    return _SCHOOL_STUDENT_PREFIX.get(normalized_code, "MSI")


def _normalize_admin_school_filter(value):
    normalized = str(value or _ADMIN_SCHOOL_FILTER_ALL).strip().casefold()
    if normalized in _SCHOOL_DISPLAY_NAMES:
        return normalized
    return _ADMIN_SCHOOL_FILTER_ALL


def _next_student_code(conn, school_code):
    return queries.get_next_student_code(
        conn,
        _student_code_prefix_for_school(school_code),
    )


def _normalize_subject_label(subject_name):
    normalized = (subject_name or "").strip().casefold()
    if normalized in {"igcse mathematics a", "mathematics", "math"}:
        return "Math"
    if normalized in {"general english", "english"}:
        return "English"
    return (subject_name or "").strip()


def _normalize_name(value):
    return " ".join(str(value or "").strip().casefold().split())


def _split_subjects(subjects_value):
    normalized = str(subjects_value or "").replace(";", ",")
    parts = [part.strip() for part in normalized.split(",")]
    cleaned = [part for part in parts if part]
    return cleaned


def sync_students_from_dataset(dataset):
    init_storage()
    students = dataset.get("students", []) if isinstance(dataset, dict) else []
    if not isinstance(students, list):
        return {"added": 0, "updated": 0}

    added = 0
    updated = 0
    active_sheet_ids_by_school = {}

    with _DB_LOCK:
        with _connect() as conn:
            for student in students:
                if not isinstance(student, dict):
                    continue

                sheet_student_id = student.get("id")
                if not isinstance(sheet_student_id, int):
                    continue

                full_name = str(student.get("fullName", "")).strip()
                if not full_name:
                    continue

                subject_label = _normalize_subject_label(student.get("subject", ""))
                if not subject_label:
                    subject_label = "Unknown"
                school_code = _normalize_school_code(student.get("schoolCode", "school5"))
                school_name = _school_display_name(school_code)
                active_sheet_ids_by_school.setdefault(school_code, set()).add(sheet_student_id)

                mapping = queries.get_students_sheet_map_row(
                    conn,
                    sheet_student_id,
                    school_key=school_code,
                )

                if mapping:
                    student_row_id = int(mapping["student_row_id"])
                    queries.update_student_profile(
                        conn,
                        full_name,
                        subject_label,
                        school_name,
                        student_row_id,
                        school_code,
                    )
                    updated += 1
                    continue

                student_code = _next_student_code(conn, school_code)
                default_password = student_code
                student_row_id = queries.insert_student(
                    conn,
                    full_name,
                    student_code,
                    default_password,
                    subject_label,
                    school_name,
                    school_code,
                )
                queries.insert_student_auth(
                    conn,
                    student_row_id,
                    generate_password_hash(default_password),
                    _utc_now_iso(),
                )
                queries.insert_students_sheet_map(
                    conn,
                    sheet_student_id,
                    student_row_id,
                    school_code,
                )
                added += 1

            # Remove stale students whose sheet IDs are no longer present.
            stale_student_row_ids = []
            for school_code, active_sheet_ids in active_sheet_ids_by_school.items():
                mapping_rows = queries.list_students_sheet_map_rows_by_school(
                    conn,
                    school_key=school_code,
                )
                for mapping_row in mapping_rows:
                    mapped_sheet_student_id = mapping_row["sheet_student_id"]
                    if mapped_sheet_student_id in active_sheet_ids:
                        continue
                    stale_student_row_ids.append(int(mapping_row["student_row_id"]))

            if stale_student_row_ids:
                queries.delete_students_by_ids(conn, stale_student_row_ids)

            conn.commit()

    return {"added": added, "updated": updated}


def sync_students_if_needed(load_dataset, school_code = None, force_refresh = False):
    _ = force_refresh
    init_storage()
    normalized_school_code = _normalize_school_code(
        school_code or os.environ.get("ACTIVE_SCHOOL_CODE", _DEFAULT_SCHOOL_CODE)
    )

    with _SYNC_LOCK:
        try:
            dataset, load_error = load_dataset(
                school_code=normalized_school_code,
                force_refresh=True,
            )
        except TypeError:
            dataset, load_error = load_dataset()
        if load_error or not dataset:
            return {
                "synced": False,
                "error": load_error or "Unable to load Google Sheets data.",
                "added": 0,
                "updated": 0,
            }

        sync_result = sync_students_from_dataset(dataset)

        return {
            "synced": True,
            "error": "",
            "added": int(sync_result.get("added", 0)),
            "updated": int(sync_result.get("updated", 0)),
        }


def list_students_for_admin(school_filter = _ADMIN_SCHOOL_FILTER_ALL):
    init_storage()
    normalized_filter = _normalize_admin_school_filter(school_filter)
    school_name = (
        _school_display_name(normalized_filter)
        if normalized_filter != _ADMIN_SCHOOL_FILTER_ALL
        else ""
    )
    with _connect() as conn:
        rows = queries.list_students_for_admin_rows(conn, school_name=school_name)

    grouped = {}
    for row in rows:
        full_name = str(row["full_name"]).strip()
        student_school_name = (
            str(row["school_name"] if row["school_name"] is not None else "").strip()
            or _DEFAULT_SCHOOL_NAME
        )
        key = f"{student_school_name}|{_normalize_name(full_name)}"
        item = grouped.get(key)

        row_subjects = _split_subjects(row["subjects"])
        if item is None:
            grouped[key] = {
                "id": int(row["id"]),
                "full_name": full_name,
                "student_id": str(row["student_id"]),
                "password": str(row["password"]),
                "subjects_set": set(row_subjects),
                "school_name": student_school_name,
                "telegram_user_id": (
                    int(row["telegram_user_id"])
                    if row["telegram_user_id"] is not None
                    else None
                ),
            }
            continue

        item["subjects_set"].update(row_subjects)

    results = []
    grouped_items = sorted(
        grouped.values(),
        key=lambda item: (
            str(item.get("school_name", "")).casefold(),
            int(item.get("id", 0)),
            _normalize_name(item.get("full_name", "")),
        ),
    )
    for index, item in enumerate(grouped_items, start=1):
        subjects_sorted = sorted(item["subjects_set"], key=lambda value: value.casefold())
        results.append(
            {
                "display_id": index,
                "id": int(item["id"]),
                "full_name": str(item["full_name"]),
                "student_id": str(item["student_id"]),
                "password": str(item["password"]),
                "subjects": ", ".join(subjects_sorted),
                "school_name": str(item.get("school_name", "")).strip() or _DEFAULT_SCHOOL_NAME,
                "telegram_user_id": item["telegram_user_id"],
            }
        )
    return results


def update_student_admin_profile(
    student_row_id,
    photo_url,
    profile_description,
    class_name,
    school_name,
    teacher_name,
):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            existing = queries.get_student_admin_row(conn, student_row_id)
            if not existing:
                return False

            queries.update_student_admin_profile(
                conn,
                student_row_id,
                str(photo_url or "").strip(),
                str(profile_description or "").strip(),
                str(class_name or "").strip(),
                str(school_name or "").strip(),
                str(teacher_name or "").strip(),
            )
            conn.commit()
    return True


def list_teachers():
    init_storage()
    with _connect() as conn:
        rows = queries.list_teachers_rows(conn)

    results = []
    for row in rows:
        results.append(
            {
                "id": int(row["id"]),
                "full_name": str(row["full_name"]),
                "pay_rate": float(row["pay_rate"] or 0),
                "assigned_group": str(row["assigned_group"]),
            }
        )
    return results


def get_teacher_by_id(teacher_id):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        row = queries.get_teacher_by_id_row(conn, teacher_id)
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "pay_rate": float(row["pay_rate"] or 0),
        "assigned_group": str(row["assigned_group"]),
    }


def upsert_teacher(full_name, pay_rate, assigned_group):
    normalized_name = str(full_name or "").strip()
    normalized_group = str(assigned_group or "").strip()
    if not normalized_name or not normalized_group:
        return False

    try:
        safe_pay_rate = float(pay_rate)
    except (TypeError, ValueError):
        return False

    if safe_pay_rate < 0:
        safe_pay_rate = 0

    init_storage()
    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            queries.insert_teacher_row(
                conn,
                normalized_name,
                safe_pay_rate,
                normalized_group,
                now,
                now,
            )
            conn.commit()
    return True


def update_teacher_by_id(teacher_id, full_name, pay_rate, assigned_group):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return False, "Teacher not found."

    normalized_name = str(full_name or "").strip()
    normalized_group = str(assigned_group or "").strip()
    if not normalized_name or not normalized_group:
        return False, "Teacher full name and group are required."

    try:
        safe_pay_rate = float(pay_rate)
    except (TypeError, ValueError):
        return False, "Pay rate must be a number."
    if safe_pay_rate < 0:
        safe_pay_rate = 0

    init_storage()
    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            existing = queries.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False, "Teacher not found."

            group_owner = queries.get_teacher_by_group_row(conn, normalized_group)
            if group_owner and int(group_owner["id"]) != teacher_id:
                return False, "Selected group is already assigned to another teacher."

            queries.update_teacher_row_by_id(
                conn,
                teacher_id,
                normalized_name,
                safe_pay_rate,
                normalized_group,
                now,
            )
            conn.commit()
    return True, ""


def delete_teacher_by_id(teacher_id):
    if not isinstance(teacher_id, int) or teacher_id <= 0:
        return False

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            existing = queries.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False
            queries.delete_teacher_row_by_id(conn, teacher_id)
            conn.commit()
    return True


def get_teacher_name_by_group(group_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return ""

    init_storage()
    with _connect() as conn:
        row = queries.get_teacher_by_group_row(conn, normalized_group)
    if not row:
        return ""
    return str(row["full_name"]).strip()


def assign_teacher_to_group(group_name, teacher_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return False

    normalized_teacher = str(teacher_name or "").strip()
    init_storage()
    now = _utc_now_iso()

    with _DB_LOCK:
        with _connect() as conn:
            if not normalized_teacher:
                queries.delete_teacher_by_group(conn, normalized_group)
                conn.commit()
                return True

            existing_teacher = queries.get_teacher_by_full_name_row(
                conn,
                normalized_teacher,
            )
            pay_rate = (
                float(existing_teacher["pay_rate"])
                if existing_teacher is not None
                else 0.0
            )
            queries.insert_teacher_row(
                conn,
                normalized_teacher,
                pay_rate,
                normalized_group,
                now,
                now,
            )
            conn.commit()
    return True


def _split_name(full_name):
    parts = [part for part in str(full_name or "").strip().split() if part]
    if not parts:
        return {"surname": "", "name": ""}
    if len(parts) == 1:
        return {"surname": parts[0], "name": ""}
    return {"surname": parts[0], "name": " ".join(parts[1:])}


def _extract_auto_student_context(full_name, load_dataset):
    context = {
        "groups": [],
        "group": "",
        "classmates": [],
    }
    if load_dataset is None:
        return context

    dataset, load_error = load_dataset()
    if load_error or not dataset:
        return context

    students = dataset.get("students", [])
    if not isinstance(students, list):
        return context

    normalized_full_name = _normalize_name(full_name)
    matched = [
        student
        for student in students
        if isinstance(student, dict)
        and _normalize_name(student.get("fullName", "")) == normalized_full_name
    ]
    if not matched:
        return context

    groups = sorted(
        {
            str(student.get("group", "")).strip()
            for student in matched
            if str(student.get("group", "")).strip()
        },
        key=lambda value: value.casefold(),
    )
    group_name = groups[0] if groups else ""

    subject_name = str(matched[0].get("subject", "")).strip()
    classmates = []
    seen = set()
    for student in students:
        if not isinstance(student, dict):
            continue
        if str(student.get("group", "")).strip() != group_name:
            continue
        if str(student.get("subject", "")).strip() != subject_name:
            continue

        classmate_name = str(student.get("fullName", "")).strip()
        if not classmate_name:
            continue
        if _normalize_name(classmate_name) == normalized_full_name:
            continue
        key = _normalize_name(classmate_name)
        if key in seen:
            continue
        seen.add(key)
        classmates.append(classmate_name)

    classmates.sort(key=lambda value: value.casefold())
    context["groups"] = groups
    context["group"] = group_name
    context["classmates"] = classmates
    return context


def get_admin_student_profile(student_row_id, load_dataset):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        row = queries.get_student_admin_row(conn, student_row_id)
    if not row:
        return None

    full_name = str(row["full_name"]).strip()
    auto_context = _extract_auto_student_context(full_name, load_dataset)
    teacher_name = get_teacher_name_by_group(auto_context.get("group", ""))
    split_name = _split_name(full_name)

    return {
        "id": int(row["id"]),
        "full_name": full_name,
        "surname": split_name["surname"],
        "name": split_name["name"],
        "student_id": str(row["student_id"]).strip(),
        "password": str(row["password"]).strip(),
        "subjects": str(row["subjects"]).strip(),
        "photo_url": str(row["photo_url"] or "").strip(),
        "profile_description": str(row["profile_description"] or "").strip(),
        "class_name": str(row["class_name"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip() or _DEFAULT_SCHOOL_NAME,
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
    load_dataset,
):
    profile = {
        "full_name": str(full_name or "").strip(),
        "photo_url": "",
        "profile_description": "",
        "class_name": "",
        "school_name": _DEFAULT_SCHOOL_NAME,
        "group_name": str(group_name or "").strip(),
        "teacher_name": "",
        "classmates": [],
    }

    if isinstance(student_db_id, int) and student_db_id > 0:
        init_storage()
        with _connect() as conn:
            row = queries.get_student_admin_row(conn, student_db_id)
        if row:
            profile["photo_url"] = str(row["photo_url"] or "").strip()
            profile["profile_description"] = str(row["profile_description"] or "").strip()
            profile["class_name"] = str(row["class_name"] or "").strip()
            profile["school_name"] = (
                str(row["school_name"] or "").strip() or _DEFAULT_SCHOOL_NAME
            )

    profile["teacher_name"] = get_teacher_name_by_group(group_name)

    if load_dataset is None:
        return profile

    dataset, load_error = load_dataset()
    if load_error or not dataset:
        return profile

    students = dataset.get("students", [])
    if not isinstance(students, list):
        return profile

    normalized_self = _normalize_name(full_name)
    classmates = []
    seen = set()
    for student in students:
        if not isinstance(student, dict):
            continue
        if str(student.get("group", "")).strip() != str(group_name or "").strip():
            continue
        if str(student.get("subject", "")).strip() != str(subject_name or "").strip():
            continue
        classmate_name = str(student.get("fullName", "")).strip()
        if not classmate_name:
            continue
        if _normalize_name(classmate_name) == normalized_self:
            continue
        key = _normalize_name(classmate_name)
        if key in seen:
            continue
        seen.add(key)
        classmates.append(classmate_name)

    classmates.sort(key=lambda value: value.casefold())
    profile["classmates"] = classmates
    return profile


def get_student_db_id_by_sheet_student_id(sheet_student_id, school_code = None):
    try:
        normalized_sheet_student_id = int(sheet_student_id)
    except (TypeError, ValueError):
        return None
    if normalized_sheet_student_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        mapping = queries.get_students_sheet_map_row(
            conn,
            normalized_sheet_student_id,
            school_key=_normalize_school_code(school_code),
        )
    if not mapping:
        return None
    try:
        return int(mapping["student_row_id"])
    except (TypeError, ValueError, KeyError):
        return None


def get_bot_users_count():
    init_storage()
    with _connect() as conn:
        return queries.get_bot_users_count(conn)


def record_bot_user(telegram_user):
    if telegram_user is None:
        return

    user_id = getattr(telegram_user, "id", None)
    if not isinstance(user_id, int):
        return

    username = getattr(telegram_user, "username", None)
    first_name = getattr(telegram_user, "first_name", None)
    last_name = getattr(telegram_user, "last_name", None)

    init_storage()
    now = _utc_now_iso()

    with _DB_LOCK:
        with _connect() as conn:
            queries.upsert_bot_user(
                conn,
                user_id,
                username,
                first_name,
                last_name,
                now,
            )
            conn.commit()


def link_student_telegram_user(student_row_id, telegram_user_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return False

    init_storage()

    with _DB_LOCK:
        with _connect() as conn:
            student_exists = queries.get_student_admin_row(conn, student_row_id)
            if not student_exists:
                return False

            # Mini app login is the source of truth:
            # one Telegram user can be linked to only one student profile at a time.
            queries.clear_student_telegram_user_conflicts(
                conn,
                telegram_user_id,
                student_row_id,
            )
            # Student/admin link is mutually exclusive for one Telegram account.
            queries.clear_admin_telegram_user_conflicts(
                conn,
                telegram_user_id,
            )
            queries.update_student_telegram_user(
                conn,
                telegram_user_id,
                student_row_id,
            )
            conn.commit()
    return True


def link_admin_telegram_user(admin_id, telegram_user_id):
    if not isinstance(admin_id, int) or admin_id <= 0:
        return False
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return False

    init_storage()

    with _DB_LOCK:
        with _connect() as conn:
            admin_exists = queries.get_admin_row_by_id(conn, admin_id)
            if not admin_exists:
                return False

            # Student/admin link is mutually exclusive for one Telegram account.
            queries.clear_student_telegram_user_conflicts(
                conn,
                telegram_user_id,
                -1,
            )
            queries.clear_admin_telegram_user_conflicts(
                conn,
                telegram_user_id,
                admin_id,
            )
            queries.update_admin_telegram_user(
                conn,
                telegram_user_id,
                admin_id,
            )
            conn.commit()
    return True


def get_admin_by_telegram_user_id(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        row = queries.get_admin_by_telegram_id(conn, telegram_user_id)

    if not row:
        return None
    return {
        "id": int(row["id"]),
        "login": str(row["login"]),
        "role": str(row["role"]),
        "is_owner": bool(row["is_owner"]),
    }


def unlink_telegram_user_links(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return {
            "success": False,
            "had_student_link": False,
            "had_admin_link": False,
        }

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            student_row = queries.get_student_by_telegram_id(conn, telegram_user_id)
            admin_row = queries.get_admin_by_telegram_id(conn, telegram_user_id)

            queries.clear_student_telegram_user_conflicts(
                conn,
                telegram_user_id,
                -1,
            )
            queries.clear_admin_telegram_user_conflicts(
                conn,
                telegram_user_id,
            )
            conn.commit()

    return {
        "success": True,
        "had_student_link": bool(student_row),
        "had_admin_link": bool(admin_row),
    }


def unlink_student_telegram_user(student_row_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            student_exists = queries.get_student_admin_row(conn, student_row_id)
            if not student_exists:
                return False
            queries.update_student_telegram_user(
                conn,
                None,
                student_row_id,
            )
            conn.commit()
    return True


def get_student_by_telegram_user_id(telegram_user_id):
    if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        row = queries.get_student_by_telegram_id(conn, telegram_user_id)

    if not row:
        return None
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "student_id": str(row["student_id"]),
        "subjects": str(row["subjects"]),
        "school_code": _normalize_school_code(row["school_key"]),
        "sheet_student_id": (
            int(row["sheet_student_id"])
            if row["sheet_student_id"] is not None
            else None
        ),
    }


def change_student_password(student_row_id, current_password, new_password):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False, "Invalid student session."

    current_password_value = str(current_password or "")
    new_password_value = str(new_password or "")
    if not current_password_value:
        return False, "Current password is required."
    if not new_password_value:
        return False, "New password is required."
    if len(new_password_value) < 6:
        return False, "New password must be at least 6 characters."
    if current_password_value == new_password_value:
        return False, "New password must be different from current password."

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            auth_row = queries.get_student_auth_row_by_id(conn, student_row_id)
            if not auth_row:
                return False, "Student account was not found."

            if not check_password_hash(
                str(auth_row["password_hash"] or ""),
                current_password_value,
            ):
                return False, "Current password is incorrect."

            queries.update_student_password(
                conn,
                student_row_id,
                new_password_value,
                generate_password_hash(new_password_value),
                _utc_now_iso(),
            )
            conn.commit()

    return True, ""
