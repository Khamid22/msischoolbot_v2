#!/usr/bin/env python3
"""Import official subject programs into the clean msi_v2 schema.

Default mode is a read-only preview. Use --apply after reviewing counts.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.academics.curriculum import CurriculumItem, load_default_curricula
from shared.db import queries


SCHEMA_SQL = PROJECT_ROOT / "scripts" / "rebuild_database_v2.sql"


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item_raw_json(item: CurriculumItem) -> str:
    return json.dumps(
        {
            "subject_name": item.subject_name,
            "subject_key": item.subject_key,
            "subject_short": item.subject_short,
            "source_file": item.source_file,
            "sheet_name": item.sheet_name,
            "source_row": item.row_number,
            "lesson_number": item.lesson_number,
            "item_order": item.item_order,
            "item_type": item.item_type,
            "title": item.title,
            "term_label": item.term_label,
            "week_label": item.week_label,
            "specification_points": item.specification_points,
            "book_pages": item.book_pages,
            "lesson_count": item.lesson_count,
            "duration_hours": item.duration_hours,
        },
        ensure_ascii=True,
        sort_keys=True,
    )


def _ensure_schema(conn) -> None:
    conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))


def _program_summary(items: list[CurriculumItem]) -> dict[str, object]:
    lessons = [item for item in items if item.item_type == "lesson"]
    exams = [item for item in items if item.item_type == "exam"]
    return {
        "subject_name": items[0].subject_name if items else "",
        "subject_key": items[0].subject_key if items else "",
        "subject_short": items[0].subject_short if items else "",
        "source_file": items[0].source_file if items else "",
        "total_items": len(items),
        "lesson_count": len(lessons),
        "exam_count": len(exams),
        "first": items[0].lesson_number if items else "",
        "last": items[-1].lesson_number if items else "",
    }


def _print_preview(curricula: dict[str, list[CurriculumItem]], academic_year: str) -> None:
    print(f"Official subject program import preview for academic_year={academic_year}")
    print()
    total_items = 0
    for items in curricula.values():
        summary = _program_summary(items)
        total_items += int(summary["total_items"])
        print(
            "- {subject_name} ({subject_short}): {total_items} rows, "
            "{lesson_count} lessons, {exam_count} exams, {first}..{last}, source={source_file}".format(
                **summary
            )
        )
    print()
    print(f"Total program items: {total_items}")


def _upsert_subject(conn, item: CurriculumItem) -> int:
    now = _utc_now_iso()
    row = conn.execute(
        """
        INSERT INTO msi_v2.subjects (
            subject_key, subject_name, subject_short, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, 'active', %s, %s)
        ON CONFLICT ((lower(subject_key))) DO UPDATE SET
            subject_name = excluded.subject_name,
            subject_short = excluded.subject_short,
            status = 'active',
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (item.subject_key, item.subject_name, item.subject_short, now, now),
    ).fetchone()
    return int(row["id"])


def _upsert_program(
    conn,
    *,
    subject_id: int,
    academic_year: str,
    items: list[CurriculumItem],
) -> int:
    now = _utc_now_iso()
    summary = _program_summary(items)
    row = conn.execute(
        """
        INSERT INTO msi_v2.subject_programs (
            subject_id, academic_year, program_name, source_file,
            total_items, lesson_count, exam_count, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
        ON CONFLICT (subject_id, academic_year) DO UPDATE SET
            program_name = excluded.program_name,
            source_file = excluded.source_file,
            total_items = excluded.total_items,
            lesson_count = excluded.lesson_count,
            exam_count = excluded.exam_count,
            status = 'active',
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (
            subject_id,
            academic_year,
            f"{summary['subject_name']} {academic_year}",
            summary["source_file"],
            summary["total_items"],
            summary["lesson_count"],
            summary["exam_count"],
            now,
            now,
        ),
    ).fetchone()
    return int(row["id"])


def _upsert_program_items(conn, *, program_id: int, items: list[CurriculumItem]) -> int:
    now = _utc_now_iso()
    count = 0
    for item in items:
        conn.execute(
            """
            INSERT INTO msi_v2.subject_program_items (
                program_id, item_order, lesson_number, item_type, title,
                term_label, week_label, specification_points, book_pages,
                lesson_count, duration_hours, source_file, sheet_name,
                source_row, raw_json, created_at, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s::jsonb, %s, %s
            )
            ON CONFLICT (program_id, item_order) DO UPDATE SET
                lesson_number = excluded.lesson_number,
                item_type = excluded.item_type,
                title = excluded.title,
                term_label = excluded.term_label,
                week_label = excluded.week_label,
                specification_points = excluded.specification_points,
                book_pages = excluded.book_pages,
                lesson_count = excluded.lesson_count,
                duration_hours = excluded.duration_hours,
                source_file = excluded.source_file,
                sheet_name = excluded.sheet_name,
                source_row = excluded.source_row,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            (
                program_id,
                item.item_order,
                item.lesson_number,
                item.item_type,
                item.title,
                item.term_label,
                item.week_label,
                item.specification_points,
                item.book_pages,
                item.lesson_count,
                item.duration_hours,
                item.source_file,
                item.sheet_name,
                item.row_number,
                _item_raw_json(item),
                now,
                now,
            ),
        )
        count += 1
    return count


def _apply(curricula: dict[str, list[CurriculumItem]], academic_year: str) -> dict[str, int]:
    counts = {"subjects": 0, "programs": 0, "items": 0}
    with queries.connect_auth_db() as conn:
        _ensure_schema(conn)
        for items in curricula.values():
            if not items:
                continue
            subject_id = _upsert_subject(conn, items[0])
            program_id = _upsert_program(
                conn,
                subject_id=subject_id,
                academic_year=academic_year,
                items=items,
            )
            counts["subjects"] += 1
            counts["programs"] += 1
            counts["items"] += _upsert_program_items(conn, program_id=program_id, items=items)
        conn.commit()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--academic-year", default="2025-26")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    curricula = load_default_curricula()
    _print_preview(curricula, args.academic_year)
    if not args.apply:
        print()
        print("READ-ONLY PREVIEW COMPLETE. No database values were changed.")
        return 0

    counts = _apply(curricula, args.academic_year)
    print()
    print(
        "APPLIED: upserted {subjects} subjects, {programs} programs, "
        "{items} program items into msi_v2.".format(**counts)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
