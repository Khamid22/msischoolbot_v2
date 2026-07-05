"""FastAPI dependency injection utilities for role and permission security."""

from typing import List
from fastapi import HTTPException, Depends, status
from backend.utils import session as session_utils
from backend.security import roles, permissions


def get_current_user_role() -> str:
    """
    Resolves the current authenticated user's role from the session.
    If no user is authenticated, raises 401.
    """
    auth_role = session_utils.current_auth_role()
    if not auth_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )

    if auth_role == "student":
        return roles.ROLE_STUDENT

    if auth_role == "teacher":
        return roles.ROLE_TEACHER

    if auth_role in {
        roles.ROLE_SYSTEM_ADMIN,
        roles.ROLE_CEO,
        roles.ROLE_HR_MANAGER,
        roles.ROLE_CUSTOMER_SUPPORT,
        roles.ROLE_PARENT,
        roles.ROLE_ACADEMIC_DIRECTOR,
        roles.ROLE_HEAD_OF_DEPARTMENT,
    }:
        return roles.normalize_role(auth_role)

    if auth_role == "admin":
        admin_role = session_utils.current_admin_role()
        if admin_role:
            return roles.normalize_role(admin_role)
        # Default fallback if auth_role is admin but admin_role is empty
        return roles.ROLE_ADMIN

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unknown authentication role."
    )


def require_role(allowed_roles: List[str]):
    """
    Returns a dependency that requires the current user to have one of the allowed roles.
    """
    def dependency(role: str = Depends(get_current_user_role)):
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action not allowed for this role."
            )
        return role
    return dependency


def require_permission(required_permission: str):
    """
    Returns a dependency that requires the current user to have the required permission.
    """
    def dependency(role: str = Depends(get_current_user_role)):
        if not permissions.role_has_permission(role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied."
            )
        return role
    return dependency
