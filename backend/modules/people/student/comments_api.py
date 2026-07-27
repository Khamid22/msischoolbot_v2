"""Student resource-comment API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.api import ApiSuccess, api_success
from backend.modules.people.student.schemas import CommentList, CommentPosted, PostCommentRequest
from backend.modules.domains.academics import contracts as comments_service
from backend.core.access import CurrentUser, get_current_user
from backend.modules.domains.identity.contracts import current_student_full_name

router = APIRouter(prefix="/resources")


@router.get(
    "/{resource_id}/comments",
    operation_id="api_v1_student_list_comments",
    response_model=ApiSuccess[CommentList],
)
def list_comments(resource_id: int, user: CurrentUser = Depends(get_current_user)):
    comments = comments_service.list_resource_comments(resource_id)
    return api_success({"comments": comments})


@router.post(
    "/{resource_id}/comments",
    operation_id="api_v1_student_post_comment",
    response_model=ApiSuccess[CommentPosted],
    status_code=201,
)
def post_comment(
    resource_id: int,
    payload: PostCommentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    if user.role != "student":
        raise HTTPException(status_code=401, detail="Login required to leave a comment.")
    author_name = current_student_full_name()
    if not author_name:
        raise HTTPException(status_code=401, detail="Could not identify your account.")

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment cannot be empty.")
    if len(body) > comments_service.COMMENT_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Comment is too long (max {comments_service.COMMENT_MAX_LENGTH} characters).",
        )

    try:
        comment = comments_service.add_resource_comment(
            resource_id, author_name=author_name, body=body
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return api_success({"comment": comment}, status_code=201)
