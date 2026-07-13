"""System API routes for MSI LMS Portal."""

from time import perf_counter

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.core.database import check_database_ready
from backend.core.http import ApiMessage, api_message

router = APIRouter()


@router.get("/api/v1/system/status", response_model=ApiMessage, tags=["system"])
def system_status():
    """Returns the status of the MSI School backend API."""
    return api_message("MSI School Backend API is running and operational.")


@router.get("/health/live", include_in_schema=False)
def health_live(request: Request):
    return {
        "status": "ok",
        "request_id": str(getattr(request.state, "request_id", "") or ""),
    }


@router.get("/health/ready", include_in_schema=False)
def health_ready(request: Request):
    started = perf_counter()
    request_id = str(getattr(request.state, "request_id", "") or "")
    try:
        if not check_database_ready(timeout=2.0):
            raise RuntimeError("Database readiness query returned an invalid result.")
    except Exception:
        return JSONResponse(
            {"status": "not_ready", "database": "unavailable", "request_id": request_id},
            status_code=503,
        )
    return {
        "status": "ok",
        "database": "ready",
        "latency_ms": round((perf_counter() - started) * 1000, 1),
        "request_id": request_id,
    }


__all__ = ["health_live", "health_ready", "router", "system_status"]
