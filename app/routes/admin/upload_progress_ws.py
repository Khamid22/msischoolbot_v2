import json

from app.extensions import sock
from app.routes.admin.services.upload_progress_service import (
    normalize_upload_id,
    wait_for_upload_event,
)
from app.routes.students.services.session_state_service import current_auth_role

_WEBSOCKET_ROUTES_REGISTERED = False


def register_admin_upload_progress_ws():
    global _WEBSOCKET_ROUTES_REGISTERED
    if _WEBSOCKET_ROUTES_REGISTERED:
        return
    _WEBSOCKET_ROUTES_REGISTERED = True

    @sock.route("/ws/resource-upload/<upload_id>")
    def resource_upload_progress_socket(ws, upload_id):
        normalized_upload_id = normalize_upload_id(upload_id)
        if current_auth_role() != "admin" or not normalized_upload_id:
            try:
                ws.send(
                    json.dumps(
                        {
                            "error": True,
                            "done": True,
                            "percent": 0.0,
                            "message": "Unauthorized upload progress request.",
                        }
                    )
                )
            except Exception:
                return
            return

        last_seq = 0
        idle_cycles = 0
        while True:
            event = wait_for_upload_event(
                normalized_upload_id,
                after_seq=last_seq,
                timeout_seconds=20.0,
            )
            if event is None:
                idle_cycles += 1
                if idle_cycles >= 90:
                    return
                try:
                    ws.send(json.dumps({"type": "heartbeat"}))
                except Exception:
                    return
                continue

            idle_cycles = 0
            last_seq = int(event.get("seq", last_seq))
            try:
                ws.send(json.dumps(event))
            except Exception:
                return

            if bool(event.get("done")):
                return
