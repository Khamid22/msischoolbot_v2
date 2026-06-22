#!/usr/bin/env python3
"""Preview or import official curriculum programs from SOW spreadsheets.

Default mode is read-only preview. Use --apply to upsert curriculum master data.
Use --update-existing-lessons with --apply only after reviewing the preview.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.academics.curriculum import CurriculumItem, load_default_curricula
from shared.db import queries
from web.backend.domains.academics.postgres_service import ensure_academic_schema


def _utc_now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _ensure_curriculum_schema(conn) -> None:
    ensure_academic_schema(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_curriculum_programs (
            id BIGSERIAL PRIMARY KEY,
            subject_key TEXT NOT NULL UNIQUE,
            subject_name TEXT NOT NULL,
            subject_short TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '',
            total_items INTEGER NOT NULL DEFAULT 0,
            lesson_count INTEGER NOT NULL DEFAULT 0,
            exam_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS academic_curriculum_items (
            id BIGSERIAL PRIMARY KEY,
            program_id BIGINT NOT NULL REFERENCES academic_curriculum_programs(id) ON DELETE CASCADE,
            item_order INTEGER NOT NULL,
            lesson_number TEXT NOT NULL,
            item_type TEXT NOT NULL DEFAULT 'lesson',
            title TEXT NOT NULL,
            term_label TEXT NOT NULL DEFAULT '',
            week_label TEXT NOT NULL DEFAULT '',
            specification_points TEXT NOT NULL DEFAULT '',
            book_pages TEXT NOT NULL DEFAULT '',
            lesson_count TEXT NOT NULL DEFAULT '',
            duration_hours TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '',
            sheet_name TEXT NOT NULL DEFAULT '',
            source_row INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(program_id, item_order)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_academic_curriculum_items_program_type_order
        ON academic_curriculum_items(program_id, item_type, item_order)
        """
    )
    conn.execute(
        """
        ALTER TABLE academic_lessons
        ADD COLUMN IF NOT EXISTS curriculum_item_id BIGINT
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_academic_lessons_curriculum_item
        ON academic_lessons(curriculum_item_id)
        """
    )
    conn.execute(
        """
        ALTER TABLE academic_lesson_sessions
        ADD COLUMN IF NOT EXISTS curriculum_item_id BIGINT
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_academic_lesson_sessions_curriculum_item
        ON academic_lesson_sessions(curriculum_item_id)
        """
    )


def _item_raw_json(item: CurriculumItem) -> str:
    return json.dumps(
        {
            "subject_name": item.subject_name,
            "subject_key": item.subject_key,
            "lesson_number": item.lesson_number,
            "title": item.title,
            "item_type": item.item_type,
            "term_label": item.term_label,
            "week_label": item.week_label,
            "specification_points": item.specification_points,
            "book_pages": item.book_pages,
            "lesson_count": item.lesson_count,
            "duration_hours": item.duration_hours,
            "source_file": item.source_file,
            "sheet_name": item.sheet_name,
            "source_row": item.row_number,
        },
        ensure_ascii=True,
        sort_keys=True,
    )


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
        "exams": [f"{item.lesson_number}: {item.title}" for item in exams],
    }


def _current_db_subjects(conn) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT s.code AS school_code, sub.id AS subject_id, sub.key, sub.name,
               sub.code, sub.short_name,
               COUNT(DISTINCT g.id) AS group_count,
               COUNT(DISTINCT l.id) AS lesson_count
        FROM academic_subjects sub
        JOIN academic_schools s ON s.id = sub.school_id
        LEFT JOIN academic_groups g ON g.subject_id = sub.id
        LEFT JOIN academic_lessons l ON l.subject_id = sub.id
        GROUP BY s.code, sub.id, sub.key, sub.name, sub.code, sub.short_name
        ORDER BY s.code, sub.name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _candidate_lesson_updates(conn, curricula: dict[str, list[CurriculumItem]]) -> list[dict[str, object]]:
    curriculum_by_subject_name: dict[str, dict[int, CurriculumItem]] = {}
    for items in curricula.values():
        if not items:
            continue
        curriculum_by_subject_name[_normalize(items[0].subject_name)] = {
            int(item.item_order): item for item in items
        }

    rows = conn.execute(
        """
        SELECT l.id, sub.name AS subject_name, sub.key AS subject_key,
               g.name AS group_name, l.lesson_number, l.lesson_order,
               l.topic, l.curriculum_item_id
        FROM academic_lessons l
        JOIN academic_subjects sub ON sub.id = l.subject_id
        JOIN academic_groups g ON g.id = l.group_id
        ORDER BY sub.name, g.name, l.lesson_order, l.lesson_number
        """
    ).fetchall()

    updates = []
    for row in rows:
        subject_items = curriculum_by_subject_name.get(_normalize(row["subject_name"]))
        if not subject_items:
            continue
        order = int(row["lesson_order"] or 0)
        if not order:
            continue
        item = subject_items.get(order)
        if not item:
            continue
        current_topic = str(row["topic"] or "").strip()
        if current_topic == item.title:
            continue
        updates.append(
            {
                "lesson_id": int(row["id"]),
                "subject_name": str(row["subject_name"]),
                "group_name": str(row["group_name"]),
                "lesson_order": order,
                "lesson_number": str(row["lesson_number"]),
                "current_topic": current_topic,
                "official_topic": item.title,
                "item_type": item.item_type,
            }
        )
    return updates


def _print_preview(conn, curricula: dict[str, list[CurriculumItem]]) -> None:
    print("Official curriculum files")
    for items in curricula.values():
        summary = _program_summary(items)
        print(
            "- {subject_name} ({subject_short}): {total_items} program rows, "
            "{lesson_count} lessons, {exam_count} exams, {first}..{last}, source={source_file}".format(
                **summary
            )
        )
        for exam in summary["exams"]:
            print(f"  exam: {exam}")

    print()
    print("Current academic subjects in PostgreSQL")
    for row in _current_db_subjects(conn):
        print(
            "- {school_code} | {name} ({short_name}) | groups={group_count} | "
            "group_lessons={lesson_count}".format(**row)
        )

    updates = _candidate_lesson_updates(conn, curricula)
    print()
    print(f"Existing group lesson topic replacements preview: {len(updates)} rows would change")
    by_subject_group: dict[tuple[str, str], int] = defaultdict(int)
    for update in updates:
        by_subject_group[(str(update["subject_name"]), str(update["group_name"]))] += 1
    for (subject_name, group_name), count in sorted(by_subject_group.items()):
        print(f"- {subject_name} | {group_name}: {count}")

    print()
    print("First 20 proposed replacements")
    for update in updates[:20]:
        print(
            "- lesson_id={lesson_id} {subject_name}/{group_name} {lesson_number} "
            "[{item_type}]\n  current: {current_topic}\n  official: {official_topic}".format(
                **update
            )
        )


def _upsert_curricula(conn, curricula: dict[str, list[CurriculumItem]]) -> dict[str, int]:
    now = _utc_now_iso()
    counts = {"programs": 0, "items": 0}
    for items in curricula.values():
        if not items:
            continue
        summary = _program_summary(items)
        program_row = conn.execute(
            """
            INSERT INTO academic_curriculum_programs (
                subject_key, subject_name, subject_short, source_file,
                total_items, lesson_count, exam_count, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(subject_key) DO UPDATE SET
                subject_name = excluded.subject_name,
                subject_short = excluded.subject_short,
                source_file = excluded.source_file,
                total_items = excluded.total_items,
                lesson_count = excluded.lesson_count,
                exam_count = excluded.exam_count,
                updated_at = excluded.updated_at
            RETURNING id
            """,
            (
                summary["subject_key"],
                summary["subject_name"],
                summary["subject_short"],
                summary["source_file"],
                summary["total_items"],
                summary["lesson_count"],
                summary["exam_count"],
                now,
                now,
            ),
        ).fetchone()
        program_id = int(program_row["id"])
        counts["programs"] += 1

        for item in items:
            conn.execute(
                """
                INSERT INTO academic_curriculum_items (
                    program_id, item_order, lesson_number, item_type, title,
                    term_label, week_label, specification_points, book_pages,
                    lesson_count, duration_hours, source_file, sheet_name,
                    source_row, raw_json, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(program_id, item_order) DO UPDATE SET
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
            counts["items"] += 1
    return counts


def _update_existing_lessons(conn, updates: list[dict[str, object]]) -> int:
    now = _utc_now_iso()
    changed = 0
    for update in updates:
        conn.execute(
            """
            UPDATE academic_lessons
            SET topic = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                str(update["official_topic"]),
                now,
                int(update["lesson_id"]),
            ),
        )
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write curriculum master data to PostgreSQL.")
    parser.add_argument(
        "--update-existing-lessons",
        action="store_true",
        help="Also replace existing group lesson topics by matching subject + lesson_order.",
    )
    args = parser.parse_args()

    curricula = load_default_curricula()
    with queries.connect_auth_db() as conn:
        _ensure_curriculum_schema(conn)
        _print_preview(conn, curricula)

        if not args.apply:
            conn.rollback()
            print()
            print("READ-ONLY PREVIEW COMPLETE. No database values were changed.")
            return 0

        counts = _upsert_curricula(conn, curricula)
        lesson_updates = 0
        if args.update_existing_lessons:
            lesson_updates = _update_existing_lessons(
                conn,
                _candidate_lesson_updates(conn, curricula),
            )
        conn.commit()

    print()
    print(
        "APPLIED: upserted {programs} curriculum programs and {items} curriculum items. "
        "Updated existing group lesson topics: {lesson_updates}.".format(
            lesson_updates=lesson_updates,
            **counts,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
