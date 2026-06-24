"""Migrate legacy parents (admins with role='parent') into the parent CLIENT tables.

Additive and idempotent. Copies — never moves or deletes:
  1. admins(role='parent')          -> parents               (anchored by source_admin_id)
  2. parent_children                -> parent_student_links  (via source_admin_id)
  3. parent_complaints.parent_id    <- backfilled            (where currently NULL)

Legacy rows/columns are left untouched, so the app keeps working through
`parent_admin_id` while the new `parents` model is populated alongside.

Usage:
  # 1. Back up first (the script does NOT do this for you):
  pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql

  # 2. Preview what WOULD change (writes nothing, rolls back):
  python scripts/migrate_parents_from_admins.py

  # 3. Apply for real:
  python scripts/migrate_parents_from_admins.py --apply

Safe to run more than once.
"""

from pathlib import Path
import argparse
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.db import queries  # noqa: E402


def _now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _count(conn, sql, params=()):
    return int(conn.execute(sql, params).fetchone()["c"])


def migrate(conn):
    now = _now()
    # Make sure every column this migration reads/writes exists: the admin
    # parent-profile fields (display_name/phone/telegram_username) live in
    # ensure_admins_schema, the new client tables + parent_complaints.parent_id
    # in the others.
    queries.create_tables(conn)
    queries.ensure_admins_schema(conn)
    queries.ensure_parent_accounts_schema(conn)
    queries.ensure_parent_complaints_schema(conn)

    counts = {
        "parent_admins_total": _count(
            conn, "SELECT count(*) AS c FROM admins WHERE lower(role) = 'parent'"
        ),
        "parents_before": _count(conn, "SELECT count(*) AS c FROM parents"),
    }

    # 1. admins(role='parent') -> parents. Idempotent via source_admin_id. A
    # telegram_user_id that already belongs to a parent row is nulled (the
    # parents.telegram_user_id index is unique) so the parent still migrates.
    counts["parents_inserted"] = conn.execute(
        """
        INSERT INTO parents (
            full_name, phone, telegram_username, telegram_user_id,
            source_admin_id, created_at, updated_at
        )
        SELECT
            COALESCE(NULLIF(trim(a.display_name), ''), trim(a.login)),
            COALESCE(a.phone, ''),
            COALESCE(a.telegram_username, ''),
            CASE
                WHEN a.telegram_user_id IS NOT NULL
                     AND EXISTS (SELECT 1 FROM parents p2 WHERE p2.telegram_user_id = a.telegram_user_id)
                THEN NULL
                ELSE a.telegram_user_id
            END,
            a.id,
            COALESCE(NULLIF(trim(a.created_at), ''), %s),
            %s
        FROM admins a
        WHERE lower(a.role) = 'parent'
          AND NOT EXISTS (SELECT 1 FROM parents p WHERE p.source_admin_id = a.id)
        """,
        (now, now),
    ).rowcount

    # 2. parent_children -> parent_student_links. Idempotent via PK conflict.
    counts["links_inserted"] = conn.execute(
        """
        INSERT INTO parent_student_links (parent_id, student_row_id, created_at)
        SELECT p.id, pc.student_row_id, COALESCE(NULLIF(trim(pc.assigned_at), ''), %s)
        FROM parent_children pc
        JOIN parents p ON p.source_admin_id = pc.parent_admin_id
        WHERE pc.student_row_id IS NOT NULL
        ON CONFLICT (parent_id, student_row_id) DO NOTHING
        """,
        (now,),
    ).rowcount

    # 3. Backfill parent_complaints.parent_id. Idempotent (only fills NULLs).
    counts["complaints_linked"] = conn.execute(
        """
        UPDATE parent_complaints pc
        SET parent_id = p.id
        FROM parents p
        WHERE p.source_admin_id = pc.parent_admin_id
          AND pc.parent_id IS NULL
        """
    ).rowcount

    counts["parents_after"] = _count(conn, "SELECT count(*) AS c FROM parents")
    counts["links_after"] = _count(conn, "SELECT count(*) AS c FROM parent_student_links")
    counts["complaints_total"] = _count(conn, "SELECT count(*) AS c FROM parent_complaints")
    counts["complaints_with_parent_id"] = _count(
        conn, "SELECT count(*) AS c FROM parent_complaints WHERE parent_id IS NOT NULL"
    )
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Migrate role='parent' admins into the parents client tables (additive, idempotent)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the changes. Without this flag the script rolls back after counting.",
    )
    args = parser.parse_args()

    with queries.connect_auth_db() as conn:
        counts = migrate(conn)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    mode = "APPLIED" if args.apply else "DRY RUN (rolled back — nothing written)"
    print(f"Parent migration {mode}:")
    for key in (
        "parent_admins_total",
        "parents_before",
        "parents_inserted",
        "links_inserted",
        "complaints_linked",
        "parents_after",
        "links_after",
        "complaints_total",
        "complaints_with_parent_id",
    ):
        print(f"- {key}: {counts.get(key)}")
    if not args.apply:
        print("\nRe-run with --apply to commit. BACK UP FIRST:")
        print('  pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql')


if __name__ == "__main__":
    main()
