"""PostgreSQL persistence for candidate documents."""

from __future__ import annotations

from typing import Any


def list_document_rows(
    conn: Any,
    candidate_id: int,
    *,
    include_removed: bool = False,
) -> list[Any]:
    removed_clause = "" if include_removed else "AND document.removed_at IS NULL"
    return conn.execute(
        f"""
        SELECT document.id, document.candidate_id, document.document_type,
               document.original_file_name, document.object_key, document.mime_type,
               document.size_bytes, document.version, document.replaces_document_id,
               document.removed_at::text AS removed_at,
               document.created_at::text AS created_at,
               COALESCE(account.login, '') AS uploaded_by
        FROM msi_v2.teacher_candidate_documents document
        LEFT JOIN msi_v2.accounts account ON account.id = document.uploaded_by_account_id
        WHERE document.candidate_id = %s {removed_clause}
        ORDER BY document.created_at DESC, document.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def get_document_row(
    conn: Any,
    *,
    candidate_id: int,
    document_id: int,
    active_only: bool = True,
) -> Any:
    active_clause = "AND removed_at IS NULL" if active_only else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, document_type, original_file_name, object_key,
               mime_type, size_bytes, version, replaces_document_id,
               removed_at::text AS removed_at, created_at::text AS created_at
        FROM msi_v2.teacher_candidate_documents
        WHERE id = %s AND candidate_id = %s {active_clause}
        LIMIT 1
        """,
        (document_id, candidate_id),
    ).fetchone()


def insert_document(
    conn: Any,
    *,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_documents (
            candidate_id, document_type, original_file_name, object_key,
            mime_type, size_bytes, version, replaces_document_id,
            uploaded_by_account_id, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz)
        RETURNING id
        """,
        (
            values["candidate_id"],
            values["document_type"],
            values["original_file_name"],
            values["object_key"],
            values["mime_type"],
            values["size_bytes"],
            values.get("version", 1),
            values.get("replaces_document_id"),
            actor_account_id,
            now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def remove_document(
    conn: Any,
    *,
    document_id: int,
    actor_account_id: int | None,
    now: str,
) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_documents
        SET removed_at = %s::timestamptz, removed_by_account_id = %s
        WHERE id = %s AND removed_at IS NULL
        """,
        (now, actor_account_id, document_id),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


__all__ = [
    "get_document_row",
    "insert_document",
    "list_document_rows",
    "remove_document",
]
