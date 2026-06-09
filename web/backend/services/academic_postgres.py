"""Runtime raw-SQL helpers for the internal academic admin model."""

import json
import math
from datetime import datetime

from web.backend import queries


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return queries.connect_auth_db()


def _normalize(value):
    return " ".join(str(value or "").strip().casefold().split())


def _average_homework_grade(homework_grades):
    scores = []
    if not isinstance(homework_grades, list):
        return 0.0
    for item in homework_grades:
        if not isinstance(item, dict):
            continue
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        if score != score:
            continue
        scores.append(max(0.0, min(9.0, score)))
    if not scores:
        return 0.0
    return math.floor((sum(scores) / len(scores)) * 10 + 0.5) / 10


_PLACEHOLDER_DATE_TOKENS = {
    "",
    "homework",
    "h/w",
    "hw",
    "task",
    "topic",
    "date",
    "lesson",
}


def _is_placeholder_date(value):
    text = str(value or "").strip()
    if not text:
        return True
    return _normalize(text) in _PLACEHOLDER_DATE_TOKENS or not any(char.isdigit() for char in text)


def _date_sort_key(value):
    text = str(value or "").strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d/%m/%y",
        "%m/%d/%y",
        "%d.%m.%y",
        "%m.%d.%y",
        "%d-%m-%y",
        "%m-%d-%y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    parts = text.replace(".", "/").replace("-", "/").split("/")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        first = int(parts[0])
        second = int(parts[1])
        if 1 <= first <= 31 and 1 <= second <= 12:
            now = datetime.utcnow()
            year = now.year - 1 if second > now.month + 1 else now.year
            try:
                return datetime(year, second, first)
            except ValueError:
                pass

    return datetime.max


def _choose_earlier_date(current, candidate):
    if _is_placeholder_date(candidate):
        return current
    if _is_placeholder_date(current):
        return str(candidate or "").strip()
    return str(candidate or "").strip() if _date_sort_key(candidate) < _date_sort_key(current) else current


def repair_placeholder_academic_dates(conn, now=None):
    """Repair imported placeholder lesson dates such as Chemistry's HOMEWORK header."""
    now = now or _utc_now_iso()
    attendance_rows = conn.execute(
        """
        SELECT e.group_id, a.enrollment_id, a.lesson_label, a.topic, a.lesson_date
        FROM academic_attendance_records a
        JOIN academic_enrollments e ON e.id = a.enrollment_id
        WHERE coalesce(a.lesson_date, '') <> ''
        """
    ).fetchall()

    enrollment_topic_dates = {}
    enrollment_label_dates = {}
    group_topic_dates = {}
    group_label_dates = {}
    for row in attendance_rows:
        lesson_label = _normalize(row["lesson_label"])
        topic = _normalize(row["topic"])
        lesson_date = str(row["lesson_date"] or "").strip()
        if _is_placeholder_date(lesson_date):
            continue
        enrollment_id = int(row["enrollment_id"])
        group_id = int(row["group_id"])
        if lesson_label and topic:
            key = (enrollment_id, lesson_label, topic)
            enrollment_topic_dates[key] = _choose_earlier_date(enrollment_topic_dates.get(key), lesson_date)
            group_key = (group_id, lesson_label, topic)
            group_topic_dates[group_key] = _choose_earlier_date(group_topic_dates.get(group_key), lesson_date)
        if lesson_label:
            key = (enrollment_id, lesson_label)
            enrollment_label_dates[key] = _choose_earlier_date(enrollment_label_dates.get(key), lesson_date)
            group_key = (group_id, lesson_label)
            group_label_dates[group_key] = _choose_earlier_date(group_label_dates.get(group_key), lesson_date)

    homework_rows = conn.execute(
        """
        SELECT h.id, h.enrollment_id, e.group_id, h.lesson_label, h.topic, h.lesson_date
        FROM academic_homework_scores h
        JOIN academic_enrollments e ON e.id = h.enrollment_id
        """
    ).fetchall()
    for row in homework_rows:
        if not _is_placeholder_date(row["lesson_date"]):
            continue
        enrollment_id = int(row["enrollment_id"])
        lesson_label = _normalize(row["lesson_label"])
        topic = _normalize(row["topic"])
        repaired_date = None
        if lesson_label and topic:
            repaired_date = enrollment_topic_dates.get((enrollment_id, lesson_label, topic))
        if not repaired_date and lesson_label:
            repaired_date = enrollment_label_dates.get((enrollment_id, lesson_label))
        if repaired_date:
            conn.execute(
                "UPDATE academic_homework_scores SET lesson_date = ?, updated_at = ? WHERE id = ?",
                (repaired_date, now, int(row["id"])),
            )
        else:
            conn.execute(
                "UPDATE academic_homework_scores SET lesson_date = '', updated_at = ? WHERE id = ?",
                (now, int(row["id"])),
            )

    lesson_rows = conn.execute(
        "SELECT id, group_id, lesson_number, topic, lesson_date FROM academic_lessons"
    ).fetchall()
    for row in lesson_rows:
        lesson_number_norm = _normalize(row["lesson_number"])
        topic_norm = _normalize(row["topic"])
        if lesson_number_norm in {"h/w", "hw", "homework"} and topic_norm == "topic":
            conn.execute("DELETE FROM academic_lessons WHERE id = ?", (int(row["id"]),))
            continue
        if not _is_placeholder_date(row["lesson_date"]):
            continue
        group_id = int(row["group_id"])
        repaired_date = None
        if lesson_number_norm and topic_norm:
            repaired_date = group_topic_dates.get((group_id, lesson_number_norm, topic_norm))
        if not repaired_date and lesson_number_norm:
            repaired_date = group_label_dates.get((group_id, lesson_number_norm))
        if repaired_date:
            conn.execute(
                "UPDATE academic_lessons SET lesson_date = ?, updated_at = ? WHERE id = ?",
                (repaired_date, now, int(row["id"])),
            )
        else:
            conn.execute(
                "UPDATE academic_lessons SET lesson_date = '', updated_at = ? WHERE id = ?",
                (now, int(row["id"])),
            )


def _slugify(value):
    import re

    text = re.sub(r"[^a-z0-9]+", "-", _normalize(value)).strip("-")
    return text or "item"


_REQUIRED_TABLES = {
    "academic_schools",
    "academic_subjects",
    "academic_groups",
    "academic_lessons",
    "academic_enrollments",
    "academic_attendance_records",
    "academic_homework_scores",
    "academic_exam_results",
    "academic_coin_events",
}


def ensure_academic_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_schools (
            id BIGSERIAL PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_subjects (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL REFERENCES academic_schools(id),
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            code TEXT NOT NULL DEFAULT '',
            short_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_groups (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL REFERENCES academic_schools(id),
            subject_id BIGINT NOT NULL REFERENCES academic_subjects(id),
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            code TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, subject_id, key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_enrollments (
            id BIGSERIAL PRIMARY KEY,
            student_row_id BIGINT REFERENCES students(id),
            school_id BIGINT NOT NULL REFERENCES academic_schools(id),
            subject_id BIGINT NOT NULL REFERENCES academic_subjects(id),
            group_id BIGINT NOT NULL REFERENCES academic_groups(id),
            public_dashboard_id BIGINT NOT NULL,
            full_name TEXT NOT NULL,
            full_name_norm TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            enrollment_status TEXT NOT NULL DEFAULT 'active',
            disqualification_reason TEXT NOT NULL DEFAULT '',
            disqualified_at TEXT NOT NULL DEFAULT '',
            average_grade DOUBLE PRECISION NOT NULL DEFAULT 0,
            coins INTEGER NOT NULL DEFAULT 0,
            student_payload_json TEXT NOT NULL DEFAULT '{}',
            dashboard_payload_json TEXT NOT NULL DEFAULT '{}',
            imported_from TEXT NOT NULL DEFAULT 'internal',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, public_dashboard_id)
        )
        """
    )
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS enrollment_status TEXT NOT NULL DEFAULT 'active'")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS disqualification_reason TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS disqualified_at TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS student_row_id BIGINT")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS full_name_norm TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS student_payload_json TEXT NOT NULL DEFAULT '{}'")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS dashboard_payload_json TEXT NOT NULL DEFAULT '{}'")
    conn.execute("ALTER TABLE academic_enrollments ADD COLUMN IF NOT EXISTS imported_from TEXT NOT NULL DEFAULT 'internal'")
    conn.execute(
        """
        UPDATE academic_enrollments
        SET full_name_norm = lower(trim(full_name))
        WHERE trim(coalesce(full_name_norm, '')) = ''
        """
    )
    conn.execute(
        """
        UPDATE academic_enrollments
        SET enrollment_status = CASE WHEN active = 1 THEN 'active' ELSE 'inactive' END
        WHERE trim(coalesce(enrollment_status, '')) = ''
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_lessons (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL REFERENCES academic_schools(id),
            subject_id BIGINT NOT NULL REFERENCES academic_subjects(id),
            group_id BIGINT NOT NULL REFERENCES academic_groups(id),
            lesson_number TEXT NOT NULL,
            topic TEXT NOT NULL,
            lesson_date TEXT NOT NULL DEFAULT '',
            lesson_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(school_id, subject_id, group_id, lesson_number)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_attendance_records (
            id BIGSERIAL PRIMARY KEY,
            enrollment_id BIGINT NOT NULL REFERENCES academic_enrollments(id),
            lesson_id BIGINT REFERENCES academic_lessons(id),
            lesson_label TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT '',
            lesson_date TEXT NOT NULL DEFAULT '',
            attendance_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            lesson_order INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(enrollment_id, lesson_label, lesson_order, attendance_type)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_homework_scores (
            id BIGSERIAL PRIMARY KEY,
            enrollment_id BIGINT NOT NULL REFERENCES academic_enrollments(id),
            lesson_id BIGINT REFERENCES academic_lessons(id),
            lesson_label TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT '',
            lesson_date TEXT NOT NULL DEFAULT '',
            score_type TEXT NOT NULL DEFAULT 'Homework',
            score DOUBLE PRECISION NOT NULL,
            lesson_order INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(enrollment_id, lesson_label, lesson_order)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_exam_results (
            id BIGSERIAL PRIMARY KEY,
            enrollment_id BIGINT NOT NULL REFERENCES academic_enrollments(id),
            label TEXT NOT NULL,
            exam_name TEXT NOT NULL DEFAULT '',
            attempt TEXT NOT NULL DEFAULT '',
            score DOUBLE PRECISION NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(enrollment_id, label)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_coin_events (
            id BIGSERIAL PRIMARY KEY,
            enrollment_id BIGINT NOT NULL REFERENCES academic_enrollments(id),
            amount INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'import',
            occurred_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(enrollment_id, source)
        )
        """
    )
    for table, column in (
        ("academic_subjects", "school_id"),
        ("academic_groups", "subject_id"),
        ("academic_enrollments", "public_dashboard_id"),
        ("academic_enrollments", "full_name_norm"),
        ("academic_lessons", "group_id"),
        ("academic_attendance_records", "enrollment_id"),
        ("academic_homework_scores", "enrollment_id"),
        ("academic_exam_results", "enrollment_id"),
        ("academic_coin_events", "enrollment_id"),
    ):
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {table}({column})")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_academic_exam_results_enrollment_label
        ON academic_exam_results(enrollment_id, label)
        """
    )


def _tables_exist(conn) -> bool:
    rows = conn.execute(
        "SELECT tablename AS name FROM pg_tables WHERE schemaname = current_schema()"
    ).fetchall()
    existing = {str(row["name"]) for row in rows}
    return _REQUIRED_TABLES.issubset(existing)


def _ensure(conn):
    ensure_academic_schema(conn)
    if not _tables_exist(conn):
        raise RuntimeError(
            "Internal academic tables are missing. Run the archived Google Sheets updater."
        )


def list_academic_admin_rows():
    with _connect() as conn:
        ensure_academic_schema(conn)
        if not _tables_exist(conn):
            return {"schools": [], "subjects": [], "groups": [], "lessons": []}
        schools = [
            dict(row)
            for row in conn.execute(
                "SELECT id, code, name FROM academic_schools ORDER BY name"
            ).fetchall()
        ]
        subjects = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sub.id, sub.school_id, s.code AS school_code, s.name AS school_name,
                       sub.name, sub.code, sub.short_name
                FROM academic_subjects sub
                JOIN academic_schools s ON s.id = sub.school_id
                ORDER BY s.name, sub.name
                """
            ).fetchall()
        ]
        groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT g.id, g.school_id, s.code AS school_code, g.subject_id,
                       sub.name AS subject_name, g.name, g.code,
                       count(e.id) FILTER (WHERE e.active = 1 AND e.enrollment_status = 'active') AS students_count,
                       count(e.id) FILTER (WHERE e.enrollment_status = 'disqualified') AS disqualified_count
                FROM academic_groups g
                JOIN academic_schools s ON s.id = g.school_id
                JOIN academic_subjects sub ON sub.id = g.subject_id
                LEFT JOIN academic_enrollments e ON e.group_id = g.id
                WHERE lower(g.name) <> 'online'
                GROUP BY g.id, g.school_id, s.code, s.name, g.subject_id, sub.name, g.name, g.code
                ORDER BY s.name, sub.name, g.name
                """
            ).fetchall()
        ]
        enrollment_summary = dict(
            conn.execute(
                """
                SELECT
                  count(*) FILTER (WHERE e.active = 1 AND e.enrollment_status = 'active') AS active_enrollments,
                  count(DISTINCT lower(trim(e.full_name))) FILTER (
                    WHERE e.active = 1
                      AND e.enrollment_status = 'active'
                      AND trim(e.full_name) <> ''
                  ) AS active_unique_students,
                  count(*) FILTER (WHERE e.enrollment_status = 'disqualified') AS disqualified_enrollments
                FROM academic_enrollments e
                JOIN academic_groups g ON g.id = e.group_id
                WHERE lower(g.name) <> 'online'
                """
            ).fetchone()
            or {}
        )
        duplicate_names = int(enrollment_summary.get("active_enrollments") or 0) - int(
            enrollment_summary.get("active_unique_students") or 0
        )
        enrollment_summary["active_duplicate_enrollments"] = max(0, duplicate_names)
        lessons = [
            dict(row)
            for row in conn.execute(
                """
                SELECT l.id, s.code AS school_code, sub.name AS subject_name,
                       g.name AS group_name, l.lesson_number, l.topic AS lesson_topic,
                       l.lesson_date, l.lesson_order
                FROM academic_lessons l
                JOIN academic_schools s ON s.id = l.school_id
                JOIN academic_subjects sub ON sub.id = l.subject_id
                JOIN academic_groups g ON g.id = l.group_id
                WHERE lower(g.name) <> 'online'
                ORDER BY s.name, sub.name, g.name, l.lesson_order
                """
            ).fetchall()
        ]
        return {
            "schools": schools,
            "subjects": subjects,
            "groups": groups,
            "lessons": lessons,
            "enrollment_summary": enrollment_summary,
        }


def _upsert_school(conn, code, name, now):
    code = str(code or "school5").strip().casefold() or "school5"
    name = str(name or ("Sehriyo" if code == "sehriyo" else "School 5")).strip()
    row = conn.execute("SELECT id FROM academic_schools WHERE code = ?", (code,)).fetchone()
    if row:
        conn.execute(
            "UPDATE academic_schools SET name = ?, updated_at = ? WHERE id = ?",
            (name, now, int(row["id"])),
        )
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO academic_schools (code, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (code, name, now, now),
    )
    return int(cur.lastrowid)


def _upsert_subject(conn, school_id, name, code, now):
    name = str(name or "Subject").strip() or "Subject"
    key = _slugify(name)
    short_name = str(code or name[:4]).strip()
    row = conn.execute(
        "SELECT id FROM academic_subjects WHERE school_id = ? AND key = ?",
        (school_id, key),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE academic_subjects
            SET name = ?, code = ?, short_name = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, str(code or ""), short_name, now, int(row["id"])),
        )
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO academic_subjects (school_id, key, name, code, short_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (school_id, key, name, str(code or ""), short_name, now, now),
    )
    return int(cur.lastrowid)


def _upsert_group(conn, school_id, subject_id, name, code, now):
    name = str(name or "Group").strip() or "Group"
    key = _slugify(name)
    row = conn.execute(
        """
        SELECT id FROM academic_groups
        WHERE school_id = ? AND subject_id = ? AND key = ?
        """,
        (school_id, subject_id, key),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE academic_groups SET name = ?, code = ?, updated_at = ? WHERE id = ?",
            (name, str(code or ""), now, int(row["id"])),
        )
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO academic_groups (school_id, subject_id, key, name, code, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (school_id, subject_id, key, name, str(code or ""), now, now),
    )
    return int(cur.lastrowid)


def _student_row_id(conn, school_key, public_dashboard_id, full_name):
    row = conn.execute(
        """
        SELECT student_row_id
        FROM students_sheet_map
        WHERE school_key = ? AND sheet_student_id = ?
        """,
        (school_key, public_dashboard_id),
    ).fetchone()
    if row:
        return int(row["student_row_id"])
    row = conn.execute(
        """
        SELECT id FROM students
        WHERE lower(full_name) = lower(?)
          AND lower(coalesce(school_key, '')) = lower(?)
        LIMIT 1
        """,
        (full_name, school_key),
    ).fetchone()
    return int(row["id"]) if row else None


def create_subject(school_code, name, code=""):
    now = _utc_now_iso()
    key = "-".join(str(name or "").strip().casefold().split())
    with _connect() as conn:
        _ensure(conn)
        school = conn.execute(
            "SELECT id FROM academic_schools WHERE code = ?",
            (school_code,),
        ).fetchone()
        if not school:
            raise ValueError("School was not found.")
        conn.execute(
            """
            INSERT INTO academic_subjects (school_id, key, name, code, short_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, key) DO UPDATE SET
              name = excluded.name,
              code = excluded.code,
              short_name = excluded.short_name,
              updated_at = excluded.updated_at
            """,
            (int(school["id"]), key, name, code, str(name or "")[:4], now, now),
        )
        conn.commit()


def create_group(school_code, subject_id, name, code=""):
    now = _utc_now_iso()
    key = "-".join(str(name or "").strip().casefold().split())
    with _connect() as conn:
        _ensure(conn)
        school = conn.execute("SELECT id FROM academic_schools WHERE code = ?", (school_code,)).fetchone()
        if not school:
            raise ValueError("School was not found.")
        subject = conn.execute(
            "SELECT id FROM academic_subjects WHERE id = ? AND school_id = ?",
            (subject_id, int(school["id"])),
        ).fetchone()
        if not subject:
            raise ValueError("Subject was not found for the selected school.")
        conn.execute(
            """
            INSERT INTO academic_groups (school_id, subject_id, key, name, code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, subject_id, key) DO UPDATE SET
              name = excluded.name,
              code = excluded.code,
              updated_at = excluded.updated_at
            """,
            (int(school["id"]), int(subject_id), key, name, code, now, now),
        )
        conn.commit()


def create_lesson(group_id, lesson_number, topic, lesson_date="", lesson_order=None):
    now = _utc_now_iso()
    with _connect() as conn:
        _ensure(conn)
        group = conn.execute(
            "SELECT school_id, subject_id FROM academic_groups WHERE id = ?",
            (group_id,),
        ).fetchone()
        if not group:
            raise ValueError("Group was not found.")
        if not lesson_order:
            row = conn.execute(
                "SELECT coalesce(max(lesson_order), 0) AS max_order FROM academic_lessons WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            lesson_order = int(row["max_order"] or 0) + 1
        conn.execute(
            """
            INSERT INTO academic_lessons (
              school_id, subject_id, group_id, lesson_number, topic, lesson_date,
              lesson_order, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(school_id, subject_id, group_id, lesson_number) DO UPDATE SET
              topic = excluded.topic,
              lesson_date = excluded.lesson_date,
              lesson_order = excluded.lesson_order,
              updated_at = excluded.updated_at
            """,
            (
                int(group["school_id"]),
                int(group["subject_id"]),
                int(group_id),
                lesson_number,
                topic,
                lesson_date,
                int(lesson_order),
                now,
                now,
            ),
        )
        conn.commit()


def update_lesson(lesson_id, lesson_number=None, topic=None, lesson_date=None):
    now = _utc_now_iso()
    with _connect() as conn:
        _ensure(conn)
        row = conn.execute(
            "SELECT id FROM academic_lessons WHERE id = ?", (lesson_id,)
        ).fetchone()
        if not row:
            raise ValueError("Lesson not found.")
        updates = {"updated_at": now}
        if lesson_number is not None:
            updates["lesson_number"] = str(lesson_number).strip()
        if topic is not None:
            updates["topic"] = str(topic).strip()
        if lesson_date is not None:
            updates["lesson_date"] = str(lesson_date).strip()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE academic_lessons SET {set_clause} WHERE id = ?",
            list(updates.values()) + [int(lesson_id)],
        )
        conn.commit()


def _insert_record(table, values):
    now = _utc_now_iso()
    columns = list(values.keys()) + ["updated_at"]
    params = list(values.values()) + [now]
    placeholders = ",".join(["?"] * len(params))
    with _connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
            params,
        )
        conn.commit()
        return int(cur.lastrowid)


def record_attendance(enrollment_id, lesson_label, status, topic="", lesson_date="", attendance_type=""):
    status = str(status or "").strip().casefold()
    if status not in {"present", "absent", "justified"}:
        raise ValueError("Attendance status must be present, absent, or justified.")
    return _insert_record(
        "academic_attendance_records",
        {
            "enrollment_id": int(enrollment_id),
            "lesson_label": lesson_label,
            "topic": topic,
            "lesson_date": lesson_date,
            "attendance_type": attendance_type,
            "status": status,
            "lesson_order": 0,
        },
    )


def record_homework_score(enrollment_id, lesson_label, score, topic="", lesson_date="", score_type="Homework"):
    return _insert_record(
        "academic_homework_scores",
        {
            "enrollment_id": int(enrollment_id),
            "lesson_label": lesson_label,
            "topic": topic,
            "lesson_date": lesson_date,
            "score_type": score_type,
            "score": float(score),
            "lesson_order": 0,
        },
    )


def record_exam_result(enrollment_id, label, score, exam_name="", attempt=""):
    return _insert_record(
        "academic_exam_results",
        {
            "enrollment_id": int(enrollment_id),
            "label": label,
            "exam_name": exam_name,
            "attempt": attempt,
            "score": float(score),
        },
    )


def record_coin_event(enrollment_id, amount, source="manual"):
    now = _utc_now_iso()
    with _connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            """
            INSERT INTO academic_coin_events (enrollment_id, amount, source, occurred_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(enrollment_id, source) DO UPDATE SET
              amount = excluded.amount,
              updated_at = excluded.updated_at
            """,
            (int(enrollment_id), int(amount), source or "manual", now, now),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
