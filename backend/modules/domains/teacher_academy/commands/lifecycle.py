"""Teacher Academy lifecycle status and removal commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.modules.domains.teacher_academy import mutations_repository
from backend.modules.domains.teacher_academy.commands.create_teacher import ConnectionContext
from backend.modules.domains.teacher_academy.domain_types import VALID_ACADEMY_STATUSES


@dataclass(frozen=True)
class LifecycleDependencies:
    connect: Callable[[], ConnectionContext]
    now: Callable[[], str]
    as_int: Callable[[Any], int]
    normalize_status: Callable[[Any, Any, str], str]
    are_canonical_accounts_available: Callable[[ConnectionContext], bool]


def update_academy_status(
    *,
    academy_teacher_id: int | str,
    status: str,
    dependencies: LifecycleDependencies,
) -> tuple[bool, str]:
    teacher_id = dependencies.as_int(academy_teacher_id)
    if not teacher_id:
        return False, "Academy teacher not found."
    normalized_status = dependencies.normalize_status(
        status,
        VALID_ACADEMY_STATUSES,
        "in_training",
    )
    with dependencies.connect() as conn:
        if not mutations_repository.get_academy_teacher_id(conn, teacher_id):
            return False, "Academy teacher not found."
        mutations_repository.update_academy_teacher_status(
            conn,
            academy_teacher_id=teacher_id,
            status=normalized_status,
            updated_at=dependencies.now(),
        )
        conn.commit()
    return True, ""


def _delete_generated_identity(
    conn: ConnectionContext,
    *,
    staff_id: int,
    teacher_id: int,
    account_ids: list[int],
) -> None:
    mutations_repository.delete_teacher_profiles_for_delete(
        conn,
        teacher_id=teacher_id,
        account_ids=account_ids,
    )
    mutations_repository.delete_staff_profiles_for_delete(
        conn,
        staff_id=staff_id,
        account_ids=account_ids,
    )
    mutations_repository.delete_teacher_accounts_for_delete(conn, account_ids)
    mutations_repository.delete_academy_teacher_staff_row(conn, staff_id)
    mutations_repository.delete_academy_teacher_profile_row(conn, teacher_id)


def delete_academy_teacher(
    *,
    academy_teacher_id: int | str,
    dependencies: LifecycleDependencies,
) -> tuple[bool, str]:
    academy_id = dependencies.as_int(academy_teacher_id)
    if not academy_id:
        return False, "Academy teacher not found."
    with dependencies.connect() as conn:
        row = mutations_repository.get_academy_teacher_delete_row(conn, academy_id)
        if not row:
            return False, "Academy teacher not found."
        staff_id = dependencies.as_int(row["staff_id"])
        teacher_id = dependencies.as_int(row["teacher_id"])
        has_generated_identity = bool(
            staff_id
            and teacher_id
            and str(row["teacher_status"] or "").strip().lower() == "academy"
            and not dependencies.as_int(row["promoted_teacher_id"])
        )
        account_ids = (
            mutations_repository.list_teacher_account_ids_for_staff(
                conn,
                staff_id=staff_id,
            )
            if has_generated_identity and dependencies.are_canonical_accounts_available(conn)
            else []
        )
        mutations_repository.delete_academy_teacher_row(conn, academy_id)
        if has_generated_identity:
            _delete_generated_identity(
                conn,
                staff_id=staff_id,
                teacher_id=teacher_id,
                account_ids=account_ids,
            )
        conn.commit()
    return True, ""


__all__ = [
    "LifecycleDependencies",
    "delete_academy_teacher",
    "update_academy_status",
]
