"""Admin parent-account API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.http import ApiSuccess, api_success
from backend.internal_operations.schemas import AssignParentChildRequest, ParentChildAssigned
from backend.modules.people.parents.service import (
    assign_parent_child,
    delete_parent_account,
    remove_parent_child,
)
from backend.internal_operations.page_cache import invalidate_admin_page_context_cache
from backend.core.access import CurrentUser, get_current_user

router = APIRouter()


def _current_parent_admin_id(user: CurrentUser) -> int:
    return int(user.admin_id or 0)


def _student_row_id(payload: AssignParentChildRequest) -> int | None:
    return payload.student_row_id if payload.student_row_id is not None else payload.student_id


@router.post(
    "/parents/{parent_admin_id}/children",
    operation_id="api_v1_admin_assign_selected_parent_child",
    response_model=ApiSuccess[ParentChildAssigned],
)
def assign_selected_parent_child(parent_admin_id: int, payload: AssignParentChildRequest):
    try:
        child = assign_parent_child(parent_admin_id, _student_row_id(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"child": child})


@router.delete(
    "/parents/{parent_admin_id}/children/{student_row_id}",
    operation_id="api_v1_admin_remove_selected_parent_child",
    response_model=ApiSuccess[None],
)
def remove_selected_parent_child(parent_admin_id: int, student_row_id: int):
    try:
        removed = remove_parent_child(parent_admin_id, student_row_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not removed:
        raise HTTPException(status_code=404, detail="Child assignment was not found.")
    invalidate_admin_page_context_cache()
    return api_success()


@router.delete(
    "/parents/{parent_admin_id}",
    operation_id="api_v1_admin_delete_parent_account",
    response_model=ApiSuccess[None],
)
def delete_parent(parent_admin_id: int):
    try:
        deleted = delete_parent_account(parent_admin_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Parent account was not found.")
    invalidate_admin_page_context_cache()
    return api_success()


@router.post(
    "/parent-children",
    operation_id="api_v1_admin_assign_parent_child",
    response_model=ApiSuccess[ParentChildAssigned],
)
def assign_parent_child_to_current(
    payload: AssignParentChildRequest,
    user: CurrentUser = Depends(get_current_user),
):
    parent_admin_id = payload.parent_admin_id or _current_parent_admin_id(user)
    try:
        child = assign_parent_child(parent_admin_id, _student_row_id(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"child": child})


@router.delete(
    "/parent-children/{student_row_id}",
    operation_id="api_v1_admin_remove_parent_child",
    response_model=ApiSuccess[None],
)
def remove_parent_child_from_current(
    student_row_id: int,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        removed = remove_parent_child(_current_parent_admin_id(user), student_row_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not removed:
        raise HTTPException(status_code=404, detail="Child assignment was not found.")
    invalidate_admin_page_context_cache()
    return api_success()
