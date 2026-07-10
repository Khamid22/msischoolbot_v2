"""System API routes for MSI LMS Portal."""

from fastapi import APIRouter

from backend.core.http import ApiMessage, api_message

router = APIRouter()


@router.get("/api/v1/system/status", response_model=ApiMessage, tags=["system"])
def system_status():
    """Returns the status of the MSI School backend API."""
    return api_message("MSI School Backend API is running and operational.")


__all__ = ["router", "system_status"]
