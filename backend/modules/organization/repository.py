"""Organization persistence for the Alembic-managed ``msi_v2`` schema."""

def list_school_rows(conn):
    return conn.execute(
        "SELECT id, school_key AS code, school_name AS name FROM msi_v2.schools ORDER BY school_name"
    ).fetchall()


def list_subject_rows(conn):
    return conn.execute(
        """
        SELECT id, subject_name AS name, subject_key AS key,
               subject_short AS code, subject_short AS short_name
        FROM msi_v2.subjects
        WHERE status = 'active'
        ORDER BY subject_name
        """
    ).fetchall()


def list_class_rows(conn):
    return conn.execute(
        """
        SELECT c.id, c.school_id, s.school_key AS school_code,
               c.class_name AS name, c.class_code AS code, c.status,
               count(DISTINCT g.id) AS groups_count,
               count(DISTINCT cs.student_id) FILTER (
                 WHERE cs.enrollment_status = 'active'
               ) AS students_count
        FROM msi_v2.classes c
        JOIN msi_v2.schools s ON s.id = c.school_id
        LEFT JOIN msi_v2.groups g ON g.class_id = c.id
        LEFT JOIN msi_v2.class_students cs ON cs.class_id = c.id
        GROUP BY c.id, s.school_key, s.school_name
        ORDER BY s.school_name, c.class_name
        """
    ).fetchall()


def get_class(conn, class_id):
    return conn.execute(
        """SELECT c.*, s.school_key, s.school_name
           FROM msi_v2.classes c JOIN msi_v2.schools s ON s.id = c.school_id
           WHERE c.id = %s""",
        (int(class_id),),
    ).fetchone()


def get_class_by_school_and_name(conn, school_id, class_name):
    return conn.execute(
        "SELECT * FROM msi_v2.classes WHERE school_id = %s AND lower(btrim(class_name)) = lower(btrim(%s))",
        (int(school_id), class_name),
    ).fetchone()


def insert_class(conn, school_id, class_name, class_code):
    return conn.execute(
        """INSERT INTO msi_v2.classes (school_id, class_name, class_code)
           VALUES (%s, %s, %s) RETURNING *""",
        (int(school_id), class_name, class_code),
    ).fetchone()


def upsert_class_student(conn, class_id, student_id):
    conn.execute(
        """INSERT INTO msi_v2.class_students (class_id, student_id)
           VALUES (%s, %s)
           ON CONFLICT (class_id, student_id) DO UPDATE SET
             enrollment_status = 'active', left_at = NULL""",
        (int(class_id), int(student_id)),
    )


def get_school_by_key(conn, school_code):
    return conn.execute(
        "SELECT id FROM msi_v2.schools WHERE lower(school_key) = lower(%s)",
        (school_code,),
    ).fetchone()


def insert_school(conn, code, name):
    conn.execute(
        "INSERT INTO msi_v2.schools (school_key, school_name) VALUES (%s, %s)",
        (code, name),
    )


def upsert_subject(conn, key, name, short_name):
    conn.execute(
        """
        INSERT INTO msi_v2.subjects (subject_key, subject_name, subject_short, status)
        VALUES (%s, %s, %s, 'active')
        ON CONFLICT ((lower(subject_key))) DO UPDATE SET
          subject_name = excluded.subject_name,
          subject_short = excluded.subject_short,
          status = 'active',
          updated_at = now()
        """,
        (key, name, short_name),
    )
