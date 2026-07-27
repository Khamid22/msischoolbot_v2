import os
from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.modules.domains.identity.api import (
    get_current_user,
    router as auth_api_router,
)
from backend.application.system_api import (
    router as system_api_router,
    system_status,
)

router = APIRouter()
router.include_router(system_api_router)
router.include_router(auth_api_router)

# Set at startup in server.py
STATIC_FOLDER = ""


@router.get("/manifest.webmanifest")
def manifest():
    path = os.path.join(STATIC_FOLDER, "manifest.webmanifest")
    if not os.path.isfile(path):
        return {"error": "manifest not found"}
    return FileResponse(
        path,
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/sw.js")
def service_worker():
    path = os.path.join(STATIC_FOLDER, "js", "sw.js")
    if not os.path.isfile(path):
        return {"error": "service worker not found"}
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
