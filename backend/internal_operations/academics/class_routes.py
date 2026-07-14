"""System-admin routes for academic class creation."""

from fastapi import APIRouter, HTTPException

from backend.core.api import ApiSuccess, api_success
from backend.internal_operations.academics.common import model_payload
from backend.modules.academics.groups.operations import list_admin_academic_context
from backend.modules.academics.schemas import (
    AdminAcademicContextPayload,
    AdminCreateAcademicClassRequest,
)
from backend.modules.organization.operations import create_class_from_payload
from backend.platform.admin_page_cache import invalidate_admin_page_context_cache


router = APIRouter()


@router.post(
    "/classes",
    operation_id="api_v1_admin_create_academic_class",
    response_model=ApiSuccess[AdminAcademicContextPayload],
)
def create_academic_class(payload: AdminCreateAcademicClassRequest):
    try:
        create_class_from_payload(model_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(list_admin_academic_context(include_heavy=False))
