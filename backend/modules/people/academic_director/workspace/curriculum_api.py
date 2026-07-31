"""Academic Director controls for supplemental subject curricula."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

from backend.core.access import (
    Capability,
    CurrentUser,
    get_current_user,
    role_has_capability,
)
from backend.core.api import ApiSuccess, api_success
from backend.modules.people.academic_director.contracts import (
    CurriculumArchiveRequest,
    CurriculumConflictError,
    CurriculumDetail,
    CurriculumExternalAssetWrite,
    CurriculumNotFoundError,
    CurriculumReorderRequest,
    CurriculumRestoreRequest,
    CurriculumValidationError,
    CurriculumVariant,
    FundamentalsLessonWrite,
    SubjectCurriculumCatalog,
    add_fundamentals_external_asset,
    archive_fundamentals_asset,
    create_fundamentals_item,
    curriculum_asset_url_for_director,
    get_director_subject_curriculum,
    list_director_subject_curricula,
    reorder_fundamentals_items,
    set_fundamentals_item_archived,
    update_fundamentals_item,
    upload_fundamentals_file_asset,
)
from backend.modules.people.academic_director.workspace.curriculum_draft_api import (
    router as draft_router,
)

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def _require_curriculum_management(user: CurrentUserDep) -> None:
    if not role_has_capability(
        user.role,
        Capability.MANAGE_SUPPLEMENTAL_CURRICULUM,
    ):
        raise HTTPException(
            status_code=403,
            detail="Supplemental curriculum management is required.",
        )


router = APIRouter(
    prefix="/subject-curricula",
    dependencies=[Depends(_require_curriculum_management)],
)
router.include_router(draft_router)


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, CurriculumConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, CurriculumNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get(
    "",
    response_model=ApiSuccess[SubjectCurriculumCatalog],
    operation_id="api_v1_academic_director_list_subject_curricula",
)
def list_curricula():
    return api_success(list_director_subject_curricula())


@router.get(
    "/{subject_id}/{curriculum_key}",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_get_subject_curriculum",
)
def get_curriculum(subject_id: int, curriculum_key: CurriculumVariant):
    try:
        return api_success(get_director_subject_curriculum(subject_id, curriculum_key))
    except (CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/items",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_create_fundamentals_item",
)
def create_item(
    subject_id: int,
    payload: FundamentalsLessonWrite,
    user: CurrentUserDep,
):
    try:
        return api_success(
            create_fundamentals_item(
                subject_id,
                payload,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.patch(
    "/{subject_id}/fundamentals/items/{item_id}",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_update_fundamentals_item",
)
def update_item(
    subject_id: int,
    item_id: int,
    payload: FundamentalsLessonWrite,
    user: CurrentUserDep,
):
    try:
        return api_success(
            update_fundamentals_item(
                subject_id,
                item_id,
                payload,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/reorder",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_reorder_fundamentals",
)
def reorder_items(
    subject_id: int,
    payload: CurriculumReorderRequest,
    user: CurrentUserDep,
):
    try:
        return api_success(
            reorder_fundamentals_items(
                subject_id,
                payload.item_ids,
                payload.expected_curriculum_version,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/items/{item_id}/archive",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_archive_fundamentals_item",
)
def archive_item(
    subject_id: int,
    item_id: int,
    payload: CurriculumArchiveRequest,
    user: CurrentUserDep,
):
    try:
        return api_success(
            set_fundamentals_item_archived(
                subject_id,
                item_id,
                expected_version=payload.expected_version,
                archive=True,
                reason=payload.reason,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/items/{item_id}/restore",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_restore_fundamentals_item",
)
def restore_item(
    subject_id: int,
    item_id: int,
    payload: CurriculumRestoreRequest,
    user: CurrentUserDep,
):
    try:
        return api_success(
            set_fundamentals_item_archived(
                subject_id,
                item_id,
                expected_version=payload.expected_version,
                archive=False,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/items/{item_id}/assets",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_add_fundamentals_asset",
)
def add_external_asset(
    subject_id: int,
    item_id: int,
    payload: CurriculumExternalAssetWrite,
    user: CurrentUserDep,
):
    try:
        return api_success(
            add_fundamentals_external_asset(
                subject_id,
                item_id,
                payload,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/items/{item_id}/files",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_upload_fundamentals_file",
)
def upload_file(
    subject_id: int,
    item_id: int,
    title: Annotated[str, Form()],
    document: Annotated[UploadFile, File()],
    user: CurrentUserDep,
):
    try:
        return api_success(
            upload_fundamentals_file_asset(
                subject_id,
                item_id,
                document,
                title=title,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/{subject_id}/fundamentals/assets/{asset_id}/archive",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_academic_director_archive_fundamentals_asset",
)
def archive_asset(
    subject_id: int,
    asset_id: int,
    payload: CurriculumRestoreRequest,
    user: CurrentUserDep,
):
    try:
        return api_success(
            archive_fundamentals_asset(
                subject_id,
                asset_id,
                expected_version=payload.expected_version,
                actor_staff_id=user.staff_id,
            )
        )
    except (CurriculumConflictError, CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.get(
    "/assets/{asset_id}/open",
    operation_id="api_v1_academic_director_open_fundamentals_asset",
)
def open_asset(asset_id: int, download: bool = False):
    try:
        url = curriculum_asset_url_for_director(asset_id, download=download)
    except (CurriculumNotFoundError, CurriculumValidationError) as exc:
        raise _error(exc) from exc
    return RedirectResponse(url=url, status_code=302)


__all__ = ["router"]
