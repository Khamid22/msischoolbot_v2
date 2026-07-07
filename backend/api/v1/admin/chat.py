"""Admin chat moderation API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api import ApiSuccess, api_success
from backend.api.v1.admin.schemas import (
    AdminChatMessages,
    BlockStudentRequest,
    BlockedStudents,
    ChatRooms,
)
from backend.domains.communication import chat_service
from backend.security import CurrentUser, get_current_user

router = APIRouter(prefix="/chat")


@router.get(
    "/messages",
    operation_id="api_v1_admin_chat_list",
    response_model=ApiSuccess[AdminChatMessages],
)
def list_messages(room: str = "global", before_id: int = 0):
    room = room.strip()
    messages = chat_service.admin_list_messages(room, before_id=before_id)
    return api_success({"messages": messages, "room": room})


@router.delete(
    "/messages/{msg_id}",
    operation_id="api_v1_admin_chat_delete",
    response_model=ApiSuccess[None],
)
def delete_message(msg_id: int):
    try:
        chat_service.admin_delete_message(msg_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return api_success()


@router.post(
    "/block",
    operation_id="api_v1_admin_chat_block",
    response_model=ApiSuccess[None],
    status_code=201,
)
def block_student(
    payload: BlockStudentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    student_id = payload.studentId.strip().lower()
    if not student_id:
        raise HTTPException(status_code=400, detail="studentId required.")
    chat_service.block_student(
        student_id,
        blocked_by=user.login,
        reason=payload.reason.strip()[:300],
    )
    return api_success(status_code=201)


@router.delete(
    "/block/{student_id}",
    operation_id="api_v1_admin_chat_unblock",
    response_model=ApiSuccess[None],
)
def unblock_student(student_id: str):
    chat_service.unblock_student(student_id)
    return api_success()


@router.get(
    "/blocked",
    operation_id="api_v1_admin_chat_blocked",
    response_model=ApiSuccess[BlockedStudents],
)
def list_blocked():
    return api_success({"blocked": chat_service.list_blocked_students()})


@router.get(
    "/rooms",
    operation_id="api_v1_admin_chat_rooms",
    response_model=ApiSuccess[ChatRooms],
)
def list_rooms():
    return api_success({"rooms": chat_service.list_rooms()})
