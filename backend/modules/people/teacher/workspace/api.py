"""Teacher subject-curriculum API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from backend.core.access import (
    Capability,
    CurrentUser,
    get_current_user,
    require_role,
    role_has_capability,
)
from backend.core.api import ApiSuccess, api_success
from backend.modules.people.teacher.contracts import (
    CurriculumDetail,
    CurriculumNotFoundError,
    CurriculumPermissionError,
    CurriculumValidationError,
    CurriculumVariant,
    CurriculumViewAcknowledgement,
    SubjectCurriculumCatalog,
    acknowledge_teacher_curriculum_view,
    curriculum_asset_url_for_teacher,
    curriculum_slide_url,
    get_teacher_subject_curriculum,
    list_teacher_subject_curricula,
)

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def _require_curriculum_access(user: CurrentUserDep) -> None:
    if not role_has_capability(user.role, Capability.VIEW_SUBJECT_CURRICULUM):
        raise HTTPException(status_code=403, detail="Subject curriculum access is required.")


router = APIRouter(
    prefix="/teacher",
    dependencies=[
        Depends(require_role("teacher")),
        Depends(_require_curriculum_access),
    ],
)


def _teacher_id(user: CurrentUser) -> int:
    teacher_id = int(user.teacher_id or 0)
    if teacher_id <= 0:
        raise HTTPException(status_code=403, detail="An active teacher profile is required.")
    return teacher_id


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, CurriculumPermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, CurriculumNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/subject-curricula",
    response_model=ApiSuccess[SubjectCurriculumCatalog],
    operation_id="api_v1_teacher_list_subject_curricula",
)
def list_curricula(user: CurrentUserDep):
    try:
        return api_success(list_teacher_subject_curricula(_teacher_id(user)))
    except (CurriculumNotFoundError, CurriculumPermissionError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.get(
    "/subject-curricula/{subject_id}/{curriculum_key}",
    response_model=ApiSuccess[CurriculumDetail],
    operation_id="api_v1_teacher_get_subject_curriculum",
)
def get_curriculum(
    subject_id: int,
    curriculum_key: CurriculumVariant,
    user: CurrentUserDep,
):
    try:
        return api_success(
            get_teacher_subject_curriculum(
                _teacher_id(user),
                subject_id,
                curriculum_key,
            )
        )
    except (CurriculumNotFoundError, CurriculumPermissionError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.post(
    "/subject-curricula/{subject_id}/{curriculum_key}/viewed",
    response_model=ApiSuccess[CurriculumViewAcknowledgement],
    operation_id="api_v1_teacher_acknowledge_subject_curriculum",
)
def acknowledge_curriculum(
    subject_id: int,
    curriculum_key: CurriculumVariant,
    user: CurrentUserDep,
):
    try:
        return api_success(
            acknowledge_teacher_curriculum_view(
                _teacher_id(user),
                subject_id,
                curriculum_key,
            )
        )
    except (CurriculumNotFoundError, CurriculumPermissionError, CurriculumValidationError) as exc:
        raise _error(exc) from exc


@router.get(
    "/subject-curricula/assets/{asset_id}/open",
    operation_id="api_v1_teacher_open_subject_curriculum_asset",
)
def open_asset(
    asset_id: int,
    user: CurrentUserDep,
    download: bool = False,
):
    try:
        url = curriculum_asset_url_for_teacher(
            _teacher_id(user),
            asset_id,
            download=download,
        )
    except (CurriculumNotFoundError, CurriculumPermissionError, CurriculumValidationError) as exc:
        raise _error(exc) from exc
    return RedirectResponse(url=url, status_code=302)


@router.get(
    "/subject-curricula/assets/{asset_id}/slides/{slide_number}/open",
    operation_id="api_v1_teacher_open_subject_curriculum_slide",
)
def open_slide(
    asset_id: int,
    slide_number: int,
    user: CurrentUserDep,
):
    try:
        url = curriculum_slide_url(
            asset_id,
            slide_number,
            teacher_id=_teacher_id(user),
        )
    except (CurriculumNotFoundError, CurriculumPermissionError, CurriculumValidationError) as exc:
        raise _error(exc) from exc
    return RedirectResponse(url=url, status_code=302)


__all__ = ["router"]
