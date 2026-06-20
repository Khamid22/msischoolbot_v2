import threading
from datetime import datetime

from db import queries

_DB_LOCK = threading.Lock()
_SYNC_LOCK = threading.Lock()


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_cancelled_text(value):
    normalized = str(value or "").strip().casefold()
    return "cancelled" in normalized or "canceled" in normalized


def _ensure_storage(conn):
    queries.create_tables(conn)
    queries.ensure_students_schema(conn)
    queries.ensure_lesson_catalog_schema(conn)


def _load_dataset(load_dataset, force_refresh = False):
    try:
        loaded = load_dataset(force_refresh=force_refresh)
    except Exception as exc:
        try:
            loaded = load_dataset()
        except Exception:
            return None, str(exc)

    if isinstance(loaded, tuple) and len(loaded) == 2:
        dataset, load_error = loaded
        return dataset, str(load_error or "")

    return loaded, ""


def _build_catalog_rows(dataset):
    lesson_catalog_by_subject_group = (
        dataset.get("lesson_catalog_by_subject_group", {})
        if isinstance(dataset, dict)
        else {}
    )
    updated_at = _utc_now_iso()
    payload_rows = []

    if isinstance(lesson_catalog_by_subject_group, dict) and lesson_catalog_by_subject_group:
        for subject_name, group_map in lesson_catalog_by_subject_group.items():
            if not isinstance(group_map, dict):
                continue

            for group_name, lessons in group_map.items():
                if not isinstance(lessons, list):
                    continue

                seen_numbers = set()
                for index, lesson in enumerate(lessons, start=1):
                    if not isinstance(lesson, dict):
                        continue

                    lesson_number = str(lesson.get("lesson_number", "")).strip()
                    lesson_topic = str(lesson.get("lesson_topic", "")).strip()
                    lesson_date = str(lesson.get("lesson_date", "")).strip()
                    lesson_order = lesson.get("lesson_order", index)
                    try:
                        lesson_order = int(lesson_order)
                    except (TypeError, ValueError):
                        lesson_order = index

                    if not lesson_number or not lesson_topic:
                        continue
                    if _is_cancelled_text(lesson_number) or _is_cancelled_text(lesson_topic):
                        continue

                    dedupe_key = lesson_number.casefold()
                    if dedupe_key in seen_numbers:
                        continue
                    seen_numbers.add(dedupe_key)

                    payload_rows.append(
                        {
                            "subject_name": str(subject_name or "").strip(),
                            "group_name": str(group_name or "").strip(),
                            "lesson_number": lesson_number,
                            "lesson_topic": lesson_topic,
                            "lesson_date": lesson_date,
                            "lesson_order": lesson_order,
                            "updated_at": updated_at,
                        }
                    )
    else:
        # Fallback for old dataset payload shape (subject-only lessons).
        lesson_catalog_by_subject = (
            dataset.get("lesson_catalog_by_subject", {})
            if isinstance(dataset, dict)
            else {}
        )
        if not isinstance(lesson_catalog_by_subject, dict):
            return []

        for subject_name, lessons in lesson_catalog_by_subject.items():
            if not isinstance(lessons, list):
                continue

            seen_numbers = set()
            for index, lesson in enumerate(lessons, start=1):
                if not isinstance(lesson, dict):
                    continue

                lesson_number = str(lesson.get("lesson_number", "")).strip()
                lesson_topic = str(lesson.get("lesson_topic", "")).strip()
                lesson_date = str(lesson.get("lesson_date", "")).strip()
                lesson_order = lesson.get("lesson_order", index)
                try:
                    lesson_order = int(lesson_order)
                except (TypeError, ValueError):
                    lesson_order = index

                if not lesson_number or not lesson_topic:
                    continue
                if _is_cancelled_text(lesson_number) or _is_cancelled_text(lesson_topic):
                    continue

                dedupe_key = lesson_number.casefold()
                if dedupe_key in seen_numbers:
                    continue
                seen_numbers.add(dedupe_key)

                payload_rows.append(
                    {
                        "subject_name": str(subject_name or "").strip(),
                        "group_name": "",
                        "lesson_number": lesson_number,
                        "lesson_topic": lesson_topic,
                        "lesson_date": lesson_date,
                        "lesson_order": lesson_order,
                        "updated_at": updated_at,
                    }
                )

    payload_rows.sort(
        key=lambda row: (
            str(row.get("subject_name", "")).casefold(),
            str(row.get("group_name", "")).casefold(),
            int(row.get("lesson_order", 0)),
            str(row.get("lesson_number", "")).casefold(),
        )
    )
    return payload_rows


def sync_lesson_catalog_if_needed(load_dataset, force_refresh=False):
    _ = force_refresh
    with _SYNC_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)

        dataset, load_error = _load_dataset(
            load_dataset,
            force_refresh=True,
        )
        if load_error or not dataset:
            return {
                "synced": False,
                "error": load_error or "Unable to load internal academic data.",
                "count": 0,
            }

        catalog_rows = _build_catalog_rows(dataset)

        with _DB_LOCK:
            with _connect() as conn:
                _ensure_storage(conn)
                queries.replace_lesson_catalog_rows(conn, catalog_rows)
                conn.commit()

        return {"synced": True, "error": "", "count": len(catalog_rows)}


def list_lessons_by_subject(subject_name, group_name=""):
    normalized_subject = str(subject_name or "").strip()
    if not normalized_subject:
        return []
    normalized_group = str(group_name or "").strip()

    with _connect() as conn:
        _ensure_storage(conn)
        if normalized_group:
            rows = queries.list_lesson_catalog_rows_by_subject_group(
                conn,
                normalized_subject,
                normalized_group,
            )
            if not rows:
                # Backward-compatible fallback to subject-only rows.
                rows = queries.list_lesson_catalog_rows_by_subject(conn, normalized_subject)
        else:
            rows = queries.list_lesson_catalog_rows_by_subject(conn, normalized_subject)

    results = []
    for row in rows:
        results.append(
            {
                "group_name": str(row["group_name"] or "").strip(),
                "lesson_number": str(row["lesson_number"]),
                "lesson_topic": str(row["lesson_topic"]),
                "lesson_date": str(row["lesson_date"] or "").strip(),
                "lesson_order": int(row["lesson_order"]),
                "updated_at": str(row["updated_at"]),
            }
        )
    return results


def get_lessons_for_subject(subject_name, group_name, load_dataset=None):
    _ = load_dataset
    rows = list_lessons_by_subject(subject_name, group_name)
    return rows, ""
