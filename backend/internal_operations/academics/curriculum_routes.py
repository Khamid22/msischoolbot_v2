"""System-admin read routes for curriculum programs and their items."""

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.api import ApiSuccess, api_success
from backend.modules.academics.groups.read_service import (
    list_program_item_page,
    list_program_page,
)


router = APIRouter()


@router.get(
    "/programs",
    operation_id="api_v1_admin_list_academic_programs",
    response_model=ApiSuccess[dict[str, Any]],
)
def list_academic_programs(cursor: str = "", limit: int = 50):
    try:
        return api_success(list_program_page(cursor=cursor, limit=limit))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/programs/{program_id}/items",
    operation_id="api_v1_admin_list_academic_program_items",
    response_model=ApiSuccess[dict[str, Any]],
)
def list_academic_program_items(
    program_id: int,
    cursor: str = "",
    limit: int = 100,
):
    try:
        return api_success(
            list_program_item_page(program_id, cursor=cursor, limit=limit)
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
