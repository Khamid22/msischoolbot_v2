import os
import threading
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

try:
    from utils.databaseStorage import connect_auth_db
except ImportError:
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.databaseStorage import connect_auth_db

try:
    from . import db_requests
except ImportError:
    import db_requests

_OWNER_LOGIN = (os.environ.get("OWNER_ADMIN_LOGIN", "staff280902") or "staff280902").strip()
_OWNER_PASSWORD = (os.environ.get("OWNER_ADMIN_PASSWORD", "Khamid007") or "Khamid007").strip()
_DEFAULT_SCHOOL_NAME = "School 5"

_DB_LOCK = threading.Lock()
_SYNC_LOCK = threading.Lock()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_today_iso():
    return datetime.utcnow().date().isoformat()


def _connect():
    return connect_auth_db()


def init_storage():
    with _DB_LOCK:
        with _connect() as conn:
            db_requests.create_tables(conn)
            _ensure_students_schema(conn)
            _ensure_owner_admin(conn)
            conn.commit()


def _ensure_students_schema(conn):
    db_requests.ensure_students_schema(conn)


def _ensure_owner_admin(conn):
    owner = db_requests.get_admin_id_by_login(conn, _OWNER_LOGIN)
    if owner:
        return

    db_requests.insert_owner_admin(
        conn,
        _OWNER_LOGIN,
        generate_password_hash(_OWNER_PASSWORD),
        _utc_now_iso(),
    )


def detect_login_role(login):
    normalized = (login or "").strip().casefold()
    if normalized.startswith("staff"):
        return "admin"
    if normalized.startswith("msi"):
        return "student"
    return ""


def verify_admin_credentials(login, password):
    init_storage()
    with _connect() as conn:
        row = db_requests.get_admin_credentials_row(
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
        row = db_requests.get_student_login_row(conn, student_login)

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
        "telegram_user_id": (
            int(row["telegram_user_id"])
            if row["telegram_user_id"] is not None
            else None
        ),
        "sheet_student_id": int(row["sheet_student_id"]),
    }


def _next_student_code(conn):
    return db_requests.get_next_student_code(conn)


def _upsert_meta(conn, key, value):
    db_requests.upsert_meta(conn, key, value)


def _get_meta(conn, key):
    return db_requests.get_meta(conn, key)


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

                mapping = db_requests.get_students_sheet_map_row(conn, sheet_student_id)

                if mapping:
                    student_row_id = int(mapping["student_row_id"])
                    db_requests.update_student_profile(
                        conn,
                        full_name,
                        subject_label,
                        student_row_id,
                    )
                    updated += 1
                    continue

                student_code = _next_student_code(conn)
                default_password = student_code
                student_row_id = db_requests.insert_student(
                    conn,
                    full_name,
                    student_code,
                    default_password,
                    subject_label,
                )
                db_requests.insert_student_auth(
                    conn,
                    student_row_id,
                    generate_password_hash(default_password),
                    _utc_now_iso(),
                )
                db_requests.insert_students_sheet_map(
                    conn,
                    sheet_student_id,
                    student_row_id,
                )
                added += 1

            conn.commit()

    return {"added": added, "updated": updated}


def sync_students_if_needed(load_dataset):
    init_storage()

    with _SYNC_LOCK:
        with _connect() as conn:
            today = _utc_today_iso()
            last_sync_date = _get_meta(conn, "students_sync_date")
            if last_sync_date == today:
                return {"synced": False, "error": "", "added": 0, "updated": 0}

        dataset, load_error = load_dataset()
        if load_error or not dataset:
            return {
                "synced": False,
                "error": load_error or "Unable to load Google Sheets data.",
                "added": 0,
                "updated": 0,
            }

        sync_result = sync_students_from_dataset(dataset)

        with _connect() as conn:
            _upsert_meta(conn, "students_sync_date", _utc_today_iso())
            conn.commit()

        return {
            "synced": True,
            "error": "",
            "added": int(sync_result.get("added", 0)),
            "updated": int(sync_result.get("updated", 0)),
        }


def list_students_for_admin():
    init_storage()
    with _connect() as conn:
        rows = db_requests.list_students_for_admin_rows(conn)

    grouped = {}
    for row in rows:
        full_name = str(row["full_name"]).strip()
        key = _normalize_name(full_name)
        item = grouped.get(key)

        row_subjects = _split_subjects(row["subjects"])
        if item is None:
            grouped[key] = {
                "id": int(row["id"]),
                "full_name": full_name,
                "student_id": str(row["student_id"]),
                "password": str(row["password"]),
                "subjects_set": set(row_subjects),
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
        key=lambda item: (int(item.get("id", 0)), _normalize_name(item.get("full_name", ""))),
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
            existing = db_requests.get_student_admin_row(conn, student_row_id)
            if not existing:
                return False

            db_requests.update_student_admin_profile(
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
        rows = db_requests.list_teachers_rows(conn)

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
        row = db_requests.get_teacher_by_id_row(conn, teacher_id)
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
            db_requests.insert_teacher_row(
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
            existing = db_requests.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False, "Teacher not found."

            group_owner = db_requests.get_teacher_by_group_row(conn, normalized_group)
            if group_owner and int(group_owner["id"]) != teacher_id:
                return False, "Selected group is already assigned to another teacher."

            db_requests.update_teacher_row_by_id(
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
            existing = db_requests.get_teacher_by_id_row(conn, teacher_id)
            if not existing:
                return False
            db_requests.delete_teacher_row_by_id(conn, teacher_id)
            conn.commit()
    return True


def get_teacher_name_by_group(group_name):
    normalized_group = str(group_name or "").strip()
    if not normalized_group:
        return ""

    init_storage()
    with _connect() as conn:
        row = db_requests.get_teacher_by_group_row(conn, normalized_group)
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
                db_requests.delete_teacher_by_group(conn, normalized_group)
                conn.commit()
                return True

            existing_teacher = db_requests.get_teacher_by_full_name_row(
                conn,
                normalized_teacher,
            )
            pay_rate = (
                float(existing_teacher["pay_rate"])
                if existing_teacher is not None
                else 0.0
            )
            db_requests.insert_teacher_row(
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
        row = db_requests.get_student_admin_row(conn, student_row_id)
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
        "school_name": _DEFAULT_SCHOOL_NAME,
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
            row = db_requests.get_student_admin_row(conn, student_db_id)
        if row:
            profile["photo_url"] = str(row["photo_url"] or "").strip()
            profile["profile_description"] = str(row["profile_description"] or "").strip()
            profile["class_name"] = str(row["class_name"] or "").strip()
            profile["school_name"] = _DEFAULT_SCHOOL_NAME

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


def get_student_db_id_by_sheet_student_id(sheet_student_id):
    try:
        normalized_sheet_student_id = int(sheet_student_id)
    except (TypeError, ValueError):
        return None
    if normalized_sheet_student_id <= 0:
        return None

    init_storage()
    with _connect() as conn:
        mapping = db_requests.get_students_sheet_map_row(conn, normalized_sheet_student_id)
    if not mapping:
        return None
    try:
        return int(mapping["student_row_id"])
    except (TypeError, ValueError, KeyError):
        return None


def get_bot_users_count():
    init_storage()
    with _connect() as conn:
        return db_requests.get_bot_users_count(conn)


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
            db_requests.upsert_bot_user(
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
            student_exists = db_requests.get_student_admin_row(conn, student_row_id)
            if not student_exists:
                return False

            # Mini app login is the source of truth:
            # one Telegram user can be linked to only one student profile at a time.
            db_requests.clear_student_telegram_user_conflicts(
                conn,
                telegram_user_id,
                student_row_id,
            )
            db_requests.update_student_telegram_user(
                conn,
                telegram_user_id,
                student_row_id,
            )
            conn.commit()
    return True


def unlink_student_telegram_user(student_row_id):
    if not isinstance(student_row_id, int) or student_row_id <= 0:
        return False

    init_storage()
    with _DB_LOCK:
        with _connect() as conn:
            student_exists = db_requests.get_student_admin_row(conn, student_row_id)
            if not student_exists:
                return False
            db_requests.update_student_telegram_user(
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
        row = db_requests.get_student_by_telegram_id(conn, telegram_user_id)

    if not row:
        return None
    return {
        "id": int(row["id"]),
        "full_name": str(row["full_name"]),
        "student_id": str(row["student_id"]),
        "subjects": str(row["subjects"]),
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
            auth_row = db_requests.get_student_auth_row_by_id(conn, student_row_id)
            if not auth_row:
                return False, "Student account was not found."

            if not check_password_hash(
                str(auth_row["password_hash"] or ""),
                current_password_value,
            ):
                return False, "Current password is incorrect."

            db_requests.update_student_password(
                conn,
                student_row_id,
                new_password_value,
                generate_password_hash(new_password_value),
                _utc_now_iso(),
            )
            conn.commit()

    return True, ""
