"""Candidate document use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.domains.recruitment import repository
from backend.modules.domains.recruitment.constants import DOCUMENT_TYPES
from backend.modules.domains.recruitment.errors import RecruitmentError
from backend.platform.storage.r2 import (
    build_private_candidate_document_url,
    delete_private_candidate_document,
    upload_private_candidate_document,
)


CandidateLoader = Callable[[CurrentUser, int], dict[str, Any]]
NextActionSync = Callable[..., None]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actor_account(user: CurrentUser) -> int | None:
    return int(user.account_id) if user.account_id else None


def _actor_staff(user: CurrentUser) -> int | None:
    return int(user.staff_id) if user.staff_id else None


def upload_document(
    user: CurrentUser,
    candidate_id: int,
    *,
    document_type: str,
    uploaded_file: Any,
    replaces_document_id: int | None = None,
    candidate_loader: CandidateLoader,
    sync_next_actions: NextActionSync,
) -> dict[str, Any]:
    normalized_type = str(document_type or "").strip().lower()
    if normalized_type not in DOCUMENT_TYPES:
        raise RecruitmentError("Unknown candidate document type.")
    with connect_auth_db() as conn:
        if not repository.get_candidate_row(conn, int(candidate_id)):
            raise RecruitmentError("Candidate was not found.", status_code=404)
        replaced = (
            repository.get_document_row(
                conn,
                candidate_id=int(candidate_id),
                document_id=int(replaces_document_id),
            )
            if replaces_document_id
            else None
        )
        if replaces_document_id and not replaced:
            raise RecruitmentError(
                "Document to replace was not found.",
                status_code=404,
            )

    uploaded, error = upload_private_candidate_document(
        uploaded_file,
        candidate_id=int(candidate_id),
        document_type=normalized_type,
    )
    if error:
        raise RecruitmentError(error)
    now = _now()
    try:
        with connect_auth_db() as conn:
            document_id = repository.insert_document(
                conn,
                values={
                    **uploaded,
                    "candidate_id": int(candidate_id),
                    "document_type": normalized_type,
                    "version": int(replaced["version"] or 1) + 1 if replaced else 1,
                    "replaces_document_id": (
                        int(replaces_document_id) if replaces_document_id else None
                    ),
                },
                actor_account_id=_actor_account(user),
                now=now,
            )
            if replaced:
                repository.remove_document(
                    conn,
                    document_id=int(replaces_document_id),
                    actor_account_id=_actor_account(user),
                    now=now,
                )
            repository.touch_candidate(
                conn,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                now=now,
            )
            repository.insert_audit(
                conn,
                candidate_id=int(candidate_id),
                event_type=(
                    "candidate.document_replaced"
                    if replaced
                    else "candidate.document_uploaded"
                ),
                detail={
                    "document_id": document_id,
                    "document_type": normalized_type,
                    "file_name": uploaded["original_file_name"],
                    "replaces_document_id": replaces_document_id,
                },
                actor_account_id=_actor_account(user),
                actor_staff_id=_actor_staff(user),
                now=now,
            )
            sync_next_actions(
                conn,
                candidate_id=int(candidate_id),
                actor_account_id=_actor_account(user),
                now=now,
            )
            conn.commit()
    except Exception:
        delete_private_candidate_document(uploaded.get("object_key"))
        raise
    if replaced:
        delete_private_candidate_document(replaced["object_key"])
    return candidate_loader(user, int(candidate_id))


def remove_document(
    user: CurrentUser,
    candidate_id: int,
    document_id: int,
    *,
    candidate_loader: CandidateLoader,
    sync_next_actions: NextActionSync,
) -> dict[str, Any]:
    now = _now()
    with connect_auth_db() as conn:
        document = repository.get_document_row(
            conn,
            candidate_id=int(candidate_id),
            document_id=int(document_id),
        )
        if not document:
            raise RecruitmentError("Document was not found.", status_code=404)
        repository.remove_document(
            conn,
            document_id=int(document_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.touch_candidate(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        repository.insert_audit(
            conn,
            candidate_id=int(candidate_id),
            event_type="candidate.document_removed",
            detail={
                "document_id": int(document_id),
                "document_type": document["document_type"],
                "file_name": document["original_file_name"],
            },
            actor_account_id=_actor_account(user),
            actor_staff_id=_actor_staff(user),
            now=now,
        )
        sync_next_actions(
            conn,
            candidate_id=int(candidate_id),
            actor_account_id=_actor_account(user),
            now=now,
        )
        conn.commit()
    delete_private_candidate_document(document["object_key"])
    return candidate_loader(user, int(candidate_id))


def document_url(
    candidate_id: int,
    document_id: int,
    *,
    download: bool = False,
) -> str:
    with connect_auth_db() as conn:
        document = repository.get_document_row(
            conn,
            candidate_id=int(candidate_id),
            document_id=int(document_id),
        )
    if not document:
        raise RecruitmentError("Document was not found.", status_code=404)
    url = build_private_candidate_document_url(
        document["object_key"],
        original_file_name=document["original_file_name"],
        download=download,
    )
    if not url:
        raise RecruitmentError(
            "Private document storage is unavailable.",
            status_code=503,
        )
    return url


__all__ = ["document_url", "remove_document", "upload_document"]
