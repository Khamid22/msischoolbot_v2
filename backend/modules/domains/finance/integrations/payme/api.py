"""Public Payme Merchant API JSON-RPC endpoint."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.application.container import AppContainer
from backend.modules.domains.finance.integrations.payme.service import (
    PaymeMerchant,
    PaymeRpcError,
)

router = APIRouter(prefix="/integrations/payme")

_ACCESS_DENIED = {
    "code": -32504,
    "message": {
        "en": "Insufficient privileges.",
        "ru": "Недостаточно привилегий.",
        "uz": "Ruxsat yetarli emas.",
    },
}
_INVALID_REQUEST = {
    "code": -32600,
    "message": {
        "en": "Invalid request.",
        "ru": "Неверный запрос.",
        "uz": "Noto'g'ri so'rov.",
    },
}
_PARSE_ERROR = {
    "code": -32700,
    "message": {
        "en": "JSON parsing error.",
        "ru": "Ошибка разбора JSON.",
        "uz": "JSON tahlil xatosi.",
    },
}
_SYSTEM_ERROR = {
    "code": -32400,
    "message": {
        "en": "System error.",
        "ru": "Системная ошибка.",
        "uz": "Tizim xatosi.",
    },
}


def _response(*, request_id: Any, result: Any = None, error: Any = None) -> JSONResponse:
    payload = {"id": request_id}
    payload["error" if error is not None else "result"] = error if error is not None else result
    return JSONResponse(payload, status_code=200, media_type="application/json")


def _authorized(request: Request, *, login: str, key: str) -> bool:
    authorization = str(request.headers.get("authorization") or "").strip()
    if not authorization.startswith("Basic ") or not login or not key:
        return False
    try:
        decoded = base64.b64decode(authorization[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    expected = f"{login}:{key}"
    return hmac.compare_digest(decoded.encode("utf-8"), expected.encode("utf-8"))


@router.post(
    "/merchant",
    operation_id="api_v1_payme_merchant",
)
async def merchant(request: Request) -> JSONResponse:
    container: AppContainer = request.app.state.container
    settings = container.settings.payme
    body = await request.body()
    if len(body) > settings.request_body_max_bytes:
        return _response(request_id=None, error=_INVALID_REQUEST)
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _response(request_id=None, error=_PARSE_ERROR)
    request_id = payload.get("id") if isinstance(payload, dict) else None
    if not _authorized(request, login=settings.login, key=settings.key):
        return _response(request_id=request_id, error=_ACCESS_DENIED)
    if not isinstance(payload, dict):
        return _response(request_id=request_id, error=_INVALID_REQUEST)
    method = payload.get("method")
    params = payload.get("params")
    if not isinstance(method, str) or not isinstance(params, dict):
        return _response(request_id=request_id, error=_INVALID_REQUEST)
    merchant_service = PaymeMerchant(
        unit_of_work_factory=container.unit_of_work_factory,
        settings=settings,
    )
    try:
        result = merchant_service.dispatch(method, params)
    except PaymeRpcError as exc:
        error: dict[str, Any] = {
            "code": exc.code,
            "message": dict(exc.messages),
        }
        if exc.data:
            error["data"] = exc.data
        return _response(request_id=request_id, error=error)
    except Exception:
        return _response(request_id=request_id, error=_SYSTEM_ERROR)
    return _response(request_id=request_id, result=result)


__all__ = ["router"]
