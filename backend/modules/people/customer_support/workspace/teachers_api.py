"""Read-only Customer Support transport for teacher records."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.application.container import AppContainer
from backend.application.customer_support import (
    build_customer_support_teacher_queries,
)
from backend.core.access import ActorContext, get_actor_context
from backend.core.api import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ApiSuccess,
    api_error,
    api_success,
)
from backend.modules.people.customer_support.domain_types import DirectoryStatus
from backend.modules.people.customer_support.policies import (
    CustomerSupportAccessError,
)
from backend.modules.people.customer_support.teachers.contracts import (
    TeacherSupportCursorError,
    TeacherSupportNotFoundError,
    TeacherSupportScopeError,
)
from backend.modules.people.customer_support.teachers.queries import (
    CustomerSupportTeacherQueries,
    TeacherDirectoryQuery,
)
from backend.modules.people.customer_support.teachers.schemas import (
    TeacherDetailResponse,
    TeacherDirectoryPageResponse,
)

router = APIRouter(prefix="/teachers")


def get_teacher_queries(request: Request) -> CustomerSupportTeacherQueries:
    container: AppContainer = request.app.state.container
    return build_customer_support_teacher_queries(container)


def _error_response(exc: Exception):
    if isinstance(exc, TeacherSupportNotFoundError):
        return api_error(str(exc), code="record_not_found", status_code=404)
    if isinstance(exc, TeacherSupportScopeError | CustomerSupportAccessError):
        return api_error(str(exc), code="school_scope_denied", status_code=403)
    if isinstance(exc, TeacherSupportCursorError):
        return api_error(str(exc), code="invalid_cursor", status_code=400)
    return api_error(str(exc), code="invalid_request", status_code=400)


@router.get(
    "",
    operation_id="api_v1_customer_support_teachers",
    response_model=ApiSuccess[TeacherDirectoryPageResponse],
)
def list_teachers(
    q: str = Query(default="", max_length=200),
    school_id: int | None = Query(default=None, gt=0, alias="schoolId"),
    teacher_status: DirectoryStatus = Query(default=DirectoryStatus.ALL, alias="status"),
    cursor: str = Query(default="", max_length=500),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    actor: ActorContext = Depends(get_actor_context),
    teacher_queries: CustomerSupportTeacherQueries = Depends(get_teacher_queries),
):
    try:
        page = teacher_queries.list_teachers(
            actor,
            TeacherDirectoryQuery(
                search_text=q,
                school_id=school_id,
                status=teacher_status,
                cursor=cursor or None,
                page_size=limit,
            ),
        )
    except (
        CustomerSupportAccessError,
        TeacherSupportCursorError,
        TeacherSupportScopeError,
        ValueError,
    ) as exc:
        return _error_response(exc)
    return api_success(TeacherDirectoryPageResponse.from_page(page))


@router.get(
    "/{teacher_id}",
    operation_id="api_v1_customer_support_teacher",
    response_model=ApiSuccess[TeacherDetailResponse],
)
def get_teacher(
    teacher_id: int,
    actor: ActorContext = Depends(get_actor_context),
    teacher_queries: CustomerSupportTeacherQueries = Depends(get_teacher_queries),
):
    try:
        result = teacher_queries.get_teacher(actor, teacher_id)
    except (
        CustomerSupportAccessError,
        TeacherSupportNotFoundError,
        TeacherSupportScopeError,
        ValueError,
    ) as exc:
        return _error_response(exc)
    return api_success(TeacherDetailResponse.from_result(result))


__all__ = ["get_teacher_queries", "router"]
