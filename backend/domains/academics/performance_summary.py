"""Subject performance summaries derived directly from msi_v2 academic tables."""

from backend.core.database import connect_auth_db
from backend.domains.academics import canonical
from backend.domains.academics import summary_queries


def _connect():
    return connect_auth_db()


def _format_summary_row(row):
    return {
        "enrollment_id": int(row["enrollment_id"]),
        "student_row_id": int(row["student_row_id"] or 0),
        "public_dashboard_id": int(row["public_dashboard_id"] or 0),
        "full_name": str(row["full_name"]),
        "school_key": str(row["school_key"] or "").strip(),
        "school_name": str(row["school_name"] or "").strip(),
        "group_name": str(row["group_name"] or "").strip(),
        "subject_name": str(row["subject_name"]),
        "subject_short": str(row["subject_short"] or "").strip()
        or canonical.subject_short_name(row["subject_name"]),
        "aap": float(row["aap"] or 0),
        "ar": int(row["ar"] or 0),
        "ep": int(row["ep"] or 0),
        "total_coins": int(row["total_coins"] or 0),
        "rating_rank": int(row["rating_rank"] or 0),
        "rating_total": int(row["rating_total"] or 0),
        "updated_at": str(row["updated_at"] or ""),
    }


def list_subject_summaries_by_full_name(full_name):
    normalized_name = canonical.normalize_text(full_name)
    if not normalized_name:
        return []

    with _connect() as conn:
        rows = summary_queries.list_subject_summary_rows_by_full_name_norm(conn, normalized_name)

    results = [_format_summary_row(row) for row in rows]
    results.sort(
        key=lambda row: (
            canonical.subject_sort_key(row.get("subject_name", "")),
            int(row.get("enrollment_id", 0)),
        )
    )
    return results


def list_subject_summaries(school_key=""):
    normalized_school_key = canonical.normalize_school_code(school_key, default="")
    with _connect() as conn:
        rows = summary_queries.list_subject_summary_rows(
            conn,
            school_key=normalized_school_key if normalized_school_key else "all",
        )
    return [_format_summary_row(row) for row in rows]


def list_subject_student_counts():
    with _connect() as conn:
        rows = summary_queries.list_subject_student_count_rows(conn)
    return [
        {
            "subject_name": str(row["subject_name"] or "").strip(),
            "count": int(row["count"] or 0),
        }
        for row in rows
        if str(row["subject_name"] or "").strip()
    ]


def list_subject_group_counts():
    with _connect() as conn:
        rows = summary_queries.list_subject_group_count_rows(conn)
    return [
        {
            "subject_name": str(row["subject_name"] or "").strip(),
            "count": int(row["count"] or 0),
        }
        for row in rows
        if str(row["subject_name"] or "").strip()
    ]


def get_subject_summaries_for_student(full_name, load_dataset=None):
    _ = load_dataset
    return list_subject_summaries_by_full_name(full_name), ""


__all__ = [
    "get_subject_summaries_for_student",
    "list_subject_group_counts",
    "list_subject_summaries_by_full_name",
    "list_subject_summaries",
    "list_subject_student_counts",
]
