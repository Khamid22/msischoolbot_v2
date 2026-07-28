"""Typed transaction-aware contracts exposed by the Parents module."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.core.unit_of_work import Connection
from backend.modules.domains.identity.contracts import (
    ProvisionParentAccountCommand,
    provision_parent_account,
)
from backend.modules.domains.parent_relationships import repository


@dataclass(frozen=True)
class CreateParentInviteCommand:
    legacy_student_row_id: int
    issued_by_staff_id: int | None
    expires_in_days: int = 14
    replace_pending: bool = False


@dataclass(frozen=True)
class CreateParentInviteResult:
    invite_code: str
    canonical_student_id: int


@dataclass(frozen=True)
class ParentPreference:
    parent_id: int
    display_name: str
    preferred_language: str


@dataclass(frozen=True)
class EnsureAdmissionParentCommand:
    student_id: int
    full_name: str
    phone: str
    telegram_username: str
    preferred_language: str


@dataclass(frozen=True)
class EnsureAdmissionParentResult:
    parent_id: int
    account_id: int
    was_reused: bool


def _token_hash(invite_code: str) -> str:
    return hashlib.sha256(invite_code.encode("utf-8")).hexdigest()


def create_parent_invite(
    conn: Connection,
    command: CreateParentInviteCommand,
) -> CreateParentInviteResult:
    student_id = repository.get_student_v2_id_by_legacy_row(
        conn,
        command.legacy_student_row_id,
        for_update=True,
    )
    if student_id is None:
        raise ValueError("Selected student was not found.")
    staff_id = repository.get_staff_db_id_for_admin_id(
        conn,
        command.issued_by_staff_id,
    )
    if command.replace_pending:
        repository.revoke_pending_parent_invites(
            conn,
            student_db_id=student_id,
        )
    expires_at = datetime.now(UTC) + timedelta(days=max(1, command.expires_in_days))
    for _attempt in range(5):
        invite_code = secrets.token_urlsafe(9).rstrip("=")
        is_created = repository.insert_parent_invite_row(
            conn,
            token_hash=_token_hash(invite_code),
            student_db_id=student_id,
            staff_db_id=staff_id,
            created_at=datetime.now(UTC).isoformat(),
            expires_at=expires_at.isoformat(),
        )
        if is_created:
            return CreateParentInviteResult(
                invite_code=invite_code,
                canonical_student_id=student_id,
            )
    raise RuntimeError("Could not generate a unique parent invite code")


def ensure_admission_parent(
    conn: Connection,
    command: EnsureAdmissionParentCommand,
) -> EnsureAdmissionParentResult:
    normalized_phone = "".join(character for character in command.phone if character.isdigit())
    if len(normalized_phone) < 5:
        raise ValueError("A valid parent phone number is required.")
    matches = repository.find_unique_active_parent_by_phone(conn, normalized_phone)
    if len(matches) > 1:
        raise ValueError(
            "More than one active parent uses this phone number. "
            "Customer Support must review the identity before activation."
        )
    was_reused = bool(matches)
    if matches:
        parent_id = int(matches[0]["id"])
    else:
        parent_id = repository.insert_admission_parent(
            conn,
            display_name=" ".join(command.full_name.strip().split()),
            phone=command.phone.strip(),
            telegram_username=command.telegram_username,
            preferred_language=command.preferred_language,
        )
    if parent_id <= 0:
        raise RuntimeError("The parent record could not be created.")
    repository.ensure_active_parent_student_link(
        conn,
        parent_id=parent_id,
        student_id=command.student_id,
    )
    account = provision_parent_account(
        conn,
        ProvisionParentAccountCommand(
            parent_id=parent_id,
            full_name=command.full_name,
            phone=command.phone,
            telegram_username=command.telegram_username,
        ),
    )
    if account.account_id <= 0:
        raise RuntimeError("The parent identity could not be provisioned.")
    return EnsureAdmissionParentResult(
        parent_id=parent_id,
        account_id=account.account_id,
        was_reused=was_reused,
    )


def parent_can_access_student_on_connection(
    conn: Connection,
    *,
    parent_id: int,
    student_row_id: int,
) -> bool:
    return bool(repository.get_parent_child_link(conn, parent_id, student_row_id))


def get_parent_preference(
    conn: Connection,
    *,
    parent_id: int,
) -> ParentPreference | None:
    row = repository.get_parent_exists_row(conn, parent_id)
    if row is None or str(row["status"] or "").strip().casefold() != "active":
        return None
    return ParentPreference(
        parent_id=int(row["id"]),
        display_name=str(row["display_name"] or "").strip(),
        preferred_language=str(row["preferred_language"] or "ru").strip().casefold(),
    )


def set_parent_preferred_language(
    conn: Connection,
    *,
    parent_id: int,
    preferred_language: str,
) -> ParentPreference:
    language = str(preferred_language or "").strip().casefold()
    if language not in {"ru", "uz"}:
        raise ValueError("Preferred language must be either 'ru' or 'uz'.")
    row = repository.update_parent_preferred_language(conn, parent_id, language)
    if row is None:
        raise ValueError("Parent account was not found.")
    preference = get_parent_preference(conn, parent_id=parent_id)
    if preference is None:
        raise ValueError("Parent account was not found.")
    return preference


def claim_parent_invite_code(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import claim_parent_invite_code

    return claim_parent_invite_code(*args, **kwargs)


def list_parent_client_children(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import list_parent_client_children

    return list_parent_client_children(*args, **kwargs)


def load_parent_invite_code_payload(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import load_parent_invite_code_payload

    return load_parent_invite_code_payload(*args, **kwargs)


def parent_can_access_dashboard(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import parent_can_access_dashboard

    return parent_can_access_dashboard(*args, **kwargs)


def parent_account_exists(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import parent_account_exists

    return parent_account_exists(*args, **kwargs)


def parent_can_access_student(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import parent_can_access_student

    return parent_can_access_student(*args, **kwargs)


def resolve_parent_child_dashboard(*args, **kwargs):
    from backend.modules.domains.parent_relationships.service import resolve_parent_child_dashboard

    return resolve_parent_child_dashboard(*args, **kwargs)


__all__ = [
    "CreateParentInviteCommand",
    "CreateParentInviteResult",
    "EnsureAdmissionParentCommand",
    "EnsureAdmissionParentResult",
    "ParentPreference",
    "claim_parent_invite_code",
    "create_parent_invite",
    "ensure_admission_parent",
    "list_parent_client_children",
    "load_parent_invite_code_payload",
    "parent_account_exists",
    "parent_can_access_dashboard",
    "parent_can_access_student",
    "parent_can_access_student_on_connection",
    "get_parent_preference",
    "resolve_parent_child_dashboard",
    "set_parent_preferred_language",
]
