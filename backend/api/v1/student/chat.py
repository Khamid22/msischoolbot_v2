"""Student chat API v1 routes.

Rooms: "global", "subject:<name>", "group:<name>".
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api import ApiSuccess, api_success
from backend.api.v1.student.schemas import (
    ChatMessageDeleted,
    ChatMessageEdited,
    ChatMessageList,
    ChatMessageSent,
    EditChatMessageRequest,
    SendChatMessageRequest,
)
from backend.domains.communication import chat_service
from backend.security import CurrentUser, get_current_user
from backend.utils.session import current_student_full_name

router = APIRouter(prefix="/chat")


def _require_student(user: CurrentUser) -> str:
    """Student login used for chat authorship/ownership checks."""
    if user.role != "student":
        raise HTTPException(status_code=401, detail="Login required.")
    author_name = current_student_full_name()
    if not author_name:
        raise HTTPException(status_code=401, detail="Could not identify your account.")
    return user.login or author_name


@router.get(
    "/messages",
    operation_id="api_v1_student_chat_list",
    response_model=ApiSuccess[ChatMessageList],
)
def list_messages(
    room: str = "global",
    before_id: int = 0,
    after_id: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    room = room.strip()
    if not chat_service.validate_room(room):
        raise HTTPException(status_code=400, detail="Invalid room.")
    messages = chat_service.list_messages(room, before_id=before_id, after_id=after_id)
    return api_success({"messages": messages, "room": room})


@router.post(
    "/messages",
    operation_id="api_v1_student_chat_send",
    response_model=ApiSuccess[ChatMessageSent],
    status_code=201,
)
def send_message(
    payload: SendChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    student_login = _require_student(user)
    room = payload.room.strip()
    body = payload.body.strip()

    if not chat_service.validate_room(room):
        raise HTTPException(status_code=400, detail="Invalid room.")
    if not body:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(body) > chat_service.MAX_BODY:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long (max {chat_service.MAX_BODY} chars).",
        )

    try:
        message = chat_service.send_message(
            room=room,
            author_name=current_student_full_name(),
            student_login=student_login,
            body=body,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return api_success({"message": message}, status_code=201)


@router.put(
    "/messages/{msg_id}",
    operation_id="api_v1_student_chat_edit",
    response_model=ApiSuccess[ChatMessageEdited],
)
def edit_message(
    msg_id: int,
    payload: EditChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    student_login = _require_student(user)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(body) > chat_service.MAX_BODY:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long (max {chat_service.MAX_BODY} chars).",
        )

    try:
        edited = chat_service.edit_message(msg_id, student_login=student_login, body=body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return api_success(edited)


@router.delete(
    "/messages/{msg_id}",
    operation_id="api_v1_student_chat_delete",
    response_model=ApiSuccess[ChatMessageDeleted],
)
def delete_message(
    msg_id: int,
    user: CurrentUser = Depends(get_current_user),
):
    student_login = _require_student(user)
    try:
        chat_service.delete_message(msg_id, student_login=student_login)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return api_success({"deleted": True, "id": msg_id})
