from typing import Any, Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def api_success(data: Any = None, status_code: int = 200) -> JSONResponse:
    payload = {
        "status": "success",
        "data": jsonable_encoder(data) if data is not None else None,
    }
    return JSONResponse(content=payload, status_code=status_code)


def api_error(
    message: str,
    code: Optional[str] = None,
    details: Optional[Any] = None,
    status_code: int = 400,
) -> JSONResponse:
    """Returns a standardized error JSONResponse with customizable message, code, and details."""
    payload = {
        "status": "error",
        "message": message,
    }
    if code is not None:
        payload["code"] = code
    if details is not None:
        payload["details"] = jsonable_encoder(details)
    return JSONResponse(content=payload, status_code=status_code)


def api_message(message: str, status_code: int = 200) -> JSONResponse:
    """Returns a standardized success JSONResponse containing a message string."""
    payload = {
        "status": "success",
        "message": message,
    }
    return JSONResponse(content=payload, status_code=status_code)
