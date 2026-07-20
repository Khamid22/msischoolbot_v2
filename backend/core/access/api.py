"""FastAPI dependency injection utilities for role and permission security."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from backend.core.access import management_permissions, roles


@dataclass(frozen=True)
class CurrentUser:
    """Session-derived user context for API route dependencies."""

    login: str
    role: str
    teacher_id: int | None = None
    teacher_staff_id: int | None = None
    student_id: str = ""
    student_db_id: int | None = None
    student_enrollment_id: int | None = None
    parent_id: int | None = None
    staff_id: int | None = None
    account_id: int | None = None
    must_change_password: bool = False
    session_version: int = 1


def _session_int(session: dict[str, Any], key: str) -> int | None:
    try:
        parsed = int(session.get(key))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _resolve_session_role(session: dict[str, Any]) -> str:
    auth_role = roles.normalize_role(session.get("auth_role", ""))
    if not auth_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    if auth_role in roles.ALL_ROLES:
        return auth_role

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unknown authentication role.",
    )


def get_current_user(request: Request) -> CurrentUser:
    """Resolve the authenticated user once from the Starlette session."""

    session = request.session
    role = _resolve_session_role(session)
    return CurrentUser(
        login=str(session.get("auth_login", "")).strip(),
        role=role,
        teacher_id=_session_int(session, "teacher_id"),
        teacher_staff_id=_session_int(session, "teacher_staff_id"),
        student_id=str(session.get("student_id", "")).strip(),
        student_db_id=_session_int(session, "student_db_id"),
        student_enrollment_id=_session_int(session, "student_enrollment_id"),
        parent_id=_session_int(session, "parent_id"),
        staff_id=_session_int(session, "staff_id"),
        account_id=_session_int(session, "account_id"),
        must_change_password=bool(session.get("must_change_password")),
        session_version=_session_int(session, "session_version") or 1,
    )


def get_current_user_role(user: CurrentUser = Depends(get_current_user)) -> str:
    """
    Resolves the current authenticated user's role from the session.
    If no user is authenticated, raises 401.
    """

    return user.role


def _normalize_allowed_roles(allowed_roles: tuple[Any, ...]) -> set[str]:
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple, set, frozenset)):
        raw_roles = allowed_roles[0]
    else:
        raw_roles = allowed_roles
    return {
        normalized
        for normalized in (roles.normalize_role(role) for role in raw_roles)
        if normalized
    }


def require_role(*allowed_roles: Any):
    """
    Returns a dependency that requires the current user to have one of the allowed roles.
    """

    allowed = _normalize_allowed_roles(allowed_roles)

    def dependency(user: CurrentUser = Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action not allowed for this role.",
            )
        return user

    return dependency


def require_permission(required_permission: str):
    """
    Returns a dependency that requires the current user to have the required permission.
    """

    def dependency(user: CurrentUser = Depends(get_current_user)):
        if not management_permissions.role_has_permission(user.role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )
        return user

    return dependency
