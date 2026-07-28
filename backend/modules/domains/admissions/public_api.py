"""Unauthenticated, token-scoped admission transport."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import RedirectResponse

from backend.application.container import AppContainer
from backend.application.customer_support import build_public_admissions
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.domains.admissions.policies import AdmissionError
from backend.modules.domains.admissions.public_service import PublicAdmissions
from backend.modules.domains.admissions.schemas import PublicAdmission

router = APIRouter(prefix="/public/admissions")


def get_public_admissions(request: Request) -> PublicAdmissions:
    container: AppContainer = request.app.state.container
    return build_public_admissions(container)


PublicAdmissionsDependency = Annotated[
    PublicAdmissions,
    Depends(get_public_admissions),
]


def _error(exc: AdmissionError):
    return api_error(str(exc), code=exc.code, status_code=exc.status_code)


@router.get(
    "/{access_token}",
    response_model=ApiSuccess[PublicAdmission],
    operation_id="api_v1_public_admission",
)
def get_admission(
    access_token: str,
    use_case: PublicAdmissionsDependency,
):
    try:
        return api_success(use_case.get(access_token))
    except AdmissionError as exc:
        return _error(exc)


@router.post(
    "/{access_token}/contract",
    response_model=ApiSuccess[PublicAdmission],
    operation_id="api_v1_public_submit_admission_contract",
)
def submit_contract(
    access_token: str,
    document: Annotated[UploadFile, File()],
    use_case: PublicAdmissionsDependency,
):
    try:
        return api_success(use_case.submit_contract(access_token, document))
    except AdmissionError as exc:
        return _error(exc)


@router.get(
    "/{access_token}/contract/download",
    response_class=RedirectResponse,
    operation_id="api_v1_public_download_admission_contract",
)
def download_contract(
    access_token: str,
    use_case: PublicAdmissionsDependency,
):
    return RedirectResponse(
        use_case.contract_download_url(access_token),
        status_code=302,
    )


__all__ = ["router"]
