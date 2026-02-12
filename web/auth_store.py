import os
import sqlite3
import threading
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

# SQLite file for auth and local app data.
_DB_PATH = os.environ.get(
    "AUTH_DB_PATH",
    os.path.join(os.path.dirname(__file__), "app_data.sqlite3"),
)

# Main owner credentials (can be overridden via env if needed).
_OWNER_LOGIN = (os.environ.get("OWNER_ADMIN_LOGIN", "staff280902") or "staff280902").strip()
_OWNER_PASSWORD = (os.environ.get("OWNER_ADMIN_PASSWORD", "Khamid007") or "Khamid007").strip()

_DB_LOCK = threading.Lock()
_SYNC_LOCK = threading.Lock()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_today_iso():
    return datetime.utcnow().date().isoformat()


def _connect():
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_storage():
    with _DB_LOCK:
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'admin',
                    is_owner INTEGER NOT NULL DEFAULT 0 CHECK (is_owner IN (0, 1)),
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    student_id TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password TEXT NOT NULL,
                    subjects TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS students_sheet_map (
                    sheet_student_id INTEGER PRIMARY KEY,
                    student_row_id INTEGER NOT NULL UNIQUE,
                    FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS student_auth (
                    student_row_id INTEGER PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(student_row_id) REFERENCES students(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            _ensure_owner_admin(conn)
            conn.commit()


def _ensure_owner_admin(conn):
    owner = conn.execute(
        "SELECT id FROM admins WHERE lower(login) = lower(?)",
        (_OWNER_LOGIN,),
    ).fetchone()
    if owner:
        return

    conn.execute(
        """
        INSERT INTO admins (login, password_hash, role, is_owner, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            _OWNER_LOGIN,
            generate_password_hash(_OWNER_PASSWORD),
            "owner",
            _utc_now_iso(),
        ),
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
        row = conn.execute(
            """
            SELECT id, login, password_hash, role, is_owner
            FROM admins
            WHERE lower(login) = lower(?)
            """,
            ((login or "").strip(),),
        ).fetchone()

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
        row = conn.execute(
            """
            SELECT
                s.id,
                s.full_name,
                s.student_id,
                s.password,
                s.subjects,
                a.password_hash,
                m.sheet_student_id
            FROM students s
            JOIN student_auth a ON a.student_row_id = s.id
            LEFT JOIN students_sheet_map m ON m.student_row_id = s.id
            WHERE upper(s.student_id) = upper(?)
            """,
            (student_login,),
        ).fetchone()

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
        "sheet_student_id": int(row["sheet_student_id"]),
    }


def _next_student_code(conn):
    row = conn.execute(
        """
        SELECT MAX(CAST(SUBSTR(student_id, 4) AS INTEGER)) AS max_num
        FROM students
        WHERE upper(student_id) LIKE 'MSI%'
        """
    ).fetchone()
    next_num = int(row["max_num"] or 0) + 1
    return f"MSI{next_num:05d}"


def _upsert_meta(conn, key, value):
    conn.execute(
        """
        INSERT INTO app_meta (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def _get_meta(conn, key):
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if not row:
        return ""
    return str(row["value"])


def _normalize_subject_label(subject_name):
    normalized = (subject_name or "").strip().casefold()
    if normalized in {"igcse mathematics a", "mathematics", "math"}:
        return "Math"
    if normalized in {"general english", "english"}:
        return "English"
    return (subject_name or "").strip()


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

                mapping = conn.execute(
                    """
                    SELECT student_row_id
                    FROM students_sheet_map
                    WHERE sheet_student_id = ?
                    """,
                    (sheet_student_id,),
                ).fetchone()

                if mapping:
                    student_row_id = int(mapping["student_row_id"])
                    conn.execute(
                        """
                        UPDATE students
                        SET full_name = ?, subjects = ?
                        WHERE id = ?
                        """,
                        (full_name, subject_label, student_row_id),
                    )
                    updated += 1
                    continue

                student_code = _next_student_code(conn)
                default_password = student_code
                inserted = conn.execute(
                    """
                    INSERT INTO students (full_name, student_id, password, subjects)
                    VALUES (?, ?, ?, ?)
                    """,
                    (full_name, student_code, default_password, subject_label),
                )
                student_row_id = int(inserted.lastrowid)

                conn.execute(
                    """
                    INSERT INTO student_auth (student_row_id, password_hash, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (student_row_id, generate_password_hash(default_password), _utc_now_iso()),
                )
                conn.execute(
                    """
                    INSERT INTO students_sheet_map (sheet_student_id, student_row_id)
                    VALUES (?, ?)
                    """,
                    (sheet_student_id, student_row_id),
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
        rows = conn.execute(
            """
            SELECT id, full_name, student_id, password, subjects
            FROM students
            ORDER BY full_name COLLATE NOCASE ASC, id ASC
            """
        ).fetchall()

    results = []
    for row in rows:
        results.append(
            {
                "id": int(row["id"]),
                "full_name": str(row["full_name"]),
                "student_id": str(row["student_id"]),
                "password": str(row["password"]),
                "subjects": str(row["subjects"]),
            }
        )
    return results


def get_bot_users_count():
    init_storage()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM bot_users").fetchone()
    return int(row["total"] if row else 0)


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
            conn.execute(
                """
                INSERT INTO bot_users (
                    telegram_user_id,
                    username,
                    first_name,
                    last_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, first_name, last_name, now, now),
            )
            conn.commit()
