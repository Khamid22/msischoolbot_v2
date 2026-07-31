"""Academic Director draft and media routes for Fundamentals lessons."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

from backend.core.access import CurrentUser, get_current_user
from backend.core.api import ApiSuccess, api_success
from backend.modules.people.academic_director.contracts import (
    CurriculumConflictError,
    CurriculumDetail,
    CurriculumDraftStartRequest,
    CurriculumExternalAssetWrite,
    CurriculumLessonDraft,
    CurriculumNotFoundError,
    CurriculumRestoreRequest,
    CurriculumValidationError,
    FundamentalsLessonPublish,
    abandon_fundamentals_draft,
    add_draft_external_asset,
    curriculum_slide_url,
    detach_draft_asset,
    get_fundamentals_draft,
    publish_fundamentals_draft,
    retry_presentation_conversion,
    start_fundamentals_draft,
    update_fundamentals_draft,
    upload_draft_file_asset,
)

router = APIRouter()
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, CurriculumConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, CurriculumNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/{subject_id}/fundamentals/drafts",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_start_fundamentals_draft",
)
def start_draft(
    subject_id: int,
    payload: CurriculumDraftStartRequest,
    user: CurrentUserDep,
):
    try:
        return api_success(
            start_fundamentals_draft(
                subject_id,
                item_id=payload.item_id,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.get(
    "/{subject_id}/fundamentals/drafts/{draft_id}",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_get_fundamentals_draft",
)
def get_draft(subject_id: int, draft_id: int):
    try:
        return api_success(get_fundamentals_draft(subject_id, draft_id))
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.patch(
    "/{subject_id}/fundamentals/drafts/{draft_id}",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_update_fundamentals_draft",
)
def update_draft(
    subject_id: int,
    draft_id: int,
    payload: FundamentalsLessonPublish,
    user: CurrentUserDep,
):
    try:
        return api_success(
            update_fundamentals_draft(
                subject_id,
                draft_id,
                payload,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/drafts/{draft_id}/publish",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_publish_fundamentals_draft",
)
def publish_draft(
    subject_id: int,
    draft_id: int,
    payload: FundamentalsLessonPublish,
    user: CurrentUserDep,
):
    try:
        return api_success(
            publish_fundamentals_draft(
                subject_id,
                draft_id,
                payload,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/drafts/{draft_id}/abandon",
    response_model=ApiSuccess[dict[str, str]],
    operation_id="api_v1_academic_director_abandon_fundamentals_draft",
)
def abandon_draft(
    subject_id: int,
    draft_id: int,
    user: CurrentUserDep,
):
    try:
        abandon_fundamentals_draft(
            subject_id,
            draft_id,
            actor_staff_id=user.staff_id,
        )
        return api_success({"message": "Draft abandoned."})
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/drafts/{draft_id}/assets",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_add_fundamentals_draft_asset",
)
def add_external_asset(
    subject_id: int,
    draft_id: int,
    payload: CurriculumExternalAssetWrite,
    user: CurrentUserDep,
):
    try:
        return api_success(
            add_draft_external_asset(
                subject_id,
                draft_id,
                payload,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/drafts/{draft_id}/files",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_upload_fundamentals_draft_file",
)
def upload_file(
    subject_id: int,
    draft_id: int,
    title: Annotated[str, Form()],
    document: Annotated[UploadFile, File()],
    user: CurrentUserDep,
):
    try:
        return api_success(
            upload_draft_file_asset(
                subject_id,
                draft_id,
                document,
                title=title,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/drafts/{draft_id}/assets/{asset_id}/detach",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_detach_fundamentals_draft_asset",
)
def detach_asset(
    subject_id: int,
    draft_id: int,
    asset_id: int,
    payload: CurriculumRestoreRequest,
    user: CurrentUserDep,
):
    try:
        return api_success(
            detach_draft_asset(
                subject_id,
                draft_id,
                asset_id,
                expected_version=payload.expected_version,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/drafts/{draft_id}/assets/{asset_id}/retry",
    response_model=ApiSuccess[CurriculumLessonDraft],
    operation_id="api_v1_academic_director_retry_fundamentals_presentation",
)
def retry_conversion(
    subject_id: int,
    draft_id: int,
    asset_id: int,
    user: CurrentUserDep,
):
    try:
        return api_success(
            retry_presentation_conversion(
                subject_id,
                draft_id,
                asset_id,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.get(
    "/assets/{asset_id}/slides/{slide_number}/open",
    operation_id="api_v1_academic_director_open_fundamentals_slide",
)
def open_slide(asset_id: int, slide_number: int):
    try:
        url = curriculum_slide_url(
            asset_id,
            slide_number,
            teacher_id=None,
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc
    return RedirectResponse(url=url, status_code=302)


__all__ = ["router"]
