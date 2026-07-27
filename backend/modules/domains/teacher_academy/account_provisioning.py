"""Idempotent Teacher Academy account provisioning.

The Academy roster, canonical teacher identity, staff login, account, lifecycle
profile, and teacher profile are linked in the caller's transaction. Curriculum
selection deliberately remains outside this service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.modules.domains.identity.passwords import generate_password_hash
from backend.modules.domains.teacher_academy import mutations_repository
from backend.modules.domains.teacher_academy import repository
from backend.modules.domains.teacher_academy.read_service import _provision_teacher_account_v2


_INELIGIBLE_ACADEMY_STATUSES = {"rejected", "removed", "trash_bin"}
_INELIGIBLE_CANDIDATE_STATUSES = {"rejected", "candidate_withdrew", "trash_bin"}


class AcademyAccountProvisioningError(RuntimeError):
    """Raised when canonical Academy identity links cannot be made safely."""


@dataclass(frozen=True)
class AcademyAccountProvisioningResult:
    academy_teacher_id: int
    candidate_id: int
    teacher_id: int
    staff_id: int
    account_id: int
    login: str
    created: bool


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def provision_recruitment_academy_account(
    conn: Any,
    *,
    academy_teacher_id: int,
    actor_account_id: int | None,
    actor_login: str,
    now: str,
) -> AcademyAccountProvisioningResult:
    """Create or repair one recruitment-linked Academy account atomically."""
    context = mutations_repository.get_recruitment_academy_account_context(
        conn,
        int(academy_teacher_id),
    )
    if not context:
        raise AcademyAccountProvisioningError(
            "The Teacher Academy record is not linked to a lifecycle profile."
        )

    academy_status = str(context["academy_status"] or "").strip().lower()
    candidate_status = str(context["candidate_status"] or "").strip().lower()
    if academy_status in _INELIGIBLE_ACADEMY_STATUSES:
        raise AcademyAccountProvisioningError(
            "Rejected or removed Academy teachers cannot receive an account."
        )
    if candidate_status in _INELIGIBLE_CANDIDATE_STATUSES:
        raise AcademyAccountProvisioningError(
            "This lifecycle profile is closed and cannot receive an Academy account."
        )

    candidate_id = _as_int(context["candidate_id"])
    if not candidate_id:
        raise AcademyAccountProvisioningError(
            "The Teacher Academy record has no lifecycle profile."
        )

    candidate_account_id = _as_int(context["candidate_account_id"])
    staff_account_id = _as_int(context["staff_account_id"])
    linked_candidate_account_id = _as_int(context["linked_candidate_account_id"])
    if (
        staff_account_id
        and linked_candidate_account_id
        and staff_account_id != linked_candidate_account_id
    ):
        raise AcademyAccountProvisioningError(
            "The Academy login and lifecycle profile are linked to different accounts."
        )
    if candidate_account_id and str(context["account_role"] or "").strip().lower() != "teacher":
        raise AcademyAccountProvisioningError(
            "The lifecycle profile account belongs to another role."
        )

    staff_id = _as_int(context["staff_id"])
    teacher_id = _as_int(context["teacher_id"])
    account_id = _as_int(context["account_id"])
    login = str(context["staff_login"] or "").strip().upper()
    already_ready = bool(
        staff_id
        and teacher_id
        and account_id
        and login
        and _as_int(context["academy_staff_id"]) == staff_id
        and str(context["account_onboarding_status"] or "").strip().lower() == "complete"
        and candidate_account_id == account_id
        and _as_int(context["teacher_candidate_id"]) == candidate_id
    )
    if already_ready:
        return AcademyAccountProvisioningResult(
            academy_teacher_id=int(academy_teacher_id),
            candidate_id=candidate_id,
            teacher_id=teacher_id,
            staff_id=staff_id,
            account_id=account_id,
            login=login,
            created=False,
        )

    created = False
    full_name = str(context["full_name"] or "").strip()
    if not full_name:
        raise AcademyAccountProvisioningError(
            "The Teacher Academy profile requires a full name before account creation."
        )

    if staff_id:
        if str(context["staff_role"] or "").strip().lower() != "teacher":
            raise AcademyAccountProvisioningError(
                "The linked staff identity belongs to another role."
            )
        if not teacher_id or not login:
            raise AcademyAccountProvisioningError(
                "The linked Academy staff identity is incomplete."
            )
        if not mutations_repository.link_teacher_identity_to_candidate(
            conn,
            teacher_id=teacher_id,
            candidate_id=candidate_id,
            updated_at=now,
        ):
            raise AcademyAccountProvisioningError(
                "The teacher identity belongs to another lifecycle profile."
            )
        password_hash = str(context["staff_password_hash"] or "").strip()
        if not password_hash:
            raise AcademyAccountProvisioningError(
                "The existing Academy login has no password hash."
            )
        account_id = _provision_teacher_account_v2(
            conn,
            teacher_id=teacher_id,
            staff_id=staff_id,
            login=login,
            password_hash=password_hash,
            full_name=full_name,
        )
    else:
        if candidate_account_id:
            raise AcademyAccountProvisioningError(
                "The lifecycle profile already belongs to an unrelated account."
            )
        mutations_repository.acquire_teacher_login_advisory_lock(conn)
        if not teacher_id:
            teacher_id = repository.insert_teacher_profile_row(
                conn,
                full_name,
                notes=str(context["notes"] or "").strip(),
                status="academy",
                subject_id=_as_int(context["subject_id"]),
                created_at=now,
                updated_at=now,
            )
            if not teacher_id:
                raise AcademyAccountProvisioningError(
                    "Unable to create the canonical Academy teacher identity."
                )
        if not mutations_repository.link_teacher_identity_to_candidate(
            conn,
            teacher_id=teacher_id,
            candidate_id=candidate_id,
            updated_at=now,
        ):
            raise AcademyAccountProvisioningError(
                "Unable to link the teacher identity to the lifecycle profile."
            )
        login = repository.get_next_teacher_code(conn)
        password_hash = generate_password_hash(login)
        staff_id = repository.insert_teacher_auth(
            conn,
            teacher_id,
            login,
            login,
            password_hash,
            now,
        )
        if not staff_id:
            raise AcademyAccountProvisioningError(
                "Unable to create the Teacher Academy login."
            )
        account_id = _provision_teacher_account_v2(
            conn,
            teacher_id=teacher_id,
            staff_id=staff_id,
            login=login,
            password_hash=password_hash,
            full_name=full_name,
        )
        created = True

    if not account_id:
        raise AcademyAccountProvisioningError(
            "Unable to create the Teacher Academy account."
        )
    if candidate_account_id and candidate_account_id != int(account_id):
        raise AcademyAccountProvisioningError(
            "The lifecycle profile is linked to a different account."
        )
    if not mutations_repository.mark_recruitment_academy_account_ready(
        conn,
        academy_teacher_id=int(academy_teacher_id),
        staff_id=int(staff_id),
        updated_at=now,
    ):
        raise AcademyAccountProvisioningError(
            "The Teacher Academy record changed while its account was being created."
        )
    if not mutations_repository.attach_lifecycle_profile_account(
        conn,
        candidate_id=candidate_id,
        account_id=int(account_id),
        updated_at=now,
    ):
        raise AcademyAccountProvisioningError(
            "The lifecycle profile changed while its account was being linked."
        )

    mutations_repository.insert_recruitment_academy_account_audit(
        conn,
        academy_teacher_id=int(academy_teacher_id),
        candidate_id=candidate_id,
        teacher_id=int(teacher_id),
        staff_id=int(staff_id),
        account_id=int(account_id),
        login=login,
        actor_account_id=_as_int(actor_account_id) or None,
        actor_login=str(actor_login or ""),
        created_at=now,
    )
    return AcademyAccountProvisioningResult(
        academy_teacher_id=int(academy_teacher_id),
        candidate_id=candidate_id,
        teacher_id=int(teacher_id),
        staff_id=int(staff_id),
        account_id=int(account_id),
        login=login,
        created=created,
    )


__all__ = [
    "AcademyAccountProvisioningError",
    "AcademyAccountProvisioningResult",
    "provision_recruitment_academy_account",
]
