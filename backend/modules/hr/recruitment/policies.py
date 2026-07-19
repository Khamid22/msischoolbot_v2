"""Fail-closed recruitment authorization rules."""

from fastapi import HTTPException, status

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.constants import (
    ACADEMIC_ROLES,
    FULL_VIEW_ROLES,
    RECRUITMENT_ROLES,
)


def require_recruitment_role(user: CurrentUser) -> CurrentUser:
    if user.role not in RECRUITMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recruitment access is not allowed for this role.")
    return user


def visible_account_id(user: CurrentUser) -> int | None:
    require_recruitment_role(user)
    if user.role in FULL_VIEW_ROLES:
        return None
    if user.role in ACADEMIC_ROLES and user.account_id:
        return int(user.account_id)
    return -1


def ensure_candidate_view(user: CurrentUser, candidate_id: int) -> None:
    require_recruitment_role(user)
    if user.role in FULL_VIEW_ROLES:
        return
    if user.role not in ACADEMIC_ROLES or not user.account_id:
        raise HTTPException(status_code=403, detail="Candidate access is not allowed.")
    with connect_auth_db() as conn:
        assignment = repository.candidate_assignment_row(
            conn,
            candidate_id=int(candidate_id),
            account_id=int(user.account_id),
        )
        decision_access = (
            repository.candidate_actionable_approval_row(conn, int(candidate_id))
            if user.role == "academic_director"
            else None
        )
    if user.role == "academic_director" and (assignment or decision_access):
        return
    if not assignment:
        raise HTTPException(status_code=403, detail="This candidate is not assigned to you.")
    # Recruitment access is granted by an explicit candidate assignment.
    # Teacher Academy's broader HOD subject scope remains enforced in that domain.


def ensure_hr_management(user: CurrentUser) -> None:
    if user.role != "hr_manager":
        raise HTTPException(status_code=403, detail="This action requires HR Manager access.")


def ensure_academy_removal_management(user: CurrentUser) -> None:
    if user.role not in {"hr_manager", "academic_director"}:
        raise HTTPException(
            status_code=403,
            detail="This action requires HR Manager or Academic Director access.",
        )


def ensure_pipeline_management(user: CurrentUser) -> None:
    if user.role not in {"hr_manager", "ceo"}:
        raise HTTPException(status_code=403, detail="You cannot move recruitment candidates.")


def ensure_assignment_management(user: CurrentUser) -> None:
    if user.role not in {"hr_manager", "ceo"}:
        raise HTTPException(status_code=403, detail="You cannot assign academic evaluators.")


def ensure_academic_write(user: CurrentUser, candidate_id: int) -> None:
    if user.role not in ACADEMIC_ROLES:
        raise HTTPException(status_code=403, detail="This action requires an assigned academic evaluator.")
    if not user.account_id:
        raise HTTPException(status_code=403, detail="This candidate is not assigned to you.")
    with connect_auth_db() as conn:
        assignment = repository.candidate_assignment_row(
            conn,
            candidate_id=int(candidate_id),
            account_id=int(user.account_id),
        )
    if not assignment:
        raise HTTPException(status_code=403, detail="This candidate is not assigned to you.")
    # Explicit recruitment assignment is sufficient for AD and HOD evaluation writes.


def ensure_subject_test_write(user: CurrentUser, candidate_id: int) -> None:
    """Allow HR to administer tests while retaining assigned academic access."""
    if user.role == "hr_manager":
        return
    ensure_academic_write(user, candidate_id)


def ensure_approval_request(user: CurrentUser) -> None:
    if user.role not in {"hr_manager", "ceo"}:
        raise HTTPException(status_code=403, detail="You cannot request a hiring approval.")


def ensure_approval_review(user: CurrentUser, candidate_id: int) -> None:
    if user.role != "academic_director":
        raise HTTPException(status_code=403, detail="Only the Academic Director can review hiring approval requests.")
    ensure_candidate_view(user, candidate_id)


def ensure_final_decision(user: CurrentUser, decision: str) -> None:
    normalized = str(decision or "").strip()
    if user.role == "ceo":
        return
    if user.role in {"hr_manager", "academic_director"} and normalized == "rejected":
        return
    if user.role == "hr_manager" and normalized == "candidate_withdrew":
        return
    raise HTTPException(status_code=403, detail="You cannot finalize this recruitment decision.")


__all__ = [name for name in globals() if name.startswith("ensure_") or name in {"require_recruitment_role", "visible_account_id"}]
