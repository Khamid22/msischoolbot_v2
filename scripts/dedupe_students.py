"""Merge duplicate `students` rows (same person held under several login codes).

A `students` row is only a login identity (code, password, telegram link,
last_seen). Grades / attendance / exams are keyed by enrollment /
public_dashboard_id / name — NOT by `students.id` — so merging duplicate student
rows does NOT touch the gradebook. For each duplicate person we keep one
canonical row, move its parent links / payments / complaints / office-hour
bookings / telegram link / latest last_seen onto it, then delete the extras.

Safety:
  - DRY RUN by default: it performs the merge in a transaction, reports what it
    would do, then ROLLS BACK. Pass --apply to commit.
  - Conservative grouping. Only auto-merges a group when exactly ONE row has a
    sheet map (the live synced identity) and the rest are unmapped orphans.
    Groups that are all-unmapped, multi-mapped, or have a telegram conflict are
    SKIPPED and listed for manual review (use --merge-unmapped to also merge
    all-unmapped groups, picking the best row as canonical).

Usage:
  pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql   # back up first!
  python scripts/dedupe_students.py                 # dry run, nothing written
  python scripts/dedupe_students.py --school sehriyo
  python scripts/dedupe_students.py --apply         # commit
"""

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.db import queries  # noqa: E402
from shared.academics import canonical  # noqa: E402
from scripts.find_duplicate_students import (  # noqa: E402
    _ensure_schema,
    fetch_student_rows,
    group_duplicates,
)


def _pick_canonical_unmapped(rows):
    """Best canonical among unmapped rows: telegram link > has activity > lowest id."""
    return sorted(
        rows,
        key=lambda r: (
            0 if r["telegram_user_id"] is not None else 1,
            0 if r["last_seen_at"] else 1,
            int(r["id"]),
        ),
    )[0]


def plan_group(group, merge_unmapped):
    """Return (canonical, orphans, skip_reason). Exactly one of (orphans / skip) is meaningful."""
    mapped = [r for r in group if r["has_map"]]
    unmapped = [r for r in group if not r["has_map"]]

    if len(mapped) == 1:
        canonical, orphans = mapped[0], unmapped
    elif len(mapped) == 0:
        if not merge_unmapped:
            return None, [], "unmapped-only (use --merge-unmapped)"
        canonical = _pick_canonical_unmapped(unmapped)
        orphans = [r for r in unmapped if r["id"] != canonical["id"]]
    else:
        return None, [], "multi-mapped (2+ live identities — review manually)"

    if not orphans:
        return canonical, [], "no orphans"

    # Telegram safety: telegram_user_id is globally unique, so we can only land
    # one value on the canonical row.
    canon_tg = canonical["telegram_user_id"]
    orphan_tgs = [o["telegram_user_id"] for o in orphans if o["telegram_user_id"] is not None]
    if canon_tg is not None and any(tg != canon_tg for tg in orphan_tgs):
        return None, [], "telegram-conflict (orphan linked to a different telegram)"
    if len(orphan_tgs) > 1:
        return None, [], "multiple-telegram-orphans (review manually)"

    return canonical, orphans, ""


def _repoint_with_pk(conn, table, partner_col, canonical_id, orphan_id):
    # Junction tables with PK (partner, student_row_id): drop rows that would
    # collide on the canonical id, then move the rest.
    conn.execute(
        f"""
        DELETE FROM {table}
        WHERE student_row_id = %s
          AND {partner_col} IN (
            SELECT {partner_col} FROM {table} WHERE student_row_id = %s
          )
        """,
        (orphan_id, canonical_id),
    )
    return conn.execute(
        f"UPDATE {table} SET student_row_id = %s WHERE student_row_id = %s",
        (canonical_id, orphan_id),
    ).rowcount


def merge_group(conn, canonical, orphans, counts):
    canonical_id = int(canonical["id"])
    canon_tg = canonical["telegram_user_id"]

    for orphan in orphans:
        orphan_id = int(orphan["id"])

        counts["parent_children"] += _repoint_with_pk(conn, "parent_children", "parent_admin_id", canonical_id, orphan_id)
        counts["parent_links"] += _repoint_with_pk(conn, "parent_student_links", "parent_id", canonical_id, orphan_id)
        counts["payments"] += conn.execute(
            "UPDATE student_payments SET student_row_id = %s WHERE student_row_id = %s",
            (canonical_id, orphan_id),
        ).rowcount
        counts["complaints"] += conn.execute(
            "UPDATE parent_complaints SET student_row_id = %s WHERE student_row_id = %s",
            (canonical_id, orphan_id),
        ).rowcount
        counts["bookings"] += conn.execute(
            "UPDATE office_hour_bookings SET student_row_id = %s WHERE student_row_id = %s",
            (canonical_id, orphan_id),
        ).rowcount

        # Move a telegram link onto the canonical row if it has none.
        if canon_tg is None and orphan["telegram_user_id"] is not None:
            conn.execute("UPDATE students SET telegram_user_id = NULL WHERE id = %s", (orphan_id,))
            conn.execute(
                "UPDATE students SET telegram_user_id = %s WHERE id = %s",
                (orphan["telegram_user_id"], canonical_id),
            )
            canon_tg = orphan["telegram_user_id"]
            counts["telegram_moved"] += 1

        conn.execute("DELETE FROM students WHERE id = %s", (orphan_id,))
        counts["orphans_deleted"] += 1

    # Keep the most recent last_seen across the whole group on the canonical row.
    seen_values = [r["last_seen_at"] for r in [canonical, *orphans] if r["last_seen_at"]]
    if seen_values:
        best = max(seen_values)
        conn.execute(
            "UPDATE students SET last_seen_at = %s WHERE id = %s AND (last_seen_at IS NULL OR last_seen_at < %s)",
            (best, canonical_id, best),
        )

    counts["groups_merged"] += 1


def main():
    parser = argparse.ArgumentParser(description="Merge duplicate students rows (dry-run by default).")
    parser.add_argument("--apply", action="store_true", help="Commit. Without it the script rolls back.")
    parser.add_argument("--school", default=None, help="Limit to one school_key.")
    parser.add_argument(
        "--merge-unmapped",
        action="store_true",
        help="Also merge all-unmapped groups (manual/leftover rows), picking the best as canonical.",
    )
    args = parser.parse_args()

    counts = {
        "groups_merged": 0,
        "orphans_deleted": 0,
        "parent_children": 0,
        "parent_links": 0,
        "payments": 0,
        "complaints": 0,
        "bookings": 0,
        "telegram_moved": 0,
    }
    skipped = []

    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        rows = fetch_student_rows(conn)
        groups = group_duplicates(rows, school_filter=args.school)

        for (school, name), group in sorted(groups.items()):
            canonical, orphans, reason = plan_group(group, args.merge_unmapped)
            if not orphans:
                if reason and reason != "no orphans":
                    skipped.append((school, name, reason))
                continue
            orphan_ids = ", ".join(str(o["id"]) for o in orphans)
            print(
                f"MERGE {school or '(no school)'} | {name}: keep id={canonical['id']}"
                f" (code {canonical['student_id']}), remove [{orphan_ids}]"
            )
            merge_group(conn, canonical, orphans, counts)

        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    mode = "APPLIED" if args.apply else "DRY RUN (rolled back — nothing written)"
    print(f"\nStudent dedupe {mode}:")
    for key in (
        "groups_merged",
        "orphans_deleted",
        "parent_children",
        "parent_links",
        "payments",
        "complaints",
        "bookings",
        "telegram_moved",
    ):
        print(f"- {key}: {counts[key]}")

    if skipped:
        print(f"\nSkipped {len(skipped)} group(s) for manual review:")
        for school, name, reason in skipped:
            print(f"- {school or '(no school)'} | {name}: {reason}")

    if not args.apply:
        print("\nRe-run with --apply to commit. BACK UP FIRST:")
        print('  pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql')


if __name__ == "__main__":
    main()
