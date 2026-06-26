"""Find `students` rows that are most likely the SAME person under several login codes.

READ-ONLY — runs only SELECTs and never writes. Use it to see how widespread the
duplication is (and which groups are safe to auto-merge) before running
`scripts/dedupe_students.py`.

A `students` row is just a login identity (code + password + telegram link +
last_seen). The gradebook is keyed by enrollment / public_dashboard_id / name,
NOT by `students.id`, so the "same person" signal we have here is
school + normalized full name. Rows are grouped by that and any group with more
than one row is reported.

Each group is classified:
  - mergeable      : exactly one row has a sheet map (the live synced identity);
                     the others are unmapped orphans -> safe to merge.
  - unmapped-only  : no row has a sheet map (manual adds / leftovers) -> review.
  - multi-mapped   : 2+ mapped rows -> could be two real people sharing a name.

Usage:
  python scripts/find_duplicate_students.py
  python scripts/find_duplicate_students.py --school sehriyo
"""

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.db import queries  # noqa: E402
from shared.academics import canonical  # noqa: E402


def _ensure_schema(conn):
    queries.create_tables(conn)
    queries.ensure_parent_children_schema(conn)
    queries.ensure_parent_accounts_schema(conn)
    queries.ensure_student_payments_schema(conn)
    queries.ensure_parent_complaints_schema(conn)
    queries.ensure_office_hours_schema(conn)


def fetch_student_rows(conn):
    return conn.execute(
        """
        SELECT s.id, s.student_id, s.full_name, s.school_key,
               s.telegram_user_id, s.last_seen_at,
               (m.student_row_id IS NOT NULL) AS has_map,
               (SELECT count(*) FROM parent_children pc WHERE pc.student_row_id = s.id) AS parent_children,
               (SELECT count(*) FROM parent_student_links pl WHERE pl.student_row_id = s.id) AS parent_links,
               (SELECT count(*) FROM student_payments sp WHERE sp.student_row_id = s.id) AS payments,
               (SELECT count(*) FROM parent_complaints px WHERE px.student_row_id = s.id) AS complaints,
               (SELECT count(*) FROM office_hour_bookings ob WHERE ob.student_row_id = s.id) AS bookings
        FROM students s
        LEFT JOIN students_sheet_map m ON m.student_row_id = s.id
        ORDER BY s.school_key, s.full_name, s.id
        """
    ).fetchall()


def group_duplicates(rows, school_filter=None):
    """Return {(school, normalized_name): [rows]} for groups with >1 row."""
    groups = {}
    for row in rows:
        school = str(row["school_key"] or "").strip().casefold()
        if school_filter and school != school_filter.strip().casefold():
            continue
        key = (school, canonical.normalize_text(str(row["full_name"] or "")))
        groups.setdefault(key, []).append(row)
    return {key: group for key, group in groups.items() if len(group) > 1}


def classify(group):
    mapped = [r for r in group if r["has_map"]]
    if len(mapped) == 1:
        return "mergeable"
    if len(mapped) == 0:
        return "unmapped-only"
    return "multi-mapped"


def main():
    parser = argparse.ArgumentParser(description="List likely-duplicate students (read-only).")
    parser.add_argument("--school", default=None, help="Limit to one school_key (e.g. sehriyo).")
    args = parser.parse_args()

    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        rows = fetch_student_rows(conn)
        conn.rollback()  # never write

    groups = group_duplicates(rows, school_filter=args.school)
    by_class = {"mergeable": 0, "unmapped-only": 0, "multi-mapped": 0}
    extra_rows = 0

    print(f"Total students rows: {len(rows)}")
    print(f"Duplicate groups (same school + name, >1 row): {len(groups)}\n")

    for (school, name), group in sorted(groups.items()):
        kind = classify(group)
        by_class[kind] += 1
        extra_rows += len(group) - 1
        print(f"[{kind}] {school or '(no school)'} | {name}  ({len(group)} rows)")
        for r in group:
            flags = "MAP " if r["has_map"] else "orphan"
            tg = r["telegram_user_id"] if r["telegram_user_id"] is not None else "-"
            seen = r["last_seen_at"] or "never"
            print(
                f"    id={r['id']:<7} code={str(r['student_id']):<10} {flags}"
                f" tg={tg!s:<12} last_seen={seen:<22}"
                f" links(pc={r['parent_children']},pl={r['parent_links']})"
                f" pay={r['payments']} compl={r['complaints']} book={r['bookings']}"
            )
        print()

    print("Summary:")
    print(f"- duplicate groups: {len(groups)}")
    print(f"- redundant rows (would be removed by a merge): {extra_rows}")
    print(f"- mergeable groups (1 mapped + orphans): {by_class['mergeable']}")
    print(f"- unmapped-only groups (manual/leftover): {by_class['unmapped-only']}")
    print(f"- multi-mapped groups (needs human review): {by_class['multi-mapped']}")
    print("\nNext: scripts/dedupe_students.py (dry-run by default) to merge the mergeable groups.")


if __name__ == "__main__":
    main()
