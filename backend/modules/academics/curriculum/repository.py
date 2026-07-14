"""Curriculum persistence for the Alembic-managed ``msi_v2`` schema."""

def get_program_teaching_session_count(conn, program_id):
    row = conn.execute(
        """SELECT coalesce(sum(greatest(spi.lesson_count, 1)), 0) AS total
           FROM msi_v2.subject_program_items spi
           WHERE spi.program_id = %s AND spi.item_type = 'lesson'""",
        (int(program_id),),
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def list_lesson_rows(conn):
    return conn.execute(
        """
        SELECT ls.id, g.school_id, subj.id AS subject_id,
               coalesce(g.legacy_group_id, g.id) AS group_id,
               s.school_key AS school_code, subj.subject_name,
               g.group_name, spi.lesson_number, spi.title AS lesson_topic,
               coalesce(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
               spi.item_order AS lesson_order
        FROM msi_v2.lesson_sessions ls
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        JOIN msi_v2.groups g ON g.id = ls.group_id
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE spi.item_type = 'lesson' AND lower(g.group_name) <> 'online'
          AND g.status = 'active'
        ORDER BY s.school_name, subj.subject_name, g.group_name, spi.item_order
        """
    ).fetchall()


def list_curriculum_program_rows(conn):
    return conn.execute(
        """
        SELECT sp.id, subj.subject_key, subj.subject_name, subj.subject_short,
               sp.source_file, sp.total_items, sp.lesson_count, sp.exam_count,
               sp.updated_at::text AS updated_at,
               1 AS db_subject_count,
               (
                 SELECT count(*) FROM msi_v2.groups g
                 WHERE g.program_id = sp.id AND lower(g.group_name) <> 'online'
                   AND g.status = 'active'
               ) AS group_count
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE sp.status = 'active'
        ORDER BY subj.subject_name
        """
    ).fetchall()


def list_curriculum_item_rows(conn):
    return conn.execute(
        """
        SELECT spi.id, spi.program_id, subj.subject_key, subj.subject_name,
               spi.item_order, spi.lesson_number, spi.item_type, spi.title,
               spi.term_label, spi.week_label, spi.specification_points,
               spi.book_pages, spi.lesson_count, spi.duration_hours
        FROM msi_v2.subject_program_items spi
        JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        ORDER BY subj.subject_name, spi.item_order
        """
    ).fetchall()


def list_curriculum_program_page(conn, *, offset=0, limit=50):
    return conn.execute(
        """
        SELECT sp.id, subj.subject_key, subj.subject_name, subj.subject_short,
               sp.source_file, sp.total_items, sp.lesson_count, sp.exam_count,
               sp.updated_at::text AS updated_at,
               count(*) OVER () AS filtered_total,
               (SELECT count(*) FROM msi_v2.groups g
                WHERE g.program_id = sp.id AND g.status = 'active'
                  AND lower(g.group_name) <> 'online') AS group_count
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE sp.status = 'active'
        ORDER BY subj.subject_name, sp.id
        LIMIT %s OFFSET %s
        """,
        (int(limit), int(offset)),
    ).fetchall()


def list_curriculum_item_page(conn, program_id, *, offset=0, limit=100):
    return conn.execute(
        """
        SELECT spi.id, spi.program_id, subj.subject_key, subj.subject_name,
               spi.item_order, spi.lesson_number, spi.item_type, spi.title,
               spi.term_label, spi.week_label, spi.specification_points,
               spi.book_pages, spi.lesson_count, spi.duration_hours,
               count(*) OVER () AS filtered_total
        FROM msi_v2.subject_program_items spi
        JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE spi.program_id = %s AND sp.status = 'active'
        ORDER BY spi.item_order
        LIMIT %s OFFSET %s
        """,
        (int(program_id), int(limit), int(offset)),
    ).fetchall()


def get_subject_program_by_subject_key(conn, subject_key):
    return conn.execute(
        """
        SELECT sp.id
        FROM msi_v2.subject_programs sp
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE lower(subj.subject_key) = lower(%s) AND sp.status = 'active'
        ORDER BY sp.id DESC
        LIMIT 1
        """,
        (subject_key,),
    ).fetchone()


def list_lesson_catalog_rows_by_subject(conn, subject_name):
    """List lesson items from the canonical active program for a subject."""
    return conn.execute(
        """
        SELECT
            spi.lesson_number,
            spi.title AS lesson_topic,
            '' AS lesson_date,
            spi.item_order AS lesson_order,
            spi.updated_at::text AS updated_at
        FROM msi_v2.subject_program_items spi
        JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
        JOIN msi_v2.subjects s ON s.id = sp.subject_id
        WHERE lower(s.subject_name) = lower(%s)
          AND s.status = 'active'
          AND sp.status = 'active'
          AND spi.item_type = 'lesson'
        ORDER BY spi.item_order ASC, spi.lesson_number ASC
        """,
        (str(subject_name or "").strip(),),
    ).fetchall()
